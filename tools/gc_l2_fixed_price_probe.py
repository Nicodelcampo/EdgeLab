"""GC R02/I-3 feasibility probe. No price outcome, aggressor inference or P&L."""
from __future__ import annotations
from collections import defaultdict, deque, Counter
from pathlib import Path
import argparse, importlib.util, sys, json, hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

CONFIG={"trade_window_us":2_000_000,"refill_window_us":5_000_000,
        "refill_min_ratio":0.7,"bootstrap_us":60_000_000}

class Cycles:
    def __init__(self):
        self.prints=defaultdict(deque);self.pending={};self.counts=Counter();self.events=[]

    def trade(self, tick, ts, row, size):
        self.prints[tick].append((ts,row,size))

    def censor(self,key,reason):
        if key in self.pending:
            self.pending.pop(key);self.counts[reason]+=1

    def change(self,key,old,new,ts,row,drop_row=None,reset=False):
        if reset or new is None or old is None:
            self.censor(key,"censored_disappearance_or_reset");return
        p=self.pending.get(key)
        if p and ts-p["drop_ts"]>CONFIG["refill_window_us"]:
            self.censor(key,"expired_before_recovery");p=None
        if new<old:
            self.counts["net_size_decreases"]+=1
            self.censor(key,"replaced_by_next_drop")
            if drop_row is None:
                self.counts["decrease_without_same_price_update"]+=1
                return
            q=self.prints[key[1]]
            while q and ts-q[0][0]>CONFIG["trade_window_us"]:q.popleft()
            cutoff=row if drop_row is None else drop_row
            matched=[t for t in q if 0<=ts-t[0]<=CONFIG["trade_window_us"] and t[1]<=cutoff]
            if matched:
                spent={t[1] for t in matched}
                self.prints[key[1]]=deque(t for t in q if t[1] not in spent)
                self.counts["drops_with_compatible_prints"]+=1
                self.pending[key]={"drop_ts":ts,"drop_row":cutoff,"available_drop_row":row,
                    "before_size":old,"after_drop_size":new,"print_count":len(matched),
                    "print_volume":sum(t[2] for t in matched)}
        elif new>old and p and new>=CONFIG["refill_min_ratio"]*p["before_size"]:
            e=dict(p,side=key[0],price_tick=key[1],available_row=row,available_ts_us=ts,
                   refill_size=new,latency_us=ts-p["drop_ts"],status="COMPATIBLE_REPLENISHMENT_NOT_ICEBERG")
            self.events.append(e);self.pending.pop(key);self.counts["recoveries"]+=1

def load_book_module(path):
    spec=importlib.util.spec_from_file_location("canonical_l2_phase0",path)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    return m

def audit_input(root,date,manifest):
    out={};dfs={}
    for kind in ("l1_quotes","l2_depth"):
        path=root/kind/f"{date}.parquet"
        want=next(x for x in manifest["files"] if x["path"]==f"{kind}/{date}.parquet")
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=want["sha256"]:raise ValueError("HASH_FAIL")
        df=pq.read_table(path).to_pandas()
        row=df["source_row"].to_numpy();t=df["ts_us"].to_numpy()
        qa={"rows":len(df),"sha256":sha,"clock_inversions":int((np.diff(t)<0).sum()),
            "source_row_duplicates":int(pd.Series(row).duplicated().sum()),
            "source_row_order_errors":int((np.diff(row)<=0).sum()),
            "null_cells":int(df.isna().sum().sum()),
            "off_grid_rows":int((abs(df["price"]/.1-df["price_tick"])>1e-6).sum())}
        if len(df)!=want["rows"] or any(qa[k] for k in ("clock_inversions","source_row_duplicates","source_row_order_errors","null_cells","off_grid_rows")):
            raise ValueError(f"QA_FAIL {kind} {qa}")
        # Feed types/prices/operations are a contract, not inferred categories.
        if kind=="l2_depth" and (not df["side"].isin([0,1]).all() or not df["operation"].isin([0,1,2]).all()):
            raise ValueError("FEED_CODE_FAIL")
        out[kind]=qa;dfs[kind]=df
    # Independent Arrow metadata count.
    out["arrow_row_counts"]={k:pq.ParquetFile(root/k/f"{date}.parquet").metadata.num_rows for k in dfs}
    a=dfs["l1_quotes"]["source_row"].to_numpy();b=dfs["l2_depth"]["source_row"].to_numpy()
    if np.intersect1d(a,b).size:raise ValueError("INTERLEAVED_ROW_COLLISION")
    return dfs,out

