"""Causal BT2A producer -> exporter regressions; synthetic pre-holdout only."""
from __future__ import annotations

import numpy as np

from edgelab.bridge import bars as bars_mod
from edgelab.bridge import viewer_export as ve
from edgelab.bridge.indicators import bigtrap2absorption as bt2
from edgelab.bridge.ticks import TickSeries

START_NS = 1_780_000_000_000_000_000
END_NS = START_NS + 3_000_000_000
HOLDOUT_NS = 1_782_856_800_000_000_000
LAST_MS = 1_780_999_999_000


def _ticks():
    px = np.asarray([102, 101, 100, 100, 100], dtype=np.int64)
    return TickSeries(
        ts_ns=np.asarray([START_NS + i * 1_000_000_000 for i in range(5)], dtype=np.int64),
        price_ticks=px,
        volume=np.asarray([10, 10, 10, 10, 1], dtype=np.float64),
        bid_ticks=px - 1,
        ask_ticks=px,
        sequence=np.arange(5, dtype=np.int64),
        tick_size=1.0,
        instrument="SYN",
        contract="SYN PREHOLDOUT",
        source="synthetic_fixture",
    )


def _params():
    return {
        "TapeWindowTicks": 4,
        "AbsorptionPct": 0.0,
        "RequireFlowSideMatch": False,
        "ImbalanceMode": "SameLevel",
        "ImbalanceRatio": 1.0,
        "MinStackedRows": 1,
        "MinTrapFrac": 0.0,
        "MinTrapVolume": 0.0,
        "MinExportVolume": 1.0,
        "UseWickFilter": False,
        "InvalidationMode": "None",
    }


def test_bar_duration_is_strict_and_display_key_has_units():
    assert ve._bar_duration_s("time_5m") == 300
    assert ve._bar_duration_s("time_1h") == 3600
    assert ve._bar_duration_s("time_5") is None
    assert ve._bar_duration_s("tick_25") is None
    display = bars_mod.build_time_bars(_ticks(), minutes=5)
    assert ve.bar_key_of(display) == "time_5m"


def test_geometry_aliases_remain_compatible():
    a = ve._zone_json({"top": 10.0, "bottom": 9.0, "kind": "BULL", "t0": 1},
                      "python", LAST_MS, None, "tick_25")
    b = ve._zone_json({"hi": 10.0, "lo": 9.0, "side": "BULL", "t0": 1},
                      "python", LAST_MS, None, "tick_25")
    assert (a["top"], a["bottom"], a["kind"]) == (10.0, 9.0, "BULL")
    assert (b["top"], b["bottom"], b["kind"]) == (10.0, 9.0, "BULL")


def test_unknown_legacy_never_uses_display_as_causal_proxy():
    legacy = {
        "top": 10.0,
        "bottom": 9.0,
        "kind": "BULL",
        # Canonical BT2A legacy created_ms is already the final formation tick.
        "created_ms": END_NS // 1_000_000,
    }
    exported = ve._zone_json(legacy, "python", LAST_MS, None,
                             display_bar_key="time_5m", formation_spec=None)
    assert exported["t0"] == END_NS // 1_000_000_000
    assert exported["available_origin"] == "UNAVAILABLE"
    assert exported["available_ts"] is None
    assert exported["formation_spec"] is None
    assert exported["source_barspec"] is None
    assert exported["display_bar_key"] == "time_5m"


def test_explicit_temporal_formation_may_derive():
    temporal = {"top": 10.0, "bottom": 9.0, "t0": 1_780_000_000,
                "formation_spec": "time_5m"}
    exported = ve._zone_json(temporal, "python", LAST_MS, None, "tick_25")
    assert exported["available_origin"] == "DERIVED_COMPATIBILITY_FALLBACK"
    assert exported["available_ts"] == 1_780_000_300


def test_actual_producer_to_exporter_roundtrip():
    ticks = _ticks()
    producer = bt2.run(ticks, params=_params())
    assert producer["n_zones"] == 1
    produced = producer["zones"][0]
    assert produced["formation_spec"] == "tick_count:4"
    assert produced["created_ms"] == produced["formation_end_ns"] // 1_000_000
    assert produced["available_at_ns"] == produced["formation_end_ns"]

    display = bars_mod.build_time_bars(ticks, minutes=5)
    run = ve.build_run("real-producer", bt2.NAME, display, producer, "psid")
    assert run["display_bar_key"] == "time_5m"
    assert run["formation_spec"] == "tick_count:4"
    zone = run["zones"][0]
    assert zone["formation_spec"] == "tick_count:4"
    assert zone["source_barspec"] == "tick_count:4"
    assert zone["available_origin"] == "KERNEL_AVAILABLE_AT_NS"
    assert zone["formation_start_ts"] < zone["formation_end_ts"] <= zone["available_ts"]
    assert zone["available_ts"] * 1_000_000_000 < HOLDOUT_NS
    assert zone["top"] is not None and zone["bottom"] is not None
