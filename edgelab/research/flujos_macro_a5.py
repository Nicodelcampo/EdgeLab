"""FLUJOS-MACRO (2026-11-19): 8 familias de reglas intrasesión basadas en flujos institucionales, VIX9D/VIX, calendario y Oro (A5).

Diseño: docs/research/flujos_macro_20261119/DISENO.md; pre-registro: docs/research/flujos_macro_20261119/PREREGISTRO.md;
catálogo: docs/research/flujos_macro_20261119/CATALOGO_14_ESTRATEGIAS_POST_FRICCION.md.
Contrato de `edgelab/research/tablas.py`: hora de Nueva York sobre la sesión CME/RTH (9:30–16:00). Decisión al cierre de la vela M1 `k`,
entrada en el primer tick de la vela siguiente (motor único `ejecucion.py`), salida forzada por nivel, tiempo o cierre RTH (`fin`).
Todos los stops iniciales están anclados a volatilidad diaria (`>= 0,50 × ATR20_D1` o sigma implícita CBOE), sin look-ahead (K48).

Definiciones (Carril 1 intrasesión):
  FM1 / FM1N  NY VIX9D/VIX Implied-Sigma Channel Trend (TradingView OS exlux): a las 10:00 ET usa sigma_d = (IV_{t-1}/100)/sqrt(252)
              con piso 0,50·ATR20 y corte 15:30 ET; FM1 = a favor del impulso 30m (SL=TP=d1), FM1N = fade en contra.
  FM2 / FM2N  Concretum Open-Centered ATR-Band Intraday Trend (Pagani & Zarattini 2026): bandas Open_930 ± 0,50·ATR14_D1 en 5m
              (09:35–15:00 ET), SL en Open_930; FM2 = brazo Largo (> Upper), FM2N = brazo Corto (< Lower).
  FM3 / FM3N  Daily IBS Oversold Snapback (QuantifiedStrategies): a las 09:35 ET compra hasta 15:59 ET con SL 1,25·ATR20;
              FM3 = tras sesión previa cerrada abajo (prev_ibs < 0,25), FM3N = tras cierre arriba (prev_ibs > 0,75).
  FM4 / FM4N  Turnaround Tuesday (Larry Williams / QS): sólo martes a las 09:35 ET compra hasta 15:59 ET con SL 1,25·ATR20;
              FM4 = lunes débil (Close < Open y IBS < 0,50), FM4N = lunes fuerte.
  FM5 / FM5N  Overnight-Gap Breakout Continuation (QS Gold COMEX + Quantpedia min+1): a las 09:31 ET con |Gap| >= 0,75·Media20(|Gap|)
              y ruptura del rango de 5 sesiones previas, SL 0,75·ATR20; FM5 = Largo > High5d, FM5N = Corto < Low5d.
  FM6 / FM6N  Pre-COMEX / London Box Compression Breakout (TradingView OS xsixs, Oro GC): caja 05:00–08:00 ET (London AM Fix),
              primera ruptura 15m (08:15–13:30 ET), SL max(|Entry-Mid|, 0,50·ATR20), TP 1,5R; FM6 = comprimida (<= 0,60·ATR20), FM6N = expandida.
  FM7 / FM7N  Vol-Spike Fear vs Vol-Crush Momentum (Bansal-Stivers / EdgeTools Multi-VIX): a las 09:35 ET sobre volatilidad causal
              (VIX prev o RV5 en sintético), Largo SL 1,50·ATR20; FM7 = pico de miedo (z20 >= 1,15), FM7N = compresión (z6 <= -0,85).
  FM8 / FM8N  Stress-Conditioned Last-30m Momentum (Baltussen 2021 / QC Crash): a las 15:30 ET en dirección (Close_1530 - Open_930),
              SL 0,50·ATR20 hasta 15:59 ET; FM8 = día de estrés (|mv| >= 0,75·ATR20), FM8N = día calmo (0,15–0,75·ATR20).
"""
from __future__ import annotations

import glob
import math
import os
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny
from edgelab.research.option_alpha_a5 import LEJOS, RTH0, RTH1

