"""Synthetic ground-truth tests for edgelab.research.bt2a_nq_gate1_nrand_capacity.

Written before any real Kaggle/tick data, per the same T1 discipline. No raw
ticks, no real event store, no post-anchor computation anywhere in this file.
"""
from __future__ import annotations

import pytest

from edgelab.research.bt2a_nq_gate1_nrand_capacity import (
    INSUFFICIENT_HISTORY,
    MAX_HORIZON_OBSERVATIONS,
    PHASES_PER_SESSION,
    availability_flag,
    capacity_report,
    coarse_phase,
    compute_quintile_edges,
    local_volatility_bin,
    stratum_key,
)


class TestCoarsePhase:
    def test_six_phases_per_session(self):
        assert PHASES_PER_SESSION == 6

    def test_phase_zero_at_session_open(self):
        assert coarse_phase(0) == 0

    def test_phase_boundaries_are_exactly_four_hours(self):
        assert coarse_phase(239) == 0
        assert coarse_phase(240) == 1
        assert coarse_phase(479) == 1
        assert coarse_phase(480) == 2

    def test_last_phase_at_end_of_session(self):
        assert coarse_phase(23 * 60 + 59) == 5

    def test_rejects_unnormalized_input(self):
        with pytest.raises(ValueError):
            coarse_phase(-1)
        with pytest.raises(ValueError):
            coarse_phase(24 * 60)


class TestAvailabilityFlag:
    def test_exactly_at_max_horizon_is_available(self):
        assert availability_flag(MAX_HORIZON_OBSERVATIONS) is True

    def test_one_short_of_max_horizon_is_not_available(self):
        assert availability_flag(MAX_HORIZON_OBSERVATIONS - 1) is False

    def test_far_more_than_needed_is_available(self):
        assert availability_flag(MAX_HORIZON_OBSERVATIONS * 10) is True

    def test_zero_rows_after_is_not_available(self):
        assert availability_flag(0) is False


class TestLocalVolatilityBin:
    def test_insufficient_history_is_none_input(self):
        assert local_volatility_bin(None, [1.0, 2.0, 3.0, 4.0]) == INSUFFICIENT_HISTORY

    def test_below_first_edge_is_bin_zero(self):
        assert local_volatility_bin(0.5, [1.0, 2.0, 3.0, 4.0]) == 0

    def test_exactly_on_an_edge_is_not_above_it(self):
        # value == edge -> not "> edge" -> stays in the lower bin (ties go low)
        assert local_volatility_bin(2.0, [1.0, 2.0, 3.0, 4.0]) == 1

    def test_above_all_edges_is_top_bin(self):
        assert local_volatility_bin(10.0, [1.0, 2.0, 3.0, 4.0]) == 4

    def test_wrong_edge_count_raises(self):
        with pytest.raises(ValueError):
            local_volatility_bin(1.0, [1.0, 2.0])


class TestComputeQuintileEdges:
    def test_four_interior_edges_from_a_known_distribution(self):
        # 0..99 -> 20th/40th/60th/80th percentiles are 19.8/39.6/59.4/79.2 (numpy linear interp)
        values = list(range(100))
        edges = compute_quintile_edges(values)
        assert len(edges) == 4
        assert edges == sorted(edges)
        assert edges[0] == pytest.approx(19.8, abs=0.5)
        assert edges[-1] == pytest.approx(79.2, abs=0.5)

    def test_empty_input_raises(self):
        with pytest.raises(ValueError):
            compute_quintile_edges([])


