import csv,json
from pathlib import Path
import numpy as np
from matrix_engine import evaluate_config
from test_matrix import ref
rules=list(csv.DictReader(open('/data/raw/avzvol-matrix/partial-return-rules.csv')));groups=sorted(set((r['distance_unit'],float(r['distance']),float(r['retracement_fraction'])) for r in rules));hor=sorted(set((r['horizon_unit'],int(r['horizon'])) for r in rules));du=np.array([g[0]=='h' for g in groups],np.int64);dv=np.array([g[1] for g in groups]);qq=np.array([g[2] for g in groups]);rg=np.array([groups.index((r['distance_unit'],float(r['distance']),float(r['retracement_fraction']))) for r in rules]);ep=np.array([['touch','enter_one_tick','cross_one_tick'].index(r['endpoint']) for r in rules]);rh=np.array([hor.index((r['horizon_unit'],int(r['horizon']))) for r in rules]);hu=np.array([h[0]=='seconds' for h in hor],np.int64);hv=np.array([h[1] for h in hor],np.int64)
rng=np.random.default_rng(1935360);n=500;p=np.cumsum(rng.integers(-3,4,n)).astype(np.int64);anchors=np.arange(0,n,50);p[anchors]=0;t=np.arange(n,dtype=np.int64)*1000000000;b=np.arange(n,dtype=np.int64)//25;day=(anchors>=250).astype(np.int64);stops=np.where(day==0,250,500);lo=np.full(10,-1);hi=np.full(10,1);raw,daily,thin=evaluate_config(p,t,b,b[anchors],lo,hi,anchors,stops,day,du,dv,qq,rg,ep,rh,hu,hv);rr=np.zeros_like(raw);dd=np.zeros_like(daily);best={}
for i,anchor in enumerate(anchors):
 stop=int(stops[i])
 for r in range(1260):
  g=rg[r];D=dv[g]*3 if du[g] else dv[g];h=rh[r];status,tr=ref(p[:stop].tolist(),t[:stop].tolist(),b[:stop].tolist(),int(anchor),-1,1,float(D),float(qq[g]),int(ep[r]),int(hu[h]),int(hv[h]));rr[r,status]+=1;dd[r,day[i],status]+=1
  if tr>=0:
   key=(r,int(day[i]),tr//6250)
   if key not in best or tr<best[key][0]:best[key]=(tr,status)
th=np.zeros_like(thin)
for (r,d,binid),(tr,status) in best.items():th[r,d,status]+=1
assert np.array_equal(rr,raw) and np.array_equal(dd,daily) and np.array_equal(th,thin)
Path('/data/analysis/avzvol-longevity/matrix-batch-test-evidence.json').write_text(json.dumps({'status':'PASS','original_rules_independently_checked':1260,'events_evaluated':12600,'raw_daily_and_thinned_counts_equal':True,'session_boundary_bin_separation':True},indent=2)+'\n');print('BATCH_INDEPENDENT_PASS',1260,12600)
