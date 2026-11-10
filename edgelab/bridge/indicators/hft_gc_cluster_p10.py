"""HFTZonesGCClusterP10 — Motor causal exacto de `HFTZonesGCClusterP10.cs` (GC / Oro COMEX).

Reproduce bit a bit los 3 componentes target-free del indicador de NinjaTrader 8:
1. Motor de rachas HFT en subserie de 1-Tick (`SCALED_FUNNEL_V1` para GC + `MaxGapActivoSeg = 300.0`):
   - `MinPasos=6`, `MinAbsorbPasos=4`, `MinSweepTicks=6`, `MaxAvgMs=21.8`, `MaxTotalMs=212.0`,
     `MaxPausaMs=100.0`, `MinVolumeRate=197.0`, `MinTotalVolume=42.0`, `MaxRetrocesoTicks=2.0`,
     `RetrocesoPctHeight=50.0`, `PredatorAvgMs=4.5`, `UltraAvgMs=13.0`, reseed no fragmentante.
2. Solver causal de Clusters por compresión vertical relativa (`P10` de los 100 grupos previos de menor
   altura de 4 zonas HFT vigentes dentro de `VigenciaZonaMinutos = 360` min de mercado activo), incluyendo
   eventos `NEW` y `EXPAND`, `POC` gravitacional y marca causal `first_in_cluster_ns` por zona.
3. Confirmación causal de Alejamiento (`RevisarAlejamiento` en barras de `spec = 50` ticks, fijo en
   `AlejamientoTicks = 20` ticks por defecto, `ExcluirVShape = True`, `VShapePct = 50%`), emitiendo el
   instante exacto `t_away_ns` en que la zona adquiere Borde Gris (y prepara la flecha en la vela siguiente).

Además expone `LibroBarrerasHFT` para consultar sin look-ahead qué zonas HFT vigentes / no mitigadas y qué
`Clusters P10` se interponen en el recorrido `[precio_origen, precio_destino]` en cualquier instante `t_ns`.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]


DEFAULTS_GC = dict(
    min_pasos=6,
    min_absorb_pasos=4,
    mostrar_absorb=True,
    min_sweep_ticks=6,
    max_retroceso_ticks=2.0,
    retroceso_pct_height=50.0,
    max_avg_ms=21.8,
    max_total_ms=212.0,
    max_pausa_ms=100.0,
    min_volume_rate=197.0,
    min_total_volume=42.0,
    predator_avg_ms=4.5,
    ultra_avg_ms=13.0,
    max_gap_activo_seg=300.0,
    min_zonas_cluster=4,
    vigencia_zona_min=360.0,
    ventana_grupos=100,
    min_grupos_warmup=20,
    percentil_altura=10.0,
    comparacion_estricta=True,
    extension_cluster_barras=400,
    alejamiento_ticks=20,
    excluir_vshape=True,
    vshape_pct=50.0,
)

BUCKET_NAMES = ("Predator", "Ultra", "Fast", "Absorb")
AWAY_RES_CODES = {
    "": 0,
    "CONFIRMED": 1,
    "TRADED_THROUGH": 2,
    "V_SHAPE": 3,
    "BOTH_SIDES_SAME_BAR": 4,
    "ABSORB_SKIP": 5,
    "EXPIRED_BARS": 6,
}


@njit(cache=False)
def construir_barras_ticks_nb(ts_ns, pt, vol, ses, n_ticks):
    """Construye barras primarias de `n_ticks` cortadas en cada cambio de sesión CME (como NT8)."""
    n = len(ts_ns)
    if n == 0:
        z_i = np.zeros(0, np.int64)
        z_f = np.zeros(0, np.float64)
        return z_i, z_i, z_i, z_i, z_i, z_i, z_f, z_i, z_i
    cap = n // max(1, n_ticks) + 2048
    b_start_ns = np.empty(cap, np.int64)
    b_end_ns = np.empty(cap, np.int64)
    b_o = np.empty(cap, np.int64)
    b_h = np.empty(cap, np.int64)
    b_l = np.empty(cap, np.int64)
    b_c = np.empty(cap, np.int64)
    b_v = np.empty(cap, np.float64)
    b_ses = np.empty(cap, np.int64)
    tick_bar_idx = np.empty(n, np.int64)

    nb = 0
    cnt = 0
    cur_ses = ses[0]
    st_ns = ts_ns[0]
    op = hi = lo = pt[0]
    vv = 0.0
    i_bar_start = 0

    for i in range(n):
        if cnt > 0 and ses[i] != cur_ses:
            if nb >= cap:
                cap2 = cap * 2
                t1 = np.empty(cap2, np.int64); t1[:nb] = b_start_ns[:nb]; b_start_ns = t1
                t2 = np.empty(cap2, np.int64); t2[:nb] = b_end_ns[:nb]; b_end_ns = t2
                t3 = np.empty(cap2, np.int64); t3[:nb] = b_o[:nb]; b_o = t3
                t4 = np.empty(cap2, np.int64); t4[:nb] = b_h[:nb]; b_h = t4
                t5 = np.empty(cap2, np.int64); t5[:nb] = b_l[:nb]; b_l = t5
                t6 = np.empty(cap2, np.int64); t6[:nb] = b_c[:nb]; b_c = t6
                t7 = np.empty(cap2, np.float64); t7[:nb] = b_v[:nb]; b_v = t7
                t8 = np.empty(cap2, np.int64); t8[:nb] = b_ses[:nb]; b_ses = t8
                cap = cap2
            b_start_ns[nb] = st_ns
            b_end_ns[nb] = ts_ns[i - 1]
            b_o[nb] = op; b_h[nb] = hi; b_l[nb] = lo; b_c[nb] = pt[i - 1]
            b_v[nb] = vv; b_ses[nb] = cur_ses
            for k in range(i_bar_start, i):
                tick_bar_idx[k] = nb
            nb += 1
            cnt = 0

        if cnt == 0:
            cur_ses = ses[i]
            st_ns = ts_ns[i]
            op = hi = lo = pt[i]
            vv = float(vol[i])
            cnt = 1
            i_bar_start = i
        else:
            p = pt[i]
            if p > hi:
                hi = p
            if p < lo:
                lo = p
            vv += float(vol[i])
            cnt += 1

        if cnt >= n_ticks:
            if nb >= cap:
                cap2 = cap * 2
                t1 = np.empty(cap2, np.int64); t1[:nb] = b_start_ns[:nb]; b_start_ns = t1
                t2 = np.empty(cap2, np.int64); t2[:nb] = b_end_ns[:nb]; b_end_ns = t2
                t3 = np.empty(cap2, np.int64); t3[:nb] = b_o[:nb]; b_o = t3
                t4 = np.empty(cap2, np.int64); t4[:nb] = b_h[:nb]; b_h = t4
                t5 = np.empty(cap2, np.int64); t5[:nb] = b_l[:nb]; b_l = t5
                t6 = np.empty(cap2, np.int64); t6[:nb] = b_c[:nb]; b_c = t6
                t7 = np.empty(cap2, np.float64); t7[:nb] = b_v[:nb]; b_v = t7
                t8 = np.empty(cap2, np.int64); t8[:nb] = b_ses[:nb]; b_ses = t8
                cap = cap2
            b_start_ns[nb] = st_ns
            b_end_ns[nb] = ts_ns[i]
            b_o[nb] = op; b_h[nb] = hi; b_l[nb] = lo; b_c[nb] = pt[i]
            b_v[nb] = vv; b_ses[nb] = cur_ses
            for k in range(i_bar_start, i + 1):
                tick_bar_idx[k] = nb
            nb += 1
            cnt = 0

    if cnt > 0:
        if nb >= cap:
            cap2 = cap + 4
            t1 = np.empty(cap2, np.int64); t1[:nb] = b_start_ns[:nb]; b_start_ns = t1
            t2 = np.empty(cap2, np.int64); t2[:nb] = b_end_ns[:nb]; b_end_ns = t2
            t3 = np.empty(cap2, np.int64); t3[:nb] = b_o[:nb]; b_o = t3
            t4 = np.empty(cap2, np.int64); t4[:nb] = b_h[:nb]; b_h = t4
            t5 = np.empty(cap2, np.int64); t5[:nb] = b_l[:nb]; b_l = t5
            t6 = np.empty(cap2, np.int64); t6[:nb] = b_c[:nb]; b_c = t6
            t7 = np.empty(cap2, np.float64); t7[:nb] = b_v[:nb]; b_v = t7
            t8 = np.empty(cap2, np.int64); t8[:nb] = b_ses[:nb]; b_ses = t8
        b_start_ns[nb] = st_ns
        b_end_ns[nb] = ts_ns[n - 1]
        b_o[nb] = op; b_h[nb] = hi; b_l[nb] = lo; b_c[nb] = pt[n - 1]
        b_v[nb] = vv; b_ses[nb] = cur_ses
        for k in range(i_bar_start, n):
            tick_bar_idx[k] = nb
        nb += 1

    return (b_start_ns[:nb], b_end_ns[:nb], b_o[:nb], b_h[:nb], b_l[:nb], b_c[:nb], b_v[:nb], b_ses[:nb], tick_bar_idx)


@njit(cache=False)
def _finalizar_racha_nb(
    dir_, streak, valid_steps, sw_lo, sw_hi, max_retro, total_vol, sum_ms, n_intervals,
    t_start_ns, t_last_ns, t_avail_ns, start_tick_idx, last_tick_idx, avail_tick_idx, end_pt, cvd, reloj_seg,
    min_pasos, min_absorb_pasos, mostrar_absorb, min_sweep_ticks, max_retro_ticks, retro_pct,
    max_avg_ms, max_total_ms, min_vol_rate, min_total_vol, pred_ms, ultra_ms,
    z_int, z_flt, nz
):
    sweep_ticks = float(sw_hi - sw_lo)
    is_sweep = sweep_ticks >= min_sweep_ticks
    is_absorb = (not is_sweep) and (mostrar_absorb == 1)
    min_req = min_pasos if is_sweep else min_absorb_pasos
    if valid_steps < min_req or (not is_sweep and not is_absorb):
        return nz

    avg_ms = sum_ms / float(max(1, n_intervals))
    dur_sec = max(sum_ms, 1.0) / 1000.0
    vol_rate = total_vol / dur_sec
    max_allowed_retro = max(max_retro_ticks, (retro_pct / 100.0) * sweep_ticks)
    limpio_ok = is_absorb or (max_retro <= max_allowed_retro + 1e-9)

    if avg_ms <= max_avg_ms and sum_ms <= max_total_ms and vol_rate >= min_vol_rate and total_vol >= min_total_vol and limpio_ok:
        if is_absorb:
            bkt = 3
        elif avg_ms <= pred_ms:
            bkt = 0
        elif avg_ms <= ultra_ms:
            bkt = 1
        else:
            bkt = 2

        lo_tk = sw_lo if sw_lo <= sw_hi else sw_hi
        hi_tk = sw_hi if sw_hi >= sw_lo else sw_lo

        z_int[nz, 0] = t_start_ns
        z_int[nz, 1] = t_last_ns
        z_int[nz, 2] = start_tick_idx
        z_int[nz, 3] = last_tick_idx
        z_int[nz, 4] = lo_tk
        z_int[nz, 5] = hi_tk
        z_int[nz, 6] = dir_
        z_int[nz, 7] = bkt
        z_int[nz, 8] = streak
        z_int[nz, 9] = valid_steps
        z_int[nz, 10] = end_pt
        z_int[nz, 11] = t_avail_ns
        z_int[nz, 12] = avail_tick_idx

        z_flt[nz, 0] = reloj_seg
        z_flt[nz, 1] = avg_ms
        z_flt[nz, 2] = sum_ms
        z_flt[nz, 3] = vol_rate
        z_flt[nz, 4] = total_vol
        z_flt[nz, 5] = max_retro
        z_flt[nz, 6] = cvd
        nz += 1
    return nz


@njit(cache=False)
def detectar_zonas_ticks_nb(
    ts_ns, pt, vol,
    min_pasos=6, min_absorb_pasos=4, mostrar_absorb=1, min_sweep_ticks=6,
    max_retro_ticks=2.0, retro_pct=50.0, max_avg_ms=21.8, max_total_ms=212.0,
    max_pausa_ms=100.0, min_vol_rate=197.0, min_total_vol=42.0,
    pred_ms=4.5, ultra_ms=13.0, max_gap_activo_seg=300.0
):
    """Réplica exacta en Numba de `ProcesarSweeps()` + `ActualizarRelojMercado()` de `HFTZonesGCClusterP10.cs`."""
    n = len(ts_ns)
    cap = 2048
    z_int = np.empty((cap, 13), np.int64)
    z_flt = np.empty((cap, 7), np.float64)
    nz = 0
    if n < 6:
        return z_int[:0], z_flt[:0]

    reloj_seg = 0.0
    prev_ts = ts_ns[0]
    last_side = 0

    dir_ = 0
    streak = 0
    valid_steps = 0
    sw_hi = 0
    sw_lo = 0
    extremo = 0
    max_retro = 0.0
    total_vol = 0.0
    sum_ms = 0.0
    n_intervals = 0
    t_start_ns = 0
    t_last_ns = 0
    start_tick_idx = 0
    last_tick_idx = 0
    end_pt = 0
    cvd = 0.0

    for i in range(1, 5):
        dt = (ts_ns[i] - prev_ts) * 1e-9
        if dt > 0.0:
            reloj_seg += dt if dt < max_gap_activo_seg else max_gap_activo_seg
        prev_ts = ts_ns[i]

    for i in range(5, n):
        t_cur = ts_ns[i]
        dt = (t_cur - prev_ts) * 1e-9
        if dt > 0.0:
            reloj_seg += dt if dt < max_gap_activo_seg else max_gap_activo_seg
        prev_ts = t_cur

        if nz + 2 >= cap:
            cap2 = cap * 2
            zi2 = np.empty((cap2, 13), np.int64); zi2[:nz] = z_int[:nz]; z_int = zi2
            zf2 = np.empty((cap2, 7), np.float64); zf2[:nz] = z_flt[:nz]; z_flt = zf2
            cap = cap2

        ms = (t_cur - ts_ns[i - 1]) * 1e-6
        v = float(vol[i])
        cl = pt[i]
        cl_p = pt[i - 1]

        if cl > cl_p:
            side = 1
        elif cl < cl_p:
            side = -1
        else:
            side = last_side if last_side != 0 else 1
        last_side = side
        signed_vol = float(side) * v

        is_down = cl <= cl_p
        is_up = cl >= cl_p

        if dir_ != 0 and ms > max_pausa_ms:
            nz = _finalizar_racha_nb(
                dir_, streak, valid_steps, sw_lo, sw_hi, max_retro, total_vol, sum_ms, n_intervals,
                t_start_ns, t_last_ns, t_cur, start_tick_idx, last_tick_idx, i, end_pt, cvd, reloj_seg,
                min_pasos, min_absorb_pasos, mostrar_absorb, min_sweep_ticks, max_retro_ticks, retro_pct,
                max_avg_ms, max_total_ms, min_vol_rate, min_total_vol, pred_ms, ultra_ms,
                z_int, z_flt, nz
            )
            dir_ = 0
            streak = 0; valid_steps = 0; total_vol = 0.0; sum_ms = 0.0; n_intervals = 0
            max_retro = 0.0; cvd = 0.0
            continue

        if dir_ == 0:
            if is_down:
                dir_ = -1
                streak = 1; valid_steps = 1
                sw_hi = cl; sw_lo = cl; extremo = cl; max_retro = 0.0
                total_vol = v; sum_ms = 0.0; n_intervals = 0
                t_start_ns = t_cur; t_last_ns = t_cur
                start_tick_idx = i; last_tick_idx = i; end_pt = cl; cvd = signed_vol
            elif is_up:
                dir_ = 1
                streak = 1; valid_steps = 1
                sw_hi = cl; sw_lo = cl; extremo = cl; max_retro = 0.0
                total_vol = v; sum_ms = 0.0; n_intervals = 0
                t_start_ns = t_cur; t_last_ns = t_cur
                start_tick_idx = i; last_tick_idx = i; end_pt = cl; cvd = signed_vol
        elif dir_ == -1:
            if is_down:
                streak += 1; valid_steps += 1
                if cl > sw_hi: sw_hi = cl
                if cl < sw_lo: sw_lo = cl
                if cl < extremo: extremo = cl
                adv = float(cl - extremo)
                if adv > max_retro: max_retro = adv
                sum_ms += ms; n_intervals += 1; total_vol += v; cvd += signed_vol
                t_last_ns = t_cur; last_tick_idx = i; end_pt = cl
            else:
                cur_ret = float(cl - extremo)
                sw_h_tk = float(sw_hi - sw_lo)
                max_allow = max(max_retro_ticks, (retro_pct / 100.0) * sw_h_tk)
                if cur_ret <= max_allow + 1e-9:
                    streak += 1
                    if cl > sw_hi: sw_hi = cl
                    if cl < sw_lo: sw_lo = cl
                    if cl < extremo: extremo = cl
                    adv = float(cl - extremo)
                    if adv > max_retro: max_retro = adv
                    sum_ms += ms; n_intervals += 1; total_vol += v; cvd += signed_vol
                    t_last_ns = t_cur; last_tick_idx = i; end_pt = cl
                else:
                    nz = _finalizar_racha_nb(
                        dir_, streak, valid_steps, sw_lo, sw_hi, max_retro, total_vol, sum_ms, n_intervals,
                        t_start_ns, t_last_ns, t_cur, start_tick_idx, last_tick_idx, i, end_pt, cvd, reloj_seg,
                        min_pasos, min_absorb_pasos, mostrar_absorb, min_sweep_ticks, max_retro_ticks, retro_pct,
                        max_avg_ms, max_total_ms, min_vol_rate, min_total_vol, pred_ms, ultra_ms,
                        z_int, z_flt, nz
                    )
                    if is_up:
                        dir_ = 1
                        streak = 1; valid_steps = 1
                        sw_hi = cl; sw_lo = cl; extremo = cl; max_retro = 0.0
                        total_vol = v; sum_ms = 0.0; n_intervals = 0
                        t_start_ns = t_cur; t_last_ns = t_cur
                        start_tick_idx = i; last_tick_idx = i; end_pt = cl; cvd = signed_vol
                    else:
                        dir_ = 0
        else:
            if is_up:
                streak += 1; valid_steps += 1
                if cl > sw_hi: sw_hi = cl
                if cl < sw_lo: sw_lo = cl
                if cl > extremo: extremo = cl
                adv = float(extremo - cl)
                if adv > max_retro: max_retro = adv
                sum_ms += ms; n_intervals += 1; total_vol += v; cvd += signed_vol
                t_last_ns = t_cur; last_tick_idx = i; end_pt = cl
            else:
                cur_ret = float(extremo - cl)
                sw_h_tk = float(sw_hi - sw_lo)
                max_allow = max(max_retro_ticks, (retro_pct / 100.0) * sw_h_tk)
                if cur_ret <= max_allow + 1e-9:
                    streak += 1
                    if cl > sw_hi: sw_hi = cl
                    if cl < sw_lo: sw_lo = cl
                    if cl > extremo: extremo = cl
                    adv = float(extremo - cl)
                    if adv > max_retro: max_retro = adv
                    sum_ms += ms; n_intervals += 1; total_vol += v; cvd += signed_vol
                    t_last_ns = t_cur; last_tick_idx = i; end_pt = cl
                else:
                    nz = _finalizar_racha_nb(
                        dir_, streak, valid_steps, sw_lo, sw_hi, max_retro, total_vol, sum_ms, n_intervals,
                        t_start_ns, t_last_ns, t_cur, start_tick_idx, last_tick_idx, i, end_pt, cvd, reloj_seg,
                        min_pasos, min_absorb_pasos, mostrar_absorb, min_sweep_ticks, max_retro_ticks, retro_pct,
                        max_avg_ms, max_total_ms, min_vol_rate, min_total_vol, pred_ms, ultra_ms,
                        z_int, z_flt, nz
                    )
                    if is_down:
                        dir_ = -1
                        streak = 1; valid_steps = 1
                        sw_hi = cl; sw_lo = cl; extremo = cl; max_retro = 0.0
                        total_vol = v; sum_ms = 0.0; n_intervals = 0
                        t_start_ns = t_cur; t_last_ns = t_cur
                        start_tick_idx = i; last_tick_idx = i; end_pt = cl; cvd = signed_vol
                    else:
                        dir_ = 0

    return z_int[:nz], z_flt[:nz]


def _calcular_poc_miembros(miembros_lo, miembros_hi, miembros_vol, lo_tk: int, hi_tk: int, tick: float) -> float:
    if hi_tk <= lo_tk:
        return float(lo_tk) * tick
    best_tk = (lo_tk + hi_tk) // 2
    best_cnt = -1
    best_vol = -1.0
    mid_tk = 0.5 * (lo_tk + hi_tk)
    for tk in range(lo_tk, hi_tk + 1):
        m = (miembros_lo <= tk) & (miembros_hi >= tk)
        cnt = int(m.sum())
        vol = float(miembros_vol[m].sum()) if cnt else 0.0
        mejora = (
            cnt > best_cnt
            or (cnt == best_cnt and vol > best_vol + 1e-9)
            or (cnt == best_cnt and abs(vol - best_vol) <= 1e-9 and abs(tk - mid_tk) < abs(best_tk - mid_tk))
        )
        if mejora:
            best_cnt = cnt
            best_vol = vol
            best_tk = tk
    return float(best_tk) * tick


@njit(cache=False)
def resolver_alejamiento_barras_nb(
    z_base_bar, z_lo_px, z_hi_px, z_dir, z_bkt, z_end_px,
    b_end_ns, b_hi_px, b_lo_px, tick=0.10,
    alejamiento_ticks=20, excluir_vshape=1, vshape_pct=50.0, excluir_absorb=0, max_barras=0
):
    """Réplica exacta IEEE-754 en Numba de `RevisarAlejamiento()` de `HFTZonesGCClusterP10.cs`."""
    nz = len(z_base_bar)
    nb = len(b_hi_px)
    res_code = np.zeros(nz, np.int64)
    away_dir = np.zeros(nz, np.int64)
    away_bar = np.full(nz, -1, np.int64)
    away_ns = np.full(nz, -1, np.int64)
    thr = float(alejamiento_ticks) * tick

    for i in range(nz):
        base_b = z_base_bar[i]
        if base_b < 0 or base_b + 1 >= nb:
            continue
        z_lo = z_lo_px[i]
        z_up = z_hi_px[i]
        bkt = z_bkt[i]
        d = z_dir[i]
        end_px = z_end_px[i]

        touched_up = False
        touched_lo = False

        for cur_b in range(base_b + 1, nb):
            if excluir_absorb == 1 and bkt == 3:
                res_code[i] = 5
                away_bar[i] = cur_b
                away_ns[i] = b_end_ns[cur_b]
                break

            if excluir_vshape == 1 and bkt != 3:
                alt = max(z_up - z_lo, tick)
                retro = (z_up - end_px) if d == 1 else (end_px - z_lo)
                if retro >= (vshape_pct / 100.0) * alt:
                    res_code[i] = 3
                    away_bar[i] = cur_b
                    away_ns[i] = b_end_ns[cur_b]
                    break

            if max_barras > 0 and (cur_b - base_b) > max_barras:
                res_code[i] = 6
                away_bar[i] = cur_b
                away_ns[i] = b_end_ns[cur_b]
                break

            hi = b_hi_px[cur_b]
            lo = b_lo_px[cur_b]
            dist_up = hi - z_up
            dist_dn = z_lo - lo
            up = dist_up >= thr
            dn = dist_dn >= thr

            if up or dn:
                t_up_now = touched_up or (hi >= z_up)
                t_lo_now = touched_lo or (lo <= z_lo)
                completa = t_up_now and t_lo_now
                ad = 1 if (up and not dn) else (-1 if (dn and not up) else 0)
                away_bar[i] = cur_b
                away_ns[i] = b_end_ns[cur_b]
                if (not completa) and ad != 0:
                    res_code[i] = 1
                    away_dir[i] = ad
                else:
                    res_code[i] = 2 if completa else 4
                break

            if hi >= z_up:
                touched_up = True
            if lo <= z_lo:
                touched_lo = True
            if touched_up and touched_lo:
                res_code[i] = 2
                away_bar[i] = cur_b
                away_ns[i] = b_end_ns[cur_b]
                break

    return res_code, away_dir, away_bar, away_ns


@njit(cache=False)
def _evaluar_p10_scan_nb(
    z_lo_tk, z_hi_tk, z_mclock,
    k_req, max_seg_activo, min_warmup, max_hist, q, comparacion_estricta
):
    nz = len(z_lo_tk)
    i0_arr = np.zeros(nz, np.int64)
    vig_counts = np.zeros(nz, np.int64)
    min4_h = np.full(nz, -1, np.int64)
    hist4_cnt = np.zeros(nz, np.int64)
    p10_thr = np.zeros(nz, np.int64)
    max_span_arr = np.full(nz, -1, np.int64)
    trig_clust = np.zeros(nz, np.int64)

    hist_buf = np.zeros(max_hist, np.int64)
    hist_total = 0
    need_others = k_req - 1

    for idx in range(nz):
        t_mc = z_mclock[idx]
        i0 = idx
        while i0 > 0 and (t_mc - z_mclock[i0 - 1]) <= max_seg_activo + 1e-9:
            i0 -= 1
        i0_arr[idx] = i0
        vc = idx - i0 + 1
        vig_counts[idx] = vc
        if vc < k_req:
            continue

        n_otras = idx - i0
        otras = np.empty(n_otras, np.int64)
        otras_hi = np.empty(n_otras, np.int64)
        for j in range(n_otras):
            oi = idx - 1 - j
            otras[j] = oi
            otras_hi[j] = z_hi_tk[oi]
        ord_idx = np.argsort(otras_hi)

        n_lo = z_lo_tk[idx]
        n_hi = z_hi_tk[idx]
        mejor_h4 = 10**15

        for vi in range(idx, i0 - 1, -1):
            piso = z_lo_tk[vi]
            if piso > n_lo:
                continue
            tomados = 0
            max_up = n_hi
            for j in range(n_otras):
                oi = otras[ord_idx[j]]
                if z_lo_tk[oi] < piso:
                    continue
                u = z_hi_tk[oi]
                if u > max_up:
                    max_up = u
                tomados += 1
                if tomados == need_others:
                    break
            if tomados == need_others:
                sp = max_up - piso
                if sp < mejor_h4:
                    mejor_h4 = sp

        if mejor_h4 >= 10**15:
            continue

        n_hist = hist_total if hist_total < max_hist else max_hist
        es_cluster = False
        umbral_p10 = 0
        max_span = -1
        if n_hist >= min_warmup:
            ordenado = np.sort(hist_buf[:n_hist])
            idx_corte = int(math.ceil(q * float(n_hist))) - 1
            if idx_corte < 0:
                idx_corte = 0
            elif idx_corte >= n_hist:
                idx_corte = n_hist - 1
            umbral_p10 = ordenado[idx_corte]
            piso_hist = ordenado[0]
            if comparacion_estricta == 1:
                max_span = (umbral_p10 - 1) if umbral_p10 > piso_hist else umbral_p10
            else:
                max_span = umbral_p10
            es_cluster = mejor_h4 <= max_span

        min4_h[idx] = mejor_h4
        hist4_cnt[idx] = n_hist
        p10_thr[idx] = umbral_p10
        max_span_arr[idx] = max_span
        trig_clust[idx] = 1 if es_cluster else 0

        if hist_total < max_hist:
            hist_buf[hist_total] = mejor_h4
        else:
            for j in range(max_hist - 1):
                hist_buf[j] = hist_buf[j + 1]
            hist_buf[max_hist - 1] = mejor_h4
        hist_total += 1

    return i0_arr, vig_counts, min4_h, hist4_cnt, p10_thr, max_span_arr, trig_clust


def evaluar_clusters_p10_causal(
    z_start_bar: np.ndarray,
    z_end_bar: np.ndarray,
    z_end_ns: np.ndarray,
    z_lo_tk: np.ndarray,
    z_hi_tk: np.ndarray,
    z_bkt: np.ndarray,
    z_vol: np.ndarray,
    z_mclock: np.ndarray,
    tick: float = 0.10,
    min_zonas_cluster: int = 4,
    vigencia_zona_min: float = 360.0,
    ventana_grupos: int = 100,
    min_grupos_warmup: int = 20,
    percentil_altura: float = 10.0,
    comparacion_estricta: bool = True,
    extension_cluster_barras: int = 400,
) -> Tuple[dict, pd.DataFrame]:
    """Réplica 100% exacta y causal de `EvaluarClusterPorAlturaRelativa` + `RegistrarOActualizarCluster`."""
    nz = len(z_lo_tk)
    first_in_cluster_ns = np.full(nz, -1, np.int64)
    in_cluster_final = np.zeros(nz, np.int64)

    active_clusters = []
    cluster_events = []
    cluster_counter = 0
    event_seq = 0

    k_req = max(2, int(min_zonas_cluster))
    max_seg_activo = max(1.0, float(vigencia_zona_min)) * 60.0
    min_warmup = max(5, min(int(ventana_grupos), int(min_grupos_warmup)))
    max_hist = max(10, int(ventana_grupos))
    q = max(0.01, min(0.99, float(percentil_altura) / 100.0))

    i0_arr, vig_counts, min4_h, hist4_cnt, p10_thr, max_span_arr, trig_clust = _evaluar_p10_scan_nb(
        np.asarray(z_lo_tk, np.int64),
        np.asarray(z_hi_tk, np.int64),
        np.asarray(z_mclock, np.float64),
        k_req,
        max_seg_activo,
        min_warmup,
        max_hist,
        q,
        1 if comparacion_estricta else 0,
    )

    for idx in np.flatnonzero(trig_clust == 1):
        idx = int(idx)
        t_mc = float(z_mclock[idx])
        i0 = int(i0_arr[idx])
        vig_idx = np.arange(idx, i0 - 1, -1, dtype=np.int64)
        n_lo = int(z_lo_tk[idx])
        n_hi = int(z_hi_tk[idx])
        max_span = int(max_span_arr[idx])
        umbral_p10 = int(p10_thr[idx])

        mejor_grupo = None
        mejor_lo = 0
        mejor_hi = 0
        mejor_sp_g = 10**15
        mejor_vol_g = -1.0

        for vi in vig_idx:
            piso = int(z_lo_tk[vi])
            if piso > n_lo:
                continue
            techo_max = piso + max_span
            if n_hi > techo_max:
                continue
            m = (z_lo_tk[vig_idx] >= piso) & (z_hi_tk[vig_idx] <= techo_max)
            dentro = vig_idx[m]
            if len(dentro) < k_req:
                continue
            lo_r = int(z_lo_tk[dentro].min())
            hi_r = int(z_hi_tk[dentro].max())
            sp_r = hi_r - lo_r
            vol_r = float(z_vol[dentro].sum())
            mejora = (
                mejor_grupo is None
                or len(dentro) > len(mejor_grupo)
                or (len(dentro) == len(mejor_grupo) and sp_r < mejor_sp_g)
                or (len(dentro) == len(mejor_grupo) and sp_r == mejor_sp_g and vol_r > mejor_vol_g)
            )
            if mejora:
                mejor_grupo = dentro
                mejor_lo = lo_r
                mejor_hi = hi_r
                mejor_sp_g = sp_r
                mejor_vol_g = vol_r

        if mejor_grupo is None or len(mejor_grupo) < k_req:
            continue

        t_conf_ns = int(z_end_ns[idx])
        earliest_sb = int(z_start_bar[mejor_grupo].min())
        for m_idx in mejor_grupo:
            in_cluster_final[m_idx] = 1
            if first_in_cluster_ns[m_idx] < 0:
                first_in_cluster_ns[m_idx] = t_conf_ns

        poc_px = _calcular_poc_miembros(
            z_lo_tk[mejor_grupo], z_hi_tk[mejor_grupo], z_vol[mejor_grupo], mejor_lo, mejor_hi, tick
        )
        draw_start = earliest_sb
        draw_end = int(z_end_bar[idx]) + max(1, int(extension_cluster_barras))

        existente = None
        for c in reversed(active_clusters):
            vig_graf = int(z_start_bar[idx]) <= c["end_bar"]
            vig_tiempo = (t_mc - c["last_mc"]) <= max_seg_activo + 1e-9
            if not (vig_graf and vig_tiempo):
                continue
            if min(mejor_hi, c["hi_tk"]) < max(mejor_lo, c["lo_tk"]):
                continue
            u_lo = min(mejor_lo, c["lo_tk"])
            u_hi = max(mejor_hi, c["hi_tk"])
            if (u_hi - u_lo) <= max_span:
                existente = c
                break

        if existente is not None:
            existente["lo_tk"] = min(existente["lo_tk"], mejor_lo)
            existente["hi_tk"] = max(existente["hi_tk"], mejor_hi)
            existente["start_bar"] = min(existente["start_bar"], draw_start)
            existente["end_bar"] = max(existente["end_bar"], draw_end)
            existente["last_mc"] = t_mc
            existente["p10_tk"] = umbral_p10
            for m_idx in mejor_grupo:
                existente["members"].add(int(m_idx))
            mem_arr = np.array(sorted(existente["members"]), dtype=np.int64)
            existente["zone_count"] = len(mem_arr)
            existente["total_vol"] = float(z_vol[mem_arr].sum())
            existente["poc"] = _calcular_poc_miembros(
                z_lo_tk[mem_arr], z_hi_tk[mem_arr], z_vol[mem_arr], existente["lo_tk"], existente["hi_tk"], tick
            )
            existente["absorb_ultra_frac"] = float((z_bkt[mem_arr] != 0).mean())
            event_seq += 1
            cluster_events.append(dict(
                event_seq=event_seq,
                cluster_id=existente["id"],
                event_type="EXPAND",
                trigger_zone_idx=idx,
                confirmed_bar=int(z_end_bar[idx]),
                t_ns=t_conf_ns,
                market_clock_sec=t_mc,
                lo=existente["lo_tk"] * tick,
                hi=existente["hi_tk"] * tick,
                lo_tk=existente["lo_tk"],
                hi_tk=existente["hi_tk"],
                height_ticks=existente["hi_tk"] - existente["lo_tk"],
                p10_ticks=umbral_p10,
                zone_count=existente["zone_count"],
                total_vol=existente["total_vol"],
                poc=existente["poc"],
                absorb_ultra_frac=existente["absorb_ultra_frac"],
            ))
        else:
            cluster_counter += 1
            mem_set = {int(x) for x in mejor_grupo}
            mem_arr = np.array(sorted(mem_set), dtype=np.int64)
            ab_frac = float((z_bkt[mem_arr] != 0).mean())
            cz = dict(
                id=cluster_counter,
                lo_tk=mejor_lo,
                hi_tk=mejor_hi,
                start_bar=draw_start,
                confirmed_bar=int(z_end_bar[idx]),
                end_bar=draw_end,
                last_mc=t_mc,
                p10_tk=umbral_p10,
                zone_count=len(mem_arr),
                total_vol=float(z_vol[mem_arr].sum()),
                poc=poc_px,
                absorb_ultra_frac=ab_frac,
                members=mem_set,
            )
            active_clusters.append(cz)
            if len(active_clusters) > 500:
                active_clusters.pop(0)
            event_seq += 1
            cluster_events.append(dict(
                event_seq=event_seq,
                cluster_id=cluster_counter,
                event_type="NEW",
                trigger_zone_idx=idx,
                confirmed_bar=int(z_end_bar[idx]),
                t_ns=t_conf_ns,
                market_clock_sec=t_mc,
                lo=mejor_lo * tick,
                hi=mejor_hi * tick,
                lo_tk=mejor_lo,
                hi_tk=mejor_hi,
                height_ticks=mejor_hi - mejor_lo,
                p10_ticks=umbral_p10,
                zone_count=len(mem_arr),
                total_vol=cz["total_vol"],
                poc=poc_px,
                absorb_ultra_frac=ab_frac,
            ))

    cols_z = dict(
        vigentes_count=vig_counts,
        min4_height_ticks=min4_h,
        hist4_count=hist4_cnt,
        p10_threshold_ticks=p10_thr,
        max_span_allowed_ticks=max_span_arr,
        triggered_cluster=trig_clust,
        in_cluster=in_cluster_final,
        first_in_cluster_ns=first_in_cluster_ns,
    )
    cols_clust = ["event_seq", "cluster_id", "event_type", "trigger_zone_idx", "confirmed_bar",
                  "t_ns", "market_clock_sec", "lo", "hi", "lo_tk", "hi_tk", "height_ticks",
                  "p10_ticks", "zone_count", "total_vol", "poc", "absorb_ultra_frac"]
    clust_df = pd.DataFrame(cluster_events, columns=cols_clust) if cluster_events else pd.DataFrame(columns=cols_clust)
    return cols_z, clust_df


def ejecutar_detector_completo(
    ts_ns: np.ndarray,
    price_ticks: np.ndarray,
    vol: np.ndarray,
    ses: np.ndarray,
    tick: float = 0.10,
    spec_barras_ticks: int = 50,
    params: Optional[dict] = None,
) -> Dict[str, pd.DataFrame]:
    """Ejecuta de punta a punta el detector de zonas HFT GC + Clusters P10 + Alejamiento en 50T."""
    p = dict(DEFAULTS_GC)
    if params:
        p.update(params)

    ts_ns = np.asarray(ts_ns, np.int64)
    pt = np.asarray(price_ticks, np.int64)
    vo = np.asarray(vol, np.float64)
    ss = np.asarray(ses, np.int64)

    b_st, b_en, b_o, b_h, b_l, b_c, b_v, b_ses, tk_bidx = construir_barras_ticks_nb(
        ts_ns, pt, vo, ss, int(spec_barras_ticks)
    )
    z_int, z_flt = detectar_zonas_ticks_nb(
        ts_ns, pt, vo,
        int(p["min_pasos"]), int(p["min_absorb_pasos"]), 1 if p["mostrar_absorb"] else 0,
        int(p["min_sweep_ticks"]), float(p["max_retroceso_ticks"]), float(p["retroceso_pct_height"]),
        float(p["max_avg_ms"]), float(p["max_total_ms"]), float(p["max_pausa_ms"]),
        float(p["min_volume_rate"]), float(p["min_total_volume"]),
        float(p["predator_avg_ms"]), float(p["ultra_avg_ms"]), float(p["max_gap_activo_seg"]),
    )

    cols_z = [
        "zone_id", "t_start_ns", "t_ns", "start_bar_50t", "end_bar_50t",
        "lo", "hi", "lo_tk", "hi_tk", "height_ticks", "dir", "bucket",
        "pasos", "valid_steps", "end_pt", "market_clock_sec",
        "avg_ms", "total_ms", "vol_rate", "total_vol", "max_retro", "cvd",
        "vigentes_count", "min4_height_ticks", "hist4_count", "p10_threshold_ticks",
        "max_span_allowed_ticks", "triggered_cluster", "in_cluster", "first_in_cluster_ns",
        "away_res_code", "away_dir", "away_bar_50t", "t_away_ns",
    ]
    if len(z_int) == 0:
        empty_z = pd.DataFrame(columns=cols_z)
        empty_c = pd.DataFrame(columns=[
            "event_seq", "cluster_id", "event_type", "trigger_zone_idx", "confirmed_bar",
            "t_ns", "market_clock_sec", "lo", "hi", "lo_tk", "hi_tk", "height_ticks",
            "p10_ticks", "zone_count", "total_vol", "poc", "absorb_ultra_frac",
            "away_res_code", "away_dir", "t_away_ns",
        ])
        return {"HFTGCP10": empty_z, "HFTGCP10_CLUST": empty_c}

    z_sb = tk_bidx[z_int[:, 2]]
    z_eb = np.maximum(z_sb, tk_bidx[z_int[:, 3]])
    z_drawn_b = np.maximum(z_eb, tk_bidx[z_int[:, 12]])
    t_avail_ns = z_int[:, 11]
    lo_tk = z_int[:, 4]
    hi_tk = z_int[:, 5]

    cl_cols, clust_df = evaluar_clusters_p10_causal(
        z_sb, z_eb, t_avail_ns, lo_tk, hi_tk, z_int[:, 7], z_flt[:, 4], z_flt[:, 0],
        tick=tick,
        min_zonas_cluster=int(p["min_zonas_cluster"]),
        vigencia_zona_min=float(p["vigencia_zona_min"]),
        ventana_grupos=int(p["ventana_grupos"]),
        min_grupos_warmup=int(p["min_grupos_warmup"]),
        percentil_altura=float(p["percentil_altura"]),
        comparacion_estricta=bool(p["comparacion_estricta"]),
        extension_cluster_barras=int(p["extension_cluster_barras"]),
    )

    z_end_px = z_int[:, 10].astype(np.float64) * float(tick)
    lo_px = lo_tk.astype(np.float64) * float(tick)
    hi_px = hi_tk.astype(np.float64) * float(tick)
    b_h_px = b_h.astype(np.float64) * float(tick)
    b_l_px = b_l.astype(np.float64) * float(tick)
    aw_code, aw_dir, aw_bar, aw_ns = resolver_alejamiento_barras_nb(
        z_drawn_b, lo_px, hi_px, z_int[:, 6], z_int[:, 7], z_end_px,
        b_en, b_h_px, b_l_px, float(tick),
        int(p["alejamiento_ticks"]), 1 if p["excluir_vshape"] else 0, float(p["vshape_pct"]), 0, 0
    )

    if len(clust_df):
        c_trig = clust_df["trigger_zone_idx"].to_numpy(np.int64)
        c_eb = np.maximum(clust_df["confirmed_bar"].to_numpy(np.int64), z_drawn_b[c_trig])
        c_lo_px = clust_df["lo"].to_numpy(np.float64)
        c_hi_px = clust_df["hi"].to_numpy(np.float64)
        c_dummy_dir = np.ones(len(clust_df), np.int64)
        c_dummy_bkt = np.full(len(clust_df), 3, np.int64)
        c_aw_code, c_aw_dir, _, c_aw_ns = resolver_alejamiento_barras_nb(
            c_eb, c_lo_px, c_hi_px, c_dummy_dir, c_dummy_bkt, c_lo_px,
            b_en, b_h_px, b_l_px, float(tick),
            int(p["alejamiento_ticks"]), 0, 50.0, 0, 0
        )
        clust_df["away_res_code"] = c_aw_code
        clust_df["away_dir"] = c_aw_dir
        clust_df["t_away_ns"] = c_aw_ns
    else:
        clust_df["away_res_code"] = np.zeros(0, np.int64)
        clust_df["away_dir"] = np.zeros(0, np.int64)
        clust_df["t_away_ns"] = np.zeros(0, np.int64)

    zones_df = pd.DataFrame(dict(
        zone_id=np.arange(1, len(z_int) + 1, dtype=np.int64),
        t_start_ns=z_int[:, 0],
        t_last_ns=z_int[:, 1],
        t_ns=t_avail_ns,
        start_bar_50t=z_sb,
        end_bar_50t=z_eb,
        drawn_bar_50t=z_drawn_b,
        lo=lo_tk.astype(np.float64) * tick,
        hi=hi_tk.astype(np.float64) * tick,
        lo_tk=lo_tk,
        hi_tk=hi_tk,
        height_ticks=hi_tk - lo_tk,
        dir=z_int[:, 6],
        bucket=z_int[:, 7],
        pasos=z_int[:, 8],
        valid_steps=z_int[:, 9],
        end_pt=z_int[:, 10],
        market_clock_sec=z_flt[:, 0],
        avg_ms=z_flt[:, 1],
        total_ms=z_flt[:, 2],
        vol_rate=z_flt[:, 3],
        total_vol=z_flt[:, 4],
        max_retro=z_flt[:, 5],
        cvd=z_flt[:, 6],
        vigentes_count=cl_cols["vigentes_count"],
        min4_height_ticks=cl_cols["min4_height_ticks"],
        hist4_count=cl_cols["hist4_count"],
        p10_threshold_ticks=cl_cols["p10_threshold_ticks"],
        max_span_allowed_ticks=cl_cols["max_span_allowed_ticks"],
        triggered_cluster=cl_cols["triggered_cluster"],
        in_cluster=cl_cols["in_cluster"],
        first_in_cluster_ns=cl_cols["first_in_cluster_ns"],
        away_res_code=aw_code,
        away_dir=aw_dir,
        away_bar_50t=aw_bar,
        t_away_ns=aw_ns,
    ))
    return {"HFTGCP10": zones_df, "HFTGCP10_CLUST": clust_df}


def almacen_gc(bloques, tick: float = 0.10, spec: int = 50) -> Dict[str, pd.DataFrame]:
    """Punto de entrada para `tools/kaggle_grilla/almacen_zonas_main.py` (`INDICADOR=HFTGCP10`)."""
    bl = list(bloques)
    if not bl:
        return ejecutar_detector_completo(
            np.zeros(0, np.int64), np.zeros(0, np.int64), np.zeros(0, np.float64), np.zeros(0, np.int64), tick, spec
        )
    ts = np.concatenate([b.ts_ns.to_numpy(np.int64) for b in bl])
    px = np.concatenate([b.px.to_numpy(np.float64) for b in bl])
    vol = np.concatenate([b.vol.to_numpy(np.float64) for b in bl])
    ses = np.concatenate([b.sesion.to_numpy(np.int64) for b in bl])
    del bl
    pt = np.round(px / tick).astype(np.int64)
    return ejecutar_detector_completo(ts, pt, vol, ses, tick=float(tick), spec_barras_ticks=int(spec))


@njit(cache=False)
def _mitigacion_m1_nb(zi_m1, zlo, zhi, h_m1, l_m1):
    """Calcula para cada zona la primera vela M1 posterior a `zi_m1` en que ya se tocaron ambos bordes (mitigada entera)
    y la primera vela M1 en que fue tocado al menos un borde."""
    nz = len(zi_m1)
    nm = len(h_m1)
    first_any = np.full(nz, -1, np.int64)
    first_full = np.full(nz, -1, np.int64)
    for i in range(nz):
        b0 = zi_m1[i]
        if b0 < 0 or b0 + 1 >= nm:
            continue
        lo = zlo[i]
        hi = zhi[i]
        tup = False
        tlo = False
        for k in range(b0 + 1, nm):
            if h_m1[k] >= hi - 1e-9:
                tup = True
            if l_m1[k] <= lo + 1e-9:
                tlo = True
            if first_any[i] < 0 and (tup or tlo):
                first_any[i] = k
            if tup and tlo:
                first_full[i] = k
                break
    return first_any, first_full


class LibroBarrerasHFT:
    """Inventario causal M1 de zonas HFT y Clusters P10 para filtrar entradas con barreras HFT delante.

    Diseñado para conectarse sobre cualquier lote de operaciones `(k, lado, entrada, stop, objetivo)` sin
    ningún look-ahead: en la vela de decisión `k`, sólo existen zonas con `zi_m1 <= k`, su estado de Borde Gris
    sólo vale si `away_k <= k`, su pertenencia a cluster sólo vale si `clust_k <= k`, y una zona cuenta como
    no mitigada en `k` si `first_full_k < 0 or first_full_k > k`.
    """

    def __init__(self, zones_df: pd.DataFrame, clust_df: pd.DataFrame, t_close_s: np.ndarray,
                 h_m1: np.ndarray, l_m1: np.ndarray, vida_m1: int = 360):
        self.t_close = np.asarray(t_close_s, np.int64)
        self.vida_m1 = int(vida_m1)
        self.zones = zones_df.sort_values("t_ns", kind="stable").reset_index(drop=True)
        self.clusters = clust_df.sort_values("t_ns", kind="stable").reset_index(drop=True)
        if len(self.zones) and len(self.t_close):
            tz_s = np.ceil(self.zones["t_ns"].to_numpy(np.int64) / 1e9).astype(np.int64)
            self.zi_m1 = np.searchsorted(self.t_close, tz_s, side="left").astype(np.int64)
            taw_ns = self.zones["t_away_ns"].to_numpy(np.int64) if "t_away_ns" in self.zones else np.full(len(self.zones), -1, np.int64)
            self.away_k = np.where(
                (taw_ns > 0) & (self.zones.get("away_res_code", 0) == 1),
                np.searchsorted(self.t_close, np.ceil(taw_ns / 1e9).astype(np.int64), side="left"),
                -1,
            ).astype(np.int64)
            tcl_ns = self.zones["first_in_cluster_ns"].to_numpy(np.int64) if "first_in_cluster_ns" in self.zones else np.full(len(self.zones), -1, np.int64)
            self.clust_k = np.where(
                tcl_ns > 0,
                np.searchsorted(self.t_close, np.ceil(tcl_ns / 1e9).astype(np.int64), side="left"),
                -1,
            ).astype(np.int64)
            self.zlo = self.zones["lo"].to_numpy(np.float64)
            self.zhi = self.zones["hi"].to_numpy(np.float64)
            self.first_any_k, self.first_full_k = _mitigacion_m1_nb(
                self.zi_m1, self.zlo, self.zhi, np.asarray(h_m1, np.float64), np.asarray(l_m1, np.float64)
            )
        else:
            z0 = np.zeros(0, np.int64)
            f0 = np.zeros(0, np.float64)
            self.zi_m1 = self.away_k = self.clust_k = self.first_any_k = self.first_full_k = z0
            self.zlo = self.zhi = f0

    def zonas_en_recorrido(
        self,
        k: int,
        precio_origen: float,
        precio_destino: float,
        solo_no_mitigadas: bool = True,
        solo_borde_gris: bool = False,
        solo_en_cluster: bool = False,
    ) -> pd.DataFrame:
        """Devuelve las zonas HFT causales conocidas en `<= k` que se interponen entre `precio_origen` y `precio_destino`."""
        if not len(self.zones):
            return self.zones.iloc[0:0]
        p_min = min(precio_origen, precio_destino)
        p_max = max(precio_origen, precio_destino)
        m = (self.zi_m1 <= k) & ((k - self.zi_m1) <= self.vida_m1)
        m &= (self.zhi >= p_min) & (self.zlo <= p_max)
        if solo_no_mitigadas:
            m &= (self.first_full_k < 0) | (self.first_full_k > k)
        if solo_borde_gris:
            m &= (self.away_k >= 0) & (self.away_k <= k)
        if solo_en_cluster:
            m &= (self.clust_k >= 0) & (self.clust_k <= k)
        return self.zones.loc[m]
