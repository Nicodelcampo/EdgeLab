import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from edgelab.edge_brain.invalidation import DependencyEdge, propagate_invalidation
from edgelab.edge_brain.registry import LedgerIntegrityError, append_record, content_sha256, verify_registry
from edgelab.edge_brain.schema_validator import validate_record


class TestEdgeBrainFoundation(unittest.TestCase):
    def test_measurement_contract_requires_semantic_gap(self):
        record = {
            "measurement_id": "MC-RET-001",
            "intended_measurement": "Retracement after a confirmed local swing",
            "mathematical_definition": "distance from confirmed swing extreme",
            "actual_implementation": {"description": "Wait K bars after event", "code_refs": ["tools/example.py:10"]},
            "unit_of_analysis": "swing_event",
            "event_start": "breakout_ts",
            "signal_available_at": "breakout_available_ts",
            "measurement_matures_at": "swing_confirmed_ts",
            "required_wait": {"value": 3, "unit": "bars"},
            "reason_for_wait": "The swing is undefined before K bars",
            "numerator": "retracement_ticks",
            "denominator": "impulse_ticks",
            "eligibility": ["causal available_ts"],
            "exclusions": ["cross-contract windows"],
            "known_proxies": [],
            "code_commit": "49eadf0",
            "query_hash": "a" * 64,
            "required_tests": ["tests/test_measurement.py::test_wait_k"],
            "status": "DRAFT",
        }
        with self.assertRaises(jsonschema.ValidationError):
            validate_record("measurement_contract", record)
        record["semantic_gap"] = None
        validate_record("measurement_contract", record)

    def test_methodological_learning_requires_guardrail(self):
        record = {
            "learning_id": "METH-001",
            "topic": "Synthetic fills",
            "intended_measurement": "Observed executable fill",
            "actual_measurement": "available_ts plus constant latency",
            "semantic_gap": "Synthetic assumption labeled as observation",
            "error_discovered": "MEASUREMENT_SEMANTICS_FAILURE",
            "why_it_failed": "Tick stream was not evaluated",
            "affected_experiments": ["EXP-1"],
            "affected_dependent_claims": ["CLAIM-1"],
            "prevention_rule": "No fill without observed tick",
            "required_invariant": "fill_ts is null or belongs to tick stream",
            "required_test": "tests/test_fill.py::test_no_synthetic_fill",
            "valid_scope": "all instruments",
            "known_exceptions": [],
            "status": "ACTIVE_GUARDRAIL",
        }
        validate_record("methodological_learning", record)

    def test_invalidation_cascades_by_relation_strength(self):
        edges = [
            DependencyEdge("EXP-1", "MC-1", "MEASURED_BY"),
            DependencyEdge("CLAIM-1", "EXP-1", "DEPENDS_ON"),
            DependencyEdge("CLAIM-2", "CLAIM-1", "SUPPORTED_BY"),
            DependencyEdge("CLAIM-OTHER", "OTHER", "DEPENDS_ON"),
        ]
        statuses = propagate_invalidation(["MC-1"], edges)
        self.assertEqual(statuses["MC-1"], "INVALIDATED_BY_MEASUREMENT_ERROR")
        self.assertEqual(statuses["EXP-1"], "STALE_BY_DEPENDENCY")
        self.assertEqual(statuses["CLAIM-1"], "STALE_BY_DEPENDENCY")
        self.assertEqual(statuses["CLAIM-2"], "REQUIRES_REAUDIT")
        self.assertNotIn("CLAIM-OTHER", statuses)

    def test_content_hash_is_order_invariant(self):
        self.assertEqual(content_sha256({"a": 1, "b": 2}), content_sha256({"b": 2, "a": 1}))

    def test_append_only_ledger_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "brain.jsonl"
            append_record(path, record_type="claim", record_id="EVT-1", payload={"value": 1}, recorded_at_utc="2026-09-19T13:00:00Z")
            append_record(path, record_type="learning", record_id="EVT-2", payload={"value": 2}, recorded_at_utc="2026-09-19T13:01:00Z")
            self.assertTrue(verify_registry(path)["valid"])
            rows = path.read_text(encoding="utf-8").splitlines()
            tampered = json.loads(rows[0])
            tampered["payload"]["value"] = 999
            rows[0] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(rows) + "\n", encoding="utf-8")
            self.assertFalse(verify_registry(path)["valid"])
            with self.assertRaises(LedgerIntegrityError):
                append_record(path, record_type="claim", record_id="EVT-3", payload={}, recorded_at_utc="2026-09-19T13:02:00Z")


if __name__ == "__main__":
    unittest.main()
