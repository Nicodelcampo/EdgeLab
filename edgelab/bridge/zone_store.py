"""Zone store formal (F6) — producto de primer nivel del bridge.

Almacena las coordenadas de zonas producidas por los kernels Python como
features reutilizables, particionadas por identidad estable, para que la fuerza
bruta / vectorbt consuma zonas SIN re-correr indicadores.

Layout en disco (una carpeta por configuración):

    <root>/<indicator>/<param_set_id>/<bar_key>/<contract>/
        zones.parquet   — una fila por zona (esquema fijo + features JSON)
        manifest.json    — identidad completa de la partición

Identidad de partición: (indicator, param_set_id, bar_key, contract). El
`param_set_id` ya es hash de (params + bar_key); `bar_key` y `contract` se
incluyen explícitos para poder consultar/particionar por ellos.

Esquema fijo de zona (columnas promovidas, comunes a todos los kernels):
    zone_id, indicator, param_set_id, bar_key, contract, instrument,
    kind, state, top, bottom, top_ticks, bottom_ticks,
    created_ms, ended_ms, touches, end_reason, features
`features` es un JSON con los campos propios del kernel (size_ticks, display,
dir, bucket, calib_id, max_pen_pct, …) — suficiente para re-filtrar offline los
umbrales legítimamente re-filtrables sin recomputar el indicador.

`trusted`: flag a nivel de partición (en el manifest). SOLO True cuando esa
configuración pasó paridad real P2 contra NT8 (parity_gate == "PASS"). La fuerza
bruta consume únicamente particiones trusted. Sin oráculo NT8 -> trusted=False.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

SCHEMA_VERSION = 1

# Campos que se promueven a columnas fijas (el resto va a `features` JSON).
_PROMOTED = {"id", "indicator", "top", "bottom", "created_ms", "ended_ms",
             "state", "kind", "touches", "end_reason", "timeline"}


def _sanitize(s: str) -> str:
    """Componente de path seguro (contract='6E 09-25' -> '6E_09-25')."""
    return re.sub(r"[^A-Za-z0-9._=-]+", "_", str(s)).strip("_") or "_"


def partition_dir(root, indicator, param_set_id, bar_key, contract) -> str:
    return os.path.join(str(root), _sanitize(indicator), _sanitize(param_set_id),
                        _sanitize(bar_key), _sanitize(contract))


def _zone_rows(zones, indicator, param_set_id, bar_key, contract, instrument,
               tick_size):
    rows = dict(zone_id=[], indicator=[], param_set_id=[], bar_key=[], contract=[],
                instrument=[], kind=[], state=[], top=[], bottom=[], top_ticks=[],
                bottom_ticks=[], created_ms=[], ended_ms=[], touches=[],
                end_reason=[], features=[])
    for z in zones:
        if z.get("created_ms") is None or z.get("top") is None:
            continue
        rows["zone_id"].append(str(z["id"]))
        rows["indicator"].append(indicator)
        rows["param_set_id"].append(param_set_id)
        rows["bar_key"].append(bar_key)
        rows["contract"].append(contract)
        rows["instrument"].append(instrument)
        rows["kind"].append(z.get("kind"))
        rows["state"].append(z.get("state"))
        rows["top"].append(float(z["top"]))
        rows["bottom"].append(float(z["bottom"]))
        rows["top_ticks"].append(int(round(z["top"] / tick_size)))
        rows["bottom_ticks"].append(int(round(z["bottom"] / tick_size)))
        rows["created_ms"].append(int(z["created_ms"]))
        rows["ended_ms"].append(None if z.get("ended_ms") is None else int(z["ended_ms"]))
        rows["touches"].append(int(z.get("touches") or 0))
        rows["end_reason"].append(z.get("end_reason"))
        feats = {k: v for k, v in z.items() if k not in _PROMOTED}
        rows["features"].append(json.dumps(feats, ensure_ascii=False, sort_keys=True,
                                           default=str))
    return rows


def write_partition(root, *, indicator, param_set_id, bar_key, contract,
                    instrument, tick_size, zones, params, chart_tz="UTC",
                    range_start_utc=None, range_end_utc=None, source=None,
                    source_sha256=None, code_rev=None, parity=None,
                    generated_utc=None) -> dict:
    """Escribe (o reescribe) una partición: zones.parquet + manifest.json.

    `parity` es el dict summary del matcher (o None sin oráculo). `trusted` se
    deriva: True solo si parity["gate"] == "PASS". Devuelve el manifest."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    pdir = partition_dir(root, indicator, param_set_id, bar_key, contract)
    os.makedirs(pdir, exist_ok=True)

    rows = _zone_rows(zones, indicator, param_set_id, bar_key, contract,
                      instrument, tick_size)
    tbl = pa.table(rows)
    tmp = os.path.join(pdir, "zones.parquet.tmp")
    pq.write_table(tbl, tmp, compression="zstd")
    os.replace(tmp, os.path.join(pdir, "zones.parquet"))

    gate = (parity or {}).get("gate") if isinstance(parity, dict) else None
    manifest = dict(
        schema_version=SCHEMA_VERSION, indicator=indicator,
        param_set_id=param_set_id, bar_key=bar_key, contract=contract,
        instrument=instrument, tick_size=tick_size, params=params,
        chart_tz=chart_tz, range_start_utc=range_start_utc,
        range_end_utc=range_end_utc, source=source, source_sha256=source_sha256,
        code_rev=code_rev, n_zones=tbl.num_rows, parity_gate=gate,
        parity_summary=(parity if isinstance(parity, dict) else None),
        trusted=bool(gate == "PASS"), generated_utc=generated_utc)
    tmpm = os.path.join(pdir, "manifest.json.tmp")
    with open(tmpm, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, default=str)
    os.replace(tmpm, os.path.join(pdir, "manifest.json"))
    return manifest


