"""Kaggle-only bounded, shared-pass six-model development benchmark."""
import argparse,json,math,os,resource,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from .phenomena import ClockMeasurements
from .phenomena_response import SecondsResponse
from .phenomena_science_pilot import USABLE,add
from .kaggle_session_reader import iter_sessions
from .phenomena_models import TRAIN,EVAL,MODELS,CAL_SHA,FEATURES,verified_calibration,phase_key,state,features,design,fit,predict,brier
from .build_target_free_pilot import digest
from .source_footer import validate_pin
CAL_PATH='docs/research/ops/MNQ_PHENOMENA_MODEL_FROZEN_CALIBRATION.json'
FIXED={'schema':'mnq_phenomena_model_available_plan_v1','missing_session_policy':'REPORT_SOURCE_EMPTY_NO_REPLACEMENT_NO_OUTCOME_BASED_EXCLUSION','minimum_available_evaluation_sessions':6,'prior_strict_plan_sha256':'80eb37bfeeb2c5f3b3a6c04afd9a230e4d10b337e6f4a57cd9ec36aa860c3a20','training_sessions':list(TRAIN),'evaluation_sessions':list(EVAL),'calibration_sha256':CAL_SHA,'ridge_lambda':.01,'models':list(MODELS),'max_session_ticks':8000000,'max_total_ticks':100000000,'max_anchors':250000,'max_scan_elements_per_session':150000000,'max_scan_elements_total':1800000000,'max_aggregate_bytes':1048576,'wall_seconds':1800,'cpu_seconds':1800,'rss_bytes':4294967296,'address_space_bytes':6442450944,'transport_wall_seconds':600,'parent_wall_seconds':2700,'requested_notebook_timeout_seconds':3600,'window_seconds':20,'context_seconds':60,'grid_seconds':5,'max_gap_ns':2000000000,'response_horizon_ns':60000000000,'barrier_min_ticks':4,'barrier_trailing_range_multiplier':.5,'minimum_signed_volume_coverage':.8,'holdout':False,'pnl':False,'inference':False,'confirmation':False,'zone_detectors':False,'raw_export':False,'canonical_brain_write':False,'private_rows_persisted':False,'fitting_outcomes_previously_inspected':True,'scope_extension':'FIRST_12_WEEKDAY_RESEARCH_TRADE_DATES_AFTER_JUNE16_INCLUDING_JUNE19_HOLIDAY_NO_REPLACEMENT','metric':'SUM_THREE_CLASS_BRIER_EQUAL_SESSION_MEAN','feature_standardization':'TRAIN_ONLY_EQUAL_SESSION_WEIGHTS','capacity_control':'TWO_PREDEFINED_CONTINUOUS_INTERACTION_TERMS_NOT_ALL_NONLINEAR_MODELS','a_e_interaction_fitted':False}

