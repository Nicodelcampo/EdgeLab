#!/usr/bin/env python3
"""PREREGISTRO_FAMILIA_20261004 T1: media de las 21 celdas normales bajo dirección sorteada por sesión."""
import json,sys,time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import run_mgc_tick_exact_finalists as F
CELLS=[(s,t) for s in(100,150,200) for t in range(150,451,50)];NSIM,SEED=2000,20261005
SD0=np.asarray(F.SD);SDAY=np.asarray(F.TD)[np.asarray(F.END)[np.asarray(F.SIG)]];DAYS=np.unique(SDAY);INV=np.searchsorted(DAYS,SDAY)
def cells(sd):return np.array([F.replay(F.SIG,sd,F.END,F.P,F.B,F.A,F.CID,F.TD,s,t,1,.5)[0].sum() for s,t in CELLS])
def work(seed):
    rng=np.random.default_rng(seed);return np.array([cells((SD0*rng.choice(np.array([-1,1],np.int8),len(DAYS))[INV]).astype(np.int8)).mean() for _ in range(NSIM//4)])
if __name__=='__main__':
    t=time.time();real=cells(SD0);assert F.TD[:].max()<20260401
    with Pool(4) as p:null=np.concatenate(p.map(work,[SEED+i for i in range(4)]))
    m=float(real.mean())
    out={'schema_version':'mgc_family_t1_v1','prereg':'PREREGISTRO_FAMILIA_20261004.md','cells':CELLS,'real_mean':m,'real_by_cell':dict(zip(map(str,CELLS),real.tolist())),'nsim':len(null),
         'null_mean':float(null.mean()),'null_sd':float(null.std()),'null_q95':float(np.quantile(null,.95)),'z':float((m-null.mean())/null.std()),
         'p':float((np.sum(null>=m)+1)/(len(null)+1)),'elapsed_s':time.time()-t,'holdout_opened':False}
    Path('/data/analysis/mgc/direction_diag/family_t1.json').write_text(json.dumps(out,indent=1));print(json.dumps({k:v for k,v in out.items() if k!='real_by_cell'},indent=1))
