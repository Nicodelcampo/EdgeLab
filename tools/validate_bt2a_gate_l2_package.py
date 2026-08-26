#!/usr/bin/env python3
"""Fail-closed target-free validator for a local BT2A Gate-L2 package."""
from __future__ import annotations
import argparse,hashlib,json,os
from pathlib import Path
from typing import Any
import pandas as pd
from edgelab.research.bt2a_gate_l2 import attach_context_strict,context_width_correlation,validate_context_labels,validate_run_identity

REQUIRED_FILES=("run_manifest.json","gate_l2_context_model.json","gate_l2_target_free_report.json","gate_l2_context_labels.parquet")
def file_sha256(path:Path):
 h=hashlib.sha256()
 with path.open("rb") as handle:
  while chunk:=handle.read(1024*1024): h.update(chunk)
 return h.hexdigest()
def read_json(path:Path):
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError(f"{path.name} must contain a JSON object")
 return value
def atomic_json(path:Path,value):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8"); os.replace(tmp,path)
def load_table(path:Path):
 suffix=path.suffix.lower()
 if suffix==".parquet": return pd.read_parquet(path)
 if suffix in {".jsonl",".ndjson"}: return pd.read_json(path,lines=True)
 if suffix==".csv": return pd.read_csv(path)
 raise ValueError(f"unsupported event table format: {path}")

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
   if isinstance(value,dict) and isinstance(value.get("sha256"),str):
    path=value.get("relative_path") or value.get("path") or name; out[str(path).replace("\\","/")]=value["sha256"].lower()
   elif isinstance(value,str) and len(value)==64: out[str(name).replace("\\","/")]=value.lower()
 inventory=manifest.get("artifact_inventory")
 if isinstance(inventory,list):
  for item in inventory:
   if not isinstance(item,dict) or not isinstance(item.get("sha256"),str): continue
   path=item.get("relative_path") or item.get("path") or item.get("name")
   if path: out[str(path).replace("\\","/")]=item["sha256"].lower()
 return out

def match_declared_hash(declared,relative_path):
 relative_path=relative_path.replace("\\","/")
 if relative_path in declared: return declared[relative_path]
 basename=Path(relative_path).name; matches={digest for path,digest in declared.items() if Path(path).name==basename}
 return next(iter(matches)) if len(matches)==1 else None

