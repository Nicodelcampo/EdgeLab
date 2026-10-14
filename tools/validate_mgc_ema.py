#!/usr/bin/env python3
from pathlib import Path
import sys,json,time
import numpy as np
sys.path.insert(0,'/data/EdgeLab')
from edgelab.audit import deflated_sharpe,sr0_haircut
from validation.pbo import pbo_cscv
from tools.run_mgc_ema_screen import replay_one,ema,signals,H,L,BO,AO,BC,AC,CID,TD,C
BROOT=Path('/data/analysis/mgc/artifacts')/Path('/data/analysis/mgc/artifacts/LATEST').read_text().strip(); OUT=Path('/data/analysis/mgc/validation');OUT.mkdir(parents=True,exist_ok=True)
def bh(ps):
 ps=np.asarray(ps);n=len(ps);o=np.argsort(ps);q=np.empty(n);v=ps[o]*n/np.arange(1,n+1);v=np.minimum.accumulate(v[::-1])[::-1];q[o]=np.minimum(v,1);return q
def main():
 t=time.time();e2=ema(C,CID,200);e5=ema(C,CID,500);e20=ema(C,CID,2000);sig,d=signals(e2,e5,e20,CID)
 # mechanical signal preflight
 me2=ema(-C,CID,200);me5=ema(-C,CID,500);me20=ema(-C,CID,2000);ms,md=signals(me2,me5,me20,CID);mirror=bool(np.array_equal(sig,ms) and np.array_equal(d,-md))
 cut=int(len(C)*.7);ps,pd=signals(ema(C[:cut],CID[:cut],200),ema(C[:cut],CID[:cut],500),ema(C[:cut],CID[:cut],2000),CID[:cut]);keep=sig<cut-1;prefix=bool(np.array_equal(ps,sig[keep]) and np.array_equal(pd,d[keep]))
 cfg=[(m,s,tp) for m in (1,-1) for s in (100,150,200) for tp in (150,200,250,300,350,400,450)];days=np.unique(TD);di={int(x):i for i,x in enumerate(days)};R=np.zeros((len(days),len(cfg)));stats=[];ledgers={}
 for q,(m,sl,tp) in enumerate(cfg):
  p,en,ex,dr,rs=replay_one(sig,d,H,L,BO,AO,BC,AC,CID,TD,sl,tp,m,.5,len(sig));xd=TD[ex]
  for day,val in zip(xd,p):R[di[int(day)],q]+=val
  mu=float(p.mean());sd=float(p.std());sk=float(((p-mu)**3).mean()/sd**3);ku=float(((p-mu)**4).mean()/sd**4);stats.append({'direction':'normal' if m==1 else 'inverse','sl':sl,'tp':tp,'n':len(p),'net':float(p.sum()),'mean':mu,'sd':sd,'sharpe':mu/sd,'skew':sk,'kurt':ku})
  if m==1 and sl==200 and tp in (300,400,450):ledgers[tp]=(p,en,ex,dr,rs)
 srs=np.array([x['sharpe'] for x in stats]);sr0=sr0_haircut(float(srs.std(ddof=1)),len(stats))
 for x in stats:x['dsr']=float(deflated_sharpe(x['sharpe'],x['n'],x['skew'],x['kurt'],sr0))
 pbo=pbo_cscv(R,S=10)
 rng=np.random.default_rng(20261002);B=20000;signs=rng.choice(np.array([-1.,1.]),size=(B,len(days)));null=signs@R;obs=R.sum(0);pvals=(1+(null>=obs).sum(0))/(B+1);qvals=bh(pvals)
 for x,pv,qv in zip(stats,pvals,qvals):x['daily_signflip_p']=float(pv);x['bh_q']=float(qv)
 robust={}
 for tp,(p,en,ex,dr,rs) in ledgers.items():
  # block bootstrap by sessions
  daily=np.array([R[i,cfg.index((1,200,tp))] for i in range(len(days))]);boot=daily[rng.integers(0,len(days),size=(B,len(days)))].sum(1)
  split=int(len(days)*.7);monthly={str(int(m)):float(p[TD[ex]//100==m].sum()) for m in np.unique(TD[ex]//100)};contracts={str(int(c)):float(p[CID[en]==c].sum()) for c in np.unique(CID[en])}
  robust[str(tp)]={'bootstrap_positive':float((boot>0).mean()),'is_net_ticks':float(daily[:split].sum()),'oos_net_ticks':float(daily[split:].sum()),'positive_days':int((daily>0).sum()),'negative_days':int((daily<0).sum()),'months':monthly,'contracts':contracts,'cost_sensitivity_net_ticks':{str(c):float(p.sum()-(c-.5)*len(p)) for c in (.5,2,4,6)}}
 out={'schema_version':'mgc_ema_validation_v1','signals':len(sig),'preflight':{'mirror_signal':mirror,'prefix_signal':prefix,'synthetic_engine':'covered_by_shared EdgeLab engine; custom stateful kernel still requires differential test','ledger_arithmetic':'pending independent differential verifier'},'grid_configs':len(cfg),'sr0_haircut':float(sr0),'dsr_gt_095':int(sum(x['dsr']>.95 for x in stats)),'bh_q_lt_005':int(sum(x['bh_q']<.05 for x in stats)),'pbo':float(pbo['pbo']),'pbo_splits':int(pbo['n_splits']),'headline_robustness':robust,'grid_stats':stats,'holdout_opened':False,'elapsed_s':round(time.time()-t,3)};(OUT/'validation.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ('grid_stats',)},indent=2))
if __name__=='__main__':main()
