#!/usr/bin/env python3
"""Kaggle entrypoint for the BT2A NQ target-free selection campaign.

Direct, minimal counterpart to notebooks/kaggle/10_frozen_job_runner.py that
invokes tools/run_bt2a_nq_target_free_selection_kaggle_all.py without going
through the generic edgelab/kaggle/execution.py envelope (which has the same
unresolved frozen-commit self-reference bug documented in
docs/incidents/INCIDENTE_frozen_commit_bootstrap_2026-08-29.md, not fixed
there). The repository is checked out at an exact commit; no credential is
embedded. Execution is disabled unless EDGELAB_EXECUTE=1 and a campaign token
are supplied through a Kaggle secret or environment variable.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_URL = os.environ.get("EDGELAB_REPO_URL", "https://github.com/Nicodelcampo/EdgeLab.git")
EXPECTED_COMMIT = os.environ.get("EDGELAB_EXPECTED_COMMIT", "")
DATA_DIR = os.environ.get("EDGELAB_DATA_DIR", "")
EXECUTE = os.environ.get("EDGELAB_EXECUTE", "0") == "1"
TOKEN = os.environ.get("EDGELAB_AUTHORIZATION_TOKEN", "")
REPO_DIR = Path(os.environ.get("EDGELAB_REPO_DIR", "/kaggle/working/EdgeLab"))
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
ARCHIVE = Path("/kaggle/working/output.zip")

if len(EXPECTED_COMMIT) != 40 or not DATA_DIR:
    raise SystemExit("Set EDGELAB_EXPECTED_COMMIT (40 chars) and EDGELAB_DATA_DIR")

if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "1"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EDGELAB_EXPECTED_COMMIT")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if not EXECUTE:
    command = [
        "python", "tools/run_bt2a_nq_target_free_selection.py",
        "--data-dir", DATA_DIR,
        "--output-dir", str(OUTPUT_DIR),
        "--expected-commit", EXPECTED_COMMIT,
        "--preflight-only",
    ]
    print("mode= PREFLIGHT_ONLY")
    print("repo_commit=", actual)
    print("data_dir=", DATA_DIR)
    subprocess.run(command, cwd=REPO_DIR, check=True)
    print("artifact=", OUTPUT_DIR / "preflight.json")
else:
    if not TOKEN:
        raise SystemExit("EDGELAB_EXECUTE=1 requires EDGELAB_AUTHORIZATION_TOKEN")
    env = os.environ.copy()
    env["EDGELAB_AUTHORIZATION_TOKEN"] = TOKEN
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "1"
    command = [
        "python", "tools/run_bt2a_nq_target_free_selection_kaggle_all.py",
        "--data-dir", DATA_DIR,
        "--output-dir", str(OUTPUT_DIR),
        "--expected-commit", EXPECTED_COMMIT,
    ]
    print("mode= RUN")
    print("repo_commit=", actual)
    print("data_dir=", DATA_DIR)
    subprocess.run(command, cwd=REPO_DIR, env=env, check=True)
    subprocess.run(
        ["python", "-c",
         f"import shutil; shutil.make_archive(r'{ARCHIVE.with_suffix('')}', 'zip', r'{OUTPUT_DIR}')"],
        check=True,
    )
    print("artifact=", ARCHIVE)
