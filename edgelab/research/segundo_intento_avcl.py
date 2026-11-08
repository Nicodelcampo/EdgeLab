"""SEGUNDO-INTENTO sobre zonas de volumen aVolClusterPOI (almacén `ZONAS_AVCL_<INST>`, como U1-ZONAS-AVCL). Lógica en `segundo_intento`."""
from __future__ import annotations

from edgelab.research import segundo_intento as SI
from edgelab.research import u1_oro as UO
from edgelab.research import u1_zonas_avcl as FUENTE
from edgelab.research.segundo_intento import (BASE, EJECUCIONES, EJES_ORDINALES, EXCLUIR_EVENTOS, LINEAS_SOLO_TIEMPO, VACIO,  # noqa: F401
                                              VARIABLES, lineas_salida, niveles)

NOMBRE = "SEGUNDO-INTENTO-AVCL"
INDICADORES = ["aVolClusterPOI"]


def disparos(ctx, r_ref=None):
    D = SI._aproximaciones(FUENTE.disparos, ctx, r_ref)
    if len(D) and "esc" in D: D = D[D.esc == UO.ESCALAS.index(1.0)].reset_index(drop=True)
    return SI.construir(D, ctx)
