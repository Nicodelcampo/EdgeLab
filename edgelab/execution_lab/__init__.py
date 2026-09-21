"""Execution-fidelity primitives for EdgeLab.

This package is deliberately separate from ``edgelab.research.sim``.  The
legacy simulator remains the sealed market-order contract; this package adds
new, explicitly versioned execution contracts without silently changing old
evidence.
"""

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
    "BookEvent",
    "EventKind",
    "Fill",
    "PassiveOrder",
    "QueueSimulationResult",
    "Side",
    "simulate_fifo_passive_fill",
]
