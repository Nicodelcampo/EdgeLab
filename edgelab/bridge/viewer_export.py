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
import re


def param_set_id(params: dict, bar_key: str) -> str:
    canon = json.dumps({"params": params, "bars": bar_key}, sort_keys=True,
                       separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode()).hexdigest()[:10]


def bar_key_of(bars) -> str:
    if bars.kind == "time":
        # BarSeries.param is expressed in minutes for time bars.
        return f"time_{bars.param}m"
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


def _bar_duration_s(bar_key: str) -> int | None:
    """Strict temporal duration; ambiguous or non-time specs return None."""
    match = re.fullmatch(r"time_(\d+)([smhd])", str(bar_key or ""))
    if match is None:
        return None
    unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    value = int(match.group(1))
    return value * unit_map[match.group(2)] if value > 0 else None


def _zone_json(z, source, last_ms, match_id, display_bar_key="", formation_spec=None):
    """Serialize geometry and causal provenance without inferring from display."""
    top = z["top"] if ("top" in z and z["top"] is not None) else z.get("hi")
    bottom = z["bottom"] if ("bottom" in z and z["bottom"] is not None) else z.get("lo")
    kind = z["kind"] if ("kind" in z and z["kind"] is not None) else z.get("side")

    f_spec = z.get("formation_spec") or formation_spec
    if not f_spec and "TapeWindowTicks" in z:
        f_spec = f"tick_count:{z['TapeWindowTicks']}"

    f_start_ns = z.get("formation_start_ns")
    f_end_ns = z.get("formation_end_ns")
    formation_start_ts = int(f_start_ns // 1_000_000_000) if f_start_ns is not None else None
    formation_end_ts = int(f_end_ns // 1_000_000_000) if f_end_ns is not None else None

    if formation_start_ts is not None:
        t0 = formation_start_ts
    elif "created_ms" in z and z["created_ms"] is not None:
        t0 = int(z["created_ms"] // 1000)
    elif "t0" in z and z["t0"] is not None:
        t0 = int(z["t0"])
    else:
        t0 = 0

    avail_ns = z.get("available_at_ns")
    avail_ts = z.get("available_ts")
    if avail_ns is not None:
        available_ts = int(avail_ns // 1_000_000_000)
        available_origin = "KERNEL_AVAILABLE_AT_NS"
    elif avail_ts is not None:
        available_ts = int(avail_ts)
        available_origin = "EXPLICIT_AVAILABLE_TS"
    else:
        # Display bars are never causal evidence. Derive only from an explicit
        # temporal formation contract; otherwise abstain.
        duration = _bar_duration_s(f_spec) if f_spec else None
        if duration is not None:
            available_ts = t0 + duration
            available_origin = "DERIVED_COMPATIBILITY_FALLBACK"
        else:
            available_ts = None
            available_origin = "UNAVAILABLE"

    return dict(
        id=str(z.get("id", "")), source=source,
        top=top, bottom=bottom,
        t0=t0,
        t1=int((z.get("ended_ms") or last_ms) // 1000),
        formation_spec=f_spec,
        display_bar_key=display_bar_key or None,
        formation_start_ts=formation_start_ts,
        formation_end_ts=formation_end_ts,
        available_ts=available_ts,
        available_origin=available_origin,
        source_barspec=f_spec or None,
        state=z.get("state"), kind=kind, touches=z.get("touches"),
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
    display_bkey = bar_key_of(bars)

    default_f_spec = None
    params = result.get("params", {})
    if "TapeWindowTicks" in params:
        default_f_spec = f"tick_count:{params['TapeWindowTicks']}"

    zones = [_zone_json(z, "python", last_ms, by_py.get(str(z.get("id"))),
                        display_bar_key=display_bkey, formation_spec=default_f_spec)
             for z in result["zones"]
             if (z.get("created_ms") is not None or z.get("formation_start_ns") is not None or z.get("t0") is not None)]
    if oracle:
        zones += [_zone_json(z, "nt8", last_ms, by_nt8.get(str(z.get("id"))),
                             display_bar_key=display_bkey, formation_spec=default_f_spec)
                  for z in oracle["zones"]
                  if (z.get("created_ms") is not None or z.get("formation_start_ns") is not None or z.get("t0") is not None)
                  and (z.get("top") is not None or z.get("hi") is not None)]
    return dict(
        run_id=run_id, indicator=indicator,
        bar_key=display_bkey,
        display_bar_key=display_bkey,
        formation_spec=default_f_spec,
        param_set_id=psid, params=result.get("params"),
        has_oracle=bool(oracle), zones=zones,
        parity=(parity["summary"] if parity else None),
        parity_diagnostics=(parity["diagnostics"] if parity else None),
        p1a=p1a, n_events=len(result.get("events", [])))


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
    """Zone store reutilizable para todas las configuraciones."""
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
