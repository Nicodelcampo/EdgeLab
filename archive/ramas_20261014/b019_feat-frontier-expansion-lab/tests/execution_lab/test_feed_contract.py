from edgelab.execution_lab.feed_contract import *
A="a"*64;B="b"*64
def prov(schema=FeedSchema.MBO_ORDER_LEVEL):return SourceProvenance("D","synthetic","CME",schema,A,"dec",B)
def e(p,i=0,**kw):
 v=dict(dataset_id="D",channel_id="C",instrument_id="NQ",packet_sequence=p,event_index=i,instrument_sequence=p*10+i,exchange_ts_ns=p*1000+i,receive_ts_ns=p*1000+10,action=BookAction.ADD,side=BookSide.BID,price_ticks=100,quantity=2,order_id=f"O{p}{i}",priority=p*10+i);v.update(kw);return NormalizedBookEvent(**v)
def pk(p,**kw):
 v=dict(dataset_id="D",channel_id="C",packet_sequence=p,receive_ts_ns=p*1000+10);v.update(kw);return PacketObservation(**v)
def test_exact_and_aggregated():
 assert certify_feed_segment(prov(),[e(10),e(11,action=BookAction.EXECUTE)],[pk(10),pk(11)]).status is CertificationStatus.CERTIFIED_EXACT_QUEUE
 assert certify_feed_segment(prov(FeedSchema.MBP_AGGREGATED),[e(10,order_id=None,priority=None)],[pk(10)]).status is CertificationStatus.CERTIFIED_AGGREGATED_ONLY
def test_new_evidence_gates():
 assert CertificationReason.EVENT_PACKET_UNOBSERVED in certify_feed_segment(prov(),[e(10),e(11)],[pk(10)]).reasons
 assert CertificationReason.PACKET_TIMESTAMP_INVERSION in certify_feed_segment(prov(),[e(10),e(11)],[pk(10,receive_ts_ns=2000),pk(11,receive_ts_ns=1000)]).reasons
 assert CertificationReason.INVALID_INSTRUMENT_ORDER in certify_feed_segment(prov(),[e(10,instrument_sequence=20),e(11,instrument_sequence=19)],[pk(10),pk(11)]).reasons
def test_gap_identity_and_hash_fail():
 assert CertificationReason.PACKET_GAP in certify_feed_segment(prov(),[e(10),e(12)],[pk(10),pk(12)]).reasons
 assert CertificationReason.ORDER_ID_MISSING in certify_feed_segment(prov(),[e(10,order_id=None)],[pk(10)]).reasons
