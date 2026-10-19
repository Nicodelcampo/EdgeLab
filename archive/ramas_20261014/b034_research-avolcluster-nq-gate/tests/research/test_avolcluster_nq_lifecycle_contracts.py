# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from edgelab.research.avolcluster_nq_lifecycle_contracts import (
    EPISODE_FROZEN,
    LIFECYCLE_EVENT_SCHEMA,
    LIFECYCLE_FROZEN,
    LifecycleContractError,
    classify_touch_observation,
    collapse_creation_episodes,
    dotted_set,
    policy_payload_sha256,
    validate_lifecycle_rows,
)
from edgelab.research.event_store_contract import canonical_sha256, stamp_identity

ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def resolve(spec: dict, values: dict[str, object], frozen_status: str) -> dict:
    out = copy.deepcopy(spec)
    self_evidence = {
        "decision_id": "SYNTHETIC_TEST_ONLY_NOT_RESEARCH_AUTHORITY",
        "authority": "UNIT_TEST_FIXTURE",
        "decided_at": "2026-08-30T00:00:00Z",
        "source_reference": "tests/research/synthetic_fixture_only",
    }
    if set(values) != set(out["decision_paths"]):
        raise AssertionError("fixture must resolve every decision path")
    for path, value in values.items():
        dotted_set(out, path, value)
        out["decision_evidence"][path] = dict(self_evidence)
    out["unresolved_decisions"] = []
    out["status"] = frozen_status
    out["authorization"]["freeze_authorized"] = True
    out["authorization"]["freeze_token"] = "SYNTHETIC_TEST_FREEZE_ONLY"
    out["frozen_at_utc"] = "2026-08-30T00:00:00Z"
    out["frozen_commit"] = "0" * 40
    out["frozen_policy_payload_sha256"] = policy_payload_sha256(out)
    return out


LIFECYCLE_VALUES = {
    "clock.observation_source": "CANONICAL_TRADE_TICKS",
    "clock.observation_clock_unit": "TRADE_TICK",
    "clock.age_origin": "AVAILABILITY_TS",
    "touch.price_field": "trade_price_tick",
    "touch.interval_boundary_policy": "INCLUSIVE_BOTH",
    "touch.contact_definition": "TRADE_TICK_INTERSECTS_ZONE",
    "touch.penetration_definition": "ZERO_AT_FIRST_ENTRY",
    "touch.intrabar_ordering_policy": "RAW_SOURCE_ROW_ORDER_REQUIRED",
    "touch.same_timestamp_tie_policy": "SOURCE_ROW_ORDER",
    "touch.source_row_identity_field": "source_row",
    "touch.missing_ticks_policy": "ABSTAIN_SESSION",
    "expiration.max_age_value": 1000,
    "expiration.max_age_unit": "TRADE_TICKS",
    "expiration.expiration_boundary_policy": "EXCLUSIVE",
    "expiration.session_carry_policy": "SAME_SESSION_ONLY",
    "invalidation.rule": "NONE",
    "invalidation.penetration_ticks": 0,
    "precedence.touch_vs_invalidation": "SOURCE_ORDER",
    "precedence.expiration_vs_touch": "SOURCE_ORDER",
    "reentries.reentry_definition": "EXIT_THEN_REENTER_INCLUSIVE_ZONE",
    "reentries.second_touch_definition": "SECOND_DISTINCT_ENTRY_AFTER_EXIT",
    "reentries.primary_inclusion_policy": "EXCLUDE_FROM_PRIMARY",
    "censoring.end_of_sample_policy": "ADMINISTRATIVE_CENSORING",
    "censoring.roll_boundary_policy": "CENSOR_AT_CONTRACT_END",
    "raw_data.source_registry_path": "specs/synthetic_only.json",
    "raw_data.source_registry_sha256": "a" * 64,
    "raw_data.kaggle_dataset_slug": "synthetic/test-only",
}

