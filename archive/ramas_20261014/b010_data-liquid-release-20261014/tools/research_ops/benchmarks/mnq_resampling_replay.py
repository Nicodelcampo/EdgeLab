"""Bounded technical replay, not a new trial or adopted scientific implementation.
Private event CSV/counts remain in Kaggle/temp storage. Output contains only
identities, hashes, timings and census, never estimates or private rows.
"""
import argparse, hashlib, itertools, json, os, resource, subprocess, sys, tempfile, time
from pathlib import Path
import numpy as np
from tools.research_ops.session_resampling import multiplicities, resampled_counts
PLAN = {
 'schema':'mnq_resampling_technical_replay_plan_v1',
 'contract':'MNQ_09-26','frozen_commit':'9125197dc6098100459f36a3d90a5c7b7aa4f9c0',
 'original_kernel':138263097,'original_version':1,'original_execution':357535155,
 'manifest_sha256':'4ac38a080ed98a60769f3f1bf29a4e8ed087c9202a3cceb31d8920c541549e2b',
 'manifest_bytes':4261,'csv_sha256':'9683c791331b57be8243f89c1092958aa8e1da5b4f65a70a16e020a5a754b31b',
 'csv_bytes':19848426,'sessions':46,'seed':17331,'draws':10000,
 'family':'P80_W5_R18_2000_20','D':40,'q':0.5,'dedup':'dedup75','origin':'real',
 'landmarks':[2000,3000],'endpoint':0,'visit_definition':'visits1',
 'visits':['all','0','1','2-4','5+'],'speed':['all','return_faster','return_slower'],
 'gaps':['observed','gap_free'],'cells':60,'pairs':3,'worker_timeout_seconds':120,
 'total_deadline_seconds':900,'memory_bytes':4*1024**3,
 'scope':'PRIMARY_ANALYSIS_RESAMPLING_SUBSTEP_ONLY','holdout_opened':False,
 'scientific_trial':False,'adoption_authorized':False}

def sha(b):return hashlib.sha256(b).hexdigest()
def plan_hash():return sha(json.dumps(PLAN,sort_keys=True,separators=(',',':')).encode())
def limits():
 resource.setrlimit(resource.RLIMIT_AS,(PLAN['memory_bytes'],PLAN['memory_bytes']))
 resource.setrlimit(resource.RLIMIT_CPU,(120,120))

def prepare(csv_path, manifest_path):
 import pandas as pd
 for p,key in [(manifest_path,'manifest'),(csv_path,'csv')]:
  b=Path(p).read_bytes()
  if len(b)!=PLAN[key+'_bytes'] or sha(b)!=PLAN[key+'_sha256']:raise ValueError('input identity mismatch')
  del b
 m=json.loads(Path(manifest_path).read_text());dates=m['event_dates']
 from datetime import date
 if len(dates)!=PLAN['sessions'] or len(set(dates))!=len(dates) or any(date.fromisoformat(d)>=date(2026,10,1) for d in dates):raise ValueError('preholdout session census')
 if m.get('feature_schema_version')!=2:raise ValueError('feature schema mismatch')
 cols=['family','D','q','dedup75','origin','landmark','endpoint','visits1','speed_ratio','prior_gap_count','session','status']
 t=pd.read_csv(csv_path,usecols=cols)
 if not t.family.eq(PLAN['family']).all() or not t.D.eq(40).all() or not t.q.eq(.5).all() or not t.session.isin(dates).all():raise ValueError('frozen primary geometry/session mismatch')
 b=t[t.dedup75.eq(1)&t.origin.eq('real')&t.endpoint.eq(0)]
 counts=[]
 # Matches frozen analyze.py cell formation, no winner-dependent selection.
 for age in PLAN['landmarks']:
  g=b[b.landmark.eq(age)].copy();g['visits_group']=pd.cut(g.visits1,[-1,0,1,4,np.inf],labels=['0','1','2-4','5+']).astype(str)
  g['speed_group']=np.where(g.speed_ratio.isna(),'unknown',np.where(g.speed_ratio>=1,'return_faster','return_slower'))
  for visits,speed,gap in itertools.product(PLAN['visits'],PLAN['speed'],PLAN['gaps']):
   h=g
   if visits!='all':h=h[h.visits_group.eq(visits)]
   if speed!='all':h=h[h.speed_group.eq(speed)]
   if gap=='gap_free':h=h[h.prior_gap_count.eq(0)]
   d=np.zeros((len(dates),3),np.int64)
   for j,day in enumerate(dates):
    hh=h[h.session.eq(day)];d[j]=[hh.status.eq('TARGET_FIRST').sum(),hh.status.eq('OPPOSITE_FIRST').sum(),len(hh)]
   counts.append(d)
 return np.array(counts),len(t)

