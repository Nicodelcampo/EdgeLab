import json,itertools
from pathlib import Path
import numpy as np
from matrix_engine import trigger,outcomes,evaluate_config
rng=np.random.default_rng(9947);checks=0;hu=np.array([0,0,0,1,1,1]);hv=np.array([100,500,2000,30,120,600])
def ref(p,t,b,anchor,lo,hi,D,q,ep,unit,h):
 if not lo<=p[anchor]<=hi:return 0,-1
 exitidx=next((i for i in range(anchor+1,len(p)) if p[i]<lo or p[i]>hi),None)
 if exitidx is None:return 1,-1
 side=1 if p[exitidx]>hi else -1;edge=hi if side==1 else lo;peak=side*(p[exitidx]-edge)
 for i in range(exitidx+1,len(p)):
  x=side*(p[i]-edge)
  if x<=0:return 3,-1
  peak=max(peak,x)
  if peak<D or x>peak*(1-q):continue
  target=edge if ep==0 else edge-side if ep==1 else lo-1 if side==1 else hi+1;opp=p[i]+side*abs(p[i]-target)
  for j in range(i+1,len(p)):
   if (b[j]-b[i]>h if unit==0 else t[j]-t[i]>h*10**9):return 6,i
   if side*(p[j]-target)<=0:return 4,i
   if side*(p[j]-opp)>=0:return 5,i
  return 8,i
 return 2,-1
for _ in range(100):
 n=300;p=np.r_[0,np.cumsum(rng.integers(-3,4,n-1))].astype(np.int64);t=np.arange(n,dtype=np.int64)*1000000000;b=np.arange(n,dtype=np.int64)//25
 for D,q in itertools.product([1,5,10],[.1,.5,.9]):
  a=trigger(p,t,0,n,-1,1,D,q)
  for ep in range(3):
   o=outcomes(p,t,b,a[1],n,-1,1,a[2],ep,hu,hv) if a[1]>=0 else None
   for h,(unit,horizon) in enumerate(zip(hu,hv)):
    status,tr=ref(p.tolist(),t.tolist(),b.tolist(),0,-1,1,D,q,ep,int(unit),int(horizon));assert tr==a[1] and status==(int(o[h]) if o is not None else a[0]);checks+=1
# Seconds-based future horizons, gap precedence and first-return failure checks.
assert trigger(np.array([0,2,0,10,5]),np.arange(5)*100,np.int64(0),5,-1,1,5,.5)[0]==3
p=np.array([0,2,10,5,1]);t=np.array([0,1,2,3,20000000000]);b=np.zeros(5,np.int64);a=trigger(p,t,0,5,-1,1,5,.5);assert (outcomes(p,t,b,a[1],5,-1,1,a[2],0,hu,hv)==7).all();checks+=2
Path('/data/analysis/avzvol-longevity/matrix-test-evidence.json').write_text(json.dumps({'status':'PASS','independent_comparisons':checks,'matrix_endpoints':'touch/enter_one_tick/cross_one_tick; not center','first_departure':True},indent=2)+'\n');print('MATRIX_REFERENCE_PASS',checks)
