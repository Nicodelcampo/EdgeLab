from edgelab.execution_lab.feed_contract import (
    BookAction,
    BookSide,
    CertificationReason,
    CertificationStatus,
    FeedSchema,
    NormalizedBookEvent,
    PacketObservation,
    SourceProvenance,
    certify_feed_segment,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def provenance(schema=FeedSchema.MBO_ORDER_LEVEL, **overrides):
    values = dict(dataset_id="CME-MBO-TEST", source_name="synthetic", venue="CME", schema=schema, raw_sha256=SHA_A, decoder_id="decoder-v1", decoder_sha256=SHA_B)
    values.update(overrides)
    return SourceProvenance(**values)


def event(packet, index, action=BookAction.ADD, **overrides):
    values = dict(dataset_id="CME-MBO-TEST", channel_id="310", instrument_id="NQZ6", packet_sequence=packet, event_index=index, instrument_sequence=packet * 10 + index, exchange_ts_ns=packet * 1_000 + index, receive_ts_ns=packet * 1_000 + index + 100, action=action, side=BookSide.BID, price_ticks=100, quantity=2, order_id=f"O-{packet}-{index}", priority=packet * 100 + index)
    values.update(overrides)
    return NormalizedBookEvent(**values)


def packet(sequence, **overrides):
    values = dict(dataset_id="CME-MBO-TEST", channel_id="310", packet_sequence=sequence, receive_ts_ns=sequence * 1_000 + 100)
    values.update(overrides)
    return PacketObservation(**values)


def test_complete_mbo_segment_is_exact_queue_eligible():
    result = certify_feed_segment(provenance(), [event(10, 0), event(11, 0, BookAction.EXECUTE)], [packet(10), packet(11)])
    assert result.status is CertificationStatus.CERTIFIED_EXACT_QUEUE
    assert result.exact_queue_eligible
    assert result.reasons == [CertificationReason.PASS]
    assert len(result.digest) == 64


def test_aggregated_mbp_can_be_certified_but_never_exact_queue():
    result = certify_feed_segment(provenance(FeedSchema.MBP_AGGREGATED), [event(10, 0, order_id=None, priority=None)], [packet(10)])
    assert result.status is CertificationStatus.CERTIFIED_AGGREGATED_ONLY
    assert not result.exact_queue_eligible
    assert CertificationReason.AGGREGATED_MBP_NOT_EXACT_QUEUE in result.reasons


def test_packet_gap_fails_closed():
    result = certify_feed_segment(provenance(), [event(10, 0), event(12, 0)], [packet(10), packet(12)])
    assert result.status is CertificationStatus.ABSTAIN
    assert CertificationReason.PACKET_GAP in result.reasons


def test_packet_evidence_is_required_even_when_events_look_contiguous():
    result = certify_feed_segment(provenance(), [event(10, 0), event(11, 0)], None)
    assert result.status is CertificationStatus.ABSTAIN
    assert CertificationReason.PACKET_EVIDENCE_MISSING in result.reasons


def test_duplicate_packet_fails_closed():
    result = certify_feed_segment(provenance(), [event(10, 0)], [packet(10), packet(10)])
    assert CertificationReason.PACKET_DUPLICATE in result.reasons


def test_missing_order_identity_blocks_mbo_queue_evidence():
    result = certify_feed_segment(provenance(), [event(10, 0, order_id=None)], [packet(10)])
    assert CertificationReason.ORDER_ID_MISSING in result.reasons
    assert not result.exact_queue_eligible


def test_missing_priority_blocks_exact_fifo_by_default():
    result = certify_feed_segment(provenance(), [event(10, 0, priority=None)], [packet(10)])
    assert CertificationReason.PRIORITY_MISSING in result.reasons


def test_source_hashes_are_hard_evidence():
    result = certify_feed_segment(provenance(raw_sha256=""), [event(10, 0)], [packet(10)])
    assert CertificationReason.SOURCE_HASH_MISSING in result.reasons


def test_event_order_uses_packet_then_event_index_not_timestamp_only():
    result = certify_feed_segment(provenance(), [event(10, 1), event(10, 0)], [packet(10)])
    assert CertificationReason.INVALID_EVENT_ORDER in result.reasons


def test_exchange_timestamp_inversion_abstains():
    result = certify_feed_segment(provenance(), [event(10, 0, exchange_ts_ns=2_000), event(11, 0, exchange_ts_ns=1_000)], [packet(10), packet(11)])
    assert CertificationReason.TIMESTAMP_INVERSION in result.reasons


def test_channel_mixing_abstains():
    result = certify_feed_segment(provenance(), [event(10, 0), event(11, 0, channel_id="311")], [packet(10), packet(11)])
    assert CertificationReason.MIXED_CHANNEL in result.reasons


def test_recovered_packets_are_counted_without_being_treated_as_missing():
    result = certify_feed_segment(provenance(), [event(10, 0), event(11, 0, recovered=True)], [packet(10), packet(11, recovered=True)])
    assert result.status is CertificationStatus.CERTIFIED_EXACT_QUEUE
    assert result.recovered_packet_count == 1
