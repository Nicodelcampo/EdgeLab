#!/usr/bin/env python3
"""Kaggle entrypoint: aVolClusterPOI parity gate, NQ 06-26, 120-tick."""
import os
import sys
import subprocess
import shutil
import zipfile
import traceback
from pathlib import Path

LOG_FILE = Path("/kaggle/working/execution_log.txt")

def log(msg):
    text = str(msg)
    print(text, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

log("=== STARTING KAGGLE PARITY RUN ===")

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
BRANCH = "research/avolcluster-nq-parity-oracle-20260901"
REPO_DIR = Path("/kaggle/working/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/avolcluster_parity_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

try:
    if not (REPO_DIR / ".git").exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "fetch", "origin", BRANCH, "--depth", "200"], cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "-B", BRANCH, "FETCH_HEAD"], cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    log(f"repo_commit={actual}")

    # Search for files under /kaggle/input
    parquet_hits = list(Path("/kaggle/input").rglob("NQ_06-26_ticks.parquet"))
    if not parquet_hits:
        raise SystemExit("NQ_06-26_ticks.parquet not found under /kaggle/input")
    parquet_path = parquet_hits[0]
    log(f"parquet={parquet_path}")

    oracle_hits = list(Path("/kaggle/input").rglob("*v2.csv"))
    if not oracle_hits:
        oracle_hits = list(Path("/kaggle/input").rglob("*NQ0626_120t_20260407_20260612*.csv"))
    if not oracle_hits:
        raise SystemExit("Oracle CSV not found under /kaggle/input")
    oracle_path = oracle_hits[0]
    log(f"oracle={oracle_path}")

    bp_hits = list(Path("/kaggle/input").rglob("*BARPROFILE*.csv"))
    if bp_hits:
        log(f"barprofile={bp_hits[0]}")
    else:
        log("WARN: No BARPROFILE CSV found")

    diag_hits = list(Path("/kaggle/input").rglob("*DIAG_BLOCKS*.csv"))
    if diag_hits:
        log(f"diag_blocks={diag_hits[0]}")
    else:
        log("WARN: No DIAG_BLOCKS CSV found")

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
    if diag_hits:
        cmd.extend(["--diag-blocks", str(diag_hits[0])])
    log(f"+ {' '.join(cmd)}")

    proc = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, text=True)
    log("=== STDOUT ===")
    log(proc.stdout)
    log("=== STDERR ===")
    log(proc.stderr)
    log(f"returncode={proc.returncode}")

    if out_json.exists():
        log("=== REPORT JSON ===")
        log(out_json.read_text(encoding="utf-8"))
        shutil.copy2(out_json, "/kaggle/working/paridad_avolclusterpoi_nq0626.json")

    archive = Path("/kaggle/working/avolcluster_parity_output.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in OUTPUT_DIR.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to("/kaggle/working"))
    log(f"artifact={archive}")

except Exception as e:
    log(f"FATAL EXCEPTION: {e}")
    log(traceback.format_exc())
