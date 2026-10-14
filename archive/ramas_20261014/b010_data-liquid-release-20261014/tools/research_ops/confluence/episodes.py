"""Bounded pair/triple confluence episodes from as-of mutations. No outcomes.

Cross-family pairs; triples only AVZP2/BT2/BT2A or RACIMO/BT2/BT2A. Preserve
episode origin across geometry/membership revisions; no repeated independent
'birth' per update. Closed half-tick intersections, atomic batch semantics.
Market eligibility and exact contract/tape/session binding are caller duties.
"""
from __future__ import annotations
from dataclasses import dataclass,asdict
from itertools import combinations
from .asof_intersections import AsOfJoin,Clock,Snapshot
from .build_target_free_pilot import digest

TRIPLES=(frozenset(('AVZP2','BT2','BT2A')),frozenset(('RACIMO','BT2','BT2A')))

@dataclass(frozen=True)
class Episode:
    episode_id: str
    components: tuple[Snapshot,...]
    recognized: Clock
    updated: Clock
    lo2: int
    hi2: int
    revision: int

@dataclass(frozen=True)
class Event:
    action: str
    episode: Episode
    observed: Clock
    reason: str

class EpisodeStream:
    def __init__(self,*,contract,tape_sha256,trade_date,max_active=100000,max_seen=1000000,max_pairs=100000,max_triples=100000):
        if type(max_triples) is not int or max_triples<1:raise ValueError('triple budget required')
        self.join=AsOfJoin(contract=contract,tape_sha256=tape_sha256,trade_date=trade_date,max_active=max_active,max_seen=max_seen,max_pairs=max_pairs)
        self.max_pairs=max_pairs;self.max_triples=max_triples;self.pairs={};self.triples={};self.neighbors={};self.triple_neighbors={};self.poisoned=False
    def _make(self,key,c,old=None):
        ss=tuple(self.join.active[k] for k in key);lo=max(s.lo2 for s in ss);hi=min(s.hi2 for s in ss)
        if hi<lo:raise ValueError('empty episode intersection')
        born=old.recognized if old else c
        eid=old.episode_id if old else digest({'scope':[self.join.contract,self.join.tape_sha256,self.join.trade_date],'keys':[asdict(k) for k in key],'recognized':asdict(c)})
        return Episode(eid,ss,born,c,lo,hi,old.revision+1 if old else 0)
    def apply(self,clock,*,upserts=(),removals=()):
        if self.poisoned:raise ValueError('poisoned episode stream; rebuild checkpoint')
        ups=tuple(upserts);rem=tuple(removals);changed={s.key for s in ups}|set(rem)
        affected_pairs=set()
        affected_triples=set()
        for k in changed:
            affected_pairs.update(tuple(sorted((k,n))) for n in self.neighbors.get(k,()))
            affected_triples.update(self.triple_neighbors.get(k,()))
        try:
            current=self.join.apply(clock,upserts=ups,removals=rem)
            new_pairs={tuple(sorted((p.left.key,p.right.key))) for p in current}
            events=[]
            # Remove old edges first; candidate triangles see final batch graph.
            for key in sorted(affected_pairs-new_pairs):
                old=self.pairs.pop(key);events.append(Event('END',old,clock,'COMPONENT_REMOVED' if set(key)&set(rem) else 'INTERSECTION_LOST'))
                for a,b in (key,key[::-1]):
                    self.neighbors[a].discard(b)
                    if not self.neighbors[a]:del self.neighbors[a]
            for key in sorted(new_pairs):
                old=self.pairs.get(key);new=self._make(key,clock,old);self.pairs[key]=new
                for a,b in (key,key[::-1]):self.neighbors.setdefault(a,set()).add(b)
                events.append(Event('UPDATE' if old else 'START',new,clock,'COMPONENT_REVISION' if old else 'INTERSECTION_OBSERVED'))
                if len(self.pairs)>self.max_pairs:raise ValueError('active pair budget exceeded; no partial output')
            candidates=set()
            for s in ups:
                k=s.key
                eligible=[n for n in self.neighbors.get(k,()) if any(frozenset((k.family,n.family))<=t for t in TRIPLES)]
                for a,b in combinations(sorted(eligible),2):
                    if frozenset((k.family,a.family,b.family)) not in TRIPLES:continue
                    if b not in self.neighbors.get(a,()):continue
                    key=tuple(sorted((k,a,b)))
                    if key not in candidates and len(candidates)>=self.max_triples:raise ValueError('candidate triple budget exceeded; no truncation')
                    candidates.add(key)
            for key in sorted(affected_triples-candidates):
                old=self.triples.pop(key);events.append(Event('END',old,clock,'COMPONENT_REMOVED' if set(key)&set(rem) else 'INTERSECTION_LOST'))
                for k in key:
                    self.triple_neighbors[k].discard(key)
                    if not self.triple_neighbors[k]:del self.triple_neighbors[k]
            for key in sorted(candidates):
                old=self.triples.get(key);new=self._make(key,clock,old);self.triples[key]=new
                for k in key:self.triple_neighbors.setdefault(k,set()).add(key)
                events.append(Event('UPDATE' if old else 'START',new,clock,'COMPONENT_REVISION' if old else 'INTERSECTION_OBSERVED'))
                if len(self.triples)>self.max_triples:raise ValueError('active triple budget exceeded; no partial output')
            return tuple(sorted(events,key=lambda e:(len(e.episode.components),tuple(s.key for s in e.episode.components),e.action)))
        except BaseException:
            self.poisoned=True;raise
