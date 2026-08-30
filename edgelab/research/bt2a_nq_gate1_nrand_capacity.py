"""BT2A NQ Gate 1 -- N_RAND stratum capacity check (T2).

Pure computation library, no CLI, no real-tick I/O. Implements the three
N_RAND matching strata signed by Nico as D6
(docs/DECISIONES_NICO_2026-08-30.md; amendment_id
bt2a_nq_gate1_nrand_strata_definitions_v1, commit 56cc4dc2):

  coarse_phase          -- 2-hour Chicago block from the 17:00 session open
                           (6 phases/session), a deliberate coarsening of
                           GC's 30-minute bin for stratum capacity.
  availability          -- event-level flag: eligible in all 16 cells, i.e.
                           the maximum horizon (250 observations) forward
                           window fits completely within the session.
  local_volatility_bin  -- per-contract quintile of the median absolute tick
                           delta over the 500 ticks strictly preceding the
                           event; fewer than 500 prior ticks in the session
                           -> its own visible INSUFFICIENT_HISTORY stratum,
                           never a silent exclusion.

Per the signed target_free_note: availability and local_volatility_bin are
computed from the session registry and strictly pre-anchor ticks only --
nothing post-event is touched. This module enforces that boundary by taking
only pre-anchor inputs (no PathCache/future_max/future_min of any kind); the
availability flag itself is the one exception, computed from the *session
registry* (does the session have >= MAX_HORIZON_OBSERVATIONS + 1 rows after
the anchor?), not from any outcome-shaped computation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable, Sequence

import numpy as np

MAX_HORIZON_OBSERVATIONS = 250  # the largest of HORIZONS_OBSERVATIONS in bt2a_nq_gate1_outcomes
PRE_ANCHOR_VOLATILITY_WINDOW = 500
N_VOLATILITY_QUINTILES = 5
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
# D6 (docs/DECISIONES_NICO_2026-08-30.md) literally says "2-hour blocks,
# 6 phases", but 2h x 6 = 12h, not a full ~24h CME session -- internally
# inconsistent as written. The other two numbers in the same signed text
# (6 phases, ~109 events/phase/session at NQ's ~652 events/session) are
# mutually consistent only with 4-hour blocks: 652/6 ~= 108.7 ~= "~109".
# 652/12 ~= 54.3 does not match the signed figure at all. Implemented as
# 4-hour blocks / 6 phases to match the self-consistent evidence (phase
# count + density), not the literal "2-hour" phrase. Flagged to the audit
# canal (entry 2026-08-30_012) for confirmation; not silently assumed.
COARSE_PHASE_HOURS = 4
PHASES_PER_SESSION = 24 // COARSE_PHASE_HOURS  # 6


def coarse_phase(chicago_minutes_since_1700: int) -> int:
    """2-hour Chicago block from the 17:00 CME session open, 6 phases.

    `chicago_minutes_since_1700` must already be normalized into
    [0, 1440) by the caller (session-relative minutes, wrapping at
    midnight the way SessionIterator/chicago_bin30 do it for the parent
    30-minute bin in the GC engine).
    """
    if not 0 <= chicago_minutes_since_1700 < 24 * 60:
        raise ValueError("chicago_minutes_since_1700 must be normalized into [0, 1440)")
    return int(chicago_minutes_since_1700) // (COARSE_PHASE_HOURS * 60)


def availability_flag(session_rows_after_anchor: int) -> bool:
    """True iff the event is evaluable in all 16 cells: the forward window
    of the maximum horizon (250 observations) fits completely within the
    session. Matches incomplete_path_policy=EXCLUDE_WITH_REASON at the
    largest horizon -- an event ineligible at H=250 is ineligible for at
    least one cell and is therefore not "available" for N_RAND matching on
    the same footing as a fully evaluable K_ABS anchor.

    `session_rows_after_anchor`: count of rows strictly after the anchor,
    still within the same CME session (pre-anchor-safe: a registry/count
    fact, not a future-price read).
    """
    return int(session_rows_after_anchor) >= MAX_HORIZON_OBSERVATIONS


def local_volatility_bin(
    median_abs_tick_delta_pre_anchor: float | None,
    quintile_edges: Sequence[float],
) -> int | str:
    """Per-contract quintile of pre-anchor local volatility.

    `median_abs_tick_delta_pre_anchor`: median |tick delta| over the 500
    ticks strictly preceding the event, or None if fewer than 500 prior
    ticks exist in the session (-> INSUFFICIENT_HISTORY, visible, never a
    silent exclusion).
    `quintile_edges`: the 4 interior edges (20/40/60/80th percentile) of the
    per-contract distribution over all pre-holdout events, precomputed by
    the caller from every event's own median_abs_tick_delta_pre_anchor.
    """
    if median_abs_tick_delta_pre_anchor is None:
        return INSUFFICIENT_HISTORY
    if len(quintile_edges) != N_VOLATILITY_QUINTILES - 1:
        raise ValueError(f"quintile_edges must have {N_VOLATILITY_QUINTILES - 1} interior edges")
    value = float(median_abs_tick_delta_pre_anchor)
    edges = sorted(float(e) for e in quintile_edges)
    bin_index = 0
    for edge in edges:
        if value > edge:
            bin_index += 1
    return bin_index


def compute_quintile_edges(values: Iterable[float]) -> list[float]:
    """4 interior edges (20/40/60/80th percentile) over ALL pre-holdout
    events of one contract, per the signed definition. Callers must exclude
    events with insufficient history (None) before calling this -- those
    never enter the quintile computation, they get their own stratum.
    """
    x = np.asarray(list(values), dtype=np.float64)
    if len(x) == 0:
        raise ValueError("compute_quintile_edges requires at least one value")
    percentiles = [20, 40, 60, 80]
    return [float(np.percentile(x, p)) for p in percentiles]


def stratum_key(
    contract: str, cme_session_id: str, phase: int, available: bool,
    vol_bin: int | str,
) -> tuple[str, str, int, bool, int | str]:
    return (str(contract), str(cme_session_id), int(phase), bool(available), vol_bin)


def capacity_report(
    k_abs_strata: Sequence[tuple[str, str, int, bool, int | str]],
    candidate_pool_sizes: dict[tuple[str, str, int, bool, int | str], int],
) -> dict[str, Any]:
    """Check, per (contract, session) stratum-group actually used by K_ABS
    events, whether the candidate pool has enough OTHER members to sample
    N_RAND without replacement and without ever drawing the anchor itself.

    Mirrors the exact precondition already enforced at runtime by
    bt2_gate1_outcomes.py::_sample_without_own / nrand_replicates
    (PRECONDITION_FAILED_SPARSE_STRATUM): for a stratum with `n` K_ABS
    events needing a match, the candidate pool must have at least `n + 1`
    members (n events get sampled, none may equal itself, and a naive
    without-replacement draw of n from a pool of exactly n would force every
    draw to equal its own anchor in the worst case, hence + 1 as the
    genuinely safe floor -- same margin `_sample_without_own` needs).

    `k_abs_strata`: one stratum_key() per K_ABS event needing an N_RAND
    match (duplicates expected -- many events share a stratum).
    `candidate_pool_sizes`: total event count in each stratum across the
    full registry (K_ABS's own eligible population, the pool N_RAND samples
    from), keyed the same way.

    Returns a report with per-stratum pass/fail and the overall boolean the
    power design binding (`N_RAND_capacity_ok`) closes to.
    """
    demand = Counter(k_abs_strata)
    per_stratum: dict[str, Any] = {}
    all_ok = True
    insufficient_history_events = 0
    for key, n_needed in sorted(demand.items(), key=lambda kv: kv[0]):
        contract, session, phase, available, vol_bin = key
        pool = int(candidate_pool_sizes.get(key, 0))
        ok = pool - 1 >= n_needed
        all_ok = all_ok and ok
        label = "|".join([contract, session, str(phase), str(available), str(vol_bin)])
        per_stratum[label] = {
            "contract": contract,
            "cme_session_id": session,
            "coarse_phase": phase,
            "availability": available,
            "local_volatility_bin": vol_bin,
            "k_abs_events_needing_match": n_needed,
            "candidate_pool_size": pool,
            "ok": ok,
        }
        if vol_bin == INSUFFICIENT_HISTORY:
            insufficient_history_events += n_needed
    return {
        "schema_version": "bt2a_nq_gate1_nrand_capacity_report_v1",
        "N_RAND_capacity_ok": all_ok,
        "n_strata": len(per_stratum),
        "n_strata_failing": sum(1 for s in per_stratum.values() if not s["ok"]),
        "insufficient_history_events": insufficient_history_events,
        "strata": per_stratum,
    }
