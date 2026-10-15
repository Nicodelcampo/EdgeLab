"""EmaCorridorTrend v4.0 — Detector de Zonas y Corredores Tendenciales Estables sobre EMA.
Traducción 1:1 verificada del indicador NinjaTrader 8 (EmaCorridorTrend.cs).

Identifica tramos donde el precio se desplaza de manera estable y ordenada respecto
de una EMA de referencia, resolviendo la singularidad de cociente en pullbacks que tocan
la media y adaptado a microestructura de futuros (ES en resoluciones tick: 25T, 100T, 500T, 1000T).

4 Pilares de Estabilidad:
  (P1) Eficiencia, Monotonía y Pendiente de la EMA.
  (P2) Dominancia Unilateral con tolerancia de apoyo/beso a la EMA.
  (P3) Estabilidad de Picos Más Lejanos (Far) y Más Cercanos (Near) por sub-bloques.
  (P4) Linealidad de Trayectoria del Precio (R^2 de regresión).
"""

import math
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd

TICK_ES = 0.25


@dataclass
class EmaCorridorPreset:
    preset_id: int
    window_bars: int
    slope_bars: int
    block_bars: int
    min_zone_bars: int
    grace_bars: int
    min_ema_eff: float
    min_ema_mono: float
    min_ema_slope_atr: float
    min_side_frac: float
    min_gap_atr: float
    max_counter_close_atr: float
    max_far_disp: float
    max_near_disp: float
    min_price_r2: float


PRESETS: Dict[int, EmaCorridorPreset] = {
    1: EmaCorridorPreset(
        preset_id=1,
        window_bars=72,
        slope_bars=50,
        block_bars=12,
        min_zone_bars=75,
        grace_bars=20,
        min_ema_eff=0.90,
        min_ema_mono=0.88,
        min_ema_slope_atr=0.040,
        min_side_frac=0.92,
        min_gap_atr=1.05,
        max_counter_close_atr=0.80,
        max_far_disp=0.36,
        max_near_disp=0.38,
        min_price_r2=0.72,
    ),
    2: EmaCorridorPreset(
        preset_id=2,  # Equilibrado (Default ES 25T)
        window_bars=60,
        slope_bars=45,
        block_bars=12,
        min_zone_bars=65,
        grace_bars=24,
        min_ema_eff=0.85,
        min_ema_mono=0.84,
        min_ema_slope_atr=0.030,
        min_side_frac=0.88,
        min_gap_atr=0.80,
        max_counter_close_atr=1.05,
        max_far_disp=0.44,
        max_near_disp=0.46,
        min_price_r2=0.64,
    ),
    3: EmaCorridorPreset(
        preset_id=3,  # Amplio
        window_bars=48,
        slope_bars=36,
        block_bars=12,
        min_zone_bars=50,
        grace_bars=28,
        min_ema_eff=0.80,
        min_ema_mono=0.80,
        min_ema_slope_atr=0.024,
        min_side_frac=0.84,
        min_gap_atr=0.65,
        max_counter_close_atr=1.25,
        max_far_disp=0.52,
        max_near_disp=0.55,
        min_price_r2=0.55,
    ),
}


@dataclass
class CompletedZone:
    zone_id: int
    direction: int            # +1: Alcista, -1: Bajista
    origin_bar: int           # Barra exacta donde despegó el impulso
    end_bar: int              # Último extremo válido a favor de la tendencia
    confirm_bar: int          # Barra en la que se cumplió min_zone_bars
    close_bar: int            # Barra en la que la zona terminó formalmente (break/grace)
    origin_price: float       # Precio en el pivote de arranque
    extreme_price: float      # Precio del extremo alcanzado
    box_low: float            # Mínimo absoluto dentro de [origin_bar .. end_bar]
    box_high: float           # Máximo absoluto dentro de [origin_bar .. end_bar]
    box_height_pts: float     # box_high - box_low
    box_height_ticks: float   # (box_high - box_low) / tick_size
    reg_slope: float          # Pendiente de la recta de regresión
    reg_intercept: float      # Ordenada al origen en origin_bar
    corridor_up_off: float    # Banda superior respecto del eje
    corridor_dn_off: float    # Banda inferior respecto del eje
    mean_far_atr: float       # Promedio de picos lejanos a la EMA en ATR
    mean_near_atr: float      # Promedio de picos cercanos a la EMA en ATR
    stability_score: float    # Puntaje compuesto 0-100
    is_virgin: bool = True
    first_retest_bar: int = -1
    first_retest_type: str = ""


