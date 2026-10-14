"""Target-free descriptive pressure/progress atlas; no prediction or raw export.
Uses only original training, existing eligibility and July31 calibration.
Private feature arrays are bounded; only aggregate counts/moments/quantiles leave.
"""
import argparse,json,math,os,time,resource
from pathlib import Path
import numpy as np
from .build_target_free_pilot import digest
from .phenomena import ClockMeasurements
from .phenomena_models import state,phase_key
from .phenomena_states import components
from .gc_a_support_diagnostic import read_session,CAL_PATH,CAL_SHA
PLAN="docs/research/ops/GC_PRESSURE_PROGRESS_PLAN.json"
PLAN_SHA="95a9012db0b498cb783600b7aed0dd956b6669fe5dece304ba4a9c98ad771d37"
METRICS=("pressure_normalized","prior_pressure_normalized","directed_progress_ticks","prior_directed_progress_ticks","abs_progress_ticks","range_ticks","path_ticks","pressure_ratio","trade_count_ratio")
STATES=("A_ONLY","E_ONLY","BOTH","NEITHER","UNKNOWN")
CORRELATIONS=(("pressure_normalized","abs_progress_ticks"),("pressure_normalized","directed_progress_ticks"),("pressure_ratio","directed_progress_ticks"))

def validate(p,c):
 if digest(p)!=PLAN_SHA:raise ValueError("exact new target-free training plan")
 if c.get("sha256")!=CAL_SHA or digest({k:v for k,v in c.items() if k!="sha256"})!=CAL_SHA or c["outcomes_used"] is not False:raise ValueError("existing frozen calibration")
 return p

def progress_bucket(x,p):return int(np.searchsorted(p["progress_bin_edges"],x,side="right"))
def new_cell():return {"pressure_progress_counts":np.zeros((4,5),dtype=np.int64),"prior_current_progress_counts":np.zeros((5,5),dtype=np.int64),"values":{k:[] for k in METRICS},"nonoverlap_pressure_progress_counts":np.zeros((4,5),dtype=np.int64),"nonoverlap_prior_current_progress_counts":np.zeros((5,5),dtype=np.int64),"nonoverlap_count":0}

def summarize_cell(z,p):
 vals={k:np.asarray(v,float) for k,v in z["values"].items()};n=len(vals[METRICS[0]])
 if not n or any(len(v)!=n or not np.isfinite(v).all() for v in vals.values()):raise ValueError("nonempty finite atlas cell")
 correlations={}
 for a,b in CORRELATIONS:
  x=vals[a];y=vals[b];dx=x-x.mean();dy=y-y.mean();den=float(np.sqrt(np.dot(dx,dx)*np.dot(dy,dy)))
  correlations[a+":"+b]={"pearson_descriptive":float(np.clip(np.dot(dx,dy)/den,-1,1)) if den else None,"undefined_if_constant":den==0}
 out={"eligible_anchors":n,"nonoverlap_windows":z["nonoverlap_count"],"continuous_metrics":{k:{"mean":float(v.mean()),"quantiles":[float(t) for t in np.quantile(v,p["component_quantile_probabilities"],method="linear")]} for k,v in vals.items()},"correlations":correlations}
 for name in ("pressure_progress_counts","prior_current_progress_counts","nonoverlap_pressure_progress_counts","nonoverlap_prior_current_progress_counts"):out[name]=z[name].tolist()
 if any(sum(map(sum,out[k]))!=n for k in ("pressure_progress_counts","prior_current_progress_counts")) or any(sum(map(sum,out[k]))!=out["nonoverlap_windows"] for k in ("nonoverlap_pressure_progress_counts","nonoverlap_prior_current_progress_counts")):raise ValueError("atlas cell crossfoot")
 return out

