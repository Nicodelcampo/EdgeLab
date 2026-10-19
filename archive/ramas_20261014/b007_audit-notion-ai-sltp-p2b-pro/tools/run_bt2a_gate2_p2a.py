#!/usr/bin/env python3
"""Checkpointed, authorization-gated BT2A Gate-2 first-passage runner."""
from __future__ import annotations
import argparse,hashlib,importlib.metadata,json,os,platform,re,subprocess
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_all5 import _context,_end,_labels,_start
from edgelab.research.bt2_gate1_outcomes import _sample_without_own,build_path_cache,chicago_bin30
from edgelab.research.bt2a_event_store import validate_event_checkpoint,verify_file_sha256
from edgelab.research.bt2a_gate2_first_passage import first_passage_scores_fast,holm_adjust,horizon_endpoints,next_barrier_touch_indices,summarize_scores,wild_cluster_test
from edgelab.research.bt2a_p2a_freeze import classify_mechanism,validate_canonical_event_store,validate_p2a_session_checkpoint
AUTH="AUTHORIZE_BT2A_P2A_POST_OUTCOME_DIAGNOSTIC"; BARRIERS=(5,9,18,30); TICK_H=(25,50,100,250); CLOCK_H=(5,30,120); BASE_SEED=20260821
FROZEN_SPEC_PAYLOAD_SHA256="176ca3e0c37f44823bfe5f8cf64849b55dcf12b5114d930d5ec8776c1566468c"
FROZEN_LOCK_SHA256="0cb96d720376a3d37cbfaaa94a3dda4d078d4d27206b47077a4cc0b276efaf1f"
def canonical(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def array_sha(v):
 a=np.ascontiguousarray(v); h=hashlib.sha256(); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.view(np.uint8)); return h.hexdigest()
def atomic(path,v):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+"\n"); os.replace(tmp,path)
def seed(label,purpose): return int.from_bytes(hashlib.sha256(f"{BASE_SEED}|{label}|{purpose}".encode()).digest()[:8],"little")%(2**32-1)
def checkpoint(out,index): return Path(out)/"checkpoints"/f"session_{int(index):03d}.json"
def map_indices(events,sequence,ts,price):
 src=np.asarray([int(e["fill_source_row"]) for e in events]); pos=np.searchsorted(sequence,src)
 if np.any(pos>=len(sequence)) or np.any(sequence[pos]!=src): raise RuntimeError("fill_source_row absent")
 for e,i in zip(events,pos):
  if int(ts[i])!=int(e["fill_ts_utc_ns"]) or int(price[i])!=int(e["fill_price_ticks"]): raise RuntimeError(f"fill identity mismatch: {e['event_id']}")
 return pos.astype(np.int64)
def sample_nrand(abs_idx,ts,cache,replications,random_seed):
 candidates=np.flatnonzero(cache.eligible); bins=chicago_bin30(ts[candidates]); event_bins=chicago_bin30(ts[abs_idx]); candidate_groups={k:candidates[(bins==k[0])&(cache.cap_driver[candidates]==k[1])] for k in sorted(set(zip(bins.tolist(),cache.cap_driver[candidates].tolist())))}; event_groups={k:np.flatnonzero((event_bins==k[0])&(cache.cap_driver[abs_idx]==k[1])) for k in sorted(set(zip(event_bins.tolist(),cache.cap_driver[abs_idx].tolist())))}
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
 abs_scores=scores(abs_idx,abs_dir); bt_scores=scores(bt_idx,bt_dir); long=scores(abs_idx,np.ones(len(abs_idx),dtype=np.int8)); short=scores(abs_idx,-np.ones(len(abs_idx),dtype=np.int8)); rng=np.random.default_rng(shuffle_seed); shuffle=np.array([np.where(rng.permutation(abs_dir)>0,long,short).mean() for _ in range(len(sampled))]); flat=scores(sampled.reshape(-1),np.tile(abs_dir,len(sampled))).reshape(sampled.shape); nrand=flat.mean(axis=1); a=summarize_scores(abs_scores); b=summarize_scores(bt_scores); n=control_summary(nrand); sh=control_summary(shuffle)
 return {"barrier_ticks":barrier,"horizon_type":"ticks" if tick_cap is not None else "seconds","horizon_value":tick_cap if tick_cap is not None else clock_cap,"K_ABS":a,"K_BT2":b,"N_RAND":n,"K_ABS_SHUFFLE":sh,"contrasts":{"K_ABS_minus_N_RAND":a["theta_fp"]-n["median_theta_fp"],"K_ABS_minus_K_ABS_SHUFFLE":a["theta_fp"]-sh["median_theta_fp"],"K_ABS_minus_K_BT2":a["theta_fp"]-b["theta_fp"]},"cap_driver_at_K_ABS":{name:int(np.sum(drivers[abs_idx]==name)) for name in ("ticks","clock","session")}}
