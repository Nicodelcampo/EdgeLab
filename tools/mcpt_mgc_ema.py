#!/usr/bin/env python3
"""Full-pipeline intraday permutation test for the MGC EMA headline.

Permutes complete 25T bar components inside each CME trade date, reconstructs
an OHLC+quote path from the real session open, then recomputes EMAs, signals
and the stateful replay. Inter-session gaps, session endpoints, OHLC geometry,
quote offsets and contract resets are preserved.
"""
from pathlib import Path
import json,time,sys
import numpy as np
from numba import njit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.run_mgc_ema_screen import ema,signals,replay_one,ROOT,C,H,L,BO,AO,BC,AC,CID,TD
OUT=Path('/data/analysis/mgc/validation');OUT.mkdir(parents=True,exist_ok=True)
O=np.load(ROOT/'open_ticks.npy',mmap_mode='r')
@njit(cache=True)
def rebuild(order,starts,ends,o,h,l,c,bo,ao,bc,ac):
 n=o.size;op=np.empty(n,np.int32);hp=np.empty(n,np.int32);lp=np.empty(n,np.int32);cp=np.empty(n,np.int32);bop=np.empty(n,np.int32);aop=np.empty(n,np.int32);bcp=np.empty(n,np.int32);acp=np.empty(n,np.int32)
 for g in range(starts.size):
  s=starts[g];e=ends[g];prev=int(o[s])
  for z in range(s,e):
   j=order[z];gap=0 if j==s else int(o[j])-int(c[j-1]);oo=prev+gap
   op[z]=oo;hp[z]=oo+(int(h[j])-int(o[j]));lp[z]=oo+(int(l[j])-int(o[j]));cc=oo+(int(c[j])-int(o[j]));cp[z]=cc
   bop[z]=oo+(int(bo[j])-int(o[j]));aop[z]=oo+(int(ao[j])-int(o[j]));bcp[z]=cc+(int(bc[j])-int(c[j]));acp[z]=cc+(int(ac[j])-int(c[j]));prev=cc
 return op,hp,lp,cp,bop,aop,bcp,acp
@njit(cache=True)
def stat(c,h,l,bo,ao,bc,ac,cid,td):
 e2=ema(c,cid,200);e5=ema(c,cid,500);e20=ema(c,cid,2000);si,sd=signals(e2,e5,e20,cid);p,_,_,_,_=replay_one(si,sd,h,l,bo,ao,bc,ac,cid,td,200,400,1,.5,si.size);return p.sum(),si.size,p.size
def main(n_perm=500,seed=20261002):
 t=time.time();cuts=np.flatnonzero(TD[1:]!=TD[:-1])+1;starts=np.r_[0,cuts].astype(np.int64);ends=np.r_[cuts,len(TD)].astype(np.int64);real,real_sig,real_tr=stat(C,H,L,BO,AO,BC,AC,CID,TD);rng=np.random.default_rng(seed);vals=np.empty(n_perm);sc=np.empty(n_perm,np.int32);tc=np.empty(n_perm,np.int32);order=np.arange(len(TD),dtype=np.int64)
 for k in range(n_perm):
  for s,e in zip(starts,ends):rng.shuffle(order[s:e])
  _,hp,lp,cp,bop,aop,bcp,acp=rebuild(order,starts,ends,O,H,L,C,BO,AO,BC,AC);vals[k],sc[k],tc[k]=stat(cp,hp,lp,bop,aop,bcp,acp,CID,TD)
  if (k+1)%50==0:print(f'{k+1}/{n_perm} p={(1+(vals[:k+1]>=real).sum())/(k+2):.4f}',flush=True)
 pval=float((1+(vals>=real).sum())/(n_perm+1));out={'schema_version':'mgc_ema_mcpt_v1','artifact_id':ROOT.name,'headline':{'direction':'normal','entry':'immediate','sl_ticks':200,'tp_ticks':400,'be':'off'},'real_net_ticks':float(real),'real_signals':int(real_sig),'real_trades':int(real_tr),'n_permutations':n_perm,'seed':seed,'p_value':pval,'null_mean_ticks':float(vals.mean()),'null_sd_ticks':float(vals.std()),'null_q95_ticks':float(np.quantile(vals,.95)),'permutation_unit':'CME trade date; additive OHLC components and quote offsets permuted together; full EMA/signal/replay rerun','holdout_opened':False,'elapsed_s':round(time.time()-t,3)};(OUT/'mcpt.json').write_text(json.dumps(out,indent=2));np.save(OUT/'mcpt_null.npy',vals);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
