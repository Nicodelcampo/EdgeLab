#!/usr/bin/env python3
"""Kaggle Entrypoint: BT2A NQ Gate 1 (16-cell) Execution.

Implementation authorized under Token 3 (AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1).
Execution authorized under Token 4 (AUTHORIZE_RUN_BT2A_NQ_GATE1_V1).

Incorporates the 3 Kaggle Speed Levers:
1. Parallel execution across contracts with ThreadPoolExecutor (MAX_WORKERS=4 fail-closed).
2. Cached pre-anchor tick features (sessions, minutes, vol, after) per contract.
3. Partial clone (--filter=blob:none --no-checkout) + dynamic robust dataset discovery under /kaggle/input.
"""
from __future__ import annotations

import concurrent.futures
import glob
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
FULL_COMMIT = "cd33a154f0b064d7afbf6f0660773d668868aad4"
TEMP_REPO_DIR = Path("/tmp/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
WORKING_DIR = Path("/kaggle/working")
EXECUTION_TOKEN = "AUTHORIZE_RUN_BT2A_NQ_GATE1_V1"

CONTRACTS = ["NQ 03-26", "NQ 06-26", "NQ 09-25", "NQ 09-26", "NQ 12-25"]
MAX_WORKERS = 4
REPLICATIONS = 1000
SEED = 20260831


def run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kw)


def find_dataset_dir(name_fragment: str) -> Path:
    search_roots = [Path("/kaggle/input"), Path("/kaggle/input/datasets"), Path(".")]
    print(f"Searching for dataset matching '{name_fragment}' in {[str(r) for r in search_roots if r.is_dir()]}", flush=True)
    for root in search_roots:
        if root.is_dir():
            hits = [p for p in root.rglob("*") if p.is_dir() and name_fragment in p.name]
            if hits:
                hits.sort(key=lambda p: len(p.parts))
                print(f"-> found '{name_fragment}' at: {hits[0]}", flush=True)
                return hits[0]
    for root in search_roots:
        if root.is_dir():
            candidate = root / name_fragment
            if candidate.is_dir():
                print(f"-> found '{name_fragment}' at: {candidate}", flush=True)
                return candidate
    raise SystemExit(f"no dataset directory matching '{name_fragment}' found under /kaggle/input")


def find_file(search_dir: Path, stub: str, suffix: str = ".parquet") -> Path:
    hits = [p for p in search_dir.rglob(f"*{suffix}") if stub in p.name]
    if not hits:
        raise SystemExit(f"no file matching '{stub}' with suffix '{suffix}' found under {search_dir}")
    hits.sort(key=lambda p: len(str(p)))
    return hits[0]


def main() -> None:
    t_start = datetime.now(timezone.utc)
    print("=== BT2A NQ GATE 1 (16-CELL) EXECUTION RUNNER ===", flush=True)
    print(f"Started at: {t_start.isoformat()}", flush=True)

    # 1. Partial clone
    if TEMP_REPO_DIR.exists():
        shutil.rmtree(TEMP_REPO_DIR)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(TEMP_REPO_DIR)])
    run(["git", "fetch", "origin", FULL_COMMIT, "--depth", "200"], cwd=TEMP_REPO_DIR)
    run(["git", "checkout", "--detach", FULL_COMMIT], cwd=TEMP_REPO_DIR)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=TEMP_REPO_DIR, text=True).strip()
    print("repo_commit=", actual, flush=True)
    if actual != FULL_COMMIT:
        raise SystemExit(f"checked-out commit differs: {actual} != {FULL_COMMIT}")

    sys.path.insert(0, str(TEMP_REPO_DIR))
    from tools.run_bt2a_nq_gate1_outcomes import run_gate1_16cell_pipeline

    # 2. Locate inputs dynamically
    coords_dir = find_dataset_dir("coordinates")
    ticks_dir = find_dataset_dir("edgelab-ticks-nq-preholdout")
    
    spec_path = TEMP_REPO_DIR / "specs/bt2a_nq_gate1_v1.draft.json"
    event_store_path = TEMP_REPO_DIR / "specs/bt2a_nq_creation_event_store_manifest.json"
    bt2_result_path = TEMP_REPO_DIR / "docs/research/bigtrap2_nq_tickframes_sweep_v2_result.json"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    res = run_gate1_16cell_pipeline(
        spec_path=spec_path,
        event_store_path=event_store_path,
        bt2_result_path=bt2_result_path,
        data_dir=ticks_dir,
        output_dir=OUTPUT_DIR,
        authorization_token=EXECUTION_TOKEN,
        max_workers=MAX_WORKERS,
        replications=REPLICATIONS,
        seed=SEED,
    )

    # Copy results to WORKING_DIR
    for f in OUTPUT_DIR.glob("*.json"):
        shutil.copy2(f, WORKING_DIR / f.name)

    print(f"\n================ SUMMARY RESULT ================", flush=True)
    print(json.dumps(
        {
            "decision": res["decision"],
            "decision_details": res["decision_details"],
            "coverage": res["coverage"],
            "execution_metadata": res["execution_metadata"],
            "attestation": res["attestation"],
        },
        indent=2, default=str,
    ), flush=True)
    print(f"================ END SUMMARY ================", flush=True)


if __name__ == "__main__":
    main()