def run_session(root,data_dir,event_store,out,index,replications):
 registry,inputs,gate1=_context(root); row=registry["sessions"][int(index)]; contract=row["contract"]; session=row["cme_session_id"]; source=json.loads((Path(event_store)/"checkpoints"/f"session_{int(index):03d}.json").read_text()); events=validate_event_checkpoint(source,contract=contract,session=session,sample_registry_sha256=registry["registry_payload_sha256"],input_registry_sha256=inputs["registry_payload_sha256"]); abs_events=[e for e in events if e["arm"]=="K_ABS"]; bt_events=[e for e in events if e["arm"]=="K_BT2"]
 parquet=Path(data_dir)/inputs["contracts"][contract]["parquet_file"]; verify_file_sha256(parquet,inputs["contracts"][contract]["parquet_sha256"]); ticks=load_canonical_parquet(parquet,contract=contract,start_utc_ns=_start(session),end_utc_ns=_end(session),instrument="GC"); sessions=_labels(ticks.ts_ns)
 if set(sessions.tolist())!={session}: raise RuntimeError("foreign session label")
 abs_idx=map_indices(abs_events,ticks.sequence,ticks.ts_ns,ticks.price_ticks); bt_idx=map_indices(bt_events,ticks.sequence,ticks.ts_ns,ticks.price_ticks); abs_dir=np.asarray([e["direction"] for e in abs_events],dtype=np.int8); bt_dir=np.asarray([e["direction"] for e in bt_events],dtype=np.int8); cache=build_path_cache(ticks.ts_ns,ticks.price_ticks,sessions,tick_cap=int(gate1["horizon"]["tick_cap"]),clock_cap_seconds=int(gate1["horizon"]["clock_cap_seconds"]))
 if np.any(~cache.eligible[abs_idx]) or np.any(~cache.eligible[bt_idx]): raise RuntimeError("Gate1-ineligible event")
 sampled=sample_nrand(abs_idx,ticks.ts_ns,cache,replications,seed(session,"nrand")); cells=[]
 for barrier in BARRIERS:
  touches=next_barrier_touch_indices(ticks.price_ticks,sessions,barrier_ticks=barrier)
  for horizon in TICK_H: cells.append(score_cell(ticks.price_ticks,ticks.ts_ns,sessions,abs_idx,abs_dir,bt_idx,bt_dir,sampled,touches,barrier,horizon,None,seed(session,f"shuffle|{barrier}|ticks|{horizon}")))
  for horizon in CLOCK_H: cells.append(score_cell(ticks.price_ticks,ticks.ts_ns,sessions,abs_idx,abs_dir,bt_idx,bt_dir,sampled,touches,barrier,None,horizon,seed(session,f"shuffle|{barrier}|seconds|{horizon}")))
 spec_sha=canonical(load_spec(root)); result={"schema":"bt2a_gate2_p2a_session_v1","status":"COMPLETE_POST_OUTCOME_DIAGNOSTIC_SESSION","session_index":int(index),"contract":contract,"cme_session":session,"spec_payload_sha256":spec_sha,"source_event_checkpoint_sha256":canonical(source),"n_K_ABS":len(abs_events),"n_K_BT2":len(bt_events),"control_replications":replications,"nrand_anchor_matrix_sha256":array_sha(sampled),"cells":cells,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False}; result["payload_sha256"]=canonical(result); atomic(checkpoint(out,index),result); return result
