"""ESPEJO-ZONAS (2026-11-07, pedido de Nico): el espejo de ESPEJO-MACRO-10T clasificado por las ZONAS DE OTROS INDICADORES que encontró
la ida, en lugar de pivotes. Hermana de ESPEJO-PICOS: misma base (detector causal con topes en tiempo de `espejo_macro_tiempo`, ancho
mínimo laxo de 5 viajes, retrocesos fijos en el laxo), mismas ejecuciones y las mismas preguntas sobre la ida.

Zonas: almacenes precalculados de indicadores PASS por instrumento (`prerange_zonas.cargar_zonas`, que resuelve HFT por trimestre,
AVZP2 en `t_decidida_ns`, AVZG en su zona base de YM y el holdout sellado). Disponibilidad: la zona entra en la primera vela que cierra
en o después de su instante (`t_ns`); se usa sólo de esa vela en adelante. LUX-IMB queda afuera: se calcula sobre velas M1 y acá las
velas son de 10 ticks (con otra vela es otro indicador).

Todo en el espacio «techo» (si la ida sube, precios tal cual; si baja, negados): A = mecha de la vela de inicio, techo = extremo de la
ida por mechas, W = techo − A. Una zona cuenta si su punto medio está más allá de A. Borde cercano = el primero que alcanza la ida.
  - VIVA: desde que existe hasta A, ningún cierre pasó su borde lejano en la dirección del impulso (como el pico «sin romper»). Las
    nacidas durante la ida se cuentan sin esa condición: son la huella del propio impulso.
  - TOMADA por la ida: el techo llegó a su borde cercano. Posición = punto medio en fracción de W (0 inicio … 1 extremo).
  - MÁS ALLÁ CERCANA: viva, no alcanzada, con el borde cercano a <= 0,25·W del techo (liquidez que queda justo después del impulso).
Antigüedad (perilla de grupo, bandas disjuntas salvo «todas»): recientes (<= 30 min antes de A) · viejas (> 30 min antes de A, misma
sesión) · nacidas en la ida (entre A y el extremo) · todas. Las zonas de otra sesión no se usan (precios de otro contrato tras un roll).
Todo se mide con datos <= k (la vela de decisión).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from edgelab.research import espejo_macro_grilla as P, espejo_macro_tiempo as TI, prerange_zonas as PZ
from edgelab.research.espejo_picos import EJECUCIONES, STOPS, TPS, niveles  # noqa: F401
from edgelab.research.grilla_generica import Variable
from edgelab.research.intento_fallido import EXCLUIR_EVENTOS, lineas_salida  # noqa: F401

try:
    from numba import njit
except ImportError:
    def njit(*a, **k):
        return (lambda f: f) if not (a and callable(a[0])) else a[0]

NOMBRE = "ESPEJO-ZONAS"
INDICADORES = ["ESPEJO-MACRO-10T", "HFTZones2", "HFTZonesNQ", "aVolZonePOI2", "aVolClusterPOI", "BigTrap2"]
LINEAS_SOLO_TIEMPO = True
TOPE_BARRAS = P.TOPE_BARRAS
VIAJES_LAXO = 5.0
EDAD_RECIENTE_S = 1800.0              # 30 min antes de A
CERCA_W = 0.25                        # «más allá cercana»: borde cercano a <= 0,25·W del techo
IND_POR_INST = {"NQ": ("AVZP2", "AVCL", "BT2", "HFT2", "HFTNQ"),
                "ES": ("AVZP2", "AVCL", "BT2", "HFT2", "HFTNQ"),
                "YM": ("AVZG", "BT2", "HFT2", "HFTNQ")}           # almacenes existentes (edgelab-zonas-u1, edgelab-zonas-hft); GC no tiene
N_IND = 5                             # tope; en YM el quinto nivel queda vacío
BANDAS = 4                            # 0 recientes · 1 viejas · 2 nacidas en la ida · 3 todas
VARIABLES = [
    Variable("fraccion", "fi", "grupo", categoria=len(P.FRACCIONES)),
    Variable("viajes", "viajes", "ge", cortes=(5.0, 10.0, 20.0), piso=True),
    Variable("rth", "rth", "eq_any", categoria=2),
    Variable("indicador", "zi_ind", "grupo", categoria=N_IND),
    Variable("antiguedad", "ai", "grupo", categoria=BANDAS),
    Variable("n_tomadas", "n_tom", "eq_any", cortes=(0.5, 2.5)),  # 0 · 1–2 · 3+ · cualquiera
    Variable("posicion", "pos", "eq_any", categoria=4),           # 0 ninguna · 1 inicio · 2 medio · 3 final
    Variable("mas_alla", "mas", "eq_any", categoria=2),           # 0 sin zona cercana más allá · 1 con
]
EJES_ORDINALES = ()
BASE = {"fraccion": 1, "viajes": 1, "rth": 2, "indicador": 0, "antiguedad": 3, "n_tomadas": 3, "posicion": 4, "mas_alla": 2,
        "ejecución": 0}


@njit(cache=False)
def _primer_cruce(c, zi, umbral, arriba):
    """Para cada zona z: primera vela j > zi[z] con c[j] > umbral[z] (arriba) o c[j] < umbral[z] (abajo); n si no hay.
    Offline con «siguiente vivo» (unión-búsqueda): se recorren los umbrales de menor a mayor exigencia y se borran las velas que ya
    no los cruzan. O((n + Z)·α)."""
    n = len(c); Z = len(zi); out = np.full(Z, n, np.int64)
    if Z == 0: return out
    s = 1.0 if arriba else -1.0
    oc = np.argsort(s * c)                                          # velas de la que menos cruza a la que más
    oz = np.argsort(s * umbral)
    nxt = np.arange(n + 1)
    p = 0
    for q in range(Z):
        z = oz[q]; u = s * umbral[z]
        while p < n and s * c[oc[p]] <= u:                          # esta vela no cruza este umbral ni ninguno mayor
            nxt[oc[p]] = oc[p] + 1; p += 1
        j = zi[z] + 1
        r = j                                                       # buscar el primer índice no borrado >= j
        while r < n and nxt[r] != r: r = nxt[r]
        while j < r:                                                # compresión de caminos
            t = nxt[j]; nxt[j] = r; j = t
        out[z] = r if r < n else n
    return out


@njit(cache=False)
def _clasificar(zi, near, far, cruce, tz, ses_z, i0, ie, ini, A, techo, ses0, t0, banda, edad_s, cerca_w):
    """Zonas en espacio techo (near <= far) ordenadas por zi; `ini` = primera vela de la sesión de A. Devuelve (n_tomadas, pos_media,
    n_mas_alla)."""
    W = techo - A; n_t = 0; spos = 0.0; n_m = 0
    if W <= 0: return 0, -1.0, 0
    hi = np.searchsorted(zi, ie, side="right")
    lo = np.searchsorted(zi, ini, side="left")
    for z in range(lo, hi):
        if ses_z[z] != ses0: continue
        mid = 0.5 * (near[z] + far[z])
        if mid <= A: continue
        ida = zi[z] >= i0
        if ida:
            if banda == 0 or banda == 1: continue
        else:
            edad = t0 - tz[z]
            if banda == 2: continue
            if banda == 0 and edad > edad_s: continue
            if banda == 1 and edad <= edad_s: continue
            if cruce[z] < i0: continue                              # ya cruzada antes de A: no está viva
        if near[z] <= techo:
            n_t += 1; x = (mid - A) / W; spos += 1.0 if x > 1.0 else x
        elif near[z] - techo <= cerca_w * W:
            n_m += 1
    return n_t, (spos / n_t if n_t > 0 else -1.0), n_m


def _zonas(ctx, ind, T, C, tick, ses):
    """(zi, lo, hi en ticks, t de disponibilidad en s, sesión, primer cruce hacia arriba de hi, primer cruce hacia abajo de lo)."""
    Z = PZ.cargar_zonas(ctx, ind)
    tz = Z.t_ns.to_numpy(np.int64) / 1e9
    ok = (tz >= T[0]) & (tz <= T[-1]); tz = tz[ok]
    a = Z.lo.to_numpy(float)[ok] / tick; b = Z.hi.to_numpy(float)[ok] / tick
    zi = np.searchsorted(T, tz, side="left").astype(np.int64)
    o = np.argsort(zi, kind="stable"); zi, tz, lo, hi = zi[o], tz[o], np.minimum(a, b)[o], np.maximum(a, b)[o]
    return zi, lo, hi, tz, ses[zi], _primer_cruce(C, zi, hi, True), _primer_cruce(C, zi, lo, False)


def _inds(ctx):
    sensor = ctx.get("sensor") or os.environ.get("SENSOR")
    if sensor: return IND_POR_INST[sensor], ctx
    if "zonas" in ctx: return tuple(ctx["zonas"]), ctx
    return ("A", "B"), dict(ctx, zonas={"A": _control(ctx, 15), "B": _control(ctx, 22)})          # sólo tests y preflight


def _control(ctx, paso):
    """SOLO preflight y tests: zona de 2 ticks cada `paso` velas, disponible al cierre exacto de su vela (como `prerange_zonas._control`,
    sin truncar el tiempo a segundos: en velas de 10 ticks eso la adelantaría a una vela anterior)."""
    k = np.arange(paso, len(ctx["c"]), paso); px = np.asarray(ctx["c"], float)[k] + (k % 7 - 3) * ctx["tick"] * 8
    t = np.asarray(ctx["t"], float)[k]
    return pd.DataFrame(dict(t_ns=np.ceil(t * 1e9).astype(np.int64), lo=px, hi=px + ctx["tick"]))


def disparos(ctx) -> pd.DataFrame:
    tick = float(ctx["tick"]); C = np.asarray(ctx["c"], float) / tick; ses = np.asarray(ctx["ses"], np.int64)
    h = np.asarray(ctx["h"], float) / tick; l = np.asarray(ctx["l"], float) / tick; T = np.asarray(ctx["t"], float)
    fr = P._friccion_ticks(ctx); min_w = 2.0 * VIAJES_LAXO * fr
    inds, ctx = _inds(ctx)
    zs = [_zonas(ctx, i, T, C, tick, ses) for i in inds]
    cambio = np.r_[True, ses[1:] != ses[:-1]]; ini_ses = np.maximum.accumulate(np.where(cambio, np.arange(len(ses)), 0))
    filas = []
    for fi, f in enumerate(P.FRACCIONES):
        for (i0, ie, k, lado, W, ri, rv) in TI._detectar_t(C, T, ses, P.RETRO_LAXO, f, min_w, P.MIN_IDA, P.MIN_VUELTA,
                                                           TI.MAX_SEG_IDA, TI.MAX_SEG_TOTAL):
            i0, ie, k, lado = int(i0), int(ie), int(k), int(lado)
            if lado == 1: A = l[i0]; techo = h[i0:ie + 1].max()
            else: A = -h[i0]; techo = (-l[i0:ie + 1]).max()
            for ii, (zi, lo, hi, tz, sz, cu, cd) in enumerate(zs):
                near, far, cruce = (lo, hi, cu) if lado == 1 else (-hi, -lo, cd)
                for ai in range(BANDAS):
                    n_t, pos, n_m = _clasificar(zi, near, far, cruce, tz, sz, i0, ie, ini_ses[i0], A, techo, ses[i0], T[i0], ai, EDAD_RECIENTE_S, CERCA_W)
                    filas.append((k, -lado, fi, W / 2.0 / fr, ii, ai, n_t,
                                  0 if n_t == 0 else (1 if pos < 1 / 3 else (2 if pos < 2 / 3 else 3)),
                                  1 if n_m > 0 else 0, C[i0] * tick, C[ie] * tick, W * tick))
    cols = ["k", "lado", "fi", "viajes", "zi_ind", "ai", "n_tom", "pos", "mas", "A", "B", "W"]
    if not filas: return pd.DataFrame(columns=cols + ["rth", "ses"])
    D = pd.DataFrame(filas, columns=cols)
    from edgelab.research.regimen_sesion import minuto_ny
    mny = minuto_ny(T[D.k.to_numpy()].astype(np.int64))
    D["rth"] = ((mny >= P.RTH_INI) & (mny < P.RTH_FIN)).astype(np.int64); D["ses"] = ses[D.k.to_numpy()]
    return D.sort_values(["k", "fi", "zi_ind", "ai"], kind="stable", ignore_index=True)
