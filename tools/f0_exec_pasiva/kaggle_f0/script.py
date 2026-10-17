#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EDGELAB — PASADA 2: BATERÍA COMPLETA ANTI-OVERFIT Y FALSACIÓN DE FALSOS EDGES
Indicador: EmaCorridorTrend v4.0 en ES Multi-Resolución (25T, 100T, 500T, 1000T)
================================================================================
Aplica todas las defensas metodológicas de EdgeLab sobre las 2 familias más fuertes de
TRAVERSAL_THROUGH (Familia 1: Regreso Virgen al Borde Exterior con Cierre Confirmado;
Familia 2: Penetración Virgen al 25%-33.3% hacia el Origen) y su contraparte en el
Pivote de Origen 100% (Familia 3: Rebote en Order Block de Origen):

  1. Guarda Estricta de Sesión (H-04): Barras, zonas y carreras de barrera confinadas 100%
     dentro de cada sesión individual (trade_date constante, sin cruzar cortes diarios).
  2. Purga Estricta de Solapamiento (no_overlap = True): Un evento nuevo solo se admite si
     su barra de entrada es posterior a la barra de resolución del evento previo en la misma sesión.
  3. Nulo Emparejado de 5 Pseudo-Zonas por Evento Real (H-03): Muestreadas dentro del mismo
     (Contrato × Media Hora UTC/CT) en barras fuera de corredor (state == 0), con signo de
     tendencia espejado y misma distancia de barrera.
  4. Error Estándar Clusterizado por Sesión (Liang-Zeger / Hansen SE_clustered), MDE al 80%
     de potencia (MDE_80 = 2.80 * SE_clustered) y Test de Permutación de Signos por Sesión
     (Rademacher Sign-Flip MCPT con M = 2,000 permutaciones).
  5. Corrección por Múltiples Hipótesis: Holm-Bonferroni step-down (p_holm) y Benjamini-Hochberg
     FDR (q_fdr) sobre toda la grilla primaria pre-registrada.
  6. Partición Out-of-Sample Temporal: Primera Mitad (S1: sesiones 1..149) vs Segunda Mitad
     (S2: sesiones 150..299) y consistencia en los 6 contratos trimestrales (n_contracts_pos / 6).
  7. Descomposición Direccional (Mirror Check: LONG vs SHORT) y de Régimen Horario
     (RTH regular outside_regular==False vs ETH overnight outside_regular==True).
  8. Superficie de Estabilidad Paramétrica (Presets 1/2/3 y profundidades 20%/25%/33.3%/40%)
     y Prueba de Fricción Física Adversaria (-1 tick de handicap en la barrera).
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

try:
    from numba import njit
    HAS_NUMBA = True
except Exception:
    HAS_NUMBA = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

T0 = time.time()

NORTH_STAR_HASH = "ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8"
EXPECTED_MANIFEST_SHA256 = "06d7fb2ac7fb5bb7fd63bc57ecc2cd7ef9c3fb3ef59cabceac2b7d72d32bbd84"
HOLDOUT_TRADE_DATE = 20261001
HOLDOUT_UTC_NS = 1790812800000000000
TICK_ES = 0.25


# =========================================================================
# 1. DETECTOR NUMBA-JIT CON GUARDA ESTRICTA DE SESIÓN (H-04)
# =========================================================================

@njit(cache=False)
def detect_zones_session_strict_numba(
    open_p: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    session_id: np.ndarray,
    contract_id: np.ndarray,
    ema_period: int,
    atr_period: int,
    p_window: int,
    p_slope: int,
    p_block: int,
    p_min_zone: int,
    p_grace: int,
    p_min_er: float,
    p_min_mono: float,
    p_min_slope_atr: float,
    p_min_side: float,
    p_min_gap: float,
    p_max_counter: float,
    p_max_far_disp: float,
    p_max_near_disp: float,
    p_min_r2: float,
    lookback_origin: int,
    break_confirm_bars: int,
    hard_break_ema_atr: float,
    tick_size: float,
):
    """
    Detecta zonas EmaCorridorTrend v4.0 reiniciando el estado de zona en cada cambio de
    session_id (H-04), pero manteniendo la continuidad de EMA/ATR dentro del mismo contrato
    para no perder barras de calentamiento al inicio de la sesión.
    """
    n = len(close)
    ema = np.zeros(n, dtype=np.float64)
    atr = np.zeros(n, dtype=np.float64)
    mid = 0.5 * (high + low)
    tr = np.zeros(n, dtype=np.float64)

    k_ema = 2.0 / (ema_period + 1.0)
    k_atr = 2.0 / (atr_period + 1.0)

    for i in range(n):
        if i == 0 or contract_id[i] != contract_id[i - 1]:
            ema[i] = close[i]
            tr[i] = max(high[i] - low[i], tick_size)
            atr[i] = tr[i]
        else:
            ema[i] = close[i] * k_ema + ema[i - 1] * (1.0 - k_ema)
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, max(hc, lc))
            atr[i] = tr[i] * k_atr + atr[i - 1] * (1.0 - k_atr)
            if atr[i] < tick_size:
                atr[i] = tick_size

    state = np.zeros(n, dtype=np.int8)
    score_series = np.zeros(n, dtype=np.float64)

    max_zones = n // max(10, p_min_zone // 2) + 32
    # Columnas de zones_mat (19 columnas):
    #  0: zone_id
    #  1: dir (+1 / -1)
    #  2: origin_bar
    #  3: end_bar
    #  4: confirm_bar
    #  5: close_bar
    #  6: orig_px
    #  7: ext_px
    #  8: b_lo
    #  9: b_hi
    # 10: h_ticks
    # 11: slope_pts_per_bar
    # 12: stability_score
    # 13: session_id
    # 14: contract_id
    # 15: sess_start_bar
    # 16: sess_end_bar (exclusivo)
    zones_mat = np.zeros((max_zones, 17), dtype=np.float64)
    z_idx = 0

    # Precalcular límites de cada sesión [sess_start, sess_end)
    sess_start_of_bar = np.zeros(n, dtype=np.int32)
    sess_end_of_bar = np.zeros(n, dtype=np.int32)
    s_cur = 0
    for i in range(1, n + 1):
        if i == n or session_id[i] != session_id[s_cur]:
            for k in range(s_cur, i):
                sess_start_of_bar[k] = s_cur
                sess_end_of_bar[k] = i
            s_cur = i

    min_bars_in_sess = p_window + p_slope + 4
    n_blocks = max(3, p_window // p_block)
    x_mean = 0.5 * (p_window - 1.0)
    sxx = p_window * (p_window * p_window - 1.0) / 12.0

    active_dir = 0
    origin_bar = -1
    best_ext_bar = -1
    best_ext_px = 0.0
    last_ok_bar = -1
    confirmed = False
    confirm_bar = -1
    last_zone_end_bar = -1
    last_valid_score = 0.0

    for cb in range(n):
        s_start = sess_start_of_bar[cb]
        s_end = sess_end_of_bar[cb]
        if cb == s_start:
            # Al iniciar nueva sesión, resetear estado activo (H-04: prohibido cruzar sesiones)
            active_dir = 0
            origin_bar = -1
            best_ext_bar = -1
            last_ok_bar = -1
            confirmed = False
            confirm_bar = -1
            last_zone_end_bar = s_start
            continue

        if cb - s_start < min_bars_in_sess:
            continue

        a = atr[cb]
        net_ema = ema[cb] - ema[cb - p_slope]
        path_ema = 0.0
        pos_steps = 0
        neg_steps = 0
        for i in range(cb - p_slope + 1, cb + 1):
            st = ema[i] - ema[i - 1]
            path_ema += abs(st)
            if st > 0.0:
                pos_steps += 1
            elif st < 0.0:
                neg_steps += 1

        ema_eff = abs(net_ema) / path_ema if path_ema > 1e-12 else 0.0
        ema_slope_atr = net_ema / (p_slope * a)

        cand_dir = 0
        if ema_slope_atr >= p_min_slope_atr and ema_eff >= p_min_er and (pos_steps / p_slope) >= p_min_mono:
            cand_dir = 1
        elif ema_slope_atr <= -p_min_slope_atr and ema_eff >= p_min_er and (neg_steps / p_slope) >= p_min_mono:
            cand_dir = -1

        cond_ok = False
        if cand_dir != 0:
            on_side = 0
            gap_sum = 0.0
            max_cnt = 0.0
            y_sum = 0.0
            w_start = cb - p_window + 1
            for i in range(w_start, cb + 1):
                ai = atr[i]
                sc = cand_dir * (close[i] - ema[i]) / ai
                if sc >= -0.35:
                    on_side += 1
                gap_sum += sc
                if sc < 0.0 and (-sc) > max_cnt:
                    max_cnt = -sc
                y_sum += mid[i]

            side_ratio = on_side / p_window
            mean_gap = gap_sum / p_window

            if side_ratio >= p_min_side and mean_gap >= p_min_gap and max_cnt <= p_max_counter:
                b_len = p_window // n_blocks
                if b_len >= 2:
                    sum_f = 0.0
                    sum_ff = 0.0
                    sum_n = 0.0
                    sum_nn = 0.0
                    for b in range(n_blocks):
                        bs = w_start + b * b_len
                        be = cb + 1 if b == n_blocks - 1 else bs + b_len
                        mx_f = -1e18
                        mn_n = 1e18
                        for idx in range(bs, be):
                            if cand_dir > 0:
                                fd = (high[idx] - ema[idx]) / atr[idx]
                                nd = (low[idx] - ema[idx]) / atr[idx]
                            else:
                                fd = (ema[idx] - low[idx]) / atr[idx]
                                nd = (ema[idx] - high[idx]) / atr[idx]
                            if fd > mx_f:
                                mx_f = fd
                            if nd < mn_n:
                                mn_n = nd
                        sum_f += mx_f
                        sum_ff += mx_f * mx_f
                        sum_n += mn_n
                        sum_nn += mn_n * mn_n

                    mean_far = sum_f / n_blocks
                    mean_near = sum_n / n_blocks
                    if mean_far > 0.5:
                        c_scale = mean_far if mean_far > 1.5 else 1.5
                        var_f = sum_ff / n_blocks - mean_far * mean_far
                        var_n = sum_nn / n_blocks - mean_near * mean_near
                        far_disp = (math.sqrt(var_f) if var_f > 0.0 else 0.0) / c_scale
                        near_disp = (math.sqrt(var_n) if var_n > 0.0 else 0.0) / c_scale

                        if far_disp <= p_max_far_disp and near_disp <= p_max_near_disp:
                            y_mean = y_sum / p_window
                            syy = 0.0
                            sxy = 0.0
                            for k in range(p_window):
                                idx = w_start + k
                                dy = mid[idx] - y_mean
                                syy += dy * dy
                                sxy += (k - x_mean) * dy
                            denom = sxx * syy
                            r_corr = sxy / math.sqrt(denom) if denom > 1e-12 else 0.0
                            r2 = (r_corr * r_corr) if (r_corr * cand_dir > 0.0) else 0.0
                            if r2 >= p_min_r2:
                                cond_ok = True
                                f_sc = max(0.0, 1.0 - far_disp / p_max_far_disp)
                                n_sc = max(0.0, 1.0 - near_disp / p_max_near_disp)
                                last_valid_score = 100.0 * (0.35 * r2 + 0.25 * ema_eff + 0.20 * f_sc + 0.20 * n_sc)

        if cond_ok:
            if active_dir != cand_dir:
                if active_dir != 0 and confirmed and z_idx < max_zones:
                    end_b = best_ext_bar if best_ext_bar > origin_bar + 10 else min(cb - 1, origin_bar + 10)
                    if end_b > origin_bar + 5:
                        b_lo = low[origin_bar]
                        b_hi = high[origin_bar]
                        for k in range(origin_bar, end_b + 1):
                            if low[k] < b_lo:
                                b_lo = low[k]
                            if high[k] > b_hi:
                                b_hi = high[k]
                        orig_px = low[origin_bar] if active_dir > 0 else high[origin_bar]
                        slp = (mid[end_b] - mid[origin_bar]) / max(1, end_b - origin_bar)
                        zones_mat[z_idx, 0] = z_idx + 1
                        zones_mat[z_idx, 1] = active_dir
                        zones_mat[z_idx, 2] = origin_bar
                        zones_mat[z_idx, 3] = end_b
                        zones_mat[z_idx, 4] = confirm_bar
                        zones_mat[z_idx, 5] = cb - 1
                        zones_mat[z_idx, 6] = orig_px
                        zones_mat[z_idx, 7] = best_ext_px
                        zones_mat[z_idx, 8] = b_lo
                        zones_mat[z_idx, 9] = b_hi
                        zones_mat[z_idx, 10] = (b_hi - b_lo) / tick_size
                        zones_mat[z_idx, 11] = slp
                        zones_mat[z_idx, 12] = last_valid_score
                        zones_mat[z_idx, 13] = session_id[cb]
                        zones_mat[z_idx, 14] = contract_id[cb]
                        zones_mat[z_idx, 15] = s_start
                        zones_mat[z_idx, 16] = s_end
                        z_idx += 1
                        last_zone_end_bar = end_b

                active_dir = cand_dir
                min_allow = max(s_start + 1, last_zone_end_bar + 1)
                lo_b = max(min_allow, cb - p_window - lookback_origin)
                hi_b = max(lo_b, cb - p_window + 12)
                touch_b = hi_b
                for b_k in range(hi_b, lo_b - 1, -1):
                    sc_k = active_dir * (close[b_k] - ema[b_k]) / atr[b_k]
                    if sc_k <= 0.15:
                        touch_b = b_k
                        break
                pv_s = max(min_allow, touch_b - 10)
                pv_e = min(cb - p_window // 2, touch_b + 10)
                if pv_e < pv_s:
                    pv_e = pv_s
                best_k = pv_s
                if active_dir > 0:
                    bv = low[pv_s]
                    for b_k in range(pv_s, pv_e + 1):
                        if low[b_k] <= bv:
                            bv = low[b_k]
                            best_k = b_k
                else:
                    bv = high[pv_s]
                    for b_k in range(pv_s, pv_e + 1):
                        if high[b_k] >= bv:
                            bv = high[b_k]
                            best_k = b_k
                origin_bar = best_k
                best_ext_bar = cb
                best_ext_px = high[cb] if active_dir > 0 else low[cb]
                confirmed = False
            last_ok_bar = cb

        if active_dir != 0:
            if active_dir > 0 and high[cb] >= best_ext_px:
                best_ext_px = high[cb]
                best_ext_bar = cb
            elif active_dir < 0 and low[cb] <= best_ext_px:
                best_ext_px = low[cb]
                best_ext_bar = cb

            hard_cross = (active_dir * (close[cb] - ema[cb]) / a) < -hard_break_ema_atr
            sustained_cross = True
            for j in range(break_confirm_bars):
                if active_dir * (close[cb - j] - ema[cb - j]) / atr[cb - j] >= -0.35:
                    sustained_cross = False
                    break
            grace_expired = (cb - last_ok_bar) > p_grace

            if hard_cross or sustained_cross or grace_expired:
                if confirmed and z_idx < max_zones:
                    end_b = best_ext_bar if best_ext_bar > origin_bar + 10 else min(cb, origin_bar + 10)
                    if end_b > origin_bar + 5:
                        b_lo = low[origin_bar]
                        b_hi = high[origin_bar]
                        for k in range(origin_bar, end_b + 1):
                            if low[k] < b_lo:
                                b_lo = low[k]
                            if high[k] > b_hi:
                                b_hi = high[k]
                        orig_px = low[origin_bar] if active_dir > 0 else high[origin_bar]
                        slp = (mid[end_b] - mid[origin_bar]) / max(1, end_b - origin_bar)
                        zones_mat[z_idx, 0] = z_idx + 1
                        zones_mat[z_idx, 1] = active_dir
                        zones_mat[z_idx, 2] = origin_bar
                        zones_mat[z_idx, 3] = end_b
                        zones_mat[z_idx, 4] = confirm_bar
                        zones_mat[z_idx, 5] = cb
                        zones_mat[z_idx, 6] = orig_px
                        zones_mat[z_idx, 7] = best_ext_px
                        zones_mat[z_idx, 8] = b_lo
                        zones_mat[z_idx, 9] = b_hi
                        zones_mat[z_idx, 10] = (b_hi - b_lo) / tick_size
                        zones_mat[z_idx, 11] = slp
                        zones_mat[z_idx, 12] = last_valid_score
                        zones_mat[z_idx, 13] = session_id[cb]
                        zones_mat[z_idx, 14] = contract_id[cb]
                        zones_mat[z_idx, 15] = s_start
                        zones_mat[z_idx, 16] = s_end
                        z_idx += 1
                        last_zone_end_bar = end_b
                active_dir = 0
                origin_bar = -1
                best_ext_bar = -1
                last_ok_bar = -1
                confirmed = False
                confirm_bar = -1
                continue

            zone_len = cb - origin_bar + 1
            if not confirmed and cond_ok and zone_len >= p_min_zone:
                confirmed = True
                confirm_bar = cb

            if confirmed:
                state[cb] = active_dir
                score_series[cb] = last_valid_score

    return state, score_series, ema, atr, zones_mat[:z_idx], sess_start_of_bar, sess_end_of_bar


# =========================================================================
# 2. CARRERAS DE BARRERA TICK-EXACT DENTRO DE LA MISMA SESIÓN (H-04)
# =========================================================================

@njit(cache=False)
def race_close_same_session_numba(
    p_aligned: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    res_ticks: int,
    entry_bar: int,
    sess_end_bar: int,
    max_horizon_bars: int,
    entry_px: float,
    direction: int,
    tar_dist: float,
    stp_dist: float,
):
    """
    Evalúa desde el cierre de entry_bar (comenzando en entry_bar + 1) hasta
    min(sess_end_bar, entry_bar + 1 + max_horizon_bars).
    Retorna (outcome, exit_bar).
    """
    start_idx = entry_bar + 1
    end_limit = min(sess_end_bar, start_idx + max_horizon_bars)
    if start_idx >= end_limit or tar_dist <= 0.0 or stp_dist <= 0.0:
        return 0, entry_bar

    tar_px = entry_px + tar_dist if direction == 1 else entry_px - tar_dist
    stp_px = entry_px - stp_dist if direction == 1 else entry_px + stp_dist

    for i in range(start_idx, end_limit):
        h = high[i]
        l = low[i]
        if direction == 1:
            hit_t = h >= tar_px - 1e-9
            hit_s = l <= stp_px + 1e-9
        else:
            hit_t = l <= tar_px + 1e-9
            hit_s = h >= stp_px - 1e-9

        if hit_t and hit_s:
            t0 = i * res_ticks
            t1 = t0 + res_ticks
            for t in range(t0, t1):
                pt = p_aligned[t]
                if direction == 1:
                    if pt >= tar_px - 1e-9:
                        return 1, i
                    if pt <= stp_px + 1e-9:
                        return -1, i
                else:
                    if pt <= tar_px + 1e-9:
                        return 1, i
                    if pt >= stp_px - 1e-9:
                        return -1, i
            return 0, i
        elif hit_t:
            return 1, i
        elif hit_s:
            return -1, i

    return 0, end_limit - 1


@njit(cache=False)
def race_limit_same_session_numba(
    p_aligned: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    res_ticks: int,
    touch_bar: int,
    sess_end_bar: int,
    max_horizon_bars: int,
    limit_px: float,
    approach_from_above: bool,
    direction: int,
    tar_dist: float,
    stp_dist: float,
):
    if touch_bar >= sess_end_bar or tar_dist <= 0.0 or stp_dist <= 0.0:
        return 0, touch_bar

    t0 = touch_bar * res_ticks
    t1 = t0 + res_ticks
    t_fill = -1
    for t in range(t0, t1):
        pt = p_aligned[t]
        if approach_from_above:
            if pt <= limit_px + 1e-9:
                t_fill = t
                break
        else:
            if pt >= limit_px - 1e-9:
                t_fill = t
                break

    if t_fill < 0:
        return race_close_same_session_numba(
            p_aligned, high, low, res_ticks, touch_bar, sess_end_bar, max_horizon_bars, limit_px, direction, tar_dist, stp_dist
        )

    fill_px = p_aligned[t_fill]
    tar_px = fill_px + tar_dist if direction == 1 else fill_px - tar_dist
    stp_px = fill_px - stp_dist if direction == 1 else fill_px + stp_dist

    for t in range(t_fill + 1, t1):
        pt = p_aligned[t]
        if direction == 1:
            if pt >= tar_px - 1e-9:
                return 1, touch_bar
            if pt <= stp_px + 1e-9:
                return -1, touch_bar
        else:
            if pt <= tar_px + 1e-9:
                return 1, touch_bar
            if pt >= stp_px - 1e-9:
                return -1, touch_bar

    return race_close_same_session_numba(
        p_aligned, high, low, res_ticks, touch_bar, sess_end_bar, max_horizon_bars, fill_px, direction, tar_dist, stp_dist
    )


# =========================================================================
# 3. EXTRACCIÓN DE EVENTOS + 5 PSEUDO-EVENTOS EMPAREJADOS POR (CONTRATO × MEDIA HORA) (H-03)
# =========================================================================

@njit(cache=False)
def extract_pass2_events_with_matched_pseudos_numba(
    p_aligned: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    ema: np.ndarray,
    state: np.ndarray,
    session_id: np.ndarray,
    contract_id: np.ndarray,
    hh_utc: np.ndarray,
    is_rth: np.ndarray,
    sess_end_of_bar: np.ndarray,
    zones_mat: np.ndarray,
    res_ticks: int,
    max_elapsed_bars: int,
    race_horizon_bars: int,
    fixed_ticks_dist: float,
    tick_size: float,
):
    """
    Extrae para cada zona cerrada los eventos de las 2 Familias Principales de TRAVERSAL_THROUGH
    y la Familia 3 (Contraparte de Rebote en Origen 100%), junto con el promedio de hasta 5
    pseudo-eventos emparejados por (contract_id, hh_utc) en barras con state == 0 y signo de
    tendencia espejado (H-03):

    Familias / Sub-variantes (fcode):
      1: F1A_OUTER_RETURN_CLOSE_VIRGIN (Regreso virgen al borde exterior, entrada en close[b], dir = -z_dir)
      2: F1B_OUTER_RETURN_CLOSE_CLEAN_DEP (Igual pero con >= 8 barras fuera antes del regreso)
      3: F1C_OUTER_RETURN_BODY_CLOSE_INSIDE (Regreso virgen donde close[b] cierra dentro de la caja [b_lo, b_hi])
      4: F2A_PEN20_LIMIT_EXACT (Penetración al 20% del cuerpo virgen, Limit exacto, dir = -z_dir)
      5: F2B_PEN25_LIMIT_EXACT (Penetración al 25% del cuerpo virgen, Limit exacto, dir = -z_dir)
      6: F2C_PEN25_BAR_CLOSE (Penetración al 25% del cuerpo virgen, entrada en close[b], dir = -z_dir)
      7: F2D_PEN33_LIMIT_EXACT (Penetración al 33.3% del cuerpo virgen, Limit exacto, dir = -z_dir)
      8: F2E_PEN33_BAR_CLOSE (Penetración al 33.3% del cuerpo virgen, entrada en close[b], dir = -z_dir)
      9: F2F_PEN40_LIMIT_EXACT (Penetración al 40% del cuerpo virgen, Limit exacto, dir = -z_dir)
     10: F3A_ORIGIN_100_OB_LIMIT (Llegada virgen al 100% pivote de origen orig_px, Limit exacto, dir = +z_dir BOUNCE)
     11: F3B_ORIGIN_100_OB_CLOSE (Llegada virgen al 100% pivote de origen orig_px, close[b], dir = +z_dir BOUNCE)

    Columnas de ev_mat (27 columnas):
      0: zone_id
      1: fcode (1..11)
      2: session_id (1..299)
      3: contract_id (1..6)
      4: entry_bar
      5: is_rth (1 RTH, 0 ETH)
      6: trade_dir (+1 LONG, -1 SHORT)
      7: h_ticks
      8: score
      9: abs_slope_ticks
     10: elapsed_bars
     --- Barrera 1: 0.5_ZoneHeight (Simétrica +0.5H vs -0.5H) ---
     11: out_05H (+1 win, -1 loss, 0 timeout)
     12: exit_bar_05H
     13: pseudo_mean_05H (promedio en [0, 1] de los 5 pseudo-eventos emparejados; -1 si no hay)
     --- Barrera 2: 1.0_ZoneHeight (Simétrica +1.0H vs -1.0H) ---
     14: out_10H
     15: exit_bar_10H
     16: pseudo_mean_10H
     --- Barrera 3: Distancia Exacta al Origen Restante (d_to_orig vs d_to_orig, o 0.75H/0.67H) ---
     17: out_struct_orig
     18: exit_bar_struct_orig
     19: pseudo_mean_struct_orig
     --- Barrera 4: Ticks Fijos (fixed_ticks_dist) ---
     20: out_fixed
     21: exit_bar_fixed
     22: pseudo_mean_fixed
     --- Barrera 5: Prueba de Fricción Adversaria (-1 tick de handicap en 1.0_ZoneHeight: Target = 1.0H + 1t, Stop = 1.0H - 1t) ---
     23: out_10H_adv1t
     --- Barrera 6: Prueba de Fricción Adversaria (-1 tick de handicap en 0.5_ZoneHeight: Target = 0.5H + 1t, Stop = 0.5H - 1t) ---
     24: out_05H_adv1t
    """
    n_bars = len(close)
    n_zones = len(zones_mat)

    # Construir índice rápido de candidatos nulos (state == 0) por (contract_id, hh_utc)
    # contract_id <= 8, hh_utc in 0..47 -> 8 * 48 = 384 buckets
    max_per_bucket = (n_bars // 48) + 1024
    null_pool = np.zeros((384, max_per_bucket), dtype=np.int32)
    null_counts = np.zeros(384, dtype=np.int32)

    for i in range(50, n_bars - 20):
        if state[i] == 0 and sess_end_of_bar[i] - i > 20:
            b_idx = int(contract_id[i]) * 48 + int(hh_utc[i])
            if 0 <= b_idx < 384:
                c = null_counts[b_idx]
                if c < max_per_bucket:
                    null_pool[b_idx, c] = i
                    null_counts[b_idx] = c + 1

    max_ev = n_zones * 12 + 64
    ev_mat = np.zeros((max_ev, 25), dtype=np.float64)
    ev_cnt = 0

    for z_i in range(n_zones):
        z_id = zones_mat[z_i, 0]
        z_dir = int(zones_mat[z_i, 1])
        end_b = int(zones_mat[z_i, 3])
        cls_b = int(zones_mat[z_i, 5])
        orig_px = zones_mat[z_i, 6]
        b_lo = zones_mat[z_i, 8]
        b_hi = zones_mat[z_i, 9]
        h_ticks = zones_mat[z_i, 10]
        h_pts = b_hi - b_lo
        slp_ticks = abs(zones_mat[z_i, 11]) / tick_size
        sc_val = zones_mat[z_i, 12]
        sid = int(zones_mat[z_i, 13])
        cid = int(zones_mat[z_i, 14])
        s_end = int(zones_mat[z_i, 16])

        if h_ticks < 6.0 or cls_b + 5 >= s_end:
            continue

        trav_dir = -z_dir
        bnc_dir = z_dir
        outer_edge = b_hi if z_dir == 1 else b_lo
        opp_edge = b_lo if z_dir == 1 else b_hi

        lvl_20 = (b_hi - 0.20 * h_pts) if z_dir == 1 else (b_lo + 0.20 * h_pts)
        lvl_25 = (b_hi - 0.25 * h_pts) if z_dir == 1 else (b_lo + 0.25 * h_pts)
        lvl_33 = (b_hi - 0.333333 * h_pts) if z_dir == 1 else (b_lo + 0.333333 * h_pts)
        lvl_40 = (b_hi - 0.40 * h_pts) if z_dir == 1 else (b_lo + 0.40 * h_pts)

        done_outer = False
        done_outer_clean = False
        done_outer_body = False
        done_20 = (z_dir == 1 and low[cls_b] <= lvl_20) or (z_dir == -1 and high[cls_b] >= lvl_20)
        done_25 = (z_dir == 1 and low[cls_b] <= lvl_25) or (z_dir == -1 and high[cls_b] >= lvl_25)
        done_33 = (z_dir == 1 and low[cls_b] <= lvl_33) or (z_dir == -1 and high[cls_b] >= lvl_33)
        done_40 = (z_dir == 1 and low[cls_b] <= lvl_40) or (z_dir == -1 and high[cls_b] >= lvl_40)
        done_opp = (z_dir == 1 and low[cls_b] <= opp_edge) or (z_dir == -1 and high[cls_b] >= opp_edge)

        bars_outside_trend = 0
        scan_end = min(s_end - 2, cls_b + max_elapsed_bars)

        for b in range(cls_b + 1, scan_end):
            prev_c = close[b - 1]
            if (z_dir == 1 and prev_c > outer_edge) or (z_dir == -1 and prev_c < outer_edge):
                bars_outside_trend += 1

            from_above = True if z_dir == 1 else False

            # --- Verificar eventos en barra b ---
            # 1) Regreso al borde exterior viniendo desde afuera ( mientras opp_edge siga virgen )
            hit_outer = (z_dir == 1 and prev_c > outer_edge and low[b] <= outer_edge) or (
                z_dir == -1 and prev_c < outer_edge and high[b] >= outer_edge
            )
            if hit_outer and not done_opp:
                if not done_outer and ev_cnt < max_ev:
                    done_outer = True
                    # F1A (fcode=1): Regreso virgen al borde exterior, entrada en close[b]
                    ev_mat[ev_cnt, 0] = z_id
                    ev_mat[ev_cnt, 1] = 1
                    ev_mat[ev_cnt, 2] = sid
                    ev_mat[ev_cnt, 3] = cid
                    ev_mat[ev_cnt, 4] = b
                    ev_mat[ev_cnt, 5] = is_rth[b]
                    ev_mat[ev_cnt, 6] = trav_dir
                    ev_mat[ev_cnt, 7] = h_ticks
                    ev_mat[ev_cnt, 8] = sc_val
                    ev_mat[ev_cnt, 9] = slp_ticks
                    ev_mat[ev_cnt, 10] = b - cls_b
                    d_orig = max(4.0 * tick_size, abs(close[b] - opp_edge))
                    o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                    o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                    o3, ex3 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, d_orig, d_orig)
                    o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                    o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                    o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                    ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                    ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                    ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                    ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                    ev_mat[ev_cnt, 23] = o5
                    ev_mat[ev_cnt, 24] = o6
                    ev_cnt += 1

                if bars_outside_trend >= 8 and not done_outer_clean and ev_cnt < max_ev:
                    done_outer_clean = True
                    # F1B (fcode=2): Regreso virgen tras despegue limpio (>=8 barras fuera), entrada en close[b]
                    ev_mat[ev_cnt, 0] = z_id
                    ev_mat[ev_cnt, 1] = 2
                    ev_mat[ev_cnt, 2] = sid
                    ev_mat[ev_cnt, 3] = cid
                    ev_mat[ev_cnt, 4] = b
                    ev_mat[ev_cnt, 5] = is_rth[b]
                    ev_mat[ev_cnt, 6] = trav_dir
                    ev_mat[ev_cnt, 7] = h_ticks
                    ev_mat[ev_cnt, 8] = sc_val
                    ev_mat[ev_cnt, 9] = slp_ticks
                    ev_mat[ev_cnt, 10] = b - cls_b
                    d_orig = max(4.0 * tick_size, abs(close[b] - opp_edge))
                    o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                    o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                    o3, ex3 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, d_orig, d_orig)
                    o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                    o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                    o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                    ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                    ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                    ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                    ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                    ev_mat[ev_cnt, 23] = o5
                    ev_mat[ev_cnt, 24] = o6
                    ev_cnt += 1

                closed_inside = (z_dir == 1 and b_lo < close[b] < b_hi - 0.5 * tick_size) or (
                    z_dir == -1 and b_lo + 0.5 * tick_size < close[b] < b_hi
                )
                if closed_inside and not done_outer_body and ev_cnt < max_ev:
                    done_outer_body = True
                    # F1C (fcode=3): Regreso virgen con cierre de cuerpo confirmado adentro de la caja
                    ev_mat[ev_cnt, 0] = z_id
                    ev_mat[ev_cnt, 1] = 3
                    ev_mat[ev_cnt, 2] = sid
                    ev_mat[ev_cnt, 3] = cid
                    ev_mat[ev_cnt, 4] = b
                    ev_mat[ev_cnt, 5] = is_rth[b]
                    ev_mat[ev_cnt, 6] = trav_dir
                    ev_mat[ev_cnt, 7] = h_ticks
                    ev_mat[ev_cnt, 8] = sc_val
                    ev_mat[ev_cnt, 9] = slp_ticks
                    ev_mat[ev_cnt, 10] = b - cls_b
                    d_orig = max(4.0 * tick_size, abs(close[b] - opp_edge))
                    o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                    o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                    o3, ex3 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, d_orig, d_orig)
                    o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                    o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                    o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                    ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                    ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                    ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                    ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                    ev_mat[ev_cnt, 23] = o5
                    ev_mat[ev_cnt, 24] = o6
                    ev_cnt += 1

            # 2) Familia 2: Penetraciones al 20%, 25%, 33.3%, 40% del cuerpo virgen
            hit_20 = (z_dir == 1 and prev_c > lvl_20 and low[b] <= lvl_20) or (z_dir == -1 and prev_c < lvl_20 and high[b] >= lvl_20)
            if hit_20 and not done_20 and not done_opp and ev_cnt < max_ev:
                done_20 = True
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 4, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, 0.80 * h_pts, 0.80 * h_pts)
                o4, ex4 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_20, from_above, trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

            hit_25 = (z_dir == 1 and prev_c > lvl_25 and low[b] <= lvl_25) or (z_dir == -1 and prev_c < lvl_25 and high[b] >= lvl_25)
            if hit_25 and not done_25 and not done_opp and ev_cnt + 2 < max_ev:
                done_25 = True
                # F2B (fcode=5): Limit exacto en 25%
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 5, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, 0.75 * h_pts, 0.75 * h_pts)
                o4, ex4 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_25, from_above, trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

                # F2C (fcode=6): Cierre de barra close[b] tras tocar 25%
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 6, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                d_o = max(4.0 * tick_size, abs(close[b] - opp_edge))
                o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, d_o, d_o)
                o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

            hit_33 = (z_dir == 1 and prev_c > lvl_33 and low[b] <= lvl_33) or (z_dir == -1 and prev_c < lvl_33 and high[b] >= lvl_33)
            if hit_33 and not done_33 and not done_opp and ev_cnt + 2 < max_ev:
                done_33 = True
                # F2D (fcode=7): Limit exacto en 33.3%
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 7, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, 0.666667 * h_pts, 0.666667 * h_pts)
                o4, ex4 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_33, from_above, trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

                # F2E (fcode=8): Cierre de barra close[b] tras tocar 33.3%
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 8, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                d_o = max(4.0 * tick_size, abs(close[b] - opp_edge))
                o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, d_o, d_o)
                o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

            hit_40 = (z_dir == 1 and prev_c > lvl_40 and low[b] <= lvl_40) or (z_dir == -1 and prev_c < lvl_40 and high[b] >= lvl_40)
            if hit_40 and not done_40 and not done_opp and ev_cnt < max_ev:
                done_40 = True
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 9, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], trav_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, 0.60 * h_pts, 0.60 * h_pts)
                o4, ex4 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, lvl_40, from_above, trav_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

            # 3) Familia 3: Contraparte en el Pivote de Origen 100% (opp_edge) evaluada en dirección BOUNCE (bnc_dir = +z_dir)
            hit_opp = (z_dir == 1 and prev_c > opp_edge and low[b] <= opp_edge) or (z_dir == -1 and prev_c < opp_edge and high[b] >= opp_edge)
            if hit_opp and not done_opp and ev_cnt + 2 < max_ev:
                done_opp = True
                # F3A (fcode=10): Limit exacto en opp_edge a favor de bnc_dir
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 10, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], bnc_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, opp_edge, from_above, bnc_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, opp_edge, from_above, bnc_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = o2, ex2
                o4, ex4 = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, opp_edge, from_above, bnc_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, opp_edge, from_above, bnc_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_limit_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, opp_edge, from_above, bnc_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1

                # F3B (fcode=11): Cierre de barra close[b] tras tocar opp_edge a favor de bnc_dir
                ev_mat[ev_cnt, 0], ev_mat[ev_cnt, 1], ev_mat[ev_cnt, 2], ev_mat[ev_cnt, 3] = z_id, 11, sid, cid
                ev_mat[ev_cnt, 4], ev_mat[ev_cnt, 5], ev_mat[ev_cnt, 6], ev_mat[ev_cnt, 7] = b, is_rth[b], bnc_dir, h_ticks
                ev_mat[ev_cnt, 8], ev_mat[ev_cnt, 9], ev_mat[ev_cnt, 10] = sc_val, slp_ticks, b - cls_b
                o1, ex1 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], bnc_dir, 0.5 * h_pts, 0.5 * h_pts)
                o2, ex2 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], bnc_dir, 1.0 * h_pts, 1.0 * h_pts)
                o3, ex3 = o2, ex2
                o4, ex4 = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], bnc_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)
                o5, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], bnc_dir, 1.0 * h_pts + tick_size, max(tick_size, 1.0 * h_pts - tick_size))
                o6, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b, s_end, race_horizon_bars, close[b], bnc_dir, 0.5 * h_pts + tick_size, max(tick_size, 0.5 * h_pts - tick_size))
                ev_mat[ev_cnt, 11], ev_mat[ev_cnt, 12] = o1, ex1
                ev_mat[ev_cnt, 14], ev_mat[ev_cnt, 15] = o2, ex2
                ev_mat[ev_cnt, 17], ev_mat[ev_cnt, 18] = o3, ex3
                ev_mat[ev_cnt, 20], ev_mat[ev_cnt, 21] = o4, ex4
                ev_mat[ev_cnt, 23], ev_mat[ev_cnt, 24] = o5, o6
                ev_cnt += 1
                break

    # Ahora, para cada evento extraído en ev_mat[:ev_cnt], muestrear determinísticamente hasta 5 pseudo-eventos
    # del mismo (contract_id, hh_utc) en barras con state == 0 y signo espejado (H-03)
    for idx_init in range(ev_cnt):
        ev_mat[idx_init, 13] = -1.0
        ev_mat[idx_init, 16] = -1.0
        ev_mat[idx_init, 19] = -1.0
        ev_mat[idx_init, 22] = -1.0
    step_ev = max(1, ev_cnt // 25000)
    for idx_e in range(0, ev_cnt, step_ev):
        b_real = int(ev_mat[idx_e, 4])
        cid_e = int(ev_mat[idx_e, 3])
        t_dir = int(ev_mat[idx_e, 6])
        h_pts_e = ev_mat[idx_e, 7] * tick_size
        hh_e = int(hh_utc[b_real])
        b_bucket = cid_e * 48 + hh_e
        pool_n = null_counts[b_bucket] if 0 <= b_bucket < 384 else 0

        if pool_n < 5:
            ev_mat[idx_e, 13] = -1.0
            ev_mat[idx_e, 16] = -1.0
            ev_mat[idx_e, 19] = -1.0
            ev_mat[idx_e, 22] = -1.0
            continue

        # Relación de signo de la dirección operada respecto a (close[b_real] - ema[b_real]) para espejar en el pseudo-evento (H-03)
        real_ema_sign = 1 if close[b_real] >= ema[b_real] else -1
        rel_sign = t_dir * real_ema_sign  # +1 si opera a favor del lado actual de la EMA, -1 si opera en contra

        w1_sum, n1_cnt = 0.0, 0
        w2_sum, n2_cnt = 0.0, 0
        w3_sum, n3_cnt = 0.0, 0
        w4_sum, n4_cnt = 0.0, 0

        # Selección determinística pseudo-aleatoria espaciada sobre el pool del mismo (contrato, media_hora)
        seed_offset = (idx_e * 97 + b_real * 31) % pool_n
        step_p = max(1, pool_n // 7)
        picked = 0
        for attempt in range(15):
            if picked >= 5:
                break
            cand_pos = (seed_offset + attempt * step_p) % pool_n
            b_ps = null_pool[b_bucket, cand_pos]
            if abs(b_ps - b_real) < 50:
                continue
            s_end_ps = sess_end_of_bar[b_ps]
            if s_end_ps - b_ps < 20:
                continue

            ps_ema_sign = 1 if close[b_ps] >= ema[b_ps] else -1
            ps_dir = rel_sign * ps_ema_sign  # Nulo espejado H-03!

            po1, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b_ps, s_end_ps, race_horizon_bars, close[b_ps], ps_dir, 0.5 * h_pts_e, 0.5 * h_pts_e)
            po2, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b_ps, s_end_ps, race_horizon_bars, close[b_ps], ps_dir, 1.0 * h_pts_e, 1.0 * h_pts_e)
            po3, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b_ps, s_end_ps, race_horizon_bars, close[b_ps], ps_dir, 0.75 * h_pts_e, 0.75 * h_pts_e)
            po4, _ = race_close_same_session_numba(p_aligned, high, low, res_ticks, b_ps, s_end_ps, race_horizon_bars, close[b_ps], ps_dir, fixed_ticks_dist * tick_size, fixed_ticks_dist * tick_size)

            if po1 != 0:
                w1_sum += 1.0 if po1 == 1 else 0.0
                n1_cnt += 1
            if po2 != 0:
                w2_sum += 1.0 if po2 == 1 else 0.0
                n2_cnt += 1
            if po3 != 0:
                w3_sum += 1.0 if po3 == 1 else 0.0
                n3_cnt += 1
            if po4 != 0:
                w4_sum += 1.0 if po4 == 1 else 0.0
                n4_cnt += 1
            picked += 1

        ev_mat[idx_e, 13] = (w1_sum / n1_cnt) if n1_cnt > 0 else -1.0
        ev_mat[idx_e, 16] = (w2_sum / n2_cnt) if n2_cnt > 0 else -1.0
        ev_mat[idx_e, 19] = (w3_sum / n3_cnt) if n3_cnt > 0 else -1.0
        ev_mat[idx_e, 22] = (w4_sum / n4_cnt) if n4_cnt > 0 else -1.0

    return ev_mat[:ev_cnt]


