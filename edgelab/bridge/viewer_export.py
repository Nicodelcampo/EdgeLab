"""Export del bundle del visor (multi-run) + zone store parquet.

data.js contiene MÚLTIPLES corridas (indicador × parameter_set × config de
barras): el visor tiene un selector para cambiar de configuración y ver el
cambio en las zonas — sin recalcular en el browser (el renderer jamás computa
señales; solo dibuja lo que el kernel produjo).

`param_set_id` = hash corto sha256 del JSON canónico de (params completos +
bar spec): identidad estable para el zone store / fuerza bruta.
"""
from __future__ import annotations

import hashlib
import json
import math
import os


def param_set_id(params: dict, bar_key: str) -> str:
    canon = json.dumps({"params": params, "bars": bar_key}, sort_keys=True,
                       separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:10]


def bar_key_of(bars) -> str:
    return f"{bars.kind}_{bars.param}"


def _candles(bars, tick_size):
    out = []
    for b in range(len(bars)):
        out.append(dict(
            time=int(bars.end_ns[b] // 1_000_000_000),
            open=float(bars.open_t[b]) * tick_size, high=float(bars.high_t[b]) * tick_size,
            low=float(bars.low_t[b]) * tick_size, close=float(bars.close_t[b]) * tick_size,
            volume=float(bars.volume[b])))
    return out


def _zone_json(z, source, last_ms, match_id):
    return dict(
        id=str(z["id"]), source=source,
        top=z["top"], bottom=z["bottom"],
        t0=int(z["created_ms"] // 1000),
        t1=int((z.get("ended_ms") or last_ms) // 1000),
        state=z.get("state"), kind=z.get("kind"), touches=z.get("touches"),
        end_reason=z.get("end_reason"), match=match_id)


def build_run(run_id, indicator, bars, result, psid, oracle=None, parity=None,
              p1a=None):
    """Un run = indicador + parameter_set + barras. Zonas python+nt8 juntas."""
    last_ms = int(bars.end_ns[-1] // 1_000_000) if len(bars) else 0
    by_py, by_nt8 = {}, {}
    if parity:
        for py_id, nt8_id in parity["pairs"]:
            by_py[str(py_id)] = str(nt8_id)
            by_nt8[str(nt8_id)] = str(py_id)
    zones = [_zone_json(z, "python", last_ms, by_py.get(str(z["id"])))
             for z in result["zones"] if z.get("created_ms") is not None]
    if oracle:
        zones += [_zone_json(z, "nt8", last_ms, by_nt8.get(str(z["id"])))
                  for z in oracle["zones"]
                  if z.get("created_ms") is not None and z.get("top") is not None]
    return dict(
        run_id=run_id, indicator=indicator, bar_key=bar_key_of(bars),
        param_set_id=psid, params=result["params"],
        has_oracle=bool(oracle), zones=zones,
        parity=(parity["summary"] if parity else None),
        parity_diagnostics=(parity["diagnostics"] if parity else None),
        p1a=p1a, n_events=len(result["events"]))


def build_bundle(ticks, bar_series_by_key, runs, chart_tz="UTC", extra_meta=None):
    meta = dict(instrument=ticks.instrument, contract=ticks.contract,
                tick_size=ticks.tick_size, chart_tz=chart_tz,
                n_ticks=len(ticks.ts_ns), source=ticks.source)
    meta.update(extra_meta or {})
    return dict(
        meta=meta,
        bar_series={k: dict(kind=b.kind, param=b.param,
                            candles=_candles(b, ticks.tick_size))
                    for k, b in bar_series_by_key.items()},
        runs=runs)


def write_data_js(bundle, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "data.js")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("window.BRIDGE_DATA = ")
        json.dump(bundle, fh, ensure_ascii=False, allow_nan=False, default=_safe)
        fh.write(";\n")
    return path


def write_zone_store(runs, ticks, out_path):
    """Zone store (semilla F5): coordenadas de TODAS las zonas de todas las
    configuraciones, con identidad (indicator, param_set_id, bar_key) para
    reutilizarlas como features sin recorrer indicadores de nuevo."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    tick = ticks.tick_size
    rows = dict(run_id=[], indicator=[], param_set_id=[], bar_key=[],
                instrument=[], contract=[], source=[], zone_id=[], zone_source=[],
                kind=[], state=[], top=[], bottom=[], top_ticks=[], bottom_ticks=[],
                created_ms=[], ended_ms=[], touches=[], end_reason=[])
    for r in runs:
        for z in r["zones"]:
            rows["run_id"].append(r["run_id"])
            rows["indicator"].append(r["indicator"])
            rows["param_set_id"].append(r["param_set_id"])
            rows["bar_key"].append(r["bar_key"])
            rows["instrument"].append(ticks.instrument)
            rows["contract"].append(ticks.contract)
            rows["source"].append(ticks.source)
            rows["zone_id"].append(z["id"])
            rows["zone_source"].append(z["source"])
            rows["kind"].append(z.get("kind"))
            rows["state"].append(z.get("state"))
            rows["top"].append(float(z["top"]))
            rows["bottom"].append(float(z["bottom"]))
            rows["top_ticks"].append(int(round(z["top"] / tick)))
            rows["bottom_ticks"].append(int(round(z["bottom"] / tick)))
            rows["created_ms"].append(int(z["t0"]) * 1000)
            rows["ended_ms"].append(int(z["t1"]) * 1000)
            rows["touches"].append(int(z.get("touches") or 0))
            rows["end_reason"].append(z.get("end_reason"))
    tbl = pa.table(rows)
    tmp = str(out_path) + ".tmp"
    pq.write_table(tbl, tmp, compression="zstd")
    os.replace(tmp, str(out_path))
    return tbl.num_rows


def _safe(o):
    if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
        return None
    return str(o)
