"""Foundational, target-free primitives for the Edge Discovery Brain."""
from .coverage import CoverageCell, build_coverage_artifact, build_coverage_mask, verify_coverage_artifact
from .eligibility import AnalysisRequest, EligibilityDecision, evaluate_eligibility
from .model_policy import ModelPolicyViolation, assert_non_evidentiary_status, validate_independent_review
from .invalidation import DependencyEdge, propagate_invalidation
from .registry import LedgerIntegrityError, append_record, content_sha256, verify_registry
from .schema_validator import validate_record
from .triangulation import ConfirmationAttempt, RunContext, TriangulationPlan, evaluate_triangulation, gate_promotion, plan_triangulation
from .typed_registry import (
    TYPED_RELATIONS,
    TypedEdge,
    TypedRegistryError,
    append_typed_record,
    project_to_json,
    project_to_parquet_zstd,
    read_parquet_projection,
    validate_synthesis_promotion,
)
from .hippocampus import (
    AnalysisEpisode,
    Counterexample,
    Expectation,
    FailureEvent,
    HippocampusError,
    HippocampusMemory,
    InvalidatedArtifactReuseError,
    LessonCandidate,
    RepairAction,
    StepExecution,
    SuccessEvent,
)
from .context_memory import (
    ContextItem,
    ContextMemoryError,
    ContextPack,
    build_deterministic_context_pack,
)
from .measurement_atlas import (
    AtlasValidationError,
    validate_atlas,
    validate_composition,
    validate_indicator,
)

__all__ = [
    "AnalysisEpisode",
    "AnalysisRequest",
    "AtlasValidationError",
    "ConfirmationAttempt",
    "ContextItem",
    "ContextMemoryError",
    "ContextPack",
    "Counterexample",
    "CoverageCell",
    "DependencyEdge",
    "EligibilityDecision",
    "Expectation",
    "FailureEvent",
    "HippocampusError",
    "HippocampusMemory",
    "InvalidatedArtifactReuseError",
    "LedgerIntegrityError",
    "LessonCandidate",
    "ModelPolicyViolation",
    "RepairAction",
    "RunContext",
    "StepExecution",
    "SuccessEvent",
    "TYPED_RELATIONS",
    "TriangulationPlan",
    "TypedEdge",
    "TypedRegistryError",
    "append_record",
    "append_typed_record",
    "assert_non_evidentiary_status",
    "build_coverage_artifact",
    "build_coverage_mask",
    "build_deterministic_context_pack",
    "content_sha256",
    "evaluate_eligibility",
    "evaluate_triangulation",
    "gate_promotion",
    "plan_triangulation",
    "project_to_json",
    "project_to_parquet_zstd",
    "propagate_invalidation",
    "read_parquet_projection",
    "validate_atlas",
    "validate_composition",
    "validate_independent_review",
    "validate_indicator",
    "validate_record",
    "validate_synthesis_promotion",
    "verify_coverage_artifact",
    "verify_registry",
]
