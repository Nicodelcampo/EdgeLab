"""All1260 original rules: first departure, tick/height distance, entry endpoints, bars/seconds horizons."""
import numpy as np
from numba import njit
@njit(cache=True)
def trigger(px,ts,anchor,stop,low,high,D,q,gap=10000000000):
 if not low<=px[anchor]<=high:return (0,-1,0,0)
 ex=-1
 for i in range(anchor+1,stop):
  if ts[i]-ts[i-1]>gap:return (9,-1,0,0)
  if px[i]>high or px[i]<low:ex=i;break
 if ex<0:return (1,-1,0,0)
 side=1 if px[ex]>high else -1;edge=high if side>0 else low;peak=side*(px[ex]-edge)
 for i in range(ex+1,stop):
  if ts[i]-ts[i-1]>gap:return (9,-1,side,peak)
  x=side*(px[i]-edge)
  if x<=0:return (3,-1,side,peak)
  if x>peak:peak=x
  if peak>=D and x<=peak*(1-q):return (4,i,side,peak)
 return (2,-1,side,peak)
@njit(cache=True)
def outcomes(px,ts,bar,tr,stop,low,high,side,endpoint,hu,hv,gap=10000000000):
 edge=high if side>0 else low;target=edge if endpoint==0 else edge-side if endpoint==1 else low-1 if side>0 else high+1;dist=abs(px[tr]-target);opp=px[tr]+side*dist
 result=np.full(len(hu),8,np.int64);pending=np.ones(len(hu),np.bool_);left=len(hu)
 for j in range(tr+1,stop):
  for h in range(len(hu)):
   if not pending[h]:continue
   expired=(bar[j]-bar[tr]>hv[h]) if hu[h]==0 else (ts[j]-ts[tr]>hv[h]*1000000000)
   if expired:result[h]=6;pending[h]=False;left-=1
  if not left:break
  status=7 if ts[j]-ts[j-1]>gap else 4 if side*(px[j]-target)<=0 else 5 if side*(px[j]-opp)>=0 else -1
  if status>=0:
   for h in range(len(hu)):
    if pending[h]:result[h]=status
   break
 return result
@njit(cache=True)
def evaluate_config(px,ts,bar,birth_b,birth_lo,birth_hi,anchors,stops,day_ids,du,dv,qq,rule_group,rule_ep,rule_h,hu,hv,bin_size=6250):
 nr=len(rule_group);nd=day_ids.max()+1 if len(day_ids) else 1;nb=len(px)//bin_size+nd+2
 counts=np.zeros((nr,10),np.int64);daily=np.zeros((nr,nd,10),np.int64);best=np.full((nr,nb),9223372036854775807,np.int64);labels=np.full((nr,nb),-1,np.int8);days=np.full(nb,-1,np.int64)
 for bi in range(len(anchors)):
  anchor=anchors[bi];stop=stops[bi];low=birth_lo[bi];high=birth_hi[bi];day=day_ids[bi];triggers=np.empty((len(qq),4),np.int64);outs=np.empty((len(qq),3,len(hu)),np.int64)
  for g in range(len(qq)):
   D=dv[g]*(high-low+1) if du[g] else dv[g];r=trigger(px,ts,anchor,stop,low,high,D,qq[g]);triggers[g]=r
   if r[1]>=0:
    reused=-1
    for pg in range(g):
     if triggers[pg,1]==r[1] and triggers[pg,2]==r[2]:reused=pg;break
    if reused>=0:outs[g]=outs[reused]
    else:
     for ep in range(3):outs[g,ep]=outcomes(px,ts,bar,r[1],stop,low,high,r[2],ep,hu,hv)
  for rule in range(nr):
   g=rule_group[rule];tr=triggers[g,1];status=triggers[g,0] if tr<0 else outs[g,rule_ep[rule],rule_h[rule]];counts[rule,status]+=1;daily[rule,day,status]+=1
   if tr>=0:
    b=tr//bin_size+day;days[b]=day
    if tr<best[rule,b]:best[rule,b]=tr;labels[rule,b]=status
 thin=np.zeros((nr,nd,10),np.int64)
 for r in range(nr):
  for b in range(nb):
   if labels[r,b]>=0:thin[r,days[b],labels[r,b]]+=1
 return counts,daily,thin
