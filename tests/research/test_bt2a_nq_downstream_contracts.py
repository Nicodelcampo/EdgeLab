from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "specs" / "bt2a_nq_creation_event_store_v1.draft.json"
GATE1 = ROOT / "specs" / "bt2a_nq_gate1_v1.draft.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_event_store_is_transform_only_and_closed():
    value = load(STORE)
    assert value["status"] == "DRAFT_PREAUTHORIZATION"
    assert value["execution_platform"] == "KAGGLE_ONLY"
    assert value["build"]["mode"] == "TRANSFORM_SELECTED_COORDINATES_ONLY"
    assert value["build"]["raw_tick_decode_allowed"] is False
    assert value["build"]["future_path_decode_allowed"] is False
    assert value["build"]["lifecycle_allowed"] is False
    assert value["source_selection"]["selected_config_id"] is None
    assert value["authorization"]["execution_authorized"] is False
    assert all(value["firewall"][name] is False for name in (
        "EVENT_STORE_READY", "LIFECYCLE_ACCESSED", "FIRST_TOUCH_ACCESSED",
        "FUTURE_PRICE_PATH_ACCESSED", "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED",
        "PNL_ACCESSED", "HOLDOUT_TOUCHED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ))


def test_gate1_registers_full_family_and_remains_closed():
    value = load(GATE1)
    # Gate 1 spec frozen 2026-08-31 (Nico token APPROVE_FREEZE_BT2A_NQ_GATE1_V1,
    # verbatim in chat); this assert tracked the pre-freeze DRAFT status until then.
    assert value["status"] == "FROZEN_PREFLIGHT_READY"
    assert value["execution_platform"] == "KAGGLE_ONLY"
    family = value["outcome_family"]
    assert family["first_passage_barriers_ticks"] == [5, 9, 18, 30]
    assert family["first_passage_horizons_observations"] == [25, 50, 100, 250]
    assert family["family_size"] == 16
    assert family["evaluate_full_family"] is True
    assert family["gc_results_may_reduce_nq_family"] is False
    assert value["arms"]["comparators"] == ["K_BT2", "N_RAND", "K_ABS_SHUFFLE"]
    assert value["inference"]["cluster_unit"] == "CME_SESSION"
    assert value["inference"]["minimum_event_count_alone_is_power_proof"] is False
    assert value["authorization"]["execution_authorized"] is False
    assert all(value["firewall"][name] is False for name in (
        "GATE1_RUN", "OUTCOMES_ACCESSED", "FUTURE_PRICE_PATH_ACCESSED",
        "FIRST_PASSAGE_ACCESSED", "MFE_MAE_ACCESSED", "PNL_ACCESSED",
        "HOLDOUT_TOUCHED", "WINNER_SELECTED", "EDGE_DECLARED", "PROMOTION_ELIGIBLE",
    ))
