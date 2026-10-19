"""Exact-input original versus rolling-percentile benchmark; no science outcomes."""
import argparse,json,os,statistics
from datetime import datetime,timezone
from pathlib import Path
from .bt2a_multisession_profile import measure
from .build_target_free_pilot import digest
from .cross_family_pilot import ROSTER
from .kaggle_session_reader import iter_sessions
PLAN='docs/research/ops/GC_BT2A_ROLLING_PLAN.json'
PLAN_SHA='c91b12d689ceeaa62ee0cb130e563814f15d40edb13855dd5c2e15475f4471ba'

def validate(p,asset):
 if digest(p)!=PLAN_SHA or asset!='GC':raise ValueError('exact bounded rolling benchmark plan')
 if any(p[k] is not False for k in ('labels','models','outcomes','holdout','pnl','raw_export','canonical_brain_write','production_default_changed','automatic_promotion')):raise ValueError('experimental rolling only no promotion')
 return p['assets'][asset]

def same(a,b):return a['profiles']==b['profiles'] and a['session_state_sha256']==b['session_state_sha256']

def run(source,p,asset):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('market rolling benchmark Kaggle only')
 a=validate(p,asset);r=json.loads(Path(ROSTER).read_bytes());assert r['roster_sha256']==p['roster_sha256'];configs=[c for c in r['configs'] if c['indicator']=='bigtrap2absorption'];tapes=list(iter_sessions(source,start_ns=p['start_ns'],end_ns=p['end_ns'],contract=a['contract'],instrument=a['instrument'],tick_size=a['tick_size'],max_session_ticks=p['max_session_ticks'],max_total_ticks=p['max_total_ticks']))
 dates=[datetime.fromtimestamp(t.session_id*86400,timezone.utc).date().isoformat() for t in tapes]
 if dates!=p['sessions']:raise ValueError('four exact rolling benchmark sessions no substitutes')
 def one(mode,diag=False):
  if mode not in ('ORIGINAL','ROLLING'):raise ValueError('closed percentile algorithm')
  return {'algorithm':mode,'diagnostics_enabled':diag,**measure(tapes,configs,a['tick_size'],'PROFILE_SEQUENTIAL',rolling_percentile=mode=='ROLLING',collect_diagnostics=diag)}
 results=[one(m) for m in p['repetitions']];diagnostics=[one(m,True) for m in p['diagnostic_pair']]
 if any(not same(results[0],v) for v in results[1:]) or not same(*diagnostics):raise ValueError('rolling exact state thresholds logs captures required')
 old=statistics.median(v['native_push_and_finish_seconds'] for v in results if v['algorithm']=='ORIGINAL');new=statistics.median(v['native_push_and_finish_seconds'] for v in results if v['algorithm']=='ROLLING')
 out={'schema':'bt2a_rolling_benchmark_receipt_v1','status':'DEVELOPMENT_CROSSFAMILY_COMPLETE_NOT_EDGE','plan_sha256':digest(p),'sessions':dates,'ticks':sum(len(t.ticks) for t in tapes),'results':results,'diagnostic_pair':diagnostics,'production_native_state_captures_exact':True,'diagnostic_thresholds_logs_state_captures_exact':True,'native_substep_median_speedup':old/new,'native_substep_duration_reduction_percent':100*(1-new/old),'original_native_median_seconds':old,'rolling_native_median_seconds':new,'scope':'BT2A_THREE_PROFILES_FOUR_GC_SESSIONS_NOT_PIPELINE_NT8_CERTIFICATE','default_rolling_opt_in':False,'production_default_changed':False,'automatic_promotion':False,'raw_exported':False,'outcomes_computed':False,'holdout_opened':False,'pnl':False,'canonical_brain_written':False,'edge_claim':False};return out

def main():
 ap=argparse.ArgumentParser();[ap.add_argument('--'+k,required=True) for k in ('source','plan','asset','private-root','receipt')];a=ap.parse_args();p=json.loads(Path(a.plan).read_bytes());r=run(a.source,p,a.asset);b=json.dumps(r,separators=(',',':'),allow_nan=False).encode();assert len(b)<=p['max_aggregate_bytes'];Path(a.receipt).write_bytes(b+b'\n')
if __name__=='__main__':main()
