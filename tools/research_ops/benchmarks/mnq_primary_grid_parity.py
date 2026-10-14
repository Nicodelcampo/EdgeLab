"""Kaggle-only replay of ALL previously emitted primary-effects rows.
No detectors, new signals, winning-cell selection, hypothesis or adoption.
Only hash/census/technical stage telemetry exits Kaggle, never effect values.
"""
import hashlib,itertools,json,math,os,resource,time
from pathlib import Path
import numpy as np
import pandas as pd
from tools.research_ops.session_resampling import multiplicities,resampled_counts
from tools.research_ops.benchmarks.mnq_resampling_replay import PLAN as PRIOR
PLAN={
 'schema':'mnq_full_primary_grid_parity_plan_v1','contract':'MNQ_09-26',
 'frozen_commit':PRIOR['frozen_commit'],'original_kernel':138263097,'original_version':1,'original_execution':357535155,
 'inputs':{'manifest':{'bytes':4261,'sha256':PRIOR['manifest_sha256']},'events':{'bytes':19848426,'sha256':PRIOR['csv_sha256']},'effects':{'bytes':1496171,'sha256':'ba401ba7c5e836a9be2fc9d8e54c242b73cd0d11015a5664c47d116e1e26b00e'}},
 'origins':['real','translated_geometry250'],'landmarks':[0,250,500,1000,2000,3000,5000],
 'dedups':['all','dedup75','dedup50'],'endpoints':[0,1,2],
 'visit_definitions':['visits1','visits5','visits_clock10s'],
 'visits':['all','0','1','2-4','5+'],'speeds':['all','return_faster','return_slower'],'gaps':['observed','gap_free'],
 'rows':11340,'sessions':46,'draws':10000,'seed':17331,'deadline_seconds':900,'memory_bytes':4*1024**3,
 'scope':'ALL_STORED_PRIMARY_EFFECTS_FROM_EXISTING_THINNED_EVENTS',
 'no_full_pipeline_claim':True,'holdout_opened':False,'pnl_computed':False,'scientific_trial':False,'adoption_authorized':False}
KEYS=['contract','dedup','origin','landmark','endpoint','visit_definition','visits_group','speed_group','gap_policy']
INTS=['signals','resolved','target_first','opposite_first','unresolved','active_dates','observed_dates']
FLOATS=['target_percent','day_lower','day_upper']
def sha(b):return hashlib.sha256(b).hexdigest()
def plan_hash():return sha(json.dumps(PLAN,sort_keys=True,separators=(',',':')).encode())
def load_pinned(path,key):
 spec=PLAN['inputs'][key];p=Path(path)
 if p.stat().st_size!=spec['bytes']:raise ValueError('input size mismatch')
 b=p.read_bytes()
 if sha(b)!=spec['sha256']:raise ValueError('input hash mismatch')
 return b

def form_cells(t,m):
 dates=m['event_dates'];sessions=pd.Categorical(t.session,categories=dates).codes
 if (sessions<0).any():raise ValueError('unapproved event session')
 statuses=t.status.to_numpy();target=statuses=='TARGET_FIRST';opposite=statuses=='OPPOSITE_FIRST'
 for dedup in PLAN['dedups']:
  mask=np.ones(len(t),bool) if dedup=='all' else t[dedup].eq(1).to_numpy()
  for origin,age,ep,definition in itertools.product(PLAN['origins'],PLAN['landmarks'],PLAN['endpoints'],PLAN['visit_definitions']):
   # Identical frozen cell definitions; only integer count formation is grouped.
   base=mask&t.origin.eq(origin).to_numpy()&t.landmark.eq(age).to_numpy()&t.endpoint.eq(ep).to_numpy()
   v=pd.cut(t[definition],[-1,0,1,4,np.inf],labels=['0','1','2-4','5+']).astype(str).to_numpy()
   speed=np.where(t.speed_ratio.isna(),'unknown',np.where(t.speed_ratio>=1,'return_faster','return_slower'))
   gap=t.prior_gap_count.eq(0).to_numpy()
   for visit,sp,gp in itertools.product(PLAN['visits'],PLAN['speeds'],PLAN['gaps']):
    take=base.copy()
    if visit!='all':take&=v==visit
    if sp!='all':take&=speed==sp
    if gp=='gap_free':take&=gap
    d=np.column_stack([np.bincount(sessions[take&target],minlength=len(dates)),np.bincount(sessions[take&opposite],minlength=len(dates)),np.bincount(sessions[take],minlength=len(dates))]).astype(np.int64)
    yield (PLAN['contract'],dedup,origin,age,ep,definition,visit,sp,gp),d

