"""U1-ZONAS con los RECTÁNGULOS de BigTrap2 (2026-10-26, pedido de Nico): la gramática de `u1_zonas` con la fuente `ZONAS_BT2_*` del
almacén — la zona dibujada (bottom/top), viva hasta que el indicador la invalida o la expira (`t_fin_ns`), no los círculos de TRAP.
BigTrap2 es PASS_CON_CAVEAT (filtro de mecha, 0,0241 %); su paridad es de 6E: en ES/NQ/YM corre sin oráculo propio (declarado en el
pre-registro `docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS_BT2_AVZR.md`). Sólo cambia la fuente; todo lo demás se importa."""
from edgelab.research import u1_zonas as Z
from edgelab.research.u1_zonas import BASE, EJECUCIONES, EJES_ORDINALES, ESCALAS, VACIO, VARIABLES, niveles  # noqa: F401

NOMBRE = "U1-ZONAS-BT2"
INDICADORES = ["BigTrap2"]
FUENTES_ZONAS = ("BT2",)


def disparos(ctx, r_ref=None):
    previo = Z.FUENTES_ZONAS; Z.FUENTES_ZONAS = FUENTES_ZONAS
    try: return Z.disparos(ctx, r_ref)
    finally: Z.FUENTES_ZONAS = previo
