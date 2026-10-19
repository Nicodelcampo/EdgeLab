#!/usr/bin/env python3
"""Derive BT2A NQ Gate 1 planning inputs without reading outcomes or price paths."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from statistics import NormalDist

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def load(path:Path)->dict:
 v=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(v,dict): raise RuntimeError('JSON root must be object')
 return v

def positive_int(v,name):
 if isinstance(v,bool) or not isinstance(v,int) or v<1: raise RuntimeError(f'{name} must be positive integer')
 return v

def derive(manifest:Path, expected_sha:str|None, bt2_events:int|None, bt2_sessions:int|None,
           n_rand_capacity_ok:bool|None, mde:float, icc:float, max_barrier:int)->dict:
 if expected_sha and sha(manifest)!=expected_sha: raise RuntimeError('event-store manifest SHA mismatch')
 m=load(manifest)
 if m.get('status')!='READY_CREATION_EVENT_STORE': raise RuntimeError('event store is not READY_CREATION_EVENT_STORE')
 fw=m.get('firewall') or {}
 if any(bool(v) for v in fw.values()): raise RuntimeError('event-store firewall is not closed')
 rows=positive_int(m.get('rows'),'rows'); sessions=positive_int(m.get('sessions_with_events'),'sessions_with_events')
 if sessions>234: raise RuntimeError('sessions exceed frozen pre-holdout universe')
 if not (mde>0 and 0<=icc<1 and max_barrier>0): raise RuntimeError('invalid planning assumption')
 mean=rows/sessions; deff=1+(mean-1)*icc
 sd_bound=2.0*max_barrier
 zcrit=NormalDist().inv_cdf(1-(.05/16)/2); zpow=NormalDist().inv_cdf(.8)
 required=math.ceil(((zcrit+zpow)*sd_bound/mde)**2)
 missing=[]
 if bt2_events is None or bt2_sessions is None: missing.append('K_BT2 density from frozen V2 artifact')
 if n_rand_capacity_ok is not True: missing.append('N_RAND matched-pool capacity by frozen strata')
 if sessions<required: missing.append('effective sessions below conservative finite-support requirement')
 return {
  'schema_version':'bt2a_nq_gate1_target_free_planning_inputs_v1',
  'status':'PASS_TARGET_FREE_INPUTS_COMPLETE' if not missing else 'NOT_READY',
  'event_store':{'manifest_file_sha256':sha(manifest),'rows':rows,'sessions':sessions,'events_per_session':mean},
  'K_BT2':None if bt2_events is None or bt2_sessions is None else {'events':positive_int(bt2_events,'bt2_events'),'sessions':positive_int(bt2_sessions,'bt2_sessions'),'events_per_session':bt2_events/bt2_sessions},
  'N_RAND_capacity_ok':n_rand_capacity_ok,
  'design':{'mde_ticks':mde,'icc_assumption':icc,'design_effect':deff,'paired_session_sd_ticks_upper_bound':sd_bound,'effective_sessions_available':float(sessions),'effective_sessions_required_conservative':required,'alpha_family':.05,'cells':16,'target_power':.8},
  'missing_or_blocking':missing,
  'attestation':{'OUTCOMES_ACCESSED':False,'FUTURE_PRICE_PATH_ACCESSED':False,'PNL_ACCESSED':False,'HOLDOUT_TOUCHED':False},
 }

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--event-store-manifest',type=Path,required=True); p.add_argument('--event-store-manifest-sha256')
 p.add_argument('--bt2-events',type=int); p.add_argument('--bt2-sessions',type=int)
 p.add_argument('--n-rand-capacity-ok',choices=['true','false'])
 p.add_argument('--mde-ticks',type=float,default=1.0); p.add_argument('--icc',type=float,default=.20); p.add_argument('--max-barrier-ticks',type=int,default=30)
 p.add_argument('--output',type=Path,required=True); a=p.parse_args(argv)
 cap=None if a.n_rand_capacity_ok is None else a.n_rand_capacity_ok=='true'
 out=derive(a.event_store_manifest,a.event_store_manifest_sha256,a.bt2_events,a.bt2_sessions,cap,a.mde_ticks,a.icc,a.max_barrier_ticks)
 a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out['status'].startswith('PASS') else 2
if __name__=='__main__': raise SystemExit(main())
