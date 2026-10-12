# Handoff para Claude — Research Ops autónomo

## Latest continuation: full primary-grid parity

Read `FULL_PRIMARY_GRID_PARITY.md` and `LATEST_CONTINUATION.json` first. All11,340 stored MNQ09-26 primary-effects rows PASSED all19fields (215,460 checks), including exact float round-trips against original CSV, on already-thinned events only. Kernel138362721 v1 COMPLETE. No new trial, full-pipeline claim or adoption.456local Research Ops tests. Do not rerun this completed replay.

## Previous continuation: existing operational snapshot and technical replay

Read `ANCHORED_MEMORY_AND_MNQ_REPLAY.md`, its evidence and `LATEST_CONTINUATION.json` first. Actual 10-record Kaggle operational ledger now bound read-only with both anchors/receipt. NOT a live writer destination or complete scientific history. MNQ resampling technical replay COMPLETE: exact parity on60 fixed cells, ~3.38x resampling-substep ratio of medians only. Candidate not adopted; preserve aggregate/interpretation, never relaunch the campaign.

## Previous continuation after the MNQ campaign review

Read `SIGNED_DELIVERY_AND_BOUNDED_EXPERIMENTS.md` and `LATEST_CONTINUATION.json` first. New offline signed-custody receiver, local reviewed canonical technical writer/ack, bounded experiment-charter review and single-process profiling are implemented/tested, not deployed or connected to production keys/ledger. Historical sections below preserve previous milestone limits. Final focal MNQ09-26 audit and five-replica interpretation are in research commit `eca53ec2277536b89f3b68cc39770c19dcba2483`; do not relaunch it. No real source selection or telemetry signing authority was fabricated.

## Entrada y estado real

