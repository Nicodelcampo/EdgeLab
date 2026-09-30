"""GC May31 current-logic event census; target-free, never mirror.run/outcomes."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import ast, argparse, hashlib, json
import sys
from itertools import chain
import numpy as np
import pyarrow.parquet as pq
from escalonadas_exact4 import Exact4
from gc_l2_fixed_price_probe import audit_input, load_book_module
from gc_kaggle_tick_l2_probe import exact_tape
from l2_asof_features import AsOfFeatures
from mirror_l2_attempts import AttemptRegistry, geometry_from_confirmed_event


def selected_functions(path, names, env):
    """Compile original function bodies, never execute GUI/grid/outcome code."""
    tree = ast.parse(Path(path).read_text())
    nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in names]
    if {x.name for x in nodes} != set(names):
        raise ValueError("SOURCE_FUNCTIONS_MISSING")
    for x in nodes:
        if x.decorator_list:
            raise ValueError("DECORATED_FUNCTION_NOT_ALLOWED")
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), env)
    return env


def publication_for(bar, rows, times):
    close_ts = bar["l2"]["decision_ts_us"]
    pos = int(np.searchsorted(times, close_ts, side="right"))
    if pos == len(rows):
        return None
    assert rows[pos] > bar["feed_trade_end_row"] and times[pos] > close_ts
    return dict(bar_i=bar["bar_i"], instrument="GC", file_id="20260531",
                bar_close_row=bar["feed_trade_end_row"],
                snapshot_asof_row=int(rows[pos-1]), snapshot_ts_us=int(times[pos-1]),
                available_row=int(rows[pos]), available_ts_us=int(times[pos]),
                publication_mode="OBSERVED_NEXT_TIMESTAMP_ROW")


def c0_first_seen(bars, params, source):
    rules = selected_functions(source/"peaks_rule.py", ["pivots","backfill"], {"np":np})
    env = selected_functions(source/"escalonadas_det.py",
                             ["pasa","chains_px","detectar_px"],
                             {"np":np,"TICK":1.0,"CONF_TICKS":28,
                              "R":SimpleNamespace(**{k:rules[k] for k in ["pivots","backfill"]})})
    cd = {k:np.array([x[v] for x in bars],float) for k,v in
          [("h","high"),("l","low"),("c","close")]}
    cd["t"] = np.array([x["l2"]["decision_ts_us"]/1e6 for x in bars])
    seen, events = set(), []
    for j in range(max(3,2*params["w"]+1)-1,len(bars)):
        prefix = {k:v[:j+1] for k,v in cd.items()}
        for z in env["detectar_px"](prefix,params,params["confirm_ticks"]):
            key = (z["kind"],z["det_i"],z["det_nivel"])
            if key in seen:
                continue
            seen.add(key)
            assert z["det_i"] <= j
            events.append(dict(profile="C0_ACTUAL",kind=z["kind"],bar=j,
                logical_det_bar=z["det_i"],timing="FIRST_SEEN_PREFIX_NO_BACKDATE",
                level_tick=int(z["det_nivel"]),members_known_at_first_seen=z["picos"],
                direction=-1 if z["kind"]=="H" else 1,
                target_side="ask" if z["kind"]=="H" else "bid"))
    return events


def geometry_events(bars, profiles, source):
    zones = c0_first_seen(bars,profiles[0]["params"],source)
    diagnostics = {}
    for p in profiles[1:]:
        engine = Exact4(p["params"])
        for b in bars:
            for z in engine.append(b["high"],b["low"],b["close"],
                                   b["l2"]["decision_ts_us"]/1e6,"20260531_CAPTURE"):
                zones.append(dict(profile=p["id"],kind=z["kind"],bar=z["det_i"],
                                  level_tick=z["level_tick"],members=z["members"],
                                  direction=-1 if z["kind"]=="H" else 1,
                                  target_side="ask" if z["kind"]=="H" else "bid"))
        diagnostics[p["id"]] = engine.finish_diagnostic()
    mirror = selected_functions(source/"espejo_impulsos.py",["detect"],
                                {"np":np})
    # Defaults are parsed literally from frozen source, not tuned on this sample.
    tree=ast.parse((source/"espejo_impulsos.py").read_text())
    assignment=next(x for x in tree.body if isinstance(x,ast.Assign) and
                    any(isinstance(t,ast.Name) and t.id=="RESEARCH_DEFAULTS" for t in x.targets))
    defaults={x.arg:ast.literal_eval(x.value) for x in assignment.value.keywords}
    t=np.array([b["l2"]["decision_ts_us"]/1e6 for b in bars])
    h,l,c,v=(np.array([b[k] for b in bars],float) for k in ["high","low","close","volume"])
    impulses=mirror["detect"](t,h,l,c,v,np.full(len(bars),defaults["min_w"]),defaults)
    confirmed=[]
    for im in impulses:
        if im["why"]==1:
            confirmed.append(dict(kind="IMP_CONFIRMED",bar=int(im["jconf"]),
                                  A=int(im["a"]),B=int(im["ext"]),dir=int(im["d"]),
                                  horizon_bar=int(im["iext"]+np.ceil(defaults["horizon_mult"]*
                                      (im["iext"]-im["i0"]+1)))))
    return zones,confirmed,diagnostics,defaults,len(impulses)-len(confirmed)


def attach_book(dfs,module,queries):
    a={c:dfs["l1_quotes"][c].to_numpy() for c in dfs["l1_quotes"].columns}
    b={c:dfs["l2_depth"][c].to_numpy() for c in dfs["l2_depth"].columns}
    na,nb=len(a["source_row"]),len(b["source_row"])
    i=j=0;books=[[],[]];group_ts=group_last=full_since=None;previous=None
    engine=AsOfFeatures("GC",window_us=10_000_000)
    sampler=AsOfFeatures("GC",window_us=10_000_000)
    pending={}
    for q in queries:
        pending.setdefault(q["row"],[]).append(q)
    def publish(row,ts):
        nonlocal full_since,previous
        complete=all(len(s)>=10 for s in books)
        ordered=all(all((s[k][0]<s[k+1][0] if n==0 else s[k][0]>s[k+1][0])
                        for k in range(len(s)-1)) for n,s in enumerate(books))
        touch=bool(books[0] and books[1] and books[1][0][0]<books[0][0][0])
        if not(complete and ordered and touch):full_since=None
        elif full_since is None:full_since=group_ts
        gate=("INCOMPLETE_DEPTH" if not complete else "UNORDERED_BOOK" if not ordered
              else "CROSSED_OR_MISSING_TOUCH" if not touch else
              "BOOTSTRAP_60S" if group_ts-full_since<60_000_000 else "PASS")
        previous=engine.current
        engine.publish([[int(p),float(q)] for p,q in books[1][:10]],
                       [[int(p),float(q)] for p,q in books[0][:10]],
                       group_last,group_ts,row,ts,gate)
    while i<na or j<nb:
        is_l1=j==nb or (i<na and a["source_row"][i]<b["source_row"][j])
        src,k=(a,i) if is_l1 else (b,j)
        ts,row=int(src["ts_us"][k]),int(src["source_row"][k])
        if group_ts is not None and ts!=group_ts:publish(row,ts)
        group_ts,group_last=ts,row
        for q in pending.pop(row,[]):
            assert q["ts_us"]==ts
            candidate=engine.current
            if candidate is not None and candidate["meta"]["available_ts_us"]>=ts:
                candidate=previous
            if candidate is not None:
                assert candidate["meta"]["available_ts_us"]<ts
                assert candidate["meta"]["available_row"]<row
            sampler.current=candidate
            q["l2"]=sampler.sample(row,ts,q["direction"],q["target_tick"],
                                   q["target_side"],instrument="GC")
        if is_l1:i+=1
        else:
            side=int(b["side"][j]);rc=module.apply_event(books[side],int(b["operation"][j]),
                int(b["level"][j]),int(b["price_tick"][j]),float(b["size"][j]),side)
            if rc==module.INVALID:raise ValueError("INVALID_BOOK")
            j+=1
    if pending:raise ValueError("EVENT_RAW_ROW_MISSING")


def summarize(queries):
    counts=Counter(total=len(queries))
    for q in queries:
        p=q["l2"];counts["gate_"+p["gate"]]+=1
        if p["values"] is not None:
            counts["full_ofi_window"]+=p["values"]["full_window_available"]
            counts["target_visible"]+=p["target_observation"]["visible"]
            counts["target_unknown"]+=not p["target_observation"]["visible"]
    assert sum(v for k,v in counts.items() if k.startswith("gate_"))==counts["total"]
    return dict(counts)


def run(bars,dfs,ticks,profiles,source,module):
    exact_tape(ticks,dfs["l1_quotes"])
    row=np.r_[dfs["l1_quotes"].source_row,dfs["l2_depth"].source_row]
    times=np.r_[dfs["l1_quotes"].ts_us,dfs["l2_depth"].ts_us]
    order=np.argsort(row);row,times=row[order],times[order]
    pubs=[publication_for(b,row,times) for b in bars]
    zones,confirmed,diagnostics,defaults,unconfirmed=geometry_events(bars,profiles,source)
    queries=[];unavailable=Counter()
    for z in zones:
        pub=pubs[z["bar"]]
        if pub is None:unavailable[z["profile"]]+=1;continue
        queries.append(dict(category="ZONE",profile=z["profile"],geometry=z,
                            row=pub["available_row"],ts_us=pub["available_ts_us"],
                            direction=z["direction"],target_tick=z["level_tick"],
                            target_side=z["target_side"],publication=pub))
    registry=AttemptRegistry("GC");tr=dfs["l1_quotes"][dfs["l1_quotes"].side.eq(2)]
    trade_rows=tr.source_row.to_numpy()
    trade_prices=tr.price_tick.to_numpy();trade_times=tr.ts_us.to_numpy()
    bar_end_rows=np.array([b["feed_trade_end_row"] for b in bars])
    for event in confirmed:
        pub=pubs[event["bar"]]
        if pub is None:unavailable["MIRROR_REGISTRATION"]+=1;continue
        geom=geometry_from_confirmed_event(event,pub,"GC","20260531",fraction=.5)
        attempt=registry.register(geom)
        direction=-1 if geom.b_tick>geom.a_tick else 1
        queries.append(dict(category="MIRROR_REGISTRATION",profile="MIRROR_AB_DEFAULT",
                            id=geom.id,row=pub["available_row"],ts_us=pub["available_ts_us"],
                            direction=direction,target_tick=geom.a_tick,
                            target_side="bid" if direction==-1 else "ask",publication=pub,
                            geometry=event))
        idx=int(np.searchsorted(trade_rows,pub["available_row"],side="right"))-1
        observations=chain(
            [(int(trade_prices[idx]),pub["available_row"],pub["available_ts_us"])],
            ((int(trade_prices[k]),int(trade_rows[k]),int(trade_times[k]))
             for k in range(idx+1,len(tr))))
        for price,r,t in observations:
            # The source's horizon is known from A/B at registration. Crossing
            # within the horizon bar remains observable; no extension after it.
            logical_bar=int(np.searchsorted(bar_end_rows,r,side="left"))
            if logical_bar>event["horizon_bar"]:
                attempt.status="EXPIRED_BEFORE_LANDMARK_LOGICAL_HORIZON"
                break
            packet=attempt.observe(price,r,t)
            if packet is not None:
                queries.append(dict(category="MIRROR_50",profile="MIRROR_50",
                                    geometry=packet,row=r,ts_us=t,direction=direction,
                                    target_tick=geom.a_tick,
                                    target_side="bid" if direction==-1 else "ask"))
                break
            if attempt.status=="INVALID_BEFORE_LANDMARK":break
    attach_book(dfs,module,queries)
    profiles_counts={p["id"]:summarize([q for q in queries if q["profile"]==p["id"]]) for p in profiles}
    landmark=[q for q in queries if q["category"]=="MIRROR_50"]
    eligible=[q for q in landmark if q["geometry"]["prospective_event_eligible"]]
    receipts=registry.receipts()
    evidence=dict(profiles=profiles_counts,exact4_diagnostics=diagnostics,
                  mirror_defaults=defaults,mirror_confirmed=len(confirmed),
                  mirror_unconfirmed_time_only=unconfirmed,
                  mirror_registration=summarize([q for q in queries if q["category"]=="MIRROR_REGISTRATION"]),
                  mirror_50_all_timing=summarize(landmark),
                  mirror_50_prospective=summarize(eligible),
                  mirror_receipt_status=dict(Counter(x["status"] for x in receipts)),
                  unavailable_publication=dict(unavailable),bars=len(bars),
                  outcomes_computed=False,models_fitted=0)
    return queries,receipts,evidence


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ["bars","ticks","raw","profiles","source","book-module","out"]:
        ap.add_argument("--"+name,required=True)
    args=ap.parse_args();source=Path(args.source)
    bars=[json.loads(x) for x in Path(args.bars).read_text().splitlines()]
    raw=Path(args.raw);dfs,qa=audit_input(raw,"20260531",json.loads((raw/"docs/manifest.json").read_text()))
    ticks=pq.read_table(args.ticks).to_pandas()
    if hashlib.sha256(Path(args.ticks).read_bytes()).hexdigest()!="7976fbe9814eff0e234b74f36af09d42938bcdb154067ea736a46a571f688b1d":
        raise ValueError("TICK_HASH_FAIL")
    # Reject arbitrary/reordered OHLC inputs; these must be exactly the matched tape.
    selected,matched_trades=exact_tape(ticks,dfs["l1_quotes"])
    if len(bars)!=len(selected)//25:raise ValueError("BAR_POPULATION_FAIL")
    for k,b in enumerate(bars):
        block=selected.iloc[25*k:25*(k+1)]
        prices=block.price_ticks.to_numpy()
        if [b[n] for n in ["open","high","low","close"]]!=[int(prices[0]),int(prices.max()),int(prices.min()),int(prices[-1])]:
            raise ValueError("BAR_GEOMETRY_FAIL")
        if b["volume"]!=int(block.volume.sum()) or b["tick_close_utc_ns"]!=int(block.ts_utc_ns.iloc[-1]):
            raise ValueError("BAR_VOLUME_TIME_FAIL")
        if b["bar_i"]!=k or b["feed_trade_end_row"]!=int(matched_trades.source_row.iloc[25*(k+1)-1]) \
                or (b["l2"]["decision_ts_us"]+10_800_000_000)*1000!=b["tick_close_utc_ns"]:
            raise ValueError("BAR_RAW_LEDGER_FAIL")
    profiles=json.loads(Path(args.profiles).read_text())["profiles"]
    module=load_book_module(args.book_module)
    queries,receipts,evidence=run(bars,dfs,ticks,profiles,source,module)
    print("Replay complete; checking geometry prefix",file=sys.stderr,flush=True)
    # Geometry-only causal prefix check; does not fit or inspect destinations.
    z0,m0,_,_,_=geometry_events(bars[:200],profiles,source)
    z1,m1,_,_,_=geometry_events(bars,profiles,source)
    if z0!=[z for z in z1 if z["bar"]<200] or m0!=[m for m in m1 if m["bar"]<200]:
        raise ValueError("GEOMETRY_PREFIX_FAIL")
    evidence["prefix_bars"]=200;evidence["prefix_pass"]=True
    evidence["input_qa"]=qa
    evidence["bars_sha256"]=hashlib.sha256(Path(args.bars).read_bytes()).hexdigest()
    evidence["source_hashes"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob("*") if p.is_file()}
    evidence["runner_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=Path(args.out)
    if out.exists():raise ValueError("NEW_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    for name,records in [("events_l2_PRIVATE.jsonl",queries),("attempts_PRIVATE.jsonl",receipts)]:
        with (out/name).open("w") as f:
            for item in records:f.write(json.dumps(item,allow_nan=False)+"\n")
    (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence))


if __name__=="__main__":main()