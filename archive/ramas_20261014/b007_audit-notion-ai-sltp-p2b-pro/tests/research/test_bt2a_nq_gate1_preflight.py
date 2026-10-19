from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "tools" / "preflight_bt2a_nq_gate1.py"
SPEC_PATH = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"
MODULE_SPEC = importlib.util.spec_from_file_location("bt2a_nq_gate1_preflight", RUNNER_PATH)
runner = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(runner)


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_gate1_draft_is_valid_but_not_ready():
    value = load_spec()
    runner.validate_spec(value)
    missing = runner.missing_bindings(value)
    assert "bt2a_creation_event_store_manifest_sha256" in missing
    assert "bt2_comparator_config_id" in missing
    assert "macro_calendar_sha256" in missing
    assert "power_design.mde_ticks" in missing
    assert "power_design.icc" in missing
    assert "power_design.effective_sessions_required" in missing


def test_gate1_preflight_has_no_execution_mode_or_outcome_import():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "bt2_gate1_outcomes" not in source
    assert "run_gate1" not in source
    assert "--run" not in source
    assert "--authorization-token" not in source


def test_full_family_and_firewalls_are_immutable_in_draft():
    value = load_spec()
    family = value["outcome_family"]
    assert len({(barrier, horizon) for barrier in family["first_passage_barriers_ticks"] for horizon in family["first_passage_horizons_observations"]}) == 16
    assert family["gc_results_may_reduce_nq_family"] is False
    assert all(value["firewall"][name] is False for name in (
        "GATE1_RUN", "OUTCOMES_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "PNL_ACCESSED",
        "HOLDOUT_TOUCHED", "WINNER_SELECTED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ))
