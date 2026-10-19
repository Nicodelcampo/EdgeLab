#!/usr/bin/env python3
"""Exposicion MEDIDA de las expresiones de precio de los .cs que `ulp_exposure.py` no cubre (triaje 2026-10-14, ulp_sweep).

`ulp_exposure.py` mide kernels completos. Esta herramienta mide las FORMAS de expresion de las 12 lineas triajadas por lectura:
  A. umbral por aritmetica       : hit = lo <= (entry - n*tick)            (aVolClusterPOISim hitSl/hitTp, t.Sl/t.Tp)
  B. umbral proporcional         : retro >= pct/100 * max(upper-lower,tick) (HFTZonesNQPureV4, ciclo de vida de dibujo)
  C. margen de medio tick         : key + 0.5*tick >= low                   (aVolZonePOI.cs)
  D. bucle acumulativo            : for (p = low; p <= high + 0.1*tick; p += tick)  (aVolZonePOI.cs)
  E. grilla llevada sin aritmetica: hi >= z.Upper con ambos del feed         (HFTZonesNQPureV4 touches)
Una decision esta EXPUESTA si el resultado en double difiere del resultado en indices ENTEROS de tick (la verdad).
Uso: python tools/ulp_exposure_expr.py [--out docs/research/ulp_exposure_expr_20261014.json]
"""
from __future__ import annotations

import argparse
import json
import math

TICKS = {"0.25 (ES/NQ/MES/MNQ)": 0.25, "0.1 (GC/MGC)": 0.1, "0.5 (YM-like)": 0.5, "1.0 (YM/RTY)": 1.0, "0.01 (CL)": 0.01, "0.0001 (6B)": 0.0001, "0.00005 (6E)": 0.00005, "5e-7 (6J)": 5e-7}


def grid(tick, n0, n1):
    return [(i, i * tick) for i in range(n0, n1)]            # (indice entero, precio como double del kernel Python)


def feed_double(i, tick):
    return float(repr(round(i * tick, 10)))                   # sustituto del decimal parseado del feed de NT8


def A(tick, n0=1000, n1=1300, ns=range(1, 41)):
    bad = tot = 0
    for ie, _ in grid(tick, n0, n1):
        entry = feed_double(ie, tick)
        for n in ns:
            sl = entry - n * tick                              # aritmetica en double
            for d in (-1, 0, 1):
                lo = feed_double(ie - n + d, tick)
                truth = (ie - n + d) <= (ie - n)               # enteros
                tot += 1; bad += (lo <= sl) != truth
    return bad, tot


def B(tick, n0=1000, n1=1200, pcts=(30, 40, 50, 60, 70)):
    bad = tot = 0
    for lw in range(n0, n1, 7):
        for h in range(1, 60):
            lower, upper = feed_double(lw, tick), feed_double(lw + h, tick)
            alt = max(upper - lower, tick)
            for r in range(0, h + 1):
                end = feed_double(lw + r, tick)
                retro = upper - end
                for p in pcts:
                    thr_i = (p / 100.0) * h                    # umbral exacto en ticks (h es entero)
                    truth = (h - r) >= thr_i - 1e-12 if False else ((h - r) * 100 >= p * h)   # entero puro
                    tot += 1; bad += (retro >= p / 100.0 * alt) != truth
    return bad, tot


def C(tick, n0=1000, n1=1200):
    bad = tot = 0
    for ie in range(n0, n1):
        key = feed_double(ie, tick)
        for d in (-2, -1, 0, 1, 2):
            low = feed_double(ie + d, tick)
            truth = ie + 0.5 >= ie + d                          # medio tick: nunca empata
            tot += 1; bad += (key + 0.5 * tick >= low) != truth
    return bad, tot


def D(tick, n0=1000, span=40):
    bad = tot = 0
    for ie in range(n0, n0 + 200):
        low = feed_double(ie, tick); high = feed_double(ie + span, tick)
        p = low; k = 0
        while p <= high + tick * 0.1:
            k += 1; p += tick
        tot += 1; bad += k != span + 1                          # esperado: span+1 iteraciones
    return bad, tot


def E(tick, n0=1000, n1=1300):
    bad = tot = 0
    for ie in range(n0, n1):
        up = feed_double(ie, tick)
        for d in (-1, 0, 1):
            hi = feed_double(ie + d, tick)
            tot += 1; bad += (hi >= up) != ((ie + d) >= ie)
    return bad, tot


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=None); a = ap.parse_args()
    res = {}
    for name, tick in TICKS.items():
        res[name] = {}
        for lab, fn in (("A_umbral_aritmetico", A), ("B_umbral_proporcional", B), ("C_margen_medio_tick", C), ("D_bucle_acumulativo", D), ("E_grilla_sin_aritmetica", E)):
            bad, tot = fn(tick)
            res[name][lab] = {"decisiones": tot, "cambian_de_lado": bad, "tasa": bad / tot if tot else 0.0}
    print(json.dumps(res, indent=1))
    if a.out:
        open(a.out, "w", encoding="utf-8").write(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
