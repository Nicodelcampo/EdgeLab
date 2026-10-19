"""Target-free exact-tape GC join; strict earlier publication, no same-ts book."""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
import numpy as np
import pyarrow.parquet as pq
from gc_l2_fixed_price_probe import audit_input, load_book_module
from l2_asof_features import AsOfFeatures

TICK_SHA = "7976fbe9814eff0e234b74f36af09d42938bcdb154067ea736a46a571f688b1d"
OFFSET_US = 10_800_000_000


def exact_tape(ticks, l1):
    tr = l1[l1.side.eq(2)].sort_values("source_row")
    ts = tr.ts_us.to_numpy() * 1000 + OFFSET_US * 1000
    selected = ticks[(ticks.ts_utc_ns >= ts[0]) & (ticks.ts_utc_ns <= ts[-1])]
    left = np.column_stack([ts, tr.price_tick.to_numpy(), tr["size"].to_numpy()])
    right = selected[["ts_utc_ns", "price_ticks", "volume"]].to_numpy()
    if left.shape != right.shape or not np.array_equal(left, right):
        raise ValueError("ABSTAIN_ORDERED_TAPE_IDENTITY_FAIL")
    # Duplicate prints are not timestamp-nearest paired. Entire ordered tape must
    # match; strict earlier publication removes same-timestamp interleaving needs.
    return selected, tr


