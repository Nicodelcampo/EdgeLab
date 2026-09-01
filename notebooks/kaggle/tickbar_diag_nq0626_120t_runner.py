#!/usr/bin/env python3
"""Kaggle entrypoint: TICKBAR-001 v2 classifier, NQ 06-26, 120-tick.

Measures the real FOOTPRINT_MISMATCH-equivalent rate at 120 ticks (H2 bar-cut
identity + H3 attribution), disambiguating whether the aVolClusterPOI parity
FAIL is a translation bug in the Python adapter or the already-declared
TICKBAR-001 defect propagating through the footprint-based cell aggregation.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
BRANCH = "research/avolcluster-nq-parity-oracle-20260901"
EXPECTED_COMMIT = "5e2d86a56a93af8d91bc3bc591b5fde11905bfdb"
REPO_DIR = Path("/kaggle/working/EdgeLab")
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
LEDGER_PATH = "/kaggle/input/datasets/nicolasbuttaro/edgelab-tickbar-diag-nq0626/tickbar_diag_NQ0626__Tick120.csv"

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", BRANCH, EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EXPECTED_COMMIT")
print("repo_commit=", actual, flush=True)

parquet_hits = list(Path(DATA_DIR).rglob("NQ_06-26_ticks.parquet"))
if not parquet_hits:
    raise SystemExit(f"NQ 06-26 parquet not found under {DATA_DIR}")
parquet_path = parquet_hits[0]
print("parquet=", parquet_path, flush=True)

cmd = [
    sys.executable, str(REPO_DIR / "tools/tickbar_diag_v2.py"),
    LEDGER_PATH,
    "--parquet", str(parquet_path),
    "--contract", "NQ 06-26",
    "--tick-n", "120",
    "--tz-shift-hours", "3",
]
print("+", " ".join(cmd), flush=True)
proc = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
print("=== STDOUT ===", flush=True)
print(proc.stdout, flush=True)
print("=== STDERR ===", flush=True)
print(proc.stderr, flush=True)
if proc.returncode != 0:
    raise SystemExit(f"tickbar_diag_v2.py failed with code {proc.returncode}")

Path("/kaggle/working/tickbar_diag_nq0626_120t_stdout.txt").write_text(proc.stdout, encoding="utf-8")
print("artifact=/kaggle/working/tickbar_diag_nq0626_120t_stdout.txt", flush=True)
