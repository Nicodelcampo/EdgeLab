#!/usr/bin/env python3
"""Command-line interface for the Edge Discovery Brain."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

# Add repository root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.edge_brain.measurement_atlas import validate_atlas
from edgelab.edge_brain.registry import verify_registry
from edgelab.edge_brain.schema_validator import SCHEMA_DIR, get_schema
from edgelab.edge_brain.typed_registry import (
    append_typed_record,
    project_to_json,
    project_to_parquet_zstd,
    read_parquet_projection,
)


def cmd_schemas(args: argparse.Namespace) -> int:
    """List and validate all registered schemas in the edge brain."""
    if not SCHEMA_DIR.is_dir():
        print(f"ERROR: Schema directory not found: {SCHEMA_DIR}", file=sys.stderr)
        return 1

    schemas = sorted([p.stem for p in SCHEMA_DIR.glob("*.json")])
    print(f"Registered Edge Brain Schemas ({len(schemas)} total):")
    valid_count = 0
    for name in schemas:
        try:
            schema = get_schema(name)
            title = schema.get("title", name)
            print(f"  [OK] {name:<32} {title}")
            valid_count += 1
        except Exception as exc:
            print(f"  [FAIL] {name:<30} ERROR: {exc}", file=sys.stderr)

    if valid_count != 35:
        print(f"WARNING: Expected exactly 35 schemas, but found {valid_count}", file=sys.stderr)
    return 0 if valid_count == len(schemas) else 1


def cmd_validate_atlas(args: argparse.Namespace) -> int:
    """Validate a measurement atlas configuration file."""
    path = Path(args.atlas_path)
    if not path.is_file():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 1

    try:
        res = validate_atlas(path)
        print(f"Atlas validation: PASS")
        print(f"  Catalog ID:    {res['catalog_id']}")
        print(f"  Indicators:    {res['indicators_count']}")
        print(f"  Compositions:  {res['compositions_count']}")
        print(f"  Concepts:      {res['concepts_count']}")
        return 0
    except Exception as exc:
        print(f"Atlas validation: FAIL - {exc}", file=sys.stderr)
        return 1


def cmd_verify_ledger(args: argparse.Namespace) -> int:
    """Verify hash-chain integrity of a canonical ledger."""
    path = Path(args.ledger_path)
    res = verify_registry(path)
    if res["valid"]:
        print(f"Ledger verification: PASS ({res['records']} records, head: {res.get('head_hash')})")
        return 0
    else:
        print(f"Ledger verification: FAIL at index {res.get('failure_index')}: {res.get('reason')}", file=sys.stderr)
        return 1


def cmd_project_parquet(args: argparse.Namespace) -> int:
    """Project a canonical ledger to a ZSTD-compressed Parquet file."""
    try:
        res = project_to_parquet_zstd(args.ledger_path, args.out_path)
        print(f"Parquet projection: SUCCESS")
        print(f"  Records: {res['record_count']}")
        print(f"  Bytes:   {res['file_size_bytes']}")
        print(f"  SHA-256: {res['parquet_sha256']}")
        return 0
    except Exception as exc:
        print(f"Parquet projection: FAIL - {exc}", file=sys.stderr)
        return 1


def cmd_smoke_test(args: argparse.Namespace) -> int:
    """Run end-to-end smoke test: ledger -> validation -> Parquet ZSTD -> verify parity."""
    print("Running Edge Brain Smoke Test...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        ledger_path = tmp_path / "brain_smoke.jsonl"
        parquet_path = tmp_path / "brain_smoke.parquet"

        # 1. Append valid typed records
        r1 = append_typed_record(
            ledger_path,
            record_type="analysis_episode",
            record_id="EPISODE-SMOKE-001",
            payload={
                "episode_id": "EPISODE-SMOKE-001",
                "goal": "Verify smoke test flow",
                "status": "COMPLETED",
                "step_ids": ["STEP-001"],
                "expectation_ids": ["EXP-001"],
                "context_pack_id": "CTX-001",
                "created_at_utc": "2026-09-20T00:00:00Z",
                "updated_at_utc": "2026-09-20T00:05:00Z",
                "recorded_by": "smoke_test_runner",
                "outcomes_inspected": False,
            },
            recorded_at_utc="2026-09-20T00:05:00Z",
        )

        r2 = append_typed_record(
            ledger_path,
            record_type="step_execution",
            record_id="STEP-001",
            payload={
                "step_id": "STEP-001",
                "episode_id": "EPISODE-SMOKE-001",
                "step_index": 0,
                "action": "execute_probe",
                "tool_name": "probe_tool",
                "status": "SUCCESS",
                "input_params": {"threshold": 1.5},
                "output_summary": "Invariants hold",
                "executed_at_utc": "2026-09-20T00:02:00Z",
            },
            recorded_at_utc="2026-09-20T00:05:10Z",
        )

        # 2. Verify ledger integrity
        v = verify_registry(ledger_path)
        assert v["valid"] is True, "Ledger integrity verification failed"
        print("  [PASS] 1. Append-only ledger hash-chain valid")

        # 3. Project to Parquet ZSTD
        proj_meta = project_to_parquet_zstd(ledger_path, parquet_path)
        assert proj_meta["record_count"] == 2
        assert parquet_path.is_file()
        print(f"  [PASS] 2. Reconstructible Parquet ZSTD projection created ({proj_meta['file_size_bytes']} bytes)")

        # 4. Read Parquet and compare record_id, record_hash, and payload
        reconstructed = read_parquet_projection(parquet_path)
        assert len(reconstructed) == 2, f"Expected 2 reconstructed records, got {len(reconstructed)}"
        for orig, recon in zip([r1, r2], reconstructed):
            assert orig["record_id"] == recon["record_id"], "record_id mismatch"
            assert orig["record_hash"] == recon["record_hash"], "record_hash mismatch"
            assert orig["payload"] == recon["payload"], "payload mismatch"
        print("  [PASS] 3. Parquet ZSTD parity confirmed bit-for-bit with canonical ledger")

    print("Smoke test: ALL CHECKS PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="EdgeLab Edge Brain CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # schemas
    subparsers.add_parser("schemas", help="List and validate all 35 Edge Brain schemas")

    # validate-atlas
    p_atlas = subparsers.add_parser("validate-atlas", help="Validate a measurement atlas catalog file")
    p_atlas.add_argument("atlas_path", help="Path to measurement atlas JSON file")

    # verify-ledger
    p_verify = subparsers.add_parser("verify-ledger", help="Verify hash-chain integrity of a ledger")
    p_verify.add_argument("ledger_path", help="Path to ledger JSONL file")

    # project-parquet
    p_proj = subparsers.add_parser("project-parquet", help="Project ledger to Parquet ZSTD")
    p_proj.add_argument("ledger_path", help="Source ledger JSONL path")
    p_proj.add_argument("out_path", help="Target Parquet path")

    # smoke-test
    subparsers.add_parser("smoke-test", help="Run end-to-end smoke test")

    args = parser.parse_args()
    if args.command == "schemas":
        return cmd_schemas(args)
    elif args.command == "validate-atlas":
        return cmd_validate_atlas(args)
    elif args.command == "verify-ledger":
        return cmd_verify_ledger(args)
    elif args.command == "project-parquet":
        return cmd_project_parquet(args)
    elif args.command == "smoke-test":
        return cmd_smoke_test(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
