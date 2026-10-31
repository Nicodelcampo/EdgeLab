"""RANGO-PREAPERTURA (2026-10-31): ruptura de rango de 15 minutos con a lo sumo una reentrada; núcleo en `rango_ruptura`.

Rango 09:15–09:30 ET (pre-apertura de Nueva York). Entradas hasta las 11:30 ET (no se opera la zona muerta 11:30–13:00); salida forzada a las 15:55 ET, en la práctica el tope de 240 velas del simulador.
Familia propia (pre-registro en docs/research/paquete_20261031/SPEC_RANGOS.md): no comparte población, multiplicidad ni resultados con
la otra ventana.
"""
from __future__ import annotations

from edgelab.research import rango_ruptura as RR

NOMBRE = "RANGO-PREAPERTURA"
INDICADORES = ["RANGO-RUPTURA"]
INI, FIN, LIMITE, SALIDA = 555, 570, 690, 955                        # minutos NY de cierre de vela
VARIABLES, EJECUCIONES, EJES_ORDINALES, BASE = RR.VARIABLES, RR.EJECUCIONES, RR.EJES_ORDINALES, RR.BASE
niveles, niveles_lote = RR.niveles, RR.niveles_lote


def disparos(ctx):
    return RR.disparos(ctx, INI, FIN, LIMITE)


def lineas_salida(ctx):
    return RR.lineas_salida(ctx, SALIDA)
