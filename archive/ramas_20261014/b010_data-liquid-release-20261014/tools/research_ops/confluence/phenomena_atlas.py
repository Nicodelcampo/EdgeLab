"""Finite target-free atlas. Market rows stay in the Kaggle child process.

Same P0 measurements, no changed gates, states, outcomes, inferential tests or
zone detectors. Exact quantiles are descriptive and never become fitted gates.
"""
import argparse,hashlib,json,math,os,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .phenomena import ClockMeasurements
from .kaggle_session_reader import iter_sessions
from .build_target_free_pilot import digest

DATES=('2026-06-12','2026-06-15','2026-06-16')
WINDOWS=('5','20','60')
STATUSES=('OBSERVABLE','INCOMPLETE_HISTORY','NO_OBSERVED_TRADES','GAP_UNKNOWN','ZERO_VOLUME','QUOTE_UNKNOWN')
PAIR_METRICS=('pressure_ratio','trade_count_ratio','total_volume_ratio','directed_progress_ticks','prior_directed_progress_ticks')
METRICS=PAIR_METRICS+('pressure_volume','prior_pressure_volume','current_trade_count','prior_trade_count','current_volume','prior_volume','mean_trade_size_ratio','current_signed_volume_coverage','prior_signed_volume_coverage')
QUANTILES=(.1,.25,.5,.75,.9)
PRESSURE_EDGES=(.25,.5,1.,2.,4.)
PROGRESS_EDGES=(-8.,-2.,0.,2.,8.)

def validate_plan(p):
    if p.get('schema')!='mnq_phenomena_atlas_plan_v1' or p.get('target_sessions')!=list(DATES):raise ValueError('fixed atlas roster')
    for k in ('outcomes','classify_states','holdout','pnl','raw_export','inference','canonical_brain_write'):
        if p.get(k) is not False:raise ValueError('measurement-only atlas')
    fixed={'window_seconds':[5,20,60],'grid_seconds':5,'max_gap_ns':2000000000,'minimum_quote_volume_coverage':.8,
           'max_session_ticks':5000000,'max_total_ticks':8000000,'max_anchors':250000,'wall_seconds':900,'cpu_seconds':900,
           'rss_bytes':4294967296,'address_space_bytes':6442450944,'transport_wall_seconds':600,'parent_wall_seconds':1500,
           'requested_notebook_timeout_seconds':1800,'min_distribution_count':100,'max_aggregate_bytes':1048576,
           'quantiles':list(QUANTILES),'pressure_ratio_bin_edges':list(PRESSURE_EDGES),'progress_ticks_bin_edges':list(PROGRESS_EDGES)}
    for k,v in fixed.items():
        if p.get(k)!=v or (type(v) is int and type(p[k]) is not int) or (type(v) is float and type(p[k]) not in (int,float)):raise ValueError('fixed atlas limit/definition: '+k)
    if len(p.get('session_ranges',[]))!=3:raise ValueError('three fixed natural sessions')
    for d,r in zip(DATES,p['session_ranges']):
        end=int(datetime.fromisoformat(d+'T22:00:00+00:00').timestamp())*10**9
        if r!={'trade_date':d,'start_ns':end-86400*10**9,'end_ns':end}:raise ValueError('native summer CME session bounds')
    return p

def reason(pair):
    """Mutually exclusive priority: current invalid, prior invalid, then zero sign.

    Window status is itself the existing P0 first-failure rule, not an inventory
    of every simultaneously failed gate. Joint-status census preserves both.
    """
    if pair['status'] not in ('MEASURABLE_PAIR','UNKNOWN_PAIR') or type(pair['direction_from_prior']) is not int or pair['direction_from_prior'] not in (-1,0,1):raise ValueError('closed pair status and direction')
    a,b=pair['current']['status'],pair['prior']['status']
    if a not in STATUSES or b not in STATUSES:raise ValueError('closed window statuses')
    if a!='OBSERVABLE':r='CURRENT_'+a
    elif b!='OBSERVABLE':r='PRIOR_'+b
    elif not pair['direction_from_prior']:r='PRIOR_ZERO_SIGNED_FLOW'
    else:r='MEASURABLE_PAIR'
    if (r=='MEASURABLE_PAIR')!=(pair['status']=='MEASURABLE_PAIR'):raise ValueError('pair eligibility mismatch')
    return r

