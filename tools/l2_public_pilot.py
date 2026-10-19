"""P0: exploratory BTC minute-flow proxies; no strategy or fill simulation.

Run: python pilot.py --raw BTC_1min.csv --out OUTPUT_DIRECTORY
Design: docs/research/PENDIENTES_L2_APLICACIONES_20260929.md
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def proxies(d):
    def total(side, kind):
        return d[[f"{side}_{kind}_notional_{i}" for i in range(15)]].sum(axis=1)
    sell, buy = total("bids", "market"), total("asks", "market")
    bl, bc = total("bids", "limit"), total("bids", "cancel")
    al, ac = total("asks", "limit"), total("asks", "cancel")
    return pd.DataFrame({
        "market_proxy": (buy - sell) / (buy + sell).replace(0, np.nan),
        "net_limit_proxy": ((bl - bc) - (al - ac)) /
                           (bl + bc + al + ac).replace(0, np.nan),
    })


def fit(x, y):
    mean, std = x.mean(axis=0), x.std(axis=0)
    std[std < 1e-12] = 1.0
    z = np.column_stack([np.ones(len(x)), (x - mean) / std])
    penalty = np.diag([0.0] + [1e-6] * x.shape[1])
    beta = np.linalg.solve(z.T @ z + penalty, z.T @ y)
    return {"mean": mean, "std": std, "beta": beta}


def predict(model, x):
    z = np.column_stack([np.ones(len(x)), (x - model["mean"]) / model["std"]])
    return z @ model["beta"]


def metrics(y, p):
    mse = float(np.mean((y - p) ** 2))
    variance = float(np.mean((y - y.mean()) ** 2))
    return {"rmse_bps": mse ** 0.5, "mse_bps2": mse,
            "r2_test_mean": 1 - mse / variance}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    source = args.raw.read_bytes()
    d = pd.read_csv(args.raw)
    t = pd.to_datetime(d.system_time, utc=True, errors="raise")
    assert t.is_monotonic_increasing and t.is_unique
    assert d.drop(columns="system_time").notna().all().all()
    assert (d.midpoint > 0).all() and (d.spread > 0).all()
    assert (d.filter(regex="notional") >= 0).all().all()
    assert np.array_equal(d["Unnamed: 0"].to_numpy(), np.arange(len(d)))
    # The unnamed column is a serial index, never an additive measurement.
    d = d.drop(columns="Unnamed: 0")
    f = proxies(d)
    logp = np.log(d.midpoint.to_numpy())
    f["ret_prev_bps"] = np.r_[np.nan, np.diff(logp) * 10000]
    f["abs_ret_prev_bps"] = f.ret_prev_bps.abs()
    f["spread_bps"] = d.spread / d.midpoint * 10000
    f["target_next_bps"] = f.ret_prev_bps.shift(-1)
    f["time"] = t
    f["target_time"] = t.shift(-1)
    f["day"] = t.dt.strftime("%Y-%m-%d")
    gap = t.diff().dt.total_seconds()
    # Exact 60-second transitions only; no crossing missing intervals.
    consecutive = gap.eq(60) & gap.shift(-1).eq(60)
    observed_days = sorted(f.day.unique())
    interior_days = observed_days[1:-1]
    assert len(interior_days) >= 6
    cutoff = interior_days[int(len(interior_days) * 2 / 3)]
    finite = np.isfinite(f[["market_proxy", "net_limit_proxy",
                            "ret_prev_bps", "spread_bps", "target_next_bps"]]).all(axis=1)
    eligible = consecutive & finite & f.day.isin(interior_days)
    # Training target must precede the first test calendar day.
    boundary = pd.Timestamp(cutoff, tz="UTC")
    train = eligible & (f.time < boundary) & (f.target_time < boundary)
    test = eligible & (f.time >= boundary)
    assert not ((f.loc[train, "target_time"] >= boundary).any())
    base_names = ["ret_prev_bps", "abs_ret_prev_bps", "spread_bps"]
    augmented_names = base_names + ["market_proxy", "net_limit_proxy"]
    ytrain = f.loc[train, "target_next_bps"].to_numpy()
    ytest = f.loc[test, "target_next_bps"].to_numpy()
    baseline = fit(f.loc[train, base_names].to_numpy(), ytrain)
    augmented = fit(f.loc[train, augmented_names].to_numpy(), ytrain)
    pbase = predict(baseline, f.loc[test, base_names].to_numpy())
    paug = predict(augmented, f.loc[test, augmented_names].to_numpy())
    pred = f.loc[test, ["time", "day", "target_next_bps"]].copy()
    pred["baseline_prediction_bps"] = pbase
    pred["l2_prediction_bps"] = paug
    pred["baseline_sq_error"] = (ytest - pbase) ** 2
    pred["l2_sq_error"] = (ytest - paug) ** 2
    day_records = []
    for day, g in pred.groupby("day"):
        b = metrics(g.target_next_bps.to_numpy(), g.baseline_prediction_bps.to_numpy())
        a = metrics(g.target_next_bps.to_numpy(), g.l2_prediction_bps.to_numpy())
        day_records.append({"day": day, "n": len(g), "baseline_rmse_bps": b["rmse_bps"],
                            "l2_rmse_bps": a["rmse_bps"],
                            "delta_mse": a["mse_bps2"] - b["mse_bps2"]})
    bm, am = metrics(ytest, pbase), metrics(ytest, paug)
    # Descriptive correlations, not causal evidence or independent tests.
    correlations = {}
    for name in ("market_proxy", "net_limit_proxy"):
        correlations[name] = {
            "current_minute": float(f.loc[eligible, name].corr(f.loc[eligible, "ret_prev_bps"])),
            "next_minute": float(f.loc[eligible, name].corr(f.loc[eligible, "target_next_bps"])),
        }
    # Independent raw-file audit via stdlib CSV, not pandas aggregation.
    with args.raw.open() as handle:
        raw_count = sum(1 for _ in csv.DictReader(handle))
    assert raw_count == len(d)
    independent_mse_b = sum((float(a) - float(b)) ** 2 for a, b in zip(ytest, pbase)) / len(ytest)
    independent_mse_a = sum((float(a) - float(b)) ** 2 for a, b in zip(ytest, paug)) / len(ytest)
    assert abs(independent_mse_b - bm["mse_bps2"]) < 1e-10
    assert abs(independent_mse_a - am["mse_bps2"]) < 1e-10
    # Causality fixture: changing future rows must not change earlier features.
    changed = d.copy()
    split = len(d) // 2
    cols = changed.filter(regex="notional").columns
    changed.loc[split:, cols] *= 2
    assert np.allclose(proxies(d).iloc[:split], proxies(changed).iloc[:split], equal_nan=True)
    improvement = 100 * (bm["rmse_bps"] - am["rmse_bps"]) / bm["rmse_bps"]
    evidence = {
        "status": "EXPLORATORY_LAB_ONLY_NOT_STRATEGY",
        "head_start": "632dedd316d246cb43545ea8b758b6a866c655ac",
        "head_end": None, "code_identity": "standalone_file_sha256_not_git_worktree",
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "plan_registered_commit": "632dedd316d246cb43545ea8b758b6a866c655ac",
        "dataset": "martinsn/high-frequency-crypto-limit-order-book-data",
        "version": 1, "file": args.raw.name, "sha256": hashlib.sha256(source).hexdigest(),
        "raw_rows": raw_count, "raw_columns": 156,
        "window_utc": [t.iloc[0].isoformat(), t.iloc[-1].isoformat()],
        "duplicates": 0, "null_cells": 0, "invalid_spreads": 0,
        "non_exact_60s_intervals": int((~gap.iloc[1:].eq(60)).sum()),
        "interior_gap_exclusions": int((f.day.isin(interior_days) & ~consecutive).sum()),
        "interior_nonfinite_proxy_exclusions": int((f.day.isin(interior_days) & consecutive & ~finite).sum()),
        "zero_market_denominator_raw_rows": int(f.market_proxy.isna().sum()),
        "interior_days": interior_days, "test_start_day": cutoff,
        "train_rows": int(train.sum()), "test_rows": int(test.sum()),
        "row_reconciliation": {
            "edge_day_rows": int((~f.day.isin(interior_days)).sum()),
            "interior_excluded_gap_or_nonfinite": int((f.day.isin(interior_days) & ~eligible).sum()),
            "boundary_purged": int((eligible & ~train & ~test).sum()),
        },
        "warning_resolutions": [
            "system_time parsed UTC; no assumed exchange timestamp",
            "Unnamed: 0 verified serial row index and dropped; summation plausibility hint inapplicable",
            "first/last partial calendar days excluded by prospective plan; interior days have gaps, not 1440-row completeness",
            "zero denominators return missing, not imputed; excluded as nonfinite",
            "aggregated moving level ranks are not fixed price queues",
        ],
        "baseline": bm, "l2_augmented": am,
        "rmse_improvement_percent": improvement,
        "correlations": correlations, "by_day": day_records,
        "coefficients_standardized": {
            "baseline": dict(zip(["intercept"] + base_names, baseline["beta"].tolist())),
            "l2_augmented": dict(zip(["intercept"] + augmented_names, augmented["beta"].tolist())),
        },
        "checks": {"raw_rows_independently_counted": True, "mse_independent_sum": True,
                   "no_future_feature_dependency_fixture": True, "no_train_target_crosses_test": True},
        "limitations": [
            "one asset, approximately 12 days; only four evaluation days",
            "timestamps are system_time; publication lag not verified",
            "minute snapshots/flows cannot identify intrasecond sequence, wall persistence at absolute prices or real fills",
            "market and net-limit proxies are NOT exact event OFI or queue imbalance",
            "side convention and aggregation mechanics are based on dataset labels, not audited against raw executions",
            "no costs, latency, own impact, strategy trades or transfer to NQ tested",
            "evaluation is exposed exploratory data; no significance/confirmatory claim",
        ],
        "comparison_plan": [{
            "grain": "UTC day", "population": "eligible next-minute predictions, chronological evaluation",
            "unit": "basis points RMSE", "finding": "compare fixed baseline with two L2 proxies on every evaluation day",
            "derivation": "sqrt(mean((next-minute log return bps - prediction)^2))",
            "disposition": "chart", "reason": "retain day-level direction and any reversal, not pooled headline alone"},
            {"grain": "eligible minute", "population": "all interior days",
             "unit": "Pearson correlation", "finding": "contemporaneous association is distinct from prediction",
             "derivation": "corr(proxy, current/next minute log return)",
             "disposition": "table", "reason": "secondary diagnostic; no extra plot needed"}],
    }
    assert sum(evidence["row_reconciliation"].values()) + train.sum() + test.sum() == len(d)
    f.loc[train | test].to_csv(args.out / "features.csv", index=False)
    pred.to_csv(args.out / "predictions.csv", index=False)
    (args.out / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False))
    print(json.dumps({k: evidence[k] for k in
                      ["raw_rows", "train_rows", "test_rows", "baseline", "l2_augmented",
                       "rmse_improvement_percent", "correlations", "by_day", "checks"]}, indent=2))


if __name__ == "__main__":
    main()