SAFE_GUARD_CODES={'P0 measurement roster fixed': 'GUARD_001', 'aggregate byte cap': 'GUARD_002', 'all exact natural sessions; no replacement': 'GUARD_003', 'anchor capacity; no silent partial census': 'GUARD_004', 'anchor identity': 'GUARD_005', 'bound natural-session clock; no mislabeled split': 'GUARD_006', 'bounded equal-length session arrays': 'GUARD_007', 'bounded exact nonnegative integer volume': 'GUARD_008', 'bounded integer response tape': 'GUARD_009', 'bounded source identity': 'GUARD_010', 'calibration anchor budget': 'GUARD_011', 'calibration training date fixed; no eval rows': 'GUARD_012', 'canonical preholdout trade date': 'GUARD_013', 'chronological development split': 'GUARD_014', 'common observable feature population': 'GUARD_015', 'complete fixed session coverage required': 'GUARD_016', 'exact source pin contract required': 'GUARD_017', 'explicit benchmark research dates': 'GUARD_018', 'explicit quote-volume coverage': 'GUARD_019', 'feature coverage': 'GUARD_020', 'finite fixed inference matrix': 'GUARD_021', 'finite fixed ridge training': 'GUARD_022', 'finite nonnegative feature': 'GUARD_023', 'finite positive response budgets': 'GUARD_024', 'finite reader budgets': 'GUARD_025', 'finite signed feature': 'GUARD_026', 'finite state components': 'GUARD_027', 'finite state ratios': 'GUARD_028', 'fit must precede all evaluation reads': 'GUARD_029', 'fixed design name': 'GUARD_030', 'fixed usable response labels': 'GUARD_031', 'fixed60s positive whole-tick barrier': 'GUARD_032', 'frozen calibration hash': 'GUARD_033', 'full range exceeds tick budget; no silent prefix truncation': 'GUARD_034', 'int64 response bounds': 'GUARD_035', 'integer coordinates in int64 range': 'GUARD_036', 'market benchmark requires Kaggle': 'GUARD_037', 'measurement wall budget': 'GUARD_038', 'midpoint bounds': 'GUARD_039', 'natural session clock binding': 'GUARD_040', 'natural session exceeds memory budget; no reset/truncation': 'GUARD_041', 'nonempty bounded range': 'GUARD_042', 'null runtime input; no imputation': 'GUARD_043', 'observed anchor and prior direction': 'GUARD_044', 'ordered preholdout response tape': 'GUARD_045', 'ordered preholdout source; no sort or truncation': 'GUARD_046', 'pair/window eligibility mismatch': 'GUARD_047', 'pinned basename only': 'GUARD_048', 'pinned regular source file required': 'GUARD_049', 'poisoned response engine': 'GUARD_050', 'population reconciliation': 'GUARD_051', 'positive finite budgets': 'GUARD_052', 'positive source measurements required': 'GUARD_053', 'prebound preholdout range required': 'GUARD_054', 'private state outside output directory': 'GUARD_055', 'published frozen calibration only': 'GUARD_056', 'quote coordinate bounds': 'GUARD_057', 'range pushdown unavailable; no whole-file fallback': 'GUARD_058', 'response capacity/deadline; no truncation': 'GUARD_059', 'response scan budget; no truncation': 'GUARD_060', 'retrograde session': 'GUARD_061', 'row group intersects closed holdout; no payload read': 'GUARD_062', 'same approved source only': 'GUARD_063', 'session common usable support below 100; no substitution': 'GUARD_064', 'signed prior direction': 'GUARD_065', 'source SHA256 pin': 'GUARD_066', 'source bytes mismatch': 'GUARD_067', 'source order invalid; no sorting': 'GUARD_068', 'source outside bounded preholdout scope': 'GUARD_069', 'source rows mismatch': 'GUARD_070', 'source size mismatch': 'GUARD_071', 'three-class probability simplex': 'GUARD_072', 'valid signed coverage': 'GUARD_073', 'whole benchmark scan cap': 'GUARD_074', 'whole benchmark tick cap': 'GUARD_075', 'whole benchmark wall cap': 'GUARD_076'}
SAFE_GUARD_CODES.update({'exact selected session only':'GUARD_077','selected session missing; no replacement':'GUARD_078','training session absent; no supervised substitution':'GUARD_079','available evaluation support below six sessions':'GUARD_080'})
SAFE_FAILURE_STAGES=frozenset(("PREFLIGHT","READ_SESSION","MEASURE_CLASSIFY_AND_LABEL","FIT_MODELS","SCORE_MODELS","FINALIZE"))

def failure_receipt(exc,progress):
    """Closed static diagnostics; no values, private clocks or arbitrary text."""
    stage=progress.get("stage");date=progress.get("trade_date")
    return {"schema":"phenomena_model_failure_v2","status":"FAILED_NO_SCIENTIFIC_CLAIM","exception_type":type(exc).__name__ if type(exc) in (ValueError,TimeoutError,MemoryError) else "UNCLASSIFIED_EXCEPTION","guard_code":SAFE_GUARD_CODES.get(str(exc),"UNCLASSIFIED_STATIC_GUARD"),"stage":stage if stage in SAFE_FAILURE_STAGES else "UNCLASSIFIED_STAGE","trade_date":date if date in TRAIN+EVAL else None,"outcomes_complete":False,"raw_exported":False,"partial_success":False}

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

def one_session(source,r,p):
    """Exact range, no relabeling/replacement. Empty range yields no session."""
    found=0
    for st in iter_sessions(source,start_ns=r['start_ns'],end_ns=r['end_ns'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_total_ticks']):
        found+=1;actual=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
        if found!=1 or actual!=r['trade_date']:raise ValueError('exact selected session only')
        yield st

def session_data(st,date,plan,cal,started,*,feature_callback=None):
    t=st.ticks;m=ClockMeasurements(max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=plan['wall_seconds'])
    response=SecondsResponse(t.ts_ns,t.sequence,t.bid_ticks,t.ask_ticks,max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],max_scan_elements=plan['max_scan_elements_per_session'],wall_seconds=plan['wall_seconds'])
    rows=m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=date)
    research_dates=plan.get('research_dates')
    xs=[];ccs=[];aes=[];ys=[];keys=[];states=[];census={};reasons={};labels={};anchors=0
    for row in rows:
        if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole benchmark wall cap')
        anchors+=1;s=state(row,cal,research_dates=research_dates)['state'];add(census,s)
        if s=='UNKNOWN':add(reasons,'CLASSIFICATION_UNKNOWN');continue
        ctx=row['windows']['60']['current']
        if ctx['status']!='OBSERVABLE':add(reasons,'ORIGIN_60S_CONTEXT_UNKNOWN');continue
        d=max(4,math.ceil(.5*ctx['range_midpoint_ticks']));x,cc=features(row,d,research_dates=research_dates)
        i=int(np.searchsorted(t.sequence,row['sequence']))
        if i>=len(t.sequence) or int(t.sequence[i])!=row['sequence'] or int(t.ts_ns[i])!=row['timestamp_ns']:raise ValueError('anchor identity')
        lab=response.label(i,direction=row['windows']['20']['direction_from_prior'],distance_ticks=d)
        add(labels,lab['status'])
        if not lab['usable']:add(reasons,lab['status']);continue
        if lab['status'] not in USABLE:raise ValueError('fixed usable response labels')
        if feature_callback is not None:feature_callback(row,i,d)
        xs.append(x);ccs.append(cc);aes.append([int(s in ('A_ONLY','BOTH')),int(s in ('E_ONLY','BOTH'))]);ys.append(USABLE.index(lab['status']));keys.append(phase_key(row,research_dates=research_dates));states.append(s)
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

