# -*- coding: utf-8 -*-
"""Unit tests for aVolClusterPOI formal tick race and P2 gate."""
import math
import numpy as np
import pytest
from datetime import datetime

from diag.tasa_senales.avolcluster_tick_formal import (
    hac_bartlett_ic, decide_labels, tick_first_touch_race, run_first_passage_race
)
from edgelab.bridge.ticks import TickSeries
from edgelab.bridge.bars import BarSeries


def test_hac_bartlett_single_session_abstains():
    res = hac_bartlett_ic([0.5])
    assert res["abstain_inferencia"] is True


def test_hac_bartlett_calculates_correct_ci():
    # Symmetric zero-mean sequence
    means = [1.0, -1.0, 1.0, -1.0] * 10
    res = hac_bartlett_ic(means)
    assert res["abstain_inferencia"] is False
    assert abs(res["mean"]) < 1e-10
    assert res["ci95_lower"] < 0 < res["ci95_upper"]


def test_decide_labels_p2_fail():
    lbl = decide_labels(
        p2_pass=False,
        n_sessions=50,
        frac_resolved=0.9,
        match_rate_random=1.0,
        zone_ic={"ci95_lower": 0.1, "ci95_upper": 0.5},
        contrast_random={"ci95_lower": 0.1, "ci95_upper": 0.5},
        contrast_nearest={"ci95_lower": 0.1, "ci95_upper": 0.5},
    )
    assert lbl == "ABSTAIN_P2"


def test_decide_labels_zone_edge():
    lbl = decide_labels(
        p2_pass=True,
        n_sessions=50,
        frac_resolved=0.9,
        match_rate_random=1.0,
        zone_ic={"ci95_lower": 0.1, "ci95_upper": 0.5},
        contrast_random={"ci95_lower": 0.1, "ci95_upper": 0.5},
        contrast_nearest={"ci95_lower": 0.1, "ci95_upper": 0.5},
    )
    assert lbl == "AVOL_ZONE_EDGE"


def test_decide_labels_bar_context():
    lbl = decide_labels(
        p2_pass=True,
        n_sessions=50,
        frac_resolved=0.9,
        match_rate_random=1.0,
        zone_ic={"ci95_lower": 0.1, "ci95_upper": 0.5},
        contrast_random={"ci95_lower": -0.1, "ci95_upper": 0.2},
        contrast_nearest={"ci95_lower": -0.1, "ci95_upper": 0.2},
    )
    assert lbl == "AVOL_BAR_CONTEXT"


def test_decide_labels_no_edge():
    lbl = decide_labels(
        p2_pass=True,
        n_sessions=50,
        frac_resolved=0.9,
        match_rate_random=1.0,
        zone_ic={"ci95_lower": -0.1, "ci95_upper": 0.1},
        contrast_random={"ci95_lower": -0.1, "ci95_upper": 0.1},
        contrast_nearest={"ci95_lower": -0.1, "ci95_upper": 0.1},
    )
    assert lbl == "AVOL_NO_EDGE"


def test_tick_first_touch_disambiguation():
    # Synthetic ticks in bar: hits zone first, then mirror
    ts = np.array([1, 2, 3, 4], dtype=np.int64)
    p = np.array([100, 110, 90, 100], dtype=np.int64) # 110 hits zone [108, 112], 90 hits mirror [88, 92]
    vol = np.array([1, 1, 1, 1], dtype=np.float64)
    seq = np.array([1, 2, 3, 4], dtype=np.int64)
    ticks = TickSeries(ts, p, vol, None, None, seq, 0.00005)
    
    res = tick_first_touch_race(ticks, 0, 4, zone_lo=108, zone_hi=112, mirror_lo=88, mirror_hi=92)
    assert res == 1 # Zone first!
    
    # Reverse order: hits mirror first, then zone
    p_rev = np.array([100, 90, 110, 100], dtype=np.int64)
    ticks_rev = TickSeries(ts, p_rev, vol, None, None, seq, 0.00005)
    res_rev = tick_first_touch_race(ticks_rev, 0, 4, zone_lo=108, zone_hi=112, mirror_lo=88, mirror_hi=92)
    assert res_rev == -1 # Mirror first!
