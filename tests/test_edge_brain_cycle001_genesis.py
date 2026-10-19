"""Pin the CYCLE-001 genesis ledger: provenance, integrity and authority gates."""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "artifacts" / "hippocampus" / "cycle001_genesis_ledger.jsonl"
EXPECTED_TIP = "af5d862d388ae4660a95bda59846f23c3e21622990e13d73371f240ddd975693"


def _load(module_name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


for pkg, pkg_path in (
    ("edgelab", ROOT / "edgelab"),
    ("edgelab.edge_brain", ROOT / "edgelab" / "edge_brain"),
):
    if pkg not in sys.modules:
        module = types.ModuleType(pkg)
        module.__path__ = [str(pkg_path)]
        sys.modules[pkg] = module

store_mod = _load("edgelab.edge_brain.hippocampus_store",
                  ROOT / "edgelab" / "edge_brain" / "hippocampus_store.py")


class TestCycle001GenesisLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = store_mod.DurableHippocampus(LEDGER)

    def test_tip_hash_is_pinned(self):
        """Any silent edit to the genesis ledger breaks this test."""
        self.assertEqual(self.store.tip_hash, EXPECTED_TIP)
        self.assertEqual(self.store.verify(), EXPECTED_TIP)

    def test_cycle001_episode_and_records_replay(self):
        rec = self.store.memory.reconstruct_episode("EPISODE-CYCLE-001-MULTIAGENT")
        self.assertFalse(rec["episode"].outcomes_inspected)
        self.assertEqual(len(rec["steps"]), 2)
        self.assertEqual(len(rec["failures"]), 2)
        self.assertEqual(len(rec["lessons"]), 5)

    def test_all_counterexamples_replay_confirmed(self):
        targets = self.store.memory.counterexamples
        self.assertEqual(len(targets.get("KAGGLE-ACCESS-CERTIFICATION-V1", [])), 3)
        self.assertEqual(len(targets.get("KAGGLE-DATASET-VISIBILITY-V1", [])), 1)

    def test_no_lesson_is_promoted_or_evidence_backed(self):
        rec = self.store.memory.reconstruct_episode("EPISODE-CYCLE-001-MULTIAGENT")
        for lesson in rec["lessons"]:
            self.assertEqual(lesson.status, "PROPOSED")
            self.assertEqual(lesson.evidence_record_ids, [])
            self.assertEqual(lesson.confidence, "LOW")


if __name__ == "__main__":
    unittest.main(verbosity=2)
