import unittest
from edgelab.edge_brain.invalidation import DependencyEdge
from edgelab.edge_brain.triangulation import *
class TriangulationTests(unittest.TestCase):
 def setUp(self):
  self.base=RunContext({"contract":"NQ_03-26","measurement_contract_id":"MC-1","effective_backend":"qwen-local","effective_model_id":"qwen-1"}); self.plan=plan_triangulation("EXP-2",edges=[DependencyEdge("EXP-2","CLAIM-1","DEPENDS_ON")],baseline=self.base)[0]
 def attempt(self,outcome=REPRODUCED,contract="NQ_06-26",mc="MC-2"): return ConfirmationAttempt("ATT-1","CLAIM-1",RunContext({"contract":contract,"measurement_contract_id":mc,"effective_backend":"gemma-local","effective_model_id":"gemma-1"}),outcome,("EVID-1",))
 def test_dependency_creates_plan(self): self.assertEqual(self.plan.prior_claim_id,"CLAIM-1")
 def test_same_measurement_is_not_independent(self): self.assertEqual(evaluate_triangulation(self.plan,[self.attempt(mc="MC-1")]).verdict,INSUFFICIENT)
 def test_reproduction_permits_promotion(self): self.assertTrue(gate_promotion([evaluate_triangulation(self.plan,[self.attempt()])])["may_promote"])
 def test_refutation_blocks_dependent(self): self.assertFalse(gate_promotion([evaluate_triangulation(self.plan,[self.attempt(NOT_REPRODUCED)])])["may_promote"])
 def test_empty_gate_fails_closed(self): self.assertFalse(gate_promotion([])["may_promote"])