def aggregate(rows,horizon_type,horizons,replications):
 out=[]
 for barrier in BARRIERS:
  for horizon in horizons:
   cells=[next(c for c in row["cells"] if c["barrier_ticks"]==barrier and c["horizon_type"]==horizon_type and c["horizon_value"]==horizon) for row in rows]; contrasts={}
   for name in ("K_ABS_minus_N_RAND","K_ABS_minus_K_ABS_SHUFFLE","K_ABS_minus_K_BT2"): contrasts[name]=wild_cluster_test([c["contrasts"][name] for c in cells],replications=replications,seed=seed(f"{horizon_type}|{barrier}|{horizon}",name))
   out.append({"barrier_ticks":barrier,"horizon_ticks" if horizon_type=="ticks" else "horizon_seconds":horizon,"n_sessions":len(cells),"contrasts":contrasts})
 return out
def load_spec(root):
 path=Path(root)/"specs"/"bt2a_gate2_first_passage_v1.json"
 if not path.is_file(): raise RuntimeError("missing Gate2 spec")
 value=json.loads(path.read_text())
 if not isinstance(value,dict): raise RuntimeError("Gate2 spec must be a JSON object")
 return value

def frozen_constant_checks(spec):
 p2a=spec.get("p2a",{}); inference=spec.get("inference",{}); score=p2a.get("score",{}); firewall=spec.get("firewall",{}); freeze=spec.get("freeze",{}); decision=spec.get("decision_rule",{}); input_spec=spec.get("input",{})
 return {
  "spec_payload_sha256":canonical(spec)==FROZEN_SPEC_PAYLOAD_SHA256,
  "status":spec.get("status")=="FROZEN_POST_OUTCOME_DIAGNOSTIC",
  "barriers":tuple(p2a.get("barriers_ticks",()))==BARRIERS,
  "tick_horizons":tuple(p2a.get("primary_horizons_ticks",()))==TICK_H,
  "clock_horizons":tuple(p2a.get("secondary_horizons_seconds",()))==CLOCK_H,
  "diagnostic_ceiling":p2a.get("diagnostic_ceiling")=={"ticks":2000,"seconds":900},
  "outcomes":tuple(p2a.get("outcomes",()))==("TP_FIRST","SL_FIRST","TIMEOUT"),
  "score":score=={"TP_FIRST":1,"SL_FIRST":-1,"TIMEOUT":0},
  "timeout_included":p2a.get("timeout_included") is True,
  "aggregation":p2a.get("aggregation")=="EQUAL_CME_SESSION_WEIGHT",
  "base_seed":int(inference.get("base_seed",-1))==BASE_SEED,
  "seed_derivation":inference.get("seed_derivation")=="SHA256(BASE_SEED|label|purpose)[0:8]_LITTLE_ENDIAN_MOD_2^32_MINUS_1",
  "control_replications":int(p2a.get("control_replications",-1))==10000,
  "bootstrap_replications":int(inference.get("bootstrap_replications",-1))==10000,
  "holm_family":inference.get("multiplicity")=="HOLM_OVER_16_PRIMARY_BARRIER_HORIZON_CELLS",
  "inference_unit":inference.get("unit")=="CME_SESSION",
  "inference_method":inference.get("method")=="WEBB_SIX_POINT_WILD_CLUSTER_BY_CME_SESSION",
  "confidence":float(inference.get("confidence",-1))==0.95,
  "alternative":inference.get("alternative")=="TWO_SIDED",
  "arms":tuple(spec.get("arms",()))==("K_ABS","N_RAND","K_ABS_SHUFFLE","K_BT2"),
  "primary_contrast":spec.get("contrasts",{}).get("primary")=="K_ABS_MINUS_N_RAND",
  "secondary_contrasts":tuple(spec.get("contrasts",{}).get("secondary",()))==("K_ABS_MINUS_K_ABS_SHUFFLE","K_ABS_MINUS_K_BT2"),
  "event_source":input_spec.get("event_source")=="CANONICAL_EVENT_STORE_234_STRICT_PY312",
  "session_boundary":input_spec.get("session_boundary")=="HARD_CME",
  "fill":input_spec.get("fill")=="FIRST_ROW_STRICTLY_AFTER_SIGNAL",
  "authorization_token":freeze.get("execution_authorization_token")==AUTH,
  "execution_authorization_separate":freeze.get("execution_authorization_separate") is True,
  "edge_forbidden":firewall.get("edge_declaration_allowed") is False and decision.get("edge_declaration_allowed") is False,
  "promotion_forbidden":firewall.get("promotion_allowed") is False and decision.get("promotion_allowed") is False,
  "winner_selection_forbidden":decision.get("cross_cell_winner_selection_allowed") is False,
 }

