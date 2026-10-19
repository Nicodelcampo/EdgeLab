"""Finite development response pilot, Kaggle-only market, aggregate-only export.

One chronological calibration, one classification/response specification. No
zones, model fitting, significance tests, inferred mechanisms or trading.
"""
import argparse,json,math,os,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .phenomena import ClockMeasurements
from .phenomena_states import Calibration,classify,cell,STATES,DATE_TRAIN,EVAL_DATES
from .phenomena_response import SecondsResponse
from .kaggle_session_reader import iter_sessions
from .build_target_free_pilot import digest
USABLE=('CONTINUATION_FIRST','REVERSAL_FIRST','HORIZON_NO_OBSERVED_PASSAGE')

def validate_plan(p):
    required={'schema':'mnq_phenomena_science_pilot_plan_v1','training_session':DATE_TRAIN,'evaluation_sessions':list(EVAL_DATES),
              'window_seconds':20,'context_seconds':60,'grid_seconds':5,'max_gap_ns':2000000000,'minimum_quote_volume_coverage':.8,
              'minimum_signed_volume_coverage':.8,'minimum_calibration_cell_anchors':100,'pressure_high_quantile':.8,'pressure_low_quantile':.2,
              'stall_abs_progress_quantile':.2,'stall_abs_progress_cap_ticks':2.,'stall_range_quantile':.25,'stall_path_quantile':.25,
              'prior_impulse_min_ticks':4.,'pressure_decay_max_ratio':.5,'trade_count_decay_max_ratio':.5,
              'response_horizon_ns':60000000000,'barrier_min_ticks':4,'barrier_trailing_range_multiplier':.5,
              'max_session_ticks':5000000,'max_total_ticks':8000000,'max_anchors':250000,'max_scan_elements_per_session':100000000,
              'max_scan_elements_total':120000000,'max_aggregate_bytes':1048576,'wall_seconds':900,'cpu_seconds':900,
              'rss_bytes':4294967296,'address_space_bytes':6442450944,'transport_wall_seconds':600,'parent_wall_seconds':1500,
              'requested_notebook_timeout_seconds':1800,'classify_states':True,'outcomes':True,'holdout':False,'pnl':False,'inference':False,
              'raw_export':False,'canonical_brain_write':False,'fit_models':False,'zone_detectors':False,'phase_definition':'AMERICA_CHICAGO_0830_INCLUSIVE_1500_EXCLUSIVE'}
    for k,v in required.items():
        if p.get(k)!=v or (type(v) in (int,bool) and type(p[k]) is not type(v)):raise ValueError('fixed scientific protocol: '+k)
    dates=(DATE_TRAIN,)+EVAL_DATES
    if len(p['session_ranges'])!=3:raise ValueError('fixed three sessions')
    for d,r in zip(dates,p['session_ranges']):
        end=int(datetime.fromisoformat(d+'T22:00:00+00:00').timestamp())*10**9
        if r!={'trade_date':d,'start_ns':end-86400*10**9,'end_ns':end}:raise ValueError('natural session bounds')
    return p

def one_session(source,r,p):
    found=0
    for st in iter_sessions(source,start_ns=r['start_ns'],end_ns=r['end_ns'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_total_ticks']):
        found+=1;actual=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
        if found!=1 or actual!=r['trade_date']:raise ValueError('exact selected session only')
        yield st
    if found!=1:raise ValueError('selected session missing; no replacement')

def add(counter,key):counter[key]=counter.get(key,0)+1

def run(source,plan,private_root):
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market pilot requires Kaggle')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private state cannot be notebook outputs')
    validate_plan(plan);started=time.monotonic();ticks=0;scan=0;cal=Calibration();sessions=[];training=None;frozen=None
    for r in plan['session_ranges']:
        for st in one_session(source,r,plan):
            t=st.ticks;ticks+=len(t.ts_ns)
            if ticks>plan['max_total_ticks']:raise ValueError('whole-pilot tick cap; no truncation')
            m=ClockMeasurements(max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=plan['wall_seconds'])
            rows=m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=r['trade_date'])
            if r['trade_date']==DATE_TRAIN:
                for row in rows:
                    if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('pilot wall budget')
                    cal.add(row)
                frozen=cal.freeze();training={'trade_date':DATE_TRAIN,'measurement':m.summary,'responses_read':False,'calibration_eligible_anchors':cal.n}
            else:
                if frozen is None:raise ValueError('calibration must finish before evaluation')
                response=SecondsResponse(t.ts_ns,t.sequence,t.bid_ticks,t.ask_ticks,max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],max_scan_elements=plan['max_scan_elements_per_session'],wall_seconds=plan['wall_seconds'])
                states={s:0 for s in STATES};reasons={};outcomes={s:{} for s in STATES};controls={};cells={};barriers={};anchors=0
                for row in rows:
                    if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('pilot wall budget')
                    x=classify(row,frozen);state=x['state'];states[state]+=1;add(reasons,x['reason']);anchors+=1
                    prior_dir=row['windows']['20']['direction_from_prior'];ctx=row['windows']['60']['current']
                    if prior_dir not in (-1,1):label={'status':'ORIGIN_DIRECTION_UNKNOWN','usable':False}
                    elif ctx['status']!='OBSERVABLE':label={'status':'ORIGIN_60S_CONTEXT_UNKNOWN','usable':False}
                    else:
                        d=max(4,math.ceil(.5*ctx['range_midpoint_ticks']));add(barriers,str(d))
                        i=int(np.searchsorted(t.sequence,row['sequence']))
                        if i>=len(t.sequence) or int(t.sequence[i])!=row['sequence'] or int(t.ts_ns[i])!=row['timestamp_ns']:raise ValueError('feature/anchor identity')
                        label=response.label(i,direction=int(prior_dir),distance_ticks=d)
                    status=label['status'];add(outcomes[state],status);group=cell(row);by=cells.setdefault(group,{s:{} for s in STATES});add(by[state],status)
                    for tag in x['tags']:add(controls.setdefault(tag,{}),status)
                scan+=response.scanned
                if scan>plan['max_scan_elements_total']:raise ValueError('whole-pilot scan cap; no successful partial')
                if sum(states.values())!=anchors or any(sum(outcomes[s].values())!=states[s] for s in STATES):raise ValueError('state/response crossfoot')
                if sum(sum(v.values()) for g in cells.values() for v in g.values())!=anchors:raise ValueError('cell response crossfoot')
                sessions.append({'trade_date':r['trade_date'],'measurement':m.summary,'anchors':anchors,'state_counts':states,'classification_reason_counts':reasons,
                                 'state_response_counts':outcomes,'calibration_cell_state_response_counts':cells,'control_tag_response_counts':controls,'control_tags_may_overlap':True,
                                 'barrier_ticks_counts':barriers,'response_scanned_elements':response.scanned,'responses_usable_statuses':list(USABLE),'calibration_sha256':frozen['sha256']})
                del response
            del m,rows,t,st
    result={'schema':'mnq_phenomena_science_pilot_receipt_v1','status':'DEVELOPMENT_PROXY_RESPONSE_COMPLETE_NOT_EDGE_OR_MECHANISM_VALIDATION',
            'plan_sha256':digest(plan),'training':training,'calibration':frozen,'evaluation_sessions':sessions,'total_ticks':ticks,'response_scanned_elements':scan,
            'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'rss_scope':'THIS_LINUX_RUNNER_PROCESS_NOT_DESCENDANTS_OR_CGROUP','source_quality_audit':False,'training_outcomes_used':False,'model_incremental_value_tested':False,
            'inference':False,'holdout_opened':False,'pnl':False,'raw_exported':False,'private_rows_persisted':False,'canonical_brain_written':False}
    if len((json.dumps(result,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('aggregate byte cap')
    return result

def main():
    ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];x=ap.parse_args()
    try:
        result=run(x.source,json.loads(Path(x.plan).read_bytes()),x.private_root);Path(x.receipt).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        Path(x.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps({'schema':'phenomena_science_failure_v1','status':'FAILED_NO_SCIENTIFIC_CLAIM','exception_type':type(exc).__name__,'raw_exported':False})+'\n');raise
if __name__=='__main__':main()
