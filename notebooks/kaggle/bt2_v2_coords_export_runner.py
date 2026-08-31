#!/usr/bin/env python3
"""Kaggle entrypoint: export raw BigTrap2 V2 coordinates for tick_25_IMB30_VOL10.

Single-process run of tools/export_bt2_v2_coords_parquet.py against the same
frozen, hash-bound spec used by the V2 sweep (this re-exports one already-
authorized cell's raw output, not a new campaign). Fail-closed if the
recomputed aggregate disagrees with the already-frozen V2 result.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
BRANCH = "research/bt2a-nq-gate1-runner-impl-v1-20260831"
EXPECTED_COMMIT = "88043c6e14cf4107f9e3454b36ab246e8edfc5a8"  # adds source_row/direction to the export schema
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
SPEC = "specs/bigtrap2_nq_tickframes_sweep_v2.draft.json"
AUTH_TOKEN = "AUTHORIZE_RUN_BT2_NQ_TICKFRAMES_SWEEP_V2"
REPO_DIR = Path("/kaggle/working/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/bt2_v2_coords_output")
FROZEN_RESULT = REPO_DIR / "docs/research/bigtrap2_nq_tickframes_sweep_v2_result.json"
OUTPUT_PARQUET = OUTPUT_DIR / "tick_25_IMB30_VOL10_coords.parquet"

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", BRANCH, EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
branch_now = subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO_DIR, text=True).strip()
print("repo_commit=", actual, " branch=", branch_now, flush=True)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=== exporting BigTrap2 V2 coordinates (tick_25_IMB30_VOL10) ===", flush=True)
proc = subprocess.run(
    [sys.executable, "tools/export_bt2_v2_coords_parquet.py",
     "--spec", SPEC, "--data-dir", DATA_DIR,
     "--expected-commit", EXPECTED_COMMIT,
     "--execution-token", AUTH_TOKEN,
     "--frozen-result", str(FROZEN_RESULT),
     "--output-parquet", str(OUTPUT_PARQUET)],
    cwd=REPO_DIR, capture_output=True, text=True,
)
print(proc.stdout, flush=True)
if proc.returncode != 0:
    print(proc.stderr, flush=True)
    raise SystemExit("coords export failed")

manifest_path = OUTPUT_PARQUET.with_suffix(".manifest.json")
print("=== MANIFEST ===", flush=True)
print(manifest_path.read_text(encoding="utf-8"), flush=True)

import zipfile

archive = Path("/kaggle/working/bt2_v2_coords_output.zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to("/kaggle/working"))
print("artifact=", archive, flush=True)
