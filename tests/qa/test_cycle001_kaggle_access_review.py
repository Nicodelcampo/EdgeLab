"""Adversarial review of CYCLE-001 Kaggle access contract.

These tests express the declared fail-closed contract. Failures are review
findings, not authorization to access Kaggle or any dataset.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "kaggle_access_probe.py"
SPEC = importlib.util.spec_from_file_location("kaggle_access_probe", MODULE_PATH)
probe = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class KaggleAccessAdversarialReview(unittest.TestCase):
    def test_200_cannot_authenticate_from_unverified_boolean_alone(self):
        """A caller-supplied True is not independent JSON-shape validation."""
        observation = probe.ProbeObservation(status=200, json_shape_valid=True)
        verdict, connected = probe.classify(observation)
        self.assertNotEqual(verdict, "AUTHENTICATED_ENDPOINT_ONLY")
        self.assertFalse(connected)

    def test_network_error_cannot_emit_secret_bearing_text(self):
        """Exception strings can contain URLs, headers or query-token values."""
        observation = probe.ProbeObservation(
            status=None,
            json_shape_valid=False,
            network_error="Authorization: Bearer KGAT_REDACT_ME",
        )
        with self.assertRaises(ValueError):
            probe.learning_packet(observation, "ADVERSARIAL-SECRET-STRING")

    def test_secret_key_normalization_rejects_whitespace_and_hyphens(self):
        for key in ("Authorization ", "api-key", "Kaggle-Api-Token"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                probe.assert_redacted({key: "redacted"})

    def test_access_packet_never_promotes_dataset_or_holdout(self):
        packet = probe.learning_packet(
            probe.ProbeObservation(200, True), "ADVERSARIAL-GATES"
        )
        self.assertIs(packet["dataset_verified"], False)
        self.assertIs(packet["hashes_verified"], False)
        self.assertIs(packet["outcomes_inspected"], False)
        self.assertIs(packet["holdout_enabled"], False)
        self.assertEqual(packet["promotion_ceiling"], "LESSON_CANDIDATE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
