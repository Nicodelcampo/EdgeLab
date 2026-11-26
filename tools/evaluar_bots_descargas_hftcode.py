#!/usr/bin/env python3
"""Forensic Code Audit & Full EdgeLab Validation Chain for the 3 Downloaded HFTCode Bots:
  1. `bar_nq_long_20260914_095412_gen2_portable.py` (NQ @ CME, 10m -> 2m, SHORT/LONG)
  2. `bar_6j_long_20260914_142933_portable.py`      (6J @ CME, 60m -> 5m & 10m -> 2m, LONG)
  3. `bot_mbtc_regulatory_momentum_portable.py`     (MBT @ CME, 60m -> 5m, LONG)

Evaluates each bot across EdgeLab's full partition chain (`DESC`, `REP`, `HOLDOUT`, `TERMINAL`)
comparing:
  - `VENDOR_MIDBAR_0FRIC`: native `(H+L)/2` or `(O+H+L+C)/4` closed-bar lookahead fills with 0 costs
  - `EDGELAB_CAUSAL_BRUTO`: causal next-M1-open fills & M1 intrabar H/L stops/targets (0 friction)
  - `EDGELAB_CAUSAL_NETO` : causal M1 execution + canonical `edgelab/costos.py` round-trip friction
"""
from __future__ import annotations

import math
import shutil
import sys
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:                                            # dependencia opcional (sólo para graficar; no está en el lock de CLAUDE.md)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = plt = None
import numpy as np
import pandas as pd
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from edgelab import costos
from edgelab.holdout import HOLDOUT_APERTURA_UTC_NS, a5_bloque, sesion_excluida

ARTIFACT_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")
SCRATCH = ARTIFACT_DIR / "scratch"
HFT_DATA_DIR = SCRATCH / "hftcode_data"
SELLADO_DIR = Path(r"C:\EdgeLab\sellado")
OUT_DIR = REPO / "docs" / "research" / "auditoria_bots_hftcode_20261124"

PREREG_MOTIVO = "docs/research/fundedsync_post_il_20261122/PREREGISTRO.md"

BG_FIG = "#0d1316"
BG_AX = "#11191c"
GRID_COL = "#243137"
FG_TEXT = "#e6eef2"
MUTED_TEXT = "#9ab0ba"
ACCENT_TEAL = "#2ec4b6"
ACCENT_GOLD = "#f4b942"
ACCENT_CORAL = "#e76f51"
ACCENT_BLUE = "#5fa8d3"
ACCENT_GREEN = "#80ed99"

plt.rcParams["text.parse_math"] = False
MIN_NS = 60_000_000_000


# =============================================================================
# 1. Data Loaders & Exact Causal Multi-Timeframe Bar Resamplers from M1 / Ticks
# =============================================================================


def _cme_trade_date_from_close_ns(close_ns: np.ndarray) -> np.ndarray:
    """CME trade_date YYYYMMDD = (UTC -> America/Chicago + 7h).date() via hourly unique lookup."""
    ns = np.asarray(close_ns, dtype=np.int64)
    if len(ns) == 0:
        return np.zeros(0, dtype=np.int64)
    uh, inv = np.unique((ns - MIN_NS) // 3_600_000_000_000, return_inverse=True)
    dt_ct = pd.DatetimeIndex(pd.to_datetime(uh * 3_600_000_000_000, unit="ns", utc=True)).tz_convert("America/Chicago") + pd.Timedelta(hours=7)
    ymd_u = dt_ct.strftime("%Y%m%d").astype(np.int64).to_numpy()
    return ymd_u[inv]


def _resample_ticks_to_m1(ts_ns: np.ndarray, px: np.ndarray, vol: np.ndarray) -> pd.DataFrame:
    """Vectorized 1-minute OHLCV bar builder from chronological ticks (bar timestamp = close_utc_ns)."""
    if len(ts_ns) == 0:
        return pd.DataFrame(columns=["close_ns", "o", "h", "l", "c", "v", "sesion"])
    order = np.argsort(ts_ns, kind="mergesort") if np.any(ts_ns[1:] < ts_ns[:-1]) else slice(None)
    t = ts_ns[order]
    p = px[order]
    v = vol[order]
    b = t // MIN_NS
    chg = np.flatnonzero(b[1:] != b[:-1]) + 1
    starts = np.concatenate((np.array([0], dtype=np.int64), chg))
    ends = np.concatenate((chg, np.array([len(b)], dtype=np.int64)))
    close_ns = (b[starts] + 1) * MIN_NS
    return pd.DataFrame({
        "close_ns": close_ns,
        "o": p[starts],
        "h": np.maximum.reduceat(p, starts),
        "l": np.minimum.reduceat(p, starts),
        "c": p[ends - 1],
        "v": np.add.reduceat(v, starts),
        "sesion": _cme_trade_date_from_close_ns(close_ns),
    })


def _resample_m1_to_tf(m1: pd.DataFrame, tf_min: int) -> pd.DataFrame:
    """Resample M1 bars (close_ns) into causal `tf_min` bars aligned to UTC clock boundaries, mapping `m1_end_idx`."""
    tf_ns = int(tf_min) * MIN_NS
    open_ns = m1["close_ns"].to_numpy(np.int64) - MIN_NS
    bucket = open_ns // tf_ns
    chg = np.flatnonzero(bucket[1:] != bucket[:-1]) + 1
    starts = np.concatenate((np.array([0], dtype=np.int64), chg))
    ends = np.concatenate((chg, np.array([len(bucket)], dtype=np.int64)))
    o = m1["o"].to_numpy(np.float64)
    h = m1["h"].to_numpy(np.float64)
    l = m1["l"].to_numpy(np.float64)
    c = m1["c"].to_numpy(np.float64)
    v = m1["v"].to_numpy(np.float64)
    return pd.DataFrame({
        "close_ns": (bucket[starts] + 1) * tf_ns,
        "m1_end_idx": ends - 1,
        "o": o[starts],
        "h": np.maximum.reduceat(h, starts),
        "l": np.minimum.reduceat(l, starts),
        "c": c[ends - 1],
        "v": np.add.reduceat(v, starts),
    })


def load_nq_m1_2020_2026() -> pd.DataFrame:
    """Load canonical CME NQ M1 bars from 2020-01-01 through 2026-11-17."""
    m1_csv = SCRATCH / "nq_m1_2008_2026.csv"
    tb = pacsv.read_csv(str(m1_csv))
    ts_ns = pd.to_datetime(tb["close_utc"].to_numpy(zero_copy_only=False), format="%Y-%m-%dT%H:%M:%S", utc=True).as_unit("ns").asi8
    mask = ts_ns >= int(pd.Timestamp("2019-12-15", tz="UTC").as_unit("ns").value)
    close_ns = ts_ns[mask]
    df = pd.DataFrame({
        "close_ns": close_ns,
        "o": tb["o"].to_numpy(zero_copy_only=False)[mask].astype(np.float64),
        "h": tb["h"].to_numpy(zero_copy_only=False)[mask].astype(np.float64),
        "l": tb["l"].to_numpy(zero_copy_only=False)[mask].astype(np.float64),
        "c": tb["c"].to_numpy(zero_copy_only=False)[mask].astype(np.float64),
        "v": tb["v"].to_numpy(zero_copy_only=False)[mask].astype(np.float64),
    })
    df["sesion"] = _cme_trade_date_from_close_ns(close_ns)
    df = df[~df["sesion"].isin({20261007})].reset_index(drop=True)
    return df


def load_6j_m1_edgelab() -> pd.DataFrame:
    """Load CME 6J ticks (2025-08..2026-09) + Sellado USDJPY->6J ticks (2026-10..2026-11) into continuous M1."""
    parts = []
    p_6j = HFT_DATA_DIR / "6J_ticks.parquet"
    if not p_6j.exists():
        p_6j = HFT_DATA_DIR / "data" / "6J_ticks.parquet"
    if p_6j.exists():
        pf = pq.ParquetFile(p_6j)
        tk = 5e-7
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=["ts_utc_ns", "price_ticks", "volume", "outside_regular"]).to_pandas()
            t = t[(~t["outside_regular"]) & (t["ts_utc_ns"] < HOLDOUT_APERTURA_UTC_NS)]
            if len(t):
                parts.append(_resample_ticks_to_m1(
                    t["ts_utc_ns"].to_numpy(np.int64),
                    t["price_ticks"].to_numpy(np.float64) * tk,
                    t["volume"].to_numpy(np.float64),
                ))

    # Append TERMINAL (2026-10-01 .. 2026-11-15) from Sellado USDJPY_ticks.parquet inverted to 6J (1 / USDJPY)
    p_uj = SELLADO_DIR / "USDJPY_ticks.parquet"
    if p_uj.exists():
        pf_u = pq.ParquetFile(p_uj)
        for g in range(pf_u.num_row_groups):
            t = pf_u.read_row_group(g, columns=["time_utc_ns", "bid", "ask", "bid_vol", "ask_vol"]).to_pandas()
            t = t[t["time_utc_ns"] >= HOLDOUT_APERTURA_UTC_NS]
            if len(t):
                mid_uj = 0.5 * (t["bid"].to_numpy(np.float64) + t["ask"].to_numpy(np.float64))
                valid = mid_uj > 1.0
                px_6j = np.round((1.0 / mid_uj[valid]) / 5e-7) * 5e-7
                vol_u = (t["bid_vol"].to_numpy(np.float64)[valid] + t["ask_vol"].to_numpy(np.float64)[valid])
                parts.append(_resample_ticks_to_m1(t["time_utc_ns"].to_numpy(np.int64)[valid], px_6j, vol_u))

    df = pd.concat(parts, ignore_index=True).sort_values("close_ns").drop_duplicates(subset=["close_ns"], keep="last").reset_index(drop=True)
    excl = {20261004, 20261011, 20261012, 20261018, 20261025, 20261029}
    df = df[~df["sesion"].isin(excl)].reset_index(drop=True)
    return df


