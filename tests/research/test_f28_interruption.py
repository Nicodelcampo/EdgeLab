# -*- coding: utf-8 -*-
import numpy as np

from edgelab.research.f28.controls import eligible_control, same_side_interval
from edgelab.research.f28.interruption import classify_after_contact


def _flat(n=12, px=1000):
    return (
        np.full(n, px, dtype=np.int64),
        np.full(n, px, dtype=np.int64),
        np.full(n, px, dtype=np.int64),
    )


def test_through_away_from_anchor():
    close_t, high_t, low_t = _flat()
    close_t[3] = 1035
    high_t[3] = 1035
    assert classify_after_contact(1000, 1020, 1030, True, 1, close_t, high_t, low_t, 12) == "through"


def test_bounce_back_toward_anchor():
    close_t, high_t, low_t = _flat()
    low_t[4] = 985
    assert classify_after_contact(1000, 1020, 1030, True, 1, close_t, high_t, low_t, 12) == "bounce"


def test_stay_if_neither_happens():
    close_t, high_t, low_t = _flat()
    assert classify_after_contact(1000, 1020, 1030, True, 1, close_t, high_t, low_t, 12) == "stay"


def test_same_side_interval_preserves_d_and_width():
    lo, hi = same_side_interval(1000, 20, 11, True)
    assert lo == 1020
    assert hi == 1030
    assert eligible_control(1000, lo, hi, [])
    assert not eligible_control(1000, 990, 1010, [])
