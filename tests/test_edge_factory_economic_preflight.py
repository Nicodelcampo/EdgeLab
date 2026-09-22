from __future__ import annotations

import json
import unittest
from pathlib import Path

from edgelab.edge_factory.economic_preflight import (
    HOLDOUT_BOUNDARY_NS,
    EconomicPreflightError,
    assert_economic_campaign_executable,
    evaluate_economic_campaign,
)


class TestEconomicPreflight(unittest.TestCase):
    def _valid(self):
        return {
            "campaign_id": "CAMP-BT2A-001",
            "holdout_boundary_ns": HOLDOUT_BOUNDARY_NS,
            "discovery_end_ns": HOLDOUT_BOUNDARY_NS - 2,
            "validation_end_ns": HOLDOUT_BOUNDARY_NS - 1,
            "input_hashes": ["a" * 64],
            "signal_semantics": {
                "status": "CERTIFIED",
                "formation_spec": {"kind": "tick_count", "value": 25},
                "available_at_contract": "LAST_TICK_OF_FORMATION_BUCKET",
            },
            "fill_policy": {"provenance": "OBSERVED_FIRST_EXECUTABLE_TICK_OR_ABSTAIN"},
            "cost_model": {
                "commission_roundturn": 1.0,
                "exchange_fees_roundturn": 1.0,
                "spread_ticks": 1,
                "slippage_ticks_base": 1,
                "slippage_ticks_stress": [2, 3],
                "latency_model": "EMPIRICAL_OR_PREREGISTERED_FIXED",
            },
            "multiplicity": {
                "family_id": "FAM-BT2A-001",
                "effective_hypothesis_count": 15,
                "correction_method": "HOLM_AND_BH_FDR",
            },
            "outcomes_enabled": True,
            "human_authorized": True,
        }

    def test_valid_manifest_passes(self):
        report = assert_economic_campaign_executable(self._valid())
        self.assertTrue(report.executable)
        self.assertEqual(report.blockers, ())

    def test_current_state_is_fail_closed(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads(
            (root / "config" / "edge_factory" / "ym_bt2a_economic_campaign_blocked_20260920.json").read_text(
                encoding="utf-8"
            )
        )
        report = evaluate_economic_campaign(manifest)
        self.assertFalse(report.executable)
        self.assertEqual(set(report.blockers), set(manifest["expected_blockers"]))
        with self.assertRaises(EconomicPreflightError):
            assert_economic_campaign_executable(manifest)

    def test_holdout_boundary_is_rejected(self):
        manifest = self._valid()
        manifest["validation_end_ns"] = HOLDOUT_BOUNDARY_NS
        report = evaluate_economic_campaign(manifest)
        self.assertIn("VALIDATION_WINDOW_NOT_STRICTLY_PREHOLDOUT", report.blockers)

    def test_incomplete_cost_model_is_rejected(self):
        manifest = self._valid()
        manifest["cost_model"].pop("latency_model")
        report = evaluate_economic_campaign(manifest)
        self.assertTrue(any(b.startswith("COST_MODEL_INCOMPLETE") for b in report.blockers))

    def test_placeholder_costs_are_rejected(self):
        manifest = self._valid()
        manifest["cost_model"]["commission_roundturn"] = "TO_FREEZE_BY_CONTRACT"
        manifest["cost_model"]["latency_model"] = "TO_PREREGISTER"
        report = evaluate_economic_campaign(manifest)
        self.assertIn("COST_COMPONENT_INVALID:commission_roundturn", report.blockers)
        self.assertIn("COST_COMPONENT_INVALID:latency_model", report.blockers)

    def test_synthetic_fill_policy_is_rejected(self):
        manifest = self._valid()
        manifest["fill_policy"] = {"provenance": "SYNTHETIC_FIXED_250MS"}
        report = evaluate_economic_campaign(manifest)
        self.assertIn("FILL_POLICY_NOT_OBSERVED_OR_ABSTAIN", report.blockers)


if __name__ == "__main__":
    unittest.main()
