import unittest
from edgelab.edge_brain.coverage import *
from edgelab.edge_brain.eligibility import *
class CoverageTests(unittest.TestCase):
 def cells(self): return build_coverage_mask(universe=[("NQ","NQ_03-26","2026-03"),("NQ","NQ_06-26","2026-06")],observations={("NQ","NQ_03-26","2026-03"):{"observed_active_minutes":1300,"evidence_ref":"ART-1"}},expected={("NQ","NQ_03-26","2026-03"):1380,("NQ","NQ_06-26","2026-06"):1380})
 def test_missing_is_not_zero(self):
  c=self.cells()[1]; self.assertEqual(c.state,EXPECTED_BUT_MISSING); self.assertIsNone(c.observed_active_minutes)
  with self.assertRaises(ZeroFillViolation): assert_not_zero_fill(c.state,0)
 def test_denominator_fails_closed(self):
  with self.assertRaises(ZeroFillViolation): active_denominator(self.cells())
  self.assertEqual(active_denominator(self.cells(),acknowledge_expected_missing=True),1)
 def test_artifact_hash_detects_tamper(self):
  a=build_coverage_artifact(self.cells(),created_at_utc="2026-09-19T18:00:00Z",holdout_boundary_ns=1782856800000000000,code_commit="8919a3b"); self.assertTrue(verify_coverage_artifact(a)); a["cells"][0]["state"]=OBSERVED; self.assertFalse(verify_coverage_artifact(a))
 def test_roll_gate_only_blocks_continuous_analysis(self):
  c=self.cells(); a=build_coverage_artifact(c,created_at_utc="2026-09-19T18:00:00Z",holdout_boundary_ns=1782856800000000000,code_commit="8919a3b"); q=AnalysisRequest("A","contract_month",False,False,("NQ_03-26",),("2026-03",),a["coverage_artifact_id"]); self.assertTrue(evaluate_eligibility(q,coverage_artifact=a,cells=c).may_run); q=AnalysisRequest("B","continuous_series",True,True,("NQ_03-26",),("2026-03",),a["coverage_artifact_id"]); self.assertEqual(evaluate_eligibility(q,coverage_artifact=a,cells=c).verdict,ABSTAIN_MISSING_CERTIFIED_ROLL)
 def test_gap_must_be_declared(self):
  c=self.cells(); a=build_coverage_artifact(c,created_at_utc="2026-09-19T18:00:00Z",holdout_boundary_ns=1782856800000000000,code_commit="8919a3b"); q=AnalysisRequest("A","contract_month",False,False,("NQ_03-26","NQ_06-26"),("2026-03","2026-06"),a["coverage_artifact_id"]); self.assertEqual(evaluate_eligibility(q,coverage_artifact=a,cells=c).verdict,ABSTAIN_INSUFFICIENT_COVERAGE)
