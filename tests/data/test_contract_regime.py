from __future__ import annotations

import copy
import unittest

from edgelab.data.contract_regime import (
    ContractRegimeError,
    assert_rows_follow_regime,
    assert_run_manifest_uses_regime,
    build_contract_regime,
    contract_for_trade_date,
    validate_contract_regime,
)

CALENDAR = [20260309, 20260310, 20260311, 20260312, 20260313]
CONTRACTS = [
    {
        "root": "NQ", "contract": "NQ_03-26", "expiry_ordinal": 202603,
        "first_trade_date": 20260309, "last_trade_date": 20260313,
    },
    {
        "root": "NQ", "contract": "NQ_06-26", "expiry_ordinal": 202606,
        "first_trade_date": 20260309, "last_trade_date": 20260313,
    },
]


def volume_rows():
    values = {
        20260309: (100, 80),
        20260310: (90, 120),
        20260311: (200, 100),
        20260312: (100, 100),
        20260313: (80, 150),
    }
    rows = []
    for day, (front, back) in values.items():
        rows.extend([
            {"root": "NQ", "contract": "NQ_03-26", "trade_date": day,
             "volume": front, "complete_session": True},
            {"root": "NQ", "contract": "NQ_06-26", "trade_date": day,
             "volume": back, "complete_session": True},
        ])
    return rows


def build(rows=None):
    return build_contract_regime(
        contracts=CONTRACTS,
        daily_volumes=volume_rows() if rows is None else rows,
        calendar_trade_dates=CALENDAR,
        source_identity={"dataset_sha256": "a" * 64, "calendar_sha256": "b" * 64},
    )


def assignments(manifest):
    return {row["trade_date"]: row for row in manifest["daily_assignments"]}


class ContractRegimeTests(unittest.TestCase):
    def test_roll_uses_previous_complete_session_not_same_day(self):
        manifest = build()
        daily = assignments(manifest)
        self.assertEqual(daily[20260309]["decision"], "NO_PRIOR_SESSION")
        self.assertEqual(daily[20260310]["active_contract"], "NQ_03-26")
        self.assertEqual(daily[20260311]["decision"], "ROLL_FORWARD")
        self.assertEqual(daily[20260311]["signal_trade_date"], 20260310)
        self.assertEqual(daily[20260311]["active_contract"], "NQ_06-26")
        self.assertAlmostEqual(daily[20260311]["leader_over_current"], 120 / 90)

    def test_chain_never_rolls_back_and_tie_keeps_current(self):
        daily = assignments(build())
        self.assertEqual(daily[20260312]["active_contract"], "NQ_06-26")
        self.assertEqual(daily[20260312]["decision"], "HOLD")
        self.assertEqual(daily[20260313]["leader_contract"], "NQ_06-26")
        self.assertEqual(daily[20260313]["active_contract"], "NQ_06-26")

    def test_missing_or_incomplete_volume_blocks_next_session(self):
        rows = [r for r in volume_rows() if not (
            r["contract"] == "NQ_06-26" and r["trade_date"] == 20260310
        )]
        daily = assignments(build(rows))
        self.assertFalse(daily[20260311]["eligible"])
        self.assertEqual(daily[20260311]["decision"], "SOURCE_INCOMPLETE")

    def test_intervals_are_half_open_and_final_edge_is_censored(self):
        intervals = build()["intervals"]
        observed = [
            (x["contract"], x["start_trade_date"], x["end_trade_date_exclusive"])
            for x in intervals
        ]
        self.assertEqual(observed, [
            ("NQ_03-26", 20260310, 20260311),
            ("NQ_06-26", 20260311, None),
        ])
        self.assertTrue(intervals[0]["left_censored"])
        self.assertTrue(intervals[-1]["right_censored"])

    def test_downstream_guard_requires_exact_contract_and_manifest_identity(self):
        manifest = build()
        identity = contract_for_trade_date(manifest, "NQ", 20260311)
        good = {"root": "NQ", "trade_date": 20260311, **identity}
        assert_rows_follow_regime([good], manifest)
        bad = {**good, "contract": "NQ_03-26"}
        with self.assertRaisesRegex(ContractRegimeError, "regime mismatch"):
            assert_rows_follow_regime([bad], manifest)

    def test_run_manifest_must_pin_exact_roll_schedule(self):
        manifest = build()
        assert_run_manifest_uses_regime(
            {"roll_schedule_sha256": manifest["manifest_sha256"]}, manifest
        )
        with self.assertRaisesRegex(ContractRegimeError, "roll_schedule_sha256 mismatch"):
            assert_run_manifest_uses_regime(
                {"roll_schedule_sha256": "0" * 64}, manifest
            )

    def test_tampered_manifest_fails_hash_validation(self):
        manifest = copy.deepcopy(build())
        manifest["daily_assignments"][1]["active_contract"] = "NQ_06-26"
        with self.assertRaisesRegex(ContractRegimeError, "hash mismatch"):
            validate_contract_regime(manifest)


if __name__ == "__main__":
    unittest.main()
