"""Frozen multiasset exploratory comparisons; each asset isolated, no pooled edge.

Source stays in Kaggle. Asset-local no-outcome calibration precedes supervised
train and evaluation. Shared native footprint memo does not share detector state.
"""
import argparse,json,os,time,resource,hashlib
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import numpy as np
from .build_target_free_pilot import digest
from .cross_family_pilot import ROSTER,fit_models,score,COMPARISONS
from .cross_family_design import MODELS,COUNTS
from .cross_family_streaming import StreamingScene
from .cross_family_collector import CrossFamilyCollector
from .kaggle_session_reader import iter_sessions
from .phenomena_model_pilot import session_data
from .phenomena_models import phase_key
from .phenomena_states import Calibration,components,eligible
from .phenomena import ClockMeasurements
from .source_footer import HOLDOUT_OPEN_NS
PLAN='docs/research/ops/MULTIASSET_CROSSFAMILY_PLAN.json'
PLAN_SHA='1fc00c5ad2e4a5a2d01641f60726d1c56c41c512ef5fdbbca824e6bca8826dd2'

GAP10_PLAN='docs/research/ops/MULTIASSET_CROSSFAMILY_GAP10_PLAN.json'
GAP10_SHA='e18747ab0efc8c3a4ab9c8d620621f6617590c63cc6d7c42e5f1355b54e3d772'

FOCUS_PLAN='docs/research/ops/GC_FOCUSED_RETURN_PLAN.json'
FOCUS_SHA='49bb3dd734685d41fddfa619ae5393a9f2be9d4f2b91e9e16a229218cb27cbd4'

class AssetCalibration(Calibration):
 def __init__(self,date):super().__init__();self.date=date
 def add(self,row):
  if row['trade_date']!=self.date:raise ValueError('asset calibration before supervised dates only')
  key=phase_key(row,research_dates=(self.date,));p=row['windows']['20']
  if eligible(p):return
  if self.n>=250000:raise ValueError('asset calibration bounded anchors')
  self.n+=1;a=self.cells.setdefault(key,{k:[] for k in ('pressure','prior_pressure','abs_progress','range','path')})
  for k,v in components(p).items():a[k].append(v)
 def freeze(self):
  r=super().freeze();r['training_trade_date']=self.date;r['sha256']=digest({k:v for k,v in r.items() if k!='sha256'});return r

def validate_plan(p,asset):
 if digest(p) not in (PLAN_SHA,GAP10_SHA,FOCUS_SHA) or asset not in p['assets']:raise ValueError('exact frozen multiasset plan and member only')
 if p['holdout'] is not False or p['raw_export'] is not False or p['confirmation'] is not False:raise ValueError('exploratory preholdout only')
 ds=[p['calibration_date']]+p['training_sessions']+p['evaluation_sessions']
 if ds!=sorted(set(ds)) or any(d>='2026-10-01' for d in ds):raise ValueError('causal fixed asset calendar')
 a=p['assets'][asset]
 if type(a['tick_size']) not in (int,float) or a['tick_size']<=0:raise ValueError('declared asset tick size')
 roster=json.loads(Path(ROSTER).read_bytes())
 if roster['roster_sha256']!=p['roster_sha256']:raise ValueError('exact nine configs eighteen pairs')
 if digest(p)==FOCUS_SHA:
  pairs=[x for x in roster['pairs'] if x['pair_sha256']==p['focus_pair_sha256']]
  if len(pairs)!=1:raise ValueError('exact focused pair')
  keys={pairs[0]['left_config_sha256'],pairs[0]['right_config_sha256']}
  roster={**roster,'configs':[c for c in roster['configs'] if c['config_sha256'] in keys],'pairs':pairs}
 return a,roster

