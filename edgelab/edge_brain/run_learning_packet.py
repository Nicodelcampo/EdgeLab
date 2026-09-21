from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from .hippocampus import (
    AnalysisEpisode,
    Counterexample,
    FailureEvent,
    HippocampusMemory,
    LessonCandidate,
    StepExecution,
    SuccessEvent,
)


class RunLearningPacketError(ValueError):
    """Raised when a run learning packet violates evidence or safety gates."""


_REQUIRED_FIELDS = {
    "packet_type", "run_id", "timestamp_utc", "work_id", "construct_id", "verdict",
    "dataset_verified", "hashes_verified", "outcomes_inspected", "holdout_enabled",
    "preexisting_outcome_exposure", "holdout_contaminated_for_this_hypothesis",
    "promotion_ceiling", "next_action",
}
_SECRET_KEYS = {"token", "api_token", "api_key", "authorization", "kaggle_api_token", "password", "secret"}
_MEASUREMENT_STATUSES = {"MEASURES_AS_INTENDED", "PROXY_ONLY", "MEASUREMENT_INVALID", "AMBIGUOUS_MEASUREMENT"}
_FAILURE_MARKERS = ("ABSTAIN", "ERROR", "FAIL", "CRASH", "TIMEOUT", "INVALID", "AMBIGUOUS")


def canonical_packet_sha256(packet: dict[str, Any]) -> str:
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _assert_no_secret_keys(value: Any, path: str = "packet") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in _SECRET_KEYS or normalized.endswith("_secret"):
                raise RunLearningPacketError(f"secret-bearing key forbidden at {path}.{key}")
            _assert_no_secret_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secret_keys(child, f"{path}[{index}]")


def _require_nonempty_string(packet: dict[str, Any], field: str) -> str:
    value = packet.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RunLearningPacketError(f"{field} must be a non-empty string")
    return value.strip()


def validate_run_learning_packet(packet: dict[str, Any], *, expected_sha256: str, source_ref: str) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise RunLearningPacketError("packet must be an object")
    missing = sorted(_REQUIRED_FIELDS - packet.keys())
    if missing:
        raise RunLearningPacketError(f"missing required fields: {missing}")
    _assert_no_secret_keys(packet)
    if packet.get("packet_type") != "RUN-LEARNING-PACKET":
        raise RunLearningPacketError("packet_type must be RUN-LEARNING-PACKET")
    for field in ("run_id", "timestamp_utc", "work_id", "construct_id", "verdict", "next_action"):
        _require_nonempty_string(packet, field)
    if not isinstance(source_ref, str) or len(source_ref.strip()) < 7:
        raise RunLearningPacketError("source_ref must identify a commit or immutable artifact")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256 or ""):
        raise RunLearningPacketError("expected_sha256 must be a lowercase SHA-256")
    observed_sha256 = canonical_packet_sha256(packet)
    if observed_sha256 != expected_sha256:
        raise RunLearningPacketError("packet SHA-256 mismatch")
    bool_fields = (
        "dataset_verified", "hashes_verified", "outcomes_inspected", "holdout_enabled",
        "preexisting_outcome_exposure", "holdout_contaminated_for_this_hypothesis",
    )
    for field in bool_fields:
        if type(packet.get(field)) is not bool:
            raise RunLearningPacketError(f"{field} must be boolean")
    if packet["outcomes_inspected"]:
        raise RunLearningPacketError("outcomes_inspected must remain false")
    if packet["holdout_enabled"]:
        raise RunLearningPacketError("holdout_enabled must remain false")
    if packet.get("promotion_ceiling") != "LESSON_CANDIDATE":
        raise RunLearningPacketError("promotion_ceiling cannot exceed LESSON_CANDIDATE")
    if packet.get("claims_are_evidence") is True:
        raise RunLearningPacketError("run packets cannot self-promote claims to evidence")
    construct_id = str(packet["construct_id"])
    is_access_probe = "ACCESS" in construct_id.upper() or "AUTH" in construct_id.upper()
    if is_access_probe and packet["dataset_verified"]:
        raise RunLearningPacketError("access/authentication cannot verify a dataset")
    if packet["hashes_verified"] and not packet["dataset_verified"]:
        raise RunLearningPacketError("hashes_verified requires dataset_verified")
    if packet["dataset_verified"]:
        hashes = packet.get("dataset_hashes")
        manifest_ref = packet.get("dataset_manifest_ref")
        if not isinstance(hashes, list) or not hashes:
            raise RunLearningPacketError("dataset_verified requires dataset_hashes")
        if not isinstance(manifest_ref, str) or not manifest_ref.strip():
            raise RunLearningPacketError("dataset_verified requires dataset_manifest_ref")
    measurement_status = packet.get("measurement_status")
    if measurement_status is not None and measurement_status not in _MEASUREMENT_STATUSES:
        raise RunLearningPacketError(f"unsupported measurement_status: {measurement_status}")
    verdict = str(packet["verdict"]).upper()
    connected = packet.get("connected")
    if connected is not None and type(connected) is not bool:
        raise RunLearningPacketError("connected must be boolean when present")
    if connected is True and "AUTHENTICATED" not in verdict:
        raise RunLearningPacketError("connected=true requires an authenticated verdict")
    authority_status = "OPERATIONAL_OBSERVATION" if is_access_probe else "RUN_OBSERVATION_UNADJUDICATED"
    return {
        "packet_sha256": observed_sha256,
        "source_ref": source_ref.strip(),
        "authority_status": authority_status,
        "claims_are_evidence": False,
        "dataset_evidence": bool(packet["dataset_verified"] and packet["hashes_verified"]),
    }


