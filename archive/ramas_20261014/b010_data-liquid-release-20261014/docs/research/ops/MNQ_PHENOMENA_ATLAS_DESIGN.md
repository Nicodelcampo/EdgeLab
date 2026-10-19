# Atlas MNQ target-free: tres sesiones, mismo estimador P0

## Diseño congelado antes del envío

Trade dates2026-06-12/15/16: últimas tres fechas hábiles por calendario dentro de la ventana de investigación ya usada en V3; no seleccionadas por rebotes, resultados, amplitud de presión ni cobertura. Se repite June16 únicamente como parte del mismo atlas agregado, no auditoría del P0. Si una sesión no existe/no cabe, fallar sin reemplazo automático. Esto es un piloto descriptivo local, no muestra representativa de todos los regímenes/contratos ni réplica independiente del desarrollo histórico.

Fuente MNQ09-26 versión2 ya vinculada. Misma ancla causal primer trade por celda5s, ventanas5/20/60s, regla quoteside y gates de P0: gap2s y quote-volume80%. No calibración de estados, outcomes, detectores, P&L o acceso al holdout. No cambiar cobertura al ver datos. Principal20s, restantes descriptivas; anclas/ventanas/sesiones comparten contexto y no representan ensayos IID.

## Producto útil y preguntas

1. Cobertura: conteos MEASURABLE/UNKNOWN y causas exclusivas. Regla determinista: primero current noOBSERVABLE; luego prior noOBSERVABLE; luego flujo previo con signo cero. No sumarlas a la tabla conjunta current|prior (son dos representaciones del mismo censo). El status de cada ventana conserva el primer gate fallido del P0: NO inventario de todos los motivos simultáneos. `QUOTE_UNKNOWN` mezcla quote endpoints y gate de volumen; no diagnosticar cuál sin evidencia adicional.
2. Medición: cuantiles10/25/50/75/90 lineales exactos por sesión/ventana, sólo con soporte>=100. Presión absoluta dirigida y previa, ratio presión, frecuencia/volumen/tamaño medio, progreso dirigido actual/previo, cobertura de signo; presión y poco avance no se reducen a un ratio inestable. Separar métricas condicionales a parMEASURABLE de métricas currentOBSERVABLE; los denominadores se publican.
3. Convivencia continua: censo6×6 de ratio presión × progreso dirigido. Cortes fijados antes del envío: presión .25/.5/1/2/4; progreso -8/-2/0/2/8ticks. `searchsorted_right` asigna igualdad al intervalo que comienza en el corte. Bins descriptivos, NO etiquetas A/E ni selección de configuraciones. Cuantiles no se convierten automáticamente en thresholds. Histogramas suman exactamente pares medibles.
4. Próximo protocolo: descubrir limitaciones/soporte para después congelar A/E/coexistencia/ninguno/UNKNOWN y respuestas/controles. Baseline de componentes crudos vs transformación A/E; controles sin zonas antes de la interacción AVZP2/racimo/BT2/BT2A. No decidir endpoint por lo que suba en este atlas.

## Optimización y presupuesto

Un procesoCPU: descargar fuente una vez, pushdown por row groups para tres rangos naturales, liberar arrays entre sesiones. Prefijos compartidos P0, sin detectar96configs, guardar millones de capturas ni toda la gráfica. Hash del stream privado en memoria, sin exportar ni persistir filas. Cuantiles exactos sobre listas sólo de anclas (máx250k/sesión), no sobre cada tick. No aproximación sketch/sampling que altere estimador.

Máx3sesiones,5Mticks/sesión,8Mtotal;900s runner/CPU,600s retrieval,1500s parent,1800s notebook;RSSstop4GiB(sampled child),AS6GiB. Un envío manual finito, sin reintentos automáticos. Journal nuevo de este batch explícitamente limitado a una intención; no reset/reembolso del P0 ni prueba de cuota global compartida con otros agentes. Watch común conserva historial y presupuesto de consultas existente.

Export allowlist: `phenomena-atlas/boot-receipt.json`, `atlas-receipt.json`, `runner-failure-receipt.json` (sólo si falla, type cerrado sin mensajes/paths). Máx1MiB/archivo y4MiB total adquisición. Recibo final generado todo-o-nada tras las tres sesiones; ningún prefijo se etiqueta completo. No descargar privado para debug. Recursos son de proceso/sampling, NO cgroup del job.

## Rigor antes de envío

Tests sintéticos: misma elegibilidad/denominadores P0, cuantiles contra NumPy, precedencia/joint de causas, cortes exactos, suppression de soporte, NaN/Inf/mismatch/caps, plan fijo/cambio de gates, falta de sesión y Kaggle/output guards, package privado CPU/source. Mantener P0 publicado intacto. Publicar código/plan antes de empaquetar, fijar sourcecommit +bundle+plan hashes, persistir SEND_UNCERTAIN antes de SaveAndRunAll, reconciliar ID/version/source exactos. Que COMPLETE sea del proveedor no sustituye review de recibos.

No servicios Debian ni writer EdgeBrain activados por este piloto. Leer handoff vigente para integración de un único host, locks, releasepin y cierres transaccionales.
