#!/usr/bin/env python3
"""Arregla el gating del chequeo de potencia y actualiza/agrega tests. Todo reemplazo con assert."""
import hashlib
from pathlib import Path

ROOT = Path("/data/EdgeLab-bt2a/EdgeLab-research-bt2a-nq-target-free-selection-v1-20260828")
PREFLIGHT = ROOT / "tools" / "preflight_bt2a_nq_gate1.py"
TEST = ROOT / "tests" / "research" / "test_bt2a_nq_gate1_preflight.py"


def replace_once(text, old, new, label):
    assert text.count(old) == 1, ("ANCHOR NOT UNIQUE", label, text.count(old))
    return text.replace(old, new)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------- 1. desacoplar potencia de los deps
src = PREFLIGHT.read_text(encoding="utf-8")

OLD = '''    if not isinstance(mde, (int, float)) or isinstance(mde, bool) or mde <= 0:
        missing.append("power_design.mde_ticks")
    if not isinstance(sd, (int, float)) or isinstance(sd, bool) or sd <= 0:
        missing.append("power_design.paired_session_sd_ticks")
    if not isinstance(required, int) or isinstance(required, bool) or required < floor:
        missing.append("power_design.effective_sessions_required")
    if not isinstance(available, int) or isinstance(available, bool) or available < floor:
        missing.append("power_design.effective_sessions_available")
    if not missing:
        alpha = float(power["alpha_family"]) / int(spec["inference"]["holm_family_size"])
        recomputed = required_effective_sessions(float(sd), float(mde), alpha,
                                                 float(power.get("target_power", TARGET_POWER_FLOOR)))
        if recomputed != int(required):
            missing.append("power_design.effective_sessions_required_mismatch")
        elif int(available) < int(required):
            missing.append("power.insufficient_effective_sessions")
    return missing
'''

NEW = '''    power_missing: list[str] = []
    if not isinstance(mde, (int, float)) or isinstance(mde, bool) or mde <= 0:
        power_missing.append("power_design.mde_ticks")
    if not isinstance(sd, (int, float)) or isinstance(sd, bool) or sd <= 0:
        power_missing.append("power_design.paired_session_sd_ticks")
    if not isinstance(required, int) or isinstance(required, bool) or required < floor:
        power_missing.append("power_design.effective_sessions_required")
    if not isinstance(available, int) or isinstance(available, bool) or available < floor:
        power_missing.append("power_design.effective_sessions_available")
    if not power_missing:
        alpha = float(power["alpha_family"]) / int(spec["inference"]["holm_family_size"])
        recomputed = required_effective_sessions(
            float(sd), float(mde), alpha, float(power.get("target_power", TARGET_POWER_FLOOR))
        )
        if recomputed != int(required):
            power_missing.append("power_design.effective_sessions_required_mismatch")
        elif int(available) < int(required):
            power_missing.append("power.insufficient_effective_sessions")
    missing.extend(power_missing)
    return missing
'''

src = replace_once(src, OLD, NEW, "power_ungated")
PREFLIGHT.write_text(src, encoding="utf-8", newline="\n")

# ------------------------------------------------- 2. actualizar el test existente
test_src = TEST.read_text(encoding="utf-8")

OLD_ASSERTS = '''    assert "bt2a_creation_event_store_manifest_sha256" in missing
    assert "bt2_comparator_config_id" in missing
    assert "macro_calendar_sha256" in missing
    assert "power_design.mde_ticks" in missing
    assert "power_design.icc" in missing
    assert "power_design.effective_sessions_required" in missing
'''

NEW_ASSERTS = '''    assert "macro_calendar_sha256" in missing
    assert "macro_calendar_file" in missing
    assert "bt2_v2_result_file_sha256" in missing
    assert "selected_configuration_file_sha256" in missing
    # Closed by the estimand amendment authorized 2026-08-30 and the GC variance transfer.
    assert "power_design.mde_ticks" not in missing
    assert "power_design.paired_session_sd_ticks" not in missing
    assert "power_design.effective_sessions_required" not in missing
    assert "power_design.effective_sessions_required_mismatch" not in missing
    assert "power.insufficient_effective_sessions" not in missing
    assert "bt2a_creation_event_store_manifest_sha256" not in missing
    assert "bt2_comparator_config_id" not in missing
'''

test_src = replace_once(test_src, OLD_ASSERTS, NEW_ASSERTS, "test_asserts")

EXTRA = '''

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
    assert "macro_calendar_sha256" in missing


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
'''

assert "test_power_gate_flags_insufficient_sessions" not in test_src
test_src = test_src.rstrip("\n") + "\n" + EXTRA
TEST.write_text(test_src, encoding="utf-8", newline="\n")

print("preflight_sha256", sha256_file(PREFLIGHT))
print("test_sha256", sha256_file(TEST))
