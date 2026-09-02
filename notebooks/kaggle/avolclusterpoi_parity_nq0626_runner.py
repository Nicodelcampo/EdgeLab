#!/usr/bin/env python3
"""Kaggle entrypoint: aVolClusterPOI parity gate, NQ 06-26, 120-tick.

Single call to tools/paridad_oraculo.py against the NT8 oracle exported
2026-09-01 (window 2026-04-07..2026-06-12, CME US Index Futures ETH,
confirmed via Instrument Properties in the NT8 install itself -- no
"Use instrument settings" ambiguity left unresolved).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
BRANCH = "research/avolcluster-nq-parity-oracle-20260901"
EXPECTED_COMMIT = "e87ff024660bbfe38efd88ea0b3f89e18b1008ca"
REPO_DIR = Path("/kaggle/working/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/avolcluster_parity_output")
DATA_DIR = "/kaggle/input/datasets/nicolasbuttaro/edgelab-ticks-nq-preholdout"
ORACLE_PATH = "/kaggle/input/datasets/nicolasbuttaro/edgelab-avolcluster-nq-oracle/avolcluster_v05_NQ0626_120t_20260407_20260612.csv"

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", BRANCH, "--depth", "200"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "-B", BRANCH, f"origin/{BRANCH}"], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
print("repo_commit=", actual, flush=True)

parquet_hits = list(Path(DATA_DIR).rglob("NQ_06-26_ticks.parquet"))
if not parquet_hits:
    raise SystemExit(f"NQ 06-26 parquet not found under {DATA_DIR}")
parquet_path = parquet_hits[0]
print("parquet=", parquet_path, flush=True)

oracle_hits = list(Path("/kaggle/input/datasets/nicolasbuttaro/edgelab-avolcluster-nq-oracle").rglob("*v2.csv"))
if not oracle_hits:
    oracle_hits = list(Path("/kaggle/input/datasets/nicolasbuttaro/edgelab-avolcluster-nq-oracle").rglob("*20260407_20260612*.csv"))
if not oracle_hits:
    raise SystemExit("Oracle CSV not found in dataset")
oracle_path = oracle_hits[0]
print("oracle=", oracle_path, flush=True)

bp_hits = list(Path("/kaggle/input/datasets/nicolasbuttaro/edgelab-avolcluster-nq-oracle").rglob("*BARPROFILE*.csv"))
if bp_hits:
    print("barprofile=", bp_hits[0], flush=True)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
out_json = OUTPUT_DIR / "paridad_avolclusterpoi_nq0626.json"

cmd = [
    sys.executable, str(REPO_DIR / "tools/paridad_oraculo.py"),
    "--indicador", "avolclusterpoi",
    "--oraculo", str(oracle_path),
    "--parquet", str(parquet_path),
    "--chart-tz", "America/Argentina/Buenos_Aires",
    "--barras", "tick:120",
    "--sesiones-warmup", "20",
    "--out", str(out_json),
]
if bp_hits:
    cmd.extend(["--barprofile", str(bp_hits[0])])
print("+", " ".join(cmd), flush=True)
proc = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
print(proc.stdout, flush=True)
if proc.returncode != 0:
    print(proc.stderr, flush=True)
    raise SystemExit(f"paridad_oraculo.py failed with code {proc.returncode}")

print("=== REPORT ===", flush=True)
print(out_json.read_text(encoding="utf-8"), flush=True)

import shutil
import zipfile

shutil.copy2(out_json, "/kaggle/working/paridad_avolclusterpoi_nq0626.json")
archive = Path("/kaggle/working/avolcluster_parity_output.zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to("/kaggle/working"))
print("artifact=", archive, flush=True)
