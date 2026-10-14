from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .hippocampus import AnalysisEpisode, Expectation, StepExecution


class FactoryAdapterError(ValueError):
    """Raised when Factory material cannot safely enter the Brain."""


FORBIDDEN_OUTCOME_FIELDS = frozenset({
    "pnl",
    "return",
    "returns",
    "mfe",
    "mae",
    "winner",
    "target_hit",
    "stop_hit",
})

OBSERVED_FILL_ORIGIN = "OBSERVED_FIRST_EXECUTABLE_TICK"


@dataclass(frozen=True)
class CanonicalFormationEvent:
    event_id: str
    formation_start_ns: int
    formation_end_ns: int
    available_at_ns: int
    formation_spec: dict[str, Any]
    display_bar_key: str | None
    executable_fill_ns: int | None
    executable_fill_status: str
    source_sha256: str | None


def _first(row: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def adapt_target_free_zone_event(row: Mapping[str, Any]) -> CanonicalFormationEvent:
    """Convert a Factory zone into a Brain-safe target-free event.

    The adapter deliberately refuses to infer formation from a display bar key and
    refuses synthetic fills.  It accepts both the new formation names and the
    older Factory origin/availability names, but never invents a missing end.
    """
    leaked = sorted(key for key in FORBIDDEN_OUTCOME_FIELDS if row.get(key) is not None)
    if leaked:
        raise FactoryAdapterError(f"Outcome fields are forbidden in target-free adapter: {leaked}")

    start = _first(row, "formation_start_ns", "origin_ts")
    end = row.get("formation_end_ns")
    available = _first(row, "available_at_ns", "signal_available_ts")
    if start is None or end is None or available is None:
        raise FactoryAdapterError(
            "formation_start_ns/origin_ts, formation_end_ns and available_at_ns/signal_available_ts are required"
        )

    formation_spec = row.get("formation_spec")
    if not isinstance(formation_spec, Mapping) or not formation_spec:
        raise FactoryAdapterError(
            "formation_spec is required; display_bar_key/bar_key cannot define signal formation"
        )
    formation_spec = dict(formation_spec)
    if formation_spec.get("kind") not in {"tick_count", "time", "volume", "external_explicit"}:
        raise FactoryAdapterError("Unsupported or missing formation_spec.kind")

    start_i, end_i, available_i = int(start), int(end), int(available)
    if not start_i <= end_i <= available_i:
        raise FactoryAdapterError(
            "Temporal invariant violated: formation_start_ns <= formation_end_ns <= available_at_ns"
        )

    fill = _first(row, "executable_fill_ns", "executable_fill_ts")
    fill_origin = row.get("executable_fill_origin")
    if fill is None:
        fill_i = None
        fill_status = "NO_EXECUTABLE_FILL_AVAILABLE"
    else:
        if fill_origin != OBSERVED_FILL_ORIGIN:
            raise FactoryAdapterError(
                "Executable fill is accepted only with OBSERVED_FIRST_EXECUTABLE_TICK provenance"
            )
        fill_i = int(fill)
        if fill_i <= available_i:
            raise FactoryAdapterError("Observed executable fill must be strictly after availability")
        fill_status = "OBSERVED_EXECUTABLE_FILL"

    event_id = str(_first(row, "event_id", "zone_id", "id") or "")
    if not event_id:
        raise FactoryAdapterError("event_id/zone_id/id is required")

    return CanonicalFormationEvent(
        event_id=event_id,
        formation_start_ns=start_i,
        formation_end_ns=end_i,
        available_at_ns=available_i,
        formation_spec=formation_spec,
        display_bar_key=_first(row, "display_bar_key", "bar_key"),
        executable_fill_ns=fill_i,
        executable_fill_status=fill_status,
        source_sha256=row.get("source_sha256"),
    )


def build_target_free_episode_records(
    plan: Mapping[str, Any],
    *,
    recorded_at_utc: str,
    recorded_by: str,
) -> dict[str, Any]:
    """Materialize the target-free plan into typed hippocampal records."""
    ep = plan.get("episode") or {}
    if ep.get("outcomes_inspected") is not False or ep.get("holdout_inspected") is not False:
        raise FactoryAdapterError("Target-free episode must explicitly keep outcomes and holdout closed")

    episode_id = str(ep.get("episode_id") or "")
    if not episode_id:
        raise FactoryAdapterError("episode.episode_id is required")
    step_names = list(plan.get("steps") or [])
    if not step_names:
        raise FactoryAdapterError("At least one planned step is required")

    step_ids = [f"STEP-{episode_id.removeprefix('EPISODE-')}:{i:02d}" for i in range(len(step_names))]
    expectation_id = f"EXP-{episode_id.removeprefix('EPISODE-')}:POPULATION-DIFFERENCE"
    episode = AnalysisEpisode(
        episode_id=episode_id,
        goal=str(ep.get("goal") or ""),
        status=str(ep.get("status") or "PLANNING"),
        step_ids=step_ids,
        expectation_ids=[expectation_id],
        context_pack_id=str(ep.get("context_pack_id") or ""),
        created_at_utc=recorded_at_utc,
        updated_at_utc=recorded_at_utc,
        recorded_by=recorded_by,
        outcomes_inspected=False,
    )
    steps = [
        StepExecution(
            step_id=step_id,
            episode_id=episode_id,
            step_index=i,
            action=str(action),
            tool_name="UNASSIGNED_DETERMINISTIC_EXECUTOR",
            status="PENDING",
            input_params={},
            output_summary="",
            executed_at_utc="",
        )
        for i, (step_id, action) in enumerate(zip(step_ids, step_names))
    ]
    expectation = Expectation(
        expectation_id=expectation_id,
        episode_id=episode_id,
        statement="Entry policies may define different target-free event populations; no economic direction is asserted.",
        metric="policy_population_counts_and_censoring",
        expected_direction="NEUTRAL",
        status="PROPOSED",
        created_at_utc=recorded_at_utc,
    )
    return {
        "analysis_episode": asdict(episode),
        "step_executions": [asdict(step) for step in steps],
        "expectations": [asdict(expectation)],
    }
