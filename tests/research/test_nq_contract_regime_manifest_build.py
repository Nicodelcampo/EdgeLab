import copy
import unittest

from edgelab.research.nq_contract_regime_manifest_build import (
    EVIDENCE_SCHEMA, NQManifestInputError, build_completeness_evidence_template,
    canonical_contract_from_columns, prepare_nq_manifest_inputs,
    validate_trade_calendar)

HASHES = {"NQ 03-26": "a" * 64, "NQ 06-26": "b" * 64}
SOURCE = {"root": "NQ", "dataset": "fixture",
          "contract_parquet_sha256": HASHES, "repo_commit": "c" * 40}
OBS = {
    "NQ 03-26": {20260312: {"volume": 100, "tick_count": 10, "maintenance_tick_count": 0},
                   20260313: {"volume": 400, "tick_count": 20, "maintenance_tick_count": 0},
                   20260316: {"volume": 200, "tick_count": 15, "maintenance_tick_count": 0}},
    "NQ 06-26": {20260313: {"volume": 50, "tick_count": 5, "maintenance_tick_count": 0},
                   20260316: {"volume": 600, "tick_count": 30, "maintenance_tick_count": 0}}}


def evidence():
    return {"schema_version": EVIDENCE_SCHEMA, "source_dataset": "fixture",
            "contract_parquet_sha256": HASHES,
            "calendar_trade_dates": [20260312, 20260313, 20260316, 20260317],
            "sessions": {
                "NQ 03-26": {str(d): {"complete_session": True, "basis": "fixture",
                                      "explicit_zero_volume": False}
                               for d in (20260312, 20260313, 20260316)},
                "NQ 06-26": {str(d): {"complete_session": True, "basis": "fixture",
                                      "explicit_zero_volume": False}
                               for d in (20260313, 20260316)}}, "approved": True}


class ManifestV2Tests(unittest.TestCase):
    def test_internal_identity(self):
        self.assertEqual(canonical_contract_from_columns("NQ", "03-26"), "NQ 03-26")
        with self.assertRaises(NQManifestInputError):
            canonical_contract_from_columns("NQ", "ES 03-26")

    def test_rejects_weekend_calendar(self):
        with self.assertRaisesRegex(NQManifestInputError, "fines de semana"):
            validate_trade_calendar([20260313, 20260314, 20260316])

    def test_template_certifies_nothing_and_quarantines_weekend(self):
        obs = copy.deepcopy(OBS)
        obs["NQ 03-26"][20260315] = {"volume": 1, "tick_count": 1,
                                              "maintenance_tick_count": 0}
        tpl = build_completeness_evidence_template(obs, SOURCE)
        self.assertFalse(tpl["approved"])
        self.assertNotIn(20260315, tpl["calendar_trade_dates"])
        self.assertEqual(tpl["quarantined_observations"][0]["code"],
                         "INVALID_WEEKEND_TRADE_DATE")

    def test_evidence_is_bound_to_hashes(self):
        bad = evidence(); bad["contract_parquet_sha256"] = {**HASHES, "NQ 06-26": "x" * 64}
        with self.assertRaisesRegex(NQManifestInputError, "otros hashes"):
            prepare_nq_manifest_inputs(per_contract_observations=OBS,
                completeness_evidence=bad, source_identity=SOURCE)

    def test_missing_is_not_silent_zero(self):
        obs = copy.deepcopy(OBS); del obs["NQ 03-26"][20260313]
        got = prepare_nq_manifest_inputs(per_contract_observations=obs,
            completeness_evidence=evidence(), source_identity=SOURCE)
        row = next(r for r in got["regime_inputs"]["daily_volumes"]
                   if r["contract"] == "NQ 03-26" and r["trade_date"] == 20260313)
        self.assertEqual(row["volume"], 0.0); self.assertFalse(row["complete_session"])
        self.assertFalse(got["ready_for_certified_manifest"])

    def test_explicit_zero_is_allowed_only_with_evidence(self):
        obs = copy.deepcopy(OBS); del obs["NQ 03-26"][20260313]
        ev = evidence(); ev["sessions"]["NQ 03-26"]["20260313"] = {
            "complete_session": True, "basis": "source-zero", "explicit_zero_volume": True}
        got = prepare_nq_manifest_inputs(per_contract_observations=obs,
            completeness_evidence=ev, source_identity=SOURCE)
        row = next(r for r in got["regime_inputs"]["daily_volumes"]
                   if r["contract"] == "NQ 03-26" and r["trade_date"] == 20260313)
        self.assertEqual(row["volume"], 0.0); self.assertTrue(row["complete_session"])

    def test_maintenance_forces_incomplete(self):
        obs = copy.deepcopy(OBS); obs["NQ 03-26"][20260313]["maintenance_tick_count"] = 2
        got = prepare_nq_manifest_inputs(per_contract_observations=obs,
            completeness_evidence=evidence(), source_identity=SOURCE)
        self.assertIn("MAINTENANCE_TICKS_PRESENT", {d["code"] for d in got["diagnostics"]})
        self.assertFalse(got["ready_for_certified_manifest"])

    def test_complete_inputs_are_ready(self):
        got = prepare_nq_manifest_inputs(per_contract_observations=OBS,
            completeness_evidence=evidence(), source_identity=SOURCE)
        self.assertTrue(got["ready_for_certified_manifest"])
        self.assertEqual(got["regime_inputs"]["calendar_trade_dates"],
                         [20260312, 20260313, 20260316, 20260317])


if __name__ == "__main__":
    unittest.main()
