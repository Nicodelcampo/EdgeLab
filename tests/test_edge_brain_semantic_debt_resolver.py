from __future__ import annotations

import unittest

from edgelab.edge_brain.semantic_debt_resolver import resolve_semantic_debt


class TestSemanticDebtResolver(unittest.TestCase):
    def graph(self):
        return {
            "nodos": [
                {
                    "id": "market efficiency",
                    "nombre_canonico": "market efficiency",
                    "tipo": "concepto",
                    "nombres_vistos": ["Market Efficiency"],
                    "menciones": 1,
                    "doc_frecuencia": 1,
                    "doc_ids": [1],
                    "definiciones": [],
                    "citas": [],
                    "relaciones_crudas": [
                        {"tipo": "CAUSA", "tipo_original": "CAUSA", "objeto_texto": "market inefficiency", "doc_id": 1, "revisar": False},
                        {"tipo": "EXPLICA", "tipo_original": "EXPLICA", "objeto_texto": "price discovery quality", "doc_id": 1, "revisar": True},
                    ],
                }
            ],
            "aristas": [],
        }

    def unresolved(self):
        return [
            {"objeto": "market inefficiency", "menciones": 1, "n_docs": 1, "tipos": ["CAUSA"]},
            {"objeto": "price discovery quality", "menciones": 1, "n_docs": 1, "tipos": ["EXPLICA"]},
        ]

    def test_resolves_every_target_without_fuzzy_antonym_merge(self):
        resolved, decisions, summary = resolve_semantic_debt(self.graph(), self.unresolved())
        ids = {node["id"] for node in resolved["nodos"]}
        self.assertIn("market efficiency", ids)
        self.assertIn("market inefficiency", ids)
        self.assertEqual(summary.unresolved_targets_output, 0)
        self.assertEqual(summary.target_nodes_created, 2)
        self.assertEqual(len(decisions), 2)

    def test_preserves_unadjudicated_relation_type(self):
        resolved, _, summary = resolve_semantic_debt(self.graph(), self.unresolved())
        edge = next(edge for edge in resolved["aristas"] if edge["tipo"] == "EXPLICA")
        self.assertEqual(edge["relation_status"], "EXTRACTED_TYPE_UNADJUDICATED")
        self.assertEqual(edge["authority_status"], "LLM_EXTRACTED_CONCEPT")
        self.assertEqual(summary.unadjudicated_types_preserved, 1)

    def test_resolution_is_deterministic(self):
        first = resolve_semantic_debt(self.graph(), self.unresolved())[2]
        second = resolve_semantic_debt(self.graph(), self.unresolved())[2]
        self.assertEqual(first.graph_sha256, second.graph_sha256)
        self.assertEqual(first.decisions_sha256, second.decisions_sha256)

    def test_all_edges_have_materialized_endpoints(self):
        resolved, _, _ = resolve_semantic_debt(self.graph(), self.unresolved())
        ids = {node["id"] for node in resolved["nodos"]}
        self.assertTrue(all(edge["origen"] in ids and edge["destino"] in ids for edge in resolved["aristas"]))


if __name__ == "__main__":
    unittest.main()
