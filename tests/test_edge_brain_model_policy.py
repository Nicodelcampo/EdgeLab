import unittest
from edgelab.edge_brain.model_policy import *
class ModelPolicyTests(unittest.TestCase):
 def sample(self,run_id,backend,model): return {"model_run_id":run_id,"effective_backend":backend,"effective_model_id":model,"review_status":"REQUIRES_ADVERSARIAL_REVIEW"}
 def test_router_names_do_not_define_independence(self): self.assertTrue(validate_independent_review(self.sample("MRUN-g","a","m1"),self.sample("MRUN-r","b","m2"))["preferred_independence_satisfied"])
 def test_same_effective_backend_is_rejected(self):
  with self.assertRaises(ModelPolicyViolation): validate_independent_review(self.sample("MRUN-g","qwen","a"),self.sample("MRUN-r","qwen","b"))
 def test_same_run_cannot_review_itself(self):
  with self.assertRaises(ModelPolicyViolation): validate_independent_review(self.sample("MRUN-x","a","m1"),self.sample("MRUN-x","b","m2"))
 def test_validated_result_is_forbidden(self):
  with self.assertRaises(ModelPolicyViolation): assert_non_evidentiary_status({"review_status":"VALIDATED_RESULT"})
