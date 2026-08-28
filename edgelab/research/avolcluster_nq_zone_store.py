# -*- coding: utf-8 -*-
"""Fail-closed NQ-120t aVolClusterPOI zone-creation Event Store contract.

This stage contains signal-time geometry only.  It deliberately does not model
FIRST_TOUCH, invalidation, forward ranges, MFE, MAE, first passage or P&L.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from edgelab.research.event_store_contract import (
    EventStoreContractError,
    canonical_sha256,
    normalize_rows,
    stamp_identity,
)

SPEC_STATUS_DRAFT = "DRAFT_PREAUTHORIZATION_FAIL_CLOSED"
SPEC_STATUS_FROZEN = "FROZEN_ZONE_CREATION_EVENT_STORE"
EVENT_SCHEMA = "avolcluster_nq_zone_creation_event_v1"


def load_spec(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise EventStoreContractError(f"invalid spec JSON: {path}") from exc
    validate_spec(payload)
    return payload


def validate_spec(spec: Mapping[str, Any]) -> None:
    if spec.get("status") not in {SPEC_STATUS_DRAFT, SPEC_STATUS_FROZEN}:
        raise EventStoreContractError("unsupported spec status")
    population = spec.get("population", {})
    detector = spec.get("detector", {})
    selected = spec.get("target_free_selection", {}).get("selected_configuration", {})
    if population.get("instrument") != "NQ" or float(population.get("tick_size", 0)) != 0.25:
        raise EventStoreContractError("this contract is bound to NQ tick_size=0.25")
    required = {
        "config_id": "tick_120_W5_M20_C4_P950",
        "bar_type": "tick_120",
        "window_bars": 5,
        "median_multiplier": 2.0,
        "min_cluster_ticks": 4,
        "detection_percentile": 95.0,
    }
    for key, value in required.items():
        if selected.get(key) != value:
            raise EventStoreContractError(f"selected configuration drift: {key}")
    detector_required = {
        "tick_bar_size": 120,
        "window_bars": 5,
        "median_multiplier": 2.0,
        "max_gap_ticks": 1,
        "min_cluster_ticks": 4,
        "lookback_sessions": 20,
        "detection_percentile": 95.0,
        "min_samples_per_bucket": 10,
    }
    for key, value in detector_required.items():
        if detector.get(key) != value:
            raise EventStoreContractError(f"detector drift: {key}")
    epistemic = spec.get("epistemic_scope", {})
    if epistemic.get("future_price_path_accessed_by_this_stage") is not False:
        raise EventStoreContractError("zone-creation stage must not access future paths")
    if epistemic.get("pnl_accessed") is not False or epistemic.get("holdout_touched") is not False:
        raise EventStoreContractError("P&L and holdout must remain closed")
    lifecycle = spec.get("lifecycle", {})
    if lifecycle.get("first_touch_implemented") is not False:
        raise EventStoreContractError("first touch is outside this infrastructure stage")
    contract = spec.get("event_store", {}).get("contract")
    if not isinstance(contract, Mapping):
        raise EventStoreContractError("missing event_store.contract")
    # normalize_rows validates the contract even for an empty population.
    normalize_rows([], contract)


def spec_payload_for_freeze(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Non-circular scientific payload; mutable ceremony metadata is excluded."""
    excluded = {
        "status", "freeze_authorized", "execution_authorized", "frozen_at_utc",
        "frozen_commit", "frozen_spec_payload_sha256",
    }
    return {key: value for key, value in spec.items() if key not in excluded}


def projected_frozen_payload_sha256(spec: Mapping[str, Any]) -> str:
    validate_spec(spec)
    return canonical_sha256(spec_payload_for_freeze(spec))


