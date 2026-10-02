# -*- coding: utf-8 -*-
"""Embudo target-free para aVolClusterPOI.

EF0 consume un trace inmutable ya calculado y produce un perfil estructural y
preguntas para EF1. No lee precio posterior, outcomes, retornos ni P&L. Ninguna
pregunta dispara automaticamente la etapa siguiente.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict

SCHEMA_VERSION = "avolclusterpoi_ef0_v1"
ALLOWED_DECISIONS = {
    "ABSTAIN_FEW_CELLS", "ABSTAIN_NO_CLUSTER", "ABSTAIN_NO_HISTORY",
    "ABSTAIN_BELOW_THRESHOLD", "CREATE",
}
FORBIDDEN_FIELDS = {
    "outcome", "outcomes", "return", "returns", "pnl", "profit", "loss",
    "mfe", "mae", "target_hit", "stop_hit", "forward_price", "future_price",
}
REQUIRED_BLOCK_FIELDS = {
    "session_end_ns", "session_index", "block_index", "block_end_ns", "bucket",
    "n_cells", "cells", "median", "hot_threshold", "best_score", "threshold",
    "history_samples", "n_history_scores", "decision", "clusters",
    "selected_cluster", "close_tick", "zone_ids",
}


class FunnelContractError(RuntimeError):
    """El bundle viola el contrato target-free o su identidad."""


def canonical_sha256(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _assert_no_forbidden_fields(value, path="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_FIELDS:
                raise FunnelContractError("campo prohibido target-free: {}.{}".format(path, key))
            _assert_no_forbidden_fields(child, "{}.{}".format(path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_forbidden_fields(child, "{}[{}]".format(path, index))


def _nearest_quantile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    index = max(0, min(len(values) - 1, int(math.ceil(q * len(values))) - 1))
    return values[index]


def distribution(values):
    values = [float(v) for v in values if v is not None]
    if not values:
        return {"n": 0, "min": None, "p10": None, "p25": None, "p50": None,
                "p75": None, "p90": None, "max": None, "mean": None}
    return {
        "n": len(values), "min": min(values),
        "p10": _nearest_quantile(values, 0.10),
        "p25": _nearest_quantile(values, 0.25),
        "p50": _nearest_quantile(values, 0.50),
        "p75": _nearest_quantile(values, 0.75),
        "p90": _nearest_quantile(values, 0.90),
        "max": max(values), "mean": sum(values) / len(values),
    }


def concentration(counts):
    counts = [int(v) for v in counts if int(v) >= 0]
    total = sum(counts)
    if not counts or total == 0:
        return {"n_groups": len(counts), "total": total, "hhi": None,
                "top_10pct_share": None, "coefficient_of_variation": None}
    shares = [v / total for v in counts]
    mean = total / len(counts)
    variance = sum((v - mean) ** 2 for v in counts) / len(counts)
    top_n = max(1, int(math.ceil(0.10 * len(counts))))
    return {
        "n_groups": len(counts), "total": total,
        "hhi": sum(s * s for s in shares),
        "top_10pct_share": sum(sorted(counts, reverse=True)[:top_n]) / total,
        "coefficient_of_variation": math.sqrt(variance) / mean if mean else None,
    }


def _decision_counts(blocks):
    return dict(sorted(Counter(str(b["decision"]) for b in blocks).items()))


def validate_trace(summary, blocks, zones, expected_source_commit=None,
                   expected_blocks=None, expected_zones=None):
    if not isinstance(summary, dict) or not isinstance(blocks, list) or not isinstance(zones, list):
        raise FunnelContractError("summary=dict, blocks=list y zones=list son obligatorios")
    _assert_no_forbidden_fields(summary, "summary")
    _assert_no_forbidden_fields(blocks, "blocks")
    _assert_no_forbidden_fields(zones, "zones")
    if summary.get("scope") != "target_free_preholdout":
        raise FunnelContractError("scope debe ser target_free_preholdout")
    source_commit = summary.get("repo_commit")
    if expected_source_commit and source_commit != expected_source_commit:
        raise FunnelContractError("source commit {} != {}".format(source_commit, expected_source_commit))
    if int(summary.get("n_blocks", -1)) != len(blocks):
        raise FunnelContractError("summary.n_blocks no coincide con all_blocks")
    if int(summary.get("n_zones", -1)) != len(zones):
        raise FunnelContractError("summary.n_zones no coincide con zones")
    if expected_blocks is not None and len(blocks) != int(expected_blocks):
        raise FunnelContractError("n_blocks {} != esperado {}".format(len(blocks), expected_blocks))
    if expected_zones is not None and len(zones) != int(expected_zones):
        raise FunnelContractError("n_zones {} != esperado {}".format(len(zones), expected_zones))

    observed_decisions = _decision_counts(blocks)
    expected_decisions = {str(k): int(v) for k, v in (summary.get("decision_counts") or {}).items()}
    if observed_decisions != dict(sorted(expected_decisions.items())):
        raise FunnelContractError("decision_counts no coincide con all_blocks")

    block_keys, block_times, referenced_zone_ids = set(), set(), []
    create_candidates = at_price_candidates = 0
    for index, block in enumerate(blocks):
        missing = REQUIRED_BLOCK_FIELDS - set(block)
        if missing:
            raise FunnelContractError("block {} sin campos {}".format(index, sorted(missing)))
        decision = str(block["decision"])
        if decision not in ALLOWED_DECISIONS:
            raise FunnelContractError("decision desconocida en block {}: {}".format(index, decision))
        key = (int(block["session_end_ns"]), int(block["block_index"]))
        if key in block_keys:
            raise FunnelContractError("identidad de bloque duplicada: {}".format(key))
        block_keys.add(key)
        block_time = int(block["block_end_ns"])
        if block_time in block_times:
            raise FunnelContractError("block_end_ns duplicado: {}".format(block_time))
        block_times.add(block_time)
        if int(block["history_samples"]) != int(block["n_history_scores"]):
            raise FunnelContractError("history_samples inconsistente en block {}".format(index))
        zone_ids = [str(z) for z in block.get("zone_ids", [])]
        referenced_zone_ids.extend(zone_ids)
        selected = block.get("selected_cluster")
        if decision == "CREATE":
            create_candidates += 1
            if selected is None:
                raise FunnelContractError("CREATE sin selected_cluster en block {}".format(index))
            if len(zone_ids) > 1:
                raise FunnelContractError("one_cluster_per_block violado en block {}".format(index))
            if not zone_ids:
                at_price_candidates += 1
        else:
            if selected is not None:
                raise FunnelContractError("ABSTAIN con selected_cluster en block {}".format(index))
            if zone_ids:
                raise FunnelContractError("ABSTAIN con zone_ids en block {}".format(index))

    zone_ids = [str(z.get("id")) for z in zones]
    if len(zone_ids) != len(set(zone_ids)):
        raise FunnelContractError("zone ids duplicados")
    if len(referenced_zone_ids) != len(set(referenced_zone_ids)):
        raise FunnelContractError("zone id referenciado mas de una vez")
    if set(referenced_zone_ids) != set(zone_ids):
        raise FunnelContractError("zone_ids del trace no coinciden con zones.json")
    if create_candidates - at_price_candidates != len(zones):
        raise FunnelContractError("CREATE no descompone en OFF_PRICE + AT_PRICE")

    return {
        "schema_version": SCHEMA_VERSION, "status": "PASS",
        "scope": summary["scope"], "source_commit": source_commit,
        "n_blocks": len(blocks), "n_zones_off_price": len(zones),
        "n_create_candidates": create_candidates,
        "n_at_price_candidates": at_price_candidates,
        "decision_counts": observed_decisions,
        "n_sessions": len({int(b["session_end_ns"]) for b in blocks}),
        "n_buckets": len({int(b["bucket"]) for b in blocks}),
        "block_identity_sha256": canonical_sha256(sorted(block_keys)),
        "outcomes_accessed": False,
    }


def _session_rows(blocks):
    grouped = defaultdict(list)
    for block in blocks:
        grouped[int(block["session_end_ns"])].append(block)
    return grouped


def build_profile(summary, blocks, zones, params):
    integrity = validate_trace(summary, blocks, zones)
    sessions = _session_rows(blocks)
    decisions = integrity["decision_counts"]
    create_blocks = [b for b in blocks if b["decision"] == "CREATE"]
    emitted_blocks = [b for b in create_blocks if b["zone_ids"]]
    at_price_blocks = [b for b in create_blocks if not b["zone_ids"]]
    selected = [b["selected_cluster"] for b in create_blocks]
    widths = [int(c["upper_tick"]) - int(c["lower_tick"]) + 1 for c in selected]
    score_ratios = [float(b["best_score"]) / float(b["threshold"])
                    for b in blocks if b.get("threshold") not in (None, 0)
                    and b.get("best_score") is not None]
    create_ratios = [float(b["best_score"]) / float(b["threshold"])
                     for b in create_blocks if b.get("threshold") not in (None, 0)]
    distances = []
    for block in emitted_blocks:
        cluster = block["selected_cluster"]
        close = int(block["close_tick"])
        lower, upper = int(cluster["lower_tick"]), int(cluster["upper_tick"])
        distances.append(close - upper if close > upper else lower - close)

    session_table = []
    for session_end, rows in sorted(sessions.items()):
        n_create = sum(r["decision"] == "CREATE" for r in rows)
        n_zones = sum(bool(r["zone_ids"]) for r in rows)
        session_table.append({
            "session_end_ns": session_end,
            "session_index": min(int(r["session_index"]) for r in rows),
            "n_blocks": len(rows), "n_create_candidates": n_create,
            "n_zones_off_price": n_zones,
            "n_at_price_candidates": n_create - n_zones,
            "n_no_history": sum(r["decision"] == "ABSTAIN_NO_HISTORY" for r in rows),
            "create_candidates_per_100_blocks": 100.0 * n_create / len(rows),
            "zones_per_100_blocks": 100.0 * n_zones / len(rows),
        })

    bucket_groups = defaultdict(list)
    for block in blocks:
        bucket_groups[int(block["bucket"])].append(block)
    bucket_table = []
    for bucket, rows in sorted(bucket_groups.items()):
        dc = Counter(str(r["decision"]) for r in rows)
        bucket_table.append({
            "bucket": bucket, "n_blocks": len(rows),
            "n_create_candidates": dc.get("CREATE", 0),
            "n_zones_off_price": sum(bool(r["zone_ids"]) for r in rows),
            "n_no_history": dc.get("ABSTAIN_NO_HISTORY", 0),
            "create_candidates_per_100_blocks": 100.0 * dc.get("CREATE", 0) / len(rows),
            "no_history_per_100_blocks": 100.0 * dc.get("ABSTAIN_NO_HISTORY", 0) / len(rows),
        })

    event_fingerprint = sorted([
        [int(b["block_end_ns"]), int(b["selected_cluster"]["lower_tick"]),
         int(b["selected_cluster"]["upper_tick"])] for b in emitted_blocks
    ])
    return {
        "schema_version": SCHEMA_VERSION, "stage": "EF0_B_STRUCTURAL_PROFILE",
        "epistemic_status": "PROVISIONAL_UNPARITIED_FOR_FORMAL_SELECTION",
        "scope": "target_free_preholdout", "source_commit": summary.get("repo_commit"),
        "config": params,
        "config_id": canonical_sha256({"source_commit": summary.get("repo_commit"), "params": params}),
        "population_id": "NQ_06-26_120tick_preholdout_complete_blocks_v1",
        "n_universe": len(blocks), "n_available": len(blocks),
        "n_processed": len(blocks), "n_eligible": len(blocks),
        "n_sessions": len(session_table),
        "n_sessions_with_create_candidate": sum(r["n_create_candidates"] > 0 for r in session_table),
        "n_sessions_with_off_price_zone": sum(r["n_zones_off_price"] > 0 for r in session_table),
        "decision_counts": decisions,
        "rates_per_100_blocks": {
            "create_candidates": 100.0 * len(create_blocks) / len(blocks),
            "zones_off_price": 100.0 * len(emitted_blocks) / len(blocks),
            "at_price_candidates": 100.0 * len(at_price_blocks) / len(blocks),
            "abstain_no_history": 100.0 * decisions.get("ABSTAIN_NO_HISTORY", 0) / len(blocks),
            "abstain_no_cluster": 100.0 * decisions.get("ABSTAIN_NO_CLUSTER", 0) / len(blocks),
            "abstain_below_threshold": 100.0 * decisions.get("ABSTAIN_BELOW_THRESHOLD", 0) / len(blocks),
        },
        "distributions": {
            "blocks_per_session": distribution(r["n_blocks"] for r in session_table),
            "create_candidates_per_session": distribution(r["n_create_candidates"] for r in session_table),
            "zones_off_price_per_session": distribution(r["n_zones_off_price"] for r in session_table),
            "history_samples": distribution(b["history_samples"] for b in blocks),
            "n_cells": distribution(b["n_cells"] for b in blocks),
            "n_candidate_clusters": distribution(len(b["clusters"]) for b in blocks),
            "selected_width_ticks": distribution(widths),
            "off_price_distance_ticks": distribution(distances),
            "score_over_threshold_all_ready": distribution(score_ratios),
            "score_over_threshold_create": distribution(create_ratios),
        },
        "concentration": {
            "create_candidates_by_session": concentration(r["n_create_candidates"] for r in session_table),
            "zones_off_price_by_session": concentration(r["n_zones_off_price"] for r in session_table),
        },
        "session_table": session_table, "bucket_table": bucket_table,
        "event_fingerprint_sha256": canonical_sha256(event_fingerprint),
        "lineage": {
            "eligibility_rule": "all complete session-anchored blocks in source trace",
            "bar_spec": "tick:120", "indicator": "aVolClusterPOI",
            "outcomes_accessed": False, "next_stage_executed": False,
        },
    }


def build_question_cards(profile):
    rates, dist, conc = (profile["rates_per_100_blocks"], profile["distributions"],
                         profile["concentration"])
    cards = [
        {"question_id": "Q-HISTORY-STATE", "family": "history_and_bucket_readiness",
         "observed": {"abstain_no_history_per_100_blocks": rates["abstain_no_history"],
                      "history_samples": dist["history_samples"],
                      "bucket_table": profile["bucket_table"]},
         "suggested_next_measurements": [
             "history depth and threshold reconstruction by bucket/session",
             "sensitivity to time_bucket_minutes, lookback_sessions and min_samples_per_bucket"]},
        {"question_id": "Q-THRESHOLD-PRESSURE", "family": "threshold_selectivity",
         "observed": {"below_threshold_per_100_blocks": rates["abstain_below_threshold"],
                      "score_over_threshold_all_ready": dist["score_over_threshold_all_ready"],
                      "score_over_threshold_create": dist["score_over_threshold_create"]},
         "suggested_next_measurements": [
             "one-axis sensitivity around detection_percentile",
             "population turnover and fingerprint stability, not winner ranking"]},
        {"question_id": "Q-GEOMETRY", "family": "cluster_geometry",
         "observed": {"selected_width_ticks": dist["selected_width_ticks"],
                      "candidate_clusters_per_block": dist["n_candidate_clusters"],
                      "off_price_distance_ticks": dist["off_price_distance_ticks"]},
         "suggested_next_measurements": [
             "one-axis sensitivity for median_multiplier, max_gap_ticks and min_cluster_ticks",
             "event fingerprint overlap between neighboring configurations"]},
        {"question_id": "Q-ATPRICE-OFFPRICE", "family": "candidate_materialization",
         "observed": {"create_candidates_per_100_blocks": rates["create_candidates"],
                      "zones_off_price_per_100_blocks": rates["zones_off_price"],
                      "at_price_candidates_per_100_blocks": rates["at_price_candidates"]},
         "suggested_next_measurements": [
             "separate AT_PRICE candidates from emitted OFF_PRICE zones in every later denominator",
             "measure whether configuration changes alter classification or only cluster detection"]},
        {"question_id": "Q-SESSION-STABILITY", "family": "coverage_and_concentration",
         "observed": {"n_sessions": profile["n_sessions"],
                      "create_concentration": conc["create_candidates_by_session"],
                      "zone_concentration": conc["zones_off_price_by_session"],
                      "blocks_per_session": dist["blocks_per_session"]},
         "suggested_next_measurements": [
             "session-level variability and regime coverage",
             "minimum effective session count before any outcome design"]},
    ]
    for card in cards:
        card.update({"status": "REVIEW_REQUIRED_NOT_A_GATE", "auto_execute": False,
                     "outcomes_allowed": False, "requires_parent_manifest_hash": True})
    return {
        "schema_version": "avolclusterpoi_ef0_question_cards_v1",
        "parent_config_id": profile["config_id"],
        "stage_completed": "EF0_B_STRUCTURAL_PROFILE",
        "next_stage": "EF1_PLAN_REQUIRED", "selection_made": False,
        "automatic_transition": False, "cards": cards, "outcomes_accessed": False,
    }
