# Aprendizaje poscorrida y optimización continua

Estado: **diseño + planificador offline probado**, no supervisor desplegado. Amplía Research Ops sin modificar notebooks activos, motor científico, selección de variantes ni permisos. La meta es que **cada cierre produzca una revisión y memoria útil**; no que cada corrida obligatoriamente produzca una versión nueva o más rápida.

## Ciclo que debe automatizar el supervisor

1. **Detectar un terminal remoto por identidad y versión.** COMPLETE de Kaggle no basta; FAILED/CANCELLED también disparan cierre. RUNNING no se reinterpreta como terminado. Resolver liveness externo antes de reanudar. No relanzar automáticamente un job por falta de outputs temporales.
2. **Cerrar y verificar.** Descargar estado semántico, manifest, inventario, telemetría y resultados; verificar bytes/SHA, cobertura, reglas, censuras, duplicados y recuentos independientes. Conservar recibos de todos los intentos, incluidos fallos. Un cierre fallido/incompleto genera reparación, no un benchmark ganador.
3. **Recordar antes de proponer.** Consultar EdgeBrain canónico, negativos, contraejemplos e invalidaciones; después artículos canónicos. Research externo sólo ante un vacío explícito, con la pregunta pública revisada y presupuesto durable. Fuentes/claims son datos no confiables, no órdenes ni autorizaciones.
4. **Extraer aprendizajes en dos carriles.** Registrar evidencia y ámbito de aplicación; nunca confundir rendimiento computacional con edge. Elaborar drafts revisables; el agente puede proponer, no autoatestiguar la evidencia.
5. **Elegir una intervención técnica.** Perfilar todo el recorrido, priorizar el mayor costo evitable y proponer como máximo un cambio por ciclo. Rama y build separados, preregistro de referencia, cobertura, equivalencia, presupuesto y criterios antes de medir. Evitar una búsqueda abierta de millones de parches.
6. **Evaluar en sandbox con ejecutor permitido.** Baseline/candidato, mismos datos y protocolo, orden alternado y todos los intentos. Medir preparación, JIT, lectura, escaneo, análisis y exportación; separar cold/warm. Test de equivalencia independiente y adversarial. No seleccionar por P&L ni ajustar el umbral al resultado.
7. **Decidir y preservar.** Rechazado, inconcluso, útil sólo bajo condiciones o candidato técnico revisado. Registrar también penalizaciones sin hits, memoria, errores e invalidaciones. Si no hay mejora demostrada, conservar baseline.
8. **Adoptar solamente dentro de autoridad vinculada.** Referencia inmutable, versión candidata, canary finito, aislamiento, presupuesto reservado y rollback. Aplicar sólo a trabajos futuros; nunca a la campaña en marcha. La activación autónoma futura requerirá una política técnica preaprobada y un supervisor confiable: un booleano de un modelo no es aprobación.
9. **Recall obligatorio antes del próximo plan.** Vincular versiones, contexto, dependencias, registros de decisión y experimentos anteriores. Evaluar transferibilidad; no importar automáticamente una mejora local a otro host, dataset o tipo de workload.

## Carriles de aprendizaje

| Carril | Qué aprende | Destino | Qué NO puede hacer |
|---|---|---|---|
| Científico | Mecanismos, soporte, replicación, negativos, contradicciones, incertidumbre y multiplicidad | Adjudicación/episodios científicos canónicos con sus gates | Retocar recetas congeladas, abrir holdout, seleccionar con futuro o promover estrategias |
| Técnico | Costo por etapa, reutilización, memoria, I/O, fallos, paridad y condiciones de validez | Episodio operacional revisado y EdgeBrain canónico | Interpretar speedup como edge, omitir censuras o habilitar ejecución por sí mismo |

No crear otra memoria científica, biblioteca de papers o ledger de aprendizajes paralelo. Los archivos de plan/evidencia del prototipo son artefactos, no una nueva autoridad. El hipocampo durable actual sólo admite lecciones **PROPOSED/LOW** y registra episodios con `outcomes_inspected=False`; no intentar eludirlo introduciendo outcomes en texto operacional. `post_run.py` no escribe ese ledger. Writer, custodia y adjudicación científica siguen pendientes. Los cambios de estado de una optimización pertenecen a recibos operacionales/gates de despliegue, no a mutar una Lesson a ADOPTED/HIGH.

