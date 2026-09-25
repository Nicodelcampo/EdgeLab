from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path
import sys

import pytest

_PATH = Path(__file__).resolve().parents[1] / "edgelab/edge_brain/recursive_eval.py"
_SPEC = importlib.util.spec_from_file_location("edge_brain_recursive_eval_tested", _PATH)
assert _SPEC and _SPEC.loader
recursive_eval = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = recursive_eval
_SPEC.loader.exec_module(recursive_eval)
create_protocol = recursive_eval.create_protocol
create_trial_receipt = recursive_eval.create_trial_receipt
assess_rewrite = recursive_eval.assess_rewrite

B = "b" * 64


def receipt(system: str, partition: str, task: str, seed: int, passed: bool,
            *, safe=True, cost=10, protocol_sha=None, benchmark=B):
    protocol_sha = protocol_sha or PROTOCOL.protocol_sha256
    return create_trial_receipt(system_sha256=system, benchmark_sha256=benchmark,
                                protocol_sha256=protocol_sha, partition=partition,
                                task_id=task, seed=seed, passed=passed, safe=safe,
                                resource_units=cost)


def protocol(**kwargs):
    values = dict(benchmark_sha256=B, per_trial_budget=10,
                  minimum_paired_trials_per_partition=2, minimum_development_gain=0.25,
                  maximum_safety_regressions=0)
    values.update(kwargs)
    return create_protocol(**values)


PROTOCOL = protocol()


def pairs(system: str, passed_by_task: dict[str, bool], partition: str):
    return [receipt(system, partition, task, seed, passed_by_task[task])
            for task in passed_by_task for seed in (1, 2)]


def test_nominates_only_preregistered_development_gain_for_final_audit():
    base = pairs("1" * 64, {"s1": False, "s2": True}, "selection") + pairs("1" * 64, {"d1": False, "d2": False}, "development")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"d1": True, "d2": True}, "development")
    result = assess_rewrite(PROTOCOL, base, new)
    assert result.eligible_for_final_audit
    assert result.development_delta == 1.0
    assert result.same_budget
    assert result.reason == "DEVELOPMENT_GAIN_NOMINATE_FOR_SEALED_AUDIT"


def test_selection_improvement_without_development_improvement_is_rejected():
    base = pairs("1" * 64, {"s1": False, "s2": True}, "selection") + pairs("1" * 64, {"d1": True, "d2": True}, "development")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"d1": True, "d2": False}, "development")
    result = assess_rewrite(PROTOCOL, base, new)
    assert not result.eligible_for_final_audit
    assert result.reason == "REJECT_NO_DEVELOPMENT_GAIN_OR_SAFETY_REGRESSION"


def test_rejects_budget_drift_and_safety_regression():
    base = pairs("1" * 64, {"s1": True, "s2": True}, "selection") + pairs("1" * 64, {"d1": False, "d2": False}, "development")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + [receipt("2" * 64, "development", "d1", 1, True, safe=False), receipt("2" * 64, "development", "d1", 2, True), receipt("2" * 64, "development", "d2", 1, True), receipt("2" * 64, "development", "d2", 2, True)]
    assert not assess_rewrite(PROTOCOL, base, new).eligible_for_final_audit
    too_expensive = [receipt("2" * 64, "selection", t, s, True, cost=9) if part == "selection" else receipt("2" * 64, part, t, s, True)
                     for part in ("selection", "development") for t in (("s1", "s2") if part == "selection" else ("d1", "d2")) for s in (1, 2)]
    with pytest.raises(ValueError, match="equal per-trial"):
        assess_rewrite(PROTOCOL, base, too_expensive)


def test_rejects_mismatched_or_insufficient_or_overlapping_eval_sets():
    base = pairs("1" * 64, {"s1": True, "s2": True}, "selection") + pairs("1" * 64, {"d1": True, "d2": True}, "development")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"d1": True, "d2": True}, "development")
    with pytest.raises(ValueError, match="exactly paired"):
        assess_rewrite(PROTOCOL, base, new[:-1])
    with pytest.raises(ValueError, match="disjoint"):
        overlap_base = pairs("1" * 64, {"same1": True, "same2": True}, "selection") + pairs("1" * 64, {"same1": True, "same2": True}, "development")
        overlap_candidate = pairs("2" * 64, {"same1": True, "same2": True}, "selection") + pairs("2" * 64, {"same1": True, "same2": True}, "development")
        assess_rewrite(PROTOCOL, overlap_base, overlap_candidate)
    with pytest.raises(ValueError, match="insufficient"):
        few_base = pairs("1" * 64, {"s1": True}, "selection") + pairs("1" * 64, {"d1": True}, "development")
        few_candidate = pairs("2" * 64, {"s1": True}, "selection") + pairs("2" * 64, {"d1": True}, "development")
        assess_rewrite(PROTOCOL, few_base, few_candidate)


def test_detects_receipt_or_protocol_tampering_and_mixed_candidate_versions():
    base = pairs("1" * 64, {"s1": True, "s2": True}, "selection") + pairs("1" * 64, {"d1": True, "d2": True}, "development")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"d1": True, "d2": True}, "development")
    tampered = [dataclasses.replace(new[0], safe=False), *new[1:]]
    with pytest.raises(ValueError, match="checksum mismatch"):
        assess_rewrite(PROTOCOL, base, tampered)
    changed_protocol = dataclasses.replace(PROTOCOL, minimum_development_gain=0.0)
    with pytest.raises(ValueError, match="protocol checksum mismatch"):
        assess_rewrite(changed_protocol, base, new)
    mixed = [*new[:-1], receipt("3" * 64, "development", "d2", 2, True)]
    with pytest.raises(ValueError, match="one system identity"):
        assess_rewrite(PROTOCOL, base, mixed)
