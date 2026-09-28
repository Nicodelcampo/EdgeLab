from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from edgelab.edge_brain.context_memory import (
    ContextItem,
    ContextMemoryError,
    ContextPack,
    build_deterministic_context_pack,
)
from edgelab.edge_brain.hippocampus import (
    AnalysisEpisode,
    Counterexample,
    Expectation,
    FailureEvent,
    HippocampusError,
    HippocampusMemory,
    InvalidatedArtifactReuseError,
    LessonCandidate,
    RepairAction,
    StepExecution,
    SuccessEvent,
)
from edgelab.edge_brain.invalidation import DependencyEdge, propagate_invalidation
from edgelab.edge_brain.measurement_atlas import (
    AtlasValidationError,
    validate_atlas,
    validate_composition,
    validate_indicator,
)
from edgelab.edge_brain.model_policy import ModelPolicyViolation, validate_independent_review
from edgelab.edge_brain.registry import LedgerIntegrityError, verify_registry
from edgelab.edge_brain.schema_validator import SCHEMA_DIR, get_schema, validate_record
from edgelab.edge_brain.typed_registry import (
    TYPED_RELATIONS,
    TypedEdge,
    TypedRegistryError,
    append_typed_record,
    project_to_json,
    project_to_parquet_zstd,
    read_parquet_projection,
    validate_synthesis_promotion,
)


