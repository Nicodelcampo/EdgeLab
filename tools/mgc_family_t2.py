#!/usr/bin/env python3
"""PREREGISTRO_FAMILIA_20261004 T2: información direccional por horizonte, sin SL/TP, nulo por sesión."""
import json,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import run_mgc_tick_exact_finalists as F
HZ={'15m':15,'30m':30,'1h':60,'2h':120,'4h':240};NSIM,SEED=200000,20261005
TS=np.load(F.TROOT/'ts_utc_ns.npy',mmap_mode='r')
sig=np.asarray(F.SIG);sd=np.asarray(F.SD).astype(np.float64);end=np.asarray(F.END)
ent=end[sig]+1;ok=ent<F.P.size
sig,sd,ent=sig[ok],sd[ok],ent[ok]
ts=np.asarray(TS);td=np.asarray(F.TD);cid=np.asarray(F.CID);b=np.asarray(F.B);a=np.asarray(F.A)
mid=(b.astype(np.float64)+a.astype(np.float64))/2
assert td[ent].max()<20260401
# primer índice fuera de (misma sesión, mismo contrato) a partir de la entrada
sess_key=td.astype(np.int64)*1000+cid.astype(np.int64)
chg=np.flatnonzero(sess_key[1:]!=sess_key[:-1])+1;starts=np.r_[0,chg];ends=np.r_[chg,len(td)]
seg=np.searchsorted(starts,ent,side='right')-1;last=ends[seg]-1
rets={}
for k,m in HZ.items():
    j=np.minimum(np.searchsorted(ts,ts[ent]+m*60*10**9,side='left'),last);j=np.minimum(j,last)
    rets[k]=sd*(mid[j]-mid[ent])
days=td[ent];D=np.unique(days);inv=np.searchsorted(D,days)
rng=np.random.default_rng(SEED);out={'schema_version':'mgc_family_t2_v1','prereg':'PREREGISTRO_FAMILIA_20261004.md','signals':int(len(ent)),'sessions':int(len(D)),'horizons':{}}
S={k:np.bincount(inv,weights=v,minlength=len(D)) for k,v in rets.items()}
sdn={k:float(np.sqrt((S[k]**2).sum())) for k in S}
eps=rng.choice(np.array([-1.,1.]),size=(NSIM,len(D)))
Z=np.stack([eps@S[k]/sdn[k] for k in HZ],axis=1)
real={k:float(rets[k].sum()/sdn[k]) for k in HZ}
for k in HZ:
    out['horizons'][k]={'mean_ticks':float(rets[k].mean()),'sum_ticks':float(rets[k].sum()),'z':real[k],'p_one_sided':float((np.sum(Z[:,list(HZ).index(k)]>=real[k])+1)/(NSIM+1)),
                        'long_mean':float(rets[k][sd>0].mean()),'short_mean':float(rets[k][sd<0].mean())}
mx=max(real.values());out['max_z']=mx;out['p_max']=float((np.sum(Z.max(1)>=mx)+1)/(NSIM+1));out['nsim']=NSIM;out['holdout_opened']=False
Path('/data/analysis/mgc/direction_diag/family_t2.json').write_text(json.dumps(out,indent=1));print(json.dumps(out,indent=1))
