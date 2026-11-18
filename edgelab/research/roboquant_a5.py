"""ROBOQUANT (2026-11-18): 8 familias de reglas extraídas del Marketplace de Roboquant (futuros CME), adaptadas a M1 (A5).

Diseño: docs/research/roboquant_20261118/DISENO.md; pre-registro: docs/research/roboquant_20261118/PREREGISTRO.md;
catálogo: docs/research/option_alpha_20261118/CATALOGO_EXTENDIDO_OA_Y_ROBOQUANT.md.
Contrato de `edgelab/research/tablas.py`: hora de Nueva York sobre la sesión RTH (9:30–16:00). Decisión al cierre de la vela M1 `k`,
entrada en el primer tick de la vela siguiente (motor único `ejecucion.py`), salida forzada por tiempo o cierre RTH (`fin`).
Todas las distancias están normalizadas a rangos o ATR20 causales (K36); sin look-ahead (K48).

Definiciones (derivadas de las estrategias gratuitas de mayor Profit Factor en Roboquant Marketplace):
  RQ1  NQ Precision Bot (PF 2.48): ORB 15m (9:30–9:45), snapshot único a las 10:00 NY, SL 2,2·ATR14_1m (piso 0,35·R15),
       TP 0,30·SL, cierre por tiempo a los 8m (fin = k + 8); RQ1 = régimen ATR14/ATR50 ∈ [1,0; 2,5], RQ1N = fuera de banda.
  RQ2  Friday Range Revisit / Monday Short (PF 2.96): apertura 9:35 NY dentro del rango RTH previo (mitad superior) → corto hacia
       mínimo previo con SL sobre máximo previo; RQ2 = máximo previo no superó el de hace 2 sesiones, RQ2N = sí lo superó.
  RQ3  T-Mean Reversion / Red Session Bounce (PF 2.58): compra a las 9:35 NY hasta cierre RTH con SL 1·ATR20 tras sesión previa
       roja (Prev_Close < Prev_Open - 0,10·ATR20); RQ3N = tras sesión previa verde.
  RQ4  Daily Anchored Typical-Price VWAP + EMA11 3m (PF 1.84): en velas 3m (10:00–14:00), EMA11 del lado de TP_VWAP y cierre 3m
       confirmando, SL 1·ATR14_3m (piso 0,25·ATR20), TP 1,5·SL; RQ4 = ATR14_3m ≤ 1,15·ATR50_3m, RQ4N = alta vol 3m.
  RQ5  Noise-Band Intraday Momentum (Zarattini/Chuk, PF 1.78): en slots de 30m (10:00–14:30), cierre fuera de Open_930 ± σ_slot(60d)
       y del lado de TP_VWAP, SL 0,5·ATR20, TP 1,0·ATR20; RQ5 = ruptura temprana (10:00–11:30 NY), RQ5N = ruptura tardía (12:00–14:30 NY).
  RQ6  Trend Day Pullback to Session VWAP (PF 1.67, DD 3.7%): entre 10:30 y 12:30 NY, con impulso matutino ≥ 0,25·ATR20, primer
       retroceso de vela 5m hacia TP_VWAP que cierra a favor de la tendencia; SL 0,40·ATR20, TP 0,80·ATR20 (2R).
  RQ7  NY ORB 15m Retest with Inside-PDH/PDL Filter (PF 1.43): ruptura ORB 15m seguida de retesteo del borde roto dentro de 80m,
       SL 0,60·ATR20, TP 0,50·ATR20; RQ7 = ORB 15m dentro del High/Low de la sesión previa, RQ7N = fuera del rango previo.
  RQ8  IVB Initial Balance 30m Contraction Breakout (PF 1.37): ruptura de IB 30m (9:30–10:00) en vela 5m con expansión ≥ 1,1x,
       SL 0,60·ATR20, TP 0,80·ATR20; RQ8 = IB contraído (< 0,95·Media_10d), RQ8N = IB expandido.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny
from edgelab.research.option_alpha_a5 import FILTROS, RTH0, RTH1, _ema_step, _macro_sesion

NOMBRE = "ROBOQUANT"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["RQ1", "RQ2", "RQ3", "RQ4", "RQ5", "RQ6", "RQ7", "RQ8"]
CONTROL = {"RQ1": "RQ1N", "RQ2": "RQ2N", "RQ3": "RQ3N", "RQ4": "RQ4N", "RQ5": "RQ5N", "RQ7": "RQ7N", "RQ8": "RQ8N"}

SLOTS_30M = (599, 629, 659, 689, 719, 749, 779, 809, 839, 869)


def eventos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    t_arr = np.asarray(ctx["t"], np.int64)
    mo = minuto_ny(t_arr)
    ext_defs = DEFINICIONES + sorted(set(CONTROL.values()))

    atr20 = deque(maxlen=20)
    ib30_hist = deque(maxlen=10)
    slot_moves = {sm: deque(maxlen=60) for sm in SLOTS_30M}

    prev_hi = prev_lo = prev_open = prev_close = None
    prev2_hi = None

    tr1m_50 = deque(maxlen=50)
    tr3m_50 = deque(maxlen=50)
    filas = []

    def emit(defn: str, k: int, lado: int, stop: float, obj: float, fin_k: int, macro: tuple[float, float, float, float, float]) -> None:
        rg = abs(float(c[k]) - float(stop))
        if not (rg > 0.0 and np.isfinite(stop) and np.isfinite(obj)):
            return
        filas.append({
            "k": int(k), "lado": int(lado), "ref": float(obj), "ext": float(stop), "rg": float(rg),
            "obj": float(obj), "stop": float(stop), "fin": int(fin_k),
            "vix_open": macro[0], "vix_prev": macro[1], "vix_ivr": macro[2],
            "is_early_close": macro[3], "is_fomc": macro[4],
            defn: True,
        })

    for s in np.unique(ses):
        m = np.flatnonzero((ses == s) & (mo >= RTH0) & (mo < RTH1))
        if not len(m):
            continue
        mm = mo[m]
        macro = _macro_sesion(int(s))
        ab, cl_rth = float(o[m[0]]), float(c[m[-1]])
        hi_rth, lo_rth = float(h[m].max()), float(l[m].min())
        ATR = float(np.mean(atr20)) if len(atr20) >= 3 else (float(prev_hi - prev_lo) if (prev_hi is not None and prev_lo is not None) else np.nan)

        def hasta_cierre(k_idx: int) -> int:
            return int(k_idx) + int(RTH1 - 1 - mo[k_idx])

        # Precalcular TR M1 causal dentro de la sesión y TP-VWAP acumulado desde 09:30 NY
        tp_sum = 0.0
        tp_cnt = 0
        vwap_m = np.empty(len(m), dtype=float)
        atr14_1m = np.full(len(m), np.nan)
        atr50_1m = np.full(len(m), np.nan)
        prev_c1 = prev_close
        for idx_local, q in enumerate(m):
            tr1 = max(float(h[q] - l[q]), abs(float(h[q]) - prev_c1), abs(float(l[q]) - prev_c1)) if prev_c1 is not None else float(h[q] - l[q])
            tr1m_50.append(max(tr1, 1e-6))
            prev_c1 = float(c[q])
            arr1 = list(tr1m_50)
            atr14_1m[idx_local] = float(np.mean(arr1[-14:]))
            atr50_1m[idx_local] = float(np.mean(arr1))
            tp_sum += (float(h[q]) + float(l[q]) + float(c[q])) / 3.0
            tp_cnt += 1
            vwap_m[idx_local] = tp_sum / tp_cnt

        # ---------- RQ2 / RQ2N (Friday Range Revisit) & RQ3 / RQ3N (T-Mean Reversion) a las 09:35 NY ----------
        pos_0935 = np.flatnonzero(mm == 574)
        if len(pos_0935) and prev_hi is not None and prev_lo is not None and np.isfinite(ATR) and ATR > 0.0:
            p35 = int(pos_0935[0])
            k35 = int(m[p35])
            c35 = float(c[k35])
            r_prev = prev_hi - prev_lo
            if r_prev > 0.0 and prev2_hi is not None and (prev_lo + 0.35 * r_prev <= c35 <= prev_hi):
                sl2 = max(prev_hi, c35 + 0.40 * r_prev)
                tp2 = min(prev_lo, c35 - 0.50 * r_prev)
                emit("RQ2" if prev_hi <= prev2_hi else "RQ2N", k35, -1, sl2, tp2, hasta_cierre(k35), macro)
            if prev_open is not None and prev_close is not None:
                delta_prev = prev_close - prev_open
                if abs(delta_prev) >= 0.08 * ATR:
                    emit("RQ3" if delta_prev < 0.0 else "RQ3N", k35, 1, c35 - ATR, c35 + 1000.0 * ATR, hasta_cierre(k35), macro)

        # ---------- RQ1 / RQ1N: NQ Precision Bot (9:30–9:45 ORB, 10:00 Snapshot, 8m Time Close) ----------
        i15 = m[mm < RTH0 + 15]
        pos_1000 = np.flatnonzero(mm == 599)
        if len(i15) >= 10 and len(pos_1000) and np.isfinite(ATR) and ATR > 0.0:
            hi15, lo15 = float(h[i15].max()), float(l[i15].min())
            r15 = hi15 - lo15
            p10 = int(pos_1000[0])
            k10 = int(m[p10])
            c10 = float(c[k10])
            if r15 > 0.0 and (c10 > hi15 or c10 < lo15):
                lado1 = 1 if c10 > hi15 else -1
                a14 = float(atr14_1m[p10])
                a50 = float(atr50_1m[p10])
                d_sl1 = max(2.2 * a14 if np.isfinite(a14) else 0.0, 0.35 * r15, 0.20 * ATR)
                sl1 = c10 - lado1 * d_sl1
                tp1 = c10 + lado1 * (0.30 * d_sl1)
                fin1 = min(k10 + 8, hasta_cierre(k10))
                ratio_reg = (a14 / a50) if (np.isfinite(a14) and np.isfinite(a50) and a50 > 0.0) else 1.0
                in_regime = 0.95 <= ratio_reg <= 2.50
                emit("RQ1" if in_regime else "RQ1N", k10, lado1, sl1, tp1, fin1, macro)

        # ---------- RQ7 / RQ7N: NY ORB 15m Retest with Inside-PDH/PDL Filter ----------
        if len(i15) >= 10 and prev_hi is not None and prev_lo is not None and np.isfinite(ATR) and ATR > 0.0:
            hi15, lo15 = float(h[i15].max()), float(l[i15].min())
            inside_pd = (hi15 <= prev_hi) and (lo15 >= prev_lo)
            armed_side = 0
            armed_mm = -1
            for p_idx in range(len(m)):
                mq = int(mm[p_idx])
                if mq < RTH0 + 15 or mq >= 840:
                    continue
                kq = int(m[p_idx])
                if armed_side == 0:
                    if mq % 15 == 14 and mq <= 780:
                        if c[kq] > hi15:
                            armed_side, armed_mm = 1, mq
                        elif c[kq] < lo15:
                            armed_side, armed_mm = -1, mq
                else:
                    if mq - armed_mm > 80:
                        break
                    if armed_side == 1 and float(l[kq]) <= hi15 + 0.05 * ATR and float(c[kq]) >= hi15:
                        d7 = max(0.50 * ATR, hi15 - lo15)
                        emit("RQ7" if inside_pd else "RQ7N", kq, 1, float(c[kq]) - d7, float(c[kq]) + 0.80 * d7, hasta_cierre(kq), macro)
                        break
                    if armed_side == -1 and float(h[kq]) >= lo15 - 0.05 * ATR and float(c[kq]) <= lo15:
                        d7 = max(0.50 * ATR, hi15 - lo15)
                        emit("RQ7" if inside_pd else "RQ7N", kq, -1, float(c[kq]) + d7, float(c[kq]) - 0.80 * d7, hasta_cierre(kq), macro)
                        break

        # ---------- RQ4 / RQ4N: Daily Anchored Typical-Price VWAP + EMA11 (3m bars) ----------
        ema11_3m = None
        rq4_done = False
        b3_cur = -1
        b3_h = b3_l = b3_c = np.nan
        for p_idx, kq in enumerate(m):
            mq = int(mm[p_idx])
            if mq >= 840:
                break
            b3 = (mq - RTH0) // 3
            if b3 != b3_cur:
                b3_cur, b3_h, b3_l, b3_c = b3, float(h[kq]), float(l[kq]), float(c[kq])
            else:
                if h[kq] > b3_h:
                    b3_h = float(h[kq])
                if l[kq] < b3_l:
                    b3_l = float(l[kq])
                b3_c = float(c[kq])
            if (mq - RTH0) % 3 == 2 and np.isfinite(ATR) and ATR > 0.0:
                tr3m_50.append(max(b3_h - b3_l, 1e-6))
                ema11_3m = _ema_step(ema11_3m, b3_c, 11)
                if not rq4_done and mq >= 600 and len(tr3m_50) >= 14:
                    vw = float(vwap_m[p_idx])
                    arr3 = list(tr3m_50)
                    a14_3 = float(np.mean(arr3[-14:]))
                    a50_3 = float(np.mean(arr3))
                    bull4 = ema11_3m > vw and b3_c > ema11_3m + 0.05 * a14_3
                    bear4 = ema11_3m < vw and b3_c < ema11_3m - 0.05 * a14_3
                    if bull4 or bear4:
                        lado4 = 1 if bull4 else -1
                        d4 = max(2.5 * a14_3, 0.30 * ATR)
                        vol_ok = a14_3 <= 1.12 * a50_3
                        emit("RQ4" if vol_ok else "RQ4N", int(kq), lado4, b3_c - lado4 * d4, b3_c + lado4 * 1.5 * d4, hasta_cierre(int(kq)), macro)
                        rq4_done = True

        # ---------- RQ5 / RQ5N: Noise-Band Intraday Momentum (30m slots, 60-session history) ----------
        rq5_done = False
        for sm in SLOTS_30M:
            pos_sm = np.flatnonzero(mm == sm)
            if not len(pos_sm):
                continue
            p_sm = int(pos_sm[0])
            k_sm = int(m[p_sm])
            c_sm = float(c[k_sm])
            move_sm = abs(c_sm - ab)
            hist_sm = slot_moves[sm]
            if not rq5_done and len(hist_sm) >= 10 and np.isfinite(ATR) and ATR > 0.0:
                band = float(np.mean(hist_sm))
                if band > 0.0 and move_sm >= band:
                    lado5 = 1 if c_sm > ab else -1
                    vw_sm = float(vwap_m[p_sm])
                    vw_agree = (lado5 == 1 and c_sm >= vw_sm) or (lado5 == -1 and c_sm <= vw_sm)
                    if vw_agree:
                        d5 = max(0.45 * ATR, 0.50 * band)
                        emit("RQ5" if sm <= 689 else "RQ5N", k_sm, lado5, c_sm - lado5 * d5, c_sm + lado5 * (2.0 * d5), hasta_cierre(k_sm), macro)
                        rq5_done = True
            hist_sm.append(move_sm)

        # ---------- RQ6 (Trend Day Pullback 5m) & RQ8 / RQ8N (IVB 30m Contraction Breakout 5m) ----------
        i30 = m[mm < RTH0 + 30]
        hi30 = float(h[i30].max()) if len(i30) else np.nan
        lo30 = float(l[i30].min()) if len(i30) else np.nan
        r30 = (hi30 - lo30) if len(i30) >= 20 else np.nan
        ib_contracted = (len(ib30_hist) >= 5 and np.isfinite(r30) and r30 < 0.95 * float(np.mean(ib30_hist)))

        rq6_done = False
        rq8_done = False
        pulled_back = False
        rng5_hist = deque(maxlen=12)
        b5_cur = -1
        b5_h = b5_l = b5_c = np.nan

        for p_idx, kq in enumerate(m):
            mq = int(mm[p_idx])
            if mq >= 840:
                break
            b5 = (mq - RTH0) // 5
            if b5 != b5_cur:
                b5_cur, b5_h, b5_l, b5_c = b5, float(h[kq]), float(l[kq]), float(c[kq])
            else:
                if h[kq] > b5_h:
                    b5_h = float(h[kq])
                if l[kq] < b5_l:
                    b5_l = float(l[kq])
                b5_c = float(c[kq])

            if (mq - RTH0) % 5 == 4 and np.isfinite(ATR) and ATR > 0.0:
                r5 = max(b5_h - b5_l, 1e-6)
                avg_r5 = float(np.mean(rng5_hist)) if len(rng5_hist) >= 4 else r5
                rng5_hist.append(r5)
                vw5 = float(vwap_m[p_idx])

                # RQ8 / RQ8N: IVB 30m breakout on 5m bar with range/volume surge >= 1.05x
                if not rq8_done and mq >= 600 and mq <= 810 and np.isfinite(r30) and r30 > 0.0 and len(ib30_hist) >= 5:
                    if (b5_c > hi30 or b5_c < lo30) and r5 >= 1.05 * avg_r5:
                        lado8 = 1 if b5_c > hi30 else -1
                        d8 = max(0.55 * ATR, 0.50 * r30)
                        emit("RQ8" if ib_contracted else "RQ8N", int(kq), lado8, b5_c - lado8 * d8, b5_c + lado8 * (1.33 * d8), hasta_cierre(int(kq)), macro)
                        rq8_done = True

                # RQ6: Trend Day Pullback to Session VWAP between 10:30 and 12:30 NY
                if not rq6_done and 629 <= mq <= 750:
                    trend_dir = 1 if (b5_c > vw5 and ( vw5 - ab ) >= 0.08 * ATR) else (-1 if (b5_c < vw5 and (ab - vw5) >= 0.08 * ATR) else 0)
                    if trend_dir == 1 and b5_l <= vw5 + 0.20 * ATR:
                        pulled_back = True
                    elif trend_dir == -1 and b5_h >= vw5 - 0.20 * ATR:
                        pulled_back = True
                    if pulled_back and trend_dir != 0:
                        cont = (trend_dir == 1 and b5_c > vw5 + 0.05 * ATR) or (trend_dir == -1 and b5_c < vw5 - 0.05 * ATR)
                        if cont:
                            d6 = max(0.40 * ATR, r5)
                            emit("RQ6", int(kq), trend_dir, b5_c - trend_dir * d6, b5_c + trend_dir * (2.0 * d6), hasta_cierre(int(kq)), macro)
                            rq6_done = True

        # Actualización estrictamente al cierre de la sesión RTH (causal)
        tr_day = max(hi_rth - lo_rth, abs(hi_rth - prev_close), abs(lo_rth - prev_close)) if prev_close is not None else (hi_rth - lo_rth)
        if np.isfinite(tr_day) and tr_day > 0.0:
            atr20.append(tr_day)
        if np.isfinite(r30) and r30 > 0.0:
            ib30_hist.append(r30)
        prev2_hi = prev_hi
        prev_hi, prev_lo, prev_open, prev_close = hi_rth, lo_rth, ab, cl_rth

    cols = ["k", "lado", "ref", "ext", "rg", "obj", "stop", "fin", "vix_open", "vix_prev", "vix_ivr", "is_early_close", "is_fomc"] + ext_defs
    E = pd.DataFrame(filas)
    for col in cols:
        if col not in E:
            E[col] = False if col in ext_defs else np.nan
    for col in ext_defs:
        E[col] = E[col].fillna(False).astype(bool)
    if not len(E):
        return pd.DataFrame(columns=cols)
    return E[cols].astype({"k": np.int64, "lado": np.int64, "fin": np.int64}).sort_values(["k", "lado"] + ext_defs, kind="mergesort").reset_index(drop=True)
