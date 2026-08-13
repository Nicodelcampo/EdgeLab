# -*- coding: utf-8 -*-
"""ZAMR-1 Z1 target-free builder. BigTrap2 defaults; no outcomes/P&L/holdout."""
from __future__ import annotations
import argparse, hashlib, json, resource, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from edgelab.bridge import bars as bars_mod, ticks as ticks_mod
from edgelab.bridge.indicators import bigtrap2
from edgelab.research.first_touch_census import session_date_ct
from edgelab.research.zamr1.parameter_dag import param_set_id, validate_param_set
from edgelab.research.zamr1.structural_contract import validate_structural_dataset

FRAMES=(5,10,25,50,100,200); CUTOFF=1782856800000000000

def file_hash(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for x in iter(lambda:f.read(1048576),b""): h.update(x)
 return h.hexdigest()
def obj_hash(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def payloads(lines):
 out={}
 for line in lines or []:
  seq,_iso,typ,raw=line.split("|",3); d={}
  for item in raw.split(";"):
   if "=" in item:
    k,v=item.split("=",1); d[k]=v
  out[int(seq)]=(typ,d)
 return out
def number(x):
 try:return float(x)
 except (TypeError,ValueError):return None
def price_tick(x,tick):
 x=number(x); return None if x is None else int(round(x/tick))
def git_state(root):
 head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
 dirty=bool(subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).strip())
 return head,dirty

def transform(result,bars,tk,sessions,rid,pid):
 parsed=payloads(result.get("csv_lines")); meta={}
 for z in result.get("zones") or []:
  cb=int(z["created_bar"]); created=int(bars.end_ns[cb]); ses=session_date_ct(created//1000000)
  if ses in sessions:
   meta[str(z["id"])]=(z,cb,created,ses,price_tick(z.get("bottom"),tk.tick_size),price_tick(z.get("top"),tk.tick_size),str(z.get("kind")))
 events=[]
 for ev in result.get("events") or []:
  zid=str(ev.get("zone_id")); typ=str(ev.get("type"))
  if zid not in meta or typ not in {"ZONE_CREATED","ZONE_TOUCHED","ZONE_INVALIDATED","ZONE_EXPIRED"}: continue
  z,cb,created,ses,lo,hi,side=meta[zid]; bar=int(ev["bar_index"]); ts=int(ev["ts_ns"])
  if ts>=CUTOFF: raise RuntimeError("FIREWALL event")
  vol=number(parsed.get(int(ev["seq"]),(typ,{}))[1].get("vol")); sk=f"{tk.instrument}|{tk.contract}|{ses}"; eid=str(ev["seq"])
  events.append({"event_key":f"{rid}|{eid}","session_key":sk,"instrument":tk.instrument,"contract":tk.contract,"session_date":ses,"indicator_id":"BigTrap2","indicator_version":"2.2","bar_spec":f"tick:{bars.param}","ticks_per_bar":int(bars.param),"param_set_id":pid,"source_run_id":rid,"event_id":eid,"zone_id":zid,"event_type":typ,"side":side,"event_time_ns":ts,"bar_end_ns":int(bars.end_ns[bar]),"available_at_ns":int(bars.end_ns[bar]),"anchor_price_tick":int(bars.close_t[cb]),"zone_lo_tick":lo,"zone_hi_tick":hi,"strength":vol,"aggressive_volume":vol,"bar_volume":float(bars.volume[cb]),"oracle_parity_status":"NOT_ESTABLISHED"})
 zones=[]
 for zid,(z,cb,created,ses,lo,hi,side) in meta.items():
  ended=None if z.get("ended_ms") is None else int(z["ended_ms"])*1000000
  if ended is not None and ended>=CUTOFF: raise RuntimeError("FIREWALL zone")
  ce=next((e for e in events if e["zone_id"]==zid and e["event_type"]=="ZONE_CREATED"),None); sk=f"{tk.instrument}|{tk.contract}|{ses}"
  zones.append({"zone_key":f"{rid}|{zid}","session_key":sk,"instrument":tk.instrument,"contract":tk.contract,"session_date":ses,"indicator_id":"BigTrap2","indicator_version":"2.2","bar_spec":f"tick:{bars.param}","ticks_per_bar":int(bars.param),"param_set_id":pid,"source_run_id":rid,"zone_id":zid,"side":side,"created_at_ns":created,"available_at_ns":created,"ended_at_ns":ended,"state":z.get("state"),"end_reason":z.get("end_reason"),"zone_lo_tick":lo,"zone_hi_tick":hi,"strength":None if ce is None else ce["strength"],"touch_count":int(z.get("touches") or 0),"oracle_parity_status":"NOT_ESTABLISHED"})
 return events,zones

def build(plan_path,data_root,out_dir,root):
 root=Path(root); plan=json.loads(Path(plan_path).read_text("utf-8")); contract=json.loads((root/"specs/zamr1_structural_contract_v0.json").read_text("utf-8")); head,dirty=git_state(root)
 if dirty: raise RuntimeError("ABSTAIN_PROVENANCE: dirty tree")
 if tuple(plan["bar_specs_ticks"])!=FRAMES or validate_param_set("BigTrap2",{}): raise RuntimeError("Z1 scope/defaults invalid")
 sessions=[s for src in plan["sources"] for s in src["selected_sessions"]]
 if len(sessions)!=len(set(sessions)) or not 20<=len(sessions)<=30: raise RuntimeError("need 20-30 unique sessions")
 pid=param_set_id("BigTrap2",{}); events=[]; zones=[]; units=[]; sources=[]
 for src in plan["sources"]:
  path=Path(data_root)/src["filename"]; digest=file_hash(path)
  if digest!=src["sha256"]: raise RuntimeError(f"hash mismatch {path.name}")
  tk=ticks_mod.load_canonical_parquet(str(path),start_utc_ns=int(src["load_start_utc_ns"]),end_utc_ns=min(int(src["load_end_utc_ns"]),CUTOFF))
  if not len(tk) or int(np.max(tk.ts_ns))>=CUTOFF or not bool((np.diff(tk.sequence)>0).all()): raise RuntimeError(f"invalid ticks {path.name}")
  sources.append({"filename":path.name,"sha256":digest,"rows_loaded":len(tk),"max_ts_ns":int(np.max(tk.ts_ns))})
  for n in FRAMES:
   t0=time.perf_counter(); b=bars_mod.build_tick_bars(tk,n,reiniciar_por_sesion=True); fp=bars_mod.build_footprints(tk,b); gate=bars_mod.p1a_gate(tk,b,fp)
   if gate["status"]!="PASS": raise RuntimeError(f"P1A FAIL {path.name} tick:{n}: {gate}")
   r=bigtrap2.run(tk,b,fp,params={},chart_tz="America/Argentina/Buenos_Aires"); rid=obj_hash({"source":digest,"contract":tk.contract,"frame":n,"params":pid}); e,z=transform(r,b,tk,set(src["selected_sessions"]),rid,pid); events+=e; zones+=z
   units.append({"file":path.name,"bar_spec":f"tick:{n}","ticks":len(tk),"bars":len(b),"events":len(e),"zones":len(z),"seconds":round(time.perf_counter()-t0,6),"ru_maxrss":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
 edf,zdf=pd.DataFrame(events),pd.DataFrame(zones); inst=plan["instrument_manifest"]
 manifest={"dataset_id":obj_hash({"builder":"zamr1_z1_bigtrap2_defaults_v1","sources":sources,"sessions":sessions,"commit":head}),"dataset_schema_version":"zamr1_structural_contract_v0","code_commit":head,"code_dirty":False,"builder_id":"zamr1_z1_bigtrap2_defaults_v1","source_data_manifest_sha256":obj_hash(sources),"parameter_registry_sha256":file_hash(root/"specs/zamr1_parameter_registry_v0.json"),"instrument_manifest_sha256":obj_hash(inst),"created_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"research_cutoff_utc":"2026-06-30T22:00:00Z","outcomes_accessed":False,"pnl_accessed":False,"holdout_included":False,"license_decision":"NO_UPLOAD","operational_override":"USER_RISK_ACCEPTANCE_NOT_LICENSE_PERMISSION","pilot_stage":"Z1_BIGTRAP2_DEFAULTS"}
 report=validate_structural_dataset(manifest=manifest,events=edf,zones=zdf,contract=contract)
 if not report.passed: raise RuntimeError(json.dumps(report.to_dict(),ensure_ascii=False))
 out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); ep=out/"events_long.parquet"; zp=out/"zones_long.parquet"; edf.to_parquet(ep,index=False); zdf.to_parquet(zp,index=False); artifacts={p.name:file_hash(p) for p in (ep,zp)}
 for name,obj in (("dataset_manifest.json",manifest),("source_data_manifest.json",sources),("instrument_manifest.json",inst),("contract_validation_report.json",report.to_dict()),("resource_report.json",{"units":units,"artifacts":artifacts})):(out/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n","utf-8")
 return {"passed":True,"sessions":len(set(sessions)),"events":len(edf),"zones":len(zdf),"artifacts":artifacts}
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument("--plan",required=True); p.add_argument("--data-root",required=True); p.add_argument("--out-dir",required=True); p.add_argument("--repo-root",default="."); a=p.parse_args(argv); print(json.dumps(build(a.plan,a.data_root,a.out_dir,a.repo_root),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
