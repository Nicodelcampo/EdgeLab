"""Causal, fixed-threshold feature gates; exact joint real/control mask collapse."""
import numpy as np
GATE_ORDER=['speed','efficiency','flow','revisits','volume','density','gaps']
def gate_masks(a):
 n=len(a['dedup75']);all_=np.ones(n,bool)
 def x(k):return np.asarray(a[k],float)
 speed=x('speed_ratio');eff=x('return_efficiency');flow=x('return_imbalance_proxy_toward');coverage=x('proxy_coverage')>=.8;vis=x('visits1');vol=x('volume_inside_fraction');den=x('return_bars_per_tick');gap=x('prior_gap_count')
 return [[all_,speed>=1,speed<1],[all_,eff>=.5,eff>=.75],[all_,(flow>0)&coverage,(flow>=.25)&coverage,(flow<0)&coverage,(flow<=-.25)&coverage],[all_,vis>=5,vis>=10,vis>=20,vis>=50],[all_,vol>=.25,vol>=.5],[all_,den<=.5,den<=1,den>1],[all_,gap==0]]
def collapse(a):
 choices=gate_masks(a);start=np.asarray(a['dedup75'])==1;states={np.packbits(start).tobytes():(start,0,1)}
 for choices0 in choices:
  nxt={}
  for mask,code,multiplicity in states.values():
   for j,g in enumerate(choices0):
    m=mask&g;key=np.packbits(m).tobytes();candidate=code*len(choices0)+j
    if key in nxt:
     old,oldcode,cnt=nxt[key];nxt[key]=(old,min(candidate,oldcode),cnt+multiplicity)
    else:nxt[key]=(m,candidate,multiplicity)
  states=nxt
 assert sum(x[2] for x in states.values())==5400
 return list(states.values())
def matched(day,stratum,origin,win,selected,nd):
 """Identical strata use min real/control counts; whole session numerator and weight."""
 keep=selected;ns=int(stratum.max())+1 if len(stratum) else 0
 nr=np.bincount(stratum[keep&(origin==0)],minlength=ns);nc=np.bincount(stratum[keep&(origin==1)],minlength=ns);wr=np.bincount(stratum[keep&(origin==0)],weights=win[keep&(origin==0)],minlength=ns);wc=np.bincount(stratum[keep&(origin==1)],weights=win[keep&(origin==1)],minlength=ns);common=(nr>0)&(nc>0);weight=np.minimum(nr,nc)[common];delta=wr[common]/nr[common]-wc[common]/nc[common]
 # All entries of a stratum share their session; reject any inconsistent caller.
 first=np.full(ns,-1,np.int64);first[stratum]=day
 assert np.array_equal(first[stratum],day), 'STRATUM_CROSSES_SESSIONS'
 numerator=np.bincount(first[common],weights=weight*delta,minlength=nd);weights=np.bincount(first[common],weights=weight,minlength=nd)
 return numerator,weights,int(common.sum())
def influence(numerator,weight):
 n=weight.sum()
 if n<=0:return np.nan,np.nan,np.full(len(weight),np.nan)
 point=numerator.sum()/n;score=(numerator-point*weight)/n;se=np.sqrt(len(weight)/(len(weight)-1)*np.sum(score**2)) if len(weight)>1 else np.nan
 return point,se,score
