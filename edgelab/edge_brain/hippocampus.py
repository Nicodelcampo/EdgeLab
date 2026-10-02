from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class HippocampusError(ValueError):
    """Raised on hippocampal invariant or reuse violations."""


class InvalidatedArtifactReuseError(HippocampusError):
    """Raised when attempting to silently reuse an invalidated or stale artifact."""


@dataclass
class AnalysisEpisode:
    episode_id: str
    goal: str
    status: str = "PLANNING"
    step_ids: list[str] = field(default_factory=list)
    expectation_ids: list[str] = field(default_factory=list)
    context_pack_id: str = ""
    created_at_utc: str = ""
    updated_at_utc: str = ""
    recorded_by: str = ""
    outcomes_inspected: bool = False

    def __post_init__(self) -> None:
        if self.outcomes_inspected:
            raise HippocampusError("outcomes_inspected must be False during target-free episode execution")


@dataclass
class StepExecution:
    step_id: str
    episode_id: str
    step_index: int
    action: str
    tool_name: str
    status: str = "PENDING"
    input_params: dict[str, Any] = field(default_factory=dict)
    output_summary: str = ""
    failure_event_id: str | None = None
    success_event_id: str | None = None
    executed_at_utc: str = ""


@dataclass
class Expectation:
    expectation_id: str
    episode_id: str
    statement: str
    metric: str
    expected_direction: str
    status: str = "PROPOSED"
    baseline_value: float | None = None
    expected_value: float | None = None
    created_at_utc: str = ""


@dataclass
class FailureEvent:
    failure_id: str
    episode_id: str
    step_id: str
    error_type: str
    description: str
    root_cause: str
    causal_hypothesis_id: str | None = None
    repair_action_id: str | None = None
    occurred_at_utc: str = ""


@dataclass
class RepairAction:
    repair_id: str
    failure_id: str
    description: str
    changes_made: list[str] = field(default_factory=list)
    verified_by_test: bool = False
    status: str = "PLANNED"
    executed_at_utc: str = ""


@dataclass
class SuccessEvent:
    success_id: str
    episode_id: str
    step_id: str
    description: str
    verified_invariants: list[str] = field(default_factory=list)
    lesson_candidate_id: str | None = None
    occurred_at_utc: str = ""


@dataclass
class LessonCandidate:
    lesson_id: str
    episode_id: str
    statement: str
    evidence_record_ids: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    status: str = "PROPOSED"
    scope: str = "METHODOLOGICAL"
    created_at_utc: str = ""
    # CerebroSSRN parity (EDGE-006, 2026-09-23): the old brain declared the
    # robustness of every finding; lessons without it read as established fact.
    # Defaults keep v1 ledger payloads replayable unchanged.
    robustness: str = "UNRATED"
    conditions: list[str] = field(default_factory=list)


@dataclass
class Counterexample:
    counterexample_id: str
    target_claim_or_rule_id: str
    context: str
    observed_behavior: str
    why_it_violates: str
    evidence_ref: str
    status: str = "CONFIRMED"
    recorded_at_utc: str = ""


class HippocampusMemory:
    """In-memory experimental hippocampus managing episodes and preventing silent reuse."""

    def __init__(self) -> None:
        self.episodes: dict[str, AnalysisEpisode] = {}
        self.steps: dict[str, list[StepExecution]] = {}
        self.expectations: dict[str, list[Expectation]] = {}
        self.failures: dict[str, list[FailureEvent]] = {}
        self.repairs: dict[str, list[RepairAction]] = {}
        self.successes: dict[str, list[SuccessEvent]] = {}
        self.lessons: dict[str, list[LessonCandidate]] = {}
        self.counterexamples: dict[str, list[Counterexample]] = {}

    def register_episode(self, episode: AnalysisEpisode) -> None:
        if episode.episode_id in self.episodes:
            raise HippocampusError(f"Episode {episode.episode_id} already exists")
        self.episodes[episode.episode_id] = episode
        self.steps[episode.episode_id] = []
        self.expectations[episode.episode_id] = []
        self.failures[episode.episode_id] = []
        self.repairs[episode.episode_id] = []
        self.successes[episode.episode_id] = []
        self.lessons[episode.episode_id] = []

    def record_step(self, step: StepExecution) -> None:
        if step.episode_id not in self.episodes:
            raise HippocampusError(f"Episode {step.episode_id} not registered")
        self.steps[step.episode_id].append(step)
        if step.step_id not in self.episodes[step.episode_id].step_ids:
            self.episodes[step.episode_id].step_ids.append(step.step_id)

    def record_expectation(self, expectation: Expectation) -> None:
        if expectation.episode_id not in self.episodes:
            raise HippocampusError(f"Episode {expectation.episode_id} not registered")
        self.expectations[expectation.episode_id].append(expectation)
        if expectation.expectation_id not in self.episodes[expectation.episode_id].expectation_ids:
            self.episodes[expectation.episode_id].expectation_ids.append(expectation.expectation_id)

    def record_failure(self, failure: FailureEvent) -> None:
        if failure.episode_id not in self.episodes:
            raise HippocampusError(f"Episode {failure.episode_id} not registered")
        self.failures[failure.episode_id].append(failure)

    def record_repair(self, repair: RepairAction, episode_id: str) -> None:
        if episode_id not in self.episodes:
            raise HippocampusError(f"Episode {episode_id} not registered")
        self.repairs[episode_id].append(repair)

    def record_success(self, success: SuccessEvent) -> None:
        if success.episode_id not in self.episodes:
            raise HippocampusError(f"Episode {success.episode_id} not registered")
        self.successes[success.episode_id].append(success)

    def record_lesson(self, lesson: LessonCandidate) -> None:
        if lesson.episode_id not in self.episodes:
            raise HippocampusError(f"Episode {lesson.episode_id} not registered")
        self.lessons[lesson.episode_id].append(lesson)

    def record_counterexample(self, counterexample: Counterexample) -> None:
        target = counterexample.target_claim_or_rule_id
        self.counterexamples.setdefault(target, []).append(counterexample)

    def reconstruct_episode(self, episode_id: str) -> dict[str, Any]:
        """Deterministically reconstruct full trajectory of an episode."""
        if episode_id not in self.episodes:
            raise HippocampusError(f"Episode {episode_id} not found")
        ep = self.episodes[episode_id]
        steps = sorted(self.steps.get(episode_id, []), key=lambda s: s.step_index)
        return {
            "episode": ep,
            "steps": steps,
            "expectations": self.expectations.get(episode_id, []),
            "failures": self.failures.get(episode_id, []),
            "repairs": self.repairs.get(episode_id, []),
            "successes": self.successes.get(episode_id, []),
            "lessons": self.lessons.get(episode_id, []),
        }

    def reuse_artifact(
        self,
        artifact_id: str,
        invalidation_statuses: dict[str, str],
        context: str = "",
    ) -> dict[str, Any]:
        """Enforce strict gate against silent reuse of invalidated or stale artifacts."""
        status = invalidation_statuses.get(artifact_id)
        if status in {"INVALIDATED_BY_MEASUREMENT_ERROR", "STALE_BY_DEPENDENCY"}:
            raise InvalidatedArtifactReuseError(
                f"Cannot reuse artifact {artifact_id}: flagged as {status}"
            )
        if status == "REQUIRES_REAUDIT":
            raise InvalidatedArtifactReuseError(
                f"Cannot reuse artifact {artifact_id} without explicit re-audit"
            )
        return {
            "artifact_id": artifact_id,
            "status": status or "ELIGIBLE",
            "context": context,
        }
