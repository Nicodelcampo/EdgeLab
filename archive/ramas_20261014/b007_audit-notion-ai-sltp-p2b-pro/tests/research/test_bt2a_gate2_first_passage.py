from __future__ import annotations

import numpy as np
import pytest

from edgelab.research.bt2a_gate2_first_passage import (
    first_passage,
    first_passage_scores_fast,
    first_passage_scores,
    holm_adjust,
    horizon_endpoint,
    next_barrier_touch_indices,
    summarize_scores,
    wild_cluster_test,
)


def stream(prices, *, sessions=None, seconds=None):
    n = len(prices)
    if seconds is None:
        seconds = list(range(n))
    return (
        np.asarray(prices, dtype=np.int64),
        np.asarray(seconds, dtype=np.int64) * 1_000_000_000,
        np.arange(100, 100 + n, dtype=np.int64),
        np.asarray(sessions or ["A"] * n),
    )


def test_long_target_first_preserves_order():
    p, ts, src, ses = stream([100, 101, 103, 98])
    got = first_passage(p, ts, src, ses, fill_idx=0, direction=1,
                        target_ticks=3, stop_ticks=2, tick_cap=3)
    assert got.outcome == "TP_FIRST"
    assert got.score == 1
    assert got.first_touch_idx == 2
    assert got.ticks_to_touch == 2
    assert got.touch_price_ticks == 103


def test_short_stop_first():
    p, ts, src, ses = stream([100, 101, 103, 96])
    got = first_passage(p, ts, src, ses, fill_idx=0, direction=-1,
                        target_ticks=4, stop_ticks=2, tick_cap=3)
    assert got.outcome == "SL_FIRST"
    assert got.score == -1
    assert got.first_touch_idx == 2


def test_same_extrema_different_order_yield_different_outcome():
    args = dict(fill_idx=0, direction=1, target_ticks=3, stop_ticks=2, tick_cap=3)
    a = stream([100, 103, 98, 100])
    b = stream([100, 98, 103, 100])
    assert first_passage(*a, **args).outcome == "TP_FIRST"
    assert first_passage(*b, **args).outcome == "SL_FIRST"


def test_timeout_is_retained_and_scored_zero():
    p, ts, src, ses = stream([100, 101, 100, 101])
    got = first_passage(p, ts, src, ses, fill_idx=0, direction=1,
                        target_ticks=3, stop_ticks=3, tick_cap=3)
    assert got.outcome == "TIMEOUT"
    assert got.score == 0
    assert got.first_touch_idx is None
    assert summarize_scores([1, -1, 0, 0])["p_timeout"] == 0.5


def test_clock_cap_never_borrows_first_tick_after_deadline():
    p, ts, src, ses = stream([100, 101, 104], seconds=[0, 2, 10])
    end, driver = horizon_endpoint(ts, ses, fill_idx=0, tick_cap=10,
                                   clock_cap_seconds=5)
    assert (end, driver) == (1, "clock")
    got = first_passage(p, ts, src, ses, fill_idx=0, direction=1,
                        target_ticks=3, stop_ticks=3, tick_cap=10,
                        clock_cap_seconds=5)
    assert got.outcome == "TIMEOUT"
    assert got.end_idx == 1


def test_session_boundary_wins_and_no_cross_session_touch():
    p, ts, src, ses = stream([100, 101, 110], sessions=["A", "A", "B"])
    got = first_passage(p, ts, src, ses, fill_idx=0, direction=1,
                        target_ticks=5, stop_ticks=5, tick_cap=20)
    assert got.outcome == "TIMEOUT"
    assert got.end_idx == 1
    assert got.cap_driver == "session"


def test_vector_scores_and_validation():
    p, ts, src, ses = stream([100, 103, 98, 100])
    scores = first_passage_scores(p, ts, src, ses, fill_indices=[0, 0],
                                  directions=[1, -1], target_ticks=3,
                                  stop_ticks=2, tick_cap=3)
    assert scores.tolist() == [1, -1]
    with pytest.raises(ValueError):
        first_passage(p, ts, src, ses, fill_idx=0, direction=0,
                      target_ticks=1, stop_ticks=1, tick_cap=2)


def test_holm_is_monotone_in_sorted_order():
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_wild_cluster_test_is_deterministic():
    x = [0.2, 0.1, 0.4, -0.1, 0.3]
    a = wild_cluster_test(x, replications=300, seed=7)
    b = wild_cluster_test(x, replications=300, seed=7)
    assert a == b
    assert a["n_sessions"] == 5
    assert 0 <= a["p_two_sided"] <= 1


def test_fast_barrier_lookup_matches_scalar_across_sessions():
    rng = np.random.default_rng(17)
    prices = 100 + np.cumsum(rng.integers(-2, 3, size=80))
    ts = np.arange(80, dtype=np.int64) * 1_000_000_000
    src = np.arange(80, dtype=np.int64)
    sessions = np.asarray(["A"] * 40 + ["B"] * 40)
    directions = rng.choice([-1, 1], size=80)
    touches = next_barrier_touch_indices(prices, sessions, barrier_ticks=3)
    fast = first_passage_scores_fast(
        prices, ts, sessions, fill_indices=np.arange(80), directions=directions,
        barrier_ticks=3, tick_cap=12, clock_cap_seconds=None,
        precomputed_touches=touches,
    )
    slow = first_passage_scores(
        prices, ts, src, sessions, fill_indices=np.arange(80), directions=directions,
        target_ticks=3, stop_ticks=3, tick_cap=12,
    )
    assert np.array_equal(fast, slow)
