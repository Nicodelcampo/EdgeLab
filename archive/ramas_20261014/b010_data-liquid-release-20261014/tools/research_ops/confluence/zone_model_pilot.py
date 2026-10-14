"""Kaggle-only fixed development benchmark: continuous + native zone context.

One continuous source pass incl. existing warmup, one native bar spec/config,
shared causal features and labels. Only aggregate receipts leave the runner.
No automatic winner selection, confirmation, holdout, P&L, or Brain writer.
"""
import argparse
import json
import math
import os
from pathlib import Path
import resource
import time
from datetime import datetime, timezone
import numpy as np
from .build_target_free_pilot import digest
from .source_footer import validate_pin
from .kaggle_session_reader import iter_sessions
from .phenomena_model_pilot import session_data, CAL_PATH
from .phenomena_models import TRAIN, EVAL, verified_calibration, fit, predict, brier
from .zone_context import ZoneContext, DENSITY_NAMES, GEOMETRY_NAMES, ARRIVAL_NAMES
from .zone_model_design import MODELS, FEATURE_COUNTS, design
from .zone_scene import ZoneScene
from .asof_intersections import Clock

PLAN='docs/research/ops/MNQ_ZONE_CONTEXT_PLAN.json'
PLAN_SHA='fa5ee4f318659ba7516e028f134b6683b92d846c403ab701a061f81e85cb89c1'
STAGES=frozenset(('PREFLIGHT','READ_AND_DETECT','MEASURE_CONTEXT_AND_LABEL','FIT','SCORE','FINALIZE'))


def validate_plan(plan):
    if digest(plan)!=PLAN_SHA:raise ValueError('immutable zone development plan')
    validate_pin(plan['pin']);return plan


class SessionContext:
    """Apply complete atomic batches before an anchor; no future final objects."""
    def __init__(self, st, date, events, plan):
        self.t=st.ticks;self.events=events;self.cursor=0;self.rows=[]
        self.ctx=ZoneContext(trade_date=date,max_active=plan['max_active_context'],
                    max_seen=plan['max_seen_context'],max_query_hits=plan['max_query_hits'],max_total_query_hits=plan['max_session_context_query_hits'])
        self.present={'AVZP2':0,'RACIMO':0};self.old={'AVZP2':0,'RACIMO':0}
    def __call__(self,row,i,barrier):
        t=self.t;c=Clock(row['timestamp_ns'],row['sequence'])
        while self.cursor<len(self.events) and self.events[self.cursor][0]<=c:
            ec,up,rem=self.events[self.cursor];self.ctx.apply(ec,upserts=up,removals=rem);self.cursor+=1
        # Same observed starting midpoint as the existing current 20s window.
        j=int(np.searchsorted(t.ts_ns,c.ns-20*10**9,side='right'))
        if j>=i:raise ValueError('observable prior endpoint required')
        pc=Clock(int(t.ts_ns[j]),int(t.sequence[j]))
        r=self.ctx.observe(c,midpoint2=int(t.bid_ticks[i])+int(t.ask_ticks[i]),prior_clock=pc,
                       prior_midpoint2=int(t.bid_ticks[j])+int(t.ask_ticks[j]),radius_ticks=barrier)
        self.rows.append(r['density']+r['geometry']+r['arrival'])
        for k,f in enumerate(('AVZP2','RACIMO')):
            self.present[f]+=int(r['nearest_present'][f]);self.old[f]+=int(r['arrival'][2+k])
    def finish(self,n):
        if len(self.rows)!=n:raise ValueError('one context row per common anchor')
        z=np.asarray(self.rows,float)
        if z.shape!=(n,16) or not np.isfinite(z).all():raise ValueError('finite common context population')
        meta={'common_anchors':n,'nearest_present_anchors':self.present,'unchanged_snapshot_at_prior_anchors':self.old,
              'observed_context_batches':self.cursor,'post_last_common_anchor_batches':len(self.events)-self.cursor,
              'context_query_hits':self.ctx.query_hits,'context_mutations':self.ctx.mutation_count,
              'retained_primary_snapshots_at_last_common_anchor':len(self.ctx.active),'zero_means_no_recognized_primary_snapshot_not_physical_absence':True}
        return z,meta


def matrices(data,z):return (data[0],z[:,:8],z[:,8:12],z[:,12:])

def fit_models(training):
    arrays=[np.concatenate([a[j] for a in training]) for j in range(5)]
    x,d,g,a,y=arrays
    w=np.concatenate([np.full(len(q[4]),1/len(q[4])/len(training)) for q in training])
    prior=w@np.eye(3)[y]
    models={name:fit(design(x,d,g,a,name),y,w) for name in MODELS if name!='PRIOR'}
    return models,prior


def score(data,z,models,prior):
    x,d,g,a=matrices(data,z);y=data[3];phases=data[4];states=data[5];s=data[-1]
    losses={name:brier(np.broadcast_to(prior,(len(y),3)) if name=='PRIOR' else
                     predict(models[name],design(x,d,g,a,name)),y) for name in MODELS}
    def group(mask):return {'anchors':int(mask.sum()),'mean_brier':{name:float(v[mask].mean()) for name,v in losses.items()}}
    s['scores']=group(np.ones(len(y),dtype=bool))
    s['phase_direction_scores']={k:group(phases==k) for k in sorted(set(phases))}
    s['proxy_state_scores']={k:group(states==k) for k in sorted(set(states))}
    s['paired_deltas']={left+'_MINUS_'+right:float((losses[left]-losses[right]).mean())
               for left,right in (('GEOMETRY','GEOMETRY_CC'),('ARRIVAL','ARRIVAL_CC'),('DENSITY','CONTINUOUS'),('GEOMETRY','DENSITY'),('ARRIVAL','GEOMETRY'))}
    s['context_feature_mean']=z.mean(axis=0).tolist()
    return s


