#!/usr/bin/env python3
"""Kaggle entrypoint for one frozen EdgeLab campaign.

Attach the private pre-holdout dataset. The repository is checked out at an
exact commit; no credential is embedded. Execution remains disabled unless
EDGELAB_EXECUTE=1 and a campaign token is supplied through a Kaggle secret or
environment variable.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_URL = os.environ.get("EDGELAB_REPO_URL", "https://github.com/Nicodelcampo/EdgeLab.git")
EXPECTED_COMMIT = os.environ.get("EDGELAB_EXPECTED_COMMIT", "")
SPEC_RELATIVE = os.environ.get("EDGELAB_EXECUTION_SPEC", "")
DATA_DIR = os.environ.get("EDGELAB_DATA_DIR", "")
EXECUTE = os.environ.get("EDGELAB_EXECUTE", "0") == "1"
TOKEN = os.environ.get("EDGELAB_AUTHORIZATION_TOKEN", "")
REPO_DIR = Path(os.environ.get("EDGELAB_REPO_DIR", "/kaggle/working/EdgeLab"))
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
ARCHIVE = Path("/kaggle/working/output.zip")

if len(EXPECTED_COMMIT) != 40 or not SPEC_RELATIVE or not DATA_DIR:
    raise SystemExit(
        "Set EDGELAB_EXPECTED_COMMIT (40 chars), EDGELAB_EXECUTION_SPEC and EDGELAB_DATA_DIR"
    )
if not (REPO_DIR / ".git").exists():
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)], check=True)
subprocess.run(["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "1"], cwd=REPO_DIR, check=True)
subprocess.run(["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO_DIR, check=True)
actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EDGELAB_EXPECTED_COMMIT")

command = [
    "python",
    "tools/run_kaggle_frozen_job.py",
    "--spec",
    str(REPO_DIR / SPEC_RELATIVE),
    "--data-dir",
    DATA_DIR,
    "--output-dir",
    str(OUTPUT_DIR),
    "--expected-commit",
    EXPECTED_COMMIT,
    "--archive",
    str(ARCHIVE),
]
if EXECUTE:
    if not TOKEN:
        raise SystemExit("EDGELAB_EXECUTE=1 requires EDGELAB_AUTHORIZATION_TOKEN")
    command.extend(["--run", "--authorization-token", TOKEN])
else:
    command.append("--preflight-only")
print("mode=", "RUN" if EXECUTE else "PREFLIGHT_ONLY")
print("repo_commit=", actual)
print("data_dir=", DATA_DIR)
subprocess.run(command, cwd=REPO_DIR, check=True)
print("artifact=", ARCHIVE if EXECUTE else OUTPUT_DIR / "preflight.json")
