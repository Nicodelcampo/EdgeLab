# Research Ops — EdgeBrain, artículos y research condicional

## Estado real

**Adaptadores de lectura y planner finito implementados; integración de fuentes reales y dispatch de research pendientes.** No servicio autónomo24/7, no permiso de mercado, holdout, P&L o promoción. No nueva memoria ni biblioteca paralela. Configuración explícita: `config/research_ops_knowledge_sources.json`.

## Ciclo de trabajo

1. Consultar el EdgeBrain canónico: experiencia operacional, fallos, contraejemplos e invalidaciones, no sólo éxitos.
2. Consultar la biblioteca canónica existente: artículos, claims y pasajes con identidad de fuente. Un resultado reportado por un autor no es evidencia propia ni demuestra transferencia a MNQ.
3. Declarar el vacío: método faltante, contradicción, fuente obsoleta, mecanismo nuevo, definición de datos o bloqueo de ejecución.
4. Investigar sólo si ese vacío afecta la decisión. Prioridad: memoria → artículos existentes → repo/fuentes internas aprobadas → fuentes públicas con pregunta revisada por separado.
5. Extraer claims con fuentes, límites y evidencia contradictoria. Los textos recuperados son datos no confiables, nunca instrucciones para herramientas.
6. Proponer una prueba falsable `PROPOSED_UNAUTHORIZED`: disponibilidad causal, control, falsificación, multiplicidad e historial de todos los intentos.
7. Revisión científica y autoridad de campaña independientes. Sólo después: gates existentes, admisión de recursos, unidades congeladas y ejecución finita aprobada.
8. Analizar todos los resultados registrados, incluidos fracasos; preparar referencias para devolver aprendizaje al EdgeBrain canónico. No append automático en este hito.

Una oportunidad prometedora justifica atención y controles más fuertes, no optimizar sobre outcomes inspeccionados o excluir variantes fallidas. El historial de millones de variantes y las definiciones focales sigue separado y no se reinicia con nuevas búsquedas.

## EdgeBrain: consumir, no reemplazar

`tools/research_ops/knowledge.py::recall_brain` usa `DurableHippocampus` y `LedgerIndex.from_memory` de main. Lee un export operacional target-free aprobado (máximo2MiB), verifica SHA256 externo del archivo y tip externo del ledger; reproduce una copia capturada e inmutable. No escribe en el ledger original ni acepta historias de trials/particiones/observaciones como memoria operacional ordinaria. El filtro de tipos NO certifica que el texto arbitrario esté autorizado o libre de outcomes: el export debe aprobarse externamente.

La búsqueda lexical canónica devuelve referencias y texto acotado, conserva invalidaciones visibles y marca `artifact_reuse_authorized=false`. Un hash correcto no autentica al productor ni transforma una lección en evidencia científica. El export real, sus anchors y la identidad del escritor siguen sin vincularse.

## Artículos: respetar el puente existente

