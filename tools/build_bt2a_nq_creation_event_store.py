#!/usr/bin/env python3
"""Build the BT2A NQ creation Event Store from selected coordinate artifacts.

This transform never reads raw ticks. It accepts only a hash-bound successful
selection artifact under /kaggle/input and writes the consolidated creation
store under /kaggle/working.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(ROOT))

from edgelab.kaggle.execution import atomic_write_json, canonical_sha256, sha256_file
from tools.sweep_bigtrap2_nq_tickframes_v2 import _is_ancestor, validate_kaggle_runtime, verify_git_clean_and_head
from tools.bt2a_nq_gate1_contracts import (
    INFORMAL_STATUS, selection_provenance_missing, validate_selection_provenance,
)

DEFAULT_SPEC = ROOT / "specs" / "bt2a_nq_creation_event_store_v1.draft.json"
FROZEN = "FROZEN_PREFLIGHT_READY"
DRAFT = "DRAFT_PREAUTHORIZATION"
BUILD_TOKEN = "AUTHORIZE_BUILD_BT2A_NQ_CREATION_EVENT_STORE_V1"
REQUIRED_COLUMNS = [
    "config_id", "contract", "cme_session_id", "event_time_ns", "source_row",
    "direction", "signal_price_ticks", "a_score", "a_threshold", "event_key",
]
FORBIDDEN_COLUMNS = {
    "first_touch", "fill_price", "future_price", "mfe", "mae", "d_hat",
    "return", "pnl", "first_passage", "target_hit", "stop_hit",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return value


def _hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _payload_valid(value: dict[str, Any]) -> bool:
    digest = value.get("payload_sha256")
    body = {key: item for key, item in value.items() if key != "payload_sha256"}
    return _hex64(digest) and canonical_sha256(body) == digest


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != "bt2a_nq_creation_event_store_v1":
        raise RuntimeError("unexpected BT2A NQ Event Store schema")
    if spec.get("status") not in {DRAFT, FROZEN}:
        raise RuntimeError("invalid Event Store spec status")
    if spec.get("execution_platform") != "KAGGLE_ONLY":
        raise RuntimeError("Event Store build must be Kaggle-only")
    build = spec.get("build") or {}
    if build.get("mode") != "TRANSFORM_SELECTED_COORDINATES_ONLY":
        raise RuntimeError("Event Store build must be transform-only")
    if any(build.get(key) is not False for key in ("raw_tick_decode_allowed", "future_path_decode_allowed", "lifecycle_allowed")):
        raise RuntimeError("Event Store build capability is too broad")
    universe = spec.get("universe") or {}
    if universe.get("instrument") != "NQ" or int(universe.get("contract_sessions", -1)) != 234:
        raise RuntimeError("unexpected Event Store universe")
    if len(universe.get("contracts") or []) != 5 or universe.get("session_max") != "20260630":
        raise RuntimeError("Event Store contract or time universe mismatch")
    auth = spec.get("authorization") or {}
    if spec["status"] == DRAFT:
        if auth.get("execution_authorized") is not False or auth.get("active_token") is not None:
            raise RuntimeError("draft Event Store cannot carry execution capability")
    else:
        if auth.get("execution_authorized") is not True or auth.get("active_token") != BUILD_TOKEN:
            raise RuntimeError("frozen Event Store requires exact build capability")
        if not isinstance(auth.get("frozen_commit"), str) or len(auth["frozen_commit"]) != 40:
            raise RuntimeError("frozen Event Store requires full commit")
    # Formal selection remains the default.  The informal 2/5 route is accepted
    # only when an external amendment is hash-bound and explicitly non-promotable.
    validate_selection_provenance(spec, ROOT, require_frozen=False)
    firewall = spec.get("firewall") or {}
    if any(firewall.get(name) is not False for name in (
        "LIFECYCLE_ACCESSED", "FIRST_TOUCH_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "PNL_ACCESSED",
        "HOLDOUT_TOUCHED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    )):
        raise RuntimeError("Event Store firewall is open")


def _safe_child(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if not relative or rel.is_absolute() or ".." in rel.parts:
        raise RuntimeError(f"unsafe artifact-relative path: {relative!r}")
    root = root.resolve()
    path = (root / rel).resolve()
    if not path.is_relative_to(root) or path.is_symlink():
        raise RuntimeError(f"artifact path escapes or is symlink: {relative!r}")
    return path


def _verify_bound_file(root: Path, name: str, expected: str | None) -> Path:
    if not _hex64(expected):
        raise RuntimeError(f"unbound artifact hash: {name}")
    path = _safe_child(root, name)
    if not path.is_file() or sha256_file(path) != expected:
        raise RuntimeError(f"artifact SHA-256 mismatch: {name}")
    return path


def verify_selection_artifact(spec: dict[str, Any], artifact_dir: Path) -> dict[str, Any]:
    source = spec["source_selection"]
    provenance = validate_selection_provenance(spec, ROOT, require_frozen=True)
    result_path = _verify_bound_file(artifact_dir, source["result_file"], source["result_file_sha256"])
    selected_path = _verify_bound_file(
        artifact_dir, source["selected_configuration_file"], source["selected_configuration_file_sha256"]
    )
    manifest_path = _verify_bound_file(
        artifact_dir, source["coordinate_manifest_file"], source["coordinate_manifest_file_sha256"]
    )
    result = load_json(result_path)
    selected = load_json(selected_path)
    manifest = load_json(manifest_path)
    if not all(_payload_valid(value) for value in (result, selected, manifest)):
        raise RuntimeError("selection artifact payload hash mismatch")
    required_status = source["required_selection_status"]
    config_id = source["selected_config_id"]
    if result.get("status") != required_status or selected.get("status") != required_status:
        raise RuntimeError("selection did not produce a stable configuration")
    if not config_id or result.get("selected_config_id") != config_id or selected.get("config_id") != config_id:
        raise RuntimeError("selected configuration binding mismatch")
    if result.get("coordinate_manifest_file_sha256") != source["coordinate_manifest_file_sha256"]:
        raise RuntimeError("selection result does not bind the coordinate manifest file")
    records = [row for row in manifest.get("files", []) if row.get("config_id") == config_id]
    expected_contracts = set(spec["universe"]["contracts"])
    if {row.get("contract") for row in records} != expected_contracts or len(records) != len(expected_contracts):
        raise RuntimeError("selected coordinate manifest lacks exactly one partition per contract")
    verified = []
    for record in records:
        path = _safe_child(artifact_dir, record["path"])
        if not path.is_file() or path.stat().st_size != record.get("bytes") or sha256_file(path) != record.get("sha256"):
            raise RuntimeError(f"selected coordinate partition mismatch: {record.get('path')}")
        verified.append({**record, "resolved_path": path})
    return {
        "config_id": config_id,
        "selected": selected,
        "selection_provenance": provenance,
        "selection_result_file_sha256": sha256_file(result_path),
        "selected_configuration_file_sha256": sha256_file(selected_path),
        "coordinate_manifest_file_sha256": sha256_file(manifest_path),
        "partitions": verified,
    }


def preflight(spec_path: Path, artifact_dir: Path, output_dir: Path, expected_commit: str) -> dict[str, Any]:
    validate_kaggle_runtime(artifact_dir, output_dir / "event_store_preflight.json")
    spec = load_json(spec_path)
    validate_spec(spec)
    git = verify_git_clean_and_head(expected_commit)
    source = spec["source_selection"]
    bound = all(_hex64(source.get(name)) for name in (
        "result_file_sha256", "selected_configuration_file_sha256", "coordinate_manifest_file_sha256"
    )) and isinstance(source.get("selected_config_id"), str) and not selection_provenance_missing(source)
    evidence = None
    error = None
    if bound:
        try:
            evidence = verify_selection_artifact(spec, artifact_dir)
        except Exception as exc:
            error = str(exc)
    ready = bound and evidence is not None
    result = {
        "schema_version": "bt2a_nq_creation_event_store_preflight_v1",
        "status": "PASS_READY_FOR_FREEZE_OR_BUILD" if ready else "NOT_READY",
        "spec_status": spec["status"],
        "spec_file_sha256": sha256_file(spec_path),
        "git": git,
        "selection_bound": bound,
        "selection_evidence": None if evidence is None else {key: value for key, value in evidence.items() if key != "partitions"},
        "error": error,
        "raw_tick_decode_executed": False,
        "future_price_path_accessed": False,
        "holdout_touched": False,
    }
    atomic_write_json(output_dir / "event_store_preflight.json", result)
    return result


def require_build_authorization(spec: dict[str, Any], expected_commit: str, token: str | None) -> None:
    validate_spec(spec)
    auth = spec["authorization"]
    if spec["status"] != FROZEN or auth.get("execution_authorized") is not True:
        raise PermissionError("Event Store spec is not frozen for build")
    if token != BUILD_TOKEN or auth.get("active_token") != BUILD_TOKEN:
        raise PermissionError("missing exact Event Store build token")
    if not _is_ancestor(auth.get("frozen_commit"), expected_commit):
        raise RuntimeError("Event Store frozen commit is not an ancestor of --expected-commit")
    verify_git_clean_and_head(expected_commit)


def build(spec_path: Path, artifact_dir: Path, output_dir: Path, expected_commit: str,
          token: str | None) -> dict[str, Any]:
    readiness = preflight(spec_path, artifact_dir, output_dir, expected_commit)
    if readiness["status"] != "PASS_READY_FOR_FREEZE_OR_BUILD":
        raise RuntimeError("ABSTAIN_BT2A_NQ_EVENT_STORE_PREFLIGHT_NOT_READY")
    spec = load_json(spec_path)
    require_build_authorization(spec, expected_commit, token)
    evidence = verify_selection_artifact(spec, artifact_dir)
    frames = []
    for record in evidence["partitions"]:
        frame = pd.read_parquet(record["resolved_path"])
        if list(frame.columns) != REQUIRED_COLUMNS:
            raise RuntimeError("coordinate schema mismatch")
        lowered = {str(name).lower() for name in frame.columns}
        if lowered & FORBIDDEN_COLUMNS:
            raise RuntimeError("outcome or lifecycle column present in creation coordinates")
        if len(frame) and (
            set(frame["config_id"]) != {evidence["config_id"]}
            or set(frame["contract"]) != {record["contract"]}
        ):
            raise RuntimeError("coordinate partition identity mismatch")
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    if combined["event_key"].duplicated().any():
        raise RuntimeError("duplicate selected creation event")
    combined = combined.sort_values(
        ["contract", "cme_session_id", "event_time_ns", "source_row", "direction", "event_key"],
        kind="stable",
    )
    target = output_dir / spec["build"]["output_parquet"]
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".parquet.tmp")
    combined.to_parquet(temporary, index=False, compression="zstd")
    os.replace(temporary, target)
    manifest = {
        "schema_version": "bt2a_nq_creation_event_store_manifest_v1",
        "status": "READY_CREATION_EVENT_STORE",
        "frozen_commit": expected_commit,
        "spec_file_sha256": sha256_file(spec_path),
        "selected_config_id": evidence["config_id"],
        "selection_provenance": evidence["selection_provenance"],
        "confirmatory_eligible": evidence["selection_provenance"]["confirmatory_eligible"],
        "promotion_eligible": evidence["selection_provenance"]["promotion_eligible"],
        "selection_result_file_sha256": evidence["selection_result_file_sha256"],
        "selected_configuration_file_sha256": evidence["selected_configuration_file_sha256"],
        "coordinate_manifest_file_sha256": evidence["coordinate_manifest_file_sha256"],
        "parquet_file": target.name,
        "parquet_file_sha256": sha256_file(target),
        "parquet_file_bytes": target.stat().st_size,
        "rows": len(combined),
        "sessions_with_events": int(combined["cme_session_id"].nunique()) if len(combined) else 0,
        "contracts": sorted(map(str, combined["contract"].unique().tolist())) if len(combined) else [],
        "event_keys_unique": True,
        "event_rows_payload_sha256": canonical_sha256(combined[REQUIRED_COLUMNS].to_dict("records")),
        "build_mode": "TRANSFORM_SELECTED_COORDINATES_ONLY",
        "firewall": {
            "raw_tick_decode_executed": False,
            "lifecycle_accessed": False,
            "future_price_path_accessed": False,
            "first_touch_accessed": False,
            "first_passage_accessed": False,
            "mfe_mae_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": False,
            "edge_declared": False,
        },
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    manifest_path = output_dir / spec["build"]["output_manifest"]
    manifest_sha = atomic_write_json(manifest_path, manifest)
    attestation = {
        "schema_version": "bt2a_nq_creation_event_store_attestation_v1",
        "manifest_file_sha256": manifest_sha,
        "parquet_file_sha256": manifest["parquet_file_sha256"],
        "raw_tick_decode_executed": False,
        "future_price_path_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
    }
    atomic_write_json(output_dir / "execution_attestation.json", attestation)
    verify_git_clean_and_head(expected_commit)
    return manifest


def validate_store(store_dir: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = store_dir / manifest_name
    manifest = load_json(manifest_path)
    if not _payload_valid(manifest) or manifest.get("status") != "READY_CREATION_EVENT_STORE":
        raise RuntimeError("invalid creation Event Store manifest")
    provenance = manifest.get("selection_provenance") or {}
    if provenance.get("status") == INFORMAL_STATUS and (
        manifest.get("confirmatory_eligible") is not False
        or manifest.get("promotion_eligible") is not False
        or provenance.get("classification") != "EXPLORATORY_NON_CONFIRMATORY_NON_PROMOTABLE"
    ):
        raise RuntimeError("informal Event Store lost non-promotable provenance")
    parquet = _safe_child(store_dir, manifest["parquet_file"])
    if not parquet.is_file() or parquet.stat().st_size != manifest["parquet_file_bytes"] or sha256_file(parquet) != manifest["parquet_file_sha256"]:
        raise RuntimeError("creation Event Store Parquet mismatch")
    frame = pd.read_parquet(parquet)
    if list(frame.columns) != REQUIRED_COLUMNS or len(frame) != manifest["rows"] or frame["event_key"].duplicated().any():
        raise RuntimeError("creation Event Store logical mismatch")
    if canonical_sha256(frame[REQUIRED_COLUMNS].to_dict("records")) != manifest["event_rows_payload_sha256"]:
        raise RuntimeError("creation Event Store row payload mismatch")
    return {
        "status": "PASS_READY_CREATION_EVENT_STORE",
        "manifest_file_sha256": sha256_file(manifest_path),
        "parquet_file_sha256": sha256_file(parquet),
        "rows": len(frame),
        "holdout_touched": False,
    }


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__)
    out.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    out.add_argument("--selection-artifact-dir", type=Path)
    out.add_argument("--output-dir", type=Path, required=True)
    out.add_argument("--expected-commit")
    out.add_argument("--authorization-token")
    mode = out.add_mutually_exclusive_group(required=True)
    mode.add_argument("--contract-only", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--build", action="store_true")
    mode.add_argument("--validate-only", action="store_true")
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    spec = load_json(args.spec)
    validate_spec(spec)
    if args.contract_only:
        print(json.dumps({"status": "PASS_EVENT_STORE_DRAFT_CONTRACT", "execution_authorized": False}, indent=2))
        return 0
    if args.validate_only:
        result = validate_store(args.output_dir, spec["build"]["output_manifest"])
    else:
        if args.selection_artifact_dir is None or not args.expected_commit:
            raise SystemExit("--selection-artifact-dir and --expected-commit are required")
        if args.preflight_only:
            result = preflight(args.spec, args.selection_artifact_dir, args.output_dir, args.expected_commit)
        else:
            token = args.authorization_token or os.environ.get("EDGELAB_AUTHORIZATION_TOKEN")
            result = build(args.spec, args.selection_artifact_dir, args.output_dir, args.expected_commit, token)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result["status"]).startswith(("PASS", "READY")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
