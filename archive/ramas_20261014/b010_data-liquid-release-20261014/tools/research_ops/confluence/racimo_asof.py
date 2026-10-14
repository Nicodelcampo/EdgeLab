"""Causal observation adapter for the pinned AVZP2 racimo rule; no access authority.

The copied rule below is verbatim UTF-8 function source from foundation commit
f397a318be8b0acf68789070fe8064d83e172f7d. It deliberately preserves legacy
cross-session membership and geometry. The adapter reports that carry, does not
silently reset/redefine it. No loader, labels, quotes or NT8 parity certification.
Birth inputs must be immutable detector creations, not mutable final-zone tables.
"""
from dataclasses import dataclass
from datetime import date
import hashlib
import ast,inspect,bisect
from functools import lru_cache
from .asof_intersections import Clock,ZoneKey,Snapshot

LEGACY_FUNCTION_SHA256="846aab2ee62074f91de17a64bf8b7ade3efbb5a842cf8ba36a9677ede6a33efe"
LEGACY_SOURCE_COMMIT="f397a318be8b0acf68789070fe8064d83e172f7d"

def _racimo(nz, zones, clusters, b, p):
    if p["racimo_min"] <= 1:
        return
    cand = []
    for z in reversed(zones):
        if nz["bar"] - z["bar"] > p["racimo_bars"]:
            break
        cand.append(z)
    cand.append(nz)
    A = int(p["racimo_altura_ticks"])
    best = None
    for bz in cand:
        lo, hi = bz["low_tick"], bz["low_tick"] + A - 1
        if nz["low_tick"] < lo or nz["high_tick"] > hi:
            continue
        inside = [z for z in cand if z["low_tick"] >= lo and z["high_tick"] <= hi]
        if best is None or len(inside) > len(best):
            best = inside
    if best is None or len(best) < p["racimo_min"]:
        return
    clo = min(m["low_tick"] for m in best); chi = max(m["high_tick"] for m in best); cst = min(m["bar"] for m in best)
    cl = None
    for m in best:
        r = m.get("rac")
        if r is not None and max(chi, r["high"]) - min(clo, r["low"]) + 1 <= A:
            cl = r
            break
    if cl is None:
        cl = dict(start=cst, low=clo, high=chi, bar=b, start0=cst, low0=clo, high0=chi)   # *0 = snapshot al formarse
        clusters.append(cl)
    else:
        cl["start"] = min(cl["start"], cst); cl["low"] = min(cl["low"], clo); cl["high"] = max(cl["high"], chi)
    for m in best:
        if m.get("rac") is None:
            m["rac"] = cl
    for m in best:
        if m["racimo_bar"] < 0:
            m["racimo_bar"] = b

def _best_members(cand,nz,A):
    """Same maximum-inside band/tie order; sweep + Fenwick, no quadratic scans."""
    lows={z['low_tick'] for z in cand if z['low_tick']<=nz['low_tick'] and z['low_tick']+A-1>=nz['high_tick']}
    if not lows:return None
    highs=sorted({z['high_tick'] for z in cand});ranks={v:i+1 for i,v in enumerate(highs)};tree=[0]*(len(highs)+1)
    ordered=sorted(cand,key=lambda z:z['low_tick'],reverse=True);pos=0;counts={}
    for lo in sorted(lows,reverse=True):
        while pos<len(ordered) and ordered[pos]['low_tick']>=lo:
            k=ranks[ordered[pos]['high_tick']]
            while k<len(tree):tree[k]+=1;k+=k&-k
            pos+=1
        k=bisect.bisect_right(highs,lo+A-1);n=0
        while k:n+=tree[k];k-=k&-k
        counts[lo]=n
    best_lo=None;best_n=-1
    # Candidate order is legacy reversed history + new zone, NOT price order.
    for z in cand:
        lo=z['low_tick']
        if lo in counts and counts[lo]>best_n:best_lo=lo;best_n=counts[lo]
    return [z for z in cand if z['low_tick']>=best_lo and z['high_tick']<=best_lo+A-1]

@lru_cache(maxsize=1)
def _fast_rule():
    raw=inspect.getsource(_racimo)
    if hashlib.sha256(raw.encode()).hexdigest()!=LEGACY_FUNCTION_SHA256:raise ValueError('legacy racimo source drift')
    fn=ast.parse(raw).body[0];count=0
    for i,n in enumerate(fn.body):
        if isinstance(n,ast.For) and ast.unparse(n.target)=='bz' and ast.unparse(n.iter)=='cand':
            fn.body[i]=ast.parse('best=_best_members(cand,nz,A)').body[0];count+=1
    if count!=1:raise ValueError('racimo selection hook census drift')
    fn.name='_racimo_fast';tree=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(tree);env={'_best_members':_best_members}
    exec(compile(tree,'<pinned-racimo-fast-selection>','exec'),env);return env['_racimo_fast']

@dataclass(frozen=True)
class Creation:
    zone_id: str
    bar: int
    low_tick: int
    high_tick: int
    trade_date: str
    available: Clock
    def __post_init__(self):
        if not isinstance(self.zone_id,str) or not self.zone_id or len(self.zone_id)>256:raise ValueError('bounded creation identity required')
        if any(type(v) is not int for v in (self.bar,self.low_tick,self.high_tick)) or self.bar<0 or self.high_tick<self.low_tick:raise ValueError('valid integer bar/geometry required')
        d=date.fromisoformat(self.trade_date)
        if self.trade_date!=d.isoformat() or d>=date(2026,10,1):raise ValueError('reserved session')
        if not isinstance(self.available,Clock):raise ValueError('typed tape availability required')

