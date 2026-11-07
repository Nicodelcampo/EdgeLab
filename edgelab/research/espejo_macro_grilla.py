"""ESPEJO-MACRO-10T (2026-11-07, Nico: «medí si hay alguna ventaja en esta lógica así como está, pasando por todo el embudo, con un
barrido de varios parámetros y grillas de entradas»; «primero lo observamos sin ningún agregado»).

La lógica es la de `docs/research/espejo_macro_10t_20261107/REGLA.md` (rama foundation, detector `espejo_macro_10t.py`), portada a
numba para que corra sobre millones de velas, y llevada al embudo SIN filtros condicionales:
  - velas de 10 ticks dentro de la sesión (la campaña declara `"ticks_por_barra": 10`: el embudo arma el contexto así);
  - un impulso ancho y limpio de A a B: ningún cierre devuelve más de `retro` de lo ya recorrido (medido en el cierre, no en la mecha);
  - una vuelta en sentido contrario, igual de limpia, y el evento es el PRIMER cierre que deshace la fracción `f` del ancho W;
  - se opera EN EL SENTIDO DE LA VUELTA (hacia A), entrada a mercado en el primer tick de la vela siguiente.
Lo que la regla fijaba como umbral pasa a ser perilla medida (buena práctica de la grilla: un solo pase de detección con los umbrales
más laxos, la grilla elige): retroceso de la ida y de la vuelta, ancho en viajes de fricción severa, duración de la ida, ritmo de la
vuelta y RTH. La fracción de entrada (25/50/75 %) es un disparo por fracción.
Limitación declarada: detectar con el umbral laxo y filtrar después no es idéntico a detectar con el estricto (un candidato laxo puede
tapar uno estricto posterior en la misma sesión); es la misma aproximación que usan las demás familias de grilla.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import EXCLUIR_EVENTOS, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ESPEJO-MACRO-10T"
INDICADORES = ["ESPEJO-MACRO-10T"]
LINEAS_SOLO_TIEMPO = True
TOPE_BARRAS = 2000                    # velas de 10 ticks (≈ horas en NQ/ES); además, cierre al fin de la sesión
RETRO_LAXO = 0.40                     # el más laxo de la grilla (la regla original usaba 0,20; el último ajuste de Nico, 0,40)
VIAJES_MIN = 10.0                     # ancho mínimo laxo: la mitad que falta vale >= 10 viajes de fricción severa
MIN_IDA, MIN_VUELTA, MAX_IDA = 8, 4, 400
FRACCIONES = (0.25, 0.50, 0.75)
RTH_INI, RTH_FIN = 570, 960           # minutos de NY: 9:30–16:00
VARIABLES = [
    Variable("fraccion", "fi", "grupo", categoria=len(FRACCIONES)),
    Variable("retro_ida", "retro_ida", "le", cortes=(0.20, 0.30, 0.40)),
    Variable("retro_vuelta", "retro_vuelta", "le", cortes=(0.20, 0.30, 0.40)),
    Variable("viajes", "viajes", "ge", cortes=(10.0, 20.0, 40.0), piso=True),
    Variable("dur_ida", "dur_ida", "extremos", cuantiles=3),
    Variable("ritmo", "ritmo", "extremos", cuantiles=3),
    Variable("rth", "rth", "eq_any", categoria=2),
]
EJES_ORDINALES = (1, 2, 3)
STOPS = ("B1", "B10")                 # un tick más allá de B · 10 % de W más allá de B
TPS = ("A", "M75", "2R")              # A (vuelta completa) · 75 % del ancho deshecho · 2R
EJECUCIONES = [(sl, tp) for sl in STOPS for tp in TPS]
BASE = {"fraccion": 1, "retro_ida": 0, "retro_vuelta": 0, "viajes": 1, "dur_ida": 2, "ritmo": 2, "rth": 2, "ejecución": 0}


@njit(cache=False)
def _vuelta(C, iext, k, lado):
    """Peor rebote de la vuelta hasta el cierre k, relativo a lo que ya había deshecho (0 = limpia)."""
    peor = 0.0
    if lado == 1:
        piso = C[iext]
        for j in range(iext + 1, k + 1):
            if C[j] < piso: piso = C[j]
            elif C[iext] - piso > 0:
                r = (C[j] - piso) / (C[iext] - piso)
                if r > peor: peor = r
    else:
        techo = C[iext]
        for j in range(iext + 1, k + 1):
            if C[j] > techo: techo = C[j]
            elif techo - C[iext] > 0:
                r = (techo - C[j]) / (techo - C[iext])
                if r > peor: peor = r
    return peor


@njit(cache=False)
def _candidato(C, i0, n, lado, retro, f, min_w, min_ida, min_vuelta, max_ida):
    """Port de `espejo_macro_10t._candidato` (foundation) con la fracción `f` como parámetro y medidas de retroceso. Sólo usa cierres
    hasta el k que devuelve. Devuelve (k, iext, W, retro_ida, retro_vuelta) o k = -1."""
    # A es el origen real del impulso: el cierre de i0 es el extremo (mínimo si sube, máximo si baja) de las `min_ida` velas previas de
    # la sesión. Sin esto, un inicio a mitad de la subida se completaba antes que la montaña entera y medía un W menor (causal, pero
    # no es la regla).
    for j in range(max(0, i0 - min_ida), i0):
        if (lado == 1 and C[j] < C[i0]) or (lado == -1 and C[j] > C[i0]): return -1, 0, 0.0, 0.0, 0.0
    A = C[i0]; ext = A; iext = i0; peor = 0.0; tope = i0 + max_ida; fin = min(n, i0 + 2 * max_ida)
    for k in range(i0 + 1, fin):
        ck = C[k]
        nuevo = (lado == 1 and ck > ext) or (lado == -1 and ck < ext)
        if nuevo:
            if k > tope: return -1, 0, 0.0, 0.0, 0.0
            if iext < k - 1 and (ext - A) * lado >= min_w * 0.5:
                if lado == 1:
                    m = C[iext + 1]
                    for j in range(iext + 1, k):
                        if C[j] < m: m = C[j]
                    dip = ext - m
                else:
                    m = C[iext + 1]
                    for j in range(iext + 1, k):
                        if C[j] > m: m = C[j]
                    dip = m - ext
                if dip > retro * (ext - A) * lado: return -1, 0, 0.0, 0.0, 0.0
                if dip > peor: peor = dip
            ext = ck; iext = k
            continue
        W = (ext - A) * lado
        if W < min_w or iext - i0 + 1 < min_ida:
            if (A - ck) * lado > 0: return -1, 0, 0.0, 0.0, 0.0
            continue
        if (ext - ck) * lado < f * W:
            if (A - ck) * lado > 0: return -1, 0, 0.0, 0.0, 0.0
            continue
        if k - iext < min_vuelta: return -1, 0, 0.0, 0.0, 0.0
        rv = _vuelta(C, iext, k, lado)
        if rv > retro: return -1, 0, 0.0, 0.0, 0.0
        return k, iext, W, peor / W, rv
    return -1, 0, 0.0, 0.0, 0.0


@njit(cache=False)
def _detectar(C, ses, retro, f, min_w, min_ida, min_vuelta, max_ida):
    """Por sesión. CAUSAL (corrige al detector de foundation, que el certificado atrapó: probaba inicios en orden y saltaba al cierre
    del primer candidato, así que un inicio temprano que se completaba TARDE tapaba candidatos posteriores ya confirmados: el futuro
    decidía qué disparos del pasado existían). Ahora: para cada inicio i, la vela k_i en que se completa (suba o baja, la primera; sólo
    usa cierres <= k_i). Después se recorren en orden de k: se emite el primero y el siguiente tiene que empezar después de ese k.
    Filas (i0, iext, k, lado, W, retro_ida, retro_vuelta)."""
    n = len(C); out = []
    a = 0
    while a < n:
        b = a
        while b < n and ses[b] == ses[a]: b += 1
        Cs = C[a:b]; m = b - a
        K = np.full(m, -1, np.int64); E = np.zeros(m, np.int64); L = np.zeros(m, np.int64)
        Wv = np.zeros(m); RI = np.zeros(m); RV = np.zeros(m)
        for i in range(max(m - min_ida, 0)):
            ku, eu, wu, riu, rvu = _candidato(Cs, i, m, 1, retro, f, min_w, min_ida, min_vuelta, max_ida)
            kd, ed, wd, rid, rvd = _candidato(Cs, i, m, -1, retro, f, min_w, min_ida, min_vuelta, max_ida)
            if ku >= 0 and (kd < 0 or ku <= kd):
                K[i] = ku; E[i] = eu; L[i] = 1; Wv[i] = wu; RI[i] = riu; RV[i] = rvu
            elif kd >= 0:
                K[i] = kd; E[i] = ed; L[i] = -1; Wv[i] = wd; RI[i] = rid; RV[i] = rvd
        orden = np.argsort(K * (m + 1) + np.arange(m), kind="mergesort")
        ultimo = -1
        for q in range(m):
            i = orden[q]
            if K[i] < 0 or i <= ultimo: continue
            out.append((a + i, a + E[i], a + K[i], L[i], Wv[i], RI[i], RV[i])); ultimo = K[i]
        a = b
    return out


def _friccion_ticks(ctx) -> float:
    from edgelab import costos
    inst = str(ctx.get("ejecucion_inst") or ctx.get("sensor") or "NQ").replace("DK:", "")
    try: return float(costos.friccion_rt_ticks(inst, "severo"))
    except Exception: return float(costos.friccion_rt_ticks("NQ", "severo"))


VACIO = ["k", "ses", "lado", "fi", "retro_ida", "retro_vuelta", "viajes", "dur_ida", "ritmo", "rth", "A", "B", "W"]


def disparos(ctx) -> pd.DataFrame:
    tick = float(ctx["tick"]); C = np.asarray(ctx["c"], float) / tick; ses = np.asarray(ctx["ses"], np.int64)
    fr = _friccion_ticks(ctx); min_w = 2.0 * VIAJES_MIN * fr
    partes = []
    for fi, f in enumerate(FRACCIONES):
        F = _detectar(C, ses, RETRO_LAXO, f, min_w, MIN_IDA, MIN_VUELTA, MAX_IDA)
        if not len(F): continue
        F = np.array(F); i0, ie, k = (F[:, j].astype(np.int64) for j in range(3)); lado = F[:, 3].astype(np.int64); W = F[:, 4]
        partes.append(pd.DataFrame(dict(k=k, lado=-lado, fi=fi, retro_ida=F[:, 5], retro_vuelta=F[:, 6], viajes=W / 2.0 / fr,
                                        dur_ida=(ie - i0 + 1).astype(float), ritmo=(k - ie) / np.maximum(ie - i0, 1) / f,
                                        A=C[i0] * tick, B=C[ie] * tick, W=W * tick)))
    if not partes: return pd.DataFrame(columns=VACIO)
    D = pd.concat(partes, ignore_index=True)
    from edgelab.research.regimen_sesion import minuto_ny
    mny = minuto_ny(np.asarray(ctx["t"], float)[D.k.to_numpy()].astype(np.int64))
    D["rth"] = ((mny >= RTH_INI) & (mny < RTH_FIN)).astype(np.int64); D["ses"] = ses[D.k.to_numpy()]
    return D.sort_values(["k", "fi"], kind="stable", ignore_index=True)


def niveles(r, ej, ctx):
    """9 valores. `lado` del disparo ya es el de la operación (sentido de la vuelta, hacia A). Entrada a mercado en el primer tick de
    la vela siguiente (límite 2, start k). Stop más allá de B; objetivo A, 75 % del ancho deshecho, o 2R."""
    sl_, tp_ = ej; k = int(r["k"]); c = ctx["c"]; ses = ctx["ses"]; tick = float(ctx["tick"]); s = int(r["lado"])
    if k + 1 >= len(c) or ses[k + 1] != ses[k]: return None
    e = float(c[k]); B = float(r["B"]); A = float(r["A"]); W = float(r["W"])
    st = B - s * (tick if sl_ == "B1" else max(tick, 0.10 * W))
    st = np.ceil(st / tick) * tick if s == -1 else np.floor(st / tick) * tick
    R = (e - st) * s
    if R < tick: return None
    tp = A if tp_ == "A" else (B + s * 0.75 * W if tp_ == "M75" else e + s * 2.0 * R)
    tp = np.round(tp / tick) * tick
    if (tp - e) * s < tick: return None
    return k, 2, s, e, st, tp, 0, (0 if s == 1 else 1), 0.0
