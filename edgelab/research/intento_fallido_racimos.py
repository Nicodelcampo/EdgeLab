"""INTENTO-FALLIDO sobre racimos de aVolZonePOI2 (fuente de U1-RACIMOS-GRILLA). Lógica en `intento_fallido`; acá sólo la fuente de zonas."""
from __future__ import annotations

from edgelab.research import intento_fallido as IF
from edgelab.research import u1_racimos_grilla as FUENTE
from edgelab.research.intento_fallido import (BASE, EJECUCIONES, EJES_ORDINALES, EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO, VACIO, VARIABLES,  # noqa: F401
                                              lineas_salida, niveles)

NOMBRE = "INTENTO-FALLIDO-RACIMOS"
INDICADORES = ["aVolZonePOI2"]


def disparos(ctx, *a, **k):
    return IF.construir(FUENTE.disparos(ctx, *a, **k), ctx)
