"""ESPEJO-MACRO-10T-ANCHO (2026-11-07, Nico: «ajustá los parámetros para que sí aparezcan operaciones donde no alcanzan»).

Segunda variante, sobre ESPEJO-MACRO-10T-TIEMPO (topes en tiempo), que no se toca. Con topes en tiempo, ES siguió con 0 celdas
evaluables: 17,7 M velas y 18 disparos. El cuello era el ANCHO MÍNIMO: 10 viajes de fricción severa en la mitad que falta, que es
W >= 151 ticks = 37,75 pts de ES (en NQ, 51 pts, pero NQ recorre unas 4 veces más puntos que ES). Cambio único: el mínimo laxo pasa a
5 viajes y la perilla de ancho a 5 / 10 / 20 viajes. La celda >= 10 es la regla anterior; 5 es el piso: por debajo, la fricción se come
lo que falta hasta A. Todo lo demás es igual a la variante en tiempo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from edgelab.research import espejo_macro_grilla as P, espejo_macro_tiempo as TI
from edgelab.research.espejo_macro_tiempo import (EJECUCIONES, EXCLUIR_EVENTOS, FRACCIONES, LINEAS_SOLO_TIEMPO, MAX_SEG_IDA,  # noqa: F401
                                                  MAX_SEG_TOTAL, RETRO_LAXO, TOPE_BARRAS, lineas_salida, niveles)
from edgelab.research.grilla_generica import Variable

NOMBRE = "ESPEJO-MACRO-10T-ANCHO"
INDICADORES = ["ESPEJO-MACRO-10T"]
VIAJES_LAXO = 5.0
VARIABLES = [v if v.nombre != "viajes" else Variable("viajes", "viajes", "ge", cortes=(5.0, 10.0, 20.0), piso=True) for v in TI.VARIABLES]
EJES_ORDINALES = TI.EJES_ORDINALES
BASE = dict(TI.BASE, viajes=0)


def disparos(ctx) -> pd.DataFrame:
    """La variante en tiempo con el ancho mínimo laxo en 5 viajes (único cambio)."""
    viejo = TI.VIAJES_MIN
    TI.VIAJES_MIN = VIAJES_LAXO
    try: return TI.disparos(ctx)
    finally: TI.VIAJES_MIN = viejo
