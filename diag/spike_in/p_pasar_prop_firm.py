# -*- coding: utf-8 -*-
"""P(pasar) por tamaño de cuenta y contratos — el filtro de operabilidad correcto.

## Por qué E[días] NO es el filtro

LucidFlex **no tiene límite de tiempo**. Con horizonte libre el profit target no
ata: ata el PISO. La cantidad que decide es

    P(alcanzar +target antes de −MLL)

con la distribución empírica de trades, no el tiempo esperado hasta el objetivo.

## Y por qué los contratos no son neutros

Con más contratos ambos umbrales se acercan medidos EN TRADES: la partida se
resuelve en menos jugadas y el azar domina sobre la deriva. Los contratos no
compran margen — **cambian probabilidad de pasar por tiempo hasta pasar**.

## El insumo es medido, no supuesto

`SD` por trade = mediana de las 40 geometrías sobre `por_geom_nulo.json`
(el mismo artefacto del que salen `SE`, `DEFF` y `M_eff` del MDE) = **8,77 ticks**.

Modelo: ruina del jugador con deriva, aproximación browniana
`P = (1 − e^(−θb)) / (1 − e^(−θ(a+b)))` con `θ = 2μ/σ²`.
Es aproximación: con barreras P/N discretas y cientos de trades es razonable,
pero no es exacta. Se declara.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
TICK_USD = 6.25          # 6E: 0,00005 × 125.000

#: (target, MLL) en dólares — verificado en support.lucidtrading.com (2026-04-15)
CUENTAS = {"25K": (1250.0, 1000.0), "50K": (3000.0, 2000.0),
           "100K": (6000.0, 3000.0), "150K": (9000.0, 4500.0)}


def sd_por_trade():
    p = os.path.join(AQUI, "por_geom_nulo.json")
    tot = json.load(open(p, encoding="utf-8"))
    sds = []
    for g in tot:
        fe = sorted(tot[g])
        n = sum(tot[g][f][0] for f in fe)
        s = sum(tot[g][f][1] for f in fe)
        sq = sum(tot[g][f][2] for f in fe)
        mu = s / n
        sds.append(math.sqrt(sq / n - mu * mu))
    return float(np.median(sds))


def p_pasar(a, b, mu, sd):
    """P(alcanzar +a antes de −b) con deriva mu y desvío sd, en ticks."""
    if abs(mu) < 1e-12:
        return b / (a + b)
    th = 2 * mu / (sd * sd)
    try:
        return (1 - math.exp(-th * b)) / (1 - math.exp(-th * (a + b)))
    except OverflowError:
        return 1.0


def main():
    SD = sd_por_trade()
    print("SD por trade (mediana de las 40 geometrías, MEDIDA): %.2f ticks" % SD)
    print()
    print("=== ratio target/MLL: invariante a CONTRATOS, no a tamaño de cuenta ===")
    for k, (tg, ml) in CUENTAS.items():
        print("  %-5s target=%5.0f t  MLL=%5.0f t  ratio=%.2f"
              % (k, tg / TICK_USD, ml / TICK_USD, tg / ml))
    print()
    for e in (0.39, 1.00, 2.00):
        print("=== P(pasar) con edge = %.2f ticks netos/trade ===" % e)
        print("  %-6s" % "cuenta", end="")
        for c in (1, 2, 3, 4):
            print(" %9s" % ("c=%d" % c), end="")
        print()
        for k, (tg, ml) in CUENTAS.items():
            print("  %-6s" % k, end="")
            for c in (1, 2, 3, 4):
                a, b = tg / TICK_USD / c, ml / TICK_USD / c
                print(" %8.1f%%" % (100 * p_pasar(a, b, e, SD)), end="")
            print()
        print()
    print("LECTURA: el ratio NO manda. Manda el tamaño ABSOLUTO en unidades de SD.")
    print("La 25K tiene el mejor ratio (1,25) y la PEOR P(pasar): 200/160 ticks son")
    print("~20 SD de margen y el ruido resuelve antes de que la deriva se exprese.")
    print("Y P(pasar) cae monótonamente al escalar contratos, en TODAS las celdas.")


if __name__ == "__main__":
    main()
