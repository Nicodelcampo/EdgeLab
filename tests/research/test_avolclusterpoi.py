# -*- coding: utf-8 -*-
from edgelab.bridge.indicators.avolclusterpoi import (
    SessionProfile, classify_kind, cluster_hot_ticks, detect_block, empirical_quantile,
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


def test_one_cluster_per_block_keeps_max_mass():
    cells = {1: 1, 2: 1, 3: 1, 11: 50, 12: 50, 20: 10, 21: 10}
    hist = [1] * 20
    out = detect_block(cells, hist, params={"min_samples_per_bucket": 20, "detection_percentile": 95.0})
    assert len(out["zones"]) == 1
    assert out["zones"][0]["lower_tick"] == 11
    assert out["zones"][0]["score"] == 100


def test_off_price_is_the_level_object():
    cells = {1: 1, 2: 1, 3: 1, 11: 50, 12: 50}
    hist = [1] * 20
    out = detect_block(cells, hist, close_tick=20, params={"min_samples_per_bucket": 20})
    z = out["zones"][0]
    assert z["kind"] == "OFF_PRICE"
    assert z["event_type"] == "ZONE_CREATED"
    assert z["direction"] == 1
    assert z["distance_ticks"] == 8


def test_at_price_is_occupation_not_a_level():
    cells = {1: 1, 2: 1, 3: 1, 11: 50, 12: 50}
    hist = [1] * 20
    out = detect_block(cells, hist, close_tick=12, params={"min_samples_per_bucket": 20})
    z = out["zones"][0]
    assert z["kind"] == "AT_PRICE"
    assert z["event_type"] == "AT_PRICE_CREATED"
    assert z["direction"] == 0


def test_classify_kind():
    assert classify_kind(20, 11, 12)[0] == "OFF_PRICE"
    assert classify_kind(10, 11, 12)[0] == "OFF_PRICE"
    assert classify_kind(11, 11, 12)[0] == "AT_PRICE"


def test_current_session_is_not_in_history_until_commit():
    profile = SessionProfile(lookback_sessions=20)
    profile.commit()
    profile.add_block(3, 99.0)
    assert profile.history_scores(3) == []
    profile.commit()
    assert profile.history_scores(3) == [99.0]
