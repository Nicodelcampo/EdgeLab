import unittest
from edgelab.data.cme_equity_index_calendar import (
    CalendarEvidenceError, assert_source_capture_evidence, build_calendar)

EVIDENCE = [{"url": "https://www.cmegroup.com/trading-hours.html",
             "sha256": "a" * 64, "retrieved_at": "2026-09-02T04:00:00Z"}]


class CalendarTests(unittest.TestCase):
    def test_normal_weekday_and_weekend(self):
        got = build_calendar(start_trade_date=20260306, end_trade_date=20260309,
            holiday_review_dates=[], holiday_overrides=[],
            default_hours_evidence=EVIDENCE, source_capture_policy_id="fixture")
        by_day = {x["trade_date"]: x for x in got["sessions"]}
        self.assertEqual(by_day[20260306]["session_class"], "NORMAL")
        self.assertEqual(by_day[20260307]["session_class"], "CLOSED")
        self.assertFalse(got["source_capture_complete_inferred"])

    def test_review_date_requires_override(self):
        with self.assertRaisesRegex(CalendarEvidenceError, "sin override"):
            build_calendar(start_trade_date=20260119, end_trade_date=20260119,
                holiday_review_dates=[20260119], holiday_overrides=[],
                default_hours_evidence=EVIDENCE, source_capture_policy_id="fixture")

    def test_early_close_is_explicit(self):
        override = {"trade_date": 20260119, "session_class": "EARLY_CLOSE",
            "expected_open_ct": "2026-01-18T17:00:00-06:00",
            "expected_close_ct": "2026-01-19T12:00:00-06:00",
            "holiday_name": "MLK", "evidence": EVIDENCE}
        got = build_calendar(start_trade_date=20260119, end_trade_date=20260119,
            holiday_review_dates=[20260119], holiday_overrides=[override],
            default_hours_evidence=EVIDENCE, source_capture_policy_id="fixture")
        self.assertEqual(got["sessions"][0]["session_class"], "EARLY_CLOSE")

    def test_calendar_does_not_prove_capture(self):
        with self.assertRaisesRegex(CalendarEvidenceError, "particiones"):
            assert_source_capture_evidence({"trade_date": 20260119, "contract": "NQ 03-26",
                "source_partitions_expected": ["a", "b"], "source_partitions_present": ["a"],
                "extraction_status": "COMPLETE", "source_sha256": "b" * 64})


if __name__ == "__main__":
    unittest.main()
