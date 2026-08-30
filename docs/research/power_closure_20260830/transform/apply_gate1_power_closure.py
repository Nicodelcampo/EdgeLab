#!/usr/bin/env python3
"""Aplica la enmienda de estimand autorizada y cierra la potencia de BT2A NQ Gate 1.

Todo reemplazo lleva assert (leccion del defecto V2.4).
"""
import json
import math
import hashlib
from pathlib import Path
from statistics import NormalDist

ROOT = Path("/data/EdgeLab-bt2a/EdgeLab-research-bt2a-nq-target-free-selection-v1-20260828")
SPEC = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"
PREFLIGHT = ROOT / "tools" / "preflight_bt2a_nq_gate1.py"

SD = 11.528529
TARGET_POWER = 0.80
ALPHA_FAMILY = 0.05
FAMILY_SIZE = 16
AVAILABLE = 234

EVENT_STORE_MANIFEST_SHA = "b3177b51892298fc75a8bc6ab156d15525473aef52d71e4c717da148501ba544"
BT2_COMPARATOR = "tick_25_IMB30_VOL10"
GC_RESULT_PAYLOAD = "a307a12c441d82877590a20c59aa1079d590de2cdbb6d55180caaec21622ca53"


def required_sessions(sd, mde, alpha, power=TARGET_POWER):
    nd = NormalDist()
    z_crit = nd.inv_cdf(1.0 - alpha / 2.0)
    z_pow = nd.inv_cdf(power)
    return math.ceil(((z_crit + z_pow) * sd / mde) ** 2)


def sha256_file(path):
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def write_json(path, payload):
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text, old, new, label):
    assert text.count(old) == 1, ("ANCHOR NOT UNIQUE", label, text.count(old))
    return text.replace(old, new)


alpha_per_cell = ALPHA_FAMILY / FAMILY_SIZE
MDE = 2.90
req = required_sessions(SD, MDE, alpha_per_cell)
assert req <= AVAILABLE, ("MDE no potenciado", req)

knife = required_sessions(SD, 2.8614, alpha_per_cell)
assert knife > AVAILABLE, ("se esperaba que 2.8614 falle", knife)

# ---------------------------------------------------------------- spec
spec = json.loads(SPEC.read_text(encoding="utf-8"))

pd_block = spec["power_design"]
assert pd_block["mde_ticks"] is None, "power_design ya estaba cerrado"
assert pd_block["effective_sessions_required"] is None

pd_block["estimand"] = "MAGNITUDE_WITHIN_CELL"
pd_block["mde_ticks"] = MDE
pd_block["mde_ticks_knife_edge_rejected"] = 2.8614
pd_block["paired_session_sd_ticks"] = SD
pd_block["paired_session_sd_provenance"] = {
    "source": "BT2_ABSORPTION_GATE1_ALL5_RESULT_2026-08-26 (GC, all 5 contracts)",
    "gc_full_result_payload_sha256": GC_RESULT_PAYLOAD,
    "sd_is_upper_bound_for_nq": True,
    "upper_bound_reasons": [
        "NQ cell barriers 5-30 ticks and horizons 25-250 obs cap variation more tightly than GC tick_cap=2000 / clock_cap_seconds=900",
        "NQ has 652.54 events per session versus 72.39 in GC, reducing the sampling component",
    ],
    "pairing_cancels_shared_session_effect": True,
    "pairing_variance_reduction_pct": 48.06,
    "arm_correlation_rho": 0.5617,
}
pd_block["icc"] = None
pd_block["icc_status"] = "NOT_IDENTIFIED_TIGHTLY_ENOUGH_TO_USE"
pd_block["icc_retired_reason"] = (
    "Within-session pairing cancels the shared session effect, so the session-level SD already "
    "embeds clustering. The GC bootstrap CI95 for ICC was [0.0254, 0.5317], too wide to use, and "
    "the fail-closed upper bound was worse than the previously assumed 0.20."
)
pd_block["alpha_family"] = ALPHA_FAMILY
pd_block["alpha_per_cell"] = alpha_per_cell
pd_block["multiplicity_scope"] = "ALL_16_CELLS_RETAINED"
pd_block["power_multiplicity_basis"] = "BONFERRONI_CONSERVATIVE_FOR_POWER_HOLM_FOR_INFERENCE"
pd_block["effective_sessions_required"] = req
pd_block["effective_sessions_available"] = AVAILABLE
pd_block["session_attrition_margin"] = AVAILABLE - req

spec["estimand_amendment"] = {
    "amendment_id": "bt2a_nq_gate1_estimand_amendment_v1",
    "authorized_by": "Nicolas Buttaro",
    "authorized_at": "2026-08-30T15:32-03:00",
    "authorization_channel": "Notion chat survey response",
    "from_outcome_per_event": "TRICHOTOMOUS_SIGN_PLUS_B_MINUS_B_ZERO",
    "to_outcome_per_event": "MAGNITUDE_OF_EXCURSION_WITHIN_CELL_CAPPED_BY_CELL_BARRIER_AND_HORIZON",
    "unchanged": [
        "first_passage_barriers_ticks",
        "first_passage_horizons_observations",
        "family_size_16",
        "arms_and_comparators",
        "paired_within_cme_session_contrast_K_ABS_minus_N_RAND",
        "equal_session_weight",
        "holm_multiplicity_over_16_cells",
        "holdout_boundary",
    ],
    "rationale": (
        "The trichotomous encoding discards excursion magnitude and inflates the session-level SD to "
        "26.91 ticks, requiring 10443 sessions for MDE 1. The magnitude estimand is the one the GC "
        "sibling instrument already runs, with a measured session-level SD of 11.53 ticks."
    ),
    "tie_and_incomplete_policy_retained": {
        "tie": "ADVERSE",
        "incomplete_trajectory": "EXCLUDED_AT_EVENT_LEVEL",
    },
}