La biblioteca y el puente `EdgeBrainMemory` existen en [PR67](https://github.com/Nicodelcampo/EdgeLab/pull/67), todavía separado de main al inspeccionarlo. Interfaz revisada en commit `5c10da451b164c54133bdb9a4674de43d6fa2d22`: `SSRNBibliographicCortex.context_pack(query, limit, max_chars)`. No copiar aisladamente `literature_bridge.py`: depende de APIs de la misma rama que difieren de main.

El adaptador consume un export `context_pack` con archivo fijado externamente. Comprueba esquema cerrado, query, IDs, presupuesto y hash canónico de items (`ensure_ascii=False`, para conservar compatibilidad Unicode); agrega hash de cada pasaje. Mantiene `LITERATURE_CLAIM_UNVERIFIED`, `claims_are_evidence=false` y `corpus_custody_verified=false`. El commit suministrado es referencia declarada, NO prueba de que produjo el export.

No se materializó ni se validó el corpus completo. Antes de vincularlo: resolver la deuda declarada de digest del ledger, revisar textos/títulos fuera de scope, ejecutar bootstrap y custodia en entorno separado y fijar el export. La búsqueda del Cortex puede construir/actualizar el índice FTS derivado: no describir esa operación como estrictamente read-only; usar índice preparado o sandbox derivado con custodia del corpus conservada.

## Research: capacidad explícita, runtime pendiente

`tools/research_ops/research_cycle.py::plan_research` recibe un `knowledge_context` sellado, episodio, tipo de vacío y evidencia faltante. Fuente ausente es bloqueo de integración, no corpus/memoria vacíos. Los contextos y preguntas anidadas deben coincidir; el sello detecta corrupción local, no ofrece autenticación.

Con ambas fuentes y una pregunta pública separadamente revisada genera dos directivas: evidencia/metodología favorable y evidencia contraria/límites de transferencia. No copia automáticamente contexto privado a proveedores externos. `public_query_reviewed` es una declaración del caller, NO aprobación autenticada; el host futuro debe vincular revisor, credenciales y permisos.

Defaults por episodio:2rondas,4consultas,8documentos,24.000caracteres,300segundos y gasto API0. Máximos cerrados:3/8/12/24.000/600; no gasto pago habilitado. Son límites del PLAN: todavía no existe dispatcher que ejecute una llamada de red real. `provider_dispatch_attached=false`, `network_executed=false`.

Detener por presupuesto/tiempo, falta de nueva evidencia útil, proveedor bloqueado, custodia contradictoria o causalidad/autoridad sin resolver. No ciclar indefinidamente variaciones de búsquedas. El host deberá permitir sólo herramientas de lectura aprobadas y guardar recibos de fuente y de costo ANTES de nuevos intentos.

### Presupuesto durable entre reinicios: `tools/research_ops/dispatch.py`

`DispatchLedger` cierra la parte de durabilidad del hito 3 sin abrir ningún socket. Es otro ledger SQLite encadenado por hash, hermano de `Store`, pero nunca despacha una llamada de red:

- **Revisor fijo:** `Reviewer(reviewer_id, scope='public_web_readonly')` se congela en `initialize()`, igual que `Store.Policy`. Un ledger sirve a un solo revisor.
- **Plan fijado una vez:** `bind_plan(plan)` exige un plan `READY_READONLY_RESEARCH_DIRECTIVES_NOT_EXECUTED` sin `blockers`, verifica `plan_sha256` contra el propio plan y congela su cantidad de directivas (`max_queries`). No se puede reasignar ni ampliar.
- **Reserva durable:** `reserve(directive_index, reviewer_id=...)` marca una directiva como gastada en el ledger antes de que exista ningún intento de red. Si el proceso se reinicia o crashea, reabrir el mismo archivo y reservar de nuevo la misma directiva falla: el presupuesto no se regala dos veces. Esto es lo que resuelve `durable_research_budget_enforced=false` del plan.
- **Recibo, no fetch:** `record_receipt(...)` sólo acepta evidencia ya obtenida por un paso externo y autorizado aparte, identificada por SHA256 de contenido y de URL, con `cost=0` forzado (gasto pago sigue deshabilitado). Este módulo no importa `requests`/`urllib`/sockets; un test lo verifica a nivel de archivo fuente.
- **Qué sigue pendiente:** el propio fetch autorizado (adaptador de proveedor + allowlist de herramientas + identidad/credenciales), que es deliberadamente un paso separado y fuera de este módulo.

Tests: `tests/research_ops/test_dispatch.py` (20 casos): revisor congelado, plan fijado una sola vez, índice fuera de presupuesto rechazado, reserva doble rechazada, reinicio no regala presupuesto, recibo exige reserva previa y SHA externo, gasto pago rechazado, y cadena de eventos verificada contra manipulación.

## Uso del prototipo

Instalar la dependencia del core canónico en entorno aislado: `jsonschema==4.23.0` (CI focal hace lo mismo). No modificar el runtime de la campaña activa.

```bash
python -m tools.research_ops.cli recall-brain APPROVED_OPERATIONAL_EXPORT QUERY --expected-sha256 EXTERNAL_FILE_SHA256 --expected-tip EXTERNAL_LEDGER_TIP
python -m tools.research_ops.cli recall-articles CANONICAL_CONTEXT_EXPORT QUERY --expected-sha256 EXTERNAL_EXPORT_SHA256 --producer-commit CANONICAL_PRODUCER_COMMIT
python -m unittest discover -s tests/research_ops -v
```

Ambos comandos de recall se resuelven antes de abrir la cola SQLite. La composición y planificación se exponen como API Python (`knowledge_context`, `plan_research`), no como comandos de red. Un archivo creado por el propio modelo y su hash no satisfacen aprobación/custodia externa.

El presupuesto durable (`dispatch.py`) también tiene CLI, sobre un archivo SQLite separado (`--dispatch-state`) del de la cola de jobs:

```bash
python -m tools.research_ops.cli dispatch-init --dispatch-state DISPATCH_PATH --reviewer-id REVIEWER_ID
python -m tools.research_ops.cli dispatch-bind-plan --dispatch-state DISPATCH_PATH PLAN_JSON_FILE
python -m tools.research_ops.cli dispatch-reserve --dispatch-state DISPATCH_PATH --reviewer-id REVIEWER_ID DIRECTIVE_INDEX
python -m tools.research_ops.cli dispatch-receipt --dispatch-state DISPATCH_PATH DIRECTIVE_INDEX --evidence-sha256 EXTERNAL_CONTENT_SHA256 --source-sha256 EXTERNAL_URL_SHA256 --chars CHAR_COUNT
python -m tools.research_ops.cli dispatch-verify --dispatch-state DISPATCH_PATH
```

`PLAN_JSON_FILE` es la salida de `plan_research` volcada a disco (≤64KiB, sin symlink, igual límite que `audit-draft`); ningún comando de esta lista abre un socket.

## Próximas integraciones

- Vincular un export operacional real aprobado y el Cortex canónico una vez resuelta su custodia; probar consultas con recibos reales.
- Dispatcher read-only con autorización de pregunta pública, identidad, allowlist de herramientas, costo y presupuesto durable por episodio.
- Extracción tipada de claims y revisión independiente; escritor canónico para `literature_consulted`/dependencias/lecciones, sin otra memoria competidora.
- Adaptador del motor aprobado y resultados con identidad exacta; supervisión y recuperación con aislamiento antes del despliegue24/7.

Rendimiento sigue siendo un hito separado: reutilizar retrieval/contextos fijados, evitar recomputación y benchmarks con paridad. La ganancia del microbenchmark de cache no equivale a aceleración de la campaña completa; no modificar la corrida actual.
