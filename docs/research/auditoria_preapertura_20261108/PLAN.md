# Auditoría de concentración y cruce de noticias: PREAPERTURA ES y NQ

Estado: EN CURSO — diagnóstico retrospectivo, no una nueva validación ni un cambio de regla.

## Pregunta y alcance

Revisar las dos celdas ya seleccionadas, para identificar concentración en grandes ganadoras y si las operaciones históricas podrían atravesar noticias USD de impacto alto. En las series originales se guardaron las horas de decisión pero no las de llenado/salida; se recomputarán las mismas operaciones con la opción existente `precios=true` para obtener esas marcas. No se proponen ni seleccionan filtros por rentabilidad y no se cambia la estrategia congelada. No se abre ni se consulta nuevamente el holdout.

## Datos, reglas y procedimiento fijados antes de recomputar horarios

- Código del kernel histórico `e83480d13932a999e6a3683562623d38737da370124988591789b7675231ac93`; reutilizar el fuente original y módulos embebidos, cambiando exclusivamente período si corresponde y `PARAMS` para añadir `precios=true`. Fuente de ES/NQ en los kernels históricos de DESC `nicolasbuttaro/embudo-preapertura-{es,nq}-rec-desc-analizar-regla-202`. `ANALIZAR_REGLA`, neto en R, mismas fricciones canónicas de origen.
- Dataset privado `nicolasbuttaro/edgelab-liquid-ticks-20261014` v4 y catálogo `edgelab-data-catalog` v18 o versión disponible: comprobar hash de manifiesto de release `db9c42cdb714634b131fc8ff886cda67771bea6070d27c0e56e2d2fd6eb14ce5` y presencia de ES/NQ; si cambia la fuente o la reproducción no coincide, no atribuir el resultado al histórico.
- Tramos separados: descubrimiento 2025-08-05 a 2026-03-31; réplica histórica 2026-04-01 a 2026-09-30. El segundo tramo ya fue consultado para la elección de estas celdas: no es validación independiente para ellas.
- ES celda `[2,0,1,0,0,5]`, cortes `ancho_rango=[1.9468545997568203,2.725383920505872]`, fricción 0.8877 puntos. NQ celda `[2,0,0,0,1,5]`, cortes `[1.8566580922200926,2.6704467299827273]`, fricción 1.5455 puntos. Sin modificar cortes, TP, stop o política de noticias.
- Comparar por fecha, hora de decisión, riesgo y R neto con los cuatro archivos publicados en `docs/research/regimen_corto_20261106_recomputo/PREAPERTURA-{ES,NQ}__{desc,oos}.json`; exigir igualdad numérica con tolerancia 1e-9, sin duplicados ni sesiones extra. Si falla, publicar discrepancia y no inferir los cruces como si fueran de las operaciones originales.
- Con la versión exacta del calendario de eventos embebida en ese kernel, cotejar cada intervalo de llenado y salida con noticias `tier1` ±1 minuto. Las marcas son de cierre de vela M1, no tiempo exacto de tick: distinguir cruces claros de casos de borde ambiguos. Una advertencia de calendario incompleto no garantiza ausencia de noticias. Sólo conteos agregados; los precios y el detalle de operaciones quedan privados.
- Concentración: reportar suma de R total y de las cinco mejores por cada instrumento y tramo; el remanente es sensibilidad descriptiva, no un filtro ejecutable ni un nuevo resultado fuera de muestra.

## Interpretación y límites

Ninguna de estas métricas promueve una regla. Si aparecen cruces, no fingir que eliminarlos del registro simula una salida antes de noticias: exigiría una estrategia hija, pre-registro propio, pruebas de causalidad y contabilización de multiplicidad, y nueva validación sin aprovechar el holdout para escoger. CFD mide un mercado y costo distintos: antes de medirlo hay que congelar hipótesis, ventana y política de costos, y no llamarlo réplica de futuros.

## Aporte al referente

Auditar ejecutabilidad y concentración de riesgo sin seleccionar con el holdout ni alterar las reglas de PREAPERTURA.

## Enmienda técnica previa a la ejecución

La API de conexión rechaza la carga del kernel autocontenido por tamaño. Se adjunta como fuente privada la salida del kernel original de DESC, que contiene su carpeta `pkg`; el lanzador compacto verifica el SHA-256 de **cada módulo** frente a `MODULOS_SHA` del código original antes de importarlo. Si falta o difiere uno, aborta. El cuerpo de `embudo_main` es el original; las únicas diferencias de parámetros son las fechas para cada tramo y `precios=true`. Esta adaptación de transporte no cambia hipótesis ni reglas. Los notebooks son CPU, privados y sin internet.