def load_mbt_m1_edgelab() -> pd.DataFrame:
    """Load CME MBT Micro Bitcoin ticks (2025-08..2026-09) + yfinance MBT=F 5m (2026-10..2026-11 TERMINAL)."""
    parts = []
    p_mbt = HFT_DATA_DIR / "MBT_ticks.parquet"
    if not p_mbt.exists():
        p_mbt = HFT_DATA_DIR / "data" / "MBT_ticks.parquet"
    if p_mbt.exists():
        pf = pq.ParquetFile(p_mbt)
        tk = 5.0
        for g in range(pf.num_row_groups):
            t = pf.read_row_group(g, columns=["ts_utc_ns", "price_ticks", "volume", "outside_regular"]).to_pandas()
            t = t[(~t["outside_regular"]) & (t["ts_utc_ns"] < HOLDOUT_APERTURA_UTC_NS)]
            if len(t):
                parts.append(_resample_ticks_to_m1(
                    t["ts_utc_ns"].to_numpy(np.int64),
                    t["price_ticks"].to_numpy(np.float64) * tk,
                    t["volume"].to_numpy(np.float64),
                ))

    # Append TERMINAL (2026-10-01 .. 2026-11) from CME MBT=F 5m via yfinance
    try:
        import yfinance as yf
        yf_df = yf.download("MBT=F", period="60d", interval="5m", progress=False)
        if isinstance(yf_df.columns, pd.MultiIndex):
            yf_df.columns = [c[0] for c in yf_df.columns]
        if len(yf_df):
            idx_utc = pd.DatetimeIndex(yf_df.index).tz_convert("UTC") if yf_df.index.tz is not None else pd.DatetimeIndex(yf_df.index).tz_localize("UTC")
            close_ns = (idx_utc + pd.Timedelta(minutes=5)).as_unit("ns").asi8
            mask_t = close_ns > HOLDOUT_APERTURA_UTC_NS
            if np.any(mask_t):
                c_ns = close_ns[mask_t]
                sub_t = pd.DataFrame({
                    "close_ns": c_ns,
                    "o": yf_df["Open"].to_numpy(np.float64)[mask_t],
                    "h": yf_df["High"].to_numpy(np.float64)[mask_t],
                    "l": yf_df["Low"].to_numpy(np.float64)[mask_t],
                    "c": yf_df["Close"].to_numpy(np.float64)[mask_t],
                    "v": np.maximum(yf_df["Volume"].to_numpy(np.float64)[mask_t], 1.0),
                    "sesion": _cme_trade_date_from_close_ns(c_ns),
                }).dropna()
                parts.append(sub_t)
    except Exception as exc:
        print(f"  [warn] MBT=F terminal supplement skipped: {exc}", flush=True)

    df = pd.concat(parts, ignore_index=True).sort_values("close_ns").drop_duplicates(subset=["close_ns"], keep="last").reset_index(drop=True)
    return df


# =============================================================================
# 2. Exact Strategy Simulators (Vendor Mid-Bar Mode vs Causal EdgeLab M1 Mode)
# =============================================================================


