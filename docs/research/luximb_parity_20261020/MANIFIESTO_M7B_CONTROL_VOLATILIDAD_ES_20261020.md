# Manifiesto M7b (PROPUESTO, sin OK) — control por volatilidad previa de M7-H2 (ES, descubrimiento)

Estado: PROPUESTO. **No se corre sin OK de Nico.** Fecha 2026-10-20.
Referente: `docs/NORTH_STAR.md` cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.
Objetivo: decidir si "menos recorrido sobre area cargada" (M7-H2: -3,3 pts, -14 %, Holm 0,0008) es efecto de las zonas o
del regimen de volatilidad en que aparecen las areas cargadas.

## Datos y eventos
Exactamente los 7.699 eventos de M7 (misma definicion, K=350, mismos contratos ES de descubrimiento, mismo T/C y mismo
desenlace `recorrido_pts` = max high - min low de las velas 25t en los 60 min posteriores a la deteccion). No se cambia nada
de M7; solo se agrega una covariable causal. No se usa replicacion ni holdout.

## Covariable (causal, conocida al detectar)
- **vol_pre** = max high - min low de las velas 25t en los 60 min ANTERIORES al cierre de la barra de deteccion.
- Secundaria descriptiva: ATR(14) M1 cerrado en la vela anterior a la deteccion.
Se publica antes de inferir: distribucion de vol_pre en T y en C (si T tiene vol_pre menor, la confusion es real).

## Hipotesis (2, Holm; bootstrap por dia NY 10.000; direccion fijada)
- **H2b (primaria)**: recorrido T - C **< 0** dentro de estratos de **quintiles de vol_pre x franja (cash 9:30-11 / resto)**,
  promedio ponderado por el n de T en cada estrato (estratos sin C se descartan y se reporta cuantos T quedan fuera).
- **H2c**: cociente recorrido / vol_pre, T - C **< 0** (sin estratos).
Se publican MDE80 de ambas y el efecto crudo de M7 al lado para ver cuanto se "explica" por vol_pre.

## Decision
- H2b sobrevive (Holm < 0,05) -> H2 pasa a candidata a **replicacion ES abr-sep** (una sola vez, definicion H2b exacta,
  sin elegir nada ahi).
- H2b nula con MDE <= 1,5 pts -> el "freno" se explica por la volatilidad previa: H2 muere como efecto de zonas
  (queda solo como descriptor de regimen).
- H2b nula con MDE > 1,5 pts -> indeterminado por potencia; no se promueve.

## Justificacion economica
Si las zonas OG/VI absorben ordenes, el freno deberia verse aun comparando contra momentos de igual volatilidad. Si solo
reflejan mercado lento, desaparece al condicionar.

## Como podria refutarse
Ver "Decision": H2b nula con potencia suficiente.

## Riesgos
1. vol_pre y el area estan correlacionados (areas cargadas pueden ser mas grandes): por eso M7-H3 ya se reporto y aca se
   agrega el cociente H2c.
2. Quintiles fijados sobre todos los eventos (T+C), no elegidos mirando desenlaces.
3. Mismos datos que M7: es un control de confusion, no evidencia nueva; la confirmacion independiente es la replicacion.

## Datos faltantes
Ninguno.
