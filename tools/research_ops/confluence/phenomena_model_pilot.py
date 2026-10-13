"""Kaggle-only bounded, shared-pass six-model development benchmark."""
import argparse,json,math,os,resource,time
from pathlib import Path
from datetime import datetime
import numpy as np
from .phenomena import ClockMeasurements
from .phenomena_response import SecondsResponse
from .phenomena_science_pilot import one_session,USABLE,add
from .phenomena_models import TRAIN,EVAL,MODELS,CAL_SHA,FEATURES,verified_calibration,phase_key,state,features,design,fit,predict,brier
from .build_target_free_pilot import digest
from .source_footer import validate_pin
CAL_PATH='docs/research/ops/MNQ_PHENOMENA_MODEL_FROZEN_CALIBRATION.json'
FIXED={'schema':'mnq_phenomena_model_plan_v1','training_sessions':list(TRAIN),'evaluation_sessions':list(EVAL),'calibration_sha256':CAL_SHA,'ridge_lambda':.01,'models':list(MODELS),'max_session_ticks':8000000,'max_total_ticks':100000000,'max_anchors':250000,'max_scan_elements_per_session':150000000,'max_scan_elements_total':1800000000,'max_aggregate_bytes':1048576,'wall_seconds':1800,'cpu_seconds':1800,'rss_bytes':4294967296,'address_space_bytes':6442450944,'transport_wall_seconds':600,'parent_wall_seconds':2700,'requested_notebook_timeout_seconds':3600,'window_seconds':20,'context_seconds':60,'grid_seconds':5,'max_gap_ns':2000000000,'response_horizon_ns':60000000000,'barrier_min_ticks':4,'barrier_trailing_range_multiplier':.5,'minimum_signed_volume_coverage':.8,'holdout':False,'pnl':False,'inference':False,'confirmation':False,'zone_detectors':False,'raw_export':False,'canonical_brain_write':False,'private_rows_persisted':False,'fitting_outcomes_previously_inspected':True,'scope_extension':'FIRST_12_WEEKDAY_RESEARCH_TRADE_DATES_AFTER_JUNE16_INCLUDING_JUNE19_HOLIDAY_NO_REPLACEMENT','metric':'SUM_THREE_CLASS_BRIER_EQUAL_SESSION_MEAN','feature_standardization':'TRAIN_ONLY_EQUAL_SESSION_WEIGHTS','capacity_control':'TWO_PREDEFINED_CONTINUOUS_INTERACTION_TERMS_NOT_ALL_NONLINEAR_MODELS','a_e_interaction_fitted':False}

def validate_plan(p):
    for k,v in FIXED.items():
        if p.get(k)!=v or type(p[k]) is not type(v):raise ValueError('fixed model benchmark: '+k)
    validate_pin(p['pin'])
    if (p['pin']['contract'],p['pin']['file'],p['pin']['dataset'],p['pin']['version'],p['pin']['sha256'],p['pin']['bytes'],p['pin']['rows'],p['pin']['max_ns'])!=('MNQ_09-26','MNQ_09-26_ticks_ext.parquet','nicolasbuttaro/edgelab-ticks-nt8-reexport-20261005',2,'5b234b0f94888c44ba5e68fb0aaf2b52138c70d9485daa2875fa028f8ab24b77',1251646827,110632331,1789738200000000000):raise ValueError('same approved source only')
    expected=[]
    for date in TRAIN+EVAL:
        end=int(datetime.fromisoformat(date+'T22:00:00+00:00').timestamp())*10**9
        expected.append({'trade_date':date,'start_ns':end-86400*10**9,'end_ns':end})
    if p['session_ranges']!=expected:raise ValueError('all exact natural sessions; no replacement')
    return p

def session_data(st,date,plan,cal,started):
    t=st.ticks;m=ClockMeasurements(max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=plan['wall_seconds'])
    response=SecondsResponse(t.ts_ns,t.sequence,t.bid_ticks,t.ask_ticks,max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],max_scan_elements=plan['max_scan_elements_per_session'],wall_seconds=plan['wall_seconds'])
    rows=m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=date)
    xs=[];ccs=[];aes=[];ys=[];keys=[];states=[];census={};reasons={};labels={};anchors=0
    for row in rows:
        if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole benchmark wall cap')
        anchors+=1;s=state(row,cal)['state'];add(census,s)
        if s=='UNKNOWN':add(reasons,'CLASSIFICATION_UNKNOWN');continue
        ctx=row['windows']['60']['current']
        if ctx['status']!='OBSERVABLE':add(reasons,'ORIGIN_60S_CONTEXT_UNKNOWN');continue
        d=max(4,math.ceil(.5*ctx['range_midpoint_ticks']));x,cc=features(row,d)
        i=int(np.searchsorted(t.sequence,row['sequence']))
        if i>=len(t.sequence) or int(t.sequence[i])!=row['sequence'] or int(t.ts_ns[i])!=row['timestamp_ns']:raise ValueError('anchor identity')
        lab=response.label(i,direction=row['windows']['20']['direction_from_prior'],distance_ticks=d)
        add(labels,lab['status'])
        if not lab['usable']:add(reasons,lab['status']);continue
        if lab['status'] not in USABLE:raise ValueError('fixed usable response labels')
        xs.append(x);ccs.append(cc);aes.append([int(s in ('A_ONLY','BOTH')),int(s in ('E_ONLY','BOTH'))]);ys.append(USABLE.index(lab['status']));keys.append(phase_key(row));states.append(s)
    n=len(ys)
    if anchors!=sum(census.values()) or anchors!=sum(reasons.values())+n:raise ValueError('population reconciliation')
    if n<100:raise ValueError('session common usable support below 100; no substitution')
    summary={'trade_date':date,'ticks':len(t.ts_ns),'anchors':anchors,'classification_state_counts':census,'excluded_counts':reasons,'labeled_response_counts':labels,'common_usable_anchors':n,'measurement':m.summary,'response_scanned_elements':response.scanned,'label_scope':'ONLY_CLASSIFIED_PROXY_WITH_OBSERVABLE_60S_CONTEXT; UNKNOWN_NOT_NEGATIVE','common_state_counts':{s:states.count(s) for s in sorted(set(states))},'common_response_counts':{v:int(ys.count(j)) for j,v in enumerate(USABLE)}}
    return np.array(xs),np.array(ccs),np.array(aes),np.array(ys,dtype=int),np.array(keys),np.array(states),summary