def simulate_nq_gen2_bot(
    m1: pd.DataFrame,
    sig_tf_min: int = 10,
    exec_tf_min: int = 2,
    dir_filter: str = "BOTH",   # "BOTH" (as coded), "SHORT", "LONG"
    causal_m1: bool = True,
    respect_15pct_halt: bool = False,
) -> pd.DataFrame:
    """Exact replica of `BarNqLong20260914095412` (`bar_nq_long_20260914_095412_gen2_portable.py`)."""
    sig_df = _resample_m1_to_tf(m1, sig_tf_min)
    exe_df = _resample_m1_to_tf(m1, exec_tf_min)

    n1 = len(m1)
    m1_ts = m1["close_ns"].to_numpy(np.int64)
    m1_o = m1["o"].to_numpy(np.float64)
    m1_h = m1["h"].to_numpy(np.float64)
    m1_l = m1["l"].to_numpy(np.float64)
    m1_c = m1["c"].to_numpy(np.float64)
    m1_ses = m1["sesion"].to_numpy(np.int64)

    s_end = sig_df["m1_end_idx"].to_numpy(np.int64)
    s_o, s_h, s_l, s_c = sig_df["o"].to_numpy(), sig_df["h"].to_numpy(), sig_df["l"].to_numpy(), sig_df["c"].to_numpy()
    e_end = exe_df["m1_end_idx"].to_numpy(np.int64)
    e_o, e_h, e_l, e_c = exe_df["o"].to_numpy(), exe_df["h"].to_numpy(), exe_df["l"].to_numpy(), exe_df["c"].to_numpy()

    sig_closes: list[float] = []
    sig_h: list[float] = []
    sig_l: list[float] = []
    last_exec_ohlc = (0.0, 0.0, 0.0, 0.0)

    pending_sig: dict[str, Any] | None = None
    pending_mkt_open: dict[str, Any] | None = None
    pending_mkt_exit: str | None = None
    active_pos: dict[str, Any] | None = None

    alloc_cap = 50000.0
    realized_usd = 0.0
    peak_eq = alloc_cap
    halted = False
    trades: list[dict[str, Any]] = []

    ks, ke = 0, 0
    ns, ne = len(sig_df), len(exe_df)

    def _atr14() -> float:
        m = len(sig_closes)
        if m < 2:
            return 0.0
        st = max(1, m - 14)
        tot = 0.0
        cnt = 0
        for idx in range(st, m):
            hi, lo, pc = sig_h[idx], sig_l[idx], sig_closes[idx - 1]
            tot += max(hi - lo, abs(hi - pc), abs(lo - pc))
            cnt += 1
        return tot / cnt if cnt else 0.0

    def _close_pos(px: float, ts_ns: int, ses_i: int, rsn: str) -> None:
        nonlocal active_pos, realized_usd, peak_eq, halted
        if active_pos is None:
            return
        side = active_pos["side"]
        ep = active_pos["entry_px"]
        sd = active_pos["stop_dist"]
        pnl_pts = side * (px - ep)
        realized_usd += pnl_pts * 20.0
        eq = alloc_cap + realized_usd
        if eq > peak_eq:
            peak_eq = eq
        if respect_15pct_halt and peak_eq > 0 and ((peak_eq - eq) / peak_eq) * 100.0 >= 15.0:
            halted = True
        trades.append({
            "fecha_int": int(active_pos["ses"]),
            "en_ns": int(active_pos["en_ns"]),
            "ex_ns": int(ts_ns),
            "side": int(side),
            "entry_price": float(ep),
            "exit_price": float(px),
            "riesgo_pts": float(sd),
            "pnl_pts": float(pnl_pts),
            "reason": rsn,
        })
        active_pos = None

    for i in range(n1):
        ts_i = int(m1_ts[i])
        op_i, hi_i, lo_i, cl_i = float(m1_o[i]), float(m1_h[i]), float(m1_l[i]), float(m1_c[i])
        ses_i = int(m1_ses[i])

        # 1. Causal fills at M1 bar open + M1 intrabar stop/target check
        if causal_m1:
            if pending_mkt_exit is not None and active_pos is not None:
                _close_pos(op_i, ts_i - MIN_NS, ses_i, pending_mkt_exit)
                pending_mkt_exit = None
            elif pending_mkt_open is not None and active_pos is None and not halted:
                ps = pending_mkt_open
                pending_mkt_open = None
                sd = ps["stop_dist"]
                sd_sgn = -1 if ps["direction"] == "SHORT" else 1
                active_pos = {
                    "side": sd_sgn,
                    "entry_px": op_i,
                    "stop_px": (op_i + sd) if sd_sgn < 0 else (op_i - sd),
                    "target_px": (op_i - sd * ps["rr"]) if sd_sgn < 0 else (op_i + sd * ps["rr"]),
                    "stop_dist": sd,
                    "en_ns": ts_i - MIN_NS,
                    "ses": ses_i,
                }

            if active_pos is not None:
                sd_sgn = active_pos["side"]
                st_p, tg_p = active_pos["stop_px"], active_pos["target_px"]
                if sd_sgn > 0:
                    if lo_i <= st_p:
                        _close_pos(min(op_i, st_p), ts_i, ses_i, "protective_stop")
                    elif hi_i >= tg_p:
                        _close_pos(max(op_i, tg_p), ts_i, ses_i, "soft_target_hit")
                else:
                    if hi_i >= st_p:
                        _close_pos(max(op_i, st_p), ts_i, ses_i, "protective_stop")
                    elif lo_i <= tg_p:
                        _close_pos(min(op_i, tg_p), ts_i, ses_i, "soft_target_hit")

        # 2. Process closed signal bars ending at this M1 bar
        while ks < ns and int(s_end[ks]) <= i:
            sig_closes.append(float(s_c[ks]))
            sig_h.append(float(s_h[ks]))
            sig_l.append(float(s_l[ks]))
            if len(sig_closes) >= 20 and not halted:
                c0 = sig_closes[-1]
                c6 = sig_closes[-6]
                sma8 = sum(sig_closes[-8:]) / 8.0
                sma20 = sum(sig_closes[-20:]) / 20.0
                atr = _atr14()
                roc = (c0 - c6) / c6 if c6 > 0 else 0.0
                atr_pct = atr / c0 if c0 > 0 else 0.0
                rev = (c0 - sma20) / atr if atr > 0 else 0.0
                sh_sc = min(100.0, max(0.0, 50.0 + 32.0 * math.tanh(-roc * 35.0) + 18.0 * math.tanh(rev / 2.0)))
                lg_sc = min(100.0, max(0.0, 50.0 + 32.0 * math.tanh(roc * 35.0) + 18.0 * math.tanh(-rev / 2.0)))
                b_sh = 0.6 * sh_sc + 20.0
                b_lg = 0.6 * lg_sc + 20.0
                th = max(40.0, min(50.0, 50.0 - min(6.0, atr_pct * 700.0)))
                sh_ok = (b_sh >= th) and (sma8 < sma20) and (dir_filter in ("BOTH", "SHORT"))
                lg_ok = (b_lg >= th) and (sma8 > sma20) and (dir_filter in ("BOTH", "LONG"))
                cand_dir, sc = None, 0.0
                if sh_ok and lg_ok:
                    cand_dir = "SHORT" if b_sh >= b_lg else "LONG"
                    sc = max(b_sh, b_lg)
                elif sh_ok:
                    cand_dir, sc = "SHORT", b_sh
                elif lg_ok:
                    cand_dir, sc = "LONG", b_lg
                if cand_dir is not None:
                    atr_eff = atr if atr > 0 else max(c0 * 0.001, 0.01)
                    vol_adj = min(0.8, atr_pct * 200.0) if atr_pct > 0 else 0.0
                    conv_adj = max(-0.25, min(0.25, (50.0 - sc) / 200.0))
                    atr_mult = max(1.1, min(2.7, 1.6 + vol_adj + conv_adj))
                    rr = max(1.25, min(2.6, 1.35 + 0.85 * (sc / 100.0) + min(0.4, atr_pct * 120.0)))
                    pending_sig = {"direction": cand_dir, "atr": atr_eff, "atr_mult": atr_mult, "rr": rr}
            ks += 1

        # 3. Process closed execution bars ending at this M1 bar
        while ke < ne and int(e_end[ke]) <= i:
            last_exec_ohlc = (float(e_o[ke]), float(e_h[ke]), float(e_l[ke]), float(e_c[ke]))
            mid_bar = sum(last_exec_ohlc) / 4.0
            ref_px = float(e_c[ke]) if causal_m1 else mid_bar

            if active_pos is not None:
                atr_cur = _atr14()
                if atr_cur <= 0:
                    atr_cur = max(ref_px * 0.0008, 0.01)
                trail_buf = max(0.01, atr_cur * 1.1)
                sd_sgn = active_pos["side"]
                fav = (active_pos["entry_px"] - ref_px) if sd_sgn < 0 else (ref_px - active_pos["entry_px"])
                if fav > active_pos["stop_dist"] * 0.8:
                    if sd_sgn < 0:
                        active_pos["stop_px"] = min(active_pos["stop_px"], ref_px + trail_buf)
                    else:
                        active_pos["stop_px"] = max(active_pos["stop_px"], ref_px - trail_buf)
                if not causal_m1:
                    if sd_sgn < 0:
                        if mid_bar >= active_pos["stop_px"]:
                            _close_pos(mid_bar, ts_i, ses_i, "protective_stop")
                        elif mid_bar <= active_pos["target_px"]:
                            _close_pos(mid_bar, ts_i, ses_i, "soft_target_hit")
                    else:
                        if mid_bar <= active_pos["stop_px"]:
                            _close_pos(mid_bar, ts_i, ses_i, "protective_stop")
                        elif mid_bar >= active_pos["target_px"]:
                            _close_pos(mid_bar, ts_i, ses_i, "soft_target_hit")

            if pending_sig is not None and active_pos is None and pending_mkt_open is None and not halted and len(sig_closes) >= 20:
                ps = pending_sig
                pending_sig = None
                sd = max(0.01, ps["atr"] * ps["atr_mult"])
                if causal_m1:
                    pending_mkt_open = {"direction": ps["direction"], "stop_dist": sd, "rr": ps["rr"]}
                else:
                    sd_sgn = -1 if ps["direction"] == "SHORT" else 1
                    active_pos = {
                        "side": sd_sgn,
                        "entry_px": mid_bar,
                        "stop_px": (mid_bar + sd) if sd_sgn < 0 else (mid_bar - sd),
                        "target_px": (mid_bar - sd * ps["rr"]) if sd_sgn < 0 else (mid_bar + sd * ps["rr"]),
                        "stop_dist": sd,
                        "en_ns": ts_i,
                        "ses": ses_i,
                    }
            ke += 1

    return pd.DataFrame(trades)


