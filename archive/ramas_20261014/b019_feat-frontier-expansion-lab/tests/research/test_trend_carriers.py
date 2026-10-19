import pytest
from edgelab.research.trend_carriers import *
from edgelab.research.trend_context import EventAlignment,TrendBar,TrendParameters,compute_trend_contexts
P=TrendParameters(ema_fast=2,ema_slow=4,sma_fast=2,sma_slow=4,slope_lookback=1)
def contexts(s="S"): return compute_trend_contexts([TrendBar((i+1)*10,s,v,1) for i,v in enumerate((1,2,3,4,5,6))],params=P)
def test_bigtrap_mapping_and_custody():
 b=adapt_bigtrap2_zone({"id":"B","kind":"trapped_buyers","created_ms":7},available_at_ns=7_000_123,session_id="S",lineage_id="L"); s=adapt_bigtrap2_zone({"id":"S","kind":"trapped_sellers","created_ms":7},available_at_ns=7_000_123,session_id="S",lineage_id="L"); assert(b.continuation_direction,s.continuation_direction)==(-1,1)
 with pytest.raises(ValueError,match="does not match"): adapt_bigtrap2_zone({"id":"B","kind":"trapped_buyers","created_ms":8},available_at_ns=7_999_999,session_id="S",lineage_id="L")
def test_bt2a_redundancy():
 assert adapt_bigtrap2_absorption_zone({"id":"x","kind":"trapped_buyers","dir":"short","sig_ts":99},session_id="S",lineage_id="L").continuation_direction==-1
 with pytest.raises(ValueError,match="inconsistent"): adapt_bigtrap2_absorption_zone({"id":"x","kind":"trapped_buyers","dir":"long","sig_ts":99},session_id="S",lineage_id="L")
def test_hft_events_are_distinct():
 p=adapt_hftzones2_zone({"id":"Z","kind":"support_fast","dir":1,"created_ms":10},available_at_ns=10_000_001,session_id="S",lineage_id="L"); b=adapt_confirmed_zone_bounce(p,bounce_available_at_ns=11_000_000); x=adapt_confirmed_zone_breach(b,breach_available_at_ns=12_000_000); assert(p.continuation_direction,b.continuation_direction,x.continuation_direction)==(1,1,-1)
 with pytest.raises(ValueError,match="after"): adapt_confirmed_zone_bounce(p,bounce_available_at_ns=p.available_at_ns)
def test_hft_conflict_and_certification():
 with pytest.raises(ValueError,match="inconsistent"): adapt_hftzones2_zone({"id":"Z","kind":"resistance_fast","dir":1,"created_ms":10},available_at_ns=10_000_001,session_id="S",lineage_id="L")
 r={"id":"N","source":"HFTZonesNQPureV4","parity_status":"PASS_CERTIFIED_FULL_FIELD_PARITY","available_ts_source":"V2_AVAILABLE_NS","available_ts":123,"direction":1,"session_id":"S"}; assert adapt_hft_nq_v2_zone(r,lineage_id="L").continuation_direction==1
 with pytest.raises(ValueError,match="legacy"): adapt_hft_nq_v2_zone({**r,"available_ts_source":"V1_END_MS_DERIVED_DIAGNOSTIC"},lineage_id="L")
def test_lineage_and_same_session_asof_join():
 z={"id":"x","kind":"trapped_sellers","dir":"long","sig_ts":100}; a=adapt_bigtrap2_absorption_zone(z,session_id="S",lineage_id="L1"); b=adapt_bigtrap2_absorption_zone(z,session_id="S",lineage_id="L2"); assert a.digest!=b.digest
 rows=contexts()+contexts("O"); assert latest_available_context(rows,contexts()[3].available_at_ns,session_id="S")==contexts()[3]
def test_classification_and_order():
 rows=contexts(); c=adapt_bigtrap2_absorption_zone({"id":"x","kind":"trapped_sellers","dir":"long","sig_ts":rows[-1].available_at_ns},session_id="S",lineage_id="L"); assert classify_carrier(c,rows).alignment is EventAlignment.WITH_TREND
 with pytest.raises(ValueError,match="strictly increasing"): latest_available_context(reversed(rows),1000,session_id="S")