EPISODE_VALUES = {
    "spatial.link_rule": "ANY_INCLUSIVE_OVERLAP",
    "spatial.minimum_overlap_ticks": 1,
    "spatial.minimum_overlap_fraction_of_smaller_zone": 0.0,
    "spatial.maximum_adjacency_gap_ticks": 0,
    "temporal.anchor_field": "availability_ts_utc_ns",
    "temporal.window_value": 60,
    "temporal.window_unit": "SECONDS",
    "temporal.interval_boundary_policy": "INCLUSIVE",
    "grouping.partition_keys": ["instrument", "contract", "session_id", "config_id"],
    "grouping.transitivity_policy": "TRANSITIVE_CONNECTED_COMPONENTS",
    "grouping.algorithm": "CONNECTED_COMPONENTS",
    "grouping.cross_session_policy": "NEVER",
    "grouping.cross_contract_policy": "NEVER",
    "anchor.eligibility_definition": "ALL_PRIMARY_CONFIG_CREATION_EVENTS",
    "anchor.tie_break_policy": "ANCHOR_TS_THEN_ZONE_EVENT_ID",
    "anchor.anchor_replacement_policy": "NEVER",
    "lifecycle_relation.collapse_timing": "BEFORE_FIRST_TOUCH_AND_OUTCOMES",
    "lifecycle_relation.shared_touch_policy": "UNRESOLVED_UNTIL_LIFECYCLE_FREEZE",
    "multiconfig.policy": "PRIMARY_CONFIG_ONLY",
    "null_controls.episode_collapse_policy": "SAME_FROZEN_POLICY_AS_REAL_ZONES",
}


def creation(zone_id: str, ts: int, lo: int, hi: int, *, session: str = "20260630") -> dict:
    return {
        "event_id": zone_id,
        "identity_sha256": canonical_sha256({"zone": zone_id}),
        "event_type": "ZONE_CREATED",
        "instrument": "NQ",
        "contract": "NQ 06-26",
        "session_id": session,
        "config_id": "tick_120_W5_M20_C4_P950",
        "session_ordinal": 221,
        "created_ts_utc_ns": ts,
        "availability_ts_utc_ns": ts + 1,
        "lower_tick": lo,
        "upper_tick": hi,
        "width_ticks": hi - lo + 1,
    }


class TestLifecyclePrimitives(unittest.TestCase):
    def setUp(self):
        self.spec = resolve(load("specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json"), LIFECYCLE_VALUES, LIFECYCLE_FROZEN)
        self.zone = creation("zone-a", 100, 100, 104)

    def test_current_draft_cannot_classify_even_one_observation(self):
        with self.assertRaises(LifecycleContractError):
            classify_touch_observation(self.zone, {"ts_utc_ns": 101, "trade_price_tick": 100}, load("specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json"))

    def test_single_observation_classifier_respects_availability_and_edges(self):
        with self.assertRaisesRegex(LifecycleContractError, "pre-availability"):
            classify_touch_observation(self.zone, {"ts_utc_ns": 100, "trade_price_tick": 100}, self.spec)
        self.assertEqual(classify_touch_observation(self.zone, {"ts_utc_ns": 101, "trade_price_tick": 100}, self.spec), "LOWER_EDGE")
        self.assertEqual(classify_touch_observation(self.zone, {"ts_utc_ns": 102, "trade_price_tick": 104}, self.spec), "UPPER_EDGE")
        self.assertEqual(classify_touch_observation(self.zone, {"ts_utc_ns": 103, "trade_price_tick": 102}, self.spec), "INTERIOR")
        self.assertIsNone(classify_touch_observation(self.zone, {"ts_utc_ns": 104, "trade_price_tick": 99}, self.spec))

    def test_lifecycle_row_is_bound_and_honestly_marks_future_path(self):
        row = {
            "schema_version": LIFECYCLE_EVENT_SCHEMA,
            "lifecycle_event_id": canonical_sha256({"zone": "zone-a", "kind": "first-touch"}),
            "identity_sha256": "",
            "zone_event_id": "zone-a",
            "zone_identity_sha256": self.zone["identity_sha256"],
            "instrument": "NQ", "contract": "NQ 06-26", "session_id": "20260630",
            "config_id": "tick_120_W5_M20_C4_P950", "session_ordinal": 221,
            "created_ts_utc_ns": 100, "availability_ts_utc_ns": 101,
            "lower_tick": 100, "upper_tick": 104, "width_ticks": 5,
            "lifecycle_status": "FIRST_TOUCH", "first_touch_observed": True,
            "first_touch_ts_utc_ns": 105, "first_touch_tick": 100, "first_touch_source_row": 9,
            "first_touch_age_observations": 4, "first_touch_age_ns": 4,
            "contact_class": "LOWER_EDGE", "penetration_ticks": 0,
            "expired_without_touch": False, "expiration_ts_utc_ns": None,
            "invalidation_observed": False, "invalidation_ts_utc_ns": None,
            "censoring_reason": None, "source_tick_data_sha256": "b" * 64,
            "policy_payload_sha256": policy_payload_sha256(self.spec),
            "future_price_path_accessed": True, "pnl_accessed": False, "holdout_touched": False,
        }
        stamped = stamp_identity(row, self.spec["lifecycle_row_contract"])
        self.assertEqual(validate_lifecycle_rows([stamped], {"zone-a": self.zone}, self.spec), [stamped])
        dishonest = dict(stamped)
        dishonest["future_price_path_accessed"] = False
        dishonest = stamp_identity(dishonest, self.spec["lifecycle_row_contract"])
        with self.assertRaisesRegex(LifecycleContractError, "honestly attest"):
            validate_lifecycle_rows([dishonest], {"zone-a": self.zone}, self.spec)
        contaminated = dict(self.zone)
        contaminated["mfe_ticks"] = 1
        with self.assertRaisesRegex(LifecycleContractError, "outcome fields"):
            validate_lifecycle_rows([stamped], {"zone-a": contaminated}, self.spec)