def verify_transport(path,pin):
 """Identity/hash/footer binding only, reuses publisher measurements, no raw QA."""
 import pyarrow.parquet as pq
 path=Path(path)
 if path.name!=pin['file'] or path.stat().st_size!=pin['bytes']:raise ValueError('asset pinned transport size/name')
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 if h.hexdigest()!=pin['sha256']:raise ValueError('asset pinned transport hash')
 pf=pq.ParquetFile(path)
 if pf.metadata.num_rows!=pin['rows']:raise ValueError('asset pinned footer rows')
 return dict(physical_bytes_sha256=h.hexdigest(),rows=pf.metadata.num_rows,quality_reaudited=False,payload_deserialized=False)

class ArrivalCuts:
 """Fixed pooled cuts; support by sessions, never IID or winner selection."""
 def __init__(self,pair_count=18):self.groups=[{} for _ in range(pair_count)]
 def add(self,p,z,loss):
  a=z[:,25:32];b=z[:,32:39];inside=z[:,11]==1;masks={}
  for label,v in (('AVZ',a),('BIGTRAP',b)):
   for name,k in (('POST_BIRTH_OBSERVED_TOUCH',2),('FIRST_OBSERVED_TOUCH_RECENT20S',3),('OBSERVED_LEAVE_RETURN',4),('OBSERVED_GAPTHROUGH_NO_INSIDE_PRINT',5)):masks[label+':'+name]=v[:,k]>0
   masks[label+':FROM_ABOVE']=(v[:,1]==1)&(v[:,6]<0);masks[label+':FROM_BELOW']=(v[:,1]==1)&(v[:,6]>0);masks[label+':PRIOR_ORIGIN_INSIDE']=(v[:,1]==1)&(v[:,6]==0)
  masks['INSIDE_BOTH_AND_BOTH_RETURN']=inside&(a[:,4]>0)&(b[:,4]>0)
  masks['INSIDE_BOTH_AND_BOTH_OLD']=inside&(a[:,1]>0)&(b[:,1]>0)
  masks['INSIDE_BOTH_AND_BOTH_FIRST_OBSERVED_TOUCH_RECENT']=inside&(a[:,3]>0)&(b[:,3]>0)
  for name,m in masks.items():
   n=int(m.sum())
   if not n:continue
   sums={k:float(loss[k][m].sum()) for k in ('CONTINUOUS','ARRIVAL','ARRIVAL_CC')};g=self.groups[p].setdefault(name,dict(anchors=0,support_sessions=0,arrival_improved_sessions=0,loss_sums={k:0. for k in sums}));g['anchors']+=n;g['support_sessions']+=1;g['arrival_improved_sessions']+=int(sums['ARRIVAL']<sums['ARRIVAL_CC'])
   for k,v in sums.items():g['loss_sums'][k]+=v
 def finish(self,plan):
  out=[]
  for groups in self.groups:
   result={}
   for name,g in groups.items():
    result[name]={**g,'mean_brier_pooled':{k:v/g['anchors'] for k,v in g['loss_sums'].items()},'support_screen_passed_not_edge':g['anchors']>=plan['scenario_min_pooled_anchors'] and g['support_sessions']>=plan['scenario_min_sessions']}
   out.append(result)
  return out

