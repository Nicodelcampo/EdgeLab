"""Lector seguro de la release líquida (un Parquet por activo). Responde a D14–D17 del handoff 2026-10-14.

Reglas (todas fallan ANTES de deserializar precios/volúmenes):
- Manifiesto obligatorio, no vacío, con esquema y versión conocidos. Sin manifiesto no se lee nada (D15).
- Rutas relativas exactas dentro de la raíz de la release. Sin traversal, sin symlinks fuera de la raíz, sin búsqueda por
  basename ni raíces alternativas (D16).
- Tamaño exacto siempre; SHA-256 exacto (`verify_hash=True`, por defecto) contra el manifiesto (D15).
- Guarda de holdout: la lectura se hace por row groups seleccionados con las estadísticas de `trade_date`. Un row group
  sin estadísticas, o que mezcle fechas permitidas y reservadas, detiene la lectura (STOP). Los row groups reservados
  jamás se leen, ni siquiera por columnas (D14).
- Caché ligada al contenido: la clave incluye el SHA del archivo, la versión del esquema y la transformación (D17).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

SCHEMA = "edgelab_liquid_release_v1"
HOLDOUT_FIRST_TRADE_DATE = 20261001
TRADE_DATE_COL = "trade_date"


class ReleaseStop(RuntimeError):
    """STOP: la lectura no puede continuar sin violar una regla de custodia o integridad."""


@dataclass(frozen=True)
class AssetFile:
    asset: str
    path: Path
    sha256: str
    bytes: int
    rows: int


def _inside(root: Path, p: Path) -> bool:
    try:
        p.resolve(strict=True).relative_to(root.resolve(strict=True))
        return True
    except (ValueError, FileNotFoundError):
        return False


def sha256_file(path: Path, chunk=16 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def load_manifest(release_dir, *, verify_hash=True) -> dict[str, AssetFile]:
    root = Path(release_dir)
    mpath = root / "release_manifest.json"
    if not mpath.is_file():
        raise ReleaseStop(f"falta release_manifest.json en {root}")
    m = json.loads(mpath.read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA:
        raise ReleaseStop(f"esquema de manifiesto desconocido: {m.get('schema')!r}")
    files = m.get("assets") or {}
    if not files:
        raise ReleaseStop("manifiesto sin activos: no se lee nada")
    out = {}
    for asset, e in files.items():
        rel = e["file"]
        if os.path.isabs(rel) or ".." in Path(rel).parts:
            raise ReleaseStop(f"ruta no relativa o con traversal: {rel}")
        p = root / rel
        if not p.is_file() or not _inside(root, p):
            raise ReleaseStop(f"archivo ausente o fuera de la raíz: {rel}")
        if p.is_symlink():
            raise ReleaseStop(f"symlink no permitido: {rel}")
        if p.stat().st_size != int(e["bytes"]):
            raise ReleaseStop(f"tamaño distinto en {rel}: {p.stat().st_size} != {e['bytes']}")
        if verify_hash and sha256_file(p) != e["sha256"]:
            raise ReleaseStop(f"SHA-256 distinto en {rel}")
        out[asset] = AssetFile(asset, p, e["sha256"], int(e["bytes"]), int(e["rows"]))
    return out


def select_row_groups(pf: pq.ParquetFile, start: int, end: int) -> list[int]:
    """Row groups con trade_date dentro de [start, end] por estadísticas. STOP ante estadísticas ausentes o grupos mixtos."""
    if end >= HOLDOUT_FIRST_TRADE_DATE:
        raise ReleaseStop(f"rango solicitado alcanza el holdout (>= {HOLDOUT_FIRST_TRADE_DATE}): {start}..{end}")
    names = pf.schema_arrow.names
    if TRADE_DATE_COL not in names:
        raise ReleaseStop("el archivo no tiene columna trade_date")
    ci = names.index(TRADE_DATE_COL)
    keep = []
    for g in range(pf.metadata.num_row_groups):
        st = pf.metadata.row_group(g).column(ci).statistics
        if st is None or not st.has_min_max:
            raise ReleaseStop(f"row group {g} sin estadísticas de trade_date")
        lo, hi = int(st.min), int(st.max)
        if hi >= HOLDOUT_FIRST_TRADE_DATE:
            raise ReleaseStop(f"row group {g} contiene fechas reservadas ({lo}..{hi}): STOP")
        if hi < start or lo > end:
            continue
        if lo < start or hi > end:
            raise ReleaseStop(f"row group {g} ({lo}..{hi}) cruza el borde del rango pedido; pedir sesiones completas")
        keep.append(g)
    return keep


def read_asset(release_dir, asset, start_trade_date: int, end_trade_date: int, *, columns=None, verify_hash=True):
    files = load_manifest(release_dir, verify_hash=verify_hash)
    if asset not in files:
        raise ReleaseStop(f"activo {asset!r} no figura en el manifiesto")
    pf = pq.ParquetFile(files[asset].path)
    groups = select_row_groups(pf, int(start_trade_date), int(end_trade_date))
    if not groups:
        return pf.schema_arrow.empty_table() if columns is None else pf.schema_arrow.empty_table().select(columns)
    return pf.read_row_groups(groups, columns=columns)


def cache_key(file_sha256: str, schema_version: str, transform: str, transform_version: str) -> str:
    """Clave de caché por contenido: cambia si cambia el archivo, el esquema o la transformación."""
    return hashlib.sha256("|".join((file_sha256, schema_version, transform, transform_version)).encode()).hexdigest()
