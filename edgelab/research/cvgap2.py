"""CVGAP-2 (2026-11-04, Nico: «con las nuevas actualizaciones y nueva info de EdgeLab, ¿se podría correr algo nuevo sobre esas reglas?»).

Familia hija de CORREDOR-VOL-GAPS (`corredor_vol_gaps.py`): el MISMO evento causal (impulso del corredor EMA, caja amarilla de volumen
en su extremo, ruptura de la caja sólo en la dirección del impulso, excursión A y regreso a 3 puntos estructurales) con lo aprendido
entre el 02 y el 04/11:
  1. Entrada con CONFIRMACIÓN (una vela que cierra a favor de la operación), lo mejor de INTENTO-FALLIDO-HACIA, además de mercado.
  2. Stop ESTRUCTURAL estricto: un tick más allá del extremo de la excursión (además del stop con colchón del padre). Medido en R.
  3. Duración de las piernas como variables (velas M1, causales): `dur_ida` = desde la última vela que estuvo del lado de la caja
     (respecto del ancla) hasta el extremo; `dur_reg` = desde el extremo hasta la decisión.
  4. Salida forzada por noticias tier1 (línea sólo de tiempo, vale con ejecución cruzada). Tope de 240 velas y cierre de sesión ya los
     aplicaba el simulador al padre.
  5. Los dos ejes de gaps del padre (nunca separaron en DESC) quedan fijos en «cualquiera»: más potencia por celda.
  6. Más activos (campañas en config/autopilot/grillas/campanas/CVGAP2-*.json).
Pre-registro: docs/research/cvgap2_20261104/PREREGISTRO_CVGAP2.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import corredor_vol_gaps as CV
from edgelab.research.agente.regimen import VARIABLES_REGIMEN
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import EXCLUIR_EVENTOS, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "CVGAP-2"
INDICADORES = ["EmaCorridorTrendVolW2"]
LINEAS_SOLO_TIEMPO = True
VARIABLES = [
    Variable("escala", "esc", "grupo", categoria=2),
    Variable("variante_w", "vw", "grupo", categoria=2),
    Variable("pct_vol", "pvol", "ge", categoria=2),
    Variable("exc_amarilla", "exc_am", "ge", cortes=(1.0, 2.0, 4.0), piso=True),
    Variable("punto_regreso", "pt_reg", "grupo", categoria=3),
    Variable("tamano_impulso", "tam_imp", "extremos", cuantiles=3),
    Variable("dur_ida", "dur_ida", "extremos", cuantiles=3),
    Variable("dur_reg", "dur_reg", "extremos", cuantiles=3),
    Variable("vwap", "vwap_al", "eq_any", categoria=2),
    VARIABLES_REGIMEN["hora"],
]
EJES_ORDINALES = (2, 3)
BUSQUEDA_MAX = 2880                   # velas M1 hacia atrás para hallar el extremo y la salida de la caja (~2 días)
ENTRADAS = ("MERC", "CONF")
STOPS = ("S_E1", "S_EXT")              # un tick más allá del extremo · colchón del padre max(2 ticks, 0,15·H_am)
TPS = ("MID50", "MID25", "ORIG100", "2R")
EJECUCIONES = [(e, sl, tp) for e in ENTRADAS for sl in STOPS for tp in TPS]
BASE = {"escala": 0, "variante_w": 1, "pct_vol": 0, "exc_amarilla": 1, "punto_regreso": 1, "tamano_impulso": 2,
        "dur_ida": 2, "dur_reg": 2, "vwap": 2, "reg_hora": 4, "ejecución": 0}


@njit(cache=False)
def _duraciones(k, d, ext, ancla, h, l, ses):
    """Por disparo (vela k, dirección del impulso d, extremo ext, ancla): (dur_ida, dur_reg) en velas M1, sólo con velas <= k.
    La búsqueda cruza sesiones (el padre no reinicia la caja amarilla al cambiar de sesión: ~7 % de los disparos tienen la excursión en la
    sesión anterior); `ses` queda en la firma por compatibilidad. Cuenta velas, no minutos de reloj."""
    m = len(k); di = np.full(m, np.nan); dr = np.full(m, np.nan)
    for t in range(m):
        j = k[t]; je = -1; j0 = max(k[t] - BUSQUEDA_MAX, 0)
        while j >= j0:                          # última vela que tocó el extremo
            if (d[t] == 1 and h[j] >= ext[t] - 1e-9) or (d[t] == -1 and l[j] <= ext[t] + 1e-9):
                je = j; break
            j -= 1
        if je < 0: continue
        dr[t] = k[t] - je
        j = je - 1; jo = -1
        while j >= j0:                                          # última vela antes del extremo del lado de la caja (respecto del ancla)
            if (d[t] == 1 and l[j] <= ancla[t]) or (d[t] == -1 and h[j] >= ancla[t]):
                jo = j; break
            j -= 1
        di[t] = je - (jo if jo >= 0 else j0)
    return di, dr


def disparos(ctx: dict) -> pd.DataFrame:
    D = CV.disparos(ctx)
    if not len(D): return D.assign(dur_ida=pd.Series(dtype=float), dur_reg=pd.Series(dtype=float))
    di, dr = _duraciones(D.k.to_numpy(np.int64), D.dir_imp.to_numpy(np.int64), D.ext.to_numpy(float), D.ancla.to_numpy(float),
                         np.asarray(ctx["h"], float), np.asarray(ctx["l"], float), np.asarray(ctx["ses"], np.int64))
    D = D.assign(dur_ida=di, dur_reg=dr)
    return D[np.isfinite(D.dur_reg)].reset_index(drop=True)


def niveles(r, ej, ctx):
    """9 valores: (start, límite, s, entrada, stop, objetivo, be, fila de la línea de noticias, δ). Siempre contra la ruptura."""
    en, sl_, tp_ = ej; k = int(r["k"]); c = ctx["c"]; ses = ctx["ses"]; tick = float(ctx["tick"]); s = -int(r["dir_imp"])
    if k + 1 >= len(c) or ses[k + 1] != ses[k]: return None
    start, e = k, float(c[k]); ext = float(r["ext"])
    if en == "CONF":
        if k + 2 >= len(c) or ses[k + 2] != ses[k] or (c[k + 1] - c[k]) * s <= 0: return None
        start, e = k + 1, float(c[k + 1])
        # la vela de confirmación puede marcar un extremo nuevo: el stop estructural va detrás del extremo vigente al decidir
        ext = max(ext, float(ctx["h"][k + 1])) if s == -1 else min(ext, float(ctx["l"][k + 1]))
    h_am = max(float(r["h_am"]), tick)
    col = tick if sl_ == "S_E1" else max(2.0 * tick, 0.15 * h_am)
    st = ext - s * col
    st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    tp = e + s * 2.0 * R if tp_ == "2R" else {"MID50": r["mid50"], "MID25": r["mid25"], "ORIG100": r["orig100"]}[tp_]
    tp = np.round(float(tp) / tick) * tick
    if (tp - e) * s < tick: return None
    return start, 2, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0
