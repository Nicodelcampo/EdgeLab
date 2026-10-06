from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
from validation.pbo import pbo_cscv
from .isolation import bounded_batches,stage_window
from .splits import make_splits,mask_for,to_dict
from .survivors import write_survivors
from .ledger import FunnelLedger
from .custody import forbid_holdout,SeenLedger
from .multiplicity import candidate_statistic,max_null_batched,plateau_report,sidak_bonferroni,TrialRegistry
from .screen import kernel_manifest

class FunnelRunner:
    def __init__(self,*,trade_dates,signal_idx,signal_dir,high,low,bid_open,ask_open,configs,out_dir,backend="auto",holdout_first_date=None,allow_unguarded=False,campaign_id=None,trial_registry=None,seen_ledger=None):
        self.td=np.asarray(trade_dates);self.si=np.asarray(signal_idx);self.sd=np.asarray(signal_dir);self.h=np.asarray(high);self.l=np.asarray(low);self.bo=np.asarray(bid_open);self.ao=np.asarray(ask_open);self.cfg=list(configs);self.out=Path(out_dir);self.out.mkdir(parents=True,exist_ok=True);self.backend=backend;self.split=make_splits(self.td);self.ledger=FunnelLedger(self.out/'edge_brain.jsonl')
        # Fail closed: the holdout guard is mandatory unless a test explicitly opts out.
        if holdout_first_date is None and not allow_unguarded: raise ValueError('holdout_first_date is required (guard fails closed); pass allow_unguarded=True only in synthetic tests')
        if holdout_first_date is not None: forbid_holdout(self.td,holdout_first_date)
        self.holdout_first_date=holdout_first_date;self.campaign_id=campaign_id;self.reg=TrialRegistry(trial_registry) if trial_registry else None;self.seen=SeenLedger(seen_ledger) if seen_ledger else None
        if self.reg and not campaign_id: raise ValueError('campaign_id is required with trial_registry')
        if not self.cfg: raise ValueError('empty candidate registry')
        ids=[c['candidate_id'] for c in self.cfg]
        if len(ids)!=len(set(ids)): raise ValueError('duplicate candidate_id')
        if any(len(a)!=len(self.td) for a in (self.h,self.l,self.bo,self.ao)): raise ValueError('bar lengths disagree')
        if len(self.si)!=len(self.sd): raise ValueError('signal lengths disagree')
        if any(c.get('direction','normal') not in {'normal','reverse','inverse'} for c in self.cfg): raise ValueError('invalid candidate direction')

    def _mult(self):return np.array([1 if c.get('direction','normal')=='normal' else -1 for c in self.cfg],np.int8)
    def _register_trials(self,note):
        # Count BEFORE any outcome is examined, so a crash can never leave examined-but-uncounted candidates.
        if not self.reg:return None
        for fam in sorted({c['family_id'] for c in self.cfg}):self.reg.ensure(self.campaign_id,fam,sum(c['family_id']==fam for c in self.cfg),note)
        return self.reg.verify()
    def _mark_seen(self,analysis_id):
        if not self.seen:return
        for part,dates in(('D0',self.split.d0_dates),('D1',self.split.d1_dates)):self.seen.mark(analysis_id,min(dates),max(dates),f'{part} outcomes examined by funnel')
    def _guard(self):return {'first_date':self.holdout_first_date,'enforced':self.holdout_first_date is not None}
    def run_e1_e3(self,min_trades=30,max_hold_bars=200,max_matrix_bytes=512*1024*1024):
        if min_trades<1: raise ValueError('min_trades must be positive')
        self._register_trials('run_e1_e3');self._mark_seen(f'{self.campaign_id}:e1_e3')
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
            f=[r for r in surv if r['family_id']==fam];heads.append(max(f,key=lambda r:candidate_statistic(r['d0_mean'],r['d1_mean'])))
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
        payload={'stage':'E1_E2_WITH_E3_IF_ELIGIBLE','devices':devices,'split':to_dict(self.split),'isolation':isolation,'tested':len(rows),'survivors':len(surv),'headlines':heads,'multiplicity':multiplicity,'trial_artifact':trial_art,'survivor_artifact':survivor_art,'asserts_edge':False,'holdout_guard':self._guard(),'holdout_opened':False if self.holdout_first_date is not None else 'UNVERIFIED','promotion_allowed':False,'kernels':{p:kernel_manifest(d['backend']) for p,d in devices.items()},'trial_registry':{'path':str(self.reg.path),'head':self.reg.head(),'total_trials':self.reg.total()} if self.reg else None}
        rid='FUNNEL-'+hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:16]
        self.ledger.append('trial_recorded',rid,payload);(self.out/'summary.json').write_text(json.dumps(payload,indent=2));return payload

    def d2_mask(self,unlock_token=None):return mask_for(self.split,self.td,'D2',unlock_token=unlock_token)

    def run_e4(self,*,n_sims=500,seed=20261004,min_trades=30,max_hold_bars=200,max_matrix_bytes=512*1024*1024,flip='session'):
        """EF3/EF4 on D0+D1 only: max-statistic null under randomized direction, plateau, global trial count.

        Requires a trial registry (the counter is mandatory). Trials are counted BEFORE the simulation runs.
        Each partition is screened twice (own direction and the opposite one); simulations are sign-matrix products.
        """
        if not self.reg:raise ValueError('run_e4 requires trial_registry and campaign_id')
        self._register_trials('run_e4');self._mark_seen(f'{self.campaign_id}:e4')
        sl=np.array([c['sl_ticks'] for c in self.cfg]);tp=np.array([c['tp_ticks'] for c in self.cfg]);mult=self._mult()
        wins={part:stage_window(self.td,self.si,dates,max_hold_bars) for part,dates in [('D0',self.split.d0_dates),('D1',self.split.d1_dates)]}
        sizes=[len(w.signal_positions) for w in wins.values()]
        if min(sizes)==0:raise ValueError('empty D0 or D1 window; cannot run E4')
        days=np.concatenate([self.td[self.si[w.signal_positions]+1] for w in wins.values()]);devs={}
        def gen():
            its={}
            for part,w in wins.items():
                bar=slice(w.bar_start,w.bar_stop);ls=w.local_signals(self.si);dr=self.sd[w.signal_positions].astype(np.int8)
                its[part]=(bounded_batches(ls,dr,self.h[bar],self.l[bar],self.bo[bar],self.ao[bar],sl,tp,mult,max_hold_bars=max_hold_bars,backend=self.backend,max_matrix_bytes=max_matrix_bytes),
                           bounded_batches(ls,(-dr).astype(np.int8),self.h[bar],self.l[bar],self.bo[bar],self.ao[bar],sl,tp,mult,max_hold_bars=max_hold_bars,backend=self.backend,max_matrix_bytes=max_matrix_bytes))
            for (a0,b0,mp0,d0),(_,_,mm0,_),(a1,b1,mp1,d1),(_,_,mm1,_) in zip(its['D0'][0],its['D0'][1],its['D1'][0],its['D1'][1]):
                devs['D0'],devs['D1']=d0,d1
                if (a0,b0)!=(a1,b1):raise RuntimeError('D0/D1 config batches misaligned')
                yield a0,b0,[(mp0,mm0),(mp1,mm1)]
        res,obs=max_null_batched(gen(),sizes,days,n_sims,seed,flip,min_trades)
        normal=[i for i,c in enumerate(self.cfg) if c.get('direction','normal')=='normal']
        head_i=max(normal,key=lambda i:obs[i]) if normal else None
        plateau={'status':'NO_FINITE_CANDIDATE'};head=None
        if head_i is not None and np.isfinite(obs[head_i]):
            fam=self.cfg[head_i]['family_id'];cells={}
            for i in normal:
                if self.cfg[i]['family_id']!=fam:continue
                k=(int(sl[i]),int(tp[i]))
                if k in cells:raise ValueError(f'duplicate (sl,tp) {k} in family {fam}; plateau needs one cell per grid point')
                cells[k]=float(obs[i])  # -inf (too few trades) stays in the grid as a non-positive neighbour
            head=(int(sl[head_i]),int(tp[head_i]));plateau=plateau_report(cells,(sorted({k[0] for k in cells}),sorted({k[1] for k in cells})),head);plateau['family_id']=fam
        n_camp=self.reg.n_campaigns();adj=sidak_bonferroni(res['p_max'],n_camp)
        rejected=adj['bonferroni']<=.05 and plateau['status']=='PLATEAU'
        verdict='CANDIDATE_REQUIRES_FUTURE_CONFIRMATION' if rejected else 'NOT_REJECTED_NO_DIRECTIONAL_EVIDENCE'
        payload={'stage':'E4_MULTIPLICITY','max_null':res,'p_max_campaigns_adjusted':{**adj,'n_campaigns':n_camp},'plateau':plateau,'headline':list(head) if head else None,'global_trials_registered':self.reg.total(),'campaign_trials':len(self.cfg),'registry':self.reg.verify(),'verdict':verdict,'d2_prices_passed':False,'holdout_guard':self._guard(),'holdout_opened':False if self.holdout_first_date is not None else 'UNVERIFIED','promotion_allowed':False,'asserts_edge':False,'kernels':{p:kernel_manifest(d.backend) for p,d in devs.items()}}
        rid='FUNNEL-E4-'+hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()[:16];self.ledger.append('multiplicity_recorded',rid,payload);(self.out/'multiplicity.json').write_text(json.dumps(payload,indent=2,default=str));return payload
