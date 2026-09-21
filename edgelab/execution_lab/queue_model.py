"""Conservative FIFO passive-fill model over observed L2 events.

Contract ``QUEUE_FIFO_L2_V1`` is intentionally fail-closed:

* an order activates only after its declared event latency;
* queue depth at activation must be observed, never imputed;
* sequence gaps after activation invalidate the result;
* anonymous cancellations never improve queue position;
* only observed executions at the order's side and price consume queue ahead;
* partial fills are retained rather than rounded to an all-or-none fill.

This is an execution-observability primitive, not a trading strategy and not
proof of edge.  It does not read outcomes or the sealed holdout.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable

CONTRACT_VERSION = "QUEUE_FIFO_L2_V1"


class Side(str, Enum):
    BID = "BID"
    ASK = "ASK"


class EventKind(str, Enum):
    SNAPSHOT = "SNAPSHOT"
    ADD = "ADD"
    CANCEL = "CANCEL"
    EXECUTE = "EXECUTE"
    RESET = "RESET"


class AbstainReason(str, Enum):
    NO_ACTIVATION_EVENT = "NO_ACTIVATION_EVENT"
    NO_DEPTH_AT_ACTIVATION = "NO_DEPTH_AT_ACTIVATION"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    BOOK_RESET = "BOOK_RESET"


@dataclass(frozen=True, slots=True)
class BookEvent:
    sequence: int
    ts_ns: int
    kind: EventKind
    side: Side
    price_ticks: int
    quantity: int
    level_depth_after: int | None = None

    def __post_init__(self) -> None:
        if self.sequence < 0 or self.ts_ns < 0:
            raise ValueError("sequence and ts_ns must be non-negative")
        if self.quantity < 0:
            raise ValueError("quantity must be non-negative")
        if self.level_depth_after is not None and self.level_depth_after < 0:
            raise ValueError("level_depth_after must be non-negative")
        if self.kind is EventKind.SNAPSHOT and self.level_depth_after is None:
            raise ValueError("SNAPSHOT requires level_depth_after")


@dataclass(frozen=True, slots=True)
class PassiveOrder:
    order_id: str
    side: Side
    price_ticks: int
    quantity: int
    decision_sequence: int
    latency_events: int = 0

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id is required")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.decision_sequence < 0 or self.latency_events < 0:
            raise ValueError("decision_sequence and latency_events must be non-negative")

    @property
    def activation_sequence(self) -> int:
        return self.decision_sequence + self.latency_events + 1


@dataclass(frozen=True, slots=True)
class Fill:
    sequence: int
    ts_ns: int
    quantity: int
    price_ticks: int


@dataclass(slots=True)
class QueueSimulationResult:
    order_id: str
    contract_version: str = CONTRACT_VERSION
    activation_sequence: int | None = None
    initial_queue_ahead: int | None = None
    final_queue_ahead: int | None = None
    filled_quantity: int = 0
    remaining_quantity: int = 0
    fills: list[Fill] = field(default_factory=list)
    abstain_reason: AbstainReason | None = None
    diagnostics: dict[str, int] = field(default_factory=dict)
    digest: str = ""

    @property
    def complete(self) -> bool:
        return self.abstain_reason is None and self.remaining_quantity == 0

    def seal(self) -> "QueueSimulationResult":
        payload = asdict(self)
        payload["abstain_reason"] = (
            self.abstain_reason.value if self.abstain_reason is not None else None
        )
        payload["fills"] = [asdict(fill) for fill in self.fills]
        payload["digest"] = ""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self


def _ordered(events: Iterable[BookEvent]) -> list[BookEvent]:
    rows = list(events)
    if any(b.sequence <= a.sequence for a, b in zip(rows, rows[1:])):
        raise ValueError("events must be strictly increasing by sequence")
    if any(b.ts_ns < a.ts_ns for a, b in zip(rows, rows[1:])):
        raise ValueError("events must be non-decreasing by ts_ns")
    return rows


def simulate_fifo_passive_fill(
    order: PassiveOrder,
    events: Iterable[BookEvent],
    *,
    require_contiguous_sequences: bool = True,
) -> QueueSimulationResult:
    """Simulate one passive FIFO order using only observed book events.

    ``level_depth_after`` on the activation event is the observable depth already
    resting at the level after that event.  The new order joins behind it.  Adds
    and anonymous cancels after activation do not improve the simulated order's
    position.  Executions first consume queue ahead and only then fill the order.
    """
    rows = _ordered(events)
    result = QueueSimulationResult(
        order_id=order.order_id,
        remaining_quantity=order.quantity,
        diagnostics={"cancels_ignored": 0, "adds_behind": 0, "executed_at_level": 0},
    )

    activation_index = next(
        (i for i, row in enumerate(rows) if row.sequence >= order.activation_sequence),
        None,
    )
    if activation_index is None:
        result.abstain_reason = AbstainReason.NO_ACTIVATION_EVENT
        return result.seal()

    activation = rows[activation_index]
    result.activation_sequence = activation.sequence
    if require_contiguous_sequences and activation.sequence != order.activation_sequence:
        result.abstain_reason = AbstainReason.SEQUENCE_GAP
        return result.seal()
    if activation.level_depth_after is None:
        result.abstain_reason = AbstainReason.NO_DEPTH_AT_ACTIVATION
        return result.seal()

    queue_ahead = activation.level_depth_after
    result.initial_queue_ahead = queue_ahead
    previous_sequence = activation.sequence

    for row in rows[activation_index + 1 :]:
        if require_contiguous_sequences and row.sequence != previous_sequence + 1:
            result.final_queue_ahead = queue_ahead
            result.abstain_reason = AbstainReason.SEQUENCE_GAP
            return result.seal()
        previous_sequence = row.sequence

        if row.kind is EventKind.RESET:
            result.final_queue_ahead = queue_ahead
            result.abstain_reason = AbstainReason.BOOK_RESET
            return result.seal()
        if row.side is not order.side or row.price_ticks != order.price_ticks:
            continue
        if row.kind is EventKind.CANCEL:
            result.diagnostics["cancels_ignored"] += row.quantity
            continue
        if row.kind is EventKind.ADD:
            result.diagnostics["adds_behind"] += row.quantity
            continue
        if row.kind is not EventKind.EXECUTE or row.quantity == 0:
            continue

        result.diagnostics["executed_at_level"] += row.quantity
        consumes_ahead = min(queue_ahead, row.quantity)
        queue_ahead -= consumes_ahead
        executable = row.quantity - consumes_ahead
        if executable <= 0:
            continue
        fill_quantity = min(result.remaining_quantity, executable)
        result.fills.append(
            Fill(
                sequence=row.sequence,
                ts_ns=row.ts_ns,
                quantity=fill_quantity,
                price_ticks=order.price_ticks,
            )
        )
        result.filled_quantity += fill_quantity
        result.remaining_quantity -= fill_quantity
        if result.remaining_quantity == 0:
            break

    result.final_queue_ahead = queue_ahead
    return result.seal()
