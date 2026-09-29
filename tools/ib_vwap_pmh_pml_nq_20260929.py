"""Fixed NQ IB/VWAP and PMH/PML development backtest.

python runner.py preflight|test|run --raw DATA --out OUTPUT
Prices are integer NQ ticks, tick value USD5; market fills are Last-price proxies.
"""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import math

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

MIN = 60_000_000_000
BAR = 5 * MIN
NAMES = ["IB_VWAP", "PMH_PML"]
SEED = 20260929


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for b in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def clock(day, hm):
    return int(pd.Timestamp(f"{day} {hm}", tz="America/New_York").tz_convert("UTC").value)


def read_session(raw, s):
    day = pd.Timestamp(s["trade_date"]).strftime("%Y-%m-%d")
    base = clock(day, "04:00")
    path = raw / "NQ_parquet" / PureWindowsPath(s["path"]).name
    table = pq.read_table(path, columns=["ts_utc_ns", "price_ticks", "volume", "sequence"],
                          filters=[("ts_utc_ns", ">=", base), ("ts_utc_ns", "<", clock(day, "16:00"))])
    data = {k: table[k].to_numpy() for k in table.column_names}
    t, p, v, seq = (data[k] for k in ("ts_utc_ns", "price_ticks", "volume", "sequence"))
    if len(t):
        assert np.all(np.diff(t) >= 0), f"clock inversion {day}"
        assert np.all(np.diff(seq) > 0), f"source sequence not strictly increasing {day}"
        assert np.all(p > 0) and np.all(v > 0), f"invalid price/volume {day}"
    return day, base, t, p, v


