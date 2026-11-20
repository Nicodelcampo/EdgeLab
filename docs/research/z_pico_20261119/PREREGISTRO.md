# Z-PICO: ¿el pico de fábrica de Z es sobreajuste? ¿Russell tiene el mismo pico? (pre-registro, 2026-11-19)

Estado: PRE-REGISTRO — la parte de NQ/ES es descriptiva sobre operaciones ya medidas (`NQ_ES.json`, ya calculado); la grilla de Russell se
commitea antes de correrla.
- **Pedido de Nico:** «¿que en Russell funcione igual tiene más o menos peso que que sea un pico? Quiero más cálculos en los que determines
  si el pico es sobreajuste y si también da un pico en Russell».
- **North Star** sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
- **Etapa EF3** (DESC de A5 en RTY; REP de RTY sigue sellado). **Familia:** `FUNDEDSYNC`.
- **Herramienta:** `tools/z_pico.py rty_grilla|rty` (motor de la traducción de FundedSync vía `neto_pistas._ms/_ops/_cfg/GRILLAS`, la misma
  batería que en NQ: `bateria()`). `registro_global.exigir_contada` al inicio (K51).

Antecedentes: NETO-PISTAS (Z INTERMEDIO), RE-INDAGACION, TRANSFER-RTY-EMD (fábrica en RTY DESC 2018+: +0,146 R, p 0,085), `NQ_ES.json`
(fábrica 6.ª de 27 en NQ, exceso sobre la mediana dentro del ruido de elegir la mejor de 27).

Lectura previa: LEER_ANTES_DE_CADA_CORRIDA v3 — §0–§6 (K36, K40, K48, K49, K51, K52).

Potencia previa: ≈ 1,7 operaciones por mes por variante en RTY (datos desde 2017-07) → ≈ 90–110 por variante en DESC; el rango de la
fábrica entre 27 variantes con ee ≈ 0,1 R por variante es ruidoso: se reporta con su bootstrap («mejor de 27») y no se elige nada.

## Justificación económica
- Si el pico de fábrica fuera un ajuste a NQ, en un índice que el vendedor no usó la fábrica no debería destacarse de sus vecinos; si es
  una propiedad del mecanismo (eficiencia del día con cubetas de 15 min), debería volver a aparecer.

## Qué se mide (la misma batería que en NQ, fijada antes)
- En RTY, meses DESC 2017-07 → 2025-07 y desde 2018: R neto (stop 0,25 × ATR20) de las 27 variantes; rango de la fábrica; exceso sobre la
  mediana con IC 90 % (bootstrap por meses); p de «mejor de 27 por azar»; vecinos a un paso; años con la fábrica sobre la mediana; PBO.
- **Lectura decidida antes:** «pico transferido» si la fábrica queda en el tercio superior (rango ≤ 9) y su exceso tiene IC 90 % > 0;
  «sin pico» si la fábrica queda cerca de la mediana; en los dos casos se reporta la mediana de la grilla (la estimación sin selección).
- **Cómo podría refutarse** la idea de que Z vive en Russell: mediana de la grilla ≤ 0 en RTY desde 2018.
- **Contador:** 1 prueba en `FUNDEDSYNC` (la grilla es diagnóstica: no se elige variante).
