"""CORREDOR-VOL-GAPS (2026-10-28): port causal de `EmaCorridorTrendVolW2.cs` (W1=100% y W2=200%) en 50T y M1,
acoplado a la hipótesis de ruptura del Rectángulo Amarillo en la misma dirección del impulso + excursión + regreso
hacia el impulso inicial (`MID50`, `MID25`, `ORIG100`) y puntaje continuo de gaps (`ZONAS-GAPS`).

Hipótesis física y estructural (propuesta de Nico, 2026-10-28):
  1. `EmaCorridorTrendVolW2.cs` detecta un impulso de tendencia estable mediante 4 pilares sobre EMA(20) y EMA(60)
     (`StabilityWindow = 15`, `MaxNarrowingPct = 15%`, `SlopeLookback = 5`, `MaxInsideBars = 3`), fija la caja del
     impulso `[BoxLo, BoxHi]` de altura `H_imp = BoxHi - BoxLo` entre `OriginBar` y `EndBar`, y abre un sector de
     evaluación adelantado `[SectorLo, SectorHi]` (`TailPct = 25%` hacia adentro del extremo del impulso y
     `BeyondPct = 25%` más allá del extremo, de altura `H_am = 0.50 * H_imp`) durante `ForwardBars = round(impWidth * W)`
     barras (`W1 = 100%`, `W2 = 200%`).
  2. Al cerrarse el sector adelantado en `ForwardEndBar`, se mide el volumen causal acumulado dentro de `[SectorLo, SectorHi]`
     (`SectorVolume`), su `AnchorPOC` (precio modal de volumen dentro de la caja amarilla) y su `AnchorVAEdge` (borde
     interno del Value Area 70%: `VAL` en tendencia alcista, `VAH` en tendencia bajista). Si `SectorVolume` supera el
     percentil histórico causal (`P80` o `P90` sobre las zonas previas), el sector queda marcado como Rectángulo Amarillo.
  3. Condición direccional clave: el precio NO rompe en contra del impulso inicial (no invalida el origen del impulso),
     sino que rompe la Caja Amarilla EN LA MISMA DIRECCIÓN DEL IMPULSO INICIAL (`High > SectorHi` si `dir = +1`,
     `Low < SectorLo` si `dir = -1`), se aleja una excursión `A` (`exc_amarilla = A / H_am >= 1.0, 2.0, 4.0`) y regresa.
  4. Al regresar en uno de los 3 puntos estructurales (`0 = ANTES_CAJA` al retroceder 40% de `A` hacia la caja;
     `1 = EN_CAJA_AMARILLA` al retocar el borde externo / `AnchorPOC` de la caja amarilla; `2 = DESPUES_CAJA_VA` al
     cruzar el `AnchorVAEdge` / borde interno de la caja amarilla), se apuesta a que el precio invierte/rellena el
     impulso inicial hasta su `50%` (`MID50`), su `25%` medido desde el origen (`MID25`, 75% de retroceso) o el `100%`
     del origen (`ORIG100`).
  5. Acoplamiento con `ZONAS-GAPS`: se miden dos puntajes continuos de gaps ponderados por confirmación (`Bug 2 fix`),
     antigüedad exponencial (`exp(-edad_min / 180)`) y nivel de comercio (`1_toque` ponderado x1.35 según las 20 pistas
     de `ZGAP-NQ`):
     - `gap_score_tomados` (`g_tom`): puntaje de gaps activos barridos/mitigados durante la excursión `A` tras romper
       la caja amarilla (agotamiento de liquidez en el extremo `E`).
     - `gap_iman_camino` (`g_cam`): puntaje de gaps confirmados aún abiertos en el camino entre la entrada y `ORIG100`
       (vacíos de liquidez que actúan como imán de regreso hacia el origen del impulso).
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from edgelab.research.agente.regimen import VARIABLES_REGIMEN, agregar
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "CORREDOR-VOL-GAPS"
INDICADORES = ["EmaCorridorTrendVolW2", "ZONAS-GAPS"]

# --- Parámetros exactos de EmaCorridorTrendVolW2.cs -------------------------------------------------------------------------
FAST_PERIOD = 20
SLOW_PERIOD = 60
STABILITY_WINDOW = 15
SLOPE_LOOKBACK = 5
MAX_NARROWING_PCT = 15.0
MAX_INSIDE_BARS = 3
CONFIRM_BREAK_BARS = 2
TAIL_PCT = 25.0
BEYOND_PCT = 25.0
VALUE_AREA_PCT = 70.0
LOOKBACK_ZONES = 50
MIN_ZONES_FOR_PCT = 8
MIN_ZONES_STRICT_PCT = 20
N_TICKS_50T = 50
MIN_GAP_TICKS = 3
AWAY_DISTANCE_TICKS = 10
VIDA_MAX_M1 = 1440
X_ANTES_CAJA = 0.60             # D <= 0.60 * A_ext (regreso del 40% de la excursión exterior antes de entrar a la caja amarilla)

# --- Definición de Perillas (933.120 celdas por canal = 2 × 2 × 2 × 3 × 3 × 4 × 4 × 3 × 3 × 5 × 18) -------------------------
VARIABLES = [
    Variable("escala", "esc", "grupo", categoria=2),                       # 0: 50T · 1: M1
    Variable("variante_w", "vw", "grupo", categoria=2),                    # 0: W1 (100% ForwardWidth) · 1: W2 (200% ForwardWidth)
    Variable("pct_vol", "pvol", "ge", categoria=2),                        # 0: >= P80 · 1: >= P90 (volumen en caja amarilla)
    Variable("exc_amarilla", "exc_am", "ge", cortes=(1.0, 2.0, 4.0), piso=True),  # A / H_amarilla >= 1.0, >= 2.0, >= 4.0
    Variable("punto_regreso", "pt_reg", "grupo", categoria=3),             # 0: ANTES_CAJA · 1: EN_CAJA_AMARILLA · 2: DESPUES_CAJA_VA
    Variable("gap_score_tomados", "g_tom", "eq_any", cortes=(0.05, 1.15)), # 0: sin gaps · 1: moderado · 2: alto · 3: cualquiera
    Variable("gap_iman_camino", "g_cam", "eq_any", cortes=(0.05, 1.15)),   # 0: sin imán · 1: 1 gap imán · 2: multi-imán · 3: cualquiera
    Variable("tamano_impulso", "tam_imp", "extremos", cuantiles=3),        # H_imp / ATR14 (terciles causales: chico, grande, cualquiera)
    Variable("vwap", "vwap_al", "eq_any", categoria=2),                    # 0: contra VWAP · 1: a favor de VWAP · 2: cualquiera
    VARIABLES_REGIMEN["hora"],                                             # 0: Asia · 1: Europa · 2: NY · 3: Cierre · 4: cualquiera
]
EJES_ORDINALES = (2, 3, 5, 6)

# --- Matriz de Ejecuciones: 3 entradas × 3 targets (MID50, MID25, ORIG100) × 2 stops (S_EXT, S_CAJA) = 18 ejecuciones -------
ENTRADAS = ("CIERRE", "SIG", "ANCLA_LIM")
TARGETS = ("MID50", "MID25", "ORIG100")
STOPS = ("S_EXT", "S_CAJA")
EJECUCIONES = [(ent, tp, sl) for ent in ENTRADAS for tp in TARGETS for sl in STOPS]

BASE = {
    "escala": 0,
    "variante_w": 1,
    "pct_vol": 0,
    "exc_amarilla": 1,
    "punto_regreso": 1,
    "gap_score_tomados": 3,
    "gap_iman_camino": 3,
    "tamano_impulso": 2,
    "vwap": 2,
    "reg_hora": 4,
    "ejecución": EJECUCIONES.index(("CIERRE", "MID50", "S_EXT")),
}


@njit(cache=False)
def _atr_y_vwap_m1_nb(o, h, l, c, v, ses, n_atr=14):
    """ATR(14) causal y VWAP intradía causal hasta la vela k."""
    n = len(c)
    atr = np.empty(n, dtype=np.float64)
    vwap = np.empty(n, dtype=np.float64)
    tr_sum = 0.0
    tr_buf = np.zeros(n_atr, dtype=np.float64)
    pv_acc = 0.0
    v_acc = 0.0
    ses_prev = -1
    for i in range(n):
        if i == 0 or ses[i] != ses_prev:
            tr = h[i] - l[i]
            pv_acc = 0.0
            v_acc = 0.0
            ses_prev = ses[i]
        else:
            pc = c[i - 1]
            tr = max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))
        if i < n_atr:
            tr_buf[i] = tr
            tr_sum += tr
            atr[i] = max(tr_sum / float(i + 1), 1e-6)
        else:
            idx = i % n_atr
            tr_sum += tr - tr_buf[idx]
            tr_buf[idx] = tr
            atr[i] = max(tr_sum / float(n_atr), 1e-6)
        typ = (h[i] + l[i] + c[i]) / 3.0
        vi = max(v[i], 1.0)
        pv_acc += typ * vi
        v_acc += vi
        vwap[i] = pv_acc / v_acc
    return atr, vwap


@njit(cache=False)
def _barras_50t_sesion_nb(tpx, tstart_ses, a_m1, v_m1, n_ticks):
    """Reconstruye barras exactas de `n_ticks` ticks dentro de una sesión y las vincula al minuto M1 `k` donde cierran.
    Devuelve (b_k, b_o, b_h, b_l, b_c, b_v, b_t0, b_t1) donde `b_k` es el índice M1 global en el que cerró cada barra
    y `[b_t0, b_t1)` es el rango exacto de ticks en `tpx`."""
    n_m1 = len(tstart_ses) - 1
    t0 = tstart_ses[0]
    t1 = tstart_ses[n_m1]
    total_ticks = t1 - t0
    n_bars = total_ticks // n_ticks
    if n_bars <= 0:
        z_i = np.zeros(0, dtype=np.int64)
        z_f = np.zeros(0, dtype=np.float64)
        return z_i, z_f, z_f, z_f, z_f, z_f, z_i, z_i

    b_k = np.empty(n_bars, dtype=np.int64)
    b_o = np.empty(n_bars, dtype=np.float64)
    b_h = np.empty(n_bars, dtype=np.float64)
    b_l = np.empty(n_bars, dtype=np.float64)
    b_c = np.empty(n_bars, dtype=np.float64)
    b_v = np.empty(n_bars, dtype=np.float64)
    b_t0 = np.empty(n_bars, dtype=np.int64)
    b_t1 = np.empty(n_bars, dtype=np.int64)

    m_cursor = 0
    for b in range(n_bars):
        s_idx = t0 + b * n_ticks
        e_idx = s_idx + n_ticks - 1
        while m_cursor + 1 < n_m1 and tstart_ses[m_cursor + 1] <= e_idx:
            m_cursor += 1
        b_k[b] = a_m1 + m_cursor
        b_t0[b] = s_idx
        b_t1[b] = e_idx + 1
        op = tpx[s_idx]
        cl = tpx[e_idx]
        hi = op
        lo = op
        for j in range(s_idx + 1, e_idx + 1):
            px = tpx[j]
            if px > hi:
                hi = px
            if px < lo:
                lo = px
        b_o[b] = op
        b_h[b] = hi
        b_l[b] = lo
        b_c[b] = cl
        nt_m1 = max(tstart_ses[m_cursor + 1] - tstart_ses[m_cursor], 1)
        b_v[b] = max(v_m1[a_m1 + m_cursor] * (float(n_ticks) / float(nt_m1)), float(n_ticks))
    return b_k, b_o, b_h, b_l, b_c, b_v, b_t0, b_t1


@njit(cache=False)
def _gaps_barras_nb(b_k, b_o, b_h, b_l, b_c, b_t0, b_t1, tpx, atr_m1, tick, min_gap_ticks, is_50t):
    """Detecta gaps causales sobre 50T o M1 unificando la mecánica de `ZonasDeGaps.cs` y `zonas_gaps.py`:
      1. Saltos entre cierre previo y apertura actual (`|O[i] - C[i-1]| >= umbral`), verificando si quedan sin rellenar.
      2. En 50T (`is_50t == 1`), saltos tick-a-tick internos (`|tpx[t] - tpx[t-1]| >= umbral`) que dejan vacío al cerrar la barra.
      3. Vacíos estructurales de 3 barras sin solapamiento de mechas (`L[i] - H[i-2] >= umbral` o `L[i-2] - H[i] >= umbral`).
    El umbral mínimo se adapta causalmente a la escala local `max(min_gap_ticks * tick, 0.12 * ATR14)` para mantener invarianza
    entre ES y NQ. Devuelve `(g_k, g_lo, g_hi, g_conf)`."""
    n = len(b_c)
    if n < 2:
        z_i = np.zeros(0, dtype=np.int64)
        z_f = np.zeros(0, dtype=np.float64)
        return z_i, z_f, z_f, z_i

    piso_abs = float(min_gap_ticks) * tick - 1e-9
    gk = np.empty(n * 2, dtype=np.int64)
    glo = np.empty(n * 2, dtype=np.float64)
    ghi = np.empty(n * 2, dtype=np.float64)
    gconf = np.empty(n * 2, dtype=np.int64)
    cnt = 0

    for i in range(1, n):
        k_m1 = b_k[i]
        umbral = max(piso_abs, 0.12 * atr_m1[k_m1] - 1e-9)
        added = False

        # 1. Salto entre barras |O[i] - C[i-1]| >= umbral (ZonasDeGaps.cs)
        prev_c = b_c[i - 1]
        cur_o = b_o[i]
        diff = cur_o - prev_c
        if abs(diff) >= umbral:
            if diff > 0.0:
                lo = prev_c
                hi = cur_o
                rem_hi = min(hi, b_l[i])
                conf = 1 if (rem_hi - lo) >= umbral else 0
                if conf == 1:
                    hi = rem_hi
            else:
                lo = cur_o
                hi = prev_c
                rem_lo = max(lo, b_h[i])
                conf = 1 if (hi - rem_lo) >= umbral else 0
                if conf == 1:
                    lo = rem_lo
            gk[cnt] = k_m1
            glo[cnt] = lo
            ghi[cnt] = hi
            gconf[cnt] = conf
            cnt += 1
            added = True

        # 2. En 50T: salto tick-a-tick dentro de la barra (zonas_gaps.py::_gaps_50t_sesion)
        if not added and is_50t == 1:
            t0_b = b_t0[i]
            t1_b = b_t1[i]
            if t1_b - t0_b >= 2:
                best_jump = 0.0
                best_t = -1
                for t in range(t0_b + 1, t1_b):
                    jmp = abs(tpx[t] - tpx[t - 1])
                    if jmp >= umbral and jmp > best_jump:
                        best_jump = jmp
                        best_t = t
                if best_t >= 0:
                    p0 = tpx[best_t - 1]
                    p1 = tpx[best_t]
                    lo = min(p0, p1)
                    hi = max(p0, p1)
                    if p1 > p0:
                        min_after = hi
                        for t in range(best_t + 1, t1_b):
                            if tpx[t] < min_after:
                                min_after = tpx[t]
                        rem_hi = min(hi, min_after)
                        conf = 1 if (rem_hi - lo) >= umbral else 0
                        if conf == 1:
                            hi = rem_hi
                    else:
                        max_after = lo
                        for t in range(best_t + 1, t1_b):
                            if tpx[t] > max_after:
                                max_after = tpx[t]
                        rem_lo = max(lo, max_after)
                        conf = 1 if (hi - rem_lo) >= umbral else 0
                        if conf == 1:
                            lo = rem_lo
                    gk[cnt] = k_m1
                    glo[cnt] = lo
                    ghi[cnt] = hi
                    gconf[cnt] = conf
                    cnt += 1
                    added = True

        # 3. Vacío de 3 barras sin solapamiento de mechas (zonas_gaps.py::_gaps_m1_sesion)
        if not added and i >= 2:
            if b_l[i] - b_h[i - 2] >= umbral:
                gk[cnt] = k_m1
                glo[cnt] = b_h[i - 2]
                ghi[cnt] = b_l[i]
                gconf[cnt] = 1
                cnt += 1
            elif b_l[i - 2] - b_h[i] >= umbral:
                gk[cnt] = k_m1
                glo[cnt] = b_h[i]
                ghi[cnt] = b_l[i - 2]
                gconf[cnt] = 1
                cnt += 1

    return gk[:cnt], glo[:cnt], ghi[:cnt], gconf[:cnt]


@njit(cache=False)
def _eval_stability_window_nb(idx, w, c, ema_f, ema_s, slope_lb, max_narrow_pct, max_inside):
    """Traducción exacta de `EvaluateStabilityWindow` de `EmaCorridorTrendVolW2.cs` en la barra `idx`."""
    start = idx - w + 1
    if start < slope_lb:
        return 0
    f0 = ema_f[start]
    s0 = ema_s[start]
    if f0 > s0:
        d = 1
    elif f0 < s0:
        d = -1
    else:
        return 0

    inside_cnt = 0
    prev_w = abs(f0 - s0)
    if prev_w <= 1e-9:
        return 0
    narrow_fac = 1.0 - (max_narrow_pct / 100.0)

    for b in range(start, idx + 1):
        ef = ema_f[b]
        es = ema_s[b]
        # Pilar 1: Dirección consistente
        if d == 1 and ef <= es:
            return 0
        if d == -1 and ef >= es:
            return 0
        # Pilar 2: Ancho no convergente
        cw = abs(ef - es)
        if b > start and cw < prev_w * narrow_fac:
            return 0
        prev_w = cw
        # Pilar 3: Alineación de pendientes sobre SlopeLookback
        if b >= slope_lb:
            fs = ef - ema_f[b - slope_lb]
            ss = es - ema_s[b - slope_lb]
            if d == 1 and (fs <= 0.0 or ss <= 0.0):
                return 0
            if d == -1 and (fs >= 0.0 or ss >= 0.0):
                return 0
        # Pilar 4: Contención del precio respecto al corredor
        cl = c[b]
        hi_c = max(ef, es)
        lo_c = min(ef, es)
        if d == 1 and cl < lo_c:
            return 0
        if d == -1 and cl > hi_c:
            return 0
        if cl >= lo_c and cl <= hi_c:
            inside_cnt += 1
            if inside_cnt > max_inside:
                return 0

    return d


@njit(cache=False)
def _find_zone_origin_nb(win_start, d, h, l, ema_f, ema_s):
    """Traducción exacta de `FindZoneOrigin` de `EmaCorridorTrendVolW2.cs`: retrocede hasta el cruce de EMAs y busca el extremo."""
    cross_bar = 0
    for b in range(win_start, 0, -1):
        ef = ema_f[b]
        es = ema_s[b]
        if d == 1 and ef <= es:
            cross_bar = b
            break
        if d == -1 and ef >= es:
            cross_bar = b
            break
    best_bar = cross_bar
    if d == 1:
        best_val = l[cross_bar]
        for b in range(cross_bar, win_start + 1):
            if l[b] <= best_val:
                best_val = l[b]
                best_bar = b
    else:
        best_val = h[cross_bar]
        for b in range(cross_bar, win_start + 1):
            if h[b] >= best_val:
                best_val = h[b]
                best_bar = b
    return best_bar


@njit(cache=False)
def _acumular_perfil_sector_nb(
    eb, bar_end, slo, shi, b_h, b_l, b_v, b_t0, b_t1, tpx, tick
):
    """Integra exactamente el volumen tick a tick (`tpx[b_t0[b]:b_t1[b]]`) dentro de `[slo, shi]`
    en las barras `[eb + 1 .. bar_end]` (paridad con `BuildVolumeAtPrice` de `EmaCorridorTrendVolW2.cs`,
    donde el bucle adelantado corre en `b = z.EndBar + 1 .. z.ForwardEndBar`)."""
    n_bins = 20
    bin_step = max((shi - slo) / float(n_bins), tick)
    bins_v = np.zeros(n_bins, dtype=np.float64)
    sec_vol = 0.0
    touched = False
    n_tpx = len(tpx)
    for b in range(eb + 1, bar_end + 1):
        bh = b_h[b]
        bl = b_l[b]
        if bh < slo or bl > shi:
            continue
        touched = True
        t0 = b_t0[b]
        t1 = b_t1[b]
        if t1 > t0 and t0 >= 0 and t1 <= n_tpx:
            n_tk = t1 - t0
            w_tk = b_v[b] / float(n_tk)
            for ti in range(t0, t1):
                px = tpx[ti]
                if slo <= px <= shi:
                    sec_vol += w_tk
                    b_idx = int((px - slo) / bin_step)
                    if b_idx < 0:
                        b_idx = 0
                    elif b_idx >= n_bins:
                        b_idx = n_bins - 1
                    bins_v[b_idx] += w_tk
        else:
            ov_lo = max(bl, slo)
            ov_hi = min(bh, shi)
            if ov_hi >= ov_lo:
                bar_rng = bh - bl
                frac = (ov_hi - ov_lo) / bar_rng if bar_rng > 1e-9 else 1.0
                v_add = b_v[b] * frac
                sec_vol += v_add
                mid_px = 0.5 * (ov_lo + ov_hi)
                b_idx = int((mid_px - slo) / bin_step)
                if b_idx < 0:
                    b_idx = 0
                elif b_idx >= n_bins:
                    b_idx = n_bins - 1
                bins_v[b_idx] += v_add
    return touched, sec_vol, bins_v, bin_step


@njit(cache=False)
def _evaluar_percentil_causal_nb(sec_vol, hist_vols, n_hist):
    """Evalúa el percentil causal sobre las últimas `LOOKBACK_ZONES = 50` zonas cerradas
    (paridad con `ComputePercentileThresholds` de `EmaCorridorTrendVolW2.cs`)."""
    if n_hist < MIN_ZONES_FOR_PCT or sec_vol <= 0.0:
        return False, False
    h_start = max(0, n_hist - LOOKBACK_ZONES)
    n_win = n_hist - h_start
    less_cnt = 0
    for h_i in range(h_start, n_hist):
        if hist_vols[h_i] < sec_vol:
            less_cnt += 1
    pct_rank = (100.0 * float(less_cnt)) / float(n_win)
    thr80 = 80.0 if n_win >= 20 else 75.0
    thr90 = 90.0 if n_win >= 20 else 85.0
    return pct_rank >= thr80, pct_rank >= thr90


@njit(cache=False)
def _calcular_poc_y_va_nb(slo, shi, sec_vol, bins_v, bin_step, d_imp):
    """Calcula `AnchorPOC` (desempatando por cercanía al centro del sector `0.5 * (slo + shi)`,
    línea 880 de `EmaCorridorTrendVolW2.cs`) y `AnchorVAEdge` (`70%` Value Area)."""
    n_bins = len(bins_v)
    sec_mid = 0.5 * (slo + shi)
    poc_bin = 0
    best_bv = -1.0
    best_dist = 1e18
    for bi in range(n_bins):
        bv = bins_v[bi]
        b_px = slo + (float(bi) + 0.5) * bin_step
        dist = abs(b_px - sec_mid)
        if bv > best_bv + 1e-12 or (abs(bv - best_bv) <= 1e-12 and dist < best_dist):
            best_bv = bv
            best_dist = dist
            poc_bin = bi
    poc_px = slo + (float(poc_bin) + 0.5) * bin_step
    va_lo_bin = poc_bin
    va_hi_bin = poc_bin
    acc_v = bins_v[poc_bin]
    target_v = sec_vol * (VALUE_AREA_PCT / 100.0)
    while acc_v < target_v and (va_lo_bin > 0 or va_hi_bin < n_bins - 1):
        up_v = bins_v[va_hi_bin + 1] if va_hi_bin + 1 < n_bins else -1.0
        dn_v = bins_v[va_lo_bin - 1] if va_lo_bin - 1 >= 0 else -1.0
        if up_v >= dn_v and va_hi_bin + 1 < n_bins:
            va_hi_bin += 1
            acc_v += bins_v[va_hi_bin]
        elif va_lo_bin - 1 >= 0:
            va_lo_bin -= 1
            acc_v += bins_v[va_lo_bin]
        else:
            break
    val_px = slo + float(va_lo_bin) * bin_step
    vah_px = slo + float(va_hi_bin + 1) * bin_step
    va_edge = val_px if d_imp == 1 else vah_px
    return poc_px, va_edge


@njit(cache=False)
def _extraer_cajas_amarillas_nb(
    b_k, b_o, b_h, b_l, b_c, b_v, b_t0, b_t1, tpx, tick, fwd_width_pct
):
    """Ejecuta la máquina de estados causal de `EmaCorridorTrendVolW2.cs` sobre la serie de barras `(b_o, b_h, b_l, b_c, b_v)`
    integrando el volumen exacto tick a tick (`tpx[b_t0[b]:b_t1[b]]`) dentro de `[SectorLo, SectorHi]`.
    Permite confirmación causal temprana (`i < ForwardEndBar`) cuando el volumen acumulado en `[EndBar + 1 .. i]`
    ya supera `P80` (al ser monótonamente no decreciente) y el precio rompe la Caja Amarilla en la dirección del impulso,
    actualizando siempre `hist_vols` al cierre completo en `ForwardEndBar`.
    Devuelve:
      z_k_m1      : índice M1 en el que se confirma el Rectángulo Amarillo (`b_k[i]` en ruptura intra-sector o `b_k[ForwardEndBar]`)
      z_k_ic      : índice M1 en el que se confirmó el quiebre del corredor y se abrió el sector (`b_k[ic_bar]`)
      z_dir       : dirección del impulso inicial (+1 alcista, -1 bajista)
      z_box_lo    : `BoxLo` del impulso inicial
      z_box_hi    : `BoxHi` del impulso inicial
      z_sec_lo    : `SectorLo` de la caja amarilla
      z_sec_hi    : `SectorHi` de la caja amarilla
      z_poc       : `AnchorPOC` (precio modal de volumen dentro de la caja amarilla)
      z_va_edge   : `AnchorVAEdge` (`VAL` si dir=+1, `VAH` si dir=-1)
      z_pvol      : nivel de percentil de volumen alcanzado (0 = entre P80 y P90, 1 = >= P90)
    """
    n = len(b_c)
    max_z = max(n // 5, 16)
    z_k_m1 = np.empty(max_z, dtype=np.int64)
    z_k_ic = np.empty(max_z, dtype=np.int64)
    z_dir = np.empty(max_z, dtype=np.int64)
    z_box_lo = np.empty(max_z, dtype=np.float64)
    z_box_hi = np.empty(max_z, dtype=np.float64)
    z_sec_lo = np.empty(max_z, dtype=np.float64)
    z_sec_hi = np.empty(max_z, dtype=np.float64)
    z_poc = np.empty(max_z, dtype=np.float64)
    z_va_edge = np.empty(max_z, dtype=np.float64)
    z_pvol = np.empty(max_z, dtype=np.int64)
    nz = 0

    if n < SLOW_PERIOD + STABILITY_WINDOW + 5:
        return (
            z_k_m1[:0], z_k_ic[:0], z_dir[:0], z_box_lo[:0], z_box_hi[:0],
            z_sec_lo[:0], z_sec_hi[:0], z_poc[:0], z_va_edge[:0], z_pvol[:0]
        )

    # EMAs causales (20 y 60)
    ema_f = np.empty(n, dtype=np.float64)
    ema_s = np.empty(n, dtype=np.float64)
    af = 2.0 / (FAST_PERIOD + 1.0)
    as_ = 2.0 / (SLOW_PERIOD + 1.0)
    ema_f[0] = b_c[0]
    ema_s[0] = b_c[0]
    for i in range(1, n):
        ema_f[i] = af * b_c[i] + (1.0 - af) * ema_f[i - 1]
        ema_s[i] = as_ * b_c[i] + (1.0 - as_) * ema_s[i - 1]

    # Historial causal de volúmenes de sectores cerrados en ForwardEndBar
    hist_vols = np.empty(max_z * 2, dtype=np.float64)
    n_hist = 0

    # Sectores adelantados pendientes de cierre (hasta 32 en paralelo)
    p_active = np.zeros(32, dtype=np.int64)
    p_emitted = np.zeros(32, dtype=np.int64)
    p_dir = np.zeros(32, dtype=np.int64)
    p_end_bar = np.zeros(32, dtype=np.int64)
    p_ic_bar = np.zeros(32, dtype=np.int64)
    p_fwd_end = np.zeros(32, dtype=np.int64)
    p_box_lo = np.zeros(32, dtype=np.float64)
    p_box_hi = np.zeros(32, dtype=np.float64)
    p_sec_lo = np.zeros(32, dtype=np.float64)
    p_sec_hi = np.zeros(32, dtype=np.float64)

    in_zone = False
    z_dir_cur = 0
    origin_bar = 0
    outside_cnt = 0
    last_close_bar = -1000
    run_hi = 0.0
    run_lo = 0.0

    for i in range(SLOW_PERIOD, n):
        # 1. Revisar sectores adelantados activos: ruptura intra-sector causal (i < fe) o cierre en ForwardEndBar (i == fe)
        for s in range(32):
            if p_active[s] != 1:
                continue
            eb = p_end_bar[s]
            icb = p_ic_bar[s]
            fe = p_fwd_end[s]
            slo = p_sec_lo[s]
            shi = p_sec_hi[s]
            d_s = p_dir[s]

            # 1a. ¿Ruptura intra-sector causal antes de ForwardEndBar?
            if p_emitted[s] == 0 and i > icb and i < fe:
                broke_now = (d_s == 1 and b_h[i] > shi + tick) or (d_s == -1 and b_l[i] < slo - tick)
                if broke_now and shi > slo + 1e-9:
                    touched, sec_vol_i, bins_v_i, bin_step_i = _acumular_perfil_sector_nb(
                        eb, i, slo, shi, b_h, b_l, b_v, b_t0, b_t1, tpx, tick
                    )
                    if touched and sec_vol_i > 0.0:
                        is_p80, is_p90 = _evaluar_percentil_causal_nb(sec_vol_i, hist_vols, n_hist)
                        if is_p80 and nz < max_z:
                            poc_px, va_edge = _calcular_poc_y_va_nb(slo, shi, sec_vol_i, bins_v_i, bin_step_i, d_s)
                            z_k_m1[nz] = b_k[i]
                            z_k_ic[nz] = b_k[icb]
                            z_dir[nz] = d_s
                            z_box_lo[nz] = p_box_lo[s]
                            z_box_hi[nz] = p_box_hi[s]
                            z_sec_lo[nz] = slo
                            z_sec_hi[nz] = shi
                            z_poc[nz] = poc_px
                            z_va_edge[nz] = va_edge
                            z_pvol[nz] = 1 if is_p90 else 0
                            nz += 1
                            p_emitted[s] = 1

            # 1b. Alcanzó su ForwardEndBar en la barra `i`
            if i == fe:
                p_active[s] = 0
                if shi <= slo + 1e-9 or fe <= eb:
                    continue
                touched, sec_vol, bins_v, bin_step = _acumular_perfil_sector_nb(
                    eb, fe, slo, shi, b_h, b_l, b_v, b_t0, b_t1, tpx, tick
                )
                if not touched or sec_vol <= 0.0:
                    continue
                is_p80, is_p90 = _evaluar_percentil_causal_nb(sec_vol, hist_vols, n_hist)
                if n_hist < len(hist_vols):
                    hist_vols[n_hist] = sec_vol
                    n_hist += 1

                if p_emitted[s] == 0 and is_p80 and nz < max_z:
                    poc_px, va_edge = _calcular_poc_y_va_nb(slo, shi, sec_vol, bins_v, bin_step, d_s)
                    z_k_m1[nz] = b_k[fe]
                    z_k_ic[nz] = b_k[icb]
                    z_dir[nz] = d_s
                    z_box_lo[nz] = p_box_lo[s]
                    z_box_hi[nz] = p_box_hi[s]
                    z_sec_lo[nz] = slo
                    z_sec_hi[nz] = shi
                    z_poc[nz] = poc_px
                    z_va_edge[nz] = va_edge
                    z_pvol[nz] = 1 if is_p90 else 0
                    nz += 1

        # 2. Actualizar estado del corredor activo o buscar nuevo corredor (sin solapar la ventana de estabilidad con el cierre previo)
        if not in_zone:
            if i - last_close_bar < STABILITY_WINDOW:
                continue
            d = _eval_stability_window_nb(
                i, STABILITY_WINDOW, b_c, ema_f, ema_s, SLOPE_LOOKBACK, MAX_NARROWING_PCT, MAX_INSIDE_BARS
            )
            if d != 0:
                win_start = i - STABILITY_WINDOW + 1
                origin_bar = max(last_close_bar + 1, _find_zone_origin_nb(win_start, d, b_h, b_l, ema_f, ema_s))
                in_zone = True
                z_dir_cur = d
                outside_cnt = 0
                run_hi = -1e18
                run_lo = 1e18
                for b in range(origin_bar, i + 1):
                    if b_h[b] > run_hi:
                        run_hi = b_h[b]
                    if b_l[b] < run_lo:
                        run_lo = b_l[b]
        else:
            if b_h[i] > run_hi:
                run_hi = b_h[i]
            if b_l[i] < run_lo:
                run_lo = b_l[i]

            # IsTrendBroken
            ef = ema_f[i]
            es = ema_s[i]
            corridor_flipped = (z_dir_cur == 1 and ef <= es) or (z_dir_cur == -1 and ef >= es)
            wrong_side = (z_dir_cur == 1 and b_c[i] < es) or (z_dir_cur == -1 and b_c[i] > es)
            if wrong_side:
                outside_cnt += 1
            else:
                outside_cnt = 0

            if corridor_flipped or outside_cnt >= CONFIRM_BREAK_BARS:
                # Cerrar impulso en end_bar y encolar sector adelantado
                end_bar = max(origin_bar + 1, i - outside_cnt)
                box_hi = -1e18
                box_lo = 1e18
                for b in range(origin_bar, end_bar + 1):
                    if b_h[b] > box_hi:
                        box_hi = b_h[b]
                    if b_l[b] < box_lo:
                        box_lo = b_l[b]
                h_imp = box_hi - box_lo
                imp_w = max(1, end_bar - origin_bar)
                fwd_bars = max(1, int(round(float(imp_w) * (fwd_width_pct / 100.0))))
                fwd_end = end_bar + fwd_bars
                if h_imp > 2.0 * tick and fwd_end < n:
                    tail_off = h_imp * (TAIL_PCT / 100.0)
                    bey_off = h_imp * (BEYOND_PCT / 100.0)
                    if z_dir_cur == 1:
                        slo = box_hi - tail_off
                        shi = box_hi + bey_off
                    else:
                        slo = box_lo - bey_off
                        shi = box_lo + tail_off
                    # Guardar en slot libre de p_active
                    for s in range(32):
                        if p_active[s] == 0:
                            p_active[s] = 1
                            p_emitted[s] = 0
                            p_dir[s] = z_dir_cur
                            p_end_bar[s] = end_bar
                            p_ic_bar[s] = i
                            p_fwd_end[s] = fwd_end
                            p_box_lo[s] = box_lo
                            p_box_hi[s] = box_hi
                            p_sec_lo[s] = slo
                            p_sec_hi[s] = shi
                            break
                in_zone = False
                z_dir_cur = 0
                outside_cnt = 0
                last_close_bar = i

    return (
        z_k_m1[:nz], z_k_ic[:nz], z_dir[:nz], z_box_lo[:nz], z_box_hi[:nz],
        z_sec_lo[:nz], z_sec_hi[:nz], z_poc[:nz], z_va_edge[:nz], z_pvol[:nz]
    )


@njit(cache=False)
def _contar_toques_epoca_nb(gk_i, m_lim, glo_i, ghi_i, h, l, away_dist):
    """Cuenta épocas de toque separadas por alejamiento `>= away_dist` (paridad con `AwayDistanceTicks = 10`
    de `ZonasDeGaps.cs` líneas 386-455). Un gap se considera vivo mientras tenga `<= 1` época de toque previa."""
    touches = 0
    in_touch = False
    was_away = True
    for tb in range(gk_i + 1, m_lim):
        overlaps = h[tb] >= glo_i and l[tb] <= ghi_i
        if overlaps:
            if was_away:
                touches += 1
                was_away = False
                in_touch = True
                if touches >= 3:
                    return touches
        else:
            if in_touch:
                if l[tb] > ghi_i + away_dist or h[tb] < glo_i - away_dist:
                    was_away = True
                    in_touch = False
            elif l[tb] > ghi_i + away_dist or h[tb] < glo_i - away_dist:
                was_away = True
    return touches


@njit(cache=False)
def _escanear_ruptura_excursion_regreso_nb(
    z_k, z_k_ic, z_dir, z_box_lo, z_box_hi, z_sec_lo, z_sec_hi, z_poc, z_va_edge, z_pvol,
    g_k, g_lo, g_hi, g_conf,
    h, l, c, ses, tick
):
    """Para cada Caja Amarilla confirmada en `z_k[j]`, sigue causalmente la evolución minuto a minuto:
      1. Verifica que el precio NO invalide el origen del impulso (`l <= BoxLo` si `dir=+1`, `h >= BoxHi` si `dir=-1`) antes
         de romper la Caja Amarilla.
      2. Reconoce rupturas intra-sector ya ocurridas entre `z_k_ic[j]` y `z_k[j]` o rupturas posteriores a `z_k[j]`,
         exigiendo que el precio supere el borde externo de la Caja Amarilla con una excursión genuina más allá del borde
         `ext_beyond >= max(0.25 * H_amarilla, 2.0 * tick)` además de `exc_ratio >= 1.0`.
      3. Registra el extremo `E` alcanzado durante la excursión y calcula causalmente en el minuto de disparo `m`:
         - `g_tom`: puntaje de gaps vivos (`toques_epoca <= 1` antes de la ruptura, con separación `AwayDistanceTicks = 10`)
           barridos durante la excursión, con decaimiento exponencial `exp(-edad_min / 180)`, peso `1.35` para `1_toque`
           y bono de racimo `1.25x` cuando `>= 3` gaps activos forman un racimo compacto.
         - `g_cam`: puntaje de gaps confirmados vivos en el camino de retorno entre `c[m]` y `ORIG100`.
      4. Emite hasta 3 disparos por Caja Amarilla (a lo sumo UNO por barra M1 `m`, con exclusión mutua en la misma barra):
         - `0 = ANTES_CAJA`: cuando la distancia restante al borde externo cae a `<= 0.60 * ext_beyond` permaneciendo fuera.
         - `1 = EN_CAJA_AMARILLA`: cuando el precio regresa a tocar el borde externo / `AnchorPOC` de la Caja Amarilla.
         - `2 = DESPUES_CAJA_VA`: cuando el precio penetra la Caja Amarilla hasta `AnchorVAEdge` / borde interno.
    """
    nz = len(z_k)
    n_m1 = len(c)
    cap = max(nz * 3, 16)

    out_k = np.empty(cap, dtype=np.int64)
    out_dir = np.empty(cap, dtype=np.int64)
    out_pvol = np.empty(cap, dtype=np.int64)
    out_pt_reg = np.empty(cap, dtype=np.int64)
    out_exc_am = np.empty(cap, dtype=np.float64)
    out_g_tom = np.empty(cap, dtype=np.float64)
    out_g_cam = np.empty(cap, dtype=np.float64)
    out_h_imp = np.empty(cap, dtype=np.float64)
    out_h_am = np.empty(cap, dtype=np.float64)
    out_ext = np.empty(cap, dtype=np.float64)
    out_ancla = np.empty(cap, dtype=np.float64)
    out_mid50 = np.empty(cap, dtype=np.float64)
    out_mid25 = np.empty(cap, dtype=np.float64)
    out_orig100 = np.empty(cap, dtype=np.float64)
    cnt = 0

    n_gaps = len(g_k)
    away_dist = float(AWAY_DISTANCE_TICKS) * tick

    for j in range(nz):
        k0 = z_k[j]
        k_ic = min(z_k_ic[j], k0)
        if k0 >= n_m1 - 2:
            continue
        d = z_dir[j]
        blo = z_box_lo[j]
        bhi = z_box_hi[j]
        slo = z_sec_lo[j]
        shi = z_sec_hi[j]
        poc = z_poc[j]
        vae = z_va_edge[j]
        pvol = z_pvol[j]

        h_imp = max(bhi - blo, 2.0 * tick)
        h_am = max(shi - slo, tick)
        mid50 = 0.5 * (blo + bhi)
        if d == 1:
            mid25 = blo + 0.25 * h_imp
            orig100 = blo
        else:
            mid25 = bhi - 0.25 * h_imp
            orig100 = bhi

        broke_same_dir = False
        invalidated = False
        ext = shi if d == 1 else slo
        m_ext = k0
        k_brk = k0

        # Verificar si la ruptura en la dirección del impulso ya ocurrió entre k_ic y k0 (ruptura intra-sector causal)
        for m_pre in range(max(0, k_ic), k0 + 1):
            if not broke_same_dir:
                if (d == 1 and l[m_pre] <= blo) or (d == -1 and h[m_pre] >= bhi):
                    invalidated = True
                    break
                if d == 1 and h[m_pre] > shi + tick:
                    broke_same_dir = True
                    ext = h[m_pre]
                    m_ext = m_pre
                    k_brk = m_pre
                elif d == -1 and l[m_pre] < slo - tick:
                    broke_same_dir = True
                    ext = l[m_pre]
                    m_ext = m_pre
                    k_brk = m_pre
            else:
                if d == 1 and h[m_pre] > ext:
                    ext = h[m_pre]
                    m_ext = m_pre
                elif d == -1 and l[m_pre] < ext:
                    ext = l[m_pre]
                    m_ext = m_pre

        if invalidated:
            continue

        fired_0 = False
        fired_1 = False
        fired_2 = False

        # Límite de seguimiento hasta VIDA_MAX_M1 minutos desde k0
        m_end = min(n_m1 - 1, k0 + VIDA_MAX_M1)
        for m in range(k0 + 1, m_end):
            hm = h[m]
            lm = l[m]
            cm = c[m]

            if not broke_same_dir:
                # Si rompe primero el origen del impulso en sentido contrario, se descarta la zona
                if (d == 1 and lm <= blo) or (d == -1 and hm >= bhi):
                    break
                # Verificar ruptura en la MISMA dirección del impulso inicial
                if d == 1 and hm > shi + tick:
                    broke_same_dir = True
                    ext = hm
                    m_ext = m
                    k_brk = m
                elif d == -1 and lm < slo - tick:
                    broke_same_dir = True
                    ext = lm
                    m_ext = m
                    k_brk = m
                continue

            # Actualizar excursión máxima en la dirección del impulso
            if d == 1 and hm > ext:
                ext = hm
                m_ext = m
            elif d == -1 and lm < ext:
                ext = lm
                m_ext = m

            # Excursión genuina más allá del borde externo de la caja amarilla (`ext_beyond`) y ratio sobre semiancho (`exc_ratio`)
            ext_beyond = (ext - shi) if d == 1 else (slo - ext)
            if ext_beyond < max(0.25 * h_am, 2.0 * tick):
                continue
            semi_am = max(0.5 * h_am, tick)
            amp = (ext - 0.5 * (slo + shi)) if d == 1 else (0.5 * (slo + shi) - ext)
            exc_ratio = amp / semi_am
            if exc_ratio < 1.0:
                continue

            # Evaluar los 3 puntos de regreso con exclusión mutua por barra `m` (a lo sumo un nivel por barra M1)
            for pt in range(3):
                if pt == 0 and fired_0:
                    continue
                if pt == 1 and fired_1:
                    continue
                if pt == 2 and fired_2:
                    continue

                ok_pt = False
                ancla_px = poc
                if d == 1:
                    dist_rem = cm - shi
                    if pt == 0:
                        if dist_rem > 0.0 and dist_rem <= X_ANTES_CAJA * ext_beyond and cm < ext - 2.0 * tick:
                            ok_pt = True
                            ancla_px = cm + 0.25 * (ext - cm)
                    elif pt == 1:
                        if lm <= shi and cm >= slo and cm <= shi + 0.15 * h_am:
                            ok_pt = True
                            ancla_px = max(poc, shi)
                    else:
                        va_thr = min(vae, poc - 0.15 * h_am)
                        if lm <= va_thr and cm > orig100 + 2.0 * tick:
                            ok_pt = True
                            ancla_px = poc
                else:
                    dist_rem = slo - cm
                    if pt == 0:
                        if dist_rem > 0.0 and dist_rem <= X_ANTES_CAJA * ext_beyond and cm > ext + 2.0 * tick:
                            ok_pt = True
                            ancla_px = cm - 0.25 * (cm - ext)
                    elif pt == 1:
                        if hm >= slo and cm <= shi and cm >= slo - 0.15 * h_am:
                            ok_pt = True
                            ancla_px = min(poc, slo)
                    else:
                        va_thr = max(vae, poc + 0.15 * h_am)
                        if hm >= va_thr and cm < orig100 - 2.0 * tick:
                            ok_pt = True
                            ancla_px = poc

                if ok_pt:
                    if pt == 0:
                        fired_0 = True
                    elif pt == 1:
                        fired_1 = True
                    else:
                        fired_2 = True

                    # Calcular causalmente `g_tom` y `g_cam` respetando ciclo de vida de ZonasDeGaps (<= 1 época de toque previa)
                    score_tom = 0.0
                    score_cam = 0.0
                    n_tom_clust = 0
                    n_cam_clust = 0
                    last_tom_mid = -1e18
                    last_cam_mid = -1e18
                    clust_dist = 12.0 * tick

                    for gi in range(n_gaps - 1, -1, -1):
                        gk_i = g_k[gi]
                        if gk_i > m:
                            continue
                        age = float(m - gk_i)
                        if age > float(VIDA_MAX_M1):
                            break
                        glo_i = g_lo[gi]
                        ghi_i = g_hi[gi]
                        gmid_i = 0.5 * (glo_i + ghi_i)
                        w_conf = 1.0 if g_conf[gi] == 1 else 0.5
                        w_age = math.exp(-age / 180.0)

                        # 1. ¿Fue barrido durante la excursión entre SectorEdge y Ext?
                        in_exc = (d == 1 and gmid_i >= slo and gmid_i <= ext) or (
                            d == -1 and gmid_i <= shi and gmid_i >= ext
                        )
                        if in_exc and gk_i <= m_ext:
                            touches_pre = _contar_toques_epoca_nb(
                                gk_i, min(k_brk, m), glo_i, ghi_i, h, l, away_dist
                            )
                            # En ZonasDeGaps.cs, al 2do toque previo el gap muere; sólo puntúan los gaps vivos (0 o 1 época de toque)
                            if touches_pre <= 1:
                                w_touch = 1.35 if touches_pre == 1 else 1.00
                                score_tom += w_conf * w_age * w_touch
                                if last_tom_mid < -1e17 or abs(gmid_i - last_tom_mid) <= clust_dist:
                                    n_tom_clust += 1
                                last_tom_mid = gmid_i

                        # 2. ¿Está en el camino de regreso entre `cm` y `orig100` como imán vivo?
                        in_path = (d == 1 and gmid_i < cm and gmid_i >= orig100) or (
                            d == -1 and gmid_i > cm and gmid_i <= orig100
                        )
                        if in_path and g_conf[gi] == 1:
                            touches_p = _contar_toques_epoca_nb(
                                gk_i, m, glo_i, ghi_i, h, l, away_dist
                            )
                            if touches_p <= 1:
                                w_tp = 1.35 if touches_p == 1 else 1.00
                                score_cam += w_age * w_tp
                                if last_cam_mid < -1e17 or abs(gmid_i - last_cam_mid) <= clust_dist:
                                    n_cam_clust += 1
                                last_cam_mid = gmid_i

                    if n_tom_clust >= 3:
                        score_tom *= 1.25
                    if n_cam_clust >= 3:
                        score_cam *= 1.25

                    if cnt >= len(out_k):
                        new_cap = len(out_k) * 2
                        nk = np.empty(new_cap, dtype=np.int64); nk[:cnt] = out_k; out_k = nk
                        nd = np.empty(new_cap, dtype=np.int64); nd[:cnt] = out_dir; out_dir = nd
                        npv = np.empty(new_cap, dtype=np.int64); npv[:cnt] = out_pvol; out_pvol = npv
                        npt = np.empty(new_cap, dtype=np.int64); npt[:cnt] = out_pt_reg; out_pt_reg = npt
                        nex = np.empty(new_cap, dtype=np.float64); nex[:cnt] = out_exc_am; out_exc_am = nex
                        ngt = np.empty(new_cap, dtype=np.float64); ngt[:cnt] = out_g_tom; out_g_tom = ngt
                        ngc = np.empty(new_cap, dtype=np.float64); ngc[:cnt] = out_g_cam; out_g_cam = ngc
                        nhi = np.empty(new_cap, dtype=np.float64); nhi[:cnt] = out_h_imp; out_h_imp = nhi
                        nha = np.empty(new_cap, dtype=np.float64); nha[:cnt] = out_h_am; out_h_am = nha
                        nxt = np.empty(new_cap, dtype=np.float64); nxt[:cnt] = out_ext; out_ext = nxt
                        nan = np.empty(new_cap, dtype=np.float64); nan[:cnt] = out_ancla; out_ancla = nan
                        nm5 = np.empty(new_cap, dtype=np.float64); nm5[:cnt] = out_mid50; out_mid50 = nm5
                        nm2 = np.empty(new_cap, dtype=np.float64); nm2[:cnt] = out_mid25; out_mid25 = nm2
                        no1 = np.empty(new_cap, dtype=np.float64); no1[:cnt] = out_orig100; out_orig100 = no1

                    out_k[cnt] = m
                    out_dir[cnt] = d
                    out_pvol[cnt] = pvol
                    out_pt_reg[cnt] = pt
                    out_exc_am[cnt] = exc_ratio
                    out_g_tom[cnt] = score_tom
                    out_g_cam[cnt] = score_cam
                    out_h_imp[cnt] = h_imp
                    out_h_am[cnt] = h_am
                    out_ext[cnt] = ext
                    out_ancla[cnt] = ancla_px
                    out_mid50[cnt] = mid50
                    out_mid25[cnt] = mid25
                    out_orig100[cnt] = orig100
                    cnt += 1
                    # Exclusión mutua por barra M1: a lo sumo un disparo por barra `m` en cada Caja Amarilla
                    break

            if fired_0 and fired_1 and fired_2:
                break

    return (
        out_k[:cnt], out_dir[:cnt], out_pvol[:cnt], out_pt_reg[:cnt],
        out_exc_am[:cnt], out_g_tom[:cnt], out_g_cam[:cnt],
        out_h_imp[:cnt], out_h_am[:cnt], out_ext[:cnt], out_ancla[:cnt],
        out_mid50[:cnt], out_mid25[:cnt], out_orig100[:cnt]
    )


def disparos(ctx: dict) -> pd.DataFrame:
    """Extrae todos los disparos causales de `CORREDOR-VOL-GAPS` sobre las escalas 50T (`esc=0`) y M1 (`esc=1`)
    y las variantes de ancho adelantado `W1=100%` (`vw=0`) y `W2=200%` (`vw=1`)."""
    o = np.asarray(ctx["o"], dtype=np.float64)
    h = np.asarray(ctx["h"], dtype=np.float64)
    l = np.asarray(ctx["l"], dtype=np.float64)
    c = np.asarray(ctx["c"], dtype=np.float64)
    v = np.asarray(ctx["v"], dtype=np.float64)
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    tpx = np.asarray(ctx["tpx"], dtype=np.float64)
    tstart = np.asarray(ctx["tstart"], dtype=np.int64)
    tick = float(ctx["tick"])
    n = len(c)

    cols = [
        "k", "ses", "esc", "vw", "pvol", "exc_am", "pt_reg", "g_tom", "g_cam",
        "tam_imp", "vwap_al", "dir_imp", "h_imp", "h_am", "ext", "ancla",
        "mid50", "mid25", "orig100"
    ]
    if n < SLOW_PERIOD + STABILITY_WINDOW + 10:
        return agregar(pd.DataFrame(columns=cols), ctx)

    atr, vwap = _atr_y_vwap_m1_nb(o, h, l, c, v, ses, 14)

    # 1. Construir barras 50T por sesión (con rangos exactos de ticks [b_t0, b_t1]) y barras M1
    cortes_ses = np.flatnonzero(np.r_[True, ses[1:] != ses[:-1], True])
    b50_k_l, b50_o_l, b50_h_l, b50_l_l, b50_c_l, b50_v_l, b50_t0_l, b50_t1_l = [], [], [], [], [], [], [], []
    for s_i in range(len(cortes_ses) - 1):
        a0, a1 = int(cortes_ses[s_i]), int(cortes_ses[s_i + 1])
        bk, bo, bh, bl, bc, bv, bt0, bt1 = _barras_50t_sesion_nb(tpx, tstart[a0:a1 + 1], a0, v, N_TICKS_50T)
        if len(bk):
            b50_k_l.append(bk); b50_o_l.append(bo); b50_h_l.append(bh)
            b50_l_l.append(bl); b50_c_l.append(bc); b50_v_l.append(bv)
            b50_t0_l.append(bt0); b50_t1_l.append(bt1)

    if b50_k_l:
        b50_k = np.concatenate(b50_k_l)
        b50_o = np.concatenate(b50_o_l)
        b50_h = np.concatenate(b50_h_l)
        b50_l = np.concatenate(b50_l_l)
        b50_c = np.concatenate(b50_c_l)
        b50_v = np.concatenate(b50_v_l)
        b50_t0 = np.concatenate(b50_t0_l)
        b50_t1 = np.concatenate(b50_t1_l)
    else:
        b50_k = b50_t0 = b50_t1 = np.zeros(0, dtype=np.int64)
        b50_o = b50_h = b50_l = b50_c = b50_v = np.zeros(0, dtype=np.float64)

    bm1_k = np.arange(n, dtype=np.int64)
    bm1_t0 = tstart[:n]
    bm1_t1 = tstart[1:n + 1]

    partes = []
    for esc, (bk, bo, bh, bl, bc, bv, bt0, bt1) in enumerate((
        (b50_k, b50_o, b50_h, b50_l, b50_c, b50_v, b50_t0, b50_t1),
        (bm1_k, o, h, l, c, v, bm1_t0, bm1_t1),
    )):
        if len(bc) < SLOW_PERIOD + STABILITY_WINDOW + 5:
            continue
        gk, glo, ghi, gconf = _gaps_barras_nb(
            bk, bo, bh, bl, bc, bt0, bt1, tpx, atr, tick, MIN_GAP_TICKS, esc == 0
        )
        for vw, fwd_pct in enumerate((100.0, 200.0)):
            zk, zk_ic, zdir, zblo, zbhi, zslo, zshi, zpoc, zvae, zpvol = _extraer_cajas_amarillas_nb(
                bk, bo, bh, bl, bc, bv, bt0, bt1, tpx, tick, fwd_pct
            )
            if not len(zk):
                continue
            (
                ok_k, ok_dir, ok_pvol, ok_pt, ok_exc, ok_gtom, ok_gcam,
                ok_himp, ok_ham, ok_ext, ok_anc, ok_m50, ok_m25, ok_o100
            ) = _escanear_ruptura_excursion_regreso_nb(
                zk, zk_ic, zdir, zblo, zbhi, zslo, zshi, zpoc, zvae, zpvol,
                gk, glo, ghi, gconf, h, l, c, ses, tick
            )
            if not len(ok_k):
                continue

            # Dirección de nuestra operación de reversión hacia el impulso inicial: s = -ok_dir
            s_op = -ok_dir
            ck = c[ok_k]
            vwap_k = vwap[ok_k]
            # vwap_al = 1 si la operación apunta hacia el VWAP o a favor del lado del VWAP
            vwap_al = np.where(
                ((s_op == 1) & (vwap_k >= ck)) | ((s_op == -1) & (vwap_k <= ck)),
                1, 0
            )
            tam_imp = ok_himp / np.maximum(atr[ok_k], tick)

            df_p = pd.DataFrame({
                "k": ok_k,
                "ses": ses[ok_k],
                "esc": np.full(len(ok_k), esc, dtype=np.int64),
                "vw": np.full(len(ok_k), vw, dtype=np.int64),
                "pvol": ok_pvol,
                "exc_am": ok_exc,
                "pt_reg": ok_pt,
                "g_tom": ok_gtom,
                "g_cam": ok_gcam,
                "tam_imp": tam_imp,
                "vwap_al": vwap_al,
                "dir_imp": ok_dir,
                "h_imp": ok_himp,
                "h_am": ok_ham,
                "ext": ok_ext,
                "ancla": ok_anc,
                "mid50": ok_m50,
                "mid25": ok_m25,
                "orig100": ok_o100,
            })
            partes.append(df_p)

    if not partes:
        return agregar(pd.DataFrame(columns=cols), ctx)

    D = pd.concat(partes, ignore_index=True)
    D = D.sort_values(["k", "esc", "vw", "pt_reg", "dir_imp"], kind="mergesort").reset_index(drop=True)
    return agregar(D, ctx)


def niveles(r: dict, ej: tuple, ctx: dict):
    """Calcula `(start, limite, s, entrada, stop, objetivo, be)` para un disparo `r` y una ejecución `ej = (ent, tp, sl)`."""
    k = int(r["k"])
    n = len(ctx["c"])
    if k + 1 >= n or ctx["ses"][k + 1] != ctx["ses"][k]:
        return None

    ent_tipo, tp_tipo, sl_tipo = ej
    tick = float(ctx["tick"])
    d_imp = int(r["dir_imp"])
    s = -d_imp  # Operamos el regreso hacia el impulso inicial (contra la ruptura)

    ck = float(ctx["c"][k])
    h_am = max(float(r["h_am"]), tick)
    ext = float(r["ext"])
    ancla = float(r["ancla"])

    # 1. Entrada y tipo de orden (0 = cierre, 1 = límite, 2 = stop/siguiente tick)
    if ent_tipo == "CIERRE":
        limite = 0
        e = np.round(ck / tick) * tick
    elif ent_tipo == "SIG":
        limite = 2
        e = np.round((ck + s * tick) / tick) * tick
    else:  # "ANCLA_LIM": orden límite buscando mejora estructural hacia el ancla/caja amarilla
        limite = 1
        mejora = max(tick, np.round((0.20 * h_am) / tick) * tick)
        e_lim = ck - s * mejora
        # Si el ancla ofrece una mejora aún más precisa dentro de 0.60 * h_am, promediamos con el ancla
        if s == -1 and ancla > ck and (ancla - ck) <= 0.60 * h_am:
            e_lim = max(e_lim, np.round(ancla / tick) * tick)
        elif s == 1 and ancla < ck and (ck - ancla) <= 0.60 * h_am:
            e_lim = min(e_lim, np.round(ancla / tick) * tick)
        e = np.round(e_lim / tick) * tick

    # 2. Target: MID50 (50% del impulso), MID25 (25% desde el origen = 75% de retroceso), ORIG100 (100% origen del impulso)
    orig100 = float(r["orig100"])
    mid50 = float(r["mid50"])
    mid25 = float(r["mid25"])
    recorrido_total = max(abs(e - orig100), 3.0 * tick)

    d50 = max((mid50 - e) * s, max(0.35 * recorrido_total, 2.0 * tick)) if (mid50 - e) * s < 2.0 * tick else (mid50 - e) * s
    d25_raw = (mid25 - e) * s if (mid25 - e) * s >= 3.0 * tick else max(0.65 * recorrido_total, 3.0 * tick)
    d25 = max(d25_raw, d50 + tick)
    d100_raw = (orig100 - e) * s if (orig100 - e) * s >= 4.0 * tick else max(1.00 * recorrido_total, 4.0 * tick)
    d100 = max(d100_raw, d25 + tick)
    if tp_tipo == "MID50":
        tp_raw = e + s * d50
    elif tp_tipo == "MID25":
        tp_raw = e + s * d25
    else:
        tp_raw = e + s * d100

    tp = np.round(tp_raw / tick) * tick

    # 3. Stop estructural más allá del extremo de la excursión `ext`
    if sl_tipo == "S_EXT":
        colchon = max(2.0 * tick, 0.15 * h_am)
    else:  # "S_CAJA"
        colchon = max(4.0 * tick, 0.55 * h_am)

    if s == -1:
        base_sl = max(ext, e + tick)
        sl = np.ceil((base_sl + colchon) / tick) * tick
    else:
        base_sl = min(ext, e - tick)
        sl = np.floor((base_sl - colchon) / tick) * tick

    if (tp - e) * s < tick or (e - sl) * s < tick:
        return None

    return (k + 1, limite, s, float(e), float(sl), float(tp), 0)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    """Versión vectorizada exacta de `niveles` (verificada contra `ops_por_fila` en el preflight)."""
    m = len(D)
    out = np.full((m, 7), np.nan, dtype=np.float64)
    if m == 0:
        return out

    k = D["k"].to_numpy(dtype=np.int64)
    n = len(ctx["c"])
    ses = np.asarray(ctx["ses"], dtype=np.int64)
    k_next = np.minimum(k + 1, n - 1)
    valid = (k + 1 < n) & (ses[k_next] == ses[k])

    ent_tipo, tp_tipo, sl_tipo = ej
    tick = float(ctx["tick"])
    d_imp = D["dir_imp"].to_numpy(dtype=np.int64)
    s = -d_imp

    ck = np.asarray(ctx["c"], dtype=np.float64)[k]
    h_am = np.maximum(D["h_am"].to_numpy(dtype=np.float64), tick)
    ext = D["ext"].to_numpy(dtype=np.float64)
    ancla = D["ancla"].to_numpy(dtype=np.float64)

    if ent_tipo == "CIERRE":
        limite = 0.0
        e = np.round(ck / tick) * tick
    elif ent_tipo == "SIG":
        limite = 2.0
        e = np.round((ck + s * tick) / tick) * tick
    else:
        limite = 1.0
        mejora = np.maximum(tick, np.round((0.20 * h_am) / tick) * tick)
        e_lim = ck - s * mejora
        ancla_r = np.round(ancla / tick) * tick
        cond_short = (s == -1) & (ancla > ck) & ((ancla - ck) <= 0.60 * h_am)
        cond_long = (s == 1) & (ancla < ck) & ((ck - ancla) <= 0.60 * h_am)
        e_lim = np.where(cond_short, np.maximum(e_lim, ancla_r), e_lim)
        e_lim = np.where(cond_long, np.minimum(e_lim, ancla_r), e_lim)
        e = np.round(e_lim / tick) * tick

    orig100 = D["orig100"].to_numpy(dtype=np.float64)
    mid50 = D["mid50"].to_numpy(dtype=np.float64)
    mid25 = D["mid25"].to_numpy(dtype=np.float64)
    recorrido_total = np.maximum(np.abs(e - orig100), 3.0 * tick)

    d50 = np.where((mid50 - e) * s < 2.0 * tick, np.maximum(0.35 * recorrido_total, 2.0 * tick), (mid50 - e) * s)
    d25_raw = np.where((mid25 - e) * s < 3.0 * tick, np.maximum(0.65 * recorrido_total, 3.0 * tick), (mid25 - e) * s)
    d25 = np.maximum(d25_raw, d50 + tick)
    d100_raw = np.where((orig100 - e) * s < 4.0 * tick, np.maximum(1.00 * recorrido_total, 4.0 * tick), (orig100 - e) * s)
    d100 = np.maximum(d100_raw, d25 + tick)
    if tp_tipo == "MID50":
        tp_raw = e + s * d50
    elif tp_tipo == "MID25":
        tp_raw = e + s * d25
    else:
        tp_raw = e + s * d100

    tp = np.round(tp_raw / tick) * tick

    if sl_tipo == "S_EXT":
        colchon = np.maximum(2.0 * tick, 0.15 * h_am)
    else:
        colchon = np.maximum(4.0 * tick, 0.55 * h_am)

    base_sl_short = np.maximum(ext, e + tick)
    base_sl_long = np.minimum(ext, e - tick)
    sl = np.where(
        s == -1,
        np.ceil((base_sl_short + colchon) / tick) * tick,
        np.floor((base_sl_long - colchon) / tick) * tick,
    )

    valid &= ((tp - e) * s >= tick) & ((e - sl) * s >= tick)
    idx = np.flatnonzero(valid)
    out[idx, 0] = k[idx] + 1
    out[idx, 1] = limite
    out[idx, 2] = s[idx]
    out[idx, 3] = e[idx]
    out[idx, 4] = sl[idx]
    out[idx, 5] = tp[idx]
    out[idx, 6] = 0.0
    return out
