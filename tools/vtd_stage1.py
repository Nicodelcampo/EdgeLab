#!/usr/bin/env python3
r"""VTD-VOL-1 etapa 1 (manifiesto docs/research/VTD_VOL1_MANIFIESTO_20261006.md): VolTicksDef 150t/50t + AVCL base 50t.
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


def save_bars(c, spec, bars, dates):
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


def vtd_cell(c, spec, bars):
    r = vtd_run(bars)
    z = pd.DataFrame(r["zones"])
    n = len(bars.close_t)
    zn = pd.DataFrame(dict(created_bar=z.bar.astype(int), kind="AT_PRICE", direction=0,
                           lower_tick=z.low_tick.astype(int), upper_tick=z.high_tick.astype(int),
                           anomaly_ratio=z.ratio / z.threshold, ratio=z.ratio, threshold=z.threshold,
                           candle=np.sign(np.asarray(bars.close_t)[z.bar] - np.asarray(bars.open_t)[z.bar]).astype(int)))
    for k in ("cluster_share", "density", "quality_score", "burst_count", "distance_ticks", "delta", "band_vol"):
        zn[k] = np.nan
    cand = np.unique(np.r_[np.arange(9, n, 10), zn.created_bar.to_numpy()])
    blk = pd.DataFrame(dict(bar=cand, vol=np.asarray(bars.volume, float)[cand], bucket=0))
    blk.to_parquet(OUT / ("%s_vtd%d_blocks.parquet" % (c, spec)))
    zn.to_parquet(OUT / ("%s_vtd%d_zones.parquet" % (c, spec)))
    return len(zn)


def cache(c, sess):
    ds, fl, a, b, dates = contract_rows(c, sess)
    t0 = time.time()
    tk = load_ticks(ed._path(ds, fl), a, b, c)
    for spec in (50, 150):
        bars = B.build_tick_bars(tk, spec)
        save_bars(c, spec, bars, dates)
        nz = vtd_cell(c, spec, bars)
        print(c, spec, "VTD marcas", nz, "%.0f s" % (time.time() - t0), flush=True)
        if spec == 50:
            fps = B.build_total_footprint_csr_nt8(tk, bars)
            r = run_full(tk, bars, fps, PARAMS)
            z = pd.DataFrame(r["zones"])
            z = z[[k for k in z.columns if z[k].map(lambda v: v is None or np.isscalar(v)).all()]]
            z["delta"] = np.nan; z["band_vol"] = np.nan
            pd.DataFrame(r["blocks"], columns=["bar", "vol", "bucket"]).to_parquet(OUT / ("%s_base_blocks.parquet" % c))
            z.to_parquet(OUT / ("%s_base_zones.parquet" % c))
            print(c, "AVCL base zonas", len(z), "%.0f s" % (time.time() - t0), flush=True)
            del fps
        del bars
        gc.collect()


def main():
    sess = ed.sessions(INST, DESDE, HASTA)
    for c in [x.strip() for x in os.environ["AVCL_CONTRACTS"].split(",") if x.strip()]:
        cache(c, sess)
        gc.collect()


if __name__ == "__main__":
    main()