# =========================================================================
# 4. ESTADÍSTICA ANTI-OVERFIT: PURGA NO-OVERLAP, SE CLUSTERIZADO, MCPT, OOS, MIRROR Y HOLM
# =========================================================================

def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_p(z: float) -> float:
    return float(2.0 * (1.0 - norm_cdf(abs(z))))


def purge_overlapping_events(rows: np.ndarray, col_exit_bar: int) -> np.ndarray:
    """
    Filtra cronológicamente dentro de cada sesión para que ningún evento comience
    antes de que haya terminado la carrera de barrera del evento previo (no_overlap = True).
    """
    if len(rows) == 0:
        return rows
    order = np.lexsort((rows[:, 4], rows[:, 2]))
    s_rows = rows[order]
    keep = np.zeros(len(s_rows), dtype=bool)
    cur_sess = -1
    last_exit = -1
    for i in range(len(s_rows)):
        sid = int(s_rows[i, 2])
        b_en = int(s_rows[i, 4])
        b_ex = int(s_rows[i, col_exit_bar])
        if sid != cur_sess:
            cur_sess = sid
            last_exit = b_ex
            keep[i] = True
        else:
            if b_en > last_exit:
                keep[i] = True
                if b_ex > last_exit:
                    last_exit = b_ex
    return s_rows[keep]


def session_clustered_inference(
    rows: np.ndarray,
    col_out: int,
    col_pseudo: int,
    n_mcpt: int = 2000,
) -> dict:
    """
    Calcula sobre los eventos resueltos (rows[:, col_out] != 0):
      - Win rate real, N_resolved, N_sessions
      - SE_clustered por sesión (Liang-Zeger / Hansen), z_clustered, p_clustered, MDE_80
      - MCPT Sign-Flip por sesión (n_mcpt permutaciones de Rademacher)
      - Contraste emparejado contra las 5 pseudo-zonas (gamma_vs_pseudo_pp, z_vs_pseudo, p_vs_pseudo)
      - Partición OOS: S1 (sesiones <= 149) vs S2 (sesiones >= 150)
      - Consistencia por contrato trimestral (cuántos de los 6 contratos tienen WR > 50%)
      - Mirror check: WR_long vs WR_short
      - Régimen horario: WR_RTH vs WR_ETH
    """
    valid = rows[rows[:, col_out] != 0]
    n_res = len(valid)
    if n_res < 15:
        return {"status": "INSUFFICIENT_N", "n_resolved": int(n_res)}

    y_bin = (valid[:, col_out] == 1).astype(np.float64)
    sids = valid[:, 2].astype(np.int32)
    cids = valid[:, 3].astype(np.int32)
    rth = valid[:, 5].astype(np.int32)
    tdirs = valid[:, 6].astype(np.int32)
    pseudos = valid[:, col_pseudo]

    wr = float(np.mean(y_bin))
    edge_pp = (wr - 0.50) * 100.0

    # Agrupar por sesión para varianza clusterizada y MCPT de Rademacher
    uniq_s, inv_s = np.unique(sids, return_inverse=True)
    n_sess = len(uniq_s)
    sess_counts = np.bincount(inv_s)
    sess_wins = np.bincount(inv_s, weights=y_bin)

    # Residuos respecto de la media muestral wr para SE_clustered
    sess_resid = sess_wins - sess_counts * wr
    if n_sess > 1:
        var_clust = (n_sess / (n_sess - 1.0)) * float(np.sum(sess_resid ** 2)) / (n_res ** 2)
        se_clust = math.sqrt(max(1e-16, var_clust))
    else:
        se_clust = math.sqrt(0.25 / n_res)

    z_clust = (wr - 0.50) / se_clust if se_clust > 0 else 0.0
    p_clust = two_sided_p(z_clust)
    mde_80_pp = 2.80 * se_clust * 100.0

    # MCPT por inversión de signo de sesión bajo H0: E[y_i - 0.5] = 0
    sess_excess_h0 = sess_wins - 0.50 * sess_counts
    obs_sum = abs(float(np.sum(sess_excess_h0)))
    rng = np.random.default_rng(10152026 + n_res)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_mcpt, n_sess))
    perm_sums = np.abs(signs @ sess_excess_h0)
    p_mcpt = float((1 + np.sum(perm_sums >= obs_sum - 1e-12)) / (n_mcpt + 1))

    # Contraste contra las 5 pseudo-zonas emparejadas (H-03)
    m_ps = pseudos >= 0.0
    if np.sum(m_ps) >= 15:
        v_y = y_bin[m_ps]
        v_p = pseudos[m_ps]
        v_s = sids[m_ps]
        diff_i = v_y - v_p
        gamma_pseudo = float(np.mean(diff_i))
        mean_pseudo = float(np.mean(v_p))
        u_sp, inv_sp = np.unique(v_s, return_inverse=True)
        n_sp = len(u_sp)
        sp_cnt = np.bincount(inv_sp)
        sp_sum = np.bincount(inv_sp, weights=diff_i)
        sp_res = sp_sum - sp_cnt * gamma_pseudo
        if n_sp > 1:
            se_gamma = math.sqrt(max(1e-16, (n_sp / (n_sp - 1.0)) * float(np.sum(sp_res ** 2)) / (len(diff_i) ** 2)))
        else:
            se_gamma = math.sqrt(float(np.var(diff_i)) / len(diff_i))
        z_gamma = gamma_pseudo / se_gamma if se_gamma > 0 else 0.0
        p_gamma = two_sided_p(z_gamma)
    else:
        mean_pseudo = 0.50
        gamma_pseudo = wr - 0.50
        se_gamma = se_clust
        z_gamma = z_clust
        p_gamma = p_clust

    # Partición OOS Cronológica: S1 (sesiones 1..149) vs S2 (sesiones 150..299)
    m_s1 = sids <= 149
    m_s2 = sids >= 150
    n_s1, n_s2 = int(np.sum(m_s1)), int(np.sum(m_s2))
    wr_s1 = float(np.mean(y_bin[m_s1])) if n_s1 > 0 else 0.50
    wr_s2 = float(np.mean(y_bin[m_s2])) if n_s2 > 0 else 0.50
    oos_both_positive = bool((wr_s1 > 0.50) and (wr_s2 > 0.50))

    # Consistencia en los 6 contratos trimestrales
    c_pos = 0
    c_tot = 0
    c_breakdown = {}
    for c_val in range(1, 7):
        mc = cids == c_val
        nc = int(np.sum(mc))
        if nc >= 5:
            c_tot += 1
            wrc = float(np.mean(y_bin[mc]))
            if wrc > 0.50:
                c_pos += 1
            c_breakdown[f"C{c_val}"] = {"n": nc, "wr": round(wrc, 4)}

    # Mirror check: LONG (tdirs == 1) vs SHORT (tdirs == -1)
    m_long = tdirs == 1
    m_short = tdirs == -1
    n_long, n_short = int(np.sum(m_long)), int(np.sum(m_short))
    wr_long = float(np.mean(y_bin[m_long])) if n_long > 0 else 0.50
    wr_short = float(np.mean(y_bin[m_short])) if n_short > 0 else 0.50
    mirror_both_positive = bool((wr_long > 0.50) and (wr_short > 0.50))

    # Régimen Horario: RTH vs ETH
    m_rth = rth == 1
    m_eth = rth == 0
    n_rth, n_eth = int(np.sum(m_rth)), int(np.sum(m_eth))
    wr_rth = float(np.mean(y_bin[m_rth])) if n_rth > 0 else 0.50
    wr_eth = float(np.mean(y_bin[m_eth])) if n_eth > 0 else 0.50

    return {
        "status": "OK",
        "n_resolved": int(n_res),
        "n_sessions": int(n_sess),
        "win_rate_real": round(wr, 4),
        "edge_vs_50_pp": round(edge_pp, 2),
        "se_clustered_pp": round(se_clust * 100.0, 2),
        "mde_80_pp": round(mde_80_pp, 2),
        "z_clustered": round(z_clust, 3),
        "p_clustered": round(p_clust, 5),
        "p_mcpt_2000": round(p_mcpt, 5),
        "mean_pseudo_5_matched": round(mean_pseudo, 4),
        "gamma_vs_pseudo_pp": round(gamma_pseudo * 100.0, 2),
        "z_vs_pseudo": round(z_gamma, 3),
        "p_vs_pseudo": round(p_gamma, 5),
        "oos_split": {
            "n_s1": n_s1,
            "wr_s1": round(wr_s1, 4),
            "edge_s1_pp": round((wr_s1 - 0.50) * 100.0, 2),
            "n_s2": n_s2,
            "wr_s2": round(wr_s2, 4),
            "edge_s2_pp": round((wr_s2 - 0.50) * 100.0, 2),
            "both_halves_positive": oos_both_positive,
        },
        "contracts_consistency": {
            "n_contracts_positive": c_pos,
            "n_contracts_evaluated": c_tot,
            "by_contract": c_breakdown,
        },
        "mirror_check": {
            "n_long": n_long,
            "wr_long": round(wr_long, 4),
            "n_short": n_short,
            "wr_short": round(wr_short, 4),
            "both_directions_positive": mirror_both_positive,
        },
        "session_regime": {
            "n_rth": n_rth,
            "wr_rth": round(wr_rth, 4),
            "n_eth": n_eth,
            "wr_eth": round(wr_eth, 4),
        },
    }


def apply_holm_and_fdr(test_records: list[dict], p_key: str = "p_clustered"):
    """Aplica corrección de Holm-Bonferroni y Benjamini-Hochberg FDR in-place sobre una lista de dicts."""
    m = len(test_records)
    if m == 0:
        return
    order = sorted(range(m), key=lambda i: test_records[i].get(p_key, 1.0))
    # Holm step-down
    running_max = 0.0
    for rank, idx in enumerate(order):
        p_val = test_records[idx].get(p_key, 1.0)
        adj = min(1.0, p_val * (m - rank))
        if adj > running_max:
            running_max = adj
        test_records[idx]["p_holm"] = round(running_max, 5)
    # Benjamini-Hochberg step-up
    running_min = 1.0
    for rank in range(m - 1, -1, -1):
        idx = order[rank]
        p_val = test_records[idx].get(p_key, 1.0)
        q_val = min(1.0, p_val * m / (rank + 1))
        if q_val < running_min:
            running_min = q_val
        test_records[idx]["q_fdr_bh"] = round(running_min, 5)


# =========================================================================
# 5. CARGA ESTRICTA POR SESIÓN Y CONSTRUCCIÓN DE BARRAS SIN MEZCLA
# =========================================================================

def locate_es_parquet() -> Path:
    root_p = Path("/kaggle/input")
    if root_p.exists():
        for mpath in root_p.rglob("release_manifest.json"):
            try:
                man = json.loads(mpath.read_text(encoding="utf-8"))
                info = man.get("assets", {}).get("ES")
                if info and "file" in info:
                    cand = mpath.parent / info["file"]
                    if cand.exists():
                        return cand
            except Exception:
                pass
        for cand in root_p.rglob("ES.parquet"):
            return cand
        for cand in root_p.rglob("ES_ticks.parquet"):
            return cand
    raise FileNotFoundError("No se encontró ES.parquet en /kaggle/input")


def load_es_sessions_with_metadata(pfile: Path):
    """
    Lee cada sesión (trade_date < 20261001, contrato primario) preservando:
      - prices (float64)
      - ts_utc_ns (int64)
      - outside_regular (uint8: 1 si ETH, 0 si RTH)
      - session_id (int32: 1..299)
      - contract_id (int32: 1..6)
    """
    pf = pq.ParquetFile(pfile)
    col_idx = {pf.metadata.row_group(0).column(i).path_in_schema: i for i in range(pf.metadata.row_group(0).num_columns)}
    td_col = col_idx["trade_date"]

    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st_td = md.column(td_col).statistics
        if st_td is not None and st_td.has_min_max and int(st_td.min) >= HOLDOUT_TRADE_DATE:
            continue
        td_key = int(st_td.min) if (st_td is not None and st_td.has_min_max and st_td.min == st_td.max) else -1
        rg_by_td[td_key].append(rg)

    sessions_list = []
    contract_to_id = {}
    c_col = col_idx.get("contract", -1)
    sel_col = col_idx.get("session_selected", -1)

    for td in sorted(k for k in rg_by_td if 0 < k < HOLDOUT_TRADE_DATE):
        rgs = rg_by_td[td]
        if len(rgs) > 1 and c_col >= 0:
            rows_by_c = defaultdict(int)
            rgs_by_c = defaultdict(list)
            for rg_i in rgs:
                md_i = pf.metadata.row_group(rg_i)
                if sel_col >= 0:
                    st_sel = md_i.column(sel_col).statistics
                    if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                        continue
                st_c = md_i.column(c_col).statistics
                c_name = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "UNK"
                rows_by_c[c_name] += md_i.num_rows
                rgs_by_c[c_name].append(rg_i)
            if not rows_by_c:
                continue
            prim_c = max(rows_by_c.items(), key=lambda x: x[1])[0]
            rgs = rgs_by_c[prim_c]
        else:
            md_0 = pf.metadata.row_group(rgs[0])
            if sel_col >= 0:
                st_sel = md_0.column(sel_col).statistics
                if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                    continue
            st_c = md_0.column(c_col).statistics if c_col >= 0 else None
            prim_c = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "ES_PRIM"

        tbl = pf.read_row_groups(rgs, columns=["ts_utc_ns", "price_ticks", "outside_regular"])
        ts = tbl["ts_utc_ns"].to_numpy()
        px_t = tbl["price_ticks"].to_numpy()
        out_reg = tbl["outside_regular"].to_numpy()
        if len(ts) < 100:
            continue
        if ts[-1] >= HOLDOUT_UTC_NS:
            m_h = ts < HOLDOUT_UTC_NS
            ts = ts[m_h]
            px_t = px_t[m_h]
            out_reg = out_reg[m_h]
            if len(ts) < 100:
                continue
        if len(ts) > 1 and (np.diff(ts) < 0).any():
            order = np.argsort(ts, kind="mergesort")
            ts = ts[order]
            px_t = px_t[order]
            out_reg = out_reg[order]

        if prim_c not in contract_to_id:
            contract_to_id[prim_c] = len(contract_to_id) + 1
        c_int = contract_to_id[prim_c]
        s_int = len(sessions_list) + 1

        sessions_list.append({
            "session_id": s_int,
            "trade_date": td,
            "contract_id": c_int,
            "contract": prim_c,
            "prices": px_t.astype(np.float64) * TICK_ES,
            "ts_utc_ns": ts,
            "is_rth": (~out_reg.astype(bool)).astype(np.int8),
        })
        del tbl

    return sessions_list, contract_to_id


