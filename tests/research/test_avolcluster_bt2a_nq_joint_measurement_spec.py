# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "specs" / "avolcluster_bt2a_nq_joint_measurement_v1.draft.json"


def load_spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_joint_design_is_draft_and_execution_closed():
    value = load_spec()
    assert value["status"] == "DRAFT_DESIGN_ONLY_PREAUTHORIZATION"
    assert value["authority"]["primary_instrument"] == "NQ"
    assert value["authority"]["nt8_oracle_parity_claimed"] is False
    assert value["epistemic_scope"]["execution_authorized"] is False
    assert value["epistemic_scope"]["outcome_execution_token"] is None
    assert value["epistemic_scope"]["future_path_capability"] is False
    assert value["instrument_policy"]["same_instrument_required_for_primary_confluence"] is True


def test_primary_avol_and_full_bt2a_families_are_registered():
    value = load_spec()
    assert value["avol"]["primary_configuration"]["config_id"] == "tick_120_W5_M20_C4_P950"
    assert value["avol"]["target_free_observed_summary"]["off_price"] == 5876
    assert value["avol"]["robustness_can_select_winner"] is False
    bt2a = value["bt2a"]
    assert bt2a["first_passage_barriers_ticks"] == [5, 9, 18, 30]
    assert bt2a["first_passage_horizons_observations"] == [25, 50, 100, 250]
    assert bt2a["family_size"] == 16
    assert bt2a["evaluate_full_family"] is True
    assert bt2a["gc_cells_may_reduce_nq_family"] is False


def test_relation_taxonomy_and_temporal_windows_are_complete_and_unique():
    value = load_spec()
    relations = value["relation_catalog"]
    assert len(relations) == 30
    assert len({row["id"] for row in relations}) == len(relations)
    assert {row["axis"] for row in relations} >= {
        "temporal", "sequence", "spatial", "trajectory_state", "direction", "arm", "configuration", "control"
    }
    windows = value["temporal_windows_seconds_relative_to_first_touch"]
    assert len(windows) == 6
    assert len({row["id"] for row in windows}) == len(windows)
    assert min(row["start"] for row in windows) == -120
    assert max(row["end"] for row in windows) == 120


def test_clock_and_l2_context_are_registered_without_becoming_filters():
    value = load_spec()
    clock = value["time_of_day"]
    assert clock["timezone"] == "America/Chicago"
    assert len(clock["coarse_primary"]) == 4
    assert len(clock["fine_descriptive"]) == 8
    assert clock["fine_windows_confirmatory"] is False
    l2 = value["l2_context"]
    assert l2["status"] == "NOT_READY"
    assert l2["join"] == "ASOF_BACKWARD_ONLY"
    assert l2["first_role"] == "STRATIFIER_NOT_SIGNAL_FILTER"
    assert l2["minimum_effective_sessions_per_stratum"] == 40
    assert l2["hmm_final_allowed"] is False
    assert l2["ctx3_allowed"] is False


def test_hierarchical_multiplicity_and_nulls_are_explicit():
    value = load_spec()
    assert [row["id"] for row in value["hierarchical_gates"]] == [
        "GATE_A", "GATE_B", "GATE_C", "GATE_D", "GATE_E"
    ]
    assert value["multiplicity_policy"]["full_cartesian_product_forbidden"] is True
    assert value["multiplicity_policy"]["holm_within_each_preregistered_family"] is True
    assert value["multiplicity_policy"]["incomplete_family_policy"] == "ABSTAIN"
    assert "PLACEBO_LEADS_BEFORE_ZONE_AVAILABILITY" in value["null_models"]
    assert value["inference"]["cluster_unit"] == "CME_SESSION"
    assert value["inference"]["events_assumed_iid"] is False


def test_joint_design_firewall_remains_fully_closed():
    firewall = load_spec()["firewall"]
    assert firewall == {
        "AVOL_ZONE_STORE_REAL_BUILD": "NOT_RUN",
        "AVOL_FIRST_TOUCH_IMPLEMENTED": False,
        "BT2A_NQ_EVENT_STORE_READY": False,
        "L2_CONTEXT_READY": False,
        "CAUSAL_JOIN_BUILT": False,
        "FUTURE_PRICE_PATH_ACCESSED": False,
        "MFE_MAE_ACCESSED": False,
        "FIRST_PASSAGE_ACCESSED": False,
        "PNL_ACCESSED": False,
        "HOLDOUT_TOUCHED": False,
        "WINNER_SELECTED": False,
        "EDGE_DECLARED": False,
        "PROMOTION_ELIGIBLE": False,
    }
