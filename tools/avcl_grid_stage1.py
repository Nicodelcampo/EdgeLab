#!/usr/bin/env python3
r"""AVCL-CIERRE etapa 1 (manifiesto docs/research/AVCL_CIERRE_MANIFIESTO_20261006.md): 13 celdas + delta de zona.
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





CELLS = {
    "base": (50, {}), "p90": (50, dict(detection_percentile=90.0)), "p98": (50, dict(detection_percentile=98.0)),
    "W5": (50, dict(window_bars=5)), "W20": (50, dict(window_bars=20)),
    "k15": (50, dict(median_multiplier=1.5)), "k30": (50, dict(median_multiplier=3.0)), "m4": (50, dict(min_cluster_ticks=4)),
    "t200": (200, {}),
    "p90W5": (50, dict(detection_percentile=90.0, window_bars=5)), "p90W20": (50, dict(detection_percentile=90.0, window_bars=20)),
    "p98W5": (50, dict(detection_percentile=98.0, window_bars=5)), "p98W20": (50, dict(detection_percentile=98.0, window_bars=20)),
}


def zone_delta(zn, blk, tk, bars, send):
    """Delta (compra − venta agresora) de los ticks del bloque creador dentro de la banda de la zona."""
    if len(zn) == 0:
        return np.zeros(0), np.zeros(0)
    px = tk.price_ticks; v = tk.volume.astype(float)
    sg = np.where(px >= tk.ask_ticks, 1.0, np.where(px <= tk.bid_ticks, -1.0, 0.0))
    tbi = bars.tick_bar_idx
    nb = len(bars.close_t)
    t0 = np.searchsorted(tbi, np.arange(nb), side="left"); t1 = np.searchsorted(tbi, np.arange(nb), side="right")
    bb = np.asarray(blk.bar, dtype=np.int64)
    sfirst = np.r_[0, np.flatnonzero(np.diff(send)) + 1]
    d, tot = np.zeros(len(zn)), np.zeros(len(zn))
    for k, (cb, lo_, up_) in enumerate(zip(zn.created_bar.astype(int), zn.lower_tick.astype(int), zn.upper_tick.astype(int))):
        j = np.searchsorted(bb, cb)
        prev = bb[j - 1] + 1 if j > 0 else 0
        s0 = sfirst[np.searchsorted(sfirst, cb, side="right") - 1]
        a_, z_ = t0[max(prev, s0)], t1[cb]
        m = (px[a_:z_] >= lo_) & (px[a_:z_] <= up_)
        d[k] = (sg[a_:z_][m] * v[a_:z_][m]).sum(); tot[k] = v[a_:z_][m].sum()
    return d, tot


def cache(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    for spec in sorted({v[0] for v in CELLS.values()}):
        bars = B.build_tick_bars(tk, spec)
        fps = B.build_total_footprint_csr_nt8(tk, bars)
        end = np.asarray(bars.end_ns, dtype=np.int64)
        send = session_end_vec(end)
        us, uinv = np.unique(send, return_inverse=True)
        sdate = np.asarray(pd.to_datetime(us, utc=True).tz_convert(CT).strftime("%Y%m%d").astype(int))[uinv]
        mins = ct_minute_of_day(end)
        appr = np.isin(sdate, [int(d.replace("-", "")) for d in dates])
        np.savez_compressed(OUT / ("%s_%dt_bars.npz" % (c, spec)), start_ns=np.asarray(bars.start_ns, np.int64), end_ns=end,
                            open_t=np.asarray(bars.open_t, np.int32), high_t=np.asarray(bars.high_t, np.int32),
                            low_t=np.asarray(bars.low_t, np.int32), close_t=np.asarray(bars.close_t, np.int32),
                            volume=np.asarray(bars.volume, np.float32), send=send, sdate=sdate.astype(np.int32),
                            approved=appr, mins=mins.astype(np.int16))
        for cell, (sp, extra) in CELLS.items():
            if sp != spec:
                continue
            t1 = time.time()
            r = run_full(tk, bars, fps, {**PARAMS, **extra})
            blk = pd.DataFrame(r["blocks"], columns=["bar", "vol", "bucket"])
            z = pd.DataFrame(r["zones"])
            z = z[[k for k in z.columns if z[k].map(lambda v: v is None or np.isscalar(v)).all()]]
            z["delta"], z["band_vol"] = zone_delta(z, blk, tk, bars, send)
            blk.to_parquet(OUT / ("%s_%s_blocks.parquet" % (c, cell)))
            z.to_parquet(OUT / ("%s_%s_zones.parquet" % (c, cell)))
            print(c, spec, cell, "zonas", len(z), "%.0f s" % (time.time() - t1), flush=True)
        del bars, fps
        gc.collect()
    print(c, ds, "total %.0f s" % (time.time() - t0), flush=True)


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        cache(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