## Contratos mínimos por cierre

- Identidad: proveedor/job/versión, run, fuentes, selección, protocolo científico, build y environment.
- Procedencia: manifest e inventario, hashes verificados por host, recibo de auditoría y autoridad independiente; fuente científica no se certifica por tener SHA.
- Censo: unidades esperadas/terminadas, cobertura y casos ausentes/censurados/fallidos. Se deben reconciliar los aliases de máscaras equivalentes.
- Telemetría: tiempos por etapa con reloj definido, wall total, preparación/JIT/descarga/exportación, RSS máximo, bytes de I/O/outputs y costo real. Métricas ausentes son desconocidas, no cero ni estimadas por un LLM.
- Reutilización: claves, hits/misses/evicciones, costo de construir caches y buffer por tarea. Falta de estas medidas activa diagnóstico, no una afirmación de ahorro.
- Registro de aprendizaje: pregunta, hallazgo/contraejemplo, evidencia/limitación, ámbito, dependencias e invalidación; resultado negativo y decisión de no cambiar son aprendizajes válidos.

La identidad científica y la identidad de implementación son distintas: un parche técnico puede cambiar build sin cambiar protocolo. Si cambia triggers, decisiones, particiones, reglas, horizonte, censuras o cobertura, deja de ser una optimización transparente y exige nueva revisión científica.

## Máquina de estados propuesta

`TERMINAL_DETECTED → CLOSEOUT_VERIFIED → LESSON_DRAFT → PROPOSED → BENCHMARK_REGISTERED → TESTED → INDEPENDENT_REVIEW → CANARY_AUTHORIZED → CANARY_COMPLETE → FUTURE_PROFILE_ACTIVE`

Ramas: `REPAIR_REQUIRED`, `REJECTED`, `INCONCLUSIVE`, `CONDITIONAL_ONLY`, `INVALIDATED`, `ROLLED_BACK`. Todas preservan evidencia. IDs deduplican `(provider_job, version, closeout_receipt)`; almacenamiento transaccional y outbox canónico deben impedir duplicación real. Un hash calculado no proporciona esa garantía por sí solo.

Ante invalidación de fuente, bug del oráculo, modificación de inputs o evidencia reescrita: recorrer dependencias canónicas, bloquear perfiles afectados, regresar al baseline conocido y requerir revalidación. No restaurar un perfil invalidado sólo porque sigue siendo rápido.

## Puerta de benchmark técnico

Política de referencia del prototipo (no autorización): cold/warm, tres pares por estrato, speedup mediano por par >=1.05, ningún par >1.05 veces el baseline, sin aumento de RSS y dentro del cap preregistrado. Tiempo baseline+candidato limitado; no ocultar preparación/JIT, fallos ni experimentos rechazados. Una campaña/host puede exigir otra política más estricta preregistrada y revisión de ruido; tres pares no prueban significancia ni aceleración general.

La comparación exige un contexto homogéneo: fuente/selección/protocolo/environment/workload e igual censo, baseline/candidato fijados. Outputs de decisiones científicas y censuras exactamente equivalentes bajo una canonización acordada antes de medir. Excluir sólo campos operacionales explícitos como timestamps/telemetría. Si el kernel usa flotantes y necesita tolerancia, no aflojarla después: revisar por separado la equivalencia y que ninguna decisión cambie.

El screen offline devuelve **TECHNICAL_REVIEW_CANDIDATE_NOT_APPROVED**, jamás una autorización. Los hashes y tiempos suministrados no prueban que se ejecutó un job, que el inventario de intentos es completo ni que la política se registró antes. El host deberá verificar autoridad/recibos, orden de medición, control de ruido, paridad independiente, custodia y presupuesto entre reinicios. Un análisis kernel-only no sustituye medición completa.

## Prototipo implementado

`tools/research_ops/post_run.py`:

