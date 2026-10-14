# AVZVOL: selección, warmup y corrección del alcance

## Resultado que corrige la interpretación anterior

La QA de archivos completos no es la selección de sesiones de eventos. Resolver v15, con SHA previamente fijado, selecciona261 sesiones MNQ. Todas tienen resumen publicado y coinciden exactamente en conteos; ninguna tiene menos de2500 registros. Todas las153 sesiones escasas del diagnóstico anterior están fuera de selección. Son261 fechas distintas; no hay dos contratos seleccionados para una misma fecha. No se encontró evidencia de corrupción del dataset por estas alertas.

El mínimo de registros entre las sesiones seleccionadas es778.943. Hay11 intervalos adyacentes mayores de60 s en el conjunto seleccionado; no se los llama pérdidas de datos ni se eliminan sesiones por esto. Su presencia no acredita incompletitud y su ausencia tampoco garantiza feed completo.

## Separación exhaustiva de las560 sesiones de fuente

| Cohorte | Sesiones de fuente | Con menos de2500 registros |
|---|---:|---:|
| Seleccionadas para eventos | 261 | 0 |
| No seleccionadas, intervalo nominal de warmup | 121 | 43 |
| No seleccionadas, intervalo nominal de eventos | 45 | 19 |
| Fuera de la ventana nominal de lectura | 133 | 91 |

Estas categorías son excluyentes y suman560. La categoría seleccionada tiene prioridad. Para las restantes se cruzan intervalos NOMINALES Chicago17h con límites de lectura/warmup del contrato, no first/last de cada registro individual. Por eso se dice candidato a warmup, y NO conteo exacto de ticks dentro del warmup. Dos sesiones no seleccionadas de esa categoría cruzan un límite nominal; no se presentan sus totales de fuente como totales recortados. Las barras diagnósticas fuente se reinician por sesión; no prueban paridad con la construcción continua legacy.

## Salto extremo: fuera de eventos, posible entrada a calibración

La sesión de MNQ09-26 con el salto1419 ticks tiene23479 registros y no está seleccionada para eventos. Está dentro de la ventana nominal de warmup de ese contrato. No se puede concluir que el salto invalide outcomes seleccionados, ni que no pueda influir en la calibración histórica. Se medirá esa influencia dentro del pipeline antes de analizar efectos; no se censura usando resultados ni se inventa precio/volumen intermedio. El máximo salto adyacente en la selección es389 ticks: un máximo no prueba error de feed ni un recorrido operable.

## Lo que se corrige y lo que permanece

- Baja actividad y solapamiento del archivo completo: no son defectos de las261 sesiones de eventos.
- Timestamp repetido: no es duplicado de trade demostrado. La secuencia local se conserva; la velocidad con tiempo cerono se inventa. No tenemos aquí el porcentaje de barrascon tiempo cero específico de selección, y no trasladamos el3,07% del archivo completo.
- Matching de conteos: acreditado por dos caminos. No es certificación de cada hueco, reloj, aggressor o calendario.
- Catálogo: define una selección histórica versionada. Sus reglas usan componentes retrospectivos documentados; esta campaña autorizada es exploratoria/descriptiva, no validación automática de selección ejecutable as-of.
- Warmup: separado de eventos. Nunca aprobar retrospectivamente un evento por actividad final de sesión ni truncar su historia usando outcomes. Registrar calibración suficiente/pasada por bucket.
- Picos: inventario causal mantiene fecha de confirmación; estados finales/merges offline no se usan como si fueran conocidos antes.
- No se abrió holdout, no se ejecutaron nuevas hipótesis de precio ni P4/P&L.

## Proveniencia y reproducción

Inputs: CSV y revisiónQA de PR111 commit b9155170cb63e6a8f42976969379eb322f2f78da; revisión de metadatos en main 4579f5512b150a440d0bd6ea3115a5032ec8d0f0; resolver v15 con SHA 9b21eeff751d4397465fcc6831ea615b7dd401a5605a5997f52c8bfd9248117c. `reconcile_selection.py` documenta las rutas de esta sesión y usa pandas; no se lo presenta como runner portable.

El CSV derivado publicado usa LF y el pin local original de PR111 corresponde a CRLF. Se verificó exactamente que reconstruir solo CRLF restaura ese hash. Ambos hashes se conservan en evidence.json; no se modificó ningún parquet ni se cambió silenciosamente un pin de ticks. La anterior comprobación de archivos de texto al publicar comparaba strings normalizados; no acreditaba igualdad binaria CRLF/LF del CSV.

Checks independientes:261 conteos del resolver por lookup directo en csv.DictReader;153 claves escasas disjuntas de la selección; merge one-to-one, sin pérdidas ni duplicaciones; categorías exhaustivas. El profiler avisa que fechas son texto y se parsean explícitamente. Sus tasas por días calendario y sumas de máximos no se usan: mezclar contratos solapados o sumar máximos carece de interpretación.
