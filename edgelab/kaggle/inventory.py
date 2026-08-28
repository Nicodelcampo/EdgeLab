"""Censo del dataset de Kaggle leyendo SOLO metadata de Parquet.

El footer de un Parquet trae num_rows, num_row_groups, schema y estadisticas
min/max por row group. Con eso se obtiene el rango temporal y el conteo de
filas de 56 archivos y 16,74 GB en segundos, sin leer una sola pagina de datos.
Es el primer gate del notebook 00: si el censo no cierra contra el manifiesto
local, no se gasta una sesion de 12 h leyendo ticks.

pyarrow es obligatorio aca (existe en la imagen de Kaggle). El resto del
subpaquete no lo necesita.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

TS_COLUMN = "ts_utc_ns"
NS_PER_SEC = 1_000_000_000
FILENAME_RE = re.compile(r"^(?P<asset>[A-Z0-9]+)_(?P<contract>\d{2}-\d{2})_ticks\.parquet$")


def _pq():
    try:
        import pyarrow.parquet as pq  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "pyarrow no disponible: inventory requiere la imagen de Kaggle"
        ) from exc
    return pq


def parse_filename(name: str) -> dict:
    m = FILENAME_RE.match(os.path.basename(name))
    if not m:
        return {"asset": None, "contract": None, "filename_ok": False}
    return {
        "asset": m.group("asset"),
        "contract": m.group("contract"),
        "filename_ok": True,
    }


def ns_to_iso(ns: int | None) -> str | None:
    if ns is None:
        return None
    return datetime.fromtimestamp(int(ns) / NS_PER_SEC, tz=timezone.utc).isoformat()


def footer_census(path: str, *, ts_column: str = TS_COLUMN) -> dict:
    """Censo de un archivo leyendo solo el footer."""
    pq = _pq()
    rec: dict = {
        "path": path,
        "file": os.path.basename(path),
        "bytes": os.path.getsize(path),
    }
    rec.update(parse_filename(path))
    pf = pq.ParquetFile(path)
    md = pf.metadata
    rec["rows"] = int(md.num_rows)
    rec["row_groups"] = int(md.num_row_groups)
    rec["columns"] = int(md.num_columns)
    rec["created_by"] = md.created_by
    rec["format_version"] = md.format_version
    schema = pf.schema_arrow
    rec["column_names"] = list(schema.names)
    rec["column_types"] = [str(schema.field(n).type) for n in schema.names]

    ts_idx = schema.names.index(ts_column) if ts_column in schema.names else None
    rec["ts_column"] = ts_column if ts_idx is not None else None
    if ts_idx is None:
        rec["stats_available"] = False
        return rec

    mins, maxs, stats_ok, rg_rows = [], [], True, []
    for i in range(md.num_row_groups):
        col = md.row_group(i).column(ts_idx)
        rg_rows.append(int(md.row_group(i).num_rows))
        st = col.statistics
        if st is None or not st.has_min_max:
            stats_ok = False
            continue
        mins.append(int(st.min))
        maxs.append(int(st.max))
    rec["stats_available"] = stats_ok and bool(mins)
    if mins:
        rec["ts_min_ns"] = min(mins)
        rec["ts_max_ns"] = max(maxs)
        rec["ts_min_utc"] = ns_to_iso(rec["ts_min_ns"])
        rec["ts_max_utc"] = ns_to_iso(rec["ts_max_ns"])
        # row groups ordenados por tiempo: condicion para poder saltar bloques
        rec["row_groups_time_ordered"] = all(
            mins[i] <= mins[i + 1] for i in range(len(mins) - 1)
        )
        rec["row_group_rows_min"] = min(rg_rows)
        rec["row_group_rows_max"] = max(rg_rows)
    return rec


def census_dir(
    root: str,
    *,
    pattern: str = ".parquet",
    ts_column: str = TS_COLUMN,
) -> list[dict]:
    """Censo de todos los Parquet bajo `root` (recursivo, orden estable)."""
    paths = []
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith(pattern):
                paths.append(os.path.join(dirpath, f))
    out = []
    for p in sorted(paths):
        try:
            out.append(footer_census(p, ts_column=ts_column))
        except Exception as exc:
            out.append(
                {
                    "path": p,
                    "file": os.path.basename(p),
                    "bytes": os.path.getsize(p) if os.path.exists(p) else None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return out


def summarize_census(records: list[dict]) -> dict:
    """Totales y agregados por activo. Comparable contra el censo local."""
    ok = [r for r in records if "error" not in r]
    bad = [r for r in records if "error" in r]
    by_asset: dict = {}
    for r in ok:
        a = r.get("asset") or "UNKNOWN"
        acc = by_asset.setdefault(
            a, {"contracts": 0, "rows": 0, "bytes": 0, "files": []}
        )
        acc["contracts"] += 1
        acc["rows"] += int(r.get("rows", 0))
        acc["bytes"] += int(r.get("bytes", 0))
        acc["files"].append(r["file"])
    total_rows = sum(int(r.get("rows", 0)) for r in ok)
    total_bytes = sum(int(r.get("bytes", 0)) for r in ok)
    cols = {tuple(r.get("column_names", ())) for r in ok}
    return {
        "files_ok": len(ok),
        "files_error": len(bad),
        "errors": bad,
        "total_rows": total_rows,
        "total_bytes": total_bytes,
        "total_gib": round(total_bytes / (1 << 30), 3),
        "assets": len(by_asset),
        "by_asset": {
            k: {kk: vv for kk, vv in v.items() if kk != "files"}
            for k, v in sorted(by_asset.items())
        },
        "schema_variants": len(cols),
        "schema": sorted([list(c) for c in cols])[0] if cols else [],
        "columns_total": sum(int(r.get("columns", 0)) for r in ok),
        "stats_missing_files": [
            r["file"] for r in ok if not r.get("stats_available")
        ],
    }


def budget_gates(
    summary: dict,
    *,
    top_level_files: int,
    max_input_gib: float = 10.0,
    max_top_level_files: int = 20,
    kaggle_max_top_level_files: int = 50,
    kaggle_max_dataset_gib: float = 200.0,
) -> dict:
    """Gates del presupuesto tecnico contractual (Contrato Kaggle v2).

    Devuelve un dict con veredicto por gate. Superar un presupuesto produce
    ABSTAIN_CAPACITY: no se resuelve dividiendo la corrida hasta que entre.
    """
    gib = summary.get("total_gib", 0.0)
    gates = {
        "input_size_gib": {
            "value": gib,
            "limit": max_input_gib,
            "pass": gib <= max_input_gib,
            "rule": "input privado v1 <= 10 GB (contrato)",
        },
        "top_level_files_contract": {
            "value": top_level_files,
            "limit": max_top_level_files,
            "pass": top_level_files <= max_top_level_files,
            "rule": "archivos top-level <= 20 (contrato)",
        },
        "top_level_files_kaggle": {
            "value": top_level_files,
            "limit": kaggle_max_top_level_files,
            "pass": top_level_files <= kaggle_max_top_level_files,
            "rule": "maximo 50 archivos de nivel superior (limite documentado de Kaggle)",
        },
        "dataset_size_kaggle": {
            "value": gib,
            "limit": kaggle_max_dataset_gib,
            "pass": gib <= kaggle_max_dataset_gib,
            "rule": "200 GB por dataset (limite de plataforma)",
        },
    }
    failed = [k for k, v in gates.items() if not v["pass"]]
    return {
        "gates": gates,
        "failed": failed,
        "verdict": "PASS" if not failed else "ABSTAIN_CAPACITY",
    }
