"""Busqueda bilingue del cortex SSRN: glosario (siempre) + benchmark sobre el corpus real (si esta armado).

Benchmark: 15 consultas (7 en castellano). Se mide precision@5 por paper distinto contra un patron de tema.
Linea base 2026-10-09: busqueda LIKE original = 0.16; ranked (FTS5 + glosario) = 0.61 pasajes,
~0.95 papers, ~0.93 hallazgos.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from edgelab.edge_brain.bibliographic_cortex import SSRNBibliographicCortex
from edgelab.edge_brain.retrieval import LedgerIndex
from edgelab.edge_brain.trading_glossary import expand_phrases, expand_query, fold

REPO_CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "ssrn"
BENCH = [
    ("pairs trading transaction costs", r"pairs"), ("costos de transacción en pairs trading", r"pairs"),
    ("VWAP execution", r"vwap"), ("ejecución VWAP", r"vwap"),
    ("order book dynamics", r"order book|limit order"), ("dinámica del libro de órdenes", r"order book|limit order"),
    ("cointegration statistical arbitrage", r"cointegrat|statistical arbitrage|pairs"),
    ("arbitraje estadístico cointegración", r"cointegrat|statistical arbitrage|pairs"),
    ("realized volatility microstructure noise", r"volatil|noise"),
    ("reinforcement learning trading", r"reinforcement|q-learn"), ("aprendizaje por refuerzo", r"reinforcement|q-learn"),
    ("HFT regulation", r"regula|\bact\b|law"), ("regulación de alta frecuencia", r"regula|\bact\b|law"),
    ("reversión a la media", r"mean.revers|statistical arbitrage|pairs"), ("liquidez", r"liquid"),
]


def _p_at_5(titles: list[str], pattern: str) -> float:
    return sum(bool(re.search(pattern, t, re.I)) for t in titles[:5]) / 5


class TestGlossary(unittest.TestCase):
    def test_fold_and_bilingual_expansion(self):
        self.assertEqual(fold("Ejecución ÓRDENES"), "ejecucion ordenes")
        terms = expand_query("desbalance del libro de órdenes")
        for t in ("desbalance", "imbalance", "order", "book"):
            self.assertIn(t, terms)
        self.assertNotIn("del", terms)
        self.assertIn("order book", expand_phrases("libro de ordenes"))
        self.assertIn("libro de ordenes", expand_phrases("order book"))   # en -> es tambien
        self.assertIn("frequency", expand_query("HFT"))                     # siglas

    def test_ledger_index_folds_accents_and_expands(self):
        idx = LedgerIndex([("lesson_recorded", {"lesson_id": "L-1", "statement": "la ejecución falló por deslizamiento"})])
        self.assertEqual(idx.query("ejecucion")[0].record_id, "L-1")
        self.assertEqual(idx.query("slippage"), [])
        self.assertEqual(idx.query("slippage", expand=True)[0].record_id, "L-1")


@unittest.skipUnless((REPO_CORPUS / "Normalizado" / "chunks.sqlite").is_file(),
                     "corpus not bootstrapped (python tools/ssrn_corpus_bootstrap.py)")
class TestRankedSearchBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cortex = SSRNBibliographicCortex(REPO_CORPUS)
        assert cls.cortex.ensure_fts_index()

    def _bench(self, fn) -> float:
        total = 0.0
        for query, pattern in BENCH:
            total += _p_at_5(fn(query), pattern)
        return total / len(BENCH)

    def _distinct_titles(self, hits):
        seen = []
        for h in hits:
            if h.title not in seen:
                seen.append(h.title)
        return seen

    def test_passages_ranked_beats_like_baseline(self):
        old = self._bench(lambda q: self._distinct_titles(self.cortex.search_passages(q, limit=5)))
        new = self._bench(lambda q: self._distinct_titles(self.cortex.search_passages_ranked(q, limit=5)))
        self.assertGreaterEqual(new, 0.55)
        self.assertGreater(new, old + 0.3)

    def test_find_papers_spanish_and_english(self):
        score = self._bench(lambda q: [p["title"] + " " + p["summary"] for p in self.cortex.find_papers(q, limit=5)])
        self.assertGreaterEqual(score, 0.85)
        es = [p["source_id"] for p in self.cortex.find_papers("costos de transacción en pairs trading", limit=3)]
        en = [p["source_id"] for p in self.cortex.find_papers("pairs trading transaction costs", limit=3)]
        self.assertTrue(set(es) & set(en))                                 # mismo paper en ambos idiomas
        top = self.cortex.find_papers("liquidez", limit=1)[0]
        self.assertEqual(top["authority_status"], "LITERATURE_CLAIM_UNVERIFIED")
        self.assertTrue(0.85 <= top["usefulness"] <= 1.15)

    def test_findings_ranked(self):
        score = self._bench(lambda q: [f["title"] + " " + f["text"] for f in self.cortex.search_findings_ranked(q, limit=5)])
        self.assertGreaterEqual(score, 0.85)
        self.assertRegex(self.cortex.search_findings_ranked("VWAP", limit=1)[0]["claim_id"], r"CLAIM-SSRN-FINDING-\d{4}")

    def test_planner_proposes_measurable_claims(self):
        from edgelab.edge_brain.literature_planner import propose_tests
        props = propose_tests(self.cortex, ["agrupamiento de volumen en horas redondas",
                                            "continuidad del flujo de órdenes comprador vendedor"], limit=10)
        ids = [p.claim_id for p in props]
        self.assertIn("CLAIM-SSRN-FINDING-0439", ids)
        self.assertTrue(all(not p.blockers for p in props))
        done = propose_tests(self.cortex, "agrupamiento de volumen en horas redondas", limit=10,
                             claim_status=lambda c: "TESTED_PENDING_ADJUDICATION" if c.endswith("0439") else
                             "AUTHOR_REPORTED_RESULT")
        self.assertNotIn("CLAIM-SSRN-FINDING-0439", [p.claim_id for p in done])

    def test_index_is_deterministic_and_versioned(self):
        self.assertEqual(self.cortex.fts_status(), "READY")
        a = self.cortex.find_papers("order flow imbalance", limit=5)
        b = self.cortex.find_papers("order flow imbalance", limit=5)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