def run(source,plan,asset,private_root,progress):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('multiasset market source requires Kaggle')
 root=Path(private_root).resolve()
 if root==Path('/kaggle/working') or Path('/kaggle/working') in root.parents:raise ValueError('private market state outside exports')
 a,roster=validate_plan(plan,asset)
 import pyarrow.parquet as parquet
 if parquet.ParquetFile(source).metadata.num_rows!=a['pin']['rows']:raise ValueError('asset pinned footer rows')
 p={**plan,'tick_size':a['tick_size'],'research_dates':plan['training_sessions']+plan['evaluation_sessions']};start=time.monotonic();scene=StreamingScene(roster,p);training=[];tr=[];ev=[];seen=set();unavailable=[];cal=None;models=None;fitsec=0.;scan=hits=pq=pl=0;warmup=0;arrival_cuts=ArrivalCuts(len(roster['pairs']));focused=None
 if digest(plan)==FOCUS_SHA:
  from .gc_focused_summary import FocusedSummary
  focused=FocusedSummary(p)
 for st in iter_sessions(source,start_ns=p['warmup_start_ns'],end_ns=p['read_end_ns'],contract=a['contract'],instrument=a['instrument'],tick_size=a['tick_size'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_total_ticks']):
  date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat();selected=date in p['research_dates'];progress.update(stage='NATIVE_PREFIX',trade_date=date if selected or date==p['calibration_date'] else None)
  events,diag=scene.session(st,date,retain=selected)
  if date==p['calibration_date']:
   if cal is not None:raise ValueError('one asset calibration session')
   c=AssetCalibration(date);m=ClockMeasurements(max_ticks=p['max_session_ticks'],max_anchors=p['max_anchors'],wall_seconds=p['wall_seconds'],max_gap_ns=p['max_gap_ns'])
   for row in m.measure(st.ticks.ts_ns,st.ticks.sequence,st.ticks.price_ticks,st.ticks.volume,st.ticks.bid_ticks,st.ticks.ask_ticks,trade_date=date):c.add(row)
   cal=c.freeze();progress.update(stage='CALIBRATION_FROZEN_NO_OUTCOMES',calibration_anchors=c.n)
  if not selected:warmup+=1;continue
  if cal is None:raise ValueError('asset calibration missing; no MNQ threshold substitution')
  if date in seen:raise ValueError('duplicate asset selected session')
  seen.add(date);collector=CrossFamilyCollector(st,date,events,roster,p);progress.update(stage='MEASURE_CONTEXT_LABEL',trade_date=date)
  try:data=session_data(st,date,p,cal,start,feature_callback=collector)
  except ValueError as e:
   if str(e)!='session common usable support below 100; no substitution' or date in p['training_sessions']:raise
   events.finish();unavailable.append({'trade_date':date,'status':'INSUFFICIENT_COMMON_SUPPORT_NO_REPLACEMENT','replacement_selected':False});continue
  events.finish();z,meta=collector.finish(len(data[3]));data[-1]['crossfamily_context']=meta;data[-1]['native_scene']=diag;scan+=data[-1]['response_scanned_elements'];hits+=meta['profile_query_hits'];pq+=meta['print_queries'];pl+=meta['print_level_queries']
  if any(v>p[k] for v,k in ((scan,'max_scan_elements_total'),(hits,'max_total_context_query_hits'),(pq,'max_total_print_queries'),(pl,'max_total_print_level_queries'))):raise ValueError('whole asset measurement budget')
  if date in p['training_sessions']:
   training.append((data[0],z.copy(),data[3]));tr.append(data[-1])
   if date==p['training_sessions'][-1]:
    if [s['trade_date'] for s in tr]!=p['training_sessions']:raise ValueError('complete fixed six-session training')
    progress.update(stage='FIT_ASSET_ONLY');f=time.monotonic();continuous,pairs,prior=fit_models(training);models=continuous,pairs;fitsec=time.monotonic()-f;training.clear()
  else:
   if models is None:raise ValueError('asset fit before scoring')
   progress.update(stage='SCORE_ASSET')
   if focused is not None:focused.begin(date,collector.anchor_ns[:collector.n])
   def collect(j,features,loss):
    arrival_cuts.add(j,features,loss)
    if focused is not None:focused.add(j,features,loss)
   ev.append(score(data,z,models,prior,roster,extra_cuts=collect))
  progress.update(completed_selected_sessions=len(tr)+len(ev),last_completed_trade_date=date);del data,z,collector,events,st
  if time.monotonic()-start>p['wall_seconds']:raise TimeoutError('whole asset wall')
 eof=scene.finish()
 if [s['trade_date'] for s in tr]!=p['training_sessions'] or len(ev)<p['minimum_available_evaluation_sessions']:raise ValueError('insufficient fixed asset training or evaluation; no replacements')
 unavailable +=[{'trade_date':d,'status':'SOURCE_EMPTY_NO_REPLACEMENT','replacement_selected':False} for d in p['evaluation_sessions'] if d not in seen];unavailable.sort(key=lambda x:x['trade_date'])
 result={'schema':'multiasset_crossfamily_receipt_v1','status':'DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE','asset':asset,'instrument':a['instrument'],'contract':a['contract'],'tick_size':a['tick_size'],'observation_max_gap_ns':p['max_gap_ns'],'observation_gap_relaxed_vs_original':p['max_gap_ns']!=2000000000,'plan_sha256':digest(plan),'roster_sha256':roster['roster_sha256'],'calibration':cal,'calibration_sha256':cal['sha256'],'training_sessions':tr,'evaluation_sessions':ev,'requested_evaluation_sessions':p['evaluation_sessions'],'unavailable_evaluation_sessions':unavailable,'available_evaluation_session_count':len(ev),'baseline_mean_session_brier':{n:float(np.mean([s['baseline_mean_brier'][n] for s in ev])) for n in ('PRIOR','CONTINUOUS')},'pairs':[{**identity,'mean_session_brier':{n:float(np.mean([s['pairs'][j]['scores']['mean_brier'][n] for s in ev])) for n in ('PRIOR','CONTINUOUS')+MODELS},'paired_delta_equal_session_mean':{x+'_MINUS_'+y:float(np.mean([s['pairs'][j]['paired_deltas'][x+'_MINUS_'+y] for s in ev])) for x,y in COMPARISONS}} for j,identity in enumerate(roster['pairs'])],'arrival_context_summaries':arrival_cuts.finish(p),'model_feature_counts':COUNTS,'models_including_shared_baselines':2+len(roster['pairs'])*len(MODELS),'primary_pairs':len(roster['pairs']),'native_configs':len(roster['configs']),'warmup_sessions':warmup,'native_eof_diagnostics':eof,'native_stage_seconds':dict(scene.times),'fit_seconds':fitsec,'total_ticks':scene.ticks,'response_scanned_elements':scan,'context_query_hits':hits,'print_queries':pq,'print_level_queries':pl,'shared_footprint_cache':scene.footprint_cache.receipt(),'bt2a_bucket_preprocessing_shared':any(c['indicator']=='bigtrap2absorption' for c in roster['configs']),'detector_history_or_active_state_shared':False,'wall_seconds':time.monotonic()-start,'measured_runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'near100_percent_NT8_parity_measured':False,'approximate_parity_exploration_accepted':True,'cash_phase_scope':'COMMON_US_CASH_CLOCK_NOT_ASSET_SPECIFIC_RTH_CERTIFICATE','native_AVZ_liveness_measured':False,'physical_first_touch_measured':False,'zone_specific_attribution':False,'overlapping_anchors_independent':False,'automatic_model_selection':False,'raw_exported':False,'canonical_brain_written':False,'confirmation':False,'holdout_opened':False,'pnl':False,'edge_claim':False,'mirror_null_scope':p['mirror_null_scope']}
 if focused is not None:result['focused_return']=focused.finish()
 if len(json.dumps(result,separators=(',',':'),allow_nan=False).encode())>p['max_aggregate_bytes']:raise ValueError('asset bounded aggregate bytes')
 return result

def main():
 p=argparse.ArgumentParser();[p.add_argument('--'+k,required=True) for k in ('source','plan','asset','private-root','receipt')];args=p.parse_args();plan=json.loads(Path(args.plan).read_bytes());progress={}
 try:r=run(args.source,plan,args.asset,args.private_root,progress);Path(args.receipt).write_text(json.dumps(r,separators=(',',':'),allow_nan=False)+'\n')
 except Exception as e:
  from .cross_family_diagnostics import safe_failure
  safe=safe_failure(e,{})
  failure={'schema':'multiasset_failure_v1','status':'FAILED_NO_SCIENTIFIC_CLAIM','asset':args.asset,'stage':progress.get('stage'),'trade_date':progress.get('trade_date'),'exception_type':safe['exception_type'],'reason_code':safe['reason_code'],'raw_exported':False,'partial_success':False}
  Path(args.receipt).with_name('runner-failure-receipt.json').write_text(json.dumps(failure)+'\n');raise
if __name__=='__main__':main()
