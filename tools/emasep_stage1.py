#!/usr/bin/env python3
r"""EMA-SEP etapa 1 (manifiesto docs/research/EMASEP_CONTRA_MANIFIESTO_20261007.md): contrarian por separacion de 3 EMAs, 10t.
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

SPEC = 10
PCTS = (90.0, 95.0, 99.0)
FILTS = ("ninguno", "desaceleracion", "climax_vol")
MODES = ("A", "B", "C")        # A mercado, B límite 10 ticks más estirado, C vela de giro
SLS = (20, 40, 80)
RS = (1.0, 2.0, 4.0)
BES = (0, 1)
EXITS = [(sl, R, be) for sl in SLS for R in RS for be in BES]
WAIT = 50
SLIP = 1.0
LOOKBACK_SESS = 20
SAMPLE = 200


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
def run_all(px, bar_last, op, cl, sig_bar, sig_dir, lim_sess, exits, slip):
    """sig_dir = dirección del TRADE (contraria a la alineación). Devuelve (nsig, 3 modos, nexits, 2 direcciones)."""
    ns = len(sig_bar)
    ne = exits.shape[0]
    nb = len(cl)
    out = np.full((ns, 3, ne, 2), np.nan, np.float32)
    for s in range(ns):
        b = sig_bar[s]
        d = sig_dir[s]
        lim = lim_sess[s]
        i0 = bar_last[b] + 1
        if i0 > lim:
            continue
        for m in range(3):
            tE = -1
            Er = 0.0
            if m == 0:
                tE = i0
                Er = px[i0]
            elif m == 1:
                L = cl[b] - d * 10.0                   # trade corto (d=-1): vender 10 ticks más arriba
                wl = min(bar_last[min(b + WAIT, nb - 1)], lim)
                t = i0
                while t <= wl:
                    if (L - px[t]) * d >= 1:
                        tE = t
                        Er = L if (px[t - 1] - L) * d >= 0 else px[t]
                        break
                    t += 1
            else:
                for k in range(b + 1, min(b + WAIT, nb - 2) + 1):
                    if bar_last[k] + 1 > lim:
                        break
                    if (cl[k] - op[k]) * d > 0:          # vela que cierra a favor del trade (en contra de la tendencia)
                        tE = bar_last[k] + 1
                        Er = px[tE]
                        break
            if tE < 0 or tE > lim:
                continue
            for c in range(ne):
                sl = exits[c, 0]
                tp = exits[c, 1] * sl
                be = int(exits[c, 2])
                for k2 in range(2):
                    dd = d if k2 == 0 else -d
                    E = Er if m == 1 else Er + slip * dd
                    if tE + 1 > lim:
                        out[s, m, c, k2] = ((px[lim] - slip * dd) - E) * dd
                    else:
                        out[s, m, c, k2] = exit_sim(px, tE + 1, lim, E, dd, sl, tp, be, slip)
    return out


def thresholds(sep, sdate, clock, rng):
    """Percentil causal: muestra de SAMPLE valores por (sesión, franja); umbral con las 20 sesiones previas."""
    us = np.unique(sdate)
    pos = {s: i for i, s in enumerate(us)}
    si = np.array([pos[s] for s in sdate])
    th = np.full((len(PCTS), len(sep)), np.nan)
    samp = {}
    for (s, ck), idx in pd.Series(np.arange(len(sep))).groupby([si, clock]):
        v = sep[idx.to_numpy()]
        v = v[np.isfinite(v)]
        samp[(s, ck)] = rng.choice(v, min(SAMPLE, len(v)), replace=False) if len(v) else v
    for (s, ck), idx in pd.Series(np.arange(len(sep))).groupby([si, clock]):
        prev = [samp.get((j, ck)) for j in range(max(0, s - LOOKBACK_SESS), s)]
        prev = [p for p in prev if p is not None and len(p)]
        if len(prev) < 10:
            continue
        pool = np.concatenate(prev)
        q = np.percentile(pool, PCTS)
        th[:, idx.to_numpy()] = q[:, None]
    return th


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    cl = np.asarray(bars.close_t, float)
    op = np.asarray(bars.open_t, float)
    vol = np.asarray(bars.volume, float)
    n = len(cl)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    clock = mins // 30
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    rth = (mins >= 510) & (mins < 900)
    e1, e2, e3 = ema(cl, 200), ema(cl, 500), ema(cl, 2000)
    al = np.where((e1 > e2) & (e2 > e3), 1, np.where((e1 < e2) & (e2 < e3), -1, 0))
    sep = np.where(al != 0, np.minimum(np.abs(e1 - e2), np.abs(e2 - e3)), 0.0)
    sep[:1999] = np.nan
    th = thresholds(sep, sdate, clock, np.random.default_rng(20261007))
    # agotamiento (causal, en la barra de la señal; t = dirección de la tendencia)
    mom = cl - np.r_[np.full(20, np.nan), cl[:-20]]
    mom_prev = np.r_[np.full(20, np.nan), mom[:-20]]
    # clímax: en barras de ticks el volumen por barra es casi constante, así que el clímax es VELOCIDAD:
    # las últimas 20 barras se formaron en menos de la mitad del tiempo típico (mediana de las 200 previas)
    d20 = (end - np.r_[np.full(20, end[0]), end[:-20]]).astype(float)
    d20_ref = pd.Series(d20).shift(20).rolling(200, min_periods=100).median().to_numpy()
    tbi = np.asarray(bars.tick_bar_idx, dtype=np.int64)
    bar_last = (np.searchsorted(tbi, np.arange(n), side="right") - 1).astype(np.int64)
    sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
    sess_last_bar = np.r_[sfirst[1:] - 1, n - 1][np.searchsorted(sfirst, np.arange(n), side="right") - 1]
    px = tk.price_ticks.astype(np.float64)
    del tk, bars
    gc.collect()
    exits = np.array(EXITS, dtype=np.float64)
    rows = []
    allres = []
    for pi, p in enumerate(PCTS):
        above = (sep > th[pi]) & np.isfinite(th[pi])
        cross = above & ~np.r_[False, above[:-1]]
        sb = np.flatnonzero(cross & appr & rth & (np.arange(n) + 1 < n))
        trend = al[sb]
        dec = (mom[sb] * trend) < (mom_prev[sb] * trend)
        clim = d20[sb] <= 0.5 * d20_ref[sb]
        lim = np.minimum(bar_last[sess_last_bar[sb]], len(px) - 1).astype(np.int64)
        res = run_all(px, bar_last, op, cl, sb.astype(np.int64), (-trend).astype(np.int64), lim, exits, SLIP)
        allres.append(res)
        rows.append(pd.DataFrame(dict(pct=p, bar=sb, session=sdate[sb], clock=clock[sb], trend=trend,
                                      desaceleracion=dec, climax_vol=clim)))
    meta = pd.concat(rows, ignore_index=True)
    meta.to_parquet(OUT / ("%s_emasep_meta.parquet" % c))
    np.savez_compressed(OUT / ("%s_emasep.npz" % c), pnl=np.concatenate(allres), exits=exits)
    print(c, ds, "barras", n, "señales por pct", meta.groupby("pct").size().to_dict(), "desac", int(meta.desaceleracion.sum()),
          "climax", int(meta.climax_vol.sum()), "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
