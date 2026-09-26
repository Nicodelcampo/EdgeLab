"""Tests for BM25 retrieval and the narrative ledger projection.

Includes the EDGE-007 seed benchmark: fixed queries over the pinned CYCLE-001
genesis ledger with expected top hits. Any future retrieval change (embeddings,
hybrid) must not regress this seed set.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENESIS = ROOT / "artifacts" / "hippocampus" / "cycle001_genesis_ledger.jsonl"


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
retr = _load("edgelab.edge_brain.retrieval", ROOT / "edgelab" / "edge_brain" / "retrieval.py")

# EDGE-007 seed benchmark: query -> expected top-1 record id.
# Baseline fijado midiendo el ranker BM25 (2026-09-23): el registro maa on-topic
# gana aunque sea un counterexample y no la leccion; eso es lo correcto.
SEED = {
    "dataset publico privacidad verificar sin autenticacion":
        "CX-CYCLE001-KAGGLE-PUBLIC-DATASET",
    "worker duplicado 400 canonico 200 identidad":
        "FAILURE-CYCLE001-WORKER-DUPLICATE-400",
    "boolean caller payload schema autenticacion":
        "LESSON-CYCLE001-NO-CALLER-SUPPLIED-TRUTH",
    "secretos excepciones bearer authorization":
        "CX-CYCLE001-D-C-002",
    "ci local pasa remoto falla paths":
        "LESSON-CYCLE001-LOCAL-PASS-NOT-CI-PASS",
}


class TestRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = retr.LedgerIndex.from_ledger(GENESIS)

    def test_index_covers_genesis(self):
        self.assertEqual(self.index.size, 14)

    def test_seed_benchmark_top1(self):
        """EDGE-007: fixed queries must keep their expected top-1 hit."""
        for query, expected_id in SEED.items():
            with self.subTest(query=query):
                hits = self.index.query(query, k=3)
                self.assertTrue(hits, f"no hits for {query!r}")
                self.assertEqual(hits[0].record_id, expected_id)

    def test_deterministic_repeated_queries(self):
        a = self.index.query("privacy probe kaggle", k=5)
        b = self.index.query("privacy probe kaggle", k=5)
        self.assertEqual(a, b)

    def test_empty_and_novel_queries_fail_soft(self):
        self.assertEqual(self.index.query("", k=5), [])
        hits = self.index.query("zxqwv kryptonite unrelated", k=5)
        self.assertTrue(all(h.score > 0 for h in hits))

    def test_from_memory_matches_from_ledger(self):
        store = store_mod.DurableHippocampus(GENESIS)
        live = retr.LedgerIndex.from_memory(store.memory)
        q = "denylist normalized keys"
        self.assertEqual([r.record_id for r in live.query(q, k=3)],
                         [r.record_id for r in self.index.query(q, k=3)])


class TestNarrativeProjection(unittest.TestCase):
    def test_render_markdown_is_deterministic_and_complete(self):
        store = store_mod.DurableHippocampus(GENESIS)
        md1, md2 = store.render_markdown(), store.render_markdown()
        self.assertEqual(md1, md2)
        self.assertIn("EPISODE-CYCLE-001-MULTIAGENT", md1)
        self.assertIn("LESSON-CYCLE001-PRIVACY-BY-PROBE", md1)
        self.assertIn("CX-CYCLE001-KAGGLE-PUBLIC-DATASET", md1)
        self.assertIn("UNRATED", md1)  # robustness field rendered

    def test_v1_lessons_replay_with_default_robustness(self):
        """EDGE-006 migration gate: genesis (written before the field existed)
        must replay unchanged, with robustness defaulting to UNRATED."""
        store = store_mod.DurableHippocampus(GENESIS)
        rec = store.memory.reconstruct_episode("EPISODE-CYCLE-001-MULTIAGENT")
        for lesson in rec["lessons"]:
            self.assertEqual(lesson.robustness, "UNRATED")
            self.assertEqual(lesson.conditions, [])
        self.assertEqual(store.tip_hash,
                         "af5d862d388ae4660a95bda59846f23c3e21622990e13d73371f240ddd975693")


if __name__ == "__main__":
    unittest.main(verbosity=2)
