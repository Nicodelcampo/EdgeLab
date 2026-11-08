"""INTENTO-FALLIDO-HACIA sobre racimos LUX-IMB (U1-CRUZADO: USATECH → NQ; y LUX sobre NQ). Lógica en `intento_fallido_b80`; acá sólo la fuente de zonas."""
from __future__ import annotations

from edgelab.research import intento_fallido_b80 as IB
from edgelab.research import u1_indaga as FUENTE
from edgelab.research.intento_fallido_b80 import (BASE, EJECUCIONES, EJES_ORDINALES, EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO,  # noqa: F401
                                                  VACIO, VARIABLES, lineas_salida, niveles)

NOMBRE = "INTENTO-FALLIDO-HACIA-LUX"
INDICADORES = ["LUX-IMB"]


def disparos(ctx, *a, **k):
    return IB.construir(FUENTE.disparos(ctx, *a, **k), ctx)
