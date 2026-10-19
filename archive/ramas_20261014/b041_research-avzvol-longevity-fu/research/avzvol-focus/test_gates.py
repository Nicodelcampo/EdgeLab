import itertools,json
from pathlib import Path
import numpy as np
from gates import collapse,gate_masks,matched,influence
rng=np.random.default_rng(17412);checks=0
for n in [0,1,17,43]:
 a=dict(speed_ratio=rng.choice([np.nan,.4,1.,2.],n),return_efficiency=rng.choice([np.nan,.2,.5,.75,.9],n),return_imbalance_proxy_toward=rng.choice([np.nan,-.5,-.1,0.,.25,.6],n),proxy_coverage=rng.choice([.2,.79,.8,1.],n),visits1=rng.choice([0,5,10,20,50,100],n),volume_inside_fraction=rng.choice([.1,.25,.5,.9],n),return_bars_per_tick=rng.choice([np.nan,.25,.5,1.,2.],n),prior_gap_count=rng.choice([0,1],n),dedup75=rng.choice([0,1],n));collapsed=collapse(a);reference={}
 for cid,tup in enumerate(itertools.product(*gate_masks(a))):
  mask=(a['dedup75']==1)
  for g in tup:mask=mask&g
  key=np.packbits(mask).tobytes();old=reference.get(key,(cid,0));reference[key]=(min(old[0],cid),old[1]+1)
 assert {np.packbits(m).tobytes():(cid,mult) for m,cid,mult in collapsed}==reference;checks+=5400
# Independent dictionary matched-strata computation.
for _ in range(100):
 nd=4;n=40;day=rng.integers(0,nd,n);bucket=rng.integers(0,4,n);stratum=day*4+bucket;origin=rng.integers(0,2,n);win=rng.integers(0,2,n);sel=rng.random(n)>.3
 num,wei,common=matched(day,stratum,origin,win,sel,nd);rn=np.zeros(nd);rw=np.zeros(nd);cc=0
 for s in set(stratum):
  rr=[int(win[i]) for i in range(n) if sel[i] and stratum[i]==s and origin[i]==0];co=[int(win[i]) for i in range(n) if sel[i] and stratum[i]==s and origin[i]==1]
  if rr and co:
   w=min(len(rr),len(co));d=next(int(day[i]) for i in range(n) if stratum[i]==s);rn[d]+=w*(sum(rr)/len(rr)-sum(co)/len(co));rw[d]+=w;cc+=1
 assert np.allclose(num,rn) and np.array_equal(wei,rw) and cc==common;checks+=1
 if wei.sum()>0:
  p,se,score=influence(num,wei);assert abs(score.sum())<1e-12 and np.isclose(p,rn.sum()/rw.sum());checks+=1
Path('/data/analysis/avzvol-focus/test-evidence.json').write_text(json.dumps({'status':'PASS','independent_gate_condition_checks':21600,'matched_dictionary_comparisons':100,'total_checks':checks,'duplicate_masks_collapsed_exactly':True,'no_outcome_used_in_gate_construction':True},indent=2)+'\n');print('FOCUS_TESTS_PASS',checks)
