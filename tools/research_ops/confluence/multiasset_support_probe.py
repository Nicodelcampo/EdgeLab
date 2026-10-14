"""Bounded eligibility diagnosis of frozen dates, no detectors/fits or scores.

Market source remains Kaggle-only. No date substitution, gap relaxation, ticker
parameter transfer, partial-success promotion or source-quality re-audit.
"""
import argparse,json,os,time,math,resource
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import numpy as np
from .multiasset_crossfamily import PLAN,PLAN_SHA,validate_plan,AssetCalibration
from .phenomena import ClockMeasurements
from .phenomena_models import state
from .phenomena_response import SecondsResponse
from .kaggle_session_reader import iter_sessions
from .build_target_free_pilot import digest
PROBE='docs/research/ops/MULTIASSET_SUPPORT_PROBE_PLAN.json'
def finish_counts(anchors,states,reasons,labels,common):
 if anchors!=sum(states.values()) or anchors!=sum(reasons.values())+common:raise ValueError('support census reconciliation')
 return {'anchors':anchors,'classification_state_counts':dict(states),'excluded_counts':dict(reasons),'response_status_counts':dict(labels),'common_usable_anchors':common,'training_min100_passed':common>=100}
def measure_support(st,date,p,cal):
 t=st.ticks;m=ClockMeasurements(max_ticks=p['max_session_ticks'],max_anchors=p['max_anchors'],wall_seconds=600)
 response=SecondsResponse(t.ts_ns,t.sequence,t.bid_ticks,t.ask_ticks,max_ticks=p['max_session_ticks'],max_anchors=p['max_anchors'],max_scan_elements=p['max_scan_elements_per_session'],wall_seconds=600)
 census=Counter();reasons=Counter();detail=Counter();labels=Counter();windows={w:Counter() for w in ('20_CURRENT','20_PRIOR','60_CURRENT')};anchors=n=0
 for row in m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=date):
  anchors+=1;s=state(row,cal,research_dates=p['training_sessions']);census[s['state']]+=1
  for name,w,side in (('20_CURRENT','20','current'),('20_PRIOR','20','prior'),('60_CURRENT','60','current')):windows[name][row['windows'][w][side]['status']]+=1
  if s['state']=='UNKNOWN':reasons['CLASSIFICATION_UNKNOWN']+=1;detail[s['reason']]+=1;continue
  ctx=row['windows']['60']['current']
  if ctx['status']!='OBSERVABLE':reasons['ORIGIN_60S_CONTEXT_UNKNOWN']+=1;continue
  i=int(np.searchsorted(t.sequence,row['sequence']));assert i<len(t.sequence) and int(t.sequence[i])==row['sequence'] and int(t.ts_ns[i])==row['timestamp_ns']
  lab=response.label(i,direction=row['windows']['20']['direction_from_prior'],distance_ticks=max(4,math.ceil(.5*ctx['range_midpoint_ticks'])));labels[lab['status']]+=1
  if lab['usable']:n+=1
  else:reasons[lab['status']]+=1
 r=finish_counts(anchors,census,reasons,labels,n);r.update(trade_date=date,ticks=len(t.ts_ns),classification_unknown_reasons=dict(detail),window_status_counts={k:dict(v) for k,v in windows.items()},response_scanned_elements=response.scanned);return r

def run(root,plan,probe):
 if not os.environ.get('KAGGLE_KERNEL_RUN_TYPE'):raise ValueError('Kaggle-only support diagnosis')
 if digest(plan)!=PLAN_SHA or probe!={'schema':'multiasset_support_probe_plan_v1','original_plan_sha256':PLAN_SHA,'assets':['GC','6E','ZB'],'dates':[plan['calibration_date']]+plan['training_sessions'],'max_wall_seconds':600,'max_aggregate_bytes':262144,'scores':False,'native_detectors':False,'gap_relaxed':False,'calendar_changed':False,'holdout':False,'raw_export':False}:raise ValueError('exact frozen support diagnostic')
 started=time.monotonic();out={};scanned=0
 begin=int(datetime.fromisoformat(plan['calibration_date']+'T22:00:00+00:00').timestamp())*10**9-86400*10**9
 end=int(datetime.fromisoformat(plan['training_sessions'][-1]+'T22:00:00+00:00').timestamp())*10**9
 for asset in probe['assets']:
  a,_=validate_plan(plan,asset);source=Path(root)/a['pin']['file'];cal=None;sessions=[];seen=set()
  for st in iter_sessions(source,start_ns=begin,end_ns=end,contract=a['contract'],instrument=a['instrument'],tick_size=a['tick_size'],max_session_ticks=plan['max_session_ticks'],max_total_ticks=plan['max_total_ticks']):
   date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
   if date not in probe['dates']:continue
   seen.add(date)
   if date==plan['calibration_date']:
    c=AssetCalibration(date);m=ClockMeasurements(max_ticks=plan['max_session_ticks'],max_anchors=plan['max_anchors'],wall_seconds=600)
    for row in m.measure(st.ticks.ts_ns,st.ticks.sequence,st.ticks.price_ticks,st.ticks.volume,st.ticks.bid_ticks,st.ticks.ask_ticks,trade_date=date):c.add(row)
    cal=c.freeze()
   else:
    if cal is None:raise ValueError('original asset calibration unavailable')
    r=measure_support(st,date,plan,cal);scanned+=r['response_scanned_elements'];sessions.append(r)
   if time.monotonic()-started>600 or scanned>plan['max_scan_elements_total']:raise TimeoutError('bounded support diagnosis')
  out[asset]={'contract':a['contract'],'tick_size':a['tick_size'],'calibration':cal,'training_sessions':sessions,'source_empty_dates':[d for d in probe['dates'] if d not in seen],'all_original_training_min100_passed':len(sessions)==6 and all(s['training_min100_passed'] for s in sessions)}
 result={'schema':'multiasset_support_probe_receipt_v1','status':'SUPPORT_DIAGNOSIS_NOT_MODEL_RESULTS','probe_sha256':digest(probe),'original_plan_sha256':PLAN_SHA,'assets':out,'wall_seconds':time.monotonic()-started,'response_scanned_elements':scanned,'runner_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'gap_relaxed':False,'calendar_changed':False,'model_scores_computed':False,'native_detectors_run':False,'raw_exported':False,'holdout_opened':False,'pnl':False,'edge_claim':False,'canonical_brain_written':False}
 if len(json.dumps(result,separators=(',',':')).encode())>262144:raise ValueError('support aggregate cap')
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',required=True);p.add_argument('--receipt',required=True);a=p.parse_args();r=run(a.source_root,json.loads(Path(PLAN).read_bytes()),json.loads(Path(PROBE).read_bytes()));Path(a.receipt).write_text(json.dumps(r,separators=(',',':'),allow_nan=False)+'\n')
if __name__=='__main__':main()
