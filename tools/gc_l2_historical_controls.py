"""Target-free P1: historical controls, observed recovery, not price prediction."""
from __future__ import annotations
from pathlib import Path
from collections import defaultdict, deque, Counter
import argparse
import hashlib
import json
import math
import csv
import numpy as np
import gc_l2_fixed_price_probe as P0

CONFIG = P0.CONFIG
MATCH_WINDOW_US = 600_000_000
REPEAT_WINDOW_US = 60_000_000


def power_bin(value):
    return math.floor(math.log2(max(1, value)))


def activity_bin(n):
    return 0 if n == 0 else 1 if n <= 3 else 2 if n <= 15 else 3 if n <= 63 else 4


def depth_bin(depth):
    if not 1 <= depth <= 10:
        raise ValueError("PRICE_OUTSIDE_VISIBLE_DEPTH")
    return 0 if depth == 1 else 1 if depth <= 3 else 2 if depth <= 6 else 3


class HistoricalMatcher:
    """Select by start information only; outcomes are never read by matching."""
    def __init__(self):
        self.pool = defaultdict(deque)
        self.pairs = []

    def add_control(self, episode):
        self.pool[tuple(episode["stratum"])].append(episode)

    def match(self, episode):
        q = self.pool[tuple(episode["stratum"])]
        while q and episode["ts"] - q[0]["ts"] > MATCH_WINDOW_US:
            q.popleft()
        for index in range(len(q) - 1, -1, -1):
            control = q[index]
            if (control["ts"] < episode["ts"] and
                    control["row"] < episode["row"]):
                del q[index]
                pair = {"treated": episode["id"], "control": control["id"],
                        "available_row": episode["row"],
                        "available_ts": episode["ts"]}
                self.pairs.append(pair)
                return pair
        return None


class ControlCycles(P0.Cycles):
    def __init__(self):
        super().__init__()
        self.all_pending = {}
        self.episodes = []
        self.matcher = HistoricalMatcher()
        self.raw_prints = defaultdict(deque)
        self.activity = deque()
        self.prior_depths = {}

    def trade(self, tick, ts, row, size):
        super().trade(tick, ts, row, size)
        self.raw_prints[tick].append((ts, row))
        self.activity.append((ts, row))
        # Only trailing activity is used, no session-wide quantile.
        while self.activity and ts - self.activity[0][0] > CONFIG["trade_window_us"]:
            self.activity.popleft()

    def raw_compatible_count(self, tick, ts, cutoff):
        q = self.raw_prints[tick]
        while q and ts - q[0][0] > CONFIG["trade_window_us"]:
            q.popleft()
        return sum(0 <= ts - t <= CONFIG["trade_window_us"] and row <= cutoff
                   for t, row in q)

    def finish_episode(self, key, status, ts=None, refill=None):
        episode = self.all_pending.pop(key, None)
        if episode is not None:
            episode["status"] = status
            episode["end_ts"] = ts
            episode["refill_size"] = refill

    def change(self, key, old, new, ts, row, drop_row=None, reset=False):
        raw_count = self.raw_compatible_count(key[1], ts, drop_row) \
            if drop_row is not None else None
        super().change(key, old, new, ts, row, drop_row, reset)
        if reset or old is None or new is None:
            self.finish_episode(key, "disappearance_or_reset", ts)
            return
        pending = self.all_pending.get(key)
        if pending and ts - pending["ts"] > CONFIG["refill_window_us"]:
            self.finish_episode(key, "timeout", ts)
            pending = None
        if new < old:
            self.finish_episode(key, "next_drop", ts)
            if drop_row is None:
                return
            credited = self.pending.get(key)
            label = "credited_prints" if credited and credited["drop_row"] == drop_row \
                and credited["drop_ts"] == ts else \
                "no_raw_prints" if raw_count == 0 else "prints_without_credit"
            n = sum(0 <= ts - t <= CONFIG["trade_window_us"] and r <= drop_row
                    for t, r in self.activity)
            d = self.prior_depths[key]
            stratum = (key[0], depth_bin(d), power_bin(old),
                       power_bin(old-new), activity_bin(n))
            episode = {"id": len(self.episodes), "ts": ts, "row": row,
                       "drop_row": drop_row, "side": key[0], "price_tick": key[1],
                       "old_size": old, "drop_size": old-new, "depth": d,
                       "activity": n, "raw_compatible_prints": raw_count,
                       "label": label, "stratum": stratum, "status": "pending",
                       "end_ts": None, "refill_size": None}
            self.episodes.append(episode)
            self.all_pending[key] = episode
            if label == "credited_prints":
                self.matcher.match(episode)
            elif label == "no_raw_prints":
                self.matcher.add_control(episode)
        elif new > old and pending and \
                new >= CONFIG["refill_min_ratio"] * pending["old_size"]:
            self.finish_episode(key, "recovery", ts, new)

