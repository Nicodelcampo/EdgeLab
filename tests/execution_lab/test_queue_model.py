from edgelab.execution_lab import AbstainReason,BookEvent,EventKind,PassiveOrder,Side,simulate_fifo_passive_fill
import pytest
def ev(seq,kind,qty=0,depth=None,side=Side.BID,px=100):return BookEvent(seq,seq*1000,kind,side,px,qty,depth)
def order(**kw):
 v=dict(order_id="O",side=Side.BID,price_ticks=100,quantity=3,decision_sequence=9,latency_events=0);v.update(kw);return PassiveOrder(**v)
def test_queue_partial_and_cancel_conservative():
 r=simulate_fifo_passive_fill(order(),[ev(10,EventKind.SNAPSHOT,depth=5),ev(11,EventKind.EXECUTE,qty=4),ev(12,EventKind.EXECUTE,qty=2)]);assert r.filled_quantity==1 and r.final_queue_ahead==0
 r=simulate_fifo_passive_fill(order(quantity=1),[ev(10,EventKind.SNAPSHOT,depth=5),ev(11,EventKind.CANCEL,qty=5),ev(12,EventKind.EXECUTE,qty=1)]);assert r.filled_quantity==0
def test_activation_level_and_fill_validation():
 r=simulate_fifo_passive_fill(order(),[ev(10,EventKind.SNAPSHOT,depth=5,side=Side.ASK)]);assert r.abstain_reason is AbstainReason.ACTIVATION_LEVEL_MISMATCH
 from edgelab.execution_lab.queue_model import Fill
 with pytest.raises(ValueError,match="positive"):Fill(1,1,0,100)
def test_gap_reset_and_digest():
 assert simulate_fifo_passive_fill(order(),[ev(10,EventKind.SNAPSHOT,depth=0),ev(12,EventKind.EXECUTE,qty=3)]).abstain_reason is AbstainReason.SEQUENCE_GAP
 rows=[ev(10,EventKind.SNAPSHOT,depth=1),ev(11,EventKind.RESET)];a=simulate_fifo_passive_fill(order(),rows);b=simulate_fifo_passive_fill(order(),rows);assert a.abstain_reason is AbstainReason.BOOK_RESET and a.digest==b.digest
