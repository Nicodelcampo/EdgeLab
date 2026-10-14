# -*- coding: utf-8 -*-
import copy
import json
from pathlib import Path

import pytest

from edgelab.research.avolcluster_nq_zone_store import (
    SPEC_STATUS_DRAFT,
    SPEC_STATUS_FROZEN,
    build_creation_event,
    projected_frozen_payload_sha256,
    validate_spec,
    validate_zone_rows,
)
from edgelab.research.event_store_contract import EventStoreContractError, stamp_identity

ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "specs/avolcluster_nq_zone_event_store_v1.json"


def spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def event(session_id="20260630", block_index=1, score=20.0):
    return build_creation_event(
        spec(),
        contract="NQ 06-26",
        session_id=session_id,
        session_ordinal=221,
        block_index=block_index,
        block_start_bar_index=block_index * 5,
        block_end_bar_index=block_index * 5 + 4,
        created_ts_utc_ns=1_000_000_000 + block_index * 100,
        availability_ts_utc_ns=1_000_000_001 + block_index * 100,
        lower_tick=79_990,
        upper_tick=79_995,
        close_tick=80_000,
        zone_score=score,
        detection_threshold=15.0,
        history_score_count=40,
        history_session_count=12,
        source_data_sha256="a" * 64,
    )


def test_spec_is_target_free_draft_and_binds_selected_configuration():
    s = spec()
    validate_spec(s)
    assert s["status"] in {SPEC_STATUS_DRAFT, SPEC_STATUS_FROZEN}
    assert s["target_free_selection"]["selected_configuration"]["config_id"] == "tick_120_W5_M20_C4_P950"
    assert s["target_free_selection"]["observed_summary"]["off_price_events"] == 5876
    assert s["epistemic_scope"]["future_price_path_accessed_by_this_stage"] is False
    assert s["lifecycle"]["first_touch_implemented"] is False
    assert s["authorization"]["zone_store_build_capability_after_freeze"] is True
    assert s["authorization"]["future_path_capability_after_freeze"] is False
    assert s["implementation_status"]["gate1_outcomes_run"] is False


def test_projected_freeze_hash_is_stable_and_non_circular():
    s = spec()
    a = projected_frozen_payload_sha256(s)
    s["status"] = "FROZEN_ZONE_CREATION_EVENT_STORE"
    s["frozen_spec_payload_sha256"] = a
    s["frozen_commit"] = "f" * 40
    assert projected_frozen_payload_sha256(s) == a
    assert len(a) == 64


def test_creation_event_is_deterministic_and_geometrically_consistent():
    a = event()
    b = event()
    assert a == b
    assert a["event_type"] == "ZONE_CREATED"
    assert a["geometric_side"] == 1
    assert a["distance_ticks"] == 5
    assert a["width_ticks"] == 6
    assert len(a["event_id"]) == len(a["identity_sha256"]) == 64
    _, diag = validate_zone_rows([a], spec())
    assert diag["future_price_path_accessed"] is False


def test_at_price_zone_is_rejected_from_creation_population():
    with pytest.raises(EventStoreContractError, match="not OFF_PRICE"):
        build_creation_event(
            spec(), contract="NQ 06-26", session_id="20260630", session_ordinal=221,
            block_index=1, block_start_bar_index=5, block_end_bar_index=9,
            created_ts_utc_ns=100, availability_ts_utc_ns=101,
            lower_tick=99, upper_tick=101, close_tick=100, zone_score=20.0,
            detection_threshold=15.0, history_score_count=40, history_session_count=12,
            source_data_sha256="a" * 64,
        )


def test_holdout_session_is_rejected_fail_closed():
    with pytest.raises(EventStoreContractError) as exc:
        validate_zone_rows([event(session_id="20260701")], spec())
    assert exc.value.label == "ABSTAIN_HOLDOUT_FIREWALL"


