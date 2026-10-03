#!/usr/bin/env python3
"""Enmienda 1 del pre-registro: nulo de máximo sobre 21 celdas normales con dirección sorteada por sesión."""
import json,sys,time
from multiprocessing import Pool
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import run_mgc_tick_exact_finalists as F
CELLS=[(s,t) for s in(100,150,200) for t in range(150,451,50)];NSIM,SEED=500,20261004
SD0=np.asarray(F.SD);SDAY=np.asarray(F.TD)[np.asarray(F.END)[np.asarray(F.SIG)]];DAYS=np.unique(SDAY);INV=np.searchsorted(DAYS,SDAY)
def cells(sd):return np.array([F.replay(F.SIG,sd,F.END,F.P,F.B,F.A,F.CID,F.TD,s,t,1,.5)[0].sum() for s,t in CELLS])
def work(seed):
    rng=np.random.default_rng(seed);return np.array([cells((SD0*rng.choice(np.array([-1,1],np.int8),len(DAYS))[INV]).astype(np.int8)).max() for _ in range(NSIM//4)])
if __name__=='__main__':
    t=time.time();real=cells(SD0);assert F.TD[:].max()<20260401
    with Pool(4) as p:null=np.concatenate(p.map(work,[SEED+i for i in range(4)]))
    out={'schema_version':'mgc_direction_maxnull_v1','cells':CELLS,'real_by_cell':dict(zip(map(str,CELLS),real.tolist())),'real_max':float(real.max()),'nsim':len(null),
         'null_max_mean':float(null.mean()),'null_max_q95':float(np.quantile(null,.95)),'p_max':float((np.sum(null>=real.max())+1)/(len(null)+1)),'elapsed_s':time.time()-t,'holdout_opened':False}
    Path('/data/analysis/mgc/direction_diag').mkdir(parents=True,exist_ok=True);Path('/data/analysis/mgc/direction_diag/maxnull.json').write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
