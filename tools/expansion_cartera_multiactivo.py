#!/usr/bin/env python3
"""Paso 4: Expansion multi-activo y multi-estrategia (2026-11-26).

1) Mejoras causales y transferencias CME que faltaban en regla_cartera:
   - W_eod_ATR25_NQ (de NQ_W_44e274ad1d.pkl con stop causal 0.25*ATR20, friccion MNQ)
   - V_nm30_tp1400_NQ (de NQ_V_df0415f27f.pkl, friccion MNQ)
   - R_ATR25_NQ, R_ATR50_NQ, Z_ATR50_NQ, N_ATR25_NQ (de FS_OPS_NQ_IL.csv.gz con MAE stop causal, friccion MNQ)
   - SOM_eod_NQ, SOM_eod_ES (de SOM_OPS_{NQ,ES}.csv.gz celda='eod', fricciones MNQ/MES - compatible Lucid!)
   - ES_T_adapt, YM_T_adapt, RTY_T_adapt (de *_T_*.pkl transferidos, fricciones canonicas MES/MYM/M2K con estimados_permitidos)

2) 3 mecanismos canonicos en unidades proporcionales (0 grilla, < 2026-10-01, evaluacion DESC vs REP de A5, HOLDOUT SELLADO)
   sobre los 8 CSV M1 ortogonales en data/m1dk/:
   - Mecanismo A: Trend Following Donchian 55/20 1D L/S multi-activo (stop 2.0*ATR20)
   - Mecanismo B: ORB intradia en apertura local de efectivo (banda 0.25*ATR20, stop 0.45*ATR20, obj 2R, cierre EOD local)
   - Mecanismo C: Overnight con filtro de tendencia (DAX, FTSE, NKD, XAU; stop 0.50*ATR20 + swap 8%)

Uso:
  python -u tools/expansion_cartera_multiactivo.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))

from edgelab import costos
from edgelab.holdout import a5_bloque
from edgelab.research.m1_intradia import leer_m1, leer_m1nt8

OUT = ROOT / "docs/research/auditoria_cartera_20261126"
OUT.mkdir(parents=True, exist_ok=True)
FS_PKL_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\scratch\EdgeLab-fundedsync\data\fundedsync_post_il_20261122")

CUTOFF_STR = "2026-09-29"

M1DK_SPECS = [
    {"file": "DEUIDXEUR-M1-.csv", "sym": "DAX", "tz": "Europe/Berlin", "open": (9, 0), "eod": (17, 30), "fric": 2.0, "risk_usd": 75.0, "onight": True, "asset_class": "EU_IDX"},
    {"file": "EUSIDXEUR-M1-.csv", "sym": "EUSTX", "tz": "Europe/Berlin", "open": (9, 0), "eod": (17, 30), "fric": 1.5, "risk_usd": 75.0, "onight": False, "asset_class": "EU_IDX"},
    {"file": "GBRIDXGBP-M1-.csv", "sym": "FTSE", "tz": "Europe/London", "open": (8, 0), "eod": (16, 30), "fric": 1.5, "risk_usd": 75.0, "onight": True, "asset_class": "UK_IDX"},
    {"file": "JPNIDXJPY-M1-.csv", "sym": "NKD", "tz": "Asia/Tokyo", "open": (9, 0), "eod": (15, 0), "fric": 10.0, "risk_usd": 75.0, "onight": True, "asset_class": "JP_IDX"},
    {"file": "LIGHTCMDUSD-M1-.csv", "sym": "WTI", "tz": "America/New_York", "open": (9, 0), "eod": (14, 30), "fric": 0.04, "risk_usd": 75.0, "onight": False, "asset_class": "ENERGY"},
    {"file": "XAUUSD_M1_dukas-M1-.csv", "sym": "XAU", "tz": "America/New_York", "open": (8, 20), "eod": (15, 0), "fric": 0.69, "risk_usd": 75.0, "onight": True, "asset_class": "GOLD"},
    {"file": "EURUSD_M1_dukas-M1-.csv", "sym": "EURUSD", "tz": "America/New_York", "open": (8, 0), "eod": (15, 55), "fric": 0.00018, "risk_usd": 75.0, "onight": False, "asset_class": "FX"},
    {"file": "USDJPY_M1_dukas-M1-.csv", "sym": "USDJPY", "tz": "America/New_York", "open": (8, 0), "eod": (15, 55), "fric": 0.020, "risk_usd": 75.0, "onight": False, "asset_class": "FX"},
]


def _sesion_ny(ny_dt: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (ny_dt + pd.Timedelta(hours=6)).normalize()


def compute_atr20_nq() -> pd.Series:
    d_ny = leer_m1nt8(ROOT / "data/m1nt8/NQ_M1_nonadj_utc.parquet")
    d_ny = d_ny[d_ny.index >= "2011-01-01"]
    ses = _sesion_ny(d_ny.index)
    day = pd.DataFrame({
        "h": d_ny["h"].groupby(ses).max(),
        "l": d_ny["l"].groupby(ses).min(),
        "c": d_ny["c"].groupby(ses).last(),
    })
    pc = day["c"].shift(1)
    tr = np.maximum(day["h"] - day["l"], np.maximum((day["h"] - pc).abs(), (day["l"] - pc).abs()))
    return tr.rolling(20, min_periods=10).mean().shift(1)


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


def load_pkl_series(fn: str, orig_pv: float, target_pv: float, fr_pts: float, atr_s: pd.Series | None = None, cat_atr_mult: float | None = None, idx: pd.DatetimeIndex | None = None) -> tuple[pd.Series, pd.Series]:
    df = pd.read_pickle(FS_PKL_DIR / fn).copy()
    ex_ny = pd.to_datetime(df["exit_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    en_ny = pd.to_datetime(df["entry_time_utc"], unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df["dia"] = ex_ny.dt.normalize()
    df = df[df["dia"] <= CUTOFF_STR].copy()
    qty = df["qty"].to_numpy(float)
    mae_pts = df["mae_usd"].abs().to_numpy(float) / (np.maximum(qty, 1.0) * orig_pv)
    pnl_pts = df["pnl_pts"].to_numpy(float)
    if cat_atr_mult is not None and atr_s is not None:
        atr_vals = atr_s.reindex(_sesion_ny(pd.DatetimeIndex(en_ny.loc[df.index]))).to_numpy(float)
        st = cat_atr_mult * atr_vals
        hit = np.isfinite(st) & (st > 0) & (mae_pts >= st)
        pnl_pts = np.where(hit, -st, pnl_pts)
        mae_eff = np.where(hit, st, mae_pts)
    else:
        mae_eff = mae_pts

    df["usd"] = (pnl_pts - fr_pts) * target_pv
    df["min_usd"] = np.minimum(-(mae_eff + fr_pts) * target_pv, df["usd"])
    s = df.groupby("dia")["usd"].sum()
    sm = df.groupby("dia")["min_usd"].sum()
    if idx is not None:
        s = s.reindex(idx, fill_value=0.0)
        sm = sm.reindex(idx, fill_value=0.0)
    return s, sm


def load_fs_variant(fs_df: pd.DataFrame, modulo: str, fr_nq: float, fr_mnq: float, cat_atr_mult: float | None, idx: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    g = fs_df[fs_df["modulo"] == modulo].copy()
    g = g[g["dia"] <= CUTOFF_STR].copy()
    bruto = g["neto"].to_numpy(float) + fr_nq
    mae = g["mae_pts"].abs().to_numpy(float)
    atr = g["atr20"].to_numpy(float)
    if cat_atr_mult is not None:
        st = cat_atr_mult * atr
        hit = np.isfinite(st) & (st > 0) & (mae >= st)
        bruto = np.where(hit, -st, bruto)
        mae = np.where(hit, st, mae)
    g["usd"] = (bruto - fr_mnq) * 2.0
    g["min_usd"] = np.minimum(-(mae + fr_mnq) * 2.0, g["usd"])
    return g.groupby("dia")["usd"].sum().reindex(idx, fill_value=0.0), g.groupby("dia")["min_usd"].sum().reindex(idx, fill_value=0.0)


def load_som_eod(fn: str, fr_micro_pts: float, pv_micro: float, idx: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    df = pd.read_csv(ROOT / "docs/research/m1_largo_20261117" / fn)
    df = df[df["celda"] == "eod"].copy()
    df["dia"] = pd.to_datetime(df["dia"])
    df = df[df["dia"] <= CUTOFF_STR].copy()
    df["usd"] = (df["bruto"] - fr_micro_pts) * pv_micro
    # Conservative intraday min for EOD trade: stop out at -riesgo if trailing stop wasn't tighter
    df["min_usd"] = np.minimum(-(df["riesgo"].abs() + fr_micro_pts) * pv_micro, df["usd"])
    return df.groupby("dia")["usd"].sum().reindex(idx, fill_value=0.0), df.groupby("dia")["min_usd"].sum().reindex(idx, fill_value=0.0)


def eval_m1dk_asset(spec: dict, full_idx: pd.DatetimeIndex) -> dict:
    """Evalua los 3 mecanismos canonicos en 1 activo M1DK. Retorna series diarias (< 2026-09-30) y metricas DESC/REP."""
    p = ROOT / "data/m1dk" / spec["file"]
    df = leer_m1(p)
    df = df[(df.index >= "2012-01-01") & (df.index <= "2026-09-29 23:59:59")].copy()

    # Convert NY naive index -> local market naive timestamp cleanly via UTC offset mapping
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if spec["tz"] == "America/New_York":
            loc_idx = df.index
        else:
            ny_aware = df.index.tz_localize("America/New_York", ambiguous="NaT", nonexistent="shift_forward")
            ok = ~ny_aware.isna()
            df = df[ok].copy()
            loc_idx = ny_aware[ok].tz_convert(spec["tz"]).tz_localize(None)
    df.index = loc_idx

    # Build 1D OHLC in local calendar date
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

    fric = float(spec["fric"])
    risk_usd = float(spec["risk_usd"])

    # ---- MECANISMO A: Donchian 55/20 1D Trend Following L/S (cierre por Donchian 20 o stop 2*ATR20) ----
    # Causal: señal al cierre del dia t-1 (usando shift(1) ya aplicado en hi55/lo55/atr20 -> se entra al open[t]!)
    pos = 0
    entry_p = 0.0
    stop_p = 0.0
    unit_qty = 0.0
    don_ret = np.zeros(len(d1))
    don_min = np.zeros(len(d1))
    don_trades = 0
    o_a, h_a, l_a, c_a = d1["o"].to_numpy(), d1["h"].to_numpy(), d1["l"].to_numpy(), d1["c"].to_numpy()
    h55, l55, h20, l20, atr_a = d1["hi55"].to_numpy(), d1["lo55"].to_numpy(), d1["hi20"].to_numpy(), d1["lo20"].to_numpy(), d1["atr20"].to_numpy()
    c_prev_a = pc.to_numpy()

    for i in range(60, len(d1)):
        if not np.isfinite(atr_a[i]) or atr_a[i] <= 0:
            continue
        # Mark-to-market / check exit during day i
        if pos != 0:
            ex_p = None
            if pos == 1:
                if o_a[i] <= stop_p:
                    ex_p = o_a[i]
                elif l_a[i] <= stop_p:
                    ex_p = stop_p
                elif c_prev_a[i] < l20[i]:
                    ex_p = o_a[i]
                day_worst = (l_a[i] - c_prev_a[i]) * unit_qty if ex_p is None else (ex_p - c_prev_a[i]) * unit_qty
            else:
                if o_a[i] >= stop_p:
                    ex_p = o_a[i]
                elif h_a[i] >= stop_p:
                    ex_p = stop_p
                elif c_prev_a[i] > h20[i]:
                    ex_p = o_a[i]
                day_worst = (c_prev_a[i] - h_a[i]) * unit_qty if ex_p is None else (c_prev_a[i] - ex_p) * unit_qty

            if ex_p is not None:
                # Close at ex_p (note: if ex_p == o_a[i] from open trigger, gap from prev close to o_a[i])
                prev_ref = c_prev_a[i] if i > 0 else entry_p
                don_ret[i] += pos * (ex_p - prev_ref) * unit_qty - (0.5 * fric) * unit_qty
                don_min[i] += min(day_worst - (0.5 * fric) * unit_qty, don_ret[i])
                pos = 0
                unit_qty = 0.0
            else:
                don_ret[i] += pos * (c_a[i] - c_prev_a[i]) * unit_qty
                don_min[i] += min(day_worst, don_ret[i])

        # Entry check at open[i] using signal from t-1 close
        if pos == 0:
            if c_prev_a[i] > h55[i]:
                pos = 1
                entry_p = o_a[i]
                st_dist = 2.0 * atr_a[i]
                stop_p = entry_p - st_dist
                unit_qty = risk_usd / st_dist
                don_trades += 1
                if l_a[i] <= stop_p:
                    don_ret[i] += (stop_p - entry_p - fric) * unit_qty
                    don_min[i] += don_ret[i]
                    pos = 0
                else:
                    don_ret[i] += (c_a[i] - entry_p - 0.5 * fric) * unit_qty
                    don_min[i] += (l_a[i] - entry_p - 0.5 * fric) * unit_qty
            elif c_prev_a[i] < l55[i]:
                pos = -1
                entry_p = o_a[i]
                st_dist = 2.0 * atr_a[i]
                stop_p = entry_p + st_dist
                unit_qty = risk_usd / st_dist
                don_trades += 1
                if h_a[i] >= stop_p:
                    don_ret[i] += (entry_p - stop_p - fric) * unit_qty
                    don_min[i] += don_ret[i]
                    pos = 0
                else:
                    don_ret[i] += (entry_p - c_a[i] - 0.5 * fric) * unit_qty
                    don_min[i] += (entry_p - h_a[i] - 0.5 * fric) * unit_qty

    s_don = pd.Series(don_ret, index=d1.index).reindex(full_idx, fill_value=0.0)
    s_don_m = pd.Series(don_min, index=d1.index).reindex(full_idx, fill_value=0.0)

    # ---- MECANISMO B: ORB Cash-Open 15m Noise Band (0.25*ATR20, stop 0.45*ATR20, tgt 2R, cierre EOD local) ----
    oh, om = spec["open"]
    eh, em = spec["eod"]
    open_min = oh * 60 + om
    eod_min = eh * 60 + em
    # Resample to 15m for fast exact session open / close and conservative stop-first sim, OR use M1 grouped cleanly!
    # Actually numpy iteration over session M1 slices takes < 1.2s total for 3500 days!
    mins_of_day = df.index.hour * 60 + df.index.minute
    sess_mask = (mins_of_day >= open_min) & (mins_of_day <= eod_min)
    df_s = df[sess_mask]
    dates_s = df_s.index.normalize()
    atr_map = d1["atr20"].to_dict()

    orb_ret = {}
    orb_min = {}
    orb_trades = 0
    # Split by date indices using numpy unique boundaries
    d_vals = dates_s.to_numpy()
    chg = np.flatnonzero(np.concatenate(([True], d_vals[1:] != d_vals[:-1], [True])))
    o_s = df_s["o"].to_numpy()
    h_s = df_s["h"].to_numpy()
    l_s = df_s["l"].to_numpy()
    c_s = df_s["c"].to_numpy()
    m_s = (df_s.index.hour * 60 + df_s.index.minute).to_numpy()

    for k in range(len(chg) - 1):
        i0, i1 = chg[k], chg[k + 1]
        if i1 - i0 < 30:
            continue
        dt = pd.Timestamp(d_vals[i0])
        atr_v = atr_map.get(dt, np.nan)
        if not np.isfinite(atr_v) or atr_v <= 0:
            continue
        op0 = o_s[i0]
        # Wait 15 mins after open to avoid opening auction spike noise, then allow breakout within first 3 hours
        band = 0.25 * atr_v
        st_dist = 0.45 * atr_v
        tgt_dist = 2.0 * st_dist
        up_lv = op0 + band
        dn_lv = op0 - band
        win_end = open_min + 210
        side = 0
        ep = 0.0
        sp = 0.0
        tp = 0.0
        mae_pts = 0.0
        ex_p = np.nan
        for j in range(i0 + 15, i1):
            if side == 0:
                if m_s[j] > win_end:
                    break
                if h_s[j] >= up_lv:
                    side = 1
                    ep = max(o_s[j], up_lv)
                    sp = ep - st_dist
                    tp = ep + tgt_dist
                    orb_trades += 1
                    # Conservative same-bar: stop only
                    if l_s[j] <= sp:
                        ex_p = sp
                        mae_pts = st_dist
                        break
                    mae_pts = max(mae_pts, ep - l_s[j])
                elif l_s[j] <= dn_lv:
                    side = -1
                    ep = min(o_s[j], dn_lv)
                    sp = ep + st_dist
                    tp = ep - tgt_dist
                    orb_trades += 1
                    if h_s[j] >= sp:
                        ex_p = sp
                        mae_pts = st_dist
                        break
                    mae_pts = max(mae_pts, h_s[j] - ep)
            else:
                if side == 1:
                    if o_s[j] <= sp:
                        ex_p = o_s[j]; mae_pts = max(mae_pts, ep - ex_p); break
                    if l_s[j] <= sp:
                        ex_p = sp; mae_pts = max(mae_pts, st_dist); break
                    mae_pts = max(mae_pts, ep - l_s[j])
                    if h_s[j] >= tp:
                        ex_p = tp; break
                else:
                    if o_s[j] >= sp:
                        ex_p = o_s[j]; mae_pts = max(mae_pts, ex_p - ep); break
                    if h_s[j] >= sp:
                        ex_p = sp; mae_pts = max(mae_pts, st_dist); break
                    mae_pts = max(mae_pts, h_s[j] - ep)
                    if l_s[j] <= tp:
                        ex_p = tp; break
        if side != 0:
            if not np.isfinite(ex_p):
                ex_p = c_s[i1 - 1]
            pnl_pts = side * (ex_p - ep) - fric
            qty_u = risk_usd / st_dist
            usd = pnl_pts * qty_u
            min_u = min(-(mae_pts + fric) * qty_u, usd)
            orb_ret[dt] = usd
            orb_min[dt] = min_u

    s_orb = pd.Series(orb_ret, dtype=float).reindex(full_idx, fill_value=0.0)
    s_orb_m = pd.Series(orb_min, dtype=float).reindex(full_idx, fill_value=0.0)

    # ---- MECANISMO C: Overnight con filtro de tendencia (DAX, FTSE, NKD, XAU) ----
    s_on = pd.Series(0.0, index=full_idx)
    s_on_m = pd.Series(0.0, index=full_idx)
    on_trades = 0
    if spec["onight"]:
        # Build overnight segment: from eod[d-1] close -> open[d] close (approximated causally on 15m/1D bars using eod_c -> next day min/max/open!)
        # Extract exact local EOD close (15m bar at eod_hm) and next day Open bar + overnight min low
        eod_bars = df[(mins_of_day >= eod_min - 5) & (mins_of_day <= eod_min)].groupby(df[(mins_of_day >= eod_min - 5) & (mins_of_day <= eod_min)].index.normalize())["c"].last()
        open_bars = df[(mins_of_day >= open_min) & (mins_of_day <= open_min + 5)].groupby(df[(mins_of_day >= open_min) & (mins_of_day <= open_min + 5)].index.normalize())["o"].first()
        # Overnight window between day d-1 eod_min and day d open_min: scan numpy for gaps/stops
        # Map each bar to target exit session day: if time > eod_min -> next business day; if time < open_min -> current day
        ts_idx = df.index
        norm_d = ts_idx.normalize()
        # Only bars outside cash session
        out_mask = (mins_of_day > eod_min) | (mins_of_day < open_min)
        df_ov = df[out_mask].copy()
        ov_ret, ov_min = {}, {}
        dates_list = list(d1.index)
        for k in range(25, len(dates_list) - 1):
            d_in = dates_list[k]
            d_ex = dates_list[k + 1]
            # Trend filter known BEFORE d_in EOD: prev close > sma20 AND sma20 rising
            if d_in not in eod_bars.index or d_ex not in open_bars.index:
                continue
            sma = d1.at[d_in, "sma20"]
            smap = d1.at[d_in, "sma20_prev5"]
            atr_v = d1.at[d_in, "atr20"]
            if not (np.isfinite(sma) and np.isfinite(smap) and np.isfinite(atr_v) and atr_v > 0):
                continue
            ep = float(eod_bars.at[d_in])
            if not (ep > sma and sma > smap):
                continue
            # Overnight slice between (d_in @ eod_min) and (d_ex @ open_min)
            t0 = d_in + pd.Timedelta(minutes=eod_min + 1)
            t1 = d_ex + pd.Timedelta(minutes=open_min)
            sl = df_ov.loc[t0:t1]
            st_dist = 0.50 * atr_v
            sp = ep - st_dist
            qty_u = risk_usd / st_dist
            ex_p = float(open_bars.at[d_ex])
            mae_pts = 0.0
            if len(sl) > 0:
                l_arr = sl["l"].to_numpy()
                o_arr = sl["o"].to_numpy()
                hits = np.flatnonzero(l_arr <= sp)
                if len(hits) > 0:
                    j0 = hits[0]
                    ex_p = o_arr[j0] if o_arr[j0] <= sp else sp
                    mae_pts = max(ep - ex_p, st_dist)
                else:
                    mae_pts = max(0.0, ep - float(l_arr.min()))
            # Conservative 8% annualized financing cost (3x Wednesday swap)
            n_nights = max(1, (d_ex - d_in).days)
            swap_pts = ep * (0.08 / 365.0) * n_nights
            pnl_pts = (ex_p - ep) - fric - swap_pts
            usd = pnl_pts * qty_u
            min_u = min(-(mae_pts + fric + swap_pts) * qty_u, usd)
            ov_ret[d_ex] = usd
            ov_min[d_ex] = min_u
            on_trades += 1
        s_on = pd.Series(ov_ret, dtype=float).reindex(full_idx, fill_value=0.0)
        s_on_m = pd.Series(ov_min, dtype=float).reindex(full_idx, fill_value=0.0)

    return {
        "sym": spec["sym"],
        "asset_class": spec["asset_class"],
        "DON": (s_don, s_don_m, don_trades),
        "ORB": (s_orb, s_orb_m, orb_trades),
        "OVN": (s_on, s_on_m, on_trades),
    }


def main() -> None:
    base_d = pd.read_csv(OUT / "SERIES_AUDITORIA_DIARIAS.csv.gz", index_col=0, parse_dates=True)
    base_m = pd.read_csv(OUT / "SERIES_AUDITORIA_MIN_INTRADIA.csv.gz", index_col=0, parse_dates=True)
    idx = base_d.index  # 2019-07-01 .. 2026-09-29
    assert (idx <= CUTOFF_STR).all(), "Date breach in base_d"

    atr_nq = compute_atr20_nq()
    fr_nq = float(costos.friccion_rt_puntos("NQ", "base"))
    fr_mnq = float(costos.friccion_rt_puntos("MNQ", "base"))
    fr_mes = float(costos.friccion_rt_puntos("MES", "base"))
    fr_mym = float(costos.friccion_rt_puntos("MYM", "base"))
    with costos.estimados_permitidos("expansion_cartera_multiactivo_20261126: RTY->M2K spread estimado de RTY"):
        fr_m2k = float(costos.friccion_rt_puntos("M2K", "base"))

    fs_df = pd.read_csv(ROOT / "docs/research/remedicion_fs_il_20261121/FS_OPS_NQ_IL.csv.gz", parse_dates=["dia"])

    new_d = pd.DataFrame(index=idx)
    new_m = pd.DataFrame(index=idx)
    catalog: dict = {"cme_improvements": {}, "m1dk_candidates": {}}

    print("=== 1. MEJORAS CAUSALES Y TRANSFERENCIAS CME (2019-07 -> 2026-09) ===")
    cme_specs = [
        ("W_eod_ATR25_NQ", lambda: load_pkl_series("NQ_W_44e274ad1d.pkl", 20.0, 2.0, fr_mnq, atr_nq, 0.25, idx), "Intraday NQ (VWAP cross + 0.25 ATR stop)"),
        ("V_nm30_tp1400_NQ", lambda: load_pkl_series("NQ_V_df0415f27f.pkl", 20.0, 2.0, fr_mnq, None, None, idx), "Intraday NQ (VaultBreak nm=0.30)"),
        ("R_ATR25_NQ", lambda: load_fs_variant(fs_df, "R", fr_nq, fr_mnq, 0.25, idx), "Intraday NQ (AtrPhase + 0.25 ATR cat stop)"),
        ("R_ATR50_NQ", lambda: load_fs_variant(fs_df, "R", fr_nq, fr_mnq, 0.50, idx), "Intraday NQ (AtrPhase + 0.50 ATR cat stop)"),
        ("Z_ATR50_NQ", lambda: load_fs_variant(fs_df, "Z", fr_nq, fr_mnq, 0.50, idx), "Intraday NQ (Zeta + 0.50 ATR cat stop)"),
        ("N_ATR25_NQ", lambda: load_fs_variant(fs_df, "N", fr_nq, fr_mnq, 0.25, idx), "Intraday NQ (NDayLong + 0.25 ATR cat stop)"),
        ("SOM_eod_NQ", lambda: load_som_eod("SOM_OPS_NQ.csv.gz", fr_mnq, 2.0, idx), "Intraday NQ (SessionOpenMomentum cierre EOD - Lucid ok)"),
        ("SOM_eod_ES", lambda: load_som_eod("SOM_OPS_ES.csv.gz", fr_mes, 5.0, idx), "Intraday ES (SessionOpenMomentum cierre EOD - Lucid ok)"),
        ("T_ES_adapt", lambda: load_pkl_series("ES_T_e2dfc11459.pkl", 50.0, 5.0, fr_mes, None, None, idx), "Intraday ES (FtmOrb transferido 1 MES)"),
        ("T_YM_adapt", lambda: load_pkl_series("YM_T_fb5a206c81.pkl", 5.0, 0.5, fr_mym, None, None, idx), "Intraday YM (FtmOrb transferido 1 MYM)"),
        ("T_RTY_adapt", lambda: load_pkl_series("RTY_T_93740f3719.pkl", 50.0, 5.0, fr_m2k, None, None, idx), "Intraday RTY (FtmOrb transferido 1 M2K)"),
    ]

    ses_int = pd.Series([int(d.strftime("%Y%m%d")) for d in idx], index=idx)
    blq = ses_int.map(a5_bloque)
    mask_dr = blq.isin(["DESC", "REP"])

    for name, fn, desc in cme_specs:
        s, sm = fn()
        new_d[name] = s
        new_m[name] = sm
        st_all = stats_block(s, sm)
        st_desc = stats_block(s[blq == "DESC"], sm[blq == "DESC"])
        st_rep = stats_block(s[blq == "REP"], sm[blq == "REP"])
        catalog["cme_improvements"][name] = {"desc": desc, "all_2019_2026": st_all, "A5_DESC": st_desc, "A5_REP": st_rep}
        print(f"  {name:18s} | Sh={st_all['sharpe']:5.2f} t={st_all['t_mes']:5.2f} $/m={st_all['usd_mes']:6.1f} yr+={st_all['pct_anios_pos']:4.2f} | REP $/m={st_rep['usd_mes']:6.1f}", flush=True)

    print("\n=== 2. EXPLORACION M1DK (8 ACTIVOS ORTOGONALES x 3 MECANISMOS, DESC vs REP A5; HOLDOUT SELLADO) ===")
    m1_res = {}
    for spec in M1DK_SPECS:
        out = eval_m1dk_asset(spec, idx)
        sym = spec["sym"]
        for mec in ("DON", "ORB", "OVN"):
            if mec == "OVN" and not spec["onight"]:
                continue
            s, sm, ntr = out[mec]
            col = f"DK_{mec}_{sym}"
            st_desc = stats_block(s[blq == "DESC"], sm[blq == "DESC"])
            st_rep = stats_block(s[blq == "REP"], sm[blq == "REP"])
            st_dr = stats_block(s[mask_dr], sm[mask_dr])
            alive = (st_desc["usd_mes"] > 0 and st_rep["usd_mes"] > 0)
            catalog["m1dk_candidates"][col] = {
                "sym": sym, "mec": mec, "asset_class": spec["asset_class"], "n_trades_2012_26": int(ntr),
                "A5_DESC": st_desc, "A5_REP": st_rep, "DESC_REP": st_dr, "vivo_DESC_REP": bool(alive),
            }
            # Strictly seal M1DK HOLDOUT: store NaN outside DESC+REP!
            new_d[col] = np.where(mask_dr, s, np.nan)
            new_m[col] = np.where(mask_dr, sm, np.nan)
            tag = "VIVO" if alive else "no"
            print(f"  {col:16s} | DESC: Sh={st_desc['sharpe']:5.2f} $/m={st_desc['usd_mes']:6.1f} | REP: Sh={st_rep['sharpe']:5.2f} $/m={st_rep['usd_mes']:6.1f} | {tag}", flush=True)

    # Multi-asset Donchian composite (equal risk across all 8 orthogonal M1DK assets!)
    don_cols = [c for c in new_d.columns if c.startswith("DK_DON_")]
    new_d["DK_DON_8Activos"] = new_d[don_cols].mean(axis=1) * 4.0  # ~$300/tr total risk unit normalized to portfolio scale
    new_m["DK_DON_8Activos"] = new_m[don_cols].mean(axis=1) * 4.0
    st_don_desc = stats_block(new_d.loc[blq == "DESC", "DK_DON_8Activos"], new_m.loc[blq == "DESC", "DK_DON_8Activos"])
    st_don_rep = stats_block(new_d.loc[blq == "REP", "DK_DON_8Activos"], new_m.loc[blq == "REP", "DK_DON_8Activos"])
    st_don_dr = stats_block(new_d.loc[mask_dr, "DK_DON_8Activos"], new_m.loc[mask_dr, "DK_DON_8Activos"])
    catalog["m1dk_candidates"]["DK_DON_8Activos"] = {"DESC": st_don_desc, "REP": st_don_rep, "DESC_REP": st_don_dr}
    print(f"\n  >>> DK_DON_8Activos composite: DESC Sh={st_don_desc['sharpe']:.2f} ($/m={st_don_desc['usd_mes']:.1f}) | REP Sh={st_don_rep['sharpe']:.2f} ($/m={st_don_rep['usd_mes']:.1f})")

    # Build ORB & OVN surviving M1DK composites (strictly those alive in DESC AND REP!)
    orb_alive = [c for c, v in catalog["m1dk_candidates"].items() if c.startswith("DK_ORB_") and v["vivo_DESC_REP"]]
    ovn_alive = [c for c, v in catalog["m1dk_candidates"].items() if c.startswith("DK_OVN_") and v["vivo_DESC_REP"]]
    if orb_alive:
        new_d["DK_ORB_Vivos"] = new_d[orb_alive].sum(axis=1) / max(1.0, len(orb_alive) ** 0.5)
        new_m["DK_ORB_Vivos"] = new_m[orb_alive].sum(axis=1) / max(1.0, len(orb_alive) ** 0.5)
        print("  >>> DK_ORB_Vivos:", orb_alive, stats_block(new_d.loc[mask_dr, "DK_ORB_Vivos"], new_m.loc[mask_dr, "DK_ORB_Vivos"]))
    if ovn_alive:
        new_d["DK_OVN_Vivos"] = new_d[ovn_alive].sum(axis=1) / max(1.0, len(ovn_alive) ** 0.5)
        new_m["DK_OVN_Vivos"] = new_m[ovn_alive].sum(axis=1) / max(1.0, len(ovn_alive) ** 0.5)
        print("  >>> DK_OVN_Vivos:", ovn_alive, stats_block(new_d.loc[mask_dr, "DK_OVN_Vivos"], new_m.loc[mask_dr, "DK_OVN_Vivos"]))

    # Merge into unified expanded daily & min matrices
    full_d = pd.concat([base_d, new_d], axis=1)
    full_m = pd.concat([base_m, new_m], axis=1)
    assert (full_d.index <= CUTOFF_STR).all(), "Holdout-A4 date leak!"
    full_d.to_csv(OUT / "SERIES_EXPANDIDAS_DIARIAS.csv.gz")
    full_m.to_csv(OUT / "SERIES_EXPANDIDAS_MIN_INTRADIA.csv.gz")

    catalog["alive_m1dk"] = [c for c, v in catalog["m1dk_candidates"].items() if v.get("vivo_DESC_REP")]
    (OUT / "EXPANSION_MULTIACTIVO.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print("\nSaved:", OUT / "EXPANSION_MULTIACTIVO.json", "| Total columns:", full_d.shape[1])


if __name__ == "__main__":
    main()