def validate_package(package_dir:Path,*,event_store:Path|None,coverage_min:float,minimum_sessions_per_group:int,max_abs_context_width_correlation:float):
 package_dir=package_dir.resolve(); missing=[name for name in REQUIRED_FILES if not (package_dir/name).is_file()]; feature_files=sorted((package_dir/"features").glob("*.parquet"))
 if not feature_files: missing.append("features/*.parquet")
 inventory=[{"relative_path":str(path.relative_to(package_dir)).replace("\\","/"),"bytes":path.stat().st_size,"sha256":file_sha256(path)} for path in sorted(p for p in package_dir.rglob("*") if p.is_file())]
 base={"schema":"bt2a_gate_l2_package_readiness_v1","package_dir":str(package_dir),"required_files":list(REQUIRED_FILES)+["features/*.parquet"],"missing_required_files":missing,"inventory":inventory,"CAMPAIGN_OUTCOMES_OPENED":False,"EDGE_DECLARED":False}
 if missing:
  base.update({"status":"ABSTAIN_MISSING_REQUIRED_ARTIFACTS","ready_for_outcomes":False}); return base
 manifest=read_json(package_dir/"run_manifest.json"); model=read_json(package_dir/"gate_l2_context_model.json"); target_free_report=read_json(package_dir/"gate_l2_target_free_report.json"); contexts=pd.read_parquet(package_dir/"gate_l2_context_labels.parquet")
 identity=validate_run_identity(manifest,model,target_free_report); declared=declared_artifact_hashes(manifest)
 hash_targets=[package_dir/"gate_l2_context_model.json",package_dir/"gate_l2_target_free_report.json",package_dir/"gate_l2_context_labels.parquet",*feature_files]; hash_checks={}
 for path in hash_targets:
  relative=str(path.relative_to(package_dir)).replace("\\","/"); actual=file_sha256(path); expected=match_declared_hash(declared,relative); hash_checks[relative]={"declared_sha256":expected,"actual_sha256":actual,"matches":bool(expected and expected==actual)}
 artifact_hashes_ok=bool(hash_checks) and all(item["matches"] for item in hash_checks.values())
 readiness=validate_context_labels(contexts,coverage_min=coverage_min,minimum_sessions_per_group=minimum_sessions_per_group).to_dict()
 join_report=None; width_report=None; event_identity_ok=False; event_sessions_ok=False
 if event_store is not None:
  events=load_table(event_store)
  if "event_source_row" not in events.columns and "signal_source_row" in events.columns: events=events.rename(columns={"signal_source_row":"event_source_row"})
  joined,join_report=attach_context_strict(events,contexts); ok=joined.context_as_of_ok.astype(bool)
  event_identity_ok=bool(join_report["coverage"]>=float(coverage_min) and joined.loc[ok,"context_available_source_row"].astype(int).lt(joined.loc[ok,"event_source_row"].astype(int)).all())
  joined_ok=joined[ok]; joined_sessions={group:int(joined_ok.loc[joined_ok.context_group==group,["contract","cme_session"]].drop_duplicates().shape[0]) for group in ("G-operable","G-stress")}; join_report["sessions_by_group"]=joined_sessions; join_report["minimum_sessions_per_group"]=int(minimum_sessions_per_group); event_sessions_ok=all(value>=int(minimum_sessions_per_group) for value in joined_sessions.values()); join_report["minimum_sessions_ok"]=event_sessions_ok
  if "zone_width_ticks" in joined.columns:
   width_report=context_width_correlation(joined)
   if width_report["correlation"]==width_report["correlation"]: width_report["passes"]=bool(abs(float(width_report["correlation"]))<float(max_abs_context_width_correlation))
 all_ready=bool(identity["identity_ready"] and artifact_hashes_ok and readiness["ready_for_outcomes"] and event_store is not None and event_identity_ok and event_sessions_ok and (width_report is not None and bool(width_report["passes"])))
 base.update({"status":"PASS_TARGET_FREE_READY" if all_ready else "ABSTAIN_TARGET_FREE_GATES","identity":identity,"artifact_hashes_ok":artifact_hashes_ok,"artifact_hash_checks":hash_checks,"labels":readiness,"event_store":str(event_store.resolve()) if event_store is not None else None,"strict_join":join_report,"event_identity_ok":event_identity_ok,"event_sessions_ok":event_sessions_ok,"context_width":width_report,"thresholds":{"coverage_min":float(coverage_min),"minimum_sessions_per_group":int(minimum_sessions_per_group),"max_abs_context_width_correlation":float(max_abs_context_width_correlation)},"ready_for_outcomes":all_ready}); return base

def parse_args():
 p=argparse.ArgumentParser(); p.add_argument("--package-dir",type=Path,required=True); p.add_argument("--event-store",type=Path); p.add_argument("--output",type=Path,required=True); p.add_argument("--coverage-min",type=float,default=.99); p.add_argument("--minimum-sessions-per-group",type=int,default=40); p.add_argument("--max-abs-context-width-correlation",type=float,default=.20); return p.parse_args()
def main():
 a=parse_args(); result=validate_package(a.package_dir,event_store=a.event_store,coverage_min=a.coverage_min,minimum_sessions_per_group=a.minimum_sessions_per_group,max_abs_context_width_correlation=a.max_abs_context_width_correlation); atomic_json(a.output,result); print(json.dumps({"status":result["status"],"ready_for_outcomes":result["ready_for_outcomes"],"output":str(a.output)},indent=2,sort_keys=True)); return 0 if result["ready_for_outcomes"] else 2
if __name__=="__main__": raise SystemExit(main())
