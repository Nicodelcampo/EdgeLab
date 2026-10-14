"""Independent aggregate reconciliation, no raw market/model access."""
import math
import hashlib
import numpy as np
from tools.research_ops.confluence.build_target_free_pilot import digest
from tools.research_ops.confluence.gc_ae_history_runner import validate
from tools.research_ops.confluence.phenomena_history_models import MODELS
from tools.research_ops.confluence.phenomena_history import HISTORY_NAMES, MODEL_SLICES


def close(a,b):
    if type(a) not in (int,float) or not math.isfinite(a) or not math.isclose(a,b,rel_tol=0,abs_tol=1e-12):
        raise ValueError("independent aggregate numerical recount")


def group(g):
    n = g["anchors"]
    if type(n) is not int or n < 0 or sum(g["response_counts"]) != n:
        raise ValueError("group response support crossfoot")
    for v in g["response_counts"]:
        if type(v) is not int or v < 0: raise ValueError("integer response counts")
    if set(g["mean_brier"]) != set(MODELS):raise ValueError("all fixed models retained")
    for v in g["mean_brier"].values():
        if n:
            if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=2:raise ValueError("three-class Brier bounds")
        elif v is not None:raise ValueError("no support must be null, not zero loss")


def review(boot,receipt,plan,calibration,package,raw_bytes):
    validate(plan,calibration)
    if len(raw_bytes)>plan["max_aggregate_bytes"]:raise ValueError("bounded receipt bytes")
    if receipt["plan_sha256"] != digest(plan) or receipt["calibration_sha256"] != calibration["sha256"]:
        raise ValueError("scientific immutable identities")
    if boot.get("status")!="DEVELOPMENT_AE_HISTORY_COMPLETE_NOT_EDGE" or boot.get("exit_code")!=0 or boot.get("stop_reason") is not None:
        raise ValueError("technical completion required")
    for k in ("source_commit","bundle_sha256","plan_sha256"):
        if boot[k] != package[k]:raise ValueError("executed package identity")
    if boot.get("outcomes_computed") is not True or boot["ae_history_receipt_sha256"]!=hashlib.sha256(raw_bytes).hexdigest():
        raise ValueError("exact bounded raw receipt bytes")
    for k in ("holdout_opened","raw_exported","pnl_computed","new_quality_audit"):
        if boot.get(k) is not False:raise ValueError("closed boot scope")
    if boot.get("transport_pin_verified") is not True:raise ValueError("existing physical transport identity")
    if receipt["status"]!="DEVELOPMENT_AE_HISTORY_COMPLETE_NOT_EDGE" or receipt["models"]!=list(MODELS):
        raise ValueError("semantic scientific completion")
    for k in ("holdout_opened","pnl","raw_exported","canonical_brain_written","confirmation","edge_claim","automatic_model_selection","mechanism_validated","overlapping_anchors_independent"):
        if receipt[k] is not False:raise ValueError("closed scientific claim flags")
    if receipt["history_advanced_before_outcomes"] is not True or receipt["purge_embargo_clock_only"] is not True:
        raise ValueError("causal path guard receipt")
    train = receipt["training_sessions"]; ev = receipt["evaluation_sessions"]; missing = receipt["unavailable_evaluation_sessions"]
    if [s["trade_date"] for s in train] != plan["training_sessions"]:raise ValueError("complete original training calendar")
    ev_dates = [s["trade_date"] for s in ev]; missing_dates = [s["trade_date"] for s in missing]
    if ev_dates!=sorted(set(ev_dates)) or set(ev_dates)&set(missing_dates) or sorted(ev_dates+missing_dates)!=plan["evaluation_sessions"]:
        raise ValueError("evaluation calendar without replacement")
    if len(ev)<plan["minimum_available_evaluation_sessions"]:raise ValueError("available session minimum")
    expected_counts = {"PRIOR":0,"HISTORY":len(HISTORY_NAMES)}
    for family, ix in MODEL_SLICES.items():
        for kind in ("PROXY","CAPACITY"):expected_counts[kind+":"+family]=len(HISTORY_NAMES)+len(ix)
    if receipt["model_feature_counts"]!=expected_counts:raise ValueError("capacity-matched dimensions")
    for s in train+ev+[m["measurement_summary"] for m in missing if "measurement_summary" in m]:
        n = s["observed_anchors"]; usable = s["common_usable_anchors"]
        if n!=s["history_updates"] or n!=sum(s["state_counts_before_labels"].values()) or n!=usable+sum(s["excluded_counts"].values()):
            raise ValueError("all observed/usable/censored anchors reconcile")
        if s["clock_only_purge_embargo_applied"] is not True:raise ValueError("per-session clock purge/embargo")
    for s in ev:
        if s["model_feature_counts"]!=expected_counts or s["fit_on_evaluation"] is not False:raise ValueError("no eval refit")
        for pop in ("whole_population","thin_60s_whole_population"):group(s[pop])
        if s["whole_population"]["anchors"]!=s["common_usable_anchors"]:raise ValueError("whole common population")
        if s["thin_60s_whole_population"]["anchors"]!=s["thin_60s_usable_anchors"]:raise ValueError("prelabel thinning support")
        for family in ("A_TO_E","E_TO_A"):
            for pop in ("all_usable","thin_60s"):
                g=s["primary_transition_subsets"][family][pop];group(g)
                if g["anchors"]:
                    close(g["paired_delta_proxy_minus_capacity"],g["mean_brier"]["PROXY:"+family]-g["mean_brier"]["CAPACITY:"+family])
                    close(g["paired_delta_proxy_minus_history"],g["mean_brier"]["PROXY:"+family]-g["mean_brier"]["HISTORY"])
                elif g["paired_delta_proxy_minus_capacity"] is not None or g["paired_delta_proxy_minus_history"] is not None:
                    raise ValueError("empty primary delta null")
        for family in MODEL_SLICES:
            close(s["ablation_deltas"][family],s["whole_population"]["mean_brier"]["PROXY:"+family]-s["whole_population"]["mean_brier"]["CAPACITY:"+family])
    for name in MODELS:
        close(receipt["baseline_equal_session_brier"][name],sum(s["whole_population"]["mean_brier"][name] for s in ev)/len(ev))
    rng=np.random.default_rng(plan["session_bootstrap_seed"])
    for family in ("A_TO_E","E_TO_A"):
        for pop in ("all_usable","thin_60s"):
            rows=[s["primary_transition_subsets"][family][pop] for s in ev]
            total=sum(r["anchors"] for r in rows); supported=[r for r in rows if r["anchors"]]
            a=receipt["primary_results"][family][pop]
            support=total>=plan["minimum_primary_subset_anchors"] and len(supported)>=plan["minimum_primary_subset_sessions"]
            if a["anchors"]!=total or a["sessions_with_support"]!=len(supported) or a["support_minimum_met"] is not support:
                raise ValueError("primary session support recount")
            if supported:
                vectors=np.array([[r["paired_delta_proxy_minus_history"],r["paired_delta_proxy_minus_capacity"]] for r in supported])
                draws=rng.integers(0,len(supported),(plan["session_bootstrap_draws"],len(supported)))
                bound=np.quantile(np.array([vectors[ix].sum(axis=0)/len(supported) for ix in draws]),[.025,.975],axis=0)
            for comparator in ("history","capacity"):
                if supported:
                    ds=[r["paired_delta_proxy_minus_"+comparator] for r in supported]
                    close(a["minus_"+comparator]["equal_session_mean"],sum(ds)/len(ds))
                    close(a["minus_"+comparator]["pooled_anchor_mean"],sum(r["anchors"]*r["paired_delta_proxy_minus_"+comparator] for r in supported)/total)
                    if a["minus_"+comparator]["sessions_improving"]!=sum(d<0 for d in ds):raise ValueError("session signs")
                    j=0 if comparator=="history" else 1
                    close(a["minus_"+comparator]["descriptive_session_bootstrap_95"][0],bound[0,j])
                    close(a["minus_"+comparator]["descriptive_session_bootstrap_95"][1],bound[1,j])
                elif a["minus_"+comparator] is not None:raise ValueError("empty primary summary")
            classification="INCONCLUSIVE_NO_OBSERVED_TRANSITION_SUPPORT" if not supported else (
                "INCONCLUSIVE_SUPPORT" if not support else (
                    "EXPLORATORY_PRACTICAL_MARGIN_CROSSED_NOT_EDGE" if all(
                        a["minus_"+k]["equal_session_mean"]<=-plan["practical_improvement_brier"]
                        for k in ("history","capacity")) else "NO_PRACTICAL_MARGIN_CROSSING"))
            if a["classification"]!=classification:raise ValueError("no favorable relabeling")
    ticks=sum(s["ticks"] for s in train+ev+[m["measurement_summary"] for m in missing if "measurement_summary" in m])
    if receipt["total_ticks"]!=ticks:raise ValueError("all-read tick census")
    if receipt["total_ticks"]>plan["max_total_ticks"] or receipt["response_scanned_elements"]>plan["max_scan_elements_total"]:
        raise ValueError("whole job budget")
    return {"status":"PASS_AGGREGATE_GC_AE_HISTORY_RECOUNT_NOT_EDGE","plan_sha256":digest(plan),
            "receipt_sha256":hashlib.sha256(raw_bytes).hexdigest(),"training_sessions":len(train),
            "evaluation_sessions":len(ev),"missing_evaluation_sessions":len(missing),
            "models":len(MODELS),"two_primary_contrasts_retained":True,"raw_market_read":False,
            "independent_raw_market_recompute":False,"holdout_opened":False,"canonical_brain_written":False}