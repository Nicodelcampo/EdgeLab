"""Variante τ de las reglas con acta (2026-10-31, plan del paquete): MISMAS entradas, salida por tiempo de parada.

Mide si cambiar sólo la salida de una regla ya congelada por la salida estructural del paper de Tori Trades (primer cierre del lado
equivocado de la línea por los dos últimos pivotes, `tau_tendencia.lineas_salida`, δ = 0) mejora el pago. Motivo: 10 de las 12 reglas
con acta ganan seguido poco y pierden de a mucho (W/L 0,23–0,35, auditoría externa del PR #162). Pre-registro:
docs/research/paquete_20261031/PREREGISTRO_VARIANTE_TAU_ACTAS.md.

`envolver(base, g)` copia el experimento `base` en el espacio de nombres `g` y multiplica sus ejecuciones por las VARIANTES: la
ejecución e del original pasa a ser 4·e + j (j = 0 ORIGINAL, 1..3 τ con pivotes de orden 3, 5 y 8). El stop y el objetivo del
original siguen activos; τ sólo agrega una salida. No se aplica a reglas que operan en otro instrumento (CVGAP-CFD-NQ, U1-ORO):
las líneas están en precios del sensor. Los módulos `vtau_*` existen porque el kernel arma sus dependencias por importación.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import tau_tendencia as TAU

VARIANTES = ("ORIGINAL",) + TAU.ORDENES


def celda_variante(celda, j: int) -> list:
    """Celda congelada del original -> la misma celda con la variante j (último índice = ejecución)."""
    return list(celda[:-1]) + [len(VARIANTES) * int(celda[-1]) + j]


def envolver(base, g: dict) -> None:
    for k in dir(base):
        if not k.startswith("__"): g[k] = getattr(base, k)
    n = len(VARIANTES)

    def _cols(X, j):
        X = np.asarray(X, float)
        kl = np.full(len(X), -1.0) if j == 0 else 2.0 * (j - 1) + (X[:, 2] == -1)
        return np.column_stack([X, kl, np.zeros(len(X))])

    def niveles(d, ej, ctx):
        nv = base.niveles(d, ej[0], ctx)
        if nv is None: return None
        return tuple(nv) + ((-1, 0.0) if ej[1] == "ORIGINAL" else (2 * TAU.ORDENES.index(ej[1]) + (nv[2] == -1), 0.0))

    def niveles_lote(D, ej, ctx):
        j = VARIANTES.index(ej[1])
        if hasattr(base, "niveles_lote"): X = np.asarray(base.niveles_lote(D, ej[0], ctx), float)
        else:
            X = np.full((len(D), 7), np.nan)
            for i, r in enumerate(D.to_dict("records")):
                nv = base.niveles(r, ej[0], ctx)
                if nv is not None: X[i] = nv
        return _cols(X, j)

    g.update(NOMBRE=f"{base.NOMBRE}-TAU", EJECUCIONES=[(e, v) for e in base.EJECUCIONES for v in VARIANTES],
             niveles=niveles, niveles_lote=niveles_lote, lineas_salida=TAU.lineas_salida,
             BASE=dict(base.BASE, **{"ejecución": n * int(base.BASE.get("ejecución", 0))}))
