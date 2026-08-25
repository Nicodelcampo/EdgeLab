#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convierte dumps CSV L1/L2 de NT8 a Parquet sin reordenar eventos.

Contrato de entrada (dump NRD -> CSV ya usado por EdgeLab):

    L2;side;YYYYmmddHHMMSS;microsecond;operation;level;;price;size
    L1;side;YYYYmmddHHMMSS;microsecond;price;size

El conversor procesa por chunks, conserva ``source_row`` como indice 0-based de la
linea original, separa L2 y L1, escribe Zstandard de forma atomica y publica un
manifiesto por CSV con hashes, conteos, reloj y procedencia Git.

Ejemplo GC:

    python tools/convert_l2_to_parquet.py \
      --input "E:/EdgeLab/data/l2_raw/GC 08-26/2026-06-09" \
      --output-dir "E:/EdgeLab/data/l2_parquet/GC 08-26" \
      --instrument "GC 08-26" \
      --tick-size 0.1

Esto es conversion de formato target-free. No calcula retornos, P&L, MAE/MFE ni
ninguna variable de respuesta.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reusa la conversion temporal cuya independencia pandas 2/3 ya esta cubierta por tests.
from edgelab.data.l2 import _a_microsegundos  # noqa: E402

SCRIPT_VERSION = "2.0.0"
CLOCK_SEMANTICS = "NT8_WALL_CLOCK_INTERPRETED_AS_UTC_REFERENCE_UNRESOLVED"
CSV_COLUMNS = list(range(9))

L2_SCHEMA = pa.schema(
    [
        ("side", pa.int8()),
        ("operation", pa.int8()),
        ("level", pa.int16()),
        ("price", pa.float64()),
        ("size", pa.int64()),
        ("source_row", pa.int64()),
        ("ts_us", pa.int64()),
        ("price_tick", pa.int64()),
    ],
    metadata={
        b"edgelab_schema": b"nt8_l2_depth_v2",
        b"ordering": b"source_row_from_mixed_original_csv",
        b"clock": CLOCK_SEMANTICS.encode("ascii"),
    },
)

L1_SCHEMA = pa.schema(
    [
        ("side", pa.int8()),
        ("price", pa.float64()),
        ("size", pa.int64()),
        ("source_row", pa.int64()),
        ("ts_us", pa.int64()),
        ("price_tick", pa.int64()),
    ],
    metadata={
        b"edgelab_schema": b"nt8_l1_quotes_trades_v2",
        b"side_codes": b"0=ASK,1=BID,2=LAST,5=DAILY_VOLUME",
        b"ordering": b"source_row_from_mixed_original_csv",
        b"clock": CLOCK_SEMANTICS.encode("ascii"),
    },
)


def sha256_file(path: Path, block_size: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(block_size), b""):
            h.update(block)
    return h.hexdigest()


def _git_output(*args: str) -> str | None:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def git_state() -> dict[str, Any]:
    head = _git_output("rev-parse", "HEAD")
    status = _git_output("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "head": head,
        "dirty": None if status is None else bool(status),
        "status_line_count": None if status is None else len(status.splitlines()),
    }


def _integer_series(series: pd.Series, label: str, dtype: np.dtype[Any]) -> pd.Series:
    values = pd.to_numeric(series, errors="raise")
    arr = values.to_numpy(dtype=np.float64)
    if not np.isfinite(arr).all():
        raise ValueError(f"{label}: contiene NaN o infinito")
    rounded = np.rint(arr)
    if not np.array_equal(arr, rounded):
        example = arr[np.flatnonzero(arr != rounded)[0]]
        raise ValueError(f"{label}: se esperaba entero; ejemplo={example!r}")
    info = np.iinfo(dtype)
    if len(rounded) and (rounded.min() < info.min or rounded.max() > info.max):
        raise ValueError(f"{label}: fuera del rango {dtype}")
    return pd.Series(rounded.astype(dtype), index=series.index)


def _float_series(series: pd.Series, label: str) -> pd.Series:
    values = pd.to_numeric(series, errors="raise").astype(np.float64)
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(f"{label}: contiene NaN o infinito")
    return values


