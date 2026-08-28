#!/usr/bin/env python3
"""Kaggle entrypoint for the NQ post-upload integrity gate only."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_URL = os.environ.get("EDGELAB_REPO_URL", "https://github.com/Nicodelcampo/EdgeLab.git")
EXPECTED_COMMIT = os.environ.get("EDGELAB_EXPECTED_COMMIT", "")
DATA_DIR = Path(
    os.environ.get(
        "EDGELAB_DATA_DIR", "/kaggle/input/edgelab-ticks-nq-preholdout"
    )
)
REPO_DIR = Path(os.environ.get("EDGELAB_REPO_DIR", "/kaggle/working/EdgeLab"))
OUTPUT = Path("/kaggle/working/nq_post_upload_rehash.json")

if len(EXPECTED_COMMIT) != 40:
    raise SystemExit("Set EDGELAB_EXPECTED_COMMIT to the frozen 40-character verification commit")
if not str(DATA_DIR).startswith("/kaggle/input/"):
    raise SystemExit("EDGELAB_DATA_DIR must be under /kaggle/input")
if not (REPO_DIR / ".git").exists():
    subprocess.run(
        ["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)],
        check=True,
    )
subprocess.run(
    ["git", "fetch", "origin", EXPECTED_COMMIT, "--depth", "1"],
    cwd=REPO_DIR,
    check=True,
)
subprocess.run(
    ["git", "checkout", "--detach", EXPECTED_COMMIT], cwd=REPO_DIR, check=True
)
actual = subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True
).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("checked-out commit differs from EDGELAB_EXPECTED_COMMIT")

command = [
    "python",
    "tools/verify_kaggle_nq_post_upload.py",
    "--data-dir",
    str(DATA_DIR),
    "--contract",
    "specs/kaggle_nq_private_upload_v1.draft.json",
    "--output",
    str(OUTPUT),
]
print("mode=POST_UPLOAD_REHASH_ONLY")
print("repo_commit=", actual)
print("data_dir=", DATA_DIR)
subprocess.run(command, cwd=REPO_DIR, check=True)
print("artifact=", OUTPUT)
