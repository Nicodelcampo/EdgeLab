"""Comparable development-evaluation receipts for Brain-harness rewrites.

This module can nominate a rewrite for a separate final audit; it cannot
promote an agent. It is not a market-outcome evaluator. The harness must keep
development task content/results private from the inner candidate proposer and
reserve a distinct sealed final audit. This function cannot enforce either
access boundary or authenticate its caller. SHA-256 fields are integrity/
identity checks, not signed attestations.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal

Partition = Literal["selection", "development"]
_HEX_256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class EvaluationProtocol:
    protocol_sha256: str
    benchmark_sha256: str
    per_trial_budget: int
    minimum_paired_trials_per_partition: int
    minimum_development_gain: float = 0.0
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
    eligible_for_final_audit: bool
    reason: str
    selection_delta: float
    development_delta: float
    safety_regressions: int
    paired_trials_per_partition: int
    same_budget: bool


def _digest(value: str) -> bool:
    return isinstance(value, str) and bool(_HEX_256.fullmatch(value))


def _canonical_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _protocol_payload(benchmark_sha256: str, per_trial_budget: int,
                      minimum_paired_trials_per_partition: int,
                      minimum_development_gain: float,
                      maximum_safety_regressions: int) -> dict[str, object]:
    return {"benchmark_sha256": benchmark_sha256,
            "per_trial_budget": per_trial_budget,
            "minimum_paired_trials_per_partition": minimum_paired_trials_per_partition,
            "minimum_development_gain": minimum_development_gain,
            "maximum_safety_regressions": maximum_safety_regressions}


def create_protocol(*, benchmark_sha256: str, per_trial_budget: int,
                    minimum_paired_trials_per_partition: int,
                    minimum_development_gain: float = 0.0,
                    maximum_safety_regressions: int = 0) -> EvaluationProtocol:
    """Freeze a development-evaluation config into its deterministic identity."""
    payload = _protocol_payload(benchmark_sha256, per_trial_budget,
                                minimum_paired_trials_per_partition,
                                minimum_development_gain, maximum_safety_regressions)
    return EvaluationProtocol(_canonical_sha256(payload), benchmark_sha256,
                              per_trial_budget, minimum_paired_trials_per_partition,
                              minimum_development_gain, maximum_safety_regressions)


def _trial_payload(*, system_sha256: str, benchmark_sha256: str, protocol_sha256: str,
                   partition: Partition, task_id: str, seed: int, passed: bool,
                   safe: bool, resource_units: int) -> dict[str, object]:
    return {"system_sha256": system_sha256, "benchmark_sha256": benchmark_sha256,
            "protocol_sha256": protocol_sha256, "partition": partition,
            "task_id": task_id, "seed": seed, "passed": passed,
            "safe": safe, "resource_units": resource_units}


def create_trial_receipt(*, system_sha256: str, benchmark_sha256: str,
                         protocol_sha256: str, partition: Partition, task_id: str,
                         seed: int, passed: bool, safe: bool,
                         resource_units: int) -> TrialReceipt:
    """Build a self-consistent receipt; does not attest that a grader ran."""
    payload = _trial_payload(system_sha256=system_sha256, benchmark_sha256=benchmark_sha256,
                             protocol_sha256=protocol_sha256, partition=partition,
                             task_id=task_id, seed=seed, passed=passed, safe=safe,
                             resource_units=resource_units)
    return TrialReceipt(**payload, receipt_sha256=_canonical_sha256(payload))


def _index(receipts: list[TrialReceipt], protocol: EvaluationProtocol) -> dict[tuple[str, str, int], TrialReceipt]:
    indexed: dict[tuple[str, str, int], TrialReceipt] = {}
    for r in receipts:
        if not all(_digest(v) for v in (r.system_sha256, r.benchmark_sha256, r.protocol_sha256, r.receipt_sha256)):
            raise ValueError("every trial must carry valid SHA-256 identities")
        if not isinstance(r.task_id, str) or not r.task_id.strip() or type(r.seed) is not int or r.seed < 0:
            raise ValueError("invalid task id or seed")
        if not isinstance(r.passed, bool) or not isinstance(r.safe, bool):
            raise ValueError("trial outcomes must be boolean grader results")
        if r.partition not in ("selection", "development"):
            raise ValueError("partition must be selection or development")
        if type(r.resource_units) is not int or r.resource_units <= 0 or r.resource_units > protocol.per_trial_budget:
            raise ValueError("trial exceeds or invalidates the preregistered resource budget")
        payload = _trial_payload(system_sha256=r.system_sha256, benchmark_sha256=r.benchmark_sha256,
                                 protocol_sha256=r.protocol_sha256, partition=r.partition,
                                 task_id=r.task_id, seed=r.seed, passed=r.passed,
                                 safe=r.safe, resource_units=r.resource_units)
        if r.receipt_sha256 != _canonical_sha256(payload):
            raise ValueError("trial receipt checksum mismatch; data was altered or malformed")
        if r.protocol_sha256 != protocol.protocol_sha256 or r.benchmark_sha256 != protocol.benchmark_sha256:
            raise ValueError("trial identity does not match the frozen evaluation protocol")
        key = (r.partition, r.task_id, r.seed)
        if key in indexed:
            raise ValueError(f"duplicate trial receipt: {key}")
        indexed[key] = r
    if len({r.system_sha256 for r in indexed.values()}) > 1:
        raise ValueError("each evaluation arm must contain exactly one system identity")
    return indexed


def assess_rewrite(
    protocol: EvaluationProtocol,
    incumbent: list[TrialReceipt],
    candidate: list[TrialReceipt],
) -> RewriteAssessment:
    """Nominate a rewrite for final audit; development data is not the final test.

    Requires paired selection/development task-seeds and equal resource spend.
    A positive development result permits only nomination for a different,
    sealed final audit. Repeatedly querying development can still overfit it.
    """
    if not _digest(protocol.protocol_sha256) or not _digest(protocol.benchmark_sha256):
        raise ValueError("protocol and benchmark require frozen SHA-256 identities")
    if (type(protocol.per_trial_budget) is not int or protocol.per_trial_budget <= 0
            or type(protocol.minimum_paired_trials_per_partition) is not int
            or protocol.minimum_paired_trials_per_partition <= 0
            or not isinstance(protocol.minimum_development_gain, (int, float))
            or not 0.0 <= protocol.minimum_development_gain <= 1.0
            or type(protocol.maximum_safety_regressions) is not int
            or protocol.maximum_safety_regressions < 0):
        raise ValueError("invalid frozen protocol limits")
    payload = _protocol_payload(protocol.benchmark_sha256, protocol.per_trial_budget,
                                protocol.minimum_paired_trials_per_partition,
                                protocol.minimum_development_gain, protocol.maximum_safety_regressions)
    if protocol.protocol_sha256 != _canonical_sha256(payload):
        raise ValueError("evaluation protocol checksum mismatch")
    base = _index(incumbent, protocol)
    new = _index(candidate, protocol)
    if not base or not new or set(base) != set(new):
        raise ValueError("incumbent/candidate trials must be nonempty and exactly paired")
    if {r.system_sha256 for r in base.values()} == {r.system_sha256 for r in new.values()}:
        raise ValueError("candidate and incumbent have identical system identity")
    tasks_by_partition: dict[str, set[str]] = {"selection": set(), "development": set()}
    for partition, task_id, _ in base:
        tasks_by_partition[partition].add(task_id)
    if tasks_by_partition["selection"] & tasks_by_partition["development"]:
        raise ValueError("selection and development task IDs must be disjoint")
    counts = {p: sum(1 for key in base if key[0] == p) for p in ("selection", "development")}
    if any(counts[p] < protocol.minimum_paired_trials_per_partition for p in counts):
        raise ValueError("insufficient paired trials for preregistered evaluation")

    same_budget = all(base[k].resource_units == new[k].resource_units for k in base)
    if not same_budget:
        raise ValueError("candidate and incumbent must use equal per-trial resource budgets")

    def rate(rows: dict[tuple[str, str, int], TrialReceipt], partition: str, attr: str) -> float:
        subset = [getattr(r, attr) for k, r in rows.items() if k[0] == partition]
        return sum(subset) / len(subset)

    selection_delta = rate(new, "selection", "passed") - rate(base, "selection", "passed")
    development_delta = rate(new, "development", "passed") - rate(base, "development", "passed")
    safety_regressions = sum(1 for k in base if base[k].safe and not new[k].safe)
    eligible = (development_delta >= protocol.minimum_development_gain
                and safety_regressions <= protocol.maximum_safety_regressions)
    reason = "DEVELOPMENT_GAIN_NOMINATE_FOR_SEALED_AUDIT" if eligible else "REJECT_NO_DEVELOPMENT_GAIN_OR_SAFETY_REGRESSION"
    return RewriteAssessment(eligible, reason, selection_delta, development_delta,
                             safety_regressions, counts["development"], same_budget)
