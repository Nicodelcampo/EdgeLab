"""RANGO-ASIA0100 (2026-10-31): ruptura de rango de 15 minutos con a lo sumo una reentrada; núcleo en `rango_ruptura`.

Rango 01:00–01:15 ET (transición Asia → pre-Londres). Entradas hasta las 04:00 ET; salida forzada a las 06:00 ET (o el tope de 240 velas del simulador).
Familia propia (pre-registro en docs/research/paquete_20261031/SPEC_RANGOS.md): no comparte población, multiplicidad ni resultados con
la otra ventana.
"""
from __future__ import annotations

from edgelab.research import rango_ruptura as RR

NOMBRE = "RANGO-ASIA0100"
INDICADORES = ["RANGO-RUPTURA"]
INI, FIN, LIMITE, SALIDA = 60, 75, 240, 360                        # minutos NY de cierre de vela
VARIABLES, EJECUCIONES, EJES_ORDINALES, BASE = RR.VARIABLES, RR.EJECUCIONES, RR.EJES_ORDINALES, RR.BASE
niveles, niveles_lote = RR.niveles, RR.niveles_lote


def disparos(ctx):
    return RR.disparos(ctx, INI, FIN, LIMITE)


def lineas_salida(ctx):
    return RR.lineas_salida(ctx, SALIDA)