def runtime_environment_checks(root,spec):
 lock=Path(root)/"requirements"/"core-bridge-dev.lock"; expected_python=str(spec.get("canonical_event_store",{}).get("python")); checks={"python":platform.python_version()==expected_python,"lock_exists":lock.is_file()}
 if not lock.is_file(): return checks
 checks["lock_sha256"]=hashlib.sha256(lock.read_bytes()).hexdigest()==FROZEN_LOCK_SHA256
 expected={}
 for line in lock.read_text().splitlines():
  match=re.match(r"^([A-Za-z0-9_.-]+)==([^ \\]+)",line)
  if match: expected[match.group(1).lower().replace("_","-")]=match.group(2)
 mismatches={}
 for name,wanted in expected.items():
  try: actual=importlib.metadata.version(name)
  except importlib.metadata.PackageNotFoundError: actual=None
  if actual!=wanted: mismatches[name]={"expected":wanted,"actual":actual}
 checks["locked_packages"] = len(expected)==30 and not mismatches
 checks["locked_package_count"] = len(expected)==30
 return checks

def execution_git_checks(root,spec):
 def run(*args): return subprocess.run(args,cwd=root,text=True,capture_output=True)
 head=run("git","rev-parse","HEAD"); branch=run("git","branch","--show-current"); status=run("git","status","--porcelain")
 expected_branch=str(spec.get("freeze",{}).get("branch"))
 return {"git_available":head.returncode==0,"branch":branch.returncode==0 and branch.stdout.strip()==expected_branch,"worktree_clean":status.returncode==0 and not status.stdout.strip()}

def finalize(root,event_store,out,replications):
 registry,_,_=_context(root); rows=[]; spec=load_spec(root); spec_sha=canonical(spec); validations=[]
 for index,registry_row in enumerate(registry["sessions"]):
  path=checkpoint(out,index)
  if not path.is_file(): raise RuntimeError(f"missing {path.name}")
  source_path=Path(event_store)/"checkpoints"/f"session_{index:03d}.json"
  source=json.loads(source_path.read_text()); value=json.loads(path.read_text())
  validation=validate_p2a_session_checkpoint(value,expected_index=index,expected_contract=str(registry_row["contract"]),expected_session=str(registry_row["cme_session_id"]),expected_spec_payload_sha256=spec_sha,expected_source_event_checkpoint_sha256=canonical(source),expected_control_replications=int(spec["p2a"]["control_replications"]),barriers=BARRIERS,tick_horizons=TICK_H,clock_horizons=CLOCK_H)
  source_abs=sum(e.get("arm")=="K_ABS" for e in source.get("events",[])); source_bt2=sum(e.get("arm")=="K_BT2" for e in source.get("events",[]))
  if value.get("n_K_ABS")!=source_abs or value.get("n_K_BT2")!=source_bt2: validation["errors"].append("event arm count mismatch"); validation["ready"]=False
  if not validation["ready"]: raise RuntimeError(f"invalid P2-A checkpoint {path.name}: {validation['errors'][:10]}")
  validations.append({"session_index":index,"ready":True}); rows.append(value)
 primary=aggregate(rows,"ticks",TICK_H,replications); adjusted=holm_adjust([x["contrasts"]["K_ABS_minus_N_RAND"]["p_two_sided"] for x in primary])
 for cell,p in zip(primary,adjusted): cell["contrasts"]["K_ABS_minus_N_RAND"]["p_holm_16"]=p
 secondary=aggregate(rows,"seconds",CLOCK_H,replications); decision=classify_mechanism(primary,spec); result={"schema":"bt2a_gate2_p2a_result_v1","status":"COMPLETE_P2A_POST_OUTCOME_DIAGNOSTIC","n_sessions":len(rows),"primary_family":primary,"secondary_clock_family":secondary,"decision":decision,"p2a_checkpoint_validation":{"validated":len(validations),"failed":0},"spec_payload_sha256":spec_sha,"canonical_event_store_payload_sha256":spec["canonical_event_store"]["events_payload_sha256"],"multiplicity":"HOLM_OVER_16_PRIMARY_CELLS; SECONDARY_CLOCK_UNADJUSTED_DESCRIPTIVE","unit":"CME_SESSION","timeout_in_estimand":True,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False,"promotion_eligible":False}; result["payload_sha256"]=canonical(result); atomic(Path(out)/"gate2_p2a_result.json",result); return result

