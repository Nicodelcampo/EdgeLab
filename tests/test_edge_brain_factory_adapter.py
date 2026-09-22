from __future__ import annotations

import json
import unittest
from pathlib import Path

from edgelab.edge_brain.factory_adapter import (
    FactoryAdapterError,
    adapt_target_free_zone_event,
    build_target_free_episode_records,
)


class TestEdgeBrainFactoryAdapter(unittest.TestCase):
    def _row(self):
        return {
            "zone_id": "BT2A-001",
            "formation_start_ns": 1_780_000_000_000_000_000,
            "formation_end_ns": 1_780_000_001_000_000_000,
            "available_at_ns": 1_780_000_001_000_000_000,
            "formation_spec": {"kind": "tick_count", "value": 25},
            "display_bar_key": "time_5m",
            "source_sha256": "a" * 64,
        }

    def test_display_bar_key_cannot_replace_formation_spec(self):
        row = self._row()
        row.pop("formation_spec")
        row["bar_key"] = "time_5m"
        with self.assertRaises(FactoryAdapterError):
            adapt_target_free_zone_event(row)

    def test_target_free_event_preserves_no_fill(self):
        event = adapt_target_free_zone_event(self._row())
        self.assertEqual(event.formation_spec, {"kind": "tick_count", "value": 25})
        self.assertEqual(event.display_bar_key, "time_5m")
        self.assertIsNone(event.executable_fill_ns)
        self.assertEqual(event.executable_fill_status, "NO_EXECUTABLE_FILL_AVAILABLE")

    def test_synthetic_fill_is_rejected(self):
        row = self._row()
        row["executable_fill_ts"] = row["available_at_ns"] + 1
        row["executable_fill_origin"] = "SYNTHETIC_250MS"
        with self.assertRaises(FactoryAdapterError):
            adapt_target_free_zone_event(row)

    def test_outcome_leak_is_rejected(self):
        row = self._row()
        row["mfe"] = 12.0
        with self.assertRaises(FactoryAdapterError):
            adapt_target_free_zone_event(row)

    def test_episode_plan_materializes_typed_records(self):
        root = Path(__file__).resolve().parents[1]
        plan = json.loads(
            (root / "config" / "edge_brain" / "ym_bt2a_target_free_episode_plan_20260920.json").read_text(
                encoding="utf-8"
            )
        )
        records = build_target_free_episode_records(
            plan,
            recorded_at_utc="2026-09-21T01:40:00Z",
            recorded_by="notion-ai-audit",
        )
        self.assertFalse(records["analysis_episode"]["outcomes_inspected"])
        self.assertEqual(len(records["step_executions"]), 7)
        self.assertEqual(records["expectations"][0]["expected_direction"], "NEUTRAL")


if __name__ == "__main__":
    unittest.main()
