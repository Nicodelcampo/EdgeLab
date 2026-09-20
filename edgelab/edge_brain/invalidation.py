from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


INVALIDATED = "INVALIDATED_BY_MEASUREMENT_ERROR"
STALE = "STALE_BY_DEPENDENCY"
REAUDIT = "REQUIRES_REAUDIT"

HARD_RELATIONS = {"DEPENDS_ON", "MEASURED_BY", "IMPLEMENTED_BY"}
SOFT_RELATIONS = {"TESTED_BY", "SUPPORTED_BY", "REPLICATED_BY"}
_STATUS_PRIORITY = {REAUDIT: 1, STALE: 2, INVALIDATED: 3}


@dataclass(frozen=True)
class DependencyEdge:
    """A directed edge where source_id depends on target_id."""

    source_id: str
    target_id: str
    relation: str

    def __post_init__(self) -> None:
        from .typed_registry import TYPED_RELATIONS
        allowed = HARD_RELATIONS | SOFT_RELATIONS | TYPED_RELATIONS | {"CONTRADICTED_BY", "INVALIDATED_BY", "SUPERSEDES"}
        if self.relation not in allowed:
            raise ValueError(f"Unsupported dependency relation: {self.relation}")
        if self.source_id == self.target_id:
            raise ValueError("Self dependencies are forbidden")


def _promote(statuses: dict[str, str], node_id: str, proposed: str) -> bool:
    current = statuses.get(node_id)
    if current is None or _STATUS_PRIORITY[proposed] > _STATUS_PRIORITY[current]:
        statuses[node_id] = proposed
        return True
    return False


def propagate_invalidation(
    invalidated_ids: Iterable[str],
    edges: Iterable[DependencyEdge],
) -> dict[str, str]:
    """Propagate measurement invalidation through explicit dependencies.

    Hard dependencies become STALE_BY_DEPENDENCY. Evidentiary/test links become
    REQUIRES_REAUDIT. Re-audit status propagates, but never upgrades itself to
    invalidation. Contradiction and supersession edges do not propagate.
    """
    reverse: dict[str, list[DependencyEdge]] = {}
    for edge in edges:
        reverse.setdefault(edge.target_id, []).append(edge)

    statuses: dict[str, str] = {}
    queue: list[str] = []
    for node_id in invalidated_ids:
        if _promote(statuses, node_id, INVALIDATED):
            queue.append(node_id)

    cursor = 0
    while cursor < len(queue):
        upstream_id = queue[cursor]
        cursor += 1
        upstream_status = statuses[upstream_id]
        for edge in reverse.get(upstream_id, []):
            if edge.relation in HARD_RELATIONS:
                proposed = STALE if upstream_status in {INVALIDATED, STALE} else REAUDIT
            elif edge.relation in SOFT_RELATIONS:
                proposed = REAUDIT
            else:
                continue
            if _promote(statuses, edge.source_id, proposed):
                queue.append(edge.source_id)
    return statuses
