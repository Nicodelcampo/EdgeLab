from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from validation.pbo import pbo_cscv
from .isolation import bounded_batches,stage_window
from .splits import make_splits,mask_for,to_dict
from .survivors import write_survivors
from .ledger import FunnelLedger

class FunnelRunner:
    def __init__(self,*,trade_dates,signal_idx,signal_dir,high,low,bid_open,ask_open,configs,out_dir,backend="auto"):
        self.td=np.asarray(trade_dates);self.si=np.asarray(signal_idx);self.sd=np.asarray(signal_dir);self.h=np.asarray(high);self.l=np.asarray(low);self.bo=np.asarray(bid_open);self.ao=np.asarray(ask_open);self.cfg=list(configs);self.out=Path(out_dir);self.out.mkdir(parents=True,exist_ok=True);self.backend=backend;self.split=make_splits(self.td);self.ledger=FunnelLedger(self.out/'edge_brain.jsonl')
        if not self.cfg: raise ValueError('empty candidate registry')
        ids=[c['candidate_id'] for c in self.cfg]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate candidate_id')
        if any(len(a)!=len(self.td) for a in (self.h,self.l,self.bo,self.ao)): raise ValueError('bar lengths disagree')
        if len(self.si)!=len(self.sd): raise ValueError('signal lengths disagree')
        if any(c.get('direction','normal') not in {'normal','reverse'} for c in self.cfg): raise ValueError('invalid candidate direction')

    def run_e1_e3(self,min_trades=30,max_hold_bars=200,max_matrix_bytes=512*1024*1024):
        if min_trades<1: raise ValueError('min_trades must be positive')
        sl=np.array([c['sl_ticks'] for c in self.cfg]);tp=np.array([c['tp_ticks'] for c in self.cfg]);mult=np.array([1 if c.get('direction','normal')=='normal' else -1 for c in self.cfg],np.int8)
        windows={part:stage_window(self.td,self.si,dates,max_hold_bars) for part,dates in [('D0',self.split.d0_dates),('D1',self.split.d1_dates)]}
        # Never pass the full price arrays to a kernel: slice one stage only.
        # Signal order remains stable across configuration batches.
        def batches(part,keep):
            w=windows[part];bar=slice(w.bar_start,w.bar_stop)
            return bounded_batches(w.local_signals(self.si),self.sd[w.signal_positions],self.h[bar],self.l[bar],self.bo[bar],self.ao[bar],sl[keep],tp[keep],mult[keep],max_hold_bars=max_hold_bars,backend=self.backend,max_matrix_bytes=max_matrix_bytes)
        stats={part:[(0,None) for _ in self.cfg] for part in windows};devices={}
        keep=np.arange(len(self.cfg))
        for part in windows:
            for start,end,matrix,dev in batches(part,keep):
                devices[part]=dev.__dict__
                for local in range(end-start):
                    vals=matrix[:,local];a=vals[np.isfinite(vals)]
                    stats[part][start+local]=(len(a),float(a.mean()) if len(a) else None)
        rows=[]
        for i,c in enumerate(self.cfg):
            n0,a=stats['D0'][i];n1,b=stats['D1'][i]
            survive=n0>=min_trades and n1>=min_trades and a is not None and b is not None and a>0 and b>0
            rows.append({**c,'d0_n':n0,'d0_mean':a,'d1_n':n1,'d1_mean':b,'survives_e1_e2':bool(survive)})
        surv=[r for r in rows if r['survives_e1_e2']];heads=[]
        for fam in sorted({r['family_id'] for r in surv}):
            f=[r for r in surv if r['family_id']==fam];heads.append(max(f,key=lambda r:min(r['d0_mean'],r['d1_mean'])-abs(r['d0_mean']-r['d1_mean'])))
        isolation={'policy':'complete_horizon_stage_local_v1','max_hold_bars':int(max_hold_bars),'visited_bars_per_horizon':int(max_hold_bars)+1,'d2_prices_passed_to_kernel':False,'boundary_excluded':{p:w.excluded_boundary_signals for p,w in windows.items()},'eligible_signals':{p:len(w.signal_positions) for p,w in windows.items()},'max_matrix_bytes':int(max_matrix_bytes),'budget_scope':'one_output_matrix_not_total_memory'}
        meta={'split_hash':self.split.split_hash,'backend':self.backend,'confirmatory':False,'isolation_policy':isolation['policy']}
        trial_art=write_survivors(rows,self.out/'trials.parquet',meta)
        survivor_art=write_survivors(surv,self.out/'survivors.parquet',meta)
        multiplicity={'status':'NOT_RUN_INSUFFICIENT_SURVIVORS','pbo':None,'candidates':len(surv),'scope':'survivors_only_diagnostic','promotion_allowed':False}
        if len(surv)>=2:
            byid={c['candidate_id']:i for i,c in enumerate(self.cfg)};keep=np.array([byid[r['candidate_id']] for r in surv])
            days=np.array(self.split.d0_dates+self.split.d1_dates);day_pos={int(d):i for i,d in enumerate(days)}
            daily=np.zeros((len(days),len(keep)),np.float64)
            for part,w in windows.items():
                sigdays=self.td[self.si[w.signal_positions]+1]
                for start,end,matrix,_ in batches(part,keep):
                    for local in range(end-start):
                        for day,val in zip(sigdays,matrix[:,local]):
                            if np.isfinite(val): daily[day_pos[int(day)],start+local]+=val
            pbo=pbo_cscv(daily,S=10)
            multiplicity.update(status='COMPLETE_DIAGNOSTIC_ONLY',pbo=float(pbo['pbo']),splits=int(pbo['n_splits']))
        payload={'stage':'E1_E2_WITH_E3_IF_ELIGIBLE','devices':devices,'split':to_dict(self.split),'isolation':isolation,'tested':len(rows),'survivors':len(surv),'headlines':heads,'multiplicity':multiplicity,'trial_artifact':trial_art,'survivor_artifact':survivor_art,'asserts_edge':False,'holdout_opened':False,'promotion_allowed':False}
        rid='FUNNEL-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
        self.ledger.append('trial_recorded',rid,payload);(self.out/'summary.json').write_text(json.dumps(payload,indent=2));return payload

    def d2_mask(self,unlock_token=None):return mask_for(self.split,self.td,'D2',unlock_token=unlock_token)