def compute(counts,ix,method):
 dig=hashlib.sha256();weights=multiplicities(ix,ix.shape[1]) if method=='candidate' else None
 for d in counts:
  if method=='baseline':
   # Literal expressions from the frozen analyzer, including summation order.
   bw=d[ix,0].sum(axis=1);bn=d[ix,:2].sum(axis=(1,2))
  elif method=='candidate':
   a=resampled_counts(weights,d);bw=a[:,0];bn=a[:,:2].sum(axis=1)
  else:raise ValueError('unknown method')
  ok=bn>0;ci=np.quantile(100*bw[ok]/bn[ok],[.025,.975]) if ok.any() else np.array([np.nan,np.nan])
  # Hash exact integer draws and float bytes (including missing bands).
  for x in (bw,bn,ok,ci):dig.update(np.ascontiguousarray(x).tobytes())
 return dig.hexdigest()

def worker(path,method):
 limits();z=np.load(path,allow_pickle=False);counts=z['counts'];ix=z['ix'];out=[]
 for label in ['cold','warm']:
  t=time.perf_counter();digest=compute(counts,ix,method);seconds=time.perf_counter()-t
  out.append({'label':label,'seconds':seconds,'digest':digest})
 return {'method':method,'runs':out,'ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'rss_scope':'ISOLATED_SINGLE_PROCESS_INCLUDES_IMPORTS_AND_INPUT_LOAD'}

def run(csv_path,manifest_path,output):
 if os.environ.get('KAGGLE_KERNEL_RUN_TYPE') is None:raise ValueError('real private replay requires Kaggle')
 started=time.monotonic();limits();t=time.perf_counter();counts,rows=prepare(csv_path,manifest_path);prep=time.perf_counter()-t
 ix=np.random.default_rng(17331).integers(0,PLAN['sessions'],size=(10000,PLAN['sessions']))
 pairs=[]
 with tempfile.TemporaryDirectory(prefix='mnq-replay-',dir='/tmp') as td:
  p=Path(td)/'counts.npz';np.savez(p,counts=counts,ix=ix)
  for pair in range(3):
   results={}
   order=['baseline','candidate'] if pair!=1 else ['candidate','baseline']
   for method in order:
    remaining=900-(time.monotonic()-started)
    if remaining<=0:raise TimeoutError('total deadline')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    cp=subprocess.run([sys.executable,'-m','tools.research_ops.benchmarks.mnq_resampling_replay','--worker',str(p),'--method',method],capture_output=True,text=True,timeout=min(120,remaining),check=True,env=env)
    results[method]=json.loads(cp.stdout)
   digests={r['digest'] for v in results.values() for r in v['runs']}
   if len(digests)!=1:raise ValueError('EXACT_PARITY_FAILED')
   pairs.append({'pair':pair+1,'order':order,**results})
 if len({r['digest'] for p in pairs for method in ['baseline','candidate'] for r in p[method]['runs']})!=1:raise ValueError('cross-pair mismatch')
 result={'schema':'mnq_resampling_technical_replay_v1','plan':PLAN,'plan_sha256':plan_hash(),
  'counts_sha256':sha(counts.tobytes()),'draws_sha256':sha(ix.tobytes()),'private_input_rows':rows,
  'cells':len(counts),'empty_cells':int(np.sum(counts[:,:,2].sum(axis=1)==0)),
  'prepare_seconds':prep,'total_seconds':time.monotonic()-started,'pairs':pairs,
  'python':sys.version.split()[0],'numpy':np.__version__,'exact_parity':True,
  'full_pipeline_parity':False,'private_rows_exported':False,'old_job_rss_measured':False,
  'validated_edge':False,'adoption_authorized':False}
 Path(output).write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--worker');ap.add_argument('--method',choices=['baseline','candidate']);ap.add_argument('--csv');ap.add_argument('--manifest');ap.add_argument('--output');a=ap.parse_args()
 if a.worker:print(json.dumps(worker(a.worker,a.method),allow_nan=False))
 else:run(a.csv,a.manifest,a.output)
if __name__=='__main__':main()
