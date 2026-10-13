"""Finite same-tape scheduling benchmark. Market tape stays inside Kaggle."""
import argparse,hashlib,json,os,time,resource
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from .bt2a_stream import BT2AStream,TickChunk
from .bt2a_footprint_cache import BucketFootprintCache
from .kaggle_session_reader import iter_sessions
from .build_target_free_pilot import digest
from .cross_family_pilot import ROSTER

def measure(st,configs,tick_size,*,schedule):
 if schedule not in ('PROFILE_SEQUENTIAL','CHUNK_INTERLEAVED'):raise ValueError('closed benchmark schedule')
 cache=BucketFootprintCache();streams=[BT2AStream(params=c['params'],tick_size=tick_size,collect_diagnostics=True,footprint_cache=cache) for c in configs];hashes=[hashlib.sha256() for _ in streams];counts=[0]*len(streams);unavailable=[0]*len(streams)
 t=st.ticks;ids=np.full(len(t),st.session_id,dtype=np.int64);started=time.monotonic()
 def push(k,j,z):
  d=streams[k].push(TickChunk(*(getattr(t,n)[j:z] for n in ('ts_ns','price_ticks','volume','bid_ticks','ask_ticks','sequence')),ids[j:z],j));consume(k,d)
 def consume(k,d):
  unavailable[k]+=d.unavailable_events
  for r in d.records:hashes[k].update(repr(r).encode()+b'\n');counts[k]+=1
 if schedule=='PROFILE_SEQUENTIAL':
  for k in range(len(streams)):
   for j in range(0,len(t),100000):push(k,j,min(j+100000,len(t)))
 else:
  for j in range(0,len(t),1000):
   for k in range(len(streams)):push(k,j,min(j+1000,len(t)))
 for k,s in enumerate(streams):consume(k,s.finish())
 elapsed=time.monotonic()-started
 return {'schedule':schedule,'wall_seconds':elapsed,'cache':cache.receipt(),'profiles':[{'config_sha256':c['config_sha256'],'capture_sha256':h.hexdigest(),'capture_records':n,'unavailable_events':u,'state_sizes':s.state_sizes(),'native_log_sha256':s.log_hash.hexdigest()} for c,h,n,u,s in zip(configs,hashes,counts,unavailable,streams)]}

def run(source,p,asset):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market scheduling benchmark Kaggle only')
 if asset!='GC' or p['schema']!='gc_focused_return_plan_v1':raise ValueError('explicit GC benchmark scope')
 a=p['assets'][asset];roster=json.loads(Path(ROSTER).read_bytes());configs=[c for c in roster['configs'] if c['indicator']=='bigtrap2absorption'];r=p['session_ranges'][0]
 sts=list(iter_sessions(source,start_ns=r['start_ns'],end_ns=r['end_ns'],contract=a['contract'],instrument=a['instrument'],tick_size=a['tick_size'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_session_ticks']))
 if len(sts)!=1 or datetime.fromtimestamp(sts[0].session_id*86400,timezone.utc).date().isoformat()!='2026-08-03':raise ValueError('one fixed benchmark development session')
 results=[measure(sts[0],configs,a['tick_size'],schedule=s) for s in ('PROFILE_SEQUENTIAL','CHUNK_INTERLEAVED','CHUNK_INTERLEAVED','PROFILE_SEQUENTIAL')]
 exact=all(x['profiles']==results[0]['profiles'] for x in results)
 if not exact:raise ValueError('same-input scheduling native capture state log parity failed')
 return {'schema':'bt2a_schedule_benchmark_v1','status':'DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE','plan_sha256':digest(p),'asset':asset,'trade_date':'2026-08-03','ticks':len(sts[0].ticks),'repetitions_order':'ABBA','initial_state':'FRESH_EACH_PASS_SAME_NATIVE_MINIMUM_HISTORY_BUCKETS_NOT_CROSS_SESSION_WARMUP_CERTIFICATE','same_input_native_capture_state_log_exact':exact,'results':results,'median_substep_speedup':float(np.median([x['wall_seconds'] for x in results if x['schedule']=='PROFILE_SEQUENTIAL'])/np.median([x['wall_seconds'] for x in results if x['schedule']=='CHUNK_INTERLEAVED'])),'benchmark_scope':'THREE_BT2A_PROFILES_ONE_GC_SESSION_NOT_FULL_PIPELINE_OR_NT8_CERTIFICATE','schedule_deployed':False,'raw_exported':False,'holdout_opened':False,'pnl':False,'canonical_brain_written':False,'edge_claim':False,'confirmation':False,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}

def main():
 ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','asset','private-root','receipt')];a=ap.parse_args();p=json.loads(Path(a.plan).read_bytes())
 from .multiasset_crossfamily import validate_plan
 validate_plan(p,a.asset);out=run(a.source,p,a.asset);Path(a.receipt).write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
if __name__=='__main__':main()
