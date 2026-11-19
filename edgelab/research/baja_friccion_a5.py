"""BAJA-FRICCION (2026-11-19): 8 familias de reglas intrasesión de baja fricción (Roboquant 32/32 + TradingView OS + Williams/Crabel).

Diseño: docs/research/baja_friccion_20261119/DISENO.md; pre-registro: docs/research/baja_friccion_20261119/PREREGISTRO.md;
catálogo: docs/research/baja_friccion_20261119/CATALOGO_ROBOQUANT_COMPLETO_Y_TRADINGVIEW.md.
Contrato de `edgelab/research/tablas.py`: hora de Nueva York sobre la sesión CME/RTH (9:30–16:00). Decisión al cierre de la vela M1 `k`,
entrada en el primer tick de la vela siguiente (motor único `ejecucion.py`), salida forzada por nivel o cierre RTH (`fin`).
Todos los stops iniciales están anclados a volatilidad diaria (`0,50–1,00 × ATR20/ADR20`) para mantener la fricción <= 0,08 R (K36), sin look-ahead (K48).

Definiciones (Carril 1 intrasesión):
  BF1 / BF1N  MNQ Midday Continuation (Gao 2018 / Baltussen 2021): a las 10:30 ET entra en dirección de (Close_1030 - Open_930)
              con stop 1,0·ADR20 hasta 15:59 ET; BF1 si |mv| >= 0,20·ADR20, BF1N si 0 < |mv| < 0,20·ADR20.
  BF2 / BF2N  Gap-Adjusted Noise-Band Paper Mode (Zarattini et al. 2024): banda porcentual causal de 60 sesiones ajustada al gap
              nocturno + confirmación TP_VWAP en slots de 30m (10:00–14:30), SL 0,75·ATR20; BF2 = con sesión previa, BF2N = en contra.
  BF3 / BF3N  Pre-NY Sweep FU Retest (Roboquant 4H FU Retest): compara 06:00–08:00 vs 08:00–10:00 ET; tras retest 15m (10:00–14:00)
              SL 0,65·ATR20, TP 0,5R; BF3 = sweep con recupero > midA (FU), BF3N = ruptura limpia sin sweep.
  BF4 / BF4N  Previous Day Extreme 25% Reclaim (Roboquant Oficial): cuartiles ±25% del rango RTH previo; BF4 = rechazo y cierre 15m
              saliendo del cuartil extremo; BF4N = ruptura 15m fuera de PDH/PDL; SL 0,60·ATR20, TP 0,65·ATR20.
  BF5 / BF5N  Omega Volume/Range Z-Score Double-Lens (TradingView OmegaTools): cierre 15m (10:00–14:30) con |z / volF| >= 1,40,
              SL 0,60·ATR20, TP 1,20·ATR20 (2R); BF5 = a favor de SMA20 diaria, BF5N = en contra.
  BF6 / BF6N  LUBE Time-at-Price Low-Friction Breakout (TradingView Editors' Pick): fricción recency-weighted sobre 80 velas 30m
              y dirección FIR(4), SL 0,60·ATR20; BF6 = baja resistencia (p25), BF6N = alta congestión (p75).
  BF7 / BF7N  GlowVwap AVWAP Pullback + Anti-Chop (TradingView blitz_algo): 2 cierres 15m fuera de TP_VWAP ± 0,15·s_eff,
              pullback a VWAP + vela a favor, SL max(0,55·ATR20, s_eff), TP 2R; BF7 = anti-chop (rot <= 1), BF7N = rot >= 2.
  BF8 / BF8N  Williams Volatility Expansion + Crabel NR (prima de Dual Thrust): ruptura 5m (09:35–14:30) de Open_930 ± 0,55·Prev_Range,
              SL max(0,55·Prev_Range, 0,50·ATR20); BF8 = rango previo comprimido (< med 10d), BF8N = expandido.
"""
from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny
from edgelab.research.option_alpha_a5 import FILTROS, LEJOS, RTH0, RTH1, _macro_sesion

NOMBRE = "BAJA-FRICCION"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["BF1", "BF2", "BF3", "BF4", "BF5", "BF6", "BF7", "BF8"]
CONTROL = {f"BF{i}": f"BF{i}N" for i in range(1, 9)}
SLOTS_30M = (599, 629, 659, 689, 719, 749, 779, 809, 839, 869)


