# Research Ops — primera base operativa

## Estado y alcance

**PROTOTYPE_SYNTHETIC_ONLY — no agente autónomo de mercado ni servicio24/7 desplegado.**

Desarrollo nuevo autorizado después de revisar la campaña MNQ. Base:4579f5512b150a440d0bd6ea3115a5032ec8d0f0. Trabajo aislado: no se modifica el controlador, los parámetros, datos, reservas o resultados de la campaña activa. La autorización para construir infraestructura NO autoriza nuevas hipótesis económicas ni acceso al holdout.

Es un módulo operativo acotado para futuros consumidores, no una implementación/reemplazo del ccbus o del planeamiento local no publicado. No importa ni duplica Brain/Factory. Su registro de ejecución NO es el hipocampo científico, no emite certificaciones, no adjudica resultados ni promueve claims. La futura integración necesita los adaptadores y controles canónicos existentes.

Referentes: [Factory#42](https://github.com/Nicodelcampo/EdgeLab/issues/42), [mapa de componentes](../../COMPONENTS.md), [memoria y anchors](../../COMPONENT_MEMORY.md), gobernador recursivo histórico de la rama`feat/edge-brain-learning-governor-20260924`. La propuesta histórica contiene límites/fechas distintos: no se importan como permisos de una campaña nueva.

## Implementado

- SQLite con transacciones`BEGIN IMMEDIATE`, escritura síncrona y verificación del estado materializado contra eventos encadenados.
- Propuestas sintéticas inmutables; IDs únicos, esquema cerrado, tamaño/capacidad limitada, alcance y acción allowlisted.
- Presupuesto finito de intentos y segundos máximos reservado ANTES del subprocess. Los fallos e interrupciones no recuperan presupuesto y no se reintentan automáticamente.
- Máximo un trabajoRUNNING por cola, incluso con claims concurrentes. Reabrir la base conservaRUNNING; una interrupción requiere cuarentena explícita, sin autoasumir finalización.
- Worker POSIX de código fijo: sin shell, entorno mínimo, directorio temporal, timeout, límites de CPU/memoria/tamaño de archivo y eliminación del grupo de procesos al vencer el timeout.
- Recibos exclusivos y hashes: no se sobrescriben; ausencia o alteración bloquea reutilización del estado. Un éxito técnico no es un resultado económico.
- Verificación opcional contra un tip externo exacto; el CLI daemon exige un tip inicial. Detecta rollback a un prefijo válido si el tip externo esperado es conservado por una autoridad distinta.
- Propuestas de investigación estructuradas: pregunta, mecanismo, unidad, disponibilidad causal, control, outcome, familia de multiplicidad, validación, falsificación, presupuesto y referencia de autoridad. La auditoría es de COMPLETITUD, no de validez científica; estado obligatorioPROPOSED_UNAUTHORIZED.
- Observador read-only de un archivo de estado de campaña: sin control de procesos ni lectura de ticks. Estado antiguo genera advertencia, no diagnóstico automático de proceso colgado. Un estadoRUNNING no acredita liveness.
- CLI de ciclos finitos y workflow focal Python3.12/3.13. No instala modelos ni solicita credenciales.

## Prueba mínima, sin datos de mercado

Desde la raíz del repositorio, usar un directorio de estado nuevo:

```bash
python -m tools.research_ops.cli --state /tmp/edgelab-ops-demo/queue.sqlite init --attempts 2 --seconds 10
python -m tools.research_ops.cli --state /tmp/edgelab-ops-demo/queue.sqlite submit-synthetic DEMO-1
python -m tools.research_ops.cli --state /tmp/edgelab-ops-demo/queue.sqlite verify
python -m tools.research_ops.cli --state /tmp/edgelab-ops-demo/queue.sqlite run-one
python -m tools.research_ops.cli --state /tmp/edgelab-ops-demo/queue.sqlite verify
python -m unittest discover -s tests/research_ops -v
```

El runner sólo admite la suma sintética fija definida en`worker.py`. No ejecuta el texto de una hipótesis ni acepta comandos/path de datos en el plan. Para el daemon finito, pasar`--expected-tip`con el tip actual obtenido y conservado externamente después de registrar las propuestas. Un tip anterior a las propuestas rechaza el arranque.

Después de una caída, NO repetir un jobRUNNING. Revisar recibos y estado; `quarantine JOB_ID`registraINTERRUPTED y conserva el cargo de presupuesto. Un reemplazo necesita otro ID y protocolo/budget revisados. La cuarentena no mata un proceso: comprobar liveness e interrumpirlo con autoridad externa ANTES de liberar la cola.

## Riesgos y límites explícitos

- Checksums, nombres y hashes no son firmas ni autenticación. Un usuario con acceso completo al host/DB puede reescribir todos los controles locales. El tip guardado junto a la DB tampoco garantiza protección frente a rollback conjunto.
- Límites de recursos y`-I -S`NO son un sandbox para código hostil. No aceptar código generado por modelos en este worker. El futuro executor de mercado requiere aislamiento de identidad, filesystem, red y secretos.
- El reloj, SQLite y el filesystem pueden fallar. Un recibo puede quedar escrito antes de que el estado terminal confirme: se conserva, el job continúaRUNNING, no se repite ciegamente.
- El observador sólo permite el diagnóstico operacional; no certifica fuente, causalidad, éxito de una corrida ni oportunidades. No interpreta el contenido de archivos como instrucciones.
- Cada cola tiene presupuesto estático; no se reinicia diariamente ni tras un crash. Crear colas nuevas para eludirlo no está controlado contra un administrador del host.
- Todavía no hay generador LLM, scheduler científico, fuentes Brain/artículos reales vinculadas, dispatcher de research, adaptador aprobado de mercado, control durable de costo API, servicio aislado de reservas ni notificaciones. Hay adaptadores de lectura y benchmarks sintéticos, no aceleración integral demostrada.
- Tests focales no equivalen a toda la suite del repo; workflow publicado no implica CI remota pasada. Presencia en esta rama no es integración enmain.

## Camino a24/7, por hitos

1. **Este hito:** semántica de cola, presupuesto, fallos, recibos y observación; sintéticos únicamente.
2. Estado/checkpoints externos, supervisor confiable, identidad de runner, métricas y alertas. Persistencia por fragmentos de campañas; sin reejecutar outputs ambiguos.
3. Adaptador de campaña aprobada: fuente/selección/código/particiones/budget exactos y permisos verificados antes del payload. Consumir gates y motor existentes; no sustituirlos con este SQLite.
4. Benchmark del motor en inputs aprobados o sintéticos: mismo output, protocolo y presupuesto; perfilado antes de paralelismo/GPU. Cambios en rama aparte; no modificar la corrida activa.
5. Planner/LLM de propuestas y crítica, con límites de gasto, historial completo de intentos y auditoría científica independiente. No autoaprobar ni cambiar criterios tras outcomes.
6. Despliegue24/7 sólo tras piloto, revisión y permisos separados. Reservas/confirmación/trading real requieren autoridad adicional.

## Observación de MNQ

El comando`observe PATH_TO_CAMPAIGN_STATUS_JSON`lee un snapshot; no detiene, relanza ni adopta la corrida. El watchdog ya existente sigue separado y puede verificar procesos/recursos. Esta base no toca ni replica sus procesos activos.

## Segundo hito: integración read-only y paridad sintética

Se agregó un puente metadata-only al gate canónico y un candidato acotado de rango previo por sesión. No habilita ejecutor de mercado ni importa la autorización exploratoria como certificación. Alcance, límites y pruebas: [Integración y paridad](INTEGRATION_PREFLIGHT_AND_PARITY.md). Evidencia de este hito: `PHASE2_TEST_EVIDENCE.json`; la evidencia original se conserva sin reemplazar.

## Tercer hito: presupuesto por unidades y rendimiento

Se agregaron inventario sellado de18familias, evaluación conservadora de admisión (sin lanzamiento), memo causal acotado y microbenchmark de las expresiones existentes con inputs sintéticos. Se conserva el ejecutor exclusivamente sintético. Detalle: [Rendimiento y unidades](PERFORMANCE_AND_FROZEN_WORK_UNITS.md). La medición demuestra tanto beneficio con hits como penalización sin repetición; no demuestra aceleración de la campaña completa.

## Cuarto hito: conocimiento y research condicional

Adaptadores del core canónico EdgeBrain y exports de la biblioteca SSRN existente, sin duplicarla; planner explícito para investigar vacíos o contradicciones y devolver referencias al Brain. Ningún dispatch de red o append científico automático. [Arquitectura, interfaces y límites](KNOWLEDGE_FIRST_RESEARCH.md). Evidencia focal: `PHASE4_TEST_EVIDENCE.json`.

## Quinto hito: snapshots de cola y recuperación sintética

Export/inspect/restore con proyecciones, eventos, recibos y presupuesto intactos; pérdida de host simulada sólo en fixtures. RUNNING no se reejecuta ni se declara completado. [Recuperación portable y límites](PORTABLE_QUEUE_RECOVERY.md). NO hay host/store remoto/witness vinculados ni checkpoints del motor MNQ recuperados.

## Handoff de continuación

[CLAUDE_HANDOFF.md](CLAUDE_HANDOFF.md) reúne los cinco hitos implementados, fuentes/autoridad, pruebas verificadas, campaña Kaggle separada y próximos pasos. [CONTINUATION_STATE.json](CONTINUATION_STATE.json) es un snapshot, no estado vivo. Inventario de los40archivos del commit fuente: `HANDOFF_SOURCE_INVENTORY.json`; revalidación limpia: `HANDOFF_TEST_EVIDENCE.json`. No habilita autonomía de mercado ni servicio24/7.

## Aprendizaje poscorrida y mejora continua — diseño/prototipo offline

[Diseño y límites](POST_RUN_LEARNING_AND_OPTIMIZATION.md): cierre verificado → recall canónico → borradores separados científicos/técnicos → experimento finito → paridad/benchmark → revisión → canary futuro → recall del próximo plan. `post_run.py` propone y filtra, no escribe Brain, ejecuta, promueve ni despliega. Cada cierre se revisa; si no hay mejora demostrada se conserva baseline. Las optimizaciones no se instalan en corridas activas.
