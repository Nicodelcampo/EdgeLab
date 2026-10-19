#!/usr/bin/env python3
r"""HFTV4-RETORNO etapa 1 (manifiesto docs/research/HFTV4_RETORNO_MANIFIESTO_20261006.md): zonas HFTZonesNQPureV4 + flecha + pseudo-zonas.
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





from edgelab.bridge.indicators import hftzones_nq as H  # noqa: E402
from edgelab.bridge.bars import session_ids  # noqa: E402

SPEC = 50
AWAY_H = 3.0
SEARCH = 2000
TS = (50, 200, 1000)
VPCT = 0.5
NPSEUDO = 3


def arrow_event(hi, lo, send, b0, upper, lower, nmax):
    """Primera barra > b0 (misma sesión, <= b0+SEARCH) donde el precio está a >= AWAY_H alturas sin haber tocado antes
    ambos bordes. Devuelve (barra, dir) o (-1, 0)."""
    h = max(upper - lower, 1.0)
    thr = AWAY_H * h
    tu = tl = False
    end = min(b0 + SEARCH, nmax - 1)
    for t in range(b0 + 1, end + 1):
        if send[t] != send[b0]:
            break
        up = hi[t] - upper >= thr
        dn = lower - lo[t] >= thr
        if up or dn:
            comp = (tu or hi[t] >= upper) and (tl or lo[t] <= lower)
            if comp or (up and dn):
                return -1, 0
            return t, (1 if up else -1)
        if hi[t] >= upper:
            tu = True
        if lo[t] <= lower:
            tl = True
        if tu and tl:
            return -1, 0
    return -1, 0


def outcomes(hi, lo, send, e, d, upper, lower):
    near = upper if d > 0 else lower       # se alejó hacia arriba -> el borde cercano es el superior
    far = lower if d > 0 else upper
    h = max(upper - lower, 1.0)
    res = {}
    n = len(hi)
    ret_bar = fill_bar = -1
    mae = 0.0
    for t in range(e + 1, min(e + max(TS), n - 1) + 1):
        if send[t] != send[e]:
            break
        if ret_bar < 0:
            exc = (hi[t] - near) if d > 0 else (near - lo[t])
            mae = max(mae, exc)
            if (lo[t] <= near) if d > 0 else (hi[t] >= near):
                ret_bar = t
        if ret_bar >= 0 and ((lo[t] <= far) if d > 0 else (hi[t] >= far)):
            fill_bar = t
            break
    for T in TS:
        observable = (e + T < n) and (send[min(e + T, n - 1)] == send[e])
        res["ret%d" % T] = float(ret_bar >= 0 and ret_bar - e <= T) if observable or ret_bar >= 0 else np.nan
        res["fill%d" % T] = float(fill_bar >= 0 and fill_bar - e <= T) if observable or fill_bar >= 0 else np.nan
    res["t_ret"] = (ret_bar - e) if ret_bar >= 0 else np.nan
    res["mae_h"] = mae / h
    return res


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    sid = session_ids(tk.ts_ns)
    zones = []
    us = np.unique(sid)
    for k, s in enumerate(us):
        m = np.flatnonzero(sid == s)
        if len(m) < 100:
            continue
        cands = H.detect_candidates(tk.ts_ns[m], tk.price_ticks[m], tk.volume[m])
        zz, _ = H.accept_all(cands, tick_size=1.0)
        for z in zz:
            z["end_px"] = int(tk.price_ticks[m][z["idx_end"]])
            zones.append(z)
    bars = B.build_tick_bars(tk, SPEC)
    hi = np.asarray(bars.high_t, float); lo = np.asarray(bars.low_t, float); cl = np.asarray(bars.close_t, float)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    send = session_end_vec(end)
    usd, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(usd, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    rth = (mins >= 510) & (mins < 900)
    n = len(cl)
    a50 = (pd.Series(hi).rolling(50).max() - pd.Series(lo).rolling(50).min()).to_numpy()
    del tk
    gc.collect()
    rows = []
    real_geo = []
    for z in zones:
        b0 = int(np.searchsorted(end, z["ts_avail"], side="left"))
        if b0 < 60 or b0 >= n - 2 or not (appr[b0] and rth[b0]):
            continue
        upper, lower = float(z["sw_hi_tk"]), float(z["sw_lo_tk"])
        h = max(upper - lower, 1.0)
        d0 = z["direction"]
        if z["bucket"] != "Absorb":
            retro = (upper - z["end_px"]) if d0 == 1 else (z["end_px"] - lower)
            vshape = retro >= VPCT * h
        else:
            vshape = False
        real_geo.append((mins[b0] // 30, h, d0))
        e, dd = arrow_event(hi, lo, send, b0, upper, lower, n)
        row = dict(contract=c, kind="real", b0=b0, session=int(sdate[b0]), clock=int(mins[b0] // 30), height=h,
                   bucket=z["bucket"], vshape=bool(vshape), arrow=e >= 0, e=e, dir=dd, amp=a50[b0])
        if e >= 0 and not vshape:
            row.update(outcomes(hi, lo, send, e, dd, upper, lower))
            row["dist_ticks"] = (hi[e] - upper) if dd > 0 else (lower - lo[e])
        rows.append(row)
    # pseudo-zonas: barras al azar de la misma franja, con altura y dirección de zonas reales de esa franja
    rng = np.random.default_rng(int(abs(hash(c))) % (2 ** 31))
    geo = pd.DataFrame(real_geo, columns=["clock", "h", "d"])
    pool = np.flatnonzero(appr & rth)
    pool = pool[(pool > 60) & (pool < n - 2)]
    pclock = mins[pool] // 30
    for clk, g in geo.groupby("clock"):
        cand = pool[pclock == clk]
        if len(cand) == 0:
            continue
        k = NPSEUDO * len(g)
        pick = rng.choice(cand, k, replace=True)
        gg = g.sample(k, replace=True, random_state=int(rng.integers(1 << 31)))
        for b0, h, d0 in zip(pick, gg.h.to_numpy(), gg.d.to_numpy()):
            c0 = cl[b0]
            upper, lower = (c0, c0 - h) if d0 == 1 else (c0 + h, c0)
            e, dd = arrow_event(hi, lo, send, int(b0), upper, lower, n)
            row = dict(contract=c, kind="pseudo", b0=int(b0), session=int(sdate[b0]), clock=int(clk), height=h, bucket="",
                       vshape=False, arrow=e >= 0, e=e, dir=dd, amp=a50[b0])
            if e >= 0:
                row.update(outcomes(hi, lo, send, e, dd, upper, lower))
                row["dist_ticks"] = (hi[e] - upper) if dd > 0 else (lower - lo[e])
            rows.append(row)
    t = pd.DataFrame(rows)
    t.to_parquet(OUT / ("%s_hftret.parquet" % c))
    print(c, ds, "zonas", len(zones), "reales usadas", int((t.kind == "real").sum()), "flechas reales",
          int(((t.kind == "real") & t.arrow & ~t.vshape).sum()), "pseudo flechas", int(((t.kind == "pseudo") & t.arrow).sum()),
          "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