def simulate_6j_long_bot(
    m1: pd.DataFrame,
    sig_tf_min: int = 60,
    exec_tf_min: int = 5,
    causal_m1: bool = True,
) -> pd.DataFrame:
    """Exact replica of `Bar6jLong20260914142933` (`bar_6j_long_20260914_142933_portable.py`)."""
    sig_df = _resample_m1_to_tf(m1, sig_tf_min)
    exe_df = _resample_m1_to_tf(m1, exec_tf_min)

    n1 = len(m1)
    m1_ts = m1["close_ns"].to_numpy(np.int64)
    m1_o, m1_h, m1_l, m1_c = m1["o"].to_numpy(), m1["h"].to_numpy(), m1["l"].to_numpy(), m1["c"].to_numpy()
    m1_ses = m1["sesion"].to_numpy(np.int64)

    s_end = sig_df["m1_end_idx"].to_numpy(np.int64)
    s_h, s_l, s_c, s_v = sig_df["h"].to_numpy(), sig_df["l"].to_numpy(), sig_df["c"].to_numpy(), sig_df["v"].to_numpy()
    e_end = exe_df["m1_end_idx"].to_numpy(np.int64)
    e_h, e_l, e_c = exe_df["h"].to_numpy(), exe_df["l"].to_numpy(), exe_df["c"].to_numpy()

    sig_c: list[float] = []
    sig_hi: list[float] = []
    sig_lo: list[float] = []
    sig_vol: list[float] = []
    exec_c: list[float] = []

    pending_sig: dict[str, Any] | None = None
    pending_mkt_open: dict[str, Any] | None = None
    pending_mkt_exit: str | None = None
    active_pos: dict[str, Any] | None = None
    sig_invalidated = False
    last_exec_mid = 0.0
    trades: list[dict[str, Any]] = []

    def _ema(vals: list[float], p: int) -> float:
        if not vals:
            return 0.0
        a = 2.0 / (p + 1.0)
        e = vals[0]
        for x in vals[1:]:
            e = a * x + (1.0 - a) * e
        return e

    def _rsi14(vals: list[float]) -> float:
        if len(vals) < 15:
            return 50.0
        g = l_sum = 0.0
        rec = vals[-15:]
        for idx in range(1, len(rec)):
            d = rec[idx] - rec[idx - 1]
            if d >= 0:
                g += d
            else:
                l_sum -= d
        if l_sum == 0:
            return 100.0
        return 100.0 - (100.0 / (1.0 + g / l_sum))

    def _atr14_s() -> float:
        m = len(sig_c)
        if m < 2:
            return 0.0
        st = max(1, m - 14)
        tot = 0.0
        for idx in range(st, m):
            tot += max(sig_hi[idx] - sig_lo[idx], abs(sig_hi[idx] - sig_c[idx - 1]), abs(sig_lo[idx] - sig_c[idx - 1]))
        return tot / (m - st)

    def _mom_score() -> dict[str, float]:
        ef = _ema(sig_c[-50:], 8)
        es = _ema(sig_c[-80:], 21)
        at = _atr14_s()
        rs = _rsi14(sig_c)
        ts_val = (ef - es) / at if at > 0 else 0.0
        tc = max(0.0, min(100.0, 50.0 + ts_val * 15.0))
        rc = max(0.0, min(100.0, (rs - 35.0) * (100.0 / 35.0)))
        vf = _ema(sig_vol[-30:], 5)
        vs = _ema(sig_vol[-60:], 20)
        vc = 60.0 if vf <= vs else 40.0
        sc = max(0.0, min(100.0, 0.5 * tc + 0.35 * rc + 0.15 * vc))
        return {"ef": ef, "es": es, "atr": at, "score": sc, "vf": vf, "vs": vs}

    def _close_pos(px: float, ts_ns: int, rsn: str) -> None:
        nonlocal active_pos, sig_invalidated
        if active_pos is None:
            return
        ep = active_pos["entry_px"]
        sd = active_pos["stop_dist"]
        trades.append({
            "fecha_int": int(active_pos["ses"]),
            "en_ns": int(active_pos["en_ns"]),
            "ex_ns": int(ts_ns),
            "side": 1,
            "entry_price": float(ep),
            "exit_price": float(px),
            "riesgo_pts": float(sd),
            "pnl_pts": float(px - ep),
            "reason": rsn,
        })
        active_pos = None
        sig_invalidated = False

    ks, ke = 0, 0
    ns, ne = len(sig_df), len(exe_df)

    for i in range(n1):
        ts_i = int(m1_ts[i])
        op_i, hi_i, lo_i = float(m1_o[i]), float(m1_h[i]), float(m1_l[i])
        ses_i = int(m1_ses[i])

        if causal_m1:
            if pending_mkt_exit is not None and active_pos is not None:
                _close_pos(op_i, ts_i - MIN_NS, pending_mkt_exit)
                pending_mkt_exit = None
            elif pending_mkt_open is not None and active_pos is None:
                ps = pending_mkt_open
                pending_mkt_open = None
                sd = ps["stop_dist"]
                active_pos = {
                    "entry_px": op_i,
                    "stop_px": op_i - sd,
                    "target_px": op_i + sd * ps["rr"],
                    "stop_dist": sd,
                    "born_exec": ps["born_exec"],
                    "en_ns": ts_i - MIN_NS,
                    "ses": ses_i,
                }

            if active_pos is not None:
                if lo_i <= active_pos["stop_px"]:
                    _close_pos(min(op_i, active_pos["stop_px"]), ts_i, "stop_hit")
                elif hi_i >= active_pos["target_px"]:
                    _close_pos(max(op_i, active_pos["target_px"]), ts_i, "soft_target_hit")

        while ks < ns and int(s_end[ks]) <= i:
            warmup_ok = len(sig_c) >= 20
            sig_c.append(float(s_c[ks]))
            sig_hi.append(float(s_h[ks]))
            sig_lo.append(float(s_l[ks]))
            sig_vol.append(float(s_v[ks]))
            s_mid = 0.5 * (float(s_h[ks]) + float(s_l[ks]))
            if len(sig_c) >= 2:
                ind = _mom_score()
                if active_pos is not None or pending_mkt_open is not None:
                    if ind["ef"] < ind["es"] and ind["score"] < 38.0:
                        sig_invalidated = True
                elif warmup_ok:
                    cl_s = float(s_c[ks])
                    atr_v = ind["atr"] if ind["atr"] > 0 else max(cl_s * 0.0004, 1e-5)
                    ext = (cl_s - ind["ef"]) / atr_v if atr_v > 0 else 99.0
                    mr_ok = 0.0 <= ext <= 1.3
                    tr_ok = (ind["ef"] > ind["es"]) and (cl_s >= ind["ef"])
                    vr_ok = ind["vf"] <= ind["vs"] * 1.1
                    if tr_ok and mr_ok and vr_ok and ind["score"] >= 36.0:
                        ref_m = last_exec_mid if last_exec_mid > 0 else s_mid
                        atr_pct = (atr_v / ref_m) * 100.0 if ref_m > 0 else 0.05
                        b_m = 2.0 if atr_pct < 0.04 else (1.8 if atr_pct < 0.08 else 1.5)
                        if ind["score"] >= 45:
                            b_m -= 0.1
                        elif ind["score"] < 35:
                            b_m += 0.1
                        atr_mult = max(1.2, min(b_m, 2.4))
                        rr_b = 2.3 if atr_pct < 0.04 else (2.0 if atr_pct < 0.08 else 1.7)
                        if ind["score"] >= 46:
                            rr_b += 0.2
                        elif ind["score"] < 34:
                            rr_b -= 0.2
                        rr = max(1.2, min(rr_b, 2.8))
                        sd = max(atr_v * atr_mult, ref_m * 0.0002, 5 * 5e-7)
                        pending_sig = {
                            "anchor": ref_m,
                            "stop_dist": sd,
                            "rr": rr,
                            "born_exec": len(exec_c),
                        }
            ks += 1

        while ke < ne and int(e_end[ke]) <= i:
            warmup_ok = len(sig_c) >= 20
            exec_c.append(float(e_c[ke]))
            last_exec_mid = 0.5 * (float(e_h[ke]) + float(e_l[ke]))
            chk_px = float(e_c[ke]) if causal_m1 else last_exec_mid

            if active_pos is not None:
                if not causal_m1:
                    if last_exec_mid <= active_pos["stop_px"]:
                        _close_pos(active_pos["stop_px"], ts_i, "stop_hit")
                        ke += 1
                        continue
                    if last_exec_mid >= active_pos["target_px"]:
                        _close_pos(active_pos["target_px"], ts_i, "soft_target_hit")
                        ke += 1
                        continue
                bars_held = len(exec_c) - active_pos["born_exec"]
                if bars_held >= 30:
                    if causal_m1:
                        pending_mkt_exit = "time_stop"
                    else:
                        _close_pos(last_exec_mid, ts_i, "time_stop")
                elif sig_invalidated:
                    if causal_m1:
                        pending_mkt_exit = "signal_invalidation"
                    else:
                        _close_pos(last_exec_mid, ts_i, "signal_invalidation")
            elif pending_sig is not None and pending_mkt_open is None:
                if (len(exec_c) - pending_sig["born_exec"]) > 15:
                    pending_sig = None
                elif warmup_ok:
                    ex_ema = _ema(exec_c[-30:], 9)
                    if chk_px <= ex_ema * 1.0015 and chk_px <= pending_sig["anchor"] * 1.0025:
                        ps = pending_sig
                        pending_sig = None
                        if causal_m1:
                            pending_mkt_open = {"stop_dist": ps["stop_dist"], "rr": ps["rr"], "born_exec": len(exec_c)}
                        else:
                            sd = ps["stop_dist"]
                            active_pos = {
                                "entry_px": last_exec_mid,
                                "stop_px": last_exec_mid - sd,
                                "target_px": last_exec_mid + sd * ps["rr"],
                                "stop_dist": sd,
                                "born_exec": len(exec_c),
                                "en_ns": ts_i,
                                "ses": ses_i,
                            }
            ke += 1

    return pd.DataFrame(trades)


