from datetime import datetime, timedelta, timezone

import pytest

from edgelab.research.lux_imb import (
    GeometryError,
    OhlcBar,
    WidthFilter,
    WidthMethod,
    detect_og_vi,
    detect_opening_gaps,
    detect_volume_imbalances,
)

T0 = datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc)


def bar(offset, o, h, l, c):
    return OhlcBar(T0 + timedelta(minutes=offset), o, h, l, c)


def test_bullish_og_uses_wick_gap_not_body_gap():
    previous = bar(0, 99.0, 100.0, 98.0, 99.5)
    current = bar(1, 102.0, 103.0, 101.0, 102.5)
    zone, = detect_opening_gaps(previous, current)
    assert (zone.bottom, zone.top, zone.direction) == (100.0, 101.0, "bullish")
    assert zone.available_at == current.timestamp


def test_bearish_og_uses_wick_gap():
    previous = bar(0, 102.0, 103.0, 101.0, 101.5)
    current = bar(1, 99.0, 100.0, 98.0, 98.5)
    zone, = detect_opening_gaps(previous, current)
    assert (zone.bottom, zone.top, zone.direction) == (100.0, 101.0, "bearish")


def test_bullish_vi_replicates_received_nt8_inequalities():
    previous = bar(0, 99.0, 100.5, 98.5, 100.0)
    current = bar(1, 101.0, 102.5, 100.25, 102.0)
    zone, = detect_volume_imbalances(previous, current)
    assert (zone.bottom, zone.top, zone.direction) == (100.0, 101.0, "bullish")


def test_wicks_not_overlapping_is_og_not_vi():
    previous = bar(0, 99.0, 100.5, 98.5, 100.0)
    current = bar(1, 101.0, 102.5, 100.6, 102.0)
    assert detect_volume_imbalances(previous, current) == ()
    assert [(z.family, z.direction) for z in detect_og_vi(previous, current)] == [
        ("OG", "bullish")
    ]


def test_width_threshold_is_strict():
    previous = bar(0, 99.0, 100.0, 98.0, 99.5)
    current = bar(1, 102.0, 103.0, 101.0, 102.5)
    equal = WidthFilter(True, 1.0, WidthMethod.POINTS)
    below = WidthFilter(True, 0.999, WidthMethod.POINTS)
    assert detect_opening_gaps(previous, current, width_filter=equal) == ()
    assert len(detect_opening_gaps(previous, current, width_filter=below)) == 1


def test_percent_and_atr_filters():
    previous = bar(0, 99.0, 100.0, 98.0, 99.5)
    current = bar(1, 102.0, 103.0, 101.0, 102.5)
    pct = WidthFilter(True, 0.5, WidthMethod.PERCENT)
    assert len(detect_opening_gaps(previous, current, width_filter=pct)) == 1
    atr_equal = WidthFilter(True, 0.5, WidthMethod.ATR)
    assert detect_opening_gaps(previous, current, width_filter=atr_equal, atr=2.0) == ()
    with pytest.raises(GeometryError):
        detect_opening_gaps(previous, current, width_filter=atr_equal)


def test_timestamps_are_causal_and_strictly_ordered():
    with pytest.raises(GeometryError):
        OhlcBar(datetime(2026, 8, 10, 13, 0), 1, 2, 0, 1)
    previous = bar(1, 99.0, 100.0, 98.0, 99.5)
    current = bar(0, 102.0, 103.0, 101.0, 102.5)
    with pytest.raises(GeometryError):
        detect_opening_gaps(previous, current)


def test_contract_contains_no_reaction_or_return_label():
    previous = bar(0, 99.0, 100.0, 98.0, 99.5)
    current = bar(1, 102.0, 103.0, 101.0, 102.5)
    zone, = detect_opening_gaps(previous, current)
    assert not hasattr(zone, "return_value")
    assert not hasattr(zone, "reaction")
    assert not hasattr(zone, "passed")