def run(source,plan,private_root,cal,*,progress=None):
    progress={} if progress is None else progress;progress.update(stage='PREFLIGHT',trade_date=None)
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market zone benchmark requires Kaggle')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private state outside outputs')
    validate_plan(plan);verified_calibration(cal);started=time.monotonic();scene=ZoneScene(plan)
    train=[];tr=[];ev=[];seen=set();scan=0;query_hits=0;warmup_sessions=warmup_ticks=0;detector_seconds=0.;models=prior=None;fit_seconds=0.
    for st in iter_sessions(source,start_ns=plan['warmup_start_ns'],end_ns=plan['read_end_ns'],
                    max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_total_ticks']):
        date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
        progress.update(stage='READ_AND_DETECT',trade_date=date if date in TRAIN+EVAL else None)
        selected=date in TRAIN+EVAL;f=time.monotonic();events,diag=scene.session(st,date,retain=selected);detector_seconds+=time.monotonic()-f
        if not selected:
            warmup_sessions+=1;warmup_ticks+=len(st.ticks);continue
        if date in seen:raise ValueError('duplicate selected natural session')
        seen.add(date);progress.update(stage='MEASURE_CONTEXT_AND_LABEL')
        collector=SessionContext(st,date,events,plan)
        data=session_data(st,date,plan,cal,started,feature_callback=collector);z,meta=collector.finish(len(data[3]))
        query_hits+=meta['context_query_hits']
        if query_hits>plan['max_total_context_query_hits']:raise ValueError('whole context query budget')
        data[-1]['zone_context']=meta;data[-1]['native_scene']=diag;scan+=data[-1]['response_scanned_elements']
        if scan>plan['max_scan_elements_total']:raise ValueError('whole zone response scan budget')
        if date in TRAIN:
            train.append((*matrices(data,z),data[3]));tr.append(data[-1])
            if date==TRAIN[-1]:
                if [s['trade_date'] for s in tr]!=list(TRAIN):raise ValueError('complete original training roster')
                progress.update(stage='FIT');f=time.monotonic();models,prior=fit_models(train);fit_seconds=time.monotonic()-f;train.clear()
        else:
            if models is None:raise ValueError('fit before evaluation')
            progress.update(stage='SCORE');ev.append(score(data,z,models,prior))
        del data,z,collector,events,st
        if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole zone wall budget')
    progress.update(stage='FINALIZE',trade_date=None)
    if not all(d in seen for d in TRAIN):raise ValueError('missing required training session')
    unavailable=[{'trade_date':d,'status':'SOURCE_EMPTY_NO_TICKS_IN_EXACT_PRESELECTED_RANGE','replacement_selected':False} for d in EVAL if d not in seen]
    if len(ev)<plan['minimum_available_evaluation_sessions'] or len(ev)+len(unavailable)!=len(EVAL):raise ValueError('available calendar census')
    result={'schema':'mnq_zone_context_development_receipt_v1','status':'DEVELOPMENT_ZONE_BENCHMARK_COMPLETE_NOT_EDGE',
            'plan_sha256':digest(plan),'calibration_sha256':cal['sha256'],'training_sessions':tr,'evaluation_sessions':ev,
            'requested_evaluation_sessions':list(EVAL),'unavailable_evaluation_sessions':unavailable,
            'available_evaluation_session_count':len(ev),'mean_session_brier':{n:float(np.mean([s['scores']['mean_brier'][n] for s in ev])) for n in MODELS},
            'model_feature_counts':FEATURE_COUNTS,'context_feature_names':list(DENSITY_NAMES+GEOMETRY_NAMES+ARRIVAL_NAMES),
            'warmup_sessions':warmup_sessions,'warmup_ticks':warmup_ticks,'total_ticks':scene.total_ticks,
            'response_scanned_elements':scan,'context_query_hits':query_hits,'zone_specific_attribution':False,'native_detector_and_primitives_seconds':detector_seconds,'fit_seconds':fit_seconds,
            'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'rss_scope':'LINUX_RUNNER_PROCESS_NOT_CGROUP','read_once_continuous_source':True,'bar_specs_computed':1,
            'avzp2_configurations':1,'racimo_configurations':1,'retained_pair_graph':False,'sqlite_capture_store':False,
            'rows_or_snapshots_persisted':False,'evaluation_outcomes_previously_inspected':True,'confirmation':False,
            'new_inference':False,'edge_claim':False,'holdout_opened':False,'pnl':False,'raw_exported':False,
            'canonical_brain_written':False,'automatic_model_selection':False,'overlapping_anchors_independent':False,
            'native_zone_liveness_measured':False,'first_touch_measured':False,'bt2_or_bt2a_computed':False}
    if len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('zone aggregate byte cap')
    return result


def main():
    ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')]
    x=ap.parse_args();progress={}
    try:
        r=run(x.source,json.loads(Path(x.plan).read_bytes()),x.private_root,json.loads(Path(CAL_PATH).read_bytes()),progress=progress)
        Path(x.receipt).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        # No arbitrary exception strings, private rows, filenames or clocks.
        r={'schema':'zone_model_failure_v1','status':'FAILED_NO_SCIENTIFIC_CLAIM',
           'exception_type':type(exc).__name__ if type(exc) in (ValueError,TimeoutError,MemoryError) else 'UNCLASSIFIED_EXCEPTION',
           'stage':progress.get('stage') if progress.get('stage') in STAGES else 'UNCLASSIFIED_STAGE',
           'trade_date':progress.get('trade_date') if progress.get('trade_date') in TRAIN+EVAL else None,
           'partial_success':False,'raw_exported':False}
        Path(x.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps(r)+'\n');raise

if __name__=='__main__':main()
