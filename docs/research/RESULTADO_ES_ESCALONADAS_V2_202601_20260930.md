# Resultado ES-ESCALONADAS v2, descubrimiento ene-2026 — familia CERRADA en ES (2026-09-30)

Manifiesto `MANIFIESTO_ES_ESCALONADAS_V2_20260930.md` + enmiendas 1 (más SL/TP) y 2 (break even), ambas antes de ver
resultados · runner `tools/es_escalonadas_v2.py` (commit `4d3242f`) · salida `es_escalonadas/resultado_v2_202601.json`.
Replay tick a tick de 20,5 M operaciones NT8 (25 sesiones de ene-2026), control con la MISMA mecánica de entrada stop.

**Corrección de conteo (declarada):** el manifiesto decía 140 celdas; el runner implementa lo descrito y son **180**
(las variantes con BE se cuentan por familia: A 27 + B 18 por familia × 2 familias × 2 filtros). El max-T se calculó sobre
las 180 celdas evaluables, más estricto que sobre 140 (t crítico 3,64).

## Resultado
- **0/180 sobreviven max-T.** 18 celdas inconclusas por potencia (todas del filtro «a favor» en empinadas B, n ≈ 23).
- R neto > 0 en 14/180 y R bruto > 0 en 30/180, **todas dentro del ruido**. Las mejores son V-shape en empinadas sin
  filtro (n 125, 18 sesiones): p. ej. stop barrido+2 / 8R: R neto +0,24, IC 90 % [−0,20; +0,71], MDE 0,80 R.
- Promedios por grupo (R neto): planas A −0,08; planas B −0,07; empinadas A −0,07; empinadas B +0,03.
- **El filtro de tendencia empeora todos los grupos** (empinadas B «a favor» −0,27; planas B «a favor» −0,20).
- Stops amplios (10–16 ticks) y objetivos largos (5–8R) bajan el peso del spread, pero la continuación (A) sigue
  negativa: el problema no era sólo el costo.

## Descriptivo y un error de conteo
Zonas: planas 1.042, empinadas 332 en ene-2026. El campo «barridas» del descriptivo sólo cuenta los barridos que se
recuperaron (la función devuelve sin barrido si vence el plazo): **no es la tasa de recuperación**. No afecta a las
operaciones B (que sólo existen si hubo recuperación).

## Veredicto
Según el manifiesto: nada sobrevive → **la familia ES-ESCALONADAS (planas y empinadas, confirmación por precio,
continuación y V-shape, estas salidas, con y sin tendencia EMA200) se cierra en ES.** No se abre marzo. El alcance de la
muerte es exactamente ese; otro activo o una definición distinta requieren su propio registro. La V-shape en empinadas
queda como observación sin potencia (MDE 0,8 R), no como hipótesis promovida.
