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
HOLDOUT_FIRST_TS_NS = 1_790_805_600_000_000_000        # 2026-09-30T22:00:00Z: apertura CME de la sesión del 2026-10-01
TRADE_DATE_COL = "trade_date"
TS_COL = "ts_utc_ns"


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


PURPOSES = ("audit", "provisional_research", "research")
APPROVAL_FILE = "release_approval.json"
EXTERNAL_APPROVAL_DIR = "docs/infra/release_approval"      # aprobaciones versionadas en el repo, nombradas release_approval_<sha8>.json


def _load_approval(root: Path, mpath: Path):
    """Aprobacion dentro de la release o, si no esta, la externa del repo atada al SHA del manifiesto."""
    ap = root / APPROVAL_FILE
    if ap.is_file():
        return json.loads(ap.read_text(encoding="utf-8"))
    ext = Path(__file__).resolve().parents[3] / EXTERNAL_APPROVAL_DIR / f"release_approval_{sha256_file(mpath)[:8]}.json"
    return json.loads(ext.read_text(encoding="utf-8")) if ext.is_file() else None


def _check_admission(root: Path, mpath: Path, m: dict, purpose, verify_hash) -> None:
    """Integridad no es admisión (LRA-05). `audit` puede examinar una candidata; `provisional_research` también pero el llamador
    debe rotular todo resultado como PROVISIONAL; `research` exige aprobación externa atada al hash exacto del manifiesto."""
    if purpose not in PURPOSES:
        raise ReleaseStop(f"declarar purpose en {PURPOSES}; recibido {purpose!r}")
    if purpose == "research":
        if verify_hash is not True:
            raise ReleaseStop("purpose='research' exige verify_hash=True (sin atajos)")
        a = _load_approval(root, mpath)
        if a is None:
            raise ReleaseStop(f"release no aprobada para research: falta {APPROVAL_FILE} (en la release o en {EXTERNAL_APPROVAL_DIR}/) con la aprobacion de Nico")
        if a.get("manifest_sha256") != sha256_file(mpath) or not a.get("approved_by") or a.get("liquidity_policy_approved") is not True:
            raise ReleaseStop("aprobación ausente, sin aprobador, sin política aprobada o atada a otro manifiesto")
        # El manifiesto es inmutable (cambiarlo cambia su SHA): una aprobacion POSTERIOR no puede reescribirlo. La aprobacion externa,
        # atada al SHA exacto y versionada en git, es la forma de levantar `research_allowed=false` del momento de construccion.
        if not m.get("research_allowed", False) and a.get("supersedes_manifest_research_allowed") is not True:
            raise ReleaseStop("el manifiesto no declara research_allowed=true y la aprobacion no lo levanta explicitamente")


def _check_metadata_files(root: Path, m: dict, verify_hash: bool) -> None:
    for rel, e in (m.get("metadata_files") or {}).items():
        if os.path.isabs(rel) or ".." in Path(rel).parts:
            raise ReleaseStop(f"metadata_files: ruta no relativa o con traversal: {rel}")
        p = root / rel
        if not p.is_file() or not _inside(root, p):
            raise ReleaseStop(f"metadata_files: archivo listado ausente: {rel}")
        if p.stat().st_size != int(e["bytes"]):
            raise ReleaseStop(f"metadata_files: tamaño distinto en {rel}")
        if verify_hash and sha256_file(p) != e["sha256"]:
            raise ReleaseStop(f"metadata_files: SHA-256 distinto en {rel}")


def load_manifest(release_dir, *, verify_hash=True, purpose=None) -> dict[str, AssetFile]:
    root = Path(release_dir)
    mpath = root / "release_manifest.json"
    if not mpath.is_file():
        raise ReleaseStop(f"falta release_manifest.json en {root}")
    m = json.loads(mpath.read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA:
        raise ReleaseStop(f"esquema de manifiesto desconocido: {m.get('schema')!r}")
    _check_admission(root, mpath, m, purpose, verify_hash)
    _check_metadata_files(root, m, bool(verify_hash))
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


def preflight_footer(pf: pq.ParquetFile) -> None:
    """STOP de custodia ANTES de leer cualquier payload (LRA-04, LRA-06).

    Verifica en el pie del archivo, para TODOS los row groups, los dos relojes: `trade_date` y `ts_utc_ns`. Rechaza esquema
    sin alguna de las dos columnas, estadísticas ausentes o sin min/max, nulls, y cualquier fecha o timestamp reservados.
    Es una guarda de footer: un footer falso no se detecta acá; la coherencia payload<->footer se comprueba después con el
    verificador, sin usarla para justificar una lectura reservada."""
    names = pf.schema_arrow.names
    cols = {}
    for col in (TRADE_DATE_COL, TS_COL):
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
            limit = HOLDOUT_FIRST_TRADE_DATE if col == TRADE_DATE_COL else HOLDOUT_FIRST_TS_NS
            if int(st.max) >= limit:
                raise ReleaseStop(f"row group {g} contiene {col} reservado (max {int(st.max)} >= {limit}): STOP")


def select_row_groups(pf: pq.ParquetFile, start: int, end: int) -> list[int]:
    """Row groups con trade_date dentro de [start, end] por estadísticas. STOP ante estadísticas ausentes o grupos mixtos."""
    if end >= HOLDOUT_FIRST_TRADE_DATE:
        raise ReleaseStop(f"rango solicitado alcanza el holdout (>= {HOLDOUT_FIRST_TRADE_DATE}): {start}..{end}")
    preflight_footer(pf)
    names = pf.schema_arrow.names
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


def read_asset(release_dir, asset, start_trade_date: int, end_trade_date: int, *, columns=None, verify_hash=True, purpose=None):
    files = load_manifest(release_dir, verify_hash=verify_hash, purpose=purpose)
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
