"""U1-CONFIRMA (2026-10-26, aprobado por Nico): la grilla U1-CFD sobre EURUSD con un eje de CONFIRMACIÓN CRUZADA desde GBPUSD.

Hipótesis: un movimiento que comparten EURUSD y GBPUSD es del dólar (factor común, con flujo macro detrás) y se sostiene; uno propio
del euro se parece más a ruido de liquidez. El eje `confirma` (eq_any: los 3 niveles + «cualquiera» = sin filtro) clasifica cada
disparo con lo que pasó ANTES de su vela de decisión k (causal):
  r_s, r_c = retorno de los últimos L minutos en el sensor y en el confirmador, en unidades de su rango M1 mediano de la sesión ANTERIOR;
  2 «lidera»: en la ventana previa [k−2L, k−L] el confirmador se movió (|r_c'| ≥ 0,5) y el sensor no la acompañó (|r_s'| < ½|r_c'|),
              y ahora van en el mismo sentido;
  0 «común»:  mismo signo y |r_c| ≥ ½|r_s| (si no es «lidera»);
  1 «propio»: el resto (signo opuesto o el confirmador quieto).
Sin dato del confirmador en k (o sin sesión anterior) el disparo queda fuera de las celdas (índice −1).
Justificación económica y refutación: `docs/research/u1_cfd_20261025/PREREGISTRO_U1_CONFIRMA.md`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_cfd import BASE as _BASE, EJECUCIONES, EJES_ORDINALES, ESCALAS, INDICADORES, R_USATECH, VARIABLES as _VARS  # noqa: F401
from edgelab.research.u1_cfd import VACIO as _VACIO, disparos as _disparos, niveles  # noqa: F401

NOMBRE = "U1-CONFIRMA"
CONFIRMADOR = True                                   # el preflight le arma un confirmador sintético
L_MIN = 15
VARIABLES = list(_VARS) + [Variable("confirma", "conf", "eq_any", categoria=3)]
VACIO = list(_VACIO) + ["conf"]
BASE = dict(_BASE, confirma=3)                       # «cualquiera»: la base es U1-CFD sin filtro


def _escala_sesion_anterior(cx) -> np.ndarray:
    """Rango M1 mediano de la sesión anterior, por vela (NaN en la primera sesión)."""
    s = pd.DataFrame(dict(ses=cx["ses"], r=cx["h"] - cx["l"])).groupby("ses").r.median()
    return pd.Series(cx["ses"]).map(s.shift(1)).to_numpy(float)


def _retornos(cx, t_eval):
    """Retornos normalizados de [t−L, t] y [t−2L, t−L] (minutos) con la última vela cerrada <= cada t."""
    t, c, e = cx["t"], cx["c"], _escala_sesion_anterior(cx)
    def px(ts):
        j = np.searchsorted(t, ts, side="right") - 1
        ok = (j >= 0) & (j < len(t)) & (t[np.clip(j, 0, len(t) - 1)] > ts - 60 * L_MIN)   # sin hueco mayor que la ventana
        return np.where(ok, c[np.clip(j, 0, len(t) - 1)], np.nan), np.where(ok, e[np.clip(j, 0, len(t) - 1)], np.nan)
    p0, e0 = px(t_eval); p1, _ = px(t_eval - 60 * L_MIN); p2, _ = px(t_eval - 120 * L_MIN)
    return (p0 - p1) / e0, (p1 - p2) / e0


def clasificar(rs, rc, rs_prev, rc_prev) -> np.ndarray:
    ok = np.isfinite(rs) & np.isfinite(rc) & np.isfinite(rs_prev) & np.isfinite(rc_prev)
    mismo = np.sign(rs) == np.sign(rc)
    lidera = mismo & (np.abs(rc_prev) >= 0.5) & (np.abs(rs_prev) < 0.5 * np.abs(rc_prev))
    comun = mismo & (np.abs(rc) >= 0.5 * np.abs(rs))
    out = np.where(lidera, 2, np.where(comun, 0, 1)).astype(float)
    return np.where(ok, out, np.nan)


def disparos(ctx) -> pd.DataFrame:
    cf = ctx.get("conf")
    if cf is None: raise ValueError("U1-CONFIRMA exige el contexto del confirmador (spec «confirmador»)")
    D = _disparos(ctx)
    if not len(D): return pd.DataFrame(columns=VACIO)
    tk = ctx["t"][D.k.to_numpy()]
    rs, rs_p = _retornos(ctx, tk); rc, rc_p = _retornos(cf, tk)
    return D.assign(conf=clasificar(rs, rc, rs_p, rc_p))
