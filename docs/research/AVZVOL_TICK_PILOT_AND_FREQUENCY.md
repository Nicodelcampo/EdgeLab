# AVZVOL: piloto real de ticks y barrido de frecuencia

## Resultado y alcance

Piloto terminado, no campaña completa. Un contrato MNQ12-26 y 10 sesiones seleccionadas por catálogo. Se ejecutaron 45 pares configuración-regla de retorno parcial y 135 sensibilidades de gaps: 180 grupos en total. Por separado, se recalcularon 1536 configuraciones de detector para censar frecuencia; NO se evaluaron sus resultados futuros en toda la matriz.

Se verificaron 0 eventos fuera del universo permitido. Holdout no abierto, sin P&L, sin promoción P4, sin certificación de feed. No se recortó ni resubió el dataset. Las fuentes originales se mantienen intactas.

## Qué justifica profundizar

Cambiar percentil y window bars transforma la frecuencia del mismo racimo. Con mínimo18 zonas, ventana racimo2000 barras y altura máxima20 ticks:

| Percentil | Window 5 | Window 10 | Window 20 | Window 40 |
|---|---:|---:|---:|---:|
| 80 | 1194 | 40 | 0 | 0 |
| 90 | 112 | 1 | 0 | 0 |
| 95 | 6 | 0 | 0 | 0 |
| 97.5 | 0 | 0 | 0 | 0 |


Counts: nacimientos en barras completas de las mismas10 sesiones; no episodios independientes ni órdenes ejecutables. En este piloto, P80/window5 da1194 formaciones frente a40 con window10. Todas las celdas, incluidos ceros observados, están retenidas. No generalizar a los otros contratos.

El máximo por frecuencia en la malla fue mínimo4/ventana500/altura30/P80/window5: 8764 formaciones en10 sesiones, todas activas. 608 de1536 configuraciones no generaron formaciones. La suma entre configuraciones se solapa y no aumenta el tamaño independiente de muestra. La configuración de mayor frecuencia no es una ganadora predictiva.

**Prioridad de investigación:** llevar las familias densas P80/window5 y sus vecinos menos densos a pruebas de retorno parcial, contando excursiones independientes y días de soporte. No escoger parámetros por su mejor tasa de acierto en estas10 fechas. Comparar con niveles placebo y modelos de precio/contexto sin racimos; exigir aporte incremental, frecuencia y estabilidad conjunta.

## Fuente y filtros efectivamente aplicados

- Fuente documental: catálogo resolver v15; reexportación Kaggle v2 para MNQ12-26. SHA256 exacto y fechas en run-manifest.json.
- Archivo original: 21440578 registros Last, 244126468 bytes; igualdad de pin y ausencia de errores estructurales previos corroboradas. Esto no certifica sincronización, calendario ni clasificación del agresor.
- Ventana leída: 21364648 registros. Entrada detector: 21364647. Un registro de mantenimiento omitido solo del buffer derivado; cero registros no seleccionados posteriores a la primera sesión seleccionada en este archivo/ventana.
- Warmup: fechas observadas previas a la primera etiqueta seleccionada dentro de la ventana histórica45 días; después, solo fechas seleccionadas. No se filtró solo al final del detector.
- Máscara fail-closed: evento fuera de las fechas autorizadas dispara error. Selección global de261 fechas proveniente de PR111; aquí solo se corrieron las10 de este contrato, no las261.
- Convención de sesión Chicago17h, heredada y declarada, no certificada con calendario del proveedor.

## Semántica nueva, no réplica silenciosa

Nombre: SEQUENCE_CAUSAL_TOTAL_MEMBERSHIP_NEW_DEVELOPMENT_VARIANT. Barras de25 registros Last, reinicio por sesión. Cada footprint contiene exclusivamente sus propios registros ordenados y está disponible al cierre. No utiliza información posterior para reasignar registros con igual timestamp.

El footprint histórico NT8subseries usa asignación por timestamps de cierre y filtrado por high/low de la barra asignada: **no es idéntico** a este input. Las estadísticas anteriores no son directamente comparables. El detector puro legado se mantiene para geometría y membresía del racimo; se validó su replay acelerado contra esa referencia, no contra una exportación original NT8 ausente.

Se construyeron 854603 barras y 5119 zonas con P95/window10 para el piloto de resultados. Barras finales parciales conservadas como pasado para calibración, no como origen de eventos. Geometría low0/high0 congelada al nacimiento; no geometría final reconstruida con futuro. Memoria pasada del racimo entre sesiones heredada del algoritmo; señales confinadas a la sesión de nacimiento.

## Prueba de alejamiento y retorno parcial realmente ejecutada

Cinco geometrías: 4/1000/20, 4/1000/30, 4/1000/45, 4/500/45, 5/1000/45. Distancia mínima10/20/40 ticks; retracción25/50/75%. Endpoint probado: tocar el borde del racimo. Horizonte máximo2000 barras, limitado por fin de sesión. Política primaria de gap10 segundos; sensibilidades1s,60s y sin censura de gaps.