def _price_ticks(
    prices: pd.Series,
    tick_size: float,
    *,
    allow_off_grid: bool,
    label: str,
) -> tuple[pd.Series, int, float]:
    arr = prices.to_numpy(dtype=np.float64)
    ticks_float = np.rint(arr / tick_size)
    residual = np.abs(arr - ticks_float * tick_size)
    tolerance = max(1e-9, abs(tick_size) * 1e-8)
    bad = residual > tolerance
    n_bad = int(np.count_nonzero(bad))
    max_residual = float(residual.max()) if len(residual) else 0.0
    if n_bad and not allow_off_grid:
        i = int(np.flatnonzero(bad)[0])
        raise ValueError(
            f"{label}: {n_bad} precio(s) fuera de tick_size={tick_size}; "
            f"ejemplo price={arr[i]!r}, residual={residual[i]:.12g}. "
            "No se redondeo. Use --allow-off-grid solo para diagnostico."
        )
    return pd.Series(ticks_float.astype(np.int64), index=prices.index), n_bad, max_residual


def _parse_chunk(
    raw: pd.DataFrame,
    *,
    source_row_start: int,
    tick_size: float,
    allow_off_grid: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], np.ndarray]:
    raw = raw.reset_index(drop=True)
    raw["source_row"] = np.arange(
        source_row_start, source_row_start + len(raw), dtype=np.int64
    )

    kinds = raw[0].astype(str).str.strip().str.lstrip("\ufeff")
    unknown = ~kinds.isin(["L1", "L2"])
    if unknown.any():
        rows = raw.loc[unknown, "source_row"].head(10).astype(int).tolist()
        values = kinds[unknown].head(10).tolist()
        raise ValueError(f"record_type desconocido/vacio en source_row={rows}: {values}")
    raw[0] = kinds

    usec = _integer_series(raw[3], "microsecond", np.dtype(np.int32))
    if ((usec < 0) | (usec > 999_999)).any():
        raise ValueError("microsecond fuera de [0, 999999]")
    ts_text = raw[2].astype(str).str.strip()
    if (~ts_text.str.fullmatch(r"\d{14}")).any():
        rows = raw.loc[~ts_text.str.fullmatch(r"\d{14}"), "source_row"].head(10).tolist()
        raise ValueError(f"timestamp no cumple YYYYmmddHHMMSS en source_row={rows}")
    ts_us = _a_microsegundos(ts_text, usec)
    raw["ts_us"] = ts_us

    # L2: 0=ASK, 1=BID; operation: 0=ADD, 1=UPDATE, 2=REMOVE.
    l2 = raw.loc[raw[0] == "L2", [1, 4, 5, 7, 8, "source_row", "ts_us"]].copy()
    l2.columns = ["side", "operation", "level", "price", "size", "source_row", "ts_us"]
    l2.reset_index(drop=True, inplace=True)
    l2["side"] = _integer_series(l2["side"], "L2.side", np.dtype(np.int8))
    l2["operation"] = _integer_series(
        l2["operation"], "L2.operation", np.dtype(np.int8)
    )
    l2["level"] = _integer_series(l2["level"], "L2.level", np.dtype(np.int16))
    l2["price"] = _float_series(l2["price"], "L2.price")
    l2["size"] = _integer_series(l2["size"], "L2.size", np.dtype(np.int64))
    if not set(l2["side"].unique()).issubset({0, 1}):
        raise ValueError(f"L2.side fuera de {{0,1}}: {sorted(l2['side'].unique())}")
    if not set(l2["operation"].unique()).issubset({0, 1, 2}):
        raise ValueError(
            f"L2.operation fuera de {{0,1,2}}: {sorted(l2['operation'].unique())}"
        )
    if (l2["level"] < 0).any() or (l2["size"] < 0).any() or (l2["price"] <= 0).any():
        raise ValueError("L2 contiene level/size negativo o price no positivo")
    l2_ticks, l2_off_grid, l2_max_residual = _price_ticks(
        l2["price"], tick_size, allow_off_grid=allow_off_grid, label="L2.price"
    )
    l2["price_tick"] = l2_ticks
    l2 = l2[[field.name for field in L2_SCHEMA]]

    # L1: 0=ASK, 1=BID, 2=LAST, 5=DAILY_VOLUME.
    l1 = raw.loc[raw[0] == "L1", [1, 4, 5, "source_row", "ts_us"]].copy()
    l1.columns = ["side", "price", "size", "source_row", "ts_us"]
    l1.reset_index(drop=True, inplace=True)
    l1["side"] = _integer_series(l1["side"], "L1.side", np.dtype(np.int8))
    l1["price"] = _float_series(l1["price"], "L1.price")
    l1["size"] = _integer_series(l1["size"], "L1.size", np.dtype(np.int64))
    if not set(l1["side"].unique()).issubset({0, 1, 2, 5}):
        raise ValueError(f"L1.side fuera de {{0,1,2,5}}: {sorted(l1['side'].unique())}")
    if (l1["size"] < 0).any():
        raise ValueError("L1 contiene size negativo")
    bad_price = ((l1["side"] == 5) & (l1["price"] != 0)) | (
        (l1["side"] != 5) & (l1["price"] <= 0)
    )
    if bad_price.any():
        raise ValueError("L1 price invalido para quote/trade o DAILY_VOLUME")
    l1_ticks, l1_off_grid, l1_max_residual = _price_ticks(
        l1["price"], tick_size, allow_off_grid=allow_off_grid, label="L1.price"
    )
    l1["price_tick"] = l1_ticks
    l1 = l1[[field.name for field in L1_SCHEMA]]

    stats = {
        "raw_rows": len(raw),
        "l2_rows": len(l2),
        "l1_rows": len(l1),
        "off_grid_rows": l2_off_grid + l1_off_grid,
        "max_tick_residual": max(l2_max_residual, l1_max_residual),
    }
    return l2, l1, stats, ts_us


