# -*- coding: utf-8 -*-
from edgelab.research.f28.residual_atlas import (
    decide_labels,
    distance_stratum,
    isolated,
    occupancy_union,
    support_ok,
)


def test_distance_strata():
    assert distance_stratum(1) == "d<=2"
    assert distance_stratum(2) == "d<=2"
    assert distance_stratum(3) == "3<=d<=5"
    assert distance_stratum(5) == "3<=d<=5"
    assert distance_stratum(6) == "d>=6"


def test_occupancy_merges_overlaps_and_counts_gaps():
    assert occupancy_union([(10, 12), (12, 14), (20, 21)]) == 7
    assert occupancy_union([]) == 0


def test_isolated_requires_no_simultaneous_overlap():
    assert isolated((10, 12), [(14, 16)])
    assert not isolated((10, 12), [(12, 13)])


def test_far_family_and_density_can_coexist():
    labels = decide_labels({
        "strata": {"d>=6": {"n_sessions": 40, "n_resolved": 250, "ci95_lower": 0.02}},
        "bt2_minus_control": {"d>=6": {"ci95_lower": 0.01}},
        "occupancy": {"p50_visited": 0.85, "isolated_rate": 0.04},
        "holes": {},
        "fade_cuts": {},
        "interruption": {},
        "global": {},
    })
    assert "OPEN_FAR_ZONE_FAMILY" in labels
    assert "OPEN_DENSITY_FEATURES" in labels
    assert "CLOSE_ZONE_ATTRACTION" not in labels


def test_bar_classifier_when_controls_explain_the_race():
    labels = decide_labels({
        "global": {"ci95_lower": 0.03},
        "strata": {"d<=2": {"ci95_lower": 0.04}, "d>=6": {"n_sessions": 10, "n_resolved": 20, "ci95_lower": -0.01}},
        "bt2_minus_control": {"global": {"ci95_lower": -0.01, "ci95_upper": 0.02}},
        "occupancy": {"p50_visited": 0.4, "isolated_rate": 0.3},
        "holes": {"first_passage_edge": False},
        "fade_cuts": {},
        "interruption": {},
    })
    assert labels == ["OPEN_BAR_CLASSIFIER"]


def test_close_attraction_when_nothing_opens():
    labels = decide_labels({
        "global": {"ci95_lower": -0.01},
        "strata": {"d<=2": {"ci95_lower": -0.02}, "d>=6": {"n_sessions": 40, "n_resolved": 250, "ci95_lower": -0.03}},
        "bt2_minus_control": {"global": {"ci95_lower": -0.04, "ci95_upper": -0.01}, "d>=6": {"ci95_lower": -0.02}},
        "occupancy": {"p50_visited": 0.2, "isolated_rate": 0.5},
        "holes": {"first_passage_edge": False},
        "fade_cuts": {},
        "interruption": {"ci95_lower": -0.01},
        "underpowered": False,
    })
    assert labels == ["CLOSE_ZONE_ATTRACTION"]
    assert support_ok(29, 500) is False
