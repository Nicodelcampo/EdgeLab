from __future__ import annotations

import copy
import unittest

from edgelab.edge_brain.hippocampus import HippocampusMemory
from edgelab.edge_brain.run_learning_packet import RunLearningPacketError, canonical_packet_sha256, ingest_run_learning_packet


class TestRunLearningPacket(unittest.TestCase):
    def packet(self, verdict: str = "AUTHENTICATED_ENDPOINT_ONLY") -> dict:
        return {
            "packet_type": "RUN-LEARNING-PACKET", "run_id": "CYCLE-001-ACCESS-001",
            "timestamp_utc": "2026-09-21T15:00:00Z", "work_id": "CYCLE-001-C-KAGGLE-ACCESS-001",
            "construct_id": "KAGGLE-ACCESS-CERTIFICATION-V1",
            "observation": {"status": 200, "json_shape_valid": True, "network_error": None},
            "verdict": verdict, "connected": verdict == "AUTHENTICATED_ENDPOINT_ONLY",
            "dataset_verified": False, "hashes_verified": False, "outcomes_inspected": False,
            "holdout_enabled": False, "preexisting_outcome_exposure": True,
            "holdout_contaminated_for_this_hypothesis": True, "promotion_ceiling": "LESSON_CANDIDATE",
            "next_action": "independent review by Agent D",
        }

    def ingest(self, packet: dict, memory: HippocampusMemory | None = None):
        return ingest_run_learning_packet(packet, expected_sha256=canonical_packet_sha256(packet),
                                          source_ref="5a053204304cd2760e284233e53971a2de6afc63", memory=memory)

    def test_access_success_is_operational_not_dataset_evidence(self):
        result = self.ingest(self.packet())
        self.assertEqual(result.authority_status, "OPERATIONAL_OBSERVATION")
        self.assertFalse(result.claims_are_evidence); self.assertFalse(result.dataset_evidence)
        self.assertEqual(result.success_count, 1); self.assertEqual(result.failure_count, 0)
        reconstructed = result.memory.reconstruct_episode(result.episode_id)
        self.assertEqual(reconstructed["lessons"][0].status, "PROPOSED")
        self.assertEqual(reconstructed["lessons"][0].evidence_record_ids, [])

    def test_abstention_and_network_failure_are_remembered(self):
        packet = self.packet("ABSTAIN_AUTH_OR_ENDPOINT"); packet["connected"] = False
        packet["observation"] = {"status": 400, "json_shape_valid": False, "network_error": None}
        result = self.ingest(packet)
        self.assertEqual(result.failure_count, 1)
        self.assertIn("ABSTAIN_AUTH_OR_ENDPOINT", result.memory.reconstruct_episode(result.episode_id)["failures"][0].error_type)

    def test_access_probe_cannot_claim_dataset_verification(self):
        packet = self.packet(); packet["dataset_verified"] = True; packet["hashes_verified"] = True
        packet["dataset_hashes"] = ["a" * 64]; packet["dataset_manifest_ref"] = "manifest.json"
        with self.assertRaisesRegex(RunLearningPacketError, "access/authentication"): self.ingest(packet)

    def test_hash_mismatch_and_secret_keys_fail_closed(self):
        packet = self.packet()
        with self.assertRaisesRegex(RunLearningPacketError, "SHA-256 mismatch"):
            ingest_run_learning_packet(packet, expected_sha256="0" * 64, source_ref="5a053204")
        secret_packet = self.packet(); secret_packet["observation"]["authorization"] = "forbidden"
        with self.assertRaisesRegex(RunLearningPacketError, "secret-bearing"): self.ingest(secret_packet)

    def test_outcomes_holdout_and_self_promotion_fail_closed(self):
        for field in ("outcomes_inspected", "holdout_enabled"):
            packet = self.packet(); packet[field] = True
            with self.assertRaises(RunLearningPacketError): self.ingest(packet)
        packet = self.packet(); packet["claims_are_evidence"] = True
        with self.assertRaisesRegex(RunLearningPacketError, "self-promote"): self.ingest(packet)

    def test_duplicate_run_id_is_rejected_by_hippocampus(self):
        memory = HippocampusMemory(); packet = self.packet(); self.ingest(packet, memory)
        with self.assertRaisesRegex(ValueError, "already exists"): self.ingest(packet, memory)

    def test_measurement_invalid_becomes_counterexample(self):
        packet = self.packet("MEASUREMENT_INVALID"); packet["run_id"] = "CYCLE-001-MEASUREMENT-INVALID-001"
        packet["construct_id"] = "VIEWER-AVAILABLE-AT-V1"; packet["connected"] = False
        packet["measurement_status"] = "MEASUREMENT_INVALID"
        packet["measurement_failure"] = "display_bar_key was used as formation_spec"
        result = self.ingest(packet)
        self.assertEqual(result.failure_count, 1); self.assertEqual(result.counterexample_count, 1)
        counterexample = result.memory.counterexamples[packet["construct_id"]][0]
        self.assertIn("display_bar_key", counterexample.why_it_violates)
        self.assertTrue(counterexample.evidence_ref.startswith("sha256:"))

    def test_projection_is_deterministic_across_fresh_memories(self):
        packet = self.packet()
        self.assertEqual(self.ingest(copy.deepcopy(packet)).projection(), self.ingest(copy.deepcopy(packet)).projection())


if __name__ == "__main__": unittest.main()
