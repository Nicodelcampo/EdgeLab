"""Bounded Kaggle-only 18 cross-family fixed development comparisons.

Existing inspected research dates; not an independent confirmation. Shared
causal anchors and labels, no touch-only selection, no automatic winners.
"""
import argparse,json,os,resource,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from .build_target_free_pilot import digest
from .source_footer import validate_pin
from .kaggle_session_reader import iter_sessions
from .phenomena_model_pilot import session_data,CAL_PATH
from .phenomena_models import TRAIN,EVAL,verified_calibration,fit,predict,brier
from .cross_family_design import MODELS,COUNTS,design
from .cross_family_scene import CrossFamilyScene
from .cross_family_collector import CrossFamilyCollector
PLAN='docs/research/ops/MNQ_CROSS_FAMILY_PLAN.json'
ROSTER='docs/research/ops/MNQ_CROSS_FAMILY_PARAMETER_ROSTER.json'
PLAN_SHA='db73695c1846de91c1dbd2fe5ba389f1b79c861cb0969611ac22dfd1f756c1ec'
STAGES=frozenset(('PREFLIGHT','READ_AND_DETECT','MEASURE_CONTEXT_AND_LABEL','FIT','SCORE','FINALIZE'))
COMPARISONS=(('GEOMETRY','GEOMETRY_CC'),('ARRIVAL','ARRIVAL_CC'),('INTERACTION','INTERACTION_CC'),('DENSITY','CONTINUOUS'),('INTERACTION','MIRROR_FULL'))

def validate_plan(p,roster):
    if digest(p)!=PLAN_SHA:raise ValueError('immutable crossfamily development plan')
    if digest({k:v for k,v in roster.items() if k!='roster_sha256'})!=p['roster_sha256'] or roster['roster_sha256']!=p['roster_sha256']:raise ValueError('immutable nine profile18pair roster')
    if p['training_sessions']!=list(TRAIN) or p['evaluation_sessions']!=list(EVAL):raise ValueError('fixed inspected natural calendar')
    validate_pin(p['pin']);return p

def fit_models(training):
    x=np.concatenate([q[0] for q in training]);z=np.concatenate([q[1] for q in training]);y=np.concatenate([q[2] for q in training])
    w=np.concatenate([np.full(len(q[2]),1/len(q[2])/len(training)) for q in training]);prior=w@np.eye(3)[y]
    continuous=fit(x,y,w);pairs=[]
    for p in range(z.shape[2]):pairs.append({name:fit(design(x,z[:,:,p],name),y,w) for name in MODELS})
    return continuous,pairs,prior

def score(data,z,models,prior,roster):
    x=data[0];y=data[3];phases=data[4];states=data[5];s=data[-1];continuous,pairs=models
    base={'PRIOR':brier(np.broadcast_to(prior,(len(y),3)),y),'CONTINUOUS':brier(predict(continuous,x),y)}
    s['baseline_mean_brier']={n:float(v.mean()) for n,v in base.items()};s['pairs']=[]
    def group(mask,loss):
        return {'anchors':int(mask.sum()),'response_counts':np.bincount(y[mask],minlength=3).tolist(),'mean_brier':{name:float(v[mask].mean()) for name,v in loss.items()}}
    for p,identity in enumerate(roster['pairs']):
        loss={**base,**{name:brier(predict(pairs[p][name],design(x,z[:,:,p],name)),y) for name in MODELS}}
        means={name:float(v.mean()) for name,v in loss.items()}
        # These are common-anchor pooled descriptive cuts, not additional IID tests.
        geom=z[:,0,p,8:25];ages=geom[:,4:10];joint=geom[:,2];inside=geom[:,3]
        buckets={'NO_LOCAL_JOINT':joint==0,'LOCAL_JOINT_NOT_INSIDE_BOTH':(joint>0)&(inside==0),'INSIDE_BOTH':inside==1}
        for j,name in enumerate(('DISJOINT','EDGE_CONTACT','PARTIAL_OVERLAP','CONTAINMENT','IDENTICAL')):buckets['NEAREST_RELATION:'+name]=geom[:,10+j]==1
        buckets['NEAREST_RELATION:MISSING_COMPONENT']=geom[:,10:15].sum(axis=1)==0
        for a in range(3):
            for b in range(3):buckets[f'AGE_PAIR:{a}:{b}']=(ages[:,a]==1)&(ages[:,3+b]==1)
        s['pairs'].append({'pair_sha256':identity['pair_sha256'],'scores':group(np.ones(len(y),bool),loss),'paired_deltas':{a+'_MINUS_'+b:float((loss[a]-loss[b]).mean()) for a,b in COMPARISONS},'phase_direction_scores':{k:group(phases==k,loss) for k in sorted(set(phases))},'proxy_state_scores':{k:group(states==k,loss) for k in sorted(set(states))},'scenario_scores':{k:group(mask,loss) for k,mask in buckets.items() if mask.any()},'actual_and_mirror_feature_mean':z[:,:,p].mean(axis=0).tolist()})
    return s