def run_session(dfs,book_module,out_jsonl):
    a={c:dfs["l1_quotes"][c].to_numpy() for c in dfs["l1_quotes"].columns}
    b={c:dfs["l2_depth"][c].to_numpy() for c in dfs["l2_depth"].columns}
    na,nb=len(a["source_row"]),len(b["source_row"]);i=j=0
    books=[[],[]];c=ControlCycles();qa=Counter();last_ts=None;group_ts=None;first_ts=None
    prior=None;prior_ok=False;group_removed=set();group_drop_rows={};group_last_row=0;full_since=None
    def snapshot():
        return [{int(t):float(s) for t,s in side[:10]} for side in books]
    def finish(ts,last_row):
        nonlocal prior,prior_ok,full_since
        now=snapshot()
        c.prior_depths = {
            (side, tick): rank + 1
            for side in (0, 1)
            for rank, tick in enumerate(sorted(prior[side], reverse=side==1))
        } if prior else {}
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
                for key in list(c.all_pending):c.finish_episode(key,"invalid_group")
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
    for key in list(c.all_pending):c.finish_episode(key,"right_censored_eof")
    # No EOF-flushed recovery. Outputs represent events already observed.
    with out_jsonl.open("w") as f:
        for e in c.events:f.write(json.dumps(e)+"\n")
    assert qa["recoveries"]==len(c.events)
    lat=np.array([e["latency_us"] for e in c.events],float)
    return c, dict(qa),{"recoveries":len(c.events),
        "median_recovery_ms":float(np.median(lat)/1000) if len(lat) else None,
        "zero_timestamp_latency":int((lat==0).sum()),
        "independent_jsonl_lines":sum(1 for _ in out_jsonl.open()),
        "price_outcomes_computed":False}


