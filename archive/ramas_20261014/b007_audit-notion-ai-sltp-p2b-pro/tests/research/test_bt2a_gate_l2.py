from __future__ import annotations

import pandas as pd
import pytest

from edgelab.research.bt2a_gate_l2 import (
    attach_context_strict,
    context_interaction_test,
    context_width_correlation,
    validate_context_labels,
    validate_run_identity,
)


def contexts():
    return pd.DataFrame({
        "contract": ["GC", "GC", "GC", "GC"],
        "cme_session": ["S1", "S1", "S2", "S2"],
        "available_source_row": [10, 20, 10, 20],
        "context_state": ["normal", "volatile", "calm", "toxic"],
        "context_group": ["G-operable", "G-stress", "G-operable", "G-stress"],
        "context_as_of_ok": [True, True, True, True],
        "context_model_id": ["m", "m", "m", "m"],
    })


def test_strict_join_rejects_equal_source_row():
    events = pd.DataFrame({
        "event_id": ["equal", "after", "none"],
        "contract": ["GC", "GC", "GC"],
        "cme_session": ["S1", "S1", "S1"],
        "event_source_row": [10, 21, 5],
    })
    joined, report = attach_context_strict(events, contexts())
    assert not bool(joined.loc[0, "context_as_of_ok"])
    assert bool(joined.loc[1, "context_as_of_ok"])
    assert joined.loc[1, "context_available_source_row"] == 20
    assert not bool(joined.loc[2, "context_as_of_ok"])
    assert report["n_as_of_ok"] == 1
    assert report["strict_inequality"] is True


def test_context_readiness_fails_minimum_sessions_without_changing_labels():
    got = validate_context_labels(contexts(), minimum_sessions_per_group=3)
    assert got.coverage == 1.0
    assert got.state_group_mapping_ok
    assert not got.minimum_sessions_ok
    assert not got.ready_for_outcomes


def test_mapping_mismatch_fails_closed():
    bad = contexts()
    bad.loc[0, "context_group"] = "G-stress"
    got = validate_context_labels(bad, minimum_sessions_per_group=1)
    assert not got.state_group_mapping_ok
    assert not got.ready_for_outcomes


def test_physical_source_row_regression_is_not_hidden_by_sorting():
    bad = contexts()
    bad.loc[0, "available_source_row"] = 30
    got = validate_context_labels(bad, minimum_sessions_per_group=1)
    assert not got.monotone_source_rows
    assert not got.ready_for_outcomes


def test_width_correlation_gate():
    frame = pd.DataFrame({
        "context_group": ["G-operable", "G-stress"] * 4,
        "zone_width_ticks": [5, 6, 7, 8, 6, 7, 8, 9],
        "context_as_of_ok": [True] * 8,
    })
    got = context_width_correlation(frame)
    assert got["n"] == 8
    assert isinstance(got["passes"], bool)


def test_interaction_is_direct_difference_of_differences():
    rows = []
    for i in range(4):
        rows += [
            {"cme_session": f"O{i}", "context_group": "G-operable", "arm": "K_ABS", "score_fp": 0.6},
            {"cme_session": f"O{i}", "context_group": "G-operable", "arm": "N_RAND", "score_fp": 0.1},
        ]
    for i in range(4):
        rows += [
            {"cme_session": f"S{i}", "context_group": "G-stress", "arm": "K_ABS", "score_fp": 0.2},
            {"cme_session": f"S{i}", "context_group": "G-stress", "arm": "N_RAND", "score_fp": 0.1},
        ]
    got = context_interaction_test(pd.DataFrame(rows), minimum_sessions_per_group=4,
                                   replications=200, seed=3)
    assert got["status"] == "CONTEXT_INTERACTION_ESTIMATED"
    assert got["point"] == pytest.approx(0.4)
    assert got["edge_declared"] is False


def test_interaction_abstains_before_reading_small_cells():
    rows = pd.DataFrame({
        "cme_session": ["A", "A", "B", "B"],
        "context_group": ["G-operable", "G-operable", "G-stress", "G-stress"],
        "arm": ["K_ABS", "N_RAND", "K_ABS", "N_RAND"],
        "score_fp": [1.0, 0.0, -1.0, 0.0],
    })
    got = context_interaction_test(rows, minimum_sessions_per_group=40)
    assert got["status"] == "CONTEXT_INCONCLUSIVE_LOW_POWER"
    assert got["outcomes_interpreted"] is False


def test_run_identity_detects_dirty_or_mixed_run():
    manifest = {
        "status": "COMPLETE_TARGET_FREE_CONTEXT_EXTRACTION", "model_id": "m",
        "CAMPAIGN_OUTCOMES_OPENED": False, "EDGE_DECLARED": False,
        "code_commit_start": "a", "code_commit_end": "a",
        "dirty_start": True, "dirty_end": True,
    }
    got = validate_run_identity(manifest, {"model_id": "m"}, {"model_id": "m"})
    assert not got["clean_worktree"]
    assert not got["identity_ready"]
