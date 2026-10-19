# -*- coding: utf-8 -*-
"""Synthetic ground-truth tests for the SL/TP + breakeven exit simulator.

Pure mechanics test (no real GC/NQ data) -- per Nico's explicit choice
2026-09-01: this validates the pipeline runs correctly, it does not open
any outcomes campaign. See edgelab/research/bt2a_sltp_breakeven_exitlogic.py.
"""
from __future__ import annotations

import numpy as np
import pytest

from edgelab.research.bt2a_sltp_breakeven_exitlogic import (
    OUTCOME_BE_STOP,
    OUTCOME_SL_FIRST,
    OUTCOME_TIMEOUT,
    OUTCOME_TP_FIRST,
    simulate_exit,
)


def _path(prices):
    n = len(prices)
    return dict(
        price=np.asarray(prices, dtype=np.int64),
        ts=np.arange(n, dtype=np.int64) * 1_000_000_000,
        source=np.arange(n, dtype=np.int64),
        sessions=np.full(n, "S1", dtype=object),
    )


def _run(prices, **kwargs):
    kwargs.setdefault("tick_cap", len(prices))
    return simulate_exit(**_path(prices), **kwargs)


class TestREFSymmetric:
    """target_ticks == stop_ticks, trigger_ticks=None -- the REF family."""

    def test_tp_first_long(self):
        prices = [100, 101, 102, 103, 105, 90]  # +5 hits target before -5 stop
        r = _run(prices, fill_idx=0, direction=1, target_ticks=5, stop_ticks=5)
        assert r.outcome == OUTCOME_TP_FIRST
        assert r.score_ticks == 5

    def test_sl_first_long(self):
        prices = [100, 99, 98, 97, 95, 110]  # -5 hits stop before +5 target
        r = _run(prices, fill_idx=0, direction=1, target_ticks=5, stop_ticks=5)
        assert r.outcome == OUTCOME_SL_FIRST
        assert r.score_ticks == -5

    def test_timeout_marks_to_market(self):
        prices = [100, 101, 100, 101, 100]  # never reaches +-5
        r = _run(prices, fill_idx=0, direction=1, target_ticks=5, stop_ticks=5)
        assert r.outcome == OUTCOME_TIMEOUT
        assert r.score_ticks == 0  # ends flat at 100


class TestASIMAsymmetric:
    """target_ticks != stop_ticks -- the ASIM family, same simulate_exit call."""

    def test_wide_target_narrow_stop_hits_stop(self):
        prices = [100, 99, 98, 120]  # -2 stop hit well before +18 target
        r = _run(prices, fill_idx=0, direction=1, target_ticks=18, stop_ticks=2)
        assert r.outcome == OUTCOME_SL_FIRST
        assert r.score_ticks == -2

    def test_short_direction_asymmetric(self):
        prices = [100, 95, 93, 108]  # short: price down 7 hits target=5 first
        r = _run(prices, fill_idx=0, direction=-1, target_ticks=5, stop_ticks=30)
        assert r.outcome == OUTCOME_TP_FIRST
        assert r.score_ticks == 5


class TestBEBreakeven:
    """trigger_ticks set -- the BE family: G < TP always."""

    def test_rejects_trigger_at_or_past_target(self):
        with pytest.raises(ValueError, match="0 < G < target_ticks"):
            _run([100, 101], fill_idx=0, direction=1,
                 target_ticks=10, stop_ticks=10, trigger_ticks=10)

    def test_scrapes_at_breakeven_after_trigger_then_reversal(self):
        # +5 trigger hit at idx2 (105), then reverses all the way back to
        # entry (100) without ever hitting the original -10 stop or +20 target.
        prices = [100, 102, 105, 103, 101, 100, 98]
        r = _run(prices, fill_idx=0, direction=1, target_ticks=20, stop_ticks=10, trigger_ticks=5)
        assert r.triggered is True
        assert r.outcome == OUTCOME_BE_STOP
        assert r.score_ticks == 0

    def test_reaches_target_after_trigger_still_tp(self):
        prices = [100, 103, 106, 110, 121]  # trigger=5 hit, then target=20 hit
        r = _run(prices, fill_idx=0, direction=1, target_ticks=20, stop_ticks=10, trigger_ticks=5)
        assert r.triggered is True
        assert r.outcome == OUTCOME_TP_FIRST
        assert r.score_ticks == 20

    def test_hits_original_stop_before_ever_triggering(self):
        prices = [100, 99, 98, 89]  # never reaches +5 trigger; -10 stop hit
        r = _run(prices, fill_idx=0, direction=1, target_ticks=20, stop_ticks=10, trigger_ticks=5)
        assert r.triggered is False
        assert r.outcome == OUTCOME_SL_FIRST
        assert r.score_ticks == -10

    def test_short_direction_breakeven(self):
        # short entry 100: favorable is price going DOWN. trigger=5 -> 95;
        # then reverses back up to exactly 100 (breakeven), never reaching
        # target=120 or original stop=110.
        prices = [100, 97, 95, 97, 99, 100, 103]
        r = _run(prices, fill_idx=0, direction=-1, target_ticks=20, stop_ticks=10, trigger_ticks=5)
        assert r.triggered is True
        assert r.outcome == OUTCOME_BE_STOP
        assert r.score_ticks == 0


class TestFailClosedValidation:
    def test_min_target_stop_below_one_raises(self):
        with pytest.raises(ValueError):
            _run([100, 101], fill_idx=0, direction=1, target_ticks=0, stop_ticks=5)

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            _run([100, 101], fill_idx=0, direction=0, target_ticks=5, stop_ticks=5)