def test_creation_bar_and_availability_are_causally_separated():
    bad = event()
    bad["availability_ts_utc_ns"] = bad["created_ts_utc_ns"]
    bad = stamp_identity(bad, spec()["event_store"]["contract"])
    with pytest.raises(EventStoreContractError, match="strictly after"):
        validate_zone_rows([bad], spec())


def test_outcome_or_first_touch_columns_cannot_enter_creation_store():
    for column in ("first_touch_ts_utc_ns", "mfe_ticks", "pnl"):
        bad = copy.deepcopy(event())
        bad[column] = 0
        with pytest.raises(EventStoreContractError, match="undeclared fields"):
            validate_zone_rows([bad], spec())


def test_real_expected_count_is_a_gate_not_faked_by_unit_fixture():
    with pytest.raises(EventStoreContractError, match="expected 5876"):
        validate_zone_rows([event()], spec(), enforce_expected_counts=True)


def test_input_registry_matches_official_datos_manifiesto():
    """Ensure all 5 NQ input registry parquet files match docs/datos_manifiesto.json exact hashes and byte counts."""
    input_path = ROOT / "specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json"
    manifest_path = ROOT / "docs/datos_manifiesto.json"
    assert input_path.is_file()
    assert manifest_path.is_file()

    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest_files = manifest.get("archivos", {})
    for contract, entry in inputs["contracts"].items():
        pq_name = entry["parquet_file"]
        canonical_key = f"data/nt8/NQ_parquet/{pq_name}"
        assert canonical_key in manifest_files, f"missing {canonical_key} in datos_manifiesto.json"
        man_entry = manifest_files[canonical_key]
        assert entry["parquet_sha256"] == man_entry["sha256"], f"hash mismatch for {contract}"
        assert entry["bytes"] == man_entry["bytes"], f"byte size mismatch for {contract}"


def test_published_gate1a_metadata_and_hashes():
    """Verify published Gate 1A creation metadata, hashes and checkpoint inventory."""
    manifest_path = ROOT / "docs/research/avolcluster_nq_zone_store_manifest.json"
    validation_path = ROOT / "docs/research/avolcluster_nq_zone_store_validation.json"
    inventory_path = ROOT / "docs/research/avolcluster_nq_checkpoints_manifest.json"
    report_path = ROOT / "docs/research/INFORME_FINAL_AVOLCLUSTER_NQ_GATE1A_2026-08-28.md"

    assert manifest_path.is_file()
    assert validation_path.is_file()
    assert inventory_path.is_file()
    assert report_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "COMPLETE_TARGET_FREE_ZONE_CREATION_STORE"
    assert manifest["code_commit"] == "910c4dd75a6e6494f01497b4ff073d5a1e8e9637"
    assert manifest["spec_payload_sha256"] == "c9792d00da4f15311acdd13f965d06d601e0d08ae0e961766338d04e5e9440ba"
    assert manifest["diagnostics"]["rows"] == 5876
    assert manifest["diagnostics"]["contract_sessions_with_events"] == 233
    assert manifest["parquet"]["parquet_physical_sha256"] == "4dad91f6a572bfb5edc714dfb13daa4a0bbee6b96301a4d734466a9da7a06674"
    assert manifest["parquet"]["logical_payload_sha256"] == "7c254009dc4ccd58f4187360a861f76a692945b94c7091766cce6cf3e46f3a77"
    assert manifest["payload_sha256"] == "f87061427d884dac3290c52144bdcf0ab079d4a4b4674237c279072eae51cacc"

    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    assert validation["status"] == "READY_ZONE_CREATION_EVENT_STORE"
    assert validation["transport"]["logical_identity"] == "PASS"
    assert validation["transport"]["parquet_matches_checkpoints_1to1"] is True

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    assert inventory["total_checkpoints"] == 234
    assert inventory["total_events"] == 5876
    assert inventory["sessions_with_events"] == 233
    assert len(inventory["checkpoints"]) == 234


