"""Synthetic ground-truth test suite for BT2A NQ Gate 1 runner.

T1 Discipline: 100% target-free, pure synthetic fixtures, hand-planted ground truth,
no real data, no lookahead, no PnL.
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from edgelab.research.bt2_gate1_outcomes import Event, build_path_cache
from edgelab.research.bt2a_nq_gate1_runner import (
    ALLOWED_DECISION_LABELS,
    SessionCellArmStat,
    aggregate_full_family_contrasts,
    decide_gate1_outcome,
    evaluate_session_cell_arm,
    permute_kabs_shuffle_indices,
    sample_nrand_strata_indices,
)
from edgelab.research.bt2a_nq_gate1_outcomes import (
    BARRIERS_TICKS,
    HORIZONS_OBSERVATIONS,
    all_cells,
    build_cell_cache,
    cell_id,
    compute_family,
    event_cell_values,
    unbiased_paired_session_variance,
)


def _make_event(key: str, fill_idx: int, direction: int = 1, session: str = "20260101") -> Event:
    return Event(
        key=key,
        arm="K_ABS",
        contract="NQ 09-25",
        session=session,
        direction=direction,
        signal_idx=fill_idx,
        signal_ts_ns=fill_idx * 1_000_000,
        signal_source_row=fill_idx,
        fill_idx=fill_idx,
    )


class TestStratumMatchingWithoutReplacement:
    def test_samples_without_replacement_when_capacity_sufficient(self):
        key1 = ("NQ 09-25", "20260101", 0, True, 2)
        key2 = ("NQ 09-25", "20260101", 1, True, 3)
        strata_demand = {key1: [10, 20, 30], key2: [40, 50]}
        candidate_pools = {
            key1: [100, 101, 102, 103, 104, 105],  # pool=6, needed=3 (6-1 >= 3)
            key2: [200, 201, 202, 203],            # pool=4, needed=2 (4-1 >= 2)
        }
        sampled = sample_nrand_strata_indices(strata_demand, candidate_pools, seed=42)
        assert len(sampled) == 5
        # All sampled from key1 must be unique and in pool1
        k1_sampled = sampled[:3]
        assert len(set(k1_sampled)) == 3
        assert all(idx in candidate_pools[key1] for idx in k1_sampled)
        # All sampled from key2 must be unique and in pool2
        k2_sampled = sampled[3:]
        assert len(set(k2_sampled)) == 2
        assert all(idx in candidate_pools[key2] for idx in k2_sampled)

    def test_fails_closed_when_pool_minus_one_less_than_demand(self):
        key = ("NQ 09-25", "20260101", 0, True, 2)
        strata_demand = {key: [10, 20, 30]}  # needed = 3
        candidate_pools = {key: [100, 101, 102]}  # pool = 3, pool-1 = 2 < 3 -> FAIL
        with pytest.raises(RuntimeError, match=r"\[FAIL_CLOSED\] Insufficient capacity"):
            sample_nrand_strata_indices(strata_demand, candidate_pools, seed=42)

    def test_sampling_is_strictly_deterministic(self):
        key = ("NQ 09-25", "20260101", 0, True, 1)
        strata_demand = {key: list(range(10))}
        candidate_pools = {key: list(range(100, 200))}
        s1 = sample_nrand_strata_indices(strata_demand, candidate_pools, seed=12345)
        s2 = sample_nrand_strata_indices(strata_demand, candidate_pools, seed=12345)
        assert s1 == s2


class TestShufflePermutationPreservesCounts:
    def test_preserves_event_counts_per_phase(self):
        ev_p0 = [_make_event(f"e0_{i}", fill_idx=i) for i in range(5)]
        ev_p1 = [_make_event(f"e1_{i}", fill_idx=i + 10) for i in range(8)]
        events_by_phase = {0: ev_p0, 1: ev_p1}
        candidate_indices = {
            0: list(range(100, 150)),
            1: list(range(200, 250)),
        }
        shuffled = permute_kabs_shuffle_indices(events_by_phase, candidate_indices, seed=99)
        assert len(shuffled) == 13
        p0_shuffled = shuffled[:5]
        p1_shuffled = shuffled[5:]
        assert len(set(p0_shuffled)) == 5
        assert all(idx in candidate_indices[0] for idx in p0_shuffled)
        assert len(set(p1_shuffled)) == 8
        assert all(idx in candidate_indices[1] for idx in p1_shuffled)


class TestPlantedOutcomes16Cells:
    def test_monotonic_favorable_price_path(self):
        n = 300
        prices = 100 + np.arange(n, dtype=np.int64)  # 100, 101, 102...
        ts = np.arange(n, dtype=np.int64) * 1_000_000
        sessions = np.full(n, "20260101", dtype=object)
        
        for horizon in HORIZONS_OBSERVATIONS:
            cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
            fill_idx = 10  # fill price is 110, has 289 ticks after >= 250
            for barrier in BARRIERS_TICKS:
                val = event_cell_values(
                    prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
                    barrier_ticks=barrier,
                )[0]
                # In monotonic upward path, MFE at horizon H is min(H, barrier), MAE is 0
                expected = min(float(horizon), float(barrier)) - 0.0
                assert val == pytest.approx(expected)

    def test_monotonic_adverse_price_path(self):
        n = 300
        prices = 500 - np.arange(n, dtype=np.int64)  # 500, 499, 498...
        ts = np.arange(n, dtype=np.int64) * 1_000_000
        sessions = np.full(n, "20260101", dtype=object)
        
        for horizon in HORIZONS_OBSERVATIONS:
            cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
            fill_idx = 10  # fill price is 490, has 289 ticks after >= 250
            for barrier in BARRIERS_TICKS:
                val = event_cell_values(
                    prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
                    barrier_ticks=barrier,
                )[0]
                # For long direction (+1), adverse path means MFE=0, MAE=min(H, barrier)
                expected = 0.0 - min(float(horizon), float(barrier))
                assert val == pytest.approx(expected)


class TestIncompletePathExclusion:
    def test_event_at_end_of_session_is_excluded_with_reason(self):
        n = 30
        prices = 100 + np.arange(n, dtype=np.int64)
        ts = np.arange(n, dtype=np.int64) * 1_000_000
        sessions = np.full(n, "20260101", dtype=object)
        
        horizon = 25
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        
        # Event 1: fill_idx = 2 (has 27 ticks after -> eligible)
        # Event 2: fill_idx = 20 (has only 9 ticks after < 25 -> ineligible)
        e1 = _make_event("e1", fill_idx=2)
        e2 = _make_event("e2", fill_idx=20)
        
        stat, exclusions = evaluate_session_cell_arm(
            [e1, e2], prices, cache,
            contract="NQ 09-25", session="20260101", arm="K_ABS",
            barrier_ticks=5, horizon_observations=horizon,
        )
        assert stat.n_events == 2
        assert stat.n_eligible == 1
        assert stat.n_excluded_incomplete == 1
        assert len(exclusions) == 1
        assert exclusions[0]["key"] == "e2"
        assert exclusions[0]["reason"] == "EXCLUDE_WITH_REASON_INCOMPLETE_PATH"
        assert stat.mean_value is not None


class TestSessionContrastsAndVariance:
    def test_unbiased_sample_variance_exact_hand_calculation(self):
        # 3 sessions with contrasts: 2.0, 4.0, 6.0
        # mean = 4.0
        # deviations = -2, 0, 2 -> squared = 4, 0, 4 -> sum = 8
        # ddof=1 -> variance = 8 / (3-1) = 4.0
        contrasts = [2.0, 4.0, 6.0]
        var = unbiased_paired_session_variance(contrasts)
        assert var == pytest.approx(4.0)

    def test_variance_requires_at_least_two_sessions(self):
        with pytest.raises(ValueError, match="requires >= 2 sessions"):
            unbiased_paired_session_variance([5.0])


class TestHolm16Monotonicity:
    def test_holm_16_family_result_structure(self):
        # Construct synthetic session means for 16 cells
        cells_input = {}
        for b, h in all_cells():
            cells_input[(b, h)] = {
                "K_ABS": {f"s_{i}": 5.0 + i * 0.1 for i in range(10)},
                "N_RAND": {f"s_{i}": 1.0 + i * 0.1 for i in range(10)},
            }
        result = compute_family(cells_input, replications=500, seed=123)
        assert result["family_size"] == 16
        assert len(result["cells"]) == 16
        for cid, data in result["cells"].items():
            assert "p_holm_16" in data
            assert 0.0 <= data["p_holm_16"] <= 1.0
            assert "p_two_sided" in data


class TestDecisionRule:
    def test_inconclusive_power_when_sessions_insufficient(self):
        family_res = {"cells": {cell_id(5, 25): {"p_holm_16": 0.001, "mean_contrast": 3.0, "ci_lower": 2.0}}}
        dec = decide_gate1_outcome(family_res, effective_sessions_available=200, effective_sessions_required=228)
        assert dec["decision"] == "BT2A_NQ_GATE1_INCONCLUSIVE_POWER"
        assert dec["EDGE_DECLARED"] is False
        assert dec["PROMOTION_ELIGIBLE"] is False
        assert dec["WINNER_SELECTED"] is False

    def test_supported_when_significant_cell_meets_mde_and_ci(self):
        family_res = {"cells": {
            cell_id(5, 25): {
                "p_holm_16": 0.002,
                "mean_contrast": 3.5,
                "ci_lower": 1.2,
            }
        }}
        dec = decide_gate1_outcome(family_res, effective_sessions_available=234, effective_sessions_required=228)
        assert dec["decision"] == "BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED"
        assert dec["positive_supported_cells"] == [cell_id(5, 25)]
        assert dec["EDGE_DECLARED"] is False

    def test_no_directional_mechanism_when_powered_but_not_significant(self):
        family_res = {"cells": {
            cell_id(5, 25): {
                "p_holm_16": 0.45,
                "mean_contrast": 0.2,
                "ci_lower": -0.8,
            }
        }}
        dec = decide_gate1_outcome(family_res, effective_sessions_available=234, effective_sessions_required=228)
        assert dec["decision"] == "BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM"
        assert dec["positive_supported_cells"] == []
        assert dec["EDGE_DECLARED"] is False

    def test_allowed_labels_are_strictly_enforced(self):
        for label in ALLOWED_DECISION_LABELS:
            assert isinstance(label, str)
            assert label.startswith("BT2A_NQ_GATE1_") or label.startswith("ABSTAIN_")
