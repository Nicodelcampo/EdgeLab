"""LUXIMB-AMARILLA-R: versión RELAJADA de LUXIMB-AMARILLA por la regla mecánica de la adenda del pre-registro (pocos casos: 12–13 de 36
definiciones del visor con ≥ 30 operaciones por corte). Cambia sólo: P60 en la caja amarilla, excursión 0,5 además de 1/2/4, W 0,5
además de 1/2, base z1 (≥ 1 zona en el 25 % inicial) y amplitud p60 SIN piso de 60 puntos. Todo lo demás igual (mismo código).
docs/research/luximb_amarilla_20261111/PREREGISTRO.md (adenda)."""
from __future__ import annotations

from edgelab.research import luximb_amarilla as A

NOMBRE = "LUXIMB-AMARILLA-R"
CARPETA = "docs/research/luximb_amarilla_20261111/relajada"
AMP_R = ((60.0, 0.0), (80.0, 60.0))                     # a0 = p60 sin piso
BASES = {"visor": "D3_20_a0_z2", "z1": "D3_20_a0_z1", "d2": "D2_20_a0_z2", "ctrl": "D3_20_a0_z0"}
WS = (0.5, 1, 2)
ES = (0.5, 1.0, 2.0, 4.0)
PCT = 60.0
FILTROS_VOL, PUNTOS, EJECUCIONES, PERIODOS = A.FILTROS_VOL, A.PUNTOS, A.EJECUCIONES, A.PERIODOS
DEFINICIONES = [f"{b}|W{w}|{f}|e{e:g}|{p}" for b in BASES for w in WS for f in FILTROS_VOL for e in ES for p in PUNTOS]
CONTROL = {**{f"{b}|W{w}|amarilla|e{e:g}|{p}": f"{b}|W{w}|sin_filtro|e{e:g}|{p}" for b in BASES for w in WS for e in ES for p in PUNTOS},
           **{f"{b}|W{w}|sin_filtro|e{e:g}|{p}": f"ctrl|W{w}|sin_filtro|e{e:g}|{p}" for b in ("visor", "z1", "d2") for w in WS for e in ES for p in PUNTOS}}


def eventos(ctx):
    return A.construir(ctx, BASES, WS, ES, PCT, AMP_R)
