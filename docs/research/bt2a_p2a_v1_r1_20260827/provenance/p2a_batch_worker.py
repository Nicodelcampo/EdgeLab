#!/usr/bin/env python3
import argparse,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--event-store-dir',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--start',type=int,required=True);p.add_argument('--step',type=int,required=True);p.add_argument('--authorization-token',required=True);a=p.parse_args()
sys.path.insert(0,str(a.root));sys.path.insert(0,str(a.root/'tools'))
import run_bt2a_gate2_p2a as r
if a.authorization_token!=r.AUTH: raise SystemExit('ABSTAIN_MISSING_EXPLICIT_P2A_AUTHORIZATION')
ready=r.preflight(a.root,a.event_store_dir)
if ready['status']!='PASS_READY_FOR_AUTHORIZATION' or ready['outcomes_opened'] is not False: raise SystemExit('ABSTAIN_P2A_PREFLIGHT_NOT_READY')
spec=r.load_spec(a.root)
if int(spec['p2a']['control_replications'])!=10000 or int(spec['inference']['bootstrap_replications'])!=10000: raise SystemExit('ABSTAIN_FROZEN_REPLICATION_COUNT_MISMATCH')
registry,_,_=r._context(a.root)
if len(registry['sessions'])!=234 or max(x['cme_session_id'] for x in registry['sessions'])>'20260630': raise SystemExit('ABSTAIN_HOLDOUT_FIREWALL')
print(json.dumps({'worker_start':a.start,'step':a.step,'preflight':ready['status'],'n_sessions':len(registry['sessions']),'authorization_verified':True}),flush=True)
for i in range(a.start,len(registry['sessions']),a.step):
 cp=r.checkpoint(a.output_dir,i)
 if cp.is_file():
  print(f'SKIP={i:03d}',flush=True);continue
 t=time.monotonic();v=r.run_session(a.root,a.data_dir,a.event_store_dir,a.output_dir,i,10000)
 print(f'DONE={i:03d} ELAPSED={time.monotonic()-t:.3f} PAYLOAD={v["payload_sha256"]}',flush=True)
print(f'WORKER_COMPLETE={a.start}',flush=True)
