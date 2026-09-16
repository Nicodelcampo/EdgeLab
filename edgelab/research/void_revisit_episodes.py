"""Target-free episode labelling for rejection -> excursion -> re-approach of a frozen void."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence
import numpy as np

class EpisodeError(ValueError): pass

# Formally recognized terminal outcomes for revisit episodes
VALID_TERMINALS = {
    "TRAVERSED",
    "REJECTED_AGAIN",
    "CENSORED_SESSION_END",
    "CENSORED_CONTRACT_ROLL",
    "CENSORED_DATA_EDGE",
    "CENSORED_MAX_FOLLOWUP",
}

VALID_STAGES_AT_CENSORING = {
    "FIRST_APPROACH",
    "REJECTION_CONFIRMED",
    "AWAY_ACCUMULATING",
    "AWAY_QUALIFIED",
    "SECOND_APPROACH",
}

VALID_BOUNDARY_REASONS = {
    "DATA_EDGE",
    "SESSION_END",
    "HOLDOUT_BOUNDARY",
}


@dataclass(frozen=True)
class RevisitSpec:
    approach_ticks: int = 1
    rejection_excursion_ticks: int = 6
    min_away_seconds: float = 60.0
    min_away_volume: float = 0.0
    crossing_buffer_ticks: int = 0
    max_episode_seconds: float = 3600.0


@dataclass(frozen=True)
class RevisitEpisode:
    side: int
    first_approach_idx: int
    rejection_confirm_idx: int | None
    away_qualified_idx: int | None
    second_approach_idx: int | None
    terminal_idx: int | None
    terminal: str
    elapsed_away_seconds: float
    volume_away: float
    max_excursion_ticks: int
    corridor_lower_tick: int
    corridor_upper_tick: int
    stage_at_censoring: str | None = None


def _validate(ts: np.ndarray, px: np.ndarray, vol: np.ndarray,
              session_ids: np.ndarray | None = None,
              state_reset_flags: np.ndarray | None = None) -> None:
    if len(ts)!=len(px) or len(ts)!=len(vol) or len(ts)==0: raise EpisodeError("aligned non-empty arrays required")
    if np.any(ts[1:]<ts[:-1]): raise EpisodeError("timestamps must be ordered")
    if np.any(vol<0): raise EpisodeError("negative volume")
    if session_ids is not None and len(session_ids) != len(ts): raise EpisodeError("session_ids length mismatch")
    if state_reset_flags is not None and len(state_reset_flags) != len(ts): raise EpisodeError("state_reset_flags length mismatch")


def _censor_code_for_boundary(reason: str) -> str:
    if reason not in VALID_BOUNDARY_REASONS:
        raise EpisodeError(f"unknown right_boundary_reason: {reason!r}")
    if reason == "SESSION_END":
        return "CENSORED_SESSION_END"
    return "CENSORED_DATA_EDGE"


def detect_revisit_episodes(
    ts_ns: Sequence[int],
    price_ticks: Sequence[int],
    volume: Sequence[float],
    lower_tick: int,
    upper_tick: int,
    side: int,
    spec: RevisitSpec = RevisitSpec(),
    session_ids: Sequence[object] | None = None,
    state_reset_flags: Sequence[bool] | None = None,
    right_boundary_reason: str = "DATA_EDGE",
) -> list[RevisitEpisode]:
    """Detect non-overlapping causal episodes around geometry frozen at episode start.

    side=+1 approaches from below and traverses above upper; side=-1 mirrors it.
    A first approach must reject without entering beyond the near boundary, travel the
    required excursion away, remain/trade away enough, and then re-approach. Terminal
    is TRAVERSED, REJECTED_AGAIN or one of the 4 formal censoring categories:
    - CENSORED_SESSION_END: CME regular session closes before resolution.
    - CENSORED_CONTRACT_ROLL: interrupted by contract roll (state_reset_flag == True).
    - CENSORED_DATA_EDGE: dataset outer boundary reached before resolution.
    - CENSORED_MAX_FOLLOWUP: elapsed clock time exceeds max_episode_seconds.
    This labels structure, never P&L.
    """
    if side not in (-1,1) or lower_tick>=upper_tick: raise EpisodeError("invalid geometry/side")
    if right_boundary_reason not in VALID_BOUNDARY_REASONS:
        raise EpisodeError(f"invalid right_boundary_reason: {right_boundary_reason!r}")
    t=np.asarray(ts_ns,np.int64); p=np.asarray(price_ticks,np.int64); v=np.asarray(volume,float)
    s_ids = np.asarray(session_ids) if session_ids is not None else None
    r_flags = np.asarray(state_reset_flags, dtype=bool) if state_reset_flags is not None else None
    _validate(t,p,v, s_ids, r_flags)
    near=lower_tick if side==1 else upper_tick
    far=upper_tick if side==1 else lower_tick
    approach=lambda x: x>=near-spec.approach_ticks if side==1 else x<=near+spec.approach_ticks
    entered=lambda x: x>=near if side==1 else x<=near
    away_dist=lambda x: near-x if side==1 else x-near
    traversed=lambda x: x>=far+spec.crossing_buffer_ticks if side==1 else x<=far-spec.crossing_buffer_ticks
    out=[]; i=0; n=len(t)
    while i<n:
        while i < n:
            if r_flags is not None and r_flags[i]:
                i += 1
                continue
            if approach(p[i]):
                break
            i += 1
        if i >= n: break
        if r_flags is not None and r_flags[i]:
            i += 1
            continue

        a = i
        deadline = t[a] + int(spec.max_episode_seconds * 1e9)
        j = a + 1
        max_exc = max(0, int(away_dist(p[a])))
        stage1_censored = None

        while j < n:
            if r_flags is not None and r_flags[j]:
                stage1_censored = (j, "CENSORED_CONTRACT_ROLL")
                break
            if s_ids is not None and s_ids[j] != s_ids[a]:
                stage1_censored = (j, "CENSORED_SESSION_END")
                break
            if t[j] > deadline:
                stage1_censored = (j, "CENSORED_MAX_FOLLOWUP")
                break
            if traversed(p[j]) or (entered(p[j]) and p[j] != near):
                break
            max_exc = max(max_exc, int(away_dist(p[j])))
            if away_dist(p[j]) >= spec.rejection_excursion_ticks:
                break
            j += 1

        if stage1_censored is not None:
            c_idx, c_term = stage1_censored
            out.append(RevisitEpisode(
                side=side, first_approach_idx=a, rejection_confirm_idx=None,
                away_qualified_idx=None, second_approach_idx=None,
                terminal_idx=c_idx, terminal=c_term,
                elapsed_away_seconds=(t[min(c_idx, n - 1)] - t[a]) / 1e9,
                volume_away=0.0, max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                stage_at_censoring="FIRST_APPROACH"
            ))
            i = c_idx if c_term == "CENSORED_CONTRACT_ROLL" else c_idx + 1
            continue

        if j >= n:
            c_term = _censor_code_for_boundary(right_boundary_reason)
            out.append(RevisitEpisode(
                side=side, first_approach_idx=a, rejection_confirm_idx=None,
                away_qualified_idx=None, second_approach_idx=None,
                terminal_idx=n - 1, terminal=c_term,
                elapsed_away_seconds=(t[n - 1] - t[a]) / 1e9,
                volume_away=0.0, max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                stage_at_censoring="FIRST_APPROACH"
            ))
            break

        if away_dist(p[j]) < spec.rejection_excursion_ticks:
            i = max(a + 1, j + 1)
            continue

        reject = j
        max_exc = max(max_exc, int(away_dist(p[reject])))
        vol_away = 0.0
        k = reject
        stage2_censored = None
        qualified = None

        while k < n:
            if r_flags is not None and r_flags[k] and k > reject:
                stage2_censored = (k, "CENSORED_CONTRACT_ROLL")
                break
            if s_ids is not None and s_ids[k] != s_ids[a]:
                stage2_censored = (k, "CENSORED_SESSION_END")
                break
            if t[k] > deadline:
                stage2_censored = (k, "CENSORED_MAX_FOLLOWUP")
                break
            vol_away += float(v[k])
            max_exc = max(max_exc, int(away_dist(p[k])))
            elapsed = (t[k] - t[reject]) / 1e9
            if elapsed >= spec.min_away_seconds and vol_away >= spec.min_away_volume:
                qualified = k
                break
            k += 1

        if stage2_censored is not None:
            c_idx, c_term = stage2_censored
            out.append(RevisitEpisode(
                side=side, first_approach_idx=a, rejection_confirm_idx=reject,
                away_qualified_idx=None, second_approach_idx=None,
                terminal_idx=c_idx, terminal=c_term,
                elapsed_away_seconds=(t[min(c_idx, n - 1)] - t[reject]) / 1e9,
                volume_away=vol_away, max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                stage_at_censoring="AWAY_ACCUMULATING"
            ))
            i = c_idx if c_term == "CENSORED_CONTRACT_ROLL" else c_idx + 1
            continue

        if qualified is None:
            if k >= n:
                c_term = _censor_code_for_boundary(right_boundary_reason)
                out.append(RevisitEpisode(
                    side=side, first_approach_idx=a, rejection_confirm_idx=reject,
                    away_qualified_idx=None, second_approach_idx=None,
                    terminal_idx=n - 1, terminal=c_term,
                    elapsed_away_seconds=(t[n - 1] - t[reject]) / 1e9,
                    volume_away=vol_away, max_excursion_ticks=max_exc,
                    corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                    stage_at_censoring="AWAY_ACCUMULATING"
                ))
            break

        r = qualified + 1
        stage3_censored = None
        while r < n:
            if r_flags is not None and r_flags[r]:
                stage3_censored = (r, "CENSORED_CONTRACT_ROLL")
                break
            if s_ids is not None and s_ids[r] != s_ids[a]:
                stage3_censored = (r, "CENSORED_SESSION_END")
                break
            if t[r] > deadline:
                stage3_censored = (r, "CENSORED_MAX_FOLLOWUP")
                break
            if approach(p[r]):
                break
            vol_away += float(v[r])
            max_exc = max(max_exc, int(away_dist(p[r])))
            r += 1

        if stage3_censored is not None:
            c_idx, c_term = stage3_censored
            out.append(RevisitEpisode(
                side=side, first_approach_idx=a, rejection_confirm_idx=reject,
                away_qualified_idx=qualified, second_approach_idx=None,
                terminal_idx=c_idx, terminal=c_term,
                elapsed_away_seconds=(t[min(c_idx, n - 1)] - t[reject]) / 1e9,
                volume_away=vol_away, max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                stage_at_censoring="AWAY_QUALIFIED"
            ))
            i = c_idx if c_term == "CENSORED_CONTRACT_ROLL" else c_idx + 1
            continue

        if r >= n:
            c_term = _censor_code_for_boundary(right_boundary_reason)
            out.append(RevisitEpisode(
                side=side, first_approach_idx=a, rejection_confirm_idx=reject,
                away_qualified_idx=qualified, second_approach_idx=None,
                terminal_idx=n - 1, terminal=c_term,
                elapsed_away_seconds=(t[n - 1] - t[reject]) / 1e9,
                volume_away=vol_away, max_excursion_ticks=max_exc,
                corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
                stage_at_censoring="AWAY_QUALIFIED"
            ))
            break

        terminal = None
        q = r
        while q < n:
            if r_flags is not None and r_flags[q]:
                terminal = (q, "CENSORED_CONTRACT_ROLL")
                break
            if s_ids is not None and s_ids[q] != s_ids[a]:
                terminal = (q, "CENSORED_SESSION_END")
                break
            if t[q] > deadline:
                terminal = (q, "CENSORED_MAX_FOLLOWUP")
                break
            if traversed(p[q]):
                terminal = (q, "TRAVERSED")
                break
            if away_dist(p[q]) >= spec.rejection_excursion_ticks:
                terminal = (q, "REJECTED_AGAIN")
                break
            q += 1

        if terminal is None:
            c_term = _censor_code_for_boundary(right_boundary_reason)
            terminal = (n - 1, c_term)

        term_idx, term = terminal
        stage_censor = "SECOND_APPROACH" if term.startswith("CENSORED") else None
        out.append(RevisitEpisode(
            side=side, first_approach_idx=a, rejection_confirm_idx=reject,
            away_qualified_idx=qualified, second_approach_idx=r,
            terminal_idx=term_idx, terminal=term,
            elapsed_away_seconds=(t[r] - t[reject]) / 1e9,
            volume_away=vol_away, max_excursion_ticks=max_exc,
            corridor_lower_tick=lower_tick, corridor_upper_tick=upper_tick,
            stage_at_censoring=stage_censor
        ))
        i = term_idx if term == "CENSORED_CONTRACT_ROLL" else (term_idx + 1 if term_idx is not None else n)

    return out


def episode_record(ep: RevisitEpisode) -> dict: return asdict(ep)
