#!/usr/bin/env python3
"""MGC EMA headline: long/short split, random-direction nulls, concentration, D0/D1/D2. Pre-registered in
docs/research/mgc_ema_20261002/DIAGNOSTICO_DIRECCION_PREREGISTRO.md. Never reads trade_date >= 20260401."""
import json,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import run_mgc_tick_exact_finalists as F
SL,TP,NSIM,SEED=200,400,2000,20261003
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/data/analysis/mgc/direction_diag')
OUT.mkdir(parents=True,exist_ok=True)
def run(sd):return F.replay(F.SIG,sd,F.END,F.P,F.B,F.A,F.CID,F.TD,SL,TP,1,.5)
pnl,en,ex,d,r=run(np.asarray(F.SD));real=float(pnl.sum());xd=np.asarray(F.TD)[ex];ed=np.asarray(F.TD)[en]
assert xd.max()<20260401
res={'schema_version':'mgc_direction_diag_v1','headline':{'sl':SL,'tp':TP},'real_net_ticks':real,'trades':int(len(pnl))}
res['long_short']={n:{'trades':int((d==s).sum()),'net_ticks':float(pnl[d==s].sum())} for n,s in(('long',1),('short',-1))}
rng=np.random.default_rng(SEED);sd0=np.asarray(F.SD);sig_day=np.asarray(F.TD)[np.asarray(F.END)[np.asarray(F.SIG)]]
days=np.unique(sig_day);inv=np.searchsorted(days,sig_day)
t=time.time();a=np.empty(NSIM);b=np.empty(NSIM)
for i in range(NSIM):
    a[i]=run(rng.choice(np.array([-1,1],np.int8),len(sd0)))[0].sum()
    flip=rng.choice(np.array([-1,1],np.int8),len(days))[inv];b[i]=run((sd0*flip).astype(np.int8))[0].sum()
res['null_iid_signal']={'mean':float(a.mean()),'sd':float(a.std()),'q95':float(np.quantile(a,.95)),'p':float((np.sum(a>=real)+1)/(NSIM+1))}
res['null_session_flip']={'mean':float(b.mean()),'sd':float(b.std()),'q95':float(np.quantile(b,.95)),'p':float((np.sum(b>=real)+1)/(NSIM+1))}
mon=xd//100;ms={int(m):float(pnl[mon==m].sum()) for m in np.unique(mon)};best=max(ms,key=ms.get)
dayp={int(x):float(pnl[xd==x].sum()) for x in np.unique(xd)};top5=sorted(dayp.values())[-5:]
res['concentration']={'months':ms,'best_month':best,'net_without_best_month':real-ms[best],'best_month_share':ms[best]/real,'net_without_top5_days':real-sum(top5),'top5_days':top5}
sp=json.load(open(Path(__file__).parent.parent/'docs/research/mgc_ema_20261002/funnel_e1_e3.json'))['split']
res['split']={k:{'trades':int(np.isin(xd,sp[k+'_dates']).sum()),'net_ticks':float(pnl[np.isin(xd,sp[k+'_dates'])].sum())} for k in('d0','d1','d2')}
cid=np.asarray(F.CID)[en];res['contracts']={int(c):float(pnl[cid==c].sum()) for c in np.unique(cid)}
res['elapsed_s']=time.time()-t;res['holdout_opened']=False
(OUT/'direction_diag.json').write_text(json.dumps(res,indent=1));print(json.dumps(res,indent=1))
