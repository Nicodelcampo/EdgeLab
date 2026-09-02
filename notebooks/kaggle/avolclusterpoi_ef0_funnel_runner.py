#!/usr/bin/env python3
"""Kaggle EF0 runner for the aVolClusterPOI full-trace bundle.

Cheap post-processing only: validates the immutable target-free trace, builds a
structural profile, and emits review-required question cards. It never reads
raw ticks, future prices, outcomes, returns or P&L, and cannot launch EF1.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_URL = "https://github.com/Nicodelcampo/EdgeLab.git"
ANALYSIS_COMMIT = "4b0e5b3c6cf359447b2b81dcb9a1f4f873fcca97"
SOURCE_COMMIT = "eafbc0380253e029acc969e07c17ebb7912ef7ec"
REPO_DIR = Path("/kaggle/working/EdgeLab-ef0")
INPUT_ROOT = Path("/kaggle/input")
EXTRACT_DIR = Path("/kaggle/working/avolclusterpoi_ef0_source")
OUT_DIR = Path("/kaggle/working/avolclusterpoi_ef0")
ARCHIVE = Path("/kaggle/working/avolclusterpoi_ef0_bundle.zip")

EXPECTED_SOURCE_HASHES = {
    "all_blocks.json": "c4d17510e45dd8492e580c6493478390e852b73174a5509efd853c05ce9fa691",
    "zones.json": "9598416abfc4b4dabda3a96cb26fb68078de3abf3663fd3727c492d0e773bff6",
    "summary.json": "629905624528af777211eee7c09b3cedddfa09cc7b2067b0a0cefa7b24f1fb57",
    "sha256_manifest.json": "e6470f09a9adcac5d5b46ecd5dcc9fe4406ab87eb85211a438ff3e54d7c48dc8",
}
EXPECTED_BLOCKS = 28_477
EXPECTED_ZONES = 414
EXPECTED_CREATE_CANDIDATES = 658
EXPECTED_AT_PRICE_CANDIDATES = 244
EXPECTED_DECISIONS = {
    "ABSTAIN_BELOW_THRESHOLD": 25_002,
    "ABSTAIN_NO_CLUSTER": 1_694,
    "ABSTAIN_NO_HISTORY": 1_123,
    "CREATE": 658,
}
BASELINE_PARAMS = {
    "window_bars": 10, "median_multiplier": 2.0, "max_gap_ticks": 1,
    "min_cluster_ticks": 2, "time_bucket_minutes": 30,
    "lookback_sessions": 20, "detection_percentile": 98.0,
    "min_samples_per_bucket": 20, "max_age_bars": 0,
    "one_cluster_per_block": True,
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True,
                               ensure_ascii=False), encoding="utf-8")


def safe_extract(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            target = (destination / info.filename).resolve()
            if root not in target.parents and target != root:
                raise SystemExit("unsafe path in source zip: {}".format(info.filename))
        zf.extractall(destination)


def valid_bundle_dirs(root):
    result = []
    for blocks_path in root.rglob("all_blocks.json"):
        parent = blocks_path.parent
        if all((parent / name).is_file() for name in
               ("zones.json", "summary.json", "sha256_manifest.json")):
            result.append(parent)
    return sorted(set(result))


def discover_bundle():
    direct = valid_bundle_dirs(INPUT_ROOT)
    if len(direct) == 1:
        return direct[0], None
    if len(direct) > 1:
        raise SystemExit("expected one trace bundle, found {}".format(direct))
    archives = sorted(INPUT_ROOT.rglob("avolclusterpoi_tracedump_full.zip"))
    if len(archives) != 1:
        raise SystemExit("no direct bundle and expected one source zip, found {}".format(len(archives)))
    if EXTRACT_DIR.exists():
        shutil.rmtree(EXTRACT_DIR)
    safe_extract(archives[0], EXTRACT_DIR)
    extracted = valid_bundle_dirs(EXTRACT_DIR)
    if len(extracted) != 1:
        raise SystemExit("source zip must contain exactly one trace bundle")
    return extracted[0], archives[0]


def verify_source(bundle):
    observed = {}
    for name, expected in EXPECTED_SOURCE_HASHES.items():
        path = bundle / name
        got = sha256(path)
        if got != expected:
            raise SystemExit("source hash mismatch {}: {} != {}".format(name, got, expected))
        observed[name] = {"bytes": path.stat().st_size, "sha256": got}
    manifest = json.loads((bundle / "sha256_manifest.json").read_text(encoding="utf-8"))
    for name in ("all_blocks.json", "zones.json", "summary.json"):
        record = manifest.get(name) or {}
        if record.get("sha256") != observed[name]["sha256"]:
            raise SystemExit("source manifest hash mismatch for {}".format(name))
        if int(record.get("bytes", -1)) != observed[name]["bytes"]:
            raise SystemExit("source manifest byte count mismatch for {}".format(name))
    return observed


def checkout_analysis_code():
    if REPO_DIR.exists():
        shutil.rmtree(REPO_DIR)
    subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                    REPO_URL, str(REPO_DIR)], check=True)
    subprocess.run(["git", "fetch", "origin", ANALYSIS_COMMIT, "--depth", "200"],
                   cwd=REPO_DIR, check=True)
    subprocess.run(["git", "checkout", "--detach", ANALYSIS_COMMIT],
                   cwd=REPO_DIR, check=True)
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_DIR,
                                     text=True).strip()
    if actual != ANALYSIS_COMMIT:
        raise SystemExit("analysis commit pin failed")
    return actual


bundle, source_zip = discover_bundle()
source_files = verify_source(bundle)
analysis_commit = checkout_analysis_code()
sys.path.insert(0, str(REPO_DIR))
from edgelab.research.avolclusterpoi_funnel import (  # noqa: E402
    build_profile, build_question_cards, canonical_sha256, validate_trace,
)

summary = json.loads((bundle / "summary.json").read_text(encoding="utf-8"))
blocks = json.loads((bundle / "all_blocks.json").read_text(encoding="utf-8"))
zones = json.loads((bundle / "zones.json").read_text(encoding="utf-8"))
integrity = validate_trace(summary, blocks, zones,
                           expected_source_commit=SOURCE_COMMIT,
                           expected_blocks=EXPECTED_BLOCKS,
                           expected_zones=EXPECTED_ZONES)
if integrity["decision_counts"] != EXPECTED_DECISIONS:
    raise SystemExit("decision count pin failed: {}".format(integrity["decision_counts"]))
if integrity["n_create_candidates"] != EXPECTED_CREATE_CANDIDATES:
    raise SystemExit("CREATE candidate pin failed")
if integrity["n_at_price_candidates"] != EXPECTED_AT_PRICE_CANDIDATES:
    raise SystemExit("AT_PRICE candidate pin failed")

profile = build_profile(summary, blocks, zones, BASELINE_PARAMS)
questions = build_question_cards(profile)
status = {
    "schema_version": "avolclusterpoi_ef0_status_v1",
    "stage": "EF0_B_STRUCTURAL_PROFILE",
    "status": "MEASURED_LOCAL_UNCOMMITTED",
    "analysis_commit": analysis_commit, "source_commit": SOURCE_COMMIT,
    "source_bundle_dir": str(bundle),
    "source_zip": None if source_zip is None else str(source_zip),
    "source_files": source_files, "config_id": profile["config_id"],
    "n_blocks": integrity["n_blocks"],
    "n_create_candidates": integrity["n_create_candidates"],
    "n_zones_off_price": integrity["n_zones_off_price"],
    "n_at_price_candidates": integrity["n_at_price_candidates"],
    "parity_status": "FAIL_END_TO_END", "selection_made": False,
    "next_stage_executed": False,
    "next_stage_status": "BLOCKED_PENDING_REVIEWED_EF1_PLAN_AND_AUTHORIZATION",
    "outcomes_accessed": False, "holdout_accessed": False,
    "heavy_cpu_started": False,
}
status["run_id"] = canonical_sha256({
    "analysis_commit": analysis_commit, "source_files": source_files,
    "config_id": profile["config_id"],
})

if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir(parents=True)
outputs = {"ef0_integrity.json": integrity, "ef0_profile.json": profile,
           "ef0_question_cards.json": questions, "ef0_status.json": status}
for name, payload in outputs.items():
    write_json(OUT_DIR / name, payload)
output_manifest = {
    name: {"bytes": (OUT_DIR / name).stat().st_size,
           "sha256": sha256(OUT_DIR / name)} for name in sorted(outputs)
}
write_json(OUT_DIR / "sha256_manifest.json", output_manifest)
with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
    for path in sorted(OUT_DIR.iterdir()):
        zf.write(path, path.relative_to(OUT_DIR.parent))

print("analysis_commit=", analysis_commit)
print("source_commit=", SOURCE_COMMIT)
print("source_bundle=", bundle)
print("n_blocks=", integrity["n_blocks"])
print("n_create_candidates=", integrity["n_create_candidates"])
print("n_zones_off_price=", integrity["n_zones_off_price"])
print("n_at_price_candidates=", integrity["n_at_price_candidates"])
print("n_sessions=", profile["n_sessions"])
print("config_id=", profile["config_id"])
print("next_stage=", status["next_stage_status"])
print("outcomes_accessed=", False)
print("artifact=", ARCHIVE)
print("artifact_sha256=", sha256(ARCHIVE))
