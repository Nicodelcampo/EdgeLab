"""Motor de fills pasivos tick a tick (2026-11-10, `PLAN_OPERABLE_Y_CUERDAS.md` §4.1): una orden límite en el libro, con máquina de
estados causal, y la operación que sigue al fill. Lo pedía la regla del 2026-10-21 («fills pasivos sólo por replay tick a tick con
máquina de estados causal»); el informe k32 midió +0,64 ticks/op de optimismo del modelo «tocó el precio» en ES, pero el motor
nunca entró al repo.

Estados: ESPERA (la orden todavía no está: el precio no se alejó lo suficiente) → EN_LIBRO (orden límite en `limite`) → LLENA →
CERRADA (objetivo, stop o tiempo) | VENCIDA (la orden nunca se llenó dentro de su vida).
Modelos de fill (se informan los dos; las decisiones usan el conservador):
  "toca"       se llena cuando un trade imprime en el límite (optimista: supone primera posición en la cola)
  "atraviesa"  se llena sólo cuando un trade imprime AL MENOS un tick más allá del límite (conservador: la cola se consumió)
Después del fill: stop y objetivo a distancias fijas; si un mismo tick cruza los dos, gana el stop (adverso); al vencer `t_max_s` se
sale al último precio. R bruto en unidades del stop; el neto resta los costos aparte (`edgelab/costos.py`).
"""
from __future__ import annotations

import numpy as np

NS = 1_000_000_000
MODELOS = ("toca", "atraviesa")


def operar(ts, px, j_activa: int, j_vence: int, limite: float, lado: int, stop: float, objetivo: float, t_max_s: float,
           tick: float, modelo: str = "atraviesa") -> dict:
    """`lado` = +1 compra límite (el precio baja al límite y se espera rebote hacia arriba), −1 venta límite.
    La orden está en el libro desde `j_activa` (incluido) hasta `j_vence` (excluido). Índices absolutos en `ts`/`px`."""
    if modelo not in MODELOS: raise ValueError(f"modelo {modelo}: usar {MODELOS}")
    umbral = limite - lado * (tick if modelo == "atraviesa" else 0.0)       # compra: px ≤ límite (toca) o ≤ límite − tick (atraviesa)
    seg = px[j_activa:j_vence]
    hit = np.flatnonzero(lado * (seg - umbral) <= 1e-12)
    if not hit.size: return dict(llena=False, r_bruto=0.0, salida="vencida", t_fill_s=np.nan, t_dur_s=np.nan)
    jf = j_activa + int(hit[0]); entrada = limite                            # el fill es al precio límite (sin mejora)
    j_fin = int(np.searchsorted(ts, ts[jf] + int(t_max_s * NS), side="right"))
    post = px[jf + 1:j_fin]                                                  # el tick del fill no cuenta para stop/objetivo
    m = lado * (post - entrada)
    s = np.flatnonzero(m <= -stop); g = np.flatnonzero(m >= objetivo)
    if s.size and (not g.size or s[0] <= g[0]): r, sal, k = -1.0, "stop", s[0]
    elif g.size: r, sal, k = objetivo / stop, "objetivo", g[0]
    else:
        k = len(post) - 1
        r, sal = (float(m[-1]) / stop, "tiempo") if len(post) else (0.0, "tiempo")
    jx = jf + 1 + k if len(post) else jf
    return dict(llena=True, r_bruto=float(r), salida=sal, t_fill_s=float((ts[jf] - ts[j_activa]) / NS), t_dur_s=float((ts[jx] - ts[jf]) / NS))