class Atlas:
 def __init__(self,p):self.p=p;self.observed=0;self.states={k:0 for k in STATES};self.cells={};self.last_by_date={};self.last_observed={};self.eligible=0
 def add(self,row,c):
  date=row["trade_date"];t=row["timestamp_ns"];s=state(row,c,research_dates=self.p["training_sessions"])["state"]
  if date in self.last_observed and t<=self.last_observed[date]:raise ValueError("strict original anchor order per date")
  self.last_observed[date]=t;self.observed+=1;self.states[s]+=1
  if self.observed>self.p["max_anchors"]*len(self.p["training_sessions"]):raise ValueError("bounded atlas anchors")
  if s=="UNKNOWN":return
  key=phase_key(row,research_dates=self.p["training_sessions"]);threshold=c["cells"][key];pair=row["windows"]["20"];x=components(pair)
  a=threshold["current_pressure_q80"];b=threshold["prior_pressure_q80"]
  if min(a,b)<=0:raise ValueError("positive approved scales")
  metrics={"pressure_normalized":x["pressure"]/a,"prior_pressure_normalized":x["prior_pressure"]/b,"directed_progress_ticks":pair["directed_progress_ticks"],"prior_directed_progress_ticks":pair["prior_directed_progress_ticks"],"abs_progress_ticks":x["abs_progress"],"range_ticks":x["range"],"path_ticks":x["path"],"pressure_ratio":pair["pressure_ratio"],"trade_count_ratio":pair["trade_count_ratio"]}
  if any(type(v) not in (int,float) or not math.isfinite(v) for v in metrics.values()):raise ValueError("finite continuous descriptor")
  self.eligible+=1
  if key not in self.cells:self.cells[key]=new_cell()
  z=self.cells[key];pressure=int(np.searchsorted(self.p["pressure_bin_edges"],metrics["pressure_normalized"],side="right"));current=progress_bucket(metrics["directed_progress_ticks"],self.p);prior=progress_bucket(metrics["prior_directed_progress_ticks"],self.p)
  z["pressure_progress_counts"][pressure,current]+=1;z["prior_current_progress_counts"][prior,current]+=1
  for k,v in metrics.items():z["values"][k].append(v)
  # Greedy earliest eligible, once per date, irrespective of cell/trajectory.
  previous=self.last_by_date.get(date)
  if previous is None or t-previous>=self.p["nonoverlap_seconds"]*10**9:
   self.last_by_date[date]=t;z["nonoverlap_count"]+=1;z["nonoverlap_pressure_progress_counts"][pressure,current]+=1;z["nonoverlap_prior_current_progress_counts"][prior,current]+=1
 def finish(self):
  out={"observed_anchors":self.observed,"eligible_anchors":self.eligible,"state_counts":dict(self.states),"cells":{k:summarize_cell(z,self.p) for k,z in sorted(self.cells.items())}}
  out["nonoverlap_windows"]=sum(z["nonoverlap_windows"] for z in out["cells"].values())
  if sum(out["state_counts"].values())!=self.observed or self.eligible!=self.observed-self.states["UNKNOWN"] or sum(z["eligible_anchors"] for z in out["cells"].values())!=self.eligible:raise ValueError("atlas crossfoot")
  return out

def run(source,p,private_root,c):
 if not os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):raise ValueError("market execution Kaggle only")
 root=Path(private_root).resolve()
 if root==Path("/kaggle/working") or Path("/kaggle/working") in root.parents:raise ValueError("private features outside outputs")
 validate(p,c);start=time.monotonic();total=Atlas(p);sessions=[];ticks=0
 for r in p["session_ranges"]:
  session=Atlas(p)
  for st in read_session(source,r,p):
   t=st.ticks;ticks+=len(t.ts_ns)
   if ticks>p["max_total_ticks"]:raise ValueError("fixed total tick cap")
   measurement=ClockMeasurements(max_ticks=p["max_session_ticks"],max_anchors=p["max_anchors"],wall_seconds=p["wall_seconds"],max_gap_ns=p["max_gap_ns"])
   for row in measurement.measure(t.ts_ns,t.sequence,t.price_ticks,t.volume,t.bid_ticks,t.ask_ticks,trade_date=r["trade_date"]):
    if time.monotonic()-start>p["wall_seconds"]:raise TimeoutError("bounded atlas")
    session.add(row,c);total.add(row,c)
   sessions.append({"trade_date":r["trade_date"],"ticks":len(t.ts_ns),"measurement":measurement.summary,**session.finish()});del t,st,measurement,session
 train=total.finish();limits=p["support_readiness"];dates=sum(s["nonoverlap_windows"]>=30 for s in sessions)
 ready=train["eligible_anchors"]>=limits["minimum_eligible_anchors"] and train["nonoverlap_windows"]>=limits["minimum_nonoverlap_windows"] and dates>=limits["minimum_dates_with_30_nonoverlap_windows"]
 result={"schema":"gc_pressure_progress_receipt_v1","status":"TARGET_FREE_PRESSURE_PROGRESS_COMPLETE_NOT_EDGE","plan_sha256":digest(p),"calibration_sha256":CAL_SHA,"sessions":sessions,"total_training":train,"total_ticks":ticks,"wall_seconds":time.monotonic()-start,"measured_runner_peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,"support_readiness":{"descriptive_population_sufficient":ready,"dates_with_30_nonoverlap_windows":dates,"supported_cells":[k for k,z in train["cells"].items() if z["nonoverlap_windows"]>=limits["minimum_cell_nonoverlap_windows"]],"evaluation_authorized":False,"independent_episodes_claimed":False},**{k:False for k in ("evaluation_read","outcomes_requested","outcomes_computed","thresholds_changed","models_fitted","new_calibration","dataset_quality_audit","raw_exported","holdout_opened","pnl","canonical_brain_written")}}
 if len((json.dumps(result,indent=2,allow_nan=False)+"\n").encode())>p["max_aggregate_bytes"]:raise ValueError("bounded aggregate atlas")
 return result

def main():
 ap=argparse.ArgumentParser()
 for k in ("source","plan","private-root","receipt"):ap.add_argument("--"+k,required=True)
 a=ap.parse_args()
 try:
  out=run(a.source,json.loads(Path(a.plan).read_bytes()),a.private_root,json.loads(Path(CAL_PATH).read_bytes()));Path(a.receipt).write_text(json.dumps(out,indent=2,allow_nan=False)+"\n")
 except Exception as exc:
  Path(a.receipt).with_name("runner-failure-receipt.json").write_text(json.dumps({"status":"FAILED_NO_SUPPORT_CLAIM","exception_type":type(exc).__name__,"raw_exported":False})+"\n");raise
if __name__=="__main__":main()
