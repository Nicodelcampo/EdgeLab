"""Fail-closed planner for EdgeLab's future unattended work loop.

This is a deterministic, side-effect-free queue planner. It does not execute
work, call a model, access data, write the Brain ledger, or authorize outcomes.
A separate reviewed executor may consume only READY decisions. Priority is a
resource-allocation heuristic, never evidence of an edge or a promise of growth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TaskKind = Literal["audit", "test", "index", "documentation", "research", "deployment", "trading"]
# Research is intentionally excluded: a target-free label alone cannot prove a
# task is safe, and the Brain may not grant itself authority to inspect outcomes.
UNATTENDED_ALLOWLIST = frozenset({"audit", "test", "index", "documentation"})


@dataclass(frozen=True)
class Candidate:
    task_id: str
    kind: TaskKind
    evidence_ref: str
    expected_reuse: int  # 0..5; expected benefit to future cycles, not an LLM claim
    blocker_reduction: int  # 0..5 against a documented blocker
    uncertainty_reduction: int  # 0..5; falsifiability / information value
    cost_units: int  # declared finite resource units
    dependency_ids: tuple[str, ...] = ()
    failure_count: int = 0
    last_progress_cycle: int = 0
    requires_outcomes: bool = False
    requires_holdout: bool = False
    requires_network: bool = False
    requires_secrets: bool = False
    touches_live_account: bool = False


@dataclass(frozen=True)
class Decision:
    task_id: str
    status: Literal["READY", "WAIT_HUMAN", "BLOCKED", "PARKED"]
    reason: str
    priority: float = 0.0


def plan(
    candidates: list[Candidate],
    *,
    completed_ids: frozenset[str],
    cycle: int,
    available_units: int,
    max_new_tasks: int = 1,
) -> list[Decision]:
    """Rank work by reusable learning per unit; never execute it.

    Repeated failures/stagnation park work for diagnosis. Human-only domains
    remain WAIT_HUMAN. A missing prereg/evidence reference blocks the task.
    """
    if cycle < 0 or available_units < 0 or max_new_tasks < 0:
        raise ValueError("cycle and budgets must be nonnegative")
    ids = [c.task_id for c in candidates]
    if any(not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("task ids must be unique and nonempty")

    decisions: list[Decision] = []
    for c in candidates:
        if c.task_id in completed_ids:
            decisions.append(Decision(c.task_id, "PARKED", "already completed"))
            continue
        if not c.evidence_ref.strip():
            decisions.append(Decision(c.task_id, "BLOCKED", "missing evidence reference"))
            continue
        scores = (c.expected_reuse, c.blocker_reduction, c.uncertainty_reduction)
        if (any(not isinstance(n, int) or not 0 <= n <= 5 for n in scores)
                or not isinstance(c.cost_units, int) or c.cost_units <= 0
                or c.failure_count < 0 or c.last_progress_cycle < 0
                or c.last_progress_cycle > cycle):
            decisions.append(Decision(c.task_id, "BLOCKED", "invalid planning inputs"))
            continue
        if (c.kind not in UNATTENDED_ALLOWLIST or c.requires_outcomes
                or c.requires_holdout or c.requires_network or c.requires_secrets
                or c.touches_live_account):
            decisions.append(Decision(c.task_id, "WAIT_HUMAN", "outside unattended allowlist; requires separate human-authorized workflow"))
            continue
        if c.task_id in c.dependency_ids or any(d not in completed_ids for d in c.dependency_ids):
            decisions.append(Decision(c.task_id, "BLOCKED", "unmet dependency"))
            continue
        if c.failure_count >= 3 or (c.failure_count > 0 and cycle - c.last_progress_cycle >= 3):
            decisions.append(Decision(c.task_id, "PARKED", "stalled/repeated failure; diagnosis required"))
            continue
        # Reuse has highest weight: infrastructure is valuable when it improves
        # multiple later cycles. This is only a transparent ranking heuristic.
        benefit = 3 * c.expected_reuse + 2 * c.blocker_reduction + c.uncertainty_reduction
        if benefit <= 0:
            decisions.append(Decision(c.task_id, "PARKED", "no articulated learning value"))
            continue
        if c.cost_units > available_units:
            decisions.append(Decision(c.task_id, "PARKED", "insufficient budget"))
            continue
        priority = benefit / (c.cost_units * (1 + c.failure_count))
        decisions.append(Decision(c.task_id, "READY", "eligible for separate reviewed executor", priority))

    ranked = sorted((d for d in decisions if d.status == "READY"), key=lambda d: (-d.priority, d.task_id))
    by_id = {c.task_id: c for c in candidates}
    selected: set[str] = set()
    remaining = available_units
    for d in ranked:
        cost = by_id[d.task_id].cost_units
        if len(selected) < max_new_tasks and cost <= remaining:
            selected.add(d.task_id)
            remaining -= cost
    return [
        d if d.status != "READY" or d.task_id in selected
        else Decision(d.task_id, "PARKED", "budget/slot allocated to higher-priority work")
        for d in sorted(decisions, key=lambda d: d.task_id)
    ]


def feedback(
    *, verified_reusable_outputs: int,
    falsified_assumptions: int,
    resolved_blockers: int,
    spent_units: int,
    unattended_cycles: int,
) -> dict[str, object]:
    """Summarize measured learning yield; never infer exponential growth."""
    values = (verified_reusable_outputs, falsified_assumptions, resolved_blockers, spent_units, unattended_cycles)
    if any(not isinstance(v, int) or v < 0 for v in values):
        raise ValueError("observed counts and budgets must be nonnegative integers")
    learning_events = verified_reusable_outputs + falsified_assumptions + resolved_blockers
    yield_per_unit = learning_events / spent_units if spent_units else None
    return {
        "learning_events": learning_events,
        "yield_per_unit": yield_per_unit,
        "idle_cycles": unattended_cycles if spent_units == 0 else 0,
        "recommendation": "STOP_AND_DIAGNOSE" if spent_units > 0 and learning_events == 0 else "REVIEW_EVIDENCE",
    }