NOMBRE = "FLUJOS-MACRO"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["FM1", "FM2", "FM3", "FM4", "FM5", "FM6", "FM7", "FM8"]
CONTROL = {f"FM{i}": f"FM{i}N" for i in range(1, 9)}
FILTROS = {
    "vix_contango": ("vix_slope", "<", 1.0),
    "vix_alto": ("vix_prev", ">=", 20.0),
    "no_opex": ("is_opex", "==", 0.0),
    "no_fomc": ("is_fomc", "==", 0.0),
    "sin_early_close": ("is_early_close", "==", 0.0),
}
SQRT_252 = math.sqrt(252.0)


@lru_cache(maxsize=1)
def _cargar_cboe_cal() -> dict[int, tuple[float, ...]]:
    """Mapa causal YYYYMMDD -> (vix_o, vix_p, vix_ivr, vix9d_p, vix_slope, vxn_p, gvz_p, ec, fomc, opex)."""
    roots = [Path(p) for p in ([os.environ["EDGELAB_M1NT8_DIR"]] if os.environ.get("EDGELAB_M1NT8_DIR") else [])]
    roots.append(Path(__file__).resolve().parents[2] / "data" / "m1nt8")
    roots.extend(Path(p).parent for p in glob.glob("/kaggle/input/**/cboe_volatility_daily.parquet", recursive=True))
    v_df = c_df = None
    for d in roots:
        vf, cf = d / "cboe_volatility_daily.parquet", d / "us_market_events_calendar_2006_2026.parquet"
        if v_df is None and vf.exists():
            v_df = pd.read_parquet(
                vf,
                columns=["vix_open", "vix_prev_close", "vix_ivr_252_prev_close", "vix9d_prev_close", "vxn_prev_close", "gvz_prev_close"],
            )
            v_df.index = pd.to_datetime(v_df.index).strftime("%Y%m%d").astype(int)
        if c_df is None and cf.exists():
            c_df = pd.read_parquet(cf, columns=["is_early_close", "is_fomc_day", "is_monthly_opex"])
            c_df.index = pd.to_datetime(c_df.index).strftime("%Y%m%d").astype(int)
    out: dict[int, tuple[float, ...]] = {}
    keys = (set(v_df.index) if v_df is not None else set()) | (set(c_df.index) if c_df is not None else set())
    v_dict = v_df.to_dict("index") if v_df is not None else {}
    c_dict = c_df.to_dict("index") if c_df is not None else {}
    for k in keys:
        vr = v_dict.get(k, {})
        cr = c_dict.get(k, {})
        vp = float(vr.get("vix_prev_close", np.nan))
        vo = float(vr.get("vix_open", np.nan))
        if not np.isfinite(vo):
            vo = vp
        v9 = float(vr.get("vix9d_prev_close", np.nan))
        slope = (v9 / vp) if (np.isfinite(v9) and np.isfinite(vp) and vp > 0.0) else np.nan
        out[int(k)] = (
            vo, vp, float(vr.get("vix_ivr_252_prev_close", np.nan)), v9, slope,
            float(vr.get("vxn_prev_close", np.nan)), float(vr.get("gvz_prev_close", np.nan)),
            (1.0 if bool(cr["is_early_close"]) else 0.0) if "is_early_close" in cr else np.nan,
            (1.0 if bool(cr["is_fomc_day"]) else 0.0) if "is_fomc_day" in cr else np.nan,
            (1.0 if bool(cr["is_monthly_opex"]) else 0.0) if "is_monthly_opex" in cr else np.nan,
        )
    return out


def _rasgos_dia(ses_id: int) -> tuple[float, ...]:
    if not (19900101 <= int(ses_id) <= 20991231):
        return (np.nan,) * 10
    return _cargar_cboe_cal().get(int(ses_id), (np.nan,) * 10)


