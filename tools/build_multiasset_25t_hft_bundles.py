#!/usr/bin/env python3
"""Build viewer-ready 25-tick + HFT bundles from an explicit audited plan."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
REPO=Path(__file__).resolve().parents[1];sys.path.insert(0,str(REPO))
from edgelab.bridge.bars import build_tick_bars
from edgelab.bridge.ticks import load_canonical_parquet
from edgelab.bridge.indicators import hftzones_universal as hft
DEFAULT_HOLDOUT_NS=1782856800000000000
def sha256_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def safe_id(value:str)->str:return re.sub(r"[^A-Za-z0-9_.-]+","_",value).strip("_")
def candles_of(bars,tick_size):
 return [{"time":int(bars.end_ns[i]//1_000_000_000),"open":float(bars.open_t[i])*tick_size,"high":float(bars.high_t[i])*tick_size,"low":float(bars.low_t[i])*tick_size,"close":float(bars.close_t[i])*tick_size,"volume":float(bars.volume[i])} for i in range(len(bars))]
def zone_of(z,*,instrument,contract,trade_date,seq,tick_size):
 start_ns,end_ns,avail_ns=int(z["ts_start"]),int(z["ts_end"]),int(z["ts_avail"])
 if not(start_ns<=end_ns<=avail_ns):raise ValueError("zone violates origin <= end <= available")
 return {"id":f"{instrument}:{contract}:{trade_date}:{seq}","source":"HFTZonesUniversal","kind":("HFT_BUY" if int(z["direction"])>0 else "HFT_SELL"),"top":float(z["upper"]),"bottom":float(z["lower"]),"t0":start_ns//1_000_000_000,"t1":end_ns//1_000_000_000,"origin_ts_ns":start_ns,"end_ts_ns":end_ns,"available_ts":avail_ns//1_000_000_000,"available_ns":avail_ns,"termination_reason":z["termination_reason"],"pasos":int(z["pasos"]),"valid_steps":int(z["valid_steps"]),"height_ticks":float(z["height_ticks"]),"total_ms":float(z["total_ms"]),"avg_ms":float(z["avg_ms"]),"total_vol":float(z["total_vol"]),"vol_rate":float(z["vol_rate"]),"max_retro_ticks":float(z["max_retro_ticks"]),"bucket":z["bucket"],"instrument":instrument,"contract":contract,"session_id":str(trade_date),"tick_size":tick_size,"state":"ACTIVE"}
def validate_entry(entry,holdout_ns):
 required={"instrument","contract","parquet","expected_sha256","sessions"};missing=required-set(entry)
 if missing:raise ValueError(f"entry missing {sorted(missing)}")
 if not re.fullmatch(r"[0-9a-fA-F]{64}",str(entry["expected_sha256"])):raise ValueError("expected_sha256 must be 64 hex chars")
 parity=str(entry.get("parity_status","PARITY_ABSTAIN"))
 if parity!="PARITY_ABSTAIN" and not re.fullmatch(r"[0-9a-fA-F]{64}",str(entry.get("parity_evidence_sha256",""))):raise ValueError("non-abstain parity requires parity_evidence_sha256")
 sessions=entry["sessions"]
 if not sessions:raise ValueError("entry must declare at least one session")
 previous_end=None
 for s in sessions:
  req={"trade_date","start_utc_ns","end_utc_ns","prev_session_close_ticks"};miss=req-set(s)
  if miss:raise ValueError(f"session missing {sorted(miss)}")
  start,end=int(s["start_utc_ns"]),int(s["end_utc_ns"])
  if start>=end:raise ValueError("session start must be < end")
  if end>holdout_ns:raise ValueError("session crosses canonical holdout")
  if previous_end is not None and start<previous_end:raise ValueError("session windows overlap")
  previous_end=end
def build_entry(entry,*,holdout_ns,source_sha256):
 validate_entry(entry,holdout_ns);instrument,contract=str(entry["instrument"]),str(entry["contract"]);path=Path(entry["parquet"]);profile_name=str(entry.get("profile","NQ_LITERAL_TRANSFER"));thresholds=hft.profile(profile_name,instrument);structural=dict(entry.get("structural_params") or {});all_candles=[];all_zones=[];session_reports=[];resolved_tick_size=None;seq=0;carry=None
 for session in entry["sessions"]:
  td=int(session["trade_date"]);start_ns,end_ns=int(session["start_utc_ns"]),int(session["end_utc_ns"])
  tk=load_canonical_parquet(path,contract=contract,instrument=instrument,start_utc_ns=start_ns,end_utc_ns=end_ns)
  if tk.instrument!=instrument or tk.contract!=contract:raise ValueError("loader returned wrong instrument or contract")
  if resolved_tick_size is None:resolved_tick_size=float(tk.tick_size)
  elif float(tk.tick_size)!=resolved_tick_size:raise ValueError("tick_size changed between sessions")
  if int(tk.ts_ns[-1])>=holdout_ns:raise ValueError(f"{instrument} {contract} {td}: holdout row decoded")
  if int(tk.ts_ns[0])<start_ns or int(tk.ts_ns[-1])>=end_ns:raise ValueError("loader escaped declared session window")
  bars=build_tick_bars(tk,25,reiniciar_por_sesion=True)
  candidates=hft.detect_candidates(tk.ts_ns,tk.price_ticks,tk.volume,params=structural,prev_session_close_ticks=(carry if session["prev_session_close_ticks"]=="CARRY" else session["prev_session_close_ticks"]))
  zones,rejected=hft.accept_all(candidates,thresholds,tk.tick_size);all_candles.extend(candles_of(bars,tk.tick_size))
  for z in zones:all_zones.append(zone_of(z,instrument=instrument,contract=contract,trade_date=td,seq=seq,tick_size=tk.tick_size));seq+=1
  session_reports.append({"trade_date":td,"start_utc_ns":start_ns,"end_utc_ns":end_ns,"ticks":len(tk),"tick25_bars":len(bars),"candidates":len(candidates),"zones":len(zones),"rejected_by_gate":rejected,"first_tick_context":("EXPLICIT" if (carry if session["prev_session_close_ticks"]=="CARRY" else session["prev_session_close_ticks"]) is not None else "ABSTAIN_MISSING_PREV_SESSION_CLOSE")});carry=int(tk.price_ticks[-1])
 times=[c["time"] for c in all_candles]
 if any(b<a for a,b in zip(times,times[1:])):raise ValueError("output candles are not monotonic")
 if any(int(z["available_ns"])>=holdout_ns for z in all_zones):raise ValueError("output zone reaches holdout")
 status=hft.transfer_status(instrument,entry.get("parity_status"),profile_name);asset_id=safe_id(str(entry.get("asset_id") or f"{instrument}_{contract}_25T"))
 run={"id":f"hft_universal_{asset_id}","name":f"HFTZonesNQPureV4 · {profile_name} · {contract}","indicator":"HFTZonesNQPureV4","engine":"HFTZonesUniversal","bar_key":"tick_25","params":{**hft.profile(profile_name,instrument),**structural},"zones":all_zones,"parity":{"status":status["parity_status"],"gate":status["parity_status"]},**status}
 bundle={"meta":{"id":asset_id,"instrument":instrument,"contract":contract,"tick_size":float(resolved_tick_size),"n_zones":len(all_zones),"source_sha256":source_sha256,"holdout_boundary_ns":holdout_ns,"outcome_firewall":"ENFORCED"},"bar_series":{"tick_25":{"kind":"tick_25","name":"25 Tick","candles":all_candles}},"runs":[run]}
 manifest={"asset_id":asset_id,"instrument":instrument,"contract":contract,"source_path":str(path),"source_sha256":source_sha256,"holdout_boundary_ns":holdout_ns,"holdout_rows_decoded":0,"tick25_bars":len(all_candles),"zones":len(all_zones),"profile":profile_name,**status,"sessions":session_reports}
 return bundle,manifest
def write_json_atomic(path,payload):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":")),encoding="utf-8");tmp.replace(path)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--plan",type=Path,required=True);ap.add_argument("--out",type=Path,default=Path("viewer/nt8_bridge/bundles"));ap.add_argument("--dry-run",action="store_true");args=ap.parse_args();plan=json.loads(args.plan.read_text(encoding="utf-8"));holdout_ns=int(plan.get("holdout_boundary_ns",DEFAULT_HOLDOUT_NS))
 if holdout_ns!=DEFAULT_HOLDOUT_NS:raise ValueError("plan does not use the canonical holdout boundary")
 entries=plan.get("entries") or []
 if not entries:raise ValueError("plan has no entries")
 sha_cache={};catalog=[]
 for entry in entries:
  validate_entry(entry,holdout_ns);path=Path(entry["parquet"])
  if not path.is_file():raise FileNotFoundError(path)
  key=str(path.resolve());actual=sha_cache.setdefault(key,sha256_file(path))
  if actual.lower()!=str(entry["expected_sha256"]).lower():raise ValueError(f"source hash mismatch: {path}")
  if args.dry_run:catalog.append({"instrument":entry["instrument"],"contract":entry["contract"],"status":"DRY_RUN_PASS"});continue
  bundle,manifest=build_entry(entry,holdout_ns=holdout_ns,source_sha256=actual);asset_id=manifest["asset_id"];write_json_atomic(args.out/f"{asset_id}.json",bundle);write_json_atomic(args.out/f"{asset_id}.manifest.json",manifest);catalog.append({"id":asset_id,"instrument":manifest["instrument"],"name":f"{manifest['contract']} · 25 Tick · HFT V2","contract":manifest["contract"],"candles":manifest["tick25_bars"],"zones":manifest["zones"],"parity_status":manifest["parity_status"]})
 write_json_atomic(args.out/"multiasset_hft25_catalog.json",{"holdout_boundary_ns":holdout_ns,"entries":catalog,"status":("DRY_RUN_PASS" if args.dry_run else "BUILT_FAIL_CLOSED")});print(json.dumps({"status":"PASS","entries":len(catalog),"dry_run":args.dry_run}));return 0
if __name__=="__main__":raise SystemExit(main())
