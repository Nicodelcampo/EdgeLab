#!/usr/bin/env python3
"""CLI del bridge NT8 -> EdgeLab: kernels + paridad + visor multi-run.

Corre uno o más indicadores sobre el parquet canónico F2 (o ticks sintéticos),
con UNA O VARIAS configuraciones paramétricas por indicador (param grid). Cada
run queda identificado por (indicator, param_set_id, bar_key) y sus zonas van
al zone store (zones.parquet) — la semilla de coordenadas reutilizables.

Ejemplos:
  # demo sintética
  python tools/run_nt8_bridge.py --synthetic --indicator Gaps2 --out runs/nt8_bridge/demo

  # muestra real F2 + grid de parámetros + oráculo NT8
  python tools/run_nt8_bridge.py --data data/nt8/6E/6E_09-25_ticks.parquet \
      --contract "6E 09-25" --start-utc 2025-08-01T00:00:00 --end-utc 2025-08-02T00:00:00 \
      --bars time:1 --indicator Gaps2 \
      --param-grid "Gaps2=[{\"min_gap_ticks\":4},{\"min_gap_ticks\":8}]" \
      --oracle Gaps2=oracles/Gaps2_events_nt8.csv --out runs/nt8_bridge/6e_0925_gaps2

El bar spec por defecto viene de --bars (time:N minutos | tick:N ticks); un
param set puede overridearlo con la clave reservada "bars".
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from edgelab.bridge import bars as bars_mod  # noqa: E402
from edgelab.bridge import oracle, parity, viewer_export, zone_store  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import BAR_DRIVEN, REGISTRY  # noqa: E402

VIEWER_SRC = os.path.join(REPO, "viewer", "nt8_bridge")


def parse_bar_spec(spec: str):
    kind, _, val = spec.partition(":")
    if kind not in ("time", "tick") or not val.isdigit():
        raise SystemExit(f"bar spec inválido: {spec!r} (esperado time:N | tick:N)")
    return kind, int(val)


def build_bars(ticks, spec):
    kind, val = parse_bar_spec(spec)
    return (bars_mod.build_time_bars(ticks, minutes=val) if kind == "time"
            else bars_mod.build_tick_bars(ticks, ticks_per_bar=val))


def iso_to_ns(s):
    if s is None:
        return None
    d = datetime.fromisoformat(s.replace("Z", ""))
    return int(d.replace(tzinfo=timezone.utc).timestamp() * 1e9)


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def git_rev():
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "unknown"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bridge NT8 -> EdgeLab (kernels + visor + paridad)")
    ap.add_argument("--data", help="parquet canónico F2")
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--contract", default=None)
    ap.add_argument("--instrument", default=None)
    ap.add_argument("--start-utc", default=None)
    ap.add_argument("--end-utc", default=None)
    ap.add_argument("--bars", default="time:1", help="bar spec default: time:N | tick:N")
    ap.add_argument("--indicator", action="append", default=[],
                    help="kernel (repetible); 'all' = todos los del registry")
    ap.add_argument("--params", action="append", default=[],
                    help="JSON: Indicador={...} (un param set)")
    ap.add_argument("--param-grid", action="append", default=[],
                    help="JSON: Indicador=[{...},{...}] (varios param sets)")
    ap.add_argument("--oracle", action="append", default=[],
                    help="EventLog NT8: Indicador=ruta (repetible)")
    ap.add_argument("--chart-tz", default="UTC")
    ap.add_argument("--tol-created-ms", type=int, default=60000)
    ap.add_argument("--tol-geom-ticks", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zone-store", default=None,
                    help="raíz del zone store formal (F6): particiones "
                         "indicator/param_set_id/bar_key/contract + manifest + trusted")
    args = ap.parse_args(argv)

    names = args.indicator or ["all"]
    if "all" in names:
        names = list(REGISTRY.keys())
    for n in names:
        if n not in REGISTRY:
            ap.error(f"indicador desconocido: {n} (válidos: {', '.join(REGISTRY)})")

    grids: dict[str, list] = {n: [] for n in names}
    for spec in args.params:
        k, _, v = spec.partition("=")
        grids.setdefault(k, []).append(json.loads(v))
    for spec in args.param_grid:
        k, _, v = spec.partition("=")
        grids.setdefault(k, []).extend(json.loads(v))
    for n in names:
        if not grids.get(n):
            grids[n] = [{}]
    oracle_by = {}
    for spec in args.oracle:
        k, _, v = spec.partition("=")
        oracle_by[k] = v

    if args.synthetic:
        tk = ticks_mod.make_synthetic()
    elif args.data:
        tk = ticks_mod.load_canonical_parquet(
            args.data, contract=args.contract, instrument=args.instrument,
            start_utc_ns=iso_to_ns(args.start_utc), end_utc_ns=iso_to_ns(args.end_utc))
    else:
        ap.error("falta --data o --synthetic")
    print(f"ticks: {len(tk):,} · {tk.instrument} {tk.contract} · tick_size {tk.tick_size}")

    os.makedirs(args.out, exist_ok=True)
    gen_utc = datetime.now(timezone.utc).isoformat()
    code_rev = git_rev()
    src_sha = sha256_file(args.data) if args.data else None
    bars_cache, fps_cache, p1a_cache = {}, {}, {}

    def bars_for(spec):
        if spec not in bars_cache:
            b = build_bars(tk, spec)
            bars_cache[spec] = b
            f = bars_mod.build_footprints(tk, b)
            fps_cache[spec] = f
            p1a_cache[spec] = bars_mod.p1a_gate(tk, b, f)
            g = p1a_cache[spec]
            print(f"[bars {spec}] {len(b)} barras · P1A {g['status']} "
                  f"(quote_frac={g['quote_fraction']}, mismatches={g['footprint_mismatches']})")
        return bars_cache[spec], fps_cache[spec], p1a_cache[spec]

    runs, manifest_runs, any_fail = [], [], False
    for n in names:
        orc = None
        if n in oracle_by:
            orc = oracle.parse_nt8_log(oracle_by[n], chart_tz=args.chart_tz,
                                       tick_size=tk.tick_size)
        for pset in grids[n]:
            pset = dict(pset)
            bar_spec = pset.pop("bars", args.bars)
            bars, fps, p1a = bars_for(bar_spec)
            mod = REGISTRY[n]
            res = (mod.run(tk, bars, fps, params=pset, chart_tz=args.chart_tz)
                   if n in BAR_DRIVEN else
                   mod.run(tk, bars, params=pset, chart_tz=args.chart_tz))
            psid = viewer_export.param_set_id(res["params"], viewer_export.bar_key_of(bars))
            run_id = f"{n}_{psid}"
            csv_path = os.path.join(args.out, f"{run_id}_events_py.csv")
            with open(csv_path, "w", encoding="utf-8") as fh:
                if res.get("params_line"):
                    fh.write(res["params_line"] + "\n")
                if res.get("header"):
                    fh.write(res["header"] + "\n")
                fh.write("\n".join(res["csv_lines"]) + "\n")
            rep = None
            if orc is not None:
                extra = [dict(code="FOOTPRINT_MISMATCH", py_id=None, nt8_id=None,
                              detail=d["detail"]) for d in p1a["diagnostics"]
                         if d["code"] == "FOOTPRINT_MISMATCH"]
                rep = parity.match_zones(res["zones"], orc["zones"], tk.tick_size,
                                         tol_created_ms=args.tol_created_ms,
                                         tol_geom_ticks=args.tol_geom_ticks,
                                         extra_diags=extra)
                any_fail |= rep["gate"] == "FAIL"
            run = viewer_export.build_run(run_id, n, bars, res, psid,
                                          oracle=orc, parity=rep, p1a=p1a)
            runs.append(run)
            manifest_runs.append(dict(
                run_id=run_id, indicator=n, param_set_id=psid,
                bar_key=viewer_export.bar_key_of(bars), params=res["params"],
                n_zones=len(res["zones"]), n_events=len(res["events"]),
                p1a=p1a["status"], parity_gate=(rep["gate"] if rep else None),
                events_csv=os.path.basename(csv_path)))
            gate = rep["gate"] if rep else "sin oráculo"
            print(f"[{run_id}] zonas={len(res['zones'])} eventos={len(res['events'])} "
                  f"P1A={p1a['status']} paridad={gate}")

            if args.zone_store:
                bkey = viewer_export.bar_key_of(bars)
                m = zone_store.write_partition(
                    args.zone_store, indicator=n, param_set_id=psid, bar_key=bkey,
                    contract=tk.contract, instrument=tk.instrument,
                    tick_size=tk.tick_size, zones=res["zones"], params=res["params"],
                    chart_tz=args.chart_tz, range_start_utc=args.start_utc,
                    range_end_utc=args.end_utc, source=tk.source,
                    source_sha256=src_sha, code_rev=code_rev,
                    parity=(rep["summary"] if rep else None), generated_utc=gen_utc)
                print(f"    zone-store: {m['n_zones']} zonas -> "
                      f"{n}/{psid}/{bkey}/... (trusted={m['trusted']})")

    # ---- artefactos ----
    n_store = viewer_export.write_zone_store(runs, tk, os.path.join(args.out, "zones.parquet"))
    with open(os.path.join(args.out, "p1a_report.json"), "w", encoding="utf-8") as fh:
        json.dump({k: v for k, v in p1a_cache.items()}, fh, indent=2, ensure_ascii=False)
    par = {r["run_id"]: dict(summary=r["parity"], diagnostics=r["parity_diagnostics"])
           for r in runs if r["parity"]}
    if par:
        with open(os.path.join(args.out, "parity_report.json"), "w", encoding="utf-8") as fh:
            json.dump(par, fh, indent=2, ensure_ascii=False)
    manifest = dict(
        tool="run_nt8_bridge", generated_utc=gen_utc,
        code_rev=code_rev, source=tk.source,
        source_sha256=src_sha,
        instrument=tk.instrument, contract=tk.contract, tick_size=tk.tick_size,
        chart_tz=args.chart_tz,
        filters=dict(contract=args.contract, start_utc=args.start_utc, end_utc=args.end_utc),
        n_ticks=len(tk), zone_store_rows=n_store, runs=manifest_runs)
    with open(os.path.join(args.out, "run_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    # ---- visor ----
    for r in runs:                      # los diagnósticos completos van al JSON, no al bundle
        r.pop("parity_diagnostics", None)
    bundle = viewer_export.build_bundle(
        tk, {viewer_export.bar_key_of(b): b for b in bars_cache.values()},
        runs, chart_tz=args.chart_tz,
        extra_meta=dict(generated_utc=manifest["generated_utc"], code_rev=manifest["code_rev"]))
    vdir = os.path.join(args.out, "viewer")
    viewer_export.write_data_js(bundle, vdir)
    shutil.copy(os.path.join(VIEWER_SRC, "index.html"), os.path.join(vdir, "index.html"))
    os.makedirs(os.path.join(vdir, "vendor"), exist_ok=True)
    shutil.copy(os.path.join(VIEWER_SRC, "vendor", "lightweight-charts.standalone.production.js"),
                os.path.join(vdir, "vendor", "lightweight-charts.standalone.production.js"))
    print(f"zone store: {n_store} filas -> zones.parquet")
    print(f"visor: {os.path.join(vdir, 'index.html')} (offline, vendor local)")
    return 1 if any_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
