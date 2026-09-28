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
from unittest.mock import patch

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

    def test_suffix_rollback_requires_and_is_detected_by_external_tip_anchor(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        store.record_lesson(_lesson())
        trusted_tip = store.tip_hash
        lines = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(lines[0])  # remove a valid suffix; internal links still verify

        caller_memory = h.HippocampusMemory()
        with self.assertRaisesRegex(LedgerIntegrityError, "externally trusted"):
            DurableHippocampus(path, memory=caller_memory,
                               expected_tip_hash=trusted_tip)
        self.assertEqual(caller_memory.episodes, {})  # failed open did not publish replay

        prefix = DurableHippocampus(path)
        with self.assertRaisesRegex(LedgerIntegrityError, "externally trusted"):
            prefix.verify(expected_tip_hash=trusted_tip)

    def test_duplicate_episode_rejected_and_ledger_unchanged(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        before = path.read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            store.register_episode(_episode())
        self.assertEqual(path.read_text(encoding="utf-8"), before)
        reloaded = DurableHippocampus(path)
        self.assertEqual(reloaded.tip_hash, store.tip_hash)
        self.assertEqual(len(reloaded.memory.episodes), 1)

    def test_invalid_related_records_do_not_touch_ledger_or_memory(self):
        invalid_calls = [
            ("step", lambda store: store.record_step(h.StepExecution(
                step_id="S-1", episode_id="MISSING", step_index=0,
                action="test", tool_name="test"))),
            ("expectation", lambda store: store.record_expectation(h.Expectation(
                expectation_id="X-1", episode_id="MISSING", statement="test",
                metric="metric", expected_direction="up"))),
            ("failure", lambda store: store.record_failure(h.FailureEvent(
                failure_id="F-1", episode_id="MISSING", step_id="S-1",
                error_type="test", description="test", root_cause="test"))),
            ("success", lambda store: store.record_success(h.SuccessEvent(
                success_id="OK-1", episode_id="MISSING", step_id="S-1",
                description="test"))),
            ("lesson", lambda store: store.record_lesson(_lesson("MISSING"))),
            ("repair", lambda store: store.record_repair(h.RepairAction(
                repair_id="R-1", failure_id="F-1", description="test"),
                "MISSING")),
        ]
        for name, call in invalid_calls:
            with self.subTest(record_type=name):
                path = Path(self._tmp())
                store = DurableHippocampus(path)
                before_memory = {
                    key: dict(value) for key, value in store.memory.__dict__.items()
                }
                with self.assertRaises(ValueError):
                    call(store)
                self.assertFalse(path.exists())
                self.assertEqual(store.memory.__dict__, before_memory)
                reloaded = DurableHippocampus(path)
                self.assertEqual(reloaded.memory.__dict__, before_memory)
                self.assertEqual(reloaded.tip_hash, store_mod.GENESIS_HASH)

    def test_lesson_authority_ceiling_is_enforced_on_write_and_replay(self):
        path = Path(self._tmp())
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        before = path.read_bytes()

        for status, confidence in (("PROMOTED", "HIGH"), ("PROPOSED", "HIGH")):
            lesson = _lesson()
            lesson.status = status
            lesson.confidence = confidence
            with self.subTest(status=status, confidence=confidence):
                with self.assertRaisesRegex(ValueError, "PROPOSED/LOW"):
                    store.record_lesson(lesson)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(store.memory.reconstruct_episode("EP-1")["lessons"], [])

        # A caller can recompute hashes, so integrity alone is not the authority
        # gate. Replay must also reject a fully hash-consistent promotion.
        record = json.loads(before.splitlines()[0])
        lesson_record = {
            "schema": store_mod.LEDGER_SCHEMA,
            "type": "lesson_recorded",
            "prev_hash": record["hash"],
            "payload": {
                **{key: value for key, value in _lesson().__dict__.items()},
                "status": "PROMOTED",
                "confidence": "HIGH",
            },
        }
        lesson_record["hash"] = store_mod._record_hash(
            lesson_record["type"], lesson_record["payload"], lesson_record["prev_hash"])
        path.write_bytes(before + (json.dumps(lesson_record, sort_keys=True) + "\n").encode())
        with self.assertRaisesRegex(LedgerIntegrityError, "authority ceiling"):
            DurableHippocampus(path)

    def test_partial_append_fails_closed_and_poisoned_store_cannot_continue(self):
        path = Path(self._tmp())
        memory = h.HippocampusMemory()
        store = DurableHippocampus(path, memory=memory)

        class PartialWriter:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def write(self, data):
                with open(path, "ab") as raw:
                    raw.write(data[:20])
                raise OSError("simulated partial append")

        with patch.object(Path, "open", return_value=PartialWriter()):
            with self.assertRaisesRegex(OSError, "partial append"):
                store.register_episode(_episode())

        self.assertIs(store.memory, memory)
        self.assertEqual(memory.episodes, {})
        self.assertEqual(store.tip_hash, store_mod.GENESIS_HASH)
        with self.assertRaisesRegex(LedgerIntegrityError, "disabled after a failed append"):
            store.register_episode(_episode("EP-2"))
        # La cola a medias se trunca al ultimo byte verificado: el ledger sigue siendo reproducible.
        self.assertEqual(path.read_bytes(), b"")
        self.assertEqual(DurableHippocampus(path).tip_hash, store_mod.GENESIS_HASH)

    def test_successful_write_preserves_supplied_memory_identity(self):
        path = Path(self._tmp())
        memory = h.HippocampusMemory()
        store = DurableHippocampus(path, memory=memory)
        store.register_episode(_episode())
        self.assertIs(store.memory, memory)
        self.assertIn("EP-1", memory.episodes)

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


class TestStoreHardening20260923(unittest.TestCase):
    """Hallazgos reproducidos en la auditoria del patch (2026-09-23)."""

    def _tmp(self):
        import tempfile
        d = tempfile.mkdtemp()
        return Path(d) / "ledger.jsonl"

    def test_second_writer_is_detected_not_forked(self):
        path = self._tmp()
        a = DurableHippocampus(path); b = DurableHippocampus(path)
        a.register_episode(_episode())
        with self.assertRaisesRegex(LedgerIntegrityError, "changed on disk"):
            b.register_episode(_episode("EP-2"))
        self.assertEqual(DurableHippocampus(path).tip_hash, a.tip_hash)   # sigue siendo legible

    def test_torn_tail_is_refused_at_open(self):
        path = self._tmp()
        DurableHippocampus(path).register_episode(_episode())
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        with self.assertRaisesRegex(LedgerIntegrityError, "torn"):
            DurableHippocampus(path)

    def test_keyboard_interrupt_during_write_truncates_and_poisons(self):
        path = self._tmp()
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        before = path.read_bytes()

        class Interrupting:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def write(self, data):
                with open(path, "ab") as raw:
                    raw.write(data[:10])
                raise KeyboardInterrupt

        with patch.object(Path, "open", return_value=Interrupting()):
            with self.assertRaises(KeyboardInterrupt):
                store.record_lesson(_lesson())
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaisesRegex(LedgerIntegrityError, "disabled"):
            store.record_lesson(_lesson())

    def test_invalidation_statuses_are_closed_and_stale_views_rejected(self):
        path = self._tmp()
        a = DurableHippocampus(path)
        for bad in ("INVALIDATED", "ELIGIBLE"):
            with self.assertRaises(ValueError):
                a.record_invalidation("ART-1", bad)
        with self.assertRaises(ValueError):
            a.record_invalidation("ART-1 ", "STALE_BY_DEPENDENCY")
        b = DurableHippocampus(path)
        a.record_invalidation("ART-1", "INVALIDATED_BY_MEASUREMENT_ERROR")
        with self.assertRaisesRegex(LedgerIntegrityError, "changed on disk"):
            b.reuse_artifact("ART-1")               # antes devolvia ELIGIBLE con una vista vieja

    def test_memory_does_not_alias_caller_objects(self):
        path = self._tmp()
        store = DurableHippocampus(path)
        store.register_episode(_episode())
        lesson = _lesson()
        store.record_lesson(lesson)
        lesson.status, lesson.confidence = "ADOPTED", "HIGH"
        stored = store.memory.reconstruct_episode("EP-1")["lessons"][0]
        status = stored["status"] if isinstance(stored, dict) else stored.status
        self.assertEqual(status, "PROPOSED")

    def test_retrieval_refuses_a_tampered_ledger(self):
        from edgelab.edge_brain.retrieval import LedgerIndex
        path = self._tmp()
        DurableHippocampus(path).register_episode(_episode())
        rec = json.loads(path.read_text(encoding="utf-8"))
        rec["payload"]["goal"] = "tampered"
        path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "hash mismatch"):   # clase del paquete real, no la de _load
            LedgerIndex.from_ledger(path)