def fit_models(training):
    x,cc,ae,y=[np.concatenate([z[j] for z in training]) for j in range(4)]
    w=np.concatenate([np.full(len(z[3]),1./len(z[3])/len(training)) for z in training]);prior=w@np.eye(3)[y]
    models={name:fit(design(x,cc,ae,name),y,w) for name in MODELS if name!='PRIOR'}
    reference={'mean':w@x,'min':x.min(axis=0),'max':x.max(axis=0)}
    return models,prior,reference

def score(data,models,prior,reference):
    x,cc,ae,y,keys,states,summary=data;loss={}
    for name in MODELS:
        pr=np.broadcast_to(prior,(len(y),3)) if name=='PRIOR' else predict(models[name],design(x,cc,ae,name))
        loss[name]=brier(pr,y)
    def group(mask):return {'anchors':int(mask.sum()),'mean_brier':{name:float(v[mask].mean()) for name,v in loss.items()}}
    summary['scores']=group(np.ones(len(y),dtype=bool))
    summary['phase_direction_scores']={k:group(keys==k) for k in sorted(set(keys))}
    summary['proxy_state_scores']={s:group(states==s) for s in sorted(set(states))}
    summary['feature_mean']=x.mean(axis=0).tolist()
    summary['feature_outside_training_range_fraction']=((x<reference['min'])|(x>reference['max'])).mean(axis=0).tolist()
    summary['paired_delta_AE_minus_CONTINUOUS']=float((loss['CONTINUOUS_AE']-loss['CONTINUOUS']).mean())
    summary['paired_delta_AE_minus_CC']=float((loss['CONTINUOUS_AE']-loss['CONTINUOUS_CC']).mean())
    return summary

def run(source,plan,private_root,cal):
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market benchmark requires Kaggle')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private state outside output directory')
    validate_plan(plan);verified_calibration(cal);started=time.monotonic();training=[];tr=[];ev=[];ticks=scan=0;models=prior=reference=None;fit_seconds=None
    for r in plan['session_ranges']:
        for st in one_session(source,r,plan):
            ticks+=len(st.ticks.ts_ns)
            if ticks>plan['max_total_ticks']:raise ValueError('whole benchmark tick cap')
            data=session_data(st,r['trade_date'],plan,cal,started);scan+=data[-1]['response_scanned_elements']
            if scan>plan['max_scan_elements_total']:raise ValueError('whole benchmark scan cap')
            if r['trade_date'] in TRAIN:
                training.append(data[:4]);tr.append(data[-1])
                if r['trade_date']==TRAIN[-1]:
                    f=time.monotonic();models,prior,reference=fit_models(training);fit_seconds=time.monotonic()-f;training.clear()
            else:
                if models is None:raise ValueError('fit must precede all evaluation reads')
                ev.append(score(data,models,prior,reference))
            del data,st
            if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole benchmark wall cap')
    if len(tr)!=len(TRAIN) or len(ev)!=len(EVAL):raise ValueError('complete fixed session coverage required')
    result={'schema':'mnq_phenomena_model_receipt_v1','status':'DEVELOPMENT_REPRESENTATION_BENCHMARK_COMPLETE_NOT_EDGE','plan_sha256':digest(plan),'calibration_sha256':cal['sha256'],'training_sessions':tr,'evaluation_sessions':ev,'feature_names':list(FEATURES),'model_feature_counts':{'PRIOR':0,**{n:len(m['mean']) for n,m in models.items()}},'training_reference':{k:v.tolist() for k,v in reference.items()},'training_equal_session_prior':prior.tolist(),'mean_session_brier':{n:float(np.mean([s['scores']['mean_brier'][n] for s in ev])) for n in MODELS},'total_ticks':ticks,'response_scanned_elements':scan,'fit_seconds':fit_seconds,'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'THIS_LINUX_RUNNER_PROCESS_NOT_CGROUP','new_inference':False,'confirmation':False,'holdout_opened':False,'pnl':False,'raw_exported':False,'private_rows_persisted':False,'canonical_brain_written':False,'training_outcomes_previously_inspected':True,'a_e_mechanisms_identified':False,'automatic_model_selection':False,'overlapping_anchors_independent':False,'scored_model_count':len(MODELS)}
    if len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('aggregate byte cap')
    return result

def main():
    ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];x=ap.parse_args()
    try:
        result=run(x.source,json.loads(Path(x.plan).read_bytes()),x.private_root,json.loads(Path(CAL_PATH).read_bytes()));Path(x.receipt).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        Path(x.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps({'schema':'phenomena_model_failure_v1','status':'FAILED_NO_SCIENTIFIC_CLAIM','exception_type':type(exc).__name__,'raw_exported':False})+'\n');raise
if __name__=='__main__':main()