def metrics(d,weights):
 w=int(d[:,0].sum());l=int(d[:,1].sum());n=w+l;sig=int(d[:,2].sum())
 a=resampled_counts(weights,d);bw=a[:,0];bn=a[:,:2].sum(axis=1);ok=bn>0
 ci=np.quantile(100*bw[ok]/bn[ok],[.025,.975]) if ok.any() else np.array([np.nan,np.nan])
 return {'signals':sig,'resolved':n,'target_first':w,'opposite_first':l,'unresolved':sig-n,'active_dates':int(np.count_nonzero(d[:,2])),'observed_dates':len(d),'target_percent':100*w/n if n else math.nan,'day_lower':float(ci[0]),'day_upper':float(ci[1])}

def normalized_key(row):
 return tuple(int(row[k]) if k in ['landmark','endpoint'] else row[k] for k in KEYS)
def same_float(value,text):
 other=float(text) if text.strip() else math.nan
 return (math.isnan(value) and math.isnan(other)) or (not math.isnan(value) and np.float64(value).tobytes()==np.float64(other).tobytes())
def check_row(key,value,ref):
 if key!=normalized_key(ref):raise ValueError('cell key/order mismatch')
 if any(int(ref[k])!=value[k] for k in INTS):raise ValueError('integer field parity failure')
 if any(not same_float(value[k],ref[k]) for k in FLOATS):raise ValueError('exact float round-trip parity failure')

def run(events,manifest,effects,output):
 if os.environ.get('KAGGLE_KERNEL_RUN_TYPE') is None:raise ValueError('private event replay requires Kaggle')
 import csv,io,datetime
 resource.setrlimit(resource.RLIMIT_AS,(PLAN['memory_bytes'],PLAN['memory_bytes']))
 started=time.monotonic();stages={};t0=time.perf_counter()
 mb=load_pinned(manifest,'manifest');eb=load_pinned(events,'events');rb=load_pinned(effects,'effects')
 m=json.loads(mb);dates=m['event_dates']
 if m['origins']!=PLAN['origins'] or m['landmarks']!=PLAN['landmarks'] or m.get('feature_schema_version')!=2:raise ValueError('manifest scope mismatch')
 if len(dates)!=46 or len(set(dates))!=46 or any(datetime.date.fromisoformat(d)>=datetime.date(2026,10,1) for d in dates):raise ValueError('preholdout census')
 t=pd.read_csv(io.BytesIO(eb));del eb
 if not (t.family.eq(PRIOR['family'])&t.D.eq(40)&t.q.eq(.5)).all():raise ValueError('primary geometry mismatch')
 refs=list(csv.DictReader(io.StringIO(rb.decode())));del rb
 if len(refs)!=11340 or len({normalized_key(r) for r in refs})!=11340:raise ValueError('complete unique reference grid required')
 stages['input_load_and_identity']=time.perf_counter()-t0;t0=time.perf_counter()
 ix=np.random.default_rng(17331).integers(0,46,size=(10000,46));weights=multiplicities(ix,46)
 stages['frozen_draws_and_weights']=time.perf_counter()-t0
 count_digest=hashlib.sha256();result_digest=hashlib.sha256();rows=empty=0;formation=analysis=compare=0.;tick=time.perf_counter()
 for key,d in form_cells(t,m):
  formation+=time.perf_counter()-tick;t0=time.perf_counter();v=metrics(d,weights);analysis+=time.perf_counter()-t0;t0=time.perf_counter()
  check_row(key,v,refs[rows]);rows+=1;empty+=int(v['signals']==0)
  count_digest.update(d.tobytes());result_digest.update(json.dumps({'key':key,'value':{k:(None if isinstance(a,float) and math.isnan(a) else a) for k,a in v.items()}},sort_keys=True,separators=(',',':'),allow_nan=False).encode());compare+=time.perf_counter()-t0
  if time.monotonic()-started>900:raise TimeoutError('grid deadline')
  tick=time.perf_counter()
 if rows!=11340:raise ValueError('incomplete grid')
 stages.update(count_formation=formation,resampling_and_metrics=analysis,reference_compare_and_hash=compare)
 result={'schema':'mnq_full_primary_grid_parity_v1','plan':PLAN,'plan_sha256':plan_hash(),'rows_checked':rows,'empty_rows':empty,'sessions':46,'private_input_rows':len(t),'integer_fields_checked':INTS,'float_fields_checked_exact_roundtrip':FLOATS,'reference_sha256':PLAN['inputs']['effects']['sha256'],'counts_sha256':count_digest.hexdigest(),'results_sha256':result_digest.hexdigest(),'draws_sha256':sha(ix.tobytes()),'stage_seconds':stages,'wall_seconds':time.monotonic()-started,'ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'SELF_HIGH_WATER_TECHNICAL_REPLAY_ONLY_NOT_ORIGINAL_JOB','python':__import__('sys').version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'exact_parity':True,'full_pipeline_parity':False,'matched_contrast_parity':False,'longevity_detector_profiled':False,'private_rows_exported':False,'validated_edge':False,'adoption_authorized':False}
 Path(output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
