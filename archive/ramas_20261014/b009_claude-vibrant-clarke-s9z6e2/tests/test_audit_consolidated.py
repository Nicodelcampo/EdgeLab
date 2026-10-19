import importlib.util, numpy as np, pandas as pd
spec = importlib.util.spec_from_file_location("audit", "tools/audit_consolidated.py"); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)


def _frame(n=1000, start="2026-06-02 23:00", seed=0):
    rng = np.random.default_rng(seed); ts = (pd.Timestamp(start, tz="UTC").value + np.cumsum(rng.integers(1, 10**9, n))).astype("int64")
    px = (20000 + np.cumsum(rng.integers(-1, 2, n))).astype("int64")
    return pd.DataFrame(dict(ts_utc_ns=ts, price_ticks=px, volume=rng.integers(1, 5, n).astype("int64"), bid_ticks=px - 1, ask_ticks=px + 1, sequence=np.arange(n, dtype="int64"), instrument="NQ", contract="NQ 09-26"))


def test_audit_chunk_counts_sessions_and_flags_problems(tmp_path):
    df = _frame(); acc = dict(rows=0, per_session={}, non_monotonic=0, last_ts=None, ts_min=None, ts_max=None, exact_dup_consecutive=0, book_valid=0, volume_lt1=0, nulls={}, after_holdout=0, contracts={}, price_min=10**18, price_max=-10**18)
    A.audit_chunk(df, acc, 0.25); assert acc["rows"] == 1000 and sum(acc["per_session"].values()) == 1000 and acc["non_monotonic"] == 0 and acc["book_valid"] == 1000
    bad = df.copy(); bad.loc[10, "ts_utc_ns"] = bad.loc[5, "ts_utc_ns"]; acc2 = dict(acc, per_session={}, rows=0, non_monotonic=0, last_ts=None, ts_min=None, ts_max=None, exact_dup_consecutive=0, book_valid=0, volume_lt1=0, nulls={}, after_holdout=0, contracts={}); A.audit_chunk(bad, acc2, 0.25); assert acc2["non_monotonic"] >= 1
    exp = dict(acc["per_session"]); r = A.compare_to_resolver(acc, exp); assert r["sessions_exact"] == len(exp) and not r["sessions_missing"]
    exp2 = {**exp, "2099-01-01": 5}; r2 = A.compare_to_resolver(acc, exp2); assert r2["sessions_missing"] == ["2099-01-01"]
    p = tmp_path / "x.parquet"; df.to_parquet(p); out = A.audit_dataset("NQ", [str(p)], exp, 0.25); assert out["ok"] and out["rows"] == 1000 and out["rows_after_holdout"] == 0
    df.drop(columns=["bid_ticks"]).to_parquet(tmp_path / "y.parquet"); assert not A.audit_dataset("NQ", [str(tmp_path / "y.parquet")], exp, 0.25)["ok"]
