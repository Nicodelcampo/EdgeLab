from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone

from edgelab.data.contract_session_gate import (
    ContractSessionEligibilityGateV2,
    SessionEligibilityResultV2,
    DEFAULT_EQUITY_INDEX_CALENDAR,
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

    def test_default_completeness_is_unknown_and_abstains(self) -> None:
        # Omitting completeness must fail-closed to ABSTAIN
        res = self.gate.evaluate_session(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=500_000,
            volume=550_000,
            tick_count=600_000,
            roll_state="PRE_ROLL",
        )
        self.assertEqual(res.eligibility, "ABSTAIN")
        self.assertEqual(res.completeness, "UNKNOWN")
        self.assertEqual(res.exclusion_reason, "SOURCE_CAPTURE_COMPLETENESS_UNKNOWN")

    def test_normal_equity_session_passes_with_explicit_complete_evidence(self) -> None:
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
            completeness="COMPLETE",
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
            completeness="COMPLETE",
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
            completeness="COMPLETE",
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
            completeness="COMPLETE",
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
            completeness="COMPLETE",
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

    def test_missing_calendar_for_fx_metals_rates_abstains(self) -> None:
        for root in ["6E", "6B", "6J", "GC", "ZB", "MBT"]:
            res = self.gate.evaluate_session(
                root=root,
                trade_date=20260608,
                contract=f"{root}_06-26",
                contract_median_volume=100_000,
                volume=100_000,
                tick_count=100_000,
                completeness="COMPLETE",
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
            completeness="COMPLETE",
        )
        self.assertEqual(res.eligibility, "ABSTAIN")
        self.assertIn("TRADE_DATE_NOT_IN_EQUITY_INDEX_CALENDAR", res.exclusion_reason or "")

    def test_maintenance_window_aggregation_and_exclusion(self) -> None:
        # In Chicago summer (CDT, UTC-5):
        # 16:30 CT = 21:30 UTC.
        # 14:00 CT = 19:00 UTC (regular hours).
        ts_maint = int(datetime(2026, 6, 8, 21, 30, tzinfo=timezone.utc).timestamp() * 1e9)
        ts_reg1 = int(datetime(2026, 6, 8, 19, 0, tzinfo=timezone.utc).timestamp() * 1e9)
        ts_reg2 = int(datetime(2026, 6, 8, 19, 1, tzinfo=timezone.utc).timestamp() * 1e9)

        ts_list = [ts_reg1, ts_maint, ts_reg2]
        vol_list = [50_000, 300_000, 40_000]

        agg = ContractSessionEligibilityGateV2.aggregate_session_ticks(ts_list, vol_list)
        self.assertEqual(agg["regular_tick_count"], 2)
        self.assertEqual(agg["regular_volume"], 90_000)
        self.assertEqual(agg["maintenance_tick_count"], 1)
        self.assertEqual(agg["maintenance_volume"], 300_000)

        # evaluate_session_from_ticks must evaluate only regular volume (90,000)
        res = self.gate.evaluate_session_from_ticks(
            root="NQ",
            trade_date=20260608,
            contract="NQ_06-26",
            contract_median_volume=100_000,
            ts_utc_ns=ts_list,
            volume=vol_list,
            completeness="COMPLETE",
        )
        self.assertEqual(res.volume, 90_000)
        self.assertEqual(res.tick_count, 2)
        self.assertEqual(res.maintenance_tick_count, 1)
        self.assertEqual(res.maintenance_volume, 300_000)

    def test_portable_default_calendar_path(self) -> None:
        self.assertTrue(DEFAULT_EQUITY_INDEX_CALENDAR.name.endswith(".json"))
        self.assertTrue(DEFAULT_EQUITY_INDEX_CALENDAR.is_absolute())
        self.assertTrue(DEFAULT_EQUITY_INDEX_CALENDAR.exists())


if __name__ == "__main__":
    unittest.main()
