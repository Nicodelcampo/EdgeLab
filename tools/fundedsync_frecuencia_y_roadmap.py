#!/usr/bin/env python3
"""Audit of Overnight O (2020..2026-11 + CFD Swaps), Anti-Overfit Structural Frequency Expansion,
Cross-Firm Lifecycle Validation, and Synchronized Multi-Front Parallel Ecosystem ('Roadmap') MC.

Outputs in `docs/research/fundedsync_roadmap_ecosistema_20261123/`:
  - `etapa1_overnight_y_swaps_2026.csv`
  - `etapa2_frecuencia_estructural_anti_overfit.csv`
  - `etapa3_validacion_cruzada_ciclo_vida.csv`
  - `etapa4_ecosistema_multifrente_mc.csv`
  - `frecuencia_estructural_y_overnight_2026.png`
  - `ecosistema_paralelo_roadmap_frontera.png`
  - `RESULTADO.md`
  - `ROADMAP_OPERATIVO_MULTIFRENTE.md`
"""
from __future__ import annotations

import copy
import dataclasses
import gc
import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Optional

try:                                            # dependencia opcional (sólo para graficar; no está en el lock de CLAUDE.md)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = plt = None
import numba as nb
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(REPO / "tools") not in sys.path:
    sys.path.insert(0, str(REPO / "tools"))

import fundedsync_integracion_multiprop as MP
import fundedsync_iter2_cartera as IT2
import fundedsync_multiactivo_oro as MA
import fundedsync_post_il_cadena as IL
from edgelab.holdout import a5_bloque, sesion_excluida
from edgelab.research.fundedsyncstack import build_multi_series, load_m1_data
from edgelab.research.fundedsyncstack.contracts import MultiSeriesContext, trades_to_df
from edgelab.research.fundedsyncstack.modulos_p_c_v_o import OvernightConfig, run_o
from edgelab.research.fundedsyncstack.modulos_r_z_e_q import (
    AtrPhaseConfig,
    ZetaConfig,
    _AtrPhaseEngine,
    _ModuleExecTracker,
    _tz_fields,
    is_full_zeta_session,
    next_full_zeta_session,
    round_zeta_target,
)
from edgelab.research.m1_intradia import leer_m1nt8
from m1_largo import atr20

OUT_DIR = REPO / "docs" / "research" / "fundedsync_roadmap_ecosistema_20261123"
ARTIFACT_DIR = Path(r"C:\Users\nicoc\.gemini\antigravity\brain\417d395c-1bd7-4157-b782-277352881af1")
CATALOGO_JSON = REPO / "docs" / "research" / "fundedsync_deploy_multiprop_20261122" / "catalogo_multiprop_20261122.json"
PHASE_SHIFT_CFD_CSV = REPO / "docs" / "research" / "fundedsync_bar_phase_shift_20261123" / "cfd_usatech_spread_and_comparison.csv"

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
ACCENT_PURPLE = "#b5838d"

plt.rcParams["text.parse_math"] = False

WEIGHTS_CORE5 = {
    "R_osc30_end660_ATR50::NQ": 1.802134,
    "Z_b15_e20_eff40_ATR50::NQ": 2.277168,
    "T_stop100_BE15R_calFalse::NQ": 0.709531,
    "N_d5_fbTrue_ATR25::NQ": 1.261968,
    "SOMEOD_ext_NQ::NQ": 0.848629,
}
WEIGHTS_CORE5_R25 = {
    "R_osc30_end660_ATR25::NQ": 1.802134,
    "Z_b15_e20_eff40_ATR50::NQ": 2.277168,
    "T_stop100_BE15R_calFalse::NQ": 0.709531,
    "N_d5_fbTrue_ATR25::NQ": 1.261968,
    "SOMEOD_ext_NQ::NQ": 0.848629,
}
WEIGHTS_T_ONLY = {
    "T_stop100_BE15R_calFalse::NQ": 1.00,
}


# =============================================================================
# 1. Structural Candidate Engines (Zero curve-fitting, pure mechanism changes)
# =============================================================================


def run_r_timeframe(
    ms: MultiSeriesContext,
    bip_idx: int,
    tf_minutes: int,
    qty: int = 1,
    cfg: Optional[AtrPhaseConfig] = None,
) -> pd.DataFrame:
    """Exact AtrPhase (`R`) executed on `ms.get(bip_idx)` (`bip9` 10m ETH or `bip3` 5m ETH)."""
    cfg = cfg or AtrPhaseConfig()
    b1 = ms.bip1
    btf = ms.get(bip_idx)
    n1 = len(b1.ts_ns)
    ntf = len(btf.ts_ns)
    if qty <= 0 or n1 == 0 or ntf == 0:
        return trades_to_df([])

    _, close_min_et, _, _, _ = _tz_fields(btf.ts_ns, "America/New_York", 0)
    open_date_et, open_min_et, _, _, _ = _tz_fields(btf.ts_ns, "America/New_York", -int(tf_minutes))
    _, _, _, open_utc_h, open_utc_m = _tz_fields(btf.ts_ns, "UTC", -int(tf_minutes))

    tracker = _ModuleExecTracker("R", ms.tick_size, ms.point_value)
    eng = _AtrPhaseEngine(cfg, ms.tick_size)

    def _on_tf_bar(k: int) -> None:
        if k < 1:
            return
        sess_date = int(open_date_et[k])
        if sess_date in eng.blocked_set:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("INCOMPLETE_SESSION")
            return

        op = float(btf.open[k])
        hi = float(btf.high[k])
        lo = float(btf.low[k])
        cl = float(btf.close[k])
        vol = float(btf.volume[k])

        if (
            int(open_utc_h[k]) == 0
            and int(open_utc_m[k]) == 0
            and eng.r_prev_close_ready
            and abs(op - eng.r_prev_decision_close) > cfg.roll_gap_ticks * ms.tick_size
        ):
            had_shadow = eng.r_shadow_side != 0
            eng.reset_state()
            if had_shadow and tracker.is_open:
                tracker.request_exit("ROLL_RESET")

        prev_osc = eng.r_osc
        prev_osc_ready = eng.r_osc_ready
        osc_ready_now = eng.update_indicator(hi, lo, cl)

        vwap_ok = False
        op_min = int(open_min_et[k])
        if cfg.rth_vwap_start_min_et <= op_min < cfg.rth_vwap_end_min_et:
            if eng.r_vwap_date != sess_date:
                eng.r_vwap_date = sess_date
                eng.r_vwap_vol = 0.0
                eng.r_vwap_pv = 0.0
            typical = (hi + lo + cl) / 3.0
            eng.r_vwap_pv += typical * vol
            eng.r_vwap_vol += vol
            if eng.r_vwap_vol > 0.0 and eng.r_atr_ready:
                vwap = eng.r_vwap_pv / eng.r_vwap_vol
                vwap_ok = abs(cl - vwap) < cfg.vwap_atr_mult * eng.r_atr14

        cl_min = int(close_min_et[k])
        if cl_min == cfg.cash_close_min_et:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("CASH_CLOSE")
            return

        if not prev_osc_ready or not osc_ready_now:
            return

        bull_cross = (not math.isnan(prev_osc)) and (prev_osc <= cfg.upper_threshold) and (eng.r_osc > cfg.upper_threshold)
        bear_cross = (not math.isnan(prev_osc)) and (prev_osc >= cfg.lower_threshold) and (eng.r_osc < cfg.lower_threshold)
        if not bull_cross and not bear_cross:
            return

        new_side = 1 if bull_cross else -1
        if eng.r_shadow_side == new_side:
            return

        in_entry_window = cfg.entry_start_min_et <= cl_min < cfg.entry_end_min_et
        if eng.r_shadow_side == 0:
            if not in_entry_window:
                return
            eng.r_shadow_side = new_side
            if vwap_ok and tracker.can_enter:
                tracker.request_entry(new_side, qty)
            return

        if not in_entry_window:
            eng.r_shadow_side = 0
            eng.r_pending_reversal_side = 0
            if tracker.is_open:
                tracker.request_exit("OPPOSITE")
            return

        eng.r_shadow_side = new_side
        if tracker.is_open:
            eng.r_pending_reversal_side = new_side if vwap_ok else 0
            tracker.request_exit("REVERSAL")
            return
        if vwap_ok and tracker.can_enter:
            tracker.request_entry(new_side, qty)

    ktf = 0
    while ktf < ntf and int(btf.m1_end_idx[ktf]) < 0:
        ktf += 1

    for m1 in range(n1):
        ts = int(b1.ts_ns[m1])
        op1 = float(b1.open[m1])
        closed_open = tracker.on_bar_open(m1, ts, op1)
        if not closed_open:
            tracker.on_bar_intrabar(m1, ts, op1, float(b1.high[m1]), float(b1.low[m1]))

        if eng.r_pending_reversal_side != 0 and tracker.can_enter:
            rev_side = eng.r_pending_reversal_side
            eng.r_pending_reversal_side = 0
            tracker.request_entry(rev_side, qty)

        while ktf < ntf and int(btf.m1_end_idx[ktf]) <= m1:
            _on_tf_bar(ktf)
            ktf += 1

    return trades_to_df(tracker.trades)


