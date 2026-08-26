#!/usr/bin/env python3
"""Authorization-gated P2-B runner over the canonical Gate-1 event population."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from edgelab.research.all5_runtime.ticks import load_canonical_parquet
from edgelab.research.bt2_gate1_all5 import _context,_end,_labels,_start
from edgelab.research.bt2a_execution import scenarios,simulate
from edgelab.research.bt2a_gate2_first_passage import wild_cluster_test

AUTH="AUTHORIZE_BT2A_P2B_POST_OUTCOME_DIAGNOSTIC"
BARRIERS=(5,9,18,30); TIME_STOPS=(5,30,120); ARMS=("K_ABS","K_BT2")
def seed(label): return int.from_bytes(hashlib.sha256(label.encode()).digest()[:8],"little")%(2**32-1)
def canonical(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def atomic(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"); os.replace(tmp,path)
def checkpoint(out,index): return Path(out)/"checkpoints"/f"session_{int(index):03d}.json"

def run_session(root,data_dir,event_store,out,index,commission,tick_value,commission_source):
 registry,inputs,_=_context(root); row=registry["sessions"][int(index)]; contract=row["contract"]; session=row["cme_session_id"]
 source=json.loads((Path(event_store)/"checkpoints"/f"session_{int(index):03d}.json").read_text())
 if source.get("status")!="COMPLETE" or source.get("cme_session")!=session: raise RuntimeError("event checkpoint mismatch")
 ticks=load_canonical_parquet(Path(data_dir)/inputs["contracts"][contract]["parquet_file"],contract=contract,start_utc_ns=_start(session),end_utc_ns=_end(session),instrument="GC"); labels=_labels(ticks.ts_ns)
 if ticks.bid_ticks is None or ticks.ask_ticks is None: raise RuntimeError("P2-B requires bid/ask")
 costs=scenarios(commission); cells=[]
 for arm in ARMS:
  events=[e for e in source["events"] if e["arm"]==arm]
  if not events: raise RuntimeError(f"missing observed arm {arm}")
  for barrier in BARRIERS:
   for seconds in TIME_STOPS:
    signals=[{"event_id":e["event_id"],"signal_ts_utc_ns":e["signal_ts_utc_ns"],"signal_source_row":e["signal_source_row"],"direction":e["direction"],"target_ticks":barrier,"stop_ticks":barrier,"time_stop_seconds":seconds} for e in events]
    for name,cost in costs.items():
     result=simulate(signals,ticks.ts_ns,ticks.sequence,ticks.price_ticks,ticks.bid_ticks,ticks.ask_ticks,labels,cost=cost,tick_value_usd=tick_value,close_at_session_end=True)
     cells.append({"arm":arm,"barrier_ticks":barrier,"time_stop_seconds":seconds,"scenario":name,"summary":result["summary"],"trades":result["trades"],"rejected":result["rejected"],"digest":result["digest"]})
 result={"schema":"bt2a_gate2_p2b_session_v1","status":"COMPLETE_POST_OUTCOME_DIAGNOSTIC_SESSION","session_index":int(index),"contract":contract,"cme_session":session,"source_event_checkpoint_sha256":canonical(source),"commission_per_side_usd":float(commission),"commission_source":commission_source,"tick_value_usd":float(tick_value),"cells":cells,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False}; result["payload_sha256"]=canonical(result); atomic(checkpoint(out,index),result); return result

def finalize(root,out,bootstrap):
 registry,_,_=_context(root); rows=[]
 for i in range(len(registry["sessions"])):
  path=checkpoint(out,i)
  if not path.is_file(): raise RuntimeError(f"missing {path.name}")
  rows.append(json.loads(path.read_text()))
 sources={(r["commission_per_side_usd"],r["commission_source"],r["tick_value_usd"]) for r in rows}
 if len(sources)!=1: raise RuntimeError("mixed cost identity")
 surfaces=[]
 for arm in ARMS:
  for barrier in BARRIERS:
   for seconds in TIME_STOPS:
    for scenario in ("ideal","base","adverso","severo"):
     cells=[next(c for c in row["cells"] if c["arm"]==arm and c["barrier_ticks"]==barrier and c["time_stop_seconds"]==seconds and c["scenario"]==scenario) for row in rows]
     per_signal=[c["summary"]["mean_net_ticks_per_eligible_signal"] for c in cells]; per_trade=[x for x in (c["summary"]["mean_net_ticks_per_trade"] for c in cells) if x is not None]
     trade_inference=wild_cluster_test(per_trade,replications=bootstrap,seed=seed(f"trade|{arm}|{barrier}|{seconds}|{scenario}")) if len(per_trade)>=2 else {"status":"INSUFFICIENT_TRADE_SESSIONS","n_sessions":len(per_trade)}
     surfaces.append({"arm":arm,"barrier_ticks":barrier,"time_stop_seconds":seconds,"scenario":scenario,"n_sessions":len(cells),"net_ticks_per_eligible_signal":wild_cluster_test(per_signal,replications=bootstrap,seed=seed(f"signal|{arm}|{barrier}|{seconds}|{scenario}")),"net_ticks_per_trade":trade_inference,"total_trades":sum(c["summary"]["n_trades"] for c in cells),"total_rejected":sum(c["summary"]["n_rejected"] for c in cells)})
 commission,commission_source,tick_value=list(sources)[0]
 result={"schema":"bt2a_gate2_p2b_result_v1","status":"COMPLETE_P2B_POST_OUTCOME_DIAGNOSTIC","n_sessions":len(rows),"cost_identity":{"commission_per_side_usd":commission,"commission_source":commission_source,"tick_value_usd":tick_value},"surfaces":surfaces,"unit":"CME_SESSION","one_position":True,"first_executable_signal_wins":True,"CAMPAIGN_OUTCOMES_OPENED":True,"EDGE_DECLARED":False,"confirmatory_eligible":False,"promotion_eligible":False}; result["payload_sha256"]=canonical(result); atomic(Path(out)/"gate2_p2b_result.json",result); return result

def preflight(root,event_store,commission,source,tick_value):
 registry,_,_=_context(root); missing=[i for i in range(len(registry["sessions"])) if not (Path(event_store)/"checkpoints"/f"session_{i:03d}.json").is_file()]; spec=Path(root)/"specs"/"bt2a_gate2_first_passage_v1.json"; status=json.loads(spec.read_text()).get("status") if spec.is_file() else "MISSING"
 return {"status":"PASS_READY_FOR_AUTHORIZATION" if not missing and str(status).startswith("FROZEN") and commission is not None and bool(source) and tick_value is not None else "NOT_READY","spec_status":status,"missing_event_checkpoints":len(missing),"commission_supplied":commission is not None,"commission_source_supplied":bool(source),"tick_value_supplied":tick_value is not None,"outcomes_opened":False}

def main():
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument("--data-dir",type=Path); p.add_argument("--event-store-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path); mode=p.add_mutually_exclusive_group(required=True); mode.add_argument("--validate-only",action="store_true"); mode.add_argument("--session-index",type=int); mode.add_argument("--finalize",action="store_true"); p.add_argument("--commission-per-side-usd",type=float); p.add_argument("--commission-source"); p.add_argument("--tick-value-usd",type=float); p.add_argument("--bootstrap-replications",type=int,default=10000); p.add_argument("--authorization-token"); a=p.parse_args(); root=a.root.resolve()
 if a.validate_only: print(json.dumps(preflight(root,a.event_store_dir,a.commission_per_side_usd,a.commission_source,a.tick_value_usd),indent=2,sort_keys=True)); return 0
 if a.authorization_token!=AUTH: raise SystemExit("ABSTAIN_MISSING_EXPLICIT_P2B_AUTHORIZATION")
 spec=json.loads((root/"specs"/"bt2a_gate2_first_passage_v1.json").read_text())
 if not str(spec.get("status","")).startswith("FROZEN"): raise SystemExit("ABSTAIN_GATE2_SPEC_NOT_FROZEN")
 if a.output_dir is None or a.commission_per_side_usd is None or not a.commission_source or a.tick_value_usd is None: raise SystemExit("ABSTAIN_COST_IDENTITY_INCOMPLETE")
 result=finalize(root,a.output_dir,a.bootstrap_replications) if a.finalize else run_session(root,a.data_dir,a.event_store_dir,a.output_dir,a.session_index,a.commission_per_side_usd,a.tick_value_usd,a.commission_source); print(json.dumps({k:v for k,v in result.items() if k not in {"cells","surfaces"}},indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
