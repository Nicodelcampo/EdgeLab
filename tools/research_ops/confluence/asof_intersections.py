"""Synthetic-tested, target-free as-of interval join. NOT a detector or market loader.

Input adapters must provide immutable, genuinely available zone snapshots. This
module does not certify those declarations, interpret final detector objects,
read market files, authorize research or calculate outcomes. Price coordinates
are integer HALF ticks (including negative prices). Endpoints are CLOSED.

All mutations at a shared (ns, tape sequence) are one atomic observation batch.
Removals precede upserts; only the final batch state is joined. Cross-family
pairs are emitted when a component is new/versioned, not on every later tick.
Capacity failures are explicit; no output truncation. On a mutation failure the
instance is poisoned and must be reconstructed from verified checkpoints.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import hashlib
from typing import Iterator

FAMILIES=frozenset({'AVZP2','RACIMO','BT2','BT2A'})

@dataclass(frozen=True, order=True)
class Clock:
    ns: int
    sequence: int
    def __post_init__(self):
        if type(self.ns) is not int or self.ns<=0 or type(self.sequence) is not int or self.sequence<0:
            raise ValueError('positive integer ns and nonnegative tape sequence required')

@dataclass(frozen=True, order=True)
class ZoneKey:
    family: str
    config_sha256: str
    build_sha256: str
    zone_id: str
    def __post_init__(self):
        if self.family not in FAMILIES:raise ValueError('unknown family')
        for v in (self.config_sha256,self.build_sha256):
            if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v):raise ValueError('SHA256 required')
        if not isinstance(self.zone_id,str) or not self.zone_id or len(self.zone_id)>256:raise ValueError('bounded zone ID required')

@dataclass(frozen=True)
class Snapshot:
    key: ZoneKey
    revision: int
    available: Clock
    recognized: Clock
    lo2: int
    hi2: int
    side: int=0
    def __post_init__(self):
        if not isinstance(self.key,ZoneKey) or not isinstance(self.available,Clock) or not isinstance(self.recognized,Clock):raise ValueError('typed identity/clocks required')
        if type(self.revision) is not int or self.revision<0:raise ValueError('nonnegative revision')
        if self.recognized>self.available:raise ValueError('recognition cannot be later than availability')
        if any(type(x) is not int for x in (self.lo2,self.hi2)) or self.hi2<self.lo2:raise ValueError('ordered integer half-tick geometry required')
        if type(self.side) is not int or self.side not in (-1,0,1):raise ValueError('orientation must be -1,0,+1')

@dataclass(frozen=True)
class Pair:
    left: Snapshot
    right: Snapshot
    observed: Clock
    lo2: int
    hi2: int
    relation: str
    orientation: str

# Deterministic augmented treap, keyed by (lower edge, full zone identity).
# Expected balanced work, not a hard worst-case O(log N) guarantee.
class _Node:
    __slots__=('snapshot','key','priority','left','right','max_hi')
    def __init__(self,s):
        self.snapshot=s;self.key=(s.lo2,s.key)
        self.priority=int.from_bytes(hashlib.sha256(repr(self.key).encode()).digest(),'big')
        self.left=self.right=None;self.max_hi=s.hi2

def _fix(n):
    if n:n.max_hi=max(n.snapshot.hi2,n.left.max_hi if n.left else n.snapshot.hi2,n.right.max_hi if n.right else n.snapshot.hi2)
    return n

def _merge(a,b):
    if not a:return b
    if not b:return a
    if (a.priority,a.key)<(b.priority,b.key):a.right=_merge(a.right,b);return _fix(a)
    b.left=_merge(a,b.left);return _fix(b)

def _split(n,key):
    if not n:return None,None
    if n.key<key:
        a,b=_split(n.right,key);n.right=a;return _fix(n),b
    a,b=_split(n.left,key);n.left=b;return a,_fix(n)

def _put(n,z):
    if not n:return z
    if z.key==n.key:raise ValueError('duplicate index identity')
    if (z.priority,z.key)<(n.priority,n.key):z.left,z.right=_split(n,z.key);return _fix(z)
    if z.key<n.key:n.left=_put(n.left,z)
    else:n.right=_put(n.right,z)
    return _fix(n)

def _delete(n,key):
    if not n:raise ValueError('missing index key')
    if key==n.key:return _merge(n.left,n.right)
    if key<n.key:n.left=_delete(n.left,key)
    else:n.right=_delete(n.right,key)
    return _fix(n)

def _intersect(n,lo,hi)->Iterator[Snapshot]:
    if not n or n.max_hi<lo:return
    if n.left and n.left.max_hi>=lo:yield from _intersect(n.left,lo,hi)
    if n.snapshot.lo2<=hi and n.snapshot.hi2>=lo:yield n.snapshot
    if n.key[0]<=hi:yield from _intersect(n.right,lo,hi)

def pair_of(a,b,clock):
    if b.key<a.key:a,b=b,a
    lo,hi=max(a.lo2,b.lo2),min(a.hi2,b.hi2)
    if hi<lo:raise ValueError('disjoint geometries')
    if a.lo2==b.lo2 and a.hi2==b.hi2:rel='IDENTICAL'
    elif (a.lo2<=b.lo2 and a.hi2>=b.hi2) or (b.lo2<=a.lo2 and b.hi2>=a.hi2):rel='CONTAINMENT'
    elif hi==lo:rel='EDGE_CONTACT'
    else:rel='PARTIAL_OVERLAP'
    orient='UNSPECIFIED' if not a.side or not b.side else ('SAME' if a.side==b.side else 'OPPOSED')
    return Pair(a,b,clock,lo,hi,rel,orient)

class AsOfJoin:
    """One natural contract/tape/same-session exposure scope, with explicit limits.

    A new session requires a new instance. This prototype deliberately does NOT
    implement cross-session carry, triples, price-arrival anchors or zone-negative
    classification. A checkpoint adapter must preserve inactive-ID tombstones and
    current revisions; an invalidated zone cannot silently resurrect.
    """
    def __init__(self,*,contract,tape_sha256,trade_date,max_active=100000,max_seen=1000000,max_pairs=100000):
        if not isinstance(contract,str) or not contract.strip():raise ValueError('natural contract required')
        if not isinstance(tape_sha256,str) or len(tape_sha256)!=64 or any(c not in '0123456789abcdef' for c in tape_sha256):raise ValueError('tape identity required')
        d=date.fromisoformat(trade_date)
        if trade_date!=d.isoformat() or d>=date(2026,10,1):raise ValueError('reserved/noncanonical session')
        for x in (max_active,max_seen,max_pairs):
            if type(x) is not int or x<1:raise ValueError('explicit positive capacities')
        if max_seen<max_active:raise ValueError('seen-ID budget cannot be below active budget')
        self.contract=contract;self.tape_sha256=tape_sha256;self.trade_date=trade_date
        self.max_active=max_active;self.max_seen=max_seen;self.max_pairs=max_pairs
        self.active={};self.seen=set();self.roots={f:None for f in FAMILIES};self.clock=None;self.poisoned=False
        self.query_hits=0
    def apply(self,clock,*,upserts=(),removals=()):
        if self.poisoned:raise ValueError('poisoned join; rebuild from verified checkpoint')
        if not isinstance(clock,Clock) or (self.clock is not None and clock<=self.clock):raise ValueError('strictly ordered atomic batches required')
        ups=tuple(upserts);rem=tuple(removals)
        if any(not isinstance(s,Snapshot) for s in ups) or any(not isinstance(k,ZoneKey) for k in rem):raise ValueError('typed mutations required')
        keys=[s.key for s in ups]
        if len(set(keys))!=len(keys) or len(set(rem))!=len(rem) or set(keys)&set(rem):raise ValueError('duplicate/conflicting batch mutation')
        if any(k not in self.active for k in rem):raise ValueError('unknown removal; no silent drop')
        new=0
        for s in ups:
            if s.available!=clock:raise ValueError('snapshot must become available at this batch clock')
            old=self.active.get(s.key)
            if old:
                if s.revision!=old.revision+1 or s.recognized!=old.recognized:raise ValueError('revision must advance exactly; recognition immutable')
            else:
                if s.key in self.seen:raise ValueError('inactive identity cannot resurrect')
                if s.revision!=0 or s.recognized!=clock:raise ValueError('new object is recognized NOW, not retroactively')
                new+=1
        if len(self.active)-len(rem)+new>self.max_active or len(self.seen)+new>self.max_seen:raise ValueError('capacity exceeded; shard/spill explicitly, never truncate')
        try:
            for k in sorted(rem):
                old=self.active.pop(k);self.roots[k.family]=_delete(self.roots[k.family],(old.lo2,k))
            for s in sorted(ups,key=lambda s:s.key):
                old=self.active.get(s.key)
                if old:self.roots[s.key.family]=_delete(self.roots[s.key.family],(old.lo2,s.key))
                self.active[s.key]=s;self.seen.add(s.key);self.roots[s.key.family]=_put(self.roots[s.key.family],_Node(s))
            pairs={}
            for s in sorted(ups,key=lambda s:s.key):
                for f in sorted(FAMILIES-{s.key.family}):
                    for other in _intersect(self.roots[f],s.lo2,s.hi2):
                        self.query_hits+=1
                        # Keys, not timestamps/config aliases, identify distinct observations.
                        key=tuple(sorted((s.key,other.key)))
                        if key not in pairs:
                            if len(pairs)>=self.max_pairs:raise ValueError('pair budget exceeded; no partial output')
                            pairs[key]=pair_of(s,other,clock)
            self.clock=clock
            return tuple(pairs[k] for k in sorted(pairs))
        except BaseException:
            self.poisoned=True
            raise
