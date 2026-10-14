# Motor continuo de confluencias: tres detectores

## Alcance resuelto

No reabrir datasets, certificaciones de fuente, paridad NT8 100% ni matrices/focales históricas. Usar las fuentes y el scope exploratorio previamente aprobados; riesgos históricos declarados no se transforman en nueva aprobación ni son excusa para exigir auditorías repetidas. Holdout/reservas permanecen cerrados y ticks/eventos privados sólo viven en Kaggle.

## Implementación

- `avz_stream.py`: loop AVZP2 fijado, historia/calibración por sesión/bucket, bloques W parciales y OB pendientes. No recorta lookback, min_samples u OB. Requiere las celdas TOTAL NT8, no footprint agresor. Racimos causalmente separados como el roster.
- `bt2_stream.py`: loop y funciones detectoras BT2 fijadas, estado activo entre barras, misma omisión nativa de la primera barra, TOUCH/REMOVE/BIRTH en su disponibilidad. El nacimiento nunca se toca a sí mismo. No retiene todas las zonas finalizadas ni listas CSV/eventos render.
- `bt2a_stream.py`: funciones detectoras y umbrales BT2A fijados, ring de absorción persistente y zonas activas entre chunks/sesiones. Sólo reinicia el conteo de cubeta en la frontera que el kernel ya reiniciaba; no resetea historial. Conserva residuo hasta su cierre observable. Consume porciones de hasta TapeWindowTicks con copies propias; inputchunk acotado y consumido en una pasada.

BT2A separa índice consumido absoluto del clock de disponibilidad. El último tick de una cubeta residual no prueba su cierre: el siguiente tick de sesión sí, y el EOF no. Las señales emitidas conservan ID/config SHA/kernel SHA; una frontera de chunk no crea otra configuración.

`detector_capture._capture_tree` comparte los hooks hash-bound con el motor de referencia. La refactorización no modifica ningún archivo detector canónico. Kernels fijados sin cambios; el nuevo grafo de adaptadores tiene hashes/commit nuevos que deberá registrar el runner. El piloto Kaggle sintético histórico no certifica este grafo nuevo.

## Optimización aplicada, sin prometer speedup

El camino por defecto no construye payloads CSV diagnósticos de BigTrap: BT2 conserva únicamente el callback causal, BT2A elimina llamadas diagnósticas y cálculos exclusivamente de log. Fills/render de BT2A no entran en las reglas detectoras y se omiten; no son labels ni features del experimento. `collect_diagnostics=True` reproduce el contenido ordenado de diagnósticos nativos (sin FILL para BT2A), con hash incremental y sin guardar strings. Ese modo sirve para comparación exacta en tests, no es necesario en producción.

No se afirma mejora porcentual, velocidad MNQ, GPU, mínimo costo ni optimización máxima antes de perfilar con mercado. Todavía se recomputan mapas/percentiles por configuración; compartir ese cálculo requiere claves equivalentes y comprobación, no mezclar historial entre configs.

## Límites explícitos

BT2A: chunk máximo 100000 ticks, buffer máximo 1000 y lookback máximo 5000 por defecto; activos 100000 y capturas por chunk 200000. BT2: activos/capturas por barra 100000 y celdas por lado 10000. Son presupuestos técnicos revisables, no poda de señales ni nueva definición del indicador. Si un parámetro exige más historial/window, se rechaza ese presupuesto; nunca se reduce el parámetro. Un fallo durante ejecución envenena el stream y no devuelve un receipt truncado.

Las clases no son loaders ni otorgan acceso a datos. No hay serialización de resume ni promesa 24x7. El replay actual todavía recibe arrays/receipts declarados; la prueba integrada concatena únicamente fixtures inventados. No usarla como permiso para juntar todo MNQ en RAM o exportar Frames.

## Evidencia

- Todas las 32 configuraciones BT2 y 32 BT2A del roster conservan eventos causalmente capturados y diagnósticos contra los kernels fijados, sobre el mismo fixture inventado del piloto. Los parámetros/warmup son completos. La etapa anterior ya comprobó las 32 AVZ.
- Chunk cuts arbitrarios, cubetas parciales, session roll, ns compartidos, lookback no lleno, score modes, lifecycle, buffers mutables, source drift, capacidad y clocks inválidos están cubiertos.
- Las tres familias estatales producen los mismos racimos, episodios triples y llegadas que el pipeline de referencia; variar el corte no cambia IDs o episodios. Camino sin CSV produce las mismas capturas en pruebas específicas.
- Un test inicial asumía que el fixture llenaba siempre 500 buckets; configs de 100 ticks sólo generan 300. Se corrigió la expectativa a min(lookback, buckets completos observados), sin tocar parámetros, algoritmo o tape.
- La transformación inicial de BT2 intentó sustituir también los `continue` internos. El censo rechazó el código antes de ejecutarlo; se restringió al bucle primario. La versión final conserva íntegros los bucles de filas/lifecycle.

## Siguiente implementación

1. Constructor por lotes de barras y ambos footprints, compartido por bar spec; conservar desempates/cohortes de timestamp y carry TOTAL al cruzar entregas. No construir cada chunk independientemente y concatenar.
2. Lector Kaggle del scope existente, presupuestos conjuntos, captures privadas por lotes y replay compatible con disponibilidad y estado intersesión. No nueva auditoría de datasets.
3. Piloto real de costo/densidad/ocupación de las 96 configs y perfiles por etapa. Sin elegir configs por outcomes, sin P&L ni auto-promoción.
4. Expandir sólo después de ese perfil, con escenarios/labels congelados y análisis incremental de las interacciones, controles de ocupación/densidad, llegada/orden/flow, carry separado, estabilidad y multiplicidad.

No se lanzó aún el estudio cartesiano de confluencias ni se obtuvieron resultados de mercado nuevos en esta etapa.
