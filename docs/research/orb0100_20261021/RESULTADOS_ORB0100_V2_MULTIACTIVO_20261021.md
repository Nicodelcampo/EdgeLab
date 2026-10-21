# Resultados ORB0100 V2 — 24 variantes alrededor de 1,5R/rango/mercado/VWAP, 8 activos (descubrimiento)

Estado: MEDIDO. Veredicto: **NINGUNA VARIANTE TRANSPORTA**. Manifiesto `MANIFIESTO_ORB0100_V2_MULTIACTIVO_20261021.md`
(antes de correr). Codigo `tools/orb0100/orb0100_v2.py`; salida `RESULTADOS_ORB0100_V2.json` y `.csv`.

## Combinado de los 7 activos nuevos (R neto por operacion)
Las **24 celdas dan negativo**, todas con IC por debajo de 0 (Holm 0,0007-0,011 en contra): de -0,13 R (1,5R / 01:00-01:30 /
VWAP+EMA / 16:00) a -0,23 R. Solo 1-2 de 7 activos positivos en cualquier celda. TP mas grande empeora; rango 01:00-01:30 algo
menos malo que 01:00-01:15; filtro EMA y cierre a las 11:00 casi no cambian nada.

## Celda de partida (1,5R / 01:00-01:15 / VWAP / 16:00) por activo
| activo | n | acierto | R/op | USD/op (1 contrato) | R 2025 | R 2026 | max DD USD |
|---|---|---|---|---|---|---|---|
| NQ (no cuenta, ya usado) | 107 | 47,7 % | +0,18 | +18 (MNQ) | +0,15 | +0,23 | 610 |
| ES | 117 | 37,6 % | -0,12 | +12 | -0,24 | +0,15 | 5.179 |
| MYM | 68 | 38,2 % | -0,15 | -0,5 | -0,12 | -0,18 | 345 |
| GC | 89 | 48,3 % | +0,19 | +267 | +0,13 | +0,33 | 7.282 |
| 6E | 97 | 27,8 % | -0,42 | -36 | -0,36 | -0,54 | 3.436 |
| 6B | 94 | 29,8 % | -0,43 | -23 | -0,41 | -0,47 | 2.741 |
| 6J | 107 | 35,5 % | -0,21 | -14 | -0,12 | -0,41 | 2.295 |
| MBT | 91 | 42,9 % | +0,02 | +0,9 | +0,13 | -0,17 | 290 |

## Lectura
- La idea no es general: en divisas pierde fuerte (el rango de la 01:00 es chico y el costo pesa en R), en indices de EE.UU.
  distintos a NQ (ES en R, MYM) pierde, y solo NQ y GC dan positivo, ambos tambien en 2025 y 2026.
- ES tiene R negativo pero USD positivo: pocas ganancias grandes compensan muchas perdidas chicas; sin consistencia.
- NQ ya no es evidencia independiente. GC (+0,19 R, ambos anios) es el unico activo nuevo a favor, aislado y con DD alto.
- Cierra: ORB0100 como estrategia transportable. Queda descriptivo: NQ y GC positivos en la celda de partida (no promovido).