@dataclass(frozen=True)
class RacimoObservation:
    snapshot: Snapshot
    member_ids: tuple[str,...]
    member_trade_dates: tuple[str,...]
    formation_start_bar: int
    legacy_first_recognition_bar: int
    legacy_member_state_changed: bool
    spans_sessions: bool

class _ObservedZone(dict):
    """Observe membership assignments without changing the pinned rule."""
    def __init__(self,*args,on_join,**kwargs):
        super().__init__(*args,**kwargs);self.on_join=on_join
    def __setitem__(self,key,value):
        super().__setitem__(key,value)
        if key=='rac' and value is not None:self.on_join(self,value)

class RacimoTape:
    """Whole-contract causal state. No changes to detection or legacy racimo rule.

    Each detector batch has one bar, session and tape clock. More than one zone
    at that bar is processed in original detector order; DO NOT sort by price.
    Stable racimo IDs start at creation, geometry revisions available only now.
    Bounded seen history; overflow stops instead of dropping inputs. This first
    prototype indexes membership assignments and emits only touched racimos.
    Candidate selection uses an exact sweep/Fenwick implementation by default;
    the pinned rule remains available for reference. Complete membership
    snapshots still cost O(member count); no Kaggle speed claim.
    """
    def __init__(self,*,params,config_sha256,build_sha256,max_zones=100000,optimized_candidates=True):
        if set(params)!={'racimo_min','racimo_bars','racimo_altura_ticks'} or any(type(v) is not int for v in params.values()):raise ValueError('exact racimo parameter declaration required')
        if params['racimo_min']<2 or params['racimo_bars']<1 or params['racimo_altura_ticks']<1:raise ValueError('positive racimo geometry/recognition rule required')
        ZoneKey('RACIMO',config_sha256,build_sha256,'0')
        if type(max_zones) is not int or max_zones<1:raise ValueError('explicit history budget required')
        if type(optimized_candidates) is not bool:raise ValueError('explicit racimo implementation mode')
        if hashlib.sha256(inspect.getsource(_racimo).encode()).hexdigest()!=LEGACY_FUNCTION_SHA256:raise ValueError('legacy racimo source drift')
        self.rule=_fast_rule() if optimized_candidates else _racimo
        self.params=dict(params);self.config=config_sha256;self.build=build_sha256;self.max_zones=max_zones
        self.zones=[];self.clusters=[];self.ids=set();self.clock=None;self.last_bar=-1;self.last_session=None
        self.cluster_ids={};self.published={};self.members={};self.cluster_objects={};self.poisoned=False
    def _joined(self,member,cluster):
        # Old zones may receive membership NOW. Never capture their birth
        # batch's clock in a per-zone closure.
        obj=id(cluster)
        if obj not in self.cluster_ids:
            self.cluster_ids[obj]=(str(len(self.cluster_ids)),self.pending_clock);self.members[obj]={};self.cluster_objects[obj]=cluster
        self.members[obj][member['zone_id']]=member;self.touched.add(obj)
    def observe_batch(self,creations):
        if self.poisoned:raise ValueError('poisoned adapter')
        zs=tuple(creations)
        if not zs:raise ValueError('explicit nonempty detector creation batch required')
        if any(not isinstance(z,Creation) for z in zs):raise ValueError('typed creation snapshots required')
        c=zs[0].available;bar=zs[0].bar;session=zs[0].trade_date
        if any((z.available,z.bar,z.trade_date)!=(c,bar,session) for z in zs):raise ValueError('one atomic detector bar/clock/session batch')
        if (self.clock is not None and c<=self.clock) or bar<=self.last_bar:raise ValueError('strict batch/bar order')
        if self.last_session and session<self.last_session:raise ValueError('session order')
        ids=[z.zone_id for z in zs]
        if len(set(ids))!=len(ids) or self.ids.intersection(ids):raise ValueError('duplicate creation identity')
        if len(self.zones)+len(zs)>self.max_zones:raise ValueError('history budget exceeded; do not discard old state silently')
        self.touched=set();self.pending_clock=c
        try:
            for z in zs:
                d=_ObservedZone(bar=z.bar,low_tick=z.low_tick,high_tick=z.high_tick,racimo_bar=-1,rac=None,
                       zone_id=z.zone_id,trade_date=z.trade_date,on_join=self._joined)
                self.rule(d,self.zones,self.clusters,bar,self.params);self.zones.append(d);self.ids.add(z.zone_id)
                if d['rac'] is not None:self.touched.add(id(d['rac']))
            # The pinned rule changes at most the racimo assigned to the new
            # zone. Index assignment deltas instead of scanning every old zone.
            out=[]
            for obj in sorted(self.touched,key=lambda obj:int(self.cluster_ids[obj][0])):
                k=self.cluster_objects[obj];ms=list(self.members[obj].values())
                cid,born=self.cluster_ids[obj]
                mids=tuple(sorted(z['zone_id'] for z in ms));dates=tuple(sorted(set(z['trade_date'] for z in ms)))
                signature=(k['start'],k['low'],k['high'],mids)
                prev=self.published.get(obj)
                if prev and prev[0]==signature:continue
                rev=prev[1]+1 if prev else 0
                s=Snapshot(ZoneKey('RACIMO',self.config,self.build,cid),rev,c,born,2*k['low'],2*k['high'])
                out.append(RacimoObservation(s,mids,dates,k['start'],k['bar'],bool(prev and prev[0][3]!=mids),len(dates)>1))
                self.published[obj]=(signature,rev)
            self.clock=c;self.last_bar=bar;self.last_session=session
            return tuple(out)
        except BaseException:
            self.poisoned=True;raise
