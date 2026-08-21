# Embudo de evidencia y atajos válidos — playbook transversal

- **Fecha de registro:** 2026-08-21
- **Estado:** `PROJECT_WIDE_PRACTICE_REGISTERED`
- **Ejecución:** `NOT_A_CAMPAIGN` · `DOES_NOT_AUTHORIZE_OUTCOMES`
- **Origen:** lecciones generalizadas durante el diseño `HFTZonesESPureV2Flat × BigTrap2`.
- **Alcance:** indicadores, combinaciones de features, análisis multiescala, multiactivo, GEX/L2 y campañas futuras.

Este documento registra atajos que **ahorran trabajo sin rebajar evidencia**. No reemplaza:

- `docs/event_identity_v2.md` para identidad de captura;
- `docs/nt8_indicator_parity_contract.md` para paridad NT8↔Python;
- `docs/edge_validation_contract.md` para promoción G0–G5;
- `CONTRATO_LLM.md` para señales, fills y motor compartido;
- `docs/TRACEABILITY.md` para qué documento manda.

Si hay conflicto, mandan esos contratos y `docs/CURRENT.md`. Este playbook organiza el recorrido; no crea un camino lateral alrededor de los gates.

---

## 1. Qué significa «atajo» en EdgeLab

Un atajo válido hace al menos una de estas cosas:

1. mata una opción inviable **antes** de pagar una exportación o campaña;
2. reutiliza un artefacto inmutable en vez de recalcularlo;
3. convierte una ambigüedad en un campo o estado explícito;
4. prepara controles antes de que los outcomes puedan influir;
5. reduce por familias antes de combinar;
6. separa código, ejecución y resultado para que una corrección no deje documentos desincronizados.

No es un atajo válido:

- ampliar una tolerancia después de ver un diff;
- descartar una configuración por el output de un port sin paridad;
- tratar una inferencia de procedencia como hecho;
- sumar controles después de mirar outcomes;
- reabrir o reajustar sobre el holdout;
- llamar «paridad», «confirmación» o «edge» a un probe.

**Regla resumida:** se ahorra por mejor orden, muerte barata y reutilización; nunca por menor exigencia.

---

## 2. Namespace: EF0–EF5, no otro conjunto ambiguo de F

El repo ya usa `F2.7`, `F2.8`, fases históricas y gates `G0–G5`. Para aplicaciones nuevas, el embudo transversal se identifica como **EF** (*Embudo de evidencia*) para no colisionar:

| Etapa | Función | Qué puede decidir |
|---|---|---|
| `EF0-A` | Factibilidad del **dato**, target-free | Puede excluir una opción estructuralmente inviable |
| `EF0-B` | Probe provisional del **indicador** | Prioriza; no excluye por semántica hasta pasar paridad |
| `EF1` | Atlas estructural target-free con controles | Filtra sólo lo no causal, imposible, redundante o de calidad insuficiente |
| `EF2` | Screening exploratorio con outcomes en desarrollo | Genera hipótesis; nunca confirma |
| `EF3` | Reducción jerárquica | Elige familias y representaciones, no el mejor umbral |
| `EF4` | Freeze y preregistro | Congela un conjunto pequeño de hipótesis |
| `EF5` | Confirmación independiente | Ejecuta la única prueba limpia bajo el contrato de holdout |

Correspondencia con el borrador HFT×BigTrap2: sus `F0-A…F5` pasan a citarse como `EF0-A…EF5`. Es un cambio de namespace, no de sustancia.

**EF no otorga estados G.** Por ejemplo, sobrevivir `EF2` no concede `G1` ni `G2`; y `EF5` sólo puede ejecutarse cuando `edge_validation_contract.md` autorice G4.

---

## 3. Atajos y buenas prácticas reutilizables

### ATJ-01 — Separar imposibilidad del dato de defecto del port

**Práctica**

- `EF0-A` verifica existencia, cobertura, sesiones, ordenabilidad y capacidad de mapear al stream canónico.
- `EF0-B` usa una réplica provisional para estimar costo y priorizar.

**Decisión permitida**

