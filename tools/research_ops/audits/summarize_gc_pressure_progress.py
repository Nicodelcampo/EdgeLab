import argparse,csv,hashlib,json,math
from pathlib import Path
RAW=OUT=OPS=None
def load(p):return json.loads(p.read_bytes())
def csvout(name,rows):
 p=OUT/name
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def prepare(r):
 sessions=[];joint=[];transitions=[];correlations=[]
 for date,x in [(s['trade_date'],s) for s in r['sessions']]+[('POOLED_TRAINING',r['total_training'])]:
  sessions.append({'trade_date':date,'observed_anchors':x['observed_anchors'],'eligible_anchors':x['eligible_anchors'],'unknown_anchors':x['state_counts']['UNKNOWN'],'nonoverlap_windows':x['nonoverlap_windows'],'A_ONLY':x['state_counts']['A_ONLY'],'BOTH':x['state_counts']['BOTH']})
  for cell,z in x['cells'].items():
   for i,row in enumerate(z['pressure_progress_counts']):
    for j,count in enumerate(row):joint.append({'trade_date':date,'phase_direction':cell,'pressure_bucket':i,'progress_bucket':j,'anchors':count,'nonoverlap_windows':z['nonoverlap_pressure_progress_counts'][i][j]})
   for i,row in enumerate(z['prior_current_progress_counts']):
    for j,count in enumerate(row):transitions.append({'trade_date':date,'phase_direction':cell,'prior_progress_bucket':i,'current_progress_bucket':j,'anchors':count,'nonoverlap_windows':z['nonoverlap_prior_current_progress_counts'][i][j]})
   for name,k in z['correlations'].items():correlations.append({'trade_date':date,'phase_direction':cell,'metric_pair':name,'pearson_descriptive':k['pearson_descriptive'],'undefined_if_constant':k['undefined_if_constant'],'anchors':z['eligible_anchors']})
 csvout('sessions.csv',sessions);csvout('pressure_progress.csv',joint);csvout('trajectories.csv',transitions);csvout('correlations.csv',correlations)
 print('Normalized 4 files. Grain: session; session/cell/4x5-bin; session/cell/5x5-bin; session/cell/metric-pair. POOLED is separate, not additive to dates.')
