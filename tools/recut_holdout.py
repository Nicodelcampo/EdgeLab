#!/usr/bin/env python3
"""Re-corte fisico del holdout sobre los parquets que lo contienen (P-18).

Por que existe
--------------
`tools/build_kaggle_bundle.py` v2 DETECTA los archivos que alcanzan la apertura
de la sesion del holdout y los deja fuera del staging con
`kind=HOLDOUT_OVERLAP` / `recut_required`. No los corta: por doctrina, los
parquets de origen son inmutables. Esta herramienta produce las copias
saneadas en un arbol NUEVO, sin tocar el origen, de modo que el builder pueda
correrse contra ese arbol y emitir su veredicto sobre datos sin holdout.

Que NO hace
-----------
- No modifica ni borra ningun archivo del arbol de origen.
- No decide nada sobre licencia (P-07) ni sobre presupuesto: mide y reporta.
- No sube nada a Kaggle.

Reglas duras
------------
1. El corte es por TRADE DATE de CME, no por UTC: se conserva la fila si
   `ts_utc_ns < session_bounds_utc_ns(HOLDOUT_FIRST_TRADE_DATE)[0]`, es decir
   17:00 CT del dia anterior. El corte UTC ingenuo se calcula igual, pero solo
   para REPORTAR cuantas filas de holdout habria dejado pasar.
2. Identidad encadenada: el sha256 de cada origen debe coincidir con el que
   registro el builder en `bundle_index.json`. Si difiere -> FAIL_SOURCE.
3. El indice de origen debe estar sellado consigo mismo (`index_sha256`) y
   producido por el tool esperado. Si no cierra -> FAIL_INDEX.
4. Verificacion post-escritura obligatoria: filas, esquema, monotonia,
   `ts_max`, `trade_date_max <= RESEARCH_MAX_TRADE_DATE` y digest por columna
   del prefijo conservado. Si algo no cierra, la salida se marca `.rejected`.
5. Fail-closed: cualquier duda aborta o abstiene. Nunca se emite una salida
   "parcial" sin nombrarla.

Salidas
-------
- `<out-base>/<carpeta-activo>/<mismo nombre>.parquet` por cada archivo cortado
  (mismo nombre para que `FILENAME_RE` del builder lo siga parseando).
- `<out-base>/recut_index.json`: siempre, incluso sin PASS (rastro de auditoria).
- Enlaces/copias verificadas de los archivos limpios, para que `<out-base>` sea
  un `--base` completo y valido para el builder.

Veredictos y exit codes
-----------------------
PASS 0 | ABSTAIN_* 2 | FAIL_* 1

Uso
---
    python tools/recut_holdout.py --index E:/EdgeLab/kaggle_dataset/bundle_index.json
    python tools/recut_holdout.py --index ... --precheck      # solo medicion
    python tools/recut_holdout.py --selftest                   # sin pyarrow
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

TOOL_ID = "tools/recut_holdout.py@v1"
SCHEMA_VERSION = 1
REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = Path(__file__).resolve().with_name("build_kaggle_bundle.py")
DEFAULT_OUT_BASE = Path("E:/EdgeLab/data/nt8_research_v2")
DEFAULT_BATCH_ROWS = 262_144

EXPECTED_SOURCE_TOOLS = {"tools/build_kaggle_bundle.py@v2"}
SOURCE_VERDICTS_OK = {"PASS", "ABSTAIN_LICENSE", "ABSTAIN_HOLDOUT", "ABSTAIN_CAPACITY"}

VERDICT_PRECEDENCE = (
    "FAIL_INDEX",
    "FAIL_SOURCE",
    "FAIL_UNSORTED",
    "FAIL_VERIFY",
    "ABSTAIN_BACKEND",
    "ABSTAIN_COVERAGE",
    "PASS",
)


def verdict_exit_code(verdict: str) -> int:
    if verdict == "PASS":
        return 0
    return 2 if verdict.startswith("ABSTAIN") else 1


def worst(verdicts) -> str:
    for v in VERDICT_PRECEDENCE:
        if v in verdicts:
            return v
    return "PASS"


# ---------------------------------------------------------------------------
# Backends de parquet. pyarrow queda aislado aca para que toda la logica de
# corte, verificacion y manifiesto sea testeable sin pyarrow.
# ---------------------------------------------------------------------------


class FakeBatch:
    """Lote en memoria: dict de columnas -> lista de valores."""

    def __init__(self, names, columns):
        self.names = list(names)
        self.columns = {k: list(v) for k, v in columns.items()}
        self.num_rows = len(self.columns[self.names[0]]) if self.names else 0

    def slice(self, offset: int, length: int) -> "FakeBatch":
        return FakeBatch(
            self.names,
            {k: v[offset : offset + length] for k, v in self.columns.items()},
        )


class FakeReader:
    def __init__(self, path: Path, ts_column: str):
        self._doc = json.loads(Path(path).read_text(encoding="utf-8"))
        self.schema = tuple(
            (n, t) for n, t in zip(self._doc["schema"]["names"], self._doc["schema"]["types"])
        )
        self.compression = self._doc.get("compression", "ZSTD")
        self.names = list(self._doc["schema"]["names"])
        self.num_rows = len(self._doc["columns"][self.names[0]])
        self._ts_column = ts_column

    def batches(self, batch_rows: int):
        for off in range(0, self.num_rows, batch_rows):
            take = min(batch_rows, self.num_rows - off)
            yield FakeBatch(
                self.names,
                {k: v[off : off + take] for k, v in self._doc["columns"].items()},
            )

    def close(self):
        return None


class FakeWriter:
    def __init__(self, path: Path, schema, compression: str):
        self.path = Path(path)
        self.schema = schema
        self.compression = compression
        self._columns = {n: [] for n, _ in schema}
        self._closed = False

    def write(self, batch: FakeBatch):
        for name in self._columns:
            self._columns[name].extend(batch.columns[name])

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": {
                "names": [n for n, _ in self.schema],
                "types": [t for _, t in self.schema],
            },
            "compression": self.compression,
            "columns": self._columns,
        }
        self.path.write_text(
            json.dumps(doc, sort_keys=True, separators=(",", ":")), encoding="utf-8"
        )


class FakeBackend:
    """Backend de prueba: 'parquet' = JSON. Mismo protocolo que pyarrow."""

    name = "fake"

    def __init__(self, ts_column: str):
        self.ts_column = ts_column

    def open_reader(self, path):
        return FakeReader(path, self.ts_column)

    def open_writer(self, path, schema, compression):
        return FakeWriter(path, schema, compression)

    def ts_values(self, batch: FakeBatch):
        return batch.columns[self.ts_column]

    def digest_update(self, hashers: dict, batch: FakeBatch) -> None:
        for name in batch.names:
            h = hashers[name]
            for v in batch.columns[name]:
                h.update(b"\xff" if v is None else repr(v).encode("utf-8"))
                h.update(b"\x00")


class ArrowBackend:  # pragma: no cover - requiere pyarrow (maquina local)
    """Backend real. Streaming por lotes, memoria acotada."""

    name = "pyarrow"

    def __init__(self, ts_column: str):
        import numpy as np  # noqa: F401
        import pyarrow as pa
        import pyarrow.parquet as pq

        self.pa = pa
        self.pq = pq
        self.np = np
        self.ts_column = ts_column

    class _Reader:
        def __init__(self, backend, path):
            self._pf = backend.pq.ParquetFile(str(path))
            self._backend = backend
            self.num_rows = self._pf.metadata.num_rows
            self.arrow_schema = self._pf.schema_arrow
            self.names = list(self.arrow_schema.names)
            self.schema = tuple(
                (f.name, str(f.type)) for f in self.arrow_schema
            )
            comp = None
            if self._pf.metadata.num_row_groups:
                comp = self._pf.metadata.row_group(0).column(0).compression
            self.compression = (comp or "ZSTD").upper()
            if self.compression == "UNCOMPRESSED":
                self.compression = "NONE"

        def batches(self, batch_rows: int):
            for b in self._pf.iter_batches(batch_size=batch_rows):
                yield b

        def close(self):
            self._pf.close()

    class _Writer:
        def __init__(self, backend, path, arrow_schema, compression):
            comp = "none" if compression in ("NONE", "UNCOMPRESSED") else compression.lower()
            self._w = backend.pq.ParquetWriter(
                str(path), arrow_schema, compression=comp
            )

        def write(self, batch):
            self._w.write_batch(batch)

        def close(self):
            self._w.close()

    def open_reader(self, path):
        return ArrowBackend._Reader(self, path)

    def open_writer(self, path, schema, compression):
        raise RuntimeError("usar open_writer_arrow con el esquema arrow del origen")

    def open_writer_arrow(self, path, arrow_schema, compression):
        return ArrowBackend._Writer(self, path, arrow_schema, compression)

    def ts_values(self, batch):
        return batch.column(self.ts_column).to_numpy(zero_copy_only=False)

    def digest_update(self, hashers: dict, batch) -> None:
        np = self.np
        for i, name in enumerate(batch.schema.names):
            col = batch.column(i)
            h = hashers[name]
            h.update(col.is_null().to_numpy(zero_copy_only=False).tobytes())
            try:
                arr = col.to_numpy(zero_copy_only=False)
                if arr.dtype == object:
                    raise TypeError("object dtype")
                h.update(np.ascontiguousarray(arr).tobytes())
            except Exception:
                for v in col.to_pylist():
                    if v is None:
                        h.update(b"\xff")
                    elif isinstance(v, bytes):
                        h.update(v)
                    else:
                        h.update(str(v).encode("utf-8"))
                    h.update(b"\x00")


# ---------------------------------------------------------------------------
# Indice de origen
# ---------------------------------------------------------------------------


def validate_source_index(path: Path, identity) -> tuple[dict, list[str]]:
    """Carga y valida el bundle_index.json del builder. Fail-closed."""
    problems: list[str] = []
    if not Path(path).is_file():
        return {}, [f"no existe el indice de origen: {path}"]
    try:
        index = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"indice ilegible: {exc}"]
    if not isinstance(index, dict):
        return {}, ["el indice no es un objeto JSON"]

    tool = index.get("tool")
    if tool not in EXPECTED_SOURCE_TOOLS:
        problems.append(f"tool inesperado en el indice: {tool!r}")
    if index.get("schema_version") != 2:
        problems.append(f"schema_version inesperado: {index.get('schema_version')!r}")

    declared = index.get("index_sha256")
    if not declared:
        problems.append("el indice no trae index_sha256")
    else:
        body = {k: v for k, v in index.items() if k != "index_sha256"}
        recomputed = identity.sha256_json(body)
        if recomputed != declared:
            problems.append(
                f"index_sha256 no cierra contra su contenido "
                f"(declarado {declared[:16]}..., recomputado {recomputed[:16]}...)"
            )

    verdict = index.get("verdict")
    if verdict not in SOURCE_VERDICTS_OK:
        problems.append(
            f"veredicto del indice no habilita re-corte: {verdict!r} "
            "(un indice FAIL_* no es una base confiable)"
        )
    if not isinstance(index.get("files"), list) or not index["files"]:
        problems.append("el indice no trae registros de archivos")
    return index, problems


def select_targets(index: dict) -> tuple[list[dict], list[dict]]:
    """Devuelve (a_cortar, limpios) segun lo que midio el builder."""
    targets, clean = [], []
    for rec in index.get("files", []):
        if rec.get("holdout_overlap"):
            targets.append(rec)
        elif rec.get("eligible"):
            clean.append(rec)
    return targets, clean


# ---------------------------------------------------------------------------
# Corte
# ---------------------------------------------------------------------------


def _new_hashers(names) -> dict:
    return {n: hashlib.sha256() for n in names}


def _digests(hashers: dict) -> dict:
    return {k: v.hexdigest() for k, v in sorted(hashers.items())}


def measure_source(backend, path: Path, cut_ns: int, naive_cut_ns: int, batch_rows: int) -> dict:
    """Pasada 1: monotonia + conteos + digest del prefijo conservado."""
    reader = backend.open_reader(path)
    try:
        hashers = _new_hashers(reader.names)
        rows_total = 0
        rows_keep = 0
        rows_naive_keep = 0
        ts_min = None
        ts_max = None
        ts_max_keep = None
        prev = None
        unsorted_at = None
        keeping = True
        for batch in reader.batches(batch_rows):
            ts = list(backend.ts_values(batch))
            n = len(ts)
            if n == 0:
                continue
            for j, t in enumerate(ts):
                t = int(t)
                if prev is not None and t < prev and unsorted_at is None:
                    unsorted_at = rows_total + j
                prev = t
            if ts_min is None:
                ts_min = int(ts[0])
            ts_max = int(ts[-1])
            take = 0
            if keeping:
                for t in ts:
                    if int(t) < cut_ns:
                        take += 1
                    else:
                        keeping = False
                        break
            if take:
                backend.digest_update(hashers, batch.slice(0, take))
                rows_keep += take
                ts_max_keep = int(ts[take - 1])
            rows_naive_keep += sum(1 for t in ts if int(t) < naive_cut_ns)
            rows_total += n
        return {
            "rows_total": rows_total,
            "rows_keep": rows_keep,
            "rows_drop": rows_total - rows_keep,
            "rows_naive_keep": rows_naive_keep,
            "rows_leaked_by_naive_utc_cut": max(0, rows_naive_keep - rows_keep),
            "ts_min_ns": ts_min,
            "ts_max_ns": ts_max,
            "ts_max_keep_ns": ts_max_keep,
            "unsorted_at_row": unsorted_at,
            "schema": list(reader.schema),
            "compression": reader.compression,
            "digest": _digests(hashers),
            "reader": reader,
        }
    except Exception:
        reader.close()
        raise


def write_prefix(backend, src_path: Path, dst_path: Path, rows_keep: int, batch_rows: int) -> None:
    """Pasada 2: escribe las primeras `rows_keep` filas preservando esquema."""
    reader = backend.open_reader(src_path)
    try:
        if isinstance(backend, ArrowBackend):  # pragma: no cover
            writer = backend.open_writer_arrow(
                dst_path, reader.arrow_schema, reader.compression
            )
        else:
            writer = backend.open_writer(dst_path, reader.schema, reader.compression)
        remaining = rows_keep
        try:
            for batch in reader.batches(batch_rows):
                if remaining <= 0:
                    break
                take = min(batch.num_rows, remaining)
                writer.write(batch.slice(0, take) if take != batch.num_rows else batch)
                remaining -= take
        finally:
            writer.close()
        if remaining > 0:
            raise RuntimeError(
                f"el origen se agoto antes de escribir {rows_keep} filas (faltaron {remaining})"
            )
    finally:
        reader.close()


def verify_output(backend, path: Path, expect: dict, cut_ns: int, batch_rows: int) -> list[str]:
    """Pasada 3: la salida tiene que cerrar contra el prefijo medido."""
    problems: list[str] = []
    reader = backend.open_reader(path)
    try:
        if list(reader.schema) != list(expect["schema"]):
            problems.append("el esquema de la salida no es identico al del origen")
        if reader.num_rows != expect["rows_keep"]:
            problems.append(
                f"filas de la salida {reader.num_rows} != prefijo medido {expect['rows_keep']}"
            )
        hashers = _new_hashers(reader.names)
        prev = None
        ts_max = None
        over_cut = 0
        seen = 0
        for batch in reader.batches(batch_rows):
            backend.digest_update(hashers, batch)
            for t in backend.ts_values(batch):
                t = int(t)
                if prev is not None and t < prev:
                    problems.append("la salida no es monotona en ts_utc_ns")
                    prev = t
                    break
                prev = t
                ts_max = t
                if t >= cut_ns:
                    over_cut += 1
            seen += batch.num_rows
        if over_cut:
            problems.append(f"la salida contiene {over_cut} filas en el holdout")
        if seen and ts_max != expect["ts_max_keep_ns"]:
            problems.append(
                f"ts_max de la salida {ts_max} != esperado {expect['ts_max_keep_ns']}"
            )
        got = _digests(hashers)
        if got != expect["digest"]:
            diff = [k for k in got if got.get(k) != expect["digest"].get(k)]
            problems.append(f"digest por columna no coincide en: {sorted(diff)[:6]}")
    finally:
        reader.close()
    return problems


# ---------------------------------------------------------------------------
# Enlace de los archivos limpios
# ---------------------------------------------------------------------------


def link_clean_files(clean, base: Path, out_base: Path, asset_folders, identity, prefer_hardlink=True):
    linked, problems = [], []
    for rec in clean:
        folder = asset_folders.get(rec["asset"])
        if folder is None:
            problems.append(f"activo sin carpeta declarada: {rec['asset']}")
            continue
        src = base / folder / rec["file"]
        dst = out_base / folder / rec["file"]
        if not src.is_file():
            problems.append(f"no existe el limpio en el origen: {src}")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        method = "present"
        if not dst.exists():
            try:
                if prefer_hardlink:
                    os.link(src, dst)
                    method = "hardlink"
                else:
                    raise OSError("copia forzada")
            except OSError:
                shutil.copy2(src, dst)
                method = "copy"
        got = identity.sha256_file(str(dst))
        ok = (not rec.get("sha256")) or got == rec["sha256"]
        if not ok:
            problems.append(f"sha256 del limpio enlazado no coincide: {rec['file']}")
        linked.append(
            {
                "file": rec["file"],
                "asset": rec["asset"],
                "method": method,
                "sha256": got,
                "sha256_matches_index": bool(ok),
                "bytes": int(rec.get("bytes") or Path(dst).stat().st_size),
            }
        )
    return linked, problems


# ---------------------------------------------------------------------------
# Proyeccion del presupuesto del builder
# ---------------------------------------------------------------------------


def project_bundle_budget(clean, recut_records, inventory) -> dict:
    records = []
    for rec in clean:
        records.append(
            {
                k: rec.get(k)
                for k in ("asset", "file", "rows", "bytes", "columns", "column_names", "stats_available")
            }
        )
    for rec in recut_records:
        if not rec.get("output"):
            continue
        records.append(
            {
                "asset": rec["asset"],
                "file": rec["file"],
                "rows": rec["rows_keep"],
                "bytes": rec.get("output_bytes") or 0,
                "columns": rec.get("columns"),
                "column_names": rec.get("column_names"),
                "stats_available": True,
            }
        )
    summary = inventory.summarize_census(records)
    metadata_files = 4
    budget = inventory.budget_gates(summary, top_level_files=len(records) + metadata_files)
    projected = "PASS" if budget["verdict"] == "PASS" else "ABSTAIN_CAPACITY"
    return {
        "files": len(records),
        "summary": summary,
        "budget": budget,
        "projected_builder_verdict_after_license": projected,
        "note": (
            "proyeccion mecanica: asume licencia APPROVED y G-HOLDOUT en PASS. "
            "No es un veredicto del builder."
        ),
    }


# ---------------------------------------------------------------------------
# Corrida principal
# ---------------------------------------------------------------------------


def run(
    index_path: Path,
    out_base: Path,
    base: Path | None = None,
    backend_name: str = "pyarrow",
    batch_rows: int = DEFAULT_BATCH_ROWS,
    link_clean: bool = True,
    prefer_hardlink: bool = True,
    precheck: bool = False,
    bundle=None,
    mods=None,
    backend=None,
) -> dict:
    bundle = bundle or load_builder()
    mods = mods or bundle.load_repo_modules(REPO_ROOT)
    identity = mods.identity
    sessions = mods.sessions
    inventory = mods.inventory

    verdicts: set[str] = set()
    problems: list[str] = []
    quarantine: list[dict] = []

    index, index_problems = validate_source_index(Path(index_path), identity)
    if index_problems:
        verdicts.add("FAIL_INDEX")
        problems.extend(index_problems)

    base = Path(base or index.get("base") or ".")
    out_base = Path(out_base)
    # Barrera de escritura: se evalua SIEMPRE, incluso con un indice invalido.
    # Un chequeo de seguridad no puede depender de que el resto este sano.
    try:
        same = (
            out_base.resolve() == base.resolve()
            or base.resolve() in out_base.resolve().parents
        )
    except OSError:
        same = str(out_base) == str(base)
    if same:
        raise SystemExit(
            "ABORT: --out-base no puede ser el arbol de origen ni estar dentro de el "
            "(los parquets de origen son inmutables)"
        )

    cut_ns, _ = sessions.session_bounds_utc_ns(bundle.HOLDOUT_FIRST_TRADE_DATE)
    naive_cut_ns = bundle.NAIVE_UTC_CUT_NS
    cut = {
        "rule": "se conserva ts_utc_ns < apertura de sesion CME del primer trade date de holdout",
        "holdout_first_trade_date": bundle.HOLDOUT_FIRST_TRADE_DATE,
        "research_max_trade_date": bundle.RESEARCH_MAX_TRADE_DATE,
        "session_open_utc_ns": int(cut_ns),
        "session_open_utc_iso": datetime.fromtimestamp(
            cut_ns / 1_000_000_000, tz=timezone.utc
        ).isoformat(),
        "naive_utc_cut_ns": int(naive_cut_ns),
        "naive_utc_cut_gap_seconds": int((naive_cut_ns - cut_ns) / 1_000_000_000),
    }

    targets, clean = select_targets(index) if index else ([], [])
    records: list[dict] = []

    if targets and backend is None:
        try:
            backend = ArrowBackend(bundle.TS_COLUMN) if backend_name == "pyarrow" else FakeBackend(bundle.TS_COLUMN)
        except Exception as exc:
            verdicts.add("ABSTAIN_BACKEND")
            problems.append(f"backend de parquet no disponible: {exc}")
            backend = None

    asset_folders = bundle.ASSET_FOLDERS

    if backend is not None and "FAIL_INDEX" not in verdicts:
        for rec in targets:
            folder = asset_folders.get(rec["asset"])
            src = base / folder / rec["file"] if folder else None
            out = {
                "file": rec["file"],
                "asset": rec["asset"],
                "contract": rec.get("contract"),
                "source": str(src) if src else None,
                "source_sha256_index": rec.get("sha256"),
                "columns": rec.get("columns"),
                "column_names": rec.get("column_names"),
                "output": None,
                "status": None,
            }
            if folder is None or src is None or not Path(src).is_file():
                out["status"] = "SOURCE_MISSING"
                quarantine.append({"file": rec["file"], "kind": "SOURCE_MISSING", "detail": str(src)})
                verdicts.add("FAIL_SOURCE")
                records.append(out)
                continue

            got_sha = identity.sha256_file(str(src))
            out["source_sha256"] = got_sha
            if rec.get("sha256") and got_sha != rec["sha256"]:
                out["status"] = "SOURCE_DRIFT"
                quarantine.append(
                    {
                        "file": rec["file"],
                        "kind": "SOURCE_DRIFT",
                        "detail": f"sha256 {got_sha[:16]}... != indice {rec['sha256'][:16]}...",
                    }
                )
                verdicts.add("FAIL_SOURCE")
                records.append(out)
                continue

            dst = out_base / folder / rec["file"]
            m = measure_source(backend, Path(src), int(cut_ns), int(naive_cut_ns), batch_rows)
            m.pop("reader").close()
            out.update(
                {
                    "rows_total": m["rows_total"],
                    "rows_keep": m["rows_keep"],
                    "rows_drop": m["rows_drop"],
                    "rows_leaked_by_naive_utc_cut": m["rows_leaked_by_naive_utc_cut"],
                    "ts_min_ns": m["ts_min_ns"],
                    "ts_max_ns": m["ts_max_ns"],
                    "ts_max_keep_ns": m["ts_max_keep_ns"],
                    "compression": m["compression"],
                }
            )
            if m["unsorted_at_row"] is not None:
                out["status"] = "NOT_SORTED"
                quarantine.append(
                    {
                        "file": rec["file"],
                        "kind": "NOT_SORTED",
                        "detail": f"primera inversion en la fila {m['unsorted_at_row']}",
                    }
                )
                verdicts.add("FAIL_UNSORTED")
                records.append(out)
                continue
            if m["rows_keep"] == 0:
                out["status"] = "EMPTY_AFTER_CUT"
                quarantine.append(
                    {
                        "file": rec["file"],
                        "kind": "EMPTY_AFTER_CUT",
                        "detail": "todo el archivo cae dentro del holdout: no se emite salida",
                    }
                )
                verdicts.add("ABSTAIN_COVERAGE")
                records.append(out)
                continue

            td_max = int(sessions.trade_date_ymd(_as_array(mods, [m["ts_max_keep_ns"]]))[0])
            out["trade_date_max_keep"] = td_max
            if td_max > bundle.RESEARCH_MAX_TRADE_DATE:
                out["status"] = "CUT_INSUFFICIENT"
                quarantine.append(
                    {"file": rec["file"], "kind": "CUT_INSUFFICIENT", "detail": f"trade_date_max {td_max}"}
                )
                verdicts.add("FAIL_VERIFY")
                records.append(out)
                continue

            if precheck:
                out["status"] = "PRECHECK_ONLY"
                records.append(out)
                continue

            if Path(dst).exists():
                existing = identity.sha256_file(str(dst))
                prob = verify_output(backend, Path(dst), m, int(cut_ns), batch_rows)
                if not prob:
                    out["status"] = "ALREADY_RECUT"
                    out["output"] = str(dst)
                    out["output_sha256"] = existing
                    out["output_bytes"] = Path(dst).stat().st_size
                    records.append(out)
                    continue
                out["status"] = "OUTPUT_CONFLICT"
                out["detail"] = prob
                quarantine.append(
                    {"file": rec["file"], "kind": "OUTPUT_CONFLICT", "detail": prob}
                )
                verdicts.add("FAIL_VERIFY")
                records.append(out)
                continue

            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            write_prefix(backend, Path(src), Path(dst), m["rows_keep"], batch_rows)
            prob = verify_output(backend, Path(dst), m, int(cut_ns), batch_rows)
            if prob:
                rejected = Path(str(dst) + ".rejected")
                if rejected.exists():
                    rejected.unlink()
                Path(dst).rename(rejected)
                out["status"] = "VERIFY_FAILED"
                out["detail"] = prob
                out["rejected_output"] = str(rejected)
                quarantine.append({"file": rec["file"], "kind": "VERIFY_FAILED", "detail": prob})
                verdicts.add("FAIL_VERIFY")
                records.append(out)
                continue

            out["status"] = "RECUT"
            out["output"] = str(dst)
            out["output_sha256"] = identity.sha256_file(str(dst))
            out["output_blob_sha1"] = identity.git_blob_sha1(str(dst))
            out["output_bytes"] = Path(dst).stat().st_size
            out["digest_columns"] = m["digest"]
            records.append(out)

    linked: list[dict] = []
    if link_clean and not precheck and "FAIL_INDEX" not in verdicts:
        linked, link_problems = link_clean_files(
            clean, base, out_base, asset_folders, identity, prefer_hardlink
        )
        if link_problems:
            problems.extend(link_problems)
            verdicts.add("FAIL_VERIFY")

    projected = project_bundle_budget(clean, records, inventory) if index else {}

    totals = {
        "targets": len(targets),
        "recut": sum(1 for r in records if r["status"] in ("RECUT", "ALREADY_RECUT")),
        "rows_total_source": sum(r.get("rows_total") or 0 for r in records),
        "rows_keep": sum(r.get("rows_keep") or 0 for r in records),
        "rows_drop": sum(r.get("rows_drop") or 0 for r in records),
        "rows_leaked_by_naive_utc_cut": sum(
            r.get("rows_leaked_by_naive_utc_cut") or 0 for r in records
        ),
        "clean_linked": len(linked),
    }

    verdict = worst(verdicts) if verdicts else "PASS"
    manifest = {
        "tool": TOOL_ID,
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend": getattr(backend, "name", None),
        "precheck": bool(precheck),
        "base": str(base),
        "out_base": str(out_base),
        "source_index": {
            "path": str(index_path),
            "tool": index.get("tool"),
            "index_sha256": index.get("index_sha256"),
            "verdict": index.get("verdict"),
            "created_at_utc": index.get("created_at_utc"),
        },
        "code_identity": getattr(mods, "code_identity", None),
        "cut": cut,
        "files": records,
        "linked_clean": linked,
        "quarantine": quarantine,
        "problems": problems,
        "totals": totals,
        "projected_bundle": projected,
        "verdict": verdict,
    }
    manifest["recut_index_sha256"] = identity.sha256_json(manifest)
    return manifest


def _as_array(mods, values):
    import numpy as np

    return np.asarray(values, dtype="int64")


def load_builder():
    if not BUILDER_PATH.is_file():
        raise SystemExit(f"ABORT: falta {BUILDER_PATH} (esta herramienta reutiliza sus constantes)")
    import importlib.util

    spec = importlib.util.spec_from_file_location("_edgelab_kbundle", str(BUILDER_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_edgelab_kbundle"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _fake_parquet(path: Path, ts_values, extra_cols=None, compression="ZSTD"):
    n = len(ts_values)
    cols = {"ts_utc_ns": [int(t) for t in ts_values]}
    cols["price"] = [100 + (i % 7) * 0.25 for i in range(n)]
    cols["size"] = [1 + (i % 3) for i in range(n)]
    if extra_cols:
        cols.update(extra_cols)
    doc = {
        "schema": {
            "names": list(cols.keys()),
            "types": ["int64", "double", "int32"] + (["string"] * (len(cols) - 3)),
        },
        "compression": compression,
        "columns": cols,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(doc, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return Path(path)


def _make_index(bundle, identity, base: Path, targets: dict, clean: dict, verdict="ABSTAIN_LICENSE"):
    files = []
    for name, info in {**clean, **targets}.items():
        asset = name.split("_")[0]
        rec = {
            "file": name,
            "asset": asset,
            "contract": name.split("_")[1],
            "rows": info["rows"],
            "bytes": info["bytes"],
            "columns": 3,
            "column_names": ["ts_utc_ns", "price", "size"],
            "stats_available": True,
            "sha256": info.get("sha256"),
            "ts_min_ns": info.get("ts_min"),
            "ts_max_ns": info.get("ts_max"),
            "holdout_overlap": name in targets,
            "eligible": name not in targets,
        }
        files.append(rec)
    index = {
        "tool": "tools/build_kaggle_bundle.py@v2",
        "schema_version": 2,
        "created_at_utc": "2026-08-15T01:00:00+00:00",
        "base": str(base),
        "files": files,
        "eligible_files": [f["file"] for f in files if f["eligible"]],
        "verdict": verdict,
    }
    index["index_sha256"] = identity.sha256_json(index)
    return index


def selftest() -> int:
    bundle = load_builder()
    mods = bundle.load_repo_modules(REPO_ROOT)
    identity, sessions = mods.identity, mods.sessions
    ok = fail = 0

    def check(label, cond, detail=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ok   {label}")
        else:
            fail += 1
            print(f"  FALLA {label} {detail}")

    open_ns, _ = sessions.session_bounds_utc_ns(bundle.HOLDOUT_FIRST_TRADE_DATE)
    naive = bundle.NAIVE_UTC_CUT_NS
    day = 86_400 * 1_000_000_000
    hour = 3_600 * 1_000_000_000

    print("S1 frontera del corte")
    check(
        "S1 apertura de sesion del holdout",
        datetime.fromtimestamp(open_ns / 1e9, tz=timezone.utc).isoformat() == "2026-06-30T22:00:00+00:00",
        datetime.fromtimestamp(open_ns / 1e9, tz=timezone.utc).isoformat(),
    )
    check("S1b brecha del corte UTC ingenuo = 7200 s", (naive - open_ns) // 1_000_000_000 == 7200)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base = tmp / "nt8"
        out_base = tmp / "research_v2"

        # 6E: cruza la frontera y ademas tiene filas dentro de la brecha de 7200 s
        ts_6e = (
            [open_ns - 3 * day + i * hour for i in range(24)]
            + [open_ns - 1, open_ns + 60_000_000_000, naive - 1, naive + day]
        )
        p6e = _fake_parquet(base / "6E" / "6E_09-26_ticks.parquet", ts_6e)
        # ES: cruza la frontera, sin filas en la brecha
        ts_es = [open_ns - 2 * day + i * hour for i in range(48)] + [open_ns + 5 * day]
        pes = _fake_parquet(base / "ES_parquet" / "ES_09-26_ticks.parquet", ts_es, compression="SNAPPY")
        # limpio
        ts_clean = [open_ns - 30 * day + i * hour for i in range(100)]
        pcl = _fake_parquet(base / "ES_parquet" / "ES_06-26_ticks.parquet", ts_clean)

        targets = {
            "6E_09-26_ticks.parquet": {
                "rows": len(ts_6e),
                "bytes": p6e.stat().st_size,
                "sha256": identity.sha256_file(str(p6e)),
                "ts_min": ts_6e[0],
                "ts_max": ts_6e[-1],
            },
            "ES_09-26_ticks.parquet": {
                "rows": len(ts_es),
                "bytes": pes.stat().st_size,
                "sha256": identity.sha256_file(str(pes)),
                "ts_min": ts_es[0],
                "ts_max": ts_es[-1],
            },
        }
        clean = {
            "ES_06-26_ticks.parquet": {
                "rows": len(ts_clean),
                "bytes": pcl.stat().st_size,
                "sha256": identity.sha256_file(str(pcl)),
                "ts_min": ts_clean[0],
                "ts_max": ts_clean[-1],
            }
        }
        index = _make_index(bundle, identity, base, targets, clean)
        idx_path = tmp / "bundle_index.json"
        idx_path.write_text(json.dumps(index), encoding="utf-8")

        def run_it(**kw):
            kw.setdefault("index_path", idx_path)
            kw.setdefault("out_base", out_base)
            kw.setdefault("bundle", bundle)
            kw.setdefault("mods", mods)
            kw.setdefault("backend", FakeBackend(bundle.TS_COLUMN))
            kw.setdefault("batch_rows", 7)
            return run(**kw)

        print("S2 validacion del indice de origen")
        _, probs = validate_source_index(idx_path, identity)
        check("S2 indice valido pasa", probs == [], probs)
        bad = dict(index)
        bad["files"] = list(index["files"])
        bad["base"] = str(base) + "X"
        bp = tmp / "bad.json"
        bp.write_text(json.dumps(bad), encoding="utf-8")
        _, probs = validate_source_index(bp, identity)
        check("S2b sello alterado -> problema", any("index_sha256" in p for p in probs), probs)
        bad2 = {k: v for k, v in index.items() if k != "index_sha256"}
        bad2["tool"] = "otro_script.py@v9"
        bad2["index_sha256"] = identity.sha256_json(
            {k: v for k, v in bad2.items() if k != "index_sha256"}
        )
        bp2 = tmp / "bad2.json"
        bp2.write_text(json.dumps(bad2), encoding="utf-8")
        _, probs = validate_source_index(bp2, identity)
        check("S2c tool inesperado -> problema", any("tool inesperado" in p for p in probs), probs)
        bad3 = {k: v for k, v in index.items() if k != "index_sha256"}
        bad3["verdict"] = "FAIL_INTEGRITY"
        bad3["index_sha256"] = identity.sha256_json(bad3)
        bp3 = tmp / "bad3.json"
        bp3.write_text(json.dumps(bad3), encoding="utf-8")
        _, probs = validate_source_index(bp3, identity)
        check("S2d indice FAIL_* no habilita re-corte", any("no habilita" in p for p in probs), probs)
        man = run_it(index_path=bp3)
        check("S2e y la corrida devuelve FAIL_INDEX", man["verdict"] == "FAIL_INDEX", man["verdict"])
        check("S2f sin escribir salidas", not (out_base / "6E").exists())

        print("S3 precheck (mide, no escribe)")
        man = run_it(precheck=True)
        r6 = next(r for r in man["files"] if r["file"].startswith("6E"))
        check("S3 precheck no escribe", not (out_base / "6E" / "6E_09-26_ticks.parquet").exists())
        check("S3b conteo de conservadas", r6["rows_keep"] == 25, r6["rows_keep"])
        check("S3c conteo de descartadas", r6["rows_drop"] == 3, r6["rows_drop"])
        check(
            "S3d filas que el corte UTC ingenuo habria dejado pasar",
            r6["rows_leaked_by_naive_utc_cut"] == 2,
            r6["rows_leaked_by_naive_utc_cut"],
        )
        check("S3e trade date maximo conservado", r6["trade_date_max_keep"] == 20260630, r6.get("trade_date_max_keep"))

        print("S4 re-corte real")
        man = run_it()
        check("S4 veredicto PASS", man["verdict"] == "PASS", man["verdict"])
        check("S4b exit code 0", verdict_exit_code(man["verdict"]) == 0)
        check("S4c dos archivos re-cortados", man["totals"]["recut"] == 2, man["totals"])
        check(
            "S4d salidas existen con el mismo nombre",
            (out_base / "6E" / "6E_09-26_ticks.parquet").is_file()
            and (out_base / "ES_parquet" / "ES_09-26_ticks.parquet").is_file(),
        )
        check(
            "S4e el nombre sigue parseando con FILENAME_RE del builder",
            bool(bundle.FILENAME_RE.match("6E_09-26_ticks.parquet")),
        )
        check("S4f limpio enlazado y verificado", man["totals"]["clean_linked"] == 1, man["totals"])
        check(
            "S4g compresion preservada por archivo",
            {r["file"]: r["compression"] for r in man["files"]}
            == {"6E_09-26_ticks.parquet": "ZSTD", "ES_09-26_ticks.parquet": "SNAPPY"},
        )
        check("S4h el origen no se modifico", identity.sha256_file(str(p6e)) == targets["6E_09-26_ticks.parquet"]["sha256"])
        check("S4i manifiesto sellado consigo mismo", bool(man.get("recut_index_sha256")))
        body = {k: v for k, v in man.items() if k != "recut_index_sha256"}
        check("S4j el sello del manifiesto cierra", identity.sha256_json(body) == man["recut_index_sha256"])

        print("S5 idempotencia")
        man2 = run_it()
        check(
            "S5 segunda corrida reconoce ALREADY_RECUT",
            all(r["status"] == "ALREADY_RECUT" for r in man2["files"]),
            [r["status"] for r in man2["files"]],
        )
        check("S5b sigue PASS", man2["verdict"] == "PASS", man2["verdict"])

        print("S6 proyeccion del presupuesto")
        proj = man["projected_bundle"]
        check("S6 proyeccion presente", bool(proj))
        check(
            "S6b con datos chicos la proyeccion es PASS",
            proj["projected_builder_verdict_after_license"] == "PASS",
            proj["projected_builder_verdict_after_license"],
        )
        big_clean = [
            {
                "asset": "ES",
                "file": f"ES_{i:02d}-26_ticks.parquet",
                "rows": 20_000_000,
                "bytes": 350 << 20,
                "columns": 3,
                "column_names": ["ts_utc_ns", "price", "size"],
                "stats_available": True,
            }
            for i in range(45)
        ]
        proj_big = project_bundle_budget(big_clean, [], mods.inventory)
        check(
            "S6c 45 archivos de 350 MiB -> ABSTAIN_CAPACITY proyectado",
            proj_big["projected_builder_verdict_after_license"] == "ABSTAIN_CAPACITY",
            proj_big["budget"]["verdict"],
        )
        check(
            "S6d y falla tanto por GiB como por archivos top-level",
            not proj_big["budget"]["gates"]["input_size_gib"]["pass"]
            and not proj_big["budget"]["gates"]["top_level_files_contract"]["pass"],
        )

    print("S7 rechazos duros")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base, out_base = tmp / "nt8", tmp / "out"
        ts = [open_ns - day + i * hour for i in range(10)] + [open_ns + hour]
        p = _fake_parquet(base / "6E" / "6E_09-26_ticks.parquet", ts)
        tg = {
            "6E_09-26_ticks.parquet": {
                "rows": len(ts),
                "bytes": p.stat().st_size,
                "sha256": "0" * 64,
                "ts_min": ts[0],
                "ts_max": ts[-1],
            }
        }
        index = _make_index(bundle, identity, base, tg, {})
        ip = tmp / "idx.json"
        ip.write_text(json.dumps(index), encoding="utf-8")
        man = run(
            index_path=ip,
            out_base=out_base,
            bundle=bundle,
            mods=mods,
            backend=FakeBackend(bundle.TS_COLUMN),
            batch_rows=4,
        )
        check("S7 sha256 del origen no coincide -> FAIL_SOURCE", man["verdict"] == "FAIL_SOURCE", man["verdict"])
        check("S7b no escribio salida", not (out_base / "6E").exists())
        check("S7c exit code 1", verdict_exit_code(man["verdict"]) == 1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base, out_base = tmp / "nt8", tmp / "out"
        ts = [open_ns - day, open_ns - 2 * day, open_ns + hour]  # desordenado
        p = _fake_parquet(base / "6E" / "6E_09-26_ticks.parquet", ts)
        tg = {
            "6E_09-26_ticks.parquet": {
                "rows": len(ts),
                "bytes": p.stat().st_size,
                "sha256": identity.sha256_file(str(p)),
                "ts_min": ts[0],
                "ts_max": ts[-1],
            }
        }
        index = _make_index(bundle, identity, base, tg, {})
        ip = tmp / "idx.json"
        ip.write_text(json.dumps(index), encoding="utf-8")
        man = run(
            index_path=ip,
            out_base=out_base,
            bundle=bundle,
            mods=mods,
            backend=FakeBackend(bundle.TS_COLUMN),
            batch_rows=2,
        )
        check("S8 ts no monotono -> FAIL_UNSORTED", man["verdict"] == "FAIL_UNSORTED", man["verdict"])
        check("S8b no escribio salida", not (out_base / "6E").exists())

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base, out_base = tmp / "nt8", tmp / "out"
        ts = [open_ns + i * hour for i in range(5)]  # todo holdout
        p = _fake_parquet(base / "6E" / "6E_09-26_ticks.parquet", ts)
        tg = {
            "6E_09-26_ticks.parquet": {
                "rows": len(ts),
                "bytes": p.stat().st_size,
                "sha256": identity.sha256_file(str(p)),
                "ts_min": ts[0],
                "ts_max": ts[-1],
            }
        }
        index = _make_index(bundle, identity, base, tg, {})
        ip = tmp / "idx.json"
        ip.write_text(json.dumps(index), encoding="utf-8")
        man = run(
            index_path=ip,
            out_base=out_base,
            bundle=bundle,
            mods=mods,
            backend=FakeBackend(bundle.TS_COLUMN),
            batch_rows=2,
        )
        check(
            "S9 archivo enteramente en holdout -> ABSTAIN_COVERAGE",
            man["verdict"] == "ABSTAIN_COVERAGE",
            man["verdict"],
        )
        check("S9b exit code 2", verdict_exit_code(man["verdict"]) == 2)
        check("S9c queda nombrado en cuarentena", man["quarantine"][0]["kind"] == "EMPTY_AFTER_CUT")

    print("S10 verificacion post-escritura")

    class DroppingBackend(FakeBackend):
        """Escribe una fila menos: simula una escritura silenciosamente mala."""

        def open_writer(self, path, schema, compression):
            w = FakeWriter(path, schema, compression)
            orig = w.write
            state = {"first": True}

            def write(batch):
                if state["first"] and batch.num_rows > 1:
                    state["first"] = False
                    batch = batch.slice(0, batch.num_rows - 1)
                orig(batch)

            w.write = write
            return w

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base, out_base = tmp / "nt8", tmp / "out"
        ts = [open_ns - day + i * hour for i in range(10)] + [open_ns + hour]
        p = _fake_parquet(base / "6E" / "6E_09-26_ticks.parquet", ts)
        tg = {
            "6E_09-26_ticks.parquet": {
                "rows": len(ts),
                "bytes": p.stat().st_size,
                "sha256": identity.sha256_file(str(p)),
                "ts_min": ts[0],
                "ts_max": ts[-1],
            }
        }
        index = _make_index(bundle, identity, base, tg, {})
        ip = tmp / "idx.json"
        ip.write_text(json.dumps(index), encoding="utf-8")
        man = run(
            index_path=ip,
            out_base=out_base,
            bundle=bundle,
            mods=mods,
            backend=DroppingBackend(bundle.TS_COLUMN),
            batch_rows=50,
        )
        check("S10 escritura corta -> FAIL_VERIFY", man["verdict"] == "FAIL_VERIFY", man["verdict"])
        check(
            "S10b la salida mala queda marcada .rejected",
            (out_base / "6E" / "6E_09-26_ticks.parquet.rejected").is_file()
            and not (out_base / "6E" / "6E_09-26_ticks.parquet").is_file(),
        )

    print("S11 digest independiente del tamano de lote")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        ts = [open_ns - day + i * 60_000_000_000 for i in range(97)]
        p = _fake_parquet(Path(tmp) / "x.parquet", ts)
        be = FakeBackend(bundle.TS_COLUMN)
        d = []
        for bs in (1, 7, 96, 1000):
            m = measure_source(be, p, int(open_ns), int(naive), bs)
            m.pop("reader").close()
            d.append((m["digest"], m["rows_keep"]))
        check("S11 mismo digest con 4 tamanos de lote", len({json.dumps(x[0], sort_keys=True) for x in d}) == 1)
        check("S11b mismo conteo", len({x[1] for x in d}) == 1 and d[0][1] == 97)

    print("S12 proteccion del arbol de origen")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        base = tmp / "nt8"
        base.mkdir(parents=True)
        index = _make_index(bundle, identity, base, {}, {})
        ip = tmp / "idx.json"
        ip.write_text(json.dumps(index), encoding="utf-8")
        raised = False
        try:
            run(
                index_path=ip,
                out_base=base / "sub",
                bundle=bundle,
                mods=mods,
                backend=FakeBackend(bundle.TS_COLUMN),
            )
        except SystemExit:
            raised = True
        check("S12 out-base dentro del origen -> ABORT", raised)

    print(f"\nself-test: {fail} fallas, {ok} checks ok")
    return 0 if fail == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Re-corte fisico del holdout (P-18)")
    ap.add_argument("--index", help="bundle_index.json producido por el builder v2")
    ap.add_argument("--base", default=None, help="arbol de origen (default: el del indice)")
    ap.add_argument("--out-base", default=str(DEFAULT_OUT_BASE))
    ap.add_argument("--out", default=None, help="ruta del recut_index.json")
    ap.add_argument("--batch-rows", type=int, default=DEFAULT_BATCH_ROWS)
    ap.add_argument("--no-link-clean", action="store_true")
    ap.add_argument("--copy", action="store_true", help="copiar en vez de hardlink")
    ap.add_argument("--precheck", action="store_true", help="solo medir, no escribir")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--backend", choices=("pyarrow", "fake"), default="pyarrow")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.index:
        ap.error("--index es obligatorio (o usa --selftest)")

    out_base = Path(args.out_base)
    manifest = run(
        index_path=Path(args.index),
        out_base=out_base,
        base=Path(args.base) if args.base else None,
        backend_name=args.backend,
        batch_rows=args.batch_rows,
        link_clean=not args.no_link_clean,
        prefer_hardlink=not args.copy,
        precheck=args.precheck,
    )

    out_path = Path(args.out) if args.out else out_base / "recut_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    t = manifest["totals"]
    print(
        f"[{manifest['verdict']}] {t['recut']}/{t['targets']} archivos re-cortados | "
        f"conservadas {t['rows_keep']:,} | descartadas {t['rows_drop']:,} | "
        f"el corte UTC ingenuo habria filtrado {t['rows_leaked_by_naive_utc_cut']:,} filas"
    )
    proj = manifest.get("projected_bundle") or {}
    if proj:
        print(
            f"proyeccion del bundle: {proj['files']} archivos, "
            f"{proj['summary'].get('total_gib', 0):.3f} GiB -> "
            f"{proj['projected_builder_verdict_after_license']}"
        )
    for q in manifest["quarantine"]:
        print(f"  cuarentena {q['kind']}: {q['file']}")
    for p in manifest["problems"]:
        print(f"  problema: {p}")
    print(f"manifiesto: {out_path}")
    return verdict_exit_code(manifest["verdict"])


if __name__ == "__main__":
    raise SystemExit(main())
