import sys,time,json,hashlib,resource,subprocess,pathlib,platform
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]))
from tools.research_ops.session_resampling import multiplicities,resampled_counts

def worker(mode):
 rng=np.random.default_rng(17331);ix=rng.integers(0,57,(10000,57));ds=rng.integers(0,100,(48,57,3),dtype=np.int64)
 # Check workload before measurement; identical synthetic arrays for each subprocess.
 def run():
  w=multiplicities(ix,57) if mode=='candidate' else None
  out=[]
  for d in ds:
   if mode=='candidate':a=resampled_counts(w,d);wins=a[:,0];total=a[:,:2].sum(axis=1)
   else:wins=d[ix,0].sum(axis=1);total=d[ix,:2].sum(axis=(1,2))
   ok=total>0;out.append(np.quantile(100*wins[ok]/total[ok],[.025,.975]))
  return np.asarray(out)
 times=[];results=[]
 for phase in ['cold','warm']:
  t=time.perf_counter();a=run();times.append(time.perf_counter()-t);results.append(hashlib.sha256(a.tobytes()).hexdigest())
 print(json.dumps({'mode':mode,'seconds':times,'output_sha256':results,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}))
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--worker',choices=['baseline','candidate']);parser.add_argument('--output',default='/tmp/edgelab-session-resampling-benchmark.json');args=parser.parse_args()
if args.worker:worker(args.worker);sys.exit(0)
rows=[]
for pair in range(3):
 order=['baseline','candidate'] if pair%2==0 else ['candidate','baseline']
 entries={m:json.loads(subprocess.check_output([sys.executable,__file__,"--worker",m],text=True)) for m in order}
 assert entries['baseline']['output_sha256']==entries['candidate']['output_sha256'];rows.append({'pair':pair+1,**entries})
ratios={phase:[r['baseline']['seconds'][i]/r['candidate']['seconds'][i] for r in rows] for i,phase in enumerate(['cold','warm'])}
e={'schema':'exact_session_resampling_synthetic_microbenchmark_v1','environment':{'python':platform.python_version(),'numpy':np.__version__,'host':'local agent sandbox, not Kaggle'},'workload':{'sessions':57,'whole_session_draws':10000,'cells':48,'seed':17331,'synthetic':True},'measurement':'three isolated subprocess pairs, reversed order on second pair; measured helper calls exclude imports/workload generation, include candidate multiplicity construction; cold is first call, not full-job provisioning; ru_maxrss includes process imports and data','pairs':rows,'speedup_ratios':ratios,'median_speedup':{k:float(np.median(v)) for k,v in ratios.items()},'exact_synthetic_quantile_parity':True,'real_MNQ_parity_verified':False,'automatic_adoption_allowed':False,'scope':'prototype helper microbenchmark, not end-to-end campaign speedup or authorization'}
pathlib.Path(args.output).write_text(json.dumps(e,indent=2)+'\n');print(json.dumps({'median_speedup':e['median_speedup'],'synthetic_parity':True,'real_parity':False}))
