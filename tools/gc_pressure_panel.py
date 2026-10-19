"""C2 and prospective mirror50 pressure panel. No future labels or fitted model."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, math
import numpy as np
import pyarrow.parquet as pq

MAX_AGE_US=1_000_000
PRIMARY=("directional_queue_imbalance_1","directional_endpoint_ofi_per_touch_depth")


def pressure_gate(q):
    p=q["l2"]
    if q["category"]=="MIRROR_50" and not q["geometry"]["prospective_event_eligible"]:
        return "NOT_PROSPECTIVE"
    if p.get("gate")!="PASS" or p.get("values") is None:
        return "BOOK_UNAVAILABLE"
    if p["available_row"]>=q["row"] or p["available_ts_us"]>=q["ts_us"]:
        return "NOT_STRICT_PRIOR"
    if p["snapshot_age_us"]<0 or p["snapshot_age_us"]>MAX_AGE_US:
        return "STALE_OVER_1000MS"
    v=p["values"]
    if not v["full_window_available"]:
        return "INCOMPLETE_10S_WINDOW"
    if any(v.get(k) is None or isinstance(v[k],bool) or not math.isfinite(v[k]) for k in PRIMARY):
        return "FEATURE_UNAVAILABLE"
    return "PASS"


def sign_class(qi,ofi):
    if qi is None or ofi is None:
        return "UNKNOWN"
    if qi==0 or ofi==0:
        return "SOME_NEUTRAL"
    if qi>0 and ofi>0:
        return "BOTH_WITH_DIRECTION"
    if qi<0 and ofi<0:
        return "BOTH_AGAINST_DIRECTION"
    return "DISAGREE"


def past_baseline(prices,volume,rows,times,event_row,event_ts,direction):
    # `rows` and `times` must be monotonic: same validated raw trade feed.
    end=min(int(np.searchsorted(rows,event_row,side="right")),
            int(np.searchsorted(times,event_ts,side="right")))
    begin=int(np.searchsorted(times,event_ts-10_000_000,side="left"))
    if end<=begin:
        return dict(trade_count_10s=0,volume_10s=0,reference_trade_tick=None,
                    directional_move_10s_ticks=None,path_10s_ticks=None)
    px=prices[begin:end];vol=volume[begin:end]
    assert rows[end-1]<=event_row and times[end-1]<=event_ts
    return dict(trade_count_10s=len(px),volume_10s=int(vol.sum()),
                reference_trade_tick=int(px[-1]),
                directional_move_10s_ticks=int(direction*(px[-1]-px[0])),
                path_10s_ticks=int(np.abs(np.diff(px)).sum()),
                last_trade_row=int(rows[end-1]),last_trade_ts_us=int(times[end-1]))


def make_panel(queries,l1):
    tr=l1[l1.side.eq(2)].sort_values("source_row")
    prices=tr.price_tick.to_numpy();volume=tr["size"].to_numpy()
    rows=tr.source_row.to_numpy();times=tr.ts_us.to_numpy()
    if (np.diff(rows)<=0).any() or (np.diff(times)<0).any():
        raise ValueError("TRADE_ORDER_FAIL")
    panel=[]
    for q in queries:
        if not(q["category"]=="ZONE" and q["profile"]=="C2_EXACT4_DENSAS"
               or q["category"]=="MIRROR_50"):
            continue
        v=q["l2"].get("values") or {}
        qi,ofi=(v.get(k) for k in PRIMARY)
        gate=pressure_gate(q)
        baseline=past_baseline(prices,volume,rows,times,q["row"],q["ts_us"],q["direction"])
        reference=baseline["reference_trade_tick"]
        baseline["distance_to_known_level_ticks"]=None if reference is None else abs(q["target_tick"]-reference)
        baseline["spread_ticks"]=v.get("spread_ticks")
        panel.append(dict(cohort="C2" if q["category"]=="ZONE" else "MIRROR_50",
                          prospective=q["category"]=="ZONE" or q["geometry"]["prospective_event_eligible"],
                          raw_row=q["row"],ts_us=q["ts_us"],direction=q["direction"],
                          primary_qi=qi,primary_ofi=ofi,gate=gate,
                          snapshot_age_us=q["l2"].get("snapshot_age_us"),
                          sign_class=sign_class(qi,ofi) if gate=="PASS" else "EXCLUDED",
                          baseline=baseline,forecast_computed=False,outcomes_computed=False))
    return panel


def summarize_panel(panel):
    summaries={}
    for cohort in ["C2","MIRROR_50"]:
        pp=[p for p in panel if p["cohort"]==cohort and p["prospective"]]
        valid=[p for p in pp if p["gate"]=="PASS"]
        summary=dict(prospective_candidates=len(pp),gates=dict(Counter(p["gate"] for p in pp)),
                     valid_primary=len(valid),signs=dict(Counter(p["sign_class"] for p in valid)),
                     primary_distinct_values={k:len({p[k] for p in valid}) for k in ["primary_qi","primary_ofi"]})
        assert sum(summary["gates"].values())==len(pp)
        assert sum(summary["signs"].values())==len(valid)
        summaries[cohort]=summary
    return summaries


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ["events","receipts","l1","out"]:ap.add_argument("--"+key,required=True)
    a=ap.parse_args()
    queries=[json.loads(x) for x in Path(a.events).read_text().splitlines()]
    receipts=[json.loads(x) for x in Path(a.receipts).read_text().splitlines()]
    if any(q["l2"].get("instrument")!="GC" or q["l2"].get("outcomes_computed")
           or q["l2"].get("forecast_computed") for q in queries):
        raise ValueError("SOURCE_SCOPE_FAIL")
    l1=pq.read_table(a.l1).to_pandas()
    panel=make_panel(queries,l1)
    out=Path(a.out)
    if out.exists():raise ValueError("NEW_PRIVATE_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    with (out/"pressure_panel_PRIVATE.jsonl").open("w") as f:
        for p in panel:f.write(json.dumps(p,allow_nan=False)+"\n")
    evidence=dict(scope="PRESSURE_SUPPORT_NOT_PREDICTIVE_EFFECT",max_age_us=MAX_AGE_US,
                  primary_features=list(PRIMARY),cohorts=summarize_panel(panel),
                  retained_nonprospective_rows=sum(not p["prospective"] for p in panel),
                  all_mirror_receipts=len(receipts),mirror_receipt_status=dict(Counter(p["status"] for p in receipts)),
                  source_sha256={key:hashlib.sha256(Path(getattr(a,key)).read_bytes()).hexdigest()
                                 for key in ["events","receipts","l1"]},
                  runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  models_fitted=0,outcomes_computed=False)
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence))


if __name__=="__main__":main()