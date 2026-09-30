"""GC legacy-example QA ONLY; generic features are in l2_asof_features.

No zones, mirror discovery, labels, model fit, future destinations or P&L.
The original manifest/hash validator and canonical MBP replay are reused.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from gc_l2_fixed_price_probe import audit_input, load_book_module
from l2_asof_features import AsOfFeatures


def run(dfs, book_module, sample_path, cap_rows=None, stride=500):
    a = {c: dfs["l1_quotes"][c].to_numpy() for c in dfs["l1_quotes"].columns}
    b = {c: dfs["l2_depth"][c].to_numpy() for c in dfs["l2_depth"].columns}
    na, nb = len(a["source_row"]), len(b["source_row"])
    i = j = count = 0
    books = [[], []]
    engine = AsOfFeatures("GC", window_us=10_000_000)
    stats = Counter()
    full_since = None
    group_ts = group_last = last_ts = None
    fixed_probe_tick = None
    samples = []
    def publish(next_row, next_ts):
        nonlocal full_since, fixed_probe_tick
        complete = all(len(side) >= 10 for side in books)
        ordered = all(all((side[k][0] < side[k+1][0] if n == 0
                           else side[k][0] > side[k+1][0])
                          for k in range(len(side)-1))
                      for n, side in enumerate(books))
        touch = bool(books[0] and books[1] and books[1][0][0] < books[0][0][0])
        valid = complete and ordered and touch
        if not valid:
            full_since = None
        elif full_since is None:
            full_since = group_ts
        gate = ("INCOMPLETE_DEPTH" if not complete else
                "UNORDERED_BOOK" if not ordered else
                "CROSSED_OR_MISSING_TOUCH" if not touch else
                "BOOTSTRAP_60S" if group_ts-full_since < 60_000_000 else "PASS")
        engine.publish(
            [[int(p), float(q)] for p,q in books[1][:10]],
            [[int(p), float(q)] for p,q in books[0][:10]],
            group_last, group_ts, next_row, next_ts, gate=gate)
        actual_gate = engine.current["meta"]["gate"]
        stats["published_groups"] += 1
        stats["gate_" + actual_gate] += 1
        if actual_gate != "PASS":
            return
        if fixed_probe_tick is None:
            fixed_probe_tick = int(books[1][0][0])
        packet = engine.sample(next_row,next_ts, direction=1,
                               target_tick=fixed_probe_tick,target_side="bid")
        stats["full_window_available"] += packet["values"]["full_window_available"]
        stats["fixed_probe_visible"] += packet["target_observation"]["visible"]
        for n in (1,3,10):
            qi = packet["values"]["queue_imbalance_"+str(n)]
            if not -1 <= qi <= 1:
                raise ValueError("QUEUE_IMBALANCE_RANGE_FAIL")
        if stats["gate_PASS"] % stride == 0:
            packet["qa_book"] = engine.current["book"]
            packet["fixed_probe_scope"] = "FIRST_VALID_BID_FIXED_LEVEL_QA_NOT_ZONE_OR_MIRROR_A"
            samples.append(packet)
    while (i<na or j<nb) and (cap_rows is None or count < cap_rows):
        l1 = j == nb or (i<na and a["source_row"][i] < b["source_row"][j])
        src, k = (a,i) if l1 else (b,j)
        ts, row = int(src["ts_us"][k]), int(src["source_row"][k])
        if last_ts is not None and ts < last_ts:
            raise ValueError("MIXED_CLOCK_INVERSION")
        if group_ts is not None and ts != group_ts:
            publish(row, ts)
        group_ts, group_last, last_ts = ts,row,ts
        if not l1:
            side=int(b["side"][j])
            rc=book_module.apply_event(books[side],int(b["operation"][j]),
                int(b["level"][j]),int(b["price_tick"][j]),float(b["size"][j]),side)
            if rc == book_module.INVALID:
                raise ValueError("CANONICAL_BOOK_REPLAY_REJECTED:"+str(row))
            stats["edge_resync_events"] += rc == book_module.EDGE_RESYNC
            j += 1
        else:
            i += 1
        count += 1
    # At EOF/cap the last atomic group is NOT available; do not synthesize a next row.
    stats["processed_rows"] = count
    stats["terminal_group_unpublished"] = int(group_ts is not None)
    stats["qa_samples"] = len(samples)
    with Path(sample_path).open("x",encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s,allow_nan=False)+"\n")
    return dict(stats)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw",required=True)
    ap.add_argument("--book-module",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--files",nargs="+",required=True)
    ap.add_argument("--ack-targetfree",action="store_true")
    a=ap.parse_args()
    if not a.ack_targetfree:
        raise ValueError("TARGETFREE_ACK_REQUIRED")
    root,out=Path(a.raw),Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("OUTPUT_MUST_BE_NEW_EMPTY")
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/"docs/manifest.json").read_text())
    module=load_book_module(a.book_module)
    evidence=dict(
        scope="TWO_EXPOSED_GC_EXAMPLES_ASOF_FEATURE_QA_NOT_SIGNAL_OR_PREDICTION",
        absolute_clock_certified=False,window_us=10_000_000,stride=500,
        new_price_outcomes_computed=False,forecast_computed=False,
        real_zone_or_mirror_events_joined=0,
        hashes={Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "l2_asof_features.py":hashlib.sha256(Path(__file__).with_name("l2_asof_features.py").read_bytes()).hexdigest(),
                "book_module":hashlib.sha256(Path(a.book_module).read_bytes()).hexdigest()},
        files={})
    for date in a.files:
        if not (len(date)==8 and date.isdigit()):
            raise ValueError("EXPLICIT_FILE_ID_REQUIRED")
        dfs,qa=audit_input(root,date,manifest)
        prefix=run(dfs,module,out/(date+"_prefix_private.jsonl"),cap_rows=200_000)
        full=run(dfs,module,out/(date+"_samples_private.jsonl"))
        def lines(name):
            with (out/name).open() as f:
                return [json.loads(x) for x in f if x.strip()]
        short=lines(date+"_prefix_private.jsonl")
        large=lines(date+"_samples_private.jsonl")
        if short != large[:len(short)]:
            raise ValueError("REAL_DATA_PREFIX_CHANGED")
        evidence["files"][date]=dict(input_qa=qa,prefix_counts=prefix,
            counts=full,real_prefix_samples_equal=len(short),prefix_pass=True)
        (out/"evidence.json").write_text(json.dumps(evidence,indent=2))
        print(json.dumps({"file":date,"counts":full,"prefix_samples":len(short)}),flush=True)
    return evidence


if __name__ == "__main__":
    main()