def compute_ema(series: np.ndarray, period: int) -> np.ndarray:
    alpha = 2.0 / (period + 1.0)
    out = np.empty_like(series, dtype=np.float64)
    out[0] = series[0]
    for i in range(1, len(series)):
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1]
    return out


def compute_atr_sma(high: np.ndarray, low: np.ndarray, period: int, tick_size: float = TICK_ES) -> np.ndarray:
    rng = high - low
    out = np.empty_like(rng, dtype=np.float64)
    csum = np.cumsum(np.insert(rng, 0, 0.0))
    for i in range(len(rng)):
        start = max(0, i - period + 1)
        count = i - start + 1
        out[i] = max((csum[i + 1] - csum[start]) / count, tick_size)
    return out


def find_zone_origin(
    cb: int,
    p_window: int,
    lookback: int,
    direction: int,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    ema: np.ndarray,
    atr: np.ndarray,
    min_allowed_bar: int,
    tick_size: float = TICK_ES,
) -> int:
    lo_bound = max(min_allowed_bar, cb - p_window - lookback)
    hi_bound = max(lo_bound, cb - p_window + 12)

    touch_bar = hi_bound
    for b in range(hi_bound, lo_bound - 1, -1):
        signed_c = direction * (close[b] - ema[b]) / max(atr[b], tick_size)
        if signed_c <= 0.15:
            touch_bar = b
            break

    pv_start = max(min_allowed_bar, touch_bar - 10)
    pv_end = min(cb - p_window // 2, touch_bar + 10)
    if pv_end < pv_start:
        pv_end = pv_start

    best_k = pv_start
    if direction > 0:
        best_val = low[pv_start]
        for k in range(pv_start, pv_end + 1):
            if low[k] <= best_val:
                best_val = low[k]
                best_k = k
    else:
        best_val = high[pv_start]
        for k in range(pv_start, pv_end + 1):
            if high[k] >= best_val:
                best_val = high[k]
                best_k = k
    return int(best_k)


def evaluate_window_stability(
    cb: int,
    direction: int,
    p_window: int,
    p_block: int,
    p_min_side: float,
    p_min_gap: float,
    p_max_counter: float,
    p_max_far_disp: float,
    p_max_near_disp: float,
    p_min_r2: float,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    mid: np.ndarray,
    ema: np.ndarray,
    atr: np.ndarray,
    ema_eff: float,
) -> Tuple[bool, float, float, float, float]:
    sl = slice(cb - p_window + 1, cb + 1)
    c_w = close[sl]
    h_w = high[sl]
    l_w = low[sl]
    m_w = mid[sl]
    e_w = ema[sl]
    a_w = atr[sl]

    signed_c = direction * (c_w - e_w) / a_w
    side_frac = float(np.mean(signed_c >= -0.35))
    mean_gap = float(np.mean(signed_c))
    min_c = float(np.min(signed_c))

    if side_frac < p_min_side or mean_gap < p_min_gap or min_c < -p_max_counter:
        return False, 0.0, 0.0, 0.0, 0.0

    far_dist = (h_w - e_w) / a_w if direction > 0 else (e_w - l_w) / a_w
    near_dist = (l_w - e_w) / a_w if direction > 0 else (e_w - h_w) / a_w

    n_blocks = max(2, p_window // p_block)
    far_peaks = np.empty(n_blocks)
    near_peaks = np.empty(n_blocks)
    for b in range(n_blocks):
        bs = b * p_block
        be = min(bs + p_block, p_window)
        far_peaks[b] = np.max(far_dist[bs:be])
        near_peaks[b] = np.min(near_dist[bs:be])

    mean_far = float(np.mean(far_peaks))
    mean_near = float(np.mean(near_peaks))
    if mean_far <= 0.5:
        return False, 0.0, 0.0, 0.0, 0.0

    corridor_scale = max(mean_far, 1.5)
    far_disp = float(np.std(far_peaks)) / corridor_scale
    near_disp = float(np.std(near_peaks)) / corridor_scale

    if p_max_far_disp > 0.0 and far_disp > p_max_far_disp:
        return False, 0.0, 0.0, 0.0, 0.0
    if p_max_near_disp > 0.0 and near_disp > p_max_near_disp:
        return False, 0.0, 0.0, 0.0, 0.0

    x = np.arange(p_window, dtype=np.float64)
    dx = x - 0.5 * (p_window - 1)
    dy = m_w - np.mean(m_w)
    denom = float(np.sum(dx * dx) * np.sum(dy * dy))
    r_corr = float(np.sum(dx * dy)) / math.sqrt(denom) if denom > 1e-12 else 0.0
    r2 = (r_corr * r_corr) if (r_corr * direction > 0.0) else 0.0

    if r2 < p_min_r2:
        return False, 0.0, 0.0, 0.0, 0.0

    far_score = max(0.0, 1.0 - far_disp / p_max_far_disp) if p_max_far_disp > 0 else 1.0
    near_score = max(0.0, 1.0 - near_disp / p_max_near_disp) if p_max_near_disp > 0 else 1.0
    score = 100.0 * (0.35 * r2 + 0.25 * ema_eff + 0.20 * far_score + 0.20 * near_score)

    return True, score, mean_far, mean_near, r2


def detect_ema_corridor_zones(
    open_arr: np.ndarray,
    high_arr: np.ndarray,
    low_arr: np.ndarray,
    close_arr: np.ndarray,
    ema_period: int = 200,
    atr_period: int = 100,
    preset: int = 2,
    tick_size: float = TICK_ES,
    lookback_origin: int = 40,
    break_confirm_bars: int = 5,
    hard_break_ema_atr: float = 1.60,
    min_move_points: float = 0.0,
) -> Tuple[np.ndarray, np.ndarray, List[CompletedZone]]:
    n_bars = len(close_arr)
    p = PRESETS.get(preset, PRESETS[2])

    high = np.asarray(high_arr, dtype=np.float64)
    low = np.asarray(low_arr, dtype=np.float64)
    close = np.asarray(close_arr, dtype=np.float64)
    mid = 0.5 * (high + low)

    ema = compute_ema(close, ema_period)
    atr = compute_atr_sma(high, low, atr_period, tick_size=tick_size)

    state = np.zeros(n_bars, dtype=np.int8)
    score_series = np.zeros(n_bars, dtype=np.float32)

    active_dir = 0
    origin_bar = 0
    last_ok_bar = -1000000
    last_zone_end_bar = 0
    best_ext_bar = 0
    best_ext_px = 0.0
    last_valid_score = 0.0
    confirmed = False
    zone_count = 0

    active_zone_dict: Optional[Dict[str, Any]] = None
    completed_zones: List[CompletedZone] = []

    min_needed = max(p.window_bars + lookback_origin, p.slope_bars, ema_period, atr_period) + 5

    for cb in range(min_needed, n_bars):
        a = atr[cb]
        disp_ema = ema[cb] - ema[cb - p.slope_bars]
        cand_dir = 1 if disp_ema > 0.0 else (-1 if disp_ema < 0.0 else 0)
        cond_ok = False
        stab_score = 0.0
        mean_far = 0.0
        mean_near = 0.0
        r2_val = 0.0

        if cand_dir != 0 and a > 0.0:
            d_ema = np.diff(ema[cb - p.slope_bars : cb + 1])
            sum_abs_de = float(np.sum(np.abs(d_ema)))
            ema_eff = abs(disp_ema) / sum_abs_de if sum_abs_de > 1e-12 else 0.0
            ema_mono = float(np.mean((d_ema * cand_dir) > 0.0))
            ema_slope_atr = abs(disp_ema) / (p.slope_bars * a)

            if ema_eff >= p.min_ema_eff and ema_mono >= p.min_ema_mono and ema_slope_atr >= p.min_ema_slope_atr:
                cond_ok, stab_score, mean_far, mean_near, r2_val = evaluate_window_stability(
                    cb=cb,
                    direction=cand_dir,
                    p_window=p.window_bars,
                    p_block=p.block_bars,
                    p_min_side=p.min_side_frac,
                    p_min_gap=p.min_gap_atr,
                    p_max_counter=p.max_counter_close_atr,
                    p_max_far_disp=p.max_far_disp,
                    p_max_near_disp=p.max_near_disp,
                    p_min_r2=p.min_price_r2,
                    close=close,
                    high=high,
                    low=low,
                    mid=mid,
                    ema=ema,
                    atr=atr,
                    ema_eff=ema_eff,
                )
                if cond_ok:
                    last_valid_score = stab_score

        if cond_ok:
            if active_dir != cand_dir:
                active_dir = cand_dir
                origin_bar = find_zone_origin(
                    cb=cb,
                    p_window=p.window_bars,
                    lookback=lookback_origin,
                    direction=active_dir,
                    close=close,
                    high=high,
                    low=low,
                    ema=ema,
                    atr=atr,
                    min_allowed_bar=last_zone_end_bar + 1,
                    tick_size=tick_size,
                )
                best_ext_bar = cb
                best_ext_px = high[cb] if active_dir > 0 else low[cb]
                confirmed = False
                active_zone_dict = None
            last_ok_bar = cb

        if active_dir != 0:
            if active_dir > 0 and high[cb] >= best_ext_px:
                best_ext_px = high[cb]
                best_ext_bar = cb
            elif active_dir < 0 and low[cb] <= best_ext_px:
                best_ext_px = low[cb]
                best_ext_bar = cb

            recent_signed = [
                active_dir * (close[cb - j] - ema[cb - j]) / atr[cb - j]
                for j in range(min(break_confirm_bars, cb))
            ]
            hard_cross = (active_dir * (close[cb] - ema[cb]) / a) < -hard_break_ema_atr
            sustained_cross = len(recent_signed) == break_confirm_bars and all(x < -0.35 for x in recent_signed)
            grace_expired = (cb - last_ok_bar) > p.grace_bars

            if hard_cross or sustained_cross or grace_expired:
                if active_zone_dict is not None and confirmed:
                    active_zone_dict["close_bar"] = cb
                    completed_zones.append(CompletedZone(**active_zone_dict))
                    last_zone_end_bar = active_zone_dict["end_bar"]
                active_dir = 0
                confirmed = False
                active_zone_dict = None
                continue

            zone_len = cb - origin_bar + 1
            orig_px = low[origin_bar] if active_dir > 0 else high[origin_bar]
            move_pts = abs(close[cb] - orig_px)

            if not confirmed and cond_ok and zone_len >= p.min_zone_bars and (min_move_points <= 0.0 or move_pts >= min_move_points):
                confirmed = True
                zone_count += 1

            if confirmed:
                state[cb] = active_dir
                score_series[cb] = last_valid_score
                end_bar = max(origin_bar + 15, best_ext_bar)

                idx_seg = np.arange(origin_bar, end_bar + 1)
                x_s = (idx_seg - origin_bar).astype(np.float64)
                y_s = mid[idx_seg]
                poly = np.polyfit(x_s, y_s, 1)
                slope, intercept = float(poly[0]), float(poly[1])
                reg_line = intercept + slope * x_s

                up_res = high[idx_seg] - reg_line
                dn_res = reg_line - low[idx_seg]
                up_off = max(tick_size, float(np.percentile(up_res, 90)))
                dn_off = max(tick_size, float(np.percentile(dn_res, 90)))

                box_lo = float(np.min(low[idx_seg]))
                box_hi = float(np.max(high[idx_seg]))

                active_zone_dict = {
                    "zone_id": zone_count,
                    "direction": int(active_dir),
                    "origin_bar": int(origin_bar),
                    "end_bar": int(end_bar),
                    "confirm_bar": int(cb) if active_zone_dict is None else active_zone_dict["confirm_bar"],
                    "close_bar": int(cb),
                    "origin_price": float(orig_px),
                    "extreme_price": float(best_ext_px),
                    "box_low": box_lo,
                    "box_high": box_hi,
                    "box_height_pts": box_hi - box_lo,
                    "box_height_ticks": (box_hi - box_lo) / tick_size,
                    "reg_slope": slope,
                    "reg_intercept": intercept,
                    "corridor_up_off": up_off,
                    "corridor_dn_off": dn_off,
                    "mean_far_atr": mean_far,
                    "mean_near_atr": mean_near,
                    "stability_score": last_valid_score,
                }

    if active_zone_dict is not None and confirmed:
        active_zone_dict["close_bar"] = n_bars - 1
        completed_zones.append(CompletedZone(**active_zone_dict))

    return state, score_series, completed_zones
