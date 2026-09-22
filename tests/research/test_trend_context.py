from dataclasses import asdict
import pytest
from edgelab.research.trend_context import *
P=TrendParameters(ema_fast=2,ema_slow=4,sma_fast=2,sma_slow=4,slope_lookback=1)
def bars(v,session="S",start=1,volumes=None):
 volumes=volumes or [1]*len(v); return [TrendBar((start+i)*10,session,x,volumes[i]) for i,x in enumerate(v)]
def test_states_and_components():
 up=compute_trend_contexts(bars([1,2,3,4,5,6]),params=P); assert up[2].trend_state is TrendState.NOT_READY and up[-1].trend_state is TrendState.UP; assert(up[-1].ema_state,up[-1].sma_state,up[-1].vwap_state)==(TrendState.UP,)*3
 conflict=compute_trend_contexts(bars([1,2,3,4,5,2]),params=P)[-1]; assert conflict.ema_state is TrendState.DOWN and conflict.sma_state is TrendState.NEUTRAL and conflict.vwap_state is TrendState.DOWN and conflict.trend_state is TrendState.NEUTRAL
def test_down_flat_reset_and_zero_volume():
 assert compute_trend_contexts(bars([6,5,4,3,2,1]),params=P)[-1].trend_state is TrendState.DOWN
 assert compute_trend_contexts(bars([5]*6),params=P)[-1].trend_state is TrendState.NEUTRAL
 c=compute_trend_contexts(bars([10,20,30,40],"S1")+[TrendBar(50,"S2",100,2)],params=P)[-1]; assert c.vwap_ticks==100 and c.session_bar_index==0 and c.ema_fast_ticks!=100
 z=compute_trend_contexts(bars([1,2,3,4],volumes=[0]*4),params=P); assert z[-1].vwap_ticks is None and z[-1].trend_state is TrendState.NOT_READY
def test_vwap_prefix_and_availability():
 r=[TrendBar(10,"S",10,1,8),TrendBar(20,"S",20,3,16)]; assert compute_trend_contexts(r,params=P)[-1].vwap_ticks==14
 pre=bars([1,2,3,4,5,6]); a=compute_trend_contexts(pre,params=P); b=compute_trend_contexts(pre+bars([1000],start=7),params=P); assert[asdict(x) for x in a]==[asdict(x) for x in b[:6]]
 c=compute_trend_contexts(bars([1,2,3,4]),params=P,availability_lag_ns=7)[-1]; assert c.available_at_ns==c.ts_ns+7
def test_alignment_and_fail_closed():
 c=compute_trend_contexts(bars([1,2,3,4,5]),params=P)[-1]
 with pytest.raises(ValueError,match="precedes"):align_event_with_trend(1,c,event_available_at_ns=c.available_at_ns-1)
 assert align_event_with_trend(1,c,event_available_at_ns=c.available_at_ns) is EventAlignment.WITH_TREND
 with pytest.raises(ValueError,match="ema_fast"):TrendParameters(ema_fast=5,ema_slow=5)
 with pytest.raises(ValueError,match="strictly increasing"):compute_trend_contexts([TrendBar(20,"S",1,1),TrendBar(10,"S",2,1)],params=P)
def test_digest_deterministic():
 a=compute_trend_contexts(bars([1,2,3,4,5]),params=P); b=compute_trend_contexts(bars([1,2,3,4,5]),params=P); assert[x.digest for x in a]==[x.digest for x in b]