def summarize(c, date, out):
    labels = Counter(e["label"] for e in c.episodes)
    status = Counter(e["status"] for e in c.episodes)
    assert sum(status.values()) == len(c.episodes)
    assert status["pending"] == 0
    positives = [e for e in c.episodes if e["label"] == "credited_prints"]
    assert len(positives) == c.counts["drops_with_compatible_prints"]
    assert sum(e["status"] == "recovery" for e in positives) == c.counts["recoveries"]
    pairs = c.matcher.pairs
    assert len({p["control"] for p in pairs}) == len(pairs)
    outcomes = {k: Counter() for k in ("treated", "control")}
    discordance = Counter()
    for pair in pairs:
        a, b = c.episodes[pair["treated"]], c.episodes[pair["control"]]
        assert a["stratum"] == b["stratum"]
        assert b["row"] < a["row"] and 0 < a["ts"]-b["ts"] <= MATCH_WINDOW_US
        assert b["label"] == "no_raw_prints" and a["label"] == "credited_prints"
        for k in outcomes:
            outcomes[k][c.episodes[pair[k]]["status"]] += 1
        discordance[f'{int(a["status"]=="recovery")}_{int(b["status"]=="recovery")}'] += 1
    n = len(pairs)
    tr, cr = outcomes["treated"]["recovery"], outcomes["control"]["recovery"]
    # Repetition uses only earlier completed P0 events, ordered by availability.
    history = {}
    repeated = 0
    for e in c.events:
        key = (e["side"], e["price_tick"])
        previous = history.get(key)
        if previous is not None and 0 <= e["available_ts_us"]-previous <= REPEAT_WINDOW_US:
            repeated += 1
        history[key] = e["available_ts_us"]
    evidence = {"eligible_episodes": len(c.episodes),
        "labels": dict(labels), "all_ending_states": dict(status),
        "matched_pairs": n, "treated_total": len(positives),
        "matched_support_fraction": n/len(positives) if positives else None,
        "support_pass_10pct": bool(positives and n/len(positives) >= .1),
        "paired_ending_states": {k: dict(v) for k,v in outcomes.items()},
        "recovery_fraction_all_pairs": {"treated": tr/n if n else None,
                                       "control": cr/n if n else None},
        "difference_pp": 100*(tr-cr)/n if n else None,
        "paired_binary_outcomes": dict(discordance),
        "completed_p0_recoveries": len(c.events),
        "recoveries_with_previous_same_price_60s": repeated,
        "inference": "DESCRIPTIVE_ONLY_NO_PRICE_OUTCOMES_NO_IID_TEST"}
    with (out/f"{date}_episodes_private.csv").open("w") as f:
        writer = csv.DictWriter(f, fieldnames=list(c.episodes[0]))
        writer.writeheader();writer.writerows(c.episodes)
    (out/f"{date}_pairs_private.json").write_text(json.dumps(pairs))
    return evidence


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--book-module", required=True)
    ap.add_argument("--p0-evidence", required=True)
    ap.add_argument("--plan", required=True)
    args = ap.parse_args()
    root, out = Path(args.raw), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    B = P0.load_book_module(args.book_module)
    manifest = json.loads((root/"docs/manifest.json").read_text())
    old = json.loads(Path(args.p0_evidence).read_text())
    evidence = {"scope": "GC_P1_POST_P0_TARGET_FREE_TWO_EXAMPLES",
        "plan_sha256": hashlib.sha256(Path(args.plan).read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "p0_code_sha256": hashlib.sha256(Path(P0.__file__).read_bytes()).hexdigest(),
        "book_module_sha256": hashlib.sha256(Path(args.book_module).read_bytes()).hexdigest(),
        "config": dict(CONFIG, match_window_us=MATCH_WINDOW_US,
                       repetition_window_us=REPEAT_WINDOW_US),
        "sessions": {}, "new_returns_or_pnl": False}
    for date in ("20260531", "20260615"):
        dfs, input_qa = P0.audit_input(root, date, manifest)
        c, counts, summary = run_session(dfs, B, out/f"{date}_p0_cycles_private.jsonl")
        assert counts == old["sessions"][date]["counts"], "P0_COUNTS_PARITY_FAIL"
        assert summary == old["sessions"][date]["summary"], "P0_SUMMARY_PARITY_FAIL"
        expected = Path(args.p0_evidence).parent/f"{date}_cycles.jsonl"
        if expected.exists():
            assert expected.read_bytes() == (out/f"{date}_p0_cycles_private.jsonl").read_bytes()
        result = summarize(c, date, out)
        # Independent full-file CSV check, not a restatement of in-memory counters.
        independent = Counter()
        with (out/f"{date}_episodes_private.csv").open() as f:
            for e in csv.DictReader(f):
                independent[(e["label"], e["status"])] += 1
        assert sum(independent.values()) == result["eligible_episodes"]
        assert independent[("credited_prints","recovery")] == result["completed_p0_recoveries"]
        result["independent_csv_rows"] = sum(independent.values())
        # Real-data prefix at completed timestamp; compare published events/pairs,
        # not outcomes still unknown at cutoff. At most ~50k depth events replayed.
        cutoff = int(dfs["l2_depth"]["ts_us"].iloc[min(50_000,len(dfs["l2_depth"])-1)])
        prefix = {k: df[df["ts_us"]<=cutoff] for k,df in dfs.items()}
        pc, _, _ = run_session(prefix, B, out/f"{date}_prefix_private.jsonl")
        published = [e for e in c.events if e["available_ts_us"]<=cutoff]
        prior_pairs = [p for p in c.matcher.pairs if p["available_ts"]<=cutoff]
        assert pc.events == published, "REAL_PREFIX_EVENT_FAIL"
        assert pc.matcher.pairs == prior_pairs, "REAL_PREFIX_MATCH_FAIL"
        result["real_prefix_qa"] = {"published_events": len(pc.events),
            "fixed_pairs": len(pc.matcher.pairs), "event_and_match_parity": True}
        evidence["sessions"][date] = {"input_qa": input_qa,
                                     "p0_replay_parity": True, "results": result}
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
        print(date, json.dumps(result), flush=True)
        del dfs, c, prefix, pc


if __name__ == "__main__":
    main()