- `EF0-A` puede excluir si la pregunta no es observable con esos datos.
- `EF0-B` no puede excluir un `config_id` por pocos eventos, dirección rara, lifecycle anómalo o bajo solapamiento mientras el port no tenga paridad.

**Ahorro:** evita pagar paridad a candidatos físicamente imposibles sin convertir bugs de réplica en resultados científicos.

---

### ATJ-02 — Unir eventos sólo dentro de un stream canónico común

Para todo evento que vaya a compararse causalmente se exige, como mínimo:

```text
raw_stream_sha256
session_id
event_id
population_id
config_id
created_ts_ns
available_ts_ns
created_source_row
available_source_row
availability_basis
```

La comparación operativa es entre `available_source_row` dentro del **mismo** `raw_stream_sha256` y `session_id`.

- Un índice de fila reproducible no se presenta como secuencia del exchange.
- Que `sequence` sea creciente no prueba cuándo fue asignado ni que no hubo reordenamiento.
- Dos exportaciones sin clave común no se fuerzan por nearest timestamp: quedan `truly_ambiguous` o requieren un crosswalk auditado.

Para capturas v2, manda `docs/event_identity_v2.md`: `capture_id`, `callback_seq` y `capture_seq` conservan sus semánticas propias. En datos legacy no se rellenan inventando campos v2; `raw_stream_sha256 + source_row` sólo certifica orden del artefacto canónico, no upstream.

**Ahorro:** elimina joins temporales artesanales y permite reutilizar la misma identidad entre indicadores, near-miss y controles.

---

### ATJ-03 — Disponibilidad explícita; creación no implica utilizabilidad

Toda señal o feature declara cuándo queda disponible:

```text
created_at
available_at
available_source_row
availability_basis = timestamp | source_row | callback_seq | bar_close | unknown
```

Para `Calculate.OnBarClose`, la señal no existe al inicio de la barra creadora. Una confirmación posterior usa:

```text
t_entry = max(hft_available_at, context_available_at)
```

Estados mínimos de orden:

| Estado | Semántica | Uso |
|---|---|---|
| `timestamp_ordered` | timestamps distintos y comparables | causal |
| `source_row_order_only` | mismo timestamp; orden sólo por stream canónico | causal operativo, etiquetado |
| `truly_ambiguous` | no hay clave común suficiente | excluir o analizar aparte |

Toda conclusión sensible publica `full_source_order` vs `strict_timestamp_only`.

**Ahorro:** una única política de disponibilidad evita reauditar look-ahead indicador por indicador.

---

### ATJ-04 — El renderer nunca es la tabla analítica por defecto

Dibujo, radio, transparencia, autoscale, percentiles visuales y filtros de display no entran a features salvo demostración explícita de que:

1. son causales;
2. existen en tiempo real;
3. no dependen del conjunto futuro dibujado;
4. están en el `config_id` analítico si cambian el objeto exportado.

El análisis consume eventos crudos y lifecycle; el renderer sólo verifica presentación.

**Ahorro:** evita construir una campaña completa sobre supervivientes de una regla visual con look-ahead.

---

### ATJ-05 — Lifecycle como máquina de estados con censura

No se traduce `CREATED sin cierre` automáticamente como log roto. Estados mínimos:

```text
active_at_t0
closed_before_t0
left_truncated_unknown
right_censored_at_export_end
lifecycle_inconsistent
```

Auditoría mínima:

- `CREATED ↔ TOUCHED/INVALIDATED/EXPIRED`;
- cierres huérfanos;
- IDs duplicados;
- orden imposible;
- eventos después del fin declarado;
- zonas abiertas al final de la exportación.

Una cola abierta es censura por derecha salvo evidencia de corrupción. La auditoría clasifica antes de descartar.

**Ahorro:** el mismo parser de lifecycle sirve para todos los indicadores de zonas y evita falsos FAIL de borde.

---

### ATJ-06 — Identidad completa de configuración; no transportar paridad en silencio

Cada objeto analítico se fija por:

```text
sha256 del código + parámetros + bar_spec + instrumento + semántica de sesión + schema
```

Cada `bar_spec` es un `config_id` distinto. Un número de versión escrito en prosa no reemplaza el hash del `.cs` ni el `kernel_id`.

La cobertura de paridad sólo se hereda por las reglas fail-closed de `nt8_indicator_parity_contract.md`; nunca por parecido visual o intuición.

**Ahorro:** permite correr una vez, publicar una partición inmutable y consultar muchas veces sin perder qué se midió.

---

### ATJ-07 — Construir controles antes de outcomes

`EF1` materializa la misma representación target-free para:

```text
objeto real
near-miss emparejado
control genérico pertinente
```

Cada población usa las mismas columnas de contexto, régimen, calidad y geometría. Matching, elegibilidad, reemplazo y reutilización se fijan antes de `EF2`.

No es ejecutar el contraste: es impedir que el control se elija después de ver cuál deja mejor al objeto real.

**Ahorro:** evita rehacer el dataset y elimina una de las fuentes más caras de selección post hoc.

---

### ATJ-08 — Un atlas target-free inmutable, muchas preguntas posteriores

El atlas se materializa **as-of** una vez, con lineage y digests, y se consulta sin volver a correr kernels:

```text
una fila por event_id × config_id
features PRE / AT_EVENT
quality flags
population_id
session_id / episode_id
```

Outcomes y P&L no se almacenan en `EF1`. Cuando llegue `EF2`, se agregan desde un artefacto separado y gobernado.

**Ahorro:** densidad, dirección, tamaño, geometría y consenso multiescala comparten una sola construcción auditable.

---

### ATJ-09 — Reducir por familias, no recorrer el producto cartesiano

Orden obligatorio:

```text
familias amplias
→ efectos marginales continuos
→ agrupación de familias correlacionadas
→ una representación por familia
→ pocas interacciones justificadas
→ ≤3 hipótesis congeladas
```

No se empieza con bins pequeño/medio/grande ni con `K × densidad × dirección × tamaño × ubicación × outcome`.

Se preservan continuas las variables mientras alcance la cobertura; los thresholds son una decisión posterior y registrada.

**Ahorro:** conserva perspectivas útiles sin pagar un trial por cada celda combinatoria.

---

### ATJ-10 — Panel común de outcomes para el screening

En `EF2`, todas las familias se miran contra el mismo panel predeclarado. Ejemplo general:

```text
desplazamiento firmado
canal continuación
canal reversión
MFE / MAE en horizontes comunes
una carrera de barreras común
```

No se elige un outcome distinto para que cada feature se vea mejor. Dirección, horizonte, barreras y censura se definen una vez para la campaña.

El panel puede ser amplio porque es exploratorio, pero cada miembro queda en el ledger y las familias correlacionadas se identifican.

**Ahorro:** hace comparables las perspectivas y evita metric-shopping encubierto.

---

### ATJ-11 — Cobertura e inferencia por sesiones y episodios, no por burbujas

Todo reporte publica al menos:

```text
n_eventos
n_episodios
n_sesiones_totales
n_sesiones_con_eventos
n_sesiones_viables_por_celda
```

- La unidad de remuestreo se deriva del estimando y del proceso generador.
- Para esta familia, sesión es el cluster mínimo; episodio puede requerir otra sensibilidad.
- Miles de objetos en pocas sesiones no producen miles de apuestas independientes.

**Ahorro:** mata celdas sin potencia antes de diseñar hipótesis detalladas y evita CIs ficticiamente angostos.

---

### ATJ-12 — Ledger completo de exploración; multiplicidad no es contar filas

Todo lo probado en `EF2` registra:

```text
feature_family
representation
outcome_family
horizon
direction_channel
sample/filter
decision/result
campaign_id
```

Reglas:

- lo explorado afecta la credibilidad de lo seleccionado;
- inferencia reutilizando el mismo desarrollo contempla el proceso de selección;
- en un holdout independiente, la familia confirmatoria es el conjunto congelado y sus outcomes primarios;
- `N_eff` considera dependencia entre trials; no es un conteo bruto de gráficos o filas.

**Ahorro:** permite explorar honestamente sin fingir que sólo existieron las tres hipótesis sobrevivientes.

---

