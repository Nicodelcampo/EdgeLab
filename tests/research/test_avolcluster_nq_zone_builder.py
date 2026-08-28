# -*- coding: utf-8 -*-
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from edgelab.bridge.indicators.avolclusterpoi import SessionProfile
from edgelab.research.avolcluster_nq_zone_builder import (
    build_session_creation_events,
    checkpoint_payload,
    profile_from_snapshot,
    profile_snapshot,
    validate_checkpoint,
)
from edgelab.research.event_store_contract import EventStoreContractError
from tools.build_avolcluster_nq_zone_store import (
    cme_session_start_utc_ns,
    next_calendar_session_start_utc_ns,
)

ROOT = Path(__file__).resolve().parents[2]


def spec():
    return json.loads((ROOT / "specs/avolcluster_nq_zone_event_store_v1.json").read_text("utf-8"))


def primed_profile():
    profile = SessionProfile(lookback_sessions=20)
    for _ in range(10):
        profile.add_block(0, 10.0)
        profile.commit()
    return profile


def synthetic_bars_and_footprints():
    bars = SimpleNamespace(
        start_ns=np.array([0, 100, 200, 300, 400, 500], dtype=np.int64),
        end_ns=np.array([99, 199, 299, 399, 499, 599], dtype=np.int64),
        close_t=np.array([110, 110, 110, 110, 110, 110], dtype=np.int64),
    )
    hot = {90: 1.0, 91: 1.0, 92: 1.0, 93: 1.0, 94: 1.0,
           100: 10.0, 101: 10.0, 102: 10.0, 103: 10.0}
    footprints = SimpleNamespace(total=[hot, {}, {}, {}, {}, {}])
    return bars, footprints


def test_profile_snapshot_roundtrip_preserves_history_and_next_index():
    profile = primed_profile()
    state = profile_snapshot(profile)
    restored = profile_from_snapshot(state)
    assert restored.session_index == 10
    assert restored.history_scores(0) == profile.history_scores(0)
    assert profile_snapshot(restored) == state


def test_profile_snapshot_detects_mutation():
    state = profile_snapshot(primed_profile())
    state["next_session_index"] = 99
    with pytest.raises(EventStoreContractError, match="snapshot hash mismatch"):
        profile_from_snapshot(state)


def test_selected_builder_emits_creation_only_and_commits_history():
    profile = primed_profile()
    bars, footprints = synthetic_bars_and_footprints()
    events, diagnostics = build_session_creation_events(
        bars=bars,
        footprints=footprints,
        bar_indices=np.arange(6),
        profile=profile,
        spec=spec(),
        contract="NQ 06-26",
        session_id="20260630",
        session_ordinal=10,
        source_data_sha256="a" * 64,
    )
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "ZONE_CREATED"
    assert event["lower_tick"] == 100 and event["upper_tick"] == 103
    assert event["created_ts_utc_ns"] == 499
    assert event["availability_ts_utc_ns"] == 500
    assert "first_touch_ts_utc_ns" not in event
    assert diagnostics["complete_blocks"] == 1
    assert profile.session_index == 11


def test_checkpoint_binds_spec_source_commit_session_and_profile():
    profile = primed_profile()
    bars, footprints = synthetic_bars_and_footprints()
    events, diagnostics = build_session_creation_events(
        bars=bars, footprints=footprints, bar_indices=np.arange(6), profile=profile,
        spec=spec(), contract="NQ 06-26", session_id="20260630", session_ordinal=10,
        source_data_sha256="a" * 64,
    )
    payload = checkpoint_payload(
        spec=spec(), contract="NQ 06-26", session_id="20260630", session_ordinal=10,
        source_data_sha256="a" * 64, code_commit="b" * 40,
        events=events, diagnostics=diagnostics, profile=profile,
    )
    restored = validate_checkpoint(
        payload, spec=spec(), expected_contract="NQ 06-26", expected_session_id="20260630",
        expected_ordinal=10, expected_source_sha256="a" * 64, expected_commit="b" * 40,
    )
    assert restored.session_index == 11
    payload["events"][0]["zone_score"] = 999.0
    with pytest.raises(EventStoreContractError, match="checkpoint payload hash mismatch"):
        validate_checkpoint(
            payload, spec=spec(), expected_contract="NQ 06-26", expected_session_id="20260630",
            expected_ordinal=10, expected_source_sha256="a" * 64, expected_commit="b" * 40,
        )


def test_registry_decode_bounds_stop_before_holdout_session():
    start = cme_session_start_utc_ns("20260630")
    end = next_calendar_session_start_utc_ns("20260630")
    assert pd.Timestamp(start, unit="ns", tz="UTC") == pd.Timestamp("2026-06-29T22:00:00Z")
    assert pd.Timestamp(end, unit="ns", tz="UTC") == pd.Timestamp("2026-06-30T22:00:00Z")
    assert end > start