def run_session(dfs,book_module,out_jsonl):
    a={c:dfs["l1_quotes"][c].to_numpy() for c in dfs["l1_quotes"].columns}
    b={c:dfs["l2_depth"][c].to_numpy() for c in dfs["l2_depth"].columns}
    na,nb=len(a["source_row"]),len(b["source_row"]);i=j=0
    books=[[],[]];c=Cycles();qa=Counter();last_ts=None;group_ts=None;first_ts=None
    prior=None;prior_ok=False;group_removed=set();group_drop_rows={};group_last_row=0;full_since=None
    def snapshot():
        return [{int(t):float(s) for t,s in side[:10]} for side in books]
    def finish(ts,last_row):
        nonlocal prior,prior_ok,full_since
        now=snapshot()
        ordered=all(all(side[k][0]<side[k+1][0] if si==0 else side[k][0]>side[k+1][0]
                        for k in range(len(side)-1)) for si,side in enumerate(books))
        complete=all(len(side)>=10 for side in books)
        uncrossed=bool(books[0] and books[1] and books[1][0][0]<books[0][0][0])
        qa["timestamp_groups"]+=1
        if not ordered:qa["unordered_groups"]+=1
        if not uncrossed:qa["crossed_or_incomplete_groups"]+=1
        if complete and ordered and uncrossed:
            if full_since is None:full_since=ts
        else:full_since=None
        ok=full_since is not None and ts-full_since>=CONFIG["bootstrap_us"]
        if ok:qa["valid_bootstrapped_groups"]+=1
        if prior is not None:
            if not(prior_ok and ok):
                for key in list(c.pending):c.censor(key,"censored_invalid_group")
            else:
                for side in (0,1):
                    for tick in prior[side].keys()|now[side].keys():
                        key=(side,tick);old=prior[side].get(tick);new=now[side].get(tick)
                        if old!=new or key in group_removed:
                            c.change(key,old,new,ts,last_row,group_drop_rows.get(key),key in group_removed)
        prior=now;prior_ok=ok
    while i<na or j<nb:
        is_l1=j==nb or (i<na and a["source_row"][i]<b["source_row"][j])
        src=a if is_l1 else b;k=i if is_l1 else j
        ts=int(src["ts_us"][k]);row=int(src["source_row"][k])
        if last_ts is not None and ts<last_ts:raise ValueError(f"MIXED_CLOCK_INVERSION {row}")
        last_ts=ts
        if first_ts is None:first_ts=ts
        if group_ts is not None and ts!=group_ts:
            finish(group_ts,group_last_row);group_removed.clear();group_drop_rows.clear()
        group_ts=ts;group_last_row=row
        if is_l1:
            if int(a["side"][i])==2:
                qa["trade_prints"]+=1
                c.trade(int(a["price_tick"][i]),ts,row,float(a["size"][i]))
            i+=1;continue
        side=int(b["side"][j]);op=int(b["operation"][j]);lv=int(b["level"][j])
        tick=int(b["price_tick"][j]);size=float(b["size"][j]);old=books[side][lv][:] if 0<=lv<len(books[side]) else None
        rc=book_module.apply_event(books[side],op,lv,tick,size,side)
        if rc==book_module.INVALID:raise ValueError(f"BOOK_INVALID_LEVEL {row}")
        if rc==book_module.EDGE_RESYNC:qa["edge_resync_events"]+=1
        if old is not None:
            oldkey=(side,int(old[0]))
            if op==2 or (op==1 and tick!=old[0]):group_removed.add(oldkey)
            if op==1 and tick==old[0] and size<old[1]:group_drop_rows[oldkey]=row
        j+=1
    if group_ts is not None:finish(group_ts,group_last_row)
    qa["right_censored_pending"]=len(c.pending);qa.update(c.counts)
    # No EOF-flushed recovery. Outputs represent events already observed.
    with out_jsonl.open("w") as f:
        for e in c.events:f.write(json.dumps(e)+"\n")
    assert qa["recoveries"]==len(c.events)
    lat=np.array([e["latency_us"] for e in c.events],float)
    return dict(qa),{"recoveries":len(c.events),
        "median_recovery_ms":float(np.median(lat)/1000) if len(lat) else None,
        "zero_timestamp_latency":int((lat==0).sum()),
        "independent_jsonl_lines":sum(1 for _ in out_jsonl.open()),
        "price_outcomes_computed":False}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--raw",required=True);ap.add_argument("--out",required=True)
    ap.add_argument("--book-module",required=True);args=ap.parse_args()
    root=Path(args.raw);out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/"docs/manifest.json").read_text());B=load_book_module(args.book_module)
    evidence={"scope":"TWO_PRIVATE_GC_EXAMPLES_MECHANISTIC_FEASIBILITY_ONLY","config":CONFIG,
        "plan_sha256":hashlib.sha256(Path(__file__).with_name("PLAN.md").read_bytes()).hexdigest() if Path(__file__).with_name("PLAN.md").exists() else None,
        "code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "book_module_sha256":hashlib.sha256(Path(args.book_module).read_bytes()).hexdigest(),
        "dataset_version":2,"source":"nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921",
        "absolute_clock_certified":False,"new_returns_or_pnl":False,"sessions":{},
        "runtime":{"numpy":np.__version__,"pandas":pd.__version__,"pyarrow":pq.__version__ if hasattr(pq,"__version__") else __import__("pyarrow").__version__}}
    for date in ["20260531","20260615"]:
        dfs,q=audit_input(root,date,manifest)
        counts,summary=run_session(dfs,B,out/f"{date}_cycles.jsonl")
        evidence["sessions"][date]={"input_qa":q,"counts":counts,"summary":summary}
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
        print(date,json.dumps({"counts":counts,"summary":summary}),flush=True)
        del dfs

if __name__=="__main__":main()