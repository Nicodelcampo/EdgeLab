"""BT2A NQ Gate 1 (16-cell) Execution Runner.

Implementation authorized under Token 3 (AUTHORIZE_IMPLEMENT_BT2A_NQ_GATE1_16CELL_V1)
recorded in docs/research/DECISION_NICO_IMPLEMENT_Y_RUN_BT2A_NQ_GATE1_2026-08-31.md.

Implements the ratified specification in specs/bt2a_nq_gate1_v1.draft.json and
specs/bt2a_nq_gate1_runner_contract_v1.draft.json.

Key Guarantees:
- Input verification against frozen SHA-256 hashes (fail-closed).
- Strata-matched N_RAND sampling without replacement (contract, session, coarse_phase,
  availability, local_volatility_bin) respecting pool - 1 >= n_needed.
- N_RAND replicates averaged within session before paired contrast.
- K_ABS_SHUFFLE permutation preserving event counts within session and coarse phase.
- 16-cell capped magnitude estimand min(MFE, B) - min(MAE, B) in BT2A signal direction
  using non-absorbing window across all 16 (barrier, horizon) cells.
- Incomplete paths excluded with reason (EXCLUDE_WITH_REASON_INCOMPLETE_PATH).
- Equal session weighting, unbiased paired-session sample variance (ddof=1).
- Sole confirmatory primary contrast: K_ABS - N_RAND with Holm step-down alpha=0.05.
- Secondary comparators (K_BT2, K_ABS_SHUFFLE) reported separately and never trigger
  positive claim alone.
- Strict firewalls: zero outcomes/PnL outside pre-registered evaluation, holdout untouched,
  no promotion, no winner selection, no edge declared.
- Atomic checkpointing partitioned by contract_session.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from edgelab.research.bt2_gate1_outcomes import (
    Event,
    PathCache,
    build_path_cache,
    directional_excursions,
)
from edgelab.research.bt2a_nq_gate1_nrand_capacity import (
    INSUFFICIENT_HISTORY,
    availability_flag,
    coarse_phase,
    compute_quintile_edges,
    local_volatility_bin,
    stratum_key,
)
from edgelab.research.bt2a_nq_gate1_outcomes import (
    BARRIERS_TICKS,
    HORIZONS_OBSERVATIONS,
    all_cells,
    build_cell_cache,
    cell_id,
    compute_cell_contrast,
    compute_family,
    event_cell_values,
    paired_session_contrast,
    session_arm_cell_mean,
    unbiased_paired_session_variance,
)

MINIMUM_EFFECT_TICKS: float = 1.0
ALPHA_FAMILY: float = 0.05
HOLM_FAMILY_SIZE: int = 16
MAX_HORIZON_OBSERVATIONS: int = 250
PRE_ANCHOR_VOLATILITY_WINDOW: int = 500

ALLOWED_DECISION_LABELS: tuple[str, ...] = (
    "BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED",
    "BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM",
    "BT2A_NQ_GATE1_INCONCLUSIVE_POWER",
    "ABSTAIN_IDENTITY_CAUSALITY_OR_COVERAGE",
)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(v: Any) -> str:
    return hashlib.sha256(
        json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def verify_input_artifact(path: Path, expected_sha256: str, name: str) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input artifact [{name}]: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise ValueError(
            f"Input artifact SHA-256 mismatch for [{name}]: expected {expected_sha256}, got {actual}"
        )
    return path


def sample_nrand_strata_indices(
    strata_demand: dict[tuple, list[int]],
    candidate_pools: dict[tuple, list[int]],
    *,
    seed: int,
) -> list[tuple[int, int]]:
    """Sample N_RAND candidate indices without replacement within each stratum.

    Returns (own_anchor_position, sampled_position) pairs so the caller can
    pair each random anchor with the K_ABS event it replaces (the anchor
    inherits that event's direction, matching the GC engine's event_dir use).

    Fail-closed: requires candidate_pool_size - 1 >= n_needed for each
    stratum, and each draw excludes its own anchor (the margin exists
    precisely to make that exclusion possible, same as
    bt2_gate1_outcomes._sample_without_own).
    """
    rng = np.random.default_rng(seed)
    sampled_pairs: list[tuple[int, int]] = []

    for key in sorted(strata_demand.keys(), key=lambda kv: (str(kv[0]), str(kv[1]), int(kv[2]), bool(kv[3]), str(kv[4]))):
        own_positions = list(strata_demand[key])
        n_needed = len(own_positions)
        if n_needed == 0:
            continue
        pool = list(candidate_pools.get(key, []))
        if len(pool) - 1 < n_needed:
            raise RuntimeError(
                f"[FAIL_CLOSED] Insufficient capacity for stratum {key}: "
                f"pool={len(pool)}, needed={n_needed} (requires pool - 1 >= needed)"
            )
        chosen: list[int] = []
        for own in own_positions:
            available = [p for p in pool if p != own and p not in chosen]
            # pool - 1 >= n_needed guarantees this is non-empty at every draw
            pick = int(rng.choice(np.asarray(available, dtype=np.int64)))
            chosen.append(pick)
            sampled_pairs.append((int(own), pick))

    return sampled_pairs


def permute_kabs_shuffle_indices(
    events_by_phase: dict[int, list[Event]],
    candidate_indices_by_phase: dict[int, list[int]],
    *,
    seed: int,
) -> list[int]:
    """Permute event fill indices within session and coarse phase preserving event count."""
    rng = np.random.default_rng(seed)
    shuffled_indices: list[int] = []

    for phase in sorted(events_by_phase.keys()):
        ev_list = events_by_phase[phase]
        n_events = len(ev_list)
        if n_events == 0:
            continue
        pool = candidate_indices_by_phase.get(phase, [])
        if len(pool) < n_events:
            raise RuntimeError(
                f"[FAIL_CLOSED] Insufficient candidate indices in phase {phase}: "
                f"pool={len(pool)}, needed={n_events}"
            )
        chosen = rng.choice(pool, size=n_events, replace=False)
        shuffled_indices.extend(chosen.tolist())
    return shuffled_indices


@dataclass
class SessionCellArmStat:
    contract: str
    session: str
    arm: str
    barrier_ticks: int
    horizon_observations: int
    cell_id: str
    mean_value: Optional[float]
    n_events: int
    n_eligible: int
    n_excluded_incomplete: int


def evaluate_session_cell_arm(
    events: Sequence[Event],
    price_ticks: np.ndarray,
    cache: PathCache,
    *,
    contract: str,
    session: str,
    arm: str,
    barrier_ticks: int,
    horizon_observations: int,
) -> tuple[SessionCellArmStat, list[dict[str, Any]]]:
    """Evaluate mean capped excursion for one arm in one session for one cell."""
    cid = cell_id(barrier_ticks, horizon_observations)
    mean_val, exclusions = session_arm_cell_mean(
        events, price_ticks, cache, barrier_ticks=barrier_ticks
    )
    n_total = len(events)
    n_ineligible = len(exclusions)
    n_eligible = n_total - n_ineligible

    stat = SessionCellArmStat(
        contract=contract,
        session=session,
        arm=arm,
        barrier_ticks=barrier_ticks,
        horizon_observations=horizon_observations,
        cell_id=cid,
        mean_value=mean_val,
        n_events=n_total,
        n_eligible=n_eligible,
        n_excluded_incomplete=n_ineligible,
    )
    return stat, exclusions


def decide_gate1_outcome(
    family_result: dict[str, Any],
    effective_sessions_available: int,
    effective_sessions_required: int,
    *,
    alpha_family: float = ALPHA_FAMILY,
    minimum_effect_ticks: float = MINIMUM_EFFECT_TICKS,
) -> dict[str, Any]:
    """Apply Gate 1 decision rule to the 16-cell Holm family result.

    Allowed Labels:
    - BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED: at least one cell achieves Holm-adjusted
      p <= alpha_family with sample mean contrast >= minimum_effect_ticks and positive CI.
    - BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM: power was sufficient (available >= required)
      and zero cells achieve significance.
    - BT2A_NQ_GATE1_INCONCLUSIVE_POWER: available < required or power inputs not met.
    - ABSTAIN_IDENTITY_CAUSALITY_OR_COVERAGE: coverage or causality failed.
    """
    if effective_sessions_available < effective_sessions_required:
        return {
            "decision": "BT2A_NQ_GATE1_INCONCLUSIVE_POWER",
            "reason": (
                f"Effective sessions ({effective_sessions_available}) < "
                f"required ({effective_sessions_required})"
            ),
            "positive_supported_cells": [],
            "EDGE_DECLARED": False,
            "PROMOTION_ELIGIBLE": False,
            "WINNER_SELECTED": False,
        }

    cells = family_result.get("cells", {})
    supported_cells: list[str] = []

    for cid, cdata in cells.items():
        # Real schema emitted by compute_family/compute_cell_contrast
        # (wild_cluster_test): point/lower/upper/p_two_sided/p_holm_16.
        # Fail-closed: missing keys raise instead of silently defaulting.
        p_holm = float(cdata["p_holm_16"])
        point = float(cdata["point"])
        ci_lower = float(cdata["lower"])

        # Positive requires Holm significance, effect >= minimum, positive CI
        if p_holm <= alpha_family and point >= minimum_effect_ticks and ci_lower > 0:
            supported_cells.append(cid)

    if supported_cells:
        decision = "BT2A_NQ_GATE1_DIRECTIONAL_MECHANISM_SUPPORTED"
        reason = f"Significant directional mechanism supported in {len(supported_cells)} of 16 cells: {supported_cells}"
    else:
        decision = "BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM"
        reason = "No cell achieved Holm-adjusted two-sided significance at alpha=0.05 with required effect size"

    return {
        "decision": decision,
        "reason": reason,
        "positive_supported_cells": supported_cells,
        "n_cells_evaluated": len(cells),
        "alpha_family": alpha_family,
        "minimum_effect_ticks": minimum_effect_ticks,
        "effective_sessions_available": effective_sessions_available,
        "effective_sessions_required": effective_sessions_required,
        "EDGE_DECLARED": False,
        "PROMOTION_ELIGIBLE": False,
        "WINNER_SELECTED": False,
    }


def aggregate_full_family_contrasts(
    stats: Sequence[SessionCellArmStat],
    *,
    replications: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Aggregate session-level cell statistics into primary and secondary contrast families."""
    by_cell_arm_session: dict[tuple[int, int], dict[str, dict[str, float]]] = {
        c: {"K_ABS": {}, "N_RAND": {}, "K_BT2": {}, "K_ABS_SHUFFLE": {}}
        for c in all_cells()
    }

    for s in stats:
        if s.mean_value is not None:
            c_key = (s.barrier_ticks, s.horizon_observations)
            if c_key in by_cell_arm_session and s.arm in by_cell_arm_session[c_key]:
                sess_uid = f"{s.contract}:{s.session}"
                by_cell_arm_session[c_key][s.arm][sess_uid] = s.mean_value

    # 1. Primary Holm Family (K_ABS - N_RAND)
    primary_family_input = {
        c_key: {
            "K_ABS": by_cell_arm_session[c_key]["K_ABS"],
            "N_RAND": by_cell_arm_session[c_key]["N_RAND"],
        }
        for c_key in all_cells()
    }
    primary_family_result = compute_family(
        primary_family_input, replications=replications, seed=seed
    )

    # 2. Secondary Family A: K_ABS - K_BT2 (reported raw + Holm within family, non-triggering)
    bt2_family_input = {
        c_key: {
            "K_ABS": by_cell_arm_session[c_key]["K_ABS"],
            "N_RAND": by_cell_arm_session[c_key]["K_BT2"],
        }
        for c_key in all_cells()
    }
    bt2_family_result = compute_family(
        bt2_family_input, replications=replications, seed=seed + 1000
    )

    # 3. Secondary Family B: K_ABS - K_ABS_SHUFFLE (reported raw + Holm within family, non-triggering)
    shuffle_family_input = {
        c_key: {
            "K_ABS": by_cell_arm_session[c_key]["K_ABS"],
            "N_RAND": by_cell_arm_session[c_key]["K_ABS_SHUFFLE"],
        }
        for c_key in all_cells()
    }
    shuffle_family_result = compute_family(
        shuffle_family_input, replications=replications, seed=seed + 2000
    )
    return {
        "primary_contrast": primary_family_result,
        "secondary_contrasts": {
            "K_ABS_MINUS_K_BT2": bt2_family_result,
            "K_ABS_MINUS_K_ABS_SHUFFLE": shuffle_family_result,
        },
    }
