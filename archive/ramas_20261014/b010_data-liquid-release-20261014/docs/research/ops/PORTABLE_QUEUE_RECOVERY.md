# Cola portable y recuperación — implementación y límites

## Estado

**Export/inspect/restore de la cola sintética implementados. Host externo, almacenamiento remoto, transferencia automática y witness externo todavía NO vinculados. No resuelve por sí solo la pérdida del host ni restaura MNQ.**

Este hito responde al incidente de continuidad documentado en `CONTINUITY_AUDIT.md`. No inventa checkpoints de contratos, no descarga ticks, no lanza research/mercado ni amplía autoridad. La cola sintética es una prueba técnica, no el ledger científico ni los archivos privados del motor MNQ.

## Implementación

`tools/research_ops/snapshots.py` captura policy, jobs y eventos exactos dentro de una transacción `BEGIN IMMEDIATE`, con verificación del tip suministrado externamente. Incluye recibos referenciados y recibos aún sin commit de jobs conocidos. Recibos desconocidos o entradas inesperadas bloquean exportación: no se eliminan ni se ignoran.

El export es JSON canónico acotado, no una copia arbitraria del filesystem ni un archivo ejecutable. Límites:16MiB totales,400jobs,1024eventos,100recibos,64KiB por recibo. No shell, red, pickle, extracción de rutas o SQL suministrado por el archivo. Tablas/esquemas son fijos; sus datos se insertan mediante parámetros. La validación reconstruye una cola temporal y verifica sus proyecciones, chain, presupuesto y recibos con el Store canónico.

Archivos creados exclusivos, permisos0600; directorio restaurado0700; fsync de datos/directorios. Lectura POSIX de archivo regular con no-follow, tamaño acotado y cambios de tamaño/mtime/ctime detectados. Parent directories deben pertenecer al entorno confiable: no se promete aislamiento frente al administrador, cambios de mounts o adversarios con control del host.

El export NO sobrescribe snapshots. Restauración valida SHA256 externo y tip externo ANTES de crear un directorio destino nuevo y exclusivo. No sustituye una cola existente, no relanza jobs, no reinicia presupuesto ni transforma RUNNING en completado/QUEUED. Un fallo de escritura deja el archivo/directorio incompleto en cuarentena; no hay limpieza/reintento ciego.

Un recibo sin transición terminal se conserva y se señala para revisión. No basta un recibo o un log para asumir que una corrida terminó. Una restauración puede recuperar el estado, no decidir si el worker del host anterior sigue vivo. Antes de cuarentena/adopción se necesita comprobar liveness y fencing externamente.

## Uso — sólo sintéticos

```bash
python -m tools.research_ops.cli --state QUEUE_SQLITE snapshot-queue NEW_SNAPSHOT_JSON --snapshot-id UNIQUE_SNAPSHOT_ID --expected-tip TRUSTED_CURRENT_TIP
python -m tools.research_ops.cli inspect-snapshot RETRIEVED_SNAPSHOT_JSON --expected-sha256 TRUSTED_LATEST_SNAPSHOT_SHA256 --expected-tip TRUSTED_LATEST_TIP
python -m tools.research_ops.cli restore-queue RETRIEVED_SNAPSHOT_JSON NEW_EMPTY_PARENT_DESTINATION --expected-sha256 TRUSTED_LATEST_SNAPSHOT_SHA256 --expected-tip TRUSTED_LATEST_TIP
```

El destino no debe existir; su padre sí. `inspect-snapshot` y `restore-queue` no inicializan la cola default. Ningún comando ejecuta jobs restaurados. El path y los hashes de ejemplo no son permisos ni descubrimiento automático del snapshot más reciente.

## Lo que debe aportar el despliegue externo

1. **Host persistente:** máquina/servicio explícitamente seleccionado; supervisor, identidad, permisos, recursos y parada revisados. No reemplazarlo por otro background job en el entorno temporal de chat.
2. **Store externo independiente:** conservar también outputs reales y recibos, no solamente metadata o hashes. No copiar automáticamente hipótesis privadas, raw ticks o eventos a GitHub. Permisos y política de datos antes de transportar.
3. **Witness de latest separado:** SHA256/tip y contador monotónico conservados por otra autoridad. Un snapshot viejo válido sigue siendo viejo: si se entrega su propio hash/tip como latest, este lector no puede descubrir el rollback. Hashes no son firmas.
4. **Transferencia/readback:** upload, lectura de retorno y comparación de bytes; fallos conservados y sin marcar unidad completa. Esta implementación no hace upload ni acredita retención remota.
5. **Fencing:** no dos workers para la misma unidad después de recuperar un host. El lock SQLite de esta cola sólo serializa su propio archivo; no es un lease entre hosts.
6. **Adaptador de mercado separado:** outputs del motor, identidad congelada de unidad y prueba de completitud científica. Restaurar esta cola sintética no permite saltar18familias o adoptar checkpoints MNQ perdidos.

Todos los resultados devuelven `remote_copy_verified=false`, `external_latest_anchor_verified=false`, `auto_resume_allowed=false` y `market_execution_allowed=false`. No usar el título del módulo como certificado de durabilidad.

## Prueba de pérdida

Tests sólo sobre directorios temporales propios: completar un job sintético, dejar otro RUNNING, exportar, eliminar la fixture original y restaurar en directorio nuevo. Se exige presupuesto intacto, recibo terminal idéntico, job incierto aúnRUNNING y ausencia de dispatch. Otros tests cubren snapshots antiguos, corrupción, reset de presupuesto, missing/orphan receipts, symlinks/FIFO, schemas cerrados, no sobrescritura y escrituras parciales.

El siguiente paso requiere elegir host y almacenamiento persistentes; todavía no están provistos. No se ha retomado MNQ en este hito.