def eventos(ctx: dict) -> pd.DataFrame:
    """Genera eventos causales A5 para las 8 reglas BF1–BF8 y sus controles BF1N–BF8N."""
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    t_arr = np.asarray(ctx["t"], np.int64)
    mo = minuto_ny(t_arr)
    ext_defs = DEFINICIONES + sorted(set(CONTROL.values()))

    # Estado diario estrictamente causal (actualizado al cierre de la sesión RTH)
    atr20 = deque(maxlen=20)
    adr20 = deque(maxlen=20)
    closes20 = deque(maxlen=20)
    rth_ranges10 = deque(maxlen=10)
    prev_hi = prev_lo = prev_open = prev_close = None

    # Estado multi-sesión causal de barras intradía completadas
    slot_pct_moves = {sm: deque(maxlen=60) for sm in SLOTS_30M}
    closes15 = deque(maxlen=21)
    ranges15 = deque(maxlen=21)
    bars30 = deque(maxlen=80)
    fric_hist = deque(maxlen=40)
    filas = []

    for s in np.unique(ses):
        m_ses = np.flatnonzero(ses == s)
        m = m_ses[(mo[m_ses] >= RTH0) & (mo[m_ses] < RTH1)]
        if not len(m):
            continue
        mm = mo[m]
        macro = _macro_sesion(int(s))
        ab, cl_rth = float(o[m[0]]), float(c[m[-1]])
        hi_rth, lo_rth = float(h[m].max()), float(l[m].min())

        r_prev = (prev_hi - prev_lo) if (prev_hi is not None and prev_lo is not None) else np.nan
        ATR = float(np.mean(atr20)) if len(atr20) >= 3 else (float(r_prev) if np.isfinite(r_prev) and r_prev > 0.0 else np.nan)
        ADR = float(np.mean(adr20)) if len(adr20) >= 3 else ATR
        has_atr = bool(np.isfinite(ATR) and ATR > 0.0)

        def emit(defn: str, k_idx: int, lado: int, stop: float, obj: float) -> None:
            rg = abs(float(c[k_idx]) - float(stop))
            if not (rg > 0.0 and np.isfinite(stop) and np.isfinite(obj)):
                return
            fin_k = int(k_idx) + int(RTH1 - 1 - mo[k_idx])
            filas.append({
                "k": int(k_idx), "lado": int(lado), "ref": float(obj), "ext": float(stop), "rg": float(rg),
                "obj": float(obj), "stop": float(stop), "fin": fin_k,
                "vix_open": macro[0], "vix_prev": macro[1], "vix_ivr": macro[2],
                "is_early_close": macro[3], "is_fomc": macro[4],
                defn: True,
            })

        # TP-VWAP RTH acumulado estrictamente barra a barra
        tp_sum = 0.0
        vwap_m = np.empty(len(m), dtype=float)
        for idx_l, q in enumerate(m):
            tp_sum += (float(h[q]) + float(l[q]) + float(c[q])) / 3.0
            vwap_m[idx_l] = tp_sum / float(idx_l + 1)

        # ---------- BF1 / BF1N: MNQ Midday Continuation (10:30 -> 15:59 ET) ----------
        pos_1030 = np.flatnonzero(mm == 629)
        if has_atr and np.isfinite(ADR) and ADR > 0.0 and len(pos_1030):
            k1 = int(m[int(pos_1030[0])])
            mv = float(c[k1]) - ab
            if mv != 0.0:
                lado1 = 1 if mv > 0.0 else -1
                emit("BF1" if abs(mv) >= 0.20 * ADR else "BF1N", k1, lado1, float(c[k1]) - lado1 * ADR, float(c[k1]) + lado1 * LEJOS * ADR)

        # ---------- BF2 / BF2N: Gap-Adjusted Noise-Band Paper Mode (Zarattini) ----------
        bf2_done = False
        for sm in SLOTS_30M:
            pos_sm = np.flatnonzero(mm == sm)
            if not len(pos_sm):
                continue
            p_sm = int(pos_sm[0])
            k_sm = int(m[p_sm])
            c_sm = float(c[k_sm])
            pct_mv = abs(c_sm - ab) / ab if ab > 0.0 else np.nan
            hist_sm = slot_pct_moves[sm]
            if not bf2_done and has_atr and prev_close is not None and prev_open is not None and len(hist_sm) >= 10:
                sig = float(np.mean(hist_sm))
                up2 = max(ab, prev_close) * (1.0 + sig)
                dn2 = min(ab, prev_close) * (1.0 - sig)
                vw2 = float(vwap_m[p_sm])
                long2 = c_sm > up2 and c_sm >= vw2
                short2 = c_sm < dn2 and c_sm <= vw2
                if long2 or short2:
                    lado2 = 1 if long2 else -1
                    prev_dir = 1 if prev_close >= prev_open else -1
                    d2 = 0.75 * ATR
                    emit("BF2" if lado2 == prev_dir else "BF2N", k_sm, lado2, c_sm - lado2 * d2, c_sm + lado2 * LEJOS * d2)
                    bf2_done = True
            if np.isfinite(pct_mv):
                hist_sm.append(pct_mv)

        # ---------- BF3 / BF3N: Pre-NY (06:00-08:00 vs 08:00-10:00) Sweep FU Retest ----------
        pre_k600 = int(m[np.flatnonzero(mm >= 600)[0]]) if np.any(mm >= 600) else int(m[-1] + 1)
        m_pre = m_ses[m_ses < pre_k600]
        winA = m_pre[(mo[m_pre] >= 360) & (mo[m_pre] < 480)]
        winB = m_pre[(mo[m_pre] >= 480) & (mo[m_pre] < 600)]
        fu_side = 0
        fu_is_sweep = False
        fu_midB = np.nan
        if has_atr and len(winA) >= 20 and len(winB) >= 20:
            hiA, loA = float(h[winA].max()), float(l[winA].min())
            hiB, loB, clB = float(h[winB].max()), float(l[winB].min()), float(c[winB[-1]])
            midA, fu_midB = 0.5 * (hiA + loA), 0.5 * (hiB + loB)
            if hiA > loA and hiB > loB:
                if loB < loA and clB > midA:
                    fu_side, fu_is_sweep = 1, True
                elif hiB > hiA and clB < midA:
                    fu_side, fu_is_sweep = -1, True
                elif clB > hiA and loB >= loA:
                    fu_side, fu_is_sweep = 1, False
                elif clB < loA and hiB <= hiA:
                    fu_side, fu_is_sweep = -1, False

        # ---------- BF8 / BF8N: Williams Volatility Expansion + Crabel NR (5m) ----------
        bf8_done = False
        nr_contraction = bool(np.isfinite(r_prev) and r_prev > 0.0 and len(rth_ranges10) >= 5 and r_prev < float(np.median(rth_ranges10)))
        if has_atr and np.isfinite(r_prev) and r_prev > 0.0 and len(rth_ranges10) >= 5:
            up8, dn8 = ab + 0.55 * r_prev, ab - 0.55 * r_prev
            d8 = max(0.55 * r_prev, 0.50 * ATR)
            b5_cur, b5_c = -1, np.nan
            for p_idx, kq in enumerate(m):
                mq = int(mm[p_idx])
                if mq >= 870:
                    break
                b5 = (mq - RTH0) // 5
                b5_c = float(c[kq])
                if b5 != b5_cur:
                    b5_cur = b5
                if (mq - RTH0) % 5 == 4 and mq >= 574:
                    if not bf8_done and (b5_c > up8 or b5_c < dn8):
                        lado8 = 1 if b5_c > up8 else -1
                        emit("BF8" if nr_contraction else "BF8N", int(kq), lado8, b5_c - lado8 * d8, b5_c + lado8 * LEJOS * d8)
                        bf8_done = True
                        break

        # ---------- BF3, BF4, BF5, BF7 en velas 15m completadas ----------
        b15_cur = -1
        b15_o = b15_h = b15_l = b15_c = np.nan
        prev15_hi = prev15_lo = prev15_c = np.nan
        armed4_lo = armed4_hi = bf3_done = bf4_done = bf4n_done = bf5_done = bf7_done = False
        closes15_ses: list[float] = []
        tr14_15m = deque(maxlen=14)
        signs7_ses: list[int] = []
        gate7 = 0
        streak7 = 0

        for p_idx, kq in enumerate(m):
            mq = int(mm[p_idx])
            if mq >= 870:
                break
            b15 = (mq - RTH0) // 15
            if b15 != b15_cur:
                b15_cur = b15
                b15_o, b15_h, b15_l, b15_c = float(o[kq]), float(h[kq]), float(l[kq]), float(c[kq])
            else:
                if h[kq] > b15_h:
                    b15_h = float(h[kq])
                if l[kq] < b15_l:
                    b15_l = float(l[kq])
                b15_c = float(c[kq])

            if (mq - RTH0) % 15 == 14:
                r15_bar = max(b15_h - b15_l, 1e-6)
                tr15 = max(r15_bar, abs(b15_h - prev15_c), abs(b15_l - prev15_c)) if np.isfinite(prev15_c) else r15_bar
                tr14_15m.append(tr15)
                vw15 = float(vwap_m[p_idx])

                # BF3 / BF3N: retesteo de fu_midB entre 10:00 y 14:00 ET
                if not bf3_done and fu_side != 0 and has_atr and 600 <= mq < 840:
                    touched = (fu_side == 1 and b15_l <= fu_midB) or (fu_side == -1 and b15_h >= fu_midB)
                    if touched or mq >= 644:
                        d3 = 0.65 * ATR
                        emit("BF3" if fu_is_sweep else "BF3N", int(kq), fu_side, b15_c - fu_side * d3, b15_c + fu_side * (0.50 * d3))
                        bf3_done = True

                # BF4 / BF4N: Previous Day Extreme 25% Reclaim vs Outside Breakout
                if has_atr and np.isfinite(r_prev) and r_prev > 0.0 and mq < 840:
                    d4, tp4 = 0.60 * ATR, 0.65 * ATR
                    if not bf4_done and np.isfinite(prev15_hi):
                        if armed4_lo and b15_c > prev15_hi:
                            emit("BF4", int(kq), 1, b15_c - d4, b15_c + tp4)
                            bf4_done = True
                        elif armed4_hi and b15_c < prev15_lo:
                            emit("BF4", int(kq), -1, b15_c + d4, b15_c - tp4)
                            bf4_done = True
                    if not bf4n_done and (b15_c > prev_hi or b15_c < prev_lo):
                        lado4n = 1 if b15_c > prev_hi else -1
                        emit("BF4N", int(kq), lado4n, b15_c - lado4n * d4, b15_c + lado4n * tp4)
                        bf4n_done = True
                    if b15_l <= prev_lo + 0.25 * r_prev:
                        armed4_lo = True
                    if b15_h >= prev_hi - 0.25 * r_prev:
                        armed4_hi = True

                # BF5 / BF5N: Omega Volume/Range Z-Score Double-Lens (10:00-14:30)
                if not bf5_done and has_atr and mq >= 600 and len(closes15) == 21 and len(closes20) >= 5:
                    sd15 = float(np.std(closes15))
                    avg_r15 = float(np.mean(ranges15))
                    if sd15 > 0.0 and avg_r15 > 0.0:
                        z = (b15_c - float(np.mean(closes15))) / sd15
                        rv = r15_bar / avg_r15
                        vol_f = 0.5 * (float(np.clip(rv, 0.5, 2.0)) + float(np.clip(rv, 0.33, 3.0)))
                        z_entry = z / vol_f
                        if abs(z_entry) >= 1.40:
                            lado5 = 1 if z_entry > 0.0 else -1
                            trend_d = 1 if prev_close >= float(np.mean(closes20)) else -1
                            d5 = 0.60 * ATR
                            emit("BF5" if lado5 == trend_d else "BF5N", int(kq), lado5, b15_c - lado5 * d5, b15_c + lado5 * (2.0 * d5))
                            bf5_done = True

                # BF7 / BF7N: GlowVwap AVWAP Pullback + Anti-Chop (10:30-14:00)
                closes15_ses.append(b15_c)
                if not bf7_done and has_atr and 629 <= mq < 840 and len(closes15_ses) >= 4 and len(tr14_15m) >= 3:
                    s_eff = max(float(np.std(closes15_ses)), 0.40 * float(np.mean(tr14_15m)))
                    dz = 0.15 * s_eff
                    if gate7 == 1 and b15_l <= vw15 + 0.50 * s_eff and b15_c > vw15 + 0.10 * s_eff and b15_c > b15_o:
                        rot = sum(1 for a, b in zip(signs7_ses[-8:], signs7_ses[-7:]) if a != b and a != 0 and b != 0)
                        d7 = max(0.55 * ATR, s_eff)
                        emit("BF7" if rot <= 1 else "BF7N", int(kq), 1, b15_c - d7, b15_c + 2.0 * d7)
                        bf7_done = True
                    elif gate7 == -1 and b15_h >= vw15 - 0.50 * s_eff and b15_c < vw15 - 0.10 * s_eff and b15_c < b15_o:
                        rot = sum(1 for a, b in zip(signs7_ses[-8:], signs7_ses[-7:]) if a != b and a != 0 and b != 0)
                        d7 = max(0.55 * ATR, s_eff)
                        emit("BF7" if rot <= 1 else "BF7N", int(kq), -1, b15_c + d7, b15_c - 2.0 * d7)
                        bf7_done = True

                    # Actualizar estado GlowVwap de forma estrictamente causal para la próxima vela 15m
                    signs7_ses.append(1 if b15_c > vw15 else (-1 if b15_c < vw15 else 0))
                    if b15_c > vw15 + dz:
                        streak7 = streak7 + 1 if streak7 > 0 else 1
                        if streak7 >= 2:
                            gate7 = 1
                    elif b15_c < vw15 - dz:
                        streak7 = streak7 - 1 if streak7 < 0 else -1
                        if streak7 <= -2:
                            gate7 = -1
                else:
                    signs7_ses.append(1 if b15_c > vw15 else (-1 if b15_c < vw15 else 0))

                prev15_hi, prev15_lo, prev15_c = b15_h, b15_l, b15_c
                closes15.append(b15_c)
                ranges15.append(r15_bar)

        # ---------- BF6 / BF6N: LUBE Time-at-Price Breakout (velas 30m continuas) ----------
        b30_cur = -1
        b30_h = b30_l = b30_c = np.nan
        bf6_done = bf6n_done = False
        for p_idx, kq in enumerate(m):
            mq = int(mm[p_idx])
            if mq >= 870:
                break
            b30 = (mq - RTH0) // 30
            if b30 != b30_cur:
                b30_cur = b30
                b30_h, b30_l, b30_c = float(h[kq]), float(l[kq]), float(c[kq])
            else:
                if h[kq] > b30_h:
                    b30_h = float(h[kq])
                if l[kq] < b30_l:
                    b30_l = float(l[kq])
                b30_c = float(c[kq])

            if (mq - RTH0) % 30 == 29:
                L = len(bars30)
                if has_atr and L >= 30 and mq >= 600:
                    fric = sum((1.0 + L) / (i + L) for i, (bh_i, bl_i, _) in enumerate(reversed(bars30), 1) if bl_i <= b30_c <= bh_i)
                    c1, c2, c3, c4 = bars30[-1][2], bars30[-2][2], bars30[-3][2], bars30[-4][2]
                    fir_cur = (4.0 * b30_c + 3.0 * c1 + 2.0 * c2 + c3) / 10.0
                    fir_prev = (4.0 * c1 + 3.0 * c2 + 2.0 * c3 + c4) / 10.0
                    trend6 = 1 if fir_cur >= fir_prev else -1
                    if len(fric_hist) >= 20:
                        q25, q75 = float(np.percentile(fric_hist, 25)), float(np.percentile(fric_hist, 75))
                        d6 = 0.60 * ATR
                        if not bf6_done and fric <= q25:
                            emit("BF6", int(kq), trend6, b30_c - trend6 * d6, b30_c + trend6 * LEJOS * d6)
                            bf6_done = True
                        elif not bf6n_done and fric >= q75:
                            emit("BF6N", int(kq), trend6, b30_c - trend6 * d6, b30_c + trend6 * LEJOS * d6)
                            bf6n_done = True
                    fric_hist.append(fric)
                bars30.append((b30_h, b30_l, b30_c))

        # Actualización causal estricta al cierre de la sesión RTH
        tr_day = max(hi_rth - lo_rth, abs(hi_rth - prev_close), abs(lo_rth - prev_close)) if prev_close is not None else (hi_rth - lo_rth)
        if np.isfinite(tr_day) and tr_day > 0.0:
            atr20.append(tr_day)
        if hi_rth > lo_rth:
            adr20.append(hi_rth - lo_rth)
            rth_ranges10.append(hi_rth - lo_rth)
        closes20.append(cl_rth)
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