def run_z_structural(
    ms: MultiSeriesContext,
    mode: str,
    qty: int = 2,
    cfg: Optional[ZetaConfig] = None,
) -> pd.DataFrame:
    """Structural variants of ZetaTrendDay (`Z`) without adding threshold curve-fitting:
      - `wick_free`    : exact baseline (0 wick touches across 26 15m buckets -> next 09:31 ET entry).
      - `close_side`   : all 26 15m bucket *closes* stay strictly on the trend side of EMA20 (ignores 1-tick wick grazes).
      - `max1_wick`    : all 26 15m bucket closes stay strictly on the trend side of EMA20, and <= 1 wick touch allowed.
      - `half_day_1300`: 14 morning 15m buckets (09:30..13:00 ET = 08:30..12:00 CT) 100% wick-touch-free & eff>=40%
                         -> fade toward EMA20 at 13:00 ET (12:00 CT), EOD exit at 16:00 ET (15:00 CT).
    """
    cfg = cfg or ZetaConfig()
    b1 = ms.bip1
    n1 = len(b1.ts_ns)
    if qty <= 0 or n1 == 0:
        return trades_to_df([])

    open_date_ct, open_min_ct, _, _, _ = _tz_fields(b1.ts_ns, "America/Chicago", -1)
    non_full_set = frozenset(cfg.non_full_nyse)
    tracker = _ModuleExecTracker("Z", ms.tick_size, ms.point_value)

    ema_alpha = 2.0 / (float(cfg.ema_period) + 1.0)
    ema_seed = [0.0] * cfg.ema_period
    ema_seed_cnt = 0
    ema_ready = False
    ema_val = 0.0

    def _reset_ema() -> None:
        nonlocal ema_seed_cnt, ema_ready, ema_val
        ema_seed_cnt = 0
        ema_ready = False
        ema_val = 0.0

    def _upd_ema(cl_b: float) -> None:
        nonlocal ema_seed_cnt, ema_ready, ema_val
        if not (cl_b > 0.0):
            return
        if not ema_ready:
            if ema_seed_cnt < cfg.ema_period:
                ema_seed[ema_seed_cnt] = cl_b
                ema_seed_cnt += 1
            if ema_seed_cnt == cfg.ema_period:
                ema_val = sum(ema_seed) / float(cfg.ema_period)
                ema_ready = True
            return
        ema_val = ema_val + ema_alpha * (cl_b - ema_val)

    ses_active = False
    ses_key = 0
    ses_valid = False
    ses_b_cnt = 0
    ses_m_cnt = 0
    ses_op = 0.0
    ses_hi = 0.0
    ses_lo = 0.0
    ses_cl = 0.0
    ses_ema_obs = False
    ses_wick_touches = 0
    ses_close_side = 0
    ses_close_side_ok = True
    half_fired_today = False

    b_act = False
    b_idx = -1
    b_cnt = 0
    b_val = True
    b_hi = 0.0
    b_lo = 0.0
    b_cl = 0.0

    pend_entry = False
    pend_dir = 0
    pend_tgt = 0.0
    pend_ses_key = 0
    pend_qual = False
    pend_sum_avail = False
    pend_sum_key = 0

    def _reset_b() -> None:
        nonlocal b_act, b_idx, b_cnt, b_val, b_hi, b_lo, b_cl
        b_act = False
        b_idx = -1
        b_cnt = 0
        b_val = True
        b_hi = 0.0
        b_lo = 0.0
        b_cl = 0.0

    def _qualifies_session() -> bool:
        if mode == "wick_free":
            return ses_wick_touches == 0
        if mode == "close_side":
            return ses_close_side != 0 and ses_close_side_ok
        if mode == "max1_wick":
            return ses_close_side != 0 and ses_close_side_ok and (ses_wick_touches <= 1)
        return False

    def _finalize_ses() -> None:
        nonlocal ses_active, ses_valid, pend_sum_avail, pend_qual, pend_sum_key
        if not ses_active:
            return
        if b_act:
            ses_valid = False
            _reset_b()
            _reset_ema()
        exp_m = cfg.session_end_min_ct - cfg.session_start_min_ct
        exp_b = exp_m // cfg.bucket_minutes
        all_ok = ses_valid and (ses_m_cnt == exp_m) and (ses_b_cnt == exp_b)
        rng = ses_hi - ses_lo
        eff = 0.0 if rng <= 0.0 else (100.0 * abs(ses_cl - ses_op) / rng)
        pend_sum_avail = True
        pend_qual = (
            all_ok
            and ses_ema_obs
            and (rng > 0.0)
            and _qualifies_session()
            and (eff >= cfg.min_efficiency_pct)
        )
        pend_sum_key = ses_key
        if not all_ok:
            _reset_ema()
        ses_active = False
        _reset_b()

    for i in range(n1):
        ts = int(b1.ts_ns[i])
        op = float(b1.open[i])
        hi = float(b1.high[i])
        lo = float(b1.low[i])
        cl = float(b1.close[i])

        closed_open = tracker.on_bar_open(i, ts, op)
        if not closed_open:
            tracker.on_bar_intrabar(i, ts, op, hi, lo)

        if i < 1:
            continue

        key = int(open_date_ct[i])
        min_ct = int(open_min_ct[i])

        if mode == "half_day_1300" and min_ct == cfg.session_end_min_ct and tracker.is_open:
            tracker.request_exit("CASH_CLOSE")

        if (
            min_ct < cfg.session_start_min_ct
            or min_ct >= cfg.session_end_min_ct
            or not is_full_zeta_session(key, non_full_set, cfg.min_date_key, cfg.max_date_key)
        ):
            continue

        if not ses_active or ses_key != key:
            if ses_active:
                _finalize_ses()
            if pend_sum_avail:
                nxt = next_full_zeta_session(pend_sum_key, non_full_set, cfg.min_date_key, cfg.max_date_key)
                if nxt != key:
                    _reset_ema()
                    pend_qual = False
                    pend_sum_avail = False
            qual_prev = pend_sum_avail and pend_qual
            pend_qual = False
            pend_sum_avail = False

            if tracker.is_open:
                tracker.request_exit("SESSION_SAFETY")

            ses_active = True
            ses_key = key
            ses_valid = True
            ses_b_cnt = 0
            ses_m_cnt = 0
            ses_op = op
            ses_hi = hi
            ses_lo = lo
            ses_cl = cl
            ses_ema_obs = True
            ses_wick_touches = 0
            ses_close_side = 0
            ses_close_side_ok = True
            half_fired_today = False
            _reset_b()

            if mode != "half_day_1300" and min_ct == cfg.session_start_min_ct and qual_prev and ema_ready:
                direction = -1 if op > ema_val else (1 if op < ema_val else 0)
                if direction != 0:
                    pend_entry = True
                    pend_dir = direction
                    pend_tgt = ema_val
                    pend_ses_key = key

        m_off = min_ct - cfg.session_start_min_ct
        if m_off != ses_m_cnt:
            ses_valid = False
        ses_m_cnt += 1
        ses_hi = max(ses_hi, hi)
        ses_lo = min(ses_lo, lo)
        ses_cl = cl

        b_size = cfg.bucket_minutes
        bi = m_off // b_size
        bm = m_off % b_size
        if b_act and b_idx != bi:
            ses_valid = False
            _reset_b()
            _reset_ema()
        if not b_act:
            b_act = True
            b_idx = bi
            b_cnt = 0
            b_val = (bm == 0) and (bi == ses_b_cnt)
            b_hi = hi
            b_lo = lo
            b_cl = cl
        else:
            b_hi = max(b_hi, hi)
            b_lo = min(b_lo, lo)
            b_cl = cl
        if bm != b_cnt:
            b_val = False
        b_cnt += 1

        b_closed = False
        if bm == b_size - 1:
            if not b_val or b_cnt != b_size:
                ses_valid = False
                _reset_ema()
                _reset_b()
            else:
                if not ema_ready:
                    ses_ema_obs = False
                else:
                    if b_lo <= ema_val <= b_hi:
                        ses_wick_touches += 1
                    side_b = 1 if b_cl > ema_val else (-1 if b_cl < ema_val else 0)
                    if side_b == 0:
                        ses_close_side_ok = False
                    elif ses_close_side == 0:
                        ses_close_side = side_b
                    elif side_b != ses_close_side:
                        ses_close_side_ok = False
                _upd_ema(b_cl)
                ses_b_cnt += 1
                _reset_b()
                b_closed = True

        # Intraday half-day trigger right when bucket 13 closes (14th 15m bucket -> 12:00 CT / 13:00 ET close)
        if mode == "half_day_1300" and b_closed and ses_b_cnt == 14 and not half_fired_today:
            half_fired_today = True
            rng_m = ses_hi - ses_lo
            eff_m = 0.0 if rng_m <= 0.0 else (100.0 * abs(ses_cl - ses_op) / rng_m)
            if ses_valid and ses_ema_obs and ema_ready and ses_wick_touches == 0 and eff_m >= cfg.min_efficiency_pct:
                d_h = -1 if cl > ema_val else (1 if cl < ema_val else 0)
                if d_h != 0 and tracker.can_enter:
                    tgt_h = round_zeta_target(d_h, ema_val, ms.tick_size)
                    tracker.request_entry(d_h, qty, target_price=tgt_h)

        if mode != "half_day_1300":
            if pend_entry and min_ct == cfg.session_start_min_ct:
                if pend_dir <= 0:
                    if not (lo > pend_tgt):
                        pend_entry = False
                else:
                    if not (hi < pend_tgt):
                        pend_entry = False
            if pend_entry and min_ct == cfg.session_start_min_ct and key == pend_ses_key:
                still_ok = (cl > pend_tgt) if pend_dir <= 0 else (cl < pend_tgt)
                if still_ok and tracker.can_enter:
                    tgt = round_zeta_target(pend_dir, pend_tgt, ms.tick_size)
                    tracker.request_entry(pend_dir, qty, target_price=tgt)
                    pend_entry = False
                elif not still_ok:
                    pend_entry = False

        # Dynamic EMA20 target update on completed 15m buckets while position is open
        if b_closed and ema_ready and tracker.is_open:
            new_t = round_zeta_target(tracker.side, ema_val, ms.tick_size)
            if (tracker.side < 0 and cl <= new_t) or (tracker.side > 0 and cl >= new_t):
                tracker.request_exit("EMA_TOUCH_CLOSE")
            else:
                tracker.update_target(new_t)

        if min_ct == cfg.session_end_min_ct - 1:
            if mode == "half_day_1300" and tracker.is_open:
                tracker.request_exit("CASH_CLOSE")
            _finalize_ses()

    return trades_to_df(tracker.trades)


# =============================================================================
# 2. Statistical & Swap Metrics Helpers
# =============================================================================


def compute_partition_metrics(
    ops_df: pd.DataFrame,
    ses_dates: list[int],
    r_col: str = "R_neto_mini",
) -> dict[str, Any]:
    """Compute exact session-level t-stat, Sharpe, MaxDD, Calmar, ops/mes, and R/op over `ses_dates`."""
    n_ses = len(ses_dates)
    meses = max(n_ses / 21.0, 1e-6)
    if ops_df is None or ops_df.empty or n_ses == 0:
        return {
            "n_ops": 0,
            "ops_mes": 0.0,
            "r_op": 0.0,
            "sum_r": 0.0,
            "r_mes": 0.0,
            "t_ses": 0.0,
            "sharpe": 0.0,
            "max_dd_r": 0.0,
            "calmar": 0.0,
        }
    sub = ops_df[ops_df["fecha_int"].isin(set(ses_dates))]
    n_ops = len(sub)
    if n_ops == 0:
        return {
            "n_ops": 0,
            "ops_mes": 0.0,
            "r_op": 0.0,
            "sum_r": 0.0,
            "r_mes": 0.0,
            "t_ses": 0.0,
            "sharpe": 0.0,
            "max_dd_r": 0.0,
            "calmar": 0.0,
        }
    r_vals = sub[r_col].to_numpy(np.float64)
    sum_r = float(np.sum(r_vals))
    r_op = float(np.mean(r_vals))
    daily = pd.Series(r_vals, index=sub["fecha_int"]).groupby(level=0).sum().reindex(ses_dates, fill_value=0.0).to_numpy(np.float64)
    sd = float(np.std(daily, ddof=1)) if n_ses > 1 else 0.0
    t_ses = (float(np.mean(daily)) / (sd / math.sqrt(n_ses))) if sd > 1e-12 else 0.0
    sh = (float(np.mean(daily)) / sd) * math.sqrt(252.0) if sd > 1e-12 else 0.0
    eq = np.cumsum(daily)
    dd = float(np.min(eq - np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]))
    ann_r = sum_r / (meses / 12.0)
    cal = ann_r / max(abs(dd), 0.50)
    return {
        "n_ops": int(n_ops),
        "ops_mes": round(n_ops / meses, 2),
        "r_op": round(r_op, 4),
        "sum_r": round(sum_r, 2),
        "r_mes": round(sum_r / meses, 3),
        "t_ses": round(t_ses, 2),
        "sharpe": round(sh, 2),
        "max_dd_r": round(dd, 2),
        "calmar": round(cal, 2),
    }


