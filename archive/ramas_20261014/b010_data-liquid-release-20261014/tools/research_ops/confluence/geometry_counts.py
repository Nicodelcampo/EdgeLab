"""Exact target-free event COUNTS without retaining the live pair/triple graph.

Not an episode/arrival store: IDs, origins and revision histories are deliberately
not produced. All six cross-family pair and both declared triple families remain.
Only intersections affected by the atomic mutation are materialized, bounded per
clock. Counts compare BEFORE vs AFTER memberships in full source identity.
No source reader, authorization, labels or pruning of valid combinations.
"""
from collections import Counter
from .asof_intersections import AsOfJoin,_intersect
from .episodes import TRIPLES

class GeometryCountStream:
    def __init__(self,*,contract,tape_sha256,trade_date,max_active=100000,max_seen=1000000,max_pairs=100000,max_triples=100000):
        if type(max_triples) is not int or max_triples<1:raise ValueError('triple budget required')
        self.join=AsOfJoin(contract=contract,tape_sha256=tape_sha256,trade_date=trade_date,max_active=max_active,max_seen=max_seen,max_pairs=max_pairs)
        self.max_pairs=max_pairs;self.max_triples=max_triples;self.poisoned=False
        self.peak_affected_pairs=0;self.peak_affected_triples=0;self.total_clocks=0
    def _affected(self,changed,*,pairs=True,triples=True):
        ps=set();ts=set();active=self.join.active
        for k in sorted(changed):
            s=active.get(k)
            if s is None:continue
            if pairs:
                for family in sorted(self.join.roots):
                    if family==k.family:continue
                    for other in _intersect(self.join.roots[family],s.lo2,s.hi2):
                        key=tuple(sorted((k,other.key)))
                        # Lowest changed component owns this intersection once.
                        if k!=min(set(key)&changed):continue
                        if len(ps)>=self.max_pairs:raise ValueError('pair budget exceeded; no partial output')
                        ps.add(key)
            if triples:
                for fams in TRIPLES:
                    if k.family not in fams:continue
                    f1,f2=sorted(fams-{k.family})
                    for a in _intersect(self.join.roots[f1],s.lo2,s.hi2):
                        lo,hi=max(s.lo2,a.lo2),min(s.hi2,a.hi2)
                        # Intersect a common band, not every pair of neighbors.
                        for b in _intersect(self.join.roots[f2],lo,hi):
                            key=tuple(sorted((k,a.key,b.key)))
                            if k!=min(set(key)&changed):continue
                            if len(ts)>=self.max_triples:raise ValueError('candidate triple budget exceeded; no truncation')
                            ts.add(key)
        return ps,ts
    def apply(self,clock,*,upserts=(),removals=()):
        if self.poisoned:raise ValueError('poisoned geometry counter; rebuild checkpoint')
        ups=tuple(upserts);rem=tuple(removals);changed={s.key for s in ups}|set(rem)
        try:
            oldp,oldt=self._affected(changed)
            new_pairs=self.join.apply(clock,upserts=ups,removals=rem)
            newp={tuple(sorted((p.left.key,p.right.key))) for p in new_pairs}
            _,newt=self._affected(changed,pairs=False)
            self.peak_affected_pairs=max(self.peak_affected_pairs,len(oldp),len(newp))
            self.peak_affected_triples=max(self.peak_affected_triples,len(oldt),len(newt))
            counts=Counter()
            for before,after in ((oldp,newp),(oldt,newt)):
                for action,keys in (('END',before-after),('START',after-before),('UPDATE',before&after)):
                    for key in keys:counts[action+':'+ '+'.join(sorted(k.family for k in key))]+=1
            self.total_clocks+=1;return counts
        except BaseException:
            self.poisoned=True;raise
