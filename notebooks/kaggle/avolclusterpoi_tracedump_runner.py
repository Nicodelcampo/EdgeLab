#!/usr/bin/env python3
"""Kaggle entrypoint: run() with debug_trace=True on real NQ 06-26, dump
per-block diagnostics for creation blocks only (task 2, auditor order).

Mirrors tools/paridad_oraculo.py's data loading exactly (full parquet, no
window trimming -- that happens downstream in match_zones) so the resulting
zone ids/creation contexts line up with the already-run parity gate report.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
EXPECTED_COMMIT = "8bf9fd02861666ec3dc58928b2043223466d5ffe"
REPO_DIR = Path("/kaggle/working/EdgeLab")
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", "tracedump", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

sys.path.insert(0, str(REPO_DIR))
from edgelab.bridge import bars as bars_mod, ticks as ticks_mod  # noqa: E402
from edgelab.bridge.indicators import avolclusterpoi  # noqa: E402

parquet_hits = list(Path(DATA_DIR).rglob("NQ_06-26_ticks.parquet"))
tk = ticks_mod.load_canonical_parquet(str(parquet_hits[0]))
print("n_ticks=", len(tk.ts_ns), flush=True)

bars = bars_mod.build_tick_bars(tk, 120)
fps = bars_mod.build_footprints(tk, bars)
print("n_bars=", len(bars.close_t), flush=True)

res = avolclusterpoi.run(tk, bars, fps, debug_trace=True)
print("n_zones=", len(res["zones"]), flush=True)
print("n_blocks_total=", len(res["block_trace"]), flush=True)

creation_blocks = [bt for bt in res["block_trace"] if bt["zone_ids"]]
print("n_creation_blocks=", len(creation_blocks), flush=True)

out_dir = Path("/kaggle/working/avolclusterpoi_tracedump")
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "zones.json").write_text(json.dumps(res["zones"], indent=2), encoding="utf-8")
(out_dir / "creation_blocks.json").write_text(json.dumps(creation_blocks, indent=2), encoding="utf-8")

import shutil
import zipfile

for f in out_dir.glob("*.json"):
    shutil.copy2(f, Path("/kaggle/working") / f.name)
archive = Path("/kaggle/working/avolclusterpoi_tracedump.zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in out_dir.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to("/kaggle/working"))
print("artifact=", archive, flush=True)
