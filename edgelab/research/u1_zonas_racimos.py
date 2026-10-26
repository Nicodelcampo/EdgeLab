"""U1-ZONAS con RACIMOS de aVolZonePOI2 por tipo (2026-10-26, pedido de Nico: «los tipos de racimos son parámetros también»): la
gramática de `u1_zonas` donde cada «zona» es un racimo de AVZP2 al formarse, y la perilla `indicador` es el TIPO de racimo (8 definiciones
de `almacen_zonas_main.TIPOS_RACIMO`: mínimo {4, 8} × ventana {250, 1000} × altura {20, 45}). Pre-registro
`docs/research/u1_zonas_20261025/PREREGISTRO_U1_ZONAS_BT2_AVZR.md`."""
from edgelab.research import u1_zonas as Z
from edgelab.research.grilla_generica import Variable
from edgelab.research.u1_zonas import EJECUCIONES, EJES_ORDINALES, ESCALAS, VACIO, niveles  # noqa: F401

NOMBRE = "U1-ZONAS-RACIMOS"
INDICADORES = ["aVolZonePOI2"]
FUENTES_ZONAS = tuple(f"AVZR{i}" for i in range(8))
VARIABLES = list(Z.VARIABLES[:-1]) + [Variable("tipo_racimo", "ind", "grupo", categoria=len(FUENTES_ZONAS))]
BASE = {**{k: v for k, v in Z.BASE.items() if k != "indicador"}, "tipo_racimo": 3}       # 4 zonas / 1000 velas / 45 ticks (índice m·4 + w·2 + a)


def disparos(ctx, r_ref=None):
    if "zonas" in ctx and set(ctx["zonas"]) == {"AVZP2"}:                                  # preflight/tests: la misma fuente en cada tipo
        ctx = dict(ctx, zonas={f: ctx["zonas"]["AVZP2"] for f in FUENTES_ZONAS})
    previo = Z.FUENTES_ZONAS; Z.FUENTES_ZONAS = FUENTES_ZONAS
    try: return Z.disparos(ctx, r_ref)
    finally: Z.FUENTES_ZONAS = previo
