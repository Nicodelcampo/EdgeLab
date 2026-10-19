from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "tools" / "run_bt2a_nq_target_free_selection.py"
SPEC_PATH = ROOT / "specs" / "bt2a_nq_target_free_selection_v1.draft.json"
MODULE_SPEC = importlib.util.spec_from_file_location("bt2a_nq_selection", RUNNER_PATH)
runner = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(runner)


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_draft_is_kaggle_only_target_free_and_closed():
    value = load_spec()
    runner.validate_spec(value)
    assert value["status"] == "DRAFT_PREAUTHORIZATION"
    assert value["execution_platform"]["platform"] == "KAGGLE"
    assert value["execution_platform"]["local_heavy_execution_allowed"] is False
    assert value["execution_authorized"] is False
    assert value["execution_token"] is None
    firewall = value["firewall"]
    assert firewall["TARGET_FREE"] is True
    assert all(firewall[name] is False for name in (
        "LIFECYCLE_ACCESSED", "FIRST_TOUCH_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "RETURNS_ACCESSED",
        "PNL_ACCESSED", "HOLDOUT_ROWS_DECODED", "HOLDOUT_TOUCHED", "EDGE_DECLARED",
    ))


def test_grid_is_deterministic_complete_and_creation_only():
    value = load_spec()
    first = runner.expand_configs(value)
    second = runner.expand_configs(value)
    assert first == second
    assert len(first) >= 90
    assert len({row["config_id"] for row in first}) == len(first)
    assert first[0]["stage"] == "headline"
    assert first[0]["params"] == {**value["baseline"], **value["fixed_parameters"]}
    assert set(first[0]["params"]) == set(runner.DEFAULTS)
    assert not ({"InvalidationMode", "MaxAgeBars", "MaxTouches", "DrawZoneBand"} & set(value["candidate_levels"]))
    assert all(row["params"]["MinHistoryBuckets"] <= row["params"]["AbsorptionLookback"] for row in first)


def test_creation_identity_is_configuration_independent():
    first = runner.creation_event_key("NQ 12-25", "20251001", 1, 123, 456)
    second = runner.creation_event_key("NQ 12-25", "20251001", 1, 123, 456)
    other = runner.creation_event_key("NQ 12-25", "20251001", -1, 123, 456)
    assert first == second
    assert first != other
    assert len(first) == 64


def test_draft_cannot_be_executed_even_with_token():
    with pytest.raises(PermissionError, match="Spec status"):
        runner.require_execution(
            load_spec(), "0" * 40, "AUTHORIZE_RUN_BT2A_NQ_TARGET_FREE_SELECTION_V1"
        )


def test_structural_rank_ignores_density_and_has_deterministic_ties():
    spec = load_spec()
    rows = [
        {"config_id": "dense", "eligible": True, "structural_score": 0.70, "distance_to_gc_anchor": 0.5, "n_events": 100000},
        {"config_id": "stable-b", "eligible": True, "structural_score": 0.90, "distance_to_gc_anchor": 0.1, "n_events": 500},
        {"config_id": "stable-a", "eligible": True, "structural_score": 0.90, "distance_to_gc_anchor": 0.1, "n_events": 400},
    ]
    status, chosen = runner.rank_summaries(rows, spec)
    assert status == "SELECTED_STABLE_NQ_CONFIGURATION"
    assert chosen["config_id"] == "stable-a"
    status, chosen = runner.rank_summaries([{**rows[0], "eligible": False}], spec)
    assert status == "ABSTAIN_NO_STABLE_NQ_CONFIGURATION"
    assert chosen is None


def test_runner_does_not_import_outcome_kernel():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "bt2_gate1_outcomes" not in source
    assert "full_expectancy_surface" not in source
    assert "atlas_excursiones_nulas" not in source
