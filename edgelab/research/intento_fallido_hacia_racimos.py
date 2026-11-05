"""INTENTO-FALLIDO-HACIA sobre racimos de aVolZonePOI2. Lógica en `intento_fallido_b80`; acá sólo la fuente de zonas."""
from __future__ import annotations

from edgelab.research import intento_fallido_b80 as IB
from edgelab.research import u1_racimos_grilla as FUENTE
from edgelab.research.intento_fallido_b80 import (BASE, EJECUCIONES, EJES_ORDINALES, EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO,  # noqa: F401
                                                  VACIO, VARIABLES, lineas_salida, niveles)

NOMBRE = "INTENTO-FALLIDO-HACIA-RACIMOS"
INDICADORES = ["aVolZonePOI2"]


def disparos(ctx, *a, **k):
    return IB.construir(FUENTE.disparos(ctx, *a, **k), ctx)