def build_creation_event(
    spec: Mapping[str, Any],
    *,
    contract: str,
    session_id: str,
    session_ordinal: int,
    block_index: int,
    block_start_bar_index: int,
    block_end_bar_index: int,
    created_ts_utc_ns: int,
    availability_ts_utc_ns: int,
    lower_tick: int,
    upper_tick: int,
    close_tick: int,
    zone_score: float,
    detection_threshold: float,
    history_score_count: int,
    history_session_count: int,
    source_data_sha256: str,
) -> dict[str, Any]:
    validate_spec(spec)
    selected = spec["target_free_selection"]["selected_configuration"]
    if close_tick > upper_tick:
        side, distance = 1, close_tick - upper_tick
    elif close_tick < lower_tick:
        side, distance = -1, lower_tick - close_tick
    else:
        raise EventStoreContractError("creation event is not OFF_PRICE")
    natural_key = {
        "config_id": selected["config_id"],
        "contract": contract,
        "session_id": session_id,
        "block_index": block_index,
        "created_ts_utc_ns": created_ts_utc_ns,
        "lower_tick": lower_tick,
        "upper_tick": upper_tick,
    }
    row = {
        "schema_version": EVENT_SCHEMA,
        "event_id": canonical_sha256(natural_key),
        "identity_sha256": "",
        "event_type": "ZONE_CREATED",
        "instrument": "NQ",
        "contract": contract,
        "session_id": session_id,
        "config_id": selected["config_id"],
        "session_ordinal": session_ordinal,
        "block_index": block_index,
        "block_start_bar_index": block_start_bar_index,
        "block_end_bar_index": block_end_bar_index,
        "created_ts_utc_ns": created_ts_utc_ns,
        "availability_ts_utc_ns": availability_ts_utc_ns,
        "bar_type": selected["bar_type"],
        "lower_tick": lower_tick,
        "upper_tick": upper_tick,
        "width_ticks": upper_tick - lower_tick + 1,
        "close_tick": close_tick,
        "geometric_side": side,
        "distance_ticks": distance,
        "zone_score": zone_score,
        "detection_threshold": detection_threshold,
        "history_score_count": history_score_count,
        "history_session_count": history_session_count,
        "source_data_sha256": source_data_sha256,
    }
    return stamp_identity(row, spec["event_store"]["contract"])


def validate_zone_rows(
    rows: list[Mapping[str, Any]],
    spec: Mapping[str, Any],
    *,
    enforce_expected_counts: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    validate_spec(spec)
    normalized = normalize_rows(rows, spec["event_store"]["contract"])
    population = spec["population"]
    allowed_contracts = set(population["contracts"])
    holdout_start = str(population["holdout_session_id_min_inclusive"])
    seen_sessions: set[tuple[str, str]] = set()
    for row in normalized:
        if row["instrument"] != "NQ" or row["event_type"] != "ZONE_CREATED":
            raise EventStoreContractError("non-NQ or non-creation event in zone store")
        if row["contract"] not in allowed_contracts:
            raise EventStoreContractError(f"unexpected contract: {row['contract']}")
        if len(row["session_id"]) != 8 or not row["session_id"].isdigit():
            raise EventStoreContractError("session_id must be YYYYMMDD digits")
        if row["session_id"] >= holdout_start:
            raise EventStoreContractError("holdout session rejected", "ABSTAIN_HOLDOUT_FIREWALL")
        if row["bar_type"] != "tick_120" or row["config_id"] != "tick_120_W5_M20_C4_P950":
            raise EventStoreContractError("event detector identity drift")
        if row["block_end_bar_index"] - row["block_start_bar_index"] + 1 != 5:
            raise EventStoreContractError("zone block must contain exactly five 120-tick bars")
        if row["upper_tick"] < row["lower_tick"]:
            raise EventStoreContractError("upper_tick < lower_tick")
        if row["width_ticks"] != row["upper_tick"] - row["lower_tick"] + 1:
            raise EventStoreContractError("width_ticks mismatch")
        if row["availability_ts_utc_ns"] <= row["created_ts_utc_ns"]:
            raise EventStoreContractError("availability must be strictly after creation close")
        if row["geometric_side"] == 1:
            expected_distance = row["close_tick"] - row["upper_tick"]
        elif row["geometric_side"] == -1:
            expected_distance = row["lower_tick"] - row["close_tick"]
        else:
            raise EventStoreContractError("OFF_PRICE geometric_side must be -1 or 1")
        if expected_distance <= 0 or row["distance_ticks"] != expected_distance:
            raise EventStoreContractError("OFF_PRICE distance/side mismatch")
        if row["history_score_count"] < 10 or row["history_session_count"] < 1:
            raise EventStoreContractError("detector warmup evidence is insufficient")
        sha = row["source_data_sha256"]
        if len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
            raise EventStoreContractError("source_data_sha256 must be lowercase SHA-256")
        seen_sessions.add((row["contract"], row["session_id"]))

    expected = spec["target_free_selection"]["observed_summary"]
    if enforce_expected_counts:
        if len(normalized) != int(expected["off_price_events"]):
            raise EventStoreContractError(
                f"expected {expected['off_price_events']} creation events; got {len(normalized)}"
            )
        if len(seen_sessions) != int(expected["contract_sessions_with_off_price_events"]):
            raise EventStoreContractError(
                "contract-session coverage differs from the frozen target-free selection"
            )
    return normalized, {
        "rows": len(normalized),
        "contract_sessions_with_events": len(seen_sessions),
        "contracts_with_events": len({row["contract"] for row in normalized}),
        "session_min": min((row["session_id"] for row in normalized), default=None),
        "session_max": max((row["session_id"] for row in normalized), default=None),
        "logical_payload_sha256": canonical_sha256(normalized),
        "future_price_path_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
    }
