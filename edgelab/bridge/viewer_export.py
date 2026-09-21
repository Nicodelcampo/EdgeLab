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

def _bar_duration_s(bar_key: str) -> int | None:
    """Duración en segundos de una barra temporal, None para bars tick.

    Solo se usa como fallback explícito cuando el kernel no emitió available_at_ns.
    Nunca debe aplicarse fuera de barras temporales (time_*).
    """
    kind, _, val = bar_key.partition("_")
    if kind != "time":
        return None
    unit_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    # val puede ser '5m', '1h', '15m', etc.
    for unit, secs in unit_map.items():
        if val.endswith(unit):
            try:
                return int(val[: -len(unit)]) * secs
            except ValueError:
                return None
    try:
        return int(val)  # si val ya es solo segundos
    except ValueError:
        return None


def _zone_json(z, source, last_ms, match_id, bar_key=""):
    """Serializa una zona para el bundle del viewer.

    Campos canónicos de causalidad:
    - ``available_ts``: segundos desde epoch en que la señal es ejecutable.
      Proviene de ``available_at_ns`` del kernel (prioridad 1); si falta y la
      barra es temporal (time_*), se calcula t0 + duración de barra (fallback
      explícito y restringido). Para barras tick sin available_at_ns: None.
    - ``source_barspec``: tipo de barra generadora ("time_5m", "tick_25", ...).
      El renderer usa este campo para validar si puede aplicar fallback temporal.
    """
    # Prioridad 1: available_at_ns emitido directamente por el kernel
    avail_ns = z.get("available_at_ns")
    if avail_ns is not None:
        available_ts = int(avail_ns) // 1_000_000_000
    else:
        # Fallback EXPLÍCITO y RESTRINGIDO: sólo para barras temporales (time_*)
        dur = _bar_duration_s(bar_key) if bar_key else None
        if dur is not None:
            # t0 = apertura de barra (created_ms // 1000); t0 + dur = cierre
            available_ts = int(z["created_ms"] // 1000) + dur
        else:
            # Barras tick sin available_at_ns: no inferir, dejar None
            available_ts = None

    return dict(
        id=str(z["id"]), source=source,
        top=z["top"], bottom=z["bottom"],
        t0=int(z["created_ms"] // 1000),
        t1=int((z.get("ended_ms") or last_ms) // 1000),
        available_ts=available_ts,
        source_barspec=bar_key or None,
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
    bkey = bar_key_of(bars)
    zones = [_zone_json(z, "python", last_ms, by_py.get(str(z["id"])), bkey)
             for z in result["zones"] if z.get("created_ms") is not None]
    if oracle:
        zones += [_zone_json(z, "nt8", last_ms, by_nt8.get(str(z["id"])), bkey)
                  for z in oracle["zones"]
                  if z.get("created_ms") is not None and z.get("top") is not None]
    return dict(
        run_id=run_id, indicator=indicator, bar_key=bkey,
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
