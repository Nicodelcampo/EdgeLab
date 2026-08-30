"""Synthetic ground-truth tests for edgelab.research.bt2a_nq_gate1_outcomes.

Written before any real-data run, per the audit thread's hard rule for T1:
planted trajectories with hand-computed expected outcomes, incomplete-path
exclusion, determinism, and an explicit test that the same-observation tie
rule is genuinely not applicable to this (magnitude) estimand rather than
silently missing.

No raw ticks, no Kaggle, no outcomes-shaped real data anywhere in this file.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from edgelab.research.bt2_gate1_outcomes import Event, build_path_cache
from edgelab.research.bt2a_nq_gate1_outcomes import (
    BARRIERS_TICKS,
    HORIZONS_OBSERVATIONS,
    all_cells,
    build_cell_cache,
    cell_id,
    compute_cell_contrast,
    compute_family,
    event_cell_values,
    paired_session_contrast,
    session_arm_cell_mean,
    unbiased_paired_session_variance,
)

SESSION = "20260101"


def _make_event(key: str, direction: int, fill_idx: int) -> Event:
    return Event(
        key=key, arm="K_ABS", contract="NQ 09-25", session=SESSION,
        direction=direction, signal_idx=fill_idx, signal_ts_ns=fill_idx * 1_000,
        signal_source_row=fill_idx, fill_idx=fill_idx,
    )


def _ts_ns(n: int) -> np.ndarray:
    # One tick per millisecond, single session -- spacing is irrelevant to
    # build_path_cache's tick-count cap, only used for the clock cap, which
    # LARGE_CLOCK_CAP_SECONDS keeps out of the way.
    return (np.arange(n, dtype=np.int64)) * 1_000_000


def _sessions(n: int) -> np.ndarray:
    return np.full(n, SESSION, dtype=object)


class TestAllCellsShape:
    def test_16_cells_frozen_barriers_and_horizons(self):
        cells = all_cells()
        assert len(cells) == 16
        assert len(set(cells)) == 16
        assert set(BARRIERS_TICKS) == {5, 9, 18, 30}
        assert set(HORIZONS_OBSERVATIONS) == {25, 50, 100, 250}
        for barrier, horizon in cells:
            assert barrier in BARRIERS_TICKS
            assert horizon in HORIZONS_OBSERVATIONS

    def test_cell_id_is_stable_and_unique(self):
        ids = {cell_id(b, h) for b, h in all_cells()}
        assert len(ids) == 16


class TestPlantedTrajectoryFavorableOnly:
    """Price rises monotonically by +1 tick per step, long direction: MFE
    grows to the full window height, MAE stays exactly 0 throughout."""

    def test_uncapped_barrier_gives_full_mfe_minus_zero_mae(self):
        n = 30
        prices = 100 + np.arange(n, dtype=np.int64)  # 100,101,...,129
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        fill_idx = 5  # price=105; window is [5, 5+10]=[5,15] inclusive -> max=115
        values = event_cell_values(
            prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
            barrier_ticks=100,  # far above the achievable excursion: no capping
        )
        expected_mfe = 115 - 105  # future_max(115) - fill(105)
        expected_mae = 0.0        # price never dips below the fill
        assert values[0] == pytest.approx(expected_mfe - expected_mae)

    def test_barrier_caps_the_reported_magnitude(self):
        n = 30
        prices = 100 + np.arange(n, dtype=np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        fill_idx = 5
        barrier = 3  # far below the achievable +10 excursion
        values = event_cell_values(
            prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
            barrier_ticks=barrier,
        )
        # MFE=10 capped to 3; MAE=0 capped to 0 -> 3 - 0 = 3
        assert values[0] == pytest.approx(3.0)
        assert values[0] <= barrier
        assert values[0] >= -barrier


class TestPlantedTrajectoryAdverseOnly:
    """Price falls monotonically, long direction: MAE grows, MFE stays 0."""

    def test_adverse_only_gives_negative_capped_value(self):
        n = 30
        prices = 130 - np.arange(n, dtype=np.int64)  # 130,129,...,101
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        fill_idx = 5  # price=125; window min over [5,15] = 115
        barrier = 30  # uncapped (achievable excursion is 10)
        values = event_cell_values(
            prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
            barrier_ticks=barrier,
        )
        expected_mfe = 0.0
        expected_mae = 125 - 115
        assert values[0] == pytest.approx(expected_mfe - expected_mae)
        assert values[0] == pytest.approx(-10.0)

    def test_short_direction_mirrors_long(self):
        """A short (direction=-1) event on a RISING path sees the same
        magnitude of adverse excursion that a long event saw favorable in
        the mirrored-price test above -- direction flips which raw quantity
        (up/down) plays MFE vs MAE, not the arithmetic."""
        n = 30
        prices = 100 + np.arange(n, dtype=np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        fill_idx = 5
        barrier = 100
        values = event_cell_values(
            prices, cache, np.asarray([fill_idx]), np.asarray([-1], dtype=np.int8),
            barrier_ticks=barrier,
        )
        # Short on a rising path: adverse (price rises against the short) = 10, favorable = 0
        assert values[0] == pytest.approx(0.0 - 10.0)


class TestBoundedRange:
    def test_value_never_exceeds_barrier_in_either_direction(self):
        rng = np.random.default_rng(20260830)
        n = 400
        steps = rng.integers(-3, 4, size=n)
        prices = 1000 + np.cumsum(steps).astype(np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        for horizon in HORIZONS_OBSERVATIONS:
            if horizon >= n - 5:
                continue
            cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
            eligible_idx = np.flatnonzero(cache.eligible)
            eligible_idx = eligible_idx[eligible_idx < n - horizon - 1]
            if len(eligible_idx) == 0:
                continue
            directions = rng.choice([-1, 1], size=len(eligible_idx)).astype(np.int8)
            for barrier in BARRIERS_TICKS:
                values = event_cell_values(
                    prices, cache, eligible_idx, directions, barrier_ticks=barrier,
                )
                assert np.all(values <= barrier + 1e-9)
                assert np.all(values >= -barrier - 1e-9)


class TestIncompletePathExclusion:
    def test_events_too_close_to_session_end_are_excluded_with_reason(self):
        n = 20
        prices = 100 + np.arange(n, dtype=np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        # fill_idx=15 needs prices[15..25], but the session only has 20 rows (0..19):
        # incomplete path -> ineligible.
        complete_event = _make_event("complete", 1, fill_idx=5)
        incomplete_event = _make_event("incomplete", 1, fill_idx=15)
        assert cache.eligible[5]
        assert not cache.eligible[15]
        mean_value, excluded = session_arm_cell_mean(
            [complete_event, incomplete_event], prices, cache, barrier_ticks=30,
        )
        assert mean_value is not None
        assert len(excluded) == 1
        assert excluded[0]["key"] == "incomplete"
        assert excluded[0]["reason"] == "EXCLUDE_WITH_REASON_INCOMPLETE_PATH"

    def test_all_events_incomplete_returns_none_not_zero(self):
        n = 12
        prices = 100 + np.arange(n, dtype=np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 10
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        only_incomplete = _make_event("only_incomplete", 1, fill_idx=8)
        assert not cache.eligible[8]
        mean_value, excluded = session_arm_cell_mean(
            [only_incomplete], prices, cache, barrier_ticks=30,
        )
        assert mean_value is None
        assert len(excluded) == 1


class TestSameObservationTieIsNotApplicableToPrimary:
    """estimand_definition.event_cell_value_ticks.same_observation_tie declares
    N/A_FOR_PRIMARY: the magnitude estimand reads future_max/future_min over
    a fixed window, there is no favorable-vs-adverse "race" to break a tie
    on. This test makes that an explicit, checked property instead of an
    absence: a path that touches +G and -G in the SAME step still produces a
    single well-defined value with no branching on order."""

    def test_simultaneous_extremes_produce_one_deterministic_value(self):
        # Session touches both a high and a low within the window; since
        # future_max/future_min are independent running extrema (not a
        # first-to-happen race), the result does not depend on which
        # extreme occurred "first" in any tie-breaking sense.
        n = 12
        prices = np.array([100, 100, 105, 95, 100, 100, 100, 100, 100, 100, 100, 100], dtype=np.int64)
        ts = _ts_ns(n)
        sessions = _sessions(n)
        horizon = 8
        cache = build_cell_cache(ts, prices, sessions, horizon_observations=horizon)
        fill_idx = 0
        assert cache.eligible[fill_idx]
        barrier = 3
        values = event_cell_values(
            prices, cache, np.asarray([fill_idx]), np.asarray([1], dtype=np.int8),
            barrier_ticks=barrier,
        )
        # MFE=5 (105-100) capped to 3; MAE=5 (100-95) capped to 3 -> 3-3=0
        assert values[0] == pytest.approx(0.0)


class TestAggregationAndVariance:
    def test_paired_session_contrast_only_uses_sessions_in_both_arms(self):
        primary = {"s1": 1.0, "s2": 2.0, "s3": 3.0}
        comparator = {"s1": 0.5, "s2": 0.5}
        sessions, contrasts = paired_session_contrast(primary, comparator)
        assert sessions == ["s1", "s2"]
        assert list(contrasts) == pytest.approx([0.5, 1.5])

    def test_unbiased_variance_matches_hand_computation(self):
        # values 1,2,3 -> mean=2, sum((x-mean)^2)=2, ddof=1 -> var=1.0
        assert unbiased_paired_session_variance([1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_variance_requires_at_least_two_sessions(self):
        with pytest.raises(ValueError):
            unbiased_paired_session_variance([1.0])


class TestComputeCellContrastAndFamily:
    def _sessions_dict(self, rng, n_sessions, mean_shift, noise_scale=0.5):
        return {f"s{i}": mean_shift + rng.normal(scale=noise_scale) for i in range(n_sessions)}

    def test_planted_positive_effect_is_detected_by_the_cell_contrast(self):
        rng = np.random.default_rng(1)
        k_abs = self._sessions_dict(rng, 40, mean_shift=5.0, noise_scale=1.0)
        n_rand = self._sessions_dict(rng, 40, mean_shift=0.0, noise_scale=1.0)
        result = compute_cell_contrast(k_abs, n_rand, replications=2000, seed=42)
        assert result["point"] > 0
        assert result["lower"] > 0  # a real planted effect should clear zero
        assert result["p_two_sided"] < 0.05

    def test_planted_null_effect_is_not_detected(self):
        rng = np.random.default_rng(2)
        k_abs = self._sessions_dict(rng, 40, mean_shift=0.0, noise_scale=1.0)
        n_rand = self._sessions_dict(rng, 40, mean_shift=0.0, noise_scale=1.0)
        result = compute_cell_contrast(k_abs, n_rand, replications=2000, seed=43)
        assert result["lower"] < 0 < result["upper"]

    def test_compute_family_requires_exactly_the_16_frozen_cells(self):
        with pytest.raises(ValueError):
            compute_family({}, replications=100, seed=1)

    def test_compute_family_applies_holm_and_is_deterministic(self):
        rng = np.random.default_rng(7)
        cells = {}
        for barrier, horizon in all_cells():
            k_abs = self._sessions_dict(rng, 30, mean_shift=0.2, noise_scale=1.0)
            n_rand = self._sessions_dict(rng, 30, mean_shift=0.0, noise_scale=1.0)
            cells[(barrier, horizon)] = {"K_ABS": k_abs, "N_RAND": n_rand}
        result_a = compute_family(cells, replications=500, seed=99)
        result_b = compute_family(cells, replications=500, seed=99)
        assert json.dumps(result_a, sort_keys=True) == json.dumps(result_b, sort_keys=True)
        assert result_a["family_size"] == 16
        assert len(result_a["cells"]) == 16
        for cid, cell_result in result_a["cells"].items():
            assert 0.0 <= cell_result["p_holm_16"] <= 1.0
            assert cell_result["p_holm_16"] >= cell_result["p_two_sided"] - 1e-12

    def test_holm_p_values_are_monotone_nondecreasing_with_rank(self):
        # Holm's construction guarantees the adjusted p-values, sorted by
        # the raw p-value order, are non-decreasing.
        rng = np.random.default_rng(11)
        cells = {}
        for barrier, horizon in all_cells():
            shift = float(rng.uniform(-0.5, 0.5))
            k_abs = self._sessions_dict(rng, 25, mean_shift=shift, noise_scale=1.0)
            n_rand = self._sessions_dict(rng, 25, mean_shift=0.0, noise_scale=1.0)
            cells[(barrier, horizon)] = {"K_ABS": k_abs, "N_RAND": n_rand}
        result = compute_family(cells, replications=500, seed=5)
        ordered = sorted(result["cells"].values(), key=lambda r: r["p_two_sided"])
        holm_in_order = [r["p_holm_16"] for r in ordered]
        assert all(a <= b + 1e-12 for a, b in zip(holm_in_order, holm_in_order[1:]))
