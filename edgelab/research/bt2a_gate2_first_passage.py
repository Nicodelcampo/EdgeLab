"""Causal first-passage primitives for BT2A Gate 2."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence
import numpy as np

NS = 1_000_000_000
WEBB = np.array([-np.sqrt(1.5), -1, -np.sqrt(.5), np.sqrt(.5), 1, np.sqrt(1.5)])

@dataclass(frozen=True)
class FirstPassageResult:
    outcome: str
    score: int
    fill_idx: int
    end_idx: int
    cap_driver: str
    target_level_ticks: int
    stop_level_ticks: int
    first_touch_idx: int | None
    first_touch_ts_utc_ns: int | None
    first_touch_source_row: int | None
    touch_price_ticks: int | None
    ticks_to_touch: int | None
    seconds_to_touch: float | None
    def to_dict(self): return asdict(self)

def _arrays(price, ts, source, sessions):
    p=np.asarray(price,dtype=np.int64); t=np.asarray(ts,dtype=np.int64)
    r=np.asarray(source,dtype=np.int64); s=np.asarray(sessions)
    if not len(p) or not(len(p)==len(t)==len(r)==len(s)): raise ValueError("invalid tick arrays")
    if np.any(t[1:]<t[:-1]): raise ValueError("ts_utc_ns regresses")
    if np.any(r[1:]<=r[:-1]): raise ValueError("source_row must be strictly increasing")
    return p,t,r,s

def session_last_indices(sessions):
    s=np.asarray(sessions); n=len(s)
    if not n: return np.array([],dtype=np.int64)
    cuts=np.flatnonzero(s[1:]!=s[:-1])+1
    starts=np.r_[0,cuts]; stops=np.r_[cuts,n]; out=np.empty(n,dtype=np.int64)
    for lo,hi in zip(starts,stops): out[lo:hi]=hi-1
    return out

def horizon_endpoints(ts,sessions,*,tick_cap,clock_cap_seconds):
    t=np.asarray(ts,dtype=np.int64); s=np.asarray(sessions); n=len(t)
    if len(s)!=n or (tick_cap is None and clock_cap_seconds is None): raise ValueError("invalid horizon input")
    idx=np.arange(n,dtype=np.int64); last=session_last_indices(s)
    choices=[last]; names=["session"]; priority=[2]
    if tick_cap is not None:
        if int(tick_cap)<1: raise ValueError("tick_cap must be >= 1")
        choices.append(idx+int(tick_cap)); names.append("ticks"); priority.append(0)
    if clock_cap_seconds is not None:
        if float(clock_cap_seconds)<=0: raise ValueError("clock cap must be positive")
        deadline=t+int(round(float(clock_cap_seconds)*NS))
        choices.append(np.searchsorted(t,deadline,side="right")-1); names.append("clock"); priority.append(1)
    matrix=np.vstack(choices); minimum=matrix.min(axis=0); driver=np.full(n,"session",dtype=object)
    for rank in (2,1,0):
        for row,p in enumerate(priority):
            if p==rank: driver[matrix[row]==minimum]=names[row]
    return np.maximum(idx,np.minimum(minimum,last)).astype(np.int64),driver

def horizon_endpoint(ts,sessions,*,fill_idx,tick_cap,clock_cap_seconds):
    ends,drivers=horizon_endpoints(ts,sessions,tick_cap=tick_cap,clock_cap_seconds=clock_cap_seconds)
    if not 0<=int(fill_idx)<len(ends): raise IndexError("fill_idx outside tick stream")
    return int(ends[int(fill_idx)]),str(drivers[int(fill_idx)])

class _Tree:
    def __init__(self,n,inf):
        size=1
        while size<n: size*=2
        self.size=size; self.inf=int(inf); self.data=np.full(2*size,self.inf,dtype=np.int64)
    def update(self,pos,value):
        node=int(pos)+self.size; self.data[node]=int(value); node//=2
        while node:
            self.data[node]=min(self.data[2*node],self.data[2*node+1]); node//=2
    def query(self,left,right):
        if left>right: return self.inf
        left+=self.size; right+=self.size; answer=self.inf
        while left<=right:
            if left&1: answer=min(answer,int(self.data[left])); left+=1
            if not right&1: answer=min(answer,int(self.data[right])); right-=1
            left//=2; right//=2
        return answer

def next_barrier_touch_indices(price,sessions,*,barrier_ticks):
    p=np.asarray(price,dtype=np.int64); s=np.asarray(sessions); n=len(p); b=int(barrier_ticks)
    if len(s)!=n or b<1: raise ValueError("invalid barrier input")
    up=np.full(n,-1,dtype=np.int64); down=np.full(n,-1,dtype=np.int64)
    cuts=np.flatnonzero(s[1:]!=s[:-1])+1 if n>1 else np.array([],dtype=np.int64)
    for lo,hi in zip(np.r_[0,cuts],np.r_[cuts,n]):
        segment=p[lo:hi]; low=int(segment.min()); high=int(segment.max()); inf=n+1; tree=_Tree(high-low+1,inf)
        for idx in range(int(hi)-1,int(lo)-1,-1):
            pos=int(p[idx])-low; u=pos+b; d=pos-b
            uh=tree.query(u,high-low) if u<=high-low else inf
            dh=tree.query(0,d) if d>=0 else inf
            if uh!=inf: up[idx]=uh
            if dh!=inf: down[idx]=dh
            tree.update(pos,idx)
    return up,down

def first_passage_scores_fast(price,ts,sessions,*,fill_indices,directions,barrier_ticks,tick_cap,clock_cap_seconds,precomputed_touches=None,precomputed_endpoints=None):
    p=np.asarray(price,dtype=np.int64); idx=np.asarray(fill_indices,dtype=np.int64); direction=np.asarray(directions,dtype=np.int8)
    if len(idx)!=len(direction) or np.any((idx<0)|(idx>=len(p))): raise ValueError("invalid event vectors")
    if np.any(~np.isin(direction,(-1,1))): raise ValueError("directions must be -1 or +1")
    up,down=precomputed_touches if precomputed_touches is not None else next_barrier_touch_indices(p,sessions,barrier_ticks=barrier_ticks)
    ends=precomputed_endpoints
    if ends is None: ends,_=horizon_endpoints(ts,sessions,tick_cap=tick_cap,clock_cap_seconds=clock_cap_seconds)
    end=np.asarray(ends)[idx]; target=np.where(direction>0,up[idx],down[idx]); stop=np.where(direction>0,down[idx],up[idx])
    target_ok=(target>=0)&(target<=end); stop_ok=(stop>=0)&(stop<=end)
    if np.any(target_ok&stop_ok&(target==stop)): raise AssertionError("simultaneous scalar barrier touch")
    out=np.zeros(len(idx),dtype=np.int8)
    out[target_ok&(~stop_ok|(target<stop))]=1; out[stop_ok&(~target_ok|(stop<target))]=-1
    return out

def first_passage(price,ts,source,sessions,*,fill_idx,direction,target_ticks,stop_ticks,tick_cap=None,clock_cap_seconds=None):
    p,t,r,s=_arrays(price,ts,source,sessions); i=int(fill_idx); d=int(direction)
    if d not in (-1,1) or min(int(target_ticks),int(stop_ticks))<1: raise ValueError("invalid event")
    end,driver=horizon_endpoint(t,s,fill_idx=i,tick_cap=tick_cap,clock_cap_seconds=clock_cap_seconds)
    target=int(p[i])+d*int(target_ticks); stop=int(p[i])-d*int(stop_ticks); touch=None; outcome="TIMEOUT"
    for j in range(i+1,end+1):
        px=int(p[j]); hit_t=px>=target if d>0 else px<=target; hit_s=px<=stop if d>0 else px>=stop
        if hit_t: outcome,touch="TP_FIRST",j; break
        if hit_s: outcome,touch="SL_FIRST",j; break
    score=1 if outcome=="TP_FIRST" else -1 if outcome=="SL_FIRST" else 0
    if touch is None: return FirstPassageResult(outcome,score,i,end,driver,target,stop,None,None,None,None,None,None)
    return FirstPassageResult(outcome,score,i,end,driver,target,stop,touch,int(t[touch]),int(r[touch]),int(p[touch]),touch-i,float((t[touch]-t[i])/NS))

def first_passage_scores(price,ts,source,sessions,*,fill_indices,directions,target_ticks,stop_ticks,tick_cap=None,clock_cap_seconds=None):
    idx=np.asarray(fill_indices); dirs=np.asarray(directions)
    if len(idx)!=len(dirs): raise ValueError("event vectors differ")
    return np.array([first_passage(price,ts,source,sessions,fill_idx=int(i),direction=int(d),target_ticks=target_ticks,stop_ticks=stop_ticks,tick_cap=tick_cap,clock_cap_seconds=clock_cap_seconds).score for i,d in zip(idx,dirs)],dtype=np.int8)

def summarize_scores(scores: Iterable[int]):
    x=np.asarray(list(scores),dtype=np.int8)
    if not len(x) or np.any(~np.isin(x,(-1,0,1))): raise ValueError("invalid score vector")
    tp=int(np.sum(x==1)); sl=int(np.sum(x==-1)); timeout=int(np.sum(x==0)); resolved=tp+sl; n=len(x)
    return {"n":n,"n_tp_first":tp,"n_sl_first":sl,"n_timeout":timeout,"p_tp_first":tp/n,"p_sl_first":sl/n,"p_timeout":timeout/n,"p_tp_given_resolved":tp/resolved if resolved else float("nan"),"theta_fp":float(x.mean())}

def wild_cluster_test(values: Iterable[float],*,replications,seed,confidence=.95):
    x=np.asarray(list(values),dtype=float)
    if len(x)<2 or not np.all(np.isfinite(x)): raise ValueError("need >=2 finite sessions")
    point=float(x.mean()); residual=x-point; rng=np.random.default_rng(int(seed)); ci=np.empty(replications); null=np.empty(replications)
    for b in range(replications):
        w=rng.choice(WEBB,size=len(x)); ci[b]=point+np.mean(w*residual); null[b]=np.mean(w*x)
    alpha=(1-confidence)/2; p=(1+np.sum(np.abs(null)>=abs(point)))/(replications+1)
    return {"point":point,"lower":float(np.quantile(ci,alpha)),"upper":float(np.quantile(ci,1-alpha)),"p_two_sided":float(p),"n_sessions":len(x),"replications":replications}

def holm_adjust(p_values: Sequence[float]):
    p=np.asarray(p_values,dtype=float)
    if p.ndim!=1 or np.any((p<0)|(p>1)|~np.isfinite(p)): raise ValueError("invalid p-values")
    order=np.argsort(p,kind="stable"); sorted_out=np.empty(len(p)); running=0.
    for rank,idx in enumerate(order): running=max(running,(len(p)-rank)*float(p[idx])); sorted_out[rank]=min(1.,running)
    out=np.empty(len(p)); out[order]=sorted_out; return out.tolist()
