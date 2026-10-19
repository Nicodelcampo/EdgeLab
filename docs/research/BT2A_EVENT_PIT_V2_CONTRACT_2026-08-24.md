# BT2A event PIT v2 — contrato correctivo

- **Estado:** código y tests versionados; recomputación pendiente de inputs locales.
- **Firewall:** target-free; no abre outcomes ni holdout.
- **Schema canónico nuevo:** `bt2a_event_pit_v2`.

## Por qué v1 queda invalidado

`bt2a_event_pit_v1` fechaba `ABS_SCORE` con `t_start`, aunque el score sólo existe al
cerrar la cubeta. Además cortaba la cinta con `searchsorted(timestamp, side="right")`, lo
que podía incorporar ticks posteriores con el mismo timestamp que la señal. Los parciales
v1 no se migran: requieren recomputación desde los ticks canónicos.

## Correcciones v2

1. Disponibilidad del indicador = timestamp del log `ABS_SCORE`, emitido en
   `blk_ts[-1]`.
2. Frontera causal del tape = `zone.sig_idx`, con orden `(ts_ns, sequence)`.
3. La ventana termina en el tick de señal inclusive y no cruza sesión.
4. `N` ticks representan `N-1` intervalos para la tasa.
5. Locked book se permite y cuenta; crossed book aborta.
6. Geometría guardada como enteros en medios ticks.
7. `event_key ↔ row` debe ser uno-a-uno; no se deduplica silenciosamente.
8. Cada fila, el conjunto de keys y el store llevan SHA-256.
9. Se publican conteos y cobertura `as_of_ok` por sesión.
10. `window_ticks=500` deja de ser constante oculta: está preregistrado en
    `specs/bt2a_event_pit_v2.json` y es parámetro obligatorio del constructor.

## Estado de ejecución

No se afirma cobertura ni conteo porque los `.Last.txt` y parciales viven fuera del repo.
Cuando estén disponibles hay que correr nuevamente los kernels en commit limpio, generar
v2 y verificar hashes/conteos antes de cualquier C1 del atlas causal.