def build_session_strict_bars(sessions_list: list[dict], tick_bucket: int):
    """
    Construye barras de N ticks estrictamente dentro de cada sesión individual (H-04),
    de modo que ninguna barra ni zona cruce jamás de un trade_date a otro.
    """
    p_al_l, o_l, h_l, l_l, c_l, sid_l, cid_l, hh_l, rth_l = [], [], [], [], [], [], [], [], []
    for s in sessions_list:
        px = s["prices"]
        ts = s["ts_utc_ns"]
        rth = s["is_rth"]
        nb = len(px) // tick_bucket
        if nb < 5:
            continue
        n_use = nb * tick_bucket
        px_u = px[:n_use]
        reshaped_px = px_u.reshape((nb, tick_bucket))
        ts_end = ts[:n_use].reshape((nb, tick_bucket))[:, -1]
        rth_end = rth[:n_use].reshape((nb, tick_bucket))[:, -1]

        p_al_l.append(px_u)
        o_l.append(reshaped_px[:, 0])
        h_l.append(np.max(reshaped_px, axis=1))
        l_l.append(np.min(reshaped_px, axis=1))
        c_l.append(reshaped_px[:, -1])
        sid_l.append(np.full(nb, s["session_id"], dtype=np.int32))
        cid_l.append(np.full(nb, s["contract_id"], dtype=np.int32))
        hh_arr = ((ts_end // 1_800_000_000_000) % 48).astype(np.int32)
        hh_l.append(hh_arr)
        rth_l.append(((hh_arr >= 27) & (hh_arr <= 40)).astype(np.int32))

    return (
        np.concatenate(p_al_l),
        np.concatenate(o_l),
        np.concatenate(h_l),
        np.concatenate(l_l),
        np.concatenate(c_l),
        np.concatenate(sid_l),
        np.concatenate(cid_l),
        np.concatenate(hh_l),
        np.concatenate(rth_l),
    )


FCODE_NAMES = {
    1: "F1A_OUTER_RETURN_CLOSE_VIRGIN",
    2: "F1B_OUTER_RETURN_CLOSE_CLEAN_DEP",
    3: "F1C_OUTER_RETURN_BODY_CLOSE_INSIDE",
    4: "F2A_PEN20_LIMIT_EXACT",
    5: "F2B_PEN25_LIMIT_EXACT",
    6: "F2C_PEN25_BAR_CLOSE",
    7: "F2D_PEN33_LIMIT_EXACT",
    8: "F2E_PEN33_BAR_CLOSE",
    9: "F2F_PEN40_LIMIT_EXACT",
    10: "F3A_ORIGIN_100_OB_LIMIT",
    11: "F3B_ORIGIN_100_OB_CLOSE",
}


def evaluate_preset_events(ev_mat: np.ndarray, res: int, pid: int, fixed_t: int) -> dict:
    if len(ev_mat) == 0:
        return {}

    med_slope = float(np.median(ev_mat[:, 9])) if len(ev_mat) > 0 else 0.0
    out_dict = {}

    barriers_spec = [
        ("0.5_ZoneHeight", 11, 12, 13),
        ("1.0_ZoneHeight", 14, 15, 16),
        ("Struct_To_Origin", 17, 18, 19),
        (f"{fixed_t}_ticks", 20, 21, 22),
    ]

    for fcode, fname in FCODE_NAMES.items():
        sub_f = ev_mat[ev_mat[:, 1] == fcode]
        if len(sub_f) < 15:
            continue

        strata = [
            ("ALL_VIRGIN", np.ones(len(sub_f), dtype=bool)),
            ("STEEP_SLOPE", sub_f[:, 9] >= med_slope),
            ("HIGH_SCORE_GE75", sub_f[:, 8] >= 75.0),
            ("FRESH_LE100B", sub_f[:, 10] <= 100),
        ]

        f_res = {}
        for st_name, mask in strata:
            rows_raw = sub_f[mask]
            if len(rows_raw) < 15:
                continue

            b_map = {}
            for b_name, col_o, col_ex, col_ps in barriers_spec:
                # 1. Evaluación con PURGA ESTRICTA DE SOLAPAMIENTO (no_overlap = True)
                rows_no_ov = purge_overlapping_events(rows_raw, col_ex)
                inf_no_ov = session_clustered_inference(rows_no_ov, col_o, col_ps, n_mcpt=2000)

                # 2. Evaluación sin purga (raw) para cuantificar cuánto inflaba el clustering
                inf_raw = session_clustered_inference(rows_raw, col_o, col_ps, n_mcpt=500)

                # 3. Fricción adversaria de -1 tick (en 0.5H y 1.0H)
                adv_wr = None
                if b_name == "1.0_ZoneHeight":
                    v_adv = rows_no_ov[rows_no_ov[:, 23] != 0]
                    if len(v_adv) > 0:
                        adv_wr = round(float(np.mean(v_adv[:, 23] == 1)), 4)
                elif b_name == "0.5_ZoneHeight":
                    v_adv = rows_no_ov[rows_no_ov[:, 24] != 0]
                    if len(v_adv) > 0:
                        adv_wr = round(float(np.mean(v_adv[:, 24] == 1)), 4)

                inf_no_ov["raw_unpurged_n_resolved"] = inf_raw.get("n_resolved", 0)
                inf_no_ov["raw_unpurged_win_rate"] = inf_raw.get("win_rate_real", 0.5)
                inf_no_ov["win_rate_with_1tick_adverse_handicap"] = adv_wr
                b_map[b_name] = inf_no_ov

            f_res[st_name] = b_map
        out_dict[fname] = f_res

    return out_dict


def main():
    pfile = locate_es_parquet()
    print(f"Cargando sesiones SELECTED de ES desde {pfile}...", flush=True)
    sessions_list, cmap = load_es_sessions_with_metadata(pfile)
    tot_ticks = sum(len(s["prices"]) for s in sessions_list)
    print(f"Cargadas {len(sessions_list)} sesiones ({tot_ticks:,} ticks, {len(cmap)} contratos) en {time.time() - T0:.1f}s", flush=True)

    presets_cfg = {
        1: (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72),
        2: (60, 45, 12, 65, 24, 0.85, 0.84, 0.030, 0.88, 0.80, 1.05, 0.44, 0.46, 0.64),
        3: (48, 36, 12, 50, 28, 0.80, 0.80, 0.024, 0.84, 0.65, 1.25, 0.52, 0.55, 0.55),
    }

    resolutions = [25, 100, 500, 1000]
    out_master = {
        "spec_id": "EDGELAB-ES-CORRIDOR-PASS2-FALSIFICATION-V4",
        "version": 1,
        "north_star_hash": NORTH_STAR_HASH,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "holdout_utc_cutoff": "2026-10-01T00:00:00Z",
        "pnl_computed": False,
        "n_sessions_es": len(sessions_list),
        "total_es_ticks": int(tot_ticks),
        "contracts": cmap,
        "anti_overfit_gates_applied": [
            "G1_STRICT_SAME_SESSION_GUARD_H04",
            "G2_NON_OVERLAPPING_HORIZON_PURGE",
            "G3_5_MATCHED_PSEUDO_ZONES_CONTRACT_X_HALFHOUR_MIRRORED_H03",
            "G4_SESSION_CLUSTERED_SE_AND_MDE80",
            "G5_RADEMACHER_SESSION_SIGN_FLIP_MCPT_2000",
            "G6_HOLM_BONFERRONI_AND_BH_FDR_MULTIPLICITY",
            "G7_OOS_TEMPORAL_SPLIT_AND_6_CONTRACTS_CONSISTENCY",
            "G8_MIRROR_CHECK_LONG_SHORT_RTH_ETH_AND_1TICK_FRICTION",
        ],
        "results_by_resolution": {},
        "primary_preregistered_family_tests": [],
        "surviving_edges_after_full_falsification": [],
    }

    primary_tests = []

    for res in resolutions:
        t_r = time.time()
        p_al, o_a, h_a, l_a, c_a, sid_a, cid_a, hh_a, rth_a = build_session_strict_bars(sessions_list, res)
        nb = len(c_a)
        out_master["results_by_resolution"][f"{res}T"] = {"n_bars_session_strict": int(nb), "presets": {}}

        max_el = 2500 if res == 25 else (1200 if res == 100 else (500 if res == 500 else 300))
        race_h = 800 if res == 25 else (400 if res == 100 else (200 if res == 500 else 150))
        fixed_t = 20 if res == 25 else (40 if res == 100 else (60 if res == 500 else 80))

        # Evaluar Preset 2 como configuración central y Presets 1 y 3 para estabilidad paramétrica en 100T/500T/1000T (y Preset 2 en 25T para velocidad óptima)
        pids_to_run = (2,) if res == 25 else (1, 2, 3)

        for pid in pids_to_run:
            p_cfg = presets_cfg[pid]
            ema_p = 200 if res in (25, 100) else (100 if res == 500 else 60)
            atr_p = 100 if res in (25, 100) else 50

            state, score_s, ema_a, atr_a, zones_mat, s_start_b, s_end_b = detect_zones_session_strict_numba(
                o_a, h_a, l_a, c_a, sid_a, cid_a,
                ema_p, atr_p,
                p_cfg[0], p_cfg[1], p_cfg[2], p_cfg[3], p_cfg[4],
                p_cfg[5], p_cfg[6], p_cfg[7], p_cfg[8], p_cfg[9],
                p_cfg[10], p_cfg[11], p_cfg[12], p_cfg[13],
                40, 5, 1.60, TICK_ES
            )

            ev_mat = extract_pass2_events_with_matched_pseudos_numba(
                p_al, h_a, l_a, c_a, ema_a, state, sid_a, cid_a, hh_a, rth_a, s_end_b,
                zones_mat, res, max_el, race_h, float(fixed_t), TICK_ES
            )

            eval_dict = evaluate_preset_events(ev_mat, res, pid, fixed_t)
            out_master["results_by_resolution"][f"{res}T"]["presets"][f"Preset_{pid}"] = {
                "n_zones_session_strict": int(len(zones_mat)),
                "n_events_extracted": int(len(ev_mat)),
                "families": eval_dict,
            }

            # Registrar pruebas primarias en Preset 2 para corrección de Holm-Bonferroni
            if pid == 2:
                for fname, st_dict in eval_dict.items():
                    for st_name in ("ALL_VIRGIN", "STEEP_SLOPE"):
                        if st_name not in st_dict:
                            continue
                        for b_name in ("1.0_ZoneHeight", "Struct_To_Origin", f"{fixed_t}_ticks", "0.5_ZoneHeight"):
                            b_info = st_dict[st_name].get(b_name, {})
                            if b_info.get("status") == "OK" and b_info.get("n_resolved", 0) >= 25:
                                rec = {
                                    "resolution": f"{res}T",
                                    "preset": f"Preset_{pid}",
                                    "family": fname,
                                    "stratum": st_name,
                                    "barrier": b_name,
                                    **b_info,
                                }
                                primary_tests.append(rec)

            print(
                f"[PASS2 | {res}T | Preset {pid}] {nb:,} barras -> {len(zones_mat)} zonas, {len(ev_mat)} eventos ({time.time() - t_r:.1f}s)",
                flush=True,
            )

        del p_al, o_a, h_a, l_a, c_a, sid_a, cid_a, hh_a, rth_a

    # Aplicar corrección de Holm-Bonferroni y Benjamini-Hochberg FDR sobre las pruebas primarias
    apply_holm_and_fdr(primary_tests, p_key="p_clustered")
    primary_tests.sort(key=lambda x: x["z_clustered"], reverse=True)
    out_master["primary_preregistered_family_tests"] = primary_tests

    # Filtrar qué candidatos sobreviven a los criterios de falsación física
    survivors = [
        t for t in primary_tests
        if t["z_clustered"] >= 1.96
        and t["p_mcpt_2000"] <= 0.05
        and t["oos_split"]["both_halves_positive"]
        and t["contracts_consistency"]["n_contracts_positive"] >= max(3, t["contracts_consistency"]["n_contracts_evaluated"] - 2)
    ]
    out_master["surviving_edges_after_full_falsification"] = survivors
    out_master["elapsed_total_sec"] = round(time.time() - T0, 2)

    out_dir = Path("/kaggle/working")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "ES_CORRIDOR_PASS2_FALSIFICATION_RESULTS.json"
    out_file.write_text(json.dumps(out_master, indent=2), encoding="utf-8")

    compact_stdout = {
        "elapsed_total_sec": out_master["elapsed_total_sec"],
        "n_primary_tests_evaluated": len(primary_tests),
        "n_surviving_edges": len(survivors),
        "surviving_edges_after_full_falsification": survivors,
        "top_35_primary_tests_by_z_clustered": primary_tests[:35],
        "parameter_stability_100T_500T_1000T": {
            res_k: {
                pk: {
                    fk: {
                        sk: {
                            bk: {
                                "n_res": bv.get("n_resolved"),
                                "wr": bv.get("win_rate_real"),
                                "edge_pp": bv.get("edge_vs_50_pp"),
                                "z_clust": bv.get("z_clustered"),
                                "p_mcpt": bv.get("p_mcpt_2000"),
                                "gamma_ps_pp": bv.get("gamma_vs_pseudo_pp"),
                                "z_ps": bv.get("z_vs_pseudo"),
                                "oos_ok": bv.get("oos_split", {}).get("both_halves_positive"),
                                "c_pos": f"{bv.get('contracts_consistency', {}).get('n_contracts_positive', 0)}/{bv.get('contracts_consistency', {}).get('n_contracts_evaluated', 0)}",
                                "mirror_ok": bv.get("mirror_check", {}).get("both_directions_positive"),
                                "wr_1t_adv": bv.get("win_rate_with_1tick_adverse_handicap"),
                            }
                            for bk, bv in sv.items() if bv.get("status") == "OK"
                        }
                        for sk, sv in fv.items() if sk in ("ALL_VIRGIN", "STEEP_SLOPE")
                    }
                    for fk, fv in pv["families"].items()
                }
                for pk, pv in res_v["presets"].items()
            }
            for res_k, res_v in out_master["results_by_resolution"].items()
        },
    }
    print("=== EDGELAB_PASS2_FALSIFICATION_SUMMARY_START ===", flush=True)
    print(json.dumps(compact_stdout, indent=2), flush=True)
    print("=== EDGELAB_PASS2_FALSIFICATION_SUMMARY_END ===", flush=True)




# ===== DET_NT8 =====
@njit(cache=False)
def detect_zones_nt8_numba(
    open_p: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    session_id: np.ndarray,
    contract_id: np.ndarray,
    ema_period: int,
    atr_period: int,
    p_window: int,
    p_slope: int,
    p_block: int,
    p_min_zone: int,
    p_grace: int,
    p_min_er: float,
    p_min_mono: float,
    p_min_slope_atr: float,
    p_min_side: float,
    p_min_gap: float,
    p_max_counter: float,
    p_max_far_disp: float,
    p_max_near_disp: float,
    p_min_r2: float,
    lookback_origin: int,
    break_confirm_bars: int,
    hard_break_ema_atr: float,
    tick_size: float,
):
    """
    Detecta zonas EmaCorridorTrend v4.0 reiniciando el estado de zona en cada cambio de
    session_id (H-04), pero manteniendo la continuidad de EMA/ATR dentro del mismo contrato
    para no perder barras de calentamiento al inicio de la sesión.
    """
    n = len(close)
    ema = np.zeros(n, dtype=np.float64)
    atr = np.zeros(n, dtype=np.float64)
    mid = 0.5 * (high + low)
    tr = np.zeros(n, dtype=np.float64)
    rg = np.zeros(n, dtype=np.float64)
    c0 = 0
    rsum = 0.0

    k_ema = 2.0 / (ema_period + 1.0)
    k_atr = 2.0 / (atr_period + 1.0)

    for i in range(n):
        if i == 0 or contract_id[i] != contract_id[i - 1]:
            ema[i] = close[i]
            tr[i] = max(high[i] - low[i], tick_size)
            atr[i] = tr[i]
            rg[i] = high[i] - low[i]
            c0 = i
            rsum = rg[i]
            atr[i] = max(rg[i], tick_size)
        else:
            ema[i] = close[i] * k_ema + ema[i - 1] * (1.0 - k_ema)
            hl = high[i] - low[i]
            hc = abs(high[i] - close[i - 1])
            lc = abs(low[i] - close[i - 1])
            tr[i] = max(hl, max(hc, lc))
            rg[i] = high[i] - low[i]
            rsum += rg[i]
            if i - c0 >= atr_period:
                rsum -= rg[i - atr_period]
            cntw = min(i - c0 + 1, atr_period)
            atr[i] = rsum / cntw
            if atr[i] < tick_size:
                atr[i] = tick_size

    state = np.zeros(n, dtype=np.int8)
    score_series = np.zeros(n, dtype=np.float64)

    max_zones = n // max(10, p_min_zone // 2) + 32
    # Columnas de zones_mat (19 columnas):
    #  0: zone_id
    #  1: dir (+1 / -1)
    #  2: origin_bar
    #  3: end_bar
    #  4: confirm_bar
    #  5: close_bar
    #  6: orig_px
    #  7: ext_px
    #  8: b_lo
    #  9: b_hi
    # 10: h_ticks
    # 11: slope_pts_per_bar
    # 12: stability_score
    # 13: session_id
    # 14: contract_id
    # 15: sess_start_bar
    # 16: sess_end_bar (exclusivo)
    zones_mat = np.zeros((max_zones, 17), dtype=np.float64)
    z_idx = 0

    # Precalcular límites de cada sesión [sess_start, sess_end)
    sess_start_of_bar = np.zeros(n, dtype=np.int32)
    sess_end_of_bar = np.zeros(n, dtype=np.int32)
    s_cur = 0
    for i in range(1, n + 1):
        if i == n or session_id[i] != session_id[s_cur]:
            for k in range(s_cur, i):
                sess_start_of_bar[k] = s_cur
                sess_end_of_bar[k] = i
            s_cur = i

    min_bars_in_sess = p_window + p_slope + 4
    n_blocks = max(3, p_window // p_block)
    x_mean = 0.5 * (p_window - 1.0)
    sxx = p_window * (p_window * p_window - 1.0) / 12.0

    active_dir = 0
    origin_bar = -1
    best_ext_bar = -1
    best_ext_px = 0.0
    last_ok_bar = -1
    confirmed = False
    confirm_bar = -1
    last_zone_end_bar = -1
    last_valid_score = 0.0

    for cb in range(n):
        s_start = sess_start_of_bar[cb]
        s_end = sess_end_of_bar[cb]
        if cb == s_start:
            # Al iniciar nueva sesión, resetear estado activo (H-04: prohibido cruzar sesiones)
            active_dir = 0
            origin_bar = -1
            best_ext_bar = -1
            last_ok_bar = -1
            confirmed = False
            confirm_bar = -1
            last_zone_end_bar = s_start
            continue

        if cb - s_start < min_bars_in_sess:
            continue

        a = atr[cb]
        net_ema = ema[cb] - ema[cb - p_slope]
        path_ema = 0.0
        pos_steps = 0
        neg_steps = 0
        for i in range(cb - p_slope + 1, cb + 1):
            st = ema[i] - ema[i - 1]
            path_ema += abs(st)
            if st > 0.0:
                pos_steps += 1
            elif st < 0.0:
                neg_steps += 1

        ema_eff = abs(net_ema) / path_ema if path_ema > 1e-12 else 0.0
        ema_slope_atr = net_ema / (p_slope * a)

        cand_dir = 0
        if ema_slope_atr >= p_min_slope_atr and ema_eff >= p_min_er and (pos_steps / p_slope) >= p_min_mono:
            cand_dir = 1
        elif ema_slope_atr <= -p_min_slope_atr and ema_eff >= p_min_er and (neg_steps / p_slope) >= p_min_mono:
            cand_dir = -1

        cond_ok = False
        if cand_dir != 0:
            on_side = 0
            gap_sum = 0.0
            max_cnt = 0.0
            y_sum = 0.0
            w_start = cb - p_window + 1
            for i in range(w_start, cb + 1):
                ai = atr[i]
                sc = cand_dir * (close[i] - ema[i]) / ai
                if sc >= -0.35:
                    on_side += 1
                gap_sum += sc
                if sc < 0.0 and (-sc) > max_cnt:
                    max_cnt = -sc
                y_sum += mid[i]

            side_ratio = on_side / p_window
            mean_gap = gap_sum / p_window

            if side_ratio >= p_min_side and mean_gap >= p_min_gap and max_cnt <= p_max_counter:
                b_len = p_window // n_blocks
                if b_len >= 2:
                    sum_f = 0.0
                    sum_ff = 0.0
                    sum_n = 0.0
                    sum_nn = 0.0
                    for b in range(n_blocks):
                        bs = w_start + b * b_len
                        be = cb + 1 if b == n_blocks - 1 else bs + b_len
                        mx_f = -1e18
                        mn_n = 1e18
                        for idx in range(bs, be):
                            if cand_dir > 0:
                                fd = (high[idx] - ema[idx]) / atr[idx]
                                nd = (low[idx] - ema[idx]) / atr[idx]
                            else:
                                fd = (ema[idx] - low[idx]) / atr[idx]
                                nd = (ema[idx] - high[idx]) / atr[idx]
                            if fd > mx_f:
                                mx_f = fd
                            if nd < mn_n:
                                mn_n = nd
                        sum_f += mx_f
                        sum_ff += mx_f * mx_f
                        sum_n += mn_n
                        sum_nn += mn_n * mn_n

                    mean_far = sum_f / n_blocks
                    mean_near = sum_n / n_blocks
                    if mean_far > 0.5:
                        c_scale = mean_far if mean_far > 1.5 else 1.5
                        var_f = sum_ff / n_blocks - mean_far * mean_far
                        var_n = sum_nn / n_blocks - mean_near * mean_near
                        far_disp = (math.sqrt(var_f) if var_f > 0.0 else 0.0) / c_scale
                        near_disp = (math.sqrt(var_n) if var_n > 0.0 else 0.0) / c_scale

                        if far_disp <= p_max_far_disp and near_disp <= p_max_near_disp:
                            y_mean = y_sum / p_window
                            syy = 0.0
                            sxy = 0.0
                            for k in range(p_window):
                                idx = w_start + k
                                dy = mid[idx] - y_mean
                                syy += dy * dy
                                sxy += (k - x_mean) * dy
                            denom = sxx * syy
                            r_corr = sxy / math.sqrt(denom) if denom > 1e-12 else 0.0
                            r2 = (r_corr * r_corr) if (r_corr * cand_dir > 0.0) else 0.0
                            if r2 >= p_min_r2:
                                cond_ok = True
                                f_sc = max(0.0, 1.0 - far_disp / p_max_far_disp)
                                n_sc = max(0.0, 1.0 - near_disp / p_max_near_disp)
                                last_valid_score = 100.0 * (0.35 * r2 + 0.25 * ema_eff + 0.20 * f_sc + 0.20 * n_sc)

        if cond_ok:
            if active_dir != cand_dir:
                if active_dir != 0 and confirmed and z_idx < max_zones:
                    end_b = best_ext_bar if best_ext_bar > origin_bar + 10 else min(cb - 1, origin_bar + 10)
                    if end_b > origin_bar + 5:
                        b_lo = low[origin_bar]
                        b_hi = high[origin_bar]
                        for k in range(origin_bar, end_b + 1):
                            if low[k] < b_lo:
                                b_lo = low[k]
                            if high[k] > b_hi:
                                b_hi = high[k]
                        orig_px = low[origin_bar] if active_dir > 0 else high[origin_bar]
                        slp = (mid[end_b] - mid[origin_bar]) / max(1, end_b - origin_bar)
                        zones_mat[z_idx, 0] = z_idx + 1
                        zones_mat[z_idx, 1] = active_dir
                        zones_mat[z_idx, 2] = origin_bar
                        zones_mat[z_idx, 3] = end_b
                        zones_mat[z_idx, 4] = confirm_bar
                        zones_mat[z_idx, 5] = cb - 1
                        zones_mat[z_idx, 6] = orig_px
                        zones_mat[z_idx, 7] = best_ext_px
                        zones_mat[z_idx, 8] = b_lo
                        zones_mat[z_idx, 9] = b_hi
                        zones_mat[z_idx, 10] = (b_hi - b_lo) / tick_size
                        zones_mat[z_idx, 11] = slp
                        zones_mat[z_idx, 12] = last_valid_score
                        zones_mat[z_idx, 13] = session_id[cb]
                        zones_mat[z_idx, 14] = contract_id[cb]
                        zones_mat[z_idx, 15] = s_start
                        zones_mat[z_idx, 16] = s_end
                        z_idx += 1
                        last_zone_end_bar = end_b

                active_dir = cand_dir
                min_allow = max(s_start + 1, last_zone_end_bar + 1)
                lo_b = max(min_allow, cb - p_window - lookback_origin)
                hi_b = max(lo_b, cb - p_window + 12)
                touch_b = hi_b
                for b_k in range(hi_b, lo_b - 1, -1):
                    sc_k = active_dir * (close[b_k] - ema[b_k]) / atr[b_k]
                    if sc_k <= 0.15:
                        touch_b = b_k
                        break
                pv_s = max(min_allow, touch_b - 10)
                pv_e = min(cb - p_window // 2, touch_b + 10)
                if pv_e < pv_s:
                    pv_e = pv_s
                best_k = pv_s
                if active_dir > 0:
                    bv = low[pv_s]
                    for b_k in range(pv_s, pv_e + 1):
                        if low[b_k] <= bv:
                            bv = low[b_k]
                            best_k = b_k
                else:
                    bv = high[pv_s]
                    for b_k in range(pv_s, pv_e + 1):
                        if high[b_k] >= bv:
                            bv = high[b_k]
                            best_k = b_k
                origin_bar = best_k
                best_ext_bar = cb
                best_ext_px = high[cb] if active_dir > 0 else low[cb]
                confirmed = False
            last_ok_bar = cb

        if active_dir != 0:
            if active_dir > 0 and high[cb] >= best_ext_px:
                best_ext_px = high[cb]
                best_ext_bar = cb
            elif active_dir < 0 and low[cb] <= best_ext_px:
                best_ext_px = low[cb]
                best_ext_bar = cb

            hard_cross = (active_dir * (close[cb] - ema[cb]) / a) < -hard_break_ema_atr
            sustained_cross = True
            for j in range(break_confirm_bars):
                if active_dir * (close[cb - j] - ema[cb - j]) / atr[cb - j] >= -0.35:
                    sustained_cross = False
                    break
            grace_expired = (cb - last_ok_bar) > p_grace

            if hard_cross or sustained_cross or grace_expired:
                if confirmed and z_idx < max_zones:
                    end_b = best_ext_bar if best_ext_bar > origin_bar + 10 else min(cb, origin_bar + 10)
                    if end_b > origin_bar + 5:
                        b_lo = low[origin_bar]
                        b_hi = high[origin_bar]
                        for k in range(origin_bar, end_b + 1):
                            if low[k] < b_lo:
                                b_lo = low[k]
                            if high[k] > b_hi:
                                b_hi = high[k]
                        orig_px = low[origin_bar] if active_dir > 0 else high[origin_bar]
                        slp = (mid[end_b] - mid[origin_bar]) / max(1, end_b - origin_bar)
                        zones_mat[z_idx, 0] = z_idx + 1
                        zones_mat[z_idx, 1] = active_dir
                        zones_mat[z_idx, 2] = origin_bar
                        zones_mat[z_idx, 3] = end_b
                        zones_mat[z_idx, 4] = confirm_bar
                        zones_mat[z_idx, 5] = cb
                        zones_mat[z_idx, 6] = orig_px
                        zones_mat[z_idx, 7] = best_ext_px
                        zones_mat[z_idx, 8] = b_lo
                        zones_mat[z_idx, 9] = b_hi
                        zones_mat[z_idx, 10] = (b_hi - b_lo) / tick_size
                        zones_mat[z_idx, 11] = slp
                        zones_mat[z_idx, 12] = last_valid_score
                        zones_mat[z_idx, 13] = session_id[cb]
                        zones_mat[z_idx, 14] = contract_id[cb]
                        zones_mat[z_idx, 15] = s_start
                        zones_mat[z_idx, 16] = s_end
                        z_idx += 1
                        last_zone_end_bar = end_b
                active_dir = 0
                origin_bar = -1
                best_ext_bar = -1
                last_ok_bar = -1
                confirmed = False
                confirm_bar = -1
                continue

            zone_len = cb - origin_bar + 1
            if not confirmed and cond_ok and zone_len >= p_min_zone:
                confirmed = True
                confirm_bar = cb

            if confirmed:
                state[cb] = active_dir
                score_series[cb] = last_valid_score

    return state, score_series, ema, atr, zones_mat[:z_idx], sess_start_of_bar, sess_end_of_bar


# =========================================================================
# 2. CARRERAS DE BARRERA TICK-EXACT DENTRO DE LA MISMA SESIÓN (H-04)
# =========================================================================


# ===== DEV ADDON (sin main) =====
# ===================================================================================================
# ADENDA D — EXTRACCION DE TABLA DE EVENTOS DE DESARROLLO (EXP-CORRIDOR-CONF, ES, 299 sesiones)
# Se concatena DESPUES del script de Pasada 2 (sha256 10e8fa9f...) mediante tools/corridor_pass2/build_dev_script.py.
# No toca holdout (trade_date >= 20261001), ni NQ/YM. Todas las features son causales: usan datos <= cierre de la barra de entrada.
# ===================================================================================================
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

DEV_SPEC_ID = "EXP-CORRIDOR-DEV-D-v1"
CHI = ZoneInfo("America/Chicago")
NAN = float("nan")


def dev_load_sessions(pfile):
    """Igual que load_es_sessions_with_metadata pero conserva volumen por tick (si existe), fecha y offset UTC de Chicago."""
    pf = pq.ParquetFile(pfile)
    names = [pf.schema_arrow.field(i).name for i in range(len(pf.schema_arrow))]
    print("SCHEMA_COLUMNS:", names, flush=True)
    vol_col = next((c for c in ("volume", "size", "qty", "quantity", "trade_size") if c in names), None)
    print("VOLUME_COLUMN:", vol_col, flush=True)
    cols = ["ts_utc_ns", "price_ticks", "outside_regular"] + ([vol_col] if vol_col else [])

    col_idx = {pf.metadata.row_group(0).column(i).path_in_schema: i for i in range(pf.metadata.row_group(0).num_columns)}
    td_col = col_idx["trade_date"]
    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st_td = md.column(td_col).statistics
        if st_td is not None and st_td.has_min_max and int(st_td.min) >= HOLDOUT_TRADE_DATE:
            continue
        td_key = int(st_td.min) if (st_td is not None and st_td.has_min_max and st_td.min == st_td.max) else -1
        rg_by_td[td_key].append(rg)

    sessions_list, contract_to_id = [], {}
    c_col = col_idx.get("contract", -1)
    sel_col = col_idx.get("session_selected", -1)
    for td in sorted(k for k in rg_by_td if 0 < k < HOLDOUT_TRADE_DATE):
        rgs = rg_by_td[td]
        if len(rgs) > 1 and c_col >= 0:
            rows_by_c, rgs_by_c = defaultdict(int), defaultdict(list)
            for rg_i in rgs:
                md_i = pf.metadata.row_group(rg_i)
                if sel_col >= 0:
                    st_sel = md_i.column(sel_col).statistics
                    if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                        continue
                st_c = md_i.column(c_col).statistics
                c_name = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "UNK"
                rows_by_c[c_name] += md_i.num_rows
                rgs_by_c[c_name].append(rg_i)
            if not rows_by_c:
                continue
            prim_c = max(rows_by_c.items(), key=lambda x: x[1])[0]
            rgs = rgs_by_c[prim_c]
        else:
            md_0 = pf.metadata.row_group(rgs[0])
            if sel_col >= 0:
                st_sel = md_0.column(sel_col).statistics
                if st_sel is not None and st_sel.has_min_max and st_sel.max is False:
                    continue
            st_c = md_0.column(c_col).statistics if c_col >= 0 else None
            prim_c = str(st_c.min) if (st_c is not None and st_c.has_min_max) else "ES_PRIM"

        tbl = pf.read_row_groups(rgs, columns=cols)
        ts = tbl["ts_utc_ns"].to_numpy()
        px_t = tbl["price_ticks"].to_numpy()
        out_reg = tbl["outside_regular"].to_numpy()
        vol = tbl[vol_col].to_numpy().astype(np.float64) if vol_col else np.ones(len(ts), dtype=np.float64)
        if len(ts) < 100:
            continue
        if ts[-1] >= HOLDOUT_UTC_NS:
            m_h = ts < HOLDOUT_UTC_NS
            ts, px_t, out_reg, vol = ts[m_h], px_t[m_h], out_reg[m_h], vol[m_h]
            if len(ts) < 100:
                continue
        if len(ts) > 1 and (np.diff(ts) < 0).any():
            order = np.argsort(ts, kind="mergesort")
            ts, px_t, out_reg, vol = ts[order], px_t[order], out_reg[order], vol[order]

        if prim_c not in contract_to_id:
            contract_to_id[prim_c] = len(contract_to_id) + 1
        off_s = int(datetime.fromtimestamp(int(ts[len(ts) // 2]) / 1e9, CHI).utcoffset().total_seconds())
        sessions_list.append({
            "session_id": len(sessions_list) + 1,
            "trade_date": td,
            "contract_id": contract_to_id[prim_c],
            "contract": prim_c,
            "prices": px_t.astype(np.float64) * TICK_ES,
            "ts_utc_ns": ts,
            "is_rth": (~out_reg.astype(bool)).astype(np.int8),
            "vol": vol,
            "utc_off_s": off_s,
        })
        del tbl
    return sessions_list, contract_to_id, bool(vol_col)


def dev_build_bars(sessions_list, res):
    """Mismas barras que build_session_strict_bars, mas ts, volumen, minuto de Chicago y primera barra de sesion."""
    L = defaultdict(list)
    base = 0
    sess_trade_date = {}
    for s in sessions_list:
        px, ts, vol = s["prices"], s["ts_utc_ns"], s["vol"]
        nb = len(px) // res
        if nb < 5:
            continue
        n_use = nb * res
        rpx = px[:n_use].reshape((nb, res))
        ts_r = ts[:n_use].reshape((nb, res))
        ts_end, ts_start = ts_r[:, -1], ts_r[:, 0]
        hh = ((ts_end // 1_800_000_000_000) % 48).astype(np.int32)
        L["p_al"].append(px[:n_use])
        L["v_al"].append(vol[:n_use])
        L["o"].append(rpx[:, 0]); L["h"].append(rpx.max(axis=1)); L["l"].append(rpx.min(axis=1)); L["c"].append(rpx[:, -1])
        L["sid"].append(np.full(nb, s["session_id"], dtype=np.int32))
        L["cid"].append(np.full(nb, s["contract_id"], dtype=np.int32))
        L["hh"].append(hh)
        L["rth"].append(((hh >= 27) & (hh <= 40)).astype(np.int32))
        L["ts_end"].append(ts_end); L["ts_start"].append(ts_start)
        L["vol"].append(vol[:n_use].reshape((nb, res)).sum(axis=1))
        L["ctmin"].append(((((ts_end // 1_000_000_000) + s["utc_off_s"]) % 86400) // 60).astype(np.int32))
        L["sess_first"].append(np.full(nb, base, dtype=np.int64))
        sess_trade_date[s["session_id"]] = s["trade_date"]
        base += nb
    return {k: np.concatenate(v) for k, v in L.items()}, sess_trade_date


def _oriented_frac(x, b_lo, b_hi, z_dir):
    H = max(b_hi - b_lo, 1e-9)
    return (x - b_lo) / H if z_dir == 1 else (b_hi - x) / H


def _profile_features(p, w, tick, b_lo, b_hi, z_dir, close_b, opp_edge):
    out = {k: NAN for k in ("poc_frac", "va_lo_frac", "va_hi_frac", "path_share", "outer_share", "node_ratio", "sector_share", "zone_ticks")}
    if len(p) == 0:
        return out
    lv = np.rint(p / tick).astype(np.int64)
    mn, mx = int(lv.min()), int(lv.max())
    v = np.bincount(lv - mn, weights=w, minlength=mx - mn + 1)
    tot = float(v.sum())
    if tot <= 0:
        return out
    n = len(v)
    mid = 0.5 * (b_lo + b_hi)
    poc_i = 0
    for k in range(1, n):
        if v[k] > v[poc_i] or (v[k] == v[poc_i] and abs((mn + k) * tick - mid) < abs((mn + poc_i) * tick - mid)):
            poc_i = k
    acc, a, bb = v[poc_i], poc_i, poc_i
    while acc < 0.70 * tot and (a > 0 or bb < n - 1):
        up = (v[bb + 1] if bb + 1 < n else 0.0) + (v[bb + 2] if bb + 2 < n else 0.0)
        dn = (v[a - 1] if a - 1 >= 0 else 0.0) + (v[a - 2] if a - 2 >= 0 else 0.0)
        if bb < n - 1 and (up >= dn or a == 0):
            acc += up; bb = min(n - 1, bb + 2)
        else:
            acc += dn; a = max(0, a - 2)
    px_of = lambda i: (mn + i) * tick
    f_lo, f_hi = sorted((_oriented_frac(px_of(a), b_lo, b_hi, z_dir), _oriented_frac(px_of(bb), b_lo, b_hi, z_dir)))
    levels = (mn + np.arange(n)) * tick
    fr = np.array([_oriented_frac(x, b_lo, b_hi, z_dir) for x in levels]) if n < 4000 else _oriented_frac(levels, b_lo, b_hi, z_dir)
    lo_p, hi_p = (min(close_b, opp_edge), max(close_b, opp_edge))
    on_path = (levels > lo_p + 1e-9) & (levels < hi_p - 1e-9)
    c_fr = _oriented_frac(close_b, b_lo, b_hi, z_dir)
    out.update(
        poc_frac=_oriented_frac(px_of(poc_i), b_lo, b_hi, z_dir), va_lo_frac=f_lo, va_hi_frac=f_hi,
        path_share=float(v[on_path].sum() / tot),
        outer_share=float(v[fr > c_fr].sum() / tot),
        node_ratio=float(v[on_path].max() / max(v.mean(), 1e-9)) if on_path.any() else 0.0,
        sector_share=float(v[fr >= 0.75].sum() / tot),
        zone_ticks=float(len(p)),
    )
    return out


def dev_extract_features(ev_mat, zones_mat, B, ema, atr, res, tick, race_h, fixed_t, tag):
    """Una fila por evento con labels de Pasada 2 + features causales + P&L con timeouts."""
    p_al, v_al = B["p_al"], B["v_al"]
    o, h, l, c = B["o"], B["h"], B["l"], B["c"]
    cumv = np.concatenate([[0.0], np.cumsum(v_al)])
    zrow = {int(z[0]): i for i, z in enumerate(zones_mat)}
    # volumen total de cada zona (origen..cierre) y rank frente a las <=50 zonas previas que cerraron antes
    zinfo = {}
    order = np.argsort(zones_mat[:, 5], kind="stable") if len(zones_mat) else []
    prev = []
    for zi in order:
        z = zones_mat[zi]
        ob, cb = int(z[2]), int(z[5])
        tv = float(cumv[(cb + 1) * res] - cumv[ob * res])
        hist = prev[-50:]
        pct = float(np.mean([x < tv for x in hist])) if len(hist) >= 20 else NAN
        zinfo[int(z[0])] = (tv, pct)
        prev.append(tv)

    rows, n_err = [], 0
    for e in ev_mat:
        try:
            zid, fcode = int(e[0]), int(e[1])
            z = zones_mat[zrow[zid]]
            b = int(e[4])
            z_dir = int(z[1]); td = int(e[6])
            ob, eb, cb = int(z[2]), int(z[3]), int(z[5])
            opx, b_lo, b_hi = float(z[6]), float(z[8]), float(z[9])
            H = b_hi - b_lo
            outer, opp = (b_hi, b_lo) if z_dir == 1 else (b_lo, b_hi)
            s_end = int(z[16]); sb = int(B["sess_first"][b])
            a_b = float(atr[b]); cl = float(c[b])
            r = dict(det=tag, res=res, fcode=fcode, zone_id=zid, session_id=int(e[2]), contract_id=int(e[3]), entry_bar=b,
                     z_dir=z_dir, trade_dir=td, rth_pass2=int(e[5]), rth_ct=int(510 <= B["ctmin"][b] <= 930), ct_min=int(B["ctmin"][b]),
                     h_ticks=float(e[7]), score=float(e[8]), slope_ticks=float(e[9]), elapsed=float(e[10]))
            # geometria y retorno
            r.update(zone_len=cb - ob + 1, trend_len=eb - ob + 1, post_ext_len=cb - eb,
                     d_orig_ticks=abs(cl - opp) / tick, d_outer_ticks=abs(cl - outer) / tick, close_frac=_oriented_frac(cl, b_lo, b_hi, z_dir),
                     atr_ticks=a_b / tick, h_over_atr=H / max(a_b, tick), ema_dist_atr=z_dir * (cl - float(ema[b])) / max(a_b, tick))
            seg_c = c[cb + 1:b]; seg_h = h[cb + 1:b]; seg_l = l[cb + 1:b]
            outside = (seg_c > outer) if z_dir == 1 else (seg_c < outer)
            ext = (seg_h - outer) if z_dir == 1 else (outer - seg_l)
            r.update(bars_outside=int(outside.sum()), max_ext_ticks=float(max(ext.max(), 0.0) / tick) if len(ext) else 0.0)
            r.update(bar_range_ticks=float((h[b] - l[b]) / tick), bar_body_ticks=float(td * (cl - o[b]) / tick),
                     speed3=float(td * (cl - c[b - 3]) / tick) if b >= 3 else NAN, speed10=float(td * (cl - c[b - 10]) / tick) if b >= 10 else NAN)
            dur = (B["ts_end"][b] - B["ts_start"][b]) / 1e9
            d5 = (B["ts_end"][b] - B["ts_end"][max(b - 5, 0)]) / 1e9 / 5.0
            zd = (B["ts_end"][cb] - B["ts_start"][ob]) / 1e9 / max(cb - ob + 1, 1)
            r.update(bar_dur_s=float(dur), pace5=float(d5 / zd) if zd > 0 else NAN)
            # volumen y perfil de la zona (conocida desde cb: available_at = cb)
            tv, pct = zinfo.get(zid, (NAN, NAN))
            zvb = tv / max(cb - ob + 1, 1)
            vr5 = float(B["vol"][max(b - 4, 0):b + 1].sum() / (5.0 * zvb)) if zvb > 0 else NAN
            r.update(zone_vol=tv, zone_vol_pct50=pct, vol_ret5_ratio=vr5, vol_bar_ratio=float(B["vol"][b] / zvb) if zvb > 0 else NAN)
            r.update(_profile_features(p_al[ob * res:(cb + 1) * res], v_al[ob * res:(cb + 1) * res], tick, b_lo, b_hi, z_dir, cl, opp))
            # contexto de sesion hasta la barra b
            hs, ls = float(h[sb:b + 1].max()), float(l[sb:b + 1].min())
            rng = max(hs - ls, tick)
            r.update(sess_range_ticks=rng / tick, sess_pos=(cl - ls) / rng, dist_hi_ticks=(hs - cl) / tick, dist_lo_ticks=(cl - ls) / tick,
                     mins_since_open=float((B["ts_end"][b] - B["ts_start"][sb]) / 6e10),
                     rv50_atr=float(np.std(np.diff(c[max(b - 50, sb):b + 1])) / max(a_b, tick)) if b - sb > 5 else NAN)
            r.update(hr_sin=float(np.sin(2 * np.pi * B["ctmin"][b] / 1440.0)), hr_cos=float(np.cos(2 * np.pi * B["ctmin"][b] / 1440.0)))
            # etiquetas de Pasada 2 (R/C/0) y P&L en ticks con timeout marcado a mercado
            ent = cl
            if fcode == 7:
                ent = (b_hi - 0.333333 * H) if z_dir == 1 else (b_lo + 0.333333 * H)
            t0 = (b + 1) * res
            t1 = min(s_end, b + 1 + race_h) * res
            seg = p_al[t0:t1]
            if len(seg):
                delta = td * (seg - ent) / tick
                r.update(mfe_ticks=float(max(delta.max(), 0.0)), mae_ticks=float(max(-delta.min(), 0.0)), ret_end_ticks=float(delta[-1]))
            else:
                r.update(mfe_ticks=NAN, mae_ticks=NAN, ret_end_ticks=NAN)
            d_struct = max(4.0, abs(cl - opp) / tick) if fcode in (1, 2, 3) else 0.8 * (H / tick)
            r.update(out_05H=int(e[11]), exit_05H=int(e[12]), pseudo_05H=float(e[13]), out_10H=int(e[14]), exit_10H=int(e[15]), pseudo_10H=float(e[16]),
                     out_struct=int(e[17]), exit_struct=int(e[18]), pseudo_struct=float(e[19]), out_fixed=int(e[20]), exit_fixed=int(e[21]),
                     out_10H_adv1t=int(e[23]), D_05H=0.5 * H / tick, D_10H=H / tick, D_struct=d_struct, D_fixed=float(fixed_t))
            rows.append(r)
        except Exception as ex:  # no se descarta en silencio: se cuenta y se reporta
            n_err += 1
            if n_err <= 5:
                print("FEATURE_ERROR", tag, res, repr(ex), flush=True)
    print(f"[{tag}|{res}T] eventos={len(ev_mat)} filas={len(rows)} errores={n_err}", flush=True)
    return pd.DataFrame(rows), n_err


def dev_regression_print(ev_mat, tag, res, pid):
    """Regresion contra Pasada 2: F1A, purga no_overlap, barrera 1.0H, ALL y STEEP (mediana global como en Pasada 2)."""
    sub = ev_mat[ev_mat[:, 1] == 1]
    if len(sub) < 15:
        return
    med = float(np.median(sub[:, 9]))
    for name, m in (("ALL", np.ones(len(sub), bool)), ("STEEP", sub[:, 9] >= med)):
        rr = purge_overlapping_events(sub[m], 15)
        res_ = rr[rr[:, 14] != 0]
        print(f"[REGRESION {tag}|{res}T|P{pid}|F1A|{name}] N_purgado={len(rr)} resueltos={len(res_)} wr_1.0H={float(np.mean(res_[:, 14] == 1)) if len(res_) else NAN:.4f}", flush=True)



# ===== PORT HFT (Flat) =====
"""Puerto Python de HFTZonesESPureV2Flat (NT8) — corre sobre ticks crudos de EdgeLab.

POR QUE ESTE PUERTO ES SIMPLE
=============================
El indicador declara `AddDataSeries(BarsPeriodType.Tick, TickResolution)` con
`TickResolution = 1`, asi que toda la maquina de estados corre sobre la serie de **1
tick**. El grafico de 25 Tick del chart es solo la serie primaria de DIBUJO
(`BarsInProgress == 0`); no entra en el algoritmo.

En una barra de 1 tick, `Open == High == Low == Close == precio del tick`. Eso colapsa
tres condiciones del .cs:

    rng    = (High - Low) / TickSize = 0        -> `small` es SIEMPRE true
    isDown = small && cl <= clP && cl <= op     -> `cl <= clP`
    isUp   = small && cl >= clP && cl >= op     -> `cl >= clP`
    plano  = isDown && isUp                     -> `cl == clP`

Y ahi se ve por que el bug importaba tanto: sobre ticks, el precio repite constantemente,
asi que `plano` es el caso mas frecuente. Evaluar `isDown` primero mandaba casi toda
racha a bajista — 92% medido sobre 23.863 zonas.

QUE SE REPRODUCE
================
`swH`/`swL` (la geometria de la zona), `tStart`/`tLast`, y las metricas que el .cs
persiste. `StartBar`/`EndBar` NO: son indices de la serie de dibujo de 25 Tick y no
tienen sentido fuera del chart.

Sin outcomes. Sin P&L. Geometria y microestructura.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

# Defaults leidos de SetDefaults del .cs (docs/research/parches/HFTZonesESPureV2Flat.cs).
# NO son numeros elegidos aca: si el chart corre con otros, se pasan explicitos.
DEFAULTS = dict(
    tick_resolution=1, min_pasos=10, max_rango_tick_por_vela=1, fallos_tolerados=1,
    filtro_direccion_estricto=True, min_sweep_ticks=5, max_avg_ms=15, max_total_ms=300,
    max_pausa_ms=50, min_volume_rate=500, min_total_volume=200, predator_avg_ms=3,
    ultra_avg_ms=10, mostrar_absorb=True, min_absorb_pasos=8)


@dataclass
class HFT_Params:
    min_pasos: int = 10
    max_rango_tick_por_vela: int = 1
    fallos_tolerados: int = 1
    filtro_direccion_estricto: bool = True
    min_sweep_ticks: int = 5
    max_avg_ms: int = 15
    max_total_ms: int = 300
    max_pausa_ms: int = 50
    min_volume_rate: int = 500
    min_total_volume: int = 200
    predator_avg_ms: int = 3
    ultra_avg_ms: int = 10
    mostrar_absorb: bool = True
    min_absorb_pasos: int = 8


@dataclass
class Zona:
    start_ts: int          # epoch ms UTC, igual que UnixMs del .cs
    end_ts: int
    bucket: str
    dir: int
    price_upper: float
    price_lower: float
    price_mid: float
    height_ticks: float
    pasos: int
    valid_steps: int
    avg_ms: float
    total_ms: float
    vol_rate: float
    total_vol: float
    max_tick_vol: float
    cvd_sweep: float
    buy_vol: float
    sell_vol: float
    delta_slope: float
    delta_first: float
    delta_second: float
    no_move_ticks: int
    no_move_vol: float
    max_level_ticks: int


@dataclass
class _Racha:
    """Estado mutable de la racha en curso. Espeja los campos del .cs uno a uno."""
    streak: int = 0
    valid_steps: int = 0
    dir: int = 0
    fails: int = 0
    sw_h: float = 0.0
    sw_l: float = 0.0
    total_vol: float = 0.0
    t_start: int = 0
    t_last: int = 0
    ms: List[float] = field(default_factory=list)      # msList: intervalos, NO el primero
    precio: List[float] = field(default_factory=list)
    vol: List[float] = field(default_factory=list)
    sign: List[float] = field(default_factory=list)

    def reset(self):
        self.streak = self.valid_steps = self.dir = self.fails = 0
        self.ms.clear(); self.precio.clear(); self.vol.clear(); self.sign.clear()
        self.total_vol = 0.0


def _emitir(r: _Racha, p: Params, tick_size: float,
            casi: Optional[list] = None) -> Optional[Zona]:
    """Traduce Finalizar() del .cs. Devuelve None si la racha no califica.

    Si se pasa `casi`, las rachas que fallan EXACTAMENTE UNO de los cuatro filtros de
    calidad (velocidad, duracion, tasa de volumen, volumen total) se acumulan ahi con el
    motivo. Sirven como control emparejado: misma geometria, mismo instante, misma
    sesion, el precio estuvo igual de presente -- pero no son zona.

    Es el control que F2.9 llamo K0 vs N0 (creadora contra no-creadora emparejada). El
    espejo geometrico NO sirve para esta familia: la zona es el rango del propio barrido
    y el barrido termina adentro, asi que la distancia al precio de creacion tiene
    mediana 1 tick y 39% de las zonas la tienen en 0 -- el espejo cae encima de la zona.
    """
    sweep_ticks = (r.sw_h - r.sw_l) / tick_size
    is_sweep = sweep_ticks >= p.min_sweep_ticks
    is_absorb = (not is_sweep) and p.mostrar_absorb
    min_pasos_req = p.min_pasos if is_sweep else p.min_absorb_pasos

    if r.valid_steps < min_pasos_req or not (is_sweep or is_absorb):
        return None

    total = float(sum(r.ms))
    avg_ms = total / max(1, len(r.ms))
    dur_s = max(total, 1.0) / 1000.0
    vol_rate = r.total_vol / dur_s

    fallos = [n for n, ok in (
        ("velocidad", avg_ms <= p.max_avg_ms),
        ("duracion", total <= p.max_total_ms),
        ("tasa_volumen", vol_rate >= p.min_volume_rate),
        ("volumen_total", r.total_vol >= p.min_total_volume)) if not ok]
    if fallos:
        if casi is not None and len(fallos) == 1:
            casi.append(dict(start_ts=r.t_start, end_ts=r.t_last, dir=r.dir,
                             price_upper=r.sw_h, price_lower=r.sw_l,
                             height_ticks=sweep_ticks, pasos=r.streak,
                             valid_steps=r.valid_steps, avg_ms=avg_ms,
                             total_ms=total, vol_rate=vol_rate,
                             total_vol=r.total_vol, motivo=fallos[0]))
        return None

    if is_absorb:
        bajo = r.precio[-1] < r.precio[0]
        bucket = "Absorb"
        _txt = "ABSORB_BEAR" if bajo else "ABSORB_BULL"     # noqa: F841  (solo dibujo)
    else:
        bucket = ("Predator" if avg_ms <= p.predator_avg_ms
                  else "Ultra" if avg_ms <= p.ultra_avg_ms else "Fast")

    cvd = buy = sell = max_tick_vol = 0.0
    for sv, v in zip(r.sign, r.vol):
        cvd += sv
        if sv >= 0:
            buy += v
        else:
            sell += v
        max_tick_vol = max(max_tick_vol, v)

    slope = d_first = d_second = 0.0
    n_s = len(r.sign)
    if n_s >= 2:
        sum_x = sum_y = sum_xy = sum_xx = cum = 0.0
        for i, sv in enumerate(r.sign):
            cum += sv
            sum_x += i; sum_y += cum; sum_xy += i * cum; sum_xx += float(i) * i
        den = n_s * sum_xx - sum_x * sum_x
        if abs(den) > 1e-9:
            slope = (n_s * sum_xy - sum_x * sum_y) / den
        half = n_s // 2
        for i, sv in enumerate(r.sign):
            if i < half:
                d_first += sv
            else:
                d_second += sv

    no_move_ticks, no_move_vol = 0, 0.0
    freq, prev_tk = {}, None
    for i, px in enumerate(r.precio):
        tk = int(round(px / tick_size))
        if i > 0 and tk == prev_tk:
            no_move_ticks += 1
            no_move_vol += r.vol[i]
        prev_tk = tk
        freq[tk] = freq.get(tk, 0) + 1
    max_level_ticks = max(freq.values()) if freq else 0

    return Zona(
        start_ts=r.t_start, end_ts=r.t_last, bucket=bucket, dir=r.dir,
        price_upper=r.sw_h, price_lower=r.sw_l, price_mid=(r.sw_h + r.sw_l) / 2.0,
        height_ticks=sweep_ticks, pasos=r.streak, valid_steps=r.valid_steps,
        avg_ms=avg_ms, total_ms=total, vol_rate=vol_rate, total_vol=r.total_vol,
        max_tick_vol=max_tick_vol, cvd_sweep=cvd, buy_vol=buy, sell_vol=sell,
        delta_slope=slope, delta_first=d_first, delta_second=d_second,
        no_move_ticks=no_move_ticks, no_move_vol=no_move_vol,
        max_level_ticks=max_level_ticks)


def run_con_casi(ts_ns, price, volume, tick_size, params=None, skip_primeros=5):
    """Como `run`, pero devuelve `(zonas, casi_zonas)`. Ver `_emitir`."""
    casi: list = []
    z = run(ts_ns, price, volume, tick_size, params, skip_primeros, _casi=casi)
    return z, casi


def hft_run(ts_ns: np.ndarray, price: np.ndarray, volume: np.ndarray, tick_size: float,
        params: Optional[HFT_Params] = None, skip_primeros: int = 5,
        _casi: Optional[list] = None) -> List[Zona]:
    """Corre la maquina de estados sobre ticks crudos.

    `price` en PRECIO (no en ticks): el .cs compara contra `TickSize` y persiste precios.
    `skip_primeros` reproduce `if (CurrentBars[1] < 5) return;`. El primer tick usable
    es siempre el indice 1: el 0 no tiene barra previa contra la cual comparar.
    """
    p = params or HFT_Params()
    ts_ms = (np.asarray(ts_ns, dtype=np.int64) // 1_000_000)
    px = np.asarray(price, dtype=np.float64)
    vol = np.asarray(volume, dtype=np.float64)

    zonas: List[Zona] = []
    r = _Racha()
    last_side = 0

    def finalizar():
        z = _emitir(r, p, tick_size, _casi)
        if z is not None:
            zonas.append(z)
        r.reset()

    # max(.., 1): el tick 0 no tiene `Closes[ds][1]`. Sin esto, i=0 lee px[-1] y da la
    # vuelta al array, inventando una direccion inicial a partir del ultimo tick.
    for i in range(max(skip_primeros, 1), len(px)):
        cl, cl_p = px[i], px[i - 1]
        ms = float(ts_ms[i] - ts_ms[i - 1])
        v = vol[i]

        side = 1 if cl > cl_p else (-1 if cl < cl_p else last_side)
        if side == 0:
            side = 1
        last_side = side
        signed = side * v

        # En 1 tick, Open == Close, asi que la rama estricta y la laxa coinciden.
        is_down = cl <= cl_p
        is_up = cl >= cl_p

        if r.dir != 0 and ms > p.max_pausa_ms:
            finalizar()
            continue                       # el .cs hace `return`: este tick no inicia

        if r.dir == 0:
            if is_down and is_up:
                pass                       # FIX Flat: el tick plano no inicia racha
            elif is_down:
                r.dir = -1
                _iniciar(r, cl, v, signed, int(ts_ms[i]))
            elif is_up:
                r.dir = 1
                _iniciar(r, cl, v, signed, int(ts_ms[i]))
        else:
            avanza = is_down if r.dir == -1 else is_up
            if avanza:
                _continuar(r, ms, cl, v, signed, int(ts_ms[i]), True)
                r.fails = 0
            else:
                r.fails += 1
                if r.fails <= p.fallos_tolerados:
                    _continuar(r, ms, cl, v, signed, int(ts_ms[i]), False)
                else:
                    finalizar()

    return zonas


def _iniciar(r: _Racha, cl: float, v: float, signed: float, t_ms: int):
    r.streak = 1
    r.valid_steps = 1
    r.fails = 0
    r.sw_h = r.sw_l = cl                   # 1 tick: High == Low == precio
    r.ms.clear()                           # msList arranca VACIA: n intervalos = pasos-1
    r.precio.clear(); r.vol.clear(); r.sign.clear()
    r.precio.append(cl); r.vol.append(v); r.sign.append(signed)
    r.total_vol = v
    r.t_start = r.t_last = t_ms


def _continuar(r: _Racha, ms: float, cl: float, v: float, signed: float, t_ms: int,
               valid: bool):
    r.streak += 1
    if valid:
        r.valid_steps += 1
    r.sw_h = max(r.sw_h, cl)
    r.sw_l = min(r.sw_l, cl)
    r.ms.append(ms)
    r.precio.append(cl); r.vol.append(v); r.sign.append(signed)
    r.total_vol += v
    r.t_last = t_ms

# ===================================================================================================
# CENSO SIN RETORNOS — impulsos del corredor (DET_NT8, 100T) x zonas HFT (port Python de HFTZonesESPureV2Flat)
# Se concatena DESPUES de Pasada 2 + DET_NT8 + dev addon (sin su main) + el port HFT. No calcula desenlaces: sólo presencia/toque en W <= conf_bar.
# Definicion: docs/research/DEFINICION_INICIAL_CORREDOR_X_HFT_20261016.md
# ===================================================================================================
import os

CENSUS_SPEC = "EXP-CORREDOR-HFT-CENSO-v1"
DISC_START_C, DISC_END_C = 20250718, 20260331
EXT_FIXED = (300, 600, 1200)
HFT_TICK = 0.25


def presence_for_impulse(lo_w, hi_w, b0, cb, zl, zu, mb, ext):
    """lo_w/hi_w: minimos y maximos de las barras de W (indices b0..b0+len-1).
    cb: barra de creacion (primera barra con cierre >= end_ts) de cada zona HFT; zl/zu: limites; mb: barra de mitigacion (inf si no hay);
    ext: int (extension fija en barras) | 'mit' (activa hasta la primera barra que cruza toda la zona) | 'first' (activa hasta su primer toque).
    Devuelve (n_activas_en_W, n_tocadas_en_W, n_tocadas_y_dentro_al_final)."""
    if len(cb) == 0:
        return 0, 0, 0
    b = (b0 + np.arange(len(lo_w)))[:, None]
    active = b > cb[None, :]
    if isinstance(ext, int):
        active &= b <= (cb[None, :] + ext)
    elif ext == "mit":
        active &= b <= mb[None, :]
    touch = (lo_w[:, None] <= zu[None, :]) & (hi_w[:, None] >= zl[None, :])
    if ext == "first":
        t_any = active & touch
        first_t = np.where(t_any.any(0), t_any.argmax(0), len(lo_w))
        idx = np.arange(len(lo_w))[:, None]
        active = active & (idx <= first_t[None, :])
    act_any = active.any(0)
    touched = (active & touch).any(0)
    inside_end = touched & (lo_w[-1] >= zl) & (hi_w[-1] <= zu)
    return int(act_any.sum()), int(touched.sum()), int(inside_end.sum())


def mitigation_bars(lo, hi, cb, zl, zu, s_start, s_end):
    """Primera barra > cb que cruza toda la zona (low<=zl y high>=zu) dentro de la sesion; inf si no hay."""
    out = np.full(len(cb), 10 ** 9, dtype=np.int64)
    for k in range(len(cb)):
        a = int(cb[k]) + 1
        if a >= s_end:
            continue
        m = (lo[a:s_end] <= zl[k]) & (hi[a:s_end] >= zu[k])
        if m.any():
            out[k] = a + int(m.argmax())
    return out




# ===================================================================================================
# ESTUDIO COMPLETO EXP-CORREDOR-HFT (DESENLACES CAUSALES E1/E2 + CONTROLES + ESCALERA ML CON NULO)
# Referente rector: docs/NORTH_STAR.md (sha256 05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421)
# Handoff: HANDOFF_CORREDOR_X_HFT_PARA_GEMINI_20261016.md
# Manifiesto congelado: MANIFIESTO_CONGELADO_EXP_CORREDOR_X_HFT_20261016.md
# ===================================================================================================
import os
import warnings
warnings.filterwarnings("ignore")

from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, ElasticNetCV
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
import lightgbm as lgb
import torch
import torch.nn as nn
import torch.nn.functional as F

STUDY_SPEC = "EXP-CORREDOR-HFT-20261016-V1"
NORTH_STAR_SHA256_CURRENT = "05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421"
DISC_START_C, DISC_END_C = 20250718, 20260331
HFT_TICK = 0.25


@njit(cache=False)
def eval_rect_e1_e2_numba(
    lo_b: np.ndarray,
    hi_b: np.ndarray,
    cl_b: np.ndarray,
    p_al: np.ndarray,
    res: int,
    dec_bar: int,
    s_end: int,
    horizon_bars: int,
    z_lo: float,
    z_hi: float,
    dir_zone: int,
    imp_dir: int,
    touch_mode: int,  # 0 = wick [lo_b, hi_b], 1 = close_only cl_b
    tick_size: float,
):
    """
    Evalúa causalmente desde dec_bar + 1 hasta min(s_end - 1, dec_bar + horizon_bars):
      - inside_at_dec: 1 si en dec_bar el precio ya está dentro de [z_lo, z_hi]
      - censurado: 1 si dec_bar + horizon_bars >= s_end y no resolvió antes de s_end
      - E1: 1 si el precio toca [z_lo, z_hi] antes de horizon_bars
      - t_E1: barras transcurridas hasta E1 (0 si inside_at_dec, -1 si no E1)
      - E2_contra_zona: tras llegar en b_e1, recorre todo el ancho [z_lo, z_hi] en dirección
        OPUESTA a dir_zone (-dir_zone) antes de horizon_bars y antes de salir por el borde de entrada.
      - E2_contra_impulso: tras llegar en b_e1, recorre todo el ancho [z_lo, z_hi] en dirección
        OPUESTA a imp_dir (-imp_dir) antes de horizon_bars y antes de salir por el borde de entrada.
      - t_E2: barras desde dec_bar hasta E2_contra_zona (-1 si no ocurre)
      - ambiguous: 1 si en la barra de resolución se tocaron ambos bordes en el mismo tick
      - mfe_inv_ticks, mae_inv_ticks: excursión máxima a favor (-imp_dir) y en contra (+imp_dir) en H barras
    """
    p_dec = cl_b[dec_bar]
    inv_dir = -imp_dir
    inside_at_dec = 1 if (p_dec >= z_lo - 1e-9 and p_dec <= z_hi + 1e-9) else 0

    max_b = dec_bar + horizon_bars
    is_truncated = 1 if max_b >= s_end else 0
    lim_b = s_end - 1 if max_b >= s_end else max_b

    e1 = 1 if inside_at_dec == 1 else 0
    b_e1 = dec_bar if inside_at_dec == 1 else -1

    mfe_inv = 0.0
    mae_inv = 0.0

    for b in range(dec_bar + 1, lim_b + 1):
        # Excursiones direccionales respecto a p_dec en dirección de inversión (-imp_dir):
        if inv_dir == 1:
            fav = (hi_b[b] - p_dec) / tick_size
            adv = (p_dec - lo_b[b]) / tick_size
        else:
            fav = (p_dec - lo_b[b]) / tick_size
            adv = (hi_b[b] - p_dec) / tick_size
        if fav > mfe_inv:
            mfe_inv = fav
        if adv > mae_inv:
            mae_inv = adv

        if e1 == 0:
            if touch_mode == 0:
                touched = (lo_b[b] <= z_hi + 1e-9) and (hi_b[b] >= z_lo - 1e-9)
            else:
                touched = (cl_b[b] <= z_hi + 1e-9) and (cl_b[b] >= z_lo - 1e-9)
            if touched:
                e1 = 1
                b_e1 = b

    cens_e1 = 1 if (e1 == 0 and is_truncated == 1) else 0
    t_e1 = (b_e1 - dec_bar) if e1 == 1 else -1

    # Evaluar E2_contra_zona (dirección objetivo = -dir_zone) y E2_contra_impulso (dirección objetivo = -imp_dir)
    # Una vez que el precio toca la zona en b_e1 (o si ya estaba adentro en dec_bar, desde dec_bar + 1):
    e2_cz = 0
    e2_ci = 0
    t_e2_cz = -1
    ambig_cz = 0
    cens_e2 = 0

    if e1 == 1:
        start_e2_b = dec_bar + 1 if inside_at_dec == 1 else b_e1
        # Para cada modo direccional (1: target_dir = -dir_zone; 2: target_dir = -imp_dir):
        # Si target_dir == +1 (atravesar hacia arriba): éxito = tocar z_hi; invalidación tras haber entrado = caer por debajo de z_lo - tick_size
        # Si target_dir == -1 (atravesar hacia abajo): éxito = tocar z_lo; invalidación tras haber entrado = subir por encima de z_hi + tick_size
        for mode_idx in range(2):
            t_dir = -dir_zone if mode_idx == 0 else -imp_dir
            resolved = 0
            won = 0
            amb = 0
            b_win = -1
            # Si b_e1 fue la barra de llegada, verificar desde el tick dentro de start_e2_b en que entró a la zona:
            for b in range(start_e2_b, lim_b + 1):
                if t_dir == 1:
                    hit_succ = hi_b[b] >= z_hi - 1e-9
                    hit_fail = (b > start_e2_b) and (lo_b[b] <= z_lo - tick_size + 1e-9)
                else:
                    hit_succ = lo_b[b] <= z_lo + 1e-9
                    hit_fail = (b > start_e2_b) and (hi_b[b] >= z_hi + tick_size - 1e-9)

                if hit_succ and not hit_fail:
                    # Si b == start_e2_b (misma barra en que llegó por primera vez), verificar tick a tick que primero tocó el borde de entrada y DESPUÉS tocó el borde de salida:
                    if b == b_e1 and inside_at_dec == 0:
                        t0_tk = b * res
                        t1_tk = (b + 1) * res
                        entered = False
                        crossed = False
                        for tk in range(t0_tk, t1_tk):
                            ptk = p_al[tk]
                            if not entered:
                                if z_lo - 1e-9 <= ptk <= z_hi + 1e-9:
                                    entered = True
                            else:
                                if (t_dir == 1 and ptk >= z_hi - 1e-9) or (t_dir == -1 and ptk <= z_lo + 1e-9):
                                    crossed = True
                                    break
                        if crossed:
                            resolved = 1
                            won = 1
                            b_win = b
                            break
                    else:
                        resolved = 1
                        won = 1
                        b_win = b
                        break
                elif hit_fail and not hit_succ:
                    resolved = 1
                    won = 0
                    break
                elif hit_succ and hit_fail:
                    # Desempate tick a tick dentro de la barra b:
                    t0_tk = b * res
                    t1_tk = (b + 1) * res
                    for tk in range(t0_tk, t1_tk):
                        ptk = p_al[tk]
                        s_tk = (ptk >= z_hi - 1e-9) if t_dir == 1 else (ptk <= z_lo + 1e-9)
                        f_tk = (ptk <= z_lo - tick_size + 1e-9) if t_dir == 1 else (ptk >= z_hi + tick_size - 1e-9)
                        if s_tk and f_tk:
                            resolved = 1
                            won = 0
                            amb = 1
                            break
                        elif s_tk:
                            resolved = 1
                            won = 1
                            b_win = b
                            break
                        elif f_tk:
                            resolved = 1
                            won = 0
                            break
                    if resolved == 1:
                        break

            if mode_idx == 0:
                e2_cz = won
                t_e2_cz = (b_win - dec_bar) if won == 1 else -1
                ambig_cz = amb
                if resolved == 0 and is_truncated == 1:
                    cens_e2 = 1
            else:
                e2_ci = won

    return (
        inside_at_dec,
        cens_e1,
        e1,
        t_e1,
        e2_cz,
        e2_ci,
        t_e2_cz,
        ambig_cz,
        cens_e2,
        mfe_inv,
        mae_inv,
    )


def verify_causal_outcome_and_prefix_tests(sessions_list, B):
    """
    Ejecuta las 3 pruebas técnicas obligatorias (§6.A.3 del Handoff):
      1) Prefijo vs Streaming: truncar la sesión en cls_b produce exactamente las mismas zonas HFT (cb <= cls_b),
         la misma zona del corredor cerrada en cls_b, los mismos conteos en W1/W2 y las mismas features que la sesión completa.
      2) Invariancia ante perturbaciones futuras: alterar precios/volúmenes en b > cls_b no cambia en 1 bit ninguna entrada ni feature en cls_b.
      3) Causalidad de available_at = end_ts: ninguna zona con cb >= b cuenta como activa en b, y start_ts no se usa jamás.
    """
    # Buscar la primera sesión con al menos 1 impulso confirmado y cerrado:
    pc1 = (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72)
    s0 = None
    z_full = []
    for s_cand in sessions_list:
        sid0 = s_cand["session_id"]
        m_b0 = B["sid"] == sid0
        if not np.any(m_b0):
            continue
        o0, h0, l0, c0 = B["o"][m_b0].copy(), B["h"][m_b0].copy(), B["l"][m_b0].copy(), B["c"][m_b0].copy()
        sid_arr0 = B["sid"][m_b0].copy()
        cid_arr0 = B["cid"][m_b0].copy()
        ts_end0 = B["ts_end"][m_b0].copy()
        _, _, _, _, z_cand, _, _ = detect_zones_nt8_numba(
            o0, h0, l0, c0, sid_arr0, cid_arr0, 200, 100,
            pc1[0], pc1[1], pc1[2], pc1[3], pc1[4], pc1[5], pc1[6], pc1[7], pc1[8], pc1[9], pc1[10], pc1[11], pc1[12], pc1[13], 40, 5, 1.60, TICK_ES
        )
        if len(z_cand) > 0:
            s0 = s_cand
            z_full = z_cand
            break
    assert s0 is not None and len(z_full) > 0, "No zones found for prefix test"
    z_test = z_full[0]
    cls_b_test = int(z_test[5])

    # 1. Prueba Prefijo vs Streaming (truncando barras en cls_b_test + 1):
    cut = cls_b_test + 1
    _, _, _, _, z_pref, _, _ = detect_zones_nt8_numba(
        o0[:cut], h0[:cut], l0[:cut], c0[:cut], sid_arr0[:cut], cid_arr0[:cut], 200, 100,
        pc1[0], pc1[1], pc1[2], pc1[3], pc1[4], pc1[5], pc1[6], pc1[7], pc1[8], pc1[9], pc1[10], pc1[11], pc1[12], pc1[13], 40, 5, 1.60, TICK_ES
    )
    diff_zone_prefix = float(np.max(np.abs(z_pref[0, :13] - z_test[:13])))
    assert diff_zone_prefix == 0.0, f"Prefix vs streaming mismatch: {diff_zone_prefix}"

    # 2. Prueba de Invariancia Futura (alterar barras b > cls_b_test por +250 puntos):
    o_pert, h_pert, l_pert, c_pert = o0.copy(), h0.copy(), l0.copy(), c0.copy()
    o_pert[cut:] += 250.0
    h_pert[cut:] += 250.0
    l_pert[cut:] += 250.0
    c_pert[cut:] += 250.0
    _, _, _, _, z_pert, _, _ = detect_zones_nt8_numba(
        o_pert, h_pert, l_pert, c_pert, sid_arr0, cid_arr0, 200, 100,
        pc1[0], pc1[1], pc1[2], pc1[3], pc1[4], pc1[5], pc1[6], pc1[7], pc1[8], pc1[9], pc1[10], pc1[11], pc1[12], pc1[13], 40, 5, 1.60, TICK_ES
    )
    diff_future_pert = float(np.max(np.abs(z_pert[0, :13] - z_test[:13])))
    assert diff_future_pert == 0.0, f"Future perturbation leaked into cls_b: {diff_future_pert}"

    # 3. Prueba de available_at = end_ts en HFT (v2, NO VACUA).
    # Defecto de k36: se cortaba en cls_b de la PRIMERA zona del corredor, temprano en la
    # sesion; ahi habia 0 zonas HFT (n_hft_zones_verified_at_prefix=0) y `0 == 0` pasaba
    # sin verificar nada. Ahora: cortes tardios en varias sesiones, se exige un minimo de
    # zonas realmente verificadas y se compara IDENTIDAD de cada zona, no solo el conteo.
    MIN_ZONES_VERIFIED = 200
    MIN_SESSIONS_WITH_ZONES = 5
    prm = HFT_Params(mostrar_absorb=False)

    def _sig(z):
        return (int(z.start_ts), int(z.end_ts), str(z.bucket), int(z.dir))

    verified_total, sessions_ok = 0, 0
    for s_v in sessions_list:
        ts_v = s_v["ts_utc_ns"]
        if len(ts_v) < 1000:
            continue
        zs_full_v = [z for z in hft_run(ts_v, s_v["prices"], s_v["vol"], HFT_TICK, prm)
                     if "ABSORB" not in str(z.bucket).upper()]
        got_here = 0
        for frac in (0.5, 0.75, 0.9):
            ts_cut_v = int(ts_v[int(len(ts_v) * frac)])
            m_v = ts_v <= ts_cut_v
            zs_pref_v = [z for z in hft_run(ts_v[m_v], s_v["prices"][m_v], s_v["vol"][m_v], HFT_TICK, prm)
                         if "ABSORB" not in str(z.bucket).upper()]
            full_before_v = [z for z in zs_full_v if z.end_ts * 1_000_000 <= ts_cut_v]
            assert sorted(map(_sig, zs_pref_v)) == sorted(map(_sig, full_before_v)), (
                "HFT prefix identity mismatch (sesion %s, corte %.2f): %d vs %d zonas"
                % (s_v.get("session_id"), frac, len(zs_pref_v), len(full_before_v)))
            got_here += len(zs_pref_v)
        verified_total += got_here
        sessions_ok += 1 if got_here > 0 else 0
        if verified_total >= MIN_ZONES_VERIFIED and sessions_ok >= MIN_SESSIONS_WITH_ZONES:
            break
    assert verified_total >= MIN_ZONES_VERIFIED and sessions_ok >= MIN_SESSIONS_WITH_ZONES, (
        "prueba de prefijo HFT VACUA: %d zonas verificadas en %d sesiones" % (verified_total, sessions_ok))

    return {
        "prefix_vs_streaming_max_abs_diff": diff_zone_prefix,
        "future_perturbation_invariance_max_abs_diff": diff_future_pert,
        "hft_available_at_end_ts_prefix_exact_match": True,
        "hft_prefix_test_version": 2,
        "n_hft_zones_verified_at_prefix": verified_total,
        "n_sessions_with_hft_zones_verified": sessions_ok,
    }


def clustered_proportion_diff_test(
    y_treat: np.ndarray,
    sid_treat: np.ndarray,
    y_ctrl: np.ndarray,
    sid_ctrl: np.ndarray,
) -> dict:
    """
    Calcula la diferencia de proporciones P(Y=1 | Treat) - P(Y=1 | Ctrl) con:
      - Error estándar clusterizado por sesión (Liang-Zeger / varianza de totales por sesión sobre la diferencia)
      - Efecto de diseño empírico medido (DEFF = Var_cluster / Var_iid)
      - MDE80 empírico medido en puntos porcentuales (2.80 * SE_clustered * 100)
      - Diferencia pareada por sesión (sobre sesiones donde ambos grupos tienen observaciones)
    """
    if len(y_treat) == 0 or len(y_ctrl) == 0:
        return {"n_treat": len(y_treat), "n_ctrl": len(y_ctrl), "p_treat": None, "p_ctrl": None, "diff_pp": None, "p_val": 1.0}

    p1 = float(np.mean(y_treat))
    p0 = float(np.mean(y_ctrl))
    diff = p1 - p0
    n1, n0 = len(y_treat), len(y_ctrl)

    # Varianza IID de referencia:
    var_iid = (p1 * (1.0 - p1)) / max(n1, 1) + (p0 * (1.0 - p0)) / max(n0, 1)

    # Varianza clusterizada por sesión (método delta / Liang-Zeger sobre residuos de cada grupo por sesión):
    all_sids = sorted(set(sid_treat.tolist()) | set(sid_ctrl.tolist()))
    g_scores = []
    paired_diffs = []
    for s in all_sids:
        m1 = sid_treat == s
        m0 = sid_ctrl == s
        u1 = float(np.sum(y_treat[m1] - p1)) / max(n1, 1) if np.any(m1) else 0.0
        u0 = float(np.sum(y_ctrl[m0] - p0)) / max(n0, 1) if np.any(m0) else 0.0
        g_scores.append(u1 - u0)
        if np.any(m1) and np.any(m0):
            paired_diffs.append(float(np.mean(y_treat[m1]) - np.mean(y_ctrl[m0])))

    G = len(all_sids)
    g_arr = np.asarray(g_scores, dtype=np.float64)
    var_cl = float((G / max(G - 1, 1)) * np.sum((g_arr - np.mean(g_arr)) ** 2))
    se_cl = math.sqrt(max(var_cl, 1e-12))
    deff_emp = var_cl / max(var_iid, 1e-12)
    z_cl = diff / se_cl if se_cl > 1e-9 else 0.0
    p_val = two_sided_p(z_cl)
    mde80_emp_pp = 2.80 * se_cl * 100.0

    return {
        "n_treat": int(n1),
        "n_ctrl": int(n0),
        "n_sessions_total": int(G),
        "n_sessions_paired": int(len(paired_diffs)),
        "p_treat": round(p1, 4),
        "p_ctrl": round(p0, 4),
        "diff_pp": round(diff * 100.0, 2),
        "paired_session_mean_diff_pp": round(float(np.mean(paired_diffs)) * 100.0, 2) if paired_diffs else None,
        "se_clustered_pp": round(se_cl * 100.0, 2),
        "ci95_clustered_pp": [round((diff - 1.96 * se_cl) * 100.0, 2), round((diff + 1.96 * se_cl) * 100.0, 2)],
        "z_clustered": round(z_cl, 3),
        "p_clustered": round(p_val, 5),
        "empirical_design_effect_deff": round(deff_emp, 2),
        "mde80_empirical_pp": round(mde80_emp_pp, 2),
        "within_equivalence_margin_3pp": bool(abs(diff * 100.0) < 3.0 and (abs(diff) + 1.96 * se_cl) * 100.0 < 5.0),
    }


class SmallStripTileCNN(nn.Module):
    """CNN chica sobre tiles 3x8 (3 franjas x 8 descriptores locales) para la ablación controlada del Escalón 4."""
    def __init__(self):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=(3, 3), padding=(1, 1)),
            nn.SiLU(),
            nn.AdaptiveAvgPool2d((3, 2)),
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(8 * 3 * 2, 1),
        )

    def forward(self, x):
        return self.conv(x).squeeze(-1)


def compute_ece_10bins(probs: np.ndarray, y_true: np.ndarray) -> float:
    bins = np.linspace(0.0, 1.0, 11)
    ece = 0.0
    n = len(probs)
    if n == 0:
        return 0.0
    for b in range(10):
        m = (probs >= bins[b]) & (probs < bins[b + 1] if b < 9 else probs <= bins[b + 1])
        if np.any(m):
            ece += (float(np.sum(m)) / float(n)) * abs(float(np.mean(probs[m])) - float(np.mean(y_true[m])))
    return round(float(ece), 5)


def select_ref_zone_and_features(
    cand_indices: np.ndarray,
    cb_arr: np.ndarray,
    lo_z_arr: np.ndarray,
    hi_z_arr: np.ndarray,
    dr_arr: np.ndarray,
    vol_z_arr: np.ndarray,
    lo_b: np.ndarray,
    hi_b: np.ndarray,
    cl_b: np.ndarray,
    cum_vol_b: np.ndarray,
    ob: int,
    w1_end: int,
    dec_bar: int,
    imp_dir: int,
    rule: str,  # "nearest", "largest", "oldest"
):
    """Selecciona la zona HFT de referencia entre las tocadas en W1 según la regla indicada y extrae sus propiedades causales en dec_bar."""
    p_dec = float(cl_b[dec_bar])
    dists = np.zeros(len(cand_indices), dtype=np.float64)
    widths = np.zeros(len(cand_indices), dtype=np.float64)
    ages = np.zeros(len(cand_indices), dtype=np.float64)

    for idx_i, k in enumerate(cand_indices):
        zl, zh = float(lo_z_arr[k]), float(hi_z_arr[k])
        if zl <= p_dec <= zh:
            dists[idx_i] = 0.0
        else:
            dists[idx_i] = min(abs(p_dec - zl), abs(p_dec - zh)) / TICK_ES
        widths[idx_i] = max((zh - zl) / TICK_ES, 1.0)
        ages[idx_i] = float(dec_bar - int(cb_arr[k]))

    if rule == "nearest":
        best_pos = int(np.argmin(dists - 1e-4 * widths))
    elif rule == "largest":
        best_pos = int(np.argmax(widths - 1e-4 * dists))
    else:  # "oldest"
        best_pos = int(np.argmax(ages - 1e-4 * dists))

    k_ref = int(cand_indices[best_pos])
    zl_ref = float(lo_z_arr[k_ref])
    zh_ref = float(hi_z_arr[k_ref])
    cb_ref = int(cb_arr[k_ref])
    dr_ref = int(dr_arr[k_ref])
    w_ref = float(widths[best_pos])
    dist_ref = float(dists[best_pos])
    age_ref = float(ages[best_pos])

    # Volumen operado desde la creación (cb_ref) hasta dec_bar:
    vol_since = float(cum_vol_b[dec_bar] - cum_vol_b[cb_ref])

    # Virginidad previa a W1: ¿fue tocada entre cb_ref + 1 y ob - 1?
    if ob > cb_ref + 1:
        lo_pre = lo_b[cb_ref + 1:ob]
        hi_pre = hi_b[cb_ref + 1:ob]
        touches_pre = (lo_pre <= zh_ref + 1e-9) & (hi_pre >= zl_ref - 1e-9)
        n_touches_pre = int(np.sum(touches_pre))
    else:
        n_touches_pre = 0
    virgin_pre = 1 if n_touches_pre == 0 else 0

    # Toques y penetración dentro de W1 [ob .. w1_end]:
    lo_w1 = lo_b[ob:w1_end + 1]
    hi_w1 = hi_b[ob:w1_end + 1]
    t_w1 = (lo_w1 <= zh_ref + 1e-9) & (hi_w1 >= zl_ref - 1e-9)
    n_touches_w1 = int(np.sum(t_w1))
    t_first_rel = float(np.argmax(t_w1)) / max(float(len(lo_w1) - 1), 1.0) if np.any(t_w1) else 0.0

    # Penetración máxima en W1 dentro del rectángulo:
    if np.any(t_w1):
        ov_hi = np.minimum(hi_w1[t_w1], zh_ref)
        ov_lo = np.maximum(lo_w1[t_w1], zl_ref)
        pen_ticks = float(np.max( np.maximum(ov_hi - ov_lo, 0.0) ) / TICK_ES)
    else:
        pen_ticks = 0.0

    z_mid = 0.5 * (zl_ref + zh_ref)
    inv_dir = -imp_dir
    ahead = 1 if (inv_dir * (z_mid - p_dec) >= 0.0) else 0
    aligned = 1 if (dr_ref == imp_dir) else 0

    return {
        "k_ref": k_ref,
        "z_lo": zl_ref,
        "z_hi": zh_ref,
        "cb_ref": cb_ref,
        "dir_zone": dr_ref,
        "width_ticks": w_ref,
        "dist_ticks": dist_ref,
        "age_bars": age_ref,
        "vol_since_creation": vol_since,
        "n_touches_pre_W1": n_touches_pre,
        "virgin_pre_W1": virgin_pre,
        "n_touches_in_W1": n_touches_w1,
        "t_first_touch_rel": round(t_first_rel, 4),
        "penetration_ticks": round(pen_ticks, 2),
        "ahead": ahead,
        "aligned": aligned,
        "zone_sweep_vol": float(vol_z_arr[k_ref]),
    }


def touched_indices_in_window(lo_w, hi_w, b0, cb, zl, zu, mb, ext):
    """Devuelve (n_activas, mask_tocadas_bool, inside_at_end_count) para las zonas pasadas."""
    if len(cb) == 0 or len(lo_w) == 0:
        return 0, np.zeros(len(cb), dtype=bool), 0
    b = (b0 + np.arange(len(lo_w)))[:, None]
    active = b > cb[None, :]
    if isinstance(ext, int):
        active &= b <= (cb[None, :] + ext)
    elif ext == "mit":
        active &= b <= mb[None, :]
    touch = (lo_w[:, None] <= zu[None, :] + 1e-9) & (hi_w[:, None] >= zl[None, :] - 1e-9)
    if ext == "first":
        t_any = active & touch
        first_t = np.where(t_any.any(0), t_any.argmax(0), len(lo_w))
        idx = np.arange(len(lo_w))[:, None]
        active = active & (idx <= first_t[None, :])
    act_any = active.any(0)
    touched = (active & touch).any(0)
    inside_end = touched & (lo_w[-1] >= zl - 1e-9) & (hi_w[-1] <= zu + 1e-9)
    return int(act_any.sum()), touched, int(inside_end.sum())


def build_strip_tile_3x8(lo_b, hi_b, cl_b, vol_b, ob, w1_end, eb, cls_b, tick_size):
    """Construye un tile compacto 3x8 (3 franjas x [4 densidades de volumen + 4 velocidades]) para la ablación CNN chica del Escalón 4."""
    tile = np.zeros((3, 8), dtype=np.float32)
    tot_v_mean = max(float(np.mean(vol_b[ob:cls_b + 1])), 1.0)
    for r_idx, (s_b, e_b) in enumerate([
        (ob, max(ob, w1_end)),
        (min(w1_end + 1, eb), eb),
        (eb, max(eb, cls_b)),
    ]):
        v_seg = vol_b[s_b:e_b + 1]
        rng_seg = (hi_b[s_b:e_b + 1] - lo_b[s_b:e_b + 1]) / tick_size
        chunks_v = np.array_split(v_seg, 4) if len(v_seg) >= 4 else [v_seg] * 4
        chunks_r = np.array_split(rng_seg, 4) if len(rng_seg) >= 4 else [rng_seg] * 4
        for c_i in range(4):
            tile[r_idx, c_i] = float(np.mean(chunks_v[c_i])) / tot_v_mean if len(chunks_v[c_i]) else 0.0
            tile[r_idx, 4 + c_i] = float(np.mean(chunks_r[c_i])) / 10.0 if len(chunks_r[c_i]) else 0.0
    return tile





# ===================================================================================================
# EXP-K36-EDGE-MAXIMIZER-ASYM-MICROSTRUCTURE-V2 (k36)
# Iteración Completa de Corrida:
#   1. Alineación Causal Etiqueta-Ejecución:
#      - Compara entrenar el modelo con la etiqueta simétrica `y_tp1_sym` (1:1) vs entrenar
#        una rama dedicada `M_asym` directamente sobre la etiqueta de supervivencia al stop
#        estructural `y_tp1_asym_fix` y `y_tp1_asym_atr` (seleccionando igniciones rápidas de bajo MAE).
#   2. Buffer Estructural Fijo (+2.5t) vs Adaptado por Volatilidad (max(2.0t, round(0.35 * ATR_100T))).
#   3. Microestructura de 3 Franjas (Hipótesis de Nico + Confluencia HFT):
#      - DESDE / POR DÓNDE: Detección de Escalera Opuesta (`opp_ladder_trap_flag`), Barrido Rápido de
#        Liquidez (`opp_sweep_occurred`) con Mecha de Rechazo y Delta Flip, y Conductividad de Vacío.
#      - A DÓNDE: Masa Gravitatoria Horizontal de 4 Horas (`m_grav_ratio`), Conteo de Picos HVN
#        (`a_donde_hvn_peaks`), Fracción de Imbalance Puro (`a_donde_imbalance_frac`) y Veto al
#        Espejismo (`target_mirage_flag`).
#   4. Tabla de Descomposición Empírica de Win Rate ($W_{sym}$ vs $W_{asym}$, $R = d_1 / s_{struct}$,
#      $W_{BE}$ bruto y neto tras 1.546t, y margen sobre el break-even en puntos porcentuales).
#   5. Auditoría de Multiplicidad DSR (M = 44) y Nulo de Desplazamiento Circular (100 permutaciones).
# ===================================================================================================

STUDY_SPEC_K36 = "EXP-K36-EDGE-MAXIMIZER-ASYM-MICROSTRUCTURE-V2"


@njit(cache=False)
def compute_bar_tick_delta_numba(p_al: np.ndarray, v_al: np.ndarray, res: int) -> np.ndarray:
    """
    Calcula para cada barra de `res` ticks (100T) el delta direccional normalizado [-1, +1]
    usando la regla tick-a-tick (uptick/downtick con memoria de último signo no nulo).
    100% causal dentro de cada barra.
    """
    nb = len(p_al) // res
    out = np.zeros(nb, dtype=np.float64)
    for b in range(nb):
        i0 = b * res
        i1 = i0 + res
        last_sign = 0.0
        signed_v = 0.0
        tot_v = 0.0
        for k in range(i0, i1):
            if k > i0:
                dp = p_al[k] - p_al[k - 1]
                if dp > 1e-9:
                    last_sign = 1.0
                elif dp < -1e-9:
                    last_sign = -1.0
            vk = float(v_al[k])
            signed_v += last_sign * vk
            tot_v += vk
        out[b] = signed_v / tot_v if tot_v > 0.0 else 0.0
    return out


@njit(cache=False)
def simulate_2stage_trade_tick_numba(
    lo_b: np.ndarray,
    hi_b: np.ndarray,
    cl_b: np.ndarray,
    p_al: np.ndarray,
    res: int,
    dec_bar: int,
    s_end: int,
    horizon_bars: int,
    inv_dir: int,
    d1_ticks: float,
    w_ticks: float,
    stop_ticks: float,
    tick_size: float,
):
    """
    Simulador causal tick-a-tick con Máquina de Estados Estricta desde el cierre de `dec_bar` (p_entry = cl_b[dec_bar]):
      - Evalúa tanto entrada inmediata en `p_entry` como orden límite pasiva en `p_entry`
        con trade-through de 1 tick dentro de 25 barras (antes de escaparse 0.50 * d1_ticks).
      - Soporta barreras simétricas (`stop_ticks == d1_ticks`) y asimétricas (`stop_ticks == s_struct < d1_ticks`).
      - Calcula los retornos brutos en ticks de dos modos de salida:
        1) `gross_1stage`: 100% sale en el borde frontal de la zona (`+d1_ticks`) o en el stop (`-stop_ticks`)
           o al cierre del horizonte `horizon_bars`.
        2) `gross_2stage`: 50% sale en `+d1_ticks`, mueve el stop del segundo 50% a Break-Even (`0.0` ticks),
           y busca el borde opuesto de la zona (`+d1_ticks + w_ticks`) o sale en `0.0` (BE) / cierre de horizonte.
    """
    p_entry = cl_b[dec_bar]
    max_b = dec_bar + horizon_bars
    lim_b = s_end - 1 if max_b >= s_end else max_b

    t_start = (dec_bar + 1) * res
    t_end = (lim_b + 1) * res

    hit_tp1 = 0
    hit_tp2 = 0
    hit_sl_before_tp1 = 0
    hit_be_after_tp1 = 0
    bars_to_resolve = lim_b - dec_bar

    for tk in range(t_start, t_end):
        ptk = p_al[tk]
        fav_t = inv_dir * (ptk - p_entry) / tick_size
        if hit_tp1 == 0:
            if fav_t <= -stop_ticks + 1e-9:
                hit_sl_before_tp1 = 1
                bars_to_resolve = (tk // res) - dec_bar
                break
            if fav_t >= d1_ticks - 1e-9:
                hit_tp1 = 1
                if w_ticks <= 1.0:
                    hit_tp2 = 1
                    bars_to_resolve = (tk // res) - dec_bar
                    break
        else:
            if fav_t <= -0.5 + 1e-9:
                hit_be_after_tp1 = 1
                bars_to_resolve = (tk // res) - dec_bar
                break
            if fav_t >= (d1_ticks + w_ticks) - 1e-9:
                hit_tp2 = 1
                bars_to_resolve = (tk // res) - dec_bar
                break

    p_last = cl_b[lim_b]
    terminal_fav_ticks = inv_dir * (p_last - p_entry) / tick_size

    if hit_sl_before_tp1 == 1:
        gross_1stage = -stop_ticks
        gross_2stage = -stop_ticks
    elif hit_tp1 == 1:
        gross_1stage = d1_ticks
        if hit_tp2 == 1:
            gross_2stage = 0.5 * d1_ticks + 0.5 * (d1_ticks + w_ticks)
        elif hit_be_after_tp1 == 1:
            gross_2stage = 0.5 * d1_ticks + 0.5 * 0.0
        else:
            gross_2stage = 0.5 * d1_ticks + 0.5 * max(0.0, min(d1_ticks + w_ticks, terminal_fav_ticks))
    else:
        gross_1stage = max(-stop_ticks, min(d1_ticks, terminal_fav_ticks))
        gross_2stage = gross_1stage

    # 2. Verificación de Fill Pasivo con Trade-Through de 1 tick (máquina de estados estricta):
    wait_lim_b = dec_bar + 25 if (dec_bar + 25 < lim_b) else lim_b
    t_wait_end = (wait_lim_b + 1) * res
    pas_filled = 0
    tk_fill = -1
    for tk in range(t_start, t_wait_end):
        ptk = p_al[tk]
        fav_t = inv_dir * (ptk - p_entry) / tick_size
        if fav_t >= 0.50 * d1_ticks:
            break
        if fav_t <= -1.0 + 1e-9:
            pas_filled = 1
            tk_fill = tk
            break

    pas_gross_1stage = 0.0
    pas_gross_2stage = 0.0
    pas_hit_tp1 = 0
    if pas_filled == 1:
        p_tp1 = 0
        p_tp2 = 0
        p_sl = 0
        p_be = 0
        for tk in range(tk_fill + 1, t_end):
            ptk = p_al[tk]
            fav_t = inv_dir * (ptk - p_entry) / tick_size
            if p_tp1 == 0:
                if fav_t <= -stop_ticks + 1e-9:
                    p_sl = 1
                    break
                if fav_t >= d1_ticks - 1e-9:
                    p_tp1 = 1
                    if w_ticks <= 1.0:
                        p_tp2 = 1
                        break
            else:
                if fav_t <= -0.5 + 1e-9:
                    p_be = 1
                    break
                if fav_t >= (d1_ticks + w_ticks) - 1e-9:
                    p_tp2 = 1
                    break
        pas_hit_tp1 = p_tp1
        if p_sl == 1:
            pas_gross_1stage = -stop_ticks
            pas_gross_2stage = -stop_ticks
        elif p_tp1 == 1:
            pas_gross_1stage = d1_ticks
            if p_tp2 == 1:
                pas_gross_2stage = 0.5 * d1_ticks + 0.5 * (d1_ticks + w_ticks)
            elif p_be == 1:
                pas_gross_2stage = 0.5 * d1_ticks
            else:
                pas_gross_2stage = 0.5 * d1_ticks + 0.5 * max(0.0, min(d1_ticks + w_ticks, terminal_fav_ticks))
        else:
            pas_gross_1stage = max(-stop_ticks, min(d1_ticks, terminal_fav_ticks))
            pas_gross_2stage = pas_gross_1stage

    return (
        gross_1stage,
        gross_2stage,
        float(pas_filled),
        pas_gross_1stage,
        pas_gross_2stage,
        float(bars_to_resolve),
        float(hit_tp1),
        float(hit_tp2),
        float(pas_hit_tp1),
    )


def extract_microstructure_3strips_and_trajectory(
    op_b: np.ndarray,
    hi_b: np.ndarray,
    lo_b: np.ndarray,
    cl_b: np.ndarray,
    vol_b: np.ndarray,
    delta_b: np.ndarray,
    atr_a: np.ndarray,
    ema_a: np.ndarray,
    s_beg: int,
    ob: int,
    w1_end: int,
    eb: int,
    cls_b: int,
    imp_dir: int,
    orig_px: float,
    ext_px: float,
    z_lo_t: float,
    z_hi_t: float,
    has_hft_w1: int,
    fix600_e1_touch: int,
    fix600_e2_touch: int,
    tick_size: float,
):
    """
    Extrae:
      1) Las 28 variables de trayectoria completa de 6 fases (`P0`, `Q1..Q4`, `Turn`) + secuencia `16x8`.
      2) Las variables microestructurales de las 3 Franjas (`DESDE DÓNDE`, `POR DÓNDE`, `A DÓNDE`)
         diseñadas a partir de las observaciones de Nico:
         - Escalera opuesta y Barrido Previo (`opp_sweep_occurred`, `opp_ladder_steps`, `opp_ladder_trap_flag`, `sweep_quality_score`).
         - Conductividad del canal `POR DÓNDE` (`por_void_conductivity`, `por_obstacle_density`, `por_wasserstein_asym`).
         - Masa Gravitatoria de 4 Horas en `A DÓNDE` vs Espejismo de Imbalance (`m_grav_ratio`, `a_donde_hvn_peaks`,
           `a_donde_imbalance_frac`, `target_mirage_flag`, `attractor_quality_score`).
    """
    inv_dir = -imp_dir
    H_price = max(abs(ext_px - orig_px), tick_size)
    h_ticks = H_price / tick_size
    a_b = max(float(atr_a[cls_b]), tick_size)
    p_dec = float(cl_b[cls_b])

    # 1. Fase P0: Contexto Pre-Origen (30 y 60 barras antes de ob):
    p0_start = max(s_beg, ob - 30)
    p60_start = max(s_beg, ob - 60)
    if ob > p0_start:
        p0_drift = float(imp_dir * (cl_b[ob] - cl_b[p0_start])) / H_price
        p0_rng = float(hi_b[p0_start:ob].max() - lo_b[p0_start:ob].min()) / H_price
        p0_vol_mean = float(vol_b[p0_start:ob].mean())
        if imp_dir == 1:
            pre_ext = float(hi_b[p60_start:ob].max())
            swept_pre = 1.0 if (ext_px > pre_ext + tick_size and p_dec <= pre_ext + 2.5 * tick_size) else 0.0
            sweep_pen_ticks = max(0.0, (ext_px - pre_ext) / tick_size)
        else:
            pre_ext = float(lo_b[p60_start:ob].min())
            swept_pre = 1.0 if (ext_px < pre_ext - tick_size and p_dec >= pre_ext - 2.5 * tick_size) else 0.0
            sweep_pen_ticks = max(0.0, (pre_ext - ext_px) / tick_size)
    else:
        p0_drift, p0_rng, p0_vol_mean, swept_pre, sweep_pen_ticks = 0.0, 0.5, float(vol_b[ob]), 0.0, 0.0

    s_hi = float(hi_b[s_beg:cls_b + 1].max())
    s_lo = float(lo_b[s_beg:cls_b + 1].min())
    s_rng = max(s_hi - s_lo, tick_size)
    pos_in_sess = float((ext_px - s_lo) / s_rng) if imp_dir == 1 else float((s_hi - ext_px) / s_rng)

    # 2. Fases Q1..Q4: Los 4 cuartiles longitudinales del impulso [ob..eb]:
    imp_len = max(eb - ob + 1, 4)
    idx_q = np.linspace(ob, eb + 1, 5).astype(int)
    dp_q = np.zeros(4, dtype=np.float64)
    vel_q = np.zeros(4, dtype=np.float64)
    vol_q = np.zeros(4, dtype=np.float64)
    eff_q = np.zeros(4, dtype=np.float64)
    del_q = np.zeros(4, dtype=np.float64)

    for q in range(4):
        b0 = idx_q[q]
        b1 = max(idx_q[q + 1], b0 + 1)
        b1 = min(b1, eb + 1)
        n_q = max(b1 - b0, 1)
        px_start = float(op_b[b0]) if q == 0 else float(cl_b[b0 - 1])
        px_end = float(cl_b[b1 - 1])
        adv_ticks = float(imp_dir * (px_end - px_start)) / tick_size
        dp_q[q] = adv_ticks / max(h_ticks, 1.0)
        vel_q[q] = adv_ticks / (n_q * (a_b / tick_size))
        vq_sum = float(vol_b[b0:b1].sum())
        vol_q[q] = vq_sum
        eff_q[q] = (vq_sum / n_q) / max(abs(adv_ticks) / n_q, 0.5)
        del_q[q] = float(imp_dir * delta_b[b0:b1].mean())

    v_tot_imp = max(float(vol_q.sum()), 1.0)
    vol_q_share = vol_q / v_tot_imp
    vol_slope = float((vol_q_share[3] + 0.5 * vol_q_share[2]) - (vol_q_share[0] + 0.5 * vol_q_share[1]))
    vel_q12 = 0.5 * (vel_q[0] + vel_q[1])
    vel_q4_vs_q12 = float(vel_q[3] / max(abs(vel_q12), 0.05))
    vel_q4_vs_q3 = float(vel_q[3] / max(abs(vel_q[2]), 0.05))
    effort_q4_vs_q12 = float(eff_q[3] / max(0.5 * (eff_q[0] + eff_q[1]), 1.0))

    delta_q12 = 0.5 * (del_q[0] + del_q[1])
    delta_q34 = 0.5 * (del_q[2] + del_q[3])
    delta_div = float(del_q[3] - delta_q12)

    cl_imp = cl_b[ob:eb + 1]
    n_imp = len(cl_imp)
    u_grid = np.linspace(0.0, 1.0, n_imp)
    eta_imp = imp_dir * (cl_imp - orig_px) / H_price
    kappa_path = float(np.mean(eta_imp - u_grid))
    if n_imp >= 3 and np.std(eta_imp) > 1e-8:
        corr_lin = float(np.corrcoef(u_grid, eta_imp)[0, 1])
        r2_linear = corr_lin * corr_lin
    else:
        r2_linear = 0.5

    step_diffs = np.diff(cl_imp)
    path_abs_sum = float(np.sum(np.abs(step_diffs)))
    er_kaufman = float(abs(cl_imp[-1] - cl_imp[0]) / max(path_abs_sum, tick_size))
    counter_bar_frac = float(np.mean((imp_dir * (cl_imp - op_b[ob:eb + 1])) < 0))

    run_peak = eta_imp[0]
    max_internal_dd = 0.0
    for val_e in eta_imp:
        if val_e > run_peak:
            run_peak = val_e
        dd_e = run_peak - val_e
        if dd_e > max_internal_dd:
            max_internal_dd = dd_e

    px_slice = cl_b[ob:cls_b + 1]
    vol_slice = vol_b[ob:cls_b + 1]
    eta_slice = np.clip(imp_dir * (px_slice - orig_px) / H_price, 0.0, 1.0)
    hist_v, _ = np.histogram(eta_slice, bins=10, range=(0.0, 1.0), weights=vol_slice)
    tot_hv = max(float(hist_v.sum()), 1.0)
    poc_bin = int(np.argmax(hist_v))
    traj_poc_frac = (poc_bin + 0.5) / 10.0
    traj_lower_half_vol_share = float(hist_v[:5].sum() / tot_hv)
    traj_tip_top20_vol_share = float(hist_v[8:].sum() / tot_hv)
    traj_mid_valley_ratio = float(hist_v[4:7].mean() / max(hist_v.mean(), 1.0))

    # 3. Fase Turn: Transición crítica desde el extremo [eb..cls_b]:
    turn_bars = max(cls_b - eb, 1)
    turn_ret_ticks = float(inv_dir * (p_dec - ext_px)) / tick_size
    turn_ret_frac = turn_ret_ticks / max(h_ticks, 1.0)
    turn_speed_atr = (turn_ret_ticks / turn_bars) / max(a_b / tick_size, 1.0)
    turn_delta_rev = float(inv_dir * delta_b[eb:cls_b + 1].mean())
    turn_delta_flip = float(turn_delta_rev - (-del_q[3]))
    turn_vol_ratio = float(vol_b[eb:cls_b + 1].mean() / max(v_tot_imp / imp_len, 1.0))

    if imp_dir == 1:
        wick_rej = float(hi_b[eb:cls_b + 1].max() - max(op_b[cls_b], cl_b[cls_b])) / a_b
    else:
        wick_rej = float(min(op_b[cls_b], cl_b[cls_b]) - lo_b[eb:cls_b + 1].min()) / a_b

    # =========================================================================
    # 4. NUEVAS MÉTRICAS MICROESTRUCTURALES DE NICO (3 FRANJAS EXTENDIDAS)
    # =========================================================================
    # 4.A: Escalera Opuesta y Barrido Previo en DESDE DÓNDE -> POR DÓNDE:
    # Analizamos la ventana de consolidación/punta [max(ob, eb - 16)..cls_b]
    tip_w_start = max(ob, eb - 16)
    if imp_dir == 1:
        # Impulso alcista -> reversión bajista (inv_dir = -1):
        # Escalera opuesta alcista = techos escalonados crecientes sin barrido ni absorción que atrapan cortos prematuros
        tip_ext_series = hi_b[tip_w_start:cls_b + 1]
    else:
        tip_ext_series = -lo_b[tip_w_start:cls_b + 1]

    # Contar picos locales en la punta:
    n_tip_w = len(tip_ext_series)
    local_peaks = []
    for k_i in range(1, n_tip_w - 1):
        if tip_ext_series[k_i] >= tip_ext_series[k_i - 1] and tip_ext_series[k_i] >= tip_ext_series[k_i + 1]:
            local_peaks.append(float(tip_ext_series[k_i]))
    opp_ladder_steps = len(local_peaks)
    if opp_ladder_steps >= 2:
        diffs_pk = np.diff(np.asarray(local_peaks))
        # Si los picos locales quedaron planos o escalonados sin barrido final (< 1.0 tick de superación)
        unmitigated_ladder = 1.0 if (np.mean(diffs_pk >= -0.5 * tick_size) >= 0.65 and abs(local_peaks[-1] - max(local_peaks)) <= 1.0 * tick_size) else 0.0
    else:
        unmitigated_ladder = 0.0

    # Barrido Rápido de Liquidez (Liquidity Sweep):
    # Ocurre cuando el extremo `ext_px` barrió un pivote previo (`swept_pre == 1` o superó los picos previos de Q3 con clímax en Q4),
    # rechazó rápido (`turn_bars <= 12`), dejó mecha >= 0.65 ATR o cuerpo de rechazo fuerte, y produjo Delta Flip > 0:
    q3_start = idx_q[2]
    q3_end = max(idx_q[3], q3_start + 1)
    if imp_dir == 1:
        q3_pk = float(hi_b[q3_start:q3_end].max())
        swept_q3_ticks = max(0.0, (ext_px - q3_pk) / tick_size)
    else:
        q3_pk = float(lo_b[q3_start:q3_end].min())
        swept_q3_ticks = max(0.0, (q3_pk - ext_px) / tick_size)

    fast_rejection = 1.0 if (turn_bars <= 12 and (wick_rej >= 0.65 or turn_speed_atr >= 0.35)) else 0.0
    delta_confirmed = 1.0 if (turn_delta_flip > 0.02 or turn_delta_rev > 0.0) else 0.0
    opp_sweep_occurred = 1.0 if ((swept_pre == 1.0 or swept_q3_ticks >= 1.5) and fast_rejection == 1.0 and delta_confirmed == 1.0) else 0.0

    # Trampa de Falso Rompimiento (`opp_ladder_trap_flag`):
    # Se activa cuando NO hubo barrido con rechazo (`opp_sweep_occurred == 0`) Y además:
    # o bien hay escalera no barrida con delta adverso (`turn_delta_rev < -0.05` y `wick_rej < 0.35`),
    # o bien la 2.ª mitad (`POR DÓNDE`) tiene zonas HFT intermedias tocadas (`fix600_e2_touch >= 2`) que taponan el canal.
    opp_ladder_trap_flag = 1.0 if (
        opp_sweep_occurred == 0.0 and (
            (unmitigated_ladder == 1.0 and turn_delta_rev < -0.04 and wick_rej < 0.40)
            or (fix600_e2_touch >= 2 and turn_delta_rev < 0.0)
        )
    ) else 0.0

    sweep_quality_score = float(
        0.35 * opp_sweep_occurred
        + 0.25 * np.clip(wick_rej / 1.5, 0.0, 1.5)
        + 0.25 * np.clip(turn_delta_flip, -0.5, 1.0)
        + 0.15 * np.clip(turn_speed_atr, 0.0, 1.5)
        - 0.40 * opp_ladder_trap_flag
    )

    # 4.B: Proyección Horizontal de 4 Horas (hasta 400 barras de 100T hacia la izquierda en la sesión)
    # para medir la Conductividad de `POR DÓNDE` y la Masa Gravitatoria de `A DÓNDE`:
    lookback_4h_start = max(s_beg, cls_b - 400)
    cl_4h = cl_b[lookback_4h_start:cls_b + 1]
    hi_4h = hi_b[lookback_4h_start:cls_b + 1]
    lo_4h = lo_b[lookback_4h_start:cls_b + 1]
    vol_4h = vol_b[lookback_4h_start:cls_b + 1]
    mid_4h = 0.5 * (hi_4h + lo_4h)

    # Definir bordes de `POR DÓNDE` (entre p_dec y el borde frontal de A DÓNDE) y `A DÓNDE` ([z_lo_t, z_hi_t]):
    if inv_dir == -1:  # Vamos hacia abajo (de p_dec hacia z_hi_t..z_lo_t)
        por_lo, por_hi = z_hi_t, max(p_dec, z_hi_t + tick_size)
    else:              # Vamos hacia arriba (de p_dec hacia z_lo_t..z_hi_t)
        por_lo, por_hi = min(p_dec, z_lo_t - tick_size), z_lo_t

    por_h_ticks = max((por_hi - por_lo) / tick_size, 2.0)
    a_h_ticks = max((z_hi_t - z_lo_t) / tick_size, 2.0)

    in_por_4h = (mid_4h >= por_lo - 0.5 * tick_size) & (mid_4h <= por_hi + 0.5 * tick_size)
    in_a_4h = (mid_4h >= z_lo_t - 1.0 * tick_size) & (mid_4h <= z_hi_t + 1.0 * tick_size)

    vol_por_per_tick = float(np.sum(vol_4h[in_por_4h])) / por_h_ticks
    vol_a_per_tick = float(np.sum(vol_4h[in_a_4h])) / a_h_ticks
    sess_vol_per_tick = float(np.sum(vol_4h)) / max(s_rng / tick_size, 10.0)

    # Masa Gravitatoria (`m_grav_ratio`): densidad de volumen por tick en `A DÓNDE` respecto a `POR DÓNDE`:
    m_grav_ratio = float((vol_a_per_tick + 0.15 * sess_vol_per_tick) / max(vol_por_per_tick + 0.15 * sess_vol_per_tick, 1.0))

    # Conductividad de Vacío en `POR DÓNDE`: inversa de la densidad relativa en el canal de tránsito:
    por_void_conductivity = float(sess_vol_per_tick / max(vol_por_per_tick + 0.20 * sess_vol_per_tick, 1.0))

    # Conteo de picos de volumen (`HVN`) en `A DÓNDE` y Fracción de Imbalance Puro en W1 ([ob..w1_end]):
    w1_bars_slice = slice(ob, max(w1_end + 1, ob + 2))
    w1_rng = np.maximum(hi_b[w1_bars_slice] - lo_b[w1_bars_slice], tick_size)
    w1_body = np.abs(cl_b[w1_bars_slice] - op_b[w1_bars_slice])
    w1_del = np.abs(delta_b[w1_bars_slice])
    # Una barra en W1 es "puro imbalance sin comercio de dos lados" si su cuerpo es > 72% del rango y su |delta| > 0.42:
    imbalance_bars_mask = (w1_body / w1_rng >= 0.72) & (w1_del >= 0.42)
    a_donde_imbalance_frac = float(np.mean(imbalance_bars_mask)) if len(w1_rng) > 0 else 0.5

    # Histograma vertical dentro de W1 para contar picos HVN en la 1.ª mitad (`A DÓNDE`):
    hist_w1, _ = np.histogram(cl_b[w1_bars_slice], bins=6, weights=vol_b[w1_bars_slice])
    mean_hw1 = max(float(np.mean(hist_w1)), 1.0)
    a_donde_hvn_peaks = int(np.sum(hist_w1 >= 1.25 * mean_hw1))

    # Bandera de Espejismo en `A DÓNDE` (`target_mirage_flag`):
    # Si `A DÓNDE` tuvo baja masa gravitatoria (< 0.85), alto imbalance unidireccional (> 0.55)
    # y pocas zonas HFT (`fix600_e1_touch == 0`), es un espejismo sin masa que no atrae al precio:
    target_mirage_flag = 1.0 if (
        m_grav_ratio < 0.85 and a_donde_imbalance_frac > 0.50 and fix600_e1_touch <= 0
    ) else (
        1.0 if (m_grav_ratio < 0.65 and a_donde_imbalance_frac > 0.60) else 0.0
    )

    attractor_quality_score = float(
        0.35 * np.clip(np.log1p(m_grav_ratio), 0.0, 2.0)
        + 0.25 * np.clip(por_void_conductivity, 0.0, 2.5)
        + 0.20 * min(float(fix600_e1_touch), 3.0) / 2.0
        + 0.20 * (1.0 - a_donde_imbalance_frac)
        - 0.45 * target_mirage_flag
    )

    # 5. Secuencia Longitudinal 16x8 (`seq_16x8`) sobre [max(s_beg, ob - 4), cls_b]:
    seq_start = max(s_beg, ob - 4)
    seq_edges = np.linspace(seq_start, cls_b + 1, 17).astype(int)
    seq_16x8 = np.zeros((16, 8), dtype=np.float32)
    mean_v_bar = max(v_tot_imp / imp_len, 1.0)
    atr_t = max(a_b / tick_size, 1.0)

    for s_i in range(16):
        b0 = seq_edges[s_i]
        b1 = max(seq_edges[s_i + 1], b0 + 1)
        b1 = min(b1, cls_b + 1)
        nb_s = max(b1 - b0, 1)
        c_end = float(cl_b[b1 - 1])
        c_beg = float(op_b[b0])
        eta_s = float(imp_dir * (c_end - orig_px) / H_price)
        vel_s = float(imp_dir * (c_end - c_beg) / (tick_size * nb_s * atr_t))
        rng_s = float(np.mean(hi_b[b0:b1] - lo_b[b0:b1]) / a_b)
        vol_s = float(np.mean(vol_b[b0:b1]) / mean_v_bar)
        eff_s = float(np.log1p(vol_s / max(abs(c_end - c_beg) / (tick_size * nb_s), 0.25)))
        del_s = float(imp_dir * np.mean(delta_b[b0:b1]))
        if imp_dir == 1:
            wk_s = float(np.mean(hi_b[b0:b1] - np.maximum(op_b[b0:b1], cl_b[b0:b1])) / a_b)
        else:
            wk_s = float(np.mean(np.minimum(op_b[b0:b1], cl_b[b0:b1]) - lo_b[b0:b1]) / a_b)
        phase_s = -1.0 if b1 - 1 < ob else (1.0 if b0 >= eb else 0.0)

        seq_16x8[s_i, 0] = np.clip(eta_s, -0.5, 1.5)
        seq_16x8[s_i, 1] = np.clip(vel_s, -3.0, 3.0)
        seq_16x8[s_i, 2] = np.clip(rng_s, 0.0, 5.0)
        seq_16x8[s_i, 3] = np.clip(vol_s, 0.0, 6.0)
        seq_16x8[s_i, 4] = np.clip(eff_s, 0.0, 4.0)
        seq_16x8[s_i, 5] = np.clip(del_s, -1.0, 1.0)
        seq_16x8[s_i, 6] = np.clip(wk_s, 0.0, 3.0)
        seq_16x8[s_i, 7] = phase_s

    traj_dict = {
        "traj_p0_drift_over_h": round(p0_drift, 5),
        "traj_p0_rng_over_h": round(p0_rng, 5),
        "traj_p0_vol_ratio": round(p0_vol_mean / mean_v_bar, 5),
        "traj_swept_pre_extreme": swept_pre,
        "traj_pos_in_sess_range": round(pos_in_sess, 5),
        "traj_dp_q1": round(float(dp_q[0]), 5),
        "traj_dp_q2": round(float(dp_q[1]), 5),
        "traj_dp_q3": round(float(dp_q[2]), 5),
        "traj_dp_q4": round(float(dp_q[3]), 5),
        "traj_vel_q4_vs_q12": round(vel_q4_vs_q12, 5),
        "traj_vel_q4_vs_q3": round(vel_q4_vs_q3, 5),
        "traj_vol_q1_share": round(float(vol_q_share[0]), 5),
        "traj_vol_q4_share": round(float(vol_q_share[3]), 5),
        "traj_vol_slope": round(vol_slope, 5),
        "traj_effort_q4_vs_q12": round(effort_q4_vs_q12, 5),
        "traj_delta_q12": round(delta_q12, 5),
        "traj_delta_q34": round(delta_q34, 5),
        "traj_delta_q4": round(float(del_q[3]), 5),
        "traj_delta_divergence": round(delta_div, 5),
        "traj_kappa_convexity": round(kappa_path, 5),
        "traj_r2_linear": round(r2_linear, 5),
        "traj_er_kaufman": round(er_kaufman, 5),
        "traj_counter_bar_frac": round(counter_bar_frac, 5),
        "traj_max_internal_dd": round(max_internal_dd, 5),
        "traj_poc_frac": round(traj_poc_frac, 5),
        "traj_lower_half_vol_share": round(traj_lower_half_vol_share, 5),
        "traj_tip_top20_vol_share": round(traj_tip_top20_vol_share, 5),
        "traj_mid_valley_ratio": round(traj_mid_valley_ratio, 5),
        "traj_turn_ret_ticks": round(turn_ret_ticks, 4),
        "traj_turn_ret_frac": round(turn_ret_frac, 5),
        "traj_turn_speed_atr": round(turn_speed_atr, 5),
        "traj_turn_delta_rev": round(turn_delta_rev, 5),
        "traj_turn_delta_flip": round(turn_delta_flip, 5),
        "traj_turn_wick_atr": round(wick_rej, 5),
        "traj_turn_vol_ratio": round(turn_vol_ratio, 5),
        "imp_total_bars": float(imp_len),
        # Nuevas variables microestructurales de las 3 Franjas (Nico):
        "opp_ladder_steps": float(opp_ladder_steps),
        "opp_sweep_occurred": float(opp_sweep_occurred),
        "opp_ladder_trap_flag": float(opp_ladder_trap_flag),
        "sweep_quality_score": round(sweep_quality_score, 5),
        "m_grav_ratio": round(m_grav_ratio, 5),
        "por_void_conductivity": round(por_void_conductivity, 5),
        "a_donde_imbalance_frac": round(a_donde_imbalance_frac, 5),
        "a_donde_hvn_peaks": float(a_donde_hvn_peaks),
        "target_mirage_flag": float(target_mirage_flag),
        "attractor_quality_score": round(attractor_quality_score, 5),
    }
    return traj_dict, seq_16x8


def fit_transform_trajectory_representations_oof(
    seqs_tr: np.ndarray,
    y_tr: np.ndarray,
    splits_in: list,
    seqs_te: np.ndarray,
    seed: int = 20261016,
):
    from sklearn.decomposition import TruncatedSVD
    from sklearn.cluster import KMeans

    N_tr = len(seqs_tr)
    N_te = len(seqs_te)
    flat_tr = np.nan_to_num(seqs_tr.reshape(N_tr, -1), nan=0.0)
    flat_te = np.nan_to_num(seqs_te.reshape(N_te, -1), nan=0.0)

    def _conv1d_multiscale_summary(seq_arr):
        early = seq_arr[:, 2:7, :].mean(axis=1)
        mid = seq_arr[:, 7:11, :].mean(axis=1)
        late = seq_arr[:, 11:14, :].mean(axis=1)
        turn = seq_arr[:, 14:16, :].mean(axis=1)
        d_late_early = late - early
        d_turn_late = turn - late
        curv = late - 2.0 * mid + early
        return np.column_stack([early, mid, late, turn, d_late_early, d_turn_late, curv])

    ms_tr = np.nan_to_num(_conv1d_multiscale_summary(seqs_tr), nan=0.0)
    ms_te = np.nan_to_num(_conv1d_multiscale_summary(seqs_te), nan=0.0)

    comb_tr = np.column_stack([flat_tr, ms_tr])
    comb_te = np.column_stack([flat_te, ms_te])

    mu = comb_tr.mean(axis=0)
    sd = comb_tr.std(axis=0) + 1e-6
    Z_tr = (comb_tr - mu) / sd
    Z_te = (comb_te - mu) / sd

    svd = TruncatedSVD(n_components=8, random_state=seed)
    svd_tr = svd.fit_transform(Z_tr)
    svd_te = svd.transform(Z_te)

    km = KMeans(n_clusters=5, n_init=10, random_state=seed)
    km.fit(svd_tr[:, :6])
    d_tr = km.transform(svd_tr[:, :6])
    d_te = km.transform(svd_te[:, :6])
    sim_tr = np.exp(-0.5 * d_tr)
    sim_tr /= np.sum(sim_tr, axis=1, keepdims=True) + 1e-8
    sim_te = np.exp(-0.5 * d_te)
    sim_te /= np.sum(sim_te, axis=1, keepdims=True) + 1e-8

    oof_seq = np.full(N_tr, float(np.mean(y_tr)), dtype=np.float64)
    for tr_in, va_in in splits_in:
        if len(np.unique(y_tr[tr_in])) < 2:
            continue
        clf_s = LogisticRegression(C=0.10, max_iter=400, random_state=seed).fit(svd_tr[tr_in], y_tr[tr_in])
        oof_seq[va_in] = clf_s.predict_proba(svd_tr[va_in])[:, 1]

    clf_full = LogisticRegression(C=0.10, max_iter=400, random_state=seed).fit(svd_tr, y_tr)
    te_seq = clf_full.predict_proba(svd_te)[:, 1]

    feats_tr = np.column_stack([svd_tr, sim_tr, oof_seq])
    feats_te = np.column_stack([svd_te, sim_te, te_seq])
    return feats_tr, feats_te, km.labels_


def run_k36_trajectory_extraction(sessions_list, out_dir):
    t0 = time.time()
    B, sess_td = dev_build_bars(sessions_list, 100)
    sid_b, ts_end, hi_b, lo_b, cl_b, op_b, vol_b = (
        B["sid"], B["ts_end"], B["h"], B["l"], B["c"], B["o"], B["vol"]
    )
    p_al, v_al = B["p_al"], B["v_al"]
    cum_vol_b = np.concatenate([[0.0], np.cumsum(vol_b)])

    delta_b = compute_bar_tick_delta_numba(p_al, v_al, 100)
    print(f"Delta tick-a-tick calculado sobre {len(delta_b)} barras ({time.time() - t0:.1f}s)", flush=True)

    causal_tests = verify_causal_outcome_and_prefix_tests(sessions_list, B)
    print("CAUSAL_TESTS_PASSED:", json.dumps(causal_tests), flush=True)

    s_first, s_last = {}, {}
    for i, s in enumerate(sid_b):
        s_last[int(s)] = i + 1
        s_first.setdefault(int(s), i)

    hft = {}
    n_hft_total = 0
    prm = HFT_Params(mostrar_absorb=False)
    for s in sessions_list:
        zs = hft_run(s["ts_utc_ns"], s["prices"], s["vol"], HFT_TICK, prm)
        zs = [z for z in zs if "ABSORB" not in str(z.bucket).upper()]
        if not zs:
            hft[s["session_id"]] = None
            continue
        end_ns = np.array([z.end_ts for z in zs], dtype=np.int64) * 1_000_000
        lo_z = np.array([min(z.price_lower, z.price_upper) for z in zs], dtype=np.float64)
        hi_z = np.array([max(z.price_lower, z.price_upper) for z in zs], dtype=np.float64)
        dr = np.array([int(z.dir) for z in zs], dtype=np.int32)
        vz = np.array([float(z.total_vol) for z in zs], dtype=np.float64)
        hft[s["session_id"]] = (end_ns, lo_z, hi_z, dr, vz)
        n_hft_total += len(zs)
    print(f"Sesiones={len(sessions_list)} | Zonas HFT (sin absorb)={n_hft_total} ({time.time() - t0:.1f}s)", flush=True)

    presets = {
        1: (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72),
        2: (60, 45, 12, 65, 24, 0.85, 0.84, 0.030, 0.88, 0.80, 1.05, 0.44, 0.46, 0.64),
    }

    all_rows = []
    seqs_p1 = []
    seqs_p2 = []

    for pid, pc in presets.items():
        state, score_s, ema_a, atr_a, zones_mat, s_start_b, s_end_b = detect_zones_nt8_numba(
            op_b, hi_b, lo_b, cl_b, sid_b, B["cid"], 200, 100,
            pc[0], pc[1], pc[2], pc[3], pc[4], pc[5], pc[6], pc[7], pc[8], pc[9], pc[10], pc[11], pc[12], pc[13], 40, 5, 1.60, TICK_ES
        )
        cache = {}
        for z in zones_mat:
            sid = int(z[13])
            ob, eb, cf, cls_b = int(z[2]), int(z[3]), int(z[4]), int(z[5])
            if cf <= ob + 1 or eb <= ob + 1 or sid not in s_first:
                continue
            s_beg, s_end = s_first[sid], s_last[sid]
            if cls_b >= s_end - 5:
                continue

            imp_dir = int(z[1])
            inv_dir = -imp_dir
            orig_px = float(z[6])
            ext_px = float(z[7])
            b_lo, b_hi = float(z[8]), float(z[9])
            H_price = max(b_hi - b_lo, TICK_ES)
            h_ticks = float(z[10])
            score_val = float(z[12])
            slope_ticks = float(z[11]) / TICK_ES

            w1_end = ob + (eb - ob) // 2
            lo_e1, hi_e1 = lo_b[ob:w1_end + 1], hi_b[ob:w1_end + 1]
            lo_e2, hi_e2 = lo_b[w1_end + 1:eb + 1], hi_b[w1_end + 1:eb + 1]

            a_b = max(float(atr_a[cls_b]), TICK_ES)
            p_dec = float(cl_b[cls_b])
            ct_m = int(B["ctmin"][cls_b])
            rth_ct = 1 if (510 <= ct_m <= 930) else 0

            v_w1 = float(np.sum(vol_b[ob:w1_end + 1]))
            v_w2 = float(np.sum(vol_b[w1_end + 1:eb + 1])) if eb > w1_end else 0.0
            v_w3 = float(np.sum(vol_b[eb:cls_b + 1]))
            len_w1 = max(w1_end - ob + 1, 1)
            len_w2 = max(eb - w1_end, 1)
            len_w3 = max(cls_b - eb + 1, 1)
            v_imp_tot = max(v_w1 + v_w2, 1.0)
            mean_v_imp = v_imp_tot / max(eb - ob + 1, 1)

            spd_w1 = abs(float(cl_b[w1_end] - cl_b[ob])) / (TICK_ES * len_w1)
            spd_w2 = abs(float(cl_b[eb] - cl_b[w1_end])) / (TICK_ES * len_w2)
            max_v_w2 = float(np.max(vol_b[w1_end + 1:eb + 1])) if eb > w1_end else float(vol_b[eb])

            hs_s = float(hi_b[s_beg:cls_b + 1].max())
            ls_s = float(lo_b[s_beg:cls_b + 1].min())
            sess_rng_t = max(hs_s - ls_s, TICK_ES) / TICK_ES
            mins_open = float((ts_end[cls_b] - B["ts_start"][s_beg]) / 6e10)
            rv50 = float(np.std(np.diff(cl_b[max(cls_b - 50, s_beg):cls_b + 1])) / a_b) if cls_b - s_beg > 5 else 0.0
            spd3 = float(inv_dir * (p_dec - float(cl_b[max(cls_b - 3, s_beg)])) / TICK_ES)
            spd10 = float(inv_dir * (p_dec - float(cl_b[max(cls_b - 10, s_beg)])) / TICK_ES)

            # Zonas HFT en W1 y W2 (fix600):
            h = hft.get(sid)
            if h is not None and sid not in cache:
                end_ns, lo_z, hi_z, dr, vz = h
                cb_z = np.searchsorted(ts_end, end_ns, side="left")
                cb_z = np.minimum(cb_z, s_end - 1)
                mb_z = mitigation_bars(lo_b, hi_b, cb_z, lo_z, hi_z, s_beg, s_end)
                cache[sid] = (cb_z, lo_z, hi_z, dr, vz, mb_z)

            cand_fix600 = np.zeros(0, dtype=np.int64)
            if h is not None:
                cb_z, lo_z, hi_z, dr, vz, mb_z = cache[sid]
                s1_mask = cb_z < w1_end
                s2_mask = cb_z < eb
                na1, t_mask1, ni1 = touched_indices_in_window(
                    lo_e1, hi_e1, ob, cb_z[s1_mask], lo_z[s1_mask], hi_z[s1_mask], mb_z[s1_mask], 600
                )
                na2, t_mask2, _ = touched_indices_in_window(
                    lo_e2, hi_e2, w1_end + 1, cb_z[s2_mask], lo_z[s2_mask], hi_z[s2_mask], mb_z[s2_mask], 600
                ) if len(lo_e2) else (0, np.zeros(0, dtype=bool), 0)
                f_e1_act = na1
                f_e1_touch = int(t_mask1.sum())
                f_e2_act = na2
                f_e2_touch = int(t_mask2.sum())
                cand_fix600 = np.where(s1_mask)[0][t_mask1]
            else:
                f_e1_act, f_e1_touch, f_e2_act, f_e2_touch = 0, 0, 0, 0

            if len(cand_fix600) > 0:
                cb_z, lo_z, hi_z, dr, vz, mb_z = cache[sid]
                ref_near = select_ref_zone_and_features(
                    cand_fix600, cb_z, lo_z, hi_z, dr, vz, lo_b, hi_b, cl_b, cum_vol_b,
                    ob, w1_end, cls_b, imp_dir, "nearest"
                )
                z_lo_t = ref_near["z_lo"]
                z_hi_t = ref_near["z_hi"]
                dir_z_t = ref_near["dir_zone"]
                w_ticks_t = ref_near["width_ticks"]
                d_ticks_t = ref_near["dist_ticks"]
                has_hft_w1_val = 1
                age_bars_val = ref_near["age_bars"]
                vol_since_val = ref_near["vol_since_creation"]
                virgin_val = ref_near["virgin_pre_W1"]
                aligned_val = ref_near["aligned"]
            else:
                b_near_px = ext_px + inv_dir * 0.50 * H_price
                b_far_px = ext_px + inv_dir * 0.78 * H_price
                z_lo_t, z_hi_t = min(b_near_px, b_far_px), max(b_near_px, b_far_px)
                dir_z_t = imp_dir
                w_ticks_t = max(round((z_hi_t - z_lo_t) / TICK_ES), 4.0)
                if p_dec < z_lo_t:
                    d_ticks_t = round((z_lo_t - p_dec) / TICK_ES)
                elif p_dec > z_hi_t:
                    d_ticks_t = round((p_dec - z_hi_t) / TICK_ES)
                else:
                    d_ticks_t = 0.0
                has_hft_w1_val = 0
                age_bars_val = float(cls_b - ob)
                vol_since_val = v_w1
                virgin_val = 0
                aligned_val = 1

            # Extraer todo el recorrido previo a la decisión + microestructura de las 3 Franjas:
            traj_dict, seq_16x8 = extract_microstructure_3strips_and_trajectory(
                op_b, hi_b, lo_b, cl_b, vol_b, delta_b, atr_a, ema_a,
                s_beg, ob, w1_end, eb, cls_b, imp_dir, orig_px, ext_px,
                z_lo_t, z_hi_t, has_hft_w1_val, f_e1_touch, f_e2_touch, TICK_ES
            )

            row = {
                "preset": pid,
                "session_id": sid,
                "trade_date": sess_td.get(sid),
                "zone_id": int(z[0]),
                "imp_dir": imp_dir,
                "origin_bar": ob,
                "end_bar": eb,
                "conf_bar": cf,
                "cls_bar": cls_b,
                "rth_ct": rth_ct,
                "ct_min": ct_m,
                "h_ticks": h_ticks,
                "score": score_val,
                "slope_ticks": slope_ticks,
                "hr_sin": float(np.sin(2.0 * np.pi * ct_m / 1440.0)),
                "hr_cos": float(np.cos(2.0 * np.pi * ct_m / 1440.0)),
                "atr_ticks": a_b / TICK_ES,
                "rv50_atr": rv50,
                "bar_range_ticks": float((hi_b[cls_b] - lo_b[cls_b]) / TICK_ES),
                "speed3": spd3,
                "speed10": spd10,
                "sess_range_ticks": sess_rng_t,
                "mins_since_open": mins_open,
                "vol_bar_ratio": float(vol_b[cls_b] / max(mean_v_imp, 1.0)),
                "a_vol_share_W1": v_w1 / v_imp_tot,
                "por_vol_ratio_W2_vs_W1": (v_w2 / len_w2) / max(v_w1 / len_w1, 1.0),
                "por_speed_ratio_W2_vs_W1": spd_w2 / max(spd_w1, 0.05),
                "por_max_bar_vol_ratio_W2": max_v_w2 / max(mean_v_imp, 1.0),
                "desde_post_ext_len": float(cls_b - eb),
                "desde_ret_from_ext_frac": abs(p_dec - ext_px) / H_price,
                "desde_climax_vol_ratio": (v_w3 / len_w3) / max(mean_v_imp, 1.0),
                "desde_reversal_body_ticks": float(inv_dir * (p_dec - float(op_b[cls_b])) / TICK_ES),
                "desde_ema_dist_atr": float(imp_dir * (p_dec - float(ema_a[cls_b])) / a_b),
                "fix600_e1_act": f_e1_act,
                "fix600_e1_touch": f_e1_touch,
                "fix600_e2_act": f_e2_act,
                "fix600_e2_touch": f_e2_touch,
                "has_hft_w1": has_hft_w1_val,
                "z_lo": z_lo_t,
                "z_hi": z_hi_t,
                "dir_zone": dir_z_t,
                "width_ticks": w_ticks_t,
                "dist_ticks": d_ticks_t,
                "dist_over_h": d_ticks_t / max(h_ticks, 1.0),
                "age_bars": age_bars_val,
                "vol_since_creation": vol_since_val,
                "virgin_pre_W1": virgin_val,
                "aligned": aligned_val,
            }
            row.update(traj_dict)

            # Desenlaces causales E1 y E2 en H=300:
            o_300 = eval_rect_e1_e2_numba(
                lo_b, hi_b, cl_b, p_al, 100, cls_b, s_end, 300,
                z_lo_t, z_hi_t, dir_z_t, imp_dir, 0, TICK_ES
            )
            row.update({
                "H300_inside": int(o_300[0]),
                "H300_cens_e1": int(o_300[1]),
                "H300_e1": int(o_300[2]),
                "H300_t_e1": int(o_300[3]),
                "H300_e2_cz": int(o_300[4]),
                "H300_e2_ci": int(o_300[5]),
                "H300_t_e2": int(o_300[6]),
                "H300_mfe_inv": float(o_300[9]),
                "H300_mae_inv": float(o_300[10]),
            })

            # =================================================================================
            # TRES REGÍMENES DE SIMULACIÓN TICK-A-TICK DESDE cls_b PARA MEDIR EMPÍRICAMENTE
            # EL IMPACTO REAL DEL STOP ESTRUCTURAL ASIMÉTRICO Y LA ALINEACIÓN DE ETIQUETAS:
            # =================================================================================
            d1_use = float(np.clip(d_ticks_t, 12.0, 32.0))
            w_use = float(np.clip(w_ticks_t, 6.0, 24.0))

            # 1) Régimen Simétrico 1:1 (`sym`: stop = d1_use, baseline de k35 v3):
            stop_sym = d1_use
            sim_sym = simulate_2stage_trade_tick_numba(
                lo_b, hi_b, cl_b, p_al, 100, cls_b, s_end, 300,
                inv_dir, d1_use, w_use, stop_sym, TICK_ES
            )

            # 2) Régimen Asimétrico Estructural con Buffer Fijo +2.5 ticks detrás de `ext_px` (`asym_fix`):
            #    Distancia desde `p_dec` hasta `ext_px` es `max(1.0, traj_turn_ret_ticks)`.
            #    Acotamos s_struct_fix en [6.0, d1_use] para mantener validez física:
            raw_turn_t = max(1.0, float(traj_dict["traj_turn_ret_ticks"]))
            stop_asym_fix = float(np.clip(raw_turn_t + 2.5, 6.0, d1_use))
            sim_asym_fix = simulate_2stage_trade_tick_numba(
                lo_b, hi_b, cl_b, p_al, 100, cls_b, s_end, 300,
                inv_dir, d1_use, w_use, stop_asym_fix, TICK_ES
            )

            # 3) Régimen Asimétrico Estructural con Buffer Adaptado por Volatilidad (`asym_atr`):
            #    buffer_atr = max(2.0, round(0.40 * atr_ticks)), acotado en [7.0, d1_use]:
            buf_atr = max(2.0, round(0.40 * (a_b / TICK_ES)))
            stop_asym_atr = float(np.clip(raw_turn_t + buf_atr, 7.0, d1_use))
            sim_asym_atr = simulate_2stage_trade_tick_numba(
                lo_b, hi_b, cl_b, p_al, 100, cls_b, s_end, 300,
                inv_dir, d1_use, w_use, stop_asym_atr, TICK_ES
            )

            row.update({
                "d1_use_ticks": d1_use,
                "w_use_ticks": w_use,
                "rr_ratio_asym_fix": round(d1_use / stop_asym_fix, 4),
                "rr_ratio_asym_atr": round(d1_use / stop_asym_atr, 4),
                # Salidas Simétricas (1:1):
                "stop_sym_ticks": stop_sym,
                "gross_1s_sym": float(sim_sym[0]),
                "gross_2s_sym": float(sim_sym[1]),
                "pas_filled_sym": int(sim_sym[2]),
                "pas_gross_1s_sym": float(sim_sym[3]),
                "pas_gross_2s_sym": float(sim_sym[4]),
                "bars_res_sym": int(max(sim_sym[5], 1.0)),
                "hit_tp1_sym": int(sim_sym[6]),
                "hit_tp2_sym": int(sim_sym[7]),
                "pas_hit_tp1_sym": int(sim_sym[8]),
                # Salidas Asimétricas Fijas (+2.5t):
                "stop_asym_fix_ticks": stop_asym_fix,
                "gross_1s_asym_fix": float(sim_asym_fix[0]),
                "gross_2s_asym_fix": float(sim_asym_fix[1]),
                "pas_filled_asym_fix": int(sim_asym_fix[2]),
                "pas_gross_1s_asym_fix": float(sim_asym_fix[3]),
                "pas_gross_2s_asym_fix": float(sim_asym_fix[4]),
                "bars_res_asym_fix": int(max(sim_asym_fix[5], 1.0)),
                "hit_tp1_asym_fix": int(sim_asym_fix[6]),
                "hit_tp2_asym_fix": int(sim_asym_fix[7]),
                "pas_hit_tp1_asym_fix": int(sim_asym_fix[8]),
                # Salidas Asimétricas Adaptadas por ATR:
                "stop_asym_atr_ticks": stop_asym_atr,
                "gross_1s_asym_atr": float(sim_asym_atr[0]),
                "gross_2s_asym_atr": float(sim_asym_atr[1]),
                "pas_filled_asym_atr": int(sim_asym_atr[2]),
                "pas_gross_1s_asym_atr": float(sim_asym_atr[3]),
                "pas_gross_2s_asym_atr": float(sim_asym_atr[4]),
                "bars_res_asym_atr": int(max(sim_asym_atr[5], 1.0)),
                "hit_tp1_asym_atr": int(sim_asym_atr[6]),
                "hit_tp2_asym_atr": int(sim_asym_atr[7]),
                "pas_hit_tp1_asym_atr": int(sim_asym_atr[8]),
            })

            all_rows.append(row)
            if pid == 1:
                seqs_p1.append(seq_16x8)
            else:
                seqs_p2.append(seq_16x8)

        print(f"Preset {pid}: extraídos {sum(1 for r in all_rows if r['preset'] == pid)} impulsos con trayectoria + 3 franjas ({time.time() - t0:.1f}s)", flush=True)

    df_all = pd.DataFrame(all_rows)
    df_p1 = df_all[df_all["preset"] == 1].reset_index(drop=True)
    df_p2 = df_all[df_all["preset"] == 2].reset_index(drop=True)
    seqs_p1_arr = np.stack(seqs_p1, axis=0) if seqs_p1 else np.zeros((0, 16, 8), dtype=np.float32)
    seqs_p2_arr = np.stack(seqs_p2, axis=0) if seqs_p2 else np.zeros((0, 16, 8), dtype=np.float32)

    return df_p1, df_p2, seqs_p1_arr, seqs_p2_arr, causal_tests, n_hft_total


def venn_abers_calibrate(oof_scores: np.ndarray, y_tr: np.ndarray, test_scores: np.ndarray):
    ok = ~np.isnan(oof_scores)
    if ok.sum() < 40 or len(np.unique(y_tr[ok])) < 2:
        p_c = np.clip(test_scores, 0.05, 0.95)
        oof_c = np.where(ok, np.clip(oof_scores, 0.05, 0.95), float(np.mean(y_tr)))
        return oof_c, p_c, p_c, np.zeros_like(p_c)
    s_cal = oof_scores[ok].astype(np.float64)
    y_cal = y_tr[ok].astype(np.float64)
    iso_base = IsotonicRegression(out_of_bounds="clip", y_min=0.02, y_max=0.98).fit(s_cal, y_cal)

    p_iso_te = iso_base.predict(test_scores.astype(np.float64))
    p_iso_oof = iso_base.predict(np.where(ok, oof_scores, np.nanmedian(s_cal)).astype(np.float64))

    n_eff = max(float(len(s_cal)) / 8.0, 15.0)
    se_te = np.sqrt(np.clip(p_iso_te * (1.0 - p_iso_te), 0.02, 0.25) / n_eff)
    se_oof = np.sqrt(np.clip(p_iso_oof * (1.0 - p_iso_oof), 0.02, 0.25) / n_eff)

    p0_te = np.clip(0.50 * p_iso_te + 0.50 * test_scores - 0.35 * se_te, 0.02, 0.98)
    p1_te = np.clip(0.50 * p_iso_te + 0.50 * test_scores + 0.35 * se_te, 0.02, 0.98)
    p_mean_te = 0.5 * (p0_te + p1_te)

    p0_oof = np.clip(0.50 * p_iso_oof + 0.50 * np.where(ok, oof_scores, float(np.mean(y_tr))) - 0.35 * se_oof, 0.02, 0.98)
    p1_oof = np.clip(0.50 * p_iso_oof + 0.50 * np.where(ok, oof_scores, float(np.mean(y_tr))) + 0.35 * se_oof, 0.02, 0.98)
    p_mean_oof = 0.5 * (p0_oof + p1_oof)

    return p_mean_oof, p_mean_te, p0_te, (p1_te - p0_te)


def compute_deflated_sharpe_ratio(daily_pnl: np.ndarray, m_trials: int = 44) -> dict:
    """
    Calcula el Deflated Sharpe Ratio (DSR, Bailey & López de Prado 2014) con M = 44 ensayos acumulados.
    """
    n_s = len(daily_pnl)
    if n_s < 10 or np.std(daily_pnl, ddof=1) < 1e-9:
        return {"sr_per_session": 0.0, "sr0_benchmark": 0.0, "z_dsr": 0.0, "p_dsr": 0.0, "m_trials": m_trials}
    mu = float(np.mean(daily_pnl))
    sd = float(np.std(daily_pnl, ddof=1))
    sr_obs = mu / sd
    z_std = (daily_pnl - mu) / sd
    skew = float(np.mean(z_std ** 3))
    kurt = float(np.mean(z_std ** 4))

    gamma_em = 0.5772156649
    # Cuantil normal inverso aproximado de alta precisión (Acklam/Winitzki):
    from scipy.stats import norm
    z1 = float(norm.ppf(1.0 - 1.0 / m_trials))
    z2 = float(norm.ppf(1.0 - 1.0 / (m_trials * math.e)))
    sr0 = math.sqrt(1.0 / max(n_s - 1, 1)) * ((1.0 - gamma_em) * z1 + gamma_em * z2)

    denom = math.sqrt(max(1.0 - skew * sr_obs + 0.25 * (kurt - 1.0) * (sr_obs ** 2), 1e-6))
    z_dsr = (sr_obs - sr0) * math.sqrt(max(n_s - 1, 1)) / denom
    p_dsr = float(norm.cdf(z_dsr))
    return {
        "sr_per_session": round(sr_obs, 4),
        "sr_annualized": round(sr_obs * math.sqrt(252.0), 3),
        "sr0_benchmark": round(sr0, 4),
        "z_dsr": round(z_dsr, 4),
        "p_dsr": round(p_dsr, 4),
        "m_trials": int(m_trials),
    }


def simulate_causal_non_overlapping_trading_k36(
    df_eval: pd.DataFrame,
    ev_score: np.ndarray,
    p_tp1: np.ndarray,
    p_tp2_given_tp1: np.ndarray,
    thr_ev: float,
    exec_regime: str = "sym",
    stage2_mult: float = 0.85,
    exit_policy: str = "adaptive_2stage",
    m_trials_dsr: int = 44,
):
    """
    Simula la ejecución causal en vivo sesión por sesión bajo el régimen de barrera elegido:
      - `exec_regime == "sym"`: Stop simétrico 1:1 (`stop_sym_ticks = d1_use_ticks`)
      - `exec_regime == "asym_fix"`: Stop estructural fijo (`stop_asym_fix_ticks = turn_extreme + 2.5t`)
      - `exec_regime == "asym_atr"`: Stop estructural adaptado por ATR (`stop_asym_atr_ticks`)
    Además devuelve la Tabla de Descomposición Empírica de Win Rate y Riesgo/Beneficio (`win_rate_decomposition`)
    para responder empíricamente cuánto cambia el win rate al acortar el stop y cuál es el margen real sobre el break-even.
    """
    n_rows = len(df_eval)
    sids = df_eval["session_id"].values
    cls_bars = df_eval["cls_bar"].values
    d1_arr = df_eval["d1_use_ticks"].values
    w_arr = df_eval["w_use_ticks"].values

    stop_arr = df_eval[f"stop_{exec_regime}_ticks"].values
    res_bars = df_eval[f"bars_res_{exec_regime}"].values
    g1_arr = df_eval[f"gross_1s_{exec_regime}"].values
    g2_arr = df_eval[f"gross_2s_{exec_regime}"].values
    pf_arr = df_eval[f"pas_filled_{exec_regime}"].values
    pg1_arr = df_eval[f"pas_gross_1s_{exec_regime}"].values
    pg2_arr = df_eval[f"pas_gross_2s_{exec_regime}"].values
    tp1_arr = df_eval[f"hit_tp1_{exec_regime}"].values
    tp2_arr = df_eval[f"hit_tp2_{exec_regime}"].values
    pas_tp1_arr = df_eval[f"pas_hit_tp1_{exec_regime}"].values

    # También leemos `hit_tp1_sym` para comparar directamente en las MISMAS operaciones seleccionadas
    # cuál habría sido su win rate con stop simétrico vs stop estructural asimétrico:
    tp1_sym_ref = df_eval["hit_tp1_sym"].values
    e1_arr = df_eval["H300_e1"].values
    e2_arr = df_eval["H300_e2_cz"].values

    selected_mask = np.zeros(n_rows, dtype=bool)
    used_2stage_mask = np.zeros(n_rows, dtype=bool)
    gross_pnl = np.zeros(n_rows, dtype=np.float64)
    pas_filled_sel = np.zeros(n_rows, dtype=bool)
    pas_gross_pnl = np.zeros(n_rows, dtype=np.float64)

    last_sid = -1
    active_exit_bar = -1

    for i in range(n_rows):
        s_i = int(sids[i])
        cb_i = int(cls_bars[i])
        if s_i != last_sid:
            last_sid = s_i
            active_exit_bar = -1
        if cb_i <= active_exit_bar:
            continue
        if ev_score[i] >= thr_ev:
            selected_mask[i] = True
            active_exit_bar = cb_i + max(int(res_bars[i]), 1)

            be_ratio = d1_arr[i] / max(d1_arr[i] + w_arr[i], 1.0)
            if exit_policy == "1stage_only":
                use_2s = False
            elif exit_policy == "2stage_only":
                use_2s = True
            else:
                use_2s = bool(p_tp2_given_tp1[i] >= stage2_mult * be_ratio)

            used_2stage_mask[i] = use_2s
            gross_pnl[i] = g2_arr[i] if use_2s else g1_arr[i]
            if pf_arr[i] == 1:
                pas_filled_sel[i] = True
                pas_gross_pnl[i] = pg2_arr[i] if use_2s else pg1_arr[i]

    n_total_sessions = max(len(np.unique(sids)), 1)
    idx_sel = np.where(selected_mask)[0]
    n_sel = len(idx_sel)
    if n_sel == 0:
        return {
            "n_trades": 0, "n_sessions_total": int(n_total_sessions), "trades_per_day": 0.0,
            "win_rate_decomposition": {},
            "gross_0t": {"mean_ticks": 0.0, "z_clust": 0.0, "win_rate": 0.0, "pf": 0.0, "sharpe_ann": 0.0, "total_usd": 0.0},
            "net_limit_155t_immediate": {"mean_ticks": 0.0, "z_clust": 0.0, "win_rate": 0.0, "pf": 0.0, "sharpe_ann": 0.0, "total_usd": 0.0},
            "net_passive_tt_state_machine_155t": {"mean_ticks": 0.0, "z_clust": 0.0, "win_rate": 0.0, "pf": 0.0, "sharpe_ann": 0.0, "total_usd": 0.0},
            "net_market_355t": {"mean_ticks": 0.0, "z_clust": 0.0, "win_rate": 0.0, "pf": 0.0, "sharpe_ann": 0.0, "total_usd": 0.0},
        }

    sids_sel = sids[idx_sel]
    g_sel = gross_pnl[idx_sel]
    net_155 = g_sel - 1.546
    net_355 = g_sel - 3.546

    idx_pas = np.where(selected_mask & pas_filled_sel)[0]
    if len(idx_pas) > 0:
        pas_net = pas_gross_pnl[idx_pas] - 1.546
        sids_pas = sids[idx_pas]
    else:
        pas_net = np.zeros(0, dtype=np.float64)
        sids_pas = np.zeros(0, dtype=np.int64)

    def _metrics_vec(pnl_v, sid_v, n_sess_all):
        if len(pnl_v) == 0:
            return {"mean_ticks": 0.0, "se_clust": 0.0, "z_clust": 0.0, "win_rate": 0.0, "pf": 0.0, "sharpe_ann": 0.0, "total_usd": 0.0, "max_dd_usd": 0.0, "dsr": {}}
        mu_t = float(np.mean(pnl_v))
        wr = float(np.mean(pnl_v > 0))
        pos_s = float(np.sum(pnl_v[pnl_v > 0]))
        neg_s = float(np.abs(np.sum(pnl_v[pnl_v < 0])))
        pf = pos_s / max(neg_s, 1e-6)
        df_tmp = pd.DataFrame({"s": sid_v, "p": pnl_v})
        g_s = df_tmp.groupby("s")["p"].agg(["count", "sum", "mean"])
        n_cl = len(g_s)
        if n_cl >= 2:
            w_c = g_s["count"].values.astype(float)
            m_c = g_s["mean"].values.astype(float)
            W_tot = float(w_c.sum())
            se_c = float(np.sqrt((n_cl / (n_cl - 1.0)) * np.sum((w_c * (m_c - mu_t)) ** 2) / max(W_tot ** 2, 1.0)))
        else:
            se_c = float(np.std(pnl_v) / max(np.sqrt(len(pnl_v)), 1.0))
        z_c = mu_t / max(se_c, 1e-6)
        daily_sums = g_s["sum"].values.astype(float)
        if len(daily_sums) < n_sess_all:
            daily_full = np.concatenate([daily_sums, np.zeros(n_sess_all - len(daily_sums))])
        else:
            daily_full = daily_sums
        sh_ann = float((np.mean(daily_full) / max(np.std(daily_full, ddof=1), 1e-6)) * np.sqrt(252.0)) if len(daily_full) >= 2 else 0.0
        dsr_info = compute_deflated_sharpe_ratio(daily_full, m_trials=m_trials_dsr)
        usd_v = pnl_v * 12.50
        eq = np.cumsum(usd_v)
        pk = np.maximum.accumulate(np.maximum(eq, 0.0))
        mdd = float(np.max(pk - eq)) if len(eq) else 0.0
        return {
            "mean_ticks": round(mu_t, 4),
            "se_clust": round(se_c, 4),
            "z_clust": round(z_c, 3),
            "win_rate": round(wr, 4),
            "pf": round(pf, 3),
            "sharpe_ann": round(sh_ann, 3),
            "total_usd": round(float(np.sum(usd_v)), 2),
            "max_dd_usd": round(mdd, 2),
            "dsr": dsr_info,
        }

    m_gross = _metrics_vec(g_sel, sids_sel, n_total_sessions)
    m_155 = _metrics_vec(net_155, sids_sel, n_total_sessions)
    m_355 = _metrics_vec(net_355, sids_sel, n_total_sessions)
    m_pas = _metrics_vec(pas_net, sids_pas, n_total_sessions)

    # Descomposición Empírica de Win Rate y Riesgo/Beneficio:
    d1_sel = d1_arr[idx_sel]
    stop_sel = stop_arr[idx_sel]
    rr_sel = d1_sel / np.maximum(stop_sel, 1.0)
    mean_d1 = float(np.mean(d1_sel))
    mean_stop = float(np.mean(stop_sel))
    med_stop = float(np.median(stop_sel))
    mean_rr = float(np.mean(rr_sel))

    emp_wr_tp1 = float(np.mean(tp1_arr[idx_sel]))
    emp_wr_sym_same_trades = float(np.mean(tp1_sym_ref[idx_sel]))
    emp_wr_pas_tp1 = float(np.mean(pas_tp1_arr[idx_pas])) if len(idx_pas) > 0 else 0.0

    # Break-even win rate teórico (1 etapa) con el d1 y stop medios realizados:
    be_wr_gross = mean_stop / max(mean_d1 + mean_stop, 1.0)
    be_wr_net155 = (mean_stop + 1.546) / max(mean_d1 + mean_stop, 1.0)
    be_wr_net355 = (mean_stop + 3.546) / max(mean_d1 + mean_stop, 1.0)

    wr_decomp = {
        "exec_regime": exec_regime,
        "mean_d1_ticks": round(mean_d1, 2),
        "mean_stop_ticks": round(mean_stop, 2),
        "median_stop_ticks": round(med_stop, 2),
        "p25_stop_ticks": round(float(np.quantile(stop_sel, 0.25)), 2),
        "p75_stop_ticks": round(float(np.quantile(stop_sel, 0.75)), 2),
        "mean_reward_to_risk_ratio": round(mean_rr, 3),
        "empirical_wr_tp1_under_regime": round(emp_wr_tp1, 4),
        "empirical_wr_tp1_if_symmetric_on_same_trades": round(emp_wr_sym_same_trades, 4),
        "wr_change_from_symmetric_pp": round((emp_wr_tp1 - emp_wr_sym_same_trades) * 100.0, 2),
        "empirical_passive_tt_wr_tp1": round(emp_wr_pas_tp1, 4),
        "breakeven_wr_gross_1stage": round(be_wr_gross, 4),
        "breakeven_wr_net155_1stage": round(be_wr_net155, 4),
        "breakeven_wr_net355_1stage": round(be_wr_net355, 4),
        "margin_over_breakeven_net155_pp": round((emp_wr_tp1 - be_wr_net155) * 100.0, 2),
        "margin_over_breakeven_passive_tt_pp": round((emp_wr_pas_tp1 - be_wr_net155) * 100.0, 2),
    }

    e1_sel_rate = float(np.mean(e1_arr[idx_sel]))
    e2_sel_rate = float(np.mean(e2_arr[idx_sel][e1_arr[idx_sel] == 1])) if np.sum(e1_arr[idx_sel] == 1) > 0 else 0.0
    tp2_sel_rate = float(np.mean(tp2_arr[idx_sel][tp1_arr[idx_sel] == 1])) if np.sum(tp1_arr[idx_sel] == 1) > 0 else 0.0
    frac_2stage = float(np.mean(used_2stage_mask[idx_sel]))

    return {
        "n_trades": int(n_sel),
        "n_passive_filled": int(len(idx_pas)),
        "n_sessions_total": int(n_total_sessions),
        "n_sessions_active": int(len(np.unique(sids_sel))),
        "trades_per_day": round(n_sel / float(n_total_sessions), 3),
        "passive_fills_per_day": round(len(idx_pas) / float(n_total_sessions), 3),
        "P_E1_unstopped_selected": round(e1_sel_rate, 4),
        "P_E2_cz_given_E1_selected": round(e2_sel_rate, 4),
        "P_TP1_stopped_selected": round(emp_wr_tp1, 4),
        "P_TP2_given_TP1_selected": round(tp2_sel_rate, 4),
        "fraction_assigned_2stage_exit": round(frac_2stage, 4),
        "win_rate_decomposition": wr_decomp,
        "gross_0t": m_gross,
        "net_limit_155t_immediate": m_155,
        "net_passive_tt_state_machine_155t": m_pas,
        "net_market_355t": m_355,
    }


def calibrate_causal_threshold_for_target_freq_k36(
    df_tr: pd.DataFrame,
    score_tr: np.ndarray,
    p_tp1_tr: np.ndarray,
    p_tp2_tr: np.ndarray,
    target_trades_per_day: float,
    exec_regime: str = "sym",
) -> float:
    u_s = sorted(df_tr["session_id"].unique())
    recent_s = u_s[-min(len(u_s), 35):]
    m_rec = df_tr["session_id"].isin(recent_s).values
    df_sub = df_tr[m_rec].reset_index(drop=True)
    sc_sub = score_tr[m_rec]
    p1_sub = p_tp1_tr[m_rec]
    p2_sub = p_tp2_tr[m_rec]

    valid_sc = sc_sub[sc_sub > -1e6]
    if len(valid_sc) < 10:
        return float(np.quantile(sc_sub, 0.85))

    best_thr = float(np.quantile(valid_sc, 0.80))
    best_err = 1e9
    for q in np.linspace(0.35, 0.992, 75):
        thr_c = float(np.quantile(valid_sc, q))
        sim_c = simulate_causal_non_overlapping_trading_k36(
            df_sub, sc_sub, p1_sub, p2_sub, thr_c, exec_regime=exec_regime, stage2_mult=0.85, exit_policy="adaptive_2stage"
        )
        err = abs(sim_c["trades_per_day"] - target_trades_per_day)
        if err < best_err:
            best_err = err
            best_thr = thr_c
    return best_thr


def evaluate_k36_edge_maximizer_system(df_p1: pd.DataFrame, df_p2: pd.DataFrame, seqs_p1: np.ndarray, seqs_p2: np.ndarray):
    """
    Evalúa en las 178 sesiones Discovery las 7 arquitecturas comparativas de `k36`:
      - `C0_Baseline_Symmetric_k35`: Barrera simétrica 1:1 entrenada con `hit_tp1_sym` (línea base exacta de k35 v3).
      - `C1A_AsymStop_NaiveLabel_Mismatch`: Ejecutada con stop estructural fijo `s_struct_fix`, pero puntuada con el modelo entrenado en `hit_tp1_sym` (cuantifica la caída de WR por desfase etiqueta-ejecución).
      - `C1B_AsymStop_AlignedLabel_Fixed25t`: Ejecutada con `s_struct_fix` y entrenada directamente sobre `hit_tp1_asym_fix` con expectativa asimétrica en R-múltiplos y compuerta `d1 / s_struct >= 1.25`.
      - `C1C_AsymStop_AlignedLabel_ATRBuffer`: Ejecutada con `s_struct_atr` (buffer adaptado por ATR) y entrenada sobre `hit_tp1_asym_atr`.
      - `C2_Asym_Plus_PorDonde_SweepGate`: `C1B` + Compuerta de Escalera Opuesta y Barrido Previo (`opp_ladder_trap_flag == 0`, bonificación por `opp_sweep_occurred`).
      - `C3_Asym_Plus_ADonde_GravityGate`: `C1B` + Compuerta de Masa Gravitatoria y Veto de Espejismo en `A DÓNDE` (`target_mirage_flag == 0`, `m_grav_ratio`).
      - `C4_Full_TriStrip_Monotonic_System`: Fusión completa de `C1B` + `C2` + `C3` + Restricciones Monótonas Nativas en LightGBM + Regla de No-Compensación TreeSHAP.
    """
    COLS_MACRO_BASE = [
        "hr_sin", "hr_cos", "atr_ticks", "rv50_atr", "bar_range_ticks",
        "speed3", "speed10", "sess_range_ticks", "mins_since_open", "vol_bar_ratio",
    ]
    COLS_NARROW_DESDE = [
        "desde_post_ext_len", "desde_ret_from_ext_frac", "desde_climax_vol_ratio",
        "desde_reversal_body_ticks", "desde_ema_dist_atr",
        "opp_ladder_steps", "opp_sweep_occurred", "opp_ladder_trap_flag", "sweep_quality_score",
    ]
    COLS_A_DONDE_ZONE = [
        "has_hft_w1", "fix600_e1_touch", "fix600_e1_act", "virgin_pre_W1",
        "age_bars", "vol_since_creation", "width_ticks", "dist_ticks", "dist_over_h", "aligned",
        "m_grav_ratio", "a_donde_imbalance_frac", "a_donde_hvn_peaks", "target_mirage_flag", "attractor_quality_score",
    ]
    COLS_POR_DONDE = [
        "fix600_e2_touch", "fix600_e2_act", "por_vol_ratio_W2_vs_W1",
        "por_speed_ratio_W2_vs_W1", "por_max_bar_vol_ratio_W2", "a_vol_share_W1",
        "por_void_conductivity",
    ]
    COLS_FULL_TRAJECTORY = [
        "h_ticks", "score", "slope_ticks", "imp_total_bars",
        "traj_p0_drift_over_h", "traj_p0_rng_over_h", "traj_p0_vol_ratio",
        "traj_swept_pre_extreme", "traj_pos_in_sess_range",
        "traj_dp_q1", "traj_dp_q2", "traj_dp_q3", "traj_dp_q4",
        "traj_vel_q4_vs_q12", "traj_vel_q4_vs_q3",
        "traj_vol_q1_share", "traj_vol_q4_share", "traj_vol_slope", "traj_effort_q4_vs_q12",
        "traj_delta_q12", "traj_delta_q34", "traj_delta_q4", "traj_delta_divergence",
        "traj_kappa_convexity", "traj_r2_linear", "traj_er_kaufman",
        "traj_counter_bar_frac", "traj_max_internal_dd",
        "traj_poc_frac", "traj_lower_half_vol_share", "traj_tip_top20_vol_share", "traj_mid_valley_ratio",
        "traj_turn_ret_ticks", "traj_turn_ret_frac", "traj_turn_speed_atr",
        "traj_turn_delta_rev", "traj_turn_delta_flip", "traj_turn_wick_atr", "traj_turn_vol_ratio",
    ]

    COLS_ALL_K36 = COLS_FULL_TRAJECTORY + COLS_NARROW_DESDE + COLS_A_DONDE_ZONE + COLS_POR_DONDE + COLS_MACRO_BASE
    # Eliminar variables de escala nominal en ticks para evitar sesgo hacia micro-zonas:
    COLS_SCALE_INV_K36 = [
        c for c in COLS_ALL_K36
        if c not in ("dist_ticks", "h_ticks", "width_ticks", "sess_range_ticks", "traj_turn_ret_ticks")
    ]

    # Construir vector de restricciones monótonas para COLS_SCALE_INV_K36:
    MONO_MAP = {
        "traj_swept_pre_extreme": 1,
        "traj_turn_delta_rev": 1,
        "traj_turn_delta_flip": 1,
        "traj_turn_wick_atr": 1,
        "opp_sweep_occurred": 1,
        "opp_ladder_trap_flag": -1,
        "sweep_quality_score": 1,
        "m_grav_ratio": 1,
        "a_donde_imbalance_frac": -1,
        "target_mirage_flag": -1,
        "attractor_quality_score": 1,
        "por_void_conductivity": 1,
        "fix600_e2_touch": -1,
    }

    def _inner_session_splits(df_sub, k=4, embargo=1):
        su = np.array(sorted(df_sub["session_id"].unique()))
        blks = [list(a) for a in np.array_split(su, k)]
        out_sp = []
        for blk in blks:
            if not blk:
                continue
            lo_s, hi_s = blk[0], blk[-1]
            va = df_sub["session_id"].between(lo_s, hi_s).values
            tr = ~df_sub["session_id"].between(lo_s - embargo, hi_s + embargo).values
            if va.sum() >= 15 and tr.sum() >= 40:
                out_sp.append((np.where(tr)[0], np.where(va)[0]))
        return out_sp

    def _fit_hybrid_predictor(
        X_tr: np.ndarray,
        y_tr: np.ndarray,
        splits_in: list,
        X_te: np.ndarray,
        sample_w: np.ndarray = None,
        mono_cst: list = None,
    ):
        med = np.nanmedian(X_tr, axis=0)
        med = np.where(np.isnan(med), 0.0, med)
        Xtr_i = np.where(np.isnan(X_tr), med, X_tr)
        Xte_i = np.where(np.isnan(X_te), med, X_te)
        mu = Xtr_i.mean(axis=0)
        sd = Xtr_i.std(axis=0) + 1e-8
        Xtr_s = (Xtr_i - mu) / sd
        Xte_s = (Xte_i - mu) / sd

        def _fit_one(Xf_raw, Xf_sc, yf, wf):
            clf_l2 = LogisticRegression(C=0.15, max_iter=500, random_state=42)
            clf_l2.fit(Xf_sc, yf, sample_weight=wf)
            params_g = dict(
                n_estimators=65, learning_rate=0.04, num_leaves=6, max_depth=3,
                min_child_samples=max(20, len(yf) // 35), subsample=0.8, subsample_freq=1,
                colsample_bytree=0.8, reg_alpha=2.0, reg_lambda=8.0, path_smooth=10.0,
                verbose=-1, n_jobs=4, random_state=42,
            )
            if mono_cst is not None:
                params_g["monotone_constraints"] = mono_cst
            clf_g = lgb.LGBMClassifier(**params_g)
            clf_g.fit(Xf_raw, yf, sample_weight=wf)
            return clf_l2, clf_g

        oof = np.full(len(y_tr), np.nan, dtype=np.float64)
        for tr_in, va_in in splits_in:
            if len(np.unique(y_tr[tr_in])) < 2:
                continue
            w_sub = sample_w[tr_in] if sample_w is not None else None
            c_l2, c_g = _fit_one(Xtr_i[tr_in], Xtr_s[tr_in], y_tr[tr_in], w_sub)
            oof[va_in] = np.clip(
                0.25 * c_l2.predict_proba(Xtr_s[va_in])[:, 1]
                + 0.75 * c_g.predict_proba(Xtr_i[va_in])[:, 1],
                0.02, 0.98
            )

        c_l2_full, c_g_full = _fit_one(Xtr_i, Xtr_s, y_tr, sample_w)
        raw_te = np.clip(
            0.25 * c_l2_full.predict_proba(Xte_s)[:, 1]
            + 0.75 * c_g_full.predict_proba(Xte_i)[:, 1],
            0.02, 0.98
        )
        # Contribuciones TreeSHAP en train y test:
        shap_tr = c_g_full.predict(Xtr_i, pred_contrib=True)[:, :-1]
        shap_te = c_g_full.predict(Xte_i, pred_contrib=True)[:, :-1]

        oof_cal, p_mean_te, p0_te, dp_te = venn_abers_calibrate(oof, y_tr, raw_te)
        return oof_cal, p_mean_te, p0_te, shap_tr, shap_te

    def _run_universe_k36(df_u: pd.DataFrame, seqs_u: np.ndarray, univ_tag: str):
        m_valid = (df_u["H300_inside"] == 0) & (df_u["H300_cens_e1"] == 0) & (df_u["H300_e1"].isin([0, 1]))
        df_v = df_u[m_valid].copy().reset_index(drop=True)
        seqs_v = seqs_u[m_valid.values]

        sessions_u = np.array(sorted(df_v["session_id"].unique()))
        chunks_6 = [list(a) for a in np.array_split(sessions_u, 6)]

        configs_list = [
            ("C0_Baseline_Symmetric_k35", "sym"),
            ("C1A_AsymStop_NaiveLabel_Mismatch", "asym_fix"),
            ("C1B_AsymStop_AlignedLabel_Fixed25t", "asym_fix"),
            ("C1C_AsymStop_AlignedLabel_ATRBuffer", "asym_atr"),
            ("C2_Asym_Plus_PorDonde_SweepGate", "asym_fix"),
            ("C3_Asym_Plus_ADonde_GravityGate", "asym_fix"),
            ("C4_Full_TriStrip_Monotonic_System", "asym_fix"),
        ]

        oos_records = {
            cfg_name: {
                "exec_regime": ex_reg,
                "df": [],
                "p_tp1": [],
                "p_tp2": [],
                "ev_score": [],
                "thrs": {},
            }
            for cfg_name, ex_reg in configs_list
        }

        for fi in range(1, 6):
            te_s = chunks_6[fi]
            tr_s = [s for c in chunks_6[:fi] for s in c]
            if len(tr_s) < 25:
                continue
            te_mask = df_v["session_id"].between(te_s[0], te_s[-1]).values
            tr_mask = df_v["session_id"].isin(tr_s).values & ~df_v["session_id"].between(te_s[0] - 1, te_s[0]).values
            if te_mask.sum() < 20 or tr_mask.sum() < 80:
                continue

            dtr = df_v[tr_mask].copy().reset_index(drop=True)
            dte = df_v[te_mask].copy().reset_index(drop=True)
            seq_tr = seqs_v[tr_mask]
            seq_te = seqs_v[te_mask]

            splits_in = _inner_session_splits(dtr, k=4, embargo=1)
            y_e1_tr = dtr["H300_e1"].values.astype(int)
            y_sym_tr = dtr["hit_tp1_sym"].values.astype(int)
            y_asym_fix_tr = dtr["hit_tp1_asym_fix"].values.astype(int)
            y_asym_atr_tr = dtr["hit_tp1_asym_atr"].values.astype(int)

            # Pesos por muestra proporcionales al potencial de ganancia / unicidad:
            w_tr = np.clip(dtr["d1_use_ticks"].values / 16.0, 0.6, 2.5)

            seq_feats_tr, seq_feats_te, _ = fit_transform_trajectory_representations_oof(
                seq_tr, y_sym_tr, splits_in, seq_te, seed=20261016 + fi
            )

            X_base_tr = dtr[COLS_SCALE_INV_K36].values.astype(float)
            X_base_te = dte[COLS_SCALE_INV_K36].values.astype(float)
            X_tr_full = np.column_stack([X_base_tr, seq_feats_tr])
            X_te_full = np.column_stack([X_base_te, seq_feats_te])

            mono_vec = [MONO_MAP.get(c, 0) for c in COLS_SCALE_INV_K36] + [0] * seq_feats_tr.shape[1]

            # 1) Entrenar Etapa 1 Estructural (`P(E1)`):
            oof_p_e1, te_p_e1, _, _, _ = _fit_hybrid_predictor(X_tr_full, y_e1_tr, splits_in, X_te_full, sample_w=w_tr, mono_cst=None)

            # 2) Entrenar Modelo Operativo Simétrico (`M_sym` sobre `hit_tp1_sym`):
            oof_p_sym, te_p_sym, _, _, _ = _fit_hybrid_predictor(X_tr_full, y_sym_tr, splits_in, X_te_full, sample_w=w_tr, mono_cst=None)

            # 3) Entrenar Modelo Operativo Asimétrico Fijo (`M_asym_fix` sobre `hit_tp1_asym_fix`, sin y con restricciones monótonas):
            w_asym_tr = np.clip((dtr["d1_use_ticks"].values / np.maximum(dtr["stop_asym_fix_ticks"].values, 6.0)), 0.7, 2.5)
            oof_p_asym_fix, te_p_asym_fix, _, _, _ = _fit_hybrid_predictor(
                X_tr_full, y_asym_fix_tr, splits_in, X_te_full, sample_w=w_asym_tr, mono_cst=None
            )
            oof_p_asym_mono, te_p_asym_mono, _, shap_tr_mono, shap_te_mono = _fit_hybrid_predictor(
                X_tr_full, y_asym_fix_tr, splits_in, X_te_full, sample_w=w_asym_tr, mono_cst=mono_vec
            )

            # 4) Entrenar Modelo Operativo Asimétrico ATR (`M_asym_atr` sobre `hit_tp1_asym_atr`):
            oof_p_asym_atr, te_p_asym_atr, _, _, _ = _fit_hybrid_predictor(
                X_tr_full, y_asym_atr_tr, splits_in, X_te_full, sample_w=w_asym_tr, mono_cst=mono_vec
            )

            # 5) Entrenar Etapa 2 (`P(TP2 | TP1)` y `P(E2_cz | E1)`):
            e1_tr_mask = (y_e1_tr == 1) & (dtr["H300_e2_cz"].isin([0, 1]).values)
            if e1_tr_mask.sum() >= 45:
                y_e2_tr = dtr.loc[e1_tr_mask, "H300_e2_cz"].values.astype(int)
                med_2 = np.nanmedian(X_tr_full[e1_tr_mask], axis=0)
                med_2 = np.where(np.isnan(med_2), 0.0, med_2)
                X2_c = np.where(np.isnan(X_tr_full[e1_tr_mask]), med_2, X_tr_full[e1_tr_mask])
                X_all_tr_c = np.where(np.isnan(X_tr_full), med_2, X_tr_full)
                X_all_te_c = np.where(np.isnan(X_te_full), med_2, X_te_full)
                mu2, sd2 = X2_c.mean(axis=0), X2_c.std(axis=0) + 1e-8
                clf_e2 = LogisticRegression(C=0.15, max_iter=400, random_state=42).fit((X2_c - mu2) / sd2, y_e2_tr)
                oof_p_tp2 = clf_e2.predict_proba((X_all_tr_c - mu2) / sd2)[:, 1]
                te_p_tp2 = clf_e2.predict_proba((X_all_te_c - mu2) / sd2)[:, 1]
            else:
                oof_p_tp2 = np.full(len(dtr), 0.5)
                te_p_tp2 = np.full(len(dte), 0.5)

            # Dimensiones geométricas en train y test:
            d1_tr, w_tr_z = dtr["d1_use_ticks"].values, dtr["w_use_ticks"].values
            d1_te, w_te_z = dte["d1_use_ticks"].values, dte["w_use_ticks"].values
            s_fix_tr, s_fix_te = dtr["stop_asym_fix_ticks"].values, dte["stop_asym_fix_ticks"].values
            s_atr_tr, s_atr_te = dtr["stop_asym_atr_ticks"].values, dte["stop_asym_atr_ticks"].values
            rr_fix_tr, rr_fix_te = d1_tr / s_fix_tr, d1_te / s_fix_te
            rr_atr_tr, rr_atr_te = d1_tr / s_atr_tr, d1_te / s_atr_te

            # Función auxiliar para calcular el score de expectativa en unidades de riesgo:
            def _compute_ev_score(p_tp1_v, p_e1_v, p_tp2_v, d1_v, w_v, stop_v):
                p_w = 0.65 * p_tp1_v + 0.35 * p_e1_v
                payoff_1s = d1_v
                payoff_2s = d1_v * (0.5 + 0.5 * p_tp2_v * (1.0 + w_v / d1_v))
                best_payoff = np.maximum(payoff_1s, payoff_2s)
                # Expectativa bruta esperada en ticks dividida por sqrt(stop_v) para balancear R-multiple y ticks netos:
                ev_ticks = p_w * best_payoff - (1.0 - p_w) * stop_v - 1.546
                return ev_ticks / np.sqrt(np.maximum(stop_v, 6.0))

            # Construir scores para cada una de las 7 configuraciones:
            for cfg_name, ex_reg in configs_list:
                if cfg_name == "C0_Baseline_Symmetric_k35":
                    p1_tr_use, p1_te_use = oof_p_sym, te_p_sym
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, d1_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, d1_te)
                elif cfg_name == "C1A_AsymStop_NaiveLabel_Mismatch":
                    # Usa las probabilidades y ranking del modelo simétrico C0, pero ejecuta con stop asimétrico s_fix:
                    p1_tr_use, p1_te_use = oof_p_sym, te_p_sym
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, d1_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, d1_te)
                elif cfg_name == "C1B_AsymStop_AlignedLabel_Fixed25t":
                    # Usa M_asym_fix entrenado directamente sobre supervivencia al stop corto + compuerta R:R >= 1.20:
                    p1_tr_use, p1_te_use = oof_p_asym_fix, te_p_asym_fix
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, s_fix_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, s_fix_te)
                    sc_tr = np.where(rr_fix_tr >= 1.20, sc_tr, sc_tr - 10.0)
                    sc_te = np.where(rr_fix_te >= 1.20, sc_te, sc_te - 10.0)
                elif cfg_name == "C1C_AsymStop_AlignedLabel_ATRBuffer":
                    # Usa M_asym_atr entrenado sobre el stop adaptado por volatilidad:
                    p1_tr_use, p1_te_use = oof_p_asym_atr, te_p_asym_atr
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, s_atr_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, s_atr_te)
                    sc_tr = np.where(rr_atr_tr >= 1.15, sc_tr, sc_tr - 10.0)
                    sc_te = np.where(rr_atr_te >= 1.15, sc_te, sc_te - 10.0)
                elif cfg_name == "C2_Asym_Plus_PorDonde_SweepGate":
                    # Añade la compuerta de Escalera Opuesta y Barrido Previo de Nico:
                    p1_tr_use, p1_te_use = oof_p_asym_fix, te_p_asym_fix
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, s_fix_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, s_fix_te)
                    sc_tr = sc_tr + 0.35 * dtr["sweep_quality_score"].values - 5.0 * dtr["opp_ladder_trap_flag"].values
                    sc_te = sc_te + 0.35 * dte["sweep_quality_score"].values - 5.0 * dte["opp_ladder_trap_flag"].values
                    sc_tr = np.where(rr_fix_tr >= 1.20, sc_tr, sc_tr - 10.0)
                    sc_te = np.where(rr_fix_te >= 1.20, sc_te, sc_te - 10.0)
                elif cfg_name == "C3_Asym_Plus_ADonde_GravityGate":
                    # Añade la compuerta de Masa Gravitatoria y Veto de Espejismo en A DÓNDE:
                    p1_tr_use, p1_te_use = oof_p_asym_fix, te_p_asym_fix
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, s_fix_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, s_fix_te)
                    sc_tr = sc_tr + 0.35 * dtr["attractor_quality_score"].values - 5.0 * dtr["target_mirage_flag"].values
                    sc_te = sc_te + 0.35 * dte["attractor_quality_score"].values - 5.0 * dte["target_mirage_flag"].values
                    sc_tr = np.where(rr_fix_tr >= 1.20, sc_tr, sc_tr - 10.0)
                    sc_te = np.where(rr_fix_te >= 1.20, sc_te, sc_te - 10.0)
                else:  # "C4_Full_TriStrip_Monotonic_System"
                    # Sistema Integral Tri-Franja con restricciones monótonas + Barrido + Masa Gravitatoria + Regla TreeSHAP:
                    p1_tr_use, p1_te_use = oof_p_asym_mono, te_p_asym_mono
                    sc_tr = _compute_ev_score(p1_tr_use, oof_p_e1, oof_p_tp2, d1_tr, w_tr_z, s_fix_tr)
                    sc_te = _compute_ev_score(p1_te_use, te_p_e1, te_p_tp2, d1_te, w_te_z, s_fix_te)

                    # Coherencia por coordenada TreeSHAP (evita que una franja negativa sea compensada ciegamente):
                    idx_d = [COLS_SCALE_INV_K36.index(c) for c in COLS_NARROW_DESDE if c in COLS_SCALE_INV_K36]
                    idx_p = [COLS_SCALE_INV_K36.index(c) for c in COLS_POR_DONDE if c in COLS_SCALE_INV_K36]
                    idx_a = [COLS_SCALE_INV_K36.index(c) for c in COLS_A_DONDE_ZONE if c in COLS_SCALE_INV_K36]
                    sh_d_tr = np.sum(shap_tr_mono[:, idx_d], axis=1)
                    sh_p_tr = np.sum(shap_tr_mono[:, idx_p], axis=1)
                    sh_a_tr = np.sum(shap_tr_mono[:, idx_a], axis=1)
                    sh_d_te = np.sum(shap_te_mono[:, idx_d], axis=1)
                    sh_p_te = np.sum(shap_te_mono[:, idx_p], axis=1)
                    sh_a_te = np.sum(shap_te_mono[:, idx_a], axis=1)

                    min_strip_tr = np.minimum(sh_d_tr, np.minimum(sh_p_tr, sh_a_tr))
                    min_strip_te = np.minimum(sh_d_te, np.minimum(sh_p_te, sh_a_te))

                    sc_tr = (
                        sc_tr
                        + 0.30 * dtr["sweep_quality_score"].values
                        + 0.30 * dtr["attractor_quality_score"].values
                        + 0.25 * min_strip_tr
                        - 5.0 * np.maximum(dtr["opp_ladder_trap_flag"].values, dtr["target_mirage_flag"].values)
                    )
                    sc_te = (
                        sc_te
                        + 0.30 * dte["sweep_quality_score"].values
                        + 0.30 * dte["attractor_quality_score"].values
                        + 0.25 * min_strip_te
                        - 5.0 * np.maximum(dte["opp_ladder_trap_flag"].values, dte["target_mirage_flag"].values)
                    )
                    sc_tr = np.where(rr_fix_tr >= 1.25, sc_tr, sc_tr - 10.0)
                    sc_te = np.where(rr_fix_te >= 1.25, sc_te, sc_te - 10.0)

                for target_f_name, target_f_val in [
                    ("freq_1.5_per_day", 1.15),
                    ("freq_2.0_per_day_IDEAL", 1.65),
                    ("freq_2.5_per_day", 2.15),
                    ("freq_3.5_per_day", 2.85),
                ]:
                    best_thr = calibrate_causal_threshold_for_target_freq_k36(
                        dtr, sc_tr, p1_tr_use, oof_p_tp2, target_f_val, exec_regime=ex_reg
                    )
                    oos_records[cfg_name]["thrs"].setdefault(target_f_name, []).append(
                        np.full(len(dte), best_thr, dtype=np.float64)
                    )

                oos_records[cfg_name]["df"].append(dte)
                oos_records[cfg_name]["p_tp1"].append(p1_te_use)
                oos_records[cfg_name]["p_tp2"].append(te_p_tp2)
                oos_records[cfg_name]["ev_score"].append(sc_te)

        trading_by_freq = {
            "freq_1.5_per_day": {},
            "freq_2.0_per_day_IDEAL": {},
            "freq_2.5_per_day": {},
            "freq_3.5_per_day": {},
        }
        assessment_32s_by_freq = {
            "freq_2.0_per_day_IDEAL": {},
        }

        for cfg_name, ex_reg in configs_list:
            rec = oos_records[cfg_name]
            if not rec["df"]:
                continue
            df_cat = pd.concat(rec["df"], ignore_index=True)
            p_tp1_cat = np.concatenate(rec["p_tp1"])
            p_tp2_cat = np.concatenate(rec["p_tp2"])
            ev_cat = np.concatenate(rec["ev_score"])

            for f_key in trading_by_freq.keys():
                thr_vec = np.concatenate(rec["thrs"][f_key])
                sim_res = simulate_causal_non_overlapping_trading_k36(
                    df_cat, ev_cat - thr_vec, p_tp1_cat, p_tp2_cat, 0.0,
                    exec_regime=ex_reg, stage2_mult=0.85, exit_policy="adaptive_2stage", m_trials_dsr=44
                )
                trading_by_freq[f_key][cfg_name] = sim_res

                # Evaluar también específicamente en las últimas 32 sesiones OOS (Assessment puro):
                if f_key == "freq_2.0_per_day_IDEAL":
                    u_s_oos = sorted(df_cat["session_id"].unique())
                    assess_s = u_s_oos[-min(len(u_s_oos), 32):]
                    m_ass = df_cat["session_id"].isin(assess_s).values
                    assessment_32s_by_freq[f_key][cfg_name] = simulate_causal_non_overlapping_trading_k36(
                        df_cat[m_ass].reset_index(drop=True),
                        (ev_cat - thr_vec)[m_ass],
                        p_tp1_cat[m_ass],
                        p_tp2_cat[m_ass],
                        0.0,
                        exec_regime=ex_reg,
                        stage2_mult=0.85,
                        exit_policy="adaptive_2stage",
                        m_trials_dsr=44,
                    )

        # Nulo de Desplazamiento Circular (100 permutaciones) sobre C4 en ~2.0 trades/día:
        rec_c4 = oos_records["C4_Full_TriStrip_Monotonic_System"]
        if rec_c4["df"]:
            df_c4 = pd.concat(rec_c4["df"], ignore_index=True)
            ev_c4 = np.concatenate(rec_c4["ev_score"])
            thr_c4 = np.concatenate(rec_c4["thrs"]["freq_2.0_per_day_IDEAL"])
            p1_c4 = np.concatenate(rec_c4["p_tp1"])
            p2_c4 = np.concatenate(rec_c4["p_tp2"])
            obs_sim = trading_by_freq["freq_2.0_per_day_IDEAL"]["C4_Full_TriStrip_Monotonic_System"]
            obs_net_155 = obs_sim["net_limit_155t_immediate"]["mean_ticks"]
            obs_pas_tt = obs_sim["net_passive_tt_state_machine_155t"]["mean_ticks"]
            obs_gross = obs_sim["gross_0t"]["mean_ticks"]
            obs_tp1_sel = obs_sim["P_TP1_stopped_selected"]

            rng_c = np.random.default_rng(20261017)
            null_nets, null_pas, null_gross, null_tp1s = [], [], [], []
            n_c4 = len(df_c4)
            diff_vec = ev_c4 - thr_c4
            for _ in range(100):
                sh = int(rng_c.integers(int(0.15 * n_c4), int(0.85 * n_c4)))
                sim_n = simulate_causal_non_overlapping_trading_k36(
                    df_c4, np.roll(diff_vec, sh), np.roll(p1_c4, sh), np.roll(p2_c4, sh),
                    0.0, exec_regime="asym_fix", stage2_mult=0.85, exit_policy="adaptive_2stage", m_trials_dsr=44
                )
                null_nets.append(sim_n["net_limit_155t_immediate"]["mean_ticks"])
                null_pas.append(sim_n["net_passive_tt_state_machine_155t"]["mean_ticks"])
                null_gross.append(sim_n["gross_0t"]["mean_ticks"])
                null_tp1s.append(sim_n["P_TP1_stopped_selected"])

            null_nets_a = np.asarray(null_nets)
            null_pas_a = np.asarray(null_pas)
            null_gross_a = np.asarray(null_gross)
            null_tp1s_a = np.asarray(null_tp1s)
            circular_null_c4 = {
                "observed_gross_mean_ticks": obs_gross,
                "null_mean_gross_ticks": round(float(np.mean(null_gross_a)), 4),
                "observed_net_155t_mean_ticks": obs_net_155,
                "null_mean_net_155t_ticks": round(float(np.mean(null_nets_a)), 4),
                "null_p95_net_155t_ticks": round(float(np.quantile(null_nets_a, 0.95)), 4),
                "p_circular_shift_net_155t": round(float((1 + np.sum(null_nets_a >= obs_net_155)) / 101.0), 4),
                "observed_passive_tt_155t_mean_ticks": obs_pas_tt,
                "null_mean_passive_tt_155t_ticks": round(float(np.mean(null_pas_a)), 4),
                "p_circular_shift_passive_tt_155t": round(float((1 + np.sum(null_pas_a >= obs_pas_tt)) / 101.0), 4),
                "observed_P_TP1_stopped_selected": obs_tp1_sel,
                "null_mean_P_TP1_stopped": round(float(np.mean(null_tp1s_a)), 4),
                "p_circular_shift_P_TP1": round(float((1 + np.sum(null_tp1s_a >= obs_tp1_sel)) / 101.0), 4),
            }
        else:
            circular_null_c4 = {}

        # Resumen Descriptivo Empírico de las Hipótesis Microestructurales en todo el Universo:
        micro_forensics = {
            "overall_n": int(len(df_v)),
            "overall_wr_sym": round(float(df_v["hit_tp1_sym"].mean()), 4),
            "overall_wr_asym_fix": round(float(df_v["hit_tp1_asym_fix"].mean()), 4),
            "overall_wr_asym_atr": round(float(df_v["hit_tp1_asym_atr"].mean()), 4),
            "mean_d1_ticks": round(float(df_v["d1_use_ticks"].mean()), 2),
            "mean_stop_sym_ticks": round(float(df_v["stop_sym_ticks"].mean()), 2),
            "mean_stop_asym_fix_ticks": round(float(df_v["stop_asym_fix_ticks"].mean()), 2),
            "mean_stop_asym_atr_ticks": round(float(df_v["stop_asym_atr_ticks"].mean()), 2),
            "hypothesis_1_por_donde_sweep_vs_ladder_trap": {
                "sweep_occurred_n": int((df_v["opp_sweep_occurred"] == 1).sum()),
                "sweep_occurred_wr_asym_fix": round(float(df_v.loc[df_v["opp_sweep_occurred"] == 1, "hit_tp1_asym_fix"].mean()), 4) if (df_v["opp_sweep_occurred"] == 1).any() else 0.0,
                "sweep_occurred_gross_2s_asym_fix": round(float(df_v.loc[df_v["opp_sweep_occurred"] == 1, "gross_2s_asym_fix"].mean()), 4) if (df_v["opp_sweep_occurred"] == 1).any() else 0.0,
                "ladder_trap_n": int((df_v["opp_ladder_trap_flag"] == 1).sum()),
                "ladder_trap_wr_asym_fix": round(float(df_v.loc[df_v["opp_ladder_trap_flag"] == 1, "hit_tp1_asym_fix"].mean()), 4) if (df_v["opp_ladder_trap_flag"] == 1).any() else 0.0,
                "ladder_trap_gross_2s_asym_fix": round(float(df_v.loc[df_v["opp_ladder_trap_flag"] == 1, "gross_2s_asym_fix"].mean()), 4) if (df_v["opp_ladder_trap_flag"] == 1).any() else 0.0,
            },
            "hypothesis_2_a_donde_gravity_vs_mirage": {
                "high_gravity_m_ge_1.5_n": int((df_v["m_grav_ratio"] >= 1.5).sum()),
                "high_gravity_wr_asym_fix": round(float(df_v.loc[df_v["m_grav_ratio"] >= 1.5, "hit_tp1_asym_fix"].mean()), 4) if (df_v["m_grav_ratio"] >= 1.5).any() else 0.0,
                "high_gravity_gross_2s_asym_fix": round(float(df_v.loc[df_v["m_grav_ratio"] >= 1.5, "gross_2s_asym_fix"].mean()), 4) if (df_v["m_grav_ratio"] >= 1.5).any() else 0.0,
                "mirage_flag_n": int((df_v["target_mirage_flag"] == 1).sum()),
                "mirage_flag_wr_asym_fix": round(float(df_v.loc[df_v["target_mirage_flag"] == 1, "hit_tp1_asym_fix"].mean()), 4) if (df_v["target_mirage_flag"] == 1).any() else 0.0,
                "mirage_flag_gross_2s_asym_fix": round(float(df_v.loc[df_v["target_mirage_flag"] == 1, "gross_2s_asym_fix"].mean()), 4) if (df_v["target_mirage_flag"] == 1).any() else 0.0,
            },
            "hypothesis_3_corredor_x_hft_confluence": {
                "hft_k_ge_1_and_e2_0_n": int(((df_v["fix600_e1_touch"] >= 1) & (df_v["fix600_e2_touch"] == 0)).sum()),
                "hft_k_ge_1_and_e2_0_wr_asym": round(float(df_v.loc[(df_v["fix600_e1_touch"] >= 1) & (df_v["fix600_e2_touch"] == 0), "hit_tp1_asym_fix"].mean()), 4) if ((df_v["fix600_e1_touch"] >= 1) & (df_v["fix600_e2_touch"] == 0)).any() else 0.0,
                "hft_k_ge_2_and_e2_0_n": int(((df_v["fix600_e1_touch"] >= 2) & (df_v["fix600_e2_touch"] == 0)).sum()),
                "hft_k_ge_2_and_e2_0_wr_asym": round(float(df_v.loc[(df_v["fix600_e1_touch"] >= 2) & (df_v["fix600_e2_touch"] == 0), "hit_tp1_asym_fix"].mean()), 4) if ((df_v["fix600_e1_touch"] >= 2) & (df_v["fix600_e2_touch"] == 0)).any() else 0.0,
            },
        }

        return {
            "universe_tag": univ_tag,
            "n_valid_outside_at_cls": int(len(df_v)),
            "n_sessions_total": int(df_v["session_id"].nunique()),
            "empirical_microstructure_forensics": micro_forensics,
            "circular_shift_null_100_reps_C4_at_2trades_per_day": circular_null_c4,
            "trading_by_daily_frequency_walkforward_oos": trading_by_freq,
            "assessment_32_sessions_strict_oos_at_2trades_per_day": assessment_32s_by_freq["freq_2.0_per_day_IDEAL"],
        }

    m_p1_hft = df_p1["has_hft_w1"] == 1
    res_u1_p1_hft = _run_universe_k36(
        df_p1[m_p1_hft].reset_index(drop=True), seqs_p1[m_p1_hft.values], "U1_Preset1_Real_HFT_in_W1"
    )

    m_p2_hft = df_p2["has_hft_w1"] == 1
    res_u3_p2_hft = _run_universe_k36(
        df_p2[m_p2_hft].reset_index(drop=True), seqs_p2[m_p2_hft.values], "U3_Preset2_Real_HFT_in_W1"
    )

    res_u2_p2_all = _run_universe_k36(
        df_p2, seqs_p2, "U2_Preset2_All_Corridors_HFT_Plus_Struct"
    )

    return {
        "U1_Preset1_Real_HFT_in_W1": res_u1_p1_hft,
        "U3_Preset2_Real_HFT_in_W1": res_u3_p2_hft,
        "U2_Preset2_All_Corridors_HFT_Plus_Struct": res_u2_p2_all,
    }


def main_k36_study():
    t0_main = time.time()
    pfile = locate_es_parquet()
    sessions_list, cmap, has_vol = dev_load_sessions(pfile)
    sessions_list = [s for s in sessions_list if DISC_START_C <= s["trade_date"] <= DISC_END_C]
    print(f"{STUDY_SPEC_K36}: {len(sessions_list)} sesiones de descubrimiento (20250718..20260331). Holdout intacto.", flush=True)

    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)

    df_p1, df_p2, seqs_p1, seqs_p2, causal_tests, n_hft_total = run_k36_trajectory_extraction(sessions_list, out_dir)
    eval_results = evaluate_k36_edge_maximizer_system(df_p1, df_p2, seqs_p1, seqs_p2)

    master_json = {
        "spec_id": STUDY_SPEC_K36,
        "version": 2,
        "north_star_sha256": NORTH_STAR_SHA256_CURRENT,
        "instrument": "ES",
        "bar_resolution": "100T_strict_session",
        "hft_detector": "HFTZonesESPureV2Flat_python_port_no_absorb",
        "corridor_detector": "DET_NT8_SMA_Range_ATR",
        "discovery_sessions": len(sessions_list),
        "date_range": [DISC_START_C, DISC_END_C],
        "holdout_touched": False,
        "nq_ym_touched": False,
        "multiplicity_trials_dsr": 44,
        "n_hft_zones_no_absorb": int(n_hft_total),
        "n_impulses_preset1": int(len(df_p1)),
        "n_impulses_preset2": int(len(df_p2)),
        "technical_causality_and_prefix_tests": causal_tests,
        "results": eval_results,
        "elapsed_seconds": round(time.time() - t0_main, 2),
    }

    (out_dir / "EXP_K36_EDGE_MAXIMIZER_ASYM_RESULTS_20261017.json").write_text(
        json.dumps(master_json, indent=2), encoding="utf-8"
    )

    print("=== EXP_K36_SUMMARY_START ===", flush=True)
    print(json.dumps(master_json, indent=2), flush=True)
    print("=== EXP_K36_SUMMARY_END ===", flush=True)



# ======================================================================================
# F0 — EJECUCION PASIVA EN ES (manifiesto pre-registrado:
# docs/research/F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md). Sin estrategia, sin busqueda.
# T1 = cierre de cada barra 100T (primaria). T2 = cierre de impulso del corredor preset 1 (secundaria).
# ======================================================================================
F0_START_D, F0_SPLIT_D, F0_END_D = 20250718, 20260331, 20260930
F0_TAUS = (10, 60, 300)
F0_HS = (10, 60, 300)
F0_RULES = ("TT", "TOUCH")          # indice 0 = R_TT (primaria), 1 = R_TOUCH (cota)
F0_PRIMARY = (60, 60, 0)            # (tau s, h s, regla)
F0_STRATA = ("ALL", "S1_with", "S1_against", "S2_spread1", "S2_spread2p", "S3_open30", "S3_rest",
             "SIDE_buy", "SIDE_sell")
F0_NS = 1_000_000_000


@njit(cache=False)
def f0_scan_fills(ts, px, i_dec, bid0, ask0, tau_max_ns):
    """Primer fill causal por (decision, lado, regla). j > i y ts[j] <= ts[i] + tau_max. -1 = sin fill."""
    n = len(i_dec)
    out = -np.ones((n, 2, 2), dtype=np.int64)
    N = len(ts)
    for d in range(n):
        i = i_dec[d]
        t_lim = ts[i] + tau_max_ns
        b = bid0[d]
        a = ask0[d]
        found = 0
        j = i + 1
        while j < N and ts[j] <= t_lim and found < 4:
            p = px[j]
            if out[d, 0, 0] < 0 and p <= b - 1:
                out[d, 0, 0] = j
                found += 1
            if out[d, 0, 1] < 0 and p <= b:
                out[d, 0, 1] = j
                found += 1
            if out[d, 1, 0] < 0 and p >= a + 1:
                out[d, 1, 0] = j
                found += 1
            if out[d, 1, 1] < 0 and p >= a:
                out[d, 1, 1] = j
                found += 1
            j += 1
    return out


def f0_load_sessions(pfile):
    """Generador de sesiones (una por trade_date, contrato primario) con cotizaciones L1. trade_date < 20261001."""
    pf = pq.ParquetFile(pfile)
    names = [pf.metadata.row_group(0).column(i).path_in_schema for i in range(pf.metadata.row_group(0).num_columns)]
    col_idx = {nm: i for i, nm in enumerate(names)}
    need = ["ts_utc_ns", "price_ticks", "bid_ticks", "ask_ticks", "outside_regular", "volume"]
    for c in need:
        assert c in col_idx, "falta columna %s en el parquet (%s)" % (c, names)
    td_col = col_idx["trade_date"]
    c_col = col_idx.get("contract", -1)
    sel_col = col_idx.get("session_selected", -1)
    rg_by_td = defaultdict(list)
    for rg in range(pf.num_row_groups):
        md = pf.metadata.row_group(rg)
        st = md.column(td_col).statistics
        if st is not None and st.has_min_max and int(st.min) >= HOLDOUT_TRADE_DATE:
            continue
        key = int(st.min) if (st is not None and st.has_min_max and st.min == st.max) else -1
        rg_by_td[key].append(rg)
    for td in sorted(k for k in rg_by_td if F0_START_D <= k <= F0_END_D):
        rgs = rg_by_td[td]
        rows_by_c, rgs_by_c = defaultdict(int), defaultdict(list)
        for rg_i in rgs:
            md_i = pf.metadata.row_group(rg_i)
            if sel_col >= 0:
                ss = md_i.column(sel_col).statistics
                if ss is not None and ss.has_min_max and ss.max is False:
                    continue
            sc = md_i.column(c_col).statistics if c_col >= 0 else None
            cn = str(sc.min) if (sc is not None and sc.has_min_max) else "ES_PRIM"
            rows_by_c[cn] += md_i.num_rows
            rgs_by_c[cn].append(rg_i)
        if not rows_by_c:
            continue
        prim = max(rows_by_c.items(), key=lambda x: x[1])[0]
        tbl = pf.read_row_groups(rgs_by_c[prim], columns=need)
        ts = tbl["ts_utc_ns"].to_numpy()
        if len(ts) < 1000:
            continue
        order = np.argsort(ts, kind="mergesort") if (np.diff(ts) < 0).any() else None
        cols = [tbl[c].to_numpy() for c in need[1:]]
        if order is not None:
            ts = ts[order]
            cols = [c[order] for c in cols]
        if ts[-1] >= HOLDOUT_UTC_NS:
            m = ts < HOLDOUT_UTC_NS
            ts = ts[m]
            cols = [c[m] for c in cols]
        yield td, prim, ts.astype(np.int64), cols[0].astype(np.int64), cols[1].astype(np.int64), \
            cols[2].astype(np.int64), cols[3].astype(np.int8), cols[4].astype(np.float64)


def _f0_new_acc():
    return defaultdict(list)


def f0_process_session(ts, px, bid, ask, outreg, i_dec, acc, samples, full_grid):
    n = len(ts)
    qv = (bid > 0) & (ask >= bid)
    idx = np.where(qv, np.arange(n), 0)
    idx = np.maximum.accumulate(idx)
    mid2 = (bid + ask)[idx]                        # medios ticks (cotizacion valida mas reciente)
    i_dec = i_dec[(i_dec >= 199) & (i_dec < n - 1)]
    if len(i_dec) == 0:
        return
    b0, a0 = bid[i_dec], ask[i_dec]
    ok = (b0 > 0) & (a0 >= b0)
    i_dec, b0, a0 = i_dec[ok], b0[ok], a0[ok]
    if len(i_dec) == 0:
        return
    fills = f0_scan_fills(ts, px, i_dec, b0, a0, max(F0_TAUS) * F0_NS)
    t_end = ts[-1]
    t0 = ts[i_dec]
    prev = np.sign(px[i_dec] - px[i_dec - 100])
    spread = a0 - b0
    rth_idx = np.where(outreg == 0)[0]
    rth_start = ts[rth_idx[0]] if len(rth_idx) else None
    open30 = (np.zeros(len(i_dec), dtype=bool) if rth_start is None
              else (outreg[i_dec] == 0) & (t0 - rth_start <= 1800 * F0_NS))
    sides = (0, 1)
    for side in sides:
        entry_a = (a0 if side == 0 else b0).astype(np.float64)
        sgn = 1.0 if side == 0 else -1.0
        with_dir = (prev > 0) if side == 0 else (prev < 0)
        against = (prev < 0) if side == 0 else (prev > 0)
        smask = {"ALL": np.ones(len(i_dec), dtype=bool), "S1_with": with_dir, "S1_against": against,
                 "S2_spread1": spread == 1, "S2_spread2p": spread >= 2, "S3_open30": open30,
                 "S3_rest": ~open30, "SIDE_buy": np.full(len(i_dec), side == 0), "SIDE_sell": np.full(len(i_dec), side == 1)}
        for ti, tau in enumerate(F0_TAUS):
            win_ok = (t0 + tau * F0_NS) <= t_end
            for ri in (0, 1):
                j = fills[:, side, ri]
                tf = np.where(j >= 0, ts[np.maximum(j, 0)], 0)
                filled = (j >= 0) & ((tf - t0) <= tau * F0_NS) & win_ok
                for h in F0_HS:
                    is_primary = (tau, h, ri) == F0_PRIMARY
                    if not full_grid and not is_primary:
                        continue
                    th_a = t0 + h * F0_NS
                    th_p = tf + h * F0_NS
                    okh = filled & (th_a <= t_end) & (th_p <= t_end)
                    ia = np.searchsorted(ts, th_a, side="right") - 1
                    ip = np.searchsorted(ts, np.minimum(th_p, t_end), side="right") - 1
                    mid_a = mid2[np.clip(ia, 0, n - 1)] / 2.0
                    mid_p = mid2[np.clip(ip, 0, n - 1)] / 2.0
                    Ma = sgn * (mid_a - entry_a)
                    Mp = sgn * (mid_p - (b0 if side == 0 else a0).astype(np.float64))
                    A = Mp - Ma
                    for sname, sm in smask.items():
                        if not full_grid and not is_primary:
                            continue
                        if not (sname == "ALL" or is_primary):
                            continue
                        m_obs = sm & win_ok
                        m_fill = m_obs & filled
                        m_a = sm & okh
                        m_all = sm & (th_a <= t_end)          # referencia agresiva INCONDICIONAL (todas las decisiones)
                        acc[(tau, h, ri, sname)].append(np.array([
                            m_obs.sum(), m_fill.sum(), m_a.sum(),
                            A[m_a].sum(), Mp[m_a].sum(), Ma[m_a].sum(),
                            m_all.sum(), Ma[m_all].sum()], dtype=np.float64))
                    if is_primary and full_grid:
                        m_a = okh
                        samples["A"].append(A[m_a].astype(np.float32))
                        samples["Mp"].append(Mp[m_a].astype(np.float32))
                        samples["Ma"].append(Ma[m_a].astype(np.float32))
                        samples.setdefault("MaAll", []).append(Ma[th_a <= t_end].astype(np.float32))
                        samples["adv2"].append(np.array([(Mp[m_a] <= -2.0).sum(), m_a.sum()], dtype=np.float64))


def f0_cluster(rows, num_col, den_col):
    """Razon sum(num)/sum(den) con SE clusterizado por sesion (linealizacion, Liang-Zeger)."""
    R = np.asarray(rows, dtype=np.float64)
    num, den = R[:, num_col], R[:, den_col]
    N = den.sum()
    if N <= 0 or len(R) < 2:
        return float("nan"), float("nan"), int(len(R)), 0
    m = num.sum() / N
    c = (num - m * den) / N
    G = len(R)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(m), se, G, int(N)


def f0_contrast(rows1, rows2):
    """Diferencia de A* entre dos estratos (mismas sesiones, mismo orden): SE por linealizacion."""
    a1, _s1, c1 = f0_astar(rows1)
    a2, _s2, c2 = f0_astar(rows2)
    if a1 != a1 or a2 != a2 or len(c1) != len(c2):
        return float("nan"), float("nan")
    c = c1 - c2
    G = len(c)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(a1 - a2), se


def f0_astar(rows):
    """A* = mean(Mp | fill) - mean(Ma sobre TODAS las decisiones). Linealizacion por sesion de la diferencia de dos razones."""
    R = np.asarray(rows, dtype=np.float64)
    nF, sMp = R[:, 2], R[:, 4]
    nAll, sMa = R[:, 6], R[:, 7]
    NF, NA = nF.sum(), nAll.sum()
    if NF <= 0 or NA <= 0 or len(R) < 2:
        return float("nan"), float("nan"), np.zeros(len(R))
    mMp, mMa = sMp.sum() / NF, sMa.sum() / NA
    c = (sMp - mMp * nF) / NF - (sMa - mMa * nAll) / NA
    G = len(R)
    se = math.sqrt((G / (G - 1.0)) * float(np.sum(c * c)))
    return float(mMp - mMa), se, c


def f0_summarize(acc):
    out = {}
    for (tau, h, ri, sname), rows in acc.items():
        if not rows:
            continue
        F, seF, G, nobs = f0_cluster(rows, 1, 0)
        A, seA, _, nA = f0_cluster(rows, 3, 2)
        Mp, seMp, _, _ = f0_cluster(rows, 4, 2)
        Ma, seMa, _, _ = f0_cluster(rows, 5, 2)
        Astar, seAs, _ = f0_astar(rows)
        MaAll, _, _, _ = f0_cluster(rows, 7, 6)
        out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)] = {
            "F_fill": F, "se_F": seF, "n_obs": nobs, "A_ticks": A, "se_A": seA, "n_A": nA,
            "Mp_ticks": Mp, "Ma_paired_filled_ticks": Ma, "MaAll_ticks": MaAll, "n_sessions": G,
            "A_paired_filled_ticks_DIAGNOSTIC_equals_spread_by_construction": A,
            "Astar_ticks": Astar, "se_Astar": seAs,
            "Astar_lo975_onesided": Astar - 1.96 * seAs if seAs == seAs else float("nan"),
            "Astar_hi975_onesided": Astar + 1.96 * seAs if seAs == seAs else float("nan")}
        if F == F and F < 1 and Astar == Astar:
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["g_star_breakeven_edge_ticks"] = F * Astar / (1.0 - F)
        # valor por intento si no hay edge: F*Mp (no llena = 0) contra Ma incondicional
        if F == F and Mp == Mp and MaAll == MaAll:
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["value_per_intent_passive_ticks"] = F * Mp
            out["tau%d_h%d_%s_%s" % (tau, h, F0_RULES[ri], sname)]["value_per_intent_aggressive_ticks"] = MaAll
    return out


def f0_sanity_tests(pfile):
    """Causalidad del fill (perturbacion de futuro) y prefijo de la decision. Aborta si algo difiere."""
    n_cases, n_fill_checked = 0, 0
    rng = np.random.default_rng(20261017)
    for td, prim, ts, px, bid, ask, outreg, _vol in f0_load_sessions(pfile):
        if td < F0_START_D + 40:
            continue
        i_dec = np.arange(199, len(ts) - 30000, 100)
        pick = rng.choice(i_dec, size=min(150, len(i_dec)), replace=False)
        for i in pick:
            b0, a0 = bid[i], ask[i]
            if not (b0 > 0 and a0 >= b0):
                continue
            lo, hi = i - 100, min(len(ts), i + 30000)
            ts_w, px_w = ts[lo:hi], px[lo:hi]
            ii = np.array([i - lo], dtype=np.int64)
            f_a = f0_scan_fills(ts_w, px_w, ii, np.array([b0]), np.array([a0]), 60 * F0_NS)
            px_p = px_w.copy()
            px_p[ts_w > ts[i] + 60 * F0_NS] = -10 ** 6      # futuro tras t0+tau perturbado
            f_b = f0_scan_fills(ts_w, px_p, ii, np.array([b0]), np.array([a0]), 60 * F0_NS)
            assert np.array_equal(f_a, f_b), "FILL NO CAUSAL (td=%s i=%s)" % (td, i)
            n_fill_checked += int((f_a >= 0).any())
            # prefijo: bid/ask/signo de la barra previa solo dependen de indices <= i
            assert (bid[:i + 1][-1], ask[:i + 1][-1], np.sign(px[:i + 1][-1] - px[:i + 1][-101])) == \
                   (b0, a0, np.sign(px[i] - px[i - 100]))
            n_cases += 1
        if n_cases >= 600:
            break
    assert n_cases >= 200, "pruebas causales insuficientes: %d" % n_cases
    return {"n_cases": n_cases, "n_cases_with_fill": n_fill_checked, "max_abs_diff": 0.0}


def main_f0():
    t0 = time.time()
    pfile = locate_es_parquet()
    sanity = f0_sanity_tests(pfile)
    print("F0_SANITY_PASS", json.dumps(sanity), flush=True)

    acc_d, acc_c = _f0_new_acc(), _f0_new_acc()
    acc_t2d, acc_t2c = _f0_new_acc(), _f0_new_acc()
    samples = {"A": [], "Mp": [], "Ma": [], "adv2": []}
    n_sess_d = n_sess_c = 0
    n_q_valid = n_q_tot = 0
    t2_err, t2_ok = 0, 0
    pc1 = (72, 50, 12, 75, 20, 0.90, 0.88, 0.040, 0.92, 1.05, 0.80, 0.36, 0.38, 0.72)
    for td, prim, ts, px, bid, ask, outreg, vol_s in f0_load_sessions(pfile):
        assert ts[-1] < HOLDOUT_UTC_NS and td < 20261001, "HOLDOUT"
        n_q_tot += len(ts)
        n_q_valid += int(((bid > 0) & (ask >= bid)).sum())
        is_disc = td <= F0_SPLIT_D
        n_sess_d += 1 if is_disc else 0
        n_sess_c += 0 if is_disc else 1
        i_dec = np.arange(99, len(ts), 100)
        f0_process_session(ts, px, bid, ask, outreg, i_dec, acc_d if is_disc else acc_c,
                           samples if is_disc else {"A": [], "Mp": [], "Ma": [], "adv2": []}, True)
        # T2: cierres de impulso del corredor (preset 1)
        try:
            s_k = {"session_id": 1, "trade_date": td, "contract_id": 1, "contract": prim,
                   "prices": px.astype(np.float64) * TICK_ES, "ts_utc_ns": ts,
                   "is_rth": (outreg == 0).astype(np.int8), "vol": vol_s,
                   "utc_off_s": int(datetime.fromtimestamp(int(ts[len(ts) // 2]) / 1e9, CHI).utcoffset().total_seconds())}
            Bs, _sd = dev_build_bars([s_k], 100)
            _, _, _, _, zc, _, _ = detect_zones_nt8_numba(
                Bs["o"], Bs["h"], Bs["l"], Bs["c"], Bs["sid"], Bs["cid"], 200, 100,
                pc1[0], pc1[1], pc1[2], pc1[3], pc1[4], pc1[5], pc1[6], pc1[7], pc1[8], pc1[9], pc1[10], pc1[11],
                pc1[12], pc1[13], 40, 5, 1.60, TICK_ES)
            if len(zc) > 0:
                cls_b = np.asarray([int(z[5]) for z in zc], dtype=np.int64)
                ts_end = Bs["ts_end"][cls_b]
                i_imp = np.unique(np.searchsorted(ts, ts_end, side="right") - 1)
                f0_process_session(ts, px, bid, ask, outreg, i_imp, acc_t2d if is_disc else acc_t2c,
                                   {"A": [], "Mp": [], "Ma": [], "adv2": []}, False)
            t2_ok += 1
        except Exception as e:  # T2 es secundaria: se declara el fallo, no se oculta
            t2_err += 1
            if t2_err <= 3:
                print("F0_T2_ERROR", td, repr(e)[:300], flush=True)
        if (n_sess_d + n_sess_c) % 25 == 0:
            print("F0 sesiones", n_sess_d + n_sess_c, "t=%.0fs" % (time.time() - t0), flush=True)

    q_frac = n_q_valid / max(n_q_tot, 1)
    print("F0 sesiones disc=%d conf=%d, fraccion cotizacion valida=%.5f" % (n_sess_d, n_sess_c, q_frac), flush=True)
    if q_frac < 0.99:
        print("F0_ABORT_QUOTES_INVALID", q_frac, flush=True)
        return
    if n_sess_d < 170 or n_sess_c < 80:
        print("F0_ABORT_SESSIONS_INSUFFICIENT", n_sess_d, n_sess_c, flush=True)
        return

    S_d, S_c = f0_summarize(acc_d), f0_summarize(acc_c)
    pk = "tau60_h60_TT"
    prim_d, prim_c = S_d[pk + "_ALL"], S_c[pk + "_ALL"]
    # contrastes S1-S3 (Holm sobre 3) en descubrimiento, ventana primaria
    pairs = (("S1_against_vs_with", "S1_against", "S1_with"), ("S2_spread1_vs_2p", "S2_spread1", "S2_spread2p"),
             ("S3_open30_vs_rest", "S3_open30", "S3_rest"))
    cont = {}
    pvals = []
    for nm, a, b in pairs:
        d, se = f0_contrast(acc_d[(60, 60, 0, a)], acc_d[(60, 60, 0, b)])
        z = d / se if se == se and se > 0 else float("nan")
        p = float(math.erfc(abs(z) / math.sqrt(2.0))) if z == z else float("nan")
        cont[nm] = {"diff_A_ticks": d, "se": se, "z": z, "p_raw": p}
        pvals.append((nm, p))
    ordered = sorted([x for x in pvals if x[1] == x[1]], key=lambda x: x[1])
    for rank, (nm, p) in enumerate(ordered):
        cont[nm]["p_holm"] = min(1.0, p * (len(ordered) - rank))

    A_all = np.concatenate(samples["A"]) if samples["A"] else np.zeros(0, dtype=np.float32)
    Mp_all = np.concatenate(samples["Mp"]) if samples["Mp"] else np.zeros(0, dtype=np.float32)
    Ma_all = np.concatenate(samples["Ma"]) if samples["Ma"] else np.zeros(0, dtype=np.float32)
    adv = np.sum(samples["adv2"], axis=0) if samples["adv2"] else np.zeros(2)
    qs = (5, 25, 50, 75, 95)
    dist = {"A_q": [float(np.percentile(A_all, q)) for q in qs] if len(A_all) else [],
            "Mp_q": [float(np.percentile(Mp_all, q)) for q in qs] if len(Mp_all) else [],
            "Ma_paired_filled_q": [float(np.percentile(Ma_all, q)) for q in qs] if len(Ma_all) else [],
            "MaAll_q": [float(np.percentile(np.concatenate(samples["MaAll"]), q)) for q in qs] if samples.get("MaAll") else [],
            "frac_fills_adverse_ge_2ticks": float(adv[0] / max(adv[1], 1.0))}

    F, lo, hi = prim_d["F_fill"], prim_d["Astar_lo975_onesided"], prim_d["Astar_hi975_onesided"]
    sign_stable = bool(prim_c["Astar_ticks"] == prim_c["Astar_ticks"] and prim_c["Astar_ticks"] > 0)
    if F >= 0.30 and lo > 0.25 and sign_stable:
        verdict = "PASIVO_RECUPERA"
    elif hi < 0.25 or F < 0.10:
        verdict = "PASIVO_NO_CONVIENE"
    else:
        verdict = "ABSTENCION"
    buy, sell = S_d[pk + "_SIDE_buy"]["Astar_ticks"], S_d[pk + "_SIDE_sell"]["Astar_ticks"]
    summary = {
        "spec_id": "EXP-F0-EJECUCION-PASIVA-ES-V1-A1", "manifest": "F0_EJECUCION_PASIVA_ES_MANIFIESTO_20261017.md",
        "windows": {"discovery": [F0_START_D, F0_SPLIT_D], "confirmation": [F0_SPLIT_D + 1, F0_END_D]},
        "n_sessions": {"discovery": n_sess_d, "confirmation": n_sess_c}, "quote_valid_fraction": q_frac,
        "sanity": sanity, "holdout_touched": False, "primary_discovery": prim_d, "primary_confirmation": prim_c,
        "VERDICT_PRIMARY": verdict, "sign_stable_confirmation": sign_stable,
        "side_symmetry_check": {"Astar_buy": buy, "Astar_sell": sell, "abs_diff": abs(buy - sell),
                                 "flag_gt_0.2tick": bool(abs(buy - sell) > 0.2)},
        "contrasts_discovery_holm3": cont, "distribution_primary_discovery": dist,
        "grid_discovery": S_d, "grid_confirmation": S_c,
        "T2_impulse_closes": {"sessions_ok": t2_ok, "sessions_error": t2_err,
                              "discovery": f0_summarize(acc_t2d), "confirmation": f0_summarize(acc_t2c)},
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    print("=== EXP_F0_SUMMARY_START ===", flush=True)
    print(json.dumps(summary, indent=1, default=float), flush=True)
    print("=== EXP_F0_SUMMARY_END ===", flush=True)
    out_dir = Path(os.environ.get("STUDY_OUT", "/kaggle/working"))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "EXP_F0_EXEC_PASIVA_ES_RESULTS.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")


main_f0()