def bars(base, t, p, v):
    if not len(t):
        return {}
    bins = ((t - base) // BAR).astype(int)
    unique, starts = np.unique(bins, return_index=True)
    stops = np.r_[starts[1:], len(t)]
    result = {}
    total_pv = total_v = 0.0
    for b, i, j in zip(unique, starts, stops):
        if b >= 66:
            total_pv += float(np.dot(p[i:j].astype(float), v[i:j]))
            total_v += float(v[i:j].sum())
        result[int(b)] = {
            "bin": int(b), "start_idx": int(i), "stop_idx": int(j),
            "end": int(base + (b + 1) * BAR),
            "high": int(p[i:j].max()), "low": int(p[i:j].min()), "close": int(p[j - 1]),
            "vwap": total_pv / total_v if total_v else None,
        }
    return result


def ib_signal(b):
    ib_hi = max(b[j]["high"] for j in range(66, 78))
    ib_lo = min(b[j]["low"] for j in range(66, 78))
    direction = 0
    for j in range(78, 143):
        c = b[j]
        if not direction:
            if c["close"] > ib_hi:
                direction = 1
            elif c["close"] < ib_lo:
                direction = -1
            continue  # retest must be a later bar
        outside = c["close"] > ib_hi if direction == 1 else c["close"] < ib_lo
        if (outside and c["low"] <= c["vwap"] <= c["high"]
                and direction * (c["close"] - c["vwap"]) > 0):
            stop = c["low"] - 1 if direction == 1 else c["high"] + 1
            return {"direction": direction, "signal_ns": c["end"], "stop": stop,
                    "target": None, "signal_bin": j}
    return None


def pm_signal(b, p):
    pm_hi = max(b[j]["high"] for j in range(66))
    pm_lo = min(b[j]["low"] for j in range(66))
    midpoint = (pm_hi + pm_lo) / 2
    start_long = start_short = None
    long_count = short_count = 0
    for j in range(69, 143):
        c = b[j]
        if start_long is None and c["low"] <= pm_lo - 1:
            idx = np.flatnonzero(p[c["start_idx"]:c["stop_idx"]] <= pm_lo - 1)
            start_long = int(c["start_idx"] + idx[0])
        if start_short is None and c["high"] >= pm_hi + 1:
            idx = np.flatnonzero(p[c["start_idx"]:c["stop_idx"]] >= pm_hi + 1)
            start_short = int(c["start_idx"] + idx[0])
        long_count = long_count + 1 if start_long is not None and c["close"] > pm_lo else 0
        short_count = short_count + 1 if start_short is not None and c["close"] < pm_hi else 0
        long_ok, short_ok = long_count >= 2, short_count >= 2
        if long_ok and short_ok:
            return {"invalid": "both_directions_same_bar", "signal_bin": j}
        if long_ok or short_ok:
            direction = 1 if long_ok else -1
            start = start_long if long_ok else start_short
            extreme = p[start:c["stop_idx"]].min() if long_ok else p[start:c["stop_idx"]].max()
            target = math.ceil(midpoint) if long_ok else math.floor(midpoint)
            return {"direction": direction, "signal_ns": c["end"],
                    "stop": int(extreme - direction), "target": float(target), "signal_bin": j,
                    "premarket_high": pm_hi, "premarket_low": pm_lo}
    return None


def execute(signal, t, p, cutoff):
    if signal is None:
        return None, "no_signal"
    if "invalid" in signal:
        return None, signal["invalid"]
    i = int(np.searchsorted(t, signal["signal_ns"], side="right"))
    if i >= len(t) or t[i] >= cutoff:
        return None, "no_entry_before_cutoff"
    d, entry, stop = signal["direction"], float(p[i]), float(signal["stop"])
    risk = d * (entry - stop)
    if risk <= 0:
        return None, "stop_wrong_side_at_entry"
    target = signal["target"] if signal["target"] is not None else entry + d * 2 * risk
    if d * (target - entry) <= 0:
        return None, "target_already_reached_at_entry"
    end = int(np.searchsorted(t, cutoff, side="left"))
    if end >= len(t):
        return None, "no_time_exit_tick"
    path = p[i:end]
    stops = np.flatnonzero(d * (path - stop) <= 0)
    targets = np.flatnonzero(d * (path - target) >= 0)
    si, ti = int(stops[0]) if len(stops) else len(path), int(targets[0]) if len(targets) else len(path)
    if si < len(path) and si <= ti:
        ex, exit_idx, why = float(path[si]), i + si, "stop"
    elif ti < len(path):
        ex, exit_idx, why = float(target), i + ti, "target"
    else:
        ex, exit_idx, why = float(p[end]), end, "time"
    ticks = d * (ex - entry)
    trade = {**signal, "entry_ns": int(t[i]), "exit_ns": int(t[exit_idx]),
             "entry_ticks": entry, "stop_ticks": stop, "target_ticks": float(target),
             "exit_ticks": ex, "risk_ticks": risk, "gross_ticks": ticks,
             "gross_R": ticks / risk, "R_2ticks": (ticks - 2) / risk,
             "R_4ticks": (ticks - 4) / risk, "exit_reason": why}
    return trade, "trade"


def preflight(raw, out):
    code = digest(__file__)
    catalog_path = raw / "catalogs/NQ_ext_2026q3_sessions_catalog.json"
    cat = json.loads(catalog_path.read_text())
    sources = {str(catalog_path.relative_to(raw)): digest(catalog_path)}
    parquet_rows = {}
    for mp in sorted((raw / "NQ_parquet").glob("*manifest_ext.json")):
        m = json.loads(mp.read_text())
        pp = mp.with_name(mp.name.replace("manifest_ext.json", "ticks_ext.parquet"))
        assert digest(pp) == m["parquet_sha256"], f"hash mismatch {pp}"
        pf = pq.ParquetFile(pp)
        assert pf.metadata.num_rows == m["rows"]
        assert m["tick_size"] == 0.25
        assert m["window_utc_ns"][1] <= clock("2026-10-01", "00:00")
        parquet_rows[pp.name] = int(pf.metadata.num_rows)
        sources[str(mp.relative_to(raw))] = digest(mp)
        sources[str(pp.relative_to(raw))] = m["parquet_sha256"]
    records = []
    for s in cat["sessions"]:
        day, base, t, p, v = read_session(raw, s)
        assert day < "2026-10-01"
        b = bars(base, t, p, v)
        rth_missing = [j for j in range(66, 144) if j not in b]
        pm_missing = [j for j in range(66) if j not in b]
        rth_mask = (t >= clock(day, "09:30")) & (t < clock(day, "16:00"))
        rt = t[rth_mask]
        records.append({
            "day": day, "contract": s["contract"], "source_path": PureWindowsPath(s["path"]).name,
            "ticks_04_16": len(t), "rth_ticks": int(rth_mask.sum()),
            "rth_max_gap_s": float(np.diff(rt).max() / 1e9) if len(rt) > 1 else None,
            "missing_rth_bins": rth_missing, "missing_pm_bins": pm_missing,
            "IB_VWAP_eligible": not rth_missing,
            "PMH_PML_eligible": not rth_missing and not pm_missing,
        })
    result = {"dataset": "nicolasbuttaro/edgelab-nq-nt8-2026q3-l2ctx", "version": 1,
              "raw_files_sha256": sources, "parquet_rows": parquet_rows,
              "runner_sha256": code, "head_start": "3fc19fc9479742faa7520ca00b98d43b4d592db1",
              "scope": "NQ catalog Q3 development only, no L2 filters",
              "sessions": records, "outcomes_opened": False}
    (out / "preflight.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"catalog_sessions": len(records),
                      "eligible": {n: sum(s[n + "_eligible"] for s in records) for n in NAMES},
                      "hashes": "OK", "runner_sha256": code}))


