#!/usr/bin/env python3
r"""AVZP2-REBOTE etapa 1 (manifiesto docs/research/AVZP2_REBOTE_MANIFIESTO_20261007.md): enmienda 1: rojas vs pseudo-zonas que cumplen la regla OB.
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
from edgelab.bridge.indicators.avolzonepoi2 import run as zp2_run  # noqa: E402

SPEC = 200
SEARCH, HOR, HOR_ND = 2000, 200, 50
NPSEUDO = 10
OB_BARS, OB_AH, OB_MIN, OB_PCT = 100, 3.0, 8, 2.0


@numba.njit(cache=True)
def ob_rule(hi, lo, F_off, F_t, F_v, b0, L, H, n):
    """Misma regla OB que aVolZonePOI2, aplicada desde la barra siguiente a b0. 1 = OB, 0 = no."""
    vin = 0.0
    vall = 0.0
    maxaway = 0
    need = max(OB_AH * (H - L + 1), OB_MIN)
    for k in range(b0 + 1, min(b0 + OB_BARS, n - 1) + 1):
        for j in range(F_off[k], F_off[k + 1]):
            v = F_v[j]
            vall += v
            if F_t[j] >= L and F_t[j] <= H:
                vin += v
        away = max(hi[k] - H, L - lo[k])
        if away > maxaway:
            maxaway = away
        if maxaway >= need:
            pct = 100.0 * vin / vall if vall > 0 else 0.0
            return 1 if pct <= OB_PCT else 0
    return 0


@numba.njit(cache=True)
def event(hi, lo, send, c, L, H, n):
    """Salida -> primer regreso -> rebote. Devuelve (t_toque, lado, rebote, activo50, barras_a_resultado)."""
    end = min(c + SEARCH, n - 1)
    side = 0
    t = c + 1
    while t <= end:
        if send[t] != send[c]:
            return -1, 0, -1, -1, -1
        if lo[t] > H:
            side = 1
            break
        if hi[t] < L:
            side = -1
            break
        t += 1
    if side == 0:
        return -1, 0, -1, -1, -1
    k = t + 1
    tt = -1
    while k <= end:
        if send[k] != send[c]:
            return -1, side, -1, -1, -1
        if lo[k] <= H and hi[k] >= L:
            tt = k
            break
        k += 1
    if tt < 0:
        return -1, side, -1, -1, -1
    h = H - L + 1
    D = max(2 * h, 8)
    ref = H if side == 1 else L
    up = ref + side * D           # nivel de rebote
    dn = ref - side * D           # nivel de ruptura
    reb = -1
    act = 0
    nb = -1
    for j in range(tt + 1, min(tt + HOR, n - 1) + 1):
        if send[j] != send[tt]:
            break
        hit_r = (hi[j] >= up) if side == 1 else (lo[j] <= up)
        hit_b = (lo[j] <= dn) if side == 1 else (hi[j] >= dn)
        if hit_r or hit_b:
            if j - tt <= HOR_ND:
                act = 1
            if hit_r and hit_b:
                reb = -2                # ambiguo
            else:
                reb = 1 if hit_r else 0
            nb = j - tt
            break
    if reb == -1 and min(tt + HOR, n - 1) - tt < HOR_ND:
        act = -1
    return tt, side, reb, act, nb


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    fps = B.build_total_footprint_csr_nt8(tk, bars)
    hi = np.asarray(bars.high_t, np.int64); lo = np.asarray(bars.low_t, np.int64); cl = np.asarray(bars.close_t, np.int64)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    n = len(cl)
    send = session_end_vec(end)
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    mins = ct_minute_of_day(end)
    clock = mins // 30
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    a50 = (pd.Series(hi).rolling(50).max() - pd.Series(lo).rolling(50).min()).to_numpy()
    fam = {}
    r2 = zp2_run(bars, fps, send)
    fam["AVZP2_roja"] = [(z["bar"], z["low_tick"], z["high_tick"]) for z in r2["zones"] if z["state"] == 2]
    F_off = np.asarray(fps.offsets, np.int64); F_t = np.asarray(fps.ticks, np.int64); F_v = np.asarray(fps.vols, np.float64)
    del tk
    gc.collect()
    rng = np.random.default_rng(int(abs(hash(c))) % (2 ** 31))
    pool = np.flatnonzero(appr)
    pool = pool[(pool > 60) & (pool < n - 2)]
    pclock = clock[pool]
    rows = []
    for name, zs in fam.items():
        geo = []
        for (b0, L, H) in zs:
            if b0 >= n - 2 or not appr[b0]:
                continue
            geo.append((clock[b0], L - cl[b0], H - cl[b0]))
            rows.append((c, name, "real", b0, L, H) + event(hi, lo, send, b0, L, H, n))
        g = pd.DataFrame(geo, columns=["clock", "dl", "dh"])
        for clk, gg in g.groupby("clock"):
            cand = pool[pclock == clk]
            if len(cand) == 0:
                continue
            k = NPSEUDO * len(gg)
            pick = rng.choice(cand, k, replace=True)
            smp = gg.sample(k, replace=True, random_state=int(rng.integers(1 << 31)))
            for b0, dl, dh in zip(pick, smp.dl.to_numpy(), smp.dh.to_numpy()):
                L, H = int(cl[b0] + dl), int(cl[b0] + dh)
                if ob_rule(hi, lo, F_off, F_t, F_v, int(b0), L, H, n) != 1:
                    continue                      # nulo apareado: sólo pseudo-zonas que cumplen la regla OB
                rows.append((c, name, "pseudo", int(b0), L, H) + event(hi, lo, send, int(b0), L, H, n))
    t = pd.DataFrame(rows, columns=["contract", "fam", "kind", "b0", "L", "H", "tt", "side", "reb", "act", "nb"])
    ok = t.tt >= 0
    t["session"] = np.where(ok, sdate[np.clip(t.tt, 0, n - 1)], -1)
    t["clock"] = np.where(ok, clock[np.clip(t.tt, 0, n - 1)], -1)
    t["amp"] = np.where(ok, a50[np.clip(t.tt, 0, n - 1)], np.nan)
    t["D"] = np.maximum(2 * (t.H - t.L + 1), 8)
    t.to_parquet(OUT / ("%s_avzp2ob.parquet" % c))
    print(c, ds, "barras", n, {k: len(v) for k, v in fam.items()}, "eventos reales", int(((t.kind == "real") & ok).sum()),
          "%.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
