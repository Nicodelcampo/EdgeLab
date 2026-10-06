#!/usr/bin/env python3
r"""VTD-DIR etapa 1 (propuesta docs/research/VTD_DIR_PROPUESTA_20261006.md + enmienda 1): features de direccion en barras 150t.
Por contrato (env AVCL_CONTRACTS, separados por coma): ticks -> barras 50t -> footprint NT8 -> run_full (parámetros
congelados de VOL-1). Guarda en /kaggle/working: <c>_bars.npz, <c>_blocks.parquet, <c>_zones.parquet."""
from __future__ import annotations

import dataclasses
import gc
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

KAGGLE = Path("/kaggle/input").exists()
if KAGGLE:
    _roots = [Path("/kaggle/input"), *Path("/kaggle/input").glob("datasets/*")]
    os.environ["EDGELAB_DATA_ROOTS"] = os.pathsep.join(str(r) for r in _roots)
    sys.path.insert(0, str(next(p.parent for r in _roots for p in r.glob("edgelab-data-catalog/**/edgelab_data.py"))))
    sys.path.insert(0, str(next(p.parent.parent for r in _roots for p in r.glob("edgelab-code-avcl-fast/**/edgelab/__init__.py"))))
    OUT = Path("/kaggle/working")
else:
    os.environ.setdefault("EDGELAB_DATA_ROOTS", r"E:\_edgelab_roots")
    sys.path.insert(0, r"E:\EdgeLab-vibrant\docs\data_catalog")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    OUT = Path(os.environ.get("AVCL_OUT", r"C:\tmp_avcl_vol1"))
OUT.mkdir(parents=True, exist_ok=True)

import edgelab_data as ed  # noqa: E402
from scipy.stats import norm  # noqa: E402
from edgelab.bridge import bars as B  # noqa: E402
from edgelab.bridge import ticks as T  # noqa: E402
from edgelab.bridge.indicators.avolclusterpoi_fast import run_full_fast as run_full  # noqa: E402  (idéntico, ~6-10x)
from edgelab.bridge.sessions import session_end_ns  # noqa: E402

PARAMS = dict(window_bars=10, median_multiplier=2.0, max_gap_ticks=1, min_cluster_ticks=2, use_session_buckets=True,
              time_bucket_minutes=30, lookback_sessions=20, detection_percentile=95.0, min_samples_per_bucket=20,
              enable_predictive_filter=False, use_topk_hot_cells=False, invalidation_mode="None", max_age_bars=500)
HS = (10, 50, 200)
SEED, NPERM, NBOOT, NTESTS, MAXCTRL = 20261005, int(os.environ.get("AVCL_NPERM", 20000)), 2000, 12, 5
END_NS = pd.Timestamp("2026-09-30 22:00", tz="UTC").value
CT = "America/Chicago"
DESDE, HASTA = os.environ.get("AVCL_DESDE", "2025-07-01"), os.environ.get("AVCL_HASTA", "2026-09-30")
INST = os.environ.get("AVCL_INST", "MNQ")          # MNQ = paridad validada; MYM = sin paridad propia (exploratorio)
TICKS_BAR = 50


def ct_minute_of_day(ts_ns):
    """Minuto del día en hora de Chicago; convierte una vez por minuto único (mismo resultado que por tick)."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    um, inv = np.unique(ts // 60_000_000_000, return_inverse=True)
    c = pd.to_datetime(um * 60_000_000_000, utc=True).tz_convert(CT)
    return np.asarray(c.hour * 60 + c.minute)[inv]


def session_end_vec(end_ns):
    """Igual que session_end_ns(int(x)) por barra (verificado en 200.000 instantes 2025-06 → 2026-09): próximo cierre
    16:00 CT lun-vie estrictamente posterior."""
    end = np.asarray(end_ns, dtype=np.int64)
    d0 = pd.Timestamp(int(end.min()), tz="UTC").tz_convert(CT).normalize() - pd.Timedelta(days=1)
    d1 = pd.Timestamp(int(end.max()), tz="UTC").tz_convert(CT).normalize() + pd.Timedelta(days=8)
    days = pd.date_range(d0.tz_localize(None), d1.tz_localize(None), freq="D")
    days = days[days.weekday < 5]
    closes = np.sort((days + pd.Timedelta(hours=16)).tz_localize(CT).tz_convert("UTC").asi8)
    return closes[np.searchsorted(closes, end, side="right")]


def load_ticks(path, a, b, contract):
    """Sólo las columnas que usa el cálculo (ts, precio en ticks, volumen) y sin la pausa CME 16:00-17:00 CT."""
    import pyarrow.parquet as pq
    t = pq.read_table(str(path), columns=["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks"],
                      filters=[("ts_utc_ns", ">=", a), ("ts_utc_ns", "<", b)])
    ts = t.column("ts_utc_ns").to_numpy(); px = t.column("price_ticks").to_numpy(); vol = t.column("volume").to_numpy()
    bid = t.column("bid_ticks").to_numpy(zero_copy_only=False); ask = t.column("ask_ticks").to_numpy(zero_copy_only=False)
    del t
    o = np.argsort(ts, kind="stable") if len(ts) > 1 and (np.diff(ts) < 0).any() else None
    if o is not None:
        ts, px, vol, bid, ask = ts[o], px[o], vol[o], bid[o], ask[o]
    mod = ct_minute_of_day(ts)
    keep = ~((mod >= 960) & (mod < 1020))
    ts, px, vol, bid, ask = ts[keep], px[keep], vol[keep], bid[keep], ask[keep]
    tick = float(ed.RESOLVER["instruments"][INST]["tick_size"])
    return T.TickSeries(ts_ns=ts, price_ticks=px.astype(np.int64), volume=vol.astype(np.int64),
                        bid_ticks=np.nan_to_num(bid.astype(float), nan=-1).astype(np.int64),
                        ask_ticks=np.nan_to_num(ask.astype(float), nan=1 << 40).astype(np.int64), sequence=np.arange(len(ts), dtype=np.int64), tick_size=tick,
                        instrument=INST, contract=contract)


def contract_rows(c, sess):
    rows = sess[sess.contract == c]
    ds, fl = rows.groupby(["dataset", "file"]).size().idxmax()
    first = pd.Timestamp(rows.date.min()).tz_localize(CT) - pd.Timedelta(days=45)
    last = pd.Timestamp(rows.date.max()).tz_localize(CT) + pd.Timedelta(hours=16)
    return ds, fl, int(first.value), int(min(last.value, END_NS)), set(rows.date)





from edgelab.bridge.indicators.volticksdef import run as vtd_run  # noqa: E402

EMA_BARS = (20, 50, 100, 200, 500)
EMA_MIN = (15, 30, 60, 120, 240)
HS_DIR = (10, 50)
SPEC = 150


def features(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    n = len(bars.close_t)
    hi = np.asarray(bars.high_t, float); lo = np.asarray(bars.low_t, float)
    op = np.asarray(bars.open_t, float); cl = np.asarray(bars.close_t, float)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    # ---- flujo por barra (agresor) y VWAP de sesión a nivel tick
    px = tk.price_ticks.astype(float); v = tk.volume.astype(float)
    sg = np.where(tk.price_ticks >= tk.ask_ticks, 1.0, np.where(tk.price_ticks <= tk.bid_ticks, -1.0, 0.0))
    tbi = bars.tick_bar_idx
    flow = np.bincount(tbi, weights=sg * v, minlength=n)
    volb = np.bincount(tbi, weights=v, minlength=n)
    tsend = send[tbi]
    first = np.r_[True, tsend[1:] != tsend[:-1]]
    gid = np.cumsum(first) - 1
    pv = px * v
    cpv = np.cumsum(pv); cv = np.cumsum(v)
    base_pv = np.r_[0.0, cpv][np.flatnonzero(first)][gid]; base_v = np.r_[0.0, cv][np.flatnonzero(first)][gid]
    vw_t = (cpv - base_pv) / np.maximum(cv - base_v, 1e-9)
    last_tick = np.searchsorted(tbi, np.arange(n), side="right") - 1
    vwap = vw_t[last_tick]
    del tk, px, v, sg, tbi, pv, cpv, cv, vw_t
    gc.collect()
    d = pd.DataFrame(dict(bar=np.arange(n), close=cl, high=hi, low=lo, open=op, session=sdate, approved=appr, mins=mins))
    d["rth"] = (mins >= 510) & (mins < 900); d["clock"] = mins // 30
    # ATR(14) simple sobre true range
    pc = np.r_[cl[0], cl[:-1]]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    d["atr"] = pd.Series(tr).rolling(14).mean().to_numpy()
    for p in EMA_BARS:
        d["ema_b%d" % p] = pd.Series(cl).ewm(span=p, adjust=False).mean().to_numpy()
    dtm = np.r_[0.0, np.diff(end) / 6e10]
    for m in EMA_MIN:
        e = np.empty(n); e[0] = cl[0]
        al = 1.0 - np.exp(-dtm / m)
        for i in range(1, n):
            e[i] = e[i - 1] + al[i] * (cl[i] - e[i - 1])
        d["ema_m%d" % m] = e
    d["vwap"] = vwap
    f20 = pd.Series(flow).rolling(20).sum().to_numpy(); v20 = pd.Series(volb).rolling(20).sum().to_numpy()
    sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
    s0 = sfirst[np.searchsorted(sfirst, np.arange(n), side="right") - 1]
    d["imb20"] = np.where(np.arange(n) - s0 >= 20, f20 / np.maximum(v20, 1), np.nan)
    d["mom50"] = np.where(np.arange(n) - s0 >= 50, cl - np.r_[np.full(50, np.nan), cl[:-50]], np.nan)
    gk = pd.Series(send)
    d["sess_hi"] = pd.Series(hi).groupby(gk).cummax().to_numpy(); d["sess_lo"] = pd.Series(lo).groupby(gk).cummin().to_numpy()
    # régimen de amplitud (causal): A50 por minuto relativo a la mediana de las 2000 obs previas de la misma franja
    a50 = (pd.Series(hi).rolling(50).max() - pd.Series(lo).rolling(50).min()).to_numpy() / np.maximum(
        (end - np.r_[np.full(50, end[0]), end[:-50]]) / 6e10, 1e-3)
    a50 = np.where(np.arange(n) - s0 >= 50, a50, np.nan)
    rel = np.full(n, np.nan)
    for clk, idx in pd.Series(np.arange(n)).groupby(d.clock.to_numpy()):
        s = pd.Series(a50[idx.to_numpy()])
        med = s.shift(1).rolling(2000, min_periods=200).median()
        rel[idx.to_numpy()] = (s / med).to_numpy()
    d["amp_rel"] = rel
    # resultados: excursiones desde el close de b
    for H in HS_DIR:
        mxf = pd.Series(hi[::-1]).rolling(H).max().to_numpy()[::-1]   # max de [t, t+H-1]
        mnf = pd.Series(lo[::-1]).rolling(H).min().to_numpy()[::-1]
        U = np.r_[mxf[1:], np.nan] - cl; D = cl - np.r_[mnf[1:], np.nan]
        same = np.r_[send[np.minimum(np.arange(n) + H, n - 1)] == send, ]
        ok = (np.arange(n) + H < n) & same
        d["U%d" % H] = np.where(ok, U, np.nan); d["D%d" % H] = np.where(ok, D, np.nan)
    v = vtd_run(bars)
    marks = np.array([z["bar"] for z in v["zones"]], dtype=np.int64)
    d["vtd"] = False
    d.loc[marks, "vtd"] = True
    d["contract"] = c
    keep = d.vtd | (d.bar % 7 == 0)
    out = d[keep & d.approved].reset_index(drop=True)
    out.to_parquet(OUT / ("%s_dir150.parquet" % c))
    print(c, ds, "barras", n, "marcas VTD", int(d.vtd.sum()), "filas", len(out), "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        features(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
