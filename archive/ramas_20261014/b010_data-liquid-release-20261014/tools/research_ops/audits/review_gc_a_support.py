"""Recount aggregate masks independently; no tick/outcome/model access."""
import hashlib,math
from tools.research_ops.confluence.gc_a_support_diagnostic import validate,CONDITIONS
from tools.research_ops.confluence.build_target_free_pilot import digest

def recount(census,cal):
 states=census["state_counts"];n=census["observed_anchors"]
 if type(n) is not int or n<0 or any(type(v) is not int or v<0 for v in states.values()) or n!=sum(states.values()):raise ValueError("observed state census")
 eligible=absorptions=0
 for key,z in census["cells"].items():
  masks=z["joint_condition_mask_counts"]
  if len(masks)!=32 or any(type(v) is not int or v<0 for v in masks):raise ValueError("complete32jointmasks")
  if z["eligible_anchors"]!=sum(masks) or z["absorption_conjunction_anchors"]!=masks[31]:raise ValueError("joint counts reconcile")
  if z["frozen_calibration_thresholds"]!=cal["cells"][key]:raise ValueError("thresholds unchanged")
  eligible+=sum(masks);absorptions+=masks[31]
  for j,name in enumerate(CONDITIONS):
   active=[m for m in range(32) if format(m,"05b")[4-j]=="1"]
   count=sum(masks[m] for m in active)
   others=sum(masks[m] for m in range(32) if all(m&(1<<k) for k in range(5) if k!=j))
   if z["condition_counts"][name]!=count or z["passes_all_other_conditions"][name]!=others:raise ValueError("independent conjunct count")
  for values in z["component_training_quantiles"].values():
   if len(values)!=5 or any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values) or values!=sorted(values):raise ValueError("training quantile bounds; not pooled")
 if eligible!=n-states["UNKNOWN"] or absorptions!=states["A_ONLY"]+states["BOTH"]:raise ValueError("known/conjunction denominator")
 return eligible,absorptions

def review(boot,r,p,cal,pkg,raw):
 validate(p,cal)
 if boot["status"]!="TARGET_FREE_TRAINING_SUPPORT_COMPLETE_NOT_EDGE" or boot["exit_code"]!=0 or boot["stop_reason"] is not None:raise ValueError("targetfree technical completion")
 for k in ("source_commit","bundle_sha256","plan_sha256"):
  if boot[k]!=pkg[k]:raise ValueError("executed package binding")
 if boot["a_support_receipt_sha256"]!=hashlib.sha256(raw).hexdigest() or len(raw)>p["max_aggregate_bytes"]:raise ValueError("bounded exact aggregate")
 for k in ("outcomes_requested","outcomes_computed","raw_exported","holdout_opened","pnl_computed","new_quality_audit"):
  if boot[k] is not False:raise ValueError("targetfreebootflags")
 if boot["transport_pin_verified"] is not True:raise ValueError("physical transport identity")
 for k in ("evaluation_read","outcomes_requested","outcomes_computed","thresholds_changed","models_fitted","new_calibration","dataset_quality_audit","raw_exported","holdout_opened","pnl","canonical_brain_written"):
  if r[k] is not False:raise ValueError("no outcome/threshold/authority escalation")
 if r["plan_sha256"]!=digest(p) or r["calibration_sha256"]!=cal["sha256"] or r["conditions_in_bit_order"]!=list(CONDITIONS):raise ValueError("scientific identity")
 if [s["trade_date"] for s in r["sessions"]]!=p["training_sessions"]:raise ValueError("originaltraincalendar")
 for s in r["sessions"]:recount(s,cal)
 total=r["total_training"];known,absorption=recount(total,cal)
 if total["observed_anchors"]!=sum(s["observed_anchors"] for s in r["sessions"]):raise ValueError("wholetrainobserved")
 for state,n in total["state_counts"].items():
  if n!=sum(s["state_counts"][state] for s in r["sessions"]):raise ValueError("wholetrainstate")
 for key,z in total["cells"].items():
  for m,v in enumerate(z["joint_condition_mask_counts"]):
   if v!=sum(s["cells"].get(key,{"joint_condition_mask_counts":[0]*32})["joint_condition_mask_counts"][m] for s in r["sessions"]):raise ValueError("wholetrainmasks")
 if r["total_ticks"]!=sum(s["ticks"] for s in r["sessions"]) or r["total_ticks"]>p["max_total_ticks"]:raise ValueError("tickcensus/cap")
 return {"status":"PASS_TARGET_FREE_TRAINING_CONJUNCT_RECOUNT_NOT_EDGE","receipt_sha256":hashlib.sha256(raw).hexdigest(),"plan_sha256":digest(p),"sessions":len(r["sessions"]),"eligible_training_anchors":known,"full_conjunction_anchors":absorption,"outcomes_read":False,"raw_market_read":False,"canonical_brain_written":False}