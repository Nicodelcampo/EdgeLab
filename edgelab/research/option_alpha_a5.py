"""OPTION-ALPHA (2026-11-18): 8 familias de reglas extraídas del Top 20 Live de Option Alpha, adaptadas a M1 de futuros (A5).

Diseño: docs/research/option_alpha_20261118/DISENO.md; pre-registro: docs/research/option_alpha_20261118/PREREGISTRO.md.
Contrato de `edgelab/research/tablas.py`: hora de Nueva York sobre la sesión RTH (9:30–16:00). Decisión al cierre de la vela M1 `k`,
entrada en el primer tick de la vela siguiente (motor único `ejecucion.py`), salida forzada al cierre RTH (`fin`) o por nivel.
Todas las distancias están normalizadas a rangos o ATR20 causales (K36); sin look-ahead (K48).

Definiciones (derivadas del Top 20 Live de Option Alpha):
  OA1  1:45pm Taco (#2): a las 13:45 NY fade vs punto medio del ORB 15m en volatilidad calma (ATR20/C ≤ p75_120); OA1N = alta vol.
  OA2  1:45pm Sandwich (#4): ancla 13:45 NY; desvío ≥ 0,25·R_am → fade al ancla (1:1), Lun/Mar/Jue/Vie; OA2N = miércoles.
  OA3  ORB 60m Hold (#10): primer cierre fuera del ORB 60m (10:30–12:00), stop borde opuesto, salida cierre RTH.
  OA4  60Min ORB Wed/Fri (#20): ruptura ORB 60m (10:30–14:00) mié/vie, stop mitad ORB, TP 0,5·R; OA4N = Lun/Mar/Jue.
  OA5  ORB Intelligence (#17): ruptura ORB 60m (10:30–13:00) a favor del Daily Bias (mid ORB60 vs previo); OA5N = en contra.
  OA6  THE SPX 0DTE (#11): 10m Heikin Ashi + EMA(8/21) + MACD(12,26) > Banda Bollinger (10:00–14:00); stop vela 10m + 0,1·ATR20.
  OA7  Trendy Short Put Dip (#9): a las 10:30 NY con cierre previo > SMA200 y retroceso ≥ 0,10·ATR20 → largo con SL 1·ATR, TP 0,5·ATR.
  OA8  Theta Fly / NFH (#8/#19): tras deriva contenida a las 13:30 (≤ 0,65·ATR20), desvío ≥ 75% medio rango → fade al medio; OA8N = día tendencial.
"""
from __future__ import annotations

import glob
import os
from collections import deque
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from edgelab.research.ib_madonna import minuto_ny

NOMBRE = "OPTION-ALPHA"
EJECUCIONES = [("PRECIOS", "obj", "stop", "fin")]
DEFINICIONES = ["OA1", "OA2", "OA3", "OA4", "OA5", "OA6", "OA7", "OA8"]
CONTROL = {"OA1": "OA1N", "OA2": "OA2N", "OA4": "OA4N", "OA5": "OA5N", "OA8": "OA8N"}
FILTROS = {
    "vix_bajo": ("vix_open", "<=", 24.0),
    "vix_40": ("vix_open", "<", 40.0),
    "ivr_20": ("vix_ivr", ">=", 20.0),
    "no_fomc": ("is_fomc", "==", 0.0),
    "sin_early_close": ("is_early_close", "==", 0.0),
}
RTH0, RTH1 = 570, 960
LEJOS = 1000.0


