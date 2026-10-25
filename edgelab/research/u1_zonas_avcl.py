"""U1-ZONAS con zonas de aVolClusterPOI (2026-10-25): la misma gramática que `u1_zonas` con la otra fuente del almacén (`ZONAS_AVCL_*`).
Pre-registro: `docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS.md` §8. Sólo cambia la fuente; todo lo demás se importa."""
from edgelab.research import u1_zonas as Z
from edgelab.research.u1_zonas import BASE, EJECUCIONES, EJES_ORDINALES, ESCALAS, VACIO, VARIABLES, niveles  # noqa: F401

NOMBRE = "U1-ZONAS-AVCL"
INDICADORES = ["aVolClusterPOI"]
FUENTES_ZONAS = ("AVCL",)


def disparos(ctx, r_ref=None):
    previo = Z.FUENTES_ZONAS; Z.FUENTES_ZONAS = FUENTES_ZONAS
    try: return Z.disparos(ctx, r_ref)
    finally: Z.FUENTES_ZONAS = previo