def run(source,plan,private_root,cal,*,progress=None):
    progress={} if progress is None else progress;progress.update(stage="PREFLIGHT",trade_date=None)
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market benchmark requires Kaggle')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private state outside output directory')
    validate_plan(plan);verified_calibration(cal);started=time.monotonic();training=[];tr=[];ev=[];ticks=scan=0;models=prior=reference=None;fit_seconds=None;unavailable=[]
    for r in plan['session_ranges']:
        progress.update(stage='READ_SESSION',trade_date=r['trade_date'])
        found=False
        for st in one_session(source,r,plan):
            found=True
            ticks+=len(st.ticks.ts_ns)
            if ticks>plan['max_total_ticks']:raise ValueError('whole benchmark tick cap')
            progress.update(stage='MEASURE_CLASSIFY_AND_LABEL')
            data=session_data(st,r['trade_date'],plan,cal,started);scan+=data[-1]['response_scanned_elements']
            if scan>plan['max_scan_elements_total']:raise ValueError('whole benchmark scan cap')
            if r['trade_date'] in TRAIN:
                training.append(data[:4]);tr.append(data[-1])
                if r['trade_date']==TRAIN[-1]:
                    progress.update(stage='FIT_MODELS')
                    f=time.monotonic();models,prior,reference=fit_models(training);fit_seconds=time.monotonic()-f;training.clear()
            else:
                if models is None:raise ValueError('fit must precede all evaluation reads')
                progress.update(stage='SCORE_MODELS')
                ev.append(score(data,models,prior,reference))
            del data,st
            if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole benchmark wall cap')
        if not found:
            if r['trade_date'] in TRAIN:raise ValueError('training session absent; no supervised substitution')
            unavailable.append({'trade_date':r['trade_date'],'status':'SOURCE_EMPTY_NO_TICKS_IN_EXACT_PRESELECTED_RANGE','replacement_selected':False,'response_read':False})
    progress.update(stage='FINALIZE',trade_date=None)
    if len(tr)!=len(TRAIN) or len(ev)+len(unavailable)!=len(EVAL):raise ValueError('complete fixed session coverage required')
    if len(ev)<6:raise ValueError('available evaluation support below six sessions')
    result={'schema':'mnq_phenomena_model_available_receipt_v1','status':'DEVELOPMENT_BENCHMARK_COMPLETE_FOR_AVAILABLE_PRESELECTED_SESSIONS_NOT_EDGE','unavailable_evaluation_sessions':unavailable,'requested_evaluation_sessions':list(EVAL),'available_evaluation_session_count':len(ev),'original_strict12_protocol_succeeded':False,'plan_sha256':digest(plan),'calibration_sha256':cal['sha256'],'training_sessions':tr,'evaluation_sessions':ev,'feature_names':list(FEATURES),'model_feature_counts':{'PRIOR':0,**{n:len(m['mean']) for n,m in models.items()}},'training_reference':{k:v.tolist() for k,v in reference.items()},'training_equal_session_prior':prior.tolist(),'mean_session_brier':{n:float(np.mean([s['scores']['mean_brier'][n] for s in ev])) for n in MODELS},'total_ticks':ticks,'response_scanned_elements':scan,'fit_seconds':fit_seconds,'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'THIS_LINUX_RUNNER_PROCESS_NOT_CGROUP','new_inference':False,'confirmation':False,'holdout_opened':False,'pnl':False,'raw_exported':False,'private_rows_persisted':False,'canonical_brain_written':False,'training_outcomes_previously_inspected':True,'a_e_mechanisms_identified':False,'automatic_model_selection':False,'overlapping_anchors_independent':False,'scored_model_count':len(MODELS)}
    if len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('aggregate byte cap')
    return result

def main():
    ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];x=ap.parse_args();progress={}
    try:
        result=run(x.source,json.loads(Path(x.plan).read_bytes()),x.private_root,json.loads(Path(CAL_PATH).read_bytes()),progress=progress);Path(x.receipt).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        Path(x.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps(failure_receipt(exc,progress))+'\n');raise
if __name__=='__main__':main()
