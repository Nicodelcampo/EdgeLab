"""Per-config causal exposure index, cached across all18 AVZ/BigTrap pairs.

Native history is untouched. This measurement keeps same-session births for
<=600s, with actual native removals for BigTrap. AVZ recognition != liveness.
Mirror control preserves birth time/width/distance at birth and removal time;
it is SAME-TRIGGER MIRRORED geometry, NOT an independent zone-free creator.
"""
from bisect import bisect_left,bisect_right,insort
from collections import Counter
from datetime import datetime,date
import heapq,math
import numpy as np
from .asof_intersections import Clock,Snapshot,ZoneKey,_Node,_put,_delete,_intersect,pair_of
from .detector_capture import Capture
from .zone_context import union_cells,union_segments,joint_cells,signed_gap
from .build_target_free_pilot import digest

FAMILY={'avolzonepoi2':'AVZP2','bigtrap2':'BT2','bigtrap2absorption':'BT2A'}
RELATIONS=('DISJOINT','EDGE_CONTACT','PARTIAL_OVERLAP','CONTAINMENT','IDENTICAL')

class ExposureIndex:
    def __init__(self,config,trade_date,*,mirror=False,max_active=20000,max_seen=200000,max_hits=20000,max_total_hits=20000000,age_seconds=600):
        d=date.fromisoformat(trade_date)
        if d>=date(2026,10,1) or d.isoformat()!=trade_date:raise ValueError('bound preholdout exposure session')
        for v in (max_active,max_seen,max_hits,max_total_hits,age_seconds):
            if type(v) is not int or v<1:raise ValueError('positive exposure budgets')
        if age_seconds!=600:raise ValueError("fixed 600s exposure measurement scope")
        if max_seen<max_active or type(mirror) is not bool:raise ValueError('explicit exposure policy')
        self.family=FAMILY[config['indicator']];self.config=config['config_sha256'];self.mirror=mirror
        self.output_config=digest({'source':self.config,'virtual':'BIRTH_MIDQUOTE_REFLECTION'}) if mirror else self.config
        self.start=int(datetime.fromisoformat(trade_date+'T22:00:00+00:00').timestamp())*10**9-86400*10**9;self.end=self.start+86400*10**9
        self.max_active=max_active;self.max_seen=max_seen;self.max_hits=max_hits;self.max_total_hits=max_total_hits;self.age_ns=age_seconds*10**9
        self.active={};self.seen=set();self.root=None;self.low=[];self.high=[];self.width=0;self.expirations=[]
        self.clock=self.anchor=None;self.poisoned=False;self.hits=0;self.counts=Counter()
    def _live(self):
        if self.poisoned:raise ValueError('poisoned exposure index')
    def _key(self,k):return ZoneKey(k.family,self.output_config,k.build_sha256,k.zone_id)
    def _drop(self,k):
        s=self.active.pop(k);self.root=_delete(self.root,(s.lo2,k))
        for arr,v in ((self.low,s.lo2),(self.high,s.hi2)):
            j=bisect_left(arr,v)
            if j>=len(arr) or arr[j]!=v:raise ValueError('exposure endpoint drift')
            arr.pop(j)
        self.width-=s.hi2-s.lo2+1
    def _expire(self,c):
        while self.expirations and self.expirations[0][0]<c.ns:
            _,k=heapq.heappop(self.expirations)
            if k in self.active:self._drop(k);self.counts['measurement_age_end']+=1
    def apply(self,c,records,*,midpoint2):
        self._live()
        if not isinstance(c,Clock) or not self.start<=c.ns<self.end or (self.clock is not None and c<=self.clock) or (self.anchor is not None and c<=self.anchor):raise ValueError('strict bound exposure batches before anchors')
        if type(midpoint2) is not int:raise ValueError('observed birth midpoint')
        records=tuple(records)
        for r,primary in records:
            if not isinstance(r,Capture) or r.clock!=c or r.key.family!=self.family or r.key.config_sha256!=self.config or type(primary) is not bool or r.kind not in ('BIRTH','REMOVE','TOUCH','CLASSIFY'):raise ValueError('typed native config event batch')
        try:
            self._expire(c)
            for r,primary in records:
                k=self._key(r.key);self.counts['native_'+r.kind]+=1
                if r.kind=='BIRTH':
                    if not primary:self.counts['nonprimary_birth']+=1;continue
                    if k in self.seen:raise ValueError('duplicate exposure birth/no resurrection')
                    lo,hi=r.lo2,r.hi2;side=r.side
                    if self.mirror:lo,hi=2*midpoint2-hi,2*midpoint2-lo;side=-side
                    s=Snapshot(k,0,c,c,lo,hi,side);self.active[k]=s;self.seen.add(k)
                    self.root=_put(self.root,_Node(s));insort(self.low,lo);insort(self.high,hi);self.width+=hi-lo+1
                    heapq.heappush(self.expirations,(c.ns+self.age_ns,k));self.counts['primary_birth']+=1
                    if self.mirror and (lo,hi)==(r.lo2,r.hi2):self.counts['mirror_same_birth_band']+=1
                elif r.kind=='REMOVE':
                    if k in self.active:self._drop(k);self.counts['native_primary_remove']+=1
                    else:self.counts['nonprimary_or_already_aged_remove']+=1
                # Native TOUCH/CLASSIFY are diagnostics only, never backfilled into physical arrival.
            if len(self.active)>self.max_active or len(self.seen)>self.max_seen:raise ValueError('exposure capacity no truncation')
            self.clock=c
        except BaseException:self.poisoned=True;raise
    def _query(self,lo,hi,work):
        out=[]
        for s in _intersect(self.root,lo,hi):
            work[0]+=1
            if work[0]>self.max_hits or self.hits+work[0]>self.max_total_hits:self.poisoned=True;raise ValueError('exposure query budget')
            out.append(s)
        return out
    def observe(self,c,*,midpoint2,prior_clock,prior_midpoint2,prior_print2,print2,radius_ticks,tape,anchor_index,prior_index,prints):
        self._live()
        if not isinstance(c,Clock) or not isinstance(prior_clock,Clock) or not self.start<=prior_clock.ns<=c.ns<self.end or prior_clock>=c or (self.clock and self.clock>c) or (self.anchor and c<=self.anchor):raise ValueError('bound strictly ordered causal exposure anchor')
        if any(type(v) is not int for v in (midpoint2,prior_midpoint2,prior_print2,print2,radius_ticks,anchor_index,prior_index)) or radius_ticks<1 or not 0<=prior_index<anchor_index<len(tape.sequence):raise ValueError('bound observed endpoints and radius')
        if (int(tape.ts_ns[anchor_index]),int(tape.sequence[anchor_index]))!=(c.ns,c.sequence) or (int(tape.ts_ns[prior_index]),int(tape.sequence[prior_index]))!=(prior_clock.ns,prior_clock.sequence):raise ValueError('exposure clock/tape identity')
        try:
            self._expire(c);radius=2*radius_ticks;lo=midpoint2-radius;hi=midpoint2+radius;domain=hi-lo+1;work=[0]
            local=self._query(lo,hi,work);inside=[s for s in local if s.lo2<=midpoint2<=s.hi2]
            near=None
            if inside:near=min(inside,key=lambda s:(s.hi2-s.lo2,s.key))
            elif self.active:
                a=bisect_right(self.high,midpoint2)-1;b=bisect_left(self.low,midpoint2);ds=[]
                if a>=0:ds.append(midpoint2-self.high[a])
                if b<len(self.low):ds.append(self.low[b]-midpoint2)
                dist=min(ds);cs=[]
                for p in (midpoint2-dist,midpoint2+dist):cs.extend(self._query(p,p,work))
                near=min(cs,key=lambda s:(abs(signed_gap(s,midpoint2)),s.hi2-s.lo2,s.key))
            intervals=union_segments([(max(lo,s.lo2),min(hi,s.hi2)) for s in local])
            density=(math.log1p(len(self.active)),math.log1p(self.width),union_cells(intervals)/domain,math.log1p(len(local)))
            age=(0.,0.,0.);gap=0.;arr=(0.,)*7
            if near:
                seconds=(c.ns-near.recognized.ns)/10**9;age=tuple(float(v) for v in (seconds<=20,20<seconds<=120,120<seconds<=600))
                gap=math.tanh(signed_gap(near,midpoint2)/radius);old=near.available<=prior_clock
                # Strictly after birth: even same-ns later sequences remain eligible, creator print excluded.
                birth=int(np.searchsorted(tape.sequence,near.available.sequence,side='right'))
                lifetime=prints.query(near.lo2,near.hi2,left=birth,right=anchor_index+1)
                window=prints.query(near.lo2,near.hi2,left=max(birth,prior_index),right=anchor_index+1)
                count=lifetime['observed_print_count'];first=lifetime['first_observed_index'];last=lifetime['last_observed_index']
                first_recent=first is not None and int(tape.ts_ns[first])>c.ns-20*10**9
                observed_return=count>=2 and last-first+1>count
                g1=signed_gap(near,prior_print2);g2=signed_gap(near,print2)
                gapthrough=old and g1*g2<0 and window['observed_print_count']==0
                reduction=math.tanh((abs(signed_gap(near,prior_midpoint2))-abs(signed_gap(near,midpoint2)))/radius) if old else 0.
                arr=(reduction,float(old),math.log1p(count),float(first_recent),float(observed_return),float(gapthrough),float(np.sign(signed_gap(near,prior_midpoint2))) if old else 0.)
            self.anchor=c;self.hits+=work[0]
            return {'density':density,'gap':gap,'age':age,'arrival':arr,'near':near,'inside':bool(inside),'segments':intervals,'domain_cells':domain,'age_seconds':None if near is None else seconds}
        except BaseException:
            self.poisoned=True
            raise

