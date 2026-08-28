#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight and validate the NQ-120t aVolClusterPOI creation Event Store.

This command never builds first-touch or outcome paths.  While the spec is a
draft, only --preflight-only is accepted.  Artifact validation requires a
frozen contract, exact commit and a separate zone-store authorization token.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.research.avolcluster_nq_zone_store import (
    SPEC_STATUS_FROZEN,
    load_spec,
    projected_frozen_payload_sha256,
    validate_zone_rows,
)
from edgelab.research.event_store_contract import (
    EventStoreContractError,
    load_checkpoint_rows,
    validate_parquet_against_rows,
)

DEFAULT_SPEC = REPO_ROOT / "specs/avolcluster_nq_zone_event_store_v1.json"


def git_state() -> dict:
    def run(*args: str) -> tuple[int, str]:
        proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
        return proc.returncode, proc.stdout.strip()

    rc, commit = run("rev-parse", "HEAD")
    if rc:
        return {"available": False, "commit": None, "branch": None, "dirty": True}
    _, branch = run("branch", "--show-current")
    _, status = run("status", "--porcelain")
    return {"available": True, "commit": commit, "branch": branch, "dirty": bool(status)}


def write_json(path: Path | None, payload: dict) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(text, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--validate-artifacts", action="store_true")
    parser.add_argument("--checkpoints-dir", type=Path)
    parser.add_argument("--parquet", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--authorization-token")
    parser.add_argument("--output-json", type=Path)
    try:
        spec = load_spec(parser.parse_args(argv).spec)
        args = parser.parse_args(argv)
        gs = git_state()
        base = {
            "schema_version": "avolcluster_nq_zone_store_validation_v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_state": gs,
            "spec_status": spec["status"],
            "projected_frozen_spec_payload_sha256": projected_frozen_payload_sha256(spec),
            "future_price_path_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": False,
            "edge_declared": False,
        }
        if args.preflight_only:
            if args.expected_commit is not None and gs["commit"] != args.expected_commit:
                raise EventStoreContractError("preflight commit mismatch")
            result = {
                **base,
                "status": "DRAFT_PREPARATION_READY" if spec["status"] != SPEC_STATUS_FROZEN else "FROZEN_PREFLIGHT_READY",
                "ready_for_zone_store_validation": spec["status"] == SPEC_STATUS_FROZEN,
                "ready_for_first_touch_or_outcomes": False,
                "review_blockers": spec["review_blockers"],
            }
            write_json(args.output_json, result)
            return 0

        if spec["status"] != SPEC_STATUS_FROZEN:
            raise EventStoreContractError("spec is not frozen")
        if not args.expected_commit:
            raise EventStoreContractError("--expected-commit is mandatory")
        if not gs["available"] or gs["commit"] != args.expected_commit:
            raise EventStoreContractError("HEAD does not match --expected-commit")
        if gs["dirty"]:
            raise EventStoreContractError("dirty worktree")
        authorization = spec["authorization"]
        if authorization.get("zone_store_validation_authorized") is not True:
            raise EventStoreContractError("zone-store validation is not authorized")
        if args.authorization_token != authorization.get("zone_store_validation_token"):
            raise EventStoreContractError("invalid or missing authorization token")
        if args.checkpoints_dir is None or args.parquet is None:
            raise EventStoreContractError("--checkpoints-dir and --parquet are mandatory")
        checkpoint_rows, checkpoint_metadata = load_checkpoint_rows(args.checkpoints_dir)
        normalized, diagnostics = validate_zone_rows(
            checkpoint_rows, spec, enforce_expected_counts=True
        )
        transport = validate_parquet_against_rows(
            args.parquet, normalized, spec["event_store"]["contract"]
        )
        result = {
            **base,
            "status": "READY_ZONE_CREATION_EVENT_STORE",
            "ready_for_zone_store_validation": True,
            "ready_for_first_touch_or_outcomes": False,
            "checkpoint_files": len(checkpoint_metadata),
            "checkpoint_metadata": checkpoint_metadata,
            "diagnostics": diagnostics,
            "transport": transport,
        }
        write_json(args.output_json, result)
        return 0
    except EventStoreContractError as exc:
        payload = {
            "schema_version": "avolcluster_nq_zone_store_validation_v1",
            "status": exc.label,
            "message": str(exc),
            "future_price_path_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": exc.label == "ABSTAIN_HOLDOUT_FIREWALL",
            "edge_declared": False,
        }
        # Parsing may have failed before args exists; emit to stderr only.
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