@dataclass(frozen=True)
class RunLearningIngestion:
    episode_id: str
    run_id: str
    packet_sha256: str
    source_ref: str
    authority_status: str
    verdict: str
    measurement_status: str | None
    claims_are_evidence: bool
    dataset_evidence: bool
    failure_count: int
    success_count: int
    lesson_count: int
    counterexample_count: int
    memory: HippocampusMemory

    def projection(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if key != "memory"}


def ingest_run_learning_packet(
    packet: dict[str, Any], *, expected_sha256: str, source_ref: str,
    memory: HippocampusMemory | None = None,
) -> RunLearningIngestion:
    validation = validate_run_learning_packet(packet, expected_sha256=expected_sha256, source_ref=source_ref)
    target = memory or HippocampusMemory()
    run_id = str(packet["run_id"])
    stable = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]
    episode_id = f"EPISODE-RUN-{stable}"
    verdict = str(packet["verdict"])
    measurement_status = packet.get("measurement_status")
    is_failure = any(marker in verdict.upper() for marker in _FAILURE_MARKERS) or measurement_status in {
        "MEASUREMENT_INVALID", "AMBIGUOUS_MEASUREMENT",
    }
    target.register_episode(AnalysisEpisode(
        episode_id=episode_id,
        goal=f"Learn from run {run_id} without self-promoting its claims",
        status="ABSTAINED" if is_failure else "COMPLETED_UNADJUDICATED",
        created_at_utc=str(packet["timestamp_utc"]), updated_at_utc=str(packet["timestamp_utc"]),
        recorded_by=str(packet["work_id"]), outcomes_inspected=False,
    ))
    step_id = f"STEP-RUN-{stable}"
    target.record_step(StepExecution(
        step_id=step_id, episode_id=episode_id, step_index=0,
        action=f"Observe construct {packet['construct_id']}", tool_name="run_learning_packet_adapter",
        status="FAILED_OR_ABSTAINED" if is_failure else "SUCCEEDED_UNADJUDICATED",
        input_params={
            "packet_sha256": validation["packet_sha256"], "source_ref": validation["source_ref"],
            "authority_status": validation["authority_status"],
        }, output_summary=verdict, executed_at_utc=str(packet["timestamp_utc"]),
    ))
    if is_failure:
        target.record_failure(FailureEvent(
            failure_id=f"FAILURE-RUN-{stable}", episode_id=episode_id, step_id=step_id,
            error_type=str(measurement_status or verdict),
            description=f"Run ended without promotable evidence: {verdict}",
            root_cause=str(packet.get("root_cause") or packet.get("observation") or "UNADJUDICATED"),
            occurred_at_utc=str(packet["timestamp_utc"]),
        ))
    else:
        target.record_success(SuccessEvent(
            success_id=f"SUCCESS-RUN-{stable}", episode_id=episode_id, step_id=step_id,
            description=f"Observed run verdict {verdict}; authority remains {validation['authority_status']}",
            verified_invariants=[
                "claims_are_evidence=false", "outcomes_inspected=false", "holdout_enabled=false",
                f"promotion_ceiling={packet['promotion_ceiling']}",
            ], lesson_candidate_id=f"LESSON-RUN-{stable}", occurred_at_utc=str(packet["timestamp_utc"]),
        ))
    target.record_lesson(LessonCandidate(
        lesson_id=f"LESSON-RUN-{stable}", episode_id=episode_id,
        statement=f"{verdict}; next action: {packet['next_action']}", evidence_record_ids=[],
        confidence="LOW", status="PROPOSED",
        scope="OPERATIONAL" if validation["authority_status"] == "OPERATIONAL_OBSERVATION" else "METHODOLOGICAL",
        created_at_utc=str(packet["timestamp_utc"]),
    ))
    if measurement_status in {"MEASUREMENT_INVALID", "AMBIGUOUS_MEASUREMENT"}:
        target.record_counterexample(Counterexample(
            counterexample_id=f"COUNTEREXAMPLE-RUN-{stable}", target_claim_or_rule_id=str(packet["construct_id"]),
            context=str(packet.get("measurement_context") or packet.get("observation") or "UNSPECIFIED"),
            observed_behavior=verdict, why_it_violates=str(packet.get("measurement_failure") or measurement_status),
            evidence_ref=f"sha256:{validation['packet_sha256']}@{validation['source_ref']}",
            status="CONFIRMED" if measurement_status == "MEASUREMENT_INVALID" else "PROPOSED",
            recorded_at_utc=str(packet["timestamp_utc"]),
        ))
    reconstructed = target.reconstruct_episode(episode_id)
    return RunLearningIngestion(
        episode_id=episode_id, run_id=run_id, packet_sha256=validation["packet_sha256"],
        source_ref=validation["source_ref"], authority_status=validation["authority_status"], verdict=verdict,
        measurement_status=measurement_status, claims_are_evidence=False,
        dataset_evidence=validation["dataset_evidence"], failure_count=len(reconstructed["failures"]),
        success_count=len(reconstructed["successes"]), lesson_count=len(reconstructed["lessons"]),
        counterexample_count=len(target.counterexamples.get(str(packet["construct_id"]), [])), memory=target,
    )