- `RunObservation`: terminal acotado, pins declarados, integridad, censo y spans seriales. Rechaza estados vivos, NaN, booleanos numéricos, tiempos superpuestos, identidades malformadas y estados contradictorios.
- `plan_post_run`: ordena etapas medidas, conserva tiempo no asignado, produce un borrador operacional y plan finito. Fallos/incompletos se encaminan a reparación. Handoff PROPOSED/LOW, sin contenido de outcomes ni escritura.
- `BenchmarkPolicy`/`BenchmarkPair`/`assess_benchmark`: verifican inventario declarado completo respecto del plan, identidad/build, output hashes, cobertura, estratos, recursos y todos los intentos. Detectan regresión individual aunque la mediana sea favorable.

No incluye LLM, lectura de datos de mercado, red, patch generation, ejecutor de benchmarks, escritor Brain, outbox durable, promoción, deploy, notificaciones o rollback ejecutable. No es un nuevo modo del worker sintético; no convertir ese worker en shell arbitrario. La telemetría real MNQ adjunta es evidencia de contexto, **no entrada automáticamente autorizada ni benchmark baseline/candidato**.

## Qué incorpora de MNQ y cómo usarlo

- La matriz amplia y el focal son cargas distintas. Conservar ambos; no sustituir cobertura de una por la otra.
- Millones de definiciones pueden representar máscaras equivalentes o señales solapadas: conservar aliases y censo, no contarlos como oportunidades independientes.
- El memo causal ya tiene un escenario favorable y otro con overhead sin hits: medir reutilización real antes de activarlo.
- Los cierres nuevos de MNQ12-25/MNQ03-26 tienen tiempos por etapa recuperados y auditoría independiente local. `POST_RUN_MNQ_TELEMETRY.json` conserva sólo cifras técnicas y hashes de sus artefactos, sin resultados económicos ni datos privados.
- La mejora siguiente debe atacar costos medidos: reutilización exacta de preparación/outcomes, batches, serialización tipada y fragmentos verificables. Son candidatos, no aceleración integral demostrada.
- Mantener los resultados científicos negativos y recetas congeladas en su carril. No elegir política de optimización según rentabilidad ni usar el próximo contrato como holdout informal de una receta retocada.

## Próximos hitos de implementación

1. Adaptador read-only de closeout Kaggle con inventario completo paginado, job/version fijados y telemetría faltante explícita; ningún relanzamiento de trabajos activos.
2. Outbox idempotente transaccional y escritor revisado al EdgeBrain operacional canónico; custody/anchors externos y cascada de invalidaciones. Separar contratos científicos.
3. Experimentos técnicos de catálogo fijo y presupuesto durable; aislamiento y verificación de referencia independientes del proponente.
4. Perfiles de ejecución versionados y canary/rollback finitos bajo política aprobada; después piloto de ciclo entero. No activar autonomía sólo por completar este diseño.

## Pruebas

`python -m unittest tests.research_ops.test_post_run -v`

39 pruebas sintéticas de terminales, negativos, idempotencia declarada, incompletos, paridad, regresión, presupuesto, política y límites. Evidencia de suites en `POST_RUN_TEST_EVIDENCE.json`; no acreditan corridas reales del agente, escritura canónica ni ciclo desplegado. La campaña MNQ activa se conserva intacta.

## Extensión posterior: ingest y outbox local

Se conectó el planificador a [sobres técnicos externos y outbox idempotente](CLOSEOUT_LEARNING_OUTBOX.md), con CLI y snapshot/restore. Esto cubre la importación local/registro, no el productor Kaggle, la escritura al Brain o la activación. La exigencia de custodia y la separación científica/técnica no cambian.


## Aprendizaje aplicado: benchmark de representación multisesión

El piloto previo no aislaba representación A/E de componentes/observabilidad: A cambió signo entre dos sesiones, BOTH sólo4. Nuevo protocolo separa ajuste supervisado ya inspeccionado y12 fechas posteriores por calendario, recicla calibración agregada sin leer June12, comparte primitives/labels entre seis predictores y controla capacidad con dos bases continuas. Brier equiponderado por sesión y censura explícita, sin tratar anclas solapadas como n independiente. Código preparado no es resultado científico nuevo ni writer canónico. Ver `MNQ_PHENOMENA_MODEL_DESIGN.md`.