def analyze(r):
 allcells=r['total_training']['cells'];sessions=r['sessions'];metrics={}
 for sampled,prefix in [(False,''),(True,'nonoverlap_')]:
  q=sum(z[prefix+'pressure_progress_counts'][i][2] for z in allcells.values() for i in (2,3));name='nonoverlap' if sampled else 'anchors'
  traj=[sum(z[prefix+'prior_current_progress_counts'][4][j] for z in allcells.values() for j in js) for js in ((0,1),(2,),(3,4))]
  # Independent per-date path; don't average pooled quantiles or correlations.
  qt=sum(z[prefix+'pressure_progress_counts'][i][2] for s in sessions for z in s['cells'].values() for i in (2,3));assert qt==q
  separate=[sum(z[prefix+'prior_current_progress_counts'][4][j] for s in sessions for z in s['cells'].values() for j in js) for js in ((0,1),(2,),(3,4))];assert traj==separate
  matrix=sum(sum(z[prefix+'prior_current_progress_counts'][4]) for z in allcells.values());assert sum(traj)==matrix
  metrics[name]={'pressure_at_least_q80_and_small_net':q,'prior_progress_at_least_4_ticks_trajectories':dict(zip(('CURRENT_OPPOSITE_LT_MINUS2','CURRENT_SMALL_NET_MINUS2_TO_LT2','CURRENT_SAME_DIRECTION_GE2'),traj)),'prior_progress_at_least_4_total':matrix}
 perdate=[]
 for s in sessions:
  counts=[sum(z['nonoverlap_prior_current_progress_counts'][4][j] for z in s['cells'].values() for j in js) for js in ((0,1),(2,),(3,4))]
  perdate.append({'trade_date':s['trade_date'],'nonoverlap_windows':s['nonoverlap_windows'],'eligible_anchors':s['eligible_anchors'],'trajectories_nonoverlap':counts,'high_pressure_small_net_nonoverlap':sum(z['nonoverlap_pressure_progress_counts'][i][2] for z in s['cells'].values() for i in (2,3))})
 categories=['Avance previo → retroceso','Avance previo → neto pequeño','Avance previo → avance'];values=list(metrics['nonoverlap']['prior_progress_at_least_4_ticks_trajectories'].values())
 # Full scope correlations retained as descriptors only; do not pool cell means.
 correlation_ranges={}
 for pair in next(iter(allcells.values()))['correlations']:
  v=[z['correlations'][pair]['pearson_descriptive'] for s in sessions for z in s['cells'].values() if z['correlations'][pair]['pearson_descriptive'] is not None]
  correlation_ranges[pair]={'minimum_over_date_cells':min(v),'maximum_over_date_cells':max(v),'positive_cells':sum(x>0 for x in v),'negative_cells':sum(x<0 for x in v),'available_date_cells':len(v),'pooled_by_cell':{k:z['correlations'][pair]['pearson_descriptive'] for k,z in allcells.items()}}
 e={'schema':'gc_pressure_progress_analysis_v1','status':'EXPLORATORY_DESCRIPTIVE_SUPPORT_NOT_EDGE','receipt_sha256':hashlib.sha256((RAW/'pressure-progress-receipt.json').read_bytes()).hexdigest(),'observed_anchors':r['total_training']['observed_anchors'],'eligible_anchors':r['total_training']['eligible_anchors'],'unknown_anchors':r['total_training']['state_counts']['UNKNOWN'],'nonoverlap_windows':r['total_training']['nonoverlap_windows'],'states_unchanged':r['total_training']['state_counts'],'support_readiness':r['support_readiness'],'support_descriptors':metrics,'sessions':perdate,'correlation_descriptors':correlation_ranges,'runner_seconds':r['wall_seconds'],'boot_seconds':load(RAW/'boot-receipt.json')['wall_seconds'],'comparison_plan':[{'grain':'all six original dates, past-window trajectory; disjoint current-progress buckets','population':'greedy 40sec-nonoverlap eligible pairs with prior directed progress>=4 ticks','unit':'count of window pairs, not independent episodes','finding':'Different past-to-present trajectories have observed support; no future response measured','derivation':'sum matrix row4 across phase/direction; group current columns(0,1),(2),(3,4); crosscheck per date','disposition':'chart','reason':'Show the support of three mutually exclusive trajectories on the same conditioned population'},{'grain':'date and phase/direction','population':'all eligible anchors plus declared nonoverlap sample','unit':'counts/correlation descriptors separately','finding':'Coverage and descriptive correlations must not be mistaken for future predictive effects','derivation':'read exact per-date aggregates; no pooled mean of quantiles','disposition':'table','reason':'Retain all dates and direction/phase exceptions in CSV and closeout; no inference'}], 'profiler_resolution':'Nested receipt cannot be profiled directly; normalized CSVs profiled. Repeated dates/cells/buckets are expected components of unique composite keys. POOLED is not summed with dates. Constant/negative correlation is valid, missing values remain undefined.','outcomes_computed':False,'holdout_opened':False,'canonical_brain_written':False,'independent_episodes_claimed':False}
 neg={}
 for q in csv.DictReader((OUT/'correlations.csv').open()):
  if q['trade_date']!='POOLED_TRAINING' and float(q['pearson_descriptive'])<0:neg.setdefault(q['metric_pair'],[]).append({'trade_date':q['trade_date'],'cell':q['phase_direction'],'pearson_descriptive':float(q['pearson_descriptive'])})
 e['negative_date_cell_correlations']=neg
 e['profiler_resolution']+=' BOTH is constant zero, as prior census; undefined_if_constant is consistently False for this receipt, not imputed. Pearson values are not record keys.'
 (OUT/'analysis.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n');(OPS/'GC_PRESSURE_PROGRESS_ANALYSIS.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n')
 spec={'version':1,'form':'categorical-bars','title':'Hay soporte para tres trayectorias; todavía no se midió su efecto','subtitle':f'GC · seis sesiones de training · {r["total_training"]["nonoverlap_windows"]:,} pares elegibles sin solapamiento; no episodios independientes','aside':f'Condición: avance previo ≥4 ticks; {sum(values):,} pares. Sólo trayectoria ya observada; sin outcomes ni edge confirmado.','orientation':'horizontal','mode':'grouped','labels':categories,'series':[{'label':'Pares de ventanas sin solapamiento','data':values,'valueKind':'count','role':'subject'}],'axis':{'zero':True}}
 (OUT/'chart-spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:e[k] for k in ['eligible_anchors','nonoverlap_windows','support_descriptors','runner_seconds','boot_seconds','correlation_descriptors']},indent=2));print('Per-date',perdate)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','analyze']);a.add_argument('--raw',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--ops',type=Path,required=True);x=a.parse_args();RAW=x.raw;OUT=x.out;OPS=x.ops;OUT.mkdir(parents=True,exist_ok=True);OPS.mkdir(parents=True,exist_ok=True);r=load(RAW/'pressure-progress-receipt.json');(prepare if x.phase=='prepare' else analyze)(r)