def joint_bootstrap(trades, sessions, B=10000):
    nums = np.zeros((len(sessions), 2))
    den = np.zeros_like(nums)
    mapping = {s: i for i, s in enumerate(sessions)}
    for tr in trades:
        j = NAMES.index(tr["strategy"])
        nums[mapping[tr["day"]], j] = tr["R_2ticks"]
        den[mapping[tr["day"]], j] = 1
    assert np.all(den.sum(axis=0) > 0)
    means = nums.sum(axis=0) / den.sum(axis=0)
    rng = np.random.default_rng(SEED)
    weights = rng.multinomial(len(sessions), np.full(len(sessions), 1 / len(sessions)), size=B)
    bd = weights @ den
    assert (bd > 0).all()
    bm = weights @ nums / bd
    se = bm.std(axis=0, ddof=1)
    assert (se > 0).all()
    z = (bm - means) / se
    max_abs = np.abs(z).max(axis=1)
    critical = float(np.quantile(max_abs, .95))
    output = {}
    for j, name in enumerate(NAMES):
        nt = int(den[:, j].sum())
        output[name] = {"trades": nt, "trade_sessions": nt, "mean_R_2ticks": float(means[j]),
                        "bootstrap_se": float(se[j]), "t": float(means[j] / se[j]),
                        "ci95_simultaneous": [float(means[j] - critical * se[j]),
                                              float(means[j] + critical * se[j])],
                        "ci95_percentile": np.quantile(bm[:, j], [.025, .975]).tolist(),
                        "p_maxT": float((1 + (max_abs >= abs(means[j] / se[j])).sum()) / (B + 1)),
                        "adequate_sample": nt >= 30 and nt >= 20}
    return {"B": B, "seed": SEED, "common_universe_sessions": len(sessions),
            "weights_sha256": hashlib.sha256(weights.tobytes()).hexdigest(),
            "t_critical_two_sided": critical, "cells": output}


