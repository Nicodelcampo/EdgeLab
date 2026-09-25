"""Comparable evaluation receipts for controlled rewrites of the Brain harness.

This module scores a candidate against an incumbent under the same frozen
protocol and resource budget. It is not a trading-strategy or market-outcome
evaluator. The harness must keep holdout task content/results private from the
candidate proposer; this pure comparison function cannot enforce that boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Partition = Literal["selection", "holdout"]
_HEX_256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluationProtocol:
    protocol_sha256: str
    benchmark_sha256: str
    per_trial_budget: int
    minimum_paired_trials_per_partition: int
    minimum_holdout_gain: float = 0.0
    maximum_safety_regressions: int = 0


@dataclass(frozen=True)
class TrialReceipt:
    system_sha256: str
    benchmark_sha256: str
    protocol_sha256: str
    partition: Partition
    task_id: str
    seed: int
    passed: bool
    safe: bool
    resource_units: int
    receipt_sha256: str


@dataclass(frozen=True)
class RewriteAssessment:
    accepted: bool
    reason: str
    selection_delta: float
    holdout_delta: float
    safety_regressions: int
    paired_trials_per_partition: int
    same_budget: bool


def _digest(value: str) -> bool:
    return bool(_HEX_256.fullmatch(value))


def _index(receipts: list[TrialReceipt], protocol: EvaluationProtocol) -> dict[tuple[str, str, int], TrialReceipt]:
    indexed: dict[tuple[str, str, int], TrialReceipt] = {}
    for r in receipts:
        if not all(_digest(v) for v in (r.system_sha256, r.benchmark_sha256, r.protocol_sha256, r.receipt_sha256)):
            raise ValueError("every trial must carry valid SHA-256 identities")
        if r.protocol_sha256 != protocol.protocol_sha256 or r.benchmark_sha256 != protocol.benchmark_sha256:
            raise ValueError("trial identity does not match the frozen evaluation protocol")
        if r.partition not in ("selection", "holdout") or not r.task_id.strip() or r.seed < 0:
            raise ValueError("invalid partition, task id, or seed")
        if not isinstance(r.passed, bool) or not isinstance(r.safe, bool):
            raise ValueError("trial outcomes must be boolean grader results")
        if not isinstance(r.resource_units, int) or r.resource_units <= 0 or r.resource_units > protocol.per_trial_budget:
            raise ValueError("trial exceeds or invalidates the preregistered resource budget")
        key = (r.partition, r.task_id, r.seed)
        if key in indexed:
            raise ValueError(f"duplicate trial receipt: {key}")
        indexed[key] = r
    return indexed


def assess_rewrite(
    protocol: EvaluationProtocol,
    incumbent: list[TrialReceipt],
    candidate: list[TrialReceipt],
) -> RewriteAssessment:
    """Assess a rewrite; only a private holdout gain can accept it.

    Requires paired tasks/seeds in both partitions and per-run cost parity.
    This returns a raw benchmark decision, not proof of general capability
    gains: the outer harness must keep holdout data hidden and test additional
    domains before claiming transfer or compounding.
    """
    if not _digest(protocol.protocol_sha256) or not _digest(protocol.benchmark_sha256):
        raise ValueError("protocol and benchmark require frozen SHA-256 identities")
    if (protocol.per_trial_budget <= 0 or protocol.minimum_paired_trials_per_partition <= 0
            or not 0.0 <= protocol.minimum_holdout_gain <= 1.0
            or protocol.maximum_safety_regressions < 0):
        raise ValueError("invalid frozen protocol limits")
    base = _index(incumbent, protocol)
    new = _index(candidate, protocol)
    if not base or not new or set(base) != set(new):
        raise ValueError("incumbent/candidate trials must be nonempty and exactly paired")
    tasks_by_partition: dict[str, set[str]] = {"selection": set(), "holdout": set()}
    for partition, task_id, _ in base:
        tasks_by_partition[partition].add(task_id)
    if tasks_by_partition["selection"] & tasks_by_partition["holdout"]:
        raise ValueError("selection and holdout task IDs must be disjoint")
    counts = {p: sum(1 for key in base if key[0] == p) for p in ("selection", "holdout")}
    if any(counts[p] < protocol.minimum_paired_trials_per_partition for p in counts):
        raise ValueError("insufficient paired trials for preregistered evaluation")

    budgets = [base[k].resource_units == new[k].resource_units for k in base]
    same_budget = all(budgets)
    if not same_budget:
        raise ValueError("candidate and incumbent must use equal per-trial resource budgets")

    def rate(rows: dict[tuple[str, str, int], TrialReceipt], partition: str, attr: str) -> float:
        subset = [getattr(r, attr) for k, r in rows.items() if k[0] == partition]
        return sum(subset) / len(subset)

    selection_delta = rate(new, "selection", "passed") - rate(base, "selection", "passed")
    holdout_delta = rate(new, "holdout", "passed") - rate(base, "holdout", "passed")
    safety_regressions = sum(1 for k in base if base[k].safe and not new[k].safe)
    accepted = (holdout_delta >= protocol.minimum_holdout_gain
                and safety_regressions <= protocol.maximum_safety_regressions)
    reason = "HOLDOUT_GAIN_WITHIN_FROZEN_BUDGET" if accepted else "REJECT_NO_HOLDOUT_GAIN_OR_SAFETY_REGRESSION"
    return RewriteAssessment(accepted, reason, selection_delta, holdout_delta,
                             safety_regressions, counts["holdout"], same_budget)