Continuar en **`feat/research-ops-supervisor-mvp`**, PR [#117](https://github.com/Nicodelcampo/EdgeLab/pull/117), todavía **draft**. El código fuente verificado antes de este handoff es `ae3dfd3f42106f6d33e0a5f53112ac9d73129d02`, sobre base `4579f5512b150a440d0bd6ea3115a5032ec8d0f0`.

Los **40 archivos modificados de ese commit ya están publicados**. `HANDOFF_SOURCE_INVENTORY.json` enumera sus tamaños y SHA256. No hay un nuevo ejecutor escondido en el chat que haya que recrear. No confundir este prototipo con un agente de mercado completo: **no está desplegado 24/7**, no tiene research externo despachado, modelos pagos, adaptador de mercado ni fuentes reales vinculadas. No mergear a main ni activar nuevos permisos automáticamente.

El usuario pidió un sistema que diseñe, audite, ejecute y analice investigación buscando edge; debe integrar **EdgeBrain, la biblioteca de artículos y research cuando exista un vacío relevante**, conservar fracasos/invalidaciones y prestar atención especial a patrones prometedores sin convertir selección retrospectiva en validación.

## Qué está implementado

1. **Operación sintética:** cola SQLite transaccional, eventos encadenados, presupuesto reservado antes del subprocess, recibos exclusivos, un job RUNNING por cola, worker POSIX fijo y observador read-only. Sin shell/código generado ni reintentos ciegos.
2. **Gate y paridad:** puente metadata-only a los gates canónicos; paridad sintética de rango causal previo. Permiso exploratorio no certifica fuente.
3. **Trabajo/rendimiento:** plan sellado de las 18 familias, admisión conservadora sin lanzar, memo causal LRU y microbenchmark con escenario favorable y contraejemplo sin hits. No demuestra aceleración integral de MNQ.
4. **Knowledge-first:** recall del hipocampo/índice canónicos y export SSRN context_pack; planner finito para vacíos/contradicciones, directivas favorables y contrarias, propuestas falsables no autorizadas. Sin memoria/biblioteca paralela.
5. **Recuperación portable:** export/inspect/restore de cola sintética, SHA/tip externos exigidos, preservación de presupuesto y RUNNING, sin auto-resume. Simulación de pérdida en fixtures; no almacenamiento remoto, witness latest ni fencing real vinculados.

### Lectura recomendada

- **Nuevo hito: [Importación local de cierres + outbox durable](CLOSEOUT_LEARNING_OUTBOX.md).** CLI explícita, idempotencia transaccional y snapshot/restore sin entrega. No productor remoto ni writer canónico; pendientes de integración. Evidencia `CLOSEOUT_OUTBOX_TEST_EVIDENCE.json`.

- **Nuevo: [Aprendizaje poscorrida y optimización continua](POST_RUN_LEARNING_AND_OPTIMIZATION.md).** Planificador offline y screen de benchmarks, sin permisos de ejecución o activación. Código `tools/research_ops/post_run.py`; evidencia `POST_RUN_TEST_EVIDENCE.json` y telemetría técnica `POST_RUN_MNQ_TELEMETRY.json`.

- [Base y demo](RESEARCH_OPS_MVP.md).
- [Integración/gates/paridad](INTEGRATION_PREFLIGHT_AND_PARITY.md).
- [Rendimiento/unidades congeladas](PERFORMANCE_AND_FROZEN_WORK_UNITS.md).
- [EdgeBrain + artículos + research](KNOWLEDGE_FIRST_RESEARCH.md).
- [Recuperación portable](PORTABLE_QUEUE_RECOVERY.md).
- `config/research_ops_knowledge_sources.json`.
- `tools/research_ops/` y `tests/research_ops/`.
- [Pruebas de este handoff](HANDOFF_TEST_EVIDENCE.json) y [estado operacional](CONTINUATION_STATE.json).

## Verificación reproducible

Snapshot limpio del commit de código: **208 tests Research Ops + 18 de navegación PASS**, catálogo `PASS_NAVIGATION_ONLY`. La API de GitHub también mostró SUCCESS para los checks del head de código: synthetic Python3.12/3.13, navigation-only y cpu-base. La evidencia distingue estos checks de los del nuevo commit documental, aún no comprobados al prepararlo. No se afirma haber corrido toda la suite del repo.

Desde la raíz del checkout, en un entorno de pruebas separado del runner MNQ:

```bash
python -m pip install jsonschema==4.23.0
python -m unittest discover -s tests/research_ops -v
python -m unittest discover -s tests/navigation -v
python tools/edgelab_catalog.py check --json
```

Para una demo sintética, seguir `RESEARCH_OPS_MVP.md` con directorio de estado nuevo. No usar la cola de otro proceso ni ejecutar texto de hipótesis como código. Restore conserva jobs RUNNING: requiere revisión de liveness/fencing externa, no repetición automática.

## Campaña MNQ: separar del desarrollo del sistema

Las corridas pesadas se ejecutan en **Kaggle**, no necesitan un VPS nuevo para recuperar resultados. Un eventual host de orquestación persistente es una decisión distinta del proveedor de cómputo. No moverlas ni relanzarlas por leer este handoff.

- Rama de investigación: `research/avzvol-longevity-full-grid`, separada de este PR.
- Protocolo científico congelado: `9125197dc6098100459f36a3d90a5c7b7aa4f9c0`.
- Matriz original: **1.536 configuraciones × 1.260 reglas = 1.935.360 pares por contrato**.
- Longevidad: **18 familias y 2.772 grupos landmark/regla**.
- Focal: **594 cohortes × 5.400 condiciones = 3.207.600 definiciones por contrato**, colapsando máscaras equivalentes. No reemplaza la matriz original.
- Banco congelado de **34 recetas**, SHA256 `59184949160128b524c7a47290889d4bdf55c6c0ff214c8a7fc4eac411e0ee06`; no reseleccionar con resultados nuevos.

El piloto MNQ12-26 estaba cerrado antes de las nuevas réplicas. De las nuevas corridas, están recuperados/auditados los análisis focales MNQ09-25 y MNQ06-26, y las matrices MNQ12-25 y MNQ09-25. El snapshot exacto de notebooks/versiones y pendientes está en `CONTINUATION_STATE.json`; **no es estado vivo** y debe consultarse Kaggle antes de cualquier decisión.

Evidencia preservada:

- [Primer focal y recuento SQL](https://github.com/Nicodelcampo/EdgeLab/commit/605d3ff10121fe3397facccb79e1d96f3010c503).
- [Segundo focal + segunda matriz](https://github.com/Nicodelcampo/EdgeLab/commit/235048d9a8658dc7b451b354faf0c2f523721340).
- [Cobertura de todas las definiciones focales exportadas](https://github.com/Nicodelcampo/EdgeLab/commit/0d07675789b6029e0d48eaf8912df93c8b20ba96).

MNQ09-25 tiene 6 candidatos exploratorios relativos al control; MNQ06-26 tiene 10. **Ninguno pasa simultáneamente las bandas absolutas y relativas** en esos contratos. Las recetas congeladas se recontaron desde SQLite privado; la cobertura focal se cross-footeó sobre todos los representantes exportados y sus aliases. Estas cifras no son oportunidades independientes ni edge validado. Las bandas son aproximadas y locales al contrato/pasada, no corrección de todo el historial ni prueba causal.

No abrir holdout, calcular P&L, promover estrategias, certificar fuentes ni ampliar/retunear la campaña por inferencia. La identidad exacta de fuentes recuperadas no equivale a certificación del export original. Preservar censuras, casos sin soporte y todos los intentos, no sólo ganadores. Mantener las fuentes privadas/SQLite/gzip fuera de GitHub; los resultados existen en outputs privados de Kaggle y el repo conserva agregados/hashes/auditores. URLs firmadas/credenciales no se incluyeron en este handoff.

## Próximos pasos, en orden

1. **Terminar/revisar la campaña congelada.** Consultar notebooks actuales; COMPLETE técnico no basta: descargar estado semántico, inventario y outputs, verificar SHA/size, cobertura y recuentos. No repetir jobs RUNNING. Límite operacional aplicado: hasta cinco notebooks Kaggle simultáneos; no es el límite de un único host/cola.
2. **Vincular conocimiento real aprobado.** Export operacional EdgeBrain con custodia/anchors externos; Cortex canónico de PR67 (`5c10da451b164c54133bdb9a4674de43d6fa2d22`) tras revisar dependencias/custodia. No copiar aisladamente su bridge a main. Literatura mantiene `LITERATURE_CLAIM_UNVERIFIED`, no evidencia propia.
3. **Dispatcher read-only + presupuesto durable de research.** Identidad/revisor y autorización de pregunta pública; allowlist de herramientas, recibos de fuente/costo y límites entre reinicios. Defaults actuales del PLAN: 2 rondas/4 consultas/8 documentos/24.000 caracteres/300 segundos/gasto API0. No están ejecutados ni duraderamente impuestos aún.
4. **Control operacional remoto sobre Kaggle.** Identidad del job, versiones, poll acotado, descarga/verificación de outputs, límites de concurrencia y costo, ledger durable, persistencia independiente y witness latest/fencing. No decidir proveedor/cuenta ni pedir secretos hasta requerimiento concreto. Worker sintético no debe convertirse en ejecutor arbitrario.
5. **Acelerar en rama separada y con paridad.** Usar los tiempos reales por etapa en los commits de evidencia. Perfil completo: preparación/JIT, scans/cache, Python por señal, CSV/gzip, análisis/review. Priorizar reutilización exacta de preparación/outcomes, kernels batch, memo medido, salida tipada por batches y fragmentos verificables. Comparar mismas entradas y decisiones; preservar toda la cobertura. Nada de instalar cambios en jobs activos, recortar variantes por outcome o prometer GPU/speedup sin benchmark.
6. **Adjudicación/aprendizaje canónicos y piloto operativo finito.** Registrar fallos e invalidaciones y revisar claims independientemente. Writer al Brain canónico pendiente; no ledger científico paralelo. Despliegue 24/7 sólo tras piloto y aprobación; trading real requiere autoridad adicional.

## Consigna para continuar

> Trabajá sobre PR117/feat/research-ops-supervisor-mvp. Leé este handoff, verificá el estado remoto y corré las pruebas focales. Conservá EdgeBrain/artículos/research condicional y los controles de presupuesto, autoridad, multiplicidad y continuidad. Terminá la campaña MNQ congelada antes de modificar su motor. Proponé el siguiente hito mínimo con tests negativos, evidencia de paridad y límites explícitos; no declares autonomía de mercado ni servicio24/7 por tener una cola sintética.


## Local MNQ receipt bridge

See [MNQ_CLOSEOUT_PRODUCER.md](MNQ_CLOSEOUT_PRODUCER.md) and `MNQ_PRODUCER_TEST_EVIDENCE.json`. The technical-only producer now validates pinned, independently reviewed real receipt bundles, but blocks envelope output without measured RSS and verified execution/input/build binding. This is not live Kaggle ingestion, canonical-memory delivery or optimization activation.


## Performance and scientific information investigation

Read [FASTER_RUNS_AND_EDGE_INFORMATION.md](FASTER_RUNS_AND_EDGE_INFORMATION.md). Exact session-resampling reuse has a local synthetic prototype/benchmark, not real-MNQ or full-job certification. Recovery checkpoint and auditors were persisted first. Next priority is measured longevity substep profiling and exact batch parity on a bounded future shard; keep active jobs/frozen protocol untouched. Scientific information-gain design remains proposed, not enforced.
