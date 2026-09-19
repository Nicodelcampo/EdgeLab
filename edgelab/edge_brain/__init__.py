"""Foundational, target-free primitives for the Edge Discovery Brain."""
from .coverage import CoverageCell, build_coverage_artifact, build_coverage_mask, verify_coverage_artifact
from .eligibility import AnalysisRequest, EligibilityDecision, evaluate_eligibility
from .model_policy import ModelPolicyViolation, assert_non_evidentiary_status, validate_independent_review
from .invalidation import DependencyEdge, propagate_invalidation
from .registry import LedgerIntegrityError, append_record, content_sha256, verify_registry
from .schema_validator import validate_record
from .triangulation import ConfirmationAttempt, RunContext, TriangulationPlan, evaluate_triangulation, gate_promotion, plan_triangulation
__all__=["AnalysisRequest","ConfirmationAttempt","CoverageCell","DependencyEdge","EligibilityDecision","LedgerIntegrityError","ModelPolicyViolation","RunContext","TriangulationPlan","append_record","assert_non_evidentiary_status","build_coverage_artifact","build_coverage_mask","content_sha256","evaluate_eligibility","evaluate_triangulation","gate_promotion","plan_triangulation","propagate_invalidation","validate_independent_review","validate_record","verify_coverage_artifact","verify_registry"]
