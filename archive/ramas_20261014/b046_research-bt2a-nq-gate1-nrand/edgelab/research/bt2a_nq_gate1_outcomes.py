"""BT2A NQ Gate 1 (16-cell) outcome engine.

Pure computation library, no CLI, no execution mode, no file I/O. Reuses the
already-validated GC Gate 1 primitives from bt2_gate1_outcomes.py (Event,
PathCache, build_path_cache, directional_excursions, attach_fills,
nrand_replicates, shuffle_replicates) unmodified -- no new tick-decode logic
is introduced here. The only new computation is the per-event capped
magnitude estimand and the 16-cell aggregation/Holm correction, per the
Nico-authorized amendment recorded in
docs/research/DECISION_NICO_ESTIMAND_MAGNITUDE_2026-08-30.md and pinned into
specs/bt2a_nq_gate1_runner_contract_v1.draft.json
(estimand_definition.event_cell_value_ticks).

Do not import this module from target-free preflight code, same rule as
bt2_gate1_outcomes.py. A separate orchestration CLI (not this module) gates
the real run behind two tokens (freeze, then run) and Kaggle-only execution.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence

import numpy as np

from edgelab.research.bt2_gate1_outcomes import (
    Event,
    PathCache,
    build_path_cache,
    directional_excursions,
)
from edgelab.research.bt2a_gate2_first_passage import holm_adjust, wild_cluster_test

BARRIERS_TICKS: tuple[int, ...] = (5, 9, 18, 30)
HORIZONS_OBSERVATIONS: tuple[int, ...] = (25, 50, 100, 250)
# Large enough that clock_end never binds; only the tick cap (=horizon) governs.
# horizon_windows() computes ts + clock_cap_seconds * NS as an int64 timestamp,
# so this must stay far below the int64 overflow point for any realistic ts_ns.
LARGE_CLOCK_CAP_SECONDS: int = 10**9


def all_cells() -> list[tuple[int, int]]:
    """The 16 (barrier_ticks, horizon_observations) combinations, frozen order."""
    return [(b, h) for b in BARRIERS_TICKS for h in HORIZONS_OBSERVATIONS]


def cell_id(barrier_ticks: int, horizon_observations: int) -> str:
    return f"B{int(barrier_ticks)}_H{int(horizon_observations)}"


def build_cell_cache(
    ts_ns: np.ndarray, price_ticks: np.ndarray, session_ids: np.ndarray,
    *, horizon_observations: int,
) -> PathCache:
    """One PathCache per horizon value (not per barrier): the barrier only
    caps the reported magnitude afterward, it never changes the observation
    window. The same cache is reused across all barriers at this horizon."""
    return build_path_cache(
        ts_ns, price_ticks, session_ids,
        tick_cap=int(horizon_observations),
        clock_cap_seconds=LARGE_CLOCK_CAP_SECONDS,
    )


def event_cell_values(
    price_ticks: np.ndarray, cache: PathCache, indices: np.ndarray,
    directions: np.ndarray, *, barrier_ticks: int,
) -> np.ndarray:
    """Signed excursion magnitude per event, capped by barrier_ticks.

    definition (estimand_definition.event_cell_value_ticks):
        min(MFE_ticks_at_horizon, barrier_ticks) - min(MAE_ticks_at_horizon, barrier_ticks)

    Bounded in [-barrier_ticks, +barrier_ticks] by construction. Callers MUST
    filter indices to cache.eligible[idx] beforehand -- ineligible (incomplete
    path within the session/horizon window) events are excluded with a
    reason, not evaluated here (same contract as directional_excursions,
    which raises on any ineligible index).
    """
    mfe, mae = directional_excursions(price_ticks, cache, indices, directions)
    barrier = float(barrier_ticks)
    return np.minimum(mfe, barrier) - np.minimum(mae, barrier)


def session_arm_cell_mean(
    events: Sequence[Event], price_ticks: np.ndarray, cache: PathCache,
    *, barrier_ticks: int,
) -> tuple[float | None, list[dict[str, Any]]]:
    """Arithmetic mean of eligible event_cell_value_ticks for one arm, one
    CME session, one cell. `events` must already be filtered to a single
    session by the caller (this function does not check session identity).

    Returns (mean_or_None, excluded). mean is None if zero events are
    eligible for this cell (e.g. all incomplete-path); excluded lists every
    ineligible event with its reason, per EXCLUDE_WITH_REASON.
    """
    eligible_events = [e for e in events if cache.eligible[e.fill_idx]]
    excluded = [
        {"key": e.key, "reason": "EXCLUDE_WITH_REASON_INCOMPLETE_PATH"}
        for e in events if not cache.eligible[e.fill_idx]
    ]
    if not eligible_events:
        return None, excluded
    idx = np.asarray([e.fill_idx for e in eligible_events], dtype=np.int64)
    direction = np.asarray([e.direction for e in eligible_events], dtype=np.int8)
    values = event_cell_values(price_ticks, cache, idx, direction, barrier_ticks=barrier_ticks)
    return float(np.mean(values)), excluded


def paired_session_contrast(
    primary_by_session: dict[str, float], comparator_by_session: dict[str, float],
) -> tuple[list[str], np.ndarray]:
    """K_ABS - N_RAND (or any two arms), paired within CME session.

    Only sessions present (eligible, non-None) in BOTH arms enter the
    contrast -- equal session weight, no pseudoreplication.
    """
    sessions = sorted(set(primary_by_session) & set(comparator_by_session))
    contrasts = np.asarray(
        [primary_by_session[s] - comparator_by_session[s] for s in sessions],
        dtype=np.float64,
    )
    return sessions, contrasts


def unbiased_paired_session_variance(contrasts: Iterable[float]) -> float:
    """Unbiased sample variance (ddof=1) of equal-weight session contrasts.

    Matches paired_session_variance.definition in the runner contract:
    "Unbiased sample variance (ddof=1) of session-level paired contrasts
    among sessions eligible in both arms for that cell."
    """
    x = np.asarray(list(contrasts), dtype=np.float64)
    if len(x) < 2:
        raise ValueError("unbiased sample variance requires >= 2 sessions")
    return float(np.var(x, ddof=1))


def compute_cell_contrast(
    primary_by_session: dict[str, float], n_rand_by_session: dict[str, float],
    *, replications: int, seed: int,
) -> dict[str, Any]:
    """Sole confirmatory primary contrast (K_ABS - N_RAND) for one cell.

    Wraps wild_cluster_test (already used and validated for BT2A Gate 2 first
    passage) -- same paired-session wild cluster bootstrap methodology, not a
    new inference method.
    """
    sessions, contrasts = paired_session_contrast(primary_by_session, n_rand_by_session)
    if len(sessions) < 2:
        raise ValueError("cell contrast requires >= 2 sessions eligible in both arms")
    test = wild_cluster_test(contrasts, replications=int(replications), seed=int(seed))
    test["paired_session_variance"] = unbiased_paired_session_variance(contrasts)
    test["n_sessions_eligible_both_arms"] = len(sessions)
    return test


def compute_family(
    cells: dict[tuple[int, int], dict[str, dict[str, float]]],
    *, replications: int, seed: int,
) -> dict[str, Any]:
    """Compute the sole confirmatory primary contrast for all 16 cells and
    apply Holm step-down two-sided correction across them.

    `cells`: {(barrier, horizon): {"K_ABS": {session: value}, "N_RAND": {session: value}}}
    for exactly the 16 combinations in all_cells(). Secondary comparators
    (K_BT2, K_ABS_SHUFFLE) are not included here -- they never enter the
    primary Holm family (contrast_roles.secondary_contrasts_may_trigger_supported_label=false).
    """
    ordered = all_cells()
    if set(cells) != set(ordered):
        raise ValueError("compute_family requires exactly the 16 frozen (barrier, horizon) cells")
    per_cell: dict[str, dict[str, Any]] = {}
    p_values: list[float] = []
    child_seed = int(seed)
    for barrier, horizon in ordered:
        arms = cells[(barrier, horizon)]
        result = compute_cell_contrast(
            arms["K_ABS"], arms["N_RAND"],
            replications=int(replications), seed=child_seed,
        )
        per_cell[cell_id(barrier, horizon)] = result
        p_values.append(result["p_two_sided"])
        child_seed += 1
    holm = holm_adjust(p_values)
    for (barrier, horizon), p_holm in zip(ordered, holm):
        per_cell[cell_id(barrier, horizon)]["p_holm_16"] = p_holm
        per_cell[cell_id(barrier, horizon)]["barrier_ticks"] = barrier
        per_cell[cell_id(barrier, horizon)]["horizon_observations"] = horizon
    return {
        "schema_version": "bt2a_nq_gate1_family_result_v1",
        "family_size": 16,
        "multiplicity_method": "HOLM_STEP_DOWN_TWO_SIDED_ALPHA_0_05",
        "cells": per_cell,
    }
