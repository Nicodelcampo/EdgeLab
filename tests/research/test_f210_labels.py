# -*- coding: utf-8 -*-
from edgelab.research.f210.labels import decide_labels, is_s1, is_t1


def test_s1_is_range_extreme_and_session_volume():
    assert is_s1(5, 0.40, 0.10, 100.0, 80.0) is True
    assert is_s1(2, 0.40, 0.10, 100.0, 80.0) is False
    assert is_s1(5, 0.20, 0.10, 100.0, 80.0) is False
    assert is_s1(5, 0.40, 0.10, 70.0, 80.0) is False


def test_t1_is_previous_bar_in_session():
    assert is_t1(10, {9}, 0, 20) is True
    assert is_t1(10, {10}, 0, 20) is False
    assert is_t1(0, {0}, 0, 20) is False


def test_window_beats_cluster_when_non_s1_next_bar_lives():
    labels = decide_labels({
        "arms": {
            "T1_not_S1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": 0.02},
            "T1_and_S1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": 0.03},
            "T_minus1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": -0.01, "ci95_upper": 0.02},
        },
        "contrasts": {
            "T1_not_S1_minus_P1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": 0.01},
            "T1_after_K0_minus_T1_after_S1": {"n_sessions": 201, "ci95_lower": -0.02, "ci95_upper": 0.01},
            "T_minus1_minus_P_minus1": {"n_sessions": 201, "ci95_lower": -0.02, "ci95_upper": 0.02},
        },
    })
    assert "OPEN_POST_STAMP_WINDOW" in labels
    assert "OPEN_CLUSTER_ONLY" not in labels
    assert "KEEP_KERNEL_FOR_WINDOW" not in labels


def test_cluster_only_when_next_bar_must_also_be_s1():
    labels = decide_labels({
        "arms": {
            "T1_not_S1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": -0.01, "ci95_upper": 0.02},
            "T1_and_S1": {"n_sessions": 201, "n_resolved": 4000, "ci95_lower": 0.02},
            "T_minus1": {"n_sessions": 10, "n_resolved": 10, "ci95_upper": 0.01},
        },
        "contrasts": {
            "T1_not_S1_minus_P1": {"n_sessions": 201, "ci95_lower": -0.02, "ci95_upper": 0.01},
            "T1_after_K0_minus_T1_after_S1": {"n_sessions": 201, "ci95_lower": -0.01, "ci95_upper": 0.02},
            "T_minus1_minus_P_minus1": {"n_sessions": 10, "ci95_upper": 0.01},
        },
    })
    assert "OPEN_CLUSTER_ONLY" in labels
    assert "OPEN_POST_STAMP_WINDOW" not in labels
    assert "CLOSE_WINDOW" not in labels
