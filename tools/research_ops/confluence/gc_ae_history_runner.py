"""Finite Kaggle-only GC causal trajectory experiment, aggregate-only outputs."""
import argparse
import json
import os
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .build_target_free_pilot import digest
from .kaggle_session_reader import iter_sessions
from .phenomena_history_session import session_data
from .phenomena_history_models import fit_models, score, MODELS
from .source_footer import HOLDOUT_OPEN_NS

PLAN = "docs/research/ops/GC_AE_HISTORY_PLAN.json"
PLAN_SHA = "3abcfe6990faf97962ad185f3c9ff1668541187ec435089427e2f203e442e39d"
CAL_PATH = "docs/research/ops/GC_AE_HISTORY_CALIBRATION.json"
CAL_SHA = "539b4ba21975510eafeac107c48b415618ba502802283d8860218631b058573d"
STAGES = ("PREFLIGHT", "READ_SESSION", "HISTORY_AND_LABEL", "FIT", "SCORE", "FINALIZE")


def validate(plan, calibration):
    if digest(plan) != PLAN_SHA or plan["models"] != list(MODELS):
        raise ValueError("immutable new GC history protocol")
    if calibration.get("sha256") != CAL_SHA or digest({k:v for k,v in calibration.items() if k!="sha256"}) != CAL_SHA:
        raise ValueError("existing no-outcome GC calibration hash")
    if calibration["outcomes_used"] is not False or calibration["training_trade_date"] != "2026-07-31":
        raise ValueError("calibration precedes fitting without outcomes")
    dates = plan["training_sessions"] + plan["evaluation_sessions"]
    if dates != sorted(set(dates)) or any(d >= "2026-10-01" for d in dates):
        raise ValueError("fixed unique preholdout calendar")
    for r in plan["session_ranges"]:
        end = int(datetime.fromisoformat(r["trade_date"]+"T22:00:00+00:00").timestamp())*10**9
        if not end-86400*10**9 == r["start_ns"] < r["end_ns"] == end <= HOLDOUT_OPEN_NS:
            raise ValueError("exact natural preholdout session bound")
    return plan


def one_session(source, r, p):
    found = False
    for st in iter_sessions(
        source, start_ns=r["start_ns"], end_ns=r["end_ns"],
        contract="GC_12-26", instrument="GC", tick_size=.1,
        max_session_ticks=p["max_session_ticks"], max_total_ticks=p["max_total_ticks"]):
        date = datetime.fromtimestamp(st.session_id*86400,timezone.utc).date().isoformat()
        if found or date != r["trade_date"]:
            raise ValueError("selected GC natural session identity")
        found = True
        yield st


def summarize(sessions, plan):
    """Both primary directions retained, including no support/negative results."""
    rng = np.random.default_rng(plan["session_bootstrap_seed"])
    result = {}
    for direction in plan["primary_families"]:
        result[direction] = {}
        for population in ("all_usable", "thin_60s"):
            rows = [s["primary_transition_subsets"][direction][population] for s in sessions]
            total = sum(r["anchors"] for r in rows)
            selected = [r for r in rows if r["anchors"]]
            supported = total >= plan["minimum_primary_subset_anchors"] and len(selected) >= plan["minimum_primary_subset_sessions"]
            entry = {"anchors":total,"sessions_with_support":len(selected),"support_minimum_met":supported,
                     "independent_episode_claim":False, "two_primary_contrasts_retained":True,
                     "bootstrap_scope":"DESCRIPTIVE_SESSIONS_NOT_CONFIRMATION_MULTIPLICITY_ADJUSTMENT"}
            if selected:
                deltas = np.array([[r["paired_delta_proxy_minus_history"],
                                    r["paired_delta_proxy_minus_capacity"]] for r in selected])
                mean = deltas.mean(axis=0)
                boot = deltas[rng.integers(0,len(selected),(plan["session_bootstrap_draws"],len(selected)))].mean(axis=1)
                bounds = np.quantile(boot,[.025,.975],axis=0)
                for i, name in enumerate(("history","capacity")):
                    entry["minus_"+name] = {
                        "equal_session_mean":float(mean[i]),
                        "pooled_anchor_mean":float(sum(r["anchors"]*r["paired_delta_proxy_minus_"+name] for r in selected)/total),
                        "sessions_improving":int((deltas[:,i]<0).sum()),
                        "descriptive_session_bootstrap_95":[float(bounds[0,i]),float(bounds[1,i])],
                    }
                crosses = supported and bool(np.all(mean <= -plan["practical_improvement_brier"]))
                entry["classification"] = "EXPLORATORY_PRACTICAL_MARGIN_CROSSED_NOT_EDGE" if crosses else "NO_PRACTICAL_MARGIN_CROSSING" if supported else "INCONCLUSIVE_SUPPORT"
            else:
                entry.update(classification="INCONCLUSIVE_NO_OBSERVED_TRANSITION_SUPPORT",minus_history=None,minus_capacity=None)
            result[direction][population] = entry
    return result


