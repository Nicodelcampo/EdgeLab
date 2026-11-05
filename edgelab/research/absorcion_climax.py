"""ABSORCION-CLIMAX (2026-11-03, programa R): barra de clímax de volumen y mecha de absorción tras extensión de 60 minutos.

Fuente: Grossman y Miller (1988), «Liquidity and Market Structure», Journal of Finance; Campbell, Grossman y Wang (1993),
«Trading Volume and Serial Correlation in Stock Returns», Quarterly Journal of Economics. Un movimiento direccional sostenido
que culmina en una vela de alto volumen relativo y mecha larga de rechazo (sin anuncios macro en ±15 min) refleja absorción de
órdenes de mercado agotadas por proveedores de liquidez, revirtiendo hacia el equilibrio previo.
Diseño: docs/research/programa_r_20261103/DISENO_ABSORCION_CLIMAX.md.

Construcción (100% causal):
- Dentro de cada sesión (03:00–14:30 ET, desde la vela 60 de la sesión), se mide la extensión direccional de 60 velas
  ext = c[k−1] − c[k−60] en unidades de ATR14 causal.
- Disparo en k si |ext| >= 1,2 * ATR14, el volumen v[k] >= 1,35 * media(v[k−30:k]) y la mecha de rechazo contra el signo de ext
  supera el 38 % del rango de la vela k, con enfriamiento de 35 velas por sesión.
- Excluye eventos macro (CPI, NFP, FOMC ±15 min) mediante EXCLUIR_EVENTOS.
- Ejecución: entrada en el primer tick siguiente hacia el equilibrio (lado = −signo(ext)), stop detrás del extremo de la vela de
  clímax + 0,8x o 1,3x ATR14 (piso 4 ticks), objetivo amplio a 2,0R, 3,0R o 3,5R, y tope de 120 barras.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research import rango_ruptura as RR
from edgelab.research.eventos import TIPOS_TIER1
from edgelab.research.regimen_sesion import minuto_ny
from edgelab.research.zonas_gaps import _atr_causal

NOMBRE = "ABSORCION-CLIMAX"
INDICADORES = ["ABSORCION-CLIMAX"]
M0, M1 = 180, 870
ENFRIAMIENTO = 35
TOPE_BARRAS = 120
PREFLIGHT_T0_S = 1_760_047_200
# 2026-11-03 (revisión de Gemini): el filtro de ±15 min sólo miraba la ENTRADA y sólo CPI/NFP/FOMC. Ahora: sin entradas a ±15 min
# de cualquier dato tier1 y salida forzada antes de cada dato y a las 15:55 ET (`lineas_salida`).
EXCLUIR_EVENTOS = dict(antes_min=15, despues_min=15, tipos=TIPOS_TIER1)
M_SALE = 955
VARIABLES = [
    Variable("mecha_rechazo", "mecha", "ge", cortes=(0.45, 0.58)),
    Variable("climax_volumen", "rvol", "ge", cortes=(1.55, 2.00)),
    Variable("extension_previa", "ext_atr", "extremos", cuantiles=3),
]
EJES_ORDINALES = (0, 1)
EJECUCIONES = [("ATR", 0.8, 2.0), ("ATR", 0.8, 3.0), ("ATR", 1.3, 2.0), ("ATR", 1.3, 3.5)]
BASE = {"mecha_rechazo": 0, "climax_volumen": 0, "extension_previa": 2, "ejecución": 1}
VACIO = ["k", "ses", "lado", "mecha", "rvol", "ext_atr", "extremo", "atr_k"]


def disparos(ctx: dict) -> pd.DataFrame:
    o, h, l, c, v = (np.asarray(ctx[x], float) for x in ("o", "h", "l", "c", "v"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64))
    atr = _atr_causal(h, l, c); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg)
        if len(idx) < 65: continue
        hs, ls, cs, os_, vs, ms, atrs = h[idx], l[idx], c[idx], o[idx], v[idx], m[idx], atr[idx]
        vm = pd.Series(vs).shift(1).rolling(30, min_periods=20).mean().to_numpy()
        ult = -10**9
        for p in range(60, len(idx)):
            if p - ult < ENFRIAMIENTO or not (M0 <= ms[p] <= M1): continue
            ak = float(atrs[p]); rk = float(hs[p] - ls[p]); vmk = float(vm[p])
            if not (ak > 0 and rk > 0 and vmk > 0): continue
            ext = float(cs[p - 1] - cs[p - 60]); ext_a = abs(ext) / ak
            if ext_a < 1.2 or vs[p] < 1.35 * vmk: continue
            dir_ext = 1 if ext > 0 else -1
            mecha = (hs[p] - max(os_[p], cs[p])) / rk if dir_ext == 1 else (min(os_[p], cs[p]) - ls[p]) / rk
            if mecha < 0.38: continue
            s = -dir_ext; extr = float(hs[p]) if dir_ext == 1 else float(ls[p])
            ult = p
            filas.append((int(idx[p]), int(sg), s, float(mecha), float(vs[p] / vmk), float(ext_a), extr, ak))
    return pd.DataFrame(filas, columns=VACIO) if filas else pd.DataFrame(columns=VACIO)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = np.asarray(ctx["c"], float)[k]
    base_d = np.abs(e - D["extremo"].to_numpy(float)) + float(ej[1]) * D["atr_k"].to_numpy(float)
    d = np.maximum(base_d, 4.0 * tick)
    st = np.where(s == 1, np.floor((e - d) / tick) * tick, np.ceil((e + d) / tick) * tick)
    return k, s, e, st, np.round((e + s * float(ej[2]) * np.abs(e - st)) / tick) * tick


def _lote9(D, ej, ctx):
    k, s, e, st, tp = _lote(D, ej, ctx)
    return np.ones(len(D), bool), k, s, e, st, tp, (s == -1).astype(np.int64)


def lineas_salida(ctx) -> np.ndarray:
    return RR.lineas_salida_noticias(ctx, M_SALE)


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote9, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote9, D, ej, ctx)
