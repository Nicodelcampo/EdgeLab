#!/usr/bin/env python3
"""build_viewer.py — exporta un STORE a un bundle para el visor v2 (F6.5).

El visor es estrictamente PASIVO: renderiza lo que este exportador vuelca desde
el store publicado (catálogo + zonas + manifests), nunca recalcula ni selecciona.
Cambiar parámetros = correr otra campaña; el visor recarga su bundle.

Salida: <out>/store_data.js (window.STORE_DATA) + index.html + vendor local.

STORE_DATA = {
  meta, catalog[<fila por partición con estados>],
  bar_series{ "<contract>|<bar_key>": {candles} },   # para el chart
  configs[ {identidad, params, estados, parity, zones[], candles_key} ],
}

Con --oracle Indicador=ruta.csv se agregan zonas NT8 + diagnósticos de paridad
al/los config de ese indicador (modo PARITY REVIEW con overlay real).
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from edgelab.bridge import bars as bars_mod, oracle, parity, store  # noqa: E402
from edgelab.bridge import ticks as ticks_mod  # noqa: E402

VIEWER_SRC = os.path.join(REPO, "viewer", "nt8_bridge")


def _iso_ns(s):
    if not s:
        return None
    return int(datetime.fromisoformat(s.replace("Z", "")).replace(
        tzinfo=timezone.utc).timestamp() * 1e9)


def _candles(bars, tick_size):
    out = []
    for b in range(len(bars)):
        out.append(dict(time=int(bars.end_ns[b] // 1_000_000_000),
                        open=float(bars.open_t[b]) * tick_size,
                        high=float(bars.high_t[b]) * tick_size,
                        low=float(bars.low_t[b]) * tick_size,
                        close=float(bars.close_t[b]) * tick_size))
    return out


def _zone_view(z, tick_size, last_ms, match=None):
    return dict(zone_key=z.get("zone_key"), zone_id=z.get("zone_id") or z.get("id"),
                source="python", top=z["top"], bottom=z["bottom"],
                t0=int(z["created_ms"] // 1000),
                t1=int((z.get("ended_ms") or last_ms) // 1000),
                side=z.get("side"), state=z.get("final_state") or z.get("state"),
                kind=z.get("kind"), touches=z.get("touches"),
                features=z.get("features"), match=match)


def _nt8_zone_view(z, tick_size, last_ms, match=None):
    if z.get("created_ms") is None or z.get("top") is None:
        return None
    return dict(zone_id=z["id"], source="nt8", top=z["top"], bottom=z["bottom"],
                t0=int(z["created_ms"] // 1000),
                t1=int((z.get("ended_ms") or last_ms) // 1000),
                state=z.get("state"), kind=z.get("kind"),
                touches=z.get("touches"), match=match)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exporta un store al visor v2")
    ap.add_argument("--store", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--oracle", action="append", default=[],
                    help="Indicador=ruta.csv (repetible) para overlay NT8/paridad")
    ap.add_argument("--chart-tz", default="UTC")
    args = ap.parse_args(argv)

    oracle_paths = {}
    for spec in args.oracle:
        k, _, v = spec.partition("=")
        oracle_paths[k] = v

    cat = store.catalog_df(args.store)
    if not cat:
        print("store vacío:", args.store)
        return 2

    # candles por (contract, bar_key): cargar ticks del rango de cada partición
    bar_series = {}
    tick_cache = {}
    configs = []
    for row in cat:
        man = json.loads(row["manifest_json"])
        src = man.get("source") or {}
        path = src.get("path")
        ckey = row["contract"] + "|" + row["bar_key"]
        tick_size = ticks_mod.instrument_spec(row["instrument"]).tick_size
        if ckey not in bar_series and path and os.path.exists(path):
            tkey = (path, row["contract"], src.get("range_start_utc"), src.get("range_end_utc"))
            if tkey not in tick_cache:
                tick_cache[tkey] = ticks_mod.load_canonical_parquet(
                    path, contract=row["contract"],
                    start_utc_ns=_iso_ns(src.get("range_start_utc")),
                    end_utc_ns=_iso_ns(src.get("range_end_utc")))
            tk = tick_cache[tkey]
            kind, _, val = row["bar_key"].partition("_")
            bars = (bars_mod.build_time_bars(tk, int(val)) if kind == "time"
                    else bars_mod.build_tick_bars(tk, int(val)))
            bar_series[ckey] = dict(candles=_candles(bars, tick_size))

        zrows = store.read_zone_rows(row["dir"])
        last_ms = max([int(z.get("ended_ms") or z["created_ms"]) for z in zrows], default=0)
        pyz = [_zone_view(z, tick_size, last_ms) for z in zrows]

        # overlay NT8 + paridad si hay oráculo para este indicador
        nt8z, par = [], None
        if row["indicator"] in oracle_paths:
            orc = oracle.parse_nt8_log(oracle_paths[row["indicator"]],
                                       chart_tz=args.chart_tz, tick_size=tick_size)
            kernel_zones = [dict(id=z["zone_id"], top=z["top"], bottom=z["bottom"],
                                 created_ms=z["created_ms"], ended_ms=z["ended_ms"],
                                 state=z["final_state"], touches=z["touches"])
                            for z in zrows]
            rep = parity.match_zones(kernel_zones, orc["zones"], tick_size)
            par = dict(summary=rep["summary"], diagnostics=rep["diagnostics"])
            by_py = {str(a): str(b) for a, b in rep["pairs"]}
            by_nt8 = {str(b): str(a) for a, b in rep["pairs"]}
            for z in pyz:
                z["match"] = by_py.get(str(z["zone_id"]))
            nt8z = [v for v in (_nt8_zone_view(z, tick_size, last_ms,
                                               by_nt8.get(str(z["id"]))) for z in orc["zones"]) if v]

        configs.append(dict(
            run_id=row["run_id"], indicator=row["indicator"], config_id=row["config_id"],
            bar_key=row["bar_key"], contract=row["contract"], instrument=row["instrument"],
            kernel_id=row["kernel_id"], dataset_id=row["dataset_id"], params=man["params"],
            integrity_state=row["integrity_state"], parity_state=row["parity_state"],
            digests=man["digests"], candles_key=ckey, parity=par,
            zones=pyz + nt8z, n_zones=row["n_zones"], n_events=row["n_events"]))

    catalog = [dict(run_id=r["run_id"], indicator=r["indicator"], config_id=r["config_id"],
                    bar_key=r["bar_key"], contract=r["contract"], instrument=r["instrument"],
                    n_zones=r["n_zones"], n_events=r["n_events"], n_observations=r["n_observations"],
                    integrity_state=r["integrity_state"], parity_state=r["parity_state"])
               for r in cat]

    bundle = dict(
        meta=dict(store=os.path.abspath(args.store),
                  generated_utc=datetime.now(timezone.utc).isoformat(),
                  n_partitions=len(cat), chart_tz=args.chart_tz),
        catalog=catalog, bar_series=bar_series, configs=configs)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "store_data.js"), "w", encoding="utf-8") as fh:
        fh.write("window.STORE_DATA = ")
        json.dump(bundle, fh, ensure_ascii=False, allow_nan=False, default=str)
        fh.write(";\n")
    shutil.copy(os.path.join(VIEWER_SRC, "store_viewer.html"),
                os.path.join(args.out, "index.html"))
    os.makedirs(os.path.join(args.out, "vendor"), exist_ok=True)
    shutil.copy(os.path.join(VIEWER_SRC, "vendor", "lightweight-charts.standalone.production.js"),
                os.path.join(args.out, "vendor", "lightweight-charts.standalone.production.js"))
    print("visor v2: %s (%d particiones, %d configs)" %
          (os.path.join(args.out, "index.html"), len(cat), len(configs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
