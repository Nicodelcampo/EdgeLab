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
HOLDOUT_UTC_NS = 1790805600000000000   # 2026-09-30 22:00 UTC = apertura de la sesion del 1-oct (antes 00:00 UTC del 1-oct: dejaba pasar 2 h de holdout); copia de edgelab/holdout.py
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


if __name__ == "__main__":
    main()
