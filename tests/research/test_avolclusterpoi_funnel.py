from copy import deepcopy

from edgelab.research.avolclusterpoi_funnel import (
    FunnelContractError, build_profile, build_question_cards,
    canonical_sha256, validate_trace,
)

SOURCE = "eafbc0380253e029acc969e07c17ebb7912ef7ec"
PARAMS = {"window_bars": 10, "median_multiplier": 2.0, "max_gap_ticks": 1,
          "min_cluster_ticks": 2, "time_bucket_minutes": 30,
          "lookback_sessions": 20, "detection_percentile": 98.0,
          "min_samples_per_bucket": 20, "max_age_bars": 0,
          "one_cluster_per_block": True}


def block(session, block_index, decision, *, zone_ids=None, selected=None,
          threshold=None, best=0.0, history=0, close=100):
    return {"session_end_ns": session, "session_index": session // 1000,
            "block_index": block_index, "end_bar": block_index * 10 + 9,
            "block_end_ns": session + block_index + 1, "bucket": block_index % 2,
            "n_cells": 4, "cells": {98: 1.0, 99: 10.0, 100: 10.0, 101: 1.0},
            "median": 10.0, "hot_threshold": 20.0, "best_score": best,
            "threshold": threshold, "history_samples": history,
            "n_history_scores": history, "decision": decision,
            "clusters": [] if selected is None else [selected],
            "selected_cluster": selected,
            "abstain": "warmup" if decision == "ABSTAIN_NO_HISTORY" else None,
            "close_tick": close, "zone_ids": zone_ids or []}


def fixture():
    selected = {"lower_tick": 99, "upper_tick": 100, "score": 20.0,
                "count": 2, "ticks": [99, 100]}
    blocks = [block(1000, 0, "ABSTAIN_NO_HISTORY", history=0),
              block(1000, 1, "CREATE", zone_ids=["1"], selected=selected,
                    threshold=15.0, best=20.0, history=20, close=103),
              block(2000, 0, "CREATE", selected=selected,
                    threshold=15.0, best=20.0, history=20, close=100),
              block(2000, 1, "ABSTAIN_BELOW_THRESHOLD", threshold=25.0,
                    best=20.0, history=20)]
    zones = [{"id": "1", "top": 100.5, "bottom": 98.5,
              "created_ms": 1, "kind": "avol_cluster_off_price"}]
    summary = {"scope": "target_free_preholdout", "repo_commit": SOURCE,
               "n_blocks": 4, "n_zones": 1,
               "decision_counts": {"ABSTAIN_BELOW_THRESHOLD": 1,
                                   "ABSTAIN_NO_HISTORY": 1, "CREATE": 2}}
    return summary, blocks, zones


def test_validate_decomposes_create_candidates():
    summary, blocks, zones = fixture()
    result = validate_trace(summary, blocks, zones, SOURCE, 4, 1)
    assert result["n_create_candidates"] == 2
    assert result["n_zones_off_price"] == 1
    assert result["n_at_price_candidates"] == 1
    assert result["outcomes_accessed"] is False


def test_profile_and_questions_are_target_free_and_non_automatic():
    summary, blocks, zones = fixture()
    profile = build_profile(summary, blocks, zones, PARAMS)
    assert profile["n_sessions"] == 2
    assert profile["rates_per_100_blocks"]["create_candidates"] == 50.0
    assert profile["rates_per_100_blocks"]["zones_off_price"] == 25.0
    assert profile["distributions"]["selected_width_ticks"]["p50"] == 2.0
    cards = build_question_cards(profile)
    assert cards["selection_made"] is False
    assert cards["automatic_transition"] is False
    assert all(card["auto_execute"] is False for card in cards["cards"])
    assert all(card["outcomes_allowed"] is False for card in cards["cards"])


def test_rejects_forbidden_outcome_field():
    summary, blocks, zones = fixture(); blocks[0]["pnl"] = 1.0
    try: validate_trace(summary, blocks, zones)
    except FunnelContractError as exc: assert "campo prohibido" in str(exc)
    else: raise AssertionError("debio rechazar pnl")


def test_rejects_duplicate_block_identity_and_dangling_zone():
    summary, blocks, zones = fixture(); duplicate = deepcopy(blocks[0])
    duplicate["block_end_ns"] = 9999; blocks.append(duplicate)
    summary["n_blocks"] = 5; summary["decision_counts"]["ABSTAIN_NO_HISTORY"] = 2
    try: validate_trace(summary, blocks, zones)
    except FunnelContractError as exc: assert "identidad de bloque duplicada" in str(exc)
    else: raise AssertionError("debio rechazar identidad duplicada")
    summary, blocks, zones = fixture(); zones.append({"id": "2"}); summary["n_zones"] = 2
    try: validate_trace(summary, blocks, zones)
    except FunnelContractError as exc: assert "zone_ids" in str(exc)
    else: raise AssertionError("debio rechazar zona sin referencia")


def test_canonical_hash_is_order_independent_for_objects():
    assert canonical_sha256({"a": 1, "b": 2}) == canonical_sha256({"b": 2, "a": 1})
