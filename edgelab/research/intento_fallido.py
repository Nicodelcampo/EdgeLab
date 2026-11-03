"""INTENTO-FALLIDO (2026-11-03, idea de Nico): el precio viene de lejos hacia un objetivo en zona, se acerca a menos de `y` sin
tocarlo, se da vuelta y se aleja `z`. Dos vías de decisión:
  A  — al alejarse `z`: entrar HACIA la zona (la idea de Nico) o a favor del rechazo (control);
  B  — habiéndose alejado `z`, esperar a que el precio vuelva a acercarse al objetivo (recupera la fracción `r` del rechazo) y
       entrar: HACIA el objetivo (segundo intento) o a favor del rechazo (segundo rechazo). Son hipótesis distintas y se cuentan todas.
Diseño y pre-registro: docs/research/intento_fallido_20261103/PREREGISTRO_INTENTO_FALLIDO.md (mapa de familias con objetivo en zona:
docs/research/MAPA_OBJETIVOS_ZONAS_INTENTO_FALLIDO_20261103.md).

Población: las aproximaciones de U1 (la zona, el extremo E y el recorrido A salen de los disparos causales de U1 de cada fuente de
zonas) tomadas en su primer disparo (x = 0,33: le falta un tercio del camino). Sobre ESE camino se mide, vela a vela y sin mirar el
futuro: distancia al objetivo T (borde cercano de la zona) con el precio más cercano de cada vela; si T se toca antes del rechazo, no
hay evento (U1 habría cumplido). Todo en unidades de A (el recorrido de ida, conocido en k): `y`, `z` y `r` no mezclan puntos
entre instrumentos.

Decisión siempre al CIERRE de una vela y entrada en el primer tick de la siguiente. Stops estructurales (atlas en R, 03/11/2026):
  - a favor del rechazo: un tick más allá del precio más cercano al objetivo del intento;
  - hacia la zona: un tick más allá del extremo del rechazo (lo más lejos que llegó desde el intento);
  más un colchón opcional de 0,5·z. TP: 1R, 2R, 3R o niveles de estructura Z1/Z2/Z3 (hacia: borde cercano, medio y borde lejano de
  la zona; a favor del rechazo: un tercio, dos tercios y todo el camino de vuelta al origen E).
Noticias: sin entradas a ±5 min de un dato tier1 y salida forzada antes de cada dato (Nico 2026-10-25).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.eventos import TIPOS_TIER1, cerca
from edgelab.research.grilla_generica import Variable

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "INTENTO-FALLIDO"
YS = (0.05, 0.10, 0.20)            # cuán cerca llegó (fracción de A) sin tocar el objetivo
ZS = (0.10, 0.20, 0.35)            # cuánto se alejó después (fracción de A, desde el precio más cercano)
RS = (0.5, 0.8)                    # vía B: fracción del rechazo que el precio recupera hacia el objetivo
# 2026-11-03 (Nico: «la idea es entrar hacia la zona, no a favor del rechazo; probá las dos, con distintos niveles de TP»):
# en cada momento de decisión se mide HACIA la zona (la idea) y A FAVOR DEL RECHAZO (control), como reglas separadas.
REGLAS = ("A_HACIA", "A_RECHAZO", "B50_HACIA", "B80_HACIA", "B50_RECHAZO", "B80_RECHAZO")
LIMITE = 240                       # velas máximas desde el disparo de U1 para que ocurra el intento y la vía B
AH_CORTES = (4.0, 8.0, 16.0)
EXCLUIR_EVENTOS = dict(antes_min=5, despues_min=5, tipos=TIPOS_TIER1)
VARIABLES = [
    Variable("regla", "regla", "grupo", categoria=len(REGLAS)),
    Variable("y", "yi", "grupo", categoria=len(YS)),
    Variable("z", "zi", "grupo", categoria=len(ZS)),
    Variable("A/H", "A_H", "ge", cortes=AH_CORTES, piso=True),
    Variable("N", "ni", "grupo", categoria=2),
]
EJES_ORDINALES = (3,)
# TP: 1R, 2R, 3R o niveles de estructura Z1/Z2/Z3 (hacia: borde cercano, medio y borde lejano de la zona; a favor del rechazo: un tercio,
# dos tercios y todo el camino de vuelta al origen E). Colchón del stop: 0 o 0,5·z más allá del stop estructural.
TPS = ("1R", "2R", "3R", "Z1", "Z2", "Z3")
EJECUCIONES = [(tp, col) for tp in TPS for col in (0.0, 0.5)]
BASE = {"regla": 0, "y": 1, "z": 1, "A/H": 1, "ejecución": 0}
VACIO = ["k", "ses", "lado", "regla", "yi", "zi", "A_H", "ni", "stop_ref", "zA", "T", "mid", "lejos_zona", "E"]


@njit(cache=False)
def _intentos(k0, d, T, A, h, l, c, ses, ys, zs, rs, limite):
    """Por cada aproximación (k0, d, T, A) y cada (y, z): el primer rechazo y, para cada r, el primer reacercamiento. d = lado del
    extremo respecto de la zona (+1: precio arriba, objetivo T = borde superior). Filas (i, yi, zi, regla, j, stop_ref):
    regla 0 A_HACIA (stop más allá del extremo del rechazo), 1 A_RECHAZO (stop más allá del intento), 2+ri B_HACIA, 4+ri B_RECHAZO."""
    out = []
    n = len(c)
    for i in range(len(k0)):
        di = d[i]; Ti = T[i]; Ai = A[i]; s0 = ses[k0[i]]
        for yi in range(len(ys)):
            for zi in range(len(zs)):
                y = ys[yi] * Ai; z = zs[zi] * Ai
                best = np.inf; cerca_ = False; jA = -1; far = 0.0
                j = k0[i] + 1
                while j < n and j <= k0[i] + limite and ses[j] == s0:
                    pc = l[j] if di == 1 else h[j]                       # precio más cercano al objetivo en la vela
                    pf = h[j] if di == 1 else l[j]                       # precio más lejos
                    dc = (pc - Ti) * di
                    if dc <= 0.0: break                                  # tocó el objetivo antes del rechazo: no hay intento fallido
                    if dc < best:
                        best = dc; far = pf                              # nuevo intento: el rechazo arranca acá
                    elif (pf - far) * di > 0: far = pf
                    if best <= y: cerca_ = True
                    if cerca_ and (c[j] - Ti) * di - best >= z:          # se alejó z desde lo más cerca (al cierre)
                        jA = j; break
                    j += 1
                if jA < 0: continue
                p_ap = Ti + di * best                                    # precio del intento (lo más cerca del objetivo)
                out.append((i, yi, zi, 0, jA, far))
                out.append((i, yi, zi, 1, jA, p_ap))
                dA = (c[jA] - Ti) * di
                for ri in range(len(rs)):
                    meta = dA - rs[ri] * (dA - best)                     # distancia al objetivo tras recuperar r del rechazo
                    far2 = far; j = jA + 1
                    while j < n and j <= k0[i] + limite and ses[j] == s0:
                        pf = h[j] if di == 1 else l[j]
                        if (pf - far2) * di > 0: far2 = pf               # extremo del rechazo hasta ahora
                        if (c[j] - Ti) * di <= meta:
                            out.append((i, yi, zi, 2 + ri, j, far2))     # B hacia: stop más allá del extremo del rechazo
                            out.append((i, yi, zi, 4 + ri, j, p_ap))     # B a favor del rechazo: stop más allá del intento
                            break
                        j += 1
    return out


def construir(D: pd.DataFrame, ctx: dict) -> pd.DataFrame:
    """Filas de INTENTO-FALLIDO desde los disparos de U1 de una fuente de zonas (columnas k, lado, lo, hi, E, A, xi, ni, A_H)."""
    if D is None or not len(D): return pd.DataFrame(columns=VACIO)
    D = D[D.xi == 0].drop_duplicates(["k", "lado", "lo", "hi", "ni"]).reset_index(drop=True)      # primer disparo de cada camino
    if not len(D): return pd.DataFrame(columns=VACIO)
    h, l, c = (np.asarray(ctx[x], float) for x in ("h", "l", "c")); ses = np.asarray(ctx["ses"], np.int64)
    d = D.lado.to_numpy(np.int64); lo, hi = D.lo.to_numpy(float), D.hi.to_numpy(float)
    T = np.where(d == 1, hi, lo); LZ = np.where(d == 1, lo, hi); A = D.A.to_numpy(float)
    F = _intentos(D.k.to_numpy(np.int64), d, T, A, h, l, c, ses, np.array(YS), np.array(ZS), np.array(RS), LIMITE)
    if not len(F): return pd.DataFrame(columns=VACIO)
    F = np.array(F); i = F[:, 0].astype(np.int64); regla = F[:, 3].astype(np.int64); zi = F[:, 2].astype(np.int64)
    hacia = (regla == 0) | (regla == 2) | (regla == 3)
    k = F[:, 4].astype(np.int64)
    X = pd.DataFrame(dict(k=k, ses=ses[k], lado=np.where(hacia, -d[i], d[i]), regla=regla, yi=F[:, 1].astype(np.int64), zi=zi,
                          A_H=D.A_H.to_numpy(float)[i], ni=D.ni.to_numpy(np.int64)[i], stop_ref=F[:, 5], zA=np.array(ZS)[zi] * A[i],
                          T=T[i], mid=(lo[i] + hi[i]) / 2, lejos_zona=LZ[i], E=D.E.to_numpy(float)[i]))
    return X.sort_values(["k", "regla", "yi", "zi"], kind="stable", ignore_index=True)


def niveles(r, ej, ctx):
    """9 valores: entrada en el primer tick de la vela siguiente a la decisión, stop estructural (+ colchón) y TP; línea de noticias."""
    tp_, col = ej; s = int(r["lado"]); k = int(r["k"]); tick = float(ctx["tick"]); e = float(ctx["c"][k])
    hacia = int(r["regla"]) in (0, 2, 3)
    st = r["stop_ref"] - s * (tick + col * r["zA"])
    st = np.floor(st / tick) * tick if s == 1 else np.ceil(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    if tp_.endswith("R"): tp = e + s * float(tp_[0]) * R
    elif hacia: tp = {"Z1": r["T"], "Z2": r["mid"], "Z3": r["lejos_zona"]}[tp_]
    else: tp = e + {"Z1": 1 / 3, "Z2": 2 / 3, "Z3": 1.0}[tp_] * (r["E"] - e)
    tp = np.round(tp / tick) * tick
    if (tp - e) * s < tick: return None
    return k, 2, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0


def lineas_salida(ctx) -> np.ndarray:
    """Sólo noticias: salida forzada en la apertura siguiente a toda vela que cierra en [dato − 3 min, dato + 1 min]."""
    f = cerca(np.asarray(ctx["t"], np.int64), 3, 1, TIPOS_TIER1)
    return np.vstack([np.where(f, np.inf, np.nan), np.where(f, -np.inf, np.nan)])
