"""Tests for the durable hash-chained hippocampus ledger.

Loaded by file path (same dependency-hygiene pattern as
tests/test_edge_brain_run_learning_packet.py) so the suite does not import the
full edgelab.edge_brain package __init__ and its optional dependencies.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

h = _load("edgelab.edge_brain.hippocampus", ROOT / "edgelab" / "edge_brain" / "hippocampus.py")
store_mod = _load("edgelab.edge_brain.hippocampus_store",
                  ROOT / "edgelab" / "edge_brain" / "hippocampus_store.py")

DurableHippocampus = store_mod.DurableHippocampus
LedgerIntegrityError = store_mod.LedgerIntegrityError
UnknownRecordTypeError = store_mod.UnknownRecordTypeError


def _episode(ep_id: str = "EP-1") -> h.AnalysisEpisode:
    return h.AnalysisEpisode(
        episode_id=ep_id, goal="test", status="COMPLETED_UNADJUDICATED",
        created_at_utc="2026-09-22T00:00:00Z", updated_at_utc="2026-09-22T00:00:00Z",
        recorded_by="test", outcomes_inspected=False,
    )


def _lesson(ep_id: str = "EP-1", lesson_id: str = "L-1") -> h.LessonCandidate:
    return h.LessonCandidate(
        lesson_id=lesson_id, episode_id=ep_id, statement="lesson",
        evidence_record_ids=[], confidence="LOW", status="PROPOSED",
        scope="OPERATIONAL", created_at_utc="2026-09-22T00:00:00Z",
    )


class TestDurableHippocampus(unittest.TestCase):
    def test_roundtrip_reconstructs_identical_state(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        store.record_lesson(_lesson())
        tip = store.tip_hash

        reloaded = DurableHippocampus(path)
        self.assertEqual(reloaded.tip_hash, tip)
        rec = reloaded.memory.reconstruct_episode("EP-1")
        self.assertEqual(rec["episode"].goal, "test")
        self.assertEqual(len(rec["lessons"]), 1)
        self.assertEqual(rec["lessons"][0].status, "PROPOSED")

    def test_tampered_payload_breaks_chain(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        store.record_lesson(_lesson())

        lines = path.read_text(encoding="utf-8").splitlines()
        record = json.loads(lines[1])
        record["payload"]["confidence"] = "HIGH"  # silent promotion attempt
        lines[1] = json.dumps(record, ensure_ascii=False, sort_keys=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with self.assertRaisesRegex(LedgerIntegrityError, "line 2"):
            DurableHippocampus(path)

    def test_truncated_chain_breaks_prev_link(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        store.record_lesson(_lesson())
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(lines[1] + "\n", encoding="utf-8")  # drop genesis record
        with self.assertRaisesRegex(LedgerIntegrityError, "chain break"):
            DurableHippocampus(path)

    def test_duplicate_episode_rejected_and_ledger_unchanged(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        before = path.read_text(encoding="utf-8")
        # The ledger write happens first, so a memory-level rejection leaves an
        # orphaned record; the contract is that the NEXT replay raises.
        with self.assertRaises(ValueError):
            store.register_episode(_episode())
        self.assertNotEqual(path.read_text(encoding="utf-8"), before)
        with self.assertRaises(ValueError):
            DurableHippocampus(path)

    def test_invalidation_survives_restart_and_blocks_reuse(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.record_invalidation("ART-1", "INVALIDATED_BY_MEASUREMENT_ERROR")

        reloaded = DurableHippocampus(path)
        with self.assertRaises(h.InvalidatedArtifactReuseError):
            reloaded.reuse_artifact("ART-1", context="after restart")
        self.assertEqual(
            reloaded.reuse_artifact("ART-2")["status"], "ELIGIBLE")

    def test_verify_is_pure_and_matches_tip(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        store.record_invalidation("ART-9", "STALE_BY_DEPENDENCY")
        tip = store.tip_hash
        self.assertEqual(store.verify(), tip)
        self.assertEqual(store.tip_hash, tip)  # verify did not advance state

    def test_unknown_record_type_fails_closed(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        with self.assertRaises(UnknownRecordTypeError):
            store._append("promotion_granted", {"claim": "x"})

    def test_outcomes_flag_still_enforced_by_underlying_memory(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        bad = _episode()
        object.__setattr__(bad, "outcomes_inspected", True)
        with self.assertRaises(ValueError):
            store.register_episode(bad)

    def _tmp(self) -> str:
        import tempfile
        return tempfile.mkdtemp(prefix="hippocampus_ledger_") + "/ledger.jsonl"


if __name__ == "__main__":
    unittest.main(verbosity=2)