def run(raw, out):
    pre = json.loads((out / "preflight.json").read_text())
    assert pre["runner_sha256"] == digest(__file__), "runner changed after preflight"
    for rel, sha in pre["raw_files_sha256"].items():
        assert digest(raw / rel) == sha
    trades, decisions = [], []
    cat = json.loads((raw / "catalogs/NQ_ext_2026q3_sessions_catalog.json").read_text())
    for s, qc in zip(cat["sessions"], pre["sessions"]):
        if not qc["IB_VWAP_eligible"] and not qc["PMH_PML_eligible"]:
            for name in NAMES:
                decisions.append({"day": qc["day"], "strategy": name, "status": "excluded_coverage"})
            continue
        day, base, t, p, v = read_session(raw, s)
        b = bars(base, t, p, v)
        for name in NAMES:
            if not qc[name + "_eligible"]:
                decisions.append({"day": day, "strategy": name, "status": "excluded_coverage"})
                continue
            signal = ib_signal(b) if name == "IB_VWAP" else pm_signal(b, p)
            trade, status = execute(signal, t, p, clock(day, "15:55"))
            decisions.append({"day": day, "strategy": name, "status": status})
            if trade:
                trades.append({**trade, "strategy": name, "day": day, "contract": s["contract"]})
    universe = [s["day"] for s in pre["sessions"]]
    counts = {n: sum(t["strategy"] == n for t in trades) for n in NAMES}
    # Do not manufacture unstable CIs when a declared primary has too few trades.
    stats = joint_bootstrap(trades, universe) if all(counts[n] >= 30 for n in NAMES) else {
        "cells": {}, "reason": "declared_family_inconclusive_sample",
        "B": 0, "counts": counts, "required_trades_per_strategy": 30}
    summary = {}
    for name in NAMES:
        ts = [t for t in trades if t["strategy"] == name]
        if not ts:
            summary[name] = {"trades": 0, "state": "INCONCLUSIVE_NO_TRADES"}
            continue
        rr = np.array([x["R_2ticks"] for x in ts])
        gross = np.array([x["gross_ticks"] for x in ts])
        risks = np.array([x["risk_ticks"] for x in ts])
        equity = np.cumsum(rr)
        dd = equity - np.maximum.accumulate(np.r_[0, equity])[1:]
        cell = stats["cells"].get(name, {})
        summary[name] = {**cell, "trades": len(ts), "trade_sessions": len(ts),
                         "adequate_sample": len(ts) >= 30,
                         "mean_R_2ticks": float(np.mean(rr)),
                         "mean_gross_R": float(np.mean(gross / risks)),
                         "mean_R_4ticks": float(np.mean((gross - 4) / risks)),
                         "mean_ticks_after_2": float(np.mean(gross - 2)),
                         "breakeven_commission_usd_roundtrip": float(np.mean(gross - 2) * 5),
                         "max_drawdown_R": float(-dd.min()),
                         "R_quantiles": dict(zip(["p05", "p25", "p50", "p75", "p95"],
                                                np.quantile(rr, [.05, .25, .5, .75, .95]).tolist())),
                         "state": "INCONCLUSIVE_SAMPLE" if not cell.get("adequate_sample") else
                                  ("POSITIVE_EXPLORATORY" if cell["ci95_simultaneous"][0] > 0 else
                                   "NEGATIVE" if cell["ci95_simultaneous"][1] < 0 else "NO_EFFECT_DETECTED")}
    # Independent headline check through trade-record scalar arithmetic.
    for name, c in summary.items():
        ts = [t for t in trades if t["strategy"] == name]
        if ts:
            independent = sum((t["direction"] * (t["exit_ticks"] - t["entry_ticks"]) - 2)
                              / t["risk_ticks"] for t in ts) / len(ts)
            assert abs(independent - c["mean_R_2ticks"]) < 1e-12
    assert len({(t["day"], t["strategy"]) for t in trades}) == len(trades)
    assert len(decisions) == 2 * len(universe)
    result = {"summary": summary, "joint_bootstrap": stats, "trades": trades, "decisions": decisions,
              "provenance": pre, "runner_sha256": digest(__file__),
              "checks": {"independent_R_recomputation": True, "one_trade_per_session_strategy": True,
                         "decisions_reconcile": True, "shared_bootstrap_weights": True},
              "limitations": ["Last-price proxy, not real market fills", "commission excluded",
                              "coverage bins not a completeness certificate", "development only, no confirmation"]}
    (out / "result.json").write_text(json.dumps(result, indent=2))
    pd.DataFrame(trades).to_csv(out / "trades.csv", index=False)
    pd.DataFrame(decisions).to_csv(out / "decisions.csv", index=False)
    print(json.dumps(summary, indent=2))


