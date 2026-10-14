#!/usr/bin/env python3
"""Tick-exact validation of the immutable 42-cell MGC EMA core registry."""
from pathlib import Path
import json,time,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgelab.audit import deflated_sharpe,sr0_haircut
from validation.pbo import pbo_cscv
from tools.run_mgc_tick_exact_finalists import replay,BROOT,TROOT,SIG,SD,END,P,B,A,CID,TD
OUT=Path('/data/analysis/mgc/tick_exact_grid');OUT.mkdir(parents=True,exist_ok=True)
def bh(ps):
 ps=np.asarray(ps);n=len(ps);o=np.argsort(ps);v=ps[o]*n/np.arange(1,n+1);v=np.minimum.accumulate(v[::-1])[::-1];q=np.empty(n);q[o]=np.minimum(v,1);return q
def main():
 t=time.time();cfg=[(m,s,tp) for m in (1,-1) for s in (100,150,200) for tp in (150,200,250,300,350,400,450)];days=np.unique(TD);pos={int(x):i for i,x in enumerate(days)};R=np.zeros((len(days),len(cfg)),np.float64);rows=[]
 for q,(m,sl,tp) in enumerate(cfg):
  pnl,en,ex,d,r=replay(SIG,SD,END,P,B,A,CID,TD,sl,tp,m,.5)
  for day,v in zip(TD[ex],pnl):R[pos[int(day)],q]+=v
  mu=float(pnl.mean());sd=float(pnl.std());sk=float(((pnl-mu)**3).mean()/sd**3);ku=float(((pnl-mu)**4).mean()/sd**4)
  rows.append({'direction':'normal' if m==1 else 'inverse','sl_ticks':sl,'tp_ticks':tp,'trades':len(pnl),'net_ticks':float(pnl.sum()),'ticks_per_trade':mu,'win_rate':float((pnl>0).mean()),'sharpe_trade':mu/sd,'skew':sk,'kurt':ku,'tp_exits':int((r==0).sum()),'sl_exits':int((r==1).sum()),'roll_exits':int((r==2).sum())})
 srs=np.array([x['sharpe_trade'] for x in rows]);sr0=sr0_haircut(float(srs.std(ddof=1)),len(rows))
 for x in rows:x['dsr']=float(deflated_sharpe(x['sharpe_trade'],x['trades'],x['skew'],x['kurt'],sr0))
 pbo=pbo_cscv(R,S=10);rng=np.random.default_rng(20261002);nperm=20000;signs=rng.choice(np.array([-1.,1.]),size=(nperm,len(days)));null=signs@R;obs=R.sum(0);p=(1+(null>=obs).sum(0))/(nperm+1);q=bh(p)
 for x,pv,qv in zip(rows,p,q):x['daily_signflip_p']=float(pv);x['bh_q']=float(qv)
 rows.sort(key=lambda x:x['net_ticks'],reverse=True);np.save(OUT/'daily_pnl_matrix.npy',R);np.save(OUT/'trade_dates.npy',days)
 out={'schema_version':'mgc_tick_exact_grid_v1','bar_artifact_id':BROOT.name,'tick_artifact_id':TROOT.name,'registry':'42-cell core fixed before screening; exact original 126-cell registry unavailable','signals':len(SIG),'configs':len(cfg),'holdout_opened':False,'sr0_haircut':float(sr0),'dsr_gt_095':int(sum(x['dsr']>.95 for x in rows)),'bh_q_lt_005':int(sum(x['bh_q']<.05 for x in rows)),'pbo':float(pbo['pbo']),'pbo_splits':int(pbo['n_splits']),'top5':rows[:5],'results':rows,'elapsed_s':round(time.time()-t,3)};(OUT/'results.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
if __name__=='__main__':main()
