#!/usr/bin/env python3
"""Run frozen EMA200/500/2000 25T development campaign; fail closed."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from edgelab.research.ema3_25t import build_25t_bars, cross_events, frozen_grid, grid_manifest, simulate_cell

ALIASES={"ts_ns":["ts_ns","ts_utc_ns","timestamp_ns","timestamp"],"price":["price","last","last_price","close"],"bid":["bid","bid_price","best_bid"],"ask":["ask","ask_price","best_ask"],"contract":["contract","instrument","symbol"],"trade_date":["trade_date","session_date","date"]}

def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(8<<20),b""): h.update(chunk)
 return h.hexdigest()

def resolve(columns:list[str], explicit:dict[str,str])->dict[str,str]:
 out={}
 for name,aliases in ALIASES.items():
  if name in explicit:
   if explicit[name] not in columns: raise ValueError(f"mapped column absent: {name}={explicit[name]}")
   out[name]=explicit[name]; continue
  hits=[c for c in aliases if c in columns]
  if len(hits)!=1: raise ValueError(f"{name}: expected one alias, found {hits}; use --column-map")
  out[name]=hits[0]
 return out

def load_dataset(root:Path,tick_size:float,explicit:dict[str,str],development_end:str):
 files=sorted(root.rglob("*.parquet")) if root.is_dir() else [root]
 if not files: raise ValueError("no parquet files")
 frames=[]; inventory=[]; mapping=None
 for p in files:
  x=pd.read_parquet(p)
  if mapping is None: mapping=resolve(list(x.columns),explicit)
  elif set(mapping.values())-set(x.columns): raise ValueError(f"schema drift in {p.name}")
  frames.append(x[list(mapping.values())].rename(columns={v:k for k,v in mapping.items()}))
  inventory.append({"file":p.name,"bytes":p.stat().st_size,"rows":len(x),"sha256":sha256(p)})
 x=pd.concat(frames,ignore_index=True); raw_rows=len(x)
 if np.issubdtype(x.ts_ns.dtype,np.number):
  if x.ts_ns.dropna().astype("int64").median()<10**17: raise ValueError("numeric timestamp is not nanoseconds")
  x["ts_ns"]=x.ts_ns.astype("int64"); utc=pd.to_datetime(x.ts_ns,unit="ns",utc=True)
 else:
  utc=pd.to_datetime(x.ts_ns,utc=True,errors="raise"); x["ts_ns"]=utc.astype("int64")
 for c in ("price","bid","ask"):
  q=x[c].astype(float)/tick_size; rounded=np.rint(q)
  if np.max(np.abs(q-rounded))>1e-6: raise ValueError(f"{c} off tick grid")
  x[c+"_ticks"]=rounded.astype("int64")
 x["trade_date"]=x.trade_date.astype(str).str.replace("-","",regex=False)
 keep=utc < pd.Timestamp(development_end,tz="UTC")+pd.Timedelta(days=1)
 protected=int((~keep).sum())
 x=x.loc[keep,["ts_ns","price_ticks","bid_ticks","ask_ticks","contract","trade_date"]].copy()
 x["contract"]=x.contract.astype(str); x=x.sort_values("ts_ns",kind="stable").reset_index(drop=True); x["_row"]=np.arange(len(x),dtype="int64")
 if x.empty: raise ValueError("no development rows after cutoff")
 if (x.groupby(["contract","trade_date"],sort=False).ts_ns.diff().dropna()<0).any(): raise ValueError("clock inversion")
 if (x.ask_ticks<=x.bid_ticks).any(): raise ValueError("crossed/locked quote")
 return x,inventory,mapping,{"raw_rows":raw_rows,"development_rows":len(x),"protected_rows_not_loaded":protected}

def max_drawdown(v):
 if len(v)==0:return None
 c=np.cumsum(v); peak=np.maximum.accumulate(np.r_[0.0,c])[:-1]; return float(np.min(c-peak))

def main()->int:
 ap=argparse.ArgumentParser(); ap.add_argument("--input",required=True); ap.add_argument("--output",required=True); ap.add_argument("--tick-size",type=float,default=.1); ap.add_argument("--commission-rt-ticks",type=float,default=2.4); ap.add_argument("--development-end",default="2026-03-31"); ap.add_argument("--column-map",default="{}"); ap.add_argument("--burnin-bars",type=int,default=6000); a=ap.parse_args()
 out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
 try:
  ticks,inventory,mapping,counts=load_dataset(Path(a.input),a.tick_size,json.loads(a.column_map),a.development_end)
  bars=build_25t_bars(ticks); events=cross_events(bars,a.burnin_bars)
  pd.DataFrame(events).to_parquet(out/"events_target_free.parquet",index=False)
  bars.to_parquet(out/"bars25t.parquet",index=False)
  detail=[]; summary=[]
  for cell in frozen_grid():
   d=simulate_cell(ticks,bars,events,cell,a.commission_rt_ticks)
   if not d.empty: detail.append(d)
   c=d[d.status.eq("COMPLETE")] if not d.empty else d; v=c.net_ticks.to_numpy(float) if not c.empty else np.array([])
   summary.append({"cell_id":cell.cell_id,"trades":len(v),"mean_net_ticks":float(np.mean(v)) if len(v) else None,"sum_net_ticks":float(np.sum(v)) if len(v) else None,"win_rate":float(np.mean(v>0)) if len(v) else None,"max_drawdown_ticks":max_drawdown(v),"unknown_exits":int(d.status.eq("UNKNOWN_EXIT").sum()) if not d.empty else 0,"status":"DESCRIPTIVE_ONLY_NO_PROMOTION"})
  (pd.concat(detail,ignore_index=True) if detail else pd.DataFrame()).to_parquet(out/"trades.parquet",index=False); pd.DataFrame(summary).to_csv(out/"cell_summary.csv",index=False)
  pre={"status":"PASS","partition":"development_through_2026-03-31","holdout_opened":False,"input_inventory":inventory,"column_mapping":mapping,"counts":counts,"bars":len(bars),"events":len(events),"contracts":sorted(ticks.contract.unique().tolist()),"trade_dates":[ticks.trade_date.min(),ticks.trade_date.max()]}
  (out/"preflight.json").write_text(json.dumps(pre,indent=2)); (out/"grid.json").write_text(json.dumps(grid_manifest(),indent=2)); print(json.dumps(pre,indent=2)); return 0
 except Exception as e:
  fail={"status":"ABSTAIN","error":type(e).__name__,"message":str(e),"holdout_opened":False}; (out/"preflight.json").write_text(json.dumps(fail,indent=2)); print(json.dumps(fail,indent=2),file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
