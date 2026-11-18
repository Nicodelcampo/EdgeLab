"""EXTERNAS-ESTRUCTURALES (2026-11-18): Traducción estructural H1 / D1 / Sesión
de las 8 familias con mayor respaldo económico del Catálogo de Lógicas de Bots
de Trading Externos (2026-11-18) para el protocolo A5.

Diseño: docs/research/externas_estructurales_a5_20261118/DISENO.md
Pre-registro: docs/research/externas_estructurales_a5_20261118/PREREGISTRO.md

Motivación económica y estructural (`F-VIDA-VENTAJA-INTRADIA-FRICCION` y
`F-SALIDA-TECNICA-REGALA-LA-GANANCIA`):
En `EXTERNAS-28` (`edgelab/research/externas_a5.py`), las 28 estrategias se
evaluaron en M1 crudo donde 110 de 114 variantes usan stops de 1.0–1.5 × ATR(14)
de 1 minuto (~2–4 pts de NQ), provocando una fricción mediana >= 1.17 R que las
elimina inmediatamente en Fase 0 (requisito <= 0.08 R). Sólo Dual Thrust
(`X036`–`X039`), cuyo rango se ancla a sesiones diarias, pasó <= 0.08 R.

Este módulo adapta las 8 familias principales a su escala natural (`D1` / `H1` /
`Sesión RTH`), garantizando:
1. Causalidad estricta (K48): todas las variables diarias (`ATR20_D1`, `RSI2_D1`,
   `RSI10_D1`, `SMA100_D1`, `rng4`, `L_t` adaptativo de Pruitt) se calculan
   exclusivamente con sesiones RTH previas cerradas (`d - 1`). Los disparos
   intradía y H1 ocurren únicamente al cierre de barras completadas (`k`), con
   fin determinístico por minuto NY (`hasta_cierre(k)` sin mirar el índice futuro
   de la sesión).
2. Fricción mediana <= 0.08 R (Fase 0): todo stop inicial se ancla a estructura
   diaria (`rg >= 0.40 * ATR20_D1`), reduciendo la fricción a ~0.015–0.045 R.
3. Controles directos pareados (`ES1N`–`ES8N`): cada hipótesis (`ES1`–`ES8`)
   tiene un control en la misma ventana horaria y con el mismo stop estructural
   pero sin la condición económica/estructural que define la tesis.

Definiciones:
  ES1 / ES1N — Gao, Han, Li & Zhou (2017, JFE) Intraday First-30m -> Last-Hour
               Momentum (`intraday_first_last_momentum.py`): a las 15:00 NY
               (`mo == 899`), si los primeros 30m RTH (`09:30–10:00 NY`) movieron
               `|ret_30m| >= 0.25 * ATR20_D1`, entra en la dirección de `ret_30m`
               con stop `0.40 * ATR20_D1` y salida al cierre RTH (`15:59 NY`).
               ES1 exige doble confirmación (`ret_1500` mantiene el signo de
               `ret_30m`); ES1N = el signo a las 15:00 NY divergió de `ret_30m`.
  ES2 / ES2N — Michael Chalek Dual Thrust 4-Session Range Breakout
               (`dual_thrust_chalek.py`): `rng4 = max(HH4 - LC4, HC4 - LL4)` de
               las 4 sesiones RTH previas cerradas. Primer cierre M1 (`09:35–14:30 NY`)
               que rompe `Open_0930 ± 0.45 * rng4`, stop `0.45 * rng4`, salida
               cierre RTH. ES2 = régimen comprimido (`rng4 <= mediana_60d(rng4)`);
               ES2N = régimen expandido (`rng4 > mediana_60d(rng4)`).
  ES3 / ES3N — George Pruitt Dynamic Breakout II Adaptive Lookback
               (`dynamic_breakout_ii.py`): lookback adaptativo `L_t in [15, 50]`
               sesiones actualizado al cierre previo vía `deltavol`. Primer cierre
               M1 (`09:35–14:30 NY`) que rompe el canal Donchian de `L_t` sesiones
               previas, stop `0.50 * ATR20_D1`, salida cierre RTH. ES3 = cierre
               previo fuera de `BB(L_t, 0.75 SD)` (filtro de Pruitt); ES3N = dentro.
  ES4 / ES4N — Larry Connors RSI(2) + Zen ATR Daily Pullback (`F-CONNORS-INDICES-SQX`,
               `connors_rsi2_atr_mr.py`): con `RSI(2)` diario previo extremo
               (`< 25` largo, `> 75` corto), primer cierre M1 (`09:35–14:30 NY`)
               con pullback adicional de `0.35 * ATR20_D1` contra el cierre previo,
               stop `0.50 * ATR20_D1`, TP `1.0 * R` o cierre RTH. ES4 = a favor
               de `SMA100_D1`; ES4N = en contra de `SMA100_D1`.
  ES5 / ES5N — Composer Symphony FTLT / Deez RSI(10) Regime Switcher
               (`composer_ftlt_rsi_regime.py`): a las 10:00 NY (`mo == 599`),
               con movimiento inicial `|ret_30m| >= 0.12 * ATR20_D1`, stop
               `0.45 * ATR20_D1` y salida al cierre RTH. ES5 opera en régimen
               `RSI(10)` diario extremo (`>= 65` fade bajista si `ret_30m < 0`, o
               `<= 38` rebote alcista si `ret_30m > 0`); ES5N = régimen `RSI(10)`
               neutro (`40 <= RSI10 <= 60`) con el mismo impulso de apertura.
  ES6 / ES6N — QFL (Quickfingers Luc) / Altrady Base Scanner H1
               (`qfl_base_scanner.py`): al cierre de barras H1 RTH (`mo % 60 == 29`),
               detecta ruptura ("crack") de `>= 0.20 * ATR20_D1` bajo la última
               base de soporte/resistencia H1 confirmada (extremo H1 seguido de
               rebote `>= 0.35 * ATR20_D1`), stop `0.50 * ATR20_D1`, objetivo de
               retorno a la base. ES6 = barra H1 de ruptura con mecha de rechazo
               `>= 25%` del rango H1; ES6N = sin mecha de rechazo (`< 25%`).
  ES7 / ES7N — LuxAlgo Smart Money Concepts (SMC) H1 Fair Value Gap Retest
               (`smc_fvg_ob_retest.py`): al cierre de barras H1 RTH, retesteo de
               una zona impulsiva H1 (vela central H1 con cuerpo `>= 0.25 * ATR20_D1`)
               dentro de las 12 barras H1 siguientes con cierre H1 a favor del
               impulso, stop `0.50 * ATR20_D1`, TP `1.5 * R` o cierre RTH. ES7 =
               dejó FVG de 3 barras H1 abierto (`Low_H1[t] > High_H1[t-2]` o
               `High_H1[t] < Low_H1[t-2]`); ES7N = impulso H1 equivalente que NO
               dejó gap de 3 barras.
  ES8 / ES8N — Kivanc PMax / Supertrend H1 + LazyBear Squeeze Release
               (`pmax_profit_maximizer.py`, `supertrend_atr.py`,
               `squeeze_momentum_lazybear.py`): al cierre de barras H1 RTH
               (`10:00–14:30 NY`), inversión de tendencia de `PMax(EMA8_H1, 1.8*ATR10_H1)`,
               stop `0.50 * ATR20_D1`, salida cierre RTH. ES8 = precedido por
               compresión H1 (`BB_width_H1 <= mediana_20_H1`); ES8N = sin compresión.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny
from edgelab.research.option_alpha_a5 import FILTROS, _macro_sesion


NOMBRE = "EXTERNAS-ESTRUCTURALES"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["ES1", "ES2", "ES3", "ES4", "ES5", "ES6", "ES7", "ES8"]
CONTROL = {
    "ES1": "ES1N",
    "ES2": "ES2N",
    "ES3": "ES3N",
    "ES4": "ES4N",
    "ES5": "ES5N",
    "ES6": "ES6N",
    "ES7": "ES7N",
    "ES8": "ES8N",
}

RTH0, RTH1 = 570, 960
LEJOS = 1000.0


def _rsi_wilder_step(
    prev_c: float | None,
    cur_c: float,
    avg_g: float | None,
    avg_l: float | None,
    period: int,
) -> tuple[float | None, float | None, float]:
    if prev_c is None:
        return avg_g, avg_l, 50.0
    d = float(cur_c - prev_c)
    g = d if d > 0.0 else 0.0
    l_val = -d if d < 0.0 else 0.0
    if avg_g is None or avg_l is None:
        avg_g, avg_l = g, l_val
    else:
        alpha = 1.0 / float(period)
        avg_g = (1.0 - alpha) * avg_g + alpha * g
        avg_l = (1.0 - alpha) * avg_l + alpha * l_val
    tot = avg_g + avg_l
    rsi = 100.0 * avg_g / tot if tot > 1e-12 else 50.0
    return avg_g, avg_l, rsi


def eventos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    t_arr = np.asarray(ctx["t"], np.int64)
    mo = minuto_ny(t_arr)
    ext_defs = DEFINICIONES + sorted(set(CONTROL.values()))

    # Estado diario estrictamente causal (actualizado únicamente al final de cada sesión RTH)
    atr20 = deque(maxlen=20)
    closes100 = deque(maxlen=100)
    highs60 = deque(maxlen=60)
    lows60 = deque(maxlen=60)
    rng4_hist = deque(maxlen=60)
    prev_rth_close: float | None = None
    rsi2_g: float | None = None
    rsi2_l: float | None = None
    rsi2_val: float = 50.0
    rsi10_g: float | None = None
    rsi10_l: float | None = None
    rsi10_val: float = 50.0
    pruitt_lb: int = 20

    # Estado continuo causal de barras H1 RTH (actualizado sólo al cierre de cada barra H1: mo % 60 == 29)
    h1_h_hist = deque(maxlen=30)
    h1_l_hist = deque(maxlen=30)
    h1_c_hist = deque(maxlen=30)
    h1_o_hist = deque(maxlen=30)
    h1_bb_w_hist = deque(maxlen=20)
    h1_ema8: float | None = None
    h1_atr10: float | None = None
    h1_long_stop: float = -np.inf
    h1_short_stop: float = np.inf
    h1_pmax_dir: int = 1
    h1_count: int = 0
    last_sup_base: float = np.nan
    last_res_base: float = np.nan
    # Zonas H1 abiertas para ES7/ES7N: (lado, z_lo, z_hi, h1_idx_created, is_fvg)
    open_zones: list[tuple[int, float, float, int, bool]] = []

    filas: list[dict] = []

    def hasta_cierre(k: int) -> int:
        return int(k) + int(RTH1 - 1 - mo[k])

    def emit(
        defn: str,
        k: int,
        lado: int,
        stop: float,
        obj: float,
        macro: tuple[float, float, float, float, float],
    ) -> None:
        rg = abs(float(c[k]) - float(stop))
        if not (rg > 0.0 and np.isfinite(stop) and np.isfinite(obj)):
            return
        filas.append(
            {
                "k": int(k),
                "lado": int(lado),
                "ref": float(obj),
                "ext": float(stop),
                "rg": float(rg),
                "obj": float(obj),
                "stop": float(stop),
                "fin": hasta_cierre(k),
                "vix_open": macro[0],
                "vix_prev": macro[1],
                "vix_ivr": macro[2],
                "is_early_close": macro[3],
                "is_fomc": macro[4],
                defn: True,
            }
        )

    for s in np.unique(ses):
        m = np.flatnonzero((ses == s) & (mo >= RTH0) & (mo < RTH1))
        if not len(m):
            continue
        mm = mo[m]
        macro = _macro_sesion(int(s))
        ab = float(o[m[0]])
        cl_rth = float(c[m[-1]])
        hi_rth = float(h[m].max())
        lo_rth = float(l[m].min())

        ATR = float(np.mean(atr20)) if len(atr20) >= 4 else np.nan
        has_daily = np.isfinite(ATR) and ATR > 0.0 and prev_rth_close is not None

        # Pre-calcular métricas diarias causales disponibles antes de las 09:30 NY
        if has_daily:
            sma100 = float(np.mean(closes100))
            if len(highs60) >= 4:
                hh4 = float(max(list(highs60)[-4:]))
                ll4 = float(min(list(lows60)[-4:]))
                hc4 = float(max(list(closes100)[-4:]))
                lc4 = float(min(list(closes100)[-4:]))
                rng4 = max(hh4 - lc4, hc4 - ll4)
            else:
                rng4 = ATR
            med_rng4 = float(np.median(rng4_hist)) if len(rng4_hist) >= 4 else rng4

            lb_eff = min(pruitt_lb, len(highs60))
            don_hi = float(max(list(highs60)[-lb_eff:]))
            don_lo = float(min(list(lows60)[-lb_eff:]))
            c_lb = list(closes100)[-lb_eff:]
            bb_m = float(np.mean(c_lb))
            bb_sd = float(np.std(c_lb))

            # ---------- ES1 / ES1N: Gao et al. (2017) First-30m -> 15:00 NY ----------
            i1000 = m[mm == 599]
            i1500 = m[mm == 899]
            if len(i1000) and len(i1500):
                k1000 = int(i1000[0])
                k1500 = int(i1500[0])
                ret_30m = float(c[k1000]) - ab
                if abs(ret_30m) >= 0.25 * ATR:
                    lado = 1 if ret_30m > 0.0 else -1
                    ret_1500 = float(c[k1500]) - ab
                    d_sl = 0.40 * ATR
                    stop1 = float(c[k1500]) - lado * d_sl
                    obj1 = float(c[k1500]) + lado * LEJOS * d_sl
                    emit("ES1" if (ret_1500 * lado > 0.0) else "ES1N", k1500, lado, stop1, obj1, macro)

            # ---------- ES5 / ES5N: Composer FTLT / Deez RSI(10) Regime a las 10:00 NY ----------
            if len(i1000):
                k1000 = int(i1000[0])
                ret_30m = float(c[k1000]) - ab
                if abs(ret_30m) >= 0.12 * ATR:
                    d_sl5 = 0.45 * ATR
                    if rsi10_val >= 65.0 and ret_30m < 0.0:
                        emit("ES5", k1000, -1, float(c[k1000]) + d_sl5, float(c[k1000]) - LEJOS * d_sl5, macro)
                    elif rsi10_val <= 38.0 and ret_30m > 0.0:
                        emit("ES5", k1000, 1, float(c[k1000]) - d_sl5, float(c[k1000]) + LEJOS * d_sl5, macro)
                    elif 40.0 <= rsi10_val <= 60.0:
                        lado5 = 1 if ret_30m > 0.0 else -1
                        emit(
                            "ES5N",
                            k1000,
                            lado5,
                            float(c[k1000]) - lado5 * d_sl5,
                            float(c[k1000]) + lado5 * LEJOS * d_sl5,
                            macro,
                        )

            # ---------- Ventana M1 (09:35..14:30 NY) para ES2, ES3 y ES4 ----------
            win_m = m[(mm >= 575) & (mm <= 870)]
            if len(win_m):
                # ES2 / ES2N: Dual Thrust 4-Session Range Breakout
                dt_k = max(0.45 * rng4, 0.40 * ATR)
                up_dt = ab + dt_k
                dn_dt = ab - dt_k
                for q in win_m:
                    if c[q] > up_dt or c[q] < dn_dt:
                        lado2 = 1 if c[q] > up_dt else -1
                        stop2 = float(c[q]) - lado2 * dt_k
                        obj2 = float(c[q]) + lado2 * LEJOS * dt_k
                        emit("ES2" if rng4 <= med_rng4 else "ES2N", int(q), lado2, stop2, obj2, macro)
                        break

                # ES3 / ES3N: Pruitt Dynamic Breakout II Adaptive Lookback
                if lb_eff >= 5:
                    for q in win_m:
                        if c[q] > don_hi or c[q] < don_lo:
                            lado3 = 1 if c[q] > don_hi else -1
                            d_sl3 = 0.50 * ATR
                            stop3 = float(c[q]) - lado3 * d_sl3
                            obj3 = float(c[q]) + lado3 * LEJOS * d_sl3
                            outside_bb = abs(prev_rth_close - bb_m) > 0.75 * bb_sd
                            emit("ES3" if outside_bb else "ES3N", int(q), lado3, stop3, obj3, macro)
                            break

                # ES4 / ES4N: Connors RSI(2) + Zen ATR Daily Pullback
                if rsi2_val < 25.0:
                    trig_l = prev_rth_close - 0.35 * ATR
                    for q in win_m:
                        if c[q] <= trig_l:
                            d_sl4 = 0.50 * ATR
                            tag4 = "ES4" if prev_rth_close > sma100 else "ES4N"
                            emit(tag4, int(q), 1, float(c[q]) - d_sl4, float(c[q]) + 1.0 * d_sl4, macro)
                            break
                elif rsi2_val > 75.0:
                    trig_s = prev_rth_close + 0.35 * ATR
                    for q in win_m:
                        if c[q] >= trig_s:
                            d_sl4 = 0.50 * ATR
                            tag4 = "ES4" if prev_rth_close < sma100 else "ES4N"
                            emit(tag4, int(q), -1, float(c[q]) + d_sl4, float(c[q]) - 1.0 * d_sl4, macro)
                            break

        # ---------- Bloques H1 RTH (ES6 QFL, ES7 SMC FVG, ES8 PMax + Squeeze) ----------
        cur_b = -1
        bo = bh = bl = bc = np.nan
        bcnt = 0
        es6_done = es7_done = es8_done = False

        for q in m:
            if mo[q] >= 900:
                break
            bq = int((mo[q] - RTH0) // 60)
            if bq != cur_b:
                cur_b, bo, bh, bl, bc, bcnt = bq, float(o[q]), float(h[q]), float(l[q]), float(c[q]), 1
            else:
                if h[q] > bh:
                    bh = float(h[q])
                if l[q] < bl:
                    bl = float(l[q])
                bc = float(c[q])
                bcnt += 1

            # Cierre completo de la barra H1 RTH (ej. 10:29, 11:29, 12:29, 13:29, 14:29 NY)
            if (mo[q] - RTH0) % 60 == 59 and bcnt >= 30:
                rng_h1 = max(bh - bl, 1e-9)
                atr_ref = ATR if (np.isfinite(ATR) and ATR > 0.0) else rng_h1

                # 1) ES6 / ES6N: QFL H1 Base Crack
                if has_daily and not es6_done:
                    if np.isfinite(last_sup_base) and bc <= last_sup_base - 0.20 * ATR:
                        d_sl6 = 0.50 * ATR
                        l_wick = (min(bo, bc) - bl) / rng_h1
                        obj6 = max(last_sup_base, bc + 0.50 * d_sl6)
                        emit("ES6" if l_wick >= 0.25 else "ES6N", int(q), 1, bc - d_sl6, obj6, macro)
                        es6_done = True
                        last_sup_base = np.nan
                    elif np.isfinite(last_res_base) and bc >= last_res_base + 0.20 * ATR:
                        d_sl6 = 0.50 * ATR
                        u_wick = (bh - max(bo, bc)) / rng_h1
                        obj6 = min(last_res_base, bc - 0.50 * d_sl6)
                        emit("ES6" if u_wick >= 0.25 else "ES6N", int(q), -1, bc + d_sl6, obj6, macro)
                        es6_done = True
                        last_res_base = np.nan

                # 2) ES7 / ES7N: LuxAlgo SMC H1 FVG Retest vs Pullback sin FVG
                if has_daily and open_zones and not es7_done:
                    rem_zones: list[tuple[int, float, float, int, bool]] = []
                    for z_dir, z_lo, z_hi, z_idx, is_fvg in open_zones:
                        if h1_count - z_idx > 12:
                            continue
                        if z_dir == 1:
                            if bc < z_lo:
                                continue
                            if not es7_done and bl <= z_hi and bc > bo:
                                d_sl7 = 0.50 * ATR
                                emit("ES7" if is_fvg else "ES7N", int(q), 1, bc - d_sl7, bc + 1.5 * d_sl7, macro)
                                es7_done = True
                                continue
                        else:
                            if bc > z_hi:
                                continue
                            if not es7_done and bh >= z_lo and bc < bo:
                                d_sl7 = 0.50 * ATR
                                emit("ES7" if is_fvg else "ES7N", int(q), -1, bc + d_sl7, bc - 1.5 * d_sl7, macro)
                                es7_done = True
                                continue
                        rem_zones.append((z_dir, z_lo, z_hi, z_idx, is_fvg))
                    open_zones = rem_zones

                # Actualizar PMax H1 y BB_width H1 y evaluar ES8 / ES8N
                prev_c_h1 = float(h1_c_hist[-1]) if len(h1_c_hist) else bc
                tr_h1 = max(bh - bl, abs(bh - prev_c_h1), abs(bl - prev_c_h1))
                h1_atr10 = tr_h1 if h1_atr10 is None else (0.9 * h1_atr10 + 0.1 * tr_h1)
                h1_ema8 = bc if h1_ema8 is None else ((2.0 / 9.0) * bc + (7.0 / 9.0) * h1_ema8)
                n_ls = h1_ema8 - 1.8 * h1_atr10
                n_ss = h1_ema8 + 1.8 * h1_atr10
                old_pdir = h1_pmax_dir
                if h1_count == 0:
                    h1_long_stop = n_ls
                    h1_short_stop = n_ss
                else:
                    if old_pdir == 1:
                        h1_long_stop = max(n_ls, h1_long_stop)
                        h1_short_stop = n_ss
                        if h1_ema8 < h1_long_stop:
                            h1_pmax_dir = -1
                    else:
                        h1_short_stop = min(n_ss, h1_short_stop)
                        h1_long_stop = n_ls
                        if h1_ema8 > h1_short_stop:
                            h1_pmax_dir = 1

                if has_daily and not es8_done and h1_count >= 10 and h1_pmax_dir != old_pdir and len(h1_bb_w_hist) >= 5:
                    d_sl8 = 0.50 * ATR
                    last_bb_w = float(h1_bb_w_hist[-1])
                    med_bb_w = float(np.median(h1_bb_w_hist))
                    lado8 = int(h1_pmax_dir)
                    emit(
                        "ES8" if last_bb_w <= med_bb_w else "ES8N",
                        int(q),
                        lado8,
                        bc - lado8 * d_sl8,
                        bc + lado8 * LEJOS * d_sl8,
                        macro,
                    )
                    es8_done = True

                # Actualizar historiales H1 tras evaluar la barra H1 cerrada
                if len(h1_l_hist) >= 2:
                    l_prev1, l_prev2 = float(h1_l_hist[-1]), float(h1_l_hist[-2])
                    h_prev1, h_prev2 = float(h1_h_hist[-1]), float(h1_h_hist[-2])
                    o_prev1, c_prev1 = float(h1_o_hist[-1]), float(h1_c_hist[-1])
                    if l_prev1 <= l_prev2 and (bh - l_prev1) >= 0.35 * atr_ref:
                        last_sup_base = l_prev1
                    if h_prev1 >= h_prev2 and (h_prev1 - bl) >= 0.35 * atr_ref:
                        last_res_base = h_prev1

                    mid_body = c_prev1 - o_prev1
                    if abs(mid_body) >= 0.25 * atr_ref:
                        if mid_body > 0.0:
                            if bl > h_prev2:
                                open_zones.append((1, h_prev2, bl, h1_count, True))
                            else:
                                open_zones.append((1, o_prev1, 0.5 * (o_prev1 + c_prev1), h1_count, False))
                        else:
                            if bh < l_prev2:
                                open_zones.append((-1, bh, l_prev2, h1_count, True))
                            else:
                                open_zones.append((-1, 0.5 * (o_prev1 + c_prev1), o_prev1, h1_count, False))

                h1_o_hist.append(bo)
                h1_h_hist.append(bh)
                h1_l_hist.append(bl)
                h1_c_hist.append(bc)
                if len(h1_c_hist) >= 5:
                    arr_c = np.asarray(list(h1_c_hist)[-10:], dtype=float)
                    mc = float(np.mean(arr_c))
                    if abs(mc) > 1e-9:
                        h1_bb_w_hist.append(4.0 * float(np.std(arr_c)) / abs(mc))
                h1_count += 1

        # ---------- Actualización diaria estrictamente al cierre de la sesión ----------
        tr = (
            max(hi_rth - lo_rth, abs(hi_rth - prev_rth_close), abs(lo_rth - prev_rth_close))
            if prev_rth_close is not None
            else (hi_rth - lo_rth)
        )
        if np.isfinite(tr) and tr > 0.0:
            atr20.append(tr)
        rsi2_g, rsi2_l, rsi2_val = _rsi_wilder_step(prev_rth_close, cl_rth, rsi2_g, rsi2_l, 2)
        rsi10_g, rsi10_l, rsi10_val = _rsi_wilder_step(prev_rth_close, cl_rth, rsi10_g, rsi10_l, 10)
        prev_rth_close = cl_rth
        closes100.append(cl_rth)
        highs60.append(hi_rth)
        lows60.append(lo_rth)
        if len(highs60) >= 4:
            hh4 = float(max(list(highs60)[-4:]))
            ll4 = float(min(list(lows60)[-4:]))
            hc4 = float(max(list(closes100)[-4:]))
            lc4 = float(min(list(closes100)[-4:]))
            rng4_hist.append(max(hh4 - lc4, hc4 - ll4))
        if len(closes100) >= 6:
            c_arr = np.asarray(list(closes100)[-6:], dtype=float)
            sd_cur = float(np.std(c_arr[1:]))
            sd_prv = float(np.std(c_arr[:-1]))
            if sd_cur > 1e-12:
                dvol = (sd_cur - sd_prv) / sd_cur
                pruitt_lb = int(np.clip(round(pruitt_lb * (1.0 + dvol)), 15, 50))

    cols = [
        "k", "lado", "ref", "ext", "rg", "obj", "stop", "fin",
        "vix_open", "vix_prev", "vix_ivr", "is_early_close", "is_fomc",
    ] + ext_defs
    E = pd.DataFrame(filas)
    for col in cols:
        if col not in E:
            E[col] = False if col in ext_defs else np.nan
    for col in ext_defs:
        E[col] = E[col].fillna(False).astype(bool)
    if not len(E):
        return pd.DataFrame(columns=cols)
    return (
        E[cols]
        .astype({"k": np.int64, "lado": np.int64, "fin": np.int64})
        .sort_values(["k", "lado"] + ext_defs, kind="mergesort")
        .reset_index(drop=True)
    )