def preflight(root,event_store):
 registry,_,_=_context(root); spec=load_spec(root); missing=[i for i in range(len(registry["sessions"])) if not (Path(event_store)/"checkpoints"/f"session_{i:03d}.json").is_file()]; constants=frozen_constant_checks(spec); environment=runtime_environment_checks(root,spec); git_checks=execution_git_checks(root,spec); identity=validate_canonical_event_store(event_store,spec); ready=not missing and all(constants.values()) and all(environment.values()) and all(git_checks.values()) and identity["ready"]
 return {"status":"PASS_READY_FOR_AUTHORIZATION" if ready else "NOT_READY","spec_status":spec.get("status"),"spec_payload_sha256":canonical(spec),"frozen_constants":constants,"runtime_environment":environment,"execution_git":git_checks,"event_store_identity":identity,"n_expected_sessions":len(registry["sessions"]),"n_missing_event_checkpoints":len(missing),"missing_event_checkpoint_indices":missing[:50],"outcomes_opened":False}

def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--data-dir",type=Path); p.add_argument("--event-store-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path); mode=p.add_mutually_exclusive_group(required=True); mode.add_argument("--validate-only",action="store_true"); mode.add_argument("--session-index",type=int); mode.add_argument("--finalize",action="store_true"); p.add_argument("--control-replications",type=int,default=10000); p.add_argument("--bootstrap-replications",type=int,default=10000); p.add_argument("--authorization-token"); a=p.parse_args(); root=a.root.resolve(); readiness=preflight(root,a.event_store_dir)
 if a.validate_only: print(json.dumps(readiness,indent=2,sort_keys=True)); return 0 if readiness["status"]=="PASS_READY_FOR_AUTHORIZATION" else 2
 if a.authorization_token!=AUTH: raise SystemExit("ABSTAIN_MISSING_EXPLICIT_P2A_AUTHORIZATION")
 if readiness["status"]!="PASS_READY_FOR_AUTHORIZATION": raise SystemExit("ABSTAIN_P2A_PREFLIGHT_NOT_READY")
 spec=load_spec(root); expected_control=int(spec["p2a"]["control_replications"]); expected_bootstrap=int(spec["inference"]["bootstrap_replications"])
 if a.control_replications!=expected_control or a.bootstrap_replications!=expected_bootstrap: raise SystemExit("ABSTAIN_FROZEN_REPLICATION_COUNT_MISMATCH")
 if a.output_dir is None: raise SystemExit("--output-dir required")
 if a.session_index is not None:
  registry,_,_=_context(root)
  if not 0<=a.session_index<len(registry["sessions"]): raise SystemExit("ABSTAIN_SESSION_INDEX_OUT_OF_RANGE")
 if not a.finalize and a.data_dir is None: raise SystemExit("--data-dir required for session run")
 result=finalize(root,a.event_store_dir,a.output_dir,a.bootstrap_replications) if a.finalize else run_session(root,a.data_dir,a.event_store_dir,a.output_dir,a.session_index,a.control_replications); print(json.dumps({k:v for k,v in result.items() if k not in {"cells","primary_family","secondary_clock_family"}},indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
