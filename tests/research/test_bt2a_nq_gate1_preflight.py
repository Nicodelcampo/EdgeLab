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


def test_gate1_draft_is_valid_and_only_power_freeze_remains():
    value = load_spec()
    runner.validate_spec(value)
    missing = runner.missing_bindings(value)
    # Closed by T2: N_RAND stratum capacity (Kaggle capacity check, Antigravity)
    # Only remaining blocker before freeze: Nico token APPROVE_FREEZE_BT2A_NQ_GATE1_POWER_V1
    assert "power.arm_density.N_RAND_capacity_ok" not in missing
    assert missing == ["power.freeze"]
    # Closed by the 2026-08-30 merge: all hash bindings, comparator, power design.
    for name in (
        "selected_configuration_file_sha256",
        "bt2a_creation_event_store_manifest_sha256",
        "private_package_manifest_sha256",
        "effective_input_registry_sha256",
        "bt2_v2_result_file_sha256",
        "power_design_file_sha256",
        "runner_contract_file_sha256",
        "bt2_comparator_config_id",
        "power_design.mde_ticks",
        "power_design.paired_session_sd_ticks",
        "power_design.effective_sessions_required",
        "power_design.effective_sessions_required_mismatch",
        "power.insufficient_effective_sessions",
        "power_design.contract_invalid",
        "runner_contract.invalid",
    ):
        assert name not in missing, name


def test_gate1_comparator_config_id_is_bound_to_preregistered_v2_winner():
    value = load_spec()
    assert value["dependencies"]["bt2_comparator_config_id"] == "tick_25_IMB30_VOL10"
    rule = json.loads(
        (ROOT / "specs" / "bigtrap2_nq_tickframes_sweep_v2.draft.json").read_text(encoding="utf-8")
    )["comparator_selection_rule"]
    assert value["dependencies"]["bt2_comparator_config_id"] == rule["selected_cfg_id"]


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


def _powered_spec(mde: float, required: int | None = None, available: int = 234) -> dict:
    value = load_spec()
    power = value["power_design"]
    alpha = float(power["alpha_family"]) / int(value["inference"]["holm_family_size"])
    power["mde_ticks"] = mde
    if required is None:
        required = runner.required_effective_sessions(
            float(power["paired_session_sd_ticks"]), mde, alpha, float(power["target_power"])
        )
    power["effective_sessions_required"] = required
    power["effective_sessions_available"] = available
    return value


def test_power_gate_flags_insufficient_sessions_even_when_dependencies_are_unbound():
    """The old gate skipped the power check whenever any dependency was still null."""
    value = _powered_spec(1.0)
    missing = runner.missing_bindings(value)
    assert value["power_design"]["effective_sessions_required"] == 1916
    assert "power.insufficient_effective_sessions" in missing


def test_power_gate_rejects_a_required_session_count_that_was_not_derived():
    value = _powered_spec(2.9, required=42)
    missing = runner.missing_bindings(value)
    assert "power_design.effective_sessions_required_mismatch" in missing


def test_authorized_mde_is_powered_and_the_knife_edge_value_is_not():
    power = load_spec()["power_design"]
    sd = float(power["paired_session_sd_ticks"])
    alpha = float(power["alpha_family"]) / 16
    assert runner.required_effective_sessions(sd, 2.9, alpha, 0.8) == 228
    assert runner.required_effective_sessions(sd, 2.8614, alpha, 0.8) == 235
    assert int(power["effective_sessions_required"]) <= int(power["effective_sessions_available"])


def test_trichotomous_encoding_would_not_have_been_powered():
    alpha = 0.05 / 16
    assert runner.required_effective_sessions(26.91, 1.0, alpha, 0.8) > 10000


def test_spec_argument_has_no_fail_open_default():
    source = RUNNER_PATH.read_text(encoding="utf-8")
    assert "DEFAULT_SPEC" not in source
    assert 'out.add_argument("--spec", type=Path, required=True)' in source


def test_amendment_preserves_family_multiplicity_and_arms():
    value = load_spec()
    amendment = value["estimand_amendment"]
    assert amendment["to_outcome_per_event"].startswith("MAGNITUDE_")
    assert value["outcome_family"]["first_passage_barriers_ticks"] == [5, 9, 18, 30]
    assert value["outcome_family"]["first_passage_horizons_observations"] == [25, 50, 100, 250]
    assert int(value["outcome_family"]["family_size"]) == 16
    assert int(value["inference"]["holm_family_size"]) == 16
    assert value["arms"]["comparators"] == ["K_BT2", "N_RAND", "K_ABS_SHUFFLE"]
    assert value["power_design"]["multiplicity_scope"] == "ALL_16_CELLS_RETAINED"


def test_icc_is_retired_and_not_load_bearing():
    value = load_spec()
    assert value["power_design"]["icc"] is None
    assert "ICC" not in value["inference"]["pre_execution_power_inputs_required"]
    assert "PAIRED_SESSION_SD" in value["inference"]["pre_execution_power_inputs_required"]
    assert runner.missing_bindings(value).count("power_design.icc") == 0


def test_firewalls_remain_closed_after_the_amendment():
    value = load_spec()
    assert all(value["firewall"][name] is False for name in (
        "GATE1_RUN", "OUTCOMES_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "PNL_ACCESSED",
        "HOLDOUT_TOUCHED", "WINNER_SELECTED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ))
    assert value["authorization"]["execution_authorized"] is False
    assert value["authorization"]["active_token"] is None


def test_per_event_outcome_is_declared_as_magnitude():
    """Before the amendment outcome_family declared no per-event outcome at all."""
    family = load_spec()["outcome_family"]
    assert family["per_event_outcome"].startswith("SIGNED_MAGNITUDE_")
    assert family["per_event_outcome_superseded"].startswith("TRICHOTOMOUS_")
    assert family["per_event_outcome_units"] == "TICKS"
    assert family["same_observation_tie"] == "ADVERSE_FIRST"
    assert family["incomplete_path_policy"] == "EXCLUDE_WITH_REASON"


def test_decision_rule_binds_the_amendment_and_the_primary_contrast():
    rule = load_spec()["decision_rule"]
    assert rule["estimand_amendment_ref"] == "bt2a_nq_gate1_estimand_amendment_v1"
    assert rule["primary_contrast"] == "K_ABS_MINUS_N_RAND_PAIRED_WITHIN_CME_SESSION"
    assert rule["secondary_comparators_cannot_trigger_positive_alone"] is True
    assert rule["edge_declaration_allowed"] is False
    assert rule["promotion_allowed"] is False


def test_authorized_mde_is_recorded_and_ratified():
    rec = load_spec()["power_design"]["mde_reconciliation"]
    assert rec["authorized_value_ticks"] == 2.861
    assert rec["authorized_value_required_sessions"] == 235
    assert rec["available_sessions"] == 234
    assert rec["adopted_value_ticks"] == 2.90
    assert rec["adopted_value_ticks"] > rec["authorized_value_ticks"]
    # Ratified by Nico 2026-08-30 (docs/DECISIONES_NICO_2026-08-30.md, D1).
    assert rec["requires_nico_ratification"] is False
    assert rec["ratified_by"] == "Nicolas Buttaro"


def test_macro_calendar_dependency_eliminated_by_amendment():
    """Nico decision D2 (2026-08-30): no design element consumed the macro calendar."""
    value = load_spec()
    deps = value["dependencies"]
    assert "macro_calendar_file" not in deps
    assert "macro_calendar_sha256" not in deps
    missing = runner.missing_bindings(value)
    assert "macro_calendar_file" not in missing
    assert "macro_calendar_sha256" not in missing
