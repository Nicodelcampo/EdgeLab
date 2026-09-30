"""One-command LOCAL export. Target-free only; no return/fill/SL/TP engine."""
from __future__ import annotations
from pathlib import Path
from collections import Counter, defaultdict, deque
import argparse
import csv
import hashlib
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import gc_l2_fixed_price_probe as P0
from streaming_escalonadas import PriceConfirmed, PARAMS


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""):h.update(block)
    return h.hexdigest()


def checked_file(root,contract,date,tick):
    root=Path(root)/contract
    manifest_path=root/"manifests"/f"{date}.manifest.json"
    m=json.loads(manifest_path.read_text())
    if abs(m["conversion"]["tick_size"]-tick)>1e-12:raise ValueError("TICK_SIZE_FAIL")
    if m["conversion"].get("subsecond_unit")!="100ns_ticks":
        raise ValueError("NATIVE_MNQ_SUBSECOND_CONTRACT_FAIL")
    frames={};q={}
    for kind in ("l1_quotes","l2_depth"):
        path=root/kind/f"{date}.parquet";want=m["outputs"][kind]
        if path.stat().st_size!=want["bytes"] or sha(path)!=want["sha256"]:
            raise ValueError(f"HASH_OR_SIZE_FAIL {path}")
        df=pq.read_table(path).to_pandas()
        needed=["source_row","ts_us","side","price_tick","size"]
        if kind=="l2_depth":needed+=["operation","level"]
        if any(c not in df for c in needed):raise ValueError("SCHEMA_FAIL")
        if len(df)!=want["rows"] or df[needed].isna().any().any():raise ValueError("ROWS_OR_NULL_FAIL")
        if not len(df):raise ValueError("EMPTY_INPUT")
        if (np.diff(df["source_row"])<=0).any() or (np.diff(df["ts_us"])<0).any():
            raise ValueError("ORDER_FAIL")
        if "price" in df and (abs(df["price"]-df["price_tick"]*tick)>1e-6).any():
            raise ValueError("GRID_FAIL")
        if (df["size"]<0).any() or (df["price_tick"]%1!=0).any():raise ValueError("VALUE_FAIL")
        if kind=="l2_depth" and (not df["side"].isin([0,1]).all() or
                not df["operation"].isin([0,1,2]).all()):raise ValueError("DEPTH_CODE_FAIL")
        frames[kind]=df[needed].copy()
        q[kind]={"rows":len(df),"sha256":want["sha256"]}
    if np.intersect1d(frames["l1_quotes"]["source_row"],frames["l2_depth"]["source_row"]).size:
        raise ValueError("ROW_COLLISION")
    q["manifest_sha256"]=sha(manifest_path)
    return frames,q


def session_input(root,session,tick=.25):
    """Joint cut at next file's first timestamp; retain full new snapshot, reset book."""
    pairs=[];qa={}
    for k,date in enumerate(sorted(session["files"])):
        frames,q=checked_file(root,session["contract"],date,tick)
        if pairs:
            first=min(int(df["ts_us"].iloc[0]) for df in frames.values())
            previous=pairs[-1]
            qa[previous["file"]]["clipped_overlap_rows"]={
                kind:int((df["ts_us"]>=first).sum()) for kind,df in previous["frames"].items()}
            previous["frames"]={kind:df[df["ts_us"]<first].copy() for kind,df in previous["frames"].items()}
        for df in frames.values():df["source_row"]+=k*10**12
        pairs.append({"file":date,"frames":frames});qa[date]=q
    return pairs,qa


def features(books,valid,level=None,level_side=None,repeats=0):
    if not valid:
        return dict(book_valid=False,spread_ticks=None,bid3_size=None,ask3_size=None,
                    imbalance3=None,level_size=None,level_depth=None,level_distance_ticks=None,
                    level_visible=None,recoveries_level_10s=None,defense_mask=None)
    ask,bid=books
    aq=sum(float(v) for _,v in ask[:3]);bq=sum(float(v) for _,v in bid[:3])
    depth=size=dist=None
    if level is not None:
        side=books[level_side]
        found=[(i+1,v) for i,(p,v) in enumerate(side[:10]) if p==level]
        if found:depth,size=found[0]
        dist=abs(level-side[0][0])
    return dict(book_valid=True,spread_ticks=ask[0][0]-bid[0][0],
                bid3_size=bq,ask3_size=aq,imbalance3=(bq-aq)/(bq+aq) if bq+aq else None,
                level_size=size,level_depth=depth,level_distance_ticks=dist,
                level_visible=(size is not None) if level is not None else None,
                recoveries_level_10s=repeats if level is not None else None,
                defense_mask=(repeats>=2 and size>0) if size is not None else None)


