"""Frozen ES families on UTC-day 25-record bars; no return labels or L2 claims."""
import ast
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq

START = 1769904000000000000  # 2026-02-01 UTC
END = 1772323200000000000    # 2026-03-01 UTC
DAY = 86400000000000
FAMILIES = {
    "PLANAS": dict(w=2,max_gap=15,max_step=2,min_pull=5,nmin=3,dmax=35,total_min=0,step_min=0),
    "EMPINADAS": dict(w=2,max_gap=15,max_step=3,min_pull=6,nmin=3,dmax=35,total_min=5,step_min=3),
}

def functions(path, names, env):
    nodes = [n for n in ast.parse(Path(path).read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    assert not any(n.decorator_list for n in nodes)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),env)
    return env

def stream_month(path, keep_bars):
    pf = pq.ParquetFile(path)
    cols = ["ts_utc_ns","price_ticks","bid_ticks","ask_ticks"]
    chosen = []
    for i in range(pf.num_row_groups):
        stats = pf.metadata.row_group(i).column(pf.schema.names.index("ts_utc_ns")).statistics
        if stats is None or not (stats.max < START or stats.min >= END):
            chosen.append(i)
    daily = defaultdict(Counter)
    bars = defaultdict(lambda: defaultdict(list))
    partial = {}
    previous = None
    for batch in pf.iter_batches(batch_size=250000,row_groups=chosen,columns=cols):
        assert all(batch.column(k).null_count == 0 for k in range(4)), "NULL_INPUT"
        t,p,b,a = [batch.column(k).to_numpy(zero_copy_only=False) for k in range(4)]
        m = (t >= START) & (t < END)
        t,p,b,a = [x[m] for x in (t,p,b,a)]
        if not len(t): continue
        assert np.all(np.diff(t) >= 0) and (previous is None or t[0] >= previous), "ORDER"
        previous = int(t[-1])
        ids = t//DAY
        bounds = np.r_[0,np.flatnonzero(np.diff(ids))+1,len(t)]
        for lo,hi in zip(bounds[:-1],bounds[1:]):
            d = str(np.datetime64(int(ids[lo]),'D'))
            tt,pp,bb,aa = [x[lo:hi] for x in (t,p,b,a)]
            q = daily[d]
            q["records"] += len(tt)
            invalid = (bb <= 0) | (aa <= 0)
            locked = (~invalid) & (aa == bb)
            crossed = (~invalid) & (aa < bb)
            valid = (~invalid) & (aa > bb)
            q["invalid_quote"] += int(invalid.sum())
            q["locked"] += int(locked.sum())
            q["crossed"] += int(crossed.sum())
            q["valid_spread"] += int(valid.sum())
            q["one_tick"] += int(((aa-bb == 1) & valid).sum())
            q["spread_sum_ticks"] += int((aa-bb)[valid].sum())
            assert q["records"] == sum(q[k] for k in ("invalid_quote","locked","crossed","valid_spread"))
            if keep_bars:
                old_t,old_p = partial.get(d,(np.array([],dtype=np.int64),np.array([],dtype=np.int64)))
                tt,pp = np.r_[old_t,tt],np.r_[old_p,pp]
                n = len(pp)//25*25
                partial[d] = (tt[n:],pp[n:])
                if n:
                    v=pp[:n].reshape(-1,25)
                    bars[d]["h"].append(v.max(axis=1))
                    bars[d]["l"].append(v.min(axis=1))
                    bars[d]["t"].append(tt[:n].reshape(-1,25)[:,-1]/1e9)
    out = {}
    for d,q in daily.items():
        q["one_tick_fraction"] = q["one_tick"]/q["valid_spread"] if q["valid_spread"] else None
        if keep_bars:
            out[d] = {k:np.concatenate(bars[d][k]) if bars[d][k] else np.array([],dtype=float)
                      for k in ("h","l","t")}
            q["complete_bars"] = len(out[d]["h"])
            q["partial_records"] = len(partial[d][0])
            assert q["complete_bars"]*25+q["partial_records"] == q["records"]
    return dict(daily), out, {"row_groups_read":chosen,"file_rows":pf.metadata.num_rows}

def events(cd, f, source):
    rules=functions(source/"peaks_rule.py",["pivots","backfill"],{"np":np})
    env=functions(source/"escalonadas_det.py",["pasa","chains_px"],{"np":np,"TICK":1.0})
    result=[]
    if len(cd["h"]) < 2*f["w"]+1: return result
    for kind in (1,-1):
        src=cd["h"] if kind==1 else cd["l"]
        x=src if kind==1 else -src
        piv=rules["pivots"](x,f["w"])
        for own,conf,_ in env["chains_px"](cd["h"],cd["l"],cd["t"],
                f["w"],f["max_gap"],f["max_step"],f["min_pull"],f["nmin"],kind,2):
            for k in range(f["nmin"],len(own)+1):
                di=conf[k-1]
                pk=rules["backfill"](own[:k],x,piv,cd["t"],1.0,f["max_gap"],f["max_step"])
                assert all(q <= di and (q in own[:k] or q+f["w"]<=di) for q in pk)
                if env["pasa"](pk,src,f):
                    result.append((kind,int(di),int(src[pk[-1]])))
                    break
    assert len(set(result))==len(result)
    return result

def main():
    ap=argparse.ArgumentParser()
    for k in ("es","gc","source","out"): ap.add_argument("--"+k,required=True)
    a=ap.parse_args(); out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    evidence={"scope":"TARGET_FREE_TICKS_NOT_L2","window_utc":["2026-02-01","2026-03-01"],
              "families":FAMILIES,"confirm_ticks":2,"daily_unit":"UTC_DATE_NOT_CME_SESSION",
              "outcomes_computed":False,"models_fitted":0,"assets":{}}
    for asset,path in (("GC",a.gc),("ES",a.es)):
        daily,bars,meta=stream_month(path,asset=="ES")
        agg={k:sum(q[k] for q in daily.values()) for k in
             ("records","invalid_quote","locked","crossed","valid_spread","one_tick","spread_sum_ticks")}
        agg["one_tick_fraction"]=agg["one_tick"]/agg["valid_spread"]
        agg["mean_spread_ticks"]=agg["spread_sum_ticks"]/agg["valid_spread"]
        rec={"daily":daily,"aggregate":agg,"metadata":meta}
        evidence["assets"][asset]=rec
        if asset=="ES":
            counts={name:{} for name in FAMILIES}
            overlap=0;prefix_checks=0;totals={}
            for d,cd in sorted(bars.items()):
                groups={}
                for name,f in FAMILIES.items():
                    ev=events(cd,f,Path(a.source));groups[name]=set(ev);counts[name][d]=len(ev)
                    if prefix_checks < 8:
                        for n in (500,1000):
                            if len(cd["h"]) > n:
                                pre=events({k:v[:n] for k,v in cd.items()},f,Path(a.source))
                                assert set(pre)=={r for r in ev if r[1]<n}, "PREFIX_MISMATCH"
                                prefix_checks+=1
                overlap+=len(groups["PLANAS"]&groups["EMPINADAS"])
                np.savez_compressed(out/(d+"_bars_PRIVATE.npz"),**cd)
            for name,co in counts.items():
                totals[name]={"events":sum(co.values()),"daily":co,
                    "observed_dates":len(co),"dates_ge4":sum(v>=4 for v in co.values()),
                    "min_observed":min(co.values()),"max_observed":max(co.values())}
            rec["families"]=totals;rec["same_bar_side_level_overlap"]=overlap
            rec["prefix_checks"]=prefix_checks
    evidence["calendar_dates_without_records"]={
        asset:[str(np.datetime64("2026-02-01")+np.timedelta64(i,'D')) for i in range(28)
               if str(np.datetime64("2026-02-01")+np.timedelta64(i,'D')) not in rec["daily"]]
        for asset,rec in evidence["assets"].items()}
    evidence["runner_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
    print(json.dumps({k:{"aggregate":v["aggregate"],"families":v.get("families",{}),
                         "prefix_checks":v.get("prefix_checks")} for k,v in evidence["assets"].items()},indent=2))

if __name__=="__main__": main()