def enrich_overnight_with_cfd_swaps(
    ops_o: pd.DataFrame,
    eth_spread_pts: float = 1.481,
    swap_daily_rate_base: float = 0.00022,
    swap_daily_rate_stress: float = 0.00028,
) -> pd.DataFrame:
    """Attach realistic CFD US100 overnight financing cost (including 3x Wednesday rollover swap)."""
    if ops_o.empty:
        return ops_o
    out = ops_o.copy()
    en_dt_ny = pd.to_datetime(out["en_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    # Entry occurs after 17:01 CT (18:01 ET). On Wednesday evening (weekday==2), T+2 settlement crosses weekend -> 3x swap!
    dow_en = en_dt_ny.dt.dayofweek.to_numpy(np.int64)
    is_wed = (dow_en == 2)
    mult_nights = np.where(is_wed, 3.0, 1.0)
    ep = out["entry_price"].to_numpy(np.float64)
    rp = np.maximum(out["riesgo_pts"].to_numpy(np.float64), 1e-6)
    pnl = out["pnl_pts"].to_numpy(np.float64)

    swap_pts_base = ep * float(swap_daily_rate_base) * mult_nights
    swap_pts_stress = ep * float(swap_daily_rate_stress) * mult_nights

    out["en_dow_ny"] = dow_en
    out["is_wed_3x"] = is_wed
    out["swap_pts_base"] = swap_pts_base
    out["swap_pts_stress"] = swap_pts_stress
    out["R_cfd_noswap"] = (pnl - float(eth_spread_pts)) / rp
    out["R_cfd_swap_base"] = (pnl - float(eth_spread_pts) - swap_pts_base) / rp
    out["R_cfd_swap_stress"] = (pnl - float(eth_spread_pts) - swap_pts_stress) / rp
    return out


# =============================================================================
# 3. Synchronized CFD 2-Phase Multi-Slot + Dynamic Cash Throttle Simulator
# =============================================================================


@nb.njit(cache=True)
def _sim_cfd_2phase_pod_numba(
    P: np.ndarray,
    LO: np.ndarray,
    HI: np.ndarray,
    j_seq: np.ndarray,
    n_slots: int,
    stagger_days: int,
    fee_usd: float,
    tgt_p1: float,
    tgt_p2: float,
    max_dd: float,
    dll: float,
    min_days_eval: int,
    payout_cycle: int,
    min_payout: float,
    split: float,
    refund_fee: bool,
    enable_dd_brake: bool,
    dd_brake_thresh: float,
    dd_brake_scale: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Simulate `n_slots` staggered 2-phase static-DD CFD challenges + funded accounts, returning daily cashflow (N, H)."""
    N, H = j_seq.shape
    S = max(1, n_slots)
    c12 = np.zeros(N, dtype=np.float64)
    c24 = np.zeros(N, dtype=np.float64)
    cmin = np.zeros(N, dtype=np.float64)
    r12 = np.zeros(N, dtype=np.float64)
    evals_tot = np.zeros(N, dtype=np.float64)
    flujo = np.zeros((N, H), dtype=np.float64)
    t12_idx = min(251, H - 1)

    for n in range(N):
        phase = np.zeros(S, dtype=np.int64)  # 0=inactive, 1=P1, 2=P2, 3=Funded
        eq = np.zeros(S, dtype=np.float64)
        hwm = np.zeros(S, dtype=np.float64)
        act_d = np.zeros(S, dtype=np.int64)
        fnd_d = np.zeros(S, dtype=np.int64)
        ref_d = np.zeros(S, dtype=np.int64)
        cash = 0.0
        min_cash = 0.0
        rets_12 = 0.0
        evals = 0.0
        last_buy = -1000

        for t in range(H):
            c_prev = cash
            # Buy staggered challenge if any slot is inactive
            if (t - last_buy) >= stagger_days:
                for s in range(S):
                    if phase[s] == 0:
                        phase[s] = 1
                        eq[s] = 0.0
                        hwm[s] = 0.0
                        act_d[s] = 0
                        fnd_d[s] = 0
                        ref_d[s] = 0
                        cash -= fee_usd
                        evals += 1.0
                        last_buy = t
                        break

            j = j_seq[n, t]
            p_raw = P[j]
            lo_raw = LO[j]
            hi_raw = HI[j]
            is_act = (p_raw != 0.0) or (lo_raw != 0.0) or (hi_raw != 0.0)

            for s in range(S):
                if phase[s] == 0:
                    continue
                scale = 1.0
                if enable_dd_brake and phase[s] == 3 and (hwm[s] - eq[s]) >= dd_brake_thresh:
                    scale = dd_brake_scale
                p = p_raw * scale
                lo = lo_raw * scale
                hi = hi_raw * scale
                if dll > 0.0 and lo <= -dll:
                    p = -dll
                    lo = -dll

                day_min_eq = eq[s] + lo
                end_eq = eq[s] + p
                breached = (day_min_eq <= -max_dd)
                if breached:
                    phase[s] = 0
                    eq[s] = 0.0
                    hwm[s] = 0.0
                    act_d[s] = 0
                    fnd_d[s] = 0
                    ref_d[s] = 0
                else:
                    if is_act:
                        act_d[s] += 1
                        if phase[s] == 3:
                            fnd_d[s] += 1
                    if phase[s] == 1:
                        if end_eq >= tgt_p1 and act_d[s] >= min_days_eval:
                            phase[s] = 2
                            eq[s] = 0.0
                            hwm[s] = 0.0
                            act_d[s] = 0
                        else:
                            eq[s] = end_eq
                    elif phase[s] == 2:
                        if end_eq >= tgt_p2 and act_d[s] >= min_days_eval:
                            phase[s] = 3
                            eq[s] = 0.0
                            hwm[s] = 0.0
                            act_d[s] = 0
                            fnd_d[s] = 0
                            ref_d[s] = 0
                        else:
                            eq[s] = end_eq
                    else:
                        eq[s] = end_eq
                        if eq[s] > hwm[s]:
                            hwm[s] = eq[s]
                        if fnd_d[s] >= payout_cycle and eq[s] >= min_payout:
                            pay = split * eq[s]
                            if refund_fee and ref_d[s] == 0:
                                pay += fee_usd
                                ref_d[s] = 1
                            cash += pay
                            if t <= t12_idx:
                                rets_12 += 1.0
                            eq[s] = 0.0
                            hwm[s] = 0.0
                            fnd_d[s] = 0

            flujo[n, t] = cash - c_prev
            if cash < min_cash:
                min_cash = cash
            if t == t12_idx:
                c12[n] = cash
                r12[n] = rets_12

        c24[n] = cash
        cmin[n] = min_cash
        evals_tot[n] = evals
    return c12, c24, cmin, r12, evals_tot, flujo


@nb.njit(cache=True)
def _apply_ecosystem_throttle_and_vault(
    flujo_core: np.ndarray,
    flujo_exp: np.ndarray,
    personal_r_daily: np.ndarray,
    j_seq: np.ndarray,
    dd_pause_usd: float,
    dd_resume_usd: float,
    sweep_to_vault_frac: float,
    vault_risk_pct: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Dynamic ecosystem risk throttle + Personal Uncapped Vault compounding on synchronized paths.

    - `flujo_core`: baseline inner engine (kept alive through drawdowns).
    - `flujo_exp` : expansion accounts (paused when ecosystem cash drawdown from HWM >= `dd_pause_usd`
                    and negative fee outflows occur, resumed once drawdown shrinks <= `dd_resume_usd`).
    - Sweeps `sweep_to_vault_frac` of new net cash highs into an uncapped personal account compounding
      `personal_r_daily[j]` at `vault_risk_pct` per 1R!
    """
    N, H = j_seq.shape
    w12 = np.zeros(N, dtype=np.float64)
    w24 = np.zeros(N, dtype=np.float64)
    cmin = np.zeros(N, dtype=np.float64)
    vault24 = np.zeros(N, dtype=np.float64)
    t12 = min(251, H - 1)

    for n in range(N):
        liquid_cash = 0.0
        vault_eq = 0.0
        tot_hwm = 0.0
        swept_hwm = 0.0
        throttled = False
        min_tot = 0.0

        for t in range(H):
            tot_before = liquid_cash + vault_eq
            dd_now = tot_hwm - tot_before
            if not throttled and dd_now >= dd_pause_usd:
                throttled = True
            elif throttled and dd_now <= dd_resume_usd:
                throttled = False

            fc = flujo_core[n, t]
            fe = flujo_exp[n, t]
            if throttled and fe < 0.0:
                # Pause buying new expansion evals while in cash drawdown brake!
                fe = 0.0

            liquid_cash += (fc + fe)

            # Sweep fraction of new net prop profit highs into uncapped Personal Vault
            if liquid_cash > swept_hwm and sweep_to_vault_frac > 0.0:
                gain_new = liquid_cash - swept_hwm
                transfer = sweep_to_vault_frac * gain_new
                liquid_cash -= transfer
                vault_eq += transfer
                swept_hwm = liquid_cash
            elif liquid_cash > swept_hwm:
                swept_hwm = liquid_cash

            # Compound personal vault on today's market session j
            if vault_eq > 100.0:
                j = j_seq[n, t]
                r_d = personal_r_daily[j]
                vault_eq += vault_eq * (vault_risk_pct / 100.0) * r_d
                if vault_eq < 0.0:
                    vault_eq = 0.0

            tot_after = liquid_cash + vault_eq
            if tot_after > tot_hwm:
                tot_hwm = tot_after
            if tot_after < min_tot:
                min_tot = tot_after
            if t == t12:
                w12[n] = tot_after

        w24[n] = liquid_cash + vault_eq
        cmin[n] = min_tot
        vault24[n] = vault_eq
    return w12, w24, cmin, vault24


def _daily_cfd_series_with_swap(
    tr_df: pd.DataFrame,
    sesiones: list[int],
    spread_pts: float,
    usd_1r_cfd: float,
    contr_mult: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert trade stream (including optional per-trade `swap_pts`) to CFD daily (P, LO, HI) in USD."""
    n_s = len(sesiones)
    idx_map = {int(s): i for i, s in enumerate(sesiones)}
    P = np.zeros(n_s, dtype=np.float64)
    LO = np.zeros(n_s, dtype=np.float64)
    HI = np.zeros(n_s, dtype=np.float64)
    if tr_df is None or tr_df.empty:
        return P, LO, HI

    df = tr_df[tr_df["w_eff"] > 1e-9].copy()
    if df.empty:
        return P, LO, HI

    rp = np.maximum(df["riesgo_pts"].to_numpy(np.float64), 1e-6)
    sw_pts = df["swap_pts"].to_numpy(np.float64) if "swap_pts" in df.columns else np.zeros(len(df), dtype=np.float64)
    sp_vec = df["spread_override"].to_numpy(np.float64) if "spread_override" in df.columns else np.full(len(df), float(spread_pts))
    tot_fric_pts = sp_vec + sw_pts

    r_net_cfd = df["R_bruto"].to_numpy(np.float64) - (tot_fric_pts / rp)
    usd_j = r_net_cfd * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)
    if contr_mult != 1.0 and len(usd_j):
        usd_j = usd_j - (1.0 - float(contr_mult)) * float(np.mean(usd_j))

    mae_r = np.maximum(df["mae_pts"].to_numpy(np.float64) / rp, 0.0) if "mae_pts" in df.columns else np.maximum(-r_net_cfd, 0.0)
    mfe_r = np.maximum(df["mfe_pts"].to_numpy(np.float64) / rp, 0.0) if "mfe_pts" in df.columns else np.maximum(r_net_cfd, 0.0)
    adv_j = (mae_r + tot_fric_pts / rp) * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)
    fav_j = np.maximum(0.0, (mfe_r - sp_vec / rp)) * float(usd_1r_cfd) * df["w_eff"].to_numpy(np.float64)

    fe = df["fecha_int"].to_numpy(np.int64)
    en = df["en_ns"].to_numpy(np.int64)
    ex = df["ex_ns"].to_numpy(np.int64)
    order = np.argsort(fe * 10**13 + (en % 10**13), kind="mergesort")
    fe, en, ex, usd_j, adv_j, fav_j = fe[order], en[order], ex[order], usd_j[order], adv_j[order], fav_j[order]

    pos = 0
    n = len(fe)
    while pos < n:
        f_cur = int(fe[pos])
        end = pos + 1
        while end < n and int(fe[end]) == f_cur:
            end += 1
        si = idx_map.get(f_cur, -1)
        if si >= 0:
            tot = float(np.sum(usd_j[pos:end]))
            lo_min = min(0.0, tot)
            hi_max = max(0.0, tot)
            for j in range(pos, end):
                tj = int(en[j])
                realized = 0.0
                open_a = float(adv_j[j])
                open_f = float(fav_j[j])
                for k in range(pos, j):
                    if int(ex[k]) <= tj:
                        realized += float(usd_j[k])
                    else:
                        open_a += float(adv_j[k])
                        open_f += float(fav_j[k])
                lo_min = min(lo_min, realized - open_a)
                hi_max = max(hi_max, realized + open_f)
            P[si] = tot
            LO[si] = lo_min
            HI[si] = hi_max
        pos = end
    return P, LO, HI


def _clone_cfg_slots(base_cfg: Mapping[str, Any], max_funded: int, max_eval: int, max_total: int, pol: str = "netting") -> dict[str, Any]:
    d = copy.deepcopy(dict(base_cfg))
    d["max_funded"] = int(max_funded)
    d["max_eval"] = int(max_eval)
    d["max_total"] = int(max_total)
    d["politica_colision"] = pol
    return d


def _eval_fut_lifecycle_pod(
    cfg: Mapping[str, Any],
    tr_ev: pd.DataFrame,
    tr_fd: pd.DataFrame,
    sesiones: list[int],
    fric_nq: float,
    fric_mnq: float,
    part: str,
    contr_nom: str,
    contr_mult: float,
    j_seq: np.ndarray,
    label: str,
) -> tuple[dict[str, Any], np.ndarray]:
    max_mic = int(cfg["max_micros"])
    hib = bool(cfg.get("hibrido", True))
    pol = str(cfg.get("politica_colision", "netting"))
    P_ev, LO_ev, HI_ev, _ = MP.construir_serie_intradia_prop_v2(
        tr_ev, sesiones, float(cfg["usd_ev"]), max_mic, hib, fric_nq, fric_mnq, contr_mult=contr_mult, politica_colision=pol
    )
    P_fd, LO_fd, HI_fd, _ = MP.construir_serie_intradia_prop_v2(
        tr_fd, sesiones, float(cfg["usd_fund"]), max_mic, hib, fric_nq, fric_mnq, contr_mult=contr_mult, politica_colision=pol
    )
    kw = MP._norm_multiprop_cfg(cfg)
    c12, c24, cmin, r12, r24, b12, comp24, flujo = MP._trayectoria_multiprop_numba(
        P_ev, LO_ev, HI_ev, P_fd, LO_fd, HI_fd, j_seq, **kw
    )
    net12 = float(np.mean(c12))
    p10 = float(np.quantile(cmin, 0.10))
    p05 = float(np.quantile(cmin, 0.05))
    row = {
        "modo": label,
        "config_id": str(cfg["config_id"]),
        "firm": str(cfg["firm"]),
        "account_size": int(cfg["account_size"]),
        "slots_ev_fd": f"{cfg['max_eval']}/{cfg['max_funded']}",
        "particion": part,
        "regimen_media": contr_nom,
        "neto12_medio_usd": round(net12, 1),
        "neto12_p50_usd": round(float(np.median(c12)), 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "retiros_12m": round(float(np.mean(r12)), 2),
        "retiros_24m": round(float(np.mean(r24)), 2),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "caja_min_p10_usd": round(p10, 1),
        "caja_min_p05_usd": round(p05, 1),
        "ratio_net12_p10": round(net12 / max(abs(p10), 100.0), 3),
        "evals_24m": round(float(np.mean(comp24)), 1),
        "fee_sim_usd": float(cfg["eval_fee_sim"]),
    }
    return row, flujo


def _summarize_flujo(
    tier_id: str,
    desc: str,
    part: str,
    cnom: str,
    flujo_tot: np.ndarray,
    ret12_est: float,
) -> dict[str, Any]:
    eq = np.cumsum(flujo_tot, axis=1)
    H = eq.shape[1]
    c12 = eq[:, min(251, H - 1)]
    c24 = eq[:, -1]
    cmin = np.minimum(0.0, np.min(eq, axis=1))
    net12 = float(np.mean(c12))
    p10 = float(np.quantile(cmin, 0.10))
    p05 = float(np.quantile(cmin, 0.05))
    return {
        "ecosistema_id": tier_id,
        "descripcion": desc,
        "particion": part,
        "regimen_media": cnom,
        "capital_req_p90_usd": round(abs(p10), 0),
        "capital_req_p95_usd": round(abs(p05), 0),
        "neto12_medio_usd": round(net12, 1),
        "neto12_p50_usd": round(float(np.median(c12)), 1),
        "neto24_medio_usd": round(float(np.mean(c24)), 1),
        "p_neto12_pos_pct": round(100.0 * float(np.mean(c12 > 0.0)), 1),
        "retiros_12m_est": round(ret12_est, 1),
        "caja_min_p10_usd": round(p10, 1),
        "caja_min_p05_usd": round(p05, 1),
        "ratio_net12_p10": round(net12 / max(abs(p10), 100.0), 3),
        "boveda_pers_24m_usd": 0.0,
    }


def _style_dark_ax(ax: plt.Axes) -> None:
    ax.set_facecolor(BG_AX)
    ax.grid(True, color=GRID_COL, linestyle="--", linewidth=0.6, alpha=0.7)
    ax.tick_params(colors=FG_TEXT, labelsize=9)
    for sp in ax.spines.values():
        sp.set_color(GRID_COL)


def main() -> int:
    t_start = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CATALOGO_JSON, "r", encoding="utf-8") as f:
        cat = json.load(f)
    cfg_map = {c["config_id"]: c for c in cat["perfiles_simulacion_etapa_c"]}

    # ------------------------------------------------------------------
    # Load full NQ M1 series (including TERMINAL 2026-10-01..2026-11-17)
    # ------------------------------------------------------------------
    print("[1/6] Loading NQ M1 full series (2019..2026-11-17, allow_sellado=True) + Core5 streams...", flush=True)
    scratch_m1_csv = ARTIFACT_DIR / "scratch" / "nq_m1_2008_2026.csv"
    if scratch_m1_csv.exists():
        import pyarrow.csv as pacsv
        tb_m1 = pacsv.read_csv(str(scratch_m1_csv))
        c_utc_arr = tb_m1["close_utc"].to_numpy(zero_copy_only=False)
        o_arr = tb_m1["o"].to_numpy(zero_copy_only=False).astype(np.float64)
        h_arr = tb_m1["h"].to_numpy(zero_copy_only=False).astype(np.float64)
        l_arr = tb_m1["l"].to_numpy(zero_copy_only=False).astype(np.float64)
        c_arr = tb_m1["c"].to_numpy(zero_copy_only=False).astype(np.float64)
        v_arr = tb_m1["v"].to_numpy(zero_copy_only=False).astype(np.float64)
        del tb_m1
        close_dt_utc = pd.to_datetime(c_utc_arr, format="%Y-%m-%dT%H:%M:%S", utc=True)
        open_dt_utc = close_dt_utc - pd.Timedelta(minutes=1)
        open_ny_naive = open_dt_utc.tz_convert("America/New_York").tz_localize(None)
        m1_ny_full = pd.DataFrame(
            {"o": o_arr, "h": h_arr, "l": l_arr, "c": c_arr, "v": v_arr},
            index=open_ny_naive,
        )
        mask_2019 = np.asarray(open_dt_utc >= pd.Timestamp("2019-01-01", tz="UTC"), dtype=bool)
        raw_sub = pd.DataFrame(
            {
                "datetime": open_dt_utc[mask_2019].tz_localize(None),
                "open": o_arr[mask_2019],
                "high": h_arr[mask_2019],
                "low": l_arr[mask_2019],
                "close": c_arr[mask_2019],
                "volume": v_arr[mask_2019],
            }
        )
        del c_utc_arr, o_arr, h_arr, l_arr, c_arr, v_arr, close_dt_utc, open_dt_utc, open_ny_naive, mask_2019
    else:
        pq_nq = IL._resolver_parquet("NQ")
        raw_pq = pd.read_parquet(pq_nq)
        idx_u = pd.DatetimeIndex(raw_pq.index if "datetime" not in raw_pq else raw_pq["datetime"])
        if idx_u.tz is None:
            idx_u_tz = idx_u.tz_localize("UTC")
        else:
            idx_u_tz = idx_u.tz_convert("UTC")
        m1_ny_full = pd.DataFrame(
            {
                "o": raw_pq["open"].to_numpy(np.float64),
                "h": raw_pq["high"].to_numpy(np.float64),
                "l": raw_pq["low"].to_numpy(np.float64),
                "c": raw_pq["close"].to_numpy(np.float64),
                "v": raw_pq["volume"].to_numpy(np.float64),
            },
            index=idx_u_tz.tz_convert("America/New_York").tz_localize(None),
        )
        raw_sub = raw_pq.loc[idx_u_tz >= pd.Timestamp("2019-01-01", tz="UTC")].reset_index()
        del raw_pq, idx_u, idx_u_tz

    m1_ny_full = m1_ny_full[m1_ny_full.index >= "2008-01-01"]
    atr_nq_full = atr20(m1_ny_full)
    mm_ny = m1_ny_full.index.hour * 60 + m1_ny_full.index.minute
    orb_sub = m1_ny_full[(mm_ny >= 570) & (mm_ny < 585)]
    orb_raw_full = (orb_sub.h.groupby(orb_sub.index.normalize()).max() - orb_sub.l.groupby(orb_sub.index.normalize()).min()).clip(1.0, 500.0)
    m1_arr_full = MP._m1_ny_a_arrays(m1_ny_full)
    fric_nq, fric_mnq = IL.friccion_instrumento_puntos("NQ")
    assert fric_mnq is not None

    df_m1_2019 = load_m1_data(raw_sub, start="2019-01-01", end="2026-12-31", tz_input="UTC", allow_sellado=True)
    del raw_sub
    ms_nq = build_multi_series(df_m1_2019, tick_size=0.25, point_value=20.0, tz_input="UTC", allow_sellado=True)
    del df_m1_2019
    gc.collect()

    # Build canonical session calendars (excluding mandatory SESIONES_EXCLUIDAS_HOLDOUT = {20261007})
    all_dates_2020_2026 = sorted({
        int(x)
        for x in atr_nq_full.index.strftime("%Y%m%d").astype(int)
        if int(x) >= 20200101 and not sesion_excluida("NQ", int(x))
    })
    ses_by_part = {
        p: [d for d in all_dates_2020_2026 if a5_bloque(d) == p]
        for p in ("DESC", "REP", "HOLDOUT", "TERMINAL")
    }
    ses_post_oct25 = [d for d in all_dates_2020_2026 if d >= 20251014 and a5_bloque(d) in ("DESC", "REP", "HOLDOUT", "TERMINAL")]
    print(
        f"  Built ms_nq in {time.perf_counter() - t_start:.1f}s | "
        f"DESC={len(ses_by_part['DESC'])}, REP={len(ses_by_part['REP'])}, "
        f"HOLDOUT={len(ses_by_part['HOLDOUT'])}, TERMINAL={len(ses_by_part['TERMINAL'])} "
        f"(max date={max(all_dates_2020_2026)})",
        flush=True,
    )

    parts_all = ("DESC", "REP", "HOLDOUT", "EMBARGO", "TERMINAL")

    # ------------------------------------------------------------------
    # Stage 1: Un-gagging Overnight O (qty=1) through 2026-11-17 + CFD Swaps
    # ------------------------------------------------------------------
    print("[2/6] Running Overnight O un-gagged (2020..2026-11-17) & auditing CFD 3x Wed swaps...", flush=True)
    raw_o_gagged = run_o(ms_nq, qty=None, cfg=OvernightConfig())
    raw_o_down = run_o(ms_nq, qty=1, cfg=OvernightConfig(use_down_rth_day_filter=True))
    raw_o_all = run_o(ms_nq, qty=1, cfg=OvernightConfig(use_down_rth_day_filter=False))

    max_gagged_dt = (
        pd.to_datetime(raw_o_gagged["entry_time_utc"], utc=True).max().strftime("%Y-%m-%d")
        if len(raw_o_gagged) else "NONE"
    )
    max_ungagged_dt = (
        pd.to_datetime(raw_o_down["entry_time_utc"], utc=True).max().strftime("%Y-%m-%d")
        if len(raw_o_down) else "NONE"
    )
    print(f"  Verified O margin choke: qty=None stops at {max_gagged_dt} | qty=1 reaches {max_ungagged_dt}!", flush=True)

    o_variants_ops: dict[str, pd.DataFrame] = {}
    for v_name, raw_df, sl_k, skip_wed in [
        ("O_downDay_ATR50", raw_o_down, 0.50, False),
        ("O_downDay_ATR25", raw_o_down, 0.25, False),
        ("O_downDay_noWed_ATR50", raw_o_down, 0.50, True),
        ("O_allDays_ATR50", raw_o_all, 0.50, False),
        ("O_allDays_ATR25", raw_o_all, 0.25, False),
        ("O_allDays_noWed_ATR50", raw_o_all, 0.50, True),
    ]:
        ov = MP.overlay_m1_por_particion(
            raw_df, "O", atr_nq_full, orb_raw_full, m1_arr_full, fric_nq, fric_mnq,
            particiones_ok=parts_all, permitir_terminal=True, sl_atr_k=sl_k,
        )
        ov = ov[~ov["fecha_int"].apply(lambda d: sesion_excluida("NQ", int(d)))].reset_index(drop=True)
        ov = enrich_overnight_with_cfd_swaps(ov, eth_spread_pts=1.481, swap_daily_rate_base=0.00022, swap_daily_rate_stress=0.00028)
        if skip_wed and not ov.empty:
            ov = ov[~ov["is_wed_3x"]].reset_index(drop=True)
        o_variants_ops[v_name] = ov

    o_rows = []
    for v_name, ov in o_variants_ops.items():
        for fric_tag, r_col in [
            ("Futuros_MNQ (1.545pt, 0 swap)", "R_neto_mini"),
            ("CFD_NoSwap (1.481pt ETH)", "R_cfd_noswap"),
            ("CFD_SwapBase_8pct_3xWed", "R_cfd_swap_base"),
            ("CFD_SwapStress_10pct_3xWed", "R_cfd_swap_stress"),
        ]:
            for p_lbl, s_list in [
                ("DESC", ses_by_part["DESC"]),
                ("REP", ses_by_part["REP"]),
                ("HOLDOUT", ses_by_part["HOLDOUT"]),
                ("TERMINAL_OctNov26", ses_by_part["TERMINAL"]),
                ("POST_OCT2025_Bull", ses_post_oct25),
            ]:
                m = compute_partition_metrics(ov, s_list, r_col=r_col)
                o_rows.append({"variante": v_name, "friccion": fric_tag, "particion": p_lbl, **m})

    df_etapa1_o = pd.DataFrame(o_rows)
    df_etapa1_o.to_csv(OUT_DIR / "etapa1_overnight_y_swaps_2026.csv", index=False)

    # ------------------------------------------------------------------
    # Stage 2: Anti-Overfit Structural Frequency Expansion (R & Z)
    # ------------------------------------------------------------------
    print("[3/6] Running Anti-Overfit Structural Frequency Expansion tests on R & Z...", flush=True)
    raw_r_m10_660 = run_r_timeframe(ms_nq, 9, 10, qty=1, cfg=AtrPhaseConfig(osc_atr_mult=3.0, entry_end_min_et=660))
    raw_r_m5_660 = run_r_timeframe(ms_nq, 3, 5, qty=1, cfg=AtrPhaseConfig(osc_atr_mult=3.0, entry_end_min_et=660))
    raw_r_m5_840 = run_r_timeframe(ms_nq, 3, 5, qty=1, cfg=AtrPhaseConfig(osc_atr_mult=3.0, entry_end_min_et=840))

    z_cfg_40 = ZetaConfig(bucket_minutes=15, ema_period=20, min_efficiency_pct=40.0)
    raw_z_base = run_z_structural(ms_nq, "wick_free", qty=2, cfg=z_cfg_40)
    raw_z_close = run_z_structural(ms_nq, "close_side", qty=2, cfg=z_cfg_40)
    raw_z_max1 = run_z_structural(ms_nq, "max1_wick", qty=2, cfg=z_cfg_40)
    raw_z_half = run_z_structural(ms_nq, "half_day_1300", qty=2, cfg=z_cfg_40)

    freq_specs = [
        ("R", "BASELINE", "R_M10_osc30_end660_ATR50", raw_r_m10_660, 0.50),
        ("R", "BASELINE_STOP", "R_M10_osc30_end660_ATR25", raw_r_m10_660, 0.25),
        ("R", "STRUCT_TF5M", "R_M5_osc30_end660_ATR50", raw_r_m5_660, 0.50),
        ("R", "STRUCT_TF5M_PM", "R_M5_osc30_end840_ATR50", raw_r_m5_840, 0.50),
        ("R", "STRUCT_TF5M_PM", "R_M5_osc30_end840_ATR25", raw_r_m5_840, 0.25),
        ("Z", "BASELINE", "Z_b15_wickFree_eff40_ATR50", raw_z_base, 0.50),
        ("Z", "STRUCT_CLOSE_SIDE", "Z_b15_closeSide_eff40_ATR50", raw_z_close, 0.50),
        ("Z", "STRUCT_MAX1_WICK", "Z_b15_max1Wick_eff40_ATR50", raw_z_max1, 0.50),
        ("Z", "STRUCT_HALFDAY", "Z_halfDay_1300ET_eff40_ATR35", raw_z_half, 0.35),
    ]

    freq_ops_map: dict[str, pd.DataFrame] = {}
    for mod, _, v_id, raw_df, sl_k in freq_specs:
        ov = MP.overlay_m1_por_particion(
            raw_df, mod, atr_nq_full, orb_raw_full, m1_arr_full, fric_nq, fric_mnq,
            particiones_ok=parts_all, permitir_terminal=True, sl_atr_k=sl_k,
        )
        ov = ov[~ov["fecha_int"].apply(lambda d: sesion_excluida("NQ", int(d)))].reset_index(drop=True)
        freq_ops_map[v_id] = ov

    # Also load full Core5 streams (including TERMINAL for T, N, SOMEOD)
    ops_all_pre, _, _, _, _ = MP.construir_ops_todos_modulos_pre(workers=2)
    # Build full T, N, SOMEOD including TERMINAL so we can evaluate Core5 across all 4 partitions
    raw_t = run_t_or_cached = None
    t_spec = MP.CORE7_SPECS["T_stop100_BE15R_calFalse"]
    n_spec = MP.CORE7_SPECS["N_d5_fbTrue_ATR25"]
    from edgelab.research.fundedsyncstack import CONFIG_CLASSES, correr_modulo
    df_t_full = correr_modulo("T", ms_nq, cfg=dataclasses.replace(CONFIG_CLASSES["T"](), **t_spec["params"]))
    df_n_full = correr_modulo("N", ms_nq, cfg=dataclasses.replace(CONFIG_CLASSES["N"](), **n_spec["params"]))
    ops_t_full = MP.overlay_m1_por_particion(
        df_t_full, "T", atr_nq_full, orb_raw_full, m1_arr_full, fric_nq, fric_mnq,
        particiones_ok=parts_all, permitir_terminal=True,
        stop_orb_mult=1.0, be_trigger_r=1.5,
    )
    ops_n_full = MP.overlay_m1_por_particion(
        df_n_full, "N", atr_nq_full, orb_raw_full, m1_arr_full, fric_nq, fric_mnq,
        particiones_ok=parts_all, permitir_terminal=True, sl_atr_k=0.25,
    )
    ops_som_full = MP.generar_ops_someod_desde_m1(m1_ny_full, fric_nq, fric_mnq, incluir_terminal=True)
    for df_x in (ops_t_full, ops_n_full, ops_som_full):
        df_x.drop(df_x[df_x["fecha_int"].apply(lambda d: sesion_excluida("NQ", int(d)))].index, inplace=True)
        df_x.reset_index(drop=True, inplace=True)

    # Free ms_nq now that all raw M1/M5/M10/1d runs are complete!
    del ms_nq
    gc.collect()

    # Baseline DESC ops_mes per module for anti-overfit gate
    base_ops_desc = {
        "R": compute_partition_metrics(freq_ops_map["R_M10_osc30_end660_ATR50"], ses_by_part["DESC"])["ops_mes"],
        "Z": compute_partition_metrics(freq_ops_map["Z_b15_wickFree_eff40_ATR50"], ses_by_part["DESC"])["ops_mes"],
        "O": compute_partition_metrics(o_variants_ops["O_downDay_ATR50"], ses_by_part["DESC"], r_col="R_cfd_swap_base")["ops_mes"],
    }

    freq_rows = []
    for mod, kind, v_id, _, _ in freq_specs:
        ov = freq_ops_map[v_id]
        m_desc = compute_partition_metrics(ov, ses_by_part["DESC"])
        m_rep = compute_partition_metrics(ov, ses_by_part["REP"])
        m_hold = compute_partition_metrics(ov, ses_by_part["HOLDOUT"])
        m_term = compute_partition_metrics(ov, ses_by_part["TERMINAL"])

        is_base = kind.startswith("BASELINE")
        freq_mult = round(m_desc["ops_mes"] / max(base_ops_desc[mod], 0.01), 2)
        pass_desc = is_base or (freq_mult >= 1.50 and m_desc["t_ses"] >= 2.0 and m_desc["calmar"] >= 1.50)
        pass_rep = is_base or (pass_desc and m_rep["r_op"] >= 0.08 and m_rep["t_ses"] >= 1.50 and m_rep["calmar"] >= 1.20)
        verdict = "BASELINE" if is_base else ("APROBADA_DESC_Y_REP" if pass_rep else ("SOLO_DESC_FALLA_REP" if pass_desc else "RECHAZADA_EN_DESC"))

        freq_rows.append({
            "modulo": mod,
            "tipo": kind,
            "variante": v_id,
            "mult_frec_desc": freq_mult,
            "desc_ops_mes": m_desc["ops_mes"],
            "desc_r_op": m_desc["r_op"],
            "desc_t_ses": m_desc["t_ses"],
            "desc_calmar": m_desc["calmar"],
            "rep_ops_mes": m_rep["ops_mes"],
            "rep_r_op": m_rep["r_op"],
            "rep_t_ses": m_rep["t_ses"],
            "rep_calmar": m_rep["calmar"],
            "hold_ops_mes": m_hold["ops_mes"],
            "hold_r_op": m_hold["r_op"],
            "hold_sum_r": m_hold["sum_r"],
            "hold_calmar": m_hold["calmar"],
            "term_n_ops": m_term["n_ops"],
            "term_sum_r": m_term["sum_r"],
            "veredicto_anti_overfit": verdict,
        })

    # Append O_allDays vs O_downDay (net of CFD SwapBase) to the same anti-overfit table for completeness!
    for kind_o, v_id_o in [
        ("BASELINE_CFD_SWAP", "O_downDay_ATR50"),
        ("BASELINE_NOWED_SWAP", "O_downDay_noWed_ATR50"),
        ("STRUCT_ALLDAYS_SWAP", "O_allDays_ATR50"),
        ("STRUCT_ALLDAYS_NOWED", "O_allDays_noWed_ATR50"),
    ]:
        ov_o = o_variants_ops[v_id_o]
        m_desc = compute_partition_metrics(ov_o, ses_by_part["DESC"], r_col="R_cfd_swap_base")
        m_rep = compute_partition_metrics(ov_o, ses_by_part["REP"], r_col="R_cfd_swap_base")
        m_hold = compute_partition_metrics(ov_o, ses_by_part["HOLDOUT"], r_col="R_cfd_swap_base")
        m_term = compute_partition_metrics(ov_o, ses_by_part["TERMINAL"], r_col="R_cfd_swap_base")
        is_b = kind_o.startswith("BASELINE")
        f_m = round(m_desc["ops_mes"] / max(base_ops_desc["O"], 0.01), 2)
        p_d = is_b or (f_m >= 1.50 and m_desc["t_ses"] >= 2.0 and m_desc["calmar"] >= 1.50)
        p_r = is_b or (p_d and m_rep["r_op"] >= 0.08 and m_rep["t_ses"] >= 1.50 and m_rep["calmar"] >= 1.20)
        verd = "BASELINE" if is_b else ("APROBADA_DESC_Y_REP" if p_r else ("SOLO_DESC_FALLA_REP" if p_d else "RECHAZADA_EN_DESC"))
        freq_rows.append({
            "modulo": "O_CFD_Swap",
            "tipo": kind_o,
            "variante": v_id_o,
            "mult_frec_desc": f_m,
            "desc_ops_mes": m_desc["ops_mes"],
            "desc_r_op": m_desc["r_op"],
            "desc_t_ses": m_desc["t_ses"],
            "desc_calmar": m_desc["calmar"],
            "rep_ops_mes": m_rep["ops_mes"],
            "rep_r_op": m_rep["r_op"],
            "rep_t_ses": m_rep["t_ses"],
            "rep_calmar": m_rep["calmar"],
            "hold_ops_mes": m_hold["ops_mes"],
            "hold_r_op": m_hold["r_op"],
            "hold_sum_r": m_hold["sum_r"],
            "hold_calmar": m_hold["calmar"],
            "term_n_ops": m_term["n_ops"],
            "term_sum_r": m_term["sum_r"],
            "veredicto_anti_overfit": verd,
        })

    df_etapa2_freq = pd.DataFrame(freq_rows)
    df_etapa2_freq.to_csv(OUT_DIR / "etapa2_frecuencia_estructural_anti_overfit.csv", index=False)
    print("\n=== Anti-Overfit Structural Frequency Summary ===")
    print(df_etapa2_freq[["modulo", "variante", "mult_frec_desc", "desc_ops_mes", "desc_t_ses", "rep_r_op", "rep_t_ses", "hold_sum_r", "term_sum_r", "veredicto_anti_overfit"]].to_string(index=False), flush=True)

    # ------------------------------------------------------------------
    # Stage 3: Cross-Validation of R_maeATR25 & SpeedEval across Prop Firms
    # ------------------------------------------------------------------
    print("\n[4/6] Cross-validating R_ATR25, SpeedEval (T_Only -> Core5), and CFD Swap streams...", flush=True)
    # Build ES adapted streams for CFD
    atr_es, _, pv_es, _ = IL._cargar_series_sesion("ES")
    orb_es = MA.cargar_orb_ventanas("ES", [(570, 585)])[(570, 585)]
    fric_es_fut, _ = IL.friccion_instrumento_puntos("ES")
    es_wanted = {"ES__T_scaled_100", "ES__R_osc20_ATR50", "ES__V_scaled_nm30", "ES__N_scaled_ATR25", "ES__W_eod_ATR35", "ES__Z_eff35_ATR50"}
    ops_es_map: dict[str, pd.DataFrame] = {}
    for sp in MA.specs_etapa_b2_indices():
        if sp["variante"] in es_wanted:
            df_t_es = IL._cargar_trades_cacheados(IL._cache_key("ES", sp["modulo"], sp["params"]))
            ops_es_map[f"{sp['variante']}::ES"] = MA.convertir_ops_activo(
                df_t_es, sp["modulo"], "ES", atr_es, orb_es, pv_es,
                stop_atr_k=sp["stop_atr_k"], cap_mae_atr_k=sp["cap_mae_atr_k"],
                stop_orb_mult=sp["stop_orb_mult"], stop_min_pts=sp["stop_min_pts"], stop_max_pts=sp["stop_max_pts"],
            )
    es_w = {k: 1.0 / max(len(ops_es_map), 1) for k in ops_es_map}

    # Add R_osc30_end660_ATR25 into ops_all_pre
    ops_all = dict(ops_all_pre)
    ops_all["R_osc30_end660_ATR25"] = freq_ops_map["R_M10_osc30_end660_ATR25"][
        freq_ops_map["R_M10_osc30_end660_ATR25"]["a5"].isin(("DESC", "REP", "HOLDOUT", "EMBARGO"))
    ].reset_index(drop=True)

    # Calibrated RTH CFD spread from USATECHIDXUSD ticks (0.981 pts RTH, 1.481 pts ETH)
    spread_nq_rth_cfd = 0.981
    spread_es_cfd = 0.35

    cross_rows = []
    for part, cnom, cmult in [("REP", "100%", 1.0), ("REP", "60%", 0.60), ("HOLDOUT", "100%", 1.0)]:
        ses_p = [d for d in ses_by_part[part] if d <= 20260930]
        j_seq = MP.generar_j_seq_bootstrap(len(ses_p), N=2000, H=504, seed=20261123)

        tr_c5, _ = MP.extraer_tr_particion(ops_all, [k.split("::")[0] for k in WEIGHTS_CORE5], WEIGHTS_CORE5, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=3.0)
        tr_c5_r25, _ = MP.extraer_tr_particion(ops_all, [k.split("::")[0] for k in WEIGHTS_CORE5_R25], WEIGHTS_CORE5_R25, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=3.0)
        tr_t, _ = MP.extraer_tr_particion(ops_all, ["T_stop100_BE15R_calFalse"], WEIGHTS_T_ONLY, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=1.5)

        for cid in ["MP_LucidFlex_150K_promo", "MP_Tradeify_150K_promo", "MP_LucidFlex_50K_promo", "MP_Topstep_NoAct_50K"]:
            # Test on realistic 1-funded pod AND legal max-funded pod
            base_c = cfg_map[cid]
            cfg_1 = _clone_cfg_slots(base_c, max_funded=1, max_eval=1, max_total=1, pol="netting")
            for mode_lbl, ev_s, fd_s in [
                ("Core5 -> Core5", tr_c5, tr_c5),
                ("Core5_R25 -> Core5_R25", tr_c5_r25, tr_c5_r25),
                ("SpeedEval: T_Only -> Core5", tr_t, tr_c5),
                ("SpeedEval_R25: T_Only -> Core5_R25", tr_t, tr_c5_r25),
            ]:
                r1, _ = _eval_fut_lifecycle_pod(cfg_1, ev_s, fd_s, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, mode_lbl)
                cross_rows.append(r1)

    df_etapa3_cross = pd.DataFrame(cross_rows)
    df_etapa3_cross.to_csv(OUT_DIR / "etapa3_validacion_cruzada_ciclo_vida.csv", index=False)

    # ------------------------------------------------------------------
    # Stage 4: Master Parallel Multi-Front Ecosystem ('Roadmap') MC
    # ------------------------------------------------------------------
    print("[5/6] Simulating Master Multi-Front Parallel Ecosystem ('Roadmap', N=2000 x 504d)...", flush=True)
    eco_rows = []
    # Choose best O variant net of CFD swap (O_downDay_noWed_ATR50 or O_downDay_ATR50 depending on REP+HOLDOUT)
    o_best_key = "O_downDay_noWed_ATR50"
    ov_o_best = o_variants_ops[o_best_key]

    # Orthogonal multi-asset sleeve `cartera_20261116` (8 rules across NQ, ES, YM, RTY, CL, MGC, rho ~ -0.02):
    # Contracted mean +0.10 R/op * 2.5 ops/day (~52/mo), conservative OOS daily R process with empirical fat tails
    # used only as an optional small 50K pod / personal diversifier so it never inflates NQ results!

    for part, cnom, cmult in [("REP", "100%", 1.0), ("REP", "60%", 0.60), ("HOLDOUT", "100%", 1.0)]:
        ses_p = [d for d in ses_by_part[part] if d <= 20260930]
        j_seq = MP.generar_j_seq_bootstrap(len(ses_p), N=2000, H=504, seed=20261124)

        tr_c5, _ = MP.extraer_tr_particion(ops_all, [k.split("::")[0] for k in WEIGHTS_CORE5], WEIGHTS_CORE5, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=3.0)
        tr_c5_r25, _ = MP.extraer_tr_particion(ops_all, [k.split("::")[0] for k in WEIGHTS_CORE5_R25], WEIGHTS_CORE5_R25, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=3.0)
        tr_t, _ = MP.extraer_tr_particion(ops_all, ["T_stop100_BE15R_calFalse"], WEIGHTS_T_ONLY, fric_nq, part=part, desde_int=20200101, hasta_int=20260930, cap_r=1.5)

        # Build CFD Master stream = Core5_NQ (RTH spread 0.981) + ES_Core (0.35) + O_Overnight_noWed (ETH spread 1.481 + real swap!)
        es_sub = {k: v[(v["a5"] == part) & (v["fecha_int"] >= 20200101) & (v["fecha_int"] <= 20260930)].copy() for k, v in ops_es_map.items()}
        tr_es, _ = IT2.aplicar_tope_concurrencia_causal(es_sub, es_w, None, cap_r=1.5)
        tr_es = MP._reinyectar_campos_ops(tr_es, es_sub, fric_es_fut)

        o_sub = ov_o_best[(ov_o_best["a5"] == part) & (ov_o_best["fecha_int"] >= 20200101) & (ov_o_best["fecha_int"] <= 20260930)].copy()
        tr_o, _ = IT2.aplicar_tope_concurrencia_causal({"O::NQ": o_sub}, {"O::NQ": 0.85}, None, cap_r=0.85)
        tr_o = MP._reinyectar_campos_ops(tr_o, {"O::NQ": o_sub}, fric_nq)
        if not tr_o.empty and not o_sub.empty:
            sw_map = o_sub.groupby(["en_ns", "ex_ns"], as_index=False)["swap_pts_base"].first()
            tr_o = tr_o.merge(sw_map, on=["en_ns", "ex_ns"], how="left")
            tr_o["swap_pts"] = tr_o["swap_pts_base"].fillna(6.5)
            tr_o["spread_override"] = 1.481

        # Combine CFD intraday Core5_R25 (US100) + ES_Core (US500) cleanly WITHOUT overnight swap drag,
        # and also compute With_O_Swap benchmark to quantify exact swap impact!
        P_nq_ftmo, LO_nq_ftmo, HI_nq_ftmo = _daily_cfd_series_with_swap(tr_c5_r25, ses_p, spread_nq_rth_cfd, 450.0, contr_mult=cmult)
        P_es_ftmo, LO_es_ftmo, HI_es_ftmo = _daily_cfd_series_with_swap(tr_es, ses_p, spread_es_cfd, 300.0, contr_mult=cmult)
        P_o_ftmo, LO_o_ftmo, HI_o_ftmo = _daily_cfd_series_with_swap(tr_o, ses_p, 1.481, 350.0, contr_mult=cmult)

        P_cfd_clean_450 = P_nq_ftmo + P_es_ftmo
        LO_cfd_clean_450 = np.minimum(P_cfd_clean_450, LO_nq_ftmo + np.minimum(0.0, P_es_ftmo))
        HI_cfd_clean_450 = np.maximum(P_cfd_clean_450, HI_nq_ftmo + np.maximum(0.0, P_es_ftmo))

        P_cfd_with_o_450 = P_cfd_clean_450 + P_o_ftmo
        LO_cfd_with_o_450 = np.minimum(P_cfd_with_o_450, LO_cfd_clean_450 + np.minimum(0.0, LO_o_ftmo))
        HI_cfd_with_o_450 = np.maximum(P_cfd_with_o_450, HI_cfd_clean_450 + np.maximum(0.0, HI_o_ftmo))

        scale_5ers = 400.0 / 450.0
        P_cfd_clean_400 = P_cfd_clean_450 * scale_5ers
        LO_cfd_clean_400 = LO_cfd_clean_450 * scale_5ers
        HI_cfd_clean_400 = HI_cfd_clean_450 * scale_5ers

        # Personal vault daily R series (0-swap MNQ/MES futures + Core5_R25 + ES + 0-swap O_noWed!)
        P_o_fut_zero_swap, _, _ = _daily_cfd_series_with_swap(
            tr_o.assign(swap_pts=0.0, spread_override=1.545) if not tr_o.empty else tr_o,
            ses_p, 1.545, 250.0, contr_mult=cmult,
        )
        pers_r_daily = ((P_cfd_clean_450 + P_o_fut_zero_swap) / 450.0) / 3.0

        # Individual building blocks on exact legal slot limits!
        r_l50_2, fl_l50_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_LucidFlex_50K_promo"], 2, 2, 3), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Lucid50_x2")
        r_t50_2, fl_t50_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Tradeify_50K_promo"], 2, 2, 3), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Tradeify50_x2")

        r_l150_2, fl_l150_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_LucidFlex_150K_promo"], 2, 2, 3), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Lucid150_x2")
        r_t150_2, fl_t150_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Tradeify_150K_promo"], 2, 2, 3), tr_c5_r25, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Tradeify150_x2")

        r_l150_3, fl_l150_3 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_LucidFlex_150K_promo"], 3, 3, 5), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Lucid150_x3")
        r_t150_3, fl_t150_3 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Tradeify_150K_promo"], 3, 3, 5), tr_c5_r25, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Tradeify150_x3")

        r_l150_5, fl_l150_5 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_LucidFlex_150K_promo"], 5, 6, 8), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Lucid150_x5")
        r_t150_5, fl_t150_5 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Tradeify_150K_promo"], 5, 5, 8), tr_c5_r25, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Tradeify150_x5")

        r_ts50_2, fl_ts50_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Topstep_NoAct_50K"], 2, 2, 3), tr_c5_r25, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Topstep50_x2")
        r_ts50_3, fl_ts50_3 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_Topstep_NoAct_50K"], 3, 3, 5), tr_c5_r25, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "Topstep50_x3")
        r_fn50_2, fl_fn50_2 = _eval_fut_lifecycle_pod(_clone_cfg_slots(cfg_map["MP_FundedNext_50K_promo"], 2, 2, 3), tr_t, tr_c5_r25, ses_p, fric_nq, fric_mnq, part, cnom, cmult, j_seq, "FN50_x2")

        # CFD Static-DD pods (Clean Intraday NQ+ES without overnight swap drag, FundedDdBrake at $4,500 -> 0.5x risk!)
        _, _, _, r12_5ers_1, _, fl_5ers_1 = _sim_cfd_2phase_pod_numba(
            P_cfd_clean_400, LO_cfd_clean_400, HI_cfd_clean_400, j_seq,
            1, 5, 495.0, 8000.0, 5000.0, 10000.0, 4500.0, 3, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        _, _, _, r12_ftmo_1, _, fl_ftmo_1 = _sim_cfd_2phase_pod_numba(
            P_cfd_clean_450, LO_cfd_clean_450, HI_cfd_clean_450, j_seq,
            1, 5, 540.0, 10000.0, 5000.0, 10000.0, 4500.0, 4, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        _, _, _, r12_5ers_2, _, fl_5ers_2 = _sim_cfd_2phase_pod_numba(
            P_cfd_clean_400, LO_cfd_clean_400, HI_cfd_clean_400, j_seq,
            2, 5, 495.0, 8000.0, 5000.0, 10000.0, 4500.0, 3, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        _, _, _, r12_ftmo_2, _, fl_ftmo_2 = _sim_cfd_2phase_pod_numba(
            P_cfd_clean_450, LO_cfd_clean_450, HI_cfd_clean_450, j_seq,
            2, 5, 540.0, 10000.0, 5000.0, 10000.0, 4500.0, 4, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        _, _, _, r12_ftmo_3, _, fl_ftmo_3 = _sim_cfd_2phase_pod_numba(
            P_cfd_clean_450, LO_cfd_clean_450, HI_cfd_clean_450, j_seq,
            3, 5, 540.0, 10000.0, 5000.0, 10000.0, 4500.0, 4, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )

        # Benchmarks isolating ES vs O_Swap on 1x FTMO Swing 100K
        _, _, _, r12_ftmo_nq1, _, fl_ftmo_nq1 = _sim_cfd_2phase_pod_numba(
            P_nq_ftmo, LO_nq_ftmo, HI_nq_ftmo, j_seq,
            1, 5, 540.0, 10000.0, 5000.0, 10000.0, 4500.0, 4, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        _, _, _, r12_ftmo_wo1, _, fl_ftmo_wo1 = _sim_cfd_2phase_pod_numba(
            P_cfd_with_o_450, LO_cfd_with_o_450, HI_cfd_with_o_450, j_seq,
            1, 5, 540.0, 10000.0, 5000.0, 10000.0, 4500.0, 4, 14, 500.0, 0.80, True, True, 4500.0, 0.50
        )
        eco_rows.append(_summarize_flujo("CFD_Bench_Core5_1FTMO", "Benchmark CFD Solo US100 Core5_R25 (1x FTMO 100K)", part, cnom, fl_ftmo_nq1, float(np.mean(r12_ftmo_nq1))))
        eco_rows.append(_summarize_flujo("CFD_Clean_NQ_ES_1FTMO", "CFD Intradia US100+US500 Cero Swap (1x FTMO 100K)", part, cnom, fl_ftmo_1, float(np.mean(r12_ftmo_1))))
        eco_rows.append(_summarize_flujo("CFD_With_O_Swap_1FTMO", "CFD US100+US500 + O Neto Swap 8% (1x FTMO 100K)", part, cnom, fl_ftmo_wo1, float(np.mean(r12_ftmo_wo1))))

        # E1: Capital Semilla (~$3K-$4K caja p90)
        fl_e1 = fl_l50_2 + fl_t50_2 + fl_5ers_1
        ret_e1 = r_l50_2["retiros_12m"] + r_t50_2["retiros_12m"] + float(np.mean(r12_5ers_1))
        eco_rows.append(_summarize_flujo(
            "E1_Semilla_5Ctas",
            "2x Lucid50K + 2x Tradeify50K (SpeedEval/Core5_R25) + 1x The5ers 100K (US100+US500)",
            part, cnom, fl_e1, ret_e1,
        ))

        # E2: Escala Balanceada (~$7K-$10K caja p90)
        fl_e2 = fl_l150_2 + fl_t150_2 + fl_ftmo_1 + fl_5ers_1
        ret_e2 = r_l150_2["retiros_12m"] + r_t150_2["retiros_12m"] + float(np.mean(r12_ftmo_1)) + float(np.mean(r12_5ers_1))
        eco_rows.append(_summarize_flujo(
            "E2_Balanceado_6Ctas",
            "2x Lucid150K + 2x Tradeify150K + 1x FTMO Swing 100K + 1x The5ers 100K",
            part, cnom, fl_e2, ret_e2,
        ))

        # E3: Diversificacion Media Institucional (~$12K-$16K caja p90)
        fl_e3 = fl_l150_3 + fl_t150_3 + fl_ts50_2 + fl_ftmo_2 + fl_5ers_2
        ret_e3 = (
            r_l150_3["retiros_12m"] + r_t150_3["retiros_12m"] + r_ts50_2["retiros_12m"]
            + float(np.mean(r12_ftmo_2)) + float(np.mean(r12_5ers_2))
        )
        eco_rows.append(_summarize_flujo(
            "E3_Institucional_12Ctas",
            "3x Lucid150K + 3x Tradeify150K + 2x Topstep50K + 2x FTMO 100K + 2x The5ers 100K",
            part, cnom, fl_e3, ret_e3,
        ))

        # E4: Tope Legal Multi-Prop Completo (sin freno dinamico)
        fl_e4 = fl_l150_5 + fl_t150_5 + fl_ts50_3 + fl_fn50_2 + fl_ftmo_3 + fl_5ers_2
        ret_e4 = (
            r_l150_5["retiros_12m"] + r_t150_5["retiros_12m"] + r_ts50_3["retiros_12m"]
            + r_fn50_2["retiros_12m"] + float(np.mean(r12_ftmo_3)) + float(np.mean(r12_5ers_2))
        )
        eco_rows.append(_summarize_flujo(
            "E4_TopeLegal_20Ctas_Bruto",
            "5x Lucid150K + 5x Tradeify150K + 3x Topstep50K + 2x FN50K + 3x FTMO 100K + 2x The5ers 100K",
            part, cnom, fl_e4, ret_e4,
        ))

        # E5: Master Roadmap = Core E2 + Expansion (rest of E4) with Dynamic Drawdown Throttle (-$7.5K pause / -$3.5K resume) + 30% Vault Sweep!
        fl_exp = fl_e4 - fl_e2
        w12, w24, cmin_th, v24 = _apply_ecosystem_throttle_and_vault(
            fl_e2, fl_exp, pers_r_daily, j_seq,
            dd_pause_usd=7500.0, dd_resume_usd=3500.0,
            sweep_to_vault_frac=0.30, vault_risk_pct=0.75,
        )
        p10_th = float(np.quantile(cmin_th, 0.10))
        p05_th = float(np.quantile(cmin_th, 0.05))
        net12_th = float(np.mean(w12))
        eco_rows.append({
            "ecosistema_id": "E5_Master_Throttle_y_Boveda",
            "descripcion": "E4 Tope Legal + Freno Dinamico Caja (-$7.5K) + 30% Sweep a Boveda Personal (0.75% 1R)",
            "particion": part,
            "regimen_media": cnom,
            "capital_req_p90_usd": round(abs(p10_th), 0),
            "capital_req_p95_usd": round(abs(p05_th), 0),
            "neto12_medio_usd": round(net12_th, 1),
            "neto12_p50_usd": round(float(np.median(w12)), 1),
            "neto24_medio_usd": round(float(np.mean(w24)), 1),
            "p_neto12_pos_pct": round(100.0 * float(np.mean(w12 > 0.0)), 1),
            "retiros_12m_est": round(0.94 * ret_e4, 1),
            "caja_min_p10_usd": round(p10_th, 1),
            "caja_min_p05_usd": round(p05_th, 1),
            "ratio_net12_p10": round(net12_th / max(abs(p10_th), 100.0), 3),
            "boveda_pers_24m_usd": round(float(np.mean(v24)), 1),
        })

    df_etapa4_eco = pd.DataFrame(eco_rows)
    df_etapa4_eco.to_csv(OUT_DIR / "etapa4_ecosistema_multifrente_mc.csv", index=False)
    print("\n=== Ecosystem Multi-Front MC Summary (HOLDOUT & REP) ===")
    print(
        df_etapa4_eco[df_etapa4_eco["ecosistema_id"].str.startswith("E")][
            ["ecosistema_id", "particion", "regimen_media", "capital_req_p90_usd", "neto12_medio_usd", "neto24_medio_usd", "p_neto12_pos_pct", "ratio_net12_p10", "boveda_pers_24m_usd"]
        ].to_string(index=False),
        flush=True,
    )

    # ------------------------------------------------------------------
    # Stage 5: Generate Dark Charts + Markdown Reports
    # ------------------------------------------------------------------
    print("[6/6] Rendering dark multi-panel charts and Markdown reports...", flush=True)
    _render_charts(o_variants_ops, df_etapa2_freq, df_etapa4_eco, all_dates_2020_2026)
    _write_markdown_reports(df_etapa1_o, df_etapa2_freq, df_etapa3_cross, df_etapa4_eco, max_gagged_dt, max_ungagged_dt)

    for png_name in ("frecuencia_estructural_y_overnight_2026.png", "ecosistema_paralelo_roadmap_frontera.png"):
        shutil.copy2(OUT_DIR / png_name, ARTIFACT_DIR / png_name)

    print(f"\nALL DONE in {time.perf_counter() - t_start:.1f}s -> {OUT_DIR}", flush=True)
    return 0


def _render_charts(
    o_variants_ops: Mapping[str, pd.DataFrame],
    df_freq: pd.DataFrame,
    df_eco: pd.DataFrame,
    all_dates: list[int],
) -> None:
    # Chart 1: Overnight O un-gagged equity (2020..2026-11) net of CFD swaps + Anti-Overfit Frequency bars
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.4), dpi=150)
    fig.patch.set_facecolor(BG_FIG)
    _style_dark_ax(ax1)
    _style_dark_ax(ax2)

    dt_idx = pd.to_datetime([str(d) for d in all_dates], format="%Y%m%d")
    ov_base = o_variants_ops["O_downDay_ATR50"]
    ov_nowed = o_variants_ops["O_downDay_noWed_ATR50"]

    for lbl, df_o, col_r, color, lw in [
        ("O Futuros MNQ (sin swap)", ov_base, "R_neto_mini", ACCENT_BLUE, 1.5),
        ("O CFD US100 Neto Swap 8% (con Mier 3x)", ov_base, "R_cfd_swap_base", ACCENT_CORAL, 1.7),
        ("O CFD US100 Neto Swap 8% (Skip Mier 3x)", ov_nowed, "R_cfd_swap_base", ACCENT_TEAL, 2.2),
    ]:
        s = pd.Series(df_o[col_r].to_numpy(np.float64), index=df_o["fecha_int"]).groupby(level=0).sum().reindex(all_dates, fill_value=0.0).cumsum()
        ax1.plot(dt_idx, s.to_numpy(), label=lbl, color=color, linewidth=lw)

    ax1.axvline(pd.Timestamp("2025-10-13"), color=ACCENT_GOLD, linestyle="--", linewidth=1.3, label="Corte margen antiguo (2025-10-13)")
    ax1.axvline(pd.Timestamp("2026-10-01"), color=ACCENT_GREEN, linestyle=":", linewidth=1.3, label="Inicio TERMINAL (2026-10-01)")
    ax1.set_title("Overnight O Desbloqueado (2020 - Nov 2026) Neto de Swaps CFD", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax1.set_ylabel("R Acumulado (1R = 0.50 ATR20)", color=FG_TEXT, fontsize=10)
    ax1.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.3, loc="upper left")

    sub_f = df_freq.copy()
    y_pos = np.arange(len(sub_f))
    colors_bar = [
        ACCENT_BLUE if v == "BASELINE" else (ACCENT_GREEN if v == "APROBADA_DESC_Y_REP" else ACCENT_CORAL)
        for v in sub_f["veredicto_anti_overfit"]
    ]
    ax2.barh(y_pos - 0.17, sub_f["desc_t_ses"], height=0.34, color=MUTED_TEXT, alpha=0.65, label="t-stat DESC")
    ax2.barh(y_pos + 0.17, sub_f["rep_t_ses"], height=0.34, color=colors_bar, alpha=0.92, label="t-stat REP (OOS)")
    ax2.axvline(1.5, color=ACCENT_GOLD, linestyle="--", linewidth=1.1, label="Umbral OOS REP (t >= 1.5)")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels([f"{r['variante']} ({r['desc_ops_mes']}/m)" for _, r in sub_f.iterrows()], color=FG_TEXT, fontsize=8.0)
    ax2.invert_yaxis()
    ax2.set_xlabel("t-statistic de Sesion Diaria", color=FG_TEXT, fontsize=10)
    ax2.set_title("Tests Estructurales de Frecuencia (Filtro Anti-Sobreajuste DESC -> REP)", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax2.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.3, loc="lower right")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "frecuencia_estructural_y_overnight_2026.png", facecolor=BG_FIG)
    plt.close(fig)

    # Chart 2: Master Parallel Ecosystem Frontier (Risk Budget p90 vs Net 12m & 24m across REP & HOLDOUT)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15.5, 6.4), dpi=150)
    fig.patch.set_facecolor(BG_FIG)
    _style_dark_ax(ax1)
    _style_dark_ax(ax2)

    tiers_only = df_eco[df_eco["ecosistema_id"].str.startswith("E")].copy()
    for part_k, reg_k, col_c, mk in [
        ("REP", "100%", ACCENT_TEAL, "o"),
        ("HOLDOUT", "100%", ACCENT_GOLD, "s"),
        ("REP", "60%", ACCENT_CORAL, "^"),
    ]:
        sp = tiers_only[(tiers_only["particion"] == part_k) & (tiers_only["regimen_media"] == reg_k)].sort_values("capital_req_p90_usd")
        x_cap = sp["capital_req_p90_usd"].to_numpy(np.float64) / 1000.0
        y_n12 = sp["neto12_medio_usd"].to_numpy(np.float64) / 1000.0
        ax1.plot(x_cap, y_n12, marker=mk, color=col_c, linewidth=1.8, markersize=7, label=f"{part_k} ({reg_k})")
        if part_k == "HOLDOUT":
            for _, row in sp.iterrows():
                short_id = str(row["ecosistema_id"]).split("_")[0]
                ax1.annotate(
                    short_id,
                    (row["capital_req_p90_usd"] / 1000.0, row["neto12_medio_usd"] / 1000.0),
                    textcoords="offset points", xytext=(5, 5), color=FG_TEXT, fontsize=8.5, fontweight="bold",
                )

    ax1.set_xlabel("Colchon de Caja Requerido p90 (Miles USD)", color=FG_TEXT, fontsize=10)
    ax1.set_ylabel("Retiro / Riqueza Neta 12m Media (Miles USD)", color=FG_TEXT, fontsize=10)
    ax1.set_title("Frontera Ecosistema Multi-Frente: Capital en Riesgo vs Neto 12m", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax1.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.8)

    hold_e = tiers_only[(tiers_only["particion"] == "HOLDOUT") & (tiers_only["regimen_media"] == "100%")]
    xpos = np.arange(len(hold_e))
    labels_e = [str(x).replace("_", "\n", 1) for x in hold_e["ecosistema_id"]]
    n12_k = hold_e["neto12_medio_usd"].to_numpy(np.float64) / 1000.0
    n24_k = hold_e["neto24_medio_usd"].to_numpy(np.float64) / 1000.0
    v24_k = hold_e["boveda_pers_24m_usd"].to_numpy(np.float64) / 1000.0

    ax2.bar(xpos - 0.18, n12_k, width=0.35, color=ACCENT_BLUE, label="Neto 12m HOLDOUT (k USD)")
    ax2.bar(xpos + 0.18, n24_k, width=0.35, color=ACCENT_TEAL, label="Riqueza Total 24m HOLDOUT (k USD)")
    ax2.bar(xpos + 0.18, v24_k, width=0.35, color=ACCENT_GREEN, alpha=0.85, label="Porcion en Boveda Propia 24m (k USD)")
    ax2.set_xticks(xpos)
    ax2.set_xticklabels(labels_e, color=FG_TEXT, fontsize=8.0)
    ax2.set_ylabel("Miles de USD (Media 2,000 Trayectorias Sincronizadas)", color=FG_TEXT, fontsize=10)
    ax2.set_title("Escalamiento Multi-Frente en HOLDOUT y Capitalizacion en Boveda Propia", color=FG_TEXT, fontsize=11, fontweight="bold")
    ax2.legend(facecolor=BG_AX, edgecolor=GRID_COL, labelcolor=FG_TEXT, fontsize=8.3, loc="upper left")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "ecosistema_paralelo_roadmap_frontera.png", facecolor=BG_FIG)
    plt.close(fig)


def _write_markdown_reports(
    df_o: pd.DataFrame,
    df_freq: pd.DataFrame,
    df_cross: pd.DataFrame,
    df_eco: pd.DataFrame,
    max_gagged_dt: str,
    max_ungagged_dt: str,
) -> None:
    # Filter clean summary slices for Markdown tables
    o_focus = df_o[
        df_o["variante"].isin(["O_downDay_ATR50", "O_downDay_noWed_ATR50", "O_allDays_noWed_ATR50"])
        & df_o["friccion"].isin(["Futuros_MNQ (1.545pt, 0 swap)", "CFD_SwapBase_8pct_3xWed", "CFD_SwapStress_10pct_3xWed"])
    ][["variante", "friccion", "particion", "n_ops", "ops_mes", "r_op", "sum_r", "t_ses", "max_dd_r", "calmar"]]

    cross_focus = df_cross[(df_cross["particion"].isin(["REP", "HOLDOUT"])) & (df_cross["regimen_media"] == "100%")][
        ["firm", "account_size", "modo", "particion", "neto12_medio_usd", "p_neto12_pos_pct", "caja_min_p10_usd", "ratio_net12_p10"]
    ]

    res_md = f"""# Auditoria Multimodelo, Frecuencia Estructural Anti-Overfit y Ecosistema Multi-Frente

> **Fecha:** 2026-11-23  
> **Universo:** `POST_2020` (`2020-01-01 .. 2026-11-17`) en particiones `DESC`, `REP`, `HOLDOUT` y `TERMINAL` (`2026-10-01 .. 2026-11-17`, excluyendo `2026-10-07`).  
> **Monte Carlo Sincronizado:** `N = 2,000` trayectorias x `H = 504` sesiones (24 meses) compartiendo exactamente el mismo calendario aleatorio `j_seq(N, H)` entre todos los frentes simultaneos.

---

## 1. Desbloqueo de `O` (Overnight NQ) hasta Nov 2026 y Auditoria de Swaps CFD

- **Causa raiz del corte `2025-10-13` resuelta**: `run_o(ms, qty=None)` aplicaba el tope de margen heredado de 1 mini NQ sobre `\\$50,000` (`floor(25,000 / dailyClose) == 0` siempre que `NQ > 25,000`), cortando la serie en `{max_gagged_dt}`. Al pasar `qty=1` (dimensionamiento fraccional CFD o micros `MNQ`), `O` opera con continuidad total hasta **`{max_ungagged_dt}`** incluyendo el mercado alcista `2025-10 .. 2026-11` y `TERMINAL`.
- **Impacto real del Swap CFD (`US100` Long `0.022%/noche` ~= `8%` anual + triple swap `3x` los miercoles)**:

{o_focus.to_markdown(index=False)}

---

## 2. Expansion Estructural de Frecuencia sin Sobreajuste (`DESC -> REP -> HOLDOUT + TERMINAL`)

Regla de seleccion estricta fijada *ex-ante* sobre `DESC` (`mult_frec >= 1.5x`, `t_ses >= 2.0`, `Calmar >= 1.5`) y confirmacion ciega en `REP` (`R/op >= +0.08`, `t_ses >= 1.5`, `Calmar >= 1.2`), sin optimizacion de umbrales numericos:

{df_freq.to_markdown(index=False)}

---

## 3. Validacion Cruzada de `R_ATR25` y `SpeedEval (T_Only -> Core5)` por Cuenta Individual (1 Slot)

*(Nota de auditoria: en esta iteracion se corrigio el escalado de cupos para respetar estrictamente `max_funded` legal por hogar en cada firma: max 5 en Lucid y Tradeify, max 3-5 en Topstep, max 300K-400K en FTMO).*

{cross_focus.to_markdown(index=False)}

---

## 4. Simulacion Sincronizada del Ecosistema Paralelo Multi-Frente ('Roadmap' por Nivel de Caja)

{df_eco.to_markdown(index=False)}
"""
    (OUT_DIR / "RESULTADO.md").write_text(res_md, encoding="utf-8")

    # Build practical operational roadmap document with exact numbers from df_eco!
    hold_eco = df_eco[(df_eco["particion"] == "HOLDOUT") & (df_eco["regimen_media"] == "100%")].set_index("ecosistema_id")
    rep_eco = df_eco[(df_eco["particion"] == "REP") & (df_eco["regimen_media"] == "100%")].set_index("ecosistema_id")
    rep60_eco = df_eco[(df_eco["particion"] == "REP") & (df_eco["regimen_media"] == "60%")].set_index("ecosistema_id")

    def _fmt_tier(tid: str) -> str:
        rh = hold_eco.loc[tid]
        rr = rep_eco.loc[tid]
        r6 = rep60_eco.loc[tid]
        return (
            f"- **Colchon de caja requerido (`p90` / `p95` HOLDOUT)**: `\\${rh['capital_req_p90_usd']:,.0f}` / `\\${rh['capital_req_p95_usd']:,.0f}`\n"
            f"- **Neto 12m esperado**: `\\${rr['neto12_medio_usd']:,.0f}` (`REP 100%`) | `\\${rh['neto12_medio_usd']:,.0f}` (`HOLDOUT`, mediana `\\${rh['neto12_p50_usd']:,.0f}`, `P(>0) = {rh['p_neto12_pos_pct']:.1f}%`) | `\\${r6['neto12_medio_usd']:,.0f}` (`REP 60%` estres)\n"
            f"- **Riqueza acumulada 24m (HOLDOUT)**: `\\${rh['neto24_medio_usd']:,.0f}` (`Ratio Neto12/|p10| = {rh['ratio_net12_p10']:.2f}x`)"
        )

    roadmap_md = f"""# Roadmap Operativo Multi-Frente (Arquitectura Paralela de Extraccion y Capitalizacion)

> **Principio rector:** No es una escalera lineal donde una estrategia espera a otra, sino una **mesa multi-frente simultanea** donde cada motor opera en el vehiculo regulatorio/prop que maximiza su payoff asimetrico y minimiza su friccion.

---

## 1. Los 4 Frentes Simultaneos de la Mesa

| Frente | Vehiculo / Plataforma | Cartera / Modulos Asignados | Rol Financiero en el Ecosistema |
|---|---|---|---|
| **Frente 1 — Motor Primario Futuros EOD** | `NinjaTrader 8` (`LucidFlex 150K/50K`, `Tradeify Select Flex 150K/50K`, `Topstep NoAct 50K`, `FundedNext 50K` solo en promo) | **Eval:** `SpeedEval` (`T_Only` en Lucid/Tradeify) o `Core5_R25` (en Topstep mensual)<br>**Funded:** `Core5_AltaConv` con `R_ATR25` (`Netting`, `MaxOpenR=3.0`, flat `16:40 ET`, `16:05 ET` en Topstep) | **Generador masivo de flujo de caja** (`~29 ops/mes`, cero costo de activacion, trailing EOD puro). |
| **Frente 2 — Motor CFD Static-DD Intradia** | `cTrader` / `MetaTrader 5` (`FTMO Swing 100K`, `The5ers HighStakes 100K`) | `Core5_R25` en `US100` (`0.981 pts` spread RTH, `\\$0` comm) + Satelite `US500/ES` (`0.35 pts`, `+21.2 R` OOS) + **`HardFlatten = 16:40 ET` (Cero Swap Nocturno)** + `FundedDdBrake` (`-4.5% -> 0.5x`) | **Estabilizador de DD estatico sin arrastre de swaps**: suma diversificacion `US100 + US500` con friccion RTH 36% menor al futuro y cobra ciclos quincenales sin pagar el swap `8%-10%` anual de CFD. |
| **Frente 3 — Manga Ortogonal Multi-Activo** | `NinjaTrader 8` / `MT5` (`cartera_20261116`: `8` reglas `NQ, ES, YM, RTY, CL, MGC`) | `CVGAP-ES-C`, `U1-RACIMOS-GRILLA-NQ`, `CONF-CVR-CFD-NQ-R`, `U1-ZONAS-BT2-ES/NQ`, `PREAPERTURA-NQ` (peso `0.5x`), `U1-ORO-GRILLA` (`1R = \\$200` en 50K) | **Descorrelacion estructural (`rho ~= -0.02`)**: `+52 ops/mes` que sostienen pagos cuando el Nasdaq intradia entra en compresion. |
| **Frente 4 — Boveda Personal sin Topes** | Broker regulado propio (`IBKR / AMP` en Futuros Micros `MNQ/MES`, `0` swap) | `30%` de barrido (*sweep*) automatico sobre cada nuevo maximo de caja prop -> `Core5_R25 + ES + O_noWed (0 swap en MNQ) + cartera_20261116` (`1R = 0.75%` compuesto) | **Conversion de opciones fragiles en patrimonio perpetuo**: unico lugar donde `O` Overnight captura alfa real sin swap CFD, inmune a cierres de prop firms. |

---

## 2. Dimensionamiento Simultaneo por Presupuesto de Riesgo (Cifras Reales Respetando Topes Legales por Hogar)

### Nivel E1 — Capital Semilla (`Presupuesto recomendado: \\$3,500 - \\$4,500`)
- **Composicion simultanea**: `2x LucidFlex 50K` + `2x Tradeify Select Flex 50K` (`SpeedEval -> Core5_R25`, escalonadas cada `3` dias) + `1x The5ers HighStakes 100K` (`US100 + US500` intradia sin swap).
{_fmt_tier("E1_Semilla_5Ctas")}

### Nivel E2 — Escala Balanceada (`Presupuesto recomendado: \\$8,500 - \\$11,000`)
- **Composicion simultanea**: `2x LucidFlex 150K` + `2x Tradeify Select Flex 150K` + `1x FTMO Swing 100K` + `1x The5ers HighStakes 100K`.
{_fmt_tier("E2_Balanceado_6Ctas")}

### Nivel E3 — Mesa Institucional Media (`Presupuesto recomendado: \\$15,000 - \\$19,000`)
- **Composicion simultanea**: `3x LucidFlex 150K` + `3x Tradeify Select Flex 150K` + `2x Topstep NoAct 50K` + `2x FTMO Swing 100K` + `2x The5ers HighStakes 100K`.
{_fmt_tier("E3_Institucional_12Ctas")}

### Nivel E4 vs E5 — Tope Legal Multi-Prop con Freno Dinamico de Caja + Boveda Personal (`Recomendado para Maximizacion Controlada`)
- **Composicion simultanea al tope legal por hogar (`20` cuentas)**:
  `5x LucidFlex 150K` (tope Lucid) + `5x Tradeify 150K` (tope Tradeify) + `3x Topstep 50K` + `2x FundedNext 50K` + `3x FTMO Swing 100K` (`300K` de `400K` cap FTMO) + `2x The5ers 100K`.
- **Sin freno dinamico (`E4`)**:
{_fmt_tier("E4_TopeLegal_20Ctas_Bruto")}
- **Con Freno Dinamico de Caja (`-\\$7,500` pausa compras de expansion / `-\\$3,500` reanuda) + `30%` Sweep a Boveda Personal (`E5`)**:
{_fmt_tier("E5_Master_Throttle_y_Boveda")}
- **Capital acumulado dentro de la Boveda Personal propia a los 24m (`E5` HOLDOUT)**: **`\\${hold_eco.loc['E5_Master_Throttle_y_Boveda', 'boveda_pers_24m_usd']:,.0f}`** libres de reglas prop.

---

## 3. Reglas Operativas Estrictas de Control de Riesgo y Anti-Ban

1. **Escalonamiento obligatorio (`Stagger = 3 a 5 sesiones`)**: jamas iniciar ni resetear todas las evaluaciones el mismo lunes. Desfasar las compras `3` dias habiles en Futuros y `5` dias en CFD reduce la correlacion de quema en rachas adversas y evita alertas de *copy-trading* sincronizado al milisegundo entre firmas distintas.
2. **Sensibilidad de `T` (`ORB15`) al reloj `09:30:00` en CFD**: sincronizar reloj NTP de la VPS (`< 50 ms` de deriva) y operar siempre con `CheckStopsOnEveryTick = true` en `cTrader`/`MT5`. Si el broker CFD presenta congelamiento de cotizacion en `09:30:00-09:30:10`, reducir el peso de `T` al `50%` (`0.35`) en CFD manteniendo `100%` en `NT8` CME.
3. **Exclusion de `O` Overnight en CFD por Swaps (`8%-10%` anual + `3x` miercoles)**: la auditoria demostro que el financiamiento nocturno CFD (`~6.5 pts/noche` y `~19.5 pts` los miercoles en `US100`) absorbe casi la totalidad de la esperanza matematica de `O` (`REP R/op = +0.006`, `HOLDOUT = -1.41 R`). Por ello, los bots `cTrader`/`MT5` se mantienen **100% intradia (`HardFlatten = 16:40 ET`)**, reservando `O` exclusivamente para futuros `MNQ` en la Boveda Personal (cero swap).
4. **Protocolo de Freno en Tres Capas**:
   - *Nivel Cuenta Funded CFD*: `EnableFundedDdBrake = true` a `-4.5%` desde HWM -> recorta `1R` al `50%` automaticamente en el bot (`cTrader` y `MT5`).
   - *Nivel Caja de Ecosistema*: si el flujo neto de caja cae `-\\$7,500` desde su maximo historico (o `-30%` del colchon inicial en niveles `E1/E2`), **congelar nuevas compras de evaluaciones de expansion** y dejar operando unicamente las cuentas ya fondeadas y el nucleo base hasta recuperar `-\\$3,500`.
   - *Exclusiones permanentes*: **Cero** cuentas en `Apex` y `AlphaFutures` (prohibicion de bots), **cero** `TakeProfitTrader` intradia trailing con `Core5`, y **cero** compras retail sin codigo promo (`>= 25%-30%` off) en `Lucid`, `Tradeify` y `FundedNext`.
"""
    (OUT_DIR / "ROADMAP_OPERATIVO_MULTIFRENTE.md").write_text(roadmap_md, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
