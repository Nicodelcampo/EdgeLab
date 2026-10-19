# -*- coding: utf-8 -*-
"""UNIDAD 1 -- los dos extremos. Si alguno falla, el turno termina acá.

1A. m = 0 debe reproducir el nulo BIT A BIT. La comparación es contra el
    `procesar_dia` REAL importado de `tools/atlas_asimetrico.py`, ancla por
    ancla y campo por campo -- no contra el JSON agregado, que sólo tiene S/T
    por día y no detectaría una compensación entre anclas.

1B. m = M_forzado = P + max|MAE observado| debe llevar p_favorable a 1,0.
    A esa magnitud el resultado está forzado ARITMÉTICAMENTE: si el pipeline
    no lo devuelve, el defecto es del camino de inyección, no de la señal.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from spike_in import (A, CFG, DATA_DIR, dias_del_atlas_sellado,  # noqa: E402
                      procesar_dia_spike)

N_DIAS_CONTROL = 6
RONDAS_CONTROL = (0, 1)


def _comparar(fa, fb):
    """Diferencias campo a campo entre dos listas de filas de anclas."""
    if len(fa) != len(fb):
        return ["n de anclas: %d vs %d" % (len(fa), len(fb))]
    difs = []
    for i, (x, y) in enumerate(zip(fa, fb)):
        comunes = set(x) & set(y)
        faltan = (set(x) ^ set(y)) - {"signo_spike", "direccion"}
        if faltan:
            difs.append("ancla %d: campos distintos %s" % (i, sorted(faltan)))
        for k in sorted(comunes):
            if k in ("signo_spike",):
                continue
            if x[k] != y[k]:
                difs.append("ancla %d campo %s: %r vs %r" % (i, k, x[k], y[k]))
                if len(difs) > 12:
                    return difs
    return difs


def unidad_1a(dias):
    print("=" * 74)
    print("1A -- CONTROL m=0: mi camino vs `atlas_asimetrico.procesar_dia` REAL")
    print("=" * 74)
    print("comparación ancla por ancla y campo por campo (no S/T agregado)")
    total_anclas = 0
    t0 = time.time()
    for (archivo, contrato, fecha) in dias:
        for ronda in RONDAS_CONTROL:
            real = A.procesar_dia((archivo, contrato, fecha, DATA_DIR, ronda))
            mio = procesar_dia_spike((archivo, contrato, fecha, DATA_DIR, ronda, 0, "A"))
            if real["n"] != mio["n"]:
                print("  FALLA %s r%d: n real=%d vs mio=%d (%s / %s)"
                      % (fecha, ronda, real["n"], mio["n"],
                         real.get("motivo", "-"), mio.get("motivo", "-")))
                return False, 0
            if real["n"] == 0:
                continue
            difs = _comparar(real["filas"], mio["filas"])
            if difs:
                print("  FALLA %s ronda %d -- PRIMER PUNTO DE DIVERGENCIA:" % (fecha, ronda))
                for d in difs[:10]:
                    print("     ", d)
                return False, 0
            total_anclas += real["n"]
        print("  OK %s  (%d anclas acumuladas)" % (fecha, total_anclas))
    print()
    print("  IDÉNTICO en %d anclas sobre %d días x %d rondas  (%.0fs)"
          % (total_anclas, len(dias), len(RONDAS_CONTROL), time.time() - t0))
    return True, total_anclas


def unidad_1b(dias):
    print()
    print("=" * 74)
    print("1B -- M_forzado: la magnitud a la que el resultado está FORZADO")
    print("=" * 74)
    # MAE observado sobre el nulo, en los mismos días
    peor_mae = {}
    for (archivo, contrato, fecha) in dias:
        res = A.procesar_dia((archivo, contrato, fecha, DATA_DIR, 0))
        if res["n"] == 0:
            continue
        for H in CFG["horizontes_min"]:
            k = "mae_%d" % H
            vals = [f[k] for f in res["filas"] if k in f]
            if vals:
                peor_mae[H] = min(peor_mae.get(H, 0), min(vals))
    print("  peor MAE observado por horizonte (ticks):", dict(sorted(peor_mae.items())))
    P_max = max(P for (P, N) in CFG["pares_pn"])
    mae_peor = abs(min(peor_mae.values()))
    M_forzado = P_max + mae_peor
    print("  P_max=%d  max|MAE|=%d  =>  M_forzado = %d ticks al horizonte"
          % (P_max, mae_peor, M_forzado))
    print()

    filas_por_geom = {}
    for (archivo, contrato, fecha) in dias:
        res = procesar_dia_spike((archivo, contrato, fecha, DATA_DIR, 0, M_forzado, "A"))
        if res["n"] == 0:
            continue
        for H in CFG["horizontes_min"]:
            for (P, N) in CFG["pares_pn"]:
                g = "H%d_P%d_N%d" % (H, P, N)
                key = "r_%d_%d_%d" % (H, P, N)
                S, T = filas_por_geom.get(g, (0, 0))
                for f in res["filas"]:
                    v = f.get(key)
                    if v is None or v == 0:
                        continue
                    T += 1
                    if v == 1:
                        S += 1
                filas_por_geom[g] = (S, T)

    malas = []
    for g in sorted(filas_por_geom):
        S, T = filas_por_geom[g]
        p = S / T if T else float("nan")
        if T and p < 1.0:
            malas.append((g, S, T, p))
    print("  geometrías con p_favorable < 1,0 bajo M_forzado: %d de %d"
          % (len(malas), len(filas_por_geom)))
    for g, S, T, p in malas[:10]:
        print("     %-14s S=%d T=%d p=%.4f" % (g, S, T, p))
    ok = not malas
    print()
    print("  1B %s" % ("PASA: el resultado forzado se devuelve" if ok else
                       "FALLA: defecto del camino de inyección, no de la señal"))
    return ok, M_forzado


if __name__ == "__main__":
    dias_todos, fechas = dias_del_atlas_sellado()
    print("días del atlas sellado resueltos: %d de %d" % (len(dias_todos), len(fechas)))
    dias = dias_todos[:N_DIAS_CONTROL]
    print("subconjunto de control: %s" % [d[2] for d in dias])
    print()
    ok_a, n_anclas = unidad_1a(dias)
    if not ok_a:
        print("\nPARADA en 1A. No se gasta en la grilla.")
        sys.exit(1)
    ok_b, M = unidad_1b(dias)
    if not ok_b:
        print("\nPARADA en 1B. No se gasta en la grilla.")
        sys.exit(2)
    print("\nLOS DOS EXTREMOS PASAN. M_forzado = %d ticks." % M)
