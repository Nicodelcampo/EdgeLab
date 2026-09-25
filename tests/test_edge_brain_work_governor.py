from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

# Load only this module: importing edgelab.edge_brain runs the package-wide
# initializer and optional research dependencies, unrelated to planner tests.
_PATH = Path(__file__).resolve().parents[1] / "edgelab/edge_brain/work_governor.py"
_SPEC = importlib.util.spec_from_file_location("edge_brain_work_governor_tested", _PATH)
assert _SPEC and _SPEC.loader
work_governor = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = work_governor
_SPEC.loader.exec_module(work_governor)
Candidate, feedback, plan = work_governor.Candidate, work_governor.feedback, work_governor.plan


def candidate(task_id: str, **kwargs) -> Candidate:
    values = dict(kind="test", evidence_ref="issue:documented-blocker", expected_reuse=3,
                  blocker_reduction=2, uncertainty_reduction=2, cost_units=2)
    values.update(kwargs)
    return Candidate(task_id=task_id, **values)


def test_prefers_reusable_high_value_work_and_respects_budget():
    decisions = plan([candidate("reusable", expected_reuse=5), candidate("cheap", expected_reuse=1)],
                     completed_ids=frozenset(), cycle=1, available_units=2)
    by_id = {d.task_id: d for d in decisions}
    assert by_id["reusable"].status == "READY"
    assert by_id["cheap"].status == "PARKED"


def test_research_and_outcome_access_wait_for_human():
    decisions = plan([candidate("research", kind="research"), candidate("pnl", requires_outcomes=True)],
                     completed_ids=frozenset(), cycle=1, available_units=10)
    assert {d.task_id: d.status for d in decisions} == {"pnl": "WAIT_HUMAN", "research": "WAIT_HUMAN"}


def test_missing_provenance_and_stalls_do_not_run():
    decisions = plan([candidate("no-ref", evidence_ref=""), candidate("stalled", failure_count=3)],
                     completed_ids=frozenset(), cycle=5, available_units=10)
    assert {d.task_id: d.status for d in decisions} == {"no-ref": "BLOCKED", "stalled": "PARKED"}


def test_completed_dependencies_unlock_but_unfinished_dependencies_block():
    tasks = [candidate("base"), candidate("next", dependency_ids=("base",))]
    first = plan(tasks, completed_ids=frozenset(), cycle=1, available_units=10, max_new_tasks=2)
    assert {d.task_id: d.status for d in first}["next"] == "BLOCKED"
    second = plan(tasks, completed_ids=frozenset({"base"}), cycle=2, available_units=10)
    assert {d.task_id: d.status for d in second}["next"] == "READY"


def test_spent_cycles_without_learning_trigger_stop_not_more_work():
    result = feedback(verified_reusable_outputs=0, falsified_assumptions=0,
                      resolved_blockers=0, spent_units=10, unattended_cycles=4)
    assert result["recommendation"] == "STOP_AND_DIAGNOSE"
    assert result["yield_per_unit"] == 0
    with pytest.raises(ValueError):
        feedback(verified_reusable_outputs=-1, falsified_assumptions=0,
                 resolved_blockers=0, spent_units=1, unattended_cycles=0)


def test_duplicate_ids_and_invalid_budgets_fail_closed():
    with pytest.raises(ValueError):
        plan([candidate("same"), candidate("same")], completed_ids=frozenset(), cycle=0, available_units=1)
    with pytest.raises(ValueError):
        plan([], completed_ids=frozenset(), cycle=-1, available_units=1)
