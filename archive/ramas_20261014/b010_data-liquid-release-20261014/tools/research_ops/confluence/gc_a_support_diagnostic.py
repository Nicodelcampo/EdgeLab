"""One target-free training-only scientific support census. No future labels."""
import argparse,json,os,time,resource
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from .build_target_free_pilot import digest
from .phenomena import ClockMeasurements
from .phenomena_models import state,phase_key
from .phenomena_states import components,eligible
from .kaggle_session_reader import iter_sessions
PLAN="docs/research/ops/GC_A_SUPPORT_PLAN.json"
PLAN_SHA="0201ee0951f602d1699e93d10b843d59cdf800072205b23b4266675767685cc9"
CAL_PATH="docs/research/ops/GC_AE_HISTORY_CALIBRATION.json"
CAL_SHA="539b4ba21975510eafeac107c48b415618ba502802283d8860218631b058573d"
CONDITIONS=("CURRENT_PRESSURE_HIGH","PRIOR_PRESSURE_HIGH","ABS_PROGRESS_SMALL","RANGE_SMALL","PATH_SMALL")
QUANTILES=(.1,.25,.5,.75,.9)

def validate(p,c):
 if digest(p)!=PLAN_SHA:raise ValueError("new immutable training-only support plan")
 if c.get("sha256")!=CAL_SHA or digest({k:v for k,v in c.items() if k!="sha256"})!=CAL_SHA or c["outcomes_used"] is not False:raise ValueError("existing calibration only")
 return p

class Census:
 def __init__(self):
  self.observed=0;self.states={s:0 for s in ("A_ONLY","E_ONLY","BOTH","NEITHER","UNKNOWN")};self.cells={}
 def add(self,row,cal,dates):
  s=state(row,cal,research_dates=dates)["state"];self.observed+=1;self.states[s]+=1
  if s=="UNKNOWN":return
  key=phase_key(row,research_dates=dates);c=cal["cells"][key];x=components(row["windows"]["20"])
  flags=(x["pressure"]>=c["current_pressure_q80"],x["prior_pressure"]>=c["prior_pressure_q80"],x["abs_progress"]<=c["stall_abs_progress_max"],x["range"]<=c["stall_range_max"],x["path"]<=c["stall_path_max"])
  mask=sum(int(v)<<j for j,v in enumerate(flags))
  if (mask==31)!=(s in ("A_ONLY","BOTH")):raise ValueError("unchanged classifier/conjunct identity")
  z=self.cells.setdefault(key,{"masks":[0]*32,"values":{k:[] for k in x},"thresholds":dict(c)})
  z["masks"][mask]+=1
  for k,v in x.items():z["values"][k].append(v)
 def finish(self):
  cells={}
  for key,z in sorted(self.cells.items()):
   masks=z["masks"];n=sum(masks)
   cells[key]={"eligible_anchors":n,"joint_condition_mask_counts":masks,"condition_counts":{name:sum(v for m,v in enumerate(masks) if m&(1<<j)) for j,name in enumerate(CONDITIONS)},
    "passes_all_other_conditions":{name:sum(v for m,v in enumerate(masks) if m&(31^(1<<j))==(31^(1<<j))) for j,name in enumerate(CONDITIONS)},
    "absorption_conjunction_anchors":masks[31],"frozen_calibration_thresholds":z["thresholds"],
    "component_training_quantiles":{name:[float(v) for v in np.quantile(values,QUANTILES,method="linear")] for name,values in z["values"].items()}}
  if self.observed!=sum(self.states.values()) or sum(z["eligible_anchors"] for z in cells.values())!=self.observed-self.states["UNKNOWN"]:raise ValueError("support census crossfoot")
  if sum(z["absorption_conjunction_anchors"] for z in cells.values())!=self.states["A_ONLY"]+self.states["BOTH"]:raise ValueError("full conjunction/classifier crossfoot")
  return {"observed_anchors":self.observed,"state_counts":dict(self.states),"cells":cells}

def read_session(source,r,p):
 found=False
 for st in iter_sessions(source,start_ns=r["start_ns"],end_ns=r["end_ns"],instrument="GC",contract="GC_12-26",tick_size=.1,max_session_ticks=p["max_session_ticks"],max_total_ticks=p["max_total_ticks"]):
  date=datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
  if found or date!=r["trade_date"]:raise ValueError("fixed original natural training session")
  found=True;yield st
 if not found:raise ValueError("original training missing; no replacement")

def run(source,p,private_root,c):
 if not os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):raise ValueError("market execution only Kaggle")
 root=Path(private_root).resolve()
 if root==Path("/kaggle/working") or Path("/kaggle/working") in root.parents:raise ValueError("private workspace outside outputs")
 validate(p,c);began=time.monotonic();ticks=0;sessions=[];all_rows=Census()
 for r in p["session_ranges"]:
  census=Census()
  for st in read_session(source,r,p):
   t=st.ticks;ticks+=len(t.ts_ns)
   if ticks>p["max_total_ticks"]:raise ValueError("whole training tick cap")
   m=ClockMeasurements(max_ticks=p["max_session_ticks"],max_anchors=p["max_anchors"],wall_seconds=p["wall_seconds"],max_gap_ns=p["max_gap_ns"])
   for row in m.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=r["trade_date"]):
    if time.monotonic()-began>p["wall_seconds"]:raise TimeoutError("finite support diagnostic")
    census.add(row,c,p["training_sessions"]);all_rows.add(row,c,p["training_sessions"])
   sessions.append({"trade_date":r["trade_date"],"ticks":len(t.ts_ns),"measurement":m.summary,**census.finish()})
   del t,st,m,census
 result={"schema":"gc_a_support_receipt_v1","status":"TARGET_FREE_TRAINING_SUPPORT_COMPLETE_NOT_EDGE","plan_sha256":digest(p),"calibration_sha256":CAL_SHA,"sessions":sessions,"total_training":all_rows.finish(),"conditions_in_bit_order":list(CONDITIONS),"component_quantile_probabilities":list(QUANTILES),"total_ticks":ticks,"wall_seconds":time.monotonic()-began,"measured_runner_peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
 "evaluation_read":False,"outcomes_requested":False,"outcomes_computed":False,"thresholds_changed":False,"models_fitted":False,"new_calibration":False,"dataset_quality_audit":False,"raw_exported":False,"holdout_opened":False,"pnl":False,"canonical_brain_written":False}
 if len((json.dumps(result,indent=2,allow_nan=False)+"\n").encode())>p["max_aggregate_bytes"]:raise ValueError("bounded support aggregate")
 return result

def main():
 ap=argparse.ArgumentParser()
 for k in ("source","plan","private-root","receipt"):ap.add_argument("--"+k,required=True)
 a=ap.parse_args()
 try:
  result=run(a.source,json.loads(Path(a.plan).read_bytes()),a.private_root,json.loads(Path(CAL_PATH).read_bytes()));Path(a.receipt).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
 except Exception as exc:
  Path(a.receipt).with_name("runner-failure-receipt.json").write_text(json.dumps({"status":"FAILED_NO_SUPPORT_CLAIM","exception_type":type(exc).__name__,"raw_exported":False})+"\n");raise
if __name__=="__main__":main()