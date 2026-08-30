#!/usr/bin/env python3
"""Completa la enmienda en outcome_family y decision_rule, y reconcilia el MDE autorizado."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path("/data/EdgeLab-bt2a/EdgeLab-research-bt2a-nq-target-free-selection-v1-20260828")
SPEC = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"
TEST = ROOT / "tests" / "research" / "test_bt2a_nq_gate1_preflight.py"

AMENDMENT_ID = "bt2a_nq_gate1_estimand_amendment_v1"
MAGNITUDE = "SIGNED_MAGNITUDE_OF_EXCURSION_TICKS_CAPPED_BY_CELL_BARRIER_AND_HORIZON"
TRICHOTOMOUS = "TRICHOTOMOUS_SIGN_PLUS_B_MINUS_B_ZERO"


def write_json(path, payload):
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


spec = json.loads(SPEC.read_text(encoding="utf-8"))

fam = spec["outcome_family"]
assert "per_event_outcome" not in fam, "outcome_family ya enmendado"
assert fam["same_observation_tie"] == "ADVERSE_FIRST"
assert fam["incomplete_path_policy"] == "EXCLUDE_WITH_REASON"
assert fam["first_passage_barriers_ticks"] == [5, 9, 18, 30]
assert fam["first_passage_horizons_observations"] == [25, 50, 100, 250]
assert int(fam["family_size"]) == 16

fam["per_event_outcome"] = MAGNITUDE
fam["per_event_outcome_superseded"] = TRICHOTOMOUS
fam["per_event_outcome_amendment_ref"] = AMENDMENT_ID
fam["per_event_outcome_units"] = "TICKS"
fam["per_event_outcome_sign_convention"] = "POSITIVE_TOWARD_BT2A_SIGNAL_DIRECTION"

rule = spec["decision_rule"]
assert rule["edge_declaration_allowed"] is False
assert rule["full_family_required"] is True
assert rule["positive_requires_effect_interval_and_holm"] is True
assert "estimand_amendment_ref" not in rule
rule["estimand_amendment_ref"] = AMENDMENT_ID
rule["primary_contrast"] = "K_ABS_MINUS_N_RAND_PAIRED_WITHIN_CME_SESSION"
rule["secondary_comparators_cannot_trigger_positive_alone"] = True

# Reconciliacion del MDE: Nico autorizo 2.861, que es el MDE@234 exacto y cae sobre
# el borde del redondeo (235 requeridas > 234 disponibles). Se adopta 2.90.
power = spec["power_design"]
assert power["mde_ticks"] == 2.90
assert int(power["effective_sessions_required"]) == 228
power["mde_reconciliation"] = {
    "authorized_value_ticks": 2.861,
    "authorized_source": "docs/research/DECISION_NICO_ESTIMAND_MAGNITUDE_2026-08-30.md (commit 74860a5)",
    "authorized_value_required_sessions": 235,
    "available_sessions": 234,
    "problem": (
        "2.861 is the exact MDE@234, so ceil() of the required-session formula returns 235, "
        "one more than the 234 available. The authorized value is not implementable as written."
    ),
    "adopted_value_ticks": 2.90,
    "adopted_required_sessions": 228,
    "adopted_margin_sessions": 6,
    "why_conservative": (
        "A larger MDE is a weaker claim, so adopting 2.90 cannot inflate sensitivity. It stays "
        "below 3.360, the lower bound of the GC CI95, which is the condition that matters for "
        "being powered against an effect of the size the sibling instrument measures."
    ),
    "requires_nico_ratification": True,
}

write_json(SPEC, spec)

# ---------------------------------------------------------------- test extra
test_src = TEST.read_text(encoding="utf-8")
assert "test_per_event_outcome_is_declared_as_magnitude" not in test_src

EXTRA = '''

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


def test_authorized_mde_is_recorded_as_not_implementable():
    rec = load_spec()["power_design"]["mde_reconciliation"]
    assert rec["authorized_value_ticks"] == 2.861
    assert rec["authorized_value_required_sessions"] == 235
    assert rec["available_sessions"] == 234
    assert rec["adopted_value_ticks"] == 2.90
    assert rec["adopted_value_ticks"] > rec["authorized_value_ticks"]
    assert rec["requires_nico_ratification"] is True
'''

TEST.write_text(test_src.rstrip("\n") + "\n" + EXTRA, encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- repackage
OUT = Path("/data/BT2A_NQ_Gate1_power_closure_20260830")
shutil.copy2(SPEC, OUT / "specs/bt2a_nq_gate1_v1.draft.json")
shutil.copy2(TEST, OUT / "tests/research/test_bt2a_nq_gate1_preflight.py")
shutil.copy2(Path("/data/finish_amendment.py"), OUT / "transform/finish_amendment.py")

lines = []
for path in sorted(OUT.rglob("*")):
    if path.is_file() and path.name != "MANIFEST.sha256":
        lines.append(sha256_file(path) + "  " + str(path.relative_to(OUT)))
(OUT / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

zip_path = Path("/data/BT2A_NQ_Gate1_power_closure_20260830.zip")
if zip_path.exists():
    zip_path.unlink()
subprocess.run(["zip", "-r", "-q", str(zip_path), OUT.name], cwd=str(OUT.parent), check=True)

print("spec_sha256", sha256_file(SPEC))
print("test_sha256", sha256_file(TEST))
print("zip_sha256", hashlib.sha256(zip_path.read_bytes()).hexdigest())
print("zip_bytes", zip_path.stat().st_size)
print((OUT / "MANIFEST.sha256").read_text())
