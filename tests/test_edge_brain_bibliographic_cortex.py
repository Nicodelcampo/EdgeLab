from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from edgelab.edge_brain.bibliographic_cortex import BibliographicCortexError, SSRNBibliographicCortex
from edgelab.edge_brain.registry import verify_registry


class TestBibliographicCortex(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        for rel in ["Normalizado/documentos", "extraccion/completo", "grafo", "cerebro"]:
            (root / rel).mkdir(parents=True, exist_ok=True)
        docs = [{"id": 1, "file": "0001_alpha.txt", "words": 7}, {"id": 2, "file": "0002_beta.txt", "words": 7}]
        manifest = [
            {"id": 1, "ssrn_id": "100", "titulo": "Alpha", "url": "https://doi.org/10.2139/ssrn.100"},
            {"id": 2, "ssrn_id": "200", "titulo": "Beta", "url": "https://doi.org/10.2139/ssrn.200"},
        ]
        (root / "Normalizado/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (root / "extraccion/docs_list.json").write_text(json.dumps(docs), encoding="utf-8")
        (root / "grafo/docs_meta.json").write_text(json.dumps({"1": {"titulo": "Alpha"}, "2": {"titulo": "Beta"}}), encoding="utf-8")
        findings = [{"doc_id": 1, "afirmacion": "Order flow matters", "mercado": "ES", "periodo": "sample", "magnitud": "unknown", "condiciones": "L1", "robustez": "baja"}]
        (root / "grafo/hallazgos.json").write_text(json.dumps(findings), encoding="utf-8")
        (root / "grafo/grafo_final.json").write_text(json.dumps({"nodos": [{"id": 1}], "aristas": []}), encoding="utf-8")
        (root / "grafo/relaciones_sin_destino.json").write_text("[]", encoding="utf-8")
        (root / "Normalizado/documentos/0001_alpha.txt").write_text("order flow imbalance predicts short returns", encoding="utf-8")
        (root / "Normalizado/documentos/0002_beta.txt").write_text("transaction costs destroy weak strategies", encoding="utf-8")
        for doc_id, title in [(1, "Alpha"), (2, "Beta")]:
            (root / f"extraccion/completo/{doc_id:04d}.json").write_text(json.dumps({"doc_id": doc_id, "titulo": title, "conceptos": [], "hallazgos": []}), encoding="utf-8")
        (root / "cerebro/LEDGER_EXPERIMENTOS.md").write_text("# Ledger\n## EXP-001 — test histórico\nResultado no reauditado.\n", encoding="utf-8")
        con = sqlite3.connect(root / "Normalizado/chunks.sqlite")
        con.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, doc_id INTEGER, doc_titulo TEXT, archivo_fuente TEXT, chunk_index INTEGER, n_chunks_doc INTEGER, texto TEXT, n_palabras INTEGER)")
        con.execute("CREATE TABLE passages (id INTEGER PRIMARY KEY, chunk_id INTEGER, doc_id INTEGER, passage_index INTEGER, texto TEXT)")
        con.executemany("INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?)", [(1,1,"Alpha","0001_alpha.txt",0,1,"order flow imbalance predicts short returns",7),(2,2,"Beta","0002_beta.txt",0,1,"transaction costs destroy weak strategies",7)])
        con.executemany("INSERT INTO passages VALUES (?,?,?,?,?)", [(1,1,1,0,"order flow imbalance predicts short returns"),(2,2,2,0,"transaction costs destroy weak strategies")])
        con.commit(); con.close()
        return root

    def test_incomplete_root_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BibliographicCortexError):
                SSRNBibliographicCortex(tmp)

    def test_audit_and_retrieval_cover_every_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            cortex = SSRNBibliographicCortex(self.fixture(Path(tmp)))
            expected = {"usable_papers": 2, "normalized_documents": 2, "complete_extractions": 2, "chunks": 2, "passages": 2, "findings": 1, "graph_nodes": 1, "graph_edges": 0}
            self.assertEqual(cortex.audit(expected).status, "VERIFIED_COMPLETE")
            self.assertEqual(cortex.search_passages("order flow", 1)[0].doc_id, 1)
            self.assertEqual(cortex.search_passages("transaction costs", 1)[0].doc_id, 2)

    def test_custody_manifest_hashes_every_paper(self):
        with tempfile.TemporaryDirectory() as tmp:
            cortex = SSRNBibliographicCortex(self.fixture(Path(tmp)))
            manifest = cortex.custody_manifest("a" * 64, "2026-09-21T13:00:00Z")
            self.assertEqual(len(manifest["papers"]), 2)
            self.assertEqual(len(manifest["papers_aggregate_sha256"]), 64)
            self.assertTrue(all(len(x["normalized_sha256"]) == 64 for x in manifest["papers"]))

    def test_ingest_is_hash_chained_and_non_authoritative(self):
        with tempfile.TemporaryDirectory() as tmp:
            cortex = SSRNBibliographicCortex(self.fixture(Path(tmp) / "corpus"))
            ledger = Path(tmp) / "bibliographic.jsonl"
            result = cortex.ingest_ledger(ledger, created_at_utc="2026-09-21T13:00:00Z")
            self.assertEqual(result["sources"], 3)
            self.assertEqual(result["historical_experiments"], 1)
            self.assertTrue(verify_registry(ledger)["valid"])
            body = ledger.read_text(encoding="utf-8")
            self.assertIn("AUTHOR_REPORTED_RESULT", body)
            self.assertIn("HISTORICAL_EXPERIMENT_PENDING_REAUDIT", body)
            self.assertNotIn('"status":"SUPPORTED"', body)

    def test_context_pack_is_bounded_and_citable(self):
        with tempfile.TemporaryDirectory() as tmp:
            cortex = SSRNBibliographicCortex(self.fixture(Path(tmp)))
            pack = cortex.context_pack("order flow", limit=2, max_chars=20)
            self.assertLessEqual(pack["used_chars"], 20)
            self.assertFalse(pack["claims_are_evidence"])
            self.assertTrue(pack["items"][0]["source_id"].startswith("SRC-SSRN-"))


if __name__ == "__main__":
    unittest.main()
