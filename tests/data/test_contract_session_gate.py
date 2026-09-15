from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from edgelab.data.contract_session_gate import (
    ContractSessionEligibilityGateV2,
    SessionEligibilityResultV2,
)


class ContractSessionEligibilityGateV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cal_path = Path(self.temp_dir.name) / "test_calendar.json"

        # Mock equity calendar
        test_cal = {
            "schema_version": "cme_equity_index_session_calendar_v1",
            "sessions": [
                {
                    "trade_date": 20260608,
                    "session_class": "NORMAL",
                    "expected_open_ct": "2026-06-07T17:00:00-05:00",
                    "expected_close_ct": "2026-06-08T16:00:00-05:00",
                    "holiday_name": None,
                },
                {
                    "trade_date": 20260525,
                    "session_class": "EARLY_CLOSE",
                    "expected_open_ct": "2026-05-24T17:00:00-05:00",
                    "expected_close_ct": "2026-05-25T12:00:00-05:00",
                    "holiday_name": "MEMORIAL_DAY",
                },
                {
                    "trade_date": 20251225,
                    "session_class": "CLOSED",
                    "expected_open_ct": None,
                    "expected_close_ct": None,
                    "holiday_name": "CHRISTMAS_DAY",
                },
            ],
        }
        with open(self.cal_path, "w", encoding="utf-8") as f:
            json.dump(test_cal, f)

        self.gate = ContractSessionEligibilityGateV2(
            calendars={"EQUITY_INDEX": self.cal_path}
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_normal_equity_session_passes(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=550_000,
            tick_count=600_000,
            roll_state="PRE_ROLL",
            completeness="COMPLETE",
        )
        self.assertEqual(res.eligibility, "PASS")
        self.assertIsNone(res.exclusion_reason)
        self.assertTrue(res.calendar_valid)
        self.assertEqual(res.session_class, "NORMAL")

    def test_market_closed_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20251225,
            contract="NQ_12-25",
            contract_median_volume=500_000,
            volume=0,
            tick_count=0,
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertIn("MARKET_CLOSED_CHRISTMAS_DAY", res.exclusion_reason or "")

    def test_early_close_holiday_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260525,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=120_000,
            tick_count=100_000,
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertIn("EARLY_CLOSE_HOLIDAY_MEMORIAL_DAY", res.exclusion_reason or "")

    def test_low_volume_ratio_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=150_000,  # 30% < 50%
            tick_count=100_000,
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertIn("LOW_VOLUME_RATIO", res.exclusion_reason or "")

    def test_insufficient_ticks_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=400_000,
            tick_count=20_000,  # < 50,000
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertIn("INSUFFICIENT_TICKS", res.exclusion_reason or "")

    def test_post_roll_state_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=500_000,
            tick_count=500_000,
            roll_state="POST_ROLL",
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertEqual(res.exclusion_reason, "POST_ROLL_CONTRACT_EXPIRED_OR_ILLIQUID")

    def test_incomplete_source_capture_fails(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=500_000,
            tick_count=500_000,
            completeness="INCOMPLETE",
        )
        self.assertEqual(res.eligibility, "FAIL")
        self.assertEqual(res.exclusion_reason, "INCOMPLETE_SOURCE_CAPTURE")

    def test_unknown_source_capture_abstains(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=500_000,
            tick_count=500_000,
            completeness="UNKNOWN",
        )
        self.assertEqual(res.eligibility, "ABSTAIN")
        self.assertEqual(res.exclusion_reason, "SOURCE_CAPTURE_COMPLETENESS_UNKNOWN")

    def test_missing_calendar_for_fx_metals_rates_abstains(self) -> None:
        for root in ["6E", "6B", "6J", "GC", "ZB", "MBT"]:
            res = self.gate.evaluate_session(
                root=root,
                trade_date=20260608,
                contract=f"{root}_06-26",
                contract_median_volume=100_000,
                volume=100_000,
                tick_count=100_000,
            )
            self.assertEqual(res.eligibility, "ABSTAIN")
            self.assertIn("NO_OFFICIAL_CALENDAR_EVIDENCE", res.exclusion_reason or "")

    def test_unknown_trade_date_in_known_calendar_abstains(self) -> None:
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260609,  # Not in mock calendar
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=500_000,
            tick_count=500_000,
        )
        self.assertEqual(res.eligibility, "ABSTAIN")
        self.assertIn("TRADE_DATE_NOT_IN_EQUITY_INDEX_CALENDAR", res.exclusion_reason or "")

    def test_maintenance_window_detection(self) -> None:
        self.assertTrue(ContractSessionEligibilityGateV2.is_maintenance_window_ct(16, 0))
        self.assertTrue(ContractSessionEligibilityGateV2.is_maintenance_window_ct(16, 30))
        self.assertTrue(ContractSessionEligibilityGateV2.is_maintenance_window_ct(16, 59))
        self.assertFalse(ContractSessionEligibilityGateV2.is_maintenance_window_ct(15, 59))
        self.assertFalse(ContractSessionEligibilityGateV2.is_maintenance_window_ct(17, 0))


if __name__ == "__main__":
    unittest.main()
