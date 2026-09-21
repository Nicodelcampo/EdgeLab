"""Normalized L2/MBO observability and continuity contract.

The contract separates *events* from *evidence that the event stream is
complete*.  A list of rows is never enough to infer packet continuity after an
instrument filter: CME packet sequence numbers are channel-scoped, while book
updates also carry instrument-scoped ordering.

``certify_feed_segment`` therefore accepts channel-level packet observations and
fails closed when the source cannot prove them.  Aggregated MBP is useful for
book state and OFI, but it can never be promoted to exact FIFO queue evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Iterable

CONTRACT_VERSION = "L2_MBO_OBSERVABILITY_V1"


class FeedSchema(str, Enum):
    MBP_AGGREGATED = "MBP_AGGREGATED"
    MBO_ORDER_LEVEL = "MBO_ORDER_LEVEL"


class BookAction(str, Enum):
    SNAPSHOT = "SNAPSHOT"
    ADD = "ADD"
    MODIFY = "MODIFY"
    CANCEL = "CANCEL"
    EXECUTE = "EXECUTE"
    CLEAR = "CLEAR"


class BookSide(str, Enum):
    BID = "BID"
    ASK = "ASK"


class CertificationStatus(str, Enum):
    CERTIFIED_EXACT_QUEUE = "CERTIFIED_EXACT_QUEUE"
    CERTIFIED_AGGREGATED_ONLY = "CERTIFIED_AGGREGATED_ONLY"
    ABSTAIN = "ABSTAIN"


class CertificationReason(str, Enum):
    PASS = "PASS"
    AGGREGATED_MBP_NOT_EXACT_QUEUE = "AGGREGATED_MBP_NOT_EXACT_QUEUE"
    EMPTY_SEGMENT = "EMPTY_SEGMENT"
    MIXED_DATASET = "MIXED_DATASET"
    MIXED_CHANNEL = "MIXED_CHANNEL"
    INVALID_EVENT_ORDER = "INVALID_EVENT_ORDER"
    PACKET_GAP = "PACKET_GAP"
    PACKET_DUPLICATE = "PACKET_DUPLICATE"
    PACKET_EVIDENCE_MISSING = "PACKET_EVIDENCE_MISSING"
    ORDER_ID_MISSING = "ORDER_ID_MISSING"
    PRIORITY_MISSING = "PRIORITY_MISSING"
    SOURCE_HASH_MISSING = "SOURCE_HASH_MISSING"
    TIMESTAMP_INVERSION = "TIMESTAMP_INVERSION"


@dataclass(frozen=True, slots=True)
class SourceProvenance:
    dataset_id: str
    source_name: str
    venue: str
    schema: FeedSchema
    raw_sha256: str
    decoder_id: str
    decoder_sha256: str

    def __post_init__(self) -> None:
        for name in ("dataset_id", "source_name", "venue", "decoder_id"):
            if not getattr(self, name):
                raise ValueError(f"{name} is required")
        for name in ("raw_sha256", "decoder_sha256"):
            value = getattr(self, name)
            if value and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower())):
                raise ValueError(f"{name} must be an empty value or a SHA-256 hex digest")


@dataclass(frozen=True, slots=True)
class NormalizedBookEvent:
    dataset_id: str
    channel_id: str
    instrument_id: str
    packet_sequence: int
    event_index: int
    instrument_sequence: int
    exchange_ts_ns: int
    receive_ts_ns: int | None
    action: BookAction
    side: BookSide | None
    price_ticks: int | None
    quantity: int
    order_id: str | None = None
    priority: int | None = None
    recovered: bool = False

    def __post_init__(self) -> None:
        if not self.dataset_id or not self.channel_id or not self.instrument_id:
            raise ValueError("dataset_id, channel_id and instrument_id are required")
        for name in ("packet_sequence", "event_index", "instrument_sequence", "exchange_ts_ns", "quantity"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.receive_ts_ns is not None and self.receive_ts_ns < 0:
            raise ValueError("receive_ts_ns must be non-negative when observed")
        if self.action not in (BookAction.CLEAR, BookAction.SNAPSHOT):
            if self.side is None or self.price_ticks is None:
                raise ValueError("book mutations require side and price_ticks")
        if self.action is BookAction.ADD and self.quantity <= 0:
            raise ValueError("ADD quantity must be positive")


@dataclass(frozen=True, slots=True)
class PacketObservation:
    """One channel-level packet observation, before instrument filtering."""

    dataset_id: str
    channel_id: str
    packet_sequence: int
    receive_ts_ns: int | None
    recovered: bool = False

    def __post_init__(self) -> None:
        if not self.dataset_id or not self.channel_id:
            raise ValueError("dataset_id and channel_id are required")
        if self.packet_sequence < 0:
            raise ValueError("packet_sequence must be non-negative")
        if self.receive_ts_ns is not None and self.receive_ts_ns < 0:
            raise ValueError("receive_ts_ns must be non-negative when observed")


@dataclass(slots=True)
class FeedCertification:
    contract_version: str = CONTRACT_VERSION
    status: CertificationStatus = CertificationStatus.ABSTAIN
    reasons: list[CertificationReason] = field(default_factory=list)
    event_count: int = 0
    packet_count: int = 0
    recovered_packet_count: int = 0
    first_packet_sequence: int | None = None
    last_packet_sequence: int | None = None
    exact_queue_eligible: bool = False
    digest: str = ""

    def seal(self) -> "FeedCertification":
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["reasons"] = [reason.value for reason in self.reasons]
        payload["digest"] = ""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        self.digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self


def _append_once(reasons: list[CertificationReason], reason: CertificationReason) -> None:
    if reason not in reasons:
        reasons.append(reason)


def certify_feed_segment(
    provenance: SourceProvenance,
    events: Iterable[NormalizedBookEvent],
    packets: Iterable[PacketObservation] | None,
    *,
    require_priority: bool = True,
) -> FeedCertification:
    """Certify whether a segment may support exact FIFO queue reconstruction.

    Packet observations must be channel-level and include packets even when they
    contain no update for the selected instrument.  Passing instrument-filtered
    packet numbers as continuity evidence is a contract violation by meaning,
    even if the integers happen to be contiguous.
    """
    rows = list(events)
    packet_rows = list(packets) if packets is not None else []
    result = FeedCertification(event_count=len(rows), packet_count=len(packet_rows))
    reasons: list[CertificationReason] = []

    if not provenance.raw_sha256 or not provenance.decoder_sha256:
        _append_once(reasons, CertificationReason.SOURCE_HASH_MISSING)
    if not rows:
        _append_once(reasons, CertificationReason.EMPTY_SEGMENT)

    if any(row.dataset_id != provenance.dataset_id for row in rows):
        _append_once(reasons, CertificationReason.MIXED_DATASET)
    event_channels = {row.channel_id for row in rows}
    packet_channels = {row.channel_id for row in packet_rows}
    if len(event_channels) > 1 or len(packet_channels) > 1 or (
        event_channels and packet_channels and event_channels != packet_channels
    ):
        _append_once(reasons, CertificationReason.MIXED_CHANNEL)

    event_keys = [(row.packet_sequence, row.event_index) for row in rows]
    if any(current <= previous for previous, current in zip(event_keys, event_keys[1:])):
        _append_once(reasons, CertificationReason.INVALID_EVENT_ORDER)
    if any(
        current.exchange_ts_ns < previous.exchange_ts_ns
        for previous, current in zip(rows, rows[1:])
    ):
        _append_once(reasons, CertificationReason.TIMESTAMP_INVERSION)

    if not packet_rows:
        _append_once(reasons, CertificationReason.PACKET_EVIDENCE_MISSING)
    else:
        packet_sequences = [row.packet_sequence for row in packet_rows]
        result.first_packet_sequence = packet_sequences[0]
        result.last_packet_sequence = packet_sequences[-1]
        result.recovered_packet_count = sum(row.recovered for row in packet_rows)
        for previous, current in zip(packet_sequences, packet_sequences[1:]):
            if current == previous:
                _append_once(reasons, CertificationReason.PACKET_DUPLICATE)
            elif current != previous + 1:
                _append_once(reasons, CertificationReason.PACKET_GAP)
        if any(row.dataset_id != provenance.dataset_id for row in packet_rows):
            _append_once(reasons, CertificationReason.MIXED_DATASET)

    if provenance.schema is FeedSchema.MBO_ORDER_LEVEL:
        lifecycle = {
            BookAction.ADD,
            BookAction.MODIFY,
            BookAction.CANCEL,
            BookAction.EXECUTE,
        }
        if any(row.action in lifecycle and not row.order_id for row in rows):
            _append_once(reasons, CertificationReason.ORDER_ID_MISSING)
        if require_priority and any(
            row.action in (BookAction.ADD, BookAction.MODIFY) and row.priority is None
            for row in rows
        ):
            _append_once(reasons, CertificationReason.PRIORITY_MISSING)
    else:
        _append_once(reasons, CertificationReason.AGGREGATED_MBP_NOT_EXACT_QUEUE)

    hard_failures = {
        CertificationReason.EMPTY_SEGMENT,
        CertificationReason.MIXED_DATASET,
        CertificationReason.MIXED_CHANNEL,
        CertificationReason.INVALID_EVENT_ORDER,
        CertificationReason.PACKET_GAP,
        CertificationReason.PACKET_DUPLICATE,
        CertificationReason.PACKET_EVIDENCE_MISSING,
        CertificationReason.ORDER_ID_MISSING,
        CertificationReason.PRIORITY_MISSING,
        CertificationReason.SOURCE_HASH_MISSING,
        CertificationReason.TIMESTAMP_INVERSION,
    }
    if hard_failures.intersection(reasons):
        result.status = CertificationStatus.ABSTAIN
        result.exact_queue_eligible = False
    elif provenance.schema is FeedSchema.MBP_AGGREGATED:
        result.status = CertificationStatus.CERTIFIED_AGGREGATED_ONLY
        result.exact_queue_eligible = False
    else:
        result.status = CertificationStatus.CERTIFIED_EXACT_QUEUE
        result.exact_queue_eligible = True
        reasons = [CertificationReason.PASS]

    result.reasons = reasons
    return result.seal()