def quantiles(values,minimum):
    x=np.asarray(values,dtype=np.float64)
    if len(x) and not np.isfinite(x).all():raise ValueError('nonfinite aggregate input')
    return {'count':len(x),'quantiles':None if len(x)<minimum else dict(zip(map(str,QUANTILES),np.quantile(x,QUANTILES,method='linear').tolist())),
            'suppressed_below_count':minimum}

class AtlasAggregate:
    def __init__(self,*,minimum=100,max_anchors=250000):
        self.minimum=minimum;self.max_anchors=max_anchors;self.anchors=0
        self.windows={w:{'status_counts':{},'exclusive_reason_counts':{},'joint_window_status_counts':{},
                         'direction_counts':{},'metrics':{k:[] for k in METRICS},
                         'observable_current_metrics':{k:[] for k in ('signed_volume_coverage','quote_volume_coverage','mean_trade_size','spread_at_end_ticks')},
                         'pressure_progress_cell_counts':np.zeros((6,6),dtype=np.int64)} for w in WINDOWS}
    def add(self,row):
        if set(row['windows'])!=set(WINDOWS):raise ValueError('complete fixed windows')
        if self.anchors>=self.max_anchors:raise ValueError('aggregate anchor capacity; no truncation')
        self.anchors+=1
        for w,p in row['windows'].items():
            a=self.windows[w];rs=reason(p)
            for field,key in [('status_counts',p['status']),('exclusive_reason_counts',rs),
                              ('joint_window_status_counts',p['current']['status']+'|'+p['prior']['status']),
                              ('direction_counts',str(p['direction_from_prior']))]:a[field][key]=a[field].get(key,0)+1
            cur=p['current']
            if cur['status']=='OBSERVABLE':
                for k,v in a['observable_current_metrics'].items():
                    z=cur.get(k)
                    if z is not None:
                        if not math.isfinite(z):raise ValueError('finite observable metric')
                        v.append(z)
            if p['status']=='MEASURABLE_PAIR':
                now,prev=p['current'],p['prior'];side='buy_volume' if p['direction_from_prior']>0 else 'sell_volume'
                values={k:p.get(k) for k in PAIR_METRICS}
                values.update(pressure_volume=now[side],prior_pressure_volume=prev[side],current_trade_count=now['count'],prior_trade_count=prev['count'],current_volume=now['volume'],prior_volume=prev['volume'],mean_trade_size_ratio=now['mean_trade_size']/prev['mean_trade_size'],current_signed_volume_coverage=now['signed_volume_coverage'],prior_signed_volume_coverage=prev['signed_volume_coverage'])
                for k,v in a['metrics'].items():
                    z=values[k]
                    if z is None or not math.isfinite(z):raise ValueError('finite measurable metric')
                    v.append(z)
                ix=int(np.searchsorted(PRESSURE_EDGES,p['pressure_ratio'],side='right'))
                iy=int(np.searchsorted(PROGRESS_EDGES,p['directed_progress_ticks'],side='right'))
                a['pressure_progress_cell_counts'][ix,iy]+=1
    def finish(self):
        out={}
        for w,a in self.windows.items():
            for field in ('status_counts','exclusive_reason_counts','joint_window_status_counts','direction_counts'):
                if sum(a[field].values())!=self.anchors:raise ValueError('anchor crossfoot')
            n=a['status_counts'].get('MEASURABLE_PAIR',0)
            if int(a['pressure_progress_cell_counts'].sum())!=n:raise ValueError('joint-grid denominator')
            if any(len(x)!=n for x in a['metrics'].values()):raise ValueError('metric denominator')
            out[w]={k:a[k] for k in ('status_counts','exclusive_reason_counts','joint_window_status_counts','direction_counts')}
            out[w].update(anchor_denominator=self.anchors,measurable_pair_denominator=n,
                          measurable_metrics={k:quantiles(x,self.minimum) for k,x in a['metrics'].items()},
                          observable_current_metrics={k:quantiles(x,self.minimum) for k,x in a['observable_current_metrics'].items()},
                          pressure_progress_cell_counts=a['pressure_progress_cell_counts'].tolist())
        return out

