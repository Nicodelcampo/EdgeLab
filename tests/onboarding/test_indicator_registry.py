from __future__ import annotations
import copy
import unittest
from pathlib import Path
from edgelab.onboarding.registry import EXPECTED_IDS, by_id, load_registry, validate_registry
REPO = Path(__file__).resolve().parents[2]

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = load_registry(REPO / "config/indicator_registry_v1.json")
        self.index = by_id(self.registry)
    def test_complete_and_fail_closed(self):
        result = validate_registry(self.registry)
        self.assertEqual(result.errors, ())
        self.assertEqual(set(self.index), EXPECTED_IDS)
        self.assertEqual(set(self.registry["legacy_core_ids"]), {"gaps2","bigtrap2","hftzones2","voltickspoc2","avolcellpoi2"})
    def test_outcomes_and_holdout_are_blocked(self):
        for entry in self.registry["indicators"]:
            self.assertFalse(entry["outcome_search_enabled"], entry["id"])
        self.assertEqual(self.registry["policy"]["holdout"], "sealed")
    def test_avolcluster_is_only_source_pinned(self):
        entry = self.index["avolclusterpoi"]
        self.assertEqual(entry["stage"], "source_pinned")
        self.assertEqual(entry["source"]["sha256"], "3420519de9b4a1456f812040b62af419b0c323486281424a84aaaab126100c98")
        self.assertIn("ReactionTargetTicks", entry["parameter_contract"]["outcome"])
        self.assertNotIn("ReactionTargetTicks", entry["parameter_contract"]["target_free"])
    def test_diagnostics_are_not_candidate_families(self):
        for ident in ("tickbardiag", "captureeventprobev2"):
            self.assertEqual(self.index[ident]["role"], "diagnostic")
            self.assertEqual(self.index[ident]["stage"], "diagnostic_only")
    def test_outcome_enablement_fails(self):
        broken = copy.deepcopy(self.registry)
        by_id(broken)["avolclusterpoi"]["outcome_search_enabled"] = True
        self.assertTrue(any("outcome search" in e for e in validate_registry(broken).errors))
    def test_parameter_group_overlap_fails(self):
        broken = copy.deepcopy(self.registry)
        by_id(broken)["avolclusterpoi"]["parameter_contract"]["target_free"].append("Opacity")
        self.assertTrue(any("multiple groups" in e for e in validate_registry(broken).errors))
if __name__ == "__main__":
    unittest.main()
