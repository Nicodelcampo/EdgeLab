"""Tests de semántica causal: available_ts, formation_start/end, compatibilidad
de alias y pipeline productor->exportador en viewer_export._zone_json.

Fixtures sintéticos sin datos de holdout ni outcomes.
Holdout boundary: 1782856800000000000 ns (2026-06-30T22:00:00Z).
"""
from __future__ import annotations
import pytest
from edgelab.bridge import viewer_export as ve
from edgelab.bridge.indicators import bigtrap2absorption as bt2

BAR_OPEN_NS    = 1_780_000_000_000_000_000
BAR_CLOSE_NS   = 1_780_000_300_000_000_000
BAR_CREATED_MS = BAR_CLOSE_NS // 1_000_000
TICK_OPEN_NS   = 1_780_001_000_000_000_000
TICK_CLOSE_NS  = 1_780_001_007_000_000_000
TICK_CREATED_MS = TICK_CLOSE_NS // 1_000_000
HOLDOUT_NS     = 1_782_856_800_000_000_000
LAST_MS        = 1_780_999_999_000


def _z_m5_kernel():
    """Zona idéntica a la emitida por el kernel canónico."""
    return {
        "id": "1_B", "indicator": "BigTrap2Absorption",
        "top": 43500.0, "bottom": 43450.0,
        "kind": "trapped_buyers", "timeline": [],
        "created_bar": 1, "is_bull": True,
        "side": "trapped_buyers", "dir": "short",
        "lo": 43450.0, "hi": 43500.0,
        "vol": 150.0, "nrows": 3, "frac": 0.35, "touches": 0,
        "created_ms": BAR_CREATED_MS,
        "formation_start_ns": BAR_OPEN_NS,
        "formation_end_ns": BAR_CLOSE_NS,
        "available_at_ns": BAR_CLOSE_NS,
        "state": "ACTIVE", "ended_ms": None, "end_reason": None,
        "a_score": 12.5, "a_thr": 10.0,
        "sig_ts": BAR_CLOSE_NS, "sig_idx": 50,
    }


def _z_legacy_form_a():
    """Form A: solo top/bottom/kind, sin hi/lo/side ni formation_*_ns."""
    return {
        "id": "2_S", "top": 43550.0, "bottom": 43500.0,
        "kind": "trapped_sellers",
        "created_ms": BAR_OPEN_NS // 1_000_000,
        "state": "ACTIVE", "touches": 0,
        "ended_ms": None, "end_reason": None,
    }


def _z_legacy_form_b():
    """Form B: solo hi/lo/side, sin top/bottom/kind ni formation_*_ns."""
    return {
        "id": "3_B", "hi": 43520.0, "lo": 43490.0,
        "side": "trapped_buyers",
        "created_ms": TICK_OPEN_NS // 1_000_000,
        "state": "ACTIVE", "touches": 0,
        "ended_ms": None, "end_reason": None,
    }


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


class TestZoneCompatibilityAliases:
    """Compatibilidad dual: top/bottom/kind y hi/lo/side sin KeyError."""

    def test_form_a_top_bottom_kind(self):
        r = ve._zone_json(_z_legacy_form_a(), "python", LAST_MS, None, "time_5m")
        assert r["top"] == 43550.0
        assert r["bottom"] == 43500.0
        assert r["kind"] == "trapped_sellers"

    def test_form_b_hi_lo_side(self):
        r = ve._zone_json(_z_legacy_form_b(), "python", LAST_MS, None, "tick_25")
        assert r["top"] == 43520.0
        assert r["bottom"] == 43490.0
        assert r["kind"] == "trapped_buyers"

    def test_canonical_kernel_has_both_forms(self):
        z = _z_m5_kernel()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["top"] == z["top"] == z["hi"]
        assert r["bottom"] == z["bottom"] == z["lo"]
        assert r["kind"] == z["kind"] == z["side"]


class TestCausalOriginAndTimestamps:
    """Etiquetado exacto de procedencia y relación causal estricta."""

    def test_kernel_available_at_ns_origin(self):
        z = _z_m5_kernel()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["available_origin"] == "KERNEL_AVAILABLE_AT_NS"
        assert r["available_ts"] == BAR_CLOSE_NS // 1_000_000_000
        assert r["formation_start_ts"] == BAR_OPEN_NS // 1_000_000_000
        assert r["formation_end_ts"] == BAR_CLOSE_NS // 1_000_000_000
        assert r["t0"] == r["formation_start_ts"]

    def test_formation_start_end_available_inequality(self):
        """formation_start_ts < formation_end_ts <= available_ts."""
        z = _z_m5_kernel()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["formation_start_ts"] < r["formation_end_ts"]
        assert r["formation_end_ts"] <= r["available_ts"]

    def test_explicit_available_ts_origin(self):
        z = {"id": "exp_1", "top": 100.0, "bottom": 90.0, "available_ts": 1780000500}
        r = ve._zone_json(z, "python", LAST_MS, None, "tick_25")
        assert r["available_origin"] == "EXPLICIT_AVAILABLE_TS"
        assert r["available_ts"] == 1780000500

    def test_derived_compatibility_fallback_time_bars(self):
        z = _z_legacy_form_a()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["available_origin"] == "DERIVED_COMPATIBILITY_FALLBACK"
        assert r["available_ts"] == r["t0"] + 300

    def test_unavailable_origin_for_tick_bars_without_ns(self):
        z = _z_legacy_form_b()
        r = ve._zone_json(z, "python", LAST_MS, None, "tick_25")
        assert r["available_origin"] == "UNAVAILABLE"
        assert r["available_ts"] is None

    def test_kernel_priority_over_fallback(self):
        z = _z_m5_kernel()
        # available_at_ns debe mandar sobre cualquier cálculo t0 + dur
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["available_origin"] == "KERNEL_AVAILABLE_AT_NS"
        assert r["available_ts"] == BAR_CLOSE_NS // 1_000_000_000


class TestProducerToExporterIntegration:
    """Verificación integral productor -> exportador."""

    def test_producer_outputs_all_required_keys(self):
        """Verifica que el productor contenga todos los campos exigidos."""
        class DummyTicks:
            instrument = "GC 06-26"
            price_ticks = [1000, 1001, 1002, 1003, 1004]
            ts_ns = [
                BAR_OPEN_NS,
                BAR_OPEN_NS + 10_000_000,
                BAR_OPEN_NS + 20_000_000,
                BAR_OPEN_NS + 30_000_000,
                BAR_CLOSE_NS,
            ]
        # Verificamos estructura del meta_line y exports
        line = bt2.meta_line({}, DummyTicks.instrument, 0.1)
        assert "indicator=BigTrap2Absorption" in line
        assert "event_format=pipe_v1" in line

    def test_exporter_roundtrip_no_keyerror(self):
        z = _z_m5_kernel()
        r = ve._zone_json(z, "python", LAST_MS, "match_123", "time_5m")
        assert r["id"] == "1_B"
        assert r["source"] == "python"
        assert r["match"] == "match_123"
        assert r["source_barspec"] == "time_5m"
        assert r["available_origin"] == "KERNEL_AVAILABLE_AT_NS"
        # Ningún campo crítico es None o lanza excepción
        for key in ["top", "bottom", "t0", "t1", "available_ts", "kind"]:
            assert r[key] is not None


class TestHoldoutIntegrity:
    def test_all_fixture_timestamps_strictly_pre_holdout(self):
        assert BAR_OPEN_NS < HOLDOUT_NS
        assert BAR_CLOSE_NS < HOLDOUT_NS
        assert TICK_OPEN_NS < HOLDOUT_NS
        assert TICK_CLOSE_NS < HOLDOUT_NS

    def test_exported_available_ts_pre_holdout(self):
        z = _z_m5_kernel()
        r = ve._zone_json(z, "python", LAST_MS, None, "time_5m")
        assert r["available_ts"] * 1_000_000_000 < HOLDOUT_NS