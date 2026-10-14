"""Review aggregate atlas custody/crossfoot, never reads market payload.
Verification of aggregate arithmetic is not independent reconstruction of tape.
"""
import hashlib,math
from ..confluence.gc_pressure_progress import validate,CAL_SHA,METRICS,CORRELATIONS,STATES
from ..confluence.build_target_free_pilot import digest

def natural(x):
 if type(x) is not int or x<0:raise ValueError('natural count, bool rejected')
 return x

def grid(x,rows,cols):
 if type(x) is not list or len(x)!=rows or any(type(r) is not list or len(r)!=cols for r in x):raise ValueError('complete grid shape')
 return sum(natural(v) for r in x for v in r)

def check_census(x):
 n=natural(x['observed_anchors']);e=natural(x['eligible_anchors']);b=natural(x['nonoverlap_windows'])
 if set(x['state_counts'])!=set(STATES) or sum(natural(v) for v in x['state_counts'].values())!=n or n-x['state_counts']['UNKNOWN']!=e or b>e:raise ValueError('census population')
 es=bs=0
 for key,z in x['cells'].items():
  if key not in ('OTHER:-1','OTHER:1','RTH:-1','RTH:1'):raise ValueError('fixed phase/direction cells')
  ne=natural(z['eligible_anchors']);nb=natural(z['nonoverlap_windows']);es+=ne;bs+=nb
  if ne==0 or nb>ne:raise ValueError('cell populations')
  for name,rows,cols,target in [('pressure_progress_counts',4,5,ne),('prior_current_progress_counts',5,5,ne),('nonoverlap_pressure_progress_counts',4,5,nb),('nonoverlap_prior_current_progress_counts',5,5,nb)]:
   if grid(z[name],rows,cols)!=target:raise ValueError('grid crossfoot')
  # Progress column totals must agree between pressure and trajectory views.
  for prefix in ('','nonoverlap_'):
   a=z[prefix+'pressure_progress_counts'];bgrid=z[prefix+'prior_current_progress_counts']
   if [sum(row[j] for row in a) for j in range(5)]!=[sum(row[j] for row in bgrid) for j in range(5)]:raise ValueError('two-view progress marginal mismatch')
  if set(z['continuous_metrics'])!=set(METRICS):raise ValueError('declared continuous roster')
  for k,v in z['continuous_metrics'].items():
   q=v['quantiles'];m=v['mean']
   if type(q) is not list or len(q)!=5 or any(type(a) not in (int,float) or not math.isfinite(a) for a in q+[m]) or q!=sorted(q):raise ValueError('finite ordered descriptive statistics')
   if k not in ('directed_progress_ticks','prior_directed_progress_ticks') and (min(q)<0 or m<0):raise ValueError('nonnegative descriptor')
  if set(z['correlations'])!={a+':'+b for a,b in CORRELATIONS}:raise ValueError('correlation roster')
  for q in z['correlations'].values():
   a=q['pearson_descriptive'];undefined=q['undefined_if_constant']
   if type(undefined) is not bool or ((a is None)!=undefined) or (a is not None and (type(a) not in (int,float) or not math.isfinite(a) or not -1<=a<=1)):raise ValueError('descriptive correlation domain')
 if (es,bs)!=(e,b):raise ValueError('cell census crossfoot')
 return e,b

def review(boot,r,p,c,pkg,raw,previous):
 validate(p,c)
 if r['status']!='TARGET_FREE_PRESSURE_PROGRESS_COMPLETE_NOT_EDGE' or boot['status']!=r['status'] or boot['exit_code']!=0 or boot['stop_reason'] is not None:raise ValueError('terminal complete science/boot')
 if any(boot[k]!=pkg[k] for k in ('source_commit','bundle_sha256','plan_sha256')) or r['plan_sha256']!=digest(p) or r['calibration_sha256']!=CAL_SHA:raise ValueError('package plan custody')
 if hashlib.sha256(raw).hexdigest()!=boot['pressure_progress_receipt_sha256'] or len(raw)>p['max_aggregate_bytes'] or boot['transport_pin_verified'] is not True:raise ValueError('exact pinned aggregate')
 for k in ('evaluation_read','outcomes_requested','outcomes_computed','thresholds_changed','models_fitted','new_calibration','dataset_quality_audit','raw_exported','holdout_opened','pnl','canonical_brain_written'):
  if r[k] is not False:raise ValueError('target-free closed scope')
 for k in ('outcomes_requested','outcomes_computed','raw_exported','holdout_opened','pnl_computed','new_quality_audit'):
  if boot[k] is not False:raise ValueError('boot target-free scope')
 sessions=r['sessions']
 if [s['trade_date'] for s in sessions]!=p['training_sessions']:raise ValueError('all original sessions only')
 e,b=check_census(r['total_training']);counts=[check_census(s) for s in sessions]
 if sum(v[0] for v in counts)!=e or sum(v[1] for v in counts)!=b or sum(natural(s['ticks']) for s in sessions)!=r['total_ticks'] or r['total_ticks']>p['max_total_ticks']:raise ValueError('session/global populations')
 for k,z in r['total_training']['cells'].items():
  for name in ('pressure_progress_counts','prior_current_progress_counts','nonoverlap_pressure_progress_counts','nonoverlap_prior_current_progress_counts'):
   a=z[name]
   for i,row in enumerate(a):
    for j,v in enumerate(row):
     if v!=sum(s['cells'].get(k,{}).get(name,[[0]*len(row) for _ in a])[i][j] for s in sessions):raise ValueError('per-date grid crossfoot')
  for state in STATES:
   if r['total_training']['state_counts'][state]!=sum(s['state_counts'][state] for s in sessions):raise ValueError('date/global state crossfoot')
 # Population equality to immutable prior support census, not tuning calibration.
 if previous['calibration_sha256']!=CAL_SHA or r['total_ticks']!=previous['total_ticks']:raise ValueError('previous population identity')
 for a,z in zip(sessions,previous['sessions']):
  if a['trade_date']!=z['trade_date'] or a['ticks']!=z['ticks'] or a['observed_anchors']!=z['observed_anchors'] or a['state_counts']!={k:z['state_counts'].get(k,0) for k in STATES}:raise ValueError('unchanged prelabel census')
 limits=p['support_readiness'];date_count=sum(s['nonoverlap_windows']>=30 for s in sessions)
 ready=e>=limits['minimum_eligible_anchors'] and b>=limits['minimum_nonoverlap_windows'] and date_count>=limits['minimum_dates_with_30_nonoverlap_windows']
 expected={'descriptive_population_sufficient':ready,'dates_with_30_nonoverlap_windows':date_count,'supported_cells':[k for k,z in r['total_training']['cells'].items() if z['nonoverlap_windows']>=limits['minimum_cell_nonoverlap_windows']],'evaluation_authorized':False,'independent_episodes_claimed':False}
 if r['support_readiness']!=expected:raise ValueError('support disposition arithmetic, no authority')
 return {'status':'PASS_TARGET_FREE_CONTINUOUS_SUPPORT_AGGREGATE_RECONCILIATION_NOT_EDGE','receipt_sha256':hashlib.sha256(raw).hexdigest(),'plan_sha256':digest(p),'eligible_anchors':e,'nonoverlap_windows':b,'descriptive_population_sufficient':ready,'previous_prelabel_census_exact':True,'raw_market_read':False,'outcomes_read':False,'independent_tape_reconstruction':False,'evaluation_authorized':False,'canonical_brain_written':False}