def pair_features(left,right,c,row):
    a=left['near'];b=right['near'];present=a is not None and b is not None
    relation=pair_of(a,b,c).relation if present and a.hi2>=b.lo2 and b.hi2>=a.lo2 else 'DISJOINT'
    rel=tuple(float(present and relation==v) for v in RELATIONS)
    joint=joint_cells(left['segments'],right['segments'])/left['domain_cells']
    both=float(left['inside'] and right['inside']);order=math.tanh((left['age_seconds']-right['age_seconds'])/600) if present else 0.
    side=float(b.side) if b else 0.
    g=(left['gap'],right['gap'],joint,both)+left['age']+right['age']+rel+(order,side)
    p=row['windows']['20'];pressure=math.tanh(math.log(max(p['pressure_ratio'],1e-12)));rate=math.tanh(math.log(max(p['trade_count_ratio'],1e-12)));progress=math.tanh(p['directed_progress_ticks']/4)
    interactions=(pressure*joint,progress*both,rate*left['age'][0]*right['age'][0],float(p['direction_from_prior'])*side*max(left['arrival'][4],right['arrival'][4]))
    #17geometry +14arrival +4interactions; derived features only before future labels.
    return left['density']+right['density']+g+left['arrival']+right['arrival']+interactions,{'both_present':present,'inside_both':bool(both),'relation':relation if present else 'MISSING_COMPONENT'}