def simulate_mbtc_regulatory_bot(
    m1: pd.DataFrame,
    causal_m1: bool = True,
    neutral_catalyst: bool = False,
) -> pd.DataFrame:
    """Exact repaired replica of `MicroBitcoinRegulatoryMomentumBot` (60m signal -> 5m execution)."""
    sig_df = _resample_m1_to_tf(m1, 60)
    exe_df = _resample_m1_to_tf(m1, 5)

    n1 = len(m1)
    m1_ts = m1["close_ns"].to_numpy(np.int64)
    m1_o, m1_h, m1_l, m1_c = m1["o"].to_numpy(), m1["h"].to_numpy(), m1["l"].to_numpy(), m1["c"].to_numpy()
    m1_ses = m1["sesion"].to_numpy(np.int64)

    s_end = sig_df["m1_end_idx"].to_numpy(np.int64)
    s_ts = sig_df["close_ns"].to_numpy(np.int64)
    s_h, s_l, s_c, s_v = sig_df["h"].to_numpy(), sig_df["l"].to_numpy(), sig_df["c"].to_numpy(), sig_df["v"].to_numpy()
    e_end = exe_df["m1_end_idx"].to_numpy(np.int64)
    e_h, e_l, e_c = exe_df["h"].to_numpy(), exe_df["l"].to_numpy(), exe_df["c"].to_numpy()

    sig_bars: deque[dict[str, float]] = deque(maxlen=500)
    exec_bars: deque[dict[str, float]] = deque(maxlen=2000)
    atr_hist: deque[float] = deque(maxlen=200)
    ret_hist: deque[float] = deque(maxlen=300)
    sim_pnls: list[float] = []

    active_pos: dict[str, Any] | None = None
    pending_mkt_open: dict[str, Any] | None = None
    pending_mkt_exit: str | None = None
    trades: list[dict[str, Any]] = []

    def _mean(a: list[float]) -> float:
        return sum(a) / len(a) if a else 0.0

    def _std(a: list[float]) -> float:
        if len(a) <= 1:
            return 0.0
        m = _mean(a)
        return (sum((x - m) ** 2 for x in a) / len(a)) ** 0.5

    def _atr(blist: list[dict[str, float]], p: int = 14) -> float:
        if len(blist) < 2:
            return 0.0
        use = blist[-max(p + 1, 2):]
        trs = []
        pc = use[0]["c"]
        for b in use[1:]:
            trs.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
            pc = b["c"]
        return _mean(trs)

    def _rets(cl: list[float]) -> list[float]:
        return [(cl[j] - cl[j - 1]) / cl[j - 1] for j in range(1, len(cl)) if cl[j - 1] > 0]

    def _ema_last(vals: list[float], p: int) -> float | None:
        if len(vals) < p or p <= 0:
            return None
        k = 2.0 / (p + 1.0)
        e = vals[0]
        for v in vals[1:]:
            e = v * k + e * (1.0 - k)
        return e

    def _rsi_custom(cl: list[float], p: int) -> float:
        if len(cl) < p + 1:
            return 50.0
        g, ls = [], []
        for j in range(len(cl) - p, len(cl)):
            d = cl[j] - cl[j - 1]
            g.append(d if d >= 0 else 0.0)
            ls.append(-d if d < 0 else 0.0)
        al = _mean(ls)
        if al <= 0:
            return 100.0
        return 100.0 - (100.0 / (1.0 + _mean(g) / al))

    def _mom_comp(cl: list[float], bl: list[dict[str, float]], ts_ns_now: int) -> dict[str, Any]:
        fp = max(5, int(len(cl) * 0.15))
        sp = max(10, int(len(cl) * 0.35))
        fma = sum(cl[-fp:]) / fp if len(cl) >= fp else None
        sma = sum(cl[-sp:]) / sp if len(cl) >= sp else None
        rsi = _rsi_custom(cl, max(14, int(len(cl) * 0.2)))
        ef = _ema_last(cl, max(6, int(len(cl) * 0.12)))
        es = _ema_last(cl, max(12, int(len(cl) * 0.24)))
        macd = 0.0 if (ef is None or es is None) else (ef - es)
        lb = max(10, int(len(cl) * 0.3))
        highs = [b["h"] for b in bl[-lb:]]
        don_hi = max(highs[:-1]) if len(highs) > 1 else highs[0]
        vols = [b["v"] for b in bl[-lb:]]
        v_now = vols[-1]
        v_avg = _mean(vols[:-1]) if len(vols) > 1 else v_now
        v_rat = v_now / v_avg if v_avg > 0 else 1.0
        c_now = cl[-1]
        t_str = (fma - sma) / abs(sma) if (fma is not None and sma is not None and sma != 0) else 0.0
        m_ret = (cl[-1] - cl[-4]) / cl[-4] if len(cl) > 3 and cl[-4] > 0 else 0.0

        if neutral_catalyst:
            cat_bias = 0.25
        else:
            dt_now = datetime.fromtimestamp(ts_ns_now / 1e9, tz=timezone.utc)
            vote_dt = datetime(dt_now.year, 9, 15, tzinfo=timezone.utc)
            d_vote = (vote_dt.date() - dt_now.date()).days
            cat_bias = (1.0 / (1.0 + abs(d_vote))) * (1.0 if d_vote >= 0 else 0.5)

        sc = 50.0
        sc += 30.0 * (t_str / (abs(t_str) + 0.005))
        sc += 20.0 * (m_ret / (abs(m_ret) + 0.01))
        sc += (rsi - 50.0) * 0.4
        sc += 15.0 if macd > 0 else -15.0
        if c_now >= don_hi and don_hi > 0:
            sc += 10.0
        sc += 10.0 * ((v_rat - 1.0) / (abs(v_rat - 1.0) + 1.0))
        sc += 10.0 * cat_bias
        sc = max(0.0, min(100.0, sc))
        return {"score": sc, "trend_aligned": bool(fma is not None and sma is not None and fma > sma), "macd": macd, "rsi": rsi, "cat_bias": cat_bias}

    def _dyn_rr() -> float:
        if not sim_pnls:
            wr, sh, pf = 0.5, 0.0, 1.0
        else:
            s30 = sim_pnls[-30:]
            wr = sum(1 for x in s30 if x > 0) / len(s30)
            s50 = sim_pnls[-50:]
            gw = sum(x for x in s50 if x > 0)
            gl = -sum(x for x in s50 if x < 0)
            pf = (gw / gl) if gl > 0 else (gw if gw > 0 else 1.0)
            sd_p = _std(s50)
            sh = (_mean(s50) / sd_p) if (len(s50) >= 5 and sd_p > 0) else 0.0
        return max(2.0, 1.0 + wr + max(0.0, sh) + 0.5 * max(0.0, pf - 1.0))

    def _close_pos_full(px: float, ts_ns: int, rsn: str) -> None:
        nonlocal active_pos
        if active_pos is None:
            return
        ep = active_pos["entry_px"]
        rem_w = active_pos["rem_frac"]
        pnl_pts_w = active_pos["realized_pts_w"] + rem_w * (px - ep)
        sim_pnls.append(pnl_pts_w * 0.1 * active_pos["init_qty"])
        trades.append({
            "fecha_int": int(active_pos["ses"]),
            "en_ns": int(active_pos["en_ns"]),
            "ex_ns": int(ts_ns),
            "side": 1,
            "entry_price": float(ep),
            "exit_price": float(ep + pnl_pts_w),
            "riesgo_pts": float(active_pos["stop_dist"]),
            "pnl_pts": float(pnl_pts_w),
            "qty": int(active_pos["init_qty"]),
            "reason": rsn,
        })
        active_pos = None

    ks, ke = 0, 0
    ns, ne = len(sig_df), len(exe_df)
    total_exec_seen = 0

    for i in range(n1):
        ts_i = int(m1_ts[i])
        op_i, hi_i, lo_i = float(m1_o[i]), float(m1_h[i]), float(m1_l[i])
        ses_i = int(m1_ses[i])

        if causal_m1:
            if pending_mkt_exit is not None and active_pos is not None:
                _close_pos_full(op_i, ts_i - MIN_NS, pending_mkt_exit)
                pending_mkt_exit = None
            elif pending_mkt_open is not None and active_pos is None:
                ps = pending_mkt_open
                pending_mkt_open = None
                sd = ps["stop_dist"]
                active_pos = {
                    "entry_px": op_i,
                    "stop_px": op_i - sd,
                    "trail_px": op_i - sd,
                    "stop_dist": sd,
                    "rr": ps["rr"],
                    "init_qty": ps["qty"],
                    "rem_frac": 1.0,
                    "realized_pts_w": 0.0,
                    "t1": False,
                    "t2": False,
                    "born_exec": total_exec_seen,
                    "en_ns": ts_i - MIN_NS,
                    "ses": ses_i,
                }

            if active_pos is not None:
                prot = max(active_pos["stop_px"], active_pos["trail_px"])
                if lo_i <= prot:
                    _close_pos_full(min(op_i, prot), ts_i, "protective_stop")

        # Closed 60m signal bars
        while ks < ns and int(s_end[ks]) <= i:
            b_s = {"h": float(s_h[ks]), "l": float(s_l[ks]), "c": float(s_c[ks]), "v": float(s_v[ks])}
            sig_bars.append(b_s)
            if len(sig_bars) >= 20:
                bl = list(sig_bars)
                cl = [x["c"] for x in bl]
                atr_eff = max(_atr(bl, 14), 1.0)
                atr_hist.append(atr_eff)
                r40 = _rets(cl[-40:])
                r_std = _std(r40)
                if r40:
                    ret_hist.append(r_std)
                atr_base = _mean(list(atr_hist)[-80:]) if atr_hist else atr_eff
                vix_p = abs(r_std) * 100.0 * (365.0 ** 0.5)
                atr_m = 2.0 if vix_p <= 15.0 else (3.0 if vix_p >= 35.0 else 2.0 + (vix_p - 15.0) / 20.0)
                sd = max(atr_eff * atr_m, 25.0)  # 5 ticks * 5.0 MBT tick_size
                comp = _mom_comp(cl, bl, int(s_ts[ks]))
                th = 50.0 + 10.0 * ((abs(r_std) / (abs(r_std) + 0.01)) - 0.5)

                # Maintenance window check (17 ET Mon-Thu, 16 ET Fri)
                et_h = (datetime.fromtimestamp(int(s_ts[ks]) / 1e9, tz=timezone.utc) - timedelta(hours=5))
                in_maint = (et_h.weekday() in (0, 1, 2, 3) and et_h.hour == 17) or (et_h.weekday() == 4 and et_h.hour == 16)

                if active_pos is None and pending_mkt_open is None and not in_maint and comp["trend_aligned"] and comp["score"] >= th:
                    rr = _dyn_rr()
                    # Position size (1..2 contracts)
                    s_mid = 0.5 * (b_s["h"] + b_s["l"])
                    e_mid = 0.5 * (exec_bars[-1]["h"] + exec_bars[-1]["l"]) if exec_bars else s_mid
                    v_adj = 0.25 if vix_p > 35 else (0.5 if vix_p > 25 else (0.75 if vix_p >= 15 else 1.0))
                    vol_adj = (atr_base / atr_eff) if atr_eff > 0 else 1.0
                    raw_q = (500.0 / max(sd * 0.1, 1e-6)) * v_adj * vol_adj
                    qty = min(2, int(raw_q))
                    notional = e_mid * qty * 0.1
                    max_m = 0.5 - 0.2 * (abs(r_std) / (abs(r_std) + 0.01))
                    if qty >= 1 and (notional / 50000.0) <= max_m:
                        if causal_m1:
                            pending_mkt_open = {"stop_dist": sd, "rr": rr, "qty": qty}
                        else:
                            active_pos = {
                                "entry_px": e_mid,
                                "stop_px": e_mid - sd,
                                "trail_px": e_mid - sd,
                                "stop_dist": sd,
                                "rr": rr,
                                "init_qty": qty,
                                "rem_frac": 1.0,
                                "realized_pts_w": 0.0,
                                "t1": False,
                                "t2": False,
                                "born_exec": total_exec_seen,
                                "en_ns": ts_i,
                                "ses": ses_i,
                            }
            ks += 1

        # Closed 5m execution bars
        while ke < ne and int(e_end[ke]) <= i:
            b_e = {"h": float(e_h[ke]), "l": float(e_l[ke]), "c": float(e_c[ke])}
            exec_bars.append(b_e)
            total_exec_seen += 1
            e_mid = 0.5 * (b_e["h"] + b_e["l"])
            chk_px = b_e["c"] if causal_m1 else e_mid

            if active_pos is not None and len(exec_bars) >= 3:
                ebl = list(exec_bars)
                ecl = [x["c"] for x in ebl]
                atr_e = max(_atr(ebl, 14), 1.0)
                r_std_e = _std(_rets(ecl[-30:]))
                reg_t = 1.0 + (abs(r_std_e) / (abs(r_std_e) + 0.01))
                t_gap = max(atr_e / reg_t, 25.0)
                cand_tr = chk_px - t_gap
                if cand_tr > active_pos["trail_px"]:
                    active_pos["trail_px"] = cand_tr

                if not causal_m1:
                    prot = max(active_pos["stop_px"], active_pos["trail_px"])
                    if e_mid <= prot:
                        _close_pos_full(e_mid, ts_i, "protective_stop")
                        ke += 1
                        continue

                ep = active_pos["entry_px"]
                sd = active_pos["stop_dist"]
                rr = active_pos["rr"]
                t1 = ep + sd * rr * 0.5
                t2 = ep + sd * rr * 0.75
                t3 = ep + sd * rr * 1.0

                if not active_pos["t1"] and chk_px >= t1 and active_pos["init_qty"] >= 2:
                    active_pos["realized_pts_w"] += 0.5 * (chk_px - ep)
                    active_pos["rem_frac"] = 0.5
                    active_pos["t1"] = True
                elif active_pos["t1"] and not active_pos["t2"] and chk_px >= t2:
                    # With init_qty=2, rem=1 (<2), target2 is skipped in original code; check t3
                    if chk_px >= t3:
                        if causal_m1:
                            pending_mkt_exit = "full_target_3R"
                        else:
                            _close_pos_full(e_mid, ts_i, "full_target_3R")
                elif chk_px >= t3:
                    if causal_m1:
                        pending_mkt_exit = "full_target_3R"
                    else:
                        _close_pos_full(e_mid, ts_i, "full_target_3R")
                else:
                    held = total_exec_seen - active_pos["born_exec"]
                    r_std_h = _std(list(ret_hist)[-30:]) if ret_hist else 0.0
                    max_hold = max(5, min(20, int(5 + 15 * (abs(r_std_h) / (abs(r_std_h) + 0.01)))))
                    if held >= max_hold:
                        if causal_m1:
                            pending_mkt_exit = "time_exit"
                        else:
                            _close_pos_full(e_mid, ts_i, "time_exit")
                    elif held >= 1 and len(sig_bars) >= 10:
                        bl_s = list(sig_bars)
                        cl_s = [x["c"] for x in bl_s]
                        cp_s = _mom_comp(cl_s, bl_s, ts_i)
                        if (not cp_s["trend_aligned"]) or (cp_s["macd"] < 0 and cp_s["rsi"] < 50):
                            if causal_m1:
                                pending_mkt_exit = "thesis_invalidated"
                            else:
                                _close_pos_full(e_mid, ts_i, "thesis_invalidated")
            ke += 1

    return pd.DataFrame(trades)