def list_partitions(root) -> list[dict]:
    """Lee todos los manifest.json bajo root."""
    out = []
    for dirpath, _dirs, files in os.walk(str(root)):
        if "manifest.json" in files:
            with open(os.path.join(dirpath, "manifest.json"), encoding="utf-8") as fh:
                m = json.load(fh)
            m["_dir"] = dirpath
            out.append(m)
    return out


def query_zones(root, *, indicator=None, param_set_id=None, bar_key=None,
                contract=None, state=None, created_after_ms=None,
                created_before_ms=None, trusted_only=False):
    """Consulta el store y devuelve un pyarrow.Table filtrado.

    Filtros por partición (indicator/param_set_id/bar_key/contract/trusted) y por
    fila (state, rango created_ms). `trusted_only=True` -> solo particiones que
    pasaron paridad real P2 (la fuerza bruta usa esto)."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    tables = []
    for m in list_partitions(root):
        if indicator is not None and m["indicator"] != indicator:
            continue
        if param_set_id is not None and m["param_set_id"] != param_set_id:
            continue
        if bar_key is not None and m["bar_key"] != bar_key:
            continue
        if contract is not None and m["contract"] != contract:
            continue
        if trusted_only and not m.get("trusted"):
            continue
        zpath = os.path.join(m["_dir"], "zones.parquet")
        if not os.path.exists(zpath):
            continue
        t = pq.read_table(zpath)
        if t.num_rows:
            tables.append(t)
    if not tables:
        return _empty_table()
    tbl = pa.concat_tables(tables)

    import pyarrow.compute as pc
    mask = None

    def _and(m1, m2):
        return m2 if m1 is None else pc.and_(m1, m2)

    if state is not None:
        mask = _and(mask, pc.equal(tbl["state"], state))
    if created_after_ms is not None:
        mask = _and(mask, pc.greater_equal(tbl["created_ms"], int(created_after_ms)))
    if created_before_ms is not None:
        mask = _and(mask, pc.less(tbl["created_ms"], int(created_before_ms)))
    if mask is not None:
        tbl = tbl.filter(mask)
    return tbl


def _empty_table():
    import pyarrow as pa
    fields = dict(zone_id=pa.string(), indicator=pa.string(),
                  param_set_id=pa.string(), bar_key=pa.string(),
                  contract=pa.string(), instrument=pa.string(), kind=pa.string(),
                  state=pa.string(), top=pa.float64(), bottom=pa.float64(),
                  top_ticks=pa.int64(), bottom_ticks=pa.int64(),
                  created_ms=pa.int64(), ended_ms=pa.int64(), touches=pa.int64(),
                  end_reason=pa.string(), features=pa.string())
    return pa.table({k: pa.array([], type=v) for k, v in fields.items()})