def process(parts,B,out,session_id,start_ns=None,end_ns=None,clock_offset_us=None,
            barsize=150,max_groups=None):
    """Decision at end of timestamp group, not a retroactive intrabar execution."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    engine=PriceConfirmed();bar=[];pending_bars=[];bars=[];signals=[];stats=Counter()
    books=[[],[]];tracker=P0.Cycles();history=defaultdict(deque)
    prior=None;prior_ok=False;full_since=None;last_trade_ts=None;group_ts=None
    group_row=None;removed=set();drop_rows={};seen_events=0
    def finish(ts,row):
        nonlocal prior,prior_ok,full_since,seen_events
        ordered=all(all(s[k][0]<s[k+1][0] if side==0 else s[k][0]>s[k+1][0]
                        for k in range(len(s)-1)) for side,s in enumerate(books))
        complete=all(len(s)>=10 for s in books)
        uncrossed=bool(books[0] and books[1] and books[1][0][0]<books[0][0][0])
        if ordered and complete and uncrossed:
            if full_since is None:full_since=ts
        else:
            full_since=None;history.clear();stats["invalid_book_groups"]+=1
        ok=full_since is not None and ts-full_since>=60_000_000
        now=[{int(p):float(v) for p,v in side[:10]} for side in books]
        if prior is not None:
            if not (prior_ok and ok):
                for key in list(tracker.pending):tracker.censor(key,"censored_invalid_group")
            else:
                for side in (0,1):
                    for price in prior[side].keys()|now[side].keys():
                        key=(side,price);old=prior[side].get(price);new=now[side].get(price)
                        if old!=new or key in removed:
                            tracker.change(key,old,new,ts,row,drop_rows.get(key),key in removed)
        for event in tracker.events[seen_events:]:
            history[(event["side"],event["price_tick"])].append(event["available_ts_us"])
        seen_events=len(tracker.events)
        for key in list(history):
            while history[key] and ts-history[key][0]>10_000_000:history[key].popleft()
            if not history[key]:del history[key]
        for b in pending_bars:
            j=len(bars)
            b.update(bar_i=j,session_id=session_id,available_ts_us=ts,
                     available_utc_ns=(ts+clock_offset_us)*1000 if clock_offset_us is not None else None,
                     available_row=row)
            fresh=engine.append(b["high_tick"],b["low_tick"],b["close_tick"],b["close_ts_us"]/1e6)
            bars.append(dict(b,**features(books,ok)))
            for event in fresh:
                side=0 if event["kind"]=="H" else 1
                n=len(history[(side,event["det_nivel_tick"])])
                signals.append(dict(event,session_id=session_id,bar_close_row=b["bar_close_row"],
                    available_ts_us=ts,available_utc_ns=(ts+clock_offset_us)*1000 if clock_offset_us is not None else None,
                    available_row=row,**features(books,ok,event["det_nivel_tick"],side,n)))
        pending_bars.clear();prior=now;prior_ok=ok;stats["groups"]+=1
    stop=False
    for part in parts:
        if stop:break
        # Never carry an old depth snapshot/credit over a new file photograph.
        if group_ts is not None:finish(group_ts,group_row)
        books=[[],[]];tracker=P0.Cycles();seen_events=0;history.clear()
        prior=None;prior_ok=False;full_since=None;group_ts=None;removed.clear();drop_rows.clear()
        a,b=part["frames"]["l1_quotes"],part["frames"]["l2_depth"]
        A={c:a[c].to_numpy() for c in a};D={c:b[c].to_numpy() for c in b}
        i=j=0;last_ts=None
        while i<len(a) or j<len(b):
            l1=j==len(b) or (i<len(a) and A["source_row"][i]<D["source_row"][j])
            x=A if l1 else D;k=i if l1 else j
            ts=int(x["ts_us"][k]);row=int(x["source_row"][k]);utc=(ts+(clock_offset_us or 0))*1000
            if last_ts is not None and ts<last_ts:raise ValueError("MIXED_CLOCK_INVERSION")
            last_ts=ts
            if end_ns is not None and utc>=end_ns:stop=True;break
            if group_ts is not None and ts!=group_ts:
                finish(group_ts,group_row);removed.clear();drop_rows.clear()
                if max_groups and stats["groups"]>=max_groups:
                    group_ts=None;stop=True;break
            group_ts,group_row=ts,row
            if l1:
                if int(A["side"][i])==2:
                    price=int(A["price_tick"][i]);tracker.trade(price,ts,row,float(A["size"][i]))
                    if start_ns is None or utc>=start_ns:
                        if last_trade_ts is not None and ts-last_trade_ts>1_800_000_000:
                            stats["partial_prints_discarded_gap"]+=len(bar);bar=[]
                        last_trade_ts=ts;bar.append((price,ts,row));stats["eligible_last_prints"]+=1
                        if len(bar)==barsize:
                            prices=[v[0] for v in bar]
                            pending_bars.append(dict(open_tick=prices[0],high_tick=max(prices),
                                low_tick=min(prices),close_tick=prices[-1],
                                close_ts_us=bar[-1][1],bar_close_row=bar[-1][2],n_last=barsize))
                            bar=[]
                i+=1;continue
            side=int(D["side"][j]);op=int(D["operation"][j]);lv=int(D["level"][j])
            price=int(D["price_tick"][j]);size=float(D["size"][j])
            old=books[side][lv][:] if 0<=lv<len(books[side]) else None
            rc=B.apply_event(books[side],op,lv,price,size,side)
            if rc==B.INVALID:raise ValueError("BOOK_INVALID_LEVEL")
            if old is not None:
                key=(side,int(old[0]))
                if op==2 or (op==1 and price!=old[0]):removed.add(key)
                if op==1 and price==old[0] and size<old[1]:drop_rows[key]=row
            j+=1
        if group_ts is not None:
            finish(group_ts,group_row);group_ts=None
    stats["partial_prints_at_end"]=len(bar)
    # Defensive recomputation independent of incremental OHLC accumulation.
    assert all(b["n_last"]==barsize and b["low_tick"]<=b["close_tick"]<=b["high_tick"] for b in bars)
    assert all(s["available_row"]>=s["bar_close_row"] for s in signals)
    for name,records in (("bars",bars),("signals",signals)):
        with (out/f"{session_id}_{name}_private.jsonl").open("w") as f:
            for r in records:f.write(json.dumps(r)+"\n")
    return dict(stats,bars=len(bars),signals=len(signals),
        signals_valid_book=sum(s["book_valid"] for s in signals),
        signals_defense_mask=sum(s["defense_mask"] is True for s in signals),
        price_outcomes_computed=False),bars,signals


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",required=True);ap.add_argument("--catalog",required=True)
    ap.add_argument("--book-module",required=True);ap.add_argument("--out",required=True)
    ap.add_argument("--clock",required=True,choices=["ART"])
    ap.add_argument("--sessions",default="all")
    ap.add_argument("--max-sessions",type=int,default=1)
    args=ap.parse_args()
    catalog=json.loads(Path(args.catalog).read_text())
    sessions=sorted(catalog["instrumentos"]["MNQ"]["sesiones"],key=lambda s:s["trade_date"])
    if args.sessions!="all":
        wanted=set(args.sessions.split(","));sessions=[s for s in sessions if s["trade_date"] in wanted]
        if len(sessions)!=len(wanted):raise ValueError("SESSION_NOT_IN_CATALOG")
    if args.max_sessions>0:sessions=sessions[:args.max_sessions]
    B=P0.load_book_module(args.book_module);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    evidence={"scope":"MNQ_TARGET_FREE_PREPARATION_NOT_STRATEGY_VALIDATION",
        "catalog_sha256":sha(args.catalog),"code_sha256":sha(__file__),
        "detector_sha256":sha(Path(__file__).with_name("streaming_escalonadas.py")),
        "book_module_sha256":sha(args.book_module),"params":PARAMS,
        "decision":"COMPLETED_150_LAST_BAR_END_TIMESTAMP_GROUP",
        "clock":"ART_TO_UTC_3H_EXPLICIT_USER_CONTRACT","sessions":{},
        "new_returns_or_pnl":False}
    for session in sessions:
        if not session["contract"].startswith("MNQ_"):raise ValueError("INSTRUMENT_FAIL")
        parts,qa=session_input(args.root,session)
        counts,_,_=process(parts,B,out,session["trade_date"],session["start_ns"],
                          session["end_ns"],3*3600*1_000_000)
        evidence["sessions"][session["trade_date"]]={"contract":session["contract"],"input_qa":qa,"counts":counts}
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
        print(session["trade_date"],json.dumps(counts),flush=True)
    # Small transfer artifact; private JSONL stays private until user shares it.
    import zipfile
    with zipfile.ZipFile(out/"MNQ_targetfree_para_nube.zip","w",zipfile.ZIP_DEFLATED) as z:
        z.write(out/"evidence.json","evidence.json")
        for p in sorted(out.glob("*_private.jsonl")):z.write(p,p.name)


if __name__=="__main__":main()