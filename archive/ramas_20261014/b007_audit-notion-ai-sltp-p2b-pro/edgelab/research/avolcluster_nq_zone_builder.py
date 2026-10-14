# -*- coding: utf-8 -*-
"""Deterministic target-free builder primitives for the NQ-120t zone store."""
from __future__ import annotations

import json
import os
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from edgelab.bridge.indicators.avolclusterpoi import SessionProfile, detect_block
from edgelab.research.avolcluster_nq_zone_store import (
    build_creation_event,
    projected_frozen_payload_sha256,
    validate_zone_rows,
)
from edgelab.research.event_store_contract import (
    EventStoreContractError,
    canonical_sha256,
)

NS = 1_000_000_000


def cme_session_dates(ts_ns: np.ndarray) -> np.ndarray:
    """Trade-date labels using the same 17:00 CT rule as the selection sweep."""
    dt = pd.to_datetime(np.asarray(ts_ns, dtype=np.int64), unit="ns", utc=True).tz_convert(
        "America/Chicago"
    )
    trade_dt = dt + pd.to_timedelta(np.where(dt.hour >= 17, 1, 0), unit="D")
    return trade_dt.strftime("%Y%m%d").to_numpy()


def profile_snapshot(profile: SessionProfile) -> dict[str, Any]:
    if any(profile.pending.values()):
        raise EventStoreContractError("profile snapshot requires an empty pending buffer")
    history: dict[str, list[dict[str, Any]]] = {}
    for bucket in sorted(profile.history):
        history[str(int(bucket))] = [
            {"session_index": int(session_index), "scores": [float(x) for x in scores]}
            for session_index, scores in profile.history[bucket]
        ]
    state = {
        "schema_version": "avolcluster_session_profile_state_v1",
        "lookback_sessions": int(profile.lookback),
        "next_session_index": int(profile.session_index),
        "history": history,
    }
    state["payload_sha256"] = canonical_sha256(state)
    return state


def profile_from_snapshot(state: Mapping[str, Any]) -> SessionProfile:
    if state.get("schema_version") != "avolcluster_session_profile_state_v1":
        raise EventStoreContractError("unsupported SessionProfile snapshot schema")
    expected_hash = canonical_sha256({k: v for k, v in state.items() if k != "payload_sha256"})
    if state.get("payload_sha256") != expected_hash:
        raise EventStoreContractError("SessionProfile snapshot hash mismatch")
    lookback = int(state["lookback_sessions"])
    profile = SessionProfile(lookback_sessions=lookback)
    profile.session_index = int(state["next_session_index"])
    profile.pending = defaultdict(list)
    profile.history = defaultdict(deque)
    history = state.get("history")
    if not isinstance(history, Mapping):
        raise EventStoreContractError("SessionProfile history must be an object")
    for raw_bucket, entries in history.items():
        bucket = int(raw_bucket)
        if not isinstance(entries, list):
            raise EventStoreContractError("SessionProfile bucket entries must be a list")
        q: deque[tuple[int, list[float]]] = deque()
        for entry in entries:
            session_index = int(entry["session_index"])
            scores = [float(x) for x in entry["scores"]]
            if not all(np.isfinite(scores)):
                raise EventStoreContractError("non-finite score in SessionProfile snapshot")
            q.append((session_index, scores))
        profile.history[bucket] = q
    return profile


