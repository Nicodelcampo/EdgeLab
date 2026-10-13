"""Same-input production-mode native profile and semantic-state parity. Kaggle only."""
import argparse,cProfile,dataclasses,hashlib,json,math,os,pstats,time,statistics
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
from collections.abc import Mapping
import numpy as np
from .bt2a_stream import BT2AStream,TickChunk
from .bt2a_footprint_cache import BucketFootprintCache
from .cross_family_pilot import ROSTER
from .build_target_free_pilot import digest
from .kaggle_session_reader import iter_sessions
PLAN='docs/research/ops/GC_BT2A_PROFILE_PLAN.json'
PLAN_SHA='269f62b9991e6c9985a23fe8b1d62a9e7cf936f5c495971868a17b1f7ca29596'

def validate(p,asset):
 if digest(p)!=PLAN_SHA or asset!='GC':raise ValueError('exact bounded GC profile plan')
 if any(p[k] is not False for k in ('labels','models','outcomes','holdout','pnl','raw_export','canonical_brain_write')):raise ValueError('technical profile only')
 return p['assets'][asset]

def normalized(x):
 if isinstance(x,np.generic):return normalized(x.item())
 if isinstance(x,np.ndarray):return ['ARRAY',x.dtype.str,list(x.shape),hashlib.sha256(x.tobytes()).hexdigest()]
 if isinstance(x,float):return x if math.isfinite(x) else ['NONFINITE',repr(x)]
 if x is None or isinstance(x,(str,int,bool)):return x
 if isinstance(x,Mapping):return ['MAP',[[normalized(k),normalized(v)] for k,v in sorted(x.items(),key=lambda q:repr(q[0]))]]
 if isinstance(x,(list,tuple)):return [normalized(v) for v in x]
 if dataclasses.is_dataclass(x):return normalized(dataclasses.asdict(x))
 if isinstance(x,SimpleNamespace):return normalized(vars(x))
 raise ValueError('unsupported native state fingerprint type')

def fingerprint(s):
 # All noncallable closure cells include abs_ring, active zones, bar sequence,
 # parameters and ticks namespace; exclude nested code, whose source is pinned.
 closure={k:c.cell_contents for k,c in zip(s.flush.__code__.co_freevars,s.flush.__closure__) if not callable(c.cell_contents)}
 state={'closure':closure,'buffer':s.buffer,'session':s.session,'last_clock':s.last_clock,'last_session':s.last_session,'next_index':s.next_index,'total_buckets':s.total_buckets,'closed':s.closed,'poisoned':s.poisoned}
 return digest(normalized(state))

def measure(tapes,configs,tick_size,schedule,*,rolling_percentile=False,collect_diagnostics=False):
 if schedule not in ('PROFILE_SEQUENTIAL','CHUNK_INTERLEAVED'):raise ValueError('closed scheduling comparison')
 cache=BucketFootprintCache();ss=[BT2AStream(params=c['params'],tick_size=tick_size,collect_diagnostics=collect_diagnostics,footprint_cache=cache,rolling_percentile=rolling_percentile) for c in configs];hs=[hashlib.sha256() for s in ss];counts=[0]*len(ss);u=[0]*len(ss);snapshots=[];offset=0;started=time.monotonic();native_seconds=0.;fingerprint_seconds=0.
 def consume(k,d):
  u[k]+=d.unavailable_events
  for r in d.records:hs[k].update(repr(r).encode()+b'\n');counts[k]+=1
 for st in tapes:
  t=st.ticks;ids=np.full(len(t),st.session_id,dtype=np.int64)
  def push(k,j,z):
   nonlocal native_seconds
   chunk=TickChunk(*(getattr(t,n)[j:z] for n in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),ids[j:z],offset+j);beg=time.monotonic();d=ss[k].push(chunk);native_seconds+=time.monotonic()-beg;consume(k,d)
  if schedule=='PROFILE_SEQUENTIAL':
   for k in range(len(ss)):
    for j in range(0,len(t),100000):push(k,j,min(j+100000,len(t)))
  else:
   for j in range(0,len(t),1000):
    for k in range(len(ss)):push(k,j,min(j+1000,len(t)))
  beg=time.monotonic()
  for s in ss:
   if s.rolling_percentile is not None:
    cells=dict(zip(s.flush.__code__.co_freevars,s.flush.__closure__))
    history=cells['abs_ring'].cell_contents
    exact=lambda vs:[float(v).hex() for v in vs]
    if exact(history)!=exact(s.rolling_percentile.fifo) or exact(sorted(history))!=exact(s.rolling_percentile.ordered):
     raise ValueError('rolling cache exact history/order binding')
  snapshots.append([fingerprint(s) for s in ss]);fingerprint_seconds+=time.monotonic()-beg;offset+=len(t)
 for k,s in enumerate(ss):
  beg=time.monotonic();d=s.finish();native_seconds+=time.monotonic()-beg;consume(k,d)
 beg=time.monotonic();final=[fingerprint(s) for s in ss];fingerprint_seconds+=time.monotonic()-beg
 return {'schedule':schedule,'wall_seconds':time.monotonic()-started,'native_push_and_finish_seconds':native_seconds,'fingerprint_seconds':fingerprint_seconds,'cache':cache.receipt(),'profiles':[{'config_sha256':c['config_sha256'],'capture_sha256':h.hexdigest(),'capture_records':n,'unavailable_events':v,'final_state_sha256':f,'state_sizes':s.state_sizes(),'native_log_sha256':s.log_hash.hexdigest()} for c,h,n,v,f,s in zip(configs,hs,counts,u,final,ss)],'session_state_sha256':snapshots}