def tests():
    assert clock("2026-07-01", "09:30") == pd.Timestamp("2026-07-01 13:30", tz="UTC").value
    assert clock("2026-01-05", "09:30") == pd.Timestamp("2026-01-05 14:30", tz="UTC").value
    # Exact close tick is excluded, following tick becomes entry; first barrier wins.
    sig = {"direction": 1, "signal_ns": 10, "stop": 95, "target": 110}
    t = np.array([9, 10, 11, 12, 13, 20])
    p = np.array([100, 999, 100, 111, 94, 103])
    tr, status = execute(sig, t, p, 20)
    assert status == "trade" and tr["entry_ns"] == 11 and tr["exit_reason"] == "target"
    assert tr["gross_ticks"] == 10 and tr["R_2ticks"] == 1.6
    p = np.array([100, 999, 100, 93, 111, 103])
    tr, _ = execute(sig, t, p, 20)
    assert tr["exit_reason"] == "stop" and tr["gross_ticks"] == -7  # adverse gap
    sig2 = {"direction": -1, "signal_ns": 10, "stop": 105, "target": 90}
    p = np.array([100, 999, 100, 89, 110, 103])
    tr, _ = execute(sig2, t, p, 20)
    assert tr["gross_ticks"] == 10 and tr["exit_reason"] == "target"
    p = np.array([100, 999, 100, 101, 102, 103])
    tr, _ = execute(sig, t, p, 20)
    assert tr["exit_reason"] == "time" and tr["exit_ns"] == 20
    invalid = dict(sig, target=100)
    assert execute(invalid, t, p, 20)[1] == "target_already_reached_at_entry"
    base = clock("2026-07-01", "04:00")
    tt = np.array([base + 66 * BAR, base + 67 * BAR - 1, base + 67 * BAR])
    bb = bars(base, tt, np.array([100, 102, 110]), np.array([1, 3, 1]))
    assert bb[66]["close"] == 102 and bb[66]["vwap"] == 101.5
    assert bb[67]["close"] == 110
    # Synthetic bars: no IB retest in breakout bar; first later retest.
    bb = {j: {"high": 110, "low": 100, "close": 105, "vwap": 105, "end": j * BAR}
          for j in range(66, 144)}
    bb[78].update(high=120, low=100, close=115, vwap=110)
    bb[79].update(high=120, low=109, close=116, vwap=110)
    assert ib_signal(bb)["signal_bin"] == 79
    # PM long sweep then two closes; stop uses post-sweep extreme.
    pp = []
    bb = {}
    for j in range(144):
        vals = [105, 110, 100, 105] if j < 66 else [105, 106, 104, 105]
        if j == 69:
            vals = [100, 99, 100, 101]
        if j == 70:
            vals = [101, 103, 101, 102]
        i = len(pp)
        pp.extend(vals)
        bb[j] = {"start_idx": i, "stop_idx": len(pp), "high": max(vals),
                 "low": min(vals), "close": vals[-1], "end": (j + 1) * BAR}
    signal = pm_signal(bb, np.array(pp))
    assert signal["signal_bin"] == 70 and signal["direction"] == 1 and signal["stop"] == 98
    bb[69].update(high=111)
    pp[bb[69]["start_idx"]] = 111
    assert pm_signal(bb, np.array(pp))["invalid"] == "both_directions_same_bar"
    synth = [{"day": f"s{i}", "strategy": n, "R_2ticks": (-1 if i % 3 == 0 else 2) + j * .1}
             for i in range(40) for j, n in enumerate(NAMES)]
    bs = joint_bootstrap(synth, [f"s{i}" for i in range(40)], B=200)
    assert bs["cells"]["IB_VWAP"]["trades"] == 40
    assert abs(bs["cells"]["IB_VWAP"]["mean_R_2ticks"] - .95) < 1e-12
    assert bs["weights_sha256"] == joint_bootstrap(synth, [f"s{i}" for i in range(40)], B=200)["weights_sha256"]
    print("PASS: timezone/DST, bar boundaries, tick VWAP, first breakout/retest, PM confirmation,"
          " ambiguous directions, strict-next-tick entry, long/short TP, stop gap, time exit,"
          " costs, target already reached")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preflight", "test", "run"])
    ap.add_argument("--raw", type=Path, default=Path("/data/raw/nq_ib_pmh_v1"))
    ap.add_argument("--out", type=Path, default=Path("/data/analysis/nq_ib_pmh/output"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.mode == "test":
        tests()
    elif args.mode == "preflight":
        preflight(args.raw, args.out)
    else:
        run(args.raw, args.out)