#!/usr/bin/env python3
r"""VTD-BRACKET etapa 1 (manifiesto docs/research/VTD_BRACKET_MANIFIESTO_20261006.md): simulacion tick a tick del bracket bilateral.
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
    names = pq.ParquetFile(str(path)).schema_arrow.names
    if "price_ticks" in names:
        t = pq.read_table(str(path), columns=["ts_utc_ns", "price_ticks", "volume", "bid_ticks", "ask_ticks"],
                          filters=[("ts_utc_ns", ">=", a), ("ts_utc_ns", "<", b)])
        ts = t.column("ts_utc_ns").to_numpy(); px = t.column("price_ticks").to_numpy(); vol = t.column("volume").to_numpy()
        bid = t.column("bid_ticks").to_numpy(zero_copy_only=False); ask = t.column("ask_ticks").to_numpy(zero_copy_only=False)
    else:                                   # archivo raw NT8 (precios, no ticks): mismo dato, otro formato
        tick0 = float(ed.RESOLVER["instruments"][INST]["tick_size"])
        t = pq.read_table(str(path), columns=["ts_utc_ns", "last", "volume", "bid", "ask"],
                          filters=[("ts_utc_ns", ">=", a), ("ts_utc_ns", "<", b)])
        ts = t.column("ts_utc_ns").to_numpy(); vol = t.column("volume").to_numpy()
        px = np.round(t.column("last").to_numpy() / tick0).astype(np.int64)
        bid = np.round(t.column("bid").to_numpy(zero_copy_only=False) / tick0)
        ask = np.round(t.column("ask").to_numpy(zero_copy_only=False) / tick0)
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





import numba  # noqa: E402
from edgelab.bridge.indicators.volticksdef import run as vtd_run  # noqa: E402

SPEC = 150
KS = (0.5, 1.0)
RS = (2.0, 3.0)
ENTRY_BARS, HOLD_BARS = 10, 50
COMM_USD = {"MNQ": 1.90, "ES": 4.50, "YM": 4.50, "RTY": 4.50, "MGC": 1.90}
TICK_USD = {"MNQ": 0.50, "ES": 12.50, "YM": 5.00, "RTY": 5.00, "MGC": 1.00}
SLIP = 1


@numba.njit(cache=True)
def sim(px, tick_bar, bar_last_tick, sess_last_tick, i0, bar0, up, dn, sl, tp, slip, entry_bars, hold_bars):
    """Bracket: buy stop >= up / sell stop <= dn desde el tick i0; SL/TP desde el precio de entrada; salida por tiempo.
    Devuelve (entró, dir, pnl_ticks, motivo) con motivo 0 = sin entrada, 1 = SL, 2 = TP, 3 = tiempo/sesión."""
    n = len(px)
    lim_entry = min(bar_last_tick[min(bar0 + entry_bars, len(bar_last_tick) - 1)], sess_last_tick)
    t = i0
    d = 0
    entry = 0.0
    while t <= lim_entry and t < n:
        p = px[t]
        if p >= up:
            d = 1
            entry = p + slip
            break
        if p <= dn:
            d = -1
            entry = p - slip
            break
        t += 1
    if d == 0:
        return 0, 0, 0.0, 0
    eb = tick_bar[t]
    lim_exit = min(bar_last_tick[min(eb + hold_bars, len(bar_last_tick) - 1)], sess_last_tick)
    t += 1
    while t <= lim_exit and t < n:
        p = px[t]
        if d == 1:
            if p <= entry - sl:
                return 1, d, (p - slip) - entry, 1
            if p >= entry + tp:
                return 1, d, tp, 2
        else:
            if p >= entry + sl:
                return 1, d, entry - (p + slip), 1
            if p <= entry - tp:
                return 1, d, tp, 2
        t += 1
    tt = min(lim_exit, n - 1)
    pe = px[tt] - slip * d
    return 1, d, (pe - entry) * d, 3


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    n = len(bars.close_t)
    hi = np.asarray(bars.high_t, float); lo = np.asarray(bars.low_t, float); cl = np.asarray(bars.close_t, float)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    rth = (mins >= 510) & (mins < 900)
    pc = np.r_[cl[0], cl[:-1]]
    tr = np.maximum(hi - lo, np.maximum(np.abs(hi - pc), np.abs(lo - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
    s0 = sfirst[np.searchsorted(sfirst, np.arange(n), side="right") - 1]
    a50 = (pd.Series(hi).rolling(50).max() - pd.Series(lo).rolling(50).min()).to_numpy() / np.maximum(
        (end - np.r_[np.full(50, end[0]), end[:-50]]) / 6e10, 1e-3)
    a50 = np.where(np.arange(n) - s0 >= 50, a50, np.nan)
    clock = mins // 30
    rel = np.full(n, np.nan)
    for clk, idx in pd.Series(np.arange(n)).groupby(clock):
        s = pd.Series(a50[idx.to_numpy()])
        rel[idx.to_numpy()] = (s / s.shift(1).rolling(2000, min_periods=200).median()).to_numpy()
    tbi = np.asarray(bars.tick_bar_idx, dtype=np.int64)
    bar_last = (np.searchsorted(tbi, np.arange(n), side="right") - 1).astype(np.int64)
    sess_last_bar = np.r_[sfirst[1:] - 1, n - 1][np.searchsorted(sfirst, np.arange(n), side="right") - 1]
    px = tk.price_ticks.astype(np.float64)
    marks = np.array([z["bar"] for z in vtd_run(bars)["zones"]], dtype=np.int64)
    del tk
    gc.collect()
    ok = lambda bb: appr[bb] & rth[bb] & np.isfinite(atr[bb]) & (atr[bb] > 0) & (bb + 1 < n)
    marks = marks[ok(marks)]
    cand = np.arange(300, n - 1, 7)
    cand = cand[ok(cand)]
    j = np.searchsorted(np.sort(marks), cand)
    ms = np.sort(marks)
    if len(ms):
        dist = np.minimum(np.abs(cand - ms[np.clip(j, 0, len(ms) - 1)]), np.abs(cand - ms[np.clip(j - 1, 0, len(ms) - 1)]))
        cand = cand[dist > 100]
    inst = c.split("_")[0]
    rows = []
    for kind, bb in (("mark", marks), ("pool", cand)):
        for k in KS:
            for R in RS:
                busy_until = -1
                for b0 in bb:
                    if kind == "mark" and b0 <= busy_until:
                        continue                                  # una posición a la vez en las marcas
                    A = atr[b0]
                    kt = max(1.0, round(k * A)); sl = max(1.0, round(A)); tp = R * sl
                    i0 = bar_last[b0] + 1
                    e, d, pnl, why = sim(px, tbi, bar_last, int(bar_last[sess_last_bar[b0]]), int(i0), int(b0),
                                         cl[b0] + kt, cl[b0] - kt, sl, tp, float(SLIP), ENTRY_BARS, HOLD_BARS)
                    if kind == "mark" and e:
                        busy_until = b0 + ENTRY_BARS + HOLD_BARS
                    rows.append((c, kind, k, R, int(b0), int(sdate[b0]), int(clock[b0]), rel[b0], e, d, pnl, why, sl))
    t = pd.DataFrame(rows, columns=["contract", "kind", "k", "R", "bar", "session", "clock", "amp_rel", "entered", "dir",
                                    "pnl_ticks", "motivo", "sl_ticks"])
    t["net_usd"] = np.where(t.entered == 1, t.pnl_ticks * TICK_USD[inst] - COMM_USD[inst], 0.0)
    t.to_parquet(OUT / ("%s_bracket.parquet" % c))
    print(c, ds, "barras", n, "marcas", len(marks), "pool", len(cand), "trades", int(t.entered.sum()), "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
