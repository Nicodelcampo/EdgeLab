from dataclasses import asdict
import pytest
from edgelab.research.trend_context import EventAlignment, TrendBar, TrendParameters, TrendState, align_event_with_trend, compute_trend_contexts

PARAMS = TrendParameters(ema_fast=2, ema_slow=4, sma_fast=2, sma_slow=4, slope_lookback=1)

def bars(values, *, session="S1", start=1, volumes=None):
    volumes = volumes or [1.0] * len(values)
    return [TrendBar(ts_ns=(start+i)*10, session_id=session, close_ticks=value, volume=volumes[i]) for i,value in enumerate(values)]

def test_rising_series_becomes_uptrend_only_after_warmup():
    c=compute_trend_contexts(bars([1,2,3,4,5,6]),params=PARAMS); assert c[0].trend_state is TrendState.NOT_READY; assert c[2].trend_state is TrendState.NOT_READY; assert c[-1].trend_state is TrendState.UP

def test_falling_series_becomes_downtrend():
    assert compute_trend_contexts(bars([6,5,4,3,2,1]),params=PARAMS)[-1].trend_state is TrendState.DOWN

def test_flat_series_is_neutral_not_trending():
    assert compute_trend_contexts(bars([5,5,5,5,5,5]),params=PARAMS)[-1].trend_state is TrendState.NEUTRAL

def test_session_vwap_resets_but_moving_averages_continue():
    c=compute_trend_contexts(bars([10,20,30,40],session="S1")+[TrendBar(ts_ns=50,session_id="S2",close_ticks=100,volume=2)],params=PARAMS); assert c[-1].vwap_ticks==100; assert c[-1].session_bar_index==0; assert c[-1].ema_fast_ticks!=100

def test_zero_volume_does_not_fabricate_vwap():
    c=compute_trend_contexts(bars([10,20,30,40],volumes=[0,0,0,0]),params=PARAMS); assert all(x.vwap_ticks is None for x in c); assert c[-1].trend_state is TrendState.NOT_READY

def test_typical_price_drives_vwap_when_observed():
    rows=[TrendBar(ts_ns=10,session_id="S",close_ticks=10,typical_price_ticks=8,volume=1),TrendBar(ts_ns=20,session_id="S",close_ticks=20,typical_price_ticks=16,volume=3)]; assert compute_trend_contexts(rows,params=PARAMS)[-1].vwap_ticks==14

def test_prefix_invariance_blocks_future_leakage():
    prefix=bars([1,2,3,4,5,6]); a=compute_trend_contexts(prefix,params=PARAMS); b=compute_trend_contexts(prefix+bars([1000],start=7),params=PARAMS); assert [asdict(x) for x in a]==[asdict(x) for x in b[:len(prefix)]]

def test_context_available_strictly_after_bar_close():
    c=compute_trend_contexts(bars([1,2,3,4]),params=PARAMS,availability_lag_ns=7)[-1]; assert c.available_at_ns==c.ts_ns+7

def test_event_alignment_requires_available_context():
    c=compute_trend_contexts(bars([1,2,3,4,5]),params=PARAMS)[-1]
    with pytest.raises(ValueError,match="precedes"): align_event_with_trend(1,c,event_available_at_ns=c.available_at_ns-1)

def test_event_alignment_distinguishes_with_and_counter_trend():
    c=compute_trend_contexts(bars([1,2,3,4,5]),params=PARAMS)[-1]; assert align_event_with_trend(1,c,event_available_at_ns=c.available_at_ns) is EventAlignment.WITH_TREND; assert align_event_with_trend(-1,c,event_available_at_ns=c.available_at_ns) is EventAlignment.COUNTER_TREND

def test_invalid_parameters_and_timestamps_fail_closed():
    with pytest.raises(ValueError,match="ema_fast"): TrendParameters(ema_fast=5,ema_slow=5)
    rows=[TrendBar(ts_ns=20,session_id="S",close_ticks=1,volume=1),TrendBar(ts_ns=10,session_id="S",close_ticks=2,volume=1)]
    with pytest.raises(ValueError,match="strictly increasing"): compute_trend_contexts(rows,params=PARAMS)

def test_digest_is_deterministic():
    a=compute_trend_contexts(bars([1,2,3,4,5]),params=PARAMS); b=compute_trend_contexts(bars([1,2,3,4,5]),params=PARAMS); assert [x.digest for x in a]==[x.digest for x in b]; assert all(len(x.digest)==64 for x in a)
