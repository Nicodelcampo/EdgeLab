"""Tests adversariales del contrato EventIdentity v2."""
from dataclasses import replace

import pytest

from edgelab.data.event_identity import (
    EventIdentityError,
    EventIdentityV2,
    audit_capture,
)


def event(seq=0, **updates):
    base = dict(
        capture_id="capture-20260803-a",
        process_instance_id="nt8-4242-start-100",
        instrument="6E",
        contract="6E 09-26",
        event_kind="last",
        callback_seq=seq,
        capture_seq=seq,
        source_time_ns=1_700_000_000_000_000_000 + seq * 100,
        capture_utc_ns=1_700_000_000_100_000_000 + seq * 200,
        monotonic_ns=10_000 + seq * 50,
        timestamp_provenance="nt8_event_time",
        quote_provenance="nt8_snapshot",
        aggressor="buy",
        aggressor_provenance="quote_rule",
        price_ticks=21_500,
        volume=2.0,
        bid_ticks=21_499,
        ask_ticks=21_500,
    )
    base.update(updates)
    return EventIdentityV2(**base)


def test_event_id_is_deterministic_and_content_bound():
    a = event()
    assert a.event_id == event().event_id
    assert a.event_id != replace(a, price_ticks=a.price_ticks + 1).event_id


def test_identical_market_payloads_remain_distinct_callbacks():
    a = event(0)
    b = event(
        1,
        source_time_ns=a.source_time_ns,
        price_ticks=a.price_ticks,
        volume=a.volume,
        bid_ticks=a.bid_ticks,
        ask_ticks=a.ask_ticks,
    )
    assert a.event_id != b.event_id
    report = audit_capture([a, b])
    assert report.ok
    assert report.source_timestamp_duplicates == 1


def test_nanoseconds_that_alias_in_milliseconds_are_reported():
    a = event(0, source_time_ns=1_700_000_000_000_000_100)
    b = event(1, source_time_ns=1_700_000_000_000_000_900)
    report = audit_capture([a, b])
    assert report.ok
    assert report.millisecond_aliases == 1


def test_local_sequence_does_not_claim_upstream_continuity():
    report = audit_capture([event(0), event(1)])
    assert report.ok
    assert report.missing_external_sequence == 2
    assert report.upstream_loss_observable is False


def test_external_sequence_requires_explicit_scope():
    with pytest.raises(EventIdentityError, match="deben aparecer juntos"):
        event(source_sequence="123")
    with pytest.raises(EventIdentityError, match="deben aparecer juntos"):
        event(source_sequence_scope="exchange")


def test_declared_provider_sequence_makes_loss_auditable_not_proven_absent():
    rows = [
        event(0, source_sequence="500", source_sequence_scope="provider"),
        event(1, source_sequence="502", source_sequence_scope="provider"),
    ]
    report = audit_capture(rows)
    assert report.ok
    assert report.upstream_loss_observable is True
    # El auditor no inventa una interpretación del salto: proveedor y contrato
    # de feed deben definir si 501 era esperable antes de llamarlo pérdida.


def test_duplicate_or_gapped_capture_sequence_fails_loud():
    rows = [event(0), event(1), event(2)]
    assert audit_capture(rows).ok
    broken = [rows[0], replace(rows[1], capture_seq=2), replace(rows[2], capture_seq=3)]
    report = audit_capture(broken)
    assert not report.ok
    assert any("capture_seq" in e for e in report.errors)


def test_callback_and_monotonic_regressions_fail_loud():
    a = event(0)
    b = event(1, callback_seq=0, monotonic_ns=a.monotonic_ns - 1)
    report = audit_capture([a, b])
    assert not report.ok
    assert any("callback_seq" in e for e in report.errors)
    assert any("monotonic_ns" in e for e in report.errors)


def test_mixed_capture_ids_are_rejected():
    report = audit_capture([event(0), event(1, capture_id="otra-captura")])
    assert not report.ok
    assert report.capture_id is None
    assert any("captura mezclada" in e for e in report.errors)


def test_crossed_quote_and_invalid_provenance_are_rejected():
    with pytest.raises(EventIdentityError, match="quote cruzada"):
        event(bid_ticks=21_501, ask_ticks=21_500)
    with pytest.raises(EventIdentityError, match="aggressor_provenance"):
        event(aggressor_provenance="native_magic")
