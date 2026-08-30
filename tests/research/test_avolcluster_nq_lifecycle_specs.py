# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
from pathlib import Path

from edgelab.research.avolcluster_nq_lifecycle_contracts import (
    git_blob_sha1,
    validate_episode_spec,
    validate_lifecycle_spec,
)
from tools.preflight_avolcluster_nq_lifecycle_gate import EXPECTED_BLOBS, audit_readiness

ROOT = Path(__file__).resolve().parents[2]


class TestAvolLifecycleSpecs(unittest.TestCase):
    def load(self, rel: str) -> dict:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))

    def test_normative_base_blobs_match_reported_branch(self):
        for rel, expected in EXPECTED_BLOBS.items():
            self.assertEqual(git_blob_sha1(ROOT / rel), expected)

    def test_lifecycle_draft_is_explicitly_unresolved_and_closed(self):
        spec = self.load("specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json")
        missing = validate_lifecycle_spec(spec)
        self.assertEqual(missing, spec["decision_paths"])
        self.assertFalse(spec["authorization"]["execution_authorized"])
        self.assertIsNone(spec["authorization"]["execution_token"])
        self.assertFalse(spec["authorization"]["future_path_capability"])
        self.assertFalse(spec["firewall"]["FIRST_TOUCH_BUILD_ALLOWED"])

    def test_episode_draft_preserves_normative_anchor_without_inventing_collapse(self):
        spec = self.load("specs/avolcluster_nq_episode_collapse_v1.draft.json")
        missing = validate_episode_spec(spec)
        self.assertEqual(missing, spec["decision_paths"])
        self.assertEqual(spec["anchor"]["primary_rule"], "FIRST_ELIGIBLE_EVENT_WINS")
        self.assertIsNone(spec["spatial"]["link_rule"])
        self.assertIsNone(spec["temporal"]["window_value"])
        self.assertFalse(spec["firewall"]["EPISODE_BUILD_ALLOWED"])
        self.assertTrue(spec["authorization"]["creation_only_episode_builder_present"])
        self.assertFalse(spec["authorization"]["creation_only_episode_build_authorized"])
        self.assertFalse(spec["authorization"]["standalone_io_runner_present"])

    def test_preflight_is_not_ready_for_the_real_reason(self):
        result = audit_readiness(ROOT)
        self.assertEqual(result["status"], "NOT_READY_DECISIONS_REQUIRED")
        self.assertFalse(result["ready_for_execution"])
        self.assertEqual(len(result["lifecycle_missing_decisions"]), 27)
        self.assertEqual(len(result["episode_missing_decisions"]), 20)
        self.assertEqual(len(result["missing_decisions"]), 47)
        self.assertTrue(all(row["pass"] for row in result["source_bindings"].values()))
        self.assertTrue(result["creation_manifest"]["checks"]["payload_self_consistent"])
        self.assertFalse(result["FIRST_TOUCH_ACCESSED"])
        self.assertFalse(result["FUTURE_PRICE_PATH_ACCESSED"])

    def test_package_has_no_outcome_runner_or_raw_decoder(self):
        self.assertFalse((ROOT / "tools/run_avolcluster_nq_lifecycle.py").exists())
        self.assertFalse((ROOT / "tools/build_avolcluster_nq_first_touch_store.py").exists())
        source = (ROOT / "edgelab/research/avolcluster_nq_lifecycle_contracts.py").read_text("utf-8")
        for token in ("import pandas", "import pyarrow", "import numpy", "read_parquet(", "load_canonical_parquet("):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
