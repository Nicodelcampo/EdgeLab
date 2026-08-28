#!/usr/bin/env python3
"""Fail-closed BT2A P2-A GC time-of-day heterogeneity runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for candidate in (ROOT, TOOLS):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import run_bt2a_gate2_p2a as p2a  # noqa: E402
from edgelab.research.all5_runtime.ticks import load_canonical_parquet  # noqa: E402
from edgelab.research.bt2_gate1_all5 import _context, _end, _labels, _start  # noqa: E402
from edgelab.research.bt2_gate1_outcomes import (  # noqa: E402
    _sample_without_own,
    build_path_cache,
    chicago_bin30,
)
from edgelab.research.bt2a_clock_heterogeneity import (  # noqa: E402
    PHASES,
    aggregate_clock_family,
)
from edgelab.research.bt2a_event_store import (  # noqa: E402
    canonical_sha256,
    file_sha256,
    validate_event_checkpoint,
    verify_file_sha256,
)
from edgelab.research.bt2a_gate2_first_passage import (  # noqa: E402
    first_passage_scores_fast,
    horizon_endpoints,
    next_barrier_touch_indices,
)
from edgelab.research.holdout_guard import check_holdout  # noqa: E402

SPEC_REL = "specs/bt2a_p2a_gc_clock_heterogeneity_v1.json"
SOURCE_SPEC_REL = "specs/bt2a_gate2_first_passage_v1.json"
MACRO_REL = "specs/bt2a_macro_calendar_gc_20250804_20260630_v1.json"
BRANCH = "research/bt2a-p2a-clock-heterogeneity-v1-20260827"
AUTH = "AUTHORIZE_BT2A_P2A_GC_CLOCK_HETEROGENEITY_V1"
SOURCE_SPEC_SHA256 = "176ca3e0c37f44823bfe5f8cf64849b55dcf12b5114d930d5ec8776c1566468c"
SOURCE_SPEC_FILE_SHA256 = "0705ae8377e91bd3fc4ed60ad712acd1b4e52b436e53d094dcdb957e8fbf08d5"
SOURCE_RESULT_SHA256 = "296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28"
EVENT_PAYLOAD_SHA256 = "feee6001e88aa69f62a092b253e468531230120a3dccdc2ceac0d488c9684cbd"
MACRO_FILE_SHA256 = "5f1a484858c7d0bdd997f7f6dafef014bae2f13debdb5bcce937d74257cbd9ca"
EXPECTED_CANONICAL_PARQUET_SHA256 = "6f7994b4ff21d2ddd0addcd9d3815b7ae83ff008b5b4774e74f2821efb2a4d77"
EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256 = "0ff77118098667991b88737e91ad58b29d1eb5fee5406d2a278983edf9ae9cee"
EXPECTED_FROZEN_COMMIT: str | None = None
PARENT_CELLS = ((9, 25), (30, 100), (30, 250))
CONTROL_REPLICATIONS = 10000
INFERENCE_REPLICATIONS = 10000
BASE_SEED = 20260827
HOLDOUT_NS = int(datetime(2026, 7, 1, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
CHICAGO = ZoneInfo("America/Chicago")


def canonical(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex}")
    temp.write_text(json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
    ) + "\n", encoding="utf-8")
    temp.replace(path)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def load_spec(root: Path = ROOT) -> dict:
    return load_json(root / SPEC_REL)


def frozen_spec_payload_sha256(spec: dict) -> str:
    from copy import deepcopy
    normalized = deepcopy(spec)
    if "freeze" in normalized and isinstance(normalized["freeze"], dict):
        normalized["freeze"]["frozen_spec_payload_sha256"] = None
    return canonical(normalized)


def frozen_contract_checks(spec: dict) -> dict[str, bool]:
    source = spec.get("source_p2a", {})
    inference = spec.get("inference", {})
    decision = spec.get("decision_rule", {})
    authorization = spec.get("authorization", {})
    firewall = spec.get("firewall", {})
    estimand = spec.get("estimand", {})
    freeze_meta = spec.get("freeze", {})
    parent = tuple(
        (int(row.get("barrier_ticks", -1)), int(row.get("horizon_ticks", -1)))
        for row in source.get("parent_cells_selected_post_outcome", [])
    )
    definitions = spec.get("phases", {}).get("definitions", [])
    phases = tuple(str(row.get("name")) for row in definitions)
    computed_hash = frozen_spec_payload_sha256(spec)
    bound = isinstance(EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256, str) and len(EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256) == 64
    return {
        "schema": spec.get("schema") == "bt2a_p2a_gc_clock_heterogeneity_v1",
        "status_frozen": spec.get("status") == "FROZEN_PREAUTHORIZATION",
        "freeze_authorized": authorization.get("freeze_authorized") is True,
        "execution_closed": authorization.get("execution_authorized") is False,
        "spec_payload_bound": bool(
            bound
            and freeze_meta.get("frozen_spec_payload_sha256") == computed_hash
            and EXPECTED_FROZEN_SPEC_PAYLOAD_SHA256 == computed_hash
        ),
        "minimum_other_phases": int(estimand.get("minimum_other_phases", -1)) == 3,
        "minimum_sessions_per_contrast": int(estimand.get("minimum_sessions_per_contrast", -1)) == 117,
        "heterogeneity_contrast": estimand.get("heterogeneity_contrast") == "D_session_cell_phase - mean(D_session_cell_all_three_other_phases)",
        "source_result": source.get("result_payload_sha256") == SOURCE_RESULT_SHA256,
        "event_store": source.get("canonical_event_store_payload_sha256") == EVENT_PAYLOAD_SHA256,
        "canonical_parquet_declared": source.get("canonical_event_store_parquet_sha256") == EXPECTED_CANONICAL_PARQUET_SHA256,
        "parent_cells": parent == PARENT_CELLS,
        "parent_cells_post_selection": source.get("confirmatory_eligible") is False,
        "phases": phases == PHASES,
        "clock": spec.get("scope", {}).get("event_clock") == "FILL_TS_UTC_NS_FIRST_CANONICAL_ROW_STRICTLY_AFTER_SIGNAL",
        "nrand_replications": int(spec.get("nrand", {}).get("replications", -1)) == CONTROL_REPLICATIONS,
        "inference_replications": int(inference.get("replications", -1)) == INFERENCE_REPLICATIONS,
        "inference_method": inference.get("method") == "WEBB_SIX_POINT_WILD_CLUSTER_BY_CME_SESSION",
        "holm_family": inference.get("multiplicity") == "HOLM_OVER_12",
        "family_size": inference.get("primary_family") == "12_PHASE_VS_REST_CONTRASTS",
        "no_winner": decision.get("winner_selection_allowed") is False and decision.get("operating_window_selection_allowed") is False,
        "p2b_unchanged": decision.get("p2b_rule_change_allowed") is False,
        "macro_sha": spec.get("macro_exclusion", {}).get("calendar_file_sha256") == MACRO_FILE_SHA256,
        "authorization": authorization.get("execution_token") == AUTH and authorization.get("execution_authorized") is False,
        "holdout_closed": firewall.get("HOLDOUT_TOUCHED") is False,
        "pnl_closed": firewall.get("PNL_ACCESSED") is False,
        "p2b_closed": firewall.get("P2B_RUN") is False,
        "winner_closed": firewall.get("WINNER_SELECTED") is False,
        "edge_closed": firewall.get("EDGE_DECLARED") is False,
    }


def _iso_ns(value: str) -> int:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.timestamp() * 1_000_000_000)


def load_macro_intervals(path: Path) -> tuple[dict, list[tuple[int, int]]]:
    if file_sha256(path) != MACRO_FILE_SHA256:
        raise RuntimeError("ABSTAIN_MACRO_CALENDAR_SHA256_MISMATCH")
    value = load_json(path)
    if value.get("schema") != "bt2a_macro_calendar_v1" or value.get("status") != "FROZEN_RESEARCH_SOURCED":
        raise RuntimeError("ABSTAIN_INVALID_MACRO_CALENDAR")
    intervals: list[tuple[int, int]] = []
    identifiers: set[str] = set()
    for event in value.get("events", []):
        identifier = str(event.get("event_id", ""))
        if not identifier or identifier in identifiers or event.get("event_type") not in {"FOMC", "CPI", "NFP"}:
            raise RuntimeError("ABSTAIN_INVALID_MACRO_EVENT")
        identifiers.add(identifier)
        start = _iso_ns(event["release_utc"])
        if start >= HOLDOUT_NS:
            raise RuntimeError("ABSTAIN_MACRO_CALENDAR_TOUCHES_HOLDOUT")
        intervals.append((start, start + 300 * 1_000_000_000))
    if len(intervals) != 26:
        raise RuntimeError("ABSTAIN_MACRO_CALENDAR_COUNT_MISMATCH")
    return value, sorted(intervals)


def _git_checks(root: Path, *, expected_commit: str | None = None, require_commit: bool = False) -> dict[str, bool]:
    def run(*args):
        return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    branch = run("branch", "--show-current")
    status = run("status", "--porcelain")
    head = run("rev-parse", "HEAD")
    checks = {
        "git_available": branch.returncode == 0,
        "branch": branch.returncode == 0 and branch.stdout.strip() == BRANCH,
        "worktree_clean": status.returncode == 0 and not status.stdout.strip(),
    }
    commit_to_check = expected_commit or EXPECTED_FROZEN_COMMIT
    if commit_to_check is not None:
        checks["commit_exact"] = head.returncode == 0 and head.stdout.strip() == commit_to_check
    elif require_commit:
        checks["commit_exact"] = False
    return checks


def validate_clock_event_store(event_store_dir: Path, source_spec: dict) -> dict[str, Any]:
    """Validate Event Store for Clock Heterogeneity with deep logical identity policy."""
    root = Path(event_store_dir)
    expected = source_spec.get("canonical_event_store")
    checks: dict[str, bool] = {}
    errors: list[str] = []
    if not isinstance(expected, dict):
        return {"ready": False, "logical_identity": "FAIL", "physical_transport_identity": "MISSING", "checks": {}, "errors": ["missing canonical_event_store in source spec"]}

    manifest_path = root / "run_manifest.json"
    if not manifest_path.is_file():
        return {"ready": False, "logical_identity": "FAIL", "physical_transport_identity": "MISSING", "checks": {"manifest_exists": False}, "errors": ["missing run_manifest.json"]}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ready": False, "logical_identity": "FAIL", "physical_transport_identity": "MISSING", "checks": {"manifest_json": False}, "errors": [f"invalid run_manifest.json: {exc}"]}
    if not isinstance(manifest, dict):
        return {"ready": False, "logical_identity": "FAIL", "physical_transport_identity": "MISSING", "checks": {"manifest_object": False}, "errors": ["run manifest must be an object"]}

    checks["manifest_status"] = manifest.get("status") == source_spec.get("input", {}).get("required_manifest_status")
    checks["manifest_n_sessions"] = manifest.get("n_sessions") == expected.get("n_sessions")
    checks["manifest_n_events"] = manifest.get("n_events") == expected.get("n_events")
    checks["manifest_events_payload_sha256"] = manifest.get("events_payload_sha256") == expected.get("events_payload_sha256")
    checks["manifest_counts_by_contract"] = manifest.get("counts") == expected.get("counts_by_contract")

    # 1. Checkpoint validation (234 sessions)
    checkpoint_dir = root / "checkpoints"
    checkpoint_paths = sorted(checkpoint_dir.glob("session_*.json")) if checkpoint_dir.is_dir() else []
    wanted_n = int(expected.get("n_sessions", 234))
    wanted_names = [f"session_{i:03d}.json" for i in range(wanted_n)]
    checks["checkpoint_count"] = len(checkpoint_paths) == wanted_n
    checks["checkpoint_names"] = [p.name for p in checkpoint_paths] == wanted_names

    aggregate_events: list[dict[str, Any]] = []
    observed_counts: Counter[str] = Counter()
    checkpoint_errors: list[str] = []

    if checks["checkpoint_count"] and checks["checkpoint_names"]:
        for index, path in enumerate(checkpoint_paths):
            try:
                checkpoint = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(checkpoint, dict):
                    raise RuntimeError("checkpoint is not an object")
                if checkpoint.get("schema") != "bt2a_gate1_canonical_event_store_session_v1":
                    raise RuntimeError("checkpoint schema mismatch")
                if int(checkpoint.get("session_index", -1)) != index:
                    raise RuntimeError("checkpoint session_index mismatch")
                events = validate_event_checkpoint(
                    checkpoint,
                    contract=str(checkpoint.get("contract")),
                    session=str(checkpoint.get("cme_session")),
                    sample_registry_sha256=str(expected.get("sample_registry_payload_sha256")),
                    input_registry_sha256=str(expected.get("input_registry_payload_sha256")),
                )
                for event in events:
                    observed_counts[str(event["arm"])] += 1
                aggregate_events.extend(events)
            except Exception as exc:
                checkpoint_errors.append(f"{path.name}: {exc}")
                if len(checkpoint_errors) >= 10:
                    break

    checks["checkpoints_valid"] = not checkpoint_errors
    if checkpoint_errors:
        errors.extend(checkpoint_errors[:5])

    # Checkpoint logical identity
    if not checkpoint_errors and len(aggregate_events) == expected.get("n_events", 22202):
        computed_payload_sha256 = canonical_sha256(aggregate_events)
        checks["logical_events_payload_sha256"] = computed_payload_sha256 == expected.get("events_payload_sha256")
        checks["counts_total_match"] = dict(observed_counts) == expected.get("counts_total")
        ids = [str(e.get("event_id")) for e in aggregate_events]
        identities = [str(e.get("identity_sha256")) for e in aggregate_events]
        checks["unique_event_ids"] = len(ids) == len(set(ids))
        checks["unique_identity_sha256"] = len(identities) == len(set(identities))
    else:
        checks["logical_events_payload_sha256"] = False
        checks["counts_total_match"] = False
        checks["unique_event_ids"] = False
        checks["unique_identity_sha256"] = False

    # 2. Deep Parquet Logical & Schema Validation (Path B)
    parquet_meta = manifest.get("parquet") if isinstance(manifest.get("parquet"), dict) else {}
    parquet_path = root / str(parquet_meta.get("path") or "bt2a_gate1_canonical_events_all5.parquet")
    checks["parquet_exists"] = parquet_path.is_file()
    actual_parquet_sha256 = file_sha256(parquet_path) if parquet_path.is_file() else None

    parquet_events: list[dict[str, Any]] = []
    parquet_logical_valid = False
    if parquet_path.is_file():
        try:
            import pyarrow.parquet as pq
            parquet_table = pq.read_table(parquet_path)
            expected_cols = {
                "arm", "cme_session", "contract", "direction", "event_id",
                "fill_price_ticks", "fill_source_row", "fill_ts_utc_ns",
                "gate1_canonical_commit", "gate1_cap_driver",
                "gate1_horizon_end_source_row", "gate1_horizon_end_ts_utc_ns",
                "gate1_input_sha256", "gate1_runtime_sha256",
                "identity_sha256", "signal_source_row", "signal_ts_utc_ns"
            }
            schema_names = set(parquet_table.schema.names)
            checks["parquet_readable"] = True
            checks["parquet_schema_valid"] = expected_cols.issubset(schema_names)
            checks["parquet_n_events"] = parquet_table.num_rows == int(expected.get("n_events", 22202))

            df_parquet = parquet_table.to_pandas()
            for r in df_parquet.to_dict(orient="records"):
                row = {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items()}
                parquet_events.append(row)

            parquet_payload_sha256 = canonical_sha256(parquet_events)
            checks["parquet_logical_payload_sha256"] = parquet_payload_sha256 == expected.get("events_payload_sha256")

            p_ids = [str(e.get("event_id")) for e in parquet_events]
            p_identities = [str(e.get("identity_sha256")) for e in parquet_events]
            checks["parquet_unique_event_ids"] = len(p_ids) == len(set(p_ids))
            checks["parquet_unique_identity_sha256"] = len(p_identities) == len(set(p_identities))

            p_counts = Counter(str(e.get("arm")) for e in parquet_events)
            checks["parquet_counts_total"] = dict(p_counts) == expected.get("counts_total")

            # Validate exact 1:1 match between Parquet rows and checkpoint events
            checks["parquet_matches_checkpoints_1to1"] = (
                bool(aggregate_events) and (parquet_events == aggregate_events)
            )

            parquet_logical_valid = bool(
                checks["parquet_readable"]
                and checks["parquet_schema_valid"]
                and checks["parquet_n_events"]
                and checks["parquet_logical_payload_sha256"]
                and checks["parquet_unique_event_ids"]
                and checks["parquet_unique_identity_sha256"]
                and checks["parquet_counts_total"]
                and checks["parquet_matches_checkpoints_1to1"]
            )
        except Exception as exc:
            checks["parquet_readable"] = False
            checks["parquet_schema_valid"] = False
            checks["parquet_n_events"] = False
            checks["parquet_logical_payload_sha256"] = False
            checks["parquet_unique_event_ids"] = False
            checks["parquet_unique_identity_sha256"] = False
            checks["parquet_counts_total"] = False
            checks["parquet_matches_checkpoints_1to1"] = False
            errors.append(f"parquet deep validation failed: {exc}")
    else:
        checks["parquet_readable"] = False
        checks["parquet_schema_valid"] = False
        checks["parquet_n_events"] = False
        checks["parquet_logical_payload_sha256"] = False
        checks["parquet_unique_event_ids"] = False
        checks["parquet_unique_identity_sha256"] = False
        checks["parquet_counts_total"] = False
        checks["parquet_matches_checkpoints_1to1"] = False

    if actual_parquet_sha256 == EXPECTED_CANONICAL_PARQUET_SHA256 and parquet_logical_valid:
        parquet_transport_status = "CANONICAL_MATCH"
    elif actual_parquet_sha256 is not None and parquet_logical_valid:
        parquet_transport_status = "DIFFERENT_NON_BLOCKING"
    elif actual_parquet_sha256 is not None:
        parquet_transport_status = "CORRUPT_OR_INVALID"
    else:
        parquet_transport_status = "MISSING"

    ready = not errors and all(checks.values())
    return {
        "ready": ready,
        "logical_identity": "PASS" if (checks.get("logical_events_payload_sha256") and checks.get("parquet_logical_payload_sha256") and checks.get("parquet_matches_checkpoints_1to1")) else "FAIL",
        "physical_transport_identity": parquet_transport_status,
        "canonical_parquet_sha256": EXPECTED_CANONICAL_PARQUET_SHA256,
        "actual_parquet_sha256": actual_parquet_sha256,
        "events_payload_sha256": EVENT_PAYLOAD_SHA256,
        "n_events": len(aggregate_events),
        "n_sessions": wanted_n,
        "counts_total": dict(observed_counts),
        "checks": checks,
        "errors": errors,
    }


def preflight(root: Path, event_store_dir: Path, data_dir: Path, *, check_git: bool = True, expected_commit: str | None = None) -> dict:
    spec = load_spec(root)
    source_spec = load_json(root / SOURCE_SPEC_REL)
    frozen = frozen_contract_checks(spec)
    source_checks = {
        "payload": canonical(source_spec) == SOURCE_SPEC_SHA256,
        "frozen_constants": all(p2a.frozen_constant_checks(source_spec).values()),
        "result_binding": spec.get("source_p2a", {}).get("result_payload_sha256") == SOURCE_RESULT_SHA256,
    }
    registry, inputs, _ = _context(root)
    sessions = registry.get("sessions", [])
    sample_checks = {
        "n_sessions": len(sessions) == 234,
        "five_contracts": len({str(row.get("contract")) for row in sessions}) == 5,
        "pre_holdout": bool(sessions) and max(str(row.get("cme_session_id")) for row in sessions) <= "20260630",
    }
    identity = (
        validate_clock_event_store(event_store_dir, source_spec)
        if event_store_dir.is_dir()
        else {"ready": False, "checks": {"event_store_exists": False}, "errors": ["missing Event Store"]}
    )
    data_files = {
        str(contract): (data_dir / str(entry["parquet_file"])).is_file()
        for contract, entry in inputs.get("contracts", {}).items()
    }
    macro_path = root / MACRO_REL
    macro_checks = {"exists": macro_path.is_file(), "sha256": False, "valid": False}
    if macro_path.is_file():
        macro_checks["sha256"] = file_sha256(macro_path) == MACRO_FILE_SHA256
        if macro_checks["sha256"]:
            try:
                load_macro_intervals(macro_path)
                macro_checks["valid"] = True
            except RuntimeError:
                pass
    runtime_checks = p2a.runtime_environment_checks(root, source_spec)
    require_commit = spec.get("status") == "FROZEN_PREAUTHORIZATION"
    git_checks = _git_checks(root, expected_commit=expected_commit, require_commit=require_commit) if check_git else {"skipped_for_test": True}
    binding = spec.get("implementation_binding", {})
    impl_checks = {}
    sci_path = root / binding.get("scientific_module_repository_path", "")
    if sci_path.is_file() and binding.get("scientific_module_sha256"):
        impl_checks["scientific_module_sha256"] = file_sha256(sci_path) == binding["scientific_module_sha256"]
    else:
        impl_checks["scientific_module_sha256"] = False
    if binding.get("macro_calendar_file_sha256"):
        impl_checks["macro_calendar_sha256"] = macro_checks.get("sha256", False)
    else:
        impl_checks["macro_calendar_sha256"] = False
    source_p2a_spec_path = root / SOURCE_SPEC_REL
    if source_p2a_spec_path.is_file() and binding.get("source_p2a_spec_file_sha256"):
        impl_checks["source_spec_file_sha256"] = file_sha256(source_p2a_spec_path) == binding["source_p2a_spec_file_sha256"]
    else:
        impl_checks["source_spec_file_sha256"] = False
    if source_p2a_spec_path.is_file() and binding.get("source_p2a_spec_payload_sha256"):
        impl_checks["source_spec_payload_sha256"] = canonical(load_json(source_p2a_spec_path)) == binding["source_p2a_spec_payload_sha256"]
    else:
        impl_checks["source_spec_payload_sha256"] = False
    lock_path = root / "requirements" / "core-bridge-dev.lock"
    if lock_path.is_file() and binding.get("runtime_environment_lock_sha256"):
        impl_checks["runtime_lock_sha256"] = file_sha256(lock_path) == binding["runtime_environment_lock_sha256"]
    else:
        impl_checks["runtime_lock_sha256"] = False
    groups = (frozen, source_checks, sample_checks, data_files, macro_checks, runtime_checks, git_checks, impl_checks)
    ready = identity.get("ready") is True and all(all(group.values()) for group in groups)
    return {
        "schema": "bt2a_p2a_gc_clock_preflight_v1",
        "status": "PASS_READY_FOR_CLOCK_AUTHORIZATION" if ready else "NOT_READY",
        "spec_status": spec.get("status"),
        "spec_payload_sha256": canonical(spec),
        "frozen_contract": frozen,
        "source_p2a": source_checks,
        "sample": sample_checks,
        "event_store_identity": identity,
        "data_files_exist": data_files,
        "macro_calendar": macro_checks,
        "implementation_binding": impl_checks,
        "runtime_environment": runtime_checks,
        "git": git_checks,
        "P2A_OUTCOMES_ALREADY_OPENED": True,
        "NEW_ANALYTICAL_FAMILY_PREPARED": True,
        "NEW_ANALYTICAL_FAMILY_PARTIALLY_EXECUTED": True,
        "NEW_ANALYTICAL_FAMILY_EXECUTED": False,
        "FUTURE_PRICE_PATH_ACCESSED": True,
        "FUTURE_PRICE_PATH_ACCESSED_BY_PREPARATION": False,
        "PREMATURE_CLOCK_SESSIONS": 4,
        "PREMATURE_CHECKPOINTS_QUARANTINED": True,
        "PREMATURE_CHECKPOINTS_USED": False,
        "PNL_ACCESSED": False,
        "P2B_RUN": False,
        "L2_OUTCOMES_OPENED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "CONFIRMATORY_ELIGIBLE": False,
        "PROMOTION_ELIGIBLE": False,
    }


def _local_phase_masks(ts_ns: np.ndarray) -> dict[str, np.ndarray]:
    ts = np.asarray(ts_ns, dtype=np.int64)
    if not len(ts):
        raise RuntimeError("empty tick path")
    first = datetime.fromtimestamp(int(ts[0]) / 1e9, timezone.utc).astimezone(CHICAGO)
    last = datetime.fromtimestamp(int(ts[-1]) / 1e9, timezone.utc).astimezone(CHICAGO)
    first_offset = int(first.utcoffset().total_seconds())
    last_offset = int(last.utcoffset().total_seconds())
    if first_offset != last_offset:
        raise RuntimeError("ABSTAIN_DST_TRANSITION_INSIDE_CME_SESSION")
    local_seconds = ((ts // 1_000_000_000 + first_offset) % 86400).astype(np.int64)
    return {
        "ASIA_ETH": (local_seconds >= 17 * 3600) | (local_seconds < 1 * 3600),
        "EUROPE_PRE_RTH": (local_seconds >= 1 * 3600) & (local_seconds < 7 * 3600 + 20 * 60),
        "GC_RTH": (local_seconds >= 7 * 3600 + 20 * 60) & (local_seconds < 12 * 3600 + 30 * 60),
        "POST_RTH": (local_seconds >= 12 * 3600 + 30 * 60) & (local_seconds < 16 * 3600),
    }


def _macro_mask(ts_ns: np.ndarray, intervals: list[tuple[int, int]]) -> np.ndarray:
    ts = np.asarray(ts_ns, dtype=np.int64)
    mask = np.zeros(len(ts), dtype=bool)
    for start, end in intervals:
        if end <= int(ts[0]) or start > int(ts[-1]):
            continue
        mask |= (ts >= int(start)) & (ts < int(end))
    return mask


def _sample_nrand(abs_idx: np.ndarray, ts_ns: np.ndarray, cache, candidate_mask: np.ndarray,
                  *, replications: int, random_seed: int) -> np.ndarray:
    candidates = np.flatnonzero(np.asarray(candidate_mask, dtype=bool))
    bins = chicago_bin30(ts_ns[candidates])
    event_bins = chicago_bin30(ts_ns[abs_idx])
    candidate_groups = {
        key: candidates[(bins == key[0]) & (cache.cap_driver[candidates] == key[1])]
        for key in sorted(set(zip(bins.tolist(), cache.cap_driver[candidates].tolist())))
    }
    event_groups = {
        key: np.flatnonzero((event_bins == key[0]) & (cache.cap_driver[abs_idx] == key[1]))
        for key in sorted(set(zip(event_bins.tolist(), cache.cap_driver[abs_idx].tolist())))
    }
    for key, positions in event_groups.items():
        if len(candidate_groups.get(key, ())) - 1 < len(positions):
            raise ValueError(f"PRECONDITION_FAILED_SPARSE_PHASE_STRATUM {key}")
    rng = np.random.default_rng(int(random_seed))
    sampled = np.empty((int(replications), len(abs_idx)), dtype=np.int64)
    for replication in range(int(replications)):
        for key, positions in event_groups.items():
            sampled[replication, positions] = _sample_without_own(
                candidate_groups[key], abs_idx[positions], rng
            )
    return sampled


def _seed(label: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{BASE_SEED}|{label}".encode()).digest()[:8], "little") % (2**32 - 1)


def _score_cell(price, ts, sessions, abs_idx, abs_direction, sampled, touches,
                barrier: int, horizon: int) -> dict:
    ends, _ = horizon_endpoints(ts, sessions, tick_cap=int(horizon), clock_cap_seconds=None)
    abs_scores = first_passage_scores_fast(
        price, ts, sessions, fill_indices=abs_idx, directions=abs_direction,
        barrier_ticks=int(barrier), tick_cap=int(horizon), clock_cap_seconds=None,
        precomputed_touches=touches, precomputed_endpoints=ends,
    )
    flat_scores = first_passage_scores_fast(
        price, ts, sessions, fill_indices=sampled.reshape(-1),
        directions=np.tile(abs_direction, len(sampled)), barrier_ticks=int(barrier),
        tick_cap=int(horizon), clock_cap_seconds=None,
        precomputed_touches=touches, precomputed_endpoints=ends,
    ).reshape(sampled.shape)
    control_replication_means = flat_scores.mean(axis=1)
    k_abs = float(abs_scores.mean())
    nrand = float(np.median(control_replication_means))
    return {
        "barrier_ticks": int(barrier),
        "horizon_ticks": int(horizon),
        "n_K_ABS": len(abs_idx),
        "K_ABS_theta_fp": k_abs,
        "N_RAND_median_theta_fp": nrand,
        "K_ABS_minus_N_RAND": k_abs - nrand,
    }


def _checkpoint(output_dir: Path, index: int) -> Path:
    return output_dir / "checkpoints" / f"session_{index:03d}.json"


def run_session(root: Path, data_dir: Path, event_store_dir: Path, output_dir: Path,
                index: int, macro_intervals: list[tuple[int, int]]) -> dict:
    spec = load_spec(root)
    registry, inputs, gate1 = _context(root)
    row = registry["sessions"][int(index)]
    contract = str(row["contract"])
    session = str(row["cme_session_id"])
    check_holdout(
        datetime.fromtimestamp(_start(session) / 1e9, timezone.utc).isoformat(),
        datetime.fromtimestamp(_end(session) / 1e9, timezone.utc).isoformat(),
        purpose="development", caller="bt2a_p2a_gc_clock_heterogeneity",
    )
    source_path = event_store_dir / "checkpoints" / f"session_{index:03d}.json"
    source = load_json(source_path)
    events = validate_event_checkpoint(
        source, contract=contract, session=session,
        sample_registry_sha256=registry["registry_payload_sha256"],
        input_registry_sha256=inputs["registry_payload_sha256"],
    )
    abs_events = [event for event in events if event["arm"] == "K_ABS"]
    parquet = data_dir / inputs["contracts"][contract]["parquet_file"]
    verify_file_sha256(parquet, inputs["contracts"][contract]["parquet_sha256"])
    ticks = load_canonical_parquet(
        parquet, contract=contract, instrument="GC",
        start_utc_ns=_start(session), end_utc_ns=_end(session),
    )
    if len(ticks) == 0 or int(ticks.ts_ns[-1]) >= HOLDOUT_NS:
        raise RuntimeError("ABSTAIN_EMPTY_OR_HOLDOUT_PATH")
    sessions = _labels(ticks.ts_ns)
    if set(sessions.tolist()) != {session}:
        raise RuntimeError("ABSTAIN_FOREIGN_SESSION")
    abs_idx = p2a.map_indices(abs_events, ticks.sequence, ticks.ts_ns, ticks.price_ticks)
    abs_direction = np.asarray([event["direction"] for event in abs_events], dtype=np.int8)
    cache = build_path_cache(
        ticks.ts_ns, ticks.price_ticks, sessions,
        tick_cap=int(gate1["horizon"]["tick_cap"]),
        clock_cap_seconds=int(gate1["horizon"]["clock_cap_seconds"]),
    )
    if np.any(~cache.eligible[abs_idx]):
        raise RuntimeError("ABSTAIN_GATE1_INELIGIBLE_K_ABS")
    phase_masks = _local_phase_masks(ticks.ts_ns)
    macro_mask = _macro_mask(ticks.ts_ns, macro_intervals)
    touches_by_barrier = {
        barrier: next_barrier_touch_indices(ticks.price_ticks, sessions, barrier_ticks=barrier)
        for barrier in sorted({barrier for barrier, _ in PARENT_CELLS})
    }
    phase_rows = []
    assigned_nonmacro = np.zeros(len(ticks.ts_ns), dtype=bool)
    for mask in phase_masks.values():
        assigned_nonmacro |= mask & ~macro_mask
    for phase in PHASES:
        event_mask = phase_masks[phase][abs_idx] & ~macro_mask[abs_idx]
        phase_idx = abs_idx[event_mask]
        phase_direction = abs_direction[event_mask]
        if not len(phase_idx):
            phase_rows.append({"phase": phase, "status": "ABSTAIN_NO_K_ABS", "n_K_ABS": 0, "cells": []})
            continue
        candidate_mask = cache.eligible & phase_masks[phase] & ~macro_mask
        try:
            sampled = _sample_nrand(
                phase_idx, ticks.ts_ns, cache, candidate_mask,
                replications=CONTROL_REPLICATIONS,
                random_seed=_seed(f"nrand|{session}|{phase}"),
            )
        except ValueError as exc:
            phase_rows.append({
                "phase": phase,
                "status": "ABSTAIN_SPARSE_NRAND_STRATUM",
                "reason": str(exc),
                "n_K_ABS": len(phase_idx),
                "cells": [],
            })
            continue
        cells = [
            _score_cell(
                ticks.price_ticks, ticks.ts_ns, sessions, phase_idx, phase_direction,
                sampled, touches_by_barrier[barrier], barrier, horizon,
            )
            for barrier, horizon in PARENT_CELLS
        ]
        phase_rows.append({
            "phase": phase,
            "status": "COMPLETE",
            "n_K_ABS": len(phase_idx),
            "n_N_RAND_replications": CONTROL_REPLICATIONS,
            "nrand_anchor_matrix_sha256": p2a.array_sha(sampled),
            "cells": cells,
        })
    n_macro = int(np.sum(macro_mask[abs_idx]))
    n_maintenance = int(np.sum(~macro_mask[abs_idx] & ~assigned_nonmacro[abs_idx]))
    n_phase = sum(int(row["n_K_ABS"]) for row in phase_rows)
    if n_phase + n_macro + n_maintenance != len(abs_events):
        raise RuntimeError("ABSTAIN_K_ABS_PHASE_CONSERVATION_FAILURE")
    value = {
        "schema": "bt2a_p2a_gc_clock_session_v1",
        "status": "COMPLETE_AUTHORIZED_POST_SELECTION_CLOCK_SESSION",
        "session_index": int(index),
        "contract": contract,
        "cme_session": session,
        "spec_payload_sha256": canonical(spec),
        "source_event_checkpoint_sha256": canonical_sha256(source),
        "n_K_ABS_source": len(abs_events),
        "n_K_ABS_macro_excluded": n_macro,
        "n_K_ABS_maintenance_excluded": n_maintenance,
        "phases": phase_rows,
        "P2A_OUTCOMES_ALREADY_OPENED": True,
        "FUTURE_PRICE_PATH_ACCESSED": True,
        "PNL_ACCESSED": False,
        "P2B_RUN": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "confirmatory_eligible": False,
    }
    value["payload_sha256"] = canonical(value)
    atomic_json(_checkpoint(output_dir, index), value)
    return value


def _valid_existing_checkpoint(path: Path, spec_sha: str, index: int) -> bool:
    try:
        value = load_json(path)
        payload = value.pop("payload_sha256")
        return (
            payload == canonical(value)
            and value.get("session_index") == index
            and value.get("spec_payload_sha256") == spec_sha
        )
    except Exception:
        return False


def finalize(root: Path, event_store_dir: Path, output_dir: Path) -> dict:
    spec = load_spec(root)
    spec_sha = canonical(spec)
    rows = []
    for index in range(234):
        path = _checkpoint(output_dir, index)
        if not path.is_file():
            raise RuntimeError(f"missing clock checkpoint {index}")
        value = load_json(path)
        payload = value.pop("payload_sha256", None)
        if payload != canonical(value):
            raise RuntimeError(f"invalid clock checkpoint payload {index}")
        source = load_json(event_store_dir / "checkpoints" / f"session_{index:03d}.json")
        if (
            value.get("schema") != "bt2a_p2a_gc_clock_session_v1"
            or value.get("session_index") != index
            or value.get("spec_payload_sha256") != spec_sha
            or value.get("source_event_checkpoint_sha256") != canonical_sha256(source)
            or value.get("HOLDOUT_TOUCHED") is not False
            or value.get("P2B_RUN") is not False
            or value.get("PNL_ACCESSED") is not False
        ):
            raise RuntimeError(f"stale or invalid clock checkpoint {index}")
        value["payload_sha256"] = payload
        rows.append(value)
    aggregate = aggregate_clock_family(
        rows,
        parent_cells=PARENT_CELLS,
        phases=PHASES,
        replications=INFERENCE_REPLICATIONS,
        base_seed=BASE_SEED,
        min_other_phases=int(spec["estimand"]["minimum_other_phases"]),
        min_sessions=int(spec["estimand"]["minimum_sessions_per_contrast"]),
    )
    result = {
        "schema": "bt2a_p2a_gc_clock_heterogeneity_result_v1",
        "status": "COMPLETE_AUTHORIZED_POST_SELECTION_CLOCK_DIAGNOSTIC",
        "source_p2a_result_payload_sha256": SOURCE_RESULT_SHA256,
        "canonical_event_store_payload_sha256": EVENT_PAYLOAD_SHA256,
        "spec_payload_sha256": spec_sha,
        "n_sessions": len(rows),
        "n_K_ABS_source": sum(int(row["n_K_ABS_source"]) for row in rows),
        "n_K_ABS_macro_excluded": sum(int(row["n_K_ABS_macro_excluded"]) for row in rows),
        "n_K_ABS_maintenance_excluded": sum(int(row["n_K_ABS_maintenance_excluded"]) for row in rows),
        "clock_family": aggregate,
        "decision": aggregate["decision"],
        "P2A_OUTCOMES_ALREADY_OPENED": True,
        "NEW_ANALYTICAL_FAMILY_EXECUTED": True,
        "FUTURE_PRICE_PATH_ACCESSED": True,
        "PNL_ACCESSED": False,
        "P2B_RUN": False,
        "L2_OUTCOMES_OPENED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "confirmatory_eligible": False,
        "promotion_eligible": False,
    }
    result["payload_sha256"] = canonical(result)
    atomic_json(output_dir / "bt2a_p2a_gc_clock_heterogeneity_result.json", result)
    return result


def require_authorization(token: str | None) -> None:
    if token != AUTH:
        raise SystemExit("ABSTAIN_MISSING_EXPLICIT_CLOCK_AUTHORIZATION")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--event-store-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--session-index", type=int)
    modes.add_argument("--run-all", action="store_true")
    modes.add_argument("--finalize", action="store_true")
    parser.add_argument("--authorization-token")
    parser.add_argument("--expected-commit", help="Exact git commit SHA to verify against HEAD")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    event_store = args.event_store_dir.resolve()
    data_dir = args.data_dir.resolve()
    if not args.preflight_only:
        if args.expected_commit is None:
            raise SystemExit("ABSTAIN_MANDATORY_EXPECTED_COMMIT_REQUIRED_FOR_EXECUTION")
        git_checks = _git_checks(root, expected_commit=args.expected_commit, require_commit=True)
        if not git_checks.get("commit_exact", False):
            raise SystemExit("ABSTAIN_COMMIT_MISMATCH_AGAINST_EXPECTED_COMMIT")
        require_authorization(args.authorization_token)
    readiness = preflight(root, event_store, data_dir, expected_commit=args.expected_commit)
    if args.preflight_only:
        print(json.dumps(readiness, indent=2, sort_keys=True))
        return 0 if readiness["status"] == "PASS_READY_FOR_CLOCK_AUTHORIZATION" else 2
    if readiness["status"] != "PASS_READY_FOR_CLOCK_AUTHORIZATION":
        raise SystemExit("ABSTAIN_CLOCK_PREFLIGHT_NOT_READY")
    if args.output_dir is None:
        raise SystemExit("--output-dir required")
    output = args.output_dir.resolve()
    _, macro_intervals = load_macro_intervals(root / MACRO_REL)
    spec_sha = canonical(load_spec(root))
    if args.finalize:
        result = finalize(root, event_store, output)
    elif args.run_all:
        completed = 0
        for index in range(234):
            path = _checkpoint(output, index)
            if path.is_file():
                if not _valid_existing_checkpoint(path, spec_sha, index):
                    raise SystemExit(f"ABSTAIN_STALE_CLOCK_CHECKPOINT_{index:03d}")
                continue
            run_session(root, data_dir, event_store, output, index, macro_intervals)
            completed += 1
        result = {"status": "SESSION_RUN_COMPLETE", "new_checkpoints": completed, "expected_checkpoints": 234}
    else:
        if args.session_index is None or not 0 <= args.session_index < 234:
            raise SystemExit("ABSTAIN_SESSION_INDEX_OUT_OF_RANGE")
        result = run_session(root, data_dir, event_store, output, args.session_index, macro_intervals)
    print(json.dumps({key: value for key, value in result.items() if key not in {"phases", "clock_family"}}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
