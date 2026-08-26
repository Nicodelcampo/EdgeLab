#!/usr/bin/env python3
"""Checkpointed, authorization-gated BT2A Gate-2 first-passage runner."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
import numpy as np
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_all5 import _context,_end,_labels,_start
from edgelab.research.bt2_gate1_outcomes import _sample_without_own,build_path_cache,chicago_bin30
from edgelab.research.bt2a_gate2_first_passage import (first_passage_scores_fast,holm_adjust,horizon_endpoints,next_barrier_touch_indices,summarize_scores,wild_cluster_test)

AUTH="AUTHORIZE_BT2A_P2A_POST_OUTCOME_DIAGNOSTIC"
BARRIERS=(5,9,18,30); TICK_H=(25,50,100,250); CLOCK_H=(5,30,120); BASE_SEED=20260821

def canonical(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def array_sha(value):
 a=np.ascontiguousarray(value); h=hashlib.sha256(); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.view(np.uint8)); return h.hexdigest()
def atomic(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"); os.replace(tmp,path)
def seed(label,purpose): return int.from_bytes(hashlib.sha256(f"{BASE_SEED}|{label}|{purpose}".encode()).digest()[:8],"little")%(2**32-1)
def checkpoint(out,index): return Path(out)/"checkpoints"/f"session_{int(index):03d}.json"

def map_indices(events,sequence,ts,price):
 src=np.asarray([int(e["fill_source_row"]) for e in events]); pos=np.searchsorted(sequence,src)
 if np.any(pos>=len(sequence)) or np.any(sequence[pos]!=src): raise RuntimeError("fill_source_row absent")
 for e,i in zip(events,pos):
  if int(ts[i])!=int(e["fill_ts_utc_ns"]) or int(price[i])!=int(e["fill_price_ticks"]): raise RuntimeError(f"fill identity mismatch: {e['event_id']}")
 return pos.astype(np.int64)

def sample_nrand(abs_idx,ts,cache,replications,random_seed):
 candidates=np.flatnonzero(cache.eligible); bins=chicago_bin30(ts[candidates]); event_bins=chicago_bin30(ts[abs_idx])
 candidate_groups={k:candidates[(bins==k[0])&(cache.cap_driver[candidates]==k[1])] for k in sorted(set(zip(bins.tolist(),cache.cap_driver[candidates].tolist())))}
 event_groups={k:np.flatnonzero((event_bins==k[0])&(cache.cap_driver[abs_idx]==k[1])) for k in sorted(set(zip(event_bins.tolist(),cache.cap_driver[abs_idx].tolist())))}
 for k,positions in event_groups.items():
  if len(candidate_groups.get(k,()))-1<len(positions): raise ValueError(f"PRECONDITION_FAILED_SPARSE_STRATUM {k}")
 rng=np.random.default_rng(random_seed); sampled=np.empty((replications,len(abs_idx)),dtype=np.int64)
 for b in range(replications):
  for k,positions in event_groups.items(): sampled[b,positions]=_sample_without_own(candidate_groups[k],abs_idx[positions],rng)
 return sampled

def control_summary(x):
 x=np.asarray(x,dtype=float); return {"replications":len(x),"median_theta_fp":float(np.median(x)),"mean_theta_fp":float(x.mean()),"q025_theta_fp":float(np.quantile(x,.025)),"q975_theta_fp":float(np.quantile(x,.975))}

def score_cell(price,ts,sessions,abs_idx,abs_dir,bt_idx,bt_dir,sampled,touches,barrier,tick_cap,clock_cap,shuffle_seed):
 ends,drivers=horizon_endpoints(ts,sessions,tick_cap=tick_cap,clock_cap_seconds=clock_cap)
 def scores(idx,direction): return first_passage_scores_fast(price,ts,sessions,fill_indices=idx,directions=direction,barrier_ticks=barrier,tick_cap=tick_cap,clock_cap_seconds=clock_cap,precomputed_touches=touches,precomputed_endpoints=ends)
 abs_scores=scores(abs_idx,abs_dir); bt_scores=scores(bt_idx,bt_dir); long=scores(abs_idx,np.ones(len(abs_idx),dtype=np.int8)); short=scores(abs_idx,-np.ones(len(abs_idx),dtype=np.int8))
 rng=np.random.default_rng(shuffle_seed); shuffle=np.array([np.where(rng.permutation(abs_dir)>0,long,short).mean() for _ in range(len(sampled))])
 flat=scores(sampled.reshape(-1),np.tile(abs_dir,len(sampled))).reshape(sampled.shape); nrand=flat.mean(axis=1)
 a=summarize_scores(abs_scores); b=summarize_scores(bt_scores); n=control_summary(nrand); sh=control_summary(shuffle)
 return {"barrier_ticks":barrier,"horizon_type":"ticks" if tick_cap is not None else "seconds","horizon_value":tick_cap if tick_cap is not None else clock_cap,
  "K_ABS":a,"K_BT2":b,"N_RAND":n,"K_ABS_SHUFFLE":sh,"contrasts":{"K_ABS_minus_N_RAND":a["theta_fp"]-n["median_theta_fp"],"K_ABS_minus_K_ABS_SHUFFLE":a["theta_fp"]-sh["median_theta_fp"],"K_ABS_minus_K_BT2":a["theta_fp"]-b["theta_fp"]},
  "cap_driver_at_K_ABS":{name:int(np.sum(drivers[abs_idx]==name)) for name in ("ticks","clock","session")}}

def run_session(root,data_dir,event_store,out,index,replications):
 registry,inputs,gate1=_context(root); row=registry["sessions"][int(index)]; contract=row["contract"]; session=row["cme_session_id"]
 source=json.loads((Path(event_store)/"checkpoints"/f"session_{int(index):03d}.json").read_text())
 if source.get("status")!="COMPLETE" or source.get("cme_session")!=session: raise RuntimeError("event checkpoint mismatch")
 abs_events=[e for e in source["events"] if e["arm"]=="K_ABS"]; bt_events=[e for e in source["events"] if e["arm"]=="K_BT2"]
 if not abs_events or not bt_events: raise RuntimeError("observed arm missing")
 ticks=load_canonical_parquet(Path(data_dir)/inputs["contracts"][contract]["parquet_file"],contract=contract,start_utc_ns=_start(session),end_utc_ns=_end(session),instrument="GC"); sessions=_labels(ticks.ts_ns)
 if set(sessions.tolist())!={session}: raise RuntimeError("foreign session label")
 abs_idx=map_indices(abs_events,ticks.sequence,ticks.ts_ns,ticks.price_ticks); bt_idx=map_indices(bt_events,ticks.sequence,ticks.ts_ns,ticks.price_ticks); abs_dir=np.asarray([e["direction"] for e in abs_events],dtype=np.int8); bt_dir=np.asarray([e["direction"] for e in bt_events],dtype=np.int8)
 cache=build_path_cache(ticks.ts_ns,ticks.price_ticks,sessions,tick_cap=int(gate1["horizon"]["tick_cap"]),clock_cap_seconds=int(gate1["horizon"]["clock_cap_seconds"]))
 if np.any(~cache.eligible[abs_idx]) or np.any(~cache.eligible[bt_idx]): raise RuntimeError("Gate1-ineligible event")
 sampled=sample_nrand(abs_idx,ticks.ts_ns,cache,replications,seed(session,"nrand")); cells=[]
 for barrier in BARRIERS:
  touches=next_barrier_touch_indices(ticks.price_ticks,sessions,barrier_ticks=barrier)
  for horizon in TICK_H: cells.append(score_cell(ticks.price_ticks,ticks.ts_ns,sessions,abs_idx,abs_dir,bt_idx,bt_dir,sampled,touches,barrier,horizon,None,seed(session,f"shuffle|{barrier}|ticks|{horizon}")))
  for horizon in CLOCK_H: cells.append(score_cell(ticks.price_ticks,ticks.ts_ns,sessions,abs_idx,abs_dir,bt_idx,bt_dir,sampled,touches,barrier,None,horizon,seed(session,f"shuffle|{barrier}|seconds|{horizon}")))
 result={"schema":"bt2a_gate2_p2a_session_v1","status":"COMPLETE_POST_OUTCOME_DIAGNOSTIC_SESSION","session_index":int(index),"contract":contract,"cme_session":session,"source_event_checkpoint_sha256":canonical(source),"n_K_ABS":len(abs_events),"n_K_BT2":len(bt_events),"control_replications":replications,"nrand_anchor_matrix_sha256":array_sha(sampled),"cells":cells,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False}; result["payload_sha256"]=canonical(result); atomic(checkpoint(out,index),result); return result

def finalize(root,out,replications):
 registry,_,_=_context(root); rows=[]
 for index in range(len(registry["sessions"])):
  path=checkpoint(out,index)
  if not path.is_file(): raise RuntimeError(f"missing {path.name}")
  rows.append(json.loads(path.read_text()))
 surfaces=[]
 for barrier in BARRIERS:
  for horizon in TICK_H:
   cells=[next(c for c in row["cells"] if c["barrier_ticks"]==barrier and c["horizon_type"]=="ticks" and c["horizon_value"]==horizon) for row in rows]; contrasts={}
   for name in ("K_ABS_minus_N_RAND","K_ABS_minus_K_ABS_SHUFFLE","K_ABS_minus_K_BT2"): contrasts[name]=wild_cluster_test([c["contrasts"][name] for c in cells],replications=replications,seed=seed(f"{barrier}|{horizon}",name))
   surfaces.append({"barrier_ticks":barrier,"horizon_ticks":horizon,"n_sessions":len(cells),"contrasts":contrasts})
 adjusted=holm_adjust([x["contrasts"]["K_ABS_minus_N_RAND"]["p_two_sided"] for x in surfaces])
 for cell,p in zip(surfaces,adjusted): cell["contrasts"]["K_ABS_minus_N_RAND"]["p_holm_16"]=p
 result={"schema":"bt2a_gate2_p2a_result_v1","status":"COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC","n_sessions":len(rows),"primary_family":surfaces,"secondary_clock_cells_in_checkpoints":True,"multiplicity":"HOLM_OVER_16_PRIMARY_CELLS","unit":"CME_SESSION","timeout_in_estimand":True,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False,"promotion_eligible":False}; result["payload_sha256"]=canonical(result); atomic(Path(out)/"gate2_p2a_result.json",result); return result

def preflight(root,event_store):
 registry,_,_=_context(root); missing=[i for i in range(len(registry["sessions"])) if not (Path(event_store)/"checkpoints"/f"session_{i:03d}.json").is_file()]; path=Path(root)/"specs"/"bt2a_gate2_first_passage_v1.json"; status=json.loads(path.read_text()).get("status") if path.is_file() else "MISSING"
 return {"status":"PASS_READY_FOR_AUTHORIZATION" if not missing and str(status).startswith("FROZEN") else "NOT_READY","spec_status":status,"n_expected_sessions":len(registry["sessions"]),"n_missing_event_checkpoints":len(missing),"missing_event_checkpoint_indices":missing[:50],"outcomes_opened":False}

def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--data-dir",type=Path); p.add_argument("--event-store-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path); mode=p.add_mutually_exclusive_group(required=True); mode.add_argument("--validate-only",action="store_true"); mode.add_argument("--session-index",type=int); mode.add_argument("--finalize",action="store_true"); p.add_argument("--control-replications",type=int,default=10000); p.add_argument("--bootstrap-replications",type=int,default=10000); p.add_argument("--authorization-token"); a=p.parse_args(); root=a.root.resolve()
 if a.validate_only: print(json.dumps(preflight(root,a.event_store_dir),indent=2,sort_keys=True)); return 0
 if a.authorization_token!=AUTH: raise SystemExit("ABSTAIN_MISSING_EXPLICIT_P2A_AUTHORIZATION")
 spec=json.loads((root/"specs"/"bt2a_gate2_first_passage_v1.json").read_text())
 if not str(spec.get("status","")).startswith("FROZEN"): raise SystemExit("ABSTAIN_GATE2_SPEC_NOT_FROZEN")
 if a.output_dir is None: raise SystemExit("--output-dir required")
 result=finalize(root,a.output_dir,a.bootstrap_replications) if a.finalize else run_session(root,a.data_dir,a.event_store_dir,a.output_dir,a.session_index,a.control_replications); print(json.dumps({k:v for k,v in result.items() if k not in {"cells","primary_family"}},indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
