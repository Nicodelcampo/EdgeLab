"""Resolve proposals only against an explicitly captured GC baseline.

No defaults, no eval of formula strings, no outcome reading.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from escalonadas_exact4 import validate_params


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
                                    allow_nan=False).encode()).hexdigest()


def round_half_up(x):return int(math.floor(x+0.5))


def resolve(baseline):
    if baseline.get("instrument")!="GC":raise ValueError("GC_INSTRUMENT_REQUIRED")
    if baseline.get("scope") not in ("LOCAL_CAPTURED_CURRENT_CONFIG",
                                   "USER_REPORTED_CURRENT_CONFIG_CODE_CHECKED"):
        raise ValueError("CURRENT_LOCAL_CAPTURE_REQUIRED")
    if baseline.get("tick_size")!=0.1:raise ValueError("GC_TICK_SIZE_FAIL")
    for k in ("asset","bar_type","bar_size","window","family","source_sha256","params"):
        if k not in baseline or baseline[k] is None:raise ValueError("MISSING_BASELINE:"+k)
    sha=baseline["source_sha256"]
    if not isinstance(sha,str) or len(sha)!=64 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("SOURCE_SHA256_FAIL")
    if isinstance(baseline["bar_size"],bool) or not isinstance(baseline["bar_size"],int) or baseline["bar_size"]<1:
        raise ValueError("BAR_SIZE_FAIL")
    p=validate_params(baseline["params"])
    if isinstance(p.get("nmin"),bool) or not isinstance(p.get("nmin"),int) or p["nmin"]<1:
        raise ValueError("CURRENT_NMIN_REQUIRED")
    profiles=[];seen={}
    for ident in ("C0_ACTUAL","C1_EXACT4","C2_EXACT4_DENSAS","C3_EXACT4_SEPARADAS","C4_EXACT4_PLANAS"):
        q=copy.deepcopy(p)
        if ident!="C0_ACTUAL":q["nmin"]=4
        if ident=="C2_EXACT4_DENSAS":
            for k in ("max_gap","min_pull"):q[k]=max(1,round_half_up(p[k]*.75))
        if ident=="C3_EXACT4_SEPARADAS":
            for k in ("max_gap","min_pull"):q[k]=max(1,round_half_up(p[k]*1.5))
            if p["dmax"] is not None and not baseline.get("dmax_unbounded_sentinel",False):
                q["dmax"]=round_half_up(p["dmax"]*1.5)
        if ident=="C4_EXACT4_PLANAS":
            q.update(max_step=round_half_up(p["max_step"]*.5),total_min=0,step_min=0)
        validate_params(q)
        lifecycle="CURRENT_UNCHANGED" if ident=="C0_ACTUAL" else "EXACT4_DISJOINT_NO_BACKFILL"
        key=digest(dict(params=q,lifecycle=lifecycle))
        row=dict(id=ident,params=q,lifecycle=lifecycle,profile_sha256=key,
                 alias_of=seen.get(key),finance_authorized=False)
        if key not in seen:seen[key]=ident
        profiles.append(row)
    return dict(scope="GC_TARGETFREE_RESOLVED_PROPOSALS_NOT_APPROVED_FINANCIAL_CONFIGS",
                baseline_sha256=digest(baseline),baseline=copy.deepcopy(baseline),
                baseline_bundle_independently_hashed=baseline.get("scope")=="LOCAL_CAPTURED_CURRENT_CONFIG",
                profiles=profiles,outcomes_computed=False)


def census(bars,resolved):
    """Exact4 profiles only. C0 must use its original verified detector.

    This function deliberately abstains from approximating C0 with Exact4.
    Caller supplies closed-bar times, session IDs and (if available) publication
    rows. No OHLC-derived future destinations, returns or cost computations.
    """
    from collections import Counter
    from escalonadas_exact4 import Exact4
    results=[]
    for p in resolved["profiles"]:
        if p["id"]=="C0_ACTUAL":
            results.append(dict(id=p["id"],status="ABSTAIN_USE_CURRENT_DETECTOR_FOR_C0"))
            continue
        if p["alias_of"] is not None:
            results.append(dict(id=p["id"],status="ALIAS_NOT_RERUN",alias_of=p["alias_of"]))
            continue
        d=Exact4(p["params"]);per_session=Counter();signals=[]
        for b in bars:
            per_session.setdefault(b.get("session_id"),0)
            for e in d.append(b["high_tick"],b["low_tick"],b["close_tick"],b["time"],b.get("session_id")):
                per_session[e["session_id"]]+=1
                e["raw_publication_row"]=b.get("available_row")
                e["raw_publication_ts_us"]=b.get("available_ts_us")
                metadata_ok=b.get("publication_mode")=="OBSERVED_NEXT_TIMESTAMP_ROW"
                # Do not assert a live event if raw row metadata is absent/invalid.
                e["publication_metadata_pass"]=bool(metadata_ok and
                    isinstance(b.get("available_row"),int) and
                    isinstance(b.get("snapshot_asof_row"),int) and
                    b["available_row"]>b["snapshot_asof_row"]>=b.get("bar_close_row",math.inf) and
                    isinstance(b.get("available_ts_us"),int) and
                    isinstance(b.get("snapshot_ts_us"),int) and
                    b["available_ts_us"]>b["snapshot_ts_us"])
                e["financial_use_certified"]=False
                signals.append(e)
        stats=d.finish_diagnostic()
        results.append(dict(id=p["id"],status="LOGICAL_TARGETFREE_CENSUS",
            counts=stats,per_session=dict(per_session),signals_private=signals,
            publications_metadata_pass=sum(e["publication_metadata_pass"] for e in signals),
            outcomes_computed=False))
    return results