# MNQ escalonadas × L2 — primera sesión, QA y observabilidad

**30/09/2026 · NO resultado financiero.** Paquete privado `MNQ_targetfree_para_nube.zip`, sesión CME 20260629, MNQ_09-26, archivos 20260628/29. Código publicado inicialmente en 606f5394f0880026757ff0c6f90b0917d141bcee; HEAD de lectura b78f27f05b91ec437d8ee030a086c8b468aae2ab.

## Veredicto y alcance

**Procedencia del adjunto y geometría: PASS. Publicación live de V1: NO CERTIFICADA. Soporte del filtro actual: insuficiente en esta sesión.** No lanzar las 52 sesiones con V1 ni usar estos timestamps para fills/outcomes. V1 se conserva congelado; V2 es candidato diagnóstico con opt-in explícito, no cambio de estrategia aprobado.

- ZIP sha256 `1e332feeb2dae1d2d91d0395b441df03ef33d98ec94c2f53162b8c6b9fe22e48`.
- Los cuatro hashes recibidos (exporter, detector, reconstructor y catálogo) coinciden EXACTAMENTE con las versiones CRLF de los blobs LF publicados. No se perdona una diferencia de hash: se reprodujeron los bytes CRLF y sus hashes.
- Raw MNQ no disponible en nube: hashes/fila de parquets y manifiestos provienen del recibo local, no de un segundo hash independiente aquí.
- 2.935.440 LAST elegibles = 19.569 velas completas de 150 prints + 90 prints finales. Se reprodujeron las 31 señales sobre TODAS las velas con el detector congelado. Sin cambios de parámetros.
- QA de orden, unicidad, OHLC, grilla implícita, conversión ART→UTC +3h y reconciliación: PASS. Conteos clave recalculados por dos caminos.

## Población y soporte L2 (31 señales)

| Estado excluyente en el momento declarado por V1 | Señales |
|---|---:|
| Nivel del último pico fuera del top10 | 26 |
| Nivel visible, filtro propuesto false | 3 |
| Nivel visible, filtro propuesto true | 1 |
| Libro no disponible | 1 |
| Total | 31 |

Nivel observable: 4/31 (12,9 %). `defense_mask` desconocida: 27/31; **null no es false**. Libro válido en 30 señales. Distancia del pico al touch de su lado, en las 30 con libro válido: mediana 26 ticks, rango 3–81. La confirmación geométrica exige 25 ticks y puede dejar el pico fuera del libro. Esto orienta a medir la historia durante la formación del pico; no prueba defensa, rentabilidad ni inutilidad de L2.

Libro válido en 18.870/19.569 velas (96,428 %); 699 no disponibles en 19 rachas, máxima 141 velas. V1 no exporta causa de gate para cada racha: **causa pendiente**, no asumir corrupción ni bootstrap en todas. No comparar esta cobertura por vela con la cobertura por minuto de los climas HMM.

## Defecto de disponibilidad detectado por lectura de código

V1 cierra el grupo de timestamp cuando lee la primera fila del siguiente timestamp, pero registra `available_row`/`available_ts_us` como última fila/hora del grupo viejo. Los valores del siguiente grupo no entran en el snapshot; sin embargo, su llegada sí es necesaria para SABER que el grupo terminó. Por eso el orden de filas pasa, pero la disponibilidad live no está certificada. No asignar una orden conocida antes de la fila que permite publicar. EOF sólo diagnóstico, no evento operable. El adjunto no trae esas filas raw de frontera: no se reparó retrospectivamente.

V2 separa `snapshot_asof_row` de `available_row` (primera fila siguiente observada), y snapshot time de publication time. Filas sin publicación observada no son operables. Se añaden gates explícitos y observación en el último extremo del pico: snapshot ya conocido al trade y snapshot del grupo publicado después. La asociación de ese pico a una zona sólo se conoce al detectar la zona; nunca se retrotrae el evento de zona al pico.

## QA de V2 (no prueba MNQ real)

5/5 tests nuevos: frontera observada, EOF, tamaño antes/después dentro del mismo timestamp, invariancia del snapshot previo y gate de profundidad incompleta. Smoke GC real de 9.000 grupos: 7 velas/0 señales; cuatro velas ya publicadas idénticas al prefijo truncado. Sólo prueba de pipeline, no frecuencia/edge de GC ni validación V2 sobre MNQ. Entorno sandbox Python3.13 con pandas/NumPy/PyArrow; no se certifica CI ni lock completo del repo.

## Próximo paso

V2 debe optarse explícitamente, una sola sesión y output nuevo. Medir observabilidad previa/en pico/al confirmar, causas de gates y caducidad. Si pasa QA, ampliar preparación target-free con aprobación de semántica y sin abrir outcomes. Requisito nuevo de Nico: suficientes señales observables e independientes; ver `PLAN_MNQ_GC_ESCALONADAS_MUESTRA_Y_POTENCIA_20260930.md`. Manifiesto + OK explícito separados antes de retornos/costos; holdout oct+ intacto.

## Aporte al referente

La primera sesión reproduce las señales, pero el filtro no observa 27/31 casos y V1 no certifica publicación live. No es un nulo de edge: primero se corrige diagnóstico y se verifica soporte/potencia.
