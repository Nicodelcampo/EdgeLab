"""Causal observed-tick arrivals to pair/triple episodes; no future responses.

Point/range index finds bands affected by a tick, rather than scanning every
band every tick. Crossing a whole band without an inside print is GAP_THROUGH,
not a fabricated touch. A band born/moved onto price is not a physical arrival.
A supplied aggressor side is a declared proxy, not certified exchange orderflow.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from datetime import date
import math
from .asof_intersections import Clock,_Node,_put,_delete,_intersect

@dataclass(frozen=True)
class Tick:
    clock: Clock
    price2: int
    volume: float
    aggressor: int=0
    def __post_init__(self):
        if not isinstance(self.clock,Clock) or type(self.price2) is not int or self.price2%2:raise ValueError('observed whole-tick price in half-tick coordinates required')
        if type(self.volume) not in (int,float) or not math.isfinite(self.volume) or self.volume<0:raise ValueError('finite nonnegative volume')
        if type(self.aggressor) is not int or self.aggressor not in (-1,0,1):raise ValueError('declared aggressor proxy -1/0/+1')

@dataclass(frozen=True)
class Features:
    status: str
    available: Clock
    count: int
    net_ticks: float|None
    path_ticks: float|None
    efficiency: float|None
    elapsed_s: float|None
    rate_per_s: float|None
    volume: float|None
    signed_volume_proxy: float|None

@dataclass(frozen=True)
class Anchor:
    episode_id: str
    kind: str
    observed: Clock
    encounter_number: int
    approach_side: int
    features: Features

@dataclass(frozen=True)
class _Band:
    key: str
    lo2: int
    hi2: int

class ArrivalObserver:
    def __init__(self,*,trade_date,window_ticks=256,max_episodes=100000,max_candidates=100000):
        d=date.fromisoformat(trade_date)
        if trade_date!=d.isoformat() or d>=date(2026,10,1):raise ValueError('reserved/noncanonical session')
        if type(window_ticks) is not int or window_ticks<2:raise ValueError('window must have >=2 observed ticks')
        for n in (max_episodes,max_candidates):
            if type(n) is not int or n<1:raise ValueError('explicit capacities required')
        self.window_ticks=window_ticks;self.window=deque(maxlen=window_ticks);self.active={};self.encounters={};self.root=None
        self.max_episodes=max_episodes;self.max_candidates=max_candidates;self.previous=None;self.poisoned=False
    def _features(self,tick):
        w=list(self.window)
        if len(w)!=self.window_ticks:return Features('INCOMPLETE_WINDOW',tick.clock,len(w),None,None,None,None,None,None,None)
        net=(w[-1].price2-w[0].price2)/2;path=sum(abs(b.price2-a.price2)/2 for a,b in zip(w,w[1:]));elapsed=(w[-1].clock.ns-w[0].clock.ns)/1e9
        flow=sum(t.volume*t.aggressor for t in w) if all(t.aggressor for t in w) else None
        return Features('COMPLETE_DECLARED_WINDOW',tick.clock,len(w),net,path,abs(net)/path if path else None,elapsed,(len(w)-1)/elapsed if elapsed>0 else None,sum(t.volume for t in w),flow)
    def observe(self,tick,events=()):
        if self.poisoned:raise ValueError('poisoned arrival observer')
        if not isinstance(tick,Tick) or (self.previous and tick.clock<=self.previous.clock):raise ValueError('strict observed tape order')
        es=tuple(events);ids=[e.episode.episode_id for e in es]
        if len(set(ids))!=len(ids) or any(e.observed!=tick.clock for e in es):raise ValueError('one episode transition per atomic tape clock')
        created=set();moved=set()
        # Validate transitions before mutating index.
        for e in es:
            eid=e.episode.episode_id
            if e.episode.recognized>tick.clock or e.episode.updated>tick.clock:raise ValueError('future episode declaration')
            if e.action=='START':
                if eid in self.active:raise ValueError('episode already active')
                if e.episode.recognized!=tick.clock:raise ValueError('new episode cannot be backdated')
            elif e.action in ('UPDATE','END'):
                if eid not in self.active:raise ValueError('unknown episode transition')
                old=self.active[eid]
                if e.episode.recognized!=old.recognized:raise ValueError('episode origin changed')
                if e.action=='UPDATE' and e.episode.revision!=old.revision+1:raise ValueError('episode revision jump')
            else:raise ValueError('unsupported episode action')
        if len(self.active)+sum(e.action=='START' for e in es)-sum(e.action=='END' for e in es)>self.max_episodes:raise ValueError('episode capacity; no silent pruning')
        try:
            for e in es:
                ep=e.episode;eid=ep.episode_id;old=self.active.get(eid)
                if old:self.root=_delete(self.root,(old.lo2,eid))
                if e.action=='END':del self.active[eid];self.encounters.pop(eid,None);continue
                if old and (old.lo2,old.hi2)!=(ep.lo2,ep.hi2):moved.add(eid)
                if e.action=='START':created.add(eid);self.encounters[eid]=0
                self.active[eid]=ep;self.root=_put(self.root,_Node(_Band(eid,ep.lo2,ep.hi2)))
            self.window.append(tick);f=self._features(tick)
            previous=self.previous;lo=min(previous.price2,tick.price2) if previous else tick.price2;hi=max(previous.price2,tick.price2) if previous else tick.price2
            candidates=set(created|moved)
            if len(candidates)>self.max_candidates:raise ValueError('candidate capacity exceeded; no partial anchors')
            for b in _intersect(self.root,lo,hi):
                candidates.add(b.key)
                if len(candidates)>self.max_candidates:raise ValueError('candidate capacity exceeded; no partial anchors')
            out=[]
            for eid in sorted(candidates):
                ep=self.active[eid];inside=ep.lo2<=tick.price2<=ep.hi2
                if eid in created:
                    if inside:out.append(Anchor(eid,'AT_CREATION',tick.clock,0,0,f))
                    continue
                if eid in moved:
                    if inside:out.append(Anchor(eid,'AT_GEOMETRY_REVISION',tick.clock,self.encounters[eid],0,f))
                    continue
                if previous is None:continue
                was_inside=ep.lo2<=previous.price2<=ep.hi2
                direction=1 if previous.price2<ep.lo2 else (-1 if previous.price2>ep.hi2 else 0)
                if inside and not was_inside:
                    self.encounters[eid]+=1;n=self.encounters[eid];out.append(Anchor(eid,'FIRST_OBSERVED_TOUCH' if n==1 else 'REVISIT',tick.clock,n,direction,f))
                elif was_inside and not inside:out.append(Anchor(eid,'OBSERVED_EXIT',tick.clock,self.encounters[eid],0,f))
                elif not inside and not was_inside and ((previous.price2<ep.lo2 and tick.price2>ep.hi2) or (previous.price2>ep.hi2 and tick.price2<ep.lo2)):
                    out.append(Anchor(eid,'GAP_THROUGH_NO_INSIDE_PRINT',tick.clock,self.encounters[eid],direction,f))
            self.previous=tick
            return tuple(out)
        except BaseException:self.poisoned=True;raise
