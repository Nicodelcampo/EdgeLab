"""Target-free episode labelling for rejection -> excursion -> re-approach of a frozen void."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence
import numpy as np

class EpisodeError(ValueError): pass

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


def _validate(ts: np.ndarray, px: np.ndarray, vol: np.ndarray) -> None:
    if len(ts)!=len(px) or len(ts)!=len(vol) or len(ts)==0: raise EpisodeError("aligned non-empty arrays required")
    if np.any(ts[1:]<ts[:-1]): raise EpisodeError("timestamps must be ordered")
    if np.any(vol<0): raise EpisodeError("negative volume")


def detect_revisit_episodes(ts_ns: Sequence[int], price_ticks: Sequence[int], volume: Sequence[float],
                            lower_tick: int, upper_tick: int, side: int, spec: RevisitSpec=RevisitSpec()) -> list[RevisitEpisode]:
    """Detect non-overlapping causal episodes around geometry frozen at episode start.

    side=+1 approaches from below and traverses above upper; side=-1 mirrors it.
    A first approach must reject without entering beyond the near boundary, travel the
    required excursion away, remain/trade away enough, and then re-approach. Terminal
    is TRAVERSED, REJECTED_AGAIN or CENSORED. This labels structure, never P&L.
    """
    if side not in (-1,1) or lower_tick>=upper_tick: raise EpisodeError("invalid geometry/side")
    t=np.asarray(ts_ns,np.int64); p=np.asarray(price_ticks,np.int64); v=np.asarray(volume,float); _validate(t,p,v)
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
        while j<n and t[j]<=deadline:
            if traversed(p[j]) or (entered(p[j]) and p[j]!=near): break
            max_exc=max(max_exc,int(away_dist(p[j])))
            if away_dist(p[j])>=spec.rejection_excursion_ticks: break
            j+=1
        if j>=n or t[j]>deadline or away_dist(p[j])<spec.rejection_excursion_ticks:
            i=max(a+1,j+1); continue
        reject=j; vol_away=0.0; k=j; qualified=None
        while k<n and t[k]<=deadline:
            vol_away+=float(v[k]); max_exc=max(max_exc,int(away_dist(p[k])))
            elapsed=(t[k]-t[reject])/1e9
            if elapsed>=spec.min_away_seconds and vol_away>=spec.min_away_volume:
                qualified=k; break
            k+=1
        if qualified is None:
            i=max(a+1,k); continue
        r=qualified+1
        while r<n and t[r]<=deadline and not approach(p[r]):
            vol_away+=float(v[r]); max_exc=max(max_exc,int(away_dist(p[r]))); r+=1
        if r>=n or t[r]>deadline:
            out.append(RevisitEpisode(side,a,reject,qualified,min(r,n-1),None,"CENSORED",(t[min(r,n-1)]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick)); break
        terminal=None; q=r
        while q<n and t[q]<=deadline:
            if traversed(p[q]): terminal=(q,"TRAVERSED"); break
            if away_dist(p[q])>=spec.rejection_excursion_ticks: terminal=(q,"REJECTED_AGAIN"); break
            q+=1
        term_idx,term=terminal if terminal else (None,"CENSORED")
        out.append(RevisitEpisode(side,a,reject,qualified,r,term_idx,term,(t[r]-t[reject])/1e9,vol_away,max_exc,lower_tick,upper_tick))
        i=(term_idx+1) if term_idx is not None else n
    return out


def episode_record(ep: RevisitEpisode) -> dict: return asdict(ep)
