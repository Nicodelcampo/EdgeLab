#!/usr/bin/env python3
"""Ensambla la release a partir de las partes por activo: manifiesto global, metadatos y README para agentes.

Uso: python tools/finalize_release.py --release D:/.../release_20261014 --census D:/.../census [--repo E:/EdgeLab-data]
No toca los Parquet de ticks. Escribe release_manifest.json al final (con SHA-256 de cada archivo de metadatos).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edgelab.data.liquid_release.release_reader import SCHEMA, sha256_file  # noqa: E402

NORTH_STAR_SHA = "ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8"
SPECS = {  # tamaño de tick y valor por tick (USD) de las especificaciones CME; el tick se verificó contra la grilla de los datos
    "ES": (0.25, 12.50), "NQ": (0.25, 5.00), "MES": (0.25, 1.25), "MNQ": (0.25, 0.50), "YM": (1.0, 5.00), "MYM": (1.0, 0.50),
    "RTY": (0.1, 5.00), "GC": (0.1, 10.00), "MGC": (0.1, 1.00), "ZB": (0.03125, 31.25), "6E": (0.00005, 6.25),
    "6B": (0.0001, 6.25), "6J": (0.0000005, 6.25), "MBT": (5.0, 0.50)}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True).stdout.strip()


def session_rows(path):
    pf = pq.ParquetFile(path)
    ci = pf.schema_arrow.names.index("trade_date")
    out = {}
    for g in range(pf.metadata.num_row_groups):
        rg = pf.metadata.row_group(g)
        td = int(rg.column(ci).statistics.min)
        out[td] = out.get(td, 0) + rg.num_rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--release-id", default="liquid_release_20261014")
    a = ap.parse_args()
    root, cen = Path(a.release), Path(a.census)
    meta = root / "metadata"
    parts = meta / "parts"
    assets, policies, decs, runs, srcs = {}, {}, [], [], []
    for f in sorted(parts.glob("*_asset.json")):
        inst = f.name.split("_")[0]
        d = json.loads(f.read_text(encoding="utf-8"))
        assets[inst], policies[inst] = d["info"], d["policy"]
        decs.append(pd.read_parquet(parts / f"{inst}_decisions.parquet"))
        runs.append(pd.read_parquet(parts / f"{inst}_runs.parquet"))
        srcs.append(pd.read_parquet(parts / f"{inst}_sources.parquet"))
    dec, run, src = pd.concat(decs, ignore_index=True), pd.concat(runs, ignore_index=True), pd.concat(srcs, ignore_index=True)
    dec.to_parquet(meta / "selection_decisions.parquet", index=False)
    run.to_parquet(meta / "contract_runs.parquet", index=False)
    src.to_parquet(meta / "source_manifest.parquet", index=False)
    (meta / "liquidity_policy.json").write_text(json.dumps(policies, indent=1), encoding="utf-8")
    (meta / "instrument_specs.json").write_text(json.dumps({k: dict(tick_size=v[0], tick_value_usd=v[1]) for k, v in SPECS.items() if k in assets}, indent=1), encoding="utf-8")
    # índice de sesiones: una fila por sesión del calendario del activo, con su estado y las filas escritas
    rows_by = {i: session_rows(root / assets[i]["file"]) for i in assets}
    chosen = pd.read_parquet(cen / "chosen_sources.parquet")
    ch = chosen.set_index(["contract", "trade_date"])
    regime = {(r.instrument, r.contract): r.regime_id for r in run.itertuples()}
    idx = dec.copy()
    idx["rows_written"] = [rows_by[i].get(d, 0) if s == "SELECTED" else 0 for i, d, s in zip(idx["instrument"], idx["trade_date"], idx["status"])]
    idx["regime_id"] = [regime.get((i, c)) if s == "SELECTED" else None for i, c, s in zip(idx["instrument"], idx["contract"], idx["status"])]
    idx["source_group"] = [ch["group"].get((c, d)) if s == "SELECTED" else None for c, d, s in zip(idx["contract"], idx["trade_date"], idx["status"])]
    idx["assurance"] = [ch["assurance"].get((c, d)) if s == "SELECTED" else None for c, d, s in zip(idx["contract"], idx["trade_date"], idx["status"])]
    idx.to_parquet(meta / "session_index.parquet", index=False)
    idx[idx["status"] != "SELECTED"].drop(columns=["candidates"]).to_parquet(meta / "excluded_sessions.parquet", index=False)
    # evidencia copiada del censo (sin precios)
    for name in ("dup_blocks.parquet",):
        if (cen / name).exists():
            pd.read_parquet(cen / name).to_parquet(meta / name, index=False)
    pd.read_csv(cen / "tz_groups.csv").to_csv(meta / "tz_verdicts.csv", index=False)
    pd.read_parquet(cen / "calendar_derived.parquet").to_parquet(meta / "calendar_derived.parquet", index=False)
    if (cen / "source_conflicts.parquet").exists():
        pd.read_parquet(cen / "source_conflicts.parquet")[["contract", "trade_date", "group", "kind", "n_reg", "vol_reg", "n_min_reg", "max_gap_reg_ns", "chosen_group"]] \
            .to_parquet(meta / "source_conflicts.parquet", index=False)
    commit, dirty = git(a.repo, "rev-parse", "HEAD"), bool(git(a.repo, "status", "--porcelain"))
    summary = dict(assets={i: dict(rows=v["rows"], sessions=v["sessions"], first=v["first_trade_date"], last=v["last_trade_date"], gb=round(v["bytes"] / 1e9, 3)) for i, v in assets.items()},
                   decisions=dec["status"].value_counts().to_dict(),
                   assurance=idx.loc[idx.status == "SELECTED", "assurance"].value_counts().to_dict())
    (meta / "quality_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    meta_files = {}
    for f in sorted(meta.glob("*")):
        if f.is_file():
            meta_files[f"metadata/{f.name}"] = dict(sha256=sha256_file(f), bytes=f.stat().st_size)
    readme = root / "README_AGENTES.md"
    if readme.exists():
        meta_files["README_AGENTES.md"] = dict(sha256=sha256_file(readme), bytes=readme.stat().st_size)
    man = dict(schema=SCHEMA, release_id=a.release_id, generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               status="CANDIDATE_NOT_RESEARCH_APPROVED", research_allowed=False, promotion_allowed=False,
               privacy="PRIVATE_ONLY_NO_REDISTRIBUTION", north_star_sha256=NORTH_STAR_SHA,
               holdout=dict(first_trade_date=20261001, first_timestamp_utc="2026-09-30T22:00:00Z", payload_included=False),
               code=dict(repo_commit=commit, tree_dirty_at_finalize=dirty), liquidity_policy_approved=False,
               assets=assets, metadata_files=meta_files)
    (root / "release_manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
