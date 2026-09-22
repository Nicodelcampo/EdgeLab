from collections import Counter
import pytest
from edgelab.research.trend_ablation import ContextCell
from edgelab.research.trend_ablation_runtime import evaluate_cell,shuffle_states_within_session
from edgelab.research.trend_carriers import adapt_bigtrap2_absorption_zone
from edgelab.research.trend_context import EventAlignment,TrendBar,TrendParameters,compute_trend_contexts
P=TrendParameters(ema_fast=2,ema_slow=4,sma_fast=2,sma_slow=4,slope_lookback=1)
def rows(s="S",v=(1,2,3,4,5,6)):return compute_trend_contexts([TrendBar((i+1)*10,s,x,1) for i,x in enumerate(v)],params=P)
def carrier(ts,s="S"):return adapt_bigtrap2_absorption_zone({"id":"x","kind":"trapped_sellers","dir":"long","sig_ts":ts},session_id=s,lineage_id="L")
def test_real_cells():
 c=rows()[-1];k=carrier(c.available_at_ns);assert evaluate_cell(k,c,ContextCell.CARRIER_ONLY).alignment is None
 for cell in (ContextCell.EMA_ONLY,ContextCell.SMA_ONLY,ContextCell.VWAP_ONLY,ContextCell.ALL_COMPONENTS):
  o=evaluate_cell(k,c,cell);assert o.alignment is EventAlignment.WITH_TREND and o.execution_eligible and not o.placebo
def test_shuffle_deterministic_count_preserving_session_local():
 r=rows()+rows("O",(6,5,4,3,2,1));a=shuffle_states_within_session(r,seed=7,replicate=0);assert a==shuffle_states_within_session(r,seed=7,replicate=0)
 for s in ("S","O"):
  g=[x for x in r if x.session_id==s];assert Counter(a[x.digest] for x in g)==Counter(x.trend_state for x in g)
def test_placebo_never_execution_eligible():
 c=rows()[-1];o=evaluate_cell(carrier(c.available_at_ns),c,ContextCell.SHUFFLED_ALL_WITHIN_SESSION,shuffled_states=shuffle_states_within_session(rows(),seed=7,replicate=0));assert o.placebo and not o.execution_eligible
def test_fail_closed():
 c=rows()[-1]
 with pytest.raises(ValueError,match="shuffled"):evaluate_cell(carrier(c.available_at_ns),c,ContextCell.SHUFFLED_ALL_WITHIN_SESSION)
 with pytest.raises(ValueError,match="session"):evaluate_cell(carrier(c.available_at_ns,"O"),c,ContextCell.ALL_COMPONENTS)
 with pytest.raises(ValueError,match="causally"):evaluate_cell(carrier(c.available_at_ns-1),c,ContextCell.ALL_COMPONENTS)
