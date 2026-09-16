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
    rejection_confirm_idx: int
    away_qualified_idx: int
    second_approach_idx: int
    terminal_idx: int | None
    terminal: str
    elapsed_away_seconds: float
    volume_away: float
    max_excursion_ticks: int
    corridor_lower_tick: int
    corridor_upper_tick: int


def _validate(ts: np.ndarray, px: np.ndarray, vol: np.ndarray,
              session_ids: np.ndarray | None = None,
              state_reset_flags: np.ndarray | None = None) -> None:
    if len(ts)!=len(px) or len(ts)!=len(vol) or len(ts)==0: raise EpisodeError("aligned non-empty arrays required")
    if np.any(ts[1:]<ts[:-1]): raise EpisodeError("timestamps must be ordered")
    if np.any(vol<0): raise EpisodeError("negative volume")
    if session_ids is not None and len(session_ids) != len(ts): raise EpisodeError("session_ids length mismatch")
    if state_reset_flags is not None and len(state_reset_flags) != len(ts): raise EpisodeError("state_reset_flags length mismatch")


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
        while i<n and not approach(p[i]): i+=1
        if i>=n: break
        a=i; deadline=t[a]+int(spec.max_episode_seconds*1e9)
        j=a; max_exc=0
        aborted = False
        while j<n and t[j]<=deadline:
            if r_flags is not None and r_flags[j] and j > a:
                aborted = True; i = j; break
            if s_ids is not None and s_ids[j] != s_ids[a]:
                aborted = True; i = j; break
            if traversed(p[j]) or (entered(p[j]) and p[j]!=near): break
            max_exc=max(max_exc,int(away_dist(p[j])))
            if away_dist(p[j])>=spec.rejection_excursion_ticks: break
            j+=1
        if aborted or j>=n or t[j]>deadline or away_dist(p[j])<spec.rejection_excursion_ticks:
            i=max(a+1, j if aborted else j+1); continue
        reject=j; vol_away=0.0; k=j; qualified=None
        while k<n and t[k]<=deadline:
            if r_flags is not None and r_flags[k] and k > reject:
                aborted = True; i = k; break
            if s_ids is not None and s_ids[k] != s_ids[a]:
                aborted = True; i = k; break
            vol_away+=float(v[k]); max_exc=max(max_exc,int(away_dist(p[k])))
            elapsed=(t[k]-t[reject])/1e9
            if elapsed>=spec.min_away_seconds and vol_away>=spec.min_away_volume:
                qualified=k; break
            k+=1
        if aborted or qualified is None:
            i=max(a+1, k if aborted else k); continue
        r=qualified+1
        interrupted = False
        while r<n and not approach(p[r]):
            if r_flags is not None and r_flags[r]:
                out.append(RevisitEpisode(side,a,reject,qualified,r,r,"CENSORED_CONTRACT_ROLL",(t[r]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
                interrupted = True; i = r; break
            if s_ids is not None and s_ids[r] != s_ids[a]:
                out.append(RevisitEpisode(side,a,reject,qualified,r,r,"CENSORED_SESSION_END",(t[r]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
                interrupted = True; i = r; break
            if t[r]>deadline:
                out.append(RevisitEpisode(side,a,reject,qualified,r,r,"CENSORED_MAX_FOLLOWUP",(t[r]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
                interrupted = True; i = r + 1; break
            vol_away+=float(v[r]); max_exc=max(max_exc,int(away_dist(p[r]))); r+=1
        if interrupted:
            continue
        if r>=n:
            out.append(RevisitEpisode(side,a,reject,qualified,n-1,None,"CENSORED_DATA_EDGE",(t[n-1]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
            break
        terminal=None; q=r
        while q<n:
            if r_flags is not None and r_flags[q] and q > r:
                terminal=(q,"CENSORED_CONTRACT_ROLL"); break
            if s_ids is not None and s_ids[q] != s_ids[a]:
                terminal=(q,"CENSORED_SESSION_END"); break
            if t[q]>deadline:
                terminal=(q,"CENSORED_MAX_FOLLOWUP"); break
            if traversed(p[q]): terminal=(q,"TRAVERSED"); break
            if away_dist(p[q])>=spec.rejection_excursion_ticks: terminal=(q,"REJECTED_AGAIN"); break
            q+=1
        if terminal is None:
            terminal=(None,"CENSORED_DATA_EDGE")
        term_idx,term=terminal
        out.append(RevisitEpisode(side,a,reject,qualified,r,term_idx,term,(t[r]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
        i=(term_idx+1) if term_idx is not None else n
    return out


def episode_record(ep: RevisitEpisode) -> dict: return asdict(ep)
