"""ESCALONADAS-M1 (2026-11-18, pedido de Nico: «había un indicador de picos de 150t en MNQ… hacé una versión en M1 para el NQ y MNQ,
quizás agregándole otros filtros u otras lógicas»). Pre-registro: docs/research/escalonadas_m1_20261118/PREREGISTRO.md.

Evento: la serie ESCALONADA PLANA (picos que no superan al anterior, `tools/escalonadas_det.py`, familia «planas», confirmación por
precio) detectada en tiempo real sobre velas M1. Los parámetros del detector están en ticks de ES 25t; acá la unidad es
u = rango medio de la vela M1 en las 20 sesiones anteriores / 2,5 (K36: sin puntos fijos; una vela media ≈ 2,5 unidades, como la
distancia media de detección en ES 25t). Se corre por sesión (las series cortan en la pausa de sesión).
Dirección: techo (H) → venta, piso (L) → compra (la misma de MNQ-ESCALONADAS-ESCALAS).

Definiciones (columnas booleanas):
  ESC       toda serie detectada
  ESC4      detectada con ≥ 4 picos (escalera más larga)
  ESC_VWAP  operación del lado del VWAP de la sesión: venta sólo con cierre < VWAP, compra sólo con cierre > VWAP
  CTRL / CTRL_VWAP   control placebo causal: velas elegidas por un hash de su minuto (≈ 1 de cada 250, como la frecuencia de las
                     series), lado ±1 por el hash, la unidad de su sesión (CTRL_VWAP: además alineado con el VWAP de su sesión)
Ejecución (motor único): a mercado en el primer tick de la vela siguiente; ref = cierre + lado·rg con rg = rango medio M1 (D ≈ rg);
stop sl·D, objetivo tp·D.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NOMBRE = "ESCALONADAS-M1"
EJECUCIONES = [("MERCADO", sl, sl * r, 0, 0) for sl in (1.0, 2.0, 4.0) for r in (2.0, 5.0)]
DEFINICIONES = ["ESC", "ESC4", "ESC_VWAP"]
DEPENDENCIAS_KERNEL = ("tools.escalonadas_det", "tools.peaks_rule", "tools.peaks_learn")   # detector (import perezoso en `_detector`)
CONTROL = {"ESC": "CTRL", "ESC4": "CTRL", "ESC_VWAP": "CTRL_VWAP"}
VELA_MEDIA_U, N_SES_RANGO, P_CTRL, SEMILLA = 2.5, 20, 1 / 250, 20261118


def _detector():
    sys.path.insert(0, str(ROOT / "tools"))
    import escalonadas_det as ED
    return ED


def rango_causal(ctx) -> pd.Series:
    """Rango medio de la vela M1 por sesión, media de las N_SES_RANGO sesiones ANTERIORES (NaN al principio)."""
    r = pd.Series(np.asarray(ctx["h"]) - np.asarray(ctx["l"])).groupby(np.asarray(ctx["ses"])).mean()
    return r.rolling(N_SES_RANGO).mean().shift(1)


def _vwap(ctx) -> np.ndarray:
    c, v, ses = np.asarray(ctx["c"], float), np.asarray(ctx["v"], float), np.asarray(ctx["ses"])
    df = pd.DataFrame(dict(s=ses, pv=c * v, v=v)); g = df.groupby("s")
    with np.errstate(invalid="ignore", divide="ignore"):
        return (g.pv.cumsum() / g.v.cumsum()).to_numpy()


def eventos(ctx) -> pd.DataFrame:
    ED = _detector(); f = ED.FAMILIAS["planas"]
    h, l, c, t, ses = (np.asarray(ctx[x]) for x in ("h", "l", "c", "t", "ses")); t = t.astype(float)
    rg_s = rango_causal(ctx); vw = _vwap(ctx); filas = []
    for s in np.unique(ses):
        rg = rg_s.get(s, np.nan)
        if not rg > 0: continue
        m = np.flatnonzero(ses == s); u = rg / VELA_MEDIA_U
        if len(m) <= 2 * ED.FAMILIAS["planas"]["w"] + 1: continue           # sesión con menos velas que el pivote (peaks_rule.pivots)
        for z in ED.detectar_px(dict(h=h[m] / u * 0.25, l=l[m] / u * 0.25, t=t[m]), f):
            k = int(m[0] + z["det_i"])
            filas.append((k, -1 if z["kind"] == "H" else 1, rg, int(z["det_pico"])))
    cols = ["k", "lado", "ref", "ext", "rg", "picos", "ESC", "ESC4", "ESC_VWAP", "CTRL", "CTRL_VWAP"]
    R = pd.DataFrame(filas, columns=["k", "lado", "rg", "picos"])            # puede estar vacía: los controles igual se generan
    # control CAUSAL (placebo): velas elegidas por un hash del índice de la vela (no depende de nada más), con probabilidad P_CTRL por
    # vela (≈ la frecuencia de las series reales), lado ±1 por otro bit del hash y la unidad de su propia sesión. (La versión anterior,
    # «una vela de una sesión pasada por cada serie», ponía filas en velas pasadas decididas en el futuro: la falló la causalidad.)
    # hash del MINUTO (t // 60), no del índice: el mismo minuto se elige con ticks y con M1 (enmienda 1: con el índice, cada fuente
    # elegía velas distintas y la calibración del control no podía comparar nada)
    kk = (t.astype(np.int64) // 60).astype(np.uint64); hsh = (kk * np.uint64(2654435761) + np.uint64(SEMILLA)) % np.uint64(2 ** 32)
    elegidas = np.flatnonzero(hsh.astype(np.float64) / 2 ** 32 < P_CTRL)
    ctrl = [(int(q), 1 if (int(hsh[q]) >> 7) & 1 else -1, rg_s.get(ses[q], np.nan), 0) for q in elegidas]
    ctrl = [x for x in ctrl if x[2] > 0]
    C = pd.DataFrame(ctrl, columns=["k", "lado", "rg", "picos"])
    R["tipo"] = "ESC"; C["tipo"] = "CTRL"; E = pd.concat([x for x in (R, C) if len(x)], ignore_index=True) if len(R) or len(C) else R
    if not len(E): return pd.DataFrame(columns=cols)
    E = E.astype(dict(k=np.int64, lado=np.int64, rg=float, picos=np.int64))
    k = E.k.to_numpy(np.int64); lado = E.lado.to_numpy(np.int64)
    E["ref"] = c[k] + lado * E.rg.to_numpy(float); E["ext"] = c[k]
    alin = (lado * (c[k] - vw[k])) > 0                                                           # del lado del VWAP
    esc = (E.tipo == "ESC").to_numpy()
    E["ESC"] = esc; E["ESC4"] = esc & (E.picos.to_numpy() >= 4); E["ESC_VWAP"] = esc & alin
    E["CTRL"] = ~esc; E["CTRL_VWAP"] = ~esc & alin
    return E.drop(columns=["tipo"]).sort_values("k", kind="mergesort").reset_index(drop=True)[cols]
