from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "tools" / "build_bt2a_nq_creation_event_store.py"
SPEC_PATH = ROOT / "specs" / "bt2a_nq_creation_event_store_v1.draft.json"
MODULE_SPEC = importlib.util.spec_from_file_location("bt2a_nq_store", RUNNER_PATH)
runner = importlib.util.module_from_spec(MODULE_SPEC)
assert MODULE_SPEC.loader is not None
MODULE_SPEC.loader.exec_module(runner)


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def test_draft_contract_is_transform_only_and_closed():
    value = load_spec()
    runner.validate_spec(value)
    assert value["status"] == "DRAFT_PREAUTHORIZATION"
    assert value["build"]["mode"] == "TRANSFORM_SELECTED_COORDINATES_ONLY"
    assert value["build"]["raw_tick_decode_allowed"] is False
    assert value["build"]["future_path_decode_allowed"] is False
    assert value["build"]["lifecycle_allowed"] is False
    assert value["authorization"]["execution_authorized"] is False


def test_payload_hash_verification_is_exact():
    value = {"schema_version": "test", "rows": 1}
    value["payload_sha256"] = runner.canonical_sha256(value)
    assert runner._payload_valid(value)
    value["rows"] = 2
    assert not runner._payload_valid(value)


def test_draft_rejects_build_even_with_correct_token():
    with pytest.raises(PermissionError, match="not frozen"):
        runner.require_build_authorization(
            load_spec(), "0" * 40, "AUTHORIZE_BUILD_BT2A_NQ_CREATION_EVENT_STORE_V1"
        )


def test_builder_has_no_raw_tick_or_outcome_imports():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "load_canonical_parquet" not in source
    assert "bt2_gate1_outcomes" not in source
    assert "full_expectancy_surface" not in source
    assert set(runner.REQUIRED_COLUMNS).isdisjoint(runner.FORBIDDEN_COLUMNS)