def run(source,plan,private_root,cal,*,progress=None):
    progress={} if progress is None else progress;progress.update(stage='PREFLIGHT',trade_date=None)
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market crossfamily benchmark requires Kaggle')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private state outside outputs')
    roster=json.loads(Path(ROSTER).read_bytes());validate_plan(plan,roster);verified_calibration(cal)
    started=time.monotonic();scene=CrossFamilyScene(roster,plan);train=[];tr=[];ev=[];seen=set();scan=hits=pq=pl=0;warmup_sessions=warmup_ticks=0;models=prior=None;fit_seconds=0.
    for st in iter_sessions(source,start_ns=plan['warmup_start_ns'],end_ns=plan['read_end_ns'],max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_total_ticks']):
        date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat();selected=date in TRAIN+EVAL;progress.update(stage='READ_AND_DETECT',trade_date=date if selected else None)
        events,diag=scene.session(st,date,retain=selected)
        if not selected:warmup_sessions+=1;warmup_ticks+=len(st.ticks);continue
        if date in seen:raise ValueError('duplicate selected session')
        seen.add(date);progress.update(stage='MEASURE_CONTEXT_AND_LABEL')
        collector=CrossFamilyCollector(st,date,events,roster,plan);data=session_data(st,date,plan,cal,started,feature_callback=collector);z,meta=collector.finish(len(data[3]));data[-1]['crossfamily_context']=meta;data[-1]['native_scene']=diag
        scan+=data[-1]['response_scanned_elements'];hits+=meta['profile_query_hits'];pq+=meta['print_queries'];pl+=meta['print_level_queries']
        if any(value>plan[key] for value,key in ((scan,'max_scan_elements_total'),(hits,'max_total_context_query_hits'),(pq,'max_total_print_queries'),(pl,'max_total_print_level_queries'))):raise ValueError('whole crossfamily measurement budget')
        if date in TRAIN:
            train.append((data[0],z.copy(),data[3]));tr.append(data[-1])
            if date==TRAIN[-1]:
                if [s['trade_date'] for s in tr]!=list(TRAIN):raise ValueError('original complete training roster')
                progress.update(stage='FIT');f=time.monotonic();continuous,pairs,prior=fit_models(train);models=continuous,pairs;fit_seconds=time.monotonic()-f;train.clear()
        else:
            if models is None:raise ValueError('fit strictly before evaluation')
            progress.update(stage='SCORE');ev.append(score(data,z,models,prior,roster))
        del data,z,collector,events,st
        if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole crossfamily wall')
    progress.update(stage='FINALIZE',trade_date=None);eof=scene.finish()
    if not all(d in seen for d in TRAIN):raise ValueError('required training data unavailable')
    missing=[{'trade_date':d,'status':'SOURCE_EMPTY_NO_REPLACEMENT','replacement_selected':False} for d in EVAL if d not in seen]
    if len(ev)<plan['minimum_available_evaluation_sessions'] or len(ev)+len(missing)!=len(EVAL):raise ValueError('fixed evaluation calendar census')
    result={'schema':'mnq_crossfamily_development_receipt_v1','status':'DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE','plan_sha256':digest(plan),'roster_sha256':roster['roster_sha256'],'calibration_sha256':cal['sha256'],'training_sessions':tr,'evaluation_sessions':ev,'requested_evaluation_sessions':list(EVAL),'unavailable_evaluation_sessions':missing,'available_evaluation_session_count':len(ev),'baseline_mean_session_brier':{name:float(np.mean([s['baseline_mean_brier'][name] for s in ev])) for name in ('PRIOR','CONTINUOUS')},'pairs':[{**identity,'mean_session_brier':{name:float(np.mean([s['pairs'][p]['scores']['mean_brier'][name] for s in ev])) for name in ('PRIOR','CONTINUOUS')+MODELS},'paired_delta_equal_session_mean':{a+'_MINUS_'+b:float(np.mean([s['pairs'][p]['paired_deltas'][a+'_MINUS_'+b] for s in ev])) for a,b in COMPARISONS}} for p,identity in enumerate(roster['pairs'])],'model_feature_counts':COUNTS,'models_including_shared_baselines':2+18*len(MODELS),'warmup_sessions':warmup_sessions,'warmup_ticks':warmup_ticks,'total_ticks':scene.ticks,'response_scanned_elements':scan,'context_query_hits':hits,'print_queries':pq,'print_level_queries':pl,'native_eof_diagnostics':eof,'native_stage_seconds':dict(scene.times),'fit_seconds':fit_seconds,'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'LINUX_RUNNER_PROCESS_NOT_CGROUP','read_once_continuous_source':True,'shared_bar_specs':plan['bar_specs'],'profile_views_per_anchor':18,'primary_pairs':18,'native_configs':9,'bt2a_bucket_preprocessing_shared':False,'retained_pair_graph':False,'rows_or_snapshots_persisted':False,'evaluation_outcomes_previously_inspected':True,'confirmation':False,'new_inference':False,'edge_claim':False,'holdout_opened':False,'pnl':False,'raw_exported':False,'canonical_brain_written':False,'automatic_model_selection':False,'overlapping_anchors_independent':False,'native_AVZ_liveness_measured':False,'physical_first_touch_measured':False,'zone_specific_attribution':False,'mirror_null_scope':plan['mirror_null_scope']}
    if len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('bounded aggregate output')
    return result

def main():
    p=argparse.ArgumentParser();[p.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];a=p.parse_args();progress={}
    try:
        r=run(a.source,json.loads(Path(a.plan).read_bytes()),a.private_root,json.loads(Path(CAL_PATH).read_bytes()),progress=progress);Path(a.receipt).write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        r={'schema':'crossfamily_failure_v1','status':'FAILED_NO_SCIENTIFIC_CLAIM','exception_type':type(exc).__name__ if type(exc) in (ValueError,TimeoutError,MemoryError) else 'UNCLASSIFIED_EXCEPTION','stage':progress.get('stage') if progress.get('stage') in STAGES else 'UNCLASSIFIED_STAGE','trade_date':progress.get('trade_date') if progress.get('trade_date') in TRAIN+EVAL else None,'partial_success':False,'raw_exported':False}
        Path(a.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps(r)+'\n');raise
if __name__=='__main__':main()
