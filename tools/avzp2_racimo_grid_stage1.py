#!/usr/bin/env python3
r"""AVZP2-RACIMO-GRILLA etapa 1 (36 definiciones de racimo) (manifiesto docs/research/AVZP2_RACIMO_MANIFIESTO_20261008.md): desenlaces desde la formación del racimo, real vs pseudo apareado por ocupación.
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
import zlib  # noqa: E402
from edgelab.bridge.indicators.avolzonepoi2 import run as zp2_run, _racimo  # noqa: E402

SPEC = 25
ZP2_PARAMS = dict(ob_away_heights=6.0, ob_max_inside_pct=4.0, racimo_min=0, racimo_bars=500, racimo_altura_ticks=30)
CELLS = [(m, w, a) for m in (4, 5, 6, 8) for w in (250, 500, 1000) for a in (20, 30, 45)]


def racimos_de(zones, m, w, a):
    """Misma regla que _racimo de avolzonepoi2, aplicada a las zonas ya detectadas (las zonas no dependen del racimo)."""
    p = dict(racimo_min=m, racimo_bars=w, racimo_altura_ticks=a)
    zs, clusters = [], []
    for z in zones:
        nz = dict(bar=z["bar"], low_tick=z["low_tick"], high_tick=z["high_tick"], racimo_bar=-1, rac=None)
        _racimo(nz, zs, clusters, z["bar"], p)
        zs.append(nz)
    return clusters
EXIT_MAX, HPOST, TREND, OCC, NPSEUDO = 2000, 200, 500, 500, 5


@numba.njit(cache=True)
def outcomes(hi, lo, cl, send, t0, L, H, n):
    """Desenlaces desde t0+1 (misma sesión). Devuelve
    te, dir_salida, o2_seguimiento, o3a_retest, o3b_rebote, max_excursion_h (antes de volver a cerrar dentro, en h)."""
    h = H - L + 1
    te = -1
    d = 0
    for t in range(t0 + 1, min(t0 + EXIT_MAX, n - 1) + 1):
        if send[t] != send[t0]:
            break
        if cl[t] > H:
            te = t; d = 1
            break
        if cl[t] < L:
            te = t; d = -1
            break
    if te < 0:
        return -1, 0, -1, -1, -1, -1.0
    edge = H if d == 1 else L
    # O2: llega a edge + d*h antes de volver a cerrar dentro de [L, H]; excursión máxima hasta volver
    o2 = -1
    mx = 0.0
    for t in range(te + 1, min(te + EXIT_MAX, n - 1) + 1):
        if send[t] != send[te]:
            break
        exc = (hi[t] - edge) if d == 1 else (edge - lo[t])
        if exc > mx:
            mx = exc
        if o2 < 0 and exc >= h:
            o2 = 1
        if cl[t] >= L and cl[t] <= H:
            if o2 < 0:
                o2 = 0
            break
    # O3: retest del borde por el que salió, luego rebote (edge + d*h) vs ruptura (edge - d*h)
    o3a = 0
    o3b = -1
    tr = -1
    for t in range(te + 1, min(te + EXIT_MAX, n - 1) + 1):
        if send[t] != send[te]:
            break
        if (lo[t] <= edge) if d == 1 else (hi[t] >= edge):
            tr = t
            o3a = 1
            break
    if tr >= 0:
        up = edge + d * h
        dn = edge - d * h
        for t in range(tr + 1, min(tr + EXIT_MAX, n - 1) + 1):
            if send[t] != send[tr]:
                break
            r = (hi[t] >= up) if d == 1 else (lo[t] <= up)
            bk = (lo[t] <= dn) if d == 1 else (hi[t] >= dn)
            if r and bk:
                o3b = -2
                break
            if r:
                o3b = 1
                break
            if bk:
                o3b = 0
                break
    return te, d, o2, o3a, o3b, mx / h


def run_contract(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0_ = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    bars = B.build_tick_bars(tk, SPEC)
    fps = B.build_total_footprint_csr_nt8(tk, bars)
    del tk
    gc.collect()
    hi = np.asarray(bars.high_t, np.int64); lo = np.asarray(bars.low_t, np.int64); cl = np.asarray(bars.close_t, np.int64)
    end = np.asarray(bars.end_ns, dtype=np.int64)
    n = len(cl)
    send = session_end_vec(end)
    r = zp2_run(bars, fps, send, ZP2_PARAMS)
    del fps, bars
    gc.collect()
    us, uinv = np.unique(send, return_inverse=True)
    sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
    clock = ct_minute_of_day(end) // 30
    appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
    rng200 = (pd.Series(hi).rolling(HPOST).max() - pd.Series(lo).rolling(HPOST).min()).to_numpy()
    rng_fwd = (pd.Series(hi[::-1]).rolling(HPOST).max() - pd.Series(lo[::-1]).rolling(HPOST).min()).to_numpy()[::-1]  # [t, t+199]
    csum_cache = {}

    def occ(t0, L, H):
        a_ = max(0, t0 - OCC + 1)
        x = cl[a_:t0 + 1]
        return float(((x >= L) & (x <= H)).mean())

    def row(kind, t0, L, H, start0):
        te, d, o2, o3a, o3b, mx = outcomes(hi, lo, cl, send, t0, L, H, n)
        tr = np.sign(cl[t0] - cl[max(0, t0 - TREND)])
        pre_end = start0 - 1
        exp = np.nan
        if te >= 0 and te + HPOST < n and pre_end >= HPOST and rng200[pre_end] > 0 and send[te + HPOST - 1] == send[te]:
            exp = float(np.log(max(rng_fwd[te + 1], 1) / rng200[pre_end]))
        pos = 0 if L <= cl[t0] <= H else (1 if cl[t0] > H else -1)
        return (c, kind, int(t0), int(L), int(H), int(H - L + 1), int(sdate[t0]), int(clock[t0]), occ(t0, L, H),
                float(rng200[t0]) if t0 >= HPOST else np.nan, int(tr), pos, int(te), int(d), int(o2), int(o3a), int(o3b),
                float(mx), float(np.log(te - t0)) if te > 0 else np.nan, exp,
                float(cl[t0] - cl[max(0, t0 - TREND)]) / (H - L + 1), float(cl[t0] - cl[max(0, t0 - 100)]) / (H - L + 1))

    rows = []
    for (cm, cw, ca) in CELLS:
        cell = "%d_%d_%d" % (cm, cw, ca)
        clus = racimos_de(r["zones"], cm, cw, ca)
        reals = [k for k in clus if appr[k["bar"]] and k["bar"] < n - 2]
        for k in reals:
            rows.append((cell,) + row("real", k["bar"], k["low0"], k["high0"], k["start0"]))
        rng = np.random.default_rng(zlib.crc32((c + "|" + cell).encode()))  # semilla estable (hash() cambia por proceso)
        pool = np.flatnonzero(appr)
        pool = pool[(pool > max(OCC, HPOST) + 600) & (pool < n - 2)]
        pclock = clock[pool]
        for k in reals:
            t0 = k["bar"]
            cand = pool[pclock == clock[t0]]
            if len(cand) == 0:
                continue
            dl, dh, span = k["low0"] - cl[t0], k["high0"] - cl[t0], t0 - k["start0"]
            # apareamiento por ocupación: de hasta 200 candidatas, las primeras NPSEUDO con |occ - occ_real| <= 0.05
            occ_r = occ(t0, k["low0"], k["high0"])
            got = 0
            for b0 in rng.choice(cand, min(200, 40 * NPSEUDO), replace=True):
                L_, H_ = int(cl[b0] + dl), int(cl[b0] + dh)
                if abs(occ(int(b0), L_, H_) - occ_r) > 0.05:
                    continue
                rows.append((cell,) + row("pseudo", int(b0), L_, H_, int(b0 - span)))
                got += 1
                if got >= NPSEUDO:
                    break
    t = pd.DataFrame(rows, columns=["cell", "contract", "kind", "t0", "L", "H", "h", "session", "clock", "occ", "amp", "trend", "pos",
                                    "te", "dir", "o2", "o3a", "o3b", "mx_h", "o4", "o5", "trend_h", "mom100_h"])
    t.to_parquet(OUT / ("%s_avzp2racgrid.parquet" % c))
    print(c, ds, "velas", n, "zonas", len(r["zones"]), "filas", len(t),
          "%.0f s" % (time.time() - t0_), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        run_contract(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
