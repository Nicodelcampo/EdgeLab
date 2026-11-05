"""MODELO-ASIA (2026-11-01): ruptura del rango 18:00–20:00 ET con filtro de ANCHO ABSOLUTO 100–300 puntos y sesgo EMA20 de 5 minutos
leído a las 20:15 ET. La operación queda abierta hasta la sesión de Nueva York.

Fuente: "Modelo Asia" de @alphatraders_latam (post De2e_Mns9UG), traído por Nico. Pre-registro:
docs/research/modelo_asia_20261101/SPEC_MODELO_ASIA.md.
Parentesco declarado: ASIA_BOS_GAPS_NQ ya midió la caja 18:00–20:00 con BOS y el corredor EMA20/EMA60, con ancho relativo
(H/ATR) y salidas de a lo sumo 240 velas. Esta familia mide lo que aquélla no midió:
  - el ancho en PUNTOS;
  - la EMA20 de 5 minutos a las 20:15;
  - la tenencia hasta NY (`TOPE_BARRAS`).

Construcción (causal; minutos NY de CIERRE de vela; `rel` = minutos desde las 18:00 ET, la apertura de la sesión CME):
- Rango: máximo y mínimo de las velas que cierran en rel (0, 120]. Se exige al menos el 80 % de las velas.
- Sesgo: a las 20:15 (rel 135), signo de (cierre de la vela de 5 min − EMA20 de los cierres de 5 min). La EMA es continua entre
  sesiones, sólo con cierres ya ocurridos.
- Disparo, para cada lado y cada gatillo: el PRIMER cierre fuera del rango después de las 20:15 y hasta las 09:30 ET (rel 930).
  Gatillo 0 = cierre de vela de 1 min; gatillo 1 = cierre de vela de 5 min.
  Puede haber un disparo largo y uno corto en la misma sesión. La regla literal toma sólo el del lado del sesgo (`sesgo` = 1).
- Entrada: primer tick de la vela siguiente (limite = 2), nunca en el extremo.
- Stop: borde OPUESTO del rango ∓ 1 tick (literal) o la MITAD del rango.
- Salida, por par (objetivo, hora de cierre forzado):
  - 1R y 2R, los dos con cierre a las 16:00 ET;
  - ABIERTO, con cierre a las 09:30, 12:00 o 16:00 ET.
  Las salidas por hora usan la salida por línea de `areas_expansion.simular_cierre_linea`. El +500 del post es un ejemplo, no una
  regla: casi nunca se alcanza en una noche y duplicaba la ejecución ABIERTO-16:00 (el preflight la marcó como perilla muerta).
Celda literal: gatillo 0 · ancho [100, 300] pts · sesgo a favor · (OPUESTO, ABIERTO, 16:00). Las otras dos lecturas de "puntos"
(ticks de NQ y points de MT5) son las celdas de `LECTURAS`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import rango_ruptura as RR
from edgelab.research.grilla_generica import Variable
from edgelab.research.regimen_sesion import minuto_ny

NOMBRE = "MODELO-ASIA"
INDICADORES = ["MODELO-ASIA"]
INI_REL, FIN_REL, SESGO_REL, LIMITE_REL = 0, 120, 135, 930          # 18:00, 20:00, 20:15 y 09:30 ET en minutos desde las 18:00
# Ancho del rango en puntos del índice. "100–300 puntos" tiene tres lecturas posibles y las tres se miden (v2, 2026-11-01):
#   100–300 puntos del índice (literal; ~5–15 % de los días en 2025–26), 100–300 ticks de NQ = 25–75 puntos (zona media de la
#   distribución) y 100–300 "points" de MT5 con paso 0,1 = 10–30 puntos (aproximado por el nivel 10–25).
ANCHO_PTS = (10.0, 25.0, 75.25, 100.0, 300.25)                      # <10 | 10–25 | 25–75 | 75–100 | 100–300 | >300 (inclusive arriba)
SALIDAS = (570, 720, 960)                                           # 09:30, 12:00 y 16:00 ET (minutos NY)
TOPE_BARRAS = 1300                                                  # 20:15 → 16:00 del día siguiente = 1185 velas
PREFLIGHT_T0_S = 1_760_047_200                                      # preflight: bloques de 23 h desde las 18:00 ET (2025-10-09 22:00 UTC)
VARIABLES = [
    Variable("gatillo", "gat", "grupo", categoria=2),               # 0: cierre M1 · 1: cierre M5
    Variable("ancho_pts", "ancho", "eq_any", cortes=ANCHO_PTS),     # 0..5 los tramos de ANCHO_PTS · 6: cualquiera
    Variable("sesgo_ema", "sesgo", "eq_any", categoria=2),          # 0: contra la EMA20 M5 · 1: a favor (literal) · 2: cualquiera
]
EJES_ORDINALES = (1,)
EJECUCIONES = [(sl, tp, sal) for sl in ("OPUESTO", "MID")
               for tp, sal in (("1R", 960), ("2R", 960), ("ABIERTO", 570), ("ABIERTO", 720), ("ABIERTO", 960))]
BASE = {"gatillo": 0, "ancho_pts": 4, "sesgo_ema": 1, "ejecución": 4}
CELDA_LITERAL = [0, 4, 1, 4]                                        # 100–300 puntos del índice
LECTURAS = {"puntos_indice": CELDA_LITERAL, "ticks_nq": [0, 2, 1, 4], "points_mt5": [0, 1, 1, 4]}


def ema_m5(c: np.ndarray, m: np.ndarray, n: int = 20) -> np.ndarray:
    """EMA de los cierres de 5 minutos (velas que cierran en un múltiplo de 5), as-of cada vela M1. NaN hasta tener `n` cierres."""
    out = np.full(len(c), np.nan); a = 2.0 / (n + 1); e = np.nan; k = 0
    for i in range(len(c)):
        if m[i] % 5 == 0:
            k += 1; e = c[i] if k == 1 else a * c[i] + (1 - a) * e
        if k >= n: out[i] = e
    return out


def disparos(ctx: dict) -> pd.DataFrame:
    h, l, c = (np.asarray(ctx[x], float) for x in ("h", "l", "c"))
    ses = np.asarray(ctx["ses"], np.int64); m = minuto_ny(np.asarray(ctx["t"], np.int64)); rel = (m - 1080) % 1440
    ema = ema_m5(c, m); filas = []
    for sg in np.unique(ses):
        idx = np.flatnonzero(ses == sg); rr = rel[idx]
        rg = idx[(rr > INI_REL) & (rr <= FIN_REL)]
        if len(rg) < 0.8 * (FIN_REL - INI_REL): continue
        hi, lo = h[rg].max(), l[rg].min()
        if not hi > lo: continue
        b = idx[(rr == SESGO_REL) & (idx > rg[-1])]                         # orden de TIEMPO: sesgo después del rango
        if not len(b) or not np.isfinite(ema[b[0]]): continue
        sesgo = int(np.sign(c[b[0]] - ema[b[0]]))
        post = idx[(rr > SESGO_REL) & (rr <= LIMITE_REL) & (idx > b[0])]     # y la ruptura después del sesgo
        for gat, mask in ((0, np.ones(len(post), bool)), (1, m[post] % 5 == 0)):
            cand = post[mask]
            for lado in (1, -1):
                fuera = cand[(c[cand] > hi) if lado == 1 else (c[cand] < lo)]
                if not len(fuera): continue
                k = int(fuera[0])
                filas.append((k, int(sg), lado, hi, lo, (hi + lo) / 2, hi - lo, (1 if lado == sesgo else 0) if sesgo else -1, gat))
    return pd.DataFrame(filas, columns=["k", "ses", "lado", "hi", "lo", "mid", "ancho", "sesgo", "gat"])


def lineas_salida(ctx) -> np.ndarray:
    """Dos filas por hora de cierre (compra, venta): ±inf en la ventana [hora, hora + 120 min) ⇒ sale al primer cierre ahí."""
    m = minuto_ny(np.asarray(ctx["t"], np.int64)); filas = []
    for s in SALIDAS:
        f = (m >= s) & (m < s + 120); filas += [np.where(f, np.inf, np.nan), np.where(f, -np.inf, np.nan)]
    return np.vstack(filas)


def _lote(D, ej, ctx):
    tick = float(ctx["tick"]); c = np.asarray(ctx["c"], float)
    k = D["k"].to_numpy(np.int64); s = D["lado"].to_numpy(np.int64); e = c[k]
    ref = D["mid"].to_numpy(float) if ej[0] == "MID" else np.where(s == 1, D["lo"].to_numpy(float), D["hi"].to_numpy(float))
    st = np.where(s == 1, np.floor(ref / tick) * tick - tick, np.ceil(ref / tick) * tick + tick)
    R = (e - st) * s; ok = R >= tick
    if ej[1] in ("1R", "2R"): tp = np.round((e + s * (1.0 if ej[1] == "1R" else 2.0) * R) / tick) * tick
    else: tp = e + s * 1e6                                               # ABIERTO: objetivo inalcanzable, sale por hora o stop
    kl = 2 * SALIDAS.index(ej[2]) + (s == -1).astype(np.int64)
    return ok, k, s, e, st, tp, kl


def niveles(d, ej: tuple, ctx: dict):
    return RR.niveles_con(_lote, d, ej, ctx)


def niveles_lote(D: pd.DataFrame, ej: tuple, ctx: dict) -> np.ndarray:
    return RR.niveles_lote_con(_lote, D, ej, ctx)
