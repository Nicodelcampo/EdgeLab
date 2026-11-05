# Pre-registro — ATRAS: las celdas positivas sin señal, en la historia NUNCA mirada (ene-2023 → jul-2025)

Estado: PRE-REGISTRO (commiteado antes de correr). Fecha: 2026-10-26.
Referente: `docs/NORTH_STAR.md`, cuerpo sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Pedido de Nico (2026-10-26): ganar potencia con historia pasada («hay muchísimos datos del pasado»). Etapa: **ATRAS, informativa (ATJ-24)**:
no mata ni promueve; dice si el efecto es estable o propio del régimen actual.

## Qué corre
- **EXPZ-CFD** y **ZGAP-CFD** (señal en USATECH de Dukascopy, ejecución declarada en NQ): sus candidatas y pistas congeladas, con sus
  cortes, sobre **2023-01-03 → 2025-08-04** (antes de su DESC; ninguna corrida miró ese tramo para estas familias).
  Ejecución en el propio USATECH con los costos de NQ (`edgelab/costos.py`), porque no hay ticks de NQ de ese período: **proxy declarado**
  (la base CFD−futuro se mide en la réplica, no acá).
- Motor: etapa ANALIZAR_REGLA (mismo motor que eligió las celdas). Una corrida por campaña, registrada antes en el contador global.

## Qué NO corre, y por qué
- U1-ES-GRILLA y U1-YM-GRILLA: 2023–2025 ya se miró (`docs/research/u1_cfd_20261025/LINEA_DE_TIEMPO_CANDIDATAS_U1_ES_YM_20261026.md`, ≈0).
- EXPZ-NQ, ZGAP-NQ, U1-ZONAS-*: sensor en el futuro, sin ticks antes de 2025-08 (hace falta la historia de NT8: módulo NT8).

## Lectura (fijada antes)
Por celda: media neta, IC90 por sesiones, resultado por trimestre. A_FAVOR si el IC90 entero > 0; EN_CONTRA_PASADO si el IC90 entero
< 0 (el edge, si existe, es del régimen actual: lo decide el holdout); si no, SIN_RECHAZO. Nunca se usa para elegir celdas del holdout.

## Cómo podría refutarse la utilidad de esta etapa
Si las celdas dan lo mismo que su réplica en promedio pero con IC que cruza cero en todas, la historia vieja no agrega potencia
(N por celda chica): se registra y no se repite.

## Resultado EXPZ-CFD (2026-10-26, después de correr)
20 celdas, 2023-01-03 → 2025-08-04, ejecución proxy en USATECH con costo de NQ: **0 A_FAVOR, 6 EN_CONTRA_PASADO, 14 SIN_RECHAZO**.
Las seis mejores del analizador (reciente +8,5 a +21,1 pts/op) dan −1,0 a −4,9 pts/op en 2023–2025; tres con IC90 entero < 0.
Lectura fijada: el efecto, si existe, es del régimen actual (no estable): lo decide el holdout. No mata (ATJ-24). Detalle: `EXPZ-CFD.json`.
ZGAP-CFD: corriendo.

## Resultado ZGAP-CFD (2026-10-26)
20 celdas, mismo período y proxy: **1 A_FAVOR, 4 EN_CONTRA_PASADO, 15 SIN_RECHAZO**. A_FAVOR: celda `[0,1,0,0,2,1,1,1,2,4,11]`,
120 ops, +10,3 pts/op, IC90 [+0,7; +21,1]. Con 20 celdas, una A_FAVOR al 90 % unilateral es lo esperable por azar (≈1): no se lee como
señal por sí sola. Su reporte reciente (analizador) está pendiente de reintento. Detalle: `ZGAP-CFD.json`.
