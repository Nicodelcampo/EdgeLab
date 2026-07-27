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
from edgelab.bridge import identity, oracle, parity, store, viewer_export  # noqa: E402
from edgelab.bridge import session_preflight  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import BAR_DRIVEN, REGISTRY  # noqa: E402

# Kernels cuya salida depende del calendario de sesiones: les corre el preflight
# antes de comparar zonas. `aVolCellPOI2` calcula umbrales por sesión y
# `HFTZones2` congela su calibración al abrir cada sesión, así que en los dos una
# frontera corrida cambia QUÉ se detecta, no sólo cuándo.
SESSION_DRIVEN = {"aVolCellPOI2", "HFTZones2"}

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
    ap.add_argument("--start-utc", default=None,
                    help="inicio de la VENTANA DE COMPARACION")
    ap.add_argument("--end-utc", default=None,
                    help="fin de la VENTANA DE COMPARACION")
    # La ventana de DATOS es otra cosa que la de comparacion. Un kernel con
    # lookback largo (aVolCellPOI2 pide 10-20 sesiones; VolTicksPOC2, 2000 barras;
    # HFTZones2 calibra contra la sesion anterior) necesita historia ANTES del
    # primer instante que se compara. Cargar solo la ventana de comparacion lo
    # deja sin warmup y produce cero detecciones -- que se leen como FAIL de
    # kernel cuando en realidad es el arnes el que no le dio datos.
    ap.add_argument("--data-start-utc", default=None,
                    help="inicio de la ventana de DATOS (default: la de comparacion)")
    ap.add_argument("--data-end-utc", default=None,
                    help="fin de la ventana de DATOS (default: la de comparacion)")
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

    # Validación contra PARAM_SPEC (F6.1): rechaza parámetros inexistentes, tipos
    # incorrectos, fuera de rango/choice, visual/forbidden, y filtros offline con
    # piso de export no cubierto. La clave reservada "bars" se valida aparte.
    val_errors = []
    for n in names:
        for pset in grids[n]:
            checkable = {k: v for k, v in pset.items() if k != "bars"}
            for e in identity.validate_params(n, checkable):
                val_errors.append(f"{n}: {e}")
    if val_errors:
        ap.error("parámetros inválidos:\n  " + "\n  ".join(val_errors))

    oracle_by = {}
    for spec in args.oracle:
        k, _, v = spec.partition("=")
        oracle_by[k] = v

    if args.synthetic:
        tk = ticks_mod.make_synthetic()
    elif args.data:
        tk = ticks_mod.load_canonical_parquet(
            args.data, contract=args.contract, instrument=args.instrument,
            start_utc_ns=iso_to_ns(args.data_start_utc or args.start_utc),
            end_utc_ns=iso_to_ns(args.data_end_utc or args.end_utc))
    else:
        ap.error("falta --data o --synthetic")
    print(f"ticks: {len(tk):,} · {tk.instrument} {tk.contract} · tick_size {tk.tick_size}")
    if args.data_start_utc or args.data_end_utc:
        print(f"  datos [{args.data_start_utc or args.start_utc}, "
              f"{args.data_end_utc or args.end_utc}) · "
              f"comparacion [{args.start_utc}, {args.end_utc})")

    os.makedirs(args.out, exist_ok=True)
    gen_utc = datetime.now(timezone.utc).isoformat()
    code_rev = git_rev()
    src_sha = sha256_file(args.data) if args.data else None
    # Identidades canónicas (F6.1): dataset_id una vez; kernel_id cacheado.
    tz_interp = "synthetic" if args.synthetic else "canonical_utc_verified"
    ds_id = identity.dataset_id(tk, tz_interpretation=tz_interp, source_sha256=src_sha)
    kid_cache = {}
    print(f"dataset_id: {ds_id}")
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

    # ventana de comparación en unix_ms: NT8 exporta más rango del que se compara
    # (warmup a ambos lados). Las zonas NT8 creadas fuera de [start, end) se
    # excluyen del diff (no son huérfanas: son fuera-de-ventana).
    win_start_ms = iso_to_ns(args.start_utc) // 1_000_000 if args.start_utc else None
    win_end_ms = iso_to_ns(args.end_utc) // 1_000_000 if args.end_utc else None

    def in_window(z):
        cm = z.get("created_ms")
        if cm is None:
            return True
        if win_start_ms is not None and cm < win_start_ms:
            return False
        if win_end_ms is not None and cm >= win_end_ms:
            return False
        return True

    runs, manifest_runs, any_fail = [], [], False
    oracle_sha = {}
    for n in names:
        orc = None
        if n in oracle_by:
            orc = oracle.parse_nt8_log(oracle_by[n], chart_tz=args.chart_tz,
                                       tick_size=tk.tick_size)
            oracle_sha[n] = sha256_file(oracle_by[n])
            n_all = len(orc["zones"])
            orc["zones"] = [z for z in orc["zones"] if in_window(z)]
            if n_all != len(orc["zones"]):
                print(f"[oráculo {n}] {len(orc['zones'])}/{n_all} zonas NT8 en ventana "
                      f"[{args.start_utc}, {args.end_utc}) (resto = warmup/fuera de rango)")

            # PREFLIGHT DE CALENDARIO (decision de Nico 2026-07-26). Va ANTES de
            # comparar zonas: un calendario desalineado produce diffs de zona que
            # parecen diffs de geometria, y se gasta el oraculo persiguiendo la
            # zona equivocada. Solo corre si el oraculo trae evidencia de sesion;
            # si no la trae, se dice — no se asume que esta bien.
            if n in SESSION_DRIVEN:
                ev = orc.get("session_starts_ns") or []
                if not ev:
                    print(f"[preflight {n}] el oráculo NO exporta eventos de inicio "
                          f"de sesión: la alineación de calendario queda SIN VERIFICAR. "
                          f"Un FAIL de este kernel podría ser calendario y no geometría.")
                else:
                    b_nt8 = session_preflight.nt8_boundaries(ev)
                    b_py = session_preflight.python_boundaries(ev)
                    rep = session_preflight.preflight(b_nt8, b_py, strict=False)
                    print("[preflight %s] %s" % (n, session_preflight.formatear(rep)))
                    if not rep["ok"]:
                        any_fail = True
                        print(f"[preflight {n}] ABORTA la comparación de este kernel.")
                        continue
        for pset in grids[n]:
            pset = dict(pset)
            bar_spec = pset.pop("bars", args.bars)
            bars, fps, p1a = bars_for(bar_spec)
            mod = REGISTRY[n]
            res = (mod.run(tk, bars, fps, params=pset, chart_tz=args.chart_tz)
                   if n in BAR_DRIVEN else
                   mod.run(tk, bars, params=pset, chart_tz=args.chart_tz))
            # REGLA DE VENTANA SIMETRICA (contrato de paridad §4, decision de
            # Nico 2026-07-26). El filtro [W0, W1) se aplica IDENTICAMENTE a los
            # dos lados. Antes solo se filtraba el oraculo, asi que una zona
            # creada exactamente en W1 quedaba dentro del lado Python y fuera del
            # de NT8, produciendo un MISSING_IN_NT8 que no era discrepancia de
            # kernel sino un artefacto de medicion. La exclusion se REPORTA
            # siempre, con cuantas filas y cuales.
            _n_all_py = len(res["zones"])
            _fuera = [z for z in res["zones"] if not in_window(z)]
            if _fuera:
                res["zones"] = [z for z in res["zones"] if in_window(z)]
                print(f"[kernel {n}] {len(res['zones'])}/{_n_all_py} zonas en ventana "
                      f"[{args.start_utc}, {args.end_utc}); excluidas por borde: "
                      + ", ".join(str(z.get("id")) for z in _fuera[:10])
                      + (" …" if len(_fuera) > 10 else ""))
            bkey_id = viewer_export.bar_key_of(bars)
            psid = viewer_export.param_set_id(res["params"], bkey_id)
            kid = kid_cache.setdefault(n, identity.kernel_id(n))
            cid = identity.config_id(n, res["params"], bkey_id, args.chart_tz, kid)
            rid = identity.run_id(ds_id, cid, args.start_utc, args.end_utc)
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
                # frontera de madurez: zonas creadas a < max_age_bars del final de
                # la ventana no pueden completar su ciclo -> lifecycle no comparable
                # (geometría sí). Frontier = cierre de la barra (n-1-max_age).
                frontier_ms = None
                max_age = int(res["params"].get("max_age_bars", 0) or 0)
                if max_age and len(bars) > max_age:
                    frontier_ms = int(bars.end_ns[len(bars) - 1 - max_age]) // 1_000_000
                rep = parity.match_zones(res["zones"], orc["zones"], tk.tick_size,
                                         tol_created_ms=args.tol_created_ms,
                                         tol_geom_ticks=args.tol_geom_ticks,
                                         extra_diags=extra,
                                         maturity_frontier_ms=frontier_ms)
                any_fail |= rep["gate"] == "FAIL"
                # evidencia completa en el summary (va a parity.json del store)
                rep["summary"].update(
                    oracle_path=os.path.abspath(oracle_by[n]),
                    oracle_sha256=oracle_sha.get(n), config_id=cid,
                    window_start_utc=args.start_utc, window_end_utc=args.end_utc,
                    rule=("maturity_frontier" if frontier_ms is not None else "full"),
                    n_nt8_in_window=len(orc["zones"]))
            run = viewer_export.build_run(run_id, n, bars, res, psid,
                                          oracle=orc, parity=rep, p1a=p1a)
            runs.append(run)
            manifest_runs.append(dict(
                run_id=run_id, indicator=n, param_set_id=psid,
                dataset_id=ds_id, kernel_id=kid, config_id=cid, canonical_run_id=rid,
                bar_key=bkey_id, params=res["params"],
                n_zones=len(res["zones"]), n_events=len(res["events"]),
                p1a=p1a["status"], parity_gate=(rep["gate"] if rep else None),
                events_csv=os.path.basename(csv_path)))
            gate = rep["gate"] if rep else "sin oráculo"
            print(f"[{run_id}] zonas={len(res['zones'])} eventos={len(res['events'])} "
                  f"P1A={p1a['status']} paridad={gate}")

            if args.zone_store:
                src = dict(path=args.data, sha256=src_sha, rows=len(tk),
                           range_start_utc=args.start_utc, range_end_utc=args.end_utc,
                           kind=("synthetic" if args.synthetic else "parquet_f2"))
                m = store.publish_run(
                    args.zone_store, kernel_result=res, indicator=n,
                    tick_size=tk.tick_size, instrument=tk.instrument,
                    contract=tk.contract, bar_key=bkey_id, dataset_id=ds_id,
                    kernel_id=kid, config_id=cid, run_id=rid, params=res["params"],
                    source=src, chart_tz=args.chart_tz,
                    parity=(rep["summary"] if rep else None),
                    generated_utc=gen_utc, param_set_id=psid)
                print(f"    store: {m['counts']['n_zones']} zonas -> "
                      f"{n}/{cid} (integridad={m['integrity_state']}, "
                      f"paridad={m['parity_state']})")

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
        filters=dict(contract=args.contract, start_utc=args.start_utc,
                     end_utc=args.end_utc,
                     data_start_utc=args.data_start_utc or args.start_utc,
                     data_end_utc=args.data_end_utc or args.end_utc),
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
