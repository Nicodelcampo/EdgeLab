import sys, dataclasses, numpy as np, pandas as pd
sys.path.insert(0, r"E:\EdgeLab-gex")
from edgelab.bridge import ticks as T, bars as B
from edgelab.bridge.indicators.volticksdef import run
O = r"E:\EdgeLab\data\nt8_oracles\volticksdef_MNQ1226_150t_20260715_20260930.csv"
o = pd.read_csv(O, skiprows=1)
print("filas NT8", len(o), "ultima", o.bar_close_time.iloc[-1])
last = pd.Timestamp(o.bar_close_time.iloc[-1], tz="America/Argentina/Buenos_Aires")
tk = T.load_canonical_parquet(r"E:\kaggle_staging\reexport_mnq1226\MNQ_12-26_ticks_ext.parquet",
                              start_utc_ns=1784066400000000000, end_utc_ns=(last + pd.Timedelta(milliseconds=1)).value)
ct = pd.to_datetime(tk.ts_ns, utc=True).tz_convert("America/Chicago")
keep = np.asarray(~(((ct.hour * 60 + ct.minute) >= 960) & ((ct.hour * 60 + ct.minute) < 1020)))
tk = dataclasses.replace(tk, **{f: (getattr(tk, f)[keep] if getattr(tk, f) is not None else None) for f in ("ts_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks", "sequence")})
bars = B.build_tick_bars(tk, 150)
r = run(bars)
py = pd.DataFrame(r["rows"], columns=["bar", "fbos", "volume", "avg", "ratio", "thr_s", "n_s", "thr_g", "n_g", "thr", "flag"])
py["t"] = pd.to_datetime(np.asarray(bars.end_ns)[py.bar], utc=True).tz_convert("America/Argentina/Buenos_Aires").strftime("%Y-%m-%dT%H:%M:%S.%f").str[:23]
print("barras py", len(bars.close_t), "filas py", len(py), "NT8 barras (ult idx)", o.bar_index.iloc[-1] + 1)
m = o.merge(py, left_on="bar_close_time", right_on="t", how="outer", indicator=True, suffixes=("_n", "_p"))
print(m._merge.value_counts().to_dict())
b = m[m._merge == "both"]
print("idx igual", (b.bar_index == b.bar).mean())
for c in ("volume", "avg", "ratio"):
    print(c, "igual exacto", (b[c + "_n"] == b[c + "_p"]).mean(), "max dif", (b[c + "_n"] - b[c + "_p"]).abs().max())
print("fbos igual", (b.first_bar_of_session == b.fbos.astype(int)).mean())
d = (b.thr_used - b.thr).abs()
print("thr igual (ambos NaN o dif<1e-12)", ((d < 1e-12) | (b.thr_used.isna() & b.thr.isna())).mean(), "max", d.max())
print("flag NT8", int(b.flagged.sum()), "py", int(b.flag.sum()), "coinciden", int((b.flagged == b.flag.astype(int)).sum()), "/", len(b))
bad = b[b.flagged != b.flag.astype(int)]
print(bad[["bar_close_time", "ratio_n", "thr_used", "thr", "n_session", "n_s"]].head())
fb = b[(b.thr_used - b.thr).abs() > 1e-9]
print("primera dif de umbral:"); print(fb[["bar_index", "bar_close_time", "first_bar_of_session", "fbos", "n_session", "n_s", "thr_used", "thr", "thr_session", "thr_s", "thr_global", "thr_g"]].head(4).to_string())