def run(source,plan,private_root):
    if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('Kaggle host required')
    root=Path(private_root).resolve()
    if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private root cannot be output directory')
    validate_plan(plan);started=time.monotonic();total=0;sessions=[]
    for r in plan['session_ranges']:
        if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole atlas budget')
        found=0
        for st in iter_sessions(source,start_ns=r['start_ns'],end_ns=r['end_ns'],max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_total_ticks']):
            found+=1;actual=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
            if found!=1 or actual!=r['trade_date']:raise ValueError('exact natural session identity')
            total+=len(st.ticks.ts_ns)
            if total>plan['max_total_ticks']:raise ValueError('whole atlas tick budget; no truncation')
            m=ClockMeasurements(max_gap_ns=plan['max_gap_ns'],minimum_quote_volume_coverage=plan['minimum_quote_volume_coverage'],
                                max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=plan['wall_seconds'])
            aggregate=AtlasAggregate(minimum=plan['min_distribution_count'],max_anchors=plan['max_anchors']);h=hashlib.sha256();t=st.ticks
            for row in m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=actual):
                if time.monotonic()-started>plan['wall_seconds']:raise TimeoutError('whole atlas budget')
                # Hash private stream without persisting/exporting its rows.
                h.update((json.dumps(row,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode());aggregate.add(row)
            sessions.append({'trade_date':actual,'measurement':m.summary,'private_measurement_stream_sha256':h.hexdigest(),'atlas':aggregate.finish()})
            # Arrays/list references are released between sessions; no tick concatenation.
            del aggregate,m,t,st
        if found!=1:raise ValueError('selected session missing; no replacement')
    receipt={'schema':'mnq_phenomena_atlas_receipt_v1','status':'TARGET_FREE_ATLAS_COMPLETE_NOT_STATE_OR_EDGE_VALIDATION',
             'plan_sha256':digest(plan),'sessions':sessions,'session_count':len(sessions),'total_ticks':total,
             'wall_seconds':time.monotonic()-started,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
             'rss_scope':'THIS_LINUX_RUNNER_PROCESS_NOT_DESCENDANTS_OR_CGROUP','joint_grid_edges':{'pressure_ratio':list(PRESSURE_EDGES),'directed_progress_ticks':list(PROGRESS_EDGES),'assignment':'searchsorted_right; [-inf,e0),[e0,e1),...,[last,+inf)'},
             'quantiles_are_descriptive_not_fitted_gates':True,'source_quality_audit':False,'state_classification':False,'outcomes':False,'inference':False,
             'raw_exported':False,'private_rows_persisted':False,'canonical_brain_written':False,'holdout_opened':False,'pnl':False}
    if len((json.dumps(receipt,indent=2,allow_nan=False)+'\n').encode())>plan['max_aggregate_bytes']:raise ValueError('aggregate export byte cap')
    return receipt

def main():
    ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','private-root','receipt')];x=ap.parse_args()
    try:
        receipt=run(x.source,json.loads(Path(x.plan).read_bytes()),x.private_root)
        Path(x.receipt).write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    except Exception as exc:
        # Closed aggregate diagnosis only: never export paths/messages/private rows.
        Path(x.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps({'schema':'phenomena_atlas_failure_v1','status':'FAILED_NO_ATLAS_OR_EDGE_CLAIM','exception_type':type(exc).__name__,'raw_exported':False})+'\n')
        raise
if __name__=='__main__':main()
