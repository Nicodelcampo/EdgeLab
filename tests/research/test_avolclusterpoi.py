# -*- coding: utf-8 -*-
from edgelab.bridge.indicators.avolclusterpoi import (
    SessionProfile, cluster_hot_ticks, detect_block, empirical_quantile,
)


def test_empirical_quantile_has_no_interpolation():
    assert empirical_quantile([1, 2, 3, 4], 0.75) == 3
    assert empirical_quantile([10], 0.99) == 10


def test_hot_ticks_cluster_by_integer_gap():
    cells = {10: 1, 11: 10, 12: 10, 13: 1, 20: 10, 21: 10}
    clusters = cluster_hot_ticks(cells, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2)
    spans = [(ticks[0], ticks[-1], score) for ticks, score in clusters]
    assert (11, 12, 20) in spans
    assert (20, 21, 20) in spans


def test_warmup_does_not_detect():
    cells = {11: 10, 12: 10, 13: 10}
    out = detect_block(cells, history_scores=[1, 2, 3], params={"min_samples_per_bucket": 20})
    assert out["abstain"] == "warmup"
    assert out["zones"] == []
    assert out["best_score"] == 30


def test_history_beats_threshold_after_warmup():
    cells = {11: 50, 12: 50}
    hist = [1] * 19 + [10]
    out = detect_block(cells, hist, params={"min_samples_per_bucket": 20, "detection_percentile": 95.0})
    assert out["abstain"] is None
    assert len(out["zones"]) == 1
    assert out["zones"][0]["lower_tick"] == 11
    assert "direction" not in out["zones"][0]


def test_current_session_is_not_in_history_until_commit():
    profile = SessionProfile(lookback_sessions=20)
    profile.commit()
    profile.add_block(3, 99.0)
    assert profile.history_scores(3) == []
    profile.commit()
    assert profile.history_scores(3) == [99.0]
