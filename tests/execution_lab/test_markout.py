import pytest
from edgelab.execution_lab.markout import *
from edgelab.execution_lab.queue_model import Fill,Side
def f(ts=100,p=100,q=2):return Fill(1,ts,q,p)
def qs(*r):return[QuoteObservation(*x) for x in r]
def test_signs_and_weighting():
 q=qs((1,100,99,101,False),(2,110,101,103,False));assert measure_fill_markouts(Side.BID,[f()],q,horizons_ns=(10,),max_staleness_ns=0).observations[0].signed_markout_ticks==2;assert measure_fill_markouts(Side.ASK,[f()],q,horizons_ns=(10,),max_staleness_ns=0).observations[0].signed_markout_ticks==-2
 fs=[f(100,100,1),Fill(2,101,3,101)];q=qs((1,100,99,101,False),(2,101,100,102,False),(3,110,101,103,False),(4,111,102,104,False));assert measure_fill_markouts(Side.BID,fs,q,horizons_ns=(10,),max_staleness_ns=0).weighted_markout_ticks[10]==2
def test_abstentions():
 assert measure_fill_markouts(Side.BID,[],[]).abstain_reason is MarkoutAbstain.NO_FILLS
 assert measure_fill_markouts(Side.BID,[f()],[],horizons_ns=(10,)).abstain_reason is MarkoutAbstain.NO_ANCHOR_QUOTE
 assert measure_fill_markouts(Side.BID,[f()],qs((1,100,99,101,False)),horizons_ns=(10,)).abstain_reason is MarkoutAbstain.NO_HORIZON_QUOTE
 assert measure_fill_markouts(Side.BID,[f()],qs((1,100,99,101,False),(3,110,100,102,False)),horizons_ns=(10,),max_staleness_ns=0).abstain_reason is MarkoutAbstain.SEQUENCE_GAP
 assert measure_fill_markouts(Side.BID,[f()],qs((1,100,99,101,False),(2,105,99,101,True),(3,110,100,102,False)),horizons_ns=(10,),max_staleness_ns=0).abstain_reason is MarkoutAbstain.BOOK_RESET
 assert measure_fill_markouts(Side.BID,[f()],qs((1,100,99,101,False),(2,120,100,102,False)),horizons_ns=(10,),max_staleness_ns=5).abstain_reason is MarkoutAbstain.STALE_HORIZON_QUOTE
def test_validation_digest():
 with pytest.raises(ValueError,match="crossed"):QuoteObservation(1,1,2,1)
 q=qs((1,100,99,101,False),(2,110,101,103,False));a=measure_fill_markouts(Side.BID,[f()],q,horizons_ns=(10,),max_staleness_ns=0);b=measure_fill_markouts(Side.BID,[f()],q,horizons_ns=(10,),max_staleness_ns=0);assert a.digest==b.digest and len(a.digest)==64
