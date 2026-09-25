# Edge Brain — gobernador de trabajo recursivo

**Estado:** prototipo de planificador + comparador de desarrollo + ledger one-shot de auditoría final; pendiente de CI/revisión. No es un daemon ni modifica NORTH_STAR/G0–G5.  
**Objetivo:** que un ciclo deje capacidad reutilizable y verificable para los siguientes, sin medir progreso por CPU, tokens o cantidad de tareas.

## Research aplicado

- **Hay evidencia acotada de recursividad útil, no una receta universal de exponencialidad.** El preprint de Weco *Recursive self-improvement of AI research agents* (enviado 22-sep-2026) describe AIDE²: un ciclo de 8 días y 100 propuestas, con 7 rewrites aceptadas; mismas cotas de presupuesto por tarea, selección sobre resultados de desarrollo privados, y comparación final en cuatro benchmarks externos. Hubo dos runs adicionales con 2 y 4 aceptaciones. Los resultados no fueron monótonos por benchmark; ruido se acumula y repetir la evaluación final en más seeds es caro. Es evidencia prometedora del harness bajo un objetivo evaluable, no prueba de que EdgeLab, cualquier agente o las capacidades generales vayan a crecer exponencialmente. [Paper, arXiv:2609.26457](https://arxiv.org/abs/2609.26457)
- **No basta con memoria/autocrítica.** Reflexion halló mejoras en varios benchmarks, pero no mejoró significativamente sobre ReAct en WebShop y el equipo detuvo tras cuatro intentos sin señal. La memoria puede ayudar donde el feedback es informativo y quedarse atascada donde hace falta explorar más. [NeurIPS 2023](https://proceedings.neurips.cc/paper_files/paper/2023/file/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf)
- **Los evaluadores también fallan.** Anthropic recomienda outcomes medidos en el entorno, graders objetivos cuando sean posibles, checks de regresión, lectura de trazas y límites/guardrails: errores pueden propagarse entre turnos y el score puede invitar a hacks. Solo agregar complejidad cuando mejora resultados medibles. [Evals para agentes](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) · [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- **La tendencia METR no es una predicción para EdgeLab.** Su crecimiento exponencial es una curva entre generaciones de modelos y su horizonte de tareas en suites medidas, con intervalo de incertidumbre y reservas de validez externa; no describe el aprendizaje de un único proceso autónomo de EdgeLab. [METR, método y límites](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks)

## Iteración del prototipo

La primera versión ordenaba tareas con una heurística de reutilización/costo y registraba un rendimiento simple de aprendizaje. Riesgo detectado: las puntuaciones eran juicios declarativos; no bastaba con exigir un `evidence_ref` no vacío.

Se agregaron dos módulos:

### `edgelab/edge_brain/recursive_eval.py`

- Congela la identidad del protocolo y benchmark con SHA-256; cada receipt tiene checksum de sus campos.
- Exige misma cohorte emparejada de tareas/seeds para incumbent y candidato, misma identidad de benchmark/protocolo, disjunción entre `selection` y `development`, recursos iguales por trial y piso de pares declarado por protocolo.
- Un resultado de desarrollo positivo **solo nomina el rewrite para una auditoría final distinta**. No lo promueve ni declara que haya aprendido; el ensayo final sellado debe ser externo a este comparador y no filtrarse a quien genera candidatos.
- Rechaza cambios de presupuesto, recibos alterados, mezcla de versiones y regresión de seguridad según el límite preregistrado.

### `edgelab/edge_brain/sealed_audit.py`

- `reserve_batch` registra el lote completo (protocolo, benchmark, split sellado y hashes de todos los candidatos finalistas) en SQLite con transacción `BEGIN IMMEDIATE`, `synchronous=FULL`, archivo DB modo owner-only en POSIX y clave única por split sellado.
- La reserva se confirma **antes** de leer el split. Segundo ID, segundo lote, candidato añadido a posteriori o retry sobre el mismo hash del split se rechazan. Interrupción/error no libera el split: se queda `RESERVED` o se marca `BURNED`; no se vuelve a abrir.
- `finalize` conserva solo hash del resultado; la API de lectura devuelve únicamente estado, no scores. La fuente sellada debe vivir fuera de este ledger y estar accesible solo al runner.
- Los tests cargan los módulos por ruta directa para aislarlos del inicializador amplio de `edgelab.edge_brain`.

## Límite de seguridad importante

Esto es un **guardrail local de repetición para callers conformes**, no un boundary de seguridad contra el administrador del host ni un agente con acceso al archivo y al split. SQLite no autentica que un runner confiable haya ejecutado el ensayo; los checksums no son firmas. Tampoco puede impedir que un executor filtre scores a quien propone cambios. Para usarlo de verdad falta: (1) servicio/runner aislado dueño de datos sellados, (2) permisos POSIX/ACL para impedir acceso directo al modelo, (3) identidad firmada de imagen/código del runner y recibos verificables, y (4) separar devolución de resultado agregado de scores/datos privados. No se integra al ciclo de EdgeLab ni otorga acceso al market holdout.

## Criterio para que el ciclo valga tiempo

Comparar, bajo protocolo versionado y presupuesto igual:

1. **Calidad:** pruebas funcionales/regresiones y casos de seguridad objetivamente calificados.
2. **Eficiencia:** tareas correctamente resueltas por unidad de cómputo/token/dólar, con límite fijo.
3. **Transferencia:** la mejor versión debe mejorar en un audit independiente no consultado durante selección/desarrollo, idealmente en familias distintas.
4. **Persistencia:** mejora aceptada y reproducible en más de una seed; registrar cuántas propuestas fallan, no solo ganadoras.
5. **Compounding:** una versión candidata cuenta como mejora del proceso solo si, al reemplazar el incumbent, su rendimiento de investigación futuro mejora bajo el mismo presupuesto; una subida del score interno por sí sola no basta.
6. **Costo de error:** contabilizar regresiones, reward-hacking, retries, tareas bloqueadas y rework.

No afirmar "exponencial" por una sola racha. Medir log-yield por unidad de recurso en una serie de ciclos, fijar comparadores antes de observarlos, ensayar contra incumbent con el mismo presupuesto, separar grader/holdout del agente que propone, y reportar incertidumbre y coste de falsos positivos. El sistema puede estancarse o caer; stop-and-diagnose es parte del diseño.

## Ciclo objetivo, todavía por construir

1. Observador read-only toma snapshot de estado/tests/bloqueos e identidad.
2. Claude propone candidatos vinculados a evidencia reproducible; su texto no es evidencia.
3. Planner prioriza finite-budget en allowlist; la heurística de score sigue siendo no validada.
4. Executor aislado con locks, timeout, cuota, worktree descartable y outputs en cuarentena.
5. CI y grader verifican resultado sin dar acceso al split de desarrollo al proposer.
6. Solo los candidatos de desarrollo pueden nominarse; `SealedAuditLedger.reserve_batch` se llama antes de abrir la auditoría final, en un runner aparte.
7. Brain registra proposal, evaluación, outcome agregado, costo, código/datos y lección; aprobación separada para memoria durable.
8. Debian 24/7, retries/backoff, alertas y API usage/cost reporting solo después de piloto baseline y límites de gasto explícitos.

Anthropic documenta cuotas por requests/tokens y límites de gasto configurables, y reportes programáticos de uso/costo; la API no es "prácticamente sin límites" aunque el plan empresarial ofrezca capacidad amplia. Para trabajo asíncrono, Batch puede reducir costos según documentación oficial, pero sigue teniendo límites/expiración y no sustituye un budget guard. [Rate limits y spend limits](https://platform.claude.com/docs/en/api/rate-limits) · [Usage & Cost API](https://platform.claude.com/docs/en/api/data-usage-cost-api) · [Message Batches](https://platform.claude.com/docs/en/build-with-claude/batch-processing)

**Aporte al referente:** segunda iteración agrega comparación emparejada y de presupuesto fijo, y un ledger que consume por adelantado una auditoría sellada completa; define explícitamente el límite restante: aislamiento real, firma del runner y CI funcional antes de llamar al ciclo autónomo.
