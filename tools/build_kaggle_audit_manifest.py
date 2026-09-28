#!/usr/bin/env python3
r"""Manifiesto auditable, por archivo, para un paquete de dataset de Kaggle con datos L2.

Para cada archivo del paquete: ruta, bytes, sha256, filas/columnas (parquet) o claves de nivel superior (json),
timestamp minimo/maximo (si aplica), sesion y contrato, condicion pre-holdout, commit del builder que lo genero,
y (para los bundles del visor) el sha256 del propio archivo de salida ya queda cubierto por su propia entrada.

**Target-free.** Solo metadatos de forma/procedencia; no lee outcomes ni P&L.

    .venv\Scripts\python tools\build_kaggle_audit_manifest.py --root E:\ruta\al\paquete --out manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HOLDOUT_NS = 1782856800000000000
CUTOFF_DATE = 20260630


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def parquet_stats(path: Path) -> dict:
    import pyarrow.parquet as pq
    f = pq.ParquetFile(path)
    md = f.metadata
    cols = [md.schema.column(i).name for i in range(md.num_columns)]
    ts_col = next((c for c in ("ts_us", "ts_ns", "timestamp") if c in cols), None)
    ts_min = ts_max = None
    if ts_col is not None:
        idx = cols.index(ts_col)
        mins, maxs = [], []
        for g in range(md.num_row_groups):
            st = md.row_group(g).column(idx).statistics
            if st is not None and st.has_min_max:
                mins.append(st.min); maxs.append(st.max)
        if mins:
            ts_min, ts_max = int(min(mins)), int(max(maxs))
    return dict(rows=md.num_rows, columns=cols, ts_us_col=ts_col, ts_us_min=ts_min, ts_us_max=ts_max)


def json_stats(path: Path) -> dict:
    d = json.loads(path.read_text(encoding="utf-8"))
    out = dict(top_level_keys=sorted(d.keys()) if isinstance(d, dict) else None)
    meta = d.get("meta") if isinstance(d, dict) else None
    if meta:
        out.update(instrument=meta.get("instrument"), contract=meta.get("contract"),
                   first_ts=meta.get("first_ts"), last_ts=meta.get("last_ts"),
                   n_candles=meta.get("n_candles"), l2_events=meta.get("l2_events"))
    return out


def session_from_name(path: Path) -> str | None:
    stem = path.stem.replace(".manifest", "")
    digits = "".join(c for c in stem if c.isdigit())
    return digits[-8:] if len(digits) >= 8 else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True, help="carpeta del paquete a manifestar (recursiva)")
    ap.add_argument("--builder-repo", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)

    commit = git_commit(a.builder_repo)
    entries = []
    for p in sorted(a.root.rglob("*")):
        if not p.is_file() or p.name in ("dataset-metadata.json",):
            continue
        rel = p.relative_to(a.root).as_posix()
        entry = dict(path=rel, bytes=p.stat().st_size, sha256=sha256_file(p), builder_commit=commit)
        session = session_from_name(p)
        entry["session"] = session
        if session:
            entry["pre_holdout"] = int(session) < CUTOFF_DATE
        if p.suffix == ".parquet":
            entry.update(parquet_stats(p))
            if entry.get("ts_us_max") is not None:
                entry["pre_holdout"] = entry["ts_us_max"] * 1000 < HOLDOUT_NS
        elif p.suffix == ".json":
            entry.update(json_stats(p))
        entries.append(entry)

    manifest = dict(schema="edgelab_kaggle_audit_manifest_v1", builder_commit=commit,
                    holdout_boundary_ns=HOLDOUT_NS, files=entries, file_count=len(entries),
                    total_bytes=sum(e["bytes"] for e in entries))
    a.out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    bad = [e["path"] for e in entries if e.get("pre_holdout") is False]
    print(json.dumps(dict(files=len(entries), total_bytes=manifest["total_bytes"], post_holdout_files=bad)))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
