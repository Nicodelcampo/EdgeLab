# -*- coding: utf-8 -*-
from edgelab.research.f29.labels import decide_labels, probe_interval, probe_side, wick_fracs


def test_probe_follows_dominant_wick():
    assert probe_side(high=20, low=0, close=5) == "bull"
    assert probe_side(high=20, low=0, close=16) == "bear"
    assert probe_interval(1000, "bull") == (1002, 1002)
    assert probe_interval(1000, "bear") == (998, 998)


def test_wick_fracs_split_the_range():
    w = wick_fracs(20, 0, 5)
    assert w["range_ticks"] == 20
    assert abs(w["upper_wick_frac"] + w["lower_wick_frac"] - 1) < 1e-12


def test_simple_rule_when_s1_matches_k0():
    labels = decide_labels({
        "rungs": {
            "K0": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.03},
            "S1": {"n_sessions": 201, "n_resolved": 9000, "ci95_lower": 0.02},
            "F0": {"n_sessions": 10, "n_resolved": 10, "ci95_lower": -0.01},
            "N0": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": -0.01},
        },
        "contrasts": {
            "K0_minus_S1": {"ci95_lower": -0.02, "ci95_upper": 0.02},
            "K0_minus_N0": {"ci95_lower": 0.01, "ci95_upper": 0.04},
            "F0_minus_S1": {"ci95_lower": -0.03, "ci95_upper": 0.01},
            "K0_minus_F0": {"ci95_lower": -0.01, "ci95_upper": 0.02},
        },
        "zone_residual": {"n_sessions": 10, "n_resolved": 10, "ci95_lower": -0.02},
        "persistence": {
            "+1": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": -0.03, "ci95_upper": 0.01},
            "+2": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": -0.04, "ci95_upper": 0.01},
        },
    })
    assert "OPEN_SIMPLE_BAR_RULE" in labels
    assert "OPEN_SINGLE_BAR_STAMP" in labels
    assert "OPEN_FAR_ZONE_FAMILY" not in labels
    assert "CLOSE_BAR_OBJECT" not in labels


def test_zone_residual_and_keep_detector_can_coexist():
    labels = decide_labels({
        "rungs": {
            "K0": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.04},
            "S1": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.00},
            "F0": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.03},
            "N0": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": -0.01},
        },
        "contrasts": {
            "K0_minus_S1": {"ci95_lower": 0.01, "ci95_upper": 0.05},
            "K0_minus_N0": {"ci95_lower": 0.02, "ci95_upper": 0.06},
            "F0_minus_S1": {"ci95_lower": 0.01, "ci95_upper": 0.04},
            "K0_minus_F0": {"ci95_lower": -0.01, "ci95_upper": 0.02},
        },
        "zone_residual": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.015},
        "persistence": {
            "+1": {"n_sessions": 201, "n_resolved": 8000, "ci95_lower": 0.01},
            "+2": {"n_sessions": 40, "n_resolved": 250, "ci95_lower": -0.02, "ci95_upper": 0.01},
        },
    })
    assert "KEEP_BT2_AS_DETECTOR" in labels
    assert "OPEN_ZONE_RESIDUAL" in labels
    assert "OPEN_REGIME_WINDOW" in labels
    assert "OPEN_FOOTPRINT_OBJECT" in labels