def run(source, plan, private_root, calibration, *, progress=None):
    progress = {} if progress is None else progress
    progress.update(stage="PREFLIGHT",trade_date=None)
    if not os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        raise ValueError("market execution requires Kaggle")
    root = Path(private_root).resolve()
    if root == Path("/kaggle/working") or Path("/kaggle/working") in root.parents:
        raise ValueError("private state must remain outside outputs")
    validate(plan, calibration)
    began = time.monotonic()
    training, training_summary, evaluation, unavailable = [], [], [], []
    ticks = scan = 0
    models = None
    fit_seconds = measurement_seconds = scoring_seconds = 0.
    for r in plan["session_ranges"]:
        date = r["trade_date"]
        progress.update(stage="READ_SESSION",trade_date=date)
        found = False
        for st in one_session(source, r, plan):
            found = True
            ticks += len(st.ticks.ts_ns)
            if ticks > plan["max_total_ticks"]:
                raise ValueError("whole experiment tick cap; no truncation")
            progress.update(stage="HISTORY_AND_LABEL")
            t = time.monotonic()
            data = session_data(st,date,plan,calibration,began)
            measurement_seconds += time.monotonic()-t
            scan += data["summary"]["response_scanned_elements"]
            if scan > plan["max_scan_elements_total"]:
                raise ValueError("whole experiment response scan cap")
            if date in plan["training_sessions"]:
                if len(data["y"]) < plan["minimum_training_usable_anchors_per_session"]:
                    raise ValueError("fixed training session support below minimum")
                training.append(data)
                training_summary.append(data["summary"])
                if date == plan["training_sessions"][-1]:
                    if [s["trade_date"] for s in training_summary] != plan["training_sessions"]:
                        raise ValueError("all original training dates required")
                    progress.update(stage="FIT")
                    t = time.monotonic(); models = fit_models(training)
                    fit_seconds = time.monotonic()-t
                    training.clear()
            else:
                if models is None:
                    raise ValueError("fit must precede first evaluation read")
                if len(data["y"]):
                    progress.update(stage="SCORE")
                    t = time.monotonic(); evaluation.append(score(data,models))
                    scoring_seconds += time.monotonic()-t
                else:
                    unavailable.append({"trade_date":date,"status":"NO_COMMON_USABLE_RESPONSE",
                                        "replacement_selected":False,"measurement_summary":data["summary"]})
            del data,st
            if time.monotonic()-began > plan["wall_seconds"]:
                raise TimeoutError("whole experiment wall cap")
        if not found:
            if date in plan["training_sessions"]:
                raise ValueError("training date absent; no substitution")
            unavailable.append({"trade_date":date,"status":"SOURCE_EMPTY_NO_REPLACEMENT",
                                "replacement_selected":False,"response_read":False})
    progress.update(stage="FINALIZE",trade_date=None)
    if len(evaluation)+len(unavailable) != len(plan["evaluation_sessions"]):
        raise ValueError("requested calendar crossfoot")
    if len(evaluation) < plan["minimum_available_evaluation_sessions"]:
        raise ValueError("available evaluation sessions below fixed minimum")
    result = {
        "schema":"gc_ae_history_receipt_v1","status":"DEVELOPMENT_AE_HISTORY_COMPLETE_NOT_EDGE",
        "plan_sha256":digest(plan),"calibration_sha256":CAL_SHA,"asset":"GC","contract":"GC_12-26",
        "tick_size":.1,"training_sessions":training_summary,"evaluation_sessions":evaluation,
        "requested_evaluation_sessions":plan["evaluation_sessions"],"unavailable_evaluation_sessions":unavailable,
        "primary_results":summarize(evaluation,plan),"models":list(MODELS),"model_feature_counts":models["feature_counts"],
        "baseline_equal_session_brier":{k:float(np.mean([s["whole_population"]["mean_brier"][k] for s in evaluation])) for k in MODELS},
        "total_ticks":ticks,"response_scanned_elements":scan,"fit_seconds":fit_seconds,
        "measurement_seconds":measurement_seconds,"scoring_seconds":scoring_seconds,
        "wall_seconds":time.monotonic()-began,
        "measured_runner_peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        "history_advanced_before_outcomes":True,"purge_embargo_clock_only":True,
        "calibration_reused_no_new_outcomes":True,"MDE_power_status":plan["MDE_power_status"],
        "prior_source_audit_repeated":False,"new_inference":False,"confirmation":False,"edge_claim":False,
        "holdout_opened":False,"pnl":False,"raw_exported":False,"canonical_brain_written":False,
        "automatic_model_selection":False,"mechanism_validated":False,"overlapping_anchors_independent":False,
    }
    if len((json.dumps(result,indent=2,allow_nan=False)+"\n").encode()) > plan["max_aggregate_bytes"]:
        raise ValueError("bounded aggregate receipt")
    return result


def main():
    ap = argparse.ArgumentParser()
    for k in ("source","plan","private-root","receipt"):
        ap.add_argument("--"+k,required=True)
    args = ap.parse_args()
    progress = {}
    try:
        result = run(args.source,json.loads(Path(args.plan).read_bytes()),args.private_root,
                     json.loads(Path(CAL_PATH).read_bytes()),progress=progress)
        Path(args.receipt).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    except Exception as exc:
        # Static category only: no source paths, observed ticks, exception messages.
        receipt = {"schema":"gc_ae_history_failure_v1","status":"FAILED_NO_SCIENTIFIC_CLAIM",
                   "exception_type":type(exc).__name__ if type(exc) in (ValueError,TimeoutError,MemoryError) else "UNCLASSIFIED_EXCEPTION",
                   "stage":progress.get("stage") if progress.get("stage") in STAGES else "UNCLASSIFIED_STAGE",
                   "trade_date":progress.get("trade_date"),
                   "partial_success":False,"raw_exported":False}
        Path(args.receipt).with_name("runner-failure-receipt.json").write_text(json.dumps(receipt)+"\n")
        raise

if __name__ == "__main__":
    main()