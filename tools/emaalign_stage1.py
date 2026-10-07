#!/usr/bin/env python3
r"""EMA-ALIGN etapa 1 (manifiesto docs/research/EMAALIGN_ESTRATEGIA_MANIFIESTO_20261007.md): EMA 200/500/2000 en 2t, 54 celdas, tick a tick.
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

SPEC = 2
SLS = (20, 40, 80)
RS = (1.0, 2.0, 4.0)
BES = (0, 1)
MODES = ("A", "B", "C")        # A mercado, B límite EMA200, C límite EMA500
CELLS = [(m, sl, R, be) for m in MODES for sl in SLS for R in RS for be in BES]
MAXWAIT = 2000
SLIP = 1.0


@numba.njit(cache=True)
def ema(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty(len(x))
    v = x[0]
    for i in range(len(x)):
        if i > 0:
            v = a * x[i] + (1 - a) * v
        out[i] = v
    return out


@numba.njit(cache=True)
def signals(e1, e2, e3):
    """Misma lógica que EdgeLabEmaAlignment.cs: alineación estricta nueva, alternada, tras 2.000 barras."""
    n = len(e1)
    out = np.zeros(n, np.int8)
    prev = 0
    last = 0
    for i in range(n):
        al = 1 if (e1[i] > e2[i] and e2[i] > e3[i]) else (-1 if (e1[i] < e2[i] and e2[i] < e3[i]) else 0)
        ent = al != 0 and al != prev
        prev = al
        if i < 1999 or not ent or al == last:
            continue
        last = al
        out[i] = al
    return out


@numba.njit(cache=True)
def exit_sim(px, t0, lim, E, d, sl, tp, be, slip):
    stop = E - d * sl
    tgt = E + d * tp
    armed = False
    t = t0
    while t <= lim:
        p = px[t]
        if (p - stop) * d <= 0:
            return ((p - slip * d) - E) * d
        if (p - tgt) * d >= 0:
            return tp
        if be == 1 and not armed and (p - E) * d >= sl:
            armed = True
            stop = E
        t += 1
    return ((px[lim] - slip * d) - E) * d


@numba.njit(cache=True)
def entry_limit(px, tick_bar, lvl, i0, lim, d):
    """Límite en la EMA (valor al cierre de la barra previa); llena si el precio la atraviesa por 1 tick."""
    t = i0
    while t <= lim:
        L = lvl[tick_bar[t] - 1]
        L = np.floor(L) if d == 1 else np.ceil(L)
        p = px[t]
        if (L - p) * d >= 1:
            prevp = px[t - 1]
            E = L if (prevp - L) * d >= 0 else p
            return t, E
        t += 1
    return -1, 0.0


@numba.njit(cache=True)
def run_all(px, tick_bar, bar_last, sig_bar, sig_dir, lim_exit, lim_wait, e200, e500, cells, slip):
    ns = len(sig_bar)
    nc = cells.shape[0]
    out = np.full((ns, nc, 2), np.nan, np.float32)
    for s in range(ns):
        b = sig_bar[s]
        d = sig_dir[s]
        i0 = bar_last[b] + 1
        for m in range(3):
            if m == 0:
                tE = i0
                Er = px[i0]
            else:
                tE, Er = entry_limit(px, tick_bar, e200 if m == 1 else e500, i0, lim_wait[s], d)
                if tE < 0:
                    continue
            for c in range(nc):
                if cells[c, 0] != m:
                    continue
                sl = cells[c, 1]
                tp = cells[c, 2] * sl
                be = int(cells[c, 3])
                for k in range(2):
                    dd = d if k == 0 else -d
                    E = Er + slip * dd if m == 0 else Er
                    if tE + 1 > lim_exit[s]:
                        out[s, c, k] = ((px[lim_exit[s]] - slip * dd) - E) * dd
                    else:
                        out[s, c, k] = exit_sim(px, tE + 1, lim_exit[s], E, dd, sl, tp, be, slip)
    return out


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    cl = np.asarray(bars.close_t, float)
    n = len(cl)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    rth = (mins >= 510) & (mins < 900)
    e200, e500, e2000 = ema(cl, 200), ema(cl, 500), ema(cl, 2000)
    sg = signals(e200, e500, e2000)
    allb = np.flatnonzero(sg)                                   # todas las señales (cada una cierra la anterior)
    tbi = np.asarray(bars.tick_bar_idx, dtype=np.int64)
    bar_last = (np.searchsorted(tbi, np.arange(n), side="right") - 1).astype(np.int64)
    sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
    sess_last_bar = np.r_[sfirst[1:] - 1, n - 1][np.searchsorted(sfirst, np.arange(n), side="right") - 1]
    px = tk.price_ticks.astype(np.float64)
    del tk, bars
    gc.collect()
    keep = appr[allb] & rth[allb] & (allb + 1 < n)
    nxt = np.r_[allb[1:], n - 1]
    sb = allb[keep]
    nb = nxt[keep]
    lim_exit = np.minimum(np.minimum(bar_last[nb] + 1, bar_last[sess_last_bar[sb]]), len(px) - 1).astype(np.int64)
    lim_wait = np.minimum(lim_exit, bar_last[np.minimum(sb + MAXWAIT, n - 1)]).astype(np.int64)
    cells = np.array([(MODES.index(m), sl, R, be) for m, sl, R, be in CELLS], dtype=np.float64)
    res = run_all(px, tbi, bar_last, sb.astype(np.int64), sg[sb].astype(np.int64), lim_exit, lim_wait, e200, e500,
                  cells, SLIP)
    np.savez_compressed(OUT / ("%s_emaalign.npz" % c), pnl=res, session=sdate[sb].astype(np.int32),
                        dir=sg[sb], bar=sb, clock=(mins[sb] // 30).astype(np.int16), cells=cells)
    print(c, ds, "barras", n, "señales", len(allb), "usadas", len(sb), "llenas A/B/C",
          [int(np.isfinite(res[:, CELLS.index((m, 20, 1.0, 0)), 0]).sum()) for m in MODES],
          "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
