"""Policy checks for non-evidentiary model runs and independent review."""
from __future__ import annotations
ACCEPTED_AS_NON_EVIDENTIARY_ARTIFACT="ACCEPTED_AS_NON_EVIDENTIARY_ARTIFACT"
VALID_STATUSES=frozenset({"PROPOSED","SCHEMA_VALID","REQUIRES_ADVERSARIAL_REVIEW","REJECTED",ACCEPTED_AS_NON_EVIDENTIARY_ARTIFACT})
class ModelPolicyViolation(ValueError): pass
def validate_independent_review(generator:dict,reviewer:dict)->dict:
 """A router label is irrelevant; independence uses the effective backend."""
 if generator["model_run_id"]==reviewer["model_run_id"]: raise ModelPolicyViolation("generator_model_run_id must differ from reviewer_model_run_id")
 if generator["effective_backend"]==reviewer["effective_backend"]: raise ModelPolicyViolation("generator_effective_backend must differ from reviewer_effective_backend")
 distinct_model=generator["effective_model_id"]!=reviewer["effective_model_id"]
 return {"independent_backend":True,"independent_model":distinct_model,"preferred_independence_satisfied":distinct_model}
def assert_non_evidentiary_status(run:dict)->None:
 status=run.get("review_status")
 if status not in VALID_STATUSES: raise ModelPolicyViolation(f"forbidden model-run status: {status}")
