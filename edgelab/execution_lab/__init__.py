"""Execution-fidelity primitives for EdgeLab.

This package is deliberately separate from ``edgelab.research.sim``.  The
legacy simulator remains the sealed market-order contract; this package adds
new, explicitly versioned execution contracts without silently changing old
evidence.
"""

from .feed_contract import (
    BookAction,
    BookSide,
    CertificationReason,
    CertificationStatus,
    FeedCertification,
    FeedSchema,
    NormalizedBookEvent,
    PacketObservation,
    SourceProvenance,
    certify_feed_segment,
)
from .queue_model import (
    AbstainReason,
    BookEvent,
    EventKind,
    Fill,
    PassiveOrder,
    QueueSimulationResult,
    Side,
    simulate_fifo_passive_fill,
)

__all__ = [
    "AbstainReason",
    "BookAction",
    "BookSide",
    "BookEvent",
    "CertificationReason",
    "CertificationStatus",
    "EventKind",
    "FeedCertification",
    "FeedSchema",
    "Fill",
    "NormalizedBookEvent",
    "PacketObservation",
    "PassiveOrder",
    "QueueSimulationResult",
    "Side",
    "SourceProvenance",
    "certify_feed_segment",
    "simulate_fifo_passive_fill",
]
