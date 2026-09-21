"""Tests de semantica causal: available_ts en viewer_export._zone_json.

Fixtures sinteticos sin datos de holdout ni outcomes.
Holdout boundary: 1782856800000000000 ns (2026-06-30T22:00:00Z).
"""
from __future__ import annotations
import pytest
from edgelab.bridge import viewer_export as ve

BAR_OPEN_NS    = 1_780_000_000_000_000_000
BAR_CLOSE_NS   = 1_780_000_300_000_000_000
BAR_CREATED_MS = BAR_OPEN_NS // 1_000_000
TICK_OPEN_NS   = 1_780_001_000_000_000_000
TICK_CLOSE_NS  = 1_780_001_007_000_000_000
TICK_CREATED_MS = TICK_OPEN_NS // 1_000_000
HOLDOUT_NS     = 1_782_856_800_000_000_000
LAST_MS        = 1_780_999_999_000


def _z_m5_avail():
    return {"id": "1_B", "top": 43500.0, "bottom": 43450.0,
            "created_ms": BAR_CREATED_MS, "available_at_ns": BAR_CLOSE_NS,
            "state": "ACTIVE", "kind": "trapped_buyers", "touches": 0,
            "ended_ms": None, "end_reason": None}


def _z_m5_no_avail():
    return {"id": "2_S", "top": 43550.0, "bottom": 43500.0,
            "created_ms": BAR_CREATED_MS,
            "state": "ACTIVE", "kind": "trapped_sellers", "touches": 0,
            "ended_ms": None, "end_reason": None}


def _z_t25_avail():
    return {"id": "3_B", "top": 43520.0, "bottom": 43490.0,
            "created_ms": TICK_CREATED_MS, "available_at_ns": TICK_CLOSE_NS,
            "state": "ACTIVE", "kind": "trapped_buyers", "touches": 0,
            "ended_ms": None, "end_reason": None}


def _z_t25_no_avail():
    return {"id": "4_S", "top": 43530.0, "bottom": 43510.0,
            "created_ms": TICK_CREATED_MS,
            "state": "ACTIVE", "kind": "trapped_sellers", "touches": 0,
            "ended_ms": None, "end_reason": None}


class TestBarDurationS:
    def test_time_5m(self):  assert ve._bar_duration_s("time_5m")  == 300
    def test_time_1m(self):  assert ve._bar_duration_s("time_1m")  == 60
    def test_time_15m(self): assert ve._bar_duration_s("time_15m") == 900
    def test_time_1h(self):  assert ve._bar_duration_s("time_1h")  == 3600
    def test_time_1d(self):  assert ve._bar_duration_s("time_1d")  == 86400
    def test_tick_25(self):  assert ve._bar_duration_s("tick_25")  is None
    def test_tick_100(self): assert ve._bar_duration_s("tick_100") is None
    def test_empty(self):    assert ve._bar_duration_s("")         is None
    def test_vol(self):      assert ve._bar_duration_s("vol_1000") is None


class TestZoneJsonAvailableTs:
    def test_m5_kernel_value_preferred(self):
        r = ve._zone_json(_z_m5_avail(), "python", LAST_MS, None, "time_5m")
        assert r["available_ts"] == BAR_CLOSE_NS // 1_000_000_000

    def test_m5_available_ts_greater_than_t0(self):
        r = ve._zone_json(_z_m5_avail(), "python", LAST_MS, None, "time_5m")
        assert r["available_ts"] > r["t0"]

    def test_m5_kernel_delta_300s(self):
        r = ve._zone_json(_z_m5_avail(), "python", LAST_MS, None, "time_5m")
        assert r["available_ts"] - r["t0"] == 300

    def test_m5_no_avail_fallback_t0_plus_300(self):
        z = _z_m5_no_avail()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        t0 = int(z["created_ms"] // 1000)
        assert r["available_ts"] == t0 + 300

    def test_tick25_with_avail_uses_kernel(self):
        r = ve._zone_json(_z_t25_avail(), "python", LAST_MS, None, "tick_25")
        assert r["available_ts"] == TICK_CLOSE_NS // 1_000_000_000

    def test_tick25_no_avail_returns_none(self):
        r = ve._zone_json(_z_t25_no_avail(), "python", LAST_MS, None, "tick_25")
        assert r["available_ts"] is None

    def test_source_barspec_m5(self):
        r = ve._zone_json(_z_m5_avail(), "python", LAST_MS, None, "time_5m")
        assert r["source_barspec"] == "time_5m"

    def test_source_barspec_tick25(self):
        r = ve._zone_json(_z_t25_no_avail(), "python", LAST_MS, None, "tick_25")
        assert r["source_barspec"] == "tick_25"

    def test_empty_bar_key_with_avail_at_ns_ok(self):
        r = ve._zone_json(_z_m5_avail(), "python", LAST_MS, None, "")
        assert r["available_ts"] == BAR_CLOSE_NS // 1_000_000_000

    def test_kernel_priority_over_fallback(self):
        z = dict(_z_m5_avail())
        z["available_at_ns"] = BAR_CLOSE_NS - 10_000_000_000
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        kernel_val   = (BAR_CLOSE_NS - 10_000_000_000) // 1_000_000_000
        fallback_val = int(z["created_ms"] // 1000) + 300
        assert r["available_ts"] == kernel_val
        assert r["available_ts"] != fallback_val


class TestCausalSemanticsGeneral:
    def test_no_holdout_violation_in_fixtures(self):
        for ts_ns in [BAR_OPEN_NS, BAR_CLOSE_NS, TICK_OPEN_NS, TICK_CLOSE_NS]:
            assert ts_ns < HOLDOUT_NS

    def test_available_ts_before_holdout(self):
        for z, bkey in [(_z_m5_avail(), "time_5m"), (_z_t25_avail(), "tick_25")]:
            r = ve._zone_json(z, "python", LAST_MS, None, bkey)
            assert r["available_ts"] * 1_000_000_000 < HOLDOUT_NS

    def test_available_ts_geq_t0_for_all_defined_cases(self):
        for z, bkey in [(_z_m5_avail(), "time_5m"), (_z_m5_no_avail(), "time_5m"), (_z_t25_avail(), "tick_25")]:
            r = ve._zone_json(z, "python", LAST_MS, None, bkey)
            if r["available_ts"] is not None:
                assert r["available_ts"] >= r["t0"]
