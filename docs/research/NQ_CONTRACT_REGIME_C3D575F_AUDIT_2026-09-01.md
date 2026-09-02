# Auditoría de `c3d575f` y contrato de corrección v2

Fecha: 2026-09-01 (America/Buenos_Aires)  
Commit auditado: `c3d575fbdfc989952aace8572630a8c6ce046061`

## Veredicto

`PROVISIONAL_INVALID_CALENDAR_DO_NOT_USE_FOR_EF0`

El hash consistente solo prueba integridad interna. No certifica calendario,
completitud de sesiones ni población.

## Evidencia

1. El calendario contiene 28 fechas de sábado/domingo, incluyendo `20250803`,
   `20250809`, `20251214`, `20260621` y `20260627`.
2. Hay 263/265 asignaciones elegibles: una `NO_PRIOR_SESSION` y una
   `SOURCE_INCOMPLETE`.
3. El `SOURCE_INCOMPLETE` del 2025-12-15 nace de una fecha espuria: NQ 03-26
   tiene volumen 1 el domingo 2025-12-14 y NQ 12-25 no tiene esa falsa sesión.
4. La v1 declara `complete_session=True` ante cualquier trade date con un tick.
5. La v1 no informa mantenimiento ni distingue cero explícito de fila ausente.

Los cuatro crossovers son hipótesis plausibles, no un régimen certificado. El
intervalo escrito de NQ 06-26 es `[20260317, 20260616)`: el último trade date
incluido es 2026-06-15; 2026-06-16 ya pertenece a NQ 09-26.

## Contrato v2 fail-closed

- observaciones y evidencia de completitud son objetos separados;
- evidencia ligada al dataset y a los SHA-256 exactos de cada parquet;
- calendario certificado solo lunes-viernes;
- fechas de fin de semana excluidas y registradas en cuarentena;
- ticks 16:00–17:00 CT fuerzan sesión incompleta;
- fila ausente nunca se interpreta como volumen cero;
- cero solo con `explicit_zero_volume=true` y evidencia explícita;
- se verifican schema, identidad interna, filas, orden, sequence, volumen,
  hashes y ausencia física de holdout;
- sin evidencia completa aprobada solo se emite candidato con abstención;
- outcomes/holdout cerrados, precios reales sin ajuste y reset en cada roll.

## EF0

No se recortan zonas/bloques ya calculados: contienen estado previo al roll.
Tras certificar el manifiesto se reconstruye cada intervalo desde ticks con
reset de barras, indicador y `SessionProfile`; luego se concatenan únicamente
outputs target-free.

## STOP

Esta corrección prepara código y pruebas. Releer los cinco parquets (~119 M
ticks / ~2,26 GB) requiere una autorización pesada independiente.
