from edgelab.execution_lab import (
    AbstainReason,
    BookEvent,
    EventKind,
    PassiveOrder,
    Side,
    simulate_fifo_passive_fill,
)


def ev(seq, kind, *, qty=0, depth=None, side=Side.BID, px=100):
    return BookEvent(sequence=seq, ts_ns=seq * 1_000, kind=kind, side=side, price_ticks=px, quantity=qty, level_depth_after=depth)


def order(**overrides):
    values = dict(order_id="O-1", side=Side.BID, price_ticks=100, quantity=3, decision_sequence=9, latency_events=0)
    values.update(overrides)
    return PassiveOrder(**values)


def test_consumes_queue_ahead_then_preserves_partial_fill():
    result = simulate_fifo_passive_fill(order(), [ev(10, EventKind.SNAPSHOT, depth=5), ev(11, EventKind.EXECUTE, qty=4), ev(12, EventKind.EXECUTE, qty=2)])
    assert result.initial_queue_ahead == 5
    assert result.final_queue_ahead == 0
    assert result.filled_quantity == 1
    assert result.remaining_quantity == 2
    assert [fill.quantity for fill in result.fills] == [1]
    assert not result.complete


def test_anonymous_cancel_never_grants_optimistic_priority():
    result = simulate_fifo_passive_fill(order(quantity=1), [ev(10, EventKind.SNAPSHOT, depth=5), ev(11, EventKind.CANCEL, qty=5), ev(12, EventKind.EXECUTE, qty=1)])
    assert result.filled_quantity == 0
    assert result.final_queue_ahead == 4
    assert result.diagnostics["cancels_ignored"] == 5


def test_latency_defers_activation_and_uses_observed_depth_then():
    result = simulate_fifo_passive_fill(order(quantity=1, latency_events=2), [ev(10, EventKind.SNAPSHOT, depth=9), ev(11, EventKind.EXECUTE, qty=9), ev(12, EventKind.SNAPSHOT, depth=7), ev(13, EventKind.SNAPSHOT, depth=2), ev(14, EventKind.EXECUTE, qty=3)])
    assert result.activation_sequence == 12
    assert result.initial_queue_ahead == 7
    assert result.filled_quantity == 0


def test_missing_depth_at_activation_fails_closed():
    result = simulate_fifo_passive_fill(order(), [ev(10, EventKind.ADD, qty=2), ev(11, EventKind.EXECUTE, qty=20)])
    assert result.abstain_reason is AbstainReason.NO_DEPTH_AT_ACTIVATION
    assert result.filled_quantity == 0


def test_sequence_gap_after_activation_invalidates_result():
    result = simulate_fifo_passive_fill(order(), [ev(10, EventKind.SNAPSHOT, depth=0), ev(12, EventKind.EXECUTE, qty=3)])
    assert result.abstain_reason is AbstainReason.SEQUENCE_GAP
    assert result.filled_quantity == 0


def test_missing_activation_sequence_invalidates_result():
    result = simulate_fifo_passive_fill(order(), [ev(11, EventKind.SNAPSHOT, depth=0), ev(12, EventKind.EXECUTE, qty=3)])
    assert result.abstain_reason is AbstainReason.SEQUENCE_GAP
    assert result.filled_quantity == 0


def test_wrong_side_or_price_cannot_fill():
    result = simulate_fifo_passive_fill(order(quantity=1), [ev(10, EventKind.SNAPSHOT, depth=0), ev(11, EventKind.EXECUTE, qty=5, side=Side.ASK), ev(12, EventKind.EXECUTE, qty=5, px=101)])
    assert result.filled_quantity == 0


def test_reset_abstains_and_digest_is_deterministic():
    rows = [ev(10, EventKind.SNAPSHOT, depth=1), ev(11, EventKind.RESET)]
    first = simulate_fifo_passive_fill(order(), rows)
    second = simulate_fifo_passive_fill(order(), rows)
    assert first.abstain_reason is AbstainReason.BOOK_RESET
    assert first.digest == second.digest
    assert len(first.digest) == 64


def test_invalid_event_order_is_rejected():
    rows = [ev(10, EventKind.SNAPSHOT, depth=1), ev(10, EventKind.EXECUTE, qty=1)]
    try:
        simulate_fifo_passive_fill(order(), rows)
    except ValueError as exc:
        assert "strictly increasing" in str(exc)
    else:
        raise AssertionError("expected strict sequence validation")
