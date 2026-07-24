#!/usr/bin/env python3
"""run_campaign.py — runner de campañas de fuerza bruta (F6.4).

Toma una campaña declarativa (.toml o .json), deriva la grilla de configs,
DECLARA el número esperado de configs y el costo estimado ANTES de correr
(límite máximo configurable → aborta si se excede: control de explosión),
genera el campaign_manifest con los config_id esperados, ejecuta cada config
publicando al store (P3.1/P3.2 inline en store.publish_run), y cierra con P3.0
(completitud: expected == succeeded + failed, missing=0, duplicated=0).

Grilla gruesa primero, refinamiento local después = campañas pre-registradas
sucesivas, nunca un barrido silencioso.

Uso:
  python tools/run_campaign.py --campaign campaign.toml
  python tools/run_campaign.py --campaign campaign.toml --dry-run   # solo declara

Formato (.toml):
  campaign_id = "gaps2_smoke"
  store       = "runs/nt8_bridge/store"
  chart_tz    = "UTC"
  max_configs = 50
  [data]
    parquet   = "data/nt8/6E/6E_09-25_ticks.parquet"
    contract  = "6E 09-25"
    start_utc = "2025-08-01T00:00:00"
    end_utc   = "2025-08-02T00:00:00"
  [[jobs]]
    indicator = "Gaps2"
    bars      = ["time:1"]
    [jobs.grid]
      export_floor_ticks = [2, 3]
      min_gap_ticks      = [5, 8]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import audit, bars as bars_mod, identity, store  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import BAR_DRIVEN, REGISTRY  # noqa: E402
from edgelab.bridge.viewer_export import bar_key_of  # noqa: E402


def _load(path):
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    import tomllib
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _iso_ns(s):
    if not s:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "")).replace(
        tzinfo=timezone.utc).timestamp() * 1e9)


def _sha256(path, chunk=1 << 22):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _expand_grid(grid):
    """dict{param: [valores]} -> lista de dicts (producto cartesiano)."""
    if not grid:
        return [{}]
    keys = sorted(grid)
    return [dict(zip(keys, combo)) for combo in itertools.product(*(grid[k] for k in keys))]


def _parse_bar_spec(spec):
    kind, _, val = spec.partition(":")
    if kind not in ("time", "tick") or not val.isdigit():
        raise SystemExit("bar spec inválido: %r (time:N | tick:N)" % spec)
    return kind, int(val)


def _plan(camp):
    """Devuelve la lista de configs planificadas (sin correr): valida params,
    computa config_id. Aborta ante param inválido (no arranca a medias)."""
    chart_tz = camp.get("chart_tz", "UTC")
    planned, errors = [], []
    for job in camp["jobs"]:
        ind = job["indicator"]
        if ind not in REGISTRY:
            errors.append("indicador desconocido: %s" % ind)
            continue
        kid = identity.kernel_id(ind)
        for bar_spec in job.get("bars", ["time:1"]):
            _parse_bar_spec(bar_spec)
            for params in _expand_grid(job.get("grid", {})):
                verr = identity.validate_params(ind, params)
                if verr:
                    errors.extend("%s %s: %s" % (ind, bar_spec, e) for e in verr)
                    continue
                planned.append(dict(indicator=ind, bar_spec=bar_spec, params=params,
                                    kernel_id=kid))
    return planned, chart_tz, errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="Runner de campañas del bridge (F6.4)")
    ap.add_argument("--campaign", required=True, help="campaign.toml | campaign.json")
    ap.add_argument("--dry-run", action="store_true", help="solo declarar; no correr")
    ap.add_argument("--audit", action="store_true", help="correr store_audit al cerrar")
    args = ap.parse_args(argv)

    camp = _load(args.campaign)
    data = camp["data"]
    store_root = camp["store"]
    max_configs = int(camp.get("max_configs", 200))
    gen_utc = datetime.now(timezone.utc).isoformat()

    planned, chart_tz, errors = _plan(camp)
    if errors:
        print("PARÁMETROS INVÁLIDOS (la campaña no arranca):")
        for e in errors:
            print("  -", e)
        return 2

    # dataset_id (una vez): carga los ticks del rango declarado
    tk = ticks_mod.load_canonical_parquet(
        data["parquet"], contract=data.get("contract"),
        start_utc_ns=_iso_ns(data.get("start_utc")), end_utc_ns=_iso_ns(data.get("end_utc")))
    src_sha = _sha256(data["parquet"])
    ds_id = identity.dataset_id(tk, tz_interpretation="canonical_utc_verified",
                                source_sha256=src_sha)

    # completar config_id/run_id ahora que hay dataset_id + bars
    bars_cache = {}

    def bars_for(spec):
        if spec not in bars_cache:
            kind, val = _parse_bar_spec(spec)
            b = (bars_mod.build_time_bars(tk, val) if kind == "time"
                 else bars_mod.build_tick_bars(tk, val))
            bars_cache[spec] = b
        return bars_cache[spec]

    for pc in planned:
        b = bars_for(pc["bar_spec"])
        pc["bar_key"] = bar_key_of(b)
        pc["config_id"] = identity.config_id(pc["indicator"], pc["params"],
                                             pc["bar_key"], chart_tz, pc["kernel_id"])
        pc["run_id"] = identity.run_id(ds_id, pc["config_id"],
                                       data.get("start_utc"), data.get("end_utc"))

    expected_config_ids = sorted({pc["config_id"] for pc in planned})

    # --- DECLARACIÓN DE COSTO ANTES DE CORRER ---
    print("== campaña %s ==" % camp["campaign_id"])
    print("  dataset_id      : %s (%s %s, %d ticks)" % (ds_id, tk.instrument, tk.contract, len(tk)))
    print("  configs planificadas : %d (config_id únicos: %d)" % (len(planned), len(expected_config_ids)))
    print("  costo estimado  : %d corridas de kernel sobre %d ticks c/u" % (len(planned), len(tk)))
    print("  límite máximo   : %d" % max_configs)
    by_ind = {}
    for pc in planned:
        by_ind.setdefault(pc["indicator"], 0)
        by_ind[pc["indicator"]] += 1
    for ind, n in sorted(by_ind.items()):
        print("      %-14s %d configs" % (ind, n))
    if len(planned) > max_configs:
        print("ABORTA: %d configs > max_configs=%d (control de explosión). "
              "Subí max_configs o achicá la grilla." % (len(planned), max_configs))
        return 2

    campaign_manifest = dict(
        campaign_id=camp["campaign_id"], dataset_id=ds_id,
        expected_config_ids=expected_config_ids, chart_tz=chart_tz,
        data=dict(parquet=data["parquet"], contract=tk.contract, sha256=src_sha,
                  start_utc=data.get("start_utc"), end_utc=data.get("end_utc")),
        bar_specs=sorted({pc["bar_spec"] for pc in planned}),
        n_planned=len(planned), generated_utc=gen_utc)
    os.makedirs(store_root, exist_ok=True)
    cm_path = os.path.join(store_root, "campaign_%s.json" % camp["campaign_id"])
    with open(cm_path, "w", encoding="utf-8") as fh:
        json.dump(campaign_manifest, fh, indent=2, ensure_ascii=False)
    print("  campaign_manifest -> %s" % cm_path)

    if args.dry_run:
        print("DRY-RUN: no se ejecuta nada.")
        return 0

    # --- EJECUCIÓN ---
    src = dict(path=data["parquet"], sha256=src_sha, rows=len(tk),
               range_start_utc=data.get("start_utc"), range_end_utc=data.get("end_utc"),
               kind="parquet_f2")
    succeeded, failed = [], []
    for pc in planned:
        b = bars_for(pc["bar_spec"])
        mod = REGISTRY[pc["indicator"]]
        try:
            res = (mod.run(tk, b, bars_mod.build_footprints(tk, b), params=pc["params"], chart_tz=chart_tz)
                   if pc["indicator"] in BAR_DRIVEN else
                   mod.run(tk, b, params=pc["params"], chart_tz=chart_tz))
            store.publish_run(
                store_root, kernel_result=res, indicator=pc["indicator"],
                tick_size=tk.tick_size, instrument=tk.instrument, contract=tk.contract,
                bar_key=pc["bar_key"], dataset_id=ds_id, kernel_id=pc["kernel_id"],
                config_id=pc["config_id"], run_id=pc["run_id"], params=res["params"],
                source=src, chart_tz=chart_tz, generated_utc=gen_utc)
            succeeded.append(pc["config_id"])
        except Exception as e:
            failed.append(dict(config_id=pc["config_id"], indicator=pc["indicator"],
                               error="%s: %s" % (type(e).__name__, e)))
            print("  FALLO %s %s: %s" % (pc["indicator"], pc["config_id"], e))

    # --- CIERRE P3.0 (completitud de campaña) ---
    campaign_manifest["failed_config_ids"] = [f["config_id"] for f in failed]
    p30 = audit.check_campaign(store_root, campaign_manifest)
    print("== cierre P3.0 == expected=%d succeeded=%d failed=%d missing=%d duplicated=%d"
          % (p30["expected"], len(succeeded), len(failed), len(p30["missing"]), len(p30["duplicated"])))
    if p30["missing"]:
        print("  FALTAN (nunca corrieron):", p30["missing"])
    with open(cm_path, "w", encoding="utf-8") as fh:
        json.dump(campaign_manifest, fh, indent=2, ensure_ascii=False)

    ok = p30["ok"] and not failed
    if args.audit and ok:
        arep = audit.audit_all(store_root, campaign=campaign_manifest)
        print("== store_audit == %s (%d particiones)"
              % ("VERDE" if arep["ok"] else "ROJO", arep["n_partitions"]))
        ok = ok and arep["ok"]
    print("RESULTADO CAMPAÑA:", "OK" if ok else "CON FALLAS")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
