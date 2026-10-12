# Cierre acotado del piloto y siguiente optimización

## Resultado real V2

API ERROR, source/metadata/version exactos contrastados por host. Receipt de fallo sellado por boot: UNCLASSIFIED_ENGINE_ERROR, causa específica desconocida. Progreso: 26 sesiones reportadas completas, incluida target (2451028 ticks); 6296969 capturas acumuladas y tríadas 0,1 completadas. No hay censo final 32/32, conteos finales por configuración ni perfil de etapas exportado. El wall de 2559.058080572 s no permite atribuir cuello de botella. RSS muestreado child no equivale a peak del job.

El límite de 3M del v1 fue superado en v2 sin detener el procesamiento de target. Eso no identifica la causa del fallo geométrico posterior ni confirma retrospectivamente la causa del v1. No recortar parámetros/racimos por resultados ni presentar un fallo de capacidad como prueba de un indicador.

Inventario MCP devolvió vacío. Se descargaron por versión inmutable únicamente boot/failure/progress agregados, con seal de failure verificado. No se afirma inventario exhaustivo ni firma de custodia remota. Source, eventos, SQLite y logs privados no se descargaron.

## Supervisor implementado

`terminal_acquisition.acquisition_plan` exige intento/version/pins terminales del journal; máximo cuatro archivos allowlist y 1 MiB por archivo (4 MiB total). No ZIP total, paths arbitrarios o inferencia de éxito. Failure/partial son opcionales en estados de error: un kill/retrieval failure puede no tener receipt child; su ausencia no autoriza inventarlo.

`review_failure` valida bytes/hash físico, plan/package, flags de scope, categoría cerrada y progreso agregado ordenado dentro de límites. Vinculado al cierre real v2 en `MNQ_CONFLUENCE_V2_SUPERVISOR_CLOSEOUT.json`. El resultado sigue FAILURE_PRESERVED_NOT_COMPLETE_CENSUS. Es revisión local del agregado, no autenticación de Kaggle, certificación científica o permiso de reintentar.

`review_partial` comprueba seal de boot, scope/roster/prefix hashes, cross-foot de 96 conteos y orden de triadas. Siempre PARTIAL, nunca censo final. Respuestas de pérdida de datos, tiempos no finitos, campos arbitrarios, identidad conflictiva y sobreafirmaciones se bloquean.

La descarga MCP/HTTPS del hito real fue realizada por el host actual; no hay daemon/network adapter permanente. El journal sólo presupuestó su consulta de status cooperativa, no las llamadas de metadata/descarga de toda la sesión. El límite de bytes del planner requiere enforcement del host antes de red/escritura. No se afirma scheduler, distributed exactly-once, fencing ni restore automático.

## Instrumentación preparada para próximo intento

- Categorías precisas para límites pair/triple/join/racimo y conflictos causales.
- Tipo de excepción, **sitio de módulo cerrado** y línea de source; no mensaje libre, traceback, rutas, locals, precios o IDs.
- Receipt parcial atómico tras cada sesión y tríada; guarda conteos/hashes de prefijo y tiempos agregados aunque falle la etapa siguiente. Boot sella su hash si existe.
- Timings separados de encode/hash, insert/commit e index. **Son subpasos anidados en los tiempos de detector, no aditivos.** La última receipt parcial no incluye todo el trabajo del subpaso que falla ni una memoria medida.

Tests sobre Parquet inventado provocan un fallo de geometría posterior, conservan 96 prefijos y una tríada finalizada, rechazan su interpretación como censo completo y verifican hashes/cross-foot. No se parcheó v2 ni se atribuyen sus receipts antiguos a esta instrumentación nueva.

## Optimización medida, todavía no adoptada

`compact_store.ClusteredPrivateStore`: candidato WITHOUT ROWID, una B-tree clustered en lugar de tabla + índice secundario. Mismos payloads/hashes/lifecycle y orden; sin eliminar capturas ni geometrías. No seleccionado por el runner/paquete de mercado.

Microbenchmark sintético fijado: 100000 records por variante, 96 configs, tres pares de bases nuevas, orden de variantes alternado, salida lógica recontada al leer todas las filas. Ver `CONFLUENCE_STORAGE_BENCHMARK.json` para mediciones reales y hashes de source. El ratio total baseline/candidate fue inferior al umbral orientativo 1.05 del screen existente: **no justificar adopción por velocidad**. Menor almacenamiento por sí solo tampoco demuestra mejora integral ni memoria del job.

No control de OS cache cold/warm ni peak RSS completo, por lo que este microbenchmark no satisface la aprobación productiva del BenchmarkPolicy. El primer ensayo quedó fuera de evidencia porque se editó source durante su ejecución; el resultado fijado posterior controla pins al inicio/final. No publicar el ensayo descartado como validación.

## Eficiencia útil, no sólo rapidez

Antes del cartesiano grande: completar censo técnico, separar oportunidades de exposición de arrivals y fijar respuesta/horizonte/controles. Comparar aporte incremental de interacciones sobre mismos anchors, controlar densidad/ocupación y dependencia AVZ-racimo, conservar censuras/negativos/carry. No seleccionar configuraciones por número de coincidencias ni outcomes. Dataset resuelto, sin nuevas auditorías, holdout cerrado y sin P&L.

Próximo intento sólo después de persistir este source: mismo estudio acotado, diagnóstico/partial agregados nuevos y almacenamiento baseline. No expansión del universo ni adopción del candidato. Su propósito es localizar el fallo y conservar trabajo útil; no contar el reintento como muestra independiente. Producción autónoma/custodia/writer aprobados siguen pendientes.
