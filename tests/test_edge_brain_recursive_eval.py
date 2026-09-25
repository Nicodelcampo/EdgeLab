from __future__ import annotations

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
EvaluationProtocol = recursive_eval.EvaluationProtocol
TrialReceipt = recursive_eval.TrialReceipt
assess_rewrite = recursive_eval.assess_rewrite

H = "a" * 64
B = "b" * 64
P = "c" * 64


def receipt(system: str, partition: str, task: str, seed: int, passed: bool,
            *, safe=True, cost=10, protocol=P, benchmark=B, digest=H):
    return TrialReceipt(system, benchmark, protocol, partition, task, seed,
                        passed, safe, cost, digest)


def protocol(**kwargs):
    values = dict(protocol_sha256=P, benchmark_sha256=B, per_trial_budget=10,
                  minimum_paired_trials_per_partition=2, minimum_holdout_gain=0.25,
                  maximum_safety_regressions=0)
    values.update(kwargs)
    return EvaluationProtocol(**values)


def pairs(system: str, passed_by_task: dict[str, bool], partition: str):
    return [receipt(system, partition, task, seed, passed_by_task[task])
            for task in passed_by_task for seed in (1, 2)]


def test_accepts_only_preregistered_holdout_gain_with_matched_budget():
    base = pairs("1" * 64, {"s1": False, "s2": True}, "selection") + pairs("1" * 64, {"h1": False, "h2": False}, "holdout")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"h1": True, "h2": True}, "holdout")
    result = assess_rewrite(protocol(), base, new)
    assert result.accepted
    assert result.holdout_delta == 1.0
    assert result.same_budget


def test_selection_improvement_without_holdout_improvement_is_rejected():
    base = pairs("1" * 64, {"s1": False, "s2": True}, "selection") + pairs("1" * 64, {"h1": True, "h2": True}, "holdout")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + pairs("2" * 64, {"h1": True, "h2": False}, "holdout")
    result = assess_rewrite(protocol(), base, new)
    assert not result.accepted
    assert result.reason == "REJECT_NO_HOLDOUT_GAIN_OR_SAFETY_REGRESSION"


def test_rejects_budget_drift_and_safety_regression():
    base = pairs("1" * 64, {"s1": True, "s2": True}, "selection") + pairs("1" * 64, {"h1": False, "h2": False}, "holdout")
    new = pairs("2" * 64, {"s1": True, "s2": True}, "selection") + [receipt("2" * 64, "holdout", "h1", 1, True, safe=False), receipt("2" * 64, "holdout", "h1", 2, True), receipt("2" * 64, "holdout", "h2", 1, True), receipt("2" * 64, "holdout", "h2", 2, True)]
    assert not assess_rewrite(protocol(), base, new).accepted
    too_expensive = [receipt("2" * 64, "selection", t, s, True, cost=9) if part == "selection" else receipt("2" * 64, part, t, s, True)
                     for part in ("selection", "holdout") for t in (("s1", "s2") if part == "selection" else ("h1", "h2")) for s in (1, 2)]
    with pytest.raises(ValueError, match="equal per-trial"):
        assess_rewrite(protocol(), base, too_expensive)


def test_rejects_mismatched_or_insufficient_or_overlapping_eval_sets():
    base = pairs("1" * 64, {"s1": True, "s2": True}, "selection") + pairs("1" * 64, {"h1": True, "h2": True}, "holdout")
    with pytest.raises(ValueError, match="exactly paired"):
        assess_rewrite(protocol(), base, base[:-1])
    with pytest.raises(ValueError, match="disjoint"):
        overlap = pairs("1" * 64, {"same1": True, "same2": True}, "selection") + pairs("1" * 64, {"same1": True, "same2": True}, "holdout")
        assess_rewrite(protocol(), overlap, overlap)
    with pytest.raises(ValueError, match="insufficient"):
        few = pairs("1" * 64, {"s1": True}, "selection") + pairs("1" * 64, {"h1": True}, "holdout")
        assess_rewrite(protocol(), few, few)
