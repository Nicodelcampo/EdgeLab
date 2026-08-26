#!/usr/bin/env python3
"""Rebuild the exact 234-session Gate-1 event population for downstream gates."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_all5 import (_context,_end,_labels,_raw_abs_events,_raw_bt2_events,_runtime_sha,_start)
from edgelab.research.bt2_gate1_outcomes import attach_fills,build_path_cache

EXPECTED={
 "GC 12-25":{"K_ABS":6590,"K_BT2":2625},"GC 02-26":{"K_ABS":4523,"K_BT2":913},
 "GC 04-26":{"K_ABS":2411,"K_BT2":950},"GC 06-26":{"K_ABS":2102,"K_BT2":417},
 "GC 08-26":{"K_ABS":1314,"K_BT2":357}}
GATE1_COMMIT="3e639e150bcd7b4691da3d1ba8049a33f586c217"

def canonical_sha(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def file_sha(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for block in iter(lambda:f.read(1<<20),b""): h.update(block)
 return h.hexdigest()
def atomic(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
 tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8"); os.replace(tmp,path)
def git_state(root):
 probe=subprocess.run(["git","rev-parse","HEAD"],cwd=root,text=True,capture_output=True)
 if probe.returncode: return {"available":False,"commit":None,"branch":None,"dirty":True}
 status=subprocess.run(["git","status","--porcelain"],cwd=root,text=True,capture_output=True,check=True).stdout
 branch=subprocess.run(["git","branch","--show-current"],cwd=root,text=True,capture_output=True,check=True).stdout.strip()
 return {"available":True,"commit":probe.stdout.strip(),"branch":branch,"dirty":bool(status.strip())}
def checkpoint(out,index): return Path(out)/"checkpoints"/f"session_{int(index):03d}.json"

def build_session(root,data_dir,out,index):
 sessions,inputs,spec=_context(root); row=sessions["sessions"][int(index)]; contract=str(row["contract"]); session=str(row["cme_session_id"])
 parquet=Path(data_dir)/inputs["contracts"][contract]["parquet_file"]; expected=inputs["contracts"][contract]["parquet_sha256"]
 if not parquet.is_file() or file_sha(parquet)!=expected: raise RuntimeError(f"input identity mismatch: {contract}")
 ticks=load_canonical_parquet(parquet,contract=contract,start_utc_ns=_start(row["warmup_cme_session_id"]),end_utc_ns=_end(session),instrument="GC")
 labels=_labels(ticks.ts_ns); cache=build_path_cache(ticks.ts_ns,ticks.price_ticks,labels,tick_cap=int(spec["horizon"]["tick_cap"]),clock_cap_seconds=int(spec["horizon"]["clock_cap_seconds"]))
 raw=_raw_abs_events(ticks,labels,{session})+_raw_bt2_events(ticks,labels,{session})
 attached,fill_excluded=attach_fills(raw,ts_ns=ticks.ts_ns,source_row=ticks.sequence,session_ids=labels); events=[]; path_excluded=[]; runtime=_runtime_sha(root)
 for event in attached:
  if event.session!=session: continue
  if not cache.eligible[event.fill_idx]: path_excluded.append({"event_id":event.key,"reason":"EXCLUDED_INCOMPLETE_GATE1_HORIZON"}); continue
  i=event.fill_idx; end=cache.end_idx[i]
  payload={"event_id":event.key,"arm":event.arm,"contract":event.contract,"cme_session":event.session,"direction":int(event.direction),
   "signal_ts_utc_ns":int(event.signal_ts_ns),"signal_source_row":int(event.signal_source_row),"fill_ts_utc_ns":int(ticks.ts_ns[i]),
   "fill_source_row":int(ticks.sequence[i]),"fill_price_ticks":int(ticks.price_ticks[i]),"gate1_horizon_end_ts_utc_ns":int(ticks.ts_ns[end]),
   "gate1_horizon_end_source_row":int(ticks.sequence[end]),"gate1_cap_driver":"ticks" if int(cache.cap_driver[i])==0 else "clock",
   "gate1_input_sha256":expected,"gate1_runtime_sha256":runtime,"gate1_canonical_commit":GATE1_COMMIT}
  payload["identity_sha256"]=canonical_sha(payload); events.append(payload)
 events.sort(key=lambda x:(x["fill_ts_utc_ns"],x["fill_source_row"],x["arm"],x["event_id"])); ids=[x["event_id"] for x in events]
 if len(ids)!=len(set(ids)): raise RuntimeError("duplicate event_id")
 result={"schema":"bt2a_gate1_canonical_event_store_session_v1","status":"COMPLETE","session_index":int(index),"contract":contract,"cme_session":session,
  "warmup_session":str(row["warmup_cme_session_id"]),"counts":dict(sorted(Counter(x["arm"] for x in events).items())),
  "excluded_fill_count":len(fill_excluded),"excluded_path_count":len(path_excluded),"excluded_fills":fill_excluded,"excluded_paths":path_excluded,
  "events":events,"events_sha256":canonical_sha(events),"sample_registry_payload_sha256":sessions["registry_payload_sha256"],
  "input_registry_payload_sha256":inputs["registry_payload_sha256"],"runtime_sha256":runtime,"canonical_gate1_commit":GATE1_COMMIT,
  "CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False}
 atomic(checkpoint(out,index),result); return result

def finalize(root,out):
 sessions,inputs,_=_context(root); rows=[]
 for index in range(len(sessions["sessions"])):
  path=checkpoint(out,index)
  if not path.is_file(): raise RuntimeError(f"missing {path.name}")
  rows.append(json.loads(path.read_text()))
 events=[e for row in rows for e in row["events"]]; ids=[e["event_id"] for e in events]; hashes=[e["identity_sha256"] for e in events]
 if len(ids)!=len(set(ids)) or len(hashes)!=len(set(hashes)): raise RuntimeError("duplicate event identity")
 counts=defaultdict(lambda:defaultdict(int))
 for e in events: counts[e["contract"]][e["arm"]]+=1
 observed={c:{a:int(n) for a,n in sorted(v.items())} for c,v in sorted(counts.items())}
 if observed!=EXPECTED: raise RuntimeError(f"count mismatch: {observed}")
 frame=pd.DataFrame(events).sort_values(["contract","cme_session","fill_ts_utc_ns","fill_source_row","arm","event_id"],kind="stable"); out=Path(out); out.mkdir(parents=True,exist_ok=True)
 target=out/"bt2a_gate1_canonical_events_all5.parquet"; frame.to_parquet(target,index=False)
 manifest={"schema":"bt2a_gate1_canonical_event_store_manifest_v1","status":"COMPLETE_RECONCILED_WITH_GATE1_ALL5","generated_utc":datetime.now(timezone.utc).isoformat(),
  "n_sessions":len(rows),"n_events":len(events),"counts":observed,"expected_counts":EXPECTED,"event_ids_unique":True,"identity_sha256_unique":True,
  "fill_rule":"first canonical tick strictly after signal","session_boundary":"hard CME","gate1_eligibility_reused":True,
  "parquet":{"path":target.name,"bytes":target.stat().st_size,"sha256":file_sha(target)},"events_payload_sha256":canonical_sha(events),
  "sample_registry_payload_sha256":sessions["registry_payload_sha256"],"input_registry_payload_sha256":inputs["registry_payload_sha256"],
  "runtime_sha256":_runtime_sha(root),"canonical_gate1_commit":GATE1_COMMIT,"builder_git":git_state(root),"CAMPAIGN_OUTCOMES_OPENED":True,
  "EDGE_DECLARED":False,"confirmatory_eligible":False}
 atomic(out/"run_manifest.json",manifest); return manifest

def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--data-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True)
 mode=p.add_mutually_exclusive_group(required=True); mode.add_argument("--session-index",type=int); mode.add_argument("--finalize",action="store_true"); p.add_argument("--allow-dirty",action="store_true"); a=p.parse_args(); root=a.root.resolve(); state=git_state(root)
 if state["dirty"] and not a.allow_dirty: raise SystemExit("ABSTAIN_DIRTY_WORKTREE")
 result=finalize(root,a.output_dir) if a.finalize else build_session(root,a.data_dir,a.output_dir,a.session_index)
 print(json.dumps({k:v for k,v in result.items() if k!="events"},indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