### ATJ-13 — Discovery, freeze y confirmación son artefactos distintos

```text
EF2 = EXPLORATORY_OUTCOME_SCREEN_NOT_CONFIRMATORY
EF3 = reducción
EF4 = freeze/preregistro; no produce evidencia nueva
EF5 = confirmación real en holdout
```

`EF2` requiere manifiesto, riesgos, datos faltantes, presupuesto de hipótesis y aprobación explícita de Nico antes de acceder a outcomes.

El pre-holdout usado en `EF2` queda gastado para esa selección. `EF5` no reajusta K, períodos, thresholds, dirección, costos ni controles.

**Ahorro:** evita intentar convertir retrospectivamente una exploración útil en una confirmación inválida.

---

### ATJ-14 — Sellado en dos commits: código primero, resultados después

Patrón obligatorio cuando una corrección cambia schema o números generados:

1. **Commit A:** código + schema + tests + migración/compatibilidad.
2. Ejecutar desde árbol limpio e identidad exacta del Commit A.
3. Verificar determinismo, parámetros, universo y exclusiones.
4. **Commit B:** JSON/parquets pequeños permitidos + manifiesto + docs con los números realmente regenerados.

Prohibido que un commit corrija la fórmula pero deje un JSON viejo citado como si fuera nuevo. Si el rerun no ocurrió, el documento dice `NOT_RERUN`.

**Ahorro:** separa revisión de lógica de revisión de evidencia y evita perseguir contradicciones entre script, JSON y prosa.

---

### ATJ-15 — Metadatos computados y lineage de denominadores

Toda tasa o censo serializa, en vez de esconder en comentarios:

```text
n_universe
n_available
n_processed
n_eligible
n_matched
numerator
denominator
population_id
eligibility_rule
excluded_items[]
missing_items[]
B / seed / method
schema_version
run_id
```

Cada métrica declara cuál de esos conjuntos usa. Si price-rounding usa 62 sesiones y memoria usa 59, son dos poblaciones etiquetadas, no un único `n_sesiones` ambiguo.

Listas de exclusión se computan y serializan; no se mantienen hardcodeadas en un comentario salvo como expectativa de test.

**Ahorro:** previene la familia recurrente «numerador de un conjunto / denominador de otro» y hace que el reporte se audite sin releer el script.

---

### ATJ-16 — Etiqueta epistémica para cada afirmación

Vocabulario mínimo:

| Estado | Significado |
|---|---|
| `MEASURED_COMMITTED` | medido por artefacto versionado y reproducible |
| `MEASURED_LOCAL_UNCOMMITTED` | reportado desde una corrida local aún no sellada |
| `USER_REPORTED` | comunicado por una persona; no verificado independientemente |
| `INFERRED_NOT_VERIFIED` | deducción plausible, todavía no medida |
| `PROVISIONAL_UNPARITIED` | proviene de implementación sin paridad |
| `NOT_OBSERVABLE` | el dato no permite resolverlo |
| `RETRACTED` | afirmación retirada; se conserva su traza |

Una inferencia nunca se redacta como procedencia verificada. Corregir una sobreafirmación agrega la corrección; no borra silenciosamente el camino.

**Ahorro:** reduce rondas de auditoría dedicadas a averiguar si un número fue medido, inferido o recordado.

---

### ATJ-17 — Paralelizar logística, no adelantar evidencia

Tareas costosas e independientes pueden correr en paralelo:

- pedir/exportar oráculos NT8;
- preparar hashes, IDs y manifiestos;
- completar auditorías target-free;
- escribir schemas y tests sintéticos.

Pero el output no se consume fuera de orden. Ejemplo: una exportación BigTrap puede pedirse mientras se cierran R2/R3; el atlas no usa esa exportación hasta que identidad, paridad y prerequisitos estén aprobados.

**Ahorro:** usa tiempos muertos de máquina/persona sin contaminar la secuencia analítica.

---

## 4. Matriz rápida: qué puede matar una opción