@lru_cache(maxsize=1)
def _contexto_externo() -> dict:
    """Carga causal (sólo valores de apertura/cierre previo y calendario fijo) si los Parquets están disponibles."""
    bases = []
    if (env_dir := os.environ.get("EDGELAB_M1NT8_DIR")):
        bases.append(Path(env_dir))
    bases.append(Path(__file__).resolve().parents[2] / "data" / "m1nt8")
    bases.extend(Path(p).parent for p in glob.glob("/kaggle/input/**/cboe_volatility_daily.parquet", recursive=True))
    vol_map, cal_map = {}, {}
    for base in bases:
        vf, cf = base / "cboe_volatility_daily.parquet", base / "us_market_events_calendar_2006_2026.parquet"
        if not vol_map and vf.exists():
            V = pd.read_parquet(vf, columns=["vix_open", "vix_prev_close", "vix_ivr_252_prev_close"])
            V.index = pd.to_datetime(V.index)
            for dt, row in V.iterrows():
                vo = float(row["vix_open"]) if np.isfinite(row["vix_open"]) else float(row["vix_prev_close"])
                vol_map[int(dt.strftime("%Y%m%d"))] = (vo, float(row["vix_prev_close"]), float(row["vix_ivr_252_prev_close"]))
        if not cal_map and cf.exists():
            C = pd.read_parquet(cf, columns=["is_early_close", "is_fomc_day"])
            C.index = pd.to_datetime(C.index)
            for dt, row in C.iterrows():
                cal_map[int(dt.strftime("%Y%m%d"))] = (1.0 if bool(row["is_early_close"]) else 0.0, 1.0 if bool(row["is_fomc_day"]) else 0.0)
    return {"vol": vol_map, "cal": cal_map}


def _macro_sesion(ses_id: int) -> tuple[float, float, float, float, float]:
    """Devuelve (vix_open, vix_prev, vix_ivr, is_early_close, is_fomc) o NaNs si `ses_id` no es YYYYMMDD real."""
    if not (19900101 <= int(ses_id) <= 20991231):
        return (np.nan, np.nan, np.nan, np.nan, np.nan)
    ext = _contexto_externo()
    vix_o, vix_p, ivr = ext["vol"].get(int(ses_id), (np.nan, np.nan, np.nan))
    ec, fomc = ext["cal"].get(int(ses_id), (np.nan, np.nan))
    return (vix_o, vix_p, ivr, ec, fomc)


def _ema_step(prev: float | None, val: float, span: int) -> float:
    a = 2.0 / (span + 1.0)
    return float(val) if prev is None else (a * float(val) + (1.0 - a) * float(prev))