deps = spec["dependencies"]
assert deps["bt2a_creation_event_store_manifest_sha256"] is None
assert deps["bt2_comparator_config_id"] is None
deps["bt2a_creation_event_store_manifest_sha256"] = EVENT_STORE_MANIFEST_SHA
deps["bt2_comparator_config_id"] = BT2_COMPARATOR
deps["binding_notes"] = {
    "bt2a_creation_event_store_manifest_sha256": (
        "Bound to the frozen physical manifest. The 2026-08-30 rebuild reproduced it with only "
        "frozen_commit differing; if the rebuilt store is ever re-uploaded this binding must change."
    ),
    "macro_calendar_file": (
        "NO ARTIFACT EXISTS IN THE REPOSITORY. No design element consumes it: n_rand_matching is "
        "contract, cme_session_id, coarse_phase, availability, local_volatility_bin. Requires a "
        "decision to either supply a hash-bound calendar or drop the dependency by amendment."
    ),
    "still_requires_kaggle": [
        "selected_configuration_file_sha256",
        "private_package_manifest_sha256",
        "effective_input_registry_sha256",
        "bt2_v2_result_file_sha256",
    ],
}

inf = spec["inference"]
assert inf["pre_execution_power_inputs_required"] == ["MDE", "ICC", "EFFECTIVE_SESSION_COUNT", "ARM_DENSITY"]
inf["pre_execution_power_inputs_required"] = [
    "MDE",
    "PAIRED_SESSION_SD",
    "EFFECTIVE_SESSION_COUNT",
    "ARM_DENSITY",
]
inf["power_requires_available_at_least_required"] = True

write_json(SPEC, spec)

# ---------------------------------------------------------------- preflight
src = PREFLIGHT.read_text(encoding="utf-8")

src = replace_once(
    src,
    "import argparse\nimport json\nimport os\nfrom pathlib import Path\nfrom typing import Any\n",
    "import argparse\nimport json\nimport math\nimport os\nfrom pathlib import Path\nfrom statistics import NormalDist\nfrom typing import Any\n",
    "imports",
)

src = replace_once(
    src,
    'DEFAULT_SPEC = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"\nINPUT_ROOT = Path("/kaggle/input")\n',
    'INPUT_ROOT = Path("/kaggle/input")\n'
    'TARGET_POWER_FLOOR = 0.80\n',
    "default_spec_removed",
)

src = replace_once(
    src,
    '    out.add_argument("--spec", type=Path, default=DEFAULT_SPEC)\n',
    '    out.add_argument("--spec", type=Path, required=True)\n',
    "spec_required",
)

OLD_POWER = '''    power = spec["power_design"]
    mde = power.get("mde_ticks")
    icc = power.get("icc")
    sessions = power.get("effective_sessions_required")
    if not isinstance(mde, (int, float)) or mde <= 0:
        missing.append("power_design.mde_ticks")
    if not isinstance(icc, (int, float)) or not 0 <= icc < 1:
        missing.append("power_design.icc")
    if not isinstance(sessions, int) or sessions < int(spec["inference"]["minimum_effective_sessions"]):
        missing.append("power_design.effective_sessions_required")
    return missing
'''

NEW_POWER = '''    power = spec["power_design"]
    floor = int(spec["inference"]["minimum_effective_sessions"])
    mde = power.get("mde_ticks")
    sd = power.get("paired_session_sd_ticks")
    required = power.get("effective_sessions_required")
    available = power.get("effective_sessions_available")
    if not isinstance(mde, (int, float)) or isinstance(mde, bool) or mde <= 0:
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

src = replace_once(src, OLD_POWER, NEW_POWER, "power_block")

HELPER = '''def required_effective_sessions(sd_ticks: float, mde_ticks: float, alpha: float,
                                target_power: float = TARGET_POWER_FLOOR) -> int:
    """Sessions needed for a paired session-level contrast at the given alpha and power.

    Fail-closed: the declared effective_sessions_required must equal this value, so a design
    cannot declare a requirement it did not derive.
    """
    if not 0.0 < alpha < 1.0 or not 0.0 < target_power < 1.0 or sd_ticks <= 0 or mde_ticks <= 0:
        raise RuntimeError("invalid power inputs")
    normal = NormalDist()
    z_crit = normal.inv_cdf(1.0 - alpha / 2.0)
    z_pow = normal.inv_cdf(target_power)
    return math.ceil((((z_crit + z_pow) * sd_ticks) / mde_ticks) ** 2)


def missing_bindings('''

src = replace_once(src, "def missing_bindings(", HELPER, "helper_insert")

PREFLIGHT.write_text(src, encoding="utf-8", newline="\n")

out = {
    "mde_ticks": MDE,
    "mde_knife_edge_rejected": 2.8614,
    "knife_edge_required": knife,
    "alpha_per_cell": alpha_per_cell,
    "paired_session_sd_ticks": SD,
    "effective_sessions_required": req,
    "effective_sessions_available": AVAILABLE,
    "margin": AVAILABLE - req,
    "spec_file_sha256": sha256_file(SPEC),
    "preflight_file_sha256": sha256_file(PREFLIGHT),
}
Path("/data/gate1_power_closure.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
print(json.dumps(out, indent=2, sort_keys=True))