| Hallazgo | ¿Excluye? | Etapa |
|---|---:|---|
| No existen datos o sesiones mínimas | sí | `EF0-A` |
| No se puede mapear a un stream canónico común | sí, para claims causales cruzados | `EF0-A` |
| Cobertura estructural imposible por construcción | sí | `EF0-A` |
| Port provisional produce pocos eventos | no | `EF0-B` |
| Port provisional cambia dirección/lifecycle | no | `EF0-B` |
| Paridad formal FAIL | sí para uso formal; queda como objeto de depuración | contrato P2 |
| Renderer no dibuja el objeto | no demuestra ausencia analítica | `EF1` |
| Feature usa futuro o disponibilidad desconocida | sí o clase separada | `EF1` |
| Pocas sesiones por celda | bloquea hipótesis detallada, no borra la familia | `EF1/EF3` |
| Efecto exploratorio inestable | no confirma; normalmente no avanza | `EF2/EF3` |
| Holdout FAIL | cierra la hipótesis congelada | `EF5/G4` |

---

## 5. Paquete mínimo reutilizable por campaña

Antes de ejecutar cada etapa, la campaña referencia o produce:

| Artefacto | Momento |
|---|---|
| inventario de streams + hashes | antes de `EF0-A` |
| schema de identidad/disponibilidad | antes de unir fuentes |
| matriz de configs candidatas y costo | `EF0-A/B` |
| reporte de paridad por config elegible | antes de uso formal |
| feature registry PRE/AT_EVENT | antes de `EF1` |
| especificación de poblaciones y controles | antes de `EF1` |
| atlas target-free inmutable | salida `EF1` |
| manifiesto de screening + ledger de trials | antes/durante `EF2` |
| acta de reducción por familias | salida `EF3` |
| preregistro congelado | `EF4` |
| autorización + log de acceso al holdout | `EF5` |

---

## 6. Primera aplicación: HFTZones × BigTrap2

La línea que originó el playbook queda separada de `H-ES-CTX-1`:

```text
H-ES-HFT-BT2-ATLAS-1
H-ES-HFT-BT2-SCREEN-1
H-ES-HFT-BT2-INT-1
```

Estado al registrar este documento:

```text
DESIGN_ONLY_NOT_EXECUTABLE
H-ES-CTX-1 = DRAFT_NOT_FROZEN
R1 / R2 / R3 = prerequisitos pendientes
outcomes_accessed = false
holdout_opened = false
```

La capa D del diseño define integridad; la capa E fue la primera instancia del embudo. Este documento extrae sólo lo reutilizable para todo EdgeLab. No incorpora HFT×BigTrap2 al preregistro H-ES-CTX-1 y no autoriza `EF0`, `EF1` ni `EF2`.

---

## 7. Checklist de una sesión nueva

Antes de proponer otra campaña combinatoria:

- [ ] ¿Está claro qué puede excluir `EF0-A` y qué sólo puede priorizar `EF0-B`?
- [ ] ¿Todos los eventos comparten stream canónico o declaran ambigüedad?
- [ ] ¿Existe `available_at` causal para cada feature?
- [ ] ¿Se excluyó el renderer como fuente analítica?
- [ ] ¿Lifecycle distingue censura de corrupción?
- [ ] ¿Código + params + `bar_spec` + schema producen un `config_id` único?
- [ ] ¿Los controles están materializados antes de outcomes?
- [ ] ¿El atlas es target-free, as-of e inmutable?
- [ ] ¿Se reduce por familias antes de combinar?
- [ ] ¿El panel de outcomes es común y predeclarado?
- [ ] ¿Se reportan sesiones y episodios, no sólo eventos?
- [ ] ¿Todo lo explorado entra al ledger?
- [ ] ¿`EF4` es freeze y `EF5` es la confirmación?
- [ ] ¿La regeneración sigue Commit A → rerun limpio → Commit B?
- [ ] ¿Cada tasa declara población, numerador y denominador?
- [ ] ¿Cada afirmación distingue medido, inferido, provisional y retractado?

**Aporte al referente:** estas prácticas reducen exportaciones inútiles, joins ambiguos, recomputaciones, controles post hoc y auditorías de contradicciones. El tiempo ahorrado se desplaza de infraestructura repetida a preguntas que sí pueden acercarse a un edge válido y aplicable.
