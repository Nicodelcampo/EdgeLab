# Resultado: DOBLE-RETROCESO (04/11/2026)

Estado: VIGENTE — 10 de 10 campañas terminadas. Pre-registro: `PREREGISTRO_DOBLE_RETROCESO.md`. Embudo en R con cola t; holdout sin tocar.
Paridad con NT8 no validada; se corrió igual por decisión de Nico.

| Campaña | Evaluables (de 746.496) | FDR | Réplica: canasta de pistas (R) | Desenlace |
|---|---|---|---|---|
| DRC-NQ | 526.771 | 0 | −0,05 (−0,12 a +0,03) | PISTAS_VIVAS |
| DRC-ES | 568.735 | 0 | **−0,46** (−0,72 a −0,19) | en contra |
| DRC-YM | 381.952 | 0 | +0,01 (−0,20 a +0,24) | PISTAS_VIVAS |
| DRC-GC | 447.921 | 0 | +0,04 (−0,20 a +0,29) | PISTAS_VIVAS |
| DRC-USATECH | 555.647 | 0 | −0,12 (−0,28 a +0,05) | PISTAS_VIVAS |
| DRC-USA500 | 464.914 | 0 | **−0,11** (−0,17 a −0,05) | SIN_CANDIDATAS; en contra con potencia |
| DRC-USA30 | 506.268 | 0 | **−0,10** (−0,16 a −0,04) | SIN_CANDIDATAS; en contra con potencia |
| DRC-XAU | 569.254 | 0 | −0,05 (−0,14 a +0,04) | PISTAS_VIVAS |
| DRC-EURUSD | 500.259 | 0 | −0,08 (−0,30 a +0,15) | PISTAS_VIVAS |
| DRC-GBPUSD | 499.053 | 0 | **−1,01** (−1,37 a −0,65) | en contra |

**Lectura:** la muestra es amplia: entre 380 mil y 570 mil combinaciones evaluables por activo, todas con ≥ 30 operaciones. Aun así,
**ninguna combinación de distancias, velas por pierna, resolución ni entrada sobrevive al FDR en ningún activo**. Las canastas de las
mejores pistas en réplica son ≤ 0 o cercanas a cero, y en ES, USA500, USA30 y GBPUSD van **en contra**. Las mejores pistas tienen media
de DESC de +0,5 a +1,3R y caen a +0,0/+0,4R en réplica: maldición del ganador clásica de una grilla de 746 mil celdas.

**Nominación forzada** (réplica > 0 con cota inferior del IC90 > 0): ninguna cumple. La mejor es DRC-GC, con +0,18R e IC90 −0,11 a
+0,47. No se nomina nada.

**Qué queda medido:** en estos 10 activos, con barras de 50, 100 y 250 ticks, el patrón de 5 piernas no tiene edge en R con costos y
ejecución realistas.

**No medido:** otras resoluciones (25 o 500 ticks), entradas distintas (límite en P4), stops por debajo de P2, y la paridad con el indicador
de NT8.
