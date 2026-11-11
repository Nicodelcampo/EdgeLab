"""LUXIMB-AMARILLA-R2 (2026-11-11, pedido de Nico: «no pidas pocas velas para el impulso inicial ni tanto volumen en las cajas; dos
zonas por día en promedio al menos»). Misma regla que LUXIMB-AMARILLA (mismo código), con:
  - impulsos LARGOS: detector de hasta 40 y 60 velas (antes 20), amplitud p60 sin piso;
  - zonas: ≥ 1 en el 25 % inicial o ≥ 3 en el 50 % inicial. En desarrollo (tablas de LUXIMB-HVN, target-free: sólo conteo de marcas)
    D3_40 con esas condiciones da 3,0–6,2 marcas por sesión en NQ y USATECH: cumple «≥ 2 por día»;
  - caja amarilla con P40 (poco volumen exigido) y su control sin filtro; W 0,5 / 1 / 2; excursión 0,5 / 1 / 2.
Control de zonas: el mismo impulso de 40 velas sin condición de zonas. Pre-registro: docs/research/luximb_amarilla_20261111/PREREGISTRO_R2.md."""
from __future__ import annotations

from edgelab.research import luximb_amarilla as A

NOMBRE = "LUXIMB-AMARILLA-R2"
CARPETA = "docs/research/luximb_amarilla_20261111/r2"
AMP_R = ((60.0, 0.0), (80.0, 60.0))
BASES = {"l40z1": "D3_40_a0_z1", "l40z4": "D3_40_a0_z4", "l60z1": "D3_60_a0_z1", "ctrl": "D3_40_a0_z0"}
WS = (0.5, 1, 2)
ES = (0.5, 1.0, 2.0)
PCT = 40.0
FILTROS_VOL, PUNTOS, EJECUCIONES, PERIODOS = A.FILTROS_VOL, A.PUNTOS, A.EJECUCIONES, A.PERIODOS
DEFINICIONES = [f"{b}|W{w}|{f}|e{e:g}|{p}" for b in BASES for w in WS for f in FILTROS_VOL for e in ES for p in PUNTOS]
CONTROL = {**{f"{b}|W{w}|amarilla|e{e:g}|{p}": f"{b}|W{w}|sin_filtro|e{e:g}|{p}" for b in BASES for w in WS for e in ES for p in PUNTOS},
           **{f"{b}|W{w}|sin_filtro|e{e:g}|{p}": f"ctrl|W{w}|sin_filtro|e{e:g}|{p}" for b in ("l40z1", "l40z4", "l60z1") for w in WS for e in ES for p in PUNTOS}}


def eventos(ctx):
    return A.construir(ctx, BASES, WS, ES, PCT, AMP_R, largos=True)