# =============================================================================
# 3. EdgeLab Partition & Friction Evaluation Pipeline
# =============================================================================


def evaluate_bot_chain(
    bot_id: str,
    inst: str,
    modo_exec: str,
    trades_df: pd.DataFrame,
    all_sessions: list[int],
    fric_pts: float,
) -> tuple[list[dict[str, Any]], pd.Series]:
    """Evaluate trade DataFrame across DESC, REP, HOLDOUT, TERMINAL, and ALL_OOS (REP+HOLDOUT+TERMINAL)."""
    ses_by_p = {
        p: [s for s in all_sessions if a5_bloque(s) == p]
        for p in ("DESC", "REP", "HOLDOUT", "TERMINAL")
    }
    ses_by_p["ALL_OOS"] = sorted(ses_by_p["REP"] + ses_by_p["HOLDOUT"] + ses_by_p["TERMINAL"])

    if not trades_df.empty:
        df = trades_df.copy()
        rp = np.maximum(df["riesgo_pts"].to_numpy(np.float64), 1e-12)
        df["R_bruto"] = df["pnl_pts"].to_numpy(np.float64) / rp
        df["fric_R"] = float(fric_pts) / rp
        df["R_neto"] = (df["pnl_pts"].to_numpy(np.float64) - float(fric_pts)) / rp
    else:
        df = pd.DataFrame(columns=["fecha_int", "R_bruto", "fric_R", "R_neto"])

    rows = []
    for p_name in ("DESC", "REP", "HOLDOUT", "TERMINAL", "ALL_OOS"):
        s_list = ses_by_p[p_name]
        n_ses = len(s_list)
        meses = max(n_ses / 21.0, 1e-6)
        sub = df[df["fecha_int"].isin(set(s_list))] if not df.empty else df
        n_ops = len(sub)
        if n_ops == 0 or n_ses == 0:
            rows.append({
                "bot_id": bot_id, "inst": inst, "modo": modo_exec, "particion": p_name,
                "sesiones": n_ses, "n_ops": 0, "ops_mes": 0.0,
                "R_bruto_op": 0.0, "fric_R_med": 0.0, "R_neto_op": 0.0,
                "sum_R_neto": 0.0, "win_pct": 0.0, "pf_neto": 0.0,
                "t_ses": 0.0, "sharpe": 0.0, "max_dd_R": 0.0,
            })
            continue
        rn = sub["R_neto"].to_numpy(np.float64)
        rb = sub["R_bruto"].to_numpy(np.float64)
        fr = sub["fric_R"].to_numpy(np.float64)
        gw = float(np.sum(rn[rn > 0]))
        gl = float(-np.sum(rn[rn < 0]))
        pf = (gw / gl) if gl > 1e-9 else (99.0 if gw > 0 else 0.0)
        daily = pd.Series(rn, index=sub["fecha_int"]).groupby(level=0).sum().reindex(s_list, fill_value=0.0).to_numpy(np.float64)
        sd = float(np.std(daily, ddof=1)) if n_ses > 1 else 0.0
        t_ses = (float(np.mean(daily)) / (sd / math.sqrt(n_ses))) if sd > 1e-12 else 0.0
        sh = (float(np.mean(daily)) / sd) * math.sqrt(252.0) if sd > 1e-12 else 0.0
        eq = np.cumsum(daily)
        dd = float(np.min(eq - np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]))
        rows.append({
            "bot_id": bot_id, "inst": inst, "modo": modo_exec, "particion": p_name,
            "sesiones": n_ses, "n_ops": int(n_ops), "ops_mes": round(n_ops / meses, 2),
            "R_bruto_op": round(float(np.mean(rb)), 4),
            "fric_R_med": round(float(np.mean(fr)), 4),
            "R_neto_op": round(float(np.mean(rn)), 4),
            "sum_R_neto": round(float(np.sum(rn)), 2),
            "win_pct": round(100.0 * float(np.mean(rn > 0)), 1),
            "pf_neto": round(pf, 3),
            "t_ses": round(t_ses, 2),
            "sharpe": round(sh, 2),
            "max_dd_R": round(dd, 2),
        })

    full_daily = (
        pd.Series(df["R_neto"].to_numpy(np.float64), index=df["fecha_int"]).groupby(level=0).sum().reindex(all_sessions, fill_value=0.0)
        if not df.empty else pd.Series(0.0, index=all_sessions)
    )
    return rows, full_daily


