"""Lector mínimo y seguro de la release `liquid_tick_v1` para scripts de research del repo de investigación.

Equivalente en comportamiento a `edgelab.data.liquid_release.release_reader` (rama data/liquid-release-20261014) y a la copia embebida en
`avzp2_racimo_replica_stage1.py`; los tests de `tests/bridge/test_release_io.py` fijan los mismos casos de custodia:
  - propósito obligatorio (`audit` o `provisional_research`; `research` exige una aprobación externa que acá no existe);
  - tamaño y SHA-256 del archivo contra el manifiesto; ruta relativa sin traversal;
  - preflight de AMBOS relojes (`trade_date` y `ts_utc_ns`) en TODOS los row groups antes de leer cualquier payload;
  - nunca se pide ni se lee el holdout (trade date >= 20261001; ts >= 1_790_805_600_000_000_000).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pyarrow.parquet as pq

HOLDOUT_FIRST_TRADE_DATE = 20261001
HOLDOUT_FIRST_TS_NS = 1_790_805_600_000_000_000        # 2026-09-30T22:00:00Z
SCHEMA = "edgelab_liquid_release_v1"


class ReleaseStop(RuntimeError):
    """STOP de custodia o integridad."""


def sha256_file(path: Path, chunk: int = 16 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def preflight_footer(pf: pq.ParquetFile) -> None:
    names = pf.schema_arrow.names
    cols = {}
    for col in ("trade_date", "ts_utc_ns"):
        if col not in names:
            raise ReleaseStop(f"el archivo no tiene columna {col}")
        cols[col] = names.index(col)
    for g in range(pf.metadata.num_row_groups):
        rg = pf.metadata.row_group(g)
        for col, ci in cols.items():
            st = rg.column(ci).statistics
            if st is None or not st.has_min_max:
                raise ReleaseStop(f"row group {g} sin estadísticas de {col}")
            if st.null_count:
                raise ReleaseStop(f"row group {g} con nulls en {col}")
            limit = HOLDOUT_FIRST_TRADE_DATE if col == "trade_date" else HOLDOUT_FIRST_TS_NS
            if int(st.max) >= limit:
                raise ReleaseStop(f"row group {g} contiene {col} reservado (max {int(st.max)} >= {limit})")


def _manifest(root: Path) -> dict:
    m = json.loads((root / "release_manifest.json").read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA:
        raise ReleaseStop("esquema de manifiesto desconocido")
    return m


def _asset_path(root: Path, m: dict, asset: str) -> tuple[Path, dict]:
    e = m["assets"][asset]
    rel = e["file"]
    if os.path.isabs(rel) or ".." in Path(rel).parts:
        raise ReleaseStop("ruta del manifiesto no relativa")
    p = root / rel
    if p.stat().st_size != int(e["bytes"]):
        raise ReleaseStop("tamaño distinto al del manifiesto")
    return p, e


def verify_asset_hash(release_dir, asset: str) -> str:
    """SHA-256 completo de un activo contra el manifiesto. Devuelve el SHA o lanza ReleaseStop."""
    root = Path(release_dir)
    p, e = _asset_path(root, _manifest(root), asset)
    got = sha256_file(p)
    if got != e["sha256"]:
        raise ReleaseStop("SHA-256 distinto al del manifiesto")
    return got


def manifest_sha256(release_dir) -> str:
    return sha256_file(Path(release_dir) / "release_manifest.json")


def selected_sessions(release_dir, asset: str) -> list[tuple[int, str]]:
    """[(trade_date, contract)] de las sesiones SELECTED del activo, ordenadas, sólo pre-holdout."""
    import pandas as pd
    si = pd.read_parquet(Path(release_dir) / "metadata" / "session_index.parquet")
    s = si[(si.instrument == asset) & (si.status == "SELECTED") & (si.trade_date < HOLDOUT_FIRST_TRADE_DATE)].sort_values("trade_date")
    return [(int(d), str(c)) for d, c in zip(s.trade_date, s.contract)]


def read_asset(release_dir, asset: str, start_trade_date: int, end_trade_date: int, *, columns=None, verify_hash: bool = True, purpose=None):
    if purpose not in ("audit", "provisional_research"):
        raise ReleaseStop("declarar purpose='audit' o 'provisional_research' (research exige aprobación externa de Nico)")
    if end_trade_date >= HOLDOUT_FIRST_TRADE_DATE:
        raise ReleaseStop("el rango pedido alcanza el holdout")
    root = Path(release_dir)
    p, e = _asset_path(root, _manifest(root), asset)
    if verify_hash and sha256_file(p) != e["sha256"]:
        raise ReleaseStop("SHA-256 distinto al del manifiesto")
    pf = pq.ParquetFile(p)
    preflight_footer(pf)
    ci = pf.schema_arrow.names.index("trade_date")
    keep = []
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(ci).statistics
        lo, hi = int(st.min), int(st.max)
        if hi < start_trade_date or lo > end_trade_date:
            continue
        if lo < start_trade_date or hi > end_trade_date:
            raise ReleaseStop("row group cruza el borde del rango pedido")
        keep.append(g)
    if not keep:
        t = pf.schema_arrow.empty_table()
        return t.select(columns) if columns else t
    return pf.read_row_groups(keep, columns=columns)
