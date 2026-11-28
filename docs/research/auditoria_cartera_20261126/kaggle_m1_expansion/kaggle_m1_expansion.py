#!/usr/bin/env python3
"""Kaggle Kernel 1: Expansion Multi-Activo M1 (14 mercados x 6 mecanismos canonicos en unidades ATR, 0 grilla).

Monta:
  - nicolasbuttaro/edgelab-sqx-m1 (DAX, EUSTX, FTSE, NKD, WTI, XAU, EURUSD, USDJPY, USSC2000)
  - nicolasbuttaro/edgelab-nt8-m1-futuros (NQ, ES, YM, RTY, EMD, GC)

Custodia:
  - HOLDOUT-A4 estricto (< 2026-10-01; NT8 < HOLDOUT_APERTURA_UTC_NS = 1_790_805_600_000_000_000).
  - HOLDOUT-A5 determinista inlined de edgelab/holdout.py: evalua SOLO DESC y REP; exporta NaN en HOLDOUT/EMBARGO/TERMINAL.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import glob
import hashlib
import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

HOLDOUT_PRIMERA_SESION_INT = 20261001
HOLDOUT_APERTURA_UTC_NS = 1_790_805_600_000_000_000
CUTOFF_STR = "2026-09-29"

# Inlined deterministically from edgelab/holdout.py
A5_SEMILLA = "EdgeLab-HOLDOUT-A5-v1"
A5_REPARTO = (("DESC", 7), ("REP", 2), ("HOLDOUT", 3))


def a5_meses(anio: int) -> dict:
    sem = int.from_bytes(hashlib.sha256(f"{A5_SEMILLA}:{int(anio)}".encode()).digest()[:8], "little")
    perm = np.random.default_rng(sem).permutation(np.arange(1, 13))
    out, i = {}, 0
    for nombre, k in A5_REPARTO:
        for m in perm[i : i + k]:
            out[int(m)] = nombre
        i += k
    return out


def _dia_habil(td: int, paso: int) -> int:
    d = dt.date(td // 10000, td // 100 % 100, td % 100) + dt.timedelta(days=paso)
    while d.weekday() >= 5:
        d += dt.timedelta(days=paso)
    return int(d.strftime("%Y%m%d"))


def a5_bloque(trade_date) -> str:
    td = int(str(trade_date).replace("-", "")[:8])
    if td >= HOLDOUT_PRIMERA_SESION_INT:
        return "TERMINAL"
    b = a5_meses(td // 10000)[td // 100 % 100]
    if b != "HOLDOUT":
        for v in (_dia_habil(td, 1), _dia_habil(td, -1)):
            if v < HOLDOUT_PRIMERA_SESION_INT and a5_meses(v // 10000)[v // 100 % 100] == "HOLDOUT":
                return "EMBARGO"
    return b


EN_UTC = (
    "USSC2000IDXUSD", "DEUIDXEUR", "EUSIDXEUR", "GBRIDXGBP", "JPNIDXJPY", "LIGHTCMDUSD",
    "AUDUSD", "BRENTCMDUSD", "BUNDTREUR", "COPPERCMDUSD", "DOLLARIDXUSD", "GASCMDUSD",
    "NZDUSD", "UKGILTTRGBP", "USDCAD", "USTBONDTRUSD", "XAGUSD",
)
SERVIDOR_MENOS_NY = 7

# 15 activos (9 SQX M1 + 6 NT8 CME), 6 mecanismos canonicos ATR-scaled
SPECS = [
    # SQX M1 Dukascopy
    {"src": "sqx", "file": "DEUIDXEUR-M1-.csv", "sym": "DK_DAX", "tz": "Europe/Berlin", "open": (9, 0), "eod": (17, 30), "fric": 2.0, "cls": "EU_IDX"},
    {"src": "sqx", "file": "EUSIDXEUR-M1-.csv", "sym": "DK_EUSTX", "tz": "Europe/Berlin", "open": (9, 0), "eod": (17, 30), "fric": 1.5, "cls": "EU_IDX"},
    {"src": "sqx", "file": "GBRIDXGBP-M1-.csv", "sym": "DK_FTSE", "tz": "Europe/London", "open": (8, 0), "eod": (16, 30), "fric": 1.5, "cls": "UK_IDX"},
    {"src": "sqx", "file": "JPNIDXJPY-M1-.csv", "sym": "DK_NKD", "tz": "Asia/Tokyo", "open": (9, 0), "eod": (15, 0), "fric": 10.0, "cls": "JP_IDX"},
    {"src": "sqx", "file": "LIGHTCMDUSD-M1-.csv", "sym": "DK_WTI", "tz": "America/New_York", "open": (9, 0), "eod": (14, 30), "fric": 0.04, "cls": "ENERGY"},
    {"src": "sqx", "file": "XAUUSD_M1_dukas-M1-.csv", "sym": "DK_XAU", "tz": "America/New_York", "open": (8, 20), "eod": (15, 0), "fric": 0.69, "cls": "GOLD"},
    {"src": "sqx", "file": "EURUSD_M1_dukas-M1-.csv", "sym": "DK_EURUSD", "tz": "America/New_York", "open": (8, 0), "eod": (15, 55), "fric": 0.00018, "cls": "FX"},
    {"src": "sqx", "file": "USDJPY_M1_dukas-M1-.csv", "sym": "DK_USDJPY", "tz": "America/New_York", "open": (8, 0), "eod": (15, 55), "fric": 0.020, "cls": "FX"},
    {"src": "sqx", "file": "USSC2000IDXUSD-M1-.csv", "sym": "DK_RTY", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 0.60, "cls": "US_IDX"},
    # NT8 Real CME Futures (micro frictions)
    {"src": "nt8", "file": "NQ_M1_nonadj_utc.parquet", "sym": "CME_NQ", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 1.9775, "cls": "US_IDX"},
    {"src": "nt8", "file": "ES_M1_nonadj_utc.parquet", "sym": "CME_ES", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 1.155, "cls": "US_IDX"},
    {"src": "nt8", "file": "YM_M1_nonadj_utc.parquet", "sym": "CME_YM", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 7.49, "cls": "US_IDX"},
    {"src": "nt8", "file": "RTY_M1_nonadj_utc.parquet", "sym": "CME_RTY", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 0.55, "cls": "US_IDX"},
    {"src": "nt8", "file": "EMD_M1_nonadj_utc.parquet", "sym": "CME_EMD", "tz": "America/New_York", "open": (9, 30), "eod": (16, 0), "fric": 0.80, "cls": "US_IDX"},
    {"src": "nt8", "file": "GC_M1_nonadj_utc.parquet", "sym": "CME_GC", "tz": "America/New_York", "open": (8, 20), "eod": (15, 0), "fric": 0.692, "cls": "GOLD"},
]


def find_file(fname: str) -> str:
    hits = glob.glob(f"/kaggle/input/**/{fname}", recursive=True)
    if hits:
        return hits[0]
    local_hits = glob.glob(f"**/{fname}", recursive=True)
    if local_hits:
        return local_hits[0]
    raise FileNotFoundError(f"Missing {fname}")


def load_ny_df(spec: dict) -> pd.DataFrame:
    fpath = find_file(spec["file"])
    if spec["src"] == "sqx":
        D = pd.read_csv(fpath)
        D.columns = [c.strip().lower() for c in D.columns]
        t = pd.to_datetime(D["date"].astype(str) + " " + D["time"].astype(str), format="%Y%m%d %H:%M:%S")
        if spec["file"].startswith(EN_UTC):
            t = t.dt.tz_localize("UTC").dt.tz_convert("America/New_York").dt.tz_localize(None)
        else:
            t = t - pd.Timedelta(hours=SERVIDOR_MENOS_NY)
        df = pd.DataFrame(
            {"o": D["open"].to_numpy(float), "h": D["high"].to_numpy(float), "l": D["low"].to_numpy(float), "c": D["close"].to_numpy(float)},
            index=t,
        )
    else:
        D = pd.read_parquet(fpath)
        t = pd.DatetimeIndex(D.index if "datetime" not in D else D["datetime"]).astype("datetime64[ns]")
        ok = t.asi8 < HOLDOUT_APERTURA_UTC_NS
        D, t = D[ok], t[ok]
        ny = t.tz_localize("UTC").tz_convert("America/New_York").tz_localize(None)
        df = pd.DataFrame(
            {"o": D["open"].to_numpy(float), "h": D["high"].to_numpy(float), "l": D["low"].to_numpy(float), "c": D["close"].to_numpy(float)},
            index=ny,
        )

    df = df[(df.index >= "2012-01-01") & (df.index <= "2026-09-29 23:59:59")].copy()
    if spec["tz"] != "America/New_York":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ny_aw = df.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
            ok = ~ny_aw.isna()
            df = df[ok].copy()
            df.index = ny_aw[ok].tz_convert(spec["tz"]).tz_localize(None)
    return df


def stats_block(x: pd.Series, xmin: pd.Series | None = None) -> dict:
    x = x.dropna()
    if len(x) < 10:
        return {"usd_mes": 0.0, "sharpe": 0.0, "t_mes": 0.0, "pct_anios_pos": 0.0, "caida_max_eod": 0.0, "caida_max_intra": 0.0, "meses": 0}
    m = x.groupby(x.index.to_period("M")).sum()
    a = x.groupby(x.index.year).sum()
    eq = x.cumsum()
    dd = eq - eq.cummax()
    dd_i = float(dd.min())
    if xmin is not None:
        xm = np.minimum(xmin.reindex(x.index).fillna(0.0), np.minimum(x, 0.0))
        dd_i = float(min((eq.shift(1, fill_value=0.0) + xm - eq.cummax().shift(1, fill_value=0.0)).min(), dd.min()))
    sd = float(m.std(ddof=1)) if len(m) > 1 else 0.0
    mu = float(m.mean()) if len(m) else 0.0
    return {
        "usd_mes": round(mu, 2),
        "sharpe": round(float(mu / sd * np.sqrt(12)), 3) if sd > 0 else 0.0,
        "t_mes": round(float(mu / (sd / np.sqrt(len(m)))), 2) if sd > 0 and len(m) > 1 else 0.0,
        "pct_anios_pos": round(float((a > 0).mean()), 3) if len(a) else 0.0,
        "caida_max_eod": round(float(dd.min()), 1),
        "caida_max_intra": round(dd_i, 1),
        "meses": int(len(m)),
    }


def eval_one_asset(spec: dict) -> dict:
    t0 = time.time()
    df = load_ny_df(spec)
    fric = float(spec["fric"])
    risk_usd = 75.0

    # Daily OHLC in local calendar
    d1 = pd.DataFrame({
        "o": df["o"].groupby(df.index.normalize()).first(),
        "h": df["h"].groupby(df.index.normalize()).max(),
        "l": df["l"].groupby(df.index.normalize()).min(),
        "c": df["c"].groupby(df.index.normalize()).last(),
    }).dropna()
    d1 = d1[d1.index.dayofweek < 5]
    pc = d1["c"].shift(1)
    tr = np.maximum(d1["h"] - d1["l"], np.maximum((d1["h"] - pc).abs(), (d1["l"] - pc).abs()))
    d1["atr20"] = tr.rolling(20, min_periods=10).mean().shift(1)
    d1["sma20"] = d1["c"].rolling(20).mean().shift(1)
    d1["sma20_prev5"] = d1["sma20"].shift(5)
    d1["hi55"] = d1["h"].rolling(55).max().shift(2)
    d1["lo55"] = d1["l"].rolling(55).min().shift(2)
    d1["hi20"] = d1["h"].rolling(20).max().shift(2)
    d1["lo20"] = d1["l"].rolling(20).min().shift(2)

    idx_out = pd.bdate_range("2012-01-01", CUTOFF_STR)
    series_d, series_m, trade_cnt = {}, {}, {}

    # 1) DON: Donchian 55/20 1D Trend L/S
    pos, entry_p, stop_p, unit_qty = 0, 0.0, 0.0, 0.0
    don_ret = np.zeros(len(d1))
    don_min = np.zeros(len(d1))
    ntr = 0
    o_a, h_a, l_a, c_a = d1["o"].to_numpy(), d1["h"].to_numpy(), d1["l"].to_numpy(), d1["c"].to_numpy()
    h55, l55, h20, l20, atr_a, c_prev_a = d1["hi55"].to_numpy(), d1["lo55"].to_numpy(), d1["hi20"].to_numpy(), d1["lo20"].to_numpy(), d1["atr20"].to_numpy(), pc.to_numpy()
    for i in range(60, len(d1)):
        if not np.isfinite(atr_a[i]) or atr_a[i] <= 0:
            continue
        if pos != 0:
            ex_p = None
            if pos == 1:
                if o_a[i] <= stop_p: ex_p = o_a[i]
                elif l_a[i] <= stop_p: ex_p = stop_p
                elif c_prev_a[i] < l20[i]: ex_p = o_a[i]
                dw = (l_a[i] - c_prev_a[i]) * unit_qty if ex_p is None else (ex_p - c_prev_a[i]) * unit_qty
            else:
                if o_a[i] >= stop_p: ex_p = o_a[i]
                elif h_a[i] >= stop_p: ex_p = stop_p
                elif c_prev_a[i] > h20[i]: ex_p = o_a[i]
                dw = (c_prev_a[i] - h_a[i]) * unit_qty if ex_p is None else (c_prev_a[i] - ex_p) * unit_qty
            if ex_p is not None:
                don_ret[i] += pos * (ex_p - c_prev_a[i]) * unit_qty - (0.5 * fric) * unit_qty
                don_min[i] += min(dw - (0.5 * fric) * unit_qty, don_ret[i])
                pos, unit_qty = 0, 0.0
            else:
                don_ret[i] += pos * (c_a[i] - c_prev_a[i]) * unit_qty
                don_min[i] += min(dw, don_ret[i])
        if pos == 0:
            if c_prev_a[i] > h55[i]:
                pos, entry_p, st_d = 1, o_a[i], 2.0 * atr_a[i]
                stop_p, unit_qty = entry_p - st_d, risk_usd / st_d
                ntr += 1
                if l_a[i] <= stop_p:
                    don_ret[i] += (stop_p - entry_p - fric) * unit_qty; don_min[i] += don_ret[i]; pos = 0
                else:
                    don_ret[i] += (c_a[i] - entry_p - 0.5 * fric) * unit_qty
                    don_min[i] += (l_a[i] - entry_p - 0.5 * fric) * unit_qty
            elif c_prev_a[i] < l55[i]:
                pos, entry_p, st_d = -1, o_a[i], 2.0 * atr_a[i]
                stop_p, unit_qty = entry_p + st_d, risk_usd / st_d
                ntr += 1
                if h_a[i] >= stop_p:
                    don_ret[i] += (entry_p - stop_p - fric) * unit_qty; don_min[i] += don_ret[i]; pos = 0
                else:
                    don_ret[i] += (entry_p - c_a[i] - 0.5 * fric) * unit_qty
                    don_min[i] += (entry_p - h_a[i] - 0.5 * fric) * unit_qty
    series_d["DON"] = pd.Series(don_ret, index=d1.index).reindex(idx_out, fill_value=0.0)
    series_m["DON"] = pd.Series(don_min, index=d1.index).reindex(idx_out, fill_value=0.0)
    trade_cnt["DON"] = ntr

    # Cash session slice for intraday mechanisms (2: ORB, 4: FADE, 5: VOLBRK, 6: PRECLOSE)
    oh, om = spec["open"]
    eh, em = spec["eod"]
    open_min, eod_min = oh * 60 + om, eh * 60 + em
    mins = df.index.hour * 60 + df.index.minute
    df_s = df[(mins >= open_min) & (mins <= eod_min)]
    d_vals = df_s.index.normalize().to_numpy()
    chg = np.flatnonzero(np.concatenate(([True], d_vals[1:] != d_vals[:-1], [True])))
    o_s, h_s, l_s, c_s = df_s["o"].to_numpy(), df_s["h"].to_numpy(), df_s["l"].to_numpy(), df_s["c"].to_numpy()
    m_s = (df_s.index.hour * 60 + df_s.index.minute).to_numpy()
    atr_map = d1["atr20"].to_dict()

    # Precompute 1H vol compression ATR12/ATR72 (< 0.75) causally on df_s -> resampled 1h inside df
    h1 = df.resample("1h", label="left", closed="left").agg({"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    pc1 = h1["c"].shift(1)
    tr1 = np.maximum(h1["h"] - h1["l"], np.maximum((h1["h"] - pc1).abs(), (h1["l"] - pc1).abs()))
    h1["atr12"] = tr1.rolling(12).mean().shift(1)
    h1["atr72"] = tr1.rolling(72).mean().shift(1)
    h1["atr24"] = tr1.rolling(24).mean().shift(1)
    h1["hi12"] = h1["h"].rolling(12).max().shift(1)
    h1["lo12"] = h1["l"].rolling(12).min().shift(1)
    h1["comp"] = (h1["atr12"] / h1["atr72"]) < 0.75
    h1_hour_map = h1.to_dict("index")

    orb_r, orb_m, orb_n = {}, {}, 0
    fad_r, fad_m, fad_n = {}, {}, 0
    pre_r, pre_m, pre_n = {}, {}, 0
    vol_r, vol_m, vol_n = {}, {}, 0

    for k in range(len(chg) - 1):
        i0, i1 = chg[k], chg[k + 1]
        if i1 - i0 < 40:
            continue
        dt_d = pd.Timestamp(d_vals[i0])
        atr_v = atr_map.get(dt_d, np.nan)
        if not np.isfinite(atr_v) or atr_v <= 0:
            continue
        op0 = o_s[i0]

        # ---- 2) ORB: 0.25*ATR20 band, 0.45*ATR20 stop, 2R tgt, EOD ----
        up_lv, dn_lv = op0 + 0.25 * atr_v, op0 - 0.25 * atr_v
        st_d, tgt_d = 0.45 * atr_v, 0.90 * atr_v
        side, ep, sp, tp, mae, ex_p = 0, 0.0, 0.0, 0.0, 0.0, np.nan
        for j in range(i0 + 15, i1):
            if side == 0:
                if m_s[j] > open_min + 210: break
                if h_s[j] >= up_lv:
                    side, ep = 1, max(o_s[j], up_lv); sp, tp = ep - st_d, ep + tgt_d; orb_n += 1
                    if l_s[j] <= sp: ex_p, mae = sp, st_d; break
                    mae = max(mae, ep - l_s[j])
                elif l_s[j] <= dn_lv:
                    side, ep = -1, min(o_s[j], dn_lv); sp, tp = ep + st_d, ep - tgt_d; orb_n += 1
                    if h_s[j] >= sp: ex_p, mae = sp, st_d; break
                    mae = max(mae, h_s[j] - ep)
            else:
                if side == 1:
                    if o_s[j] <= sp: ex_p = o_s[j]; mae = max(mae, ep - ex_p); break
                    if l_s[j] <= sp: ex_p = sp; mae = max(mae, st_d); break
                    mae = max(mae, ep - l_s[j])
                    if h_s[j] >= tp: ex_p = tp; break
                else:
                    if o_s[j] >= sp: ex_p = o_s[j]; mae = max(mae, ex_p - ep); break
                    if h_s[j] >= sp: ex_p = sp; mae = max(mae, st_d); break
                    mae = max(mae, h_s[j] - ep)
                    if l_s[j] <= tp: ex_p = tp; break
        if side != 0:
            if not np.isfinite(ex_p): ex_p = c_s[i1 - 1]
            qu = risk_usd / st_d
            u = (side * (ex_p - ep) - fric) * qu
            orb_r[dt_d], orb_m[dt_d] = u, min(-(mae + fric) * qu, u)

        # ---- 4) FADE: Stretch >= 0.75*ATR20 in first 2.5h -> fade back to open (0.50*ATR20 stop) ----
        f_up, f_dn = op0 + 0.75 * atr_v, op0 - 0.75 * atr_v
        fst_d = 0.50 * atr_v
        side, ep, sp, tp, mae, ex_p = 0, 0.0, 0.0, op0, 0.0, np.nan
        for j in range(i0 + 15, i1):
            if side == 0:
                if m_s[j] > open_min + 150: break
                if h_s[j] >= f_up:
                    side, ep = -1, max(o_s[j], f_up); sp = ep + fst_d; fad_n += 1
                    if h_s[j] >= sp: ex_p, mae = sp, fst_d; break
                    mae = max(mae, h_s[j] - ep)
                elif l_s[j] <= f_dn:
                    side, ep = 1, min(o_s[j], f_dn); sp = ep - fst_d; fad_n += 1
                    if l_s[j] <= sp: ex_p, mae = sp, fst_d; break
                    mae = max(mae, ep - l_s[j])
            else:
                if side == 1:
                    if o_s[j] <= sp: ex_p = o_s[j]; mae = max(mae, ep - ex_p); break
                    if l_s[j] <= sp: ex_p = sp; mae = max(mae, fst_d); break
                    mae = max(mae, ep - l_s[j])
                    if h_s[j] >= tp: ex_p = tp; break
                else:
                    if o_s[j] >= sp: ex_p = o_s[j]; mae = max(mae, ex_p - ep); break
                    if h_s[j] >= sp: ex_p = sp; mae = max(mae, fst_d); break
                    mae = max(mae, h_s[j] - ep)
                    if l_s[j] <= tp: ex_p = tp; break
        if side != 0:
            if not np.isfinite(ex_p): ex_p = c_s[i1 - 1]
            qu = risk_usd / fst_d
            u = (side * (ex_p - ep) - fric) * qu
            fad_r[dt_d], fad_m[dt_d] = u, min(-(mae + fric) * qu, u)

        # ---- 6) PRECLOSE: Last 90m momentum if |p - op0| > 0.35*ATR20 at eod-90m ----
        idx_pc = np.searchsorted(m_s[i0:i1], eod_min - 90) + i0
        if idx_pc < i1 - 15:
            p_pc = o_s[idx_pc]
            pst_d = 0.35 * atr_v
            if abs(p_pc - op0) > pst_d:
                side = 1 if p_pc > op0 else -1
                ep = p_pc
                sp = ep - side * pst_d
                pre_n += 1
                mae, ex_p = 0.0, np.nan
                for j in range(idx_pc, i1):
                    if side == 1:
                        if o_s[j] <= sp: ex_p = o_s[j]; mae = max(mae, ep - ex_p); break
                        if l_s[j] <= sp: ex_p = sp; mae = max(mae, pst_d); break
                        mae = max(mae, ep - l_s[j])
                    else:
                        if o_s[j] >= sp: ex_p = o_s[j]; mae = max(mae, ex_p - ep); break
                        if h_s[j] >= sp: ex_p = sp; mae = max(mae, pst_d); break
                        mae = max(mae, h_s[j] - ep)
                if not np.isfinite(ex_p): ex_p = c_s[i1 - 1]
                qu = risk_usd / pst_d
                u = (side * (ex_p - ep) - fric) * qu
                pre_r[dt_d], pre_m[dt_d] = u, min(-(mae + fric) * qu, u)

        # ---- 5) VOLBRK: 1H compression (< 0.75) breakout within cash session (stop 1.2*ATR24_1H, EOD) ----
        h1_row = h1_hour_map.get(dt_d + pd.Timedelta(hours=oh))
        if h1_row is not None and h1_row.get("comp") and np.isfinite(h1_row["atr24"]) and h1_row["atr24"] > 0:
            v_up, v_dn = h1_row["hi12"], h1_row["lo12"]
            vst_d = 1.2 * h1_row["atr24"]
            side, ep, sp, mae, ex_p = 0, 0.0, 0.0, 0.0, np.nan
            for j in range(i0 + 5, i1):
                if side == 0:
                    if m_s[j] > eod_min - 60: break
                    if h_s[j] >= v_up:
                        side, ep = 1, max(o_s[j], v_up); sp = ep - vst_d; vol_n += 1
                        if l_s[j] <= sp: ex_p, mae = sp, vst_d; break
                        mae = max(mae, ep - l_s[j])
                    elif l_s[j] <= v_dn:
                        side, ep = -1, min(o_s[j], v_dn); sp = ep + vst_d; vol_n += 1
                        if h_s[j] >= sp: ex_p, mae = sp, vst_d; break
                        mae = max(mae, h_s[j] - ep)
                else:
                    if side == 1:
                        if o_s[j] <= sp: ex_p = o_s[j]; mae = max(mae, ep - ex_p); break
                        if l_s[j] <= sp: ex_p = sp; mae = max(mae, vst_d); break
                        mae = max(mae, ep - l_s[j])
                        sp = max(sp, c_s[j] - vst_d)
                    else:
                        if o_s[j] >= sp: ex_p = o_s[j]; mae = max(mae, ex_p - ep); break
                        if h_s[j] >= sp: ex_p = sp; mae = max(mae, vst_d); break
                        mae = max(mae, h_s[j] - ep)
                        sp = min(sp, c_s[j] + vst_d)
            if side != 0:
                if not np.isfinite(ex_p): ex_p = c_s[i1 - 1]
                qu = risk_usd / vst_d
                u = (side * (ex_p - ep) - fric) * qu
                vol_r[dt_d], vol_m[dt_d] = u, min(-(mae + fric) * qu, u)

    series_d["ORB"] = pd.Series(orb_r, dtype=float).reindex(idx_out, fill_value=0.0)
    series_m["ORB"] = pd.Series(orb_m, dtype=float).reindex(idx_out, fill_value=0.0)
    trade_cnt["ORB"] = orb_n
    series_d["FADE"] = pd.Series(fad_r, dtype=float).reindex(idx_out, fill_value=0.0)
    series_m["FADE"] = pd.Series(fad_m, dtype=float).reindex(idx_out, fill_value=0.0)
    trade_cnt["FADE"] = fad_n
    series_d["VOLBRK"] = pd.Series(vol_r, dtype=float).reindex(idx_out, fill_value=0.0)
    series_m["VOLBRK"] = pd.Series(vol_m, dtype=float).reindex(idx_out, fill_value=0.0)
    trade_cnt["VOLBRK"] = vol_n
    series_d["PRECLOSE"] = pd.Series(pre_r, dtype=float).reindex(idx_out, fill_value=0.0)
    series_m["PRECLOSE"] = pd.Series(pre_m, dtype=float).reindex(idx_out, fill_value=0.0)
    trade_cnt["PRECLOSE"] = pre_n

    # ---- 3) OVN: Overnight trend drift (SMA20 > SMA20_prev5 & c > SMA20, 0.50*ATR20 stop) ----
    eod_bars = df[(mins >= eod_min - 5) & (mins <= eod_min)].groupby(df[(mins >= eod_min - 5) & (mins <= eod_min)].index.normalize())["c"].last()
    open_bars = df[(mins >= open_min) & (mins <= open_min + 5)].groupby(df[(mins >= open_min) & (mins <= open_min + 5)].index.normalize())["o"].first()
    df_ov = df[(mins > eod_min) | (mins < open_min)]
    ov_r, ov_m, ov_sw_r, ov_sw_m, ov_n = {}, {}, {}, {}, 0
    dates_l = list(d1.index)
    for k in range(25, len(dates_l) - 1):
        d_in, d_ex = dates_l[k], dates_l[k + 1]
        if d_in not in eod_bars.index or d_ex not in open_bars.index:
            continue
        sma, smap, atr_v = d1.at[d_in, "sma20"], d1.at[d_in, "sma20_prev5"], d1.at[d_in, "atr20"]
        if not (np.isfinite(sma) and np.isfinite(smap) and np.isfinite(atr_v) and atr_v > 0):
            continue
        ep = float(eod_bars.at[d_in])
        if not (ep > sma and sma > smap):
            continue
        st_d = 0.50 * atr_v
        sp = ep - st_d
        qu = risk_usd / st_d
        ex_p = float(open_bars.at[d_ex])
        sl = df_ov.loc[d_in + pd.Timedelta(minutes=eod_min + 1) : d_ex + pd.Timedelta(minutes=open_min)]
        mae = 0.0
        if len(sl) > 0:
            la, oa = sl["l"].to_numpy(), sl["o"].to_numpy()
            hits = np.flatnonzero(la <= sp)
            if len(hits) > 0:
                j0 = hits[0]
                ex_p = oa[j0] if oa[j0] <= sp else sp
                mae = max(ep - ex_p, st_d)
            else:
                mae = max(0.0, ep - float(la.min()))
        u_raw = ((ex_p - ep) - fric) * qu
        m_raw = min(-(mae + fric) * qu, u_raw)
        n_nights = max(1, (d_ex - d_in).days)
        swap_pts = ep * (0.08 / 365.0) * n_nights if spec["src"] == "sqx" else 0.0
        u_sw = ((ex_p - ep) - fric - swap_pts) * qu
        m_sw = min(-(mae + fric + swap_pts) * qu, u_sw)
        ov_r[d_ex], ov_m[d_ex] = u_raw, m_raw
        ov_sw_r[d_ex], ov_sw_m[d_ex] = u_sw, m_sw
        ov_n += 1
    series_d["OVN_RAW"] = pd.Series(ov_r, dtype=float).reindex(idx_out, fill_value=0.0)
    series_m["OVN_RAW"] = pd.Series(ov_m, dtype=float).reindex(idx_out, fill_value=0.0)
    trade_cnt["OVN_RAW"] = ov_n
    if spec["src"] == "sqx":
        series_d["OVN_SW8"] = pd.Series(ov_sw_r, dtype=float).reindex(idx_out, fill_value=0.0)
        series_m["OVN_SW8"] = pd.Series(ov_sw_m, dtype=float).reindex(idx_out, fill_value=0.0)
        trade_cnt["OVN_SW8"] = ov_n

    print(f"  done {spec['sym']:12s} in {time.time() - t0:.1f}s (ORB={orb_n}, FADE={fad_n}, VOL={vol_n}, PRE={pre_n}, OVN={ov_n})", flush=True)
    return {"spec": spec, "d": series_d, "m": series_m, "cnt": trade_cnt}


def main() -> None:
    t0 = time.time()
    out_dir = Path("/kaggle/working") if os.path.isdir("/kaggle/working") else Path(".")
    print(f"=== KAGGLE M1 EXPANSION ({len(SPECS)} activos x 6 mecanismos, < 2026-10-01) ===", flush=True)
    results = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(eval_one_asset, s) for s in SPECS]
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    idx = pd.bdate_range("2012-01-01", CUTOFF_STR)
    ses_int = pd.Series([int(d.strftime("%Y%m%d")) for d in idx], index=idx)
    blq = ses_int.map(a5_bloque)
    mask_dr = blq.isin(["DESC", "REP"])
    assert not (idx >= pd.Timestamp("2026-10-01")).any(), "HOLDOUT-A4 breach!"

    mat_d = {}
    mat_m = {}
    summary = {}
    alive_list = []

    for res in sorted(results, key=lambda r: r["spec"]["sym"]):
        sym = res["spec"]["sym"]
        cls = res["spec"]["cls"]
        for mec, s in res["d"].items():
            sm = res["m"][mec]
            col = f"{sym}_{mec}"
            st_desc = stats_block(s[blq == "DESC"], sm[blq == "DESC"])
            st_rep = stats_block(s[blq == "REP"], sm[blq == "REP"])
            st_dr = stats_block(s[mask_dr], sm[mask_dr])
            st_rec_dr = stats_block(s[mask_dr & (idx >= "2019-07-01")], sm[mask_dr & (idx >= "2019-07-01")])
            # Alive criterion: positive in BOTH A5 DESC & REP, Sharpe >= 0.40 on DESC_REP, >= 60% yrs positive on DESC_REP
            vivo = bool(st_desc["usd_mes"] > 0 and st_rep["usd_mes"] > 0 and st_dr["sharpe"] >= 0.40 and st_dr["pct_anios_pos"] >= 0.60)
            if vivo:
                alive_list.append(col)
            summary[col] = {
                "sym": sym, "cls": cls, "mec": mec, "n_trades": int(res["cnt"][mec]),
                "DESC": st_desc, "REP": st_rep, "DESC_REP": st_dr, "DESC_REP_19_26": st_rec_dr, "vivo": vivo,
            }
            # Strictly seal A5 HOLDOUT/EMBARGO/TERMINAL in saved series!
            mat_d[col] = np.where(mask_dr, s.to_numpy(), np.nan)
            mat_m[col] = np.where(mask_dr, sm.to_numpy(), np.nan)

    df_d = pd.DataFrame(mat_d, index=idx)
    df_m = pd.DataFrame(mat_m, index=idx)

    # Save 2019-07 -> 2026-09 slice for compact portfolio merging
    df_d_sub = df_d[df_d.index >= "2019-07-01"]
    df_m_sub = df_m[df_m.index >= "2019-07-01"]
    df_d_sub.to_csv(out_dir / "KAGGLE_M1_DAILY_DR.csv.gz")
    df_m_sub.to_csv(out_dir / "KAGGLE_M1_MIN_DR.csv.gz")

    out_json = {
        "n_assets": len(SPECS),
        "n_candidates": len(summary),
        "alive_candidates": alive_list,
        "elapsed_s": round(time.time() - t0, 1),
        "candidates": summary,
    }
    (out_dir / "KAGGLE_M1_EXPANSION.json").write_text(json.dumps(out_json, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"\nDONE in {time.time() - t0:.1f}s | VIVOS ({len(alive_list)}): {alive_list}", flush=True)


if __name__ == "__main__":
    main()
