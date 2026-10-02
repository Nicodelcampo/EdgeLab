from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from validation.pbo import pbo_cscv
from .screen import iter_screen_batches
from .splits import make_splits,mask_for,to_dict
from .survivors import write_survivors
from .ledger import FunnelLedger
class FunnelRunner:
    def __init__(self,*,trade_dates,signal_idx,signal_dir,high,low,bid_open,ask_open,configs,out_dir,backend="auto"):
        self.td=np.asarray(trade_dates);self.si=np.asarray(signal_idx);self.sd=np.asarray(signal_dir);self.h=np.asarray(high);self.l=np.asarray(low);self.bo=np.asarray(bid_open);self.ao=np.asarray(ask_open);self.cfg=list(configs);self.out=Path(out_dir);self.out.mkdir(parents=True,exist_ok=True);self.backend=backend;self.split=make_splits(self.td);self.ledger=FunnelLedger(self.out/'edge_brain.jsonl')
    def run_e1_e3(self,min_trades=30):
        sl=np.array([c['sl_ticks'] for c in self.cfg]);tp=np.array([c['tp_ticks'] for c in self.cfg]);mult=np.array([1 if c.get('direction','normal')=='normal' else -1 for c in self.cfg],np.int8)
        sigdays=self.td[np.minimum(self.si+1,len(self.td)-1)];m0=np.isin(sigdays,self.split.d0_dates);m1=np.isin(sigdays,self.split.d1_dates)
        rows=[];dev=None
        for start,end,out,dev in iter_screen_batches(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl,tp,mult,backend=self.backend):
            for local,c in enumerate(self.cfg[start:end]):
                x0=out[m0,local];x1=out[m1,local];a=x0[np.isfinite(x0)];b=x1[np.isfinite(x1)];survive=len(a)>=min_trades and a.mean()>0 and len(b)>=min_trades and b.mean()>0
                rows.append({**c,'d0_n':len(a),'d0_mean':float(a.mean()) if len(a) else None,'d1_n':len(b),'d1_mean':float(b.mean()) if len(b) else None,'survives_e1_e2':bool(survive)})
        surv=[r for r in rows if r['survives_e1_e2']];heads=[]
        for fam in sorted({r['family_id'] for r in surv}):
            f=[r for r in surv if r['family_id']==fam];heads.append(max(f,key=lambda r:min(r['d0_mean'],r['d1_mean'])-abs(r['d0_mean']-r['d1_mean'])))
        meta={'split_hash':self.split.split_hash,'backend':dev.backend,'confirmatory':False}
        trial_art=write_survivors(rows,self.out/'trials.parquet',meta)
        survivor_art=write_survivors(surv,self.out/'survivors.parquet',meta)
        multiplicity={'status':'NOT_RUN_INSUFFICIENT_SURVIVORS','pbo':None,'candidates':len(surv)}
        if len(surv)>=2:
            keep=[self.cfg.index(next(c for c in self.cfg if c['candidate_id']==r['candidate_id'])) for r in surv]
            days=np.unique(sigdays[np.isin(sigdays,np.r_[self.split.d0_dates,self.split.d1_dates])])
            daily=np.zeros((len(days),len(keep)),np.float64)
            day_pos={int(d):i for i,d in enumerate(days)}
            for start,end,matrix,_ in iter_screen_batches(self.si,self.sd,self.h,self.l,self.bo,self.ao,sl[keep],tp[keep],mult[keep],backend=self.backend):
                for local in range(end-start):
                    col=keep[start+local]
                    for day,val in zip(sigdays,matrix[:,local]):
                        if int(day) in day_pos and np.isfinite(val):daily[day_pos[int(day)],start+local]+=val
            pbo=pbo_cscv(daily,S=10)
            multiplicity={'status':'COMPLETE','pbo':float(pbo['pbo']),'splits':int(pbo['n_splits']),'candidates':len(surv)}
        payload={'stage':'E1_E2_WITH_E3_IF_ELIGIBLE','device':dev.__dict__,'split':to_dict(self.split),'tested':len(rows),'survivors':len(surv),'headlines':heads,'multiplicity':multiplicity,'trial_artifact':trial_art,'survivor_artifact':survivor_art,'asserts_edge':False};rid='FUNNEL-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16];self.ledger.append('trial_recorded',rid,payload);(self.out/'summary.json').write_text(json.dumps(payload,indent=2));return payload
    def d2_mask(self,unlock_token=None):return mask_for(self.split,self.td,'D2',unlock_token=unlock_token)
