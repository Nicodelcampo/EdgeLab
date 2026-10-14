#!/usr/bin/env python3
"""Kaggle entrypoint: rebuild the BT2A NQ informal creation Event Store and
verify it against the frozen hashes on record, per the Notion AI auditor's
order 3a (2026-08-30 14:05 ART): the prior kernel run's output could not be
recovered via `kaggle kernels output` (only 26 stray top-level repo docs came
back, the manifest+parquet were never in it). This rebuild is target-free: it
only consolidates already-selected creation-only coordinate parquets, it never
reads raw ticks, price paths, or outcomes.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
FULL_COMMIT = "a6bfcb08590c3f20f1863cabd9e5f5916e4b3b04"
REPO_DIR = Path("/kaggle/working/EdgeLab")
OUTPUT_DIR = Path("/kaggle/working/edgelab-output")
KAGGLE_INPUT = Path("/kaggle/input")
TOKEN = "AUTHORIZE_BUILD_BT2A_NQ_CREATION_EVENT_STORE_V1"


def find_selection_dir() -> Path:
    print("kaggle_input contents:", sorted(p.name for p in KAGGLE_INPUT.iterdir()) if KAGGLE_INPUT.is_dir() else "MISSING")
    hits = list(KAGGLE_INPUT.glob("**/coordinate_manifest.json"))
    if not hits:
        raise SystemExit(f"coordinate_manifest.json not found anywhere under {KAGGLE_INPUT}")
    if len(hits) > 1:
        raise SystemExit(f"ambiguous: multiple coordinate_manifest.json found: {hits}")
    return hits[0].parent

EXPECTED_MANIFEST_SHA256 = "b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544"
EXPECTED_PARQUET_SHA256 = "96281e880d7949f9dfcf3364091d9ce7696f778e59e6f2e2243995becdd38808"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd, **kw):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=True, **kw)


def main() -> None:
    commit = FULL_COMMIT
    run(["git", "clone", "--filter=blob:none", "--no-checkout", REPO_URL, str(REPO_DIR)])
    run(["git", "fetch", "origin", commit, "--depth", "200"], cwd=REPO_DIR)
    run(["git", "checkout", "--detach", commit], cwd=REPO_DIR)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR, text=True).strip()
    print("repo_commit=", actual)
    if actual != commit:
        raise SystemExit(f"checked-out commit differs from expected: {actual} != {commit}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SELECTION_DIR = find_selection_dir()
    print("selection_artifact_dir=", SELECTION_DIR)
    print("selection_artifact_dir contents:", sorted(p.name for p in SELECTION_DIR.iterdir()))

    base_cmd = [
        "python", "tools/build_bt2a_nq_creation_event_store.py",
        "--spec", "specs/bt2a_nq_creation_event_store_informal_v1.draft.json",
        "--selection-artifact-dir", str(SELECTION_DIR),
        "--output-dir", str(OUTPUT_DIR),
        "--expected-commit", commit,
    ]

    print("\n=== PREFLIGHT ===")
    run(base_cmd + ["--preflight-only"], cwd=REPO_DIR)

    print("\n=== BUILD ===")
    run(base_cmd + ["--expected-commit", commit, "--authorization-token", TOKEN, "--build"], cwd=REPO_DIR)

    print("\n=== VALIDATE ===")
    run(base_cmd + ["--validate-only"], cwd=REPO_DIR)

    manifest_path = OUTPUT_DIR / "bt2a_nq_creation_event_store_manifest.json"
    parquet_path = OUTPUT_DIR / "bt2a_nq_creation_events.parquet"

    print("\n=== HASH VERIFICATION AGAINST FROZEN RECORD ===")
    manifest_sha = sha256_file(manifest_path) if manifest_path.is_file() else None
    parquet_sha = sha256_file(parquet_path) if parquet_path.is_file() else None
    result = {
        "manifest_path": str(manifest_path),
        "manifest_exists": manifest_path.is_file(),
        "manifest_sha256_actual": manifest_sha,
        "manifest_sha256_expected_frozen": EXPECTED_MANIFEST_SHA256,
        "manifest_sha256_match": manifest_sha == EXPECTED_MANIFEST_SHA256,
        "parquet_path": str(parquet_path),
        "parquet_exists": parquet_path.is_file(),
        "parquet_sha256_actual": parquet_sha,
        "parquet_sha256_expected_frozen": EXPECTED_PARQUET_SHA256,
        "parquet_sha256_match": parquet_sha == EXPECTED_PARQUET_SHA256,
    }
    print(json.dumps(result, indent=2))
    if manifest_path.is_file():
        print("\n=== MANIFEST CONTENT ===")
        print(manifest_path.read_text(encoding="utf-8"))

    (OUTPUT_DIR / "hash_verification_result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