def eventos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, ses = (np.asarray(ctx[x]) for x in ("o", "h", "l", "c", "ses"))
    o, h, l, c = (x.astype(float) for x in (o, h, l, c))
    t_arr = np.asarray(ctx["t"], np.int64)
    mo = minuto_ny(t_arr)
    ext_defs = DEFINICIONES + sorted(set(CONTROL.values()))

    atr20 = deque(maxlen=20)
    atr_pct_hist = deque(maxlen=120)
    closes200 = deque(maxlen=200)
    prev_mid60 = None
    prev_rth_close = None

    # Estado causal continuo de velas 10m para OA6 (actualizado sólo al cierre completo de cada bloque de 10m)
    ha_prev_o = ha_prev_c = ema8 = ema21 = ema12 = ema26 = None
    macd_hist = deque(maxlen=20)
    filas = []

    def hasta_cierre(k: int) -> int:
        return int(k) + int(RTH1 - 1 - mo[k])

    def emit(defn: str, k: int, lado: int, stop: float, obj: float, macro: tuple[float, float, float, float, float]) -> None:
        rg = abs(float(c[k]) - float(stop))
        if not (rg > 0.0 and np.isfinite(stop) and np.isfinite(obj)):
            return
        filas.append({
            "k": int(k), "lado": int(lado), "ref": float(obj), "ext": float(stop), "rg": float(rg),
            "obj": float(obj), "stop": float(stop), "fin": hasta_cierre(k),
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
        dow = int(pd.Timestamp(int(t_arr[m[0]]) - 60, unit="s", tz="UTC").tz_convert("America/New_York").dayofweek)
        ab, cl_rth = float(o[m[0]]), float(c[m[-1]])
        hi_rth, lo_rth = float(h[m].max()), float(l[m].min())
        ATR = float(np.mean(atr20)) if len(atr20) >= 5 else np.nan
        cur_atr_pct = (ATR / prev_rth_close) if (np.isfinite(ATR) and prev_rth_close and prev_rth_close > 0) else np.nan

        # ---------- OA1 / OA1N: 1:45pm Taco (#2) ----------
        i15 = m[mm < RTH0 + 15]
        i_taco = m[mm == 824]
        if len(i15) >= 10 and len(i_taco) and np.isfinite(ATR) and np.isfinite(cur_atr_pct):
            r15 = float(h[i15].max() - l[i15].min())
            mid15 = 0.5 * float(h[i15].max() + l[i15].min())
            kt = int(i_taco[0])
            if r15 > 0.0 and c[kt] != mid15:
                lado = -1 if c[kt] > mid15 else 1
                d_sl = max(r15, 0.25 * ATR)
                stop = c[kt] - lado * d_sl
                obj = c[kt] + lado * LEJOS * d_sl
                calm = len(atr_pct_hist) >= 15 and cur_atr_pct <= float(np.percentile(atr_pct_hist, 75))
                emit("OA1" if calm else "OA1N", kt, lado, stop, obj, macro)

        # ---------- OA2 / OA2N: 1:45pm Sandwich (#4) ----------
        if len(i_taco):
            kt = int(i_taco[0])
            p0 = float(c[kt])
            am_bars = m[mm <= 824]
            r_am = float(h[am_bars].max() - l[am_bars].min())
            if r_am > 0.0:
                post_sw = m[(mm > 824) & (mm <= 870)]
                for k_sw in post_sw:
                    diff = float(c[k_sw] - p0)
                    if abs(diff) >= 0.25 * r_am:
                        lado = -1 if diff > 0.0 else 1
                        stop = float(c[k_sw] - lado * abs(diff))
                        emit("OA2" if dow != 2 else "OA2N", int(k_sw), lado, stop, p0, macro)
                        break

        # ---------- OA3 (#10), OA4/OA4N (#20), OA5/OA5N (#17): ORB 60m ----------
        i60 = m[mm < RTH0 + 60]
        cur_mid60 = None
        if len(i60) >= 35:
            hi60, lo60 = float(h[i60].max()), float(l[i60].min())
            cur_mid60 = 0.5 * (hi60 + lo60)
            post60 = m[(mm >= RTH0 + 60) & (mm < 840)]
            if hi60 > lo60 and len(post60):
                br = next((int(q) for q in post60 if c[q] > hi60 or c[q] < lo60), None)
                if br is not None:
                    lado = 1 if c[br] > hi60 else -1
                    if mo[br] < 720:  # 10:30–12:00 NY: OA3
                        stop3 = lo60 if lado == 1 else hi60
                        emit("OA3", br, lado, stop3, c[br] + lado * LEJOS * abs(c[br] - stop3), macro)
                    # 10:30–14:00 NY: OA4 (mié/vie) vs OA4N (lun/mar/jue)
                    d_mid = abs(c[br] - cur_mid60)
                    if d_mid > 0.0:
                        emit("OA4" if dow in (2, 4) else "OA4N", br, lado, cur_mid60, c[br] + lado * 0.5 * d_mid, macro)
                    # 10:30–13:00 NY: OA5 Daily Bias
                    if mo[br] < 780 and prev_mid60 is not None and d_mid > 0.0:
                        bias = 1 if cur_mid60 > prev_mid60 else (-1 if cur_mid60 < prev_mid60 else 0)
                        if bias != 0:
                            emit("OA5" if lado == bias else "OA5N", br, lado, cur_mid60, c[br] + lado * LEJOS * d_mid, macro)

        # ---------- OA7: Trendy Short Put Spread Dip (#9) ----------
        i1030 = m[mm == 629]
        if len(i1030) and len(closes200) >= 20 and prev_rth_close is not None and np.isfinite(ATR):
            k7 = int(i1030[0])
            sma200 = float(np.mean(closes200))
            if prev_rth_close > sma200 and c[k7] < prev_rth_close - 0.10 * ATR:
                emit("OA7", k7, 1, c[k7] - ATR, c[k7] + 0.5 * ATR, macro)

        # ---------- OA8 / OA8N: Theta Fly / NFH EM% Containment Fade (#8 / #19) ----------
        i1330 = m[mm == 809]
        if len(i1330) and np.isfinite(ATR):
            k1330 = int(i1330[0])
            contained = abs(float(c[k1330] - ab)) <= 0.65 * ATR
            pre_1330 = m[mm <= 809]
            run_hi = float(h[pre_1330].max())
            run_lo = float(l[pre_1330].min())
            for k8 in m[(mm > 809) & (mm <= 870)]:
                if h[k8] > run_hi:
                    run_hi = float(h[k8])
                if l[k8] < run_lo:
                    run_lo = float(l[k8])
                run_rng = run_hi - run_lo
                run_mid = 0.5 * (run_hi + run_lo)
                if run_rng > 0.0 and abs(c[k8] - run_mid) >= 0.375 * run_rng:
                    lado = -1 if c[k8] > run_mid else 1
                    ext8 = run_hi if lado == -1 else run_lo
                    stop8 = ext8 - lado * 0.25 * run_rng
                    emit("OA8" if contained else "OA8N", int(k8), lado, stop8, run_mid, macro)
                    break

        # ---------- OA6: THE SPX 0DTE 10m Heikin Ashi BB-MACD (#11) ----------
        cur_b = -1
        bo = bh = bl = bc = np.nan
        bcnt = 0
        oa6_done = False
        for q in m:
            if mo[q] >= 840:
                break
            bq = int((mo[q] - RTH0) // 10)
            if bq != cur_b:
                cur_b, bo, bh, bl, bc, bcnt = bq, float(o[q]), float(h[q]), float(l[q]), float(c[q]), 1
            else:
                if h[q] > bh:
                    bh = float(h[q])
                if l[q] < bl:
                    bl = float(l[q])
                bc = float(c[q])
                bcnt += 1
            if mo[q] % 10 == 9 and bcnt >= 7 and np.isfinite(ATR):
                ha_c = 0.25 * (bo + bh + bl + bc)
                ha_o = 0.5 * (bo + bc) if ha_prev_o is None else 0.5 * (ha_prev_o + ha_prev_c)
                ha_prev_o, ha_prev_c = ha_o, ha_c
                ema8 = _ema_step(ema8, bc, 8)
                ema21 = _ema_step(ema21, bc, 21)
                ema12 = _ema_step(ema12, bc, 12)
                ema26 = _ema_step(ema26, bc, 26)
                macd = ema12 - ema26
                if len(macd_hist) >= 15 and not oa6_done and mo[q] >= 600:
                    mu = float(np.mean(macd_hist))
                    sd = float(np.std(macd_hist))
                    if sd > 0.0:
                        bull = ha_c > ha_o and ema8 > ema21 and macd > 0.0 and macd > mu + 1.5 * sd
                        bear = ha_c < ha_o and ema8 < ema21 and macd < 0.0 and macd < mu - 1.5 * sd
                        if bull or bear:
                            lado = 1 if bull else -1
                            stop6 = (bl - 0.1 * ATR) if lado == 1 else (bh + 0.1 * ATR)
                            emit("OA6", int(q), lado, stop6, bc + lado * LEJOS * abs(bc - stop6), macro)
                            oa6_done = True
                macd_hist.append(macd)

        # Actualización estrictamente al cierre de la sesión (causal)
        tr = max(hi_rth - lo_rth, abs(hi_rth - prev_rth_close), abs(lo_rth - prev_rth_close)) if prev_rth_close is not None else (hi_rth - lo_rth)
        if np.isfinite(tr) and tr > 0.0:
            atr20.append(tr)
            if prev_rth_close is not None and prev_rth_close > 0.0 and len(atr20) >= 5:
                atr_pct_hist.append(float(np.mean(atr20)) / prev_rth_close)
        prev_rth_close = cl_rth
        closes200.append(cl_rth)
        if cur_mid60 is not None:
            prev_mid60 = cur_mid60

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