class TestStratumKey:
    def test_key_is_hashable_and_stable(self):
        k1 = stratum_key("NQ 09-25", "20260115", 2, True, 3)
        k2 = stratum_key("NQ 09-25", "20260115", 2, True, 3)
        assert k1 == k2
        assert hash(k1) == hash(k2)

    def test_key_distinguishes_every_component(self):
        base = stratum_key("NQ 09-25", "20260115", 2, True, 3)
        variants = [
            stratum_key("NQ 12-25", "20260115", 2, True, 3),
            stratum_key("NQ 09-25", "20260116", 2, True, 3),
            stratum_key("NQ 09-25", "20260115", 3, True, 3),
            stratum_key("NQ 09-25", "20260115", 2, False, 3),
            stratum_key("NQ 09-25", "20260115", 2, True, 4),
            stratum_key("NQ 09-25", "20260115", 2, True, INSUFFICIENT_HISTORY),
        ]
        assert len({base, *variants}) == len(variants) + 1


class TestCapacityReport:
    def test_sufficient_pool_passes(self):
        key = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        demand = [key] * 5  # 5 K_ABS events need a match in this stratum
        pool = {key: 20}     # 20 total events in the stratum (K_ABS's own eligible pool)
        report = capacity_report(demand, pool)
        assert report["N_RAND_capacity_ok"] is True
        assert report["n_strata"] == 1
        assert report["n_strata_failing"] == 0
        assert report["strata"][list(report["strata"])[0]]["candidate_pool_size"] == 20

    def test_sparse_pool_fails_that_stratum_and_the_overall_flag(self):
        sparse_key = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        ok_key = stratum_key("NQ 09-25", "20260115", 1, True, 2)
        demand = [sparse_key] * 5 + [ok_key] * 3
        pool = {sparse_key: 5, ok_key: 20}  # 5 events need 5 matches from a pool of 5: pool-1=4 < 5
        report = capacity_report(demand, pool)
        assert report["N_RAND_capacity_ok"] is False
        assert report["n_strata"] == 2
        assert report["n_strata_failing"] == 1
        failing = [s for s in report["strata"].values() if not s["ok"]]
        assert len(failing) == 1
        assert failing[0]["contract"] == "NQ 09-25"
        assert failing[0]["coarse_phase"] == 0

    def test_exact_boundary_pool_minus_one_equals_demand_passes(self):
        # pool - 1 == n_needed is the documented floor: n+1 members required, so
        # a pool of exactly n+1 passes.
        key = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        demand = [key] * 4
        pool = {key: 5}  # pool - 1 = 4 == n_needed -> ok
        report = capacity_report(demand, pool)
        assert report["N_RAND_capacity_ok"] is True

    def test_pool_one_short_of_boundary_fails(self):
        key = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        demand = [key] * 4
        pool = {key: 4}  # pool - 1 = 3 < 4 -> fails
        report = capacity_report(demand, pool)
        assert report["N_RAND_capacity_ok"] is False

    def test_missing_pool_entry_is_treated_as_zero_capacity(self):
        key = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        report = capacity_report([key], {})
        assert report["N_RAND_capacity_ok"] is False
        assert report["strata"][list(report["strata"])[0]]["candidate_pool_size"] == 0

    def test_insufficient_history_stratum_is_visible_not_silently_dropped(self):
        key = stratum_key("NQ 09-25", "20260115", 0, True, INSUFFICIENT_HISTORY)
        pool = {key: 50}
        report = capacity_report([key] * 3, pool)
        assert report["insufficient_history_events"] == 3
        assert report["N_RAND_capacity_ok"] is True  # this stratum itself has enough pool
        stratum = report["strata"][list(report["strata"])[0]]
        assert stratum["local_volatility_bin"] == INSUFFICIENT_HISTORY

    def test_no_demand_is_trivially_ok(self):
        report = capacity_report([], {})
        assert report["N_RAND_capacity_ok"] is True
        assert report["n_strata"] == 0

    def test_report_is_deterministic(self):
        import json
        key_a = stratum_key("NQ 09-25", "20260115", 0, True, 2)
        key_b = stratum_key("NQ 12-25", "20260116", 3, False, INSUFFICIENT_HISTORY)
        demand = [key_a] * 3 + [key_b] * 2
        pool = {key_a: 10, key_b: 8}
        r1 = capacity_report(demand, pool)
        r2 = capacity_report(demand, pool)
        assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