def eventos(ctx: dict) -> pd.DataFrame:
    """Genera eventos causales A5 para las 8 reglas FM1–FM8 y sus controles FM1N–FM8N."""
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    t_arr = np.asarray(ctx["t"], np.int64)
    mo = minuto_ny(t_arr)
    ext_defs = DEFINICIONES + sorted(set(CONTROL.values()))

    # Estado diario estrictamente causal (actualizado al cierre de la sesión RTH)
    atr20 = deque(maxlen=20)
    highs5 = deque(maxlen=5)
    lows5 = deque(maxlen=5)
    abs_gaps20 = deque(maxlen=20)
    ret_hist = deque(maxlen=5)
    vol_hist20 = deque(maxlen=20)
    vol_hist6 = deque(maxlen=6)
    prev_hi = prev_lo = prev_open = prev_close = prev_ibs = None
    filas = []

    for s in np.unique(ses):
        m_ses = np.flatnonzero(ses == s)
        if not len(m_ses):
            continue
        m = m_ses[(mo[m_ses] >= RTH0) & (mo[m_ses] < RTH1)]
        mm = mo[m] if len(m) else np.empty(0, dtype=np.int64)
        macro = _rasgos_dia(int(s))  # vo, vp, ivr, v9, slope, vxn, gvz, ec, fomc, opex
        r_prev = (prev_hi - prev_lo) if (prev_hi is not None and prev_lo is not None) else np.nan
        ATR = float(np.mean(atr20)) if len(atr20) >= 3 else (float(r_prev) if np.isfinite(r_prev) and r_prev > 0.0 else np.nan)
        ATR14 = float(np.mean(list(atr20)[-14:])) if len(atr20) >= 3 else ATR
        has_atr = bool(np.isfinite(ATR) and ATR > 0.0)

        def emit(defn: str, k_idx: int, lado: int, stop: float, obj: float, fin_k: int | None = None) -> None:
            rg = abs(float(c[k_idx]) - float(stop))
            if not (rg > 0.0 and np.isfinite(stop) and np.isfinite(obj)):
                return
            f_out = int(k_idx) + int(RTH1 - 1 - mo[k_idx]) if fin_k is None else int(fin_k)
            filas.append({
                "k": int(k_idx), "lado": int(lado), "ref": float(obj), "ext": float(stop), "rg": float(rg),
                "obj": float(obj), "stop": float(stop), "fin": f_out,
                "vix_open": macro[0], "vix_prev": macro[1], "vix_ivr": macro[2], "vix_slope": macro[4],
                "is_early_close": macro[7], "is_fomc": macro[8], "is_opex": macro[9],
                defn: True,
            })

        # ---------- FM6 / FM6N: Pre-COMEX / London Box (05:00-08:00 ET) -> 15m breakout (08:15-13:30 ET) ----------
        idx_495 = np.flatnonzero((mo[m_ses] >= 495) & (mo[m_ses] < 1020))   # 2026-11-19 (K53): la sesión CME empieza 18:00 del día previo; sin el tope, la vela de las 18:00 pasaba como «≥ 08:15» y la caja quedaba vacía
        if has_atr and len(idx_495):
            k_495 = int(m_ses[int(idx_495[0])])
            box_idx = m_ses[(m_ses < k_495) & (mo[m_ses] >= 300) & (mo[m_ses] < 480)]
            if len(box_idx) >= 20:
                b_hi, b_lo = float(h[box_idx].max()), float(l[box_idx].min())
                b_rng = b_hi - b_lo
                b_mid = 0.5 * (b_hi + b_lo)
                if b_rng >= 0.15 * ATR:
                    b15_cur = -1
                    b15_c = np.nan
                    for kq in m_ses[(mo[m_ses] >= 480) & (mo[m_ses] < 810)]:
                        mq = int(mo[kq])
                        b15 = mq // 15
                        b15_c = float(c[kq])
                        if b15 != b15_cur:
                            b15_cur = b15
                        if mq >= 495 and mq % 15 == 14 and (b15_c > b_hi or b15_c < b_lo):
                            lado6 = 1 if b15_c > b_hi else -1
                            d6 = max(abs(b15_c - b_mid), 0.50 * ATR)
                            emit("FM6" if b_rng <= 0.60 * ATR else "FM6N", int(kq), lado6, b15_c - lado6 * d6, b15_c + lado6 * 1.50 * d6)
                            break

        if not len(m):
            continue

        ab, cl_rth = float(o[m[0]]), float(c[m[-1]])
        hi_rth, lo_rth = float(h[m].max()), float(l[m].min())

        # ---------- FM5 / FM5N: Overnight-Gap Breakout Continuation (09:31 ET) ----------
        pos_931 = np.flatnonzero((mm >= 571) & (mm <= 574))
        cur_abs_gap = np.nan
        if prev_close is not None and len(pos_931):
            k5 = int(m[int(pos_931[0])])
            gap = float(o[k5]) - prev_close
            cur_abs_gap = abs(gap)
            if has_atr and len(highs5) == 5 and len(abs_gaps20) >= 5:
                avg_gap = float(np.mean(abs_gaps20))
                d5 = 0.75 * ATR
                if avg_gap > 0.0:
                    if float(c[k5]) > max(highs5) and gap >= 0.75 * avg_gap:
                        emit("FM5", k5, 1, float(c[k5]) - d5, float(c[k5]) + LEJOS * d5)
                    elif float(c[k5]) < min(lows5) and gap <= -0.75 * avg_gap:
                        emit("FM5N", k5, -1, float(c[k5]) + d5, float(c[k5]) - LEJOS * d5)

        # ---------- FM3 (IBS), FM4 (Turnaround Tuesday), FM7 (Vol Spike/Crush) a las 09:35 ET ----------
        pos_935 = np.flatnonzero(mm == 574)
        cur_vol_obs = macro[1] if np.isfinite(macro[1]) else (float(np.std(ret_hist)) * SQRT_252 * 100.0 if len(ret_hist) == 5 else np.nan)
        if has_atr and len(pos_935):
            k35 = int(m[int(pos_935[0])])
            c35 = float(c[k35])
            if prev_ibs is not None:
                d3 = 1.25 * ATR
                if prev_ibs < 0.25:
                    emit("FM3", k35, 1, c35 - d3, c35 + LEJOS * d3)
                elif prev_ibs > 0.75:
                    emit("FM3N", k35, 1, c35 - d3, c35 + LEJOS * d3)

                dow = int(pd.Timestamp(int(t_arr[k35]) - 60, unit="s", tz="UTC").tz_convert("America/New_York").dayofweek)
                if dow == 1 and prev_open is not None and prev_close is not None:
                    weak_mon = (prev_close < prev_open) and (prev_ibs < 0.50)
                    emit("FM4" if weak_mon else "FM4N", k35, 1, c35 - d3, c35 + LEJOS * d3)

            if np.isfinite(cur_vol_obs) and len(vol_hist20) >= 12 and len(vol_hist6) == 6:
                sd20, sd6 = float(np.std(vol_hist20)), float(np.std(vol_hist6))
                d7 = 1.50 * ATR
                if sd20 > 1e-9 and ((cur_vol_obs - float(np.mean(vol_hist20))) / sd20) >= 1.15:
                    emit("FM7", k35, 1, c35 - d7, c35 + LEJOS * d7)
                elif sd6 > 1e-9 and ((cur_vol_obs - float(np.mean(vol_hist6))) / sd6) <= -0.85:
                    emit("FM7N", k35, 1, c35 - d7, c35 + LEJOS * d7)

        # ---------- FM1 / FM1N: NY VIX9D/VIX Implied-Sigma Channel Trend (10:00 -> 15:30 ET) ----------
        pos_1000 = np.flatnonzero(mm == 599)
        if has_atr and prev_close is not None and prev_close > 0.0 and len(pos_1000):
            k1 = int(m[int(pos_1000[0])])
            iv_p = macro[3] if np.isfinite(macro[3]) else macro[1]
            sig_d = (iv_p / 100.0) / SQRT_252 if np.isfinite(iv_p) and iv_p > 0.0 else (ATR / prev_close)
            d1 = max(sig_d * ab, 0.50 * ATR)
            mv1 = float(c[k1]) - ab
            if mv1 != 0.0:
                lado1 = 1 if mv1 > 0.0 else -1
                fin1 = min(int(k1) + 330, int(k1) + int(RTH1 - 1 - mo[k1]))
                emit("FM1", k1, lado1, float(c[k1]) - lado1 * d1, float(c[k1]) + lado1 * d1, fin1)
                emit("FM1N", k1, -lado1, float(c[k1]) + lado1 * d1, float(c[k1]) - lado1 * d1, fin1)

        # ---------- FM2 / FM2N: Concretum Open-Centered ATR-Band Intraday Trend (5m) ----------
        if has_atr and np.isfinite(ATR14) and ATR14 > 0.0:
            up2, dn2 = ab + 0.50 * ATR14, ab - 0.50 * ATR14
            fm2_done = fm2n_done = False
            b5_cur = -1
            b5_c = np.nan
            for p_idx, kq in enumerate(m):
                mq = int(mm[p_idx])
                if mq >= 900:
                    break
                b5 = (mq - RTH0) // 5
                b5_c = float(c[kq])
                if b5 != b5_cur:
                    b5_cur = b5
                if (mq - RTH0) % 5 == 4 and mq >= 574:
                    if not fm2_done and b5_c > up2:
                        emit("FM2", int(kq), 1, ab, b5_c + LEJOS * (b5_c - ab))
                        fm2_done = True
                    if not fm2n_done and b5_c < dn2:
                        emit("FM2N", int(kq), -1, ab, b5_c - LEJOS * (ab - b5_c))
                        fm2n_done = True
                    if fm2_done and fm2n_done:
                        break

        # ---------- FM8 / FM8N: Stress-Conditioned Last-30m Institutional Momentum (15:30 ET) ----------
        pos_1530 = np.flatnonzero(mm == 929)
        if has_atr and len(pos_1530):
            k8 = int(m[int(pos_1530[0])])
            mv8 = float(c[k8]) - ab
            d8 = 0.50 * ATR
            if abs(mv8) >= 0.75 * ATR:
                lado8 = 1 if mv8 > 0.0 else -1
                emit("FM8", k8, lado8, float(c[k8]) - lado8 * d8, float(c[k8]) + lado8 * LEJOS * d8)
            elif abs(mv8) >= 0.15 * ATR:
                lado8 = 1 if mv8 > 0.0 else -1
                emit("FM8N", k8, lado8, float(c[k8]) - lado8 * d8, float(c[k8]) + lado8 * LEJOS * d8)

        # Actualización causal estricta al cierre de la sesión RTH
        tr_day = max(hi_rth - lo_rth, abs(hi_rth - prev_close), abs(lo_rth - prev_close)) if prev_close is not None else (hi_rth - lo_rth)
        if np.isfinite(tr_day) and tr_day > 0.0:
            atr20.append(tr_day)
        if prev_close is not None and prev_close > 0.0 and cl_rth > 0.0:
            ret_hist.append(math.log(cl_rth / prev_close))
        if np.isfinite(cur_abs_gap):
            abs_gaps20.append(cur_abs_gap)
        if np.isfinite(cur_vol_obs):
            vol_hist20.append(cur_vol_obs)
            vol_hist6.append(cur_vol_obs)
        highs5.append(hi_rth)
        lows5.append(lo_rth)
        prev_ibs = ((cl_rth - lo_rth) / (hi_rth - lo_rth)) if (hi_rth > lo_rth) else None
        prev_hi, prev_lo, prev_open, prev_close = hi_rth, lo_rth, ab, cl_rth

    cols = ["k", "lado", "ref", "ext", "rg", "obj", "stop", "fin", "vix_open", "vix_prev", "vix_ivr", "vix_slope", "is_early_close", "is_fomc", "is_opex"] + ext_defs
    E = pd.DataFrame(filas)
    for col in cols:
        if col not in E:
            E[col] = False if col in ext_defs else np.nan
    for col in ext_defs:
        E[col] = E[col].fillna(False).astype(bool)
    if not len(E):
        return pd.DataFrame(columns=cols)
    return E[cols].astype({"k": np.int64, "lado": np.int64, "fin": np.int64}).sort_values(["k", "lado"] + ext_defs, kind="mergesort").reset_index(drop=True)
