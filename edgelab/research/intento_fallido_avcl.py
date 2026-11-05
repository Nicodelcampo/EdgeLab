"""INTENTO-FALLIDO sobre racimos de aVolClusterPOI (fuente de U1-ZONAS-AVCL). Lógica en `intento_fallido`; acá sólo la fuente de zonas."""
from __future__ import annotations

from edgelab.research import intento_fallido as IF
from edgelab.research import u1_zonas_avcl as FUENTE
from edgelab.research.intento_fallido import (BASE, EJECUCIONES, EJES_ORDINALES, EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO, VACIO, VARIABLES,  # noqa: F401
                                              lineas_salida, niveles)

NOMBRE = "INTENTO-FALLIDO-AVCL"
INDICADORES = ["aVolClusterPOI"]


def disparos(ctx, *a, **k):
    return IF.construir(FUENTE.disparos(ctx, *a, **k), ctx)