class TestEpisodeCollapsePrimitive(unittest.TestCase):
    def setUp(self):
        self.spec = resolve(load("specs/avolcluster_nq_episode_collapse_v1.draft.json"), EPISODE_VALUES, EPISODE_FROZEN)
        second = 1_000_000_000
        self.rows = [
            creation("zone-b", 20 * second, 103, 108),
            creation("zone-a", 10 * second, 100, 105),
            creation("zone-c", 30 * second, 200, 205),
        ]

    def test_current_draft_cannot_collapse(self):
        with self.assertRaises(LifecycleContractError):
            collapse_creation_episodes(self.rows, load("specs/avolcluster_nq_episode_collapse_v1.draft.json"))

    def test_creation_only_collapse_is_deterministic_and_one_anchor_per_episode(self):
        first = collapse_creation_episodes(self.rows, self.spec)
        second = collapse_creation_episodes(list(reversed(self.rows)), self.spec)
        self.assertEqual(first, second)
        episodes = {}
        for row in first:
            episodes.setdefault(row["episode_id"], []).append(row)
            self.assertFalse(row["future_price_path_accessed"])
        self.assertEqual(len(episodes), 2)
        pair = next(rows for rows in episodes.values() if len(rows) == 2)
        self.assertEqual({row["zone_event_id"] for row in pair}, {"zone-a", "zone-b"})
        anchors = [row for row in pair if row["is_primary_anchor"]]
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]["zone_event_id"], "zone-a")
        self.assertEqual(anchors[0]["member_rank"], 0)

    def test_outcome_contaminated_source_is_rejected(self):
        contaminated = dict(self.rows[0])
        contaminated["first_touch_ts_utc_ns"] = contaminated["availability_ts_utc_ns"]
        with self.assertRaisesRegex(LifecycleContractError, "outcome fields"):
            collapse_creation_episodes([contaminated], self.spec)

    def test_holdout_source_is_rejected(self):
        with self.assertRaises(LifecycleContractError) as ctx:
            collapse_creation_episodes([creation("holdout", 10, 100, 101, session="20260701")], self.spec)
        self.assertEqual(ctx.exception.label, "ABSTAIN_HOLDOUT_FIREWALL")


if __name__ == "__main__":
    unittest.main()