def build_session_creation_events(
    *,
    bars: Any,
    footprints: Any,
    bar_indices: np.ndarray,
    profile: SessionProfile,
    spec: Mapping[str, Any],
    contract: str,
    session_id: str,
    session_ordinal: int,
    source_data_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one registered session and commit its detector history exactly once."""
    idx = np.asarray(bar_indices, dtype=np.int64)
    if idx.size and (np.diff(idx) <= 0).any():
        raise EventStoreContractError("session bar indices must be strictly increasing")
    detector = spec["detector"]
    window = int(detector["window_bars"])
    events: list[dict[str, Any]] = []
    n_blocks = int(idx.size // window)
    session_start_ns = int(bars.start_ns[idx[0]]) if idx.size else None

    for block_index in range(n_blocks):
        block_bars = idx[block_index * window:(block_index + 1) * window]
        cells: dict[int, float] = {}
        for bar_index in block_bars:
            for price_tick, volume in footprints.total[int(bar_index)].items():
                tick = int(price_tick)
                cells[tick] = cells.get(tick, 0.0) + float(volume)
        end_bar = int(block_bars[-1])
        elapsed_minutes = int((int(bars.end_ns[end_bar]) - session_start_ns) // (60 * NS))
        bucket = min(int(elapsed_minutes // int(detector["time_bucket_minutes"])), 45)
        history_scores = profile.history_scores(bucket)
        history_session_count = profile.history_session_count(bucket)
        result = detect_block(
            cells,
            history_scores,
            close_tick=int(bars.close_t[end_bar]),
            params={
                "window_bars": window,
                "median_multiplier": float(detector["median_multiplier"]),
                "max_gap_ticks": int(detector["max_gap_ticks"]),
                "min_cluster_ticks": int(detector["min_cluster_ticks"]),
                "time_bucket_minutes": int(detector["time_bucket_minutes"]),
                "lookback_sessions": int(detector["lookback_sessions"]),
                "detection_percentile": float(detector["detection_percentile"]),
                "min_samples_per_bucket": int(detector["min_samples_per_bucket"]),
                "one_cluster_per_block": True,
            },
        )
        profile.add_block(bucket, result["best_score"])
        for zone in result.get("zones", []):
            if zone.get("kind") != "OFF_PRICE":
                continue
            created_ts = int(bars.end_ns[end_bar])
            events.append(build_creation_event(
                spec,
                contract=contract,
                session_id=session_id,
                session_ordinal=int(session_ordinal),
                block_index=block_index,
                block_start_bar_index=block_index * window,
                block_end_bar_index=(block_index + 1) * window - 1,
                created_ts_utc_ns=created_ts,
                # This is an exclusive causal boundary, not a fabricated market tick.
                availability_ts_utc_ns=created_ts + 1,
                lower_tick=int(zone["lower_tick"]),
                upper_tick=int(zone["upper_tick"]),
                close_tick=int(bars.close_t[end_bar]),
                zone_score=float(zone["score"]),
                detection_threshold=float(zone["threshold"]),
                history_score_count=len(history_scores),
                history_session_count=history_session_count,
                source_data_sha256=source_data_sha256,
            ))

    profile.commit()
    normalized, diagnostics = validate_zone_rows(events, spec)
    diagnostics.update({
        "session_id": session_id,
        "contract": contract,
        "session_ordinal": int(session_ordinal),
        "bars": int(idx.size),
        "complete_blocks": n_blocks,
        "profile_next_session_index": int(profile.session_index),
    })
    return normalized, diagnostics


def checkpoint_payload(
    *,
    spec: Mapping[str, Any],
    contract: str,
    session_id: str,
    session_ordinal: int,
    source_data_sha256: str,
    code_commit: str,
    events: list[Mapping[str, Any]],
    diagnostics: Mapping[str, Any],
    profile: SessionProfile,
) -> dict[str, Any]:
    payload = {
        "schema_version": "avolcluster_nq_zone_store_checkpoint_v1",
        "spec_payload_sha256": projected_frozen_payload_sha256(spec),
        "contract": contract,
        "session_id": session_id,
        "session_ordinal": int(session_ordinal),
        "source_data_sha256": source_data_sha256,
        "code_commit": code_commit,
        "events": list(events),
        "diagnostics": dict(diagnostics),
        "profile_state_after_session": profile_snapshot(profile),
        "future_price_path_accessed": False,
        "pnl_accessed": False,
        "holdout_touched": False,
    }
    payload["payload_sha256"] = canonical_sha256(payload)
    return payload


def validate_checkpoint(
    payload: Mapping[str, Any],
    *,
    spec: Mapping[str, Any],
    expected_contract: str,
    expected_session_id: str,
    expected_ordinal: int,
    expected_source_sha256: str,
    expected_commit: str,
) -> SessionProfile:
    if payload.get("schema_version") != "avolcluster_nq_zone_store_checkpoint_v1":
        raise EventStoreContractError("unsupported checkpoint schema")
    expected_payload_hash = canonical_sha256({k: v for k, v in payload.items() if k != "payload_sha256"})
    if payload.get("payload_sha256") != expected_payload_hash:
        raise EventStoreContractError("checkpoint payload hash mismatch")
    expected = {
        "contract": expected_contract,
        "session_id": expected_session_id,
        "session_ordinal": expected_ordinal,
        "source_data_sha256": expected_source_sha256,
        "code_commit": expected_commit,
        "spec_payload_sha256": projected_frozen_payload_sha256(spec),
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise EventStoreContractError(f"checkpoint binding mismatch: {key}")
    if payload.get("future_price_path_accessed") is not False or payload.get("pnl_accessed") is not False:
        raise EventStoreContractError("checkpoint violates target-free firewall")
    events = payload.get("events")
    if not isinstance(events, list):
        raise EventStoreContractError("checkpoint events must be a list")
    normalized, _ = validate_zone_rows(events, spec)
    if any(row["contract"] != expected_contract or row["session_id"] != expected_session_id for row in normalized):
        raise EventStoreContractError("checkpoint contains events from another session")
    profile = profile_from_snapshot(payload["profile_state_after_session"])
    if profile.session_index != expected_ordinal + 1:
        raise EventStoreContractError("checkpoint profile ordinal mismatch")
    return profile


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    try:
        temp.write_text(text, encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def checkpoint_name(session_ordinal: int, contract: str, session_id: str) -> str:
    safe_contract = contract.replace(" ", "_")
    return f"{session_ordinal:03d}_{safe_contract}_{session_id}.json"
