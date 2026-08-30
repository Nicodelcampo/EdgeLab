# -*- coding: utf-8 -*-
"""Metadata-only preflight for AVolCluster NQ Gate 1B / roadmap Gate 3.

It reads specs and published manifests only. It has no raw-tick decoder, future
path scanner, first-touch builder, outcome engine or P&L capability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from edgelab.research.avolcluster_nq_lifecycle_contracts import (
    LifecycleContractError,
    git_blob_sha1,
    load_json,
    sha256_file,
    validate_episode_spec,
    validate_lifecycle_spec,
)
from edgelab.research.event_store_contract import canonical_sha256

ROOT = Path(__file__).resolve().parents[1]
LIFECYCLE_SPEC = Path("specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json")
EPISODE_SPEC = Path("specs/avolcluster_nq_episode_collapse_v1.draft.json")
EXPECTED_BLOBS = {
    "docs/research/INFORME_FINAL_AVOLCLUSTER_NQ_GATE1A_2026-08-28.md": "08632a173babd85abf02050424c863edf0ec05be",
    "docs/research/AVOLCLUSTER_BT2A_NQ_JOINT_MEASUREMENT_DESIGN_V1_2026-08-28.md": "fea95f2957c306a42004b4bfcff75f17bc061f55",
    "specs/avolcluster_nq_zone_event_store_v1.json": "c788924a3851e86a54b17bff03546dc7d730b989",
    "specs/avolcluster_bt2a_nq_joint_measurement_v1.draft.json": "3db09331f730cc1f137e6bc3aa0dc57f524dddb6",
}
EXPECTED_CREATION_MANIFEST = {
    "file_sha256": "df80294138d0401d979bceb5416c6006d05fd7d143b00a1bab2323260fea0cd3",
    "payload_sha256": "f87061427d884dac3290c52144bdcf0ab079d4a4b4674237c279072eae51cacc",
    "logical_payload_sha256": "7c254009dc4ccd58f4187360a861f76a692945b94c7091766cce6cf3e46f3a77",
    "parquet_physical_sha256": "4dad91f6a572bfb5edc714dfb13daa4a0bbee6b96301a4d734466a9da7a06674",
    "rows": 5876,
    "checkpoint_files": 234,
    "sessions_with_events": 233,
}


def _verify_creation_manifest(root: Path) -> dict[str, Any]:
    path = root / "docs/research/avolcluster_nq_zone_store_manifest.json"
    value = load_json(path)
    checks = {
        "file_sha256": sha256_file(path) == EXPECTED_CREATION_MANIFEST["file_sha256"],
        "status": value.get("status") == "COMPLETE_TARGET_FREE_ZONE_CREATION_STORE",
        "payload_sha256": value.get("payload_sha256") == EXPECTED_CREATION_MANIFEST["payload_sha256"],
        "payload_self_consistent": value.get("payload_sha256") == canonical_sha256({k: v for k, v in value.items() if k != "payload_sha256"}),
        "logical_payload_sha256": value.get("diagnostics", {}).get("logical_payload_sha256") == EXPECTED_CREATION_MANIFEST["logical_payload_sha256"],
        "parquet_physical_sha256": value.get("parquet", {}).get("parquet_physical_sha256") == EXPECTED_CREATION_MANIFEST["parquet_physical_sha256"],
        "rows": value.get("diagnostics", {}).get("rows") == EXPECTED_CREATION_MANIFEST["rows"],
        "checkpoint_files": value.get("checkpoint_files") == EXPECTED_CREATION_MANIFEST["checkpoint_files"],
        "sessions_with_events": value.get("diagnostics", {}).get("contract_sessions_with_events") == EXPECTED_CREATION_MANIFEST["sessions_with_events"],
        "future_path_closed": value.get("future_price_path_accessed") is False,
        "pnl_closed": value.get("pnl_accessed") is False,
        "holdout_closed": value.get("holdout_touched") is False,
    }
    if not all(checks.values()):
        failed = sorted(key for key, ok in checks.items() if not ok)
        raise LifecycleContractError(f"creation manifest binding failed: {failed}")
    return {"path": str(path.relative_to(root)), "checks": checks}


def audit_readiness(root: Path = ROOT) -> dict[str, Any]:
    try:
        source_files: dict[str, Any] = {}
        for rel, expected in EXPECTED_BLOBS.items():
            path = root / rel
            actual = git_blob_sha1(path)
            source_files[rel] = {"expected_git_blob_sha1": expected, "actual_git_blob_sha1": actual, "pass": actual == expected}
        if not all(item["pass"] for item in source_files.values()):
            raise LifecycleContractError("one or more normative source blobs drifted")
        creation = _verify_creation_manifest(root)
        lifecycle_path = root / LIFECYCLE_SPEC
        episode_path = root / EPISODE_SPEC
        lifecycle = load_json(lifecycle_path)
        episode = load_json(episode_path)
        lifecycle_missing = validate_lifecycle_spec(lifecycle)
        episode_missing = validate_episode_spec(episode)
        if episode.get("authority", {}).get("lifecycle_spec_file_sha256") != sha256_file(lifecycle_path):
            raise LifecycleContractError("episode spec is not bound to the lifecycle draft file")
        contract_source = (root / "edgelab/research/avolcluster_nq_lifecycle_contracts.py").read_text(encoding="utf-8")
        forbidden_runtime_tokens = ["import pandas", "import pyarrow", "import numpy", "read_parquet(", "load_canonical_parquet("]
        runtime_surface_absent = not any(token in contract_source for token in forbidden_runtime_tokens)
        runner_paths = [
            root / "tools/run_avolcluster_nq_lifecycle.py",
            root / "tools/build_avolcluster_nq_first_touch_store.py",
        ]
        runner_absent = not any(path.exists() for path in runner_paths)
        if not runtime_surface_absent or not runner_absent:
            raise LifecycleContractError("forbidden execution surface is present")
        missing = [f"lifecycle.{path}" for path in lifecycle_missing] + [f"episode.{path}" for path in episode_missing]
        if missing:
            status = "NOT_READY_DECISIONS_REQUIRED"
            ready_for_freeze_review = False
        elif lifecycle["status"].startswith("DRAFT") and episode["status"].startswith("DRAFT"):
            status = "PASS_READY_FOR_FREEZE_REVIEW"
            ready_for_freeze_review = True
        else:
            status = "PASS_CONTRACTS_FROZEN_EXECUTION_STILL_NOT_AUTHORIZED"
            ready_for_freeze_review = False
        return {
            "schema_version": "avolcluster_nq_gate1b_gate3_preflight_v1",
            "status": status,
            "ready_for_freeze_review": ready_for_freeze_review,
            "ready_for_execution": False,
            "source_bindings": source_files,
            "creation_manifest": creation,
            "lifecycle_missing_decisions": lifecycle_missing,
            "episode_missing_decisions": episode_missing,
            "missing_decisions": missing,
            "forbidden_execution_surface_absent": True,
            "runner_present": False,
            "RAW_TICK_DECODED": False,
            "LIFECYCLE_ACCESSED": False,
            "FIRST_TOUCH_ACCESSED": False,
            "FUTURE_PRICE_PATH_ACCESSED": False,
            "MFE_MAE_ACCESSED": False,
            "FIRST_PASSAGE_ACCESSED": False,
            "PNL_ACCESSED": False,
            "HOLDOUT_TOUCHED": False,
            "EDGE_DECLARED": False,
            "PROMOTION_ELIGIBLE": False,
        }
    except Exception as exc:
        label = exc.label if isinstance(exc, LifecycleContractError) else "ABSTAIN_AVOL_LIFECYCLE_PREFLIGHT"
        return {
            "schema_version": "avolcluster_nq_gate1b_gate3_preflight_v1",
            "status": label,
            "message": str(exc),
            "ready_for_freeze_review": False,
            "ready_for_execution": False,
            "RAW_TICK_DECODED": False,
            "LIFECYCLE_ACCESSED": False,
            "FIRST_TOUCH_ACCESSED": False,
            "FUTURE_PRICE_PATH_ACCESSED": False,
            "MFE_MAE_ACCESSED": False,
            "FIRST_PASSAGE_ACCESSED": False,
            "PNL_ACCESSED": False,
            "HOLDOUT_TOUCHED": False,
            "EDGE_DECLARED": False,
            "PROMOTION_ELIGIBLE": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = audit_readiness(args.root.resolve())
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    if result["status"].startswith("PASS_"):
        return 0
    if result["status"] == "NOT_READY_DECISIONS_REQUIRED":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
