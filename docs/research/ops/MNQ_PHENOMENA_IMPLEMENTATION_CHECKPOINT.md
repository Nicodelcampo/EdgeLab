# Piloto P0 de absorción/exhaustion — checkpoint de implementación

**Motor de medición y runner privado implementados; notebook/host aún no empaquetado ni enviado.** No resultados nuevos de mercado. La última consulta del slug de confluencia devolvió RUNNING; no se inició una carga concurrente. No existe una cola/daemon que lo lance automáticamente al terminar.

## Trabajo nuevo

- `confluence/phenomena.py`: censo del primer trade de cada celda de5s y ventanas retrospectivas5/20/60s; volumen total/comprador/vendedor/no clasificado, frecuencia, tamaño medio, cobertura de cotización/signo, presión relativa a ventana previa, progreso/rango/recorrido de midpoint y dirección desde el pasado.
- Corte exacto en índice/secuencia del anchor, no inclusión de ticks posteriores del mismo timestamp. Midpoint en medios ticks; interiores sin default BUY; gaps, falta de historia y cotizaciones ambiguas conservan estados UNKNOWN.
- Prefix sums compartidas por sesión; tres ventanas sobre los mismos componentes. No construir footprints, indicadores, joins de zonas ni leer outcomes para P0. Se conserva referencia directa NumPy para extremos.
- `confluence/phenomena_pilot.py`: consume el lector existente dentro de un host Kaggle, verifica sesión y escribe filas de features sólo en directorio temporal privado, nunca en `/kaggle/working`. Recibo exportable de conteos/timing/hash/tamaño/RSS del proceso, sin features ni ticks.
- Plan separado `MNQ_PHENOMENA_P0_PLAN.json`: sesión2026-06-16 ya elegida en el piloto de confluencia, límites de sesión natural17h Chicago/22h UTC. No nueva selección por outcomes ni QA del dataset.

## Medición versus clasificación

Se pueden medir presión/progreso/decaimiento sin declarar que hubo absorción real. P0 NO ajusta percentiles, no etiqueta A/E ni produce respuestas futuras. `MEASURABLE_PAIR` significa ventana actual/previamente observable y dirección estimable; no diagnóstico físico. La cobertura de signo se reporta sin ocultar volumen ambiguo; antes de clasificar habrá que fijar su requisito, historia de cuantiles y política científica completa.

Gap2s y cobertura de cotización80% están fijados para **este piloto de medición**, antes de outcomes. Son políticas conservadoras propuestas, no hechos verificados sobre calidad del feed. Se reporta su pérdida de soporte; baja observabilidad no se convierte en detector negativo. Las primeras2W de la sesión quedan incompletas: no se acorta warm-up de un indicador, porque ninguno se ejecuta y no se ajustan umbrales en P0.

El progreso es diferencia entre primer y último midpoint registrado **dentro** de la ventana abierta por izquierda/cerrada por anchor, no cotización continua o precio sintético en el instante del borde. La cinta de cotizaciones es la disponible en filas de trades. Path sólo suma pasos con ambos extremos de cotización válidos; debe interpretarse con cobertura, no como recorrido completo cuando falta información.

## Optimización: resultado negativo preservado

`MNQ_PHENOMENA_SYNTHETIC_BENCHMARK.json` compara una pareja secuencial sobre tape inventado, con500.000ticks y1.000anchors: resultados lógicos idénticos; el candidato de extremos por bloques tuvo mayor tiempo que las reducciones NumPy directas en ese fixture. **No se adoptó el candidato.** No hay speedup de Kaggle demostrado, ni repetición suficiente para una conclusión general de rendimiento.

`benchmarks/phenomena_measurement.py --out RECEIPT.json` permite repetir el microbenchmark, siempre sintético. Se preserva la comparación original; una segunda ejecución se conservó localmente como chequeo de reproducibilidad, no se eligió el intento más favorable. Pico RSS del benchmark corresponde al proceso sintético conjunto, no por variante ni a mercado.

## Tests y límites de preparación

Pruebas nuevas: oráculo independiente de sumas/ventanas y rangos, prefix/append, ticks con timestamp idéntico, espejo de signos, UNKNOWN/interiores, cotización inválida, gaps, capacidad sin truncación, volumen cero, holdout, orden, conteos y aislamiento Kaggle/directorio privado. Recibo `MNQ_PHENOMENA_IMPLEMENTATION_RECEIPT.json` fija hashes y resultados de suites.

El runner mide RSS del proceso Linux por `getrusage`, no descendientes/cgroup; el host con control de memoria/CPU/process-group y source/bundle pinning todavía debe empaquetarse. La presencia de una variable de entorno Kaggle **no autentica autoridad** ni sustituye esa vinculación. El plan no permite outcomes/holdout/P&L ni writer canónico.

## Siguiente ejecución concreta

1. Cuando se observe un estado terminal de la corrida de confluencia, empaquetar un notebook privado separado con esta fuente/build/plan fijados y límites de host; no cambiar la V3.
2. Ejecutar P0 de una sesión, exportar sólo recibo agregado y registrar observabilidad/costo. Nada de campañas históricas repetidas.
3. Usar esos conteos para dimensionar atlas/soporte; congelar calibración pasada y política de etiquetas antes de resultados futuros. Luego medir respuestas e interacciones con zonas como hipótesis separadas.

No autorreplicación, no promoción y no servicio24/7. Dataset/holdout/permisos y riesgos exploratorios previamente aceptados no se redefinen desde este checkpoint.