def main() -> int:
    t0 = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with costos.estimados_permitidos(PREREG_MOTIVO):
        fric_nq = float(costos.friccion_rt_puntos("NQ", "base"))
        fric_6j = float(costos.friccion_rt_puntos("6J", "base"))
        fric_mbt = float(costos.friccion_rt_puntos("MBT", "base"))

    print(f"[1/4] Canonical RT frictions: NQ={fric_nq:.4f} pts | 6J={fric_6j:.8f} ({fric_6j/5e-7:.2f} ticks) | MBT={fric_mbt:.2f} pts ({fric_mbt/5.0:.2f} ticks)", flush=True)

    print("[2/4] Loading CME NQ (2020..2026-11), 6J (2025-08..2026-11), and MBT (2025-08..2026-11) M1 datasets...", flush=True)
    m1_nq = load_nq_m1_2020_2026()
    m1_6j = load_6j_m1_edgelab()
    m1_mbt = load_mbt_m1_edgelab()

    ses_nq = sorted(int(s) for s in m1_nq["sesion"].unique() if int(s) >= 20200101)
    ses_6j = sorted(int(s) for s in m1_6j["sesion"].unique() if int(s) >= 20250804)
    ses_mbt = sorted(int(s) for s in m1_mbt["sesion"].unique() if int(s) >= 20250804)
    print(f"  Sessions loaded: NQ={len(ses_nq)} ({min(ses_nq)}..{max(ses_nq)}) | 6J={len(ses_6j)} ({min(ses_6j)}..{max(ses_6j)}) | MBT={len(ses_mbt)} ({min(ses_mbt)}..{max(ses_mbt)})", flush=True)

    print("[3/4] Running Vendor Mid-Bar (0 cost) vs EdgeLab Causal M1 (Bruto & Neto) across all 3 bots...", flush=True)
    all_rows: list[dict[str, Any]] = []
    curves_causal_net: dict[str, tuple[list[int], pd.Series]] = {}
    curves_vendor_0f: dict[str, tuple[list[int], pd.Series]] = {}

    # --- Bot 1: bar_nq_long_20260914_095412_gen2 (NQ) ---
    tr_nq_vend = simulate_nq_gen2_bot(m1_nq, 10, 2, "BOTH", causal_m1=False, respect_15pct_halt=False)
    tr_nq_caus = simulate_nq_gen2_bot(m1_nq, 10, 2, "BOTH", causal_m1=True, respect_15pct_halt=False)
    tr_nq_halt = simulate_nq_gen2_bot(m1_nq, 10, 2, "BOTH", causal_m1=True, respect_15pct_halt=True)
    tr_nq_long = simulate_nq_gen2_bot(m1_nq, 10, 2, "LONG", causal_m1=True, respect_15pct_halt=False)
    tr_nq_shrt = simulate_nq_gen2_bot(m1_nq, 10, 2, "SHORT", causal_m1=True, respect_15pct_halt=False)

    r_v, s_v = evaluate_bot_chain("bar_nq_gen2_10m_2m", "NQ", "1_VENDOR_MIDBAR_0FRIC", tr_nq_vend, ses_nq, 0.0)
    r_b, _ = evaluate_bot_chain("bar_nq_gen2_10m_2m", "NQ", "2_EDGELAB_CAUSAL_BRUTO", tr_nq_caus, ses_nq, 0.0)
    r_n, s_n = evaluate_bot_chain("bar_nq_gen2_10m_2m", "NQ", "3_EDGELAB_CAUSAL_NETO", tr_nq_caus, ses_nq, fric_nq)
    r_h, _ = evaluate_bot_chain("bar_nq_gen2_10m_2m_15pctHalt", "NQ", "3_EDGELAB_CAUSAL_NETO", tr_nq_halt, ses_nq, fric_nq)
    r_l, _ = evaluate_bot_chain("bar_nq_gen2_SOLO_LONG", "NQ", "3_EDGELAB_CAUSAL_NETO", tr_nq_long, ses_nq, fric_nq)
    r_s, _ = evaluate_bot_chain("bar_nq_gen2_SOLO_SHORT", "NQ", "3_EDGELAB_CAUSAL_NETO", tr_nq_shrt, ses_nq, fric_nq)
    all_rows.extend(r_v + r_b + r_n + r_h + r_l + r_s)
    curves_vendor_0f["NQ Gen2 (10m->2m)"] = (ses_nq, s_v)
    curves_causal_net["NQ Gen2 (10m->2m)"] = (ses_nq, s_n)

    # --- Bot 2: bar_6j_long_20260914_142933 (6J, both 60m->5m calibrated & 10m->2m original) ---
    tr_6j_60_vend = simulate_6j_long_bot(m1_6j, 60, 5, causal_m1=False)
    tr_6j_60_caus = simulate_6j_long_bot(m1_6j, 60, 5, causal_m1=True)
    tr_6j_10_caus = simulate_6j_long_bot(m1_6j, 10, 2, causal_m1=True)

    r6_v, s6_v = evaluate_bot_chain("bar_6j_long_60m_5m", "6J", "1_VENDOR_MIDBAR_0FRIC", tr_6j_60_vend, ses_6j, 0.0)
    r6_b, _ = evaluate_bot_chain("bar_6j_long_60m_5m", "6J", "2_EDGELAB_CAUSAL_BRUTO", tr_6j_60_caus, ses_6j, 0.0)
    r6_n, s6_n = evaluate_bot_chain("bar_6j_long_60m_5m", "6J", "3_EDGELAB_CAUSAL_NETO", tr_6j_60_caus, ses_6j, fric_6j)
    r6_10, _ = evaluate_bot_chain("bar_6j_long_10m_2m_orig", "6J", "3_EDGELAB_CAUSAL_NETO", tr_6j_10_caus, ses_6j, fric_6j)
    all_rows.extend(r6_v + r6_b + r6_n + r6_10)
    curves_vendor_0f["6J Long (60m->5m)"] = (ses_6j, s6_v)
    curves_causal_net["6J Long (60m->5m)"] = (ses_6j, s6_n)

    # --- Bot 3: bot_mbtc_regulatory_momentum (MBT, 60m->5m) ---
    tr_mb_vend = simulate_mbtc_regulatory_bot(m1_mbt, causal_m1=False, neutral_catalyst=False)
    tr_mb_caus = simulate_mbtc_regulatory_bot(m1_mbt, causal_m1=True, neutral_catalyst=False)
    tr_mb_neut = simulate_mbtc_regulatory_bot(m1_mbt, causal_m1=True, neutral_catalyst=True)

    rm_v, sm_v = evaluate_bot_chain("bot_mbtc_reg_mom_60m_5m", "MBT", "1_VENDOR_MIDBAR_0FRIC", tr_mb_vend, ses_mbt, 0.0)
    rm_b, _ = evaluate_bot_chain("bot_mbtc_reg_mom_60m_5m", "MBT", "2_EDGELAB_CAUSAL_BRUTO", tr_mb_caus, ses_mbt, 0.0)
    rm_n, sm_n = evaluate_bot_chain("bot_mbtc_reg_mom_60m_5m", "MBT", "3_EDGELAB_CAUSAL_NETO", tr_mb_caus, ses_mbt, fric_mbt)
    rm_nt, _ = evaluate_bot_chain("bot_mbtc_sin_sesgo_sep15", "MBT", "3_EDGELAB_CAUSAL_NETO", tr_mb_neut, ses_mbt, fric_mbt)
    all_rows.extend(rm_v + rm_b + rm_n + rm_nt)
    curves_vendor_0f["MBT RegMom (60m->5m)"] = (ses_mbt, sm_v)
    curves_causal_net["MBT RegMom (60m->5m)"] = (ses_mbt, sm_n)

    df_res = pd.DataFrame(all_rows)
    df_res.to_csv(OUT_DIR / "resumen_particiones_hftcode.csv", index=False)

    defects = pd.DataFrame([
        {
            "archivo": "bot_mbtc_regulatory_momentum_portable.py",
            "severidad": "CRITICA (No ejecuta)",
            "defecto": "_handle_signal_bar indentado dentro de `if __name__ == '__main__':` (L901): AttributeError inmediato al cerrar la primera barra de 60m; `_now_utc()` usa `datetime.now()` en vez del timestamp de la barra; lookahead `_mid_price = (H+L)/2`; sesgo de fecha fija `Sep 15 Clarity Act`.",
        },
        {
            "archivo": "bar_nq_long_20260914_095412_gen2_portable.py",
            "severidad": "CRITICA (Error de sintaxis)",
            "defecto": "Bloque `try:` vacio en L108-110 (`IndentationError`); referencias a `setup_bot_logger` y `RedisEventDrivenTradingBot` comentadas (`NameError`); `closed_signal_bars` nunca recibe `append(bar)` en `on_bar_closed`; lookahead `(O+H+L+C)/4` y propio dossier reporta PF=0.004 (-99.6%).",
        },
        {
            "archivo": "bar_6j_long_20260914_142933_portable.py",
            "severidad": "ALTA (Lookahead + Inconsistencia TF)",
            "defecto": "`__init__` declara `10m/2m` mientras `TIMEFRAME_CALIBRATION` declara `60m/5m` con `liquidity_tradeable=False`; llena entradas y evalua stops usando `(H+L)/2` al cierre de vela (ignorando mechas intrabar); freno de DD 15% apaga `session_halted` para siempre sin reset.",
        },
    ])
    defects.to_csv(OUT_DIR / "defectos_codigo_auditoria.csv", index=False)

    print("[4/4] Rendering dark audit chart & RESULTADO.md...", flush=True)
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 5.4), dpi=150)
    fig.patch.set_facecolor(BG_FIG)
    for ax, key, col_net in zip(
        axes,
        ["NQ Gen2 (10m->2m)", "6J Long (60m->5m)", "MBT RegMom (60m->5m)"],
        [ACCENT_CORAL, ACCENT_GOLD, ACCENT_TEAL],
    ):
        ax.set_facecolor(BG_AX)
        ax.grid(True, color=GRID_COL, linestyle="--", linewidth=0.6, alpha=0.7)
        ax.tick_params(colors=FG_TEXT, labelsize=8.5)
        for sp in ax.spines.values():
            sp.set_color(GRID_COL)
        ses_k, sv = curves_vendor_0f[key]
        _, sn = curves_causal_net[key]
        dt_k = pd.to_datetime([str(x) for x in ses_k], format="%Y%m%d")
        ax.plot(dt_k, sv.cumsum().to_numpy(), color=ACCENT_BLUE, linestyle="--", linewidth=1.4, label="Vendor Mid-Bar Lookahead (0 costo)")
        ax.plot(dt_k, sn.cumsum().to_numpy(), color=col_net, linewidth=2.0, label="EdgeLab Causal M1 + Costo Canonico")
        ax.axhline(0.0, color=MUTED_TEXT, linewidth=0.8)
        ax.axvline(pd.Timestamp("2026-10-01"), color=ACCENT_GREEN, linestyle=":", linewidth=1.2, label="Frontera TERMINAL (2026-10-01)")
        ax.set_title(key, color=FG_TEXT, fontsize=10.5, fontweight="bold")
        ax.set_ylabel("R Acumulado", color=FG_TEXT, fontsize=9.5)
        ax.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=7.8, loc="best")

    fig.suptitle("Auditoria EdgeLab de Bots Descargados (HFTCode): Ilusion Mid-Bar Lookahead vs Ejecucion Causal Neta", color=FG_TEXT, fontsize=12, fontweight="bold")
    fig.tight_layout()
    png_p = OUT_DIR / "auditoria_bots_hftcode_curvas.png"
    fig.savefig(png_p, facecolor=BG_FIG)
    plt.close(fig)
    shutil.copy2(png_p, ARTIFACT_DIR / "auditoria_bots_hftcode_curvas.png")

    focus = df_res[df_res["particion"].isin(["DESC", "REP", "HOLDOUT", "TERMINAL", "ALL_OOS"])]
    md = f"""# Auditoria Forense y Evaluacion en Cadena EdgeLab — Bots Descargados (`HFTCode`)

> **Fecha:** 2026-11-24  
> **Archivos auditados desde Descargas (`C:\\NuevosIngresos\\SSRN_Researches\\downloaded_files`):**
> 1. `bot_mbtc_regulatory_momentum_portable.zip` -> `MicroBitcoinRegulatoryMomentumBot` (`MBT` @ CME, `60m -> 5m`, `LONG`)
> 2. `bar_6j_long_20260914_142933_portable.zip` -> `Bar6jLong20260914142933` (`6J` @ CME, `60m -> 5m` y `10m -> 2m`, `LONG`)
> 3. `free-python-futures-trading-strategies-nq-short-selling-micro-bitcoin...zip` -> contiene el mismo `bot_mbtc` + `bar_nq_long_20260914_095412_gen2_portable.zip` (`NQ` @ CME, `10m -> 2m`, `SHORT/LONG`)

---

## 1. Defectos de Codigo y Sesgos de Lookahead Detectados antes del Backtest

{defects.to_markdown(index=False)}

---

## 2. Resultados en Toda la Cadena EdgeLab (`DESC`, `REP`, `HOLDOUT`, `TERMINAL`, `ALL_OOS`)

Comparativa entre el relleno irreal del proveedor (`1_VENDOR_MIDBAR_0FRIC`: entrar y salir al punto medio `(H+L)/2` o `(O+H+L+C)/4` de una vela ya cerrada sin costos) frente a la **ejecucion causal M1 de EdgeLab** (`2_EDGELAB_CAUSAL_BRUTO` y `3_EDGELAB_CAUSAL_NETO` con `costos_canonicos.json`: `NQ = {fric_nq:.3f} pts`, `6J = {fric_6j/5e-7:.2f} ticks`, `MBT = {fric_mbt:.2f} pts`):

{focus.to_markdown(index=False)}
"""
    (OUT_DIR / "RESULTADO.md").write_text(md, encoding="utf-8")

    print("\n=== ALL_OOS & DESC Summary (EdgeLab Causal Neto vs Vendor MidBar) ===")
    sub_p = df_res[df_res["particion"].isin(["DESC", "ALL_OOS", "TERMINAL"])]
    print(sub_p[["bot_id", "modo", "particion", "n_ops", "ops_mes", "R_bruto_op", "fric_R_med", "R_neto_op", "sum_R_neto", "t_ses", "sharpe", "max_dd_R"]].to_string(index=False), flush=True)
    print(f"\nCompleted HFTCode audit in {time.perf_counter() - t0:.1f}s -> {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