def safe_profile(pr):
 rows=[]
 for (file,line,name),(primitive,total,selfsec,cum,callers) in pstats.Stats(pr).stats.items():
  category='NATIVE' if file=='<pinned-bt2a-bucket-stream>' or file.endswith('/bigtrap2absorption.py') else 'NUMPY' if '/numpy/' in file else 'FOOTPRINT_CACHE' if file.endswith('/bt2a_footprint_cache.py') else 'STREAM' if file.endswith('/bt2a_stream.py') else 'BUILTIN' if file=='~' and name in ('<built-in method builtins.sorted>','<built-in method builtins.max>','<built-in method builtins.min>','<built-in method builtins.sum>','<built-in method builtins.repr>','<built-in method builtins.len>') else None
  if category:rows.append({'category':category,'function':name,'primitive_calls':primitive,'total_calls':total,'self_seconds':selfsec,'cumulative_seconds':cum})
 rows.sort(key=lambda r:r['self_seconds'],reverse=True)
 return {'instrumented_total_seconds':pstats.Stats(pr).total_tt,'top_self_time_functions':rows[:18],'scope':'WHITELIST_STATIC_CODE_NAMES_NO_PATHS_MARKET_ROWS_OR_PRIVATE_LOGS','cumulative_times_overlap_do_not_sum':True,'profiled_pass_excluded_from_speedup':True}

def run(source,p,asset):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market profiling requires Kaggle')
 a=validate(p,asset);roster=json.loads(Path(ROSTER).read_bytes());assert roster['roster_sha256']==p['roster_sha256'];configs=[c for c in roster['configs'] if c['indicator']=='bigtrap2absorption'];tapes=list(iter_sessions(source,start_ns=p['start_ns'],end_ns=p['end_ns'],contract=a['contract'],instrument=a['instrument'],tick_size=a['tick_size'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_total_ticks']))
 dates=[datetime.fromtimestamp(t.session_id*86400,timezone.utc).date().isoformat() for t in tapes]
 if dates!=p['sessions']:raise ValueError('four exact benchmark sessions no substitution')
 results=[measure(tapes,configs,a['tick_size'],s) for s in p['repetitions']];pr=cProfile.Profile();pr.enable();instrumented=measure(tapes,configs,a['tick_size'],p['extra_profile_pass']);pr.disable()
 if any(r['profiles']!=results[0]['profiles'] or r['session_state_sha256']!=results[0]['session_state_sha256'] for r in results[1:]+[instrumented]):raise ValueError('multisession exact native semantic state and capture required')
 speed=statistics.median(r['native_push_and_finish_seconds'] for r in results if r['schedule']=='PROFILE_SEQUENTIAL')/statistics.median(r['native_push_and_finish_seconds'] for r in results if r['schedule']=='CHUNK_INTERLEAVED')
 return {'schema':'bt2a_multisession_profile_receipt_v1','status':'DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE','plan_sha256':digest(p),'sessions':dates,'ticks':sum(len(t.ticks) for t in tapes),'results':results,'native_substep_median_speedup':speed,'semantic_state_and_capture_exact':True,'profile':safe_profile(pr),'initial_state':p['initial_state'],'diagnostics_enabled':False,'outcomes_computed':False,'raw_exported':False,'holdout_opened':False,'pnl':False,'canonical_brain_written':False,'schedule_deployed':False,'NT8_parity_certified':False}

def main():
 ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','asset','private-root','receipt')];a=ap.parse_args();p=json.loads(Path(a.plan).read_bytes());r=run(a.source,p,a.asset);b=json.dumps(r,separators=(',',':'),allow_nan=False).encode();assert len(b)<=p['max_aggregate_bytes'];Path(a.receipt).write_bytes(b+b'\n')
if __name__=='__main__':main()