class TestEdgeBrainHippocampusAtlas(unittest.TestCase):
    def test_exact_inventory_of_35_schemas(self):
        """1. Verify exact inventory of 35 registered schemas in edge_brain."""
        self.assertTrue(SCHEMA_DIR.is_dir(), f"Schema dir missing: {SCHEMA_DIR}")
        schemas = sorted([p.stem for p in SCHEMA_DIR.glob("*.json")])
        self.assertEqual(
            len(schemas),
            35,
            f"Expected exactly 35 schemas, got {len(schemas)}: {schemas}",
        )
        for s_name in schemas:
            schema = get_schema(s_name)
            self.assertIn("$schema", schema)
            self.assertIn("$id", schema)
            self.assertEqual(schema["type"], "object")

    def test_validation_of_atlas_seed(self):
        """2. Validate the seed measurement atlas file."""
        seed_path = Path(__file__).resolve().parents[1] / "config" / "edge_brain" / "measurement_atlas_seed.json"
        self.assertTrue(seed_path.is_file(), f"Seed atlas missing: {seed_path}")
        result = validate_atlas(seed_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["catalog_id"], "ATLAS-FOUNDATION")
        self.assertEqual(result["indicators_count"], 2)
        self.assertEqual(result["compositions_count"], 1)
        self.assertEqual(result["concepts_count"], 1)

    def test_seed_atlas_cannot_assert_edge(self):
        """Seed catalog, indicator, or composition asserting edge in DRAFT/PROPOSED must fail."""
        bad_indicator = {
            "indicator_id": "IND-BAD",
            "name": "Bad Indicator",
            "role": "TRIGGER",
            "formula_description": "Test formula",
            "parameters": {},
            "units": "ticks",
            "timing": "close",
            "normalization": "none",
            "ablations": ["none"],
            "failure_modes": ["none"],
            "status": "DRAFT",
            "asserts_edge": True,  # Forbidden in DRAFT/PROPOSED
            "created_at_utc": "2026-09-20T00:00:00Z",
        }
        with self.assertRaises(AtlasValidationError):
            validate_indicator(bad_indicator)

    def test_nonexistent_references_blocked_in_atlas(self):
        """3. Compositions referencing undeclared components must fail validation."""
        bad_comp = {
            "composition_id": "COMP-BAD",
            "name": "Bad Composition",
            "components": ["IND-EMA", "IND-NONEXISTENT"],
            "composition_logic": "EMA and missing component",
            "required_roles": ["REGIME_GATE", "TRIGGER"],
            "interaction_hypothesis": "Test",
            "ablations": ["none"],
            "status": "DRAFT",
            "asserts_edge": False,
            "created_at_utc": "2026-09-20T00:00:00Z",
        }
        with self.assertRaises(AtlasValidationError):
            validate_composition(bad_comp, known_indicators={"IND-EMA", "IND-RSI"})

    def test_llm_proposal_not_acceptable_as_evidence(self):
        """4. Verify LLM proposals cannot be registered as evidence or self-promoted."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "brain.jsonl"
            # Attempt to register an LLM proposal with is_proposal_not_evidence=False
            with self.assertRaises(jsonschema.ValidationError):
                append_typed_record(
                    ledger_path,
                    record_type="causal_hypothesis",
                    record_id="HYP-LLM-001",
                    payload={
                        "hypothesis_id": "HYP-LLM-001",
                        "statement": "LLM claims edge without evidence",
                        "source_type": "LLM_PROPOSAL",
                        "is_proposal_not_evidence": False,  # Violates schema const: true
                        "proposed_by": "gpt-4",
                        "mechanism": "Unverified assertion",
                        "falsification_condition": "Any test",
                        "status": "PROPOSED",
                        "created_at_utc": "2026-09-20T00:00:00Z",
                    },
                    recorded_at_utc="2026-09-20T00:00:00Z",
                )

            # Attempt to register an LLM proposal as CORROBORATED
            with self.assertRaises(TypedRegistryError):
                append_typed_record(
                    ledger_path,
                    record_type="causal_hypothesis",
                    record_id="HYP-LLM-002",
                    payload={
                        "hypothesis_id": "HYP-LLM-002",
                        "statement": "LLM claims edge without evidence",
                        "source_type": "LLM_PROPOSAL",
                        "is_proposal_not_evidence": True,
                        "proposed_by": "gpt-4",
                        "mechanism": "Unverified assertion",
                        "falsification_condition": "Any test",
                        "status": "CORROBORATED",  # Self-promotion to evidence forbidden
                        "created_at_utc": "2026-09-20T00:00:00Z",
                    },
                    recorded_at_utc="2026-09-20T00:00:00Z",
                )

    def test_validation_before_append(self):
        """5. Invalid records must be rejected BEFORE touching the ledger file."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "brain.jsonl"
            invalid_payload = {
                "episode_id": "EPISODE-001",
                # missing required fields
            }
            with self.assertRaises(jsonschema.ValidationError):
                append_typed_record(
                    ledger_path,
                    record_type="analysis_episode",
                    record_id="EPISODE-001",
                    payload=invalid_payload,
                    recorded_at_utc="2026-09-20T00:00:00Z",
                )
            self.assertFalse(ledger_path.exists(), "Ledger should not exist after rejected append")

    def test_detection_of_altered_ledger(self):
        """6. Tampering with any byte or hash in the ledger is detected."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "brain.jsonl"
            append_typed_record(
                ledger_path,
                record_type="skill",
                record_id="SKILL-001",
                payload={
                    "skill_id": "SKILL-001",
                    "name": "Test Skill",
                    "description": "Deterministic skill",
                    "workflow_steps": ["step1", "step2"],
                    "input_schema": "input.json",
                    "output_schema": "output.json",
                    "version": "1.0.0",
                    "status": "ACTIVE",
                    "created_at_utc": "2026-09-20T00:00:00Z",
                },
                recorded_at_utc="2026-09-20T00:00:00Z",
            )
            append_typed_record(
                ledger_path,
                record_type="skill",
                record_id="SKILL-002",
                payload={
                    "skill_id": "SKILL-002",
                    "name": "Test Skill 2",
                    "description": "Deterministic skill 2",
                    "workflow_steps": ["stepA"],
                    "input_schema": "in.json",
                    "output_schema": "out.json",
                    "version": "1.0.0",
                    "status": "ACTIVE",
                    "created_at_utc": "2026-09-20T00:01:00Z",
                },
                recorded_at_utc="2026-09-20T00:01:00Z",
            )
            self.assertTrue(verify_registry(ledger_path)["valid"])

            # Tamper with first line
            lines = ledger_path.read_text(encoding="utf-8").splitlines()
            rec = json.loads(lines[0])
            rec["payload"]["name"] = "Tampered Name"
            lines[0] = json.dumps(rec)
            ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            verif = verify_registry(ledger_path)
            self.assertFalse(verif["valid"])
            self.assertEqual(verif["reason"], "RECORD_HASH_MISMATCH")

    def test_reconstructible_json_projection(self):
        """7. Test deterministic JSON projection from canonical ledger."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "brain.jsonl"
            json_proj = Path(tmp) / "projection.json"
            append_typed_record(
                ledger_path,
                record_type="open_question",
                record_id="QUEST-001",
                payload={
                    "question_id": "QUEST-001",
                    "question": "What is the true edge?",
                    "context": "BT2 study",
                    "urgency": "HIGH",
                    "status": "OPEN",
                    "resolution_ref": None,
                    "created_at_utc": "2026-09-20T00:00:00Z",
                },
                recorded_at_utc="2026-09-20T00:00:00Z",
            )
            meta = project_to_json(ledger_path, json_proj)
            self.assertEqual(meta["record_count"], 1)
            self.assertTrue(json_proj.is_file())
            loaded = json.loads(json_proj.read_text(encoding="utf-8"))
            self.assertEqual(loaded["record_count"], 1)
            self.assertEqual(loaded["records"][0]["record_id"], "QUEST-001")

    def test_reconstructible_parquet_zstd_projection(self):
        """8. Test reconstructible Parquet ZSTD projection and round-trip parity."""
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "brain.jsonl"
            parquet_path = Path(tmp) / "brain.parquet"
            r1 = append_typed_record(
                ledger_path,
                record_type="repair_action",
                record_id="REPAIR-001",
                payload={
                    "repair_id": "REPAIR-001",
                    "failure_id": "FAIL-001",
                    "description": "Patch timing gap",
                    "changes_made": ["tools/patch.py"],
                    "verified_by_test": True,
                    "status": "VERIFIED",
                    "executed_at_utc": "2026-09-20T00:00:00Z",
                },
                recorded_at_utc="2026-09-20T00:00:00Z",
            )
            meta = project_to_parquet_zstd(ledger_path, parquet_path)
            self.assertEqual(meta["record_count"], 1)
            self.assertTrue(parquet_path.is_file())

            reconstructed = read_parquet_projection(parquet_path)
            self.assertEqual(len(reconstructed), 1)
            self.assertEqual(reconstructed[0]["record_id"], r1["record_id"])
            self.assertEqual(reconstructed[0]["record_hash"], r1["record_hash"])
            self.assertEqual(reconstructed[0]["payload"], r1["payload"])

    def test_precedence_of_source_over_synthesis(self):
        """9. Primary sources supersede synthesis; unresolved conflict blocks promotion."""
        synthesis_with_conflict = {
            "synthesis_id": "SYNTH-001",
            "title": "Synthesis with divergence",
            "summary": "Source A and Source B disagree",
            "source_record_ids": ["SRC-A", "SRC-B"],
            "has_unresolved_conflicts": True,
            "can_promote": True,  # Illegal
            "generated_by": "synthesizer_agent",
            "status": "ACCEPTED",  # Illegal
            "created_at_utc": "2026-09-20T00:00:00Z",
        }
        with self.assertRaises(TypedRegistryError):
            validate_synthesis_promotion(synthesis_with_conflict)

    def test_reconstruction_of_episodes(self):
        """10. Deterministic reconstruction of episode trajectory."""
        hippo = HippocampusMemory()
        ep = AnalysisEpisode(
            episode_id="EPISODE-101",
            goal="Test reconstruction",
            status="IN_PROGRESS",
            recorded_by="agent",
        )
        hippo.register_episode(ep)
        hippo.record_step(
            StepExecution(
                step_id="STEP-1",
                episode_id="EPISODE-101",
                step_index=0,
                action="init_probe",
                tool_name="tool_a",
                status="SUCCESS",
            )
        )
        hippo.record_step(
            StepExecution(
                step_id="STEP-2",
                episode_id="EPISODE-101",
                step_index=1,
                action="measure_response",
                tool_name="tool_b",
                status="SUCCESS",
            )
        )
        hippo.record_expectation(
            Expectation(
                expectation_id="EXP-1",
                episode_id="EPISODE-101",
                statement="Response is positive",
                metric="response_ticks",
                expected_direction="POSITIVE",
            )
        )
        trace = hippo.reconstruct_episode("EPISODE-101")
        self.assertEqual(trace["episode"].episode_id, "EPISODE-101")
        self.assertEqual(len(trace["steps"]), 2)
        self.assertEqual(trace["steps"][0].step_id, "STEP-1")
        self.assertEqual(trace["steps"][1].step_id, "STEP-2")
        self.assertEqual(len(trace["expectations"]), 1)

    def test_deterministic_and_bounded_context_packs(self):
        """11. Context packs are strictly bounded by token budget and deterministically hashed."""
        items = [
            ContextItem("REC-B", "rule", "relevant rule", estimated_tokens=100),
            ContextItem("REC-A", "claim", "relevant claim", estimated_tokens=100),
            ContextItem("REC-C", "lesson", "relevant lesson", estimated_tokens=100),
        ]
        pack = build_deterministic_context_pack(
            context_pack_id="CTX-001",
            episode_id="EPISODE-101",
            token_budget=250,  # Room for only 2 items
            provenance="pilot_pipeline",
            candidates=items,
            created_at_utc="2026-09-20T00:00:00Z",
        )
        # Because REC-A and REC-B come first alphabetically and sum to 200 <= 250, REC-C is dropped
        self.assertEqual(len(pack.items), 2)
        self.assertEqual(pack.items[0].record_id, "REC-A")
        self.assertEqual(pack.items[1].record_id, "REC-B")

        # Hash is deterministic
        h1 = pack.deterministic_hash()
        h2 = pack.deterministic_hash()
        self.assertEqual(h1, h2)

        # Exceeding budget explicitly raises error
        with self.assertRaises(ContextMemoryError):
            pack.add_item(ContextItem("REC-D", "overflow", "too big", estimated_tokens=100))

    def test_undeclared_relations_rejected(self):
        """12. Edges with undeclared relations must be rejected."""
        with self.assertRaises(TypedRegistryError):
            TypedEdge(
                edge_id="EDGE-001",
                source_id="NODE-A",
                target_id="NODE-B",
                relation="MADE_UP_RELATION",
                source_record_id="REC-001",
            )
        # All declared relations must pass
        for rel in [
            "DERIVED_FROM",
            "EXPLAINS",
            "CAUSED_BY",
            "MITIGATED_BY",
            "APPLIES_TO",
            "FAILS_UNDER",
            "REQUIRES",
            "SPECIALIZES",
            "GENERALIZES",
            "TRANSFERS_TO",
            "CO_OCCURRED_WITH",
            "USED_IN",
            "HELPED",
            "HARMED",
            "REQUIRES_REAUDIT",
            "OPERATIONALIZED_AS",
            "NORMALIZES",
            "GATES",
            "CONDITIONS",
            "CONFIRMS",
            "DIVERGES_FROM",
            "REDUNDANT_WITH",
            "COMPLEMENTS",
            "VERSION_OF",
            "SAME_WORK_DIFFERENT_VERSION",
        ]:
            edge = TypedEdge(
                edge_id=f"EDGE-{rel}",
                source_id="NODE-A",
                target_id="NODE-B",
                relation=rel,
                source_record_id="REC-001",
            )
            self.assertEqual(edge.relation, rel)

    def test_no_self_approval(self):
        """13. A model or reviewer cannot approve its own proposal or hypothesis."""
        generator = {
            "model_run_id": "RUN-001",
            "effective_backend": "anthropic",
            "effective_model_id": "claude-3-sonnet",
        }
        reviewer_same_run = {
            "model_run_id": "RUN-001",
            "effective_backend": "anthropic",
            "effective_model_id": "claude-3-sonnet",
        }
        reviewer_same_backend = {
            "model_run_id": "RUN-002",
            "effective_backend": "anthropic",
            "effective_model_id": "claude-3-opus",
        }
        reviewer_independent = {
            "model_run_id": "RUN-003",
            "effective_backend": "google",
            "effective_model_id": "gemini-1.5-pro",
        }

        # Same model_run_id fails
        with self.assertRaises(ModelPolicyViolation):
            validate_independent_review(generator, reviewer_same_run)

        # Same effective backend fails
        with self.assertRaises(ModelPolicyViolation):
            validate_independent_review(generator, reviewer_same_backend)

        # Independent backend passes
        res = validate_independent_review(generator, reviewer_independent)
        self.assertTrue(res["independent_backend"])
        self.assertTrue(res["independent_model"])

    def test_no_silent_reuse_of_invalidated_results(self):
        """14. Invalidation prevents silent reuse of compromised artifacts."""
        hippo = HippocampusMemory()
        edges = [
            DependencyEdge("CLAIM-A", "MC-BROKEN", "MEASURED_BY"),
            DependencyEdge("RULE-B", "CLAIM-A", "DEPENDS_ON"),
        ]
        statuses = propagate_invalidation(["MC-BROKEN"], edges)
        self.assertEqual(statuses["MC-BROKEN"], "INVALIDATED_BY_MEASUREMENT_ERROR")
        self.assertEqual(statuses["CLAIM-A"], "STALE_BY_DEPENDENCY")
        self.assertEqual(statuses["RULE-B"], "STALE_BY_DEPENDENCY")

        # Reusing MC-BROKEN or CLAIM-A must raise InvalidatedArtifactReuseError
        with self.assertRaises(InvalidatedArtifactReuseError):
            hippo.reuse_artifact("MC-BROKEN", statuses)

        with self.assertRaises(InvalidatedArtifactReuseError):
            hippo.reuse_artifact("CLAIM-A", statuses)

        # Unaffected artifact is eligible
        res = hippo.reuse_artifact("CLAIM-UNAFFECTED", statuses)
        self.assertEqual(res["status"], "ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