def run(dfs, ticks, module, cap_trades=None):
    selected, tr = exact_tape(ticks, dfs["l1_quotes"])
    a = {c: dfs["l1_quotes"][c].to_numpy() for c in dfs["l1_quotes"].columns}
    b = {c: dfs["l2_depth"][c].to_numpy() for c in dfs["l2_depth"].columns}
    na, nb = len(a["source_row"]), len(b["source_row"])
    engine = AsOfFeatures("GC", window_us=10_000_000)
    sampler = AsOfFeatures("GC", window_us=10_000_000)
    books = [[], []]
    stats = Counter()
    i = j = ntr = 0
    group_ts = group_last = full_since = None
    previous_published = None
    bars, bar = [], []

    def publish(row, ts):
        nonlocal full_since, previous_published
        complete = all(len(x) >= 10 for x in books)
        ordered = all(all((s[k][0] < s[k+1][0] if n == 0 else
                          s[k][0] > s[k+1][0]) for k in range(len(s)-1))
                      for n, s in enumerate(books))
        touch = bool(books[0] and books[1] and books[1][0][0] < books[0][0][0])
        if not (complete and ordered and touch):
            full_since = None
        elif full_since is None:
            full_since = group_ts
        gate = ("INCOMPLETE_DEPTH" if not complete else "UNORDERED_BOOK"
                if not ordered else "CROSSED_OR_MISSING_TOUCH" if not touch else
                "BOOTSTRAP_60S" if group_ts-full_since < 60_000_000 else "PASS")
        previous_published = engine.current
        engine.publish([[int(p), float(q)] for p,q in books[1][:10]],
                       [[int(p), float(q)] for p,q in books[0][:10]],
                       group_last, group_ts, row, ts, gate)
        stats["published_groups"] += 1

    while (i < na or j < nb) and (cap_trades is None or ntr < cap_trades):
        is_l1 = j == nb or (i < na and a["source_row"][i] < b["source_row"][j])
        src, k = (a, i) if is_l1 else (b, j)
        ts, row = int(src["ts_us"][k]), int(src["source_row"][k])
        if group_ts is not None and ts != group_ts:
            publish(row, ts)
        group_ts, group_last = ts, row
        if not is_l1:
            side = int(b["side"][j])
            rc = module.apply_event(books[side], int(b["operation"][j]),
                                    int(b["level"][j]), int(b["price_tick"][j]),
                                    float(b["size"][j]), side)
            if rc == module.INVALID:
                raise ValueError("INVALID_BOOK_EVENT")
            j += 1
            continue
        if int(a["side"][i]) == 2:
            canonical = selected.iloc[ntr]
            assert int(canonical.ts_utc_ns) == (ts+OFFSET_US)*1000
            bar.append((int(canonical.price_ticks), int(canonical.volume),
                        int(canonical.source_row), row, ts))
            ntr += 1
            if len(bar) == 25:
                candidate = engine.current
                if candidate is not None and candidate["meta"]["available_ts_us"] >= ts:
                    candidate = previous_published
                if candidate is not None:
                    assert candidate["meta"]["available_ts_us"] < ts
                    assert candidate["meta"]["available_row"] < row
                sampler.current = candidate
                packet = sampler.sample(row, ts, instrument="GC")
                prices = [x[0] for x in bar]
                record = dict(bar_i=len(bars), trades=25, open=prices[0],
                              high=max(prices), low=min(prices), close=prices[-1],
                              volume=sum(x[1] for x in bar),
                              tick_start_row=bar[0][2], tick_end_row=bar[-1][2],
                              feed_trade_end_row=row, tick_close_utc_ns=(ts+OFFSET_US)*1000,
                              book_publication_policy="STRICTLY_BEFORE_TRADE_TIMESTAMP",
                              l2=packet, outcomes_computed=False, forecast_computed=False)
                bars.append(record)
                stats["bar_gate_"+packet["gate"]] += 1
                if packet["values"] is not None:
                    stats["bars_with_full_ofi_window"] += packet["values"]["full_window_available"]
                bar = []
        i += 1
    stats["trades_processed"] = ntr
    stats["complete_25tick_bars"] = len(bars)
    stats["partial_bar_trade_count"] = len(bar)
    stats["terminal_group_not_published"] = 1
    return bars, dict(stats)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ticks", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--book-module", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--file", required=True, choices=["20260531", "20260615"])
    args = ap.parse_args()
    p = Path(args.ticks)
    if hashlib.sha256(p.read_bytes()).hexdigest() != TICK_SHA:
        raise ValueError("TICK_HASH_FAIL")
    ticks = pq.read_table(p).to_pandas()
    if not ticks.contract.eq("GC 08-26").all() or not ticks.tick_type.eq("trade").all():
        raise ValueError("CONTRACT_OR_TRADE_FAIL")
    if ticks.ts_utc_ns.max() >= 1782856800000000000:
        raise ValueError("HOLDOUT_FAIL")
    raw = Path(args.raw)
    dfs, qa = audit_input(raw, args.file, json.loads((raw/"docs/manifest.json").read_text()))
    exact_tape(ticks, dfs["l1_quotes"])  # fail before replay/output on mismatch
    out = Path(args.out)
    if out.exists():
        raise ValueError("NEW_OUTPUT_REQUIRED")
    module = load_book_module(args.book_module)
    short, _ = run(dfs, ticks, module, cap_trades=2000)
    full, counts = run(dfs, ticks, module)
    if short != full[:len(short)]:
        raise ValueError("PREFIX_CHANGED")
    out.mkdir(parents=True)
    with (out/"bars_l2_PRIVATE.jsonl").open("w") as f:
        for x in full:
            f.write(json.dumps(x, allow_nan=False)+"\n")
    evidence = dict(schema="edgelab.gc_kaggle_tick_l2_probe/1", file=args.file,
                    scope="TARGETFREE_EXACT_ORDERED_TAPE_STRICT_PRE_TIMESTAMP_BOOK",
                    ordered_tape_identity="PASS", offset_hours=3,
                    clock_scope="EMPIRICAL_TWO_SOURCE_CORRESPONDENCE_FOR_THIS_FILE_ONLY",
                    same_timestamp_book_used=False, input_qa=qa, ticks_sha256=TICK_SHA,
                    counts=counts, prefix_bars_equal=len(short), outcomes_computed=False,
                    models_fitted=0, real_zones_or_mirrors_joined=0)
    (out/"evidence.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()