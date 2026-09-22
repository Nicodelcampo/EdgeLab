import pytest
from edgelab.execution_lab.markout import MarkoutAbstain,QuoteObservation,measure_fill_markouts
from edgelab.execution_lab.queue_model import Fill,Side
def f(ts=100,p=100,q=2):return Fill(1,ts,q,p)
def qs(*r):return[QuoteObservation(*x) for x in r]
def m(side,fills,quotes,**kw):return measure_fill_markouts(side,fills,quotes,lineage_id="D:L",**kw)
def test_causal_anchor_never_future():
 r=m(Side.BID,[f()],qs((1,99,99,101,False),(2,101,103,105,False),(3,110,101,103,False)),horizons_ns=(10,),max_anchor_staleness_ns=1,max_horizon_staleness_ns=0);assert r.observations[0].anchor_mid_ticks==100
 assert m(Side.BID,[f()],qs((1,101,99,101,False),(2,110,101,103,False)),horizons_ns=(10,)).abstain_reason is MarkoutAbstain.NO_ANCHOR_QUOTE
 assert m(Side.BID,[f()],qs((1,90,99,101,False),(2,110,101,103,False)),horizons_ns=(10,),max_anchor_staleness_ns=5).abstain_reason is MarkoutAbstain.STALE_ANCHOR_QUOTE
def test_sign_weight_and_fail_closed():
 rows=qs((1,100,99,101,False),(2,110,101,103,False));assert m(Side.BID,[f()],rows,horizons_ns=(10,),max_horizon_staleness_ns=0).observations[0].signed_markout_ticks==2;assert m(Side.ASK,[f()],rows,horizons_ns=(10,),max_horizon_staleness_ns=0).observations[0].signed_markout_ticks==-2
 assert m(Side.BID,[],[]).abstain_reason is MarkoutAbstain.NO_FILLS
 assert m(Side.BID,[f()],qs((1,100,99,101,False),(3,110,100,102,False)),horizons_ns=(10,),max_horizon_staleness_ns=0).abstain_reason is MarkoutAbstain.SEQUENCE_GAP
def test_lineage_and_digest():
 with pytest.raises(ValueError,match="lineage"):measure_fill_markouts(Side.BID,[f()],[],lineage_id="")
 rows=qs((1,100,99,101,False),(2,110,101,103,False));a=m(Side.BID,[f()],rows,horizons_ns=(10,),max_horizon_staleness_ns=0);b=m(Side.BID,[f()],rows,horizons_ns=(10,),max_horizon_staleness_ns=0);assert a.digest==b.digest
