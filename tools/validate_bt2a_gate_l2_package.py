#!/usr/bin/env python3
"""Fail-closed target-free validator for a local BT2A Gate-L2 package."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from typing import Any
import pandas as pd
from edgelab.research.bt2a_gate_l2 import attach_context_strict,context_width_correlation,validate_context_labels,validate_run_identity
REQUIRED_FILES=("run_manifest.json","gate_l2_context_model.json","gate_l2_target_free_report.json","gate_l2_context_labels.parquet")
def file_sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  while chunk:=f.read(1<<20): h.update(chunk)
 return h.hexdigest()
def read_json(path):
 value=json.loads(Path(path).read_text())
 if not isinstance(value,dict): raise ValueError("JSON object required")
 return value
def atomic_json(path,value):
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n"); os.replace(tmp,path)
def load_table(path):
 path=Path(path)
 if path.suffix.lower()==".parquet": return pd.read_parquet(path)
 if path.suffix.lower() in {".jsonl",".ndjson"}: return pd.read_json(path,lines=True)
 if path.suffix.lower()==".csv": return pd.read_csv(path)
 raise ValueError("unsupported event table")
def declared_artifact_hashes(manifest:dict[str,Any]):
 out={}
 for key in ("artifact_sha256","artifact_hashes"):
  value=manifest.get(key)
  if isinstance(value,dict):
   for path,digest in value.items():
    if isinstance(digest,str): out[str(path).replace("\\","/")]=digest.lower()
 artifacts=manifest.get("artifacts")
 if isinstance(artifacts,dict):
  for name,value in artifacts.items():
   if isinstance(value,dict) and isinstance(value.get("sha256"),str): out[str(value.get("relative_path") or value.get("path") or name).replace("\\","/")]=value["sha256"].lower()
   elif isinstance(value,str) and len(value)==64: out[str(name).replace("\\","/")]=value.lower()
 inventory=manifest.get("artifact_inventory")
 if isinstance(inventory,list):
  for item in inventory:
   if isinstance(item,dict) and isinstance(item.get("sha256"),str):
    path=item.get("relative_path") or item.get("path") or item.get("name")
    if path: out[str(path).replace("\\","/")]=item["sha256"].lower()
 return out
def match_declared_hash(declared,relative):
 relative=relative.replace("\\","/")
 if relative in declared: return declared[relative]
 matches={digest for path,digest in declared.items() if Path(path).name==Path(relative).name}; return next(iter(matches)) if len(matches)==1 else None
def validate_package(package_dir,*,event_store,coverage_min,minimum_sessions_per_group,max_abs_context_width_correlation):
 package_dir=Path(package_dir).resolve(); missing=[x for x in REQUIRED_FILES if not (package_dir/x).is_file()]; features=sorted((package_dir/"features").glob("*.parquet"))
 if not features: missing.append("features/*.parquet")
 inventory=[{"relative_path":str(p.relative_to(package_dir)).replace("\\","/"),"bytes":p.stat().st_size,"sha256":file_sha256(p)} for p in sorted(x for x in package_dir.rglob("*") if x.is_file())]; base={"schema":"bt2a_gate_l2_package_readiness_v1","package_dir":str(package_dir),"required_files":list(REQUIRED_FILES)+["features/*.parquet"],"missing_required_files":missing,"inventory":inventory,"CAMPAIGN_OUTCOMES_OPENED":False,"EDGE_DECLARED":False}
 if missing: base.update({"status":"ABSTAIN_MISSING_REQUIRED_ARTIFACTS","ready_for_outcomes":False}); return base
 manifest=read_json(package_dir/"run_manifest.json"); model=read_json(package_dir/"gate_l2_context_model.json"); report=read_json(package_dir/"gate_l2_target_free_report.json"); contexts=pd.read_parquet(package_dir/"gate_l2_context_labels.parquet"); identity=validate_run_identity(manifest,model,report); declared=declared_artifact_hashes(manifest); checks={}
 for path in [package_dir/"gate_l2_context_model.json",package_dir/"gate_l2_target_free_report.json",package_dir/"gate_l2_context_labels.parquet",*features]:
  relative=str(path.relative_to(package_dir)).replace("\\","/"); actual=file_sha256(path); expected=match_declared_hash(declared,relative); checks[relative]={"declared_sha256":expected,"actual_sha256":actual,"matches":bool(expected and expected==actual)}
 hashes_ok=bool(checks) and all(x["matches"] for x in checks.values()); readiness=validate_context_labels(contexts,coverage_min=coverage_min,minimum_sessions_per_group=minimum_sessions_per_group).to_dict(); join=None; width=None; event_identity_ok=False; event_sessions_ok=False
 if event_store is not None:
  events=load_table(event_store)
  if "event_source_row" not in events and "signal_source_row" in events: events=events.rename(columns={"signal_source_row":"event_source_row"})
  joined,join=attach_context_strict(events,contexts); ok=joined.context_as_of_ok.astype(bool); event_identity_ok=bool(join["coverage"]>=coverage_min and joined.loc[ok,"context_available_source_row"].astype(int).lt(joined.loc[ok,"event_source_row"].astype(int)).all()); joined_ok=joined[ok]; sessions={g:int(joined_ok.loc[joined_ok.context_group==g,["contract","cme_session"]].drop_duplicates().shape[0]) for g in ("G-operable","G-stress")}; event_sessions_ok=all(n>=minimum_sessions_per_group for n in sessions.values()); join.update({"sessions_by_group":sessions,"minimum_sessions_per_group":minimum_sessions_per_group,"minimum_sessions_ok":event_sessions_ok})
  if "zone_width_ticks" in joined:
   width=context_width_correlation(joined)
   if width["correlation"] is not None: width["passes"]=bool(abs(float(width["correlation"]))<max_abs_context_width_correlation)
 ready=bool(identity["identity_ready"] and hashes_ok and readiness["ready_for_outcomes"] and event_store is not None and event_identity_ok and event_sessions_ok and width is not None and width["passes"]); base.update({"status":"PASS_TARGET_FREE_READY" if ready else "ABSTAIN_TARGET_FREE_GATES","identity":identity,"artifact_hashes_ok":hashes_ok,"artifact_hash_checks":checks,"labels":readiness,"event_store":str(Path(event_store).resolve()) if event_store is not None else None,"strict_join":join,"event_identity_ok":event_identity_ok,"event_sessions_ok":event_sessions_ok,"context_width":width,"thresholds":{"coverage_min":coverage_min,"minimum_sessions_per_group":minimum_sessions_per_group,"max_abs_context_width_correlation":max_abs_context_width_correlation},"ready_for_outcomes":ready}); return base
def main():
 p=argparse.ArgumentParser(); p.add_argument("--package-dir",type=Path,required=True); p.add_argument("--event-store",type=Path); p.add_argument("--output",type=Path,required=True); p.add_argument("--coverage-min",type=float,default=.99); p.add_argument("--minimum-sessions-per-group",type=int,default=40); p.add_argument("--max-abs-context-width-correlation",type=float,default=.20); a=p.parse_args(); result=validate_package(a.package_dir,event_store=a.event_store,coverage_min=a.coverage_min,minimum_sessions_per_group=a.minimum_sessions_per_group,max_abs_context_width_correlation=a.max_abs_context_width_correlation); atomic_json(a.output,result); print(json.dumps({"status":result["status"],"ready_for_outcomes":result["ready_for_outcomes"],"output":str(a.output)},indent=2,sort_keys=True)); return 0 if result["ready_for_outcomes"] else 2
if __name__=="__main__": raise SystemExit(main())
