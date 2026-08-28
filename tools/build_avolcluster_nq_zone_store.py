#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build/resume/finalize the target-free NQ-120t aVolClusterPOI zone store.

No mode scans post-creation outcomes.  --run-all remains disabled until the
creation contract is frozen and its dedicated build token is authorized.
Finalization has a separate authorization and is never implicit in --run-all.
"""
from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from edgelab.bridge.bars import build_footprints, build_tick_bars
from edgelab.bridge.indicators.avolclusterpoi import SessionProfile
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.research.avolcluster_nq_zone_builder import (
    atomic_write_json,
    build_session_creation_events,
    checkpoint_name,
    checkpoint_payload,
    cme_session_dates,
    validate_checkpoint,
)
from edgelab.research.avolcluster_nq_zone_store import (
    SPEC_STATUS_FROZEN,
    load_spec,
    projected_frozen_payload_sha256,
    validate_zone_rows,
)
from edgelab.research.event_store_contract import (
    EventStoreContractError,
    canonical_sha256,
    load_checkpoint_rows,
    sha256_file,
    validate_parquet_against_rows,
)
from tools.build_event_store_all5_v2 import expand_sessions

DEFAULT_SPEC = REPO_ROOT / "specs/avolcluster_nq_zone_event_store_v1.json"
DEFAULT_SESSION_REGISTRY = REPO_ROOT / "specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json"
DEFAULT_INPUT_REGISTRY = REPO_ROOT / "specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json"


def git_state() -> dict:
    def run(*args: str) -> str | None:
        proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
        return proc.stdout.strip() if proc.returncode == 0 else None
    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {
        "available": commit is not None,
        "commit": commit,
        "branch": run("branch", "--show-current") or "",
        "dirty": status is None or bool(status),
    }


def cme_session_start_utc_ns(session_id: str) -> int:
    """17:00 America/Chicago on the calendar day before the CME trade date."""
    trade_date = pd.Timestamp(datetime.strptime(session_id, "%Y%m%d").date())
    local_start = (trade_date - pd.Timedelta(days=1) + pd.Timedelta(hours=17)).tz_localize(
        "America/Chicago", ambiguous="raise", nonexistent="raise"
    )
    return int(local_start.tz_convert("UTC").value)


def next_calendar_session_start_utc_ns(session_id: str) -> int:
    next_day = datetime.strptime(session_id, "%Y%m%d") + timedelta(days=1)
    return cme_session_start_utc_ns(next_day.strftime("%Y%m%d"))


def load_registries(session_path: Path, input_path: Path) -> tuple[dict, dict, list[dict]]:
    try:
        sessions = json.loads(session_path.read_text(encoding="utf-8"))
        inputs = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EventStoreContractError("invalid or missing NQ registry") from exc
    if sessions.get("instrument") != "NQ" or inputs.get("instrument") != "NQ":
        raise EventStoreContractError("registries are not bound to NQ")
    expanded = expand_sessions(sessions)
    if len(expanded) != 234:
        raise EventStoreContractError(f"expected 234 registry rows; got {len(expanded)}")
    contracts = sessions["selection"]["contracts"]
    if contracts != inputs.get("selected_contracts"):
        raise EventStoreContractError("session/input registry contract order mismatch")
    for ordinal, row in enumerate(expanded):
        row["session_ordinal"] = ordinal
    return sessions, inputs, expanded


def require_execution(args: argparse.Namespace, spec: dict, gs: dict, token_key: str, flag_key: str) -> None:
    if spec["status"] != SPEC_STATUS_FROZEN:
        raise EventStoreContractError("creation Event Store spec is not frozen")
    if not args.expected_commit:
        raise EventStoreContractError("--expected-commit is mandatory")
    if not gs["available"] or gs["commit"] != args.expected_commit:
        raise EventStoreContractError("HEAD mismatch against --expected-commit")
    if gs["dirty"]:
        raise EventStoreContractError("dirty worktree")
    auth = spec["authorization"]
    if auth.get(flag_key) is not True or args.authorization_token != auth.get(token_key):
        raise EventStoreContractError("missing or invalid dedicated authorization")


def verify_input_file(data_dir: Path, contract: str, entry: dict) -> Path:
    path = data_dir / entry["parquet_file"]
    if not path.is_file():
        raise EventStoreContractError(f"missing source Parquet for {contract}: {path}")
    if path.stat().st_size != int(entry["bytes"]):
        raise EventStoreContractError(f"source byte-size mismatch for {contract}")
    actual = sha256_file(path)
    if actual != entry["parquet_sha256"]:
        raise EventStoreContractError(f"source SHA-256 mismatch for {contract}")
    return path


def scan_resume(
    checkpoints_dir: Path,
    expanded: list[dict],
    inputs: dict,
    spec: dict,
    expected_commit: str,
) -> tuple[int, SessionProfile]:
    profile = SessionProfile(lookback_sessions=int(spec["detector"]["lookback_sessions"]))
    first_missing = len(expanded)
    missing_seen = False
    for row in expanded:
        ordinal = int(row["session_ordinal"])
        path = checkpoints_dir / checkpoint_name(ordinal, row["contract"], row["cme_session_id"])
        if not path.exists():
            if not missing_seen:
                first_missing = ordinal
                missing_seen = True
            continue
        if missing_seen:
            raise EventStoreContractError("checkpoint set is not a contiguous prefix")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise EventStoreContractError(f"invalid checkpoint JSON: {path.name}") from exc
        source_sha = inputs["contracts"][row["contract"]]["parquet_sha256"]
        profile = validate_checkpoint(
            payload,
            spec=spec,
            expected_contract=row["contract"],
            expected_session_id=row["cme_session_id"],
            expected_ordinal=ordinal,
            expected_source_sha256=source_sha,
            expected_commit=expected_commit,
        )
    return first_missing, profile


def run_all(args: argparse.Namespace, spec: dict, inputs: dict, expanded: list[dict], gs: dict) -> dict:
    require_execution(args, spec, gs, "zone_store_build_token", "zone_store_build_authorized")
    if args.data_dir is None or args.output_dir is None:
        raise EventStoreContractError("--data-dir and --output-dir are mandatory for --run-all")
    checkpoints_dir = args.output_dir / "checkpoints"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    start, profile = scan_resume(checkpoints_dir, expanded, inputs, spec, args.expected_commit)
    remaining = expanded[start:]
    contracts_in_order = list(dict.fromkeys(row["contract"] for row in remaining))
    written = 0
    for contract in contracts_in_order:
        entry = inputs["contracts"][contract]
        source_path = verify_input_file(args.data_dir, contract, entry)
        contract_registry_rows = [row for row in expanded if row["contract"] == contract]
        start_ns = cme_session_start_utc_ns(contract_registry_rows[0]["cme_session_id"])
        end_ns = next_calendar_session_start_utc_ns(contract_registry_rows[-1]["cme_session_id"])
        # Predicate pushdown ensures out-of-registry and holdout rows are never decoded.
        ticks = load_canonical_parquet(
            source_path,
            contract=contract,
            instrument="NQ",
            start_utc_ns=start_ns,
            end_utc_ns=end_ns,
        )
        bars = build_tick_bars(ticks, 120, reiniciar_por_sesion=True)
        footprints = build_footprints(ticks, bars)
        bar_sessions = cme_session_dates(bars.end_ns)
        for row in (x for x in remaining if x["contract"] == contract):
            sid = row["cme_session_id"]
            indices = np.flatnonzero(bar_sessions == sid)
            events, diagnostics = build_session_creation_events(
                bars=bars,
                footprints=footprints,
                bar_indices=indices,
                profile=profile,
                spec=spec,
                contract=contract,
                session_id=sid,
                session_ordinal=int(row["session_ordinal"]),
                source_data_sha256=entry["parquet_sha256"],
            )
            payload = checkpoint_payload(
                spec=spec,
                contract=contract,
                session_id=sid,
                session_ordinal=int(row["session_ordinal"]),
                source_data_sha256=entry["parquet_sha256"],
                code_commit=args.expected_commit,
                events=events,
                diagnostics=diagnostics,
                profile=profile,
            )
            path = checkpoints_dir / checkpoint_name(int(row["session_ordinal"]), contract, sid)
            atomic_write_json(path, payload)
            written += 1
        del ticks, bars, footprints, bar_sessions
        gc.collect()
    total_checkpoints = len(list(checkpoints_dir.glob("*.json")))
    return {
        "status": "COMPLETE_TARGET_FREE_CHECKPOINT_BUILD" if total_checkpoints == len(expanded) else "PARTIAL_TARGET_FREE_CHECKPOINT_BUILD",
        "checkpoints_written_this_run": written,
        "checkpoint_files_total": total_checkpoints,
        "resume_start_ordinal": start,
        "ready_for_finalize": total_checkpoints == len(expanded),
        "finalize_executed": False,
        "future_price_path_accessed": False,
        "pnl_accessed": False,
        "holdout_rows_decoded": False,
    }


def finalize(args: argparse.Namespace, spec: dict, inputs: dict, expanded: list[dict], gs: dict) -> dict:
    require_execution(args, spec, gs, "zone_store_finalize_token", "zone_store_finalize_authorized")
    if args.output_dir is None:
        raise EventStoreContractError("--output-dir is mandatory for --finalize")
    checkpoints_dir = args.output_dir / "checkpoints"
    if len(list(checkpoints_dir.glob("*.json"))) != len(expanded):
        raise EventStoreContractError("expected exactly 234 checkpoint files")
    start, _ = scan_resume(checkpoints_dir, expanded, inputs, spec, args.expected_commit)
    if start != len(expanded):
        raise EventStoreContractError("checkpoint prefix is incomplete")
    rows, metadata = load_checkpoint_rows(checkpoints_dir)
    normalized, diagnostics = validate_zone_rows(rows, spec, enforce_expected_counts=True)
    parquet_path = args.output_dir / "avolcluster_nq_zone_creation_event_store.parquet"
    pq.write_table(pa.Table.from_pylist(normalized), parquet_path, compression="zstd")
    transport = validate_parquet_against_rows(parquet_path, normalized, spec["event_store"]["contract"])
    manifest = {
        "schema_version": "avolcluster_nq_zone_store_manifest_v1",
        "status": "COMPLETE_TARGET_FREE_ZONE_CREATION_STORE",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "code_commit": args.expected_commit,
        "spec_payload_sha256": projected_frozen_payload_sha256(spec),
        "input_registry_sha256": sha256_file(args.input_registry),
        "session_registry_sha256": sha256_file(args.session_registry),
        "checkpoint_files": len(metadata),
        "diagnostics": diagnostics,
        "parquet": transport,
        "future_price_path_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
        "edge_declared": False,
        "promotion_eligible": False,
    }
    manifest["payload_sha256"] = canonical_sha256(manifest)
    atomic_write_json(args.output_dir / "avolcluster_nq_zone_store_manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--session-registry", type=Path, default=DEFAULT_SESSION_REGISTRY)
    parser.add_argument("--input-registry", type=Path, default=DEFAULT_INPUT_REGISTRY)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--expected-commit")
    parser.add_argument("--authorization-token")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--run-all", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    args = parser.parse_args(argv)
    try:
        spec = load_spec(args.spec)
        _sessions, inputs, expanded = load_registries(args.session_registry, args.input_registry)
        gs = git_state()
        base = {
            "schema_version": "avolcluster_nq_zone_builder_status_v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "git_state": gs,
            "spec_status": spec["status"],
            "spec_payload_sha256": projected_frozen_payload_sha256(spec),
            "registry_sessions": len(expanded),
            "input_contracts": len(inputs["contracts"]),
            "future_price_path_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": False,
        }
        if args.preflight_only:
            if args.expected_commit is not None and gs["commit"] != args.expected_commit:
                raise EventStoreContractError("preflight commit mismatch")
            result = {
                **base,
                "status": "DRAFT_BUILDER_PREPARED" if spec["status"] != SPEC_STATUS_FROZEN else "FROZEN_BUILDER_PREFLIGHT",
                "run_all_authorized": bool(spec["authorization"]["zone_store_build_authorized"]),
                "finalize_authorized": bool(spec["authorization"]["zone_store_finalize_authorized"]),
                "ready_for_first_touch_or_outcomes": False,
                "review_blockers": spec["review_blockers"],
            }
        elif args.run_all:
            result = {**base, **run_all(args, spec, inputs, expanded, gs)}
        else:
            result = {**base, **finalize(args, spec, inputs, expanded, gs)}
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))
        return 0
    except EventStoreContractError as exc:
        payload = {
            "schema_version": "avolcluster_nq_zone_builder_status_v1",
            "status": exc.label,
            "message": str(exc),
            "future_price_path_accessed": False,
            "pnl_accessed": False,
            "holdout_touched": exc.label == "ABSTAIN_HOLDOUT_FIREWALL",
        }
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