Se toma la primera salida del racimo, extremo creciente conocido al momento y primer cruce observable del porcentaje de vuelta. El extremo no se elige retrospectivamente. En el disparador queda fijada la distancia restante al borde y una barrera contraria de igual distancia desde el precio real del disparador. El resultado comienza en el siguiente trade. Si el toque ya ocurrió antes del disparador observable no se concede una victoria gratuita.

**Restricción importante:** es primera salida, no primer episodio posterior que sí llegue a D. Las salidas pequeñas que vuelven antes de alcanzar D/q terminan el intento. El rearmado de nuevas excursiones es una variante pendiente y debe compararse, no reemplazarse silenciosamente.

Features persistidas privadamente al disparador: distancia, tiempos y velocidades de ida/vuelta, barras y registros por distancia, eficiencia de recorrido y flujo firmado por quote proxy con cobertura. Picos confirmados causalmente en barras cerradas, reiniciados por sesión. No se usó el ciclo final de liquidez fusionada. La clasificación buy/sell por bid/ask es proxy, no agresor real certificado; unknown no se convierte en flujo verdadero. Medir estas features NO equivale a demostrar que añaden capacidad predictiva: aún no se ejecutó esa comparación incremental.

## Soporte y por qué no se anuncia ventaja

Las cinco geometrías produjeron 2673 formaciones correlacionadas. 96228 filas de evaluación incluyen no-señales y cuatro políticas de gap; no representan trades ni observaciones independientes.

En la política primaria hubo 927 evaluaciones con señal y 419 disparadores de fuente distintos; estos también pueden pertenecer a excursiones solapadas. Conteos primarios: 510 TARGET_FIRST, 408 OPPOSITE_FIRST y 9 sin resolver al horizonte. Soporte por regla de0 a57 señales y de0 a10 sesiones con señales. No se estima una ventaja usando el porcentaje pooled.

No hay todavía comparación contra azar contextual, controles sin racimos, intervalos agrupados por día/episodio, ajuste por múltiples pruebas ni validación temporal independiente. Las cotas lower/upper de rule-summary.csv son sensibilidad a resultados censurados, **no intervalos de confianza**. Gaps tratados como incertidumbre de observación, no como corrupción demostrada. El análisis no permite inferir fills, rentabilidad neta ni dirección estratégica.

## Pruebas y optimización realizadas

- Cinco tests del adapter;2400 comparaciones sintéticas de pasaje con referencia Python, espejo direccional y3 endpoints.
- Replay racimo:360 comparaciones de prefijos sintéticos y5 arrays de nacimientos sobre mercado real, igualdad exacta con legado sobre el input nuevo.
-30 tramos cortos de ticks fuente cotejados contra algoritmo Python independiente, con disparador, resultado, timestamps enteros y barreras exactas. Muestreo estratificado para validación de software, no población de rendimiento.
-180 resúmenes recontados por csv.DictReader; cero fugas de universo.
- Optimización: un tape de zonas por combinación percentil/window compartido por96 geometrías;16 tapes para1536 configuraciones. Tiempo observado de la malla 56.15s, dependiente del entorno, no garantía de producción.
- Primer intento salió137 por memoria antes de generar labels. Se sustituyeron buffers globales de flujo por sumas locales de cada tramo y se liberó footprint intermedio. Piloto final completado en 14.98s. La recorrección de serialización mantuvo las mismas clasificaciones y no es otra muestra independiente.

## Pendientes explícitos

No ejecutados: seis contratos completos; matriz de1260 reglas futuras por configuración; tocar centro/atravesar racimo sobre toda la malla; rearmado de episodios; filtros y controles de velocidad/imbalance/picos/corredor reciente; inferencia robusta y costes. El siguiente tramo debe mantener la máscara y pins, registrar multiplicidad, separar episodios solapados y probar el aporte incremental de contexto del corredor. No se afirma que quede una corrida en segundo plano.

## Artefactos y reproducción

Adjuntos de repositorio: manifests, evidencia, censos agregados, código y tests. No se publican ticks ni registros event-level con precios/secuencias; permanecen en entorno privado. Scripts son un snapshot de desarrollo con rutas locales explícitas, no runner portable ni productor certificado.

Dependencias: Python3.13, numpy/pandas, pyarrow26.0.0, numba0.63.1. Scripts importan adapter/legacy/reference/pivots del mismo directorio. Fuente debe aprovisionarse en ruta declarada por run_pilot.py y el universo261 fechas/authorization en las rutas documentadas por el código; esas lecturas se pinnean. Procedencia heredada: PR109 referencia pasaje, PR110 QA de fuente, PR111 autorización y reconciliación corregida commit b047753b180090da19fc7a8a7d56a67a6a284df4. El PR nuevo no modifica certificados anteriores ni implica que dependencias no mergeadas estén en main.