def _parquet_rows(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def _write_json_staged(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def convert_one_file(
    csv_path: str | Path,
    out_dir: str | Path,
    *,
    instrument: str,
    tick_size: float,
    chunk_rows: int = 250_000,
    overwrite: bool = False,
    allow_off_grid: bool = False,
    allow_time_inversions: bool = False,
    allow_dirty: bool = False,
) -> dict[str, Any]:
    """Convierte un CSV y devuelve el manifiesto materializado."""
    csv_path = Path(csv_path).resolve()
    out_dir = Path(out_dir).resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)
    if not instrument.strip():
        raise ValueError("instrument no puede estar vacio")
    if not np.isfinite(tick_size) or tick_size <= 0:
        raise ValueError("tick_size debe ser finito y positivo")
    if chunk_rows < 1:
        raise ValueError("chunk_rows debe ser >= 1")

    start_git = git_state()
    if start_git["head"] is None:
        raise RuntimeError("No se pudo resolver el HEAD del repo")
    if start_git["dirty"] and not allow_dirty:
        raise RuntimeError(
            "El repo esta dirty. Commit/stash o use --allow-dirty; el manifiesto lo declarara."
        )

    l2_dir = out_dir / "l2_depth"
    l1_dir = out_dir / "l1_quotes"
    manifest_dir = out_dir / "manifests"
    for directory in (l2_dir, l1_dir, manifest_dir):
        directory.mkdir(parents=True, exist_ok=True)

    stem = csv_path.stem
    final_l2 = l2_dir / f"{stem}.parquet"
    final_l1 = l1_dir / f"{stem}.parquet"
    final_manifest = manifest_dir / f"{stem}.manifest.json"
    finals = (final_l2, final_l1, final_manifest)
    existing = [str(path) for path in finals if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Ya existen outputs; no se sobreescriben sin --overwrite: " + ", ".join(existing)
        )

    token = f"{os.getpid()}.{time.time_ns()}"
    tmp_l2 = final_l2.with_name(final_l2.name + f".{token}.part")
    tmp_l1 = final_l1.with_name(final_l1.name + f".{token}.part")
    tmp_manifest = final_manifest.with_name(final_manifest.name + f".{token}.part")
    temporaries = (tmp_l2, tmp_l1, tmp_manifest)

    source_bytes = csv_path.stat().st_size
    source_sha = sha256_file(csv_path)
    started = time.perf_counter()
    l2_writer: pq.ParquetWriter | None = None
    l1_writer: pq.ParquetWriter | None = None
    counters: dict[str, Any] = {
        "raw_rows": 0,
        "l2_rows": 0,
        "l1_rows": 0,
        "off_grid_rows": 0,
        "max_tick_residual": 0.0,
        "timestamp_inversions": 0,
        "first_ts_us": None,
        "last_ts_us": None,
        "min_ts_us": None,
        "max_ts_us": None,
    }
    previous_ts: int | None = None

    try:
        l2_writer = pq.ParquetWriter(
            tmp_l2, L2_SCHEMA, compression="zstd", compression_level=7
        )
        l1_writer = pq.ParquetWriter(
            tmp_l1, L1_SCHEMA, compression="zstd", compression_level=7
        )

        reader = pd.read_csv(
            csv_path,
            sep=";",
            header=None,
            names=CSV_COLUMNS,
            dtype=str,
            chunksize=chunk_rows,
            low_memory=False,
            keep_default_na=False,
            na_filter=False,
            skip_blank_lines=False,
            on_bad_lines="error",
        )
        for raw in reader:
            l2, l1, stats, ts_us = _parse_chunk(
                raw,
                source_row_start=int(counters["raw_rows"]),
                tick_size=tick_size,
                allow_off_grid=allow_off_grid,
            )
            if len(ts_us):
                inversions = int(np.count_nonzero(np.diff(ts_us) < 0))
                if previous_ts is not None and int(ts_us[0]) < previous_ts:
                    inversions += 1
                counters["timestamp_inversions"] += inversions
                if inversions and not allow_time_inversions:
                    raise ValueError(
                        f"Se detectaron {inversions} inversiones temporales en el chunk. "
                        "No se reordeno. Use --allow-time-inversions solo para diagnostico."
                    )
                if counters["first_ts_us"] is None:
                    counters["first_ts_us"] = int(ts_us[0])
                counters["last_ts_us"] = int(ts_us[-1])
                chunk_min, chunk_max = int(ts_us.min()), int(ts_us.max())
                counters["min_ts_us"] = (
                    chunk_min
                    if counters["min_ts_us"] is None
                    else min(int(counters["min_ts_us"]), chunk_min)
                )
                counters["max_ts_us"] = (
                    chunk_max
                    if counters["max_ts_us"] is None
                    else max(int(counters["max_ts_us"]), chunk_max)
                )
                previous_ts = int(ts_us[-1])

            if len(l2):
                l2_writer.write_table(
                    pa.Table.from_pandas(l2, schema=L2_SCHEMA, preserve_index=False, safe=True)
                )
            if len(l1):
                l1_writer.write_table(
                    pa.Table.from_pandas(l1, schema=L1_SCHEMA, preserve_index=False, safe=True)
                )
            for key in ("raw_rows", "l2_rows", "l1_rows", "off_grid_rows"):
                counters[key] += int(stats[key])
            counters["max_tick_residual"] = max(
                float(counters["max_tick_residual"]), float(stats["max_tick_residual"])
            )

        l2_writer.close()
        l2_writer = None
        l1_writer.close()
        l1_writer = None

        if counters["raw_rows"] == 0:
            raise ValueError("CSV vacio")
        if counters["l2_rows"] == 0 or counters["l1_rows"] == 0:
            raise ValueError(
                f"Se requieren ambos flujos: L2={counters['l2_rows']}, L1={counters['l1_rows']}"
            )
        if counters["l2_rows"] + counters["l1_rows"] != counters["raw_rows"]:
            raise AssertionError("L1 + L2 no cubre exactamente todas las filas")
        if _parquet_rows(tmp_l2) != counters["l2_rows"]:
            raise AssertionError("row count L2 del parquet no coincide")
        if _parquet_rows(tmp_l1) != counters["l1_rows"]:
            raise AssertionError("row count L1 del parquet no coincide")

        end_git = git_state()
        if end_git["head"] != start_git["head"]:
            raise RuntimeError(
                f"HEAD cambio durante la conversion: {start_git['head']} -> {end_git['head']}"
            )
        if end_git["dirty"] and not allow_dirty:
            raise RuntimeError("El arbol quedo dirty durante la conversion")

        l2_sha = sha256_file(tmp_l2)
        l1_sha = sha256_file(tmp_l1)
        elapsed = time.perf_counter() - started
        manifest: dict[str, Any] = {
            "schema": "edgelab_nt8_l2_parquet_manifest_v2",
            "status": "COMPLETE_FORMAT_CONVERSION",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "script": "tools/convert_l2_to_parquet.py",
            "script_version": SCRIPT_VERSION,
            "instrument": instrument,
            "session_name": stem,
            "source": {
                "path": str(csv_path),
                "name": csv_path.name,
                "bytes": source_bytes,
                "sha256": source_sha,
                "rows": counters["raw_rows"],
            },
            "conversion": {
                "tick_size": tick_size,
                "chunk_rows": chunk_rows,
                "compression": "zstd",
                "compression_level": 7,
                "preserved_original_order": True,
                "source_row_base": 0,
                "off_grid_rows": counters["off_grid_rows"],
                "max_tick_residual": counters["max_tick_residual"],
                "allow_off_grid": allow_off_grid,
                "timestamp_inversions": counters["timestamp_inversions"],
                "allow_time_inversions": allow_time_inversions,
                "elapsed_seconds": round(elapsed, 3),
            },
            "clock": {
                "column": "ts_us",
                "unit": "microseconds",
                "semantics": CLOCK_SEMANTICS,
                "reference_resolved": False,
                "first_ts_us": counters["first_ts_us"],
                "last_ts_us": counters["last_ts_us"],
                "min_ts_us": counters["min_ts_us"],
                "max_ts_us": counters["max_ts_us"],
            },
            "outputs": {
                "l2_depth": {
                    "path": str(final_l2.relative_to(out_dir)),
                    "rows": counters["l2_rows"],
                    "bytes": tmp_l2.stat().st_size,
                    "sha256": l2_sha,
                },
                "l1_quotes": {
                    "path": str(final_l1.relative_to(out_dir)),
                    "rows": counters["l1_rows"],
                    "bytes": tmp_l1.stat().st_size,
                    "sha256": l1_sha,
                },
            },
            "provenance": {
                "head_start": start_git["head"],
                "head_end": end_git["head"],
                "dirty_start": start_git["dirty"],
                "dirty_end": end_git["dirty"],
                "allow_dirty": allow_dirty,
                "python": platform.python_version(),
                "pandas": pd.__version__,
                "pyarrow": pa.__version__,
            },
            "scope": {
                "format_conversion_only": True,
                "outcomes_computed": False,
                "returns_computed": False,
                "mae_mfe_computed": False,
            },
        }
        _write_json_staged(tmp_manifest, manifest)

        # El manifiesto se publica ultimo: su presencia es el marcador de sesion completa.
        os.replace(tmp_l2, final_l2)
        os.replace(tmp_l1, final_l1)
        os.replace(tmp_manifest, final_manifest)
        return manifest
    except Exception:
        for writer in (l2_writer, l1_writer):
            if writer is not None:
                with contextlib.suppress(Exception):
                    writer.close()
        for temp in temporaries:
            with contextlib.suppress(FileNotFoundError):
                temp.unlink()
        raise


def discover_csv_files(input_path: Path, pattern: str, recursive: bool) -> list[Path]:
    input_path = input_path.resolve()
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(input_path)
    files = sorted(input_path.rglob(pattern) if recursive else input_path.glob(pattern))
    files = [path.resolve() for path in files if path.is_file()]
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos {pattern!r} en {input_path}")
    stems = [path.stem for path in files]
    duplicates = sorted({stem for stem in stems if stems.count(stem) > 1})
    if duplicates:
        raise ValueError(f"Stems duplicados producirian colisiones de output: {duplicates}")
    return files


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convertir CSV L1/L2 de NT8 a Parquet, por chunks y fail-closed"
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="CSV individual o directorio")
    source.add_argument(
        "--input-dir",
        help="Alias compatible con el script anterior; directorio de CSV",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--instrument", required=True, help='Ejemplo: "GC 08-26"')
    parser.add_argument("--tick-size", required=True, type=float, help="GC=0.1")
    parser.add_argument("--pattern", default="*.csv")
    parser.add_argument("--recursive", action="store_true")
    parser.add_argument("--chunk-rows", type=int, default=250_000)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--allow-off-grid",
        action="store_true",
        help="Diagnostico: preserva price y redondea solo price_tick; queda en manifest",
    )
    parser.add_argument(
        "--allow-time-inversions",
        action="store_true",
        help="Diagnostico: no ordena; conserva y cuenta inversiones",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Permite arbol dirty, declarado en el manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = Path(args.input if args.input is not None else args.input_dir)
    try:
        files = discover_csv_files(input_path, args.pattern, args.recursive)
        print(f"Conversor NT8 L2 v{SCRIPT_VERSION}: {len(files)} archivo(s)")
        for index, csv_path in enumerate(files, 1):
            size_mb = csv_path.stat().st_size / (1024 * 1024)
            print(f"[{index}/{len(files)}] {csv_path.name} ({size_mb:.1f} MiB)")
            manifest = convert_one_file(
                csv_path,
                args.output_dir,
                instrument=args.instrument,
                tick_size=args.tick_size,
                chunk_rows=args.chunk_rows,
                overwrite=args.overwrite,
                allow_off_grid=args.allow_off_grid,
                allow_time_inversions=args.allow_time_inversions,
                allow_dirty=args.allow_dirty,
            )
            print(
                "  OK: rows=%s L2=%s L1=%s sha=%s..."
                % (
                    manifest["source"]["rows"],
                    manifest["outputs"]["l2_depth"]["rows"],
                    manifest["outputs"]["l1_quotes"]["rows"],
                    manifest["source"]["sha256"][:16],
                )
            )
        print(f"Completado. Outputs en {Path(args.output_dir).resolve()}")
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
