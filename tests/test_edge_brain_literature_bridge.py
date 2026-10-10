from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from edgelab.edge_brain.bibliographic_cortex import BibliographicCortexError, SSRNBibliographicCortex
from edgelab.edge_brain.hippocampus import AnalysisEpisode, LessonCandidate
from edgelab.edge_brain.hippocampus_store import DurableHippocampus, LedgerIntegrityError
from edgelab.edge_brain.literature_bridge import EdgeBrainMemory
import tests.test_edge_brain_bibliographic_cortex as _cortex_tests

T0 = "2026-10-09T20:00:00Z"
REPO_CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "ssrn"


class TestLiteratureBridge(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self.cortex = SSRNBibliographicCortex(_cortex_tests.TestBibliographicCortex.fixture(None, tmp / "corpus"))
        self.ledger = tmp / "brain.jsonl"
        self.store = DurableHippocampus(self.ledger)
        self.store.register_episode(AnalysisEpisode(episode_id="EP-1", goal="estudiar order flow", created_at_utc=T0))
        self.store.record_lesson(LessonCandidate(lesson_id="L-1", episode_id="EP-1", confidence="LOW",
                                                 statement="order flow imbalance fallo con costos reales"))
        self.brain = EdgeBrainMemory(self.store, self.cortex)

    def tearDown(self):
        self._tmp.cleanup()

    def consult(self, cid="CONS-1", query="order flow imbalance"):
        return self.brain.consult(consultation_id=cid, episode_id="EP-1", query=query,
                                  purpose="antes de proponer hipotesis", recorded_by="test", created_at_utc=T0)

    def test_recall_joins_own_memory_and_literature_with_authority(self):
        rec = self.brain.recall("order flow imbalance")
        self.assertEqual(rec.own[0].record_id, "L-1")
        self.assertEqual(rec.findings[0].source_id, "SRC-SSRN-0001")
        self.assertEqual(rec.findings[0].authority_status, "AUTHOR_REPORTED_RESULT")
        self.assertEqual(rec.passages[0].authority_status, "LITERATURE_CLAIM_UNVERIFIED")
        self.assertFalse(rec.to_dict()["claims_are_evidence"])
        self.assertEqual(self.ledger.read_text(encoding="utf-8").count("literature_consulted"), 0)  # recall = solo lectura

    def test_consult_is_persisted_replayed_and_searchable(self):
        cons = self.consult()
        self.assertIn("CONS-1", self.store.literature)
        reopened = DurableHippocampus(self.ledger)
        self.assertEqual(reopened.literature["CONS-1"]["items"][0]["source_id"], "SRC-SSRN-0001")
        self.assertEqual(reopened.verify(), self.store.tip_hash)
        self.assertIn({"source_id": "CONS-1", "target_id": "SRC-SSRN-0001", "relation": "SUPPORTED_BY"},
                      reopened.dependencies)
        own_ids = [h.record_id for h in EdgeBrainMemory(reopened, self.cortex).recall("order flow").own]
        self.assertIn("CONS-1", own_ids)
        pack = cons.context_pack("CP-1", "EP-1", token_budget=10_000, created_at_utc=T0)
        self.assertTrue(pack.provenance.startswith("literature_consulted:CONS-1@"))
        self.assertTrue(any(i.item_type.startswith("FINDING") for i in pack.items))

    def test_invalid_paper_cascades_to_cited_hypothesis(self):
        self.consult()
        self.brain.cite("HYP-OFI-1", "CONS-1")
        statuses = self.brain.invalidate_source("SRC-SSRN-0001")
        self.assertEqual(statuses["CONS-1"], "REQUIRES_REAUDIT")
        self.assertEqual(statuses["HYP-OFI-1"], "REQUIRES_REAUDIT")
        with self.assertRaises(Exception):
            DurableHippocampus(self.ledger).reuse_artifact("HYP-OFI-1")

    def test_fail_closed_guards(self):
        with self.assertRaises(BibliographicCortexError):
            self.consult(query="zzzz qqqq")                         # nada que registrar
        with self.assertRaises(ValueError):
            self.brain.consult(consultation_id="C-X", episode_id="EP-NOPE", query="order flow", purpose="p",
                               recorded_by="t", created_at_utc=T0)  # episodio inexistente
        self.consult()
        with self.assertRaises(ValueError):
            self.consult()                                          # id duplicado
        with self.assertRaises(ValueError):
            self.brain.cite("HYP-2", "CONS-NOPE")

    def test_tampered_authority_is_rejected_on_replay(self):
        self.consult()
        from edgelab.edge_brain.hippocampus_store import _record_hash
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        out, prev = [], "0" * 64
        for raw in lines:   # re-encadena con autoridad elevada: la cadena cierra, el techo no
            rec = json.loads(raw)
            if rec["type"] == "literature_consulted":
                rec["payload"]["claims_are_evidence"] = True
            rec["prev_hash"] = prev
            rec["hash"] = prev = _record_hash(rec["type"], rec["payload"], prev)
            out.append(json.dumps(rec, ensure_ascii=False, sort_keys=True))
        self.ledger.write_text("\n".join(out) + "\n", encoding="utf-8")
        with self.assertRaises(LedgerIntegrityError):
            DurableHippocampus(self.ledger)


@unittest.skipUnless((REPO_CORPUS / "Normalizado" / "chunks.sqlite").is_file(),
                     "corpus not bootstrapped (python tools/ssrn_corpus_bootstrap.py)")
class TestLiteratureBridgeRealCorpus(unittest.TestCase):
    def test_real_corpus_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DurableHippocampus(Path(tmp) / "brain.jsonl")
            brain = EdgeBrainMemory(store, SSRNBibliographicCortex(REPO_CORPUS))
            rec = brain.recall("order flow imbalance midprice desbalance")
            self.assertTrue(rec.findings and rec.passages)
            self.assertTrue(all(h.source_id.startswith("SRC-SSRN-") for h in rec.literature))


if __name__ == "__main__":
    unittest.main()
