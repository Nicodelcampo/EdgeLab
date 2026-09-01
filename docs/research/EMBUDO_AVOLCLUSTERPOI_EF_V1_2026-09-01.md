# Embudo de medición — aVolClusterPOI (EF V1, diseño)

- **Fecha de registro:** 2026-09-01 (ART)
- **Autor:** Notion AI — Auditor Cuantitativo. **Pedido por:** Nicolás.
- **Estado:** `DESIGN_ONLY_NOT_EXECUTABLE` · `NOT_A_CAMPAIGN` · `DOES_NOT_AUTHORIZE_OUTCOMES`
- **Holdout:** no se abre, no se toca, no se menciona como fuente.
- **Namespace:** `EF0-A … EF5` de `docs/research_funnel_playbook.md`. No se crea otro conjunto de etapas.
- **Objeto:** `nt8/aVolClusterPOI.cs` v0.5 (research freeze), blob `d512d91a606d41609b21ef244c896ead1dc52a10`, leído completo para escribir este documento.
- **Estado epistémico del objeto:** `parity_pending`, con registro abierto en `docs/parity_coverage/aVolClusterPOI.md` (creado 2026-09-01). **Corrige a la V1:** sí existe contraparte Python — `edgelab/bridge/indicators/avolclusterpoi.py` v0.5, blob `e472a06899e3d76287072fdbeef4b95604101eb3` — y es **parcial**; ver §10. La cabecera del propio `.cs` sigue vigente: «No usar sus zonas para operar hasta pasar el pipeline estandar».
- **Enmiendas vigentes:** **V1.1 (2026-09-01)** — ver §9: vincula `bar_spec = tick:120` sobre NQ y corrige el encuadre del gate de paridad del §4. **V1.2 (2026-09-01)** — ver §10: corrige la afirmación de que no había contraparte Python y fija el alcance real del gate.

---

## 0. El principio que hace válido un embudo adaptativo

Lo pedido: ir de medidas generales a particulares, donde la particularización no es al azar sino guiada por lo que arrojen las mediciones iniciales. Eso es correcto y es la forma barata de trabajar — **pero sólo suma evidencia si se prerregistra el mapa, no las conclusiones.**

Regla constitutiva de este embudo:

> Antes de correr una etapa, se declara por escrito: (a) qué mide, (b) qué **variables de decisión** produce, (c) con qué **umbrales**, (d) **qué rama abre cada resultado posible**.

Si las ramas se eligen después de ver los números, el embudo deja de ser un embudo y pasa a ser *garden of forking paths*: cada decisión post hoc gasta evidencia sin registrarla, y ninguna medición posterior puede ser confirmatoria. El adaptativo legítimo es un árbol de decisión fijado de antemano, no una improvisación informada.

Dos parámetros se declaran **ahora, antes de medir nada**:

1. **Efecto mínimo económicamente relevante: ≥ 1 tick** (misma vara que Gate 1). Lección del 2026-08-31: con 234 sesiones, 9 de 16 celdas dieron `p_holm ≤ 0,05` y el efecto máximo fue **0,261 ticks** — estadísticamente significativo, económicamente nulo. La puerta económica se declara antes o no sirve.
2. **Unidad de inferencia: la sesión.** No la zona. Miles de zonas en pocas sesiones no son miles de apuestas independientes (ATJ-11).

Todo lo explorado entra al ledger (ATJ-12), incluso lo que se descarta.

---

## 1. Qué emite el objeto (leído del código, no supuesto)

| Pieza | Comportamiento declarado y verificado en el fuente |
|---|---|
| Unidad de detección | Bloque de `WindowBars = 10` barras primarias; contador reiniciado al inicio de sesión; bloque parcial final descartado |
| Perfil por precio | Reconstruido siempre desde la subserie de 1 tick; celdas en **ticks enteros** (ULP 0 por construcción); ticks fuera de `[low, high]` de la barra ignorados |
| Nivel «hot» | `vol_celda ≥ mediana(bloque) × MedianMultiplier` (2.0); mediana = superior para n par |
| Cluster | Niveles hot contiguos con `gap ≤ MaxGapTicks` (1) y `≥ MinClusterTicks` (2); score = **suma** de volumen |
| Umbral de anomalía | Cuantil **empírico sin interpolar** (p98) del historial del **mismo bucket horario** (30 min, relativo a sesión), con `≥ MinSamplesPerBucket` (20), FIFO `LookbackSessions` (20). **Sin fallback global**: sin historia del bucket, no detecta |
| Cardinalidad | **Una zona por bloque**: el cluster de máxima masa entre los que pasan |
| Muestra al historial | Una por bloque = score del mejor cluster (**0 si no hubo**), commiteada al iniciar la sesión siguiente ⇒ causal, sin look-ahead |
| Dirección | LONG si el cierre creador queda arriba (soporte), SHORT si abajo (resistencia), y si cierra **dentro** ⇒ `AT_PRICE` (población aparte) |
| QualityScore | Heurístico 0–100: anomalía 35 %, concentración 25 %, densidad 15 %, rechazo 15 %, ráfaga 10 %. Declarado explícitamente **no probabilidad calibrada** |
| Ciclo de vida | Touch = intersección de rangos; default `CloseThrough`; `MaxAgeBars = 0` (sin expiración); `MaxTouches = 0` (ilimitado) |
| Evaluador forward | Tras el primer toque: MFE/MAE en ticks, `TARGET` 12 t / `STOP` 8 t / `TIMEOUT` 50 barras; empate en la misma barra ⇒ **`AMBIGUOUS`** (no inventa el orden — bien) |
| Export | CSV con meta completa en línea 1; eventos `ZONE_CREATED`, `AT_PRICE_CREATED`, `FIRST_TOUCH`, `ZONE_INVALIDATED`; modo **overwrite** siempre |

El diseño interno es notablemente disciplinado: aritmética entera, sin fallback que mezcle horas, historial sólo de sesiones completas anteriores, cuantil sin interpolar, `AMBIGUOUS` en vez de inventar orden. Eso hace que el embudo pueda arrancar en factibilidad y no en limpieza.

---

## 2. Cinco hallazgos estructurales del código que condicionan el embudo

**H1 — El export mezcla features con outcomes.** Las columnas `touch_bar`, `mfe_ticks`, `mae_ticks`, `outcome` viajan en las filas `FIRST_TOUCH` y `ZONE_INVALIDATED`. Consecuencia dura: el atlas de `EF1` **debe proyectarlas fuera explícitamente** para ser target-free. Leerlas es `EF2` y requiere aprobación escrita. No es un detalle de estilo: es dónde está el cortafuegos.

**H2 — Riesgo de umbral degenerado.** La muestra por bloque incluye los ceros (bloques sin cluster). Si los clusters son raros en un bucket, el p98 puede ser **0**, y el código exige `thresh > 0` para que una zona pase ⇒ **el detector no enciende nunca en ese bucket**. Es el mismo patrón que los `quintile_edges` degenerados que aparecieron en Gate 1 sobre NQ. Se mide antes de cualquier hipótesis.

**H3 — Warm-up estructuralmente ajustado.** Con una muestra por bloque·bucket·sesión, `MinSamplesPerBucket = 20` y `LookbackSessions = 20`, la FIFO retiene apenas el mínimo exigido. Cuántas muestras por bucket entran por sesión depende del `bar_spec`, y de eso depende si el detector alguna vez alcanza el mínimo. Medible y barato.

**H4 — `AT_PRICE` fuera del ciclo de vida.** El lifecycle hace `continue` sobre esas zonas: nunca reciben `FIRST_TOUCH` ni invalidación, y quedan acumulándose en el estado interno. Población separada, sólo con evento de creación. No se comparan sus tasas con las de `OFF_PRICE` como si fueran lo mismo.

**H5 — La ráfaga cruza sesiones.** La lista `creations` sólo se poda por ventana de 200 barras, no al inicio de sesión ⇒ `burst_count` puede contar creaciones de sesiones distintas. Declarable; no fatal, pero no se interpreta «ráfaga» como fenómeno intrasesión sin corregirlo.

---

## 3. `EF0-A` — Factibilidad del dato (puede EXCLUIR; target-free; barato)

Cinco preguntas, cada una con su regla de decisión declarada de antemano:

| # | Qué se mide | Rama si NO | Rama si SÍ |
|---|---|---|---|
| A1 | ¿El tick store congelado tiene **volumen por tick**? El detector reconstruye el perfil desde la subserie de 1 tick: sin volumen por precio no existe el objeto | **EXCLUYE** la réplica en Python sobre ese store; la línea queda dependiendo de un export NT8 (y de la limitación de la prueba gratuita) | Sigue a A2 |
| A2 | Bloques por bucket por sesión, y sesiones completas por contrato (alimenta H3) | Si no se alcanzan 20 muestras/bucket: **reparametrizar bucket/lookback antes de medir nada** — y eso es un `config_id` nuevo, no un ajuste silencioso | Sigue a A3 |
| A3 | Distribución de mejores scores por bucket (alimenta H2) | Si el p98 es 0 en la mayoría de buckets: el detector no enciende con los defaults ⇒ decisión de reparametrización **declarada**, no post hoc | Sigue a A4 |
| A4 | Zona horaria de los timestamps y semántica de sesión | Queda `NOT_OBSERVABLE` hasta que Nico declare TZ (misma deuda que la línea L2 de ZB) | Sigue a A5 |
| A5 | Sesiones pre-holdout disponibles **menos** las quemadas por warm-up | Si el remanente no da potencia por celda, se cierra la ambición de grilla fina antes de diseñarla | Habilita `EF0-B` |

Salida: acta `EF0-A` con esos números y nada más. Cero outcomes.

---

## 4. `EF0-B` — Probe provisional (prioriza; **no** excluye)

> **Corregido por la enmienda V1.1, §9.1.** Este parágrafo asumía implícitamente el camino del port en Python. Si el embudo se mide sobre el CSV nativo de NT8, no hay gate de paridad.
>
> **Corregido otra vez por la V1.2, §10.1.** Dos afirmaciones de acá quedaron falsas: la réplica Python **ya existe** (parcial, `edgelab/bridge/indicators/avolclusterpoi.py`), y `docs/parity_coverage/aVolClusterPOI.md` **ya fue creado**. Lo que falta es el oráculo.

- Réplica Python del contrato de la cabecera (ticks enteros ⇒ exposición ULP 0 por construcción; verificar con `tools/ulp_exposure.py`).
- Oráculo NT8 sobre una ventana chica y creación de `docs/parity_coverage/aVolClusterPOI.md` bajo las reglas fail-closed del contrato de paridad.
- **Regla del playbook (ATJ-01):** pocos eventos, dirección rara o lifecycle anómalo **no excluyen** ninguna configuración mientras el port no tenga paridad. Un bug de réplica no es un resultado científico.

---

## 5. `EF1` — Atlas estructural target-free (acá se decide qué se pregunta después)

Una fila por zona × `config_id`, con features PRE/AT_EVENT, quality flags, `population_id`, `session_id`. **Sin outcomes** — proyección explícita por H1. Inmutable y as-of (ATJ-08).

Poblaciones materializadas **antes** de mirar cualquier outcome (ATJ-07):

- zona real (`OFF_PRICE`), separada de `AT_PRICE` por H4;
- **near-miss**: el cluster que pasó el umbral pero fue descartado por la regla de uno-por-bloque, y el que quedó a un pelo del percentil;
- control genérico emparejado por sesión · bucket · volatilidad.

Variables de decisión de `EF1` — todas target-free — y qué rama abre cada una:

| Variable | Qué decide |
|---|---|
| Eventos por sesión y sesiones con eventos | Potencia disponible. Si no hay sesiones viables por celda, la celda **muere antes de existir** (ATJ-11). Este es el filtro que Gate 1 enseñó a poner primero |
| Balance LONG/SHORT y share `AT_PRICE` | Si hay una, dos o tres poblaciones que analizar |
| Ancho de zona, densidad, `anomaly_ratio`, `distance_ticks` | Si alcanza **una** representación por familia o hay que separar (ATJ-09) |
| Solapamiento con `aVolCellPOI2` y con los eventos BT2A del store congelado | Redundancia. Si es alto, la pregunta correcta pasa a ser **incremental** («¿agrega algo sobre lo ya medido?»), no nueva |
| Integridad de lifecycle: censura por derecha vs corrupción (ATJ-05) | Qué zonas son analizables y cuáles quedan en clase separada |

**Éste es el corazón del embudo:** las mediciones de `EF0-A` y `EF1` están elegidas justamente porque sus resultados determinan qué hipótesis tiene sentido escribir después — y las reglas de esa determinación están escritas arriba, antes de correrlas.

---

## 6. `EF2` — Screening exploratorio (requiere aprobación escrita; consume pre-holdout)

- Panel común predeclarado de outcomes (ATJ-10): desplazamiento firmado, MFE/MAE en horizontes comunes, una carrera de barreras común.
- **El evaluador interno del indicador (12 t / 8 t / 50 barras) no es el outcome primario:** son tres parámetros elegidos por el autor, no un panel neutral. Queda como comparador secundario, declarado.
- Unidad de remuestreo = sesión; bootstrap por sesión; Holm sobre la grilla; **efecto mínimo ≥ 1 tick** ya declarado en §0.
- Etiqueta obligatoria del resultado: `EXPLORATORY_OUTCOME_SCREEN_NOT_CONFIRMATORY`.
- El pre-holdout usado acá queda **gastado** para esta selección.

---

## 7. `EF3` → `EF4` → `EF5`

- `EF3`: reducción por familias, no recorrido del producto cartesiano (ATJ-09).
- `EF4`: freeze de **≤ 3 hipótesis** con `config_id`, poblaciones, outcome primario, umbral económico y potencia requerida. No produce evidencia nueva.
- `EF5`: confirmación, sólo con autorización de holdout bajo `docs/edge_validation_contract.md` (G4). No reajusta nada de lo congelado.

---

## 8. Lo que este documento NO hace

No autoriza `EF0`, `EF1` ni `EF2`. No accede a outcomes. No abre el holdout. No declara paridad ni la hereda. No promueve nada. No habilita usar las zonas para operar — lo prohíbe la propia cabecera del indicador.

## Aporte al referente

Un embudo adaptativo con **mapa prerregistrado** es lo que permite que «particularizar según lo que se midió» acumule evidencia en vez de gastarla. La diferencia entre este diseño y una exploración improvisada no está en los números que se van a medir, sino en que las ramas ya están escritas antes de verlos.

---

## 9. Enmienda V1.1 (2026-09-01) — vinculación de config y corrección del gate de paridad

**Origen.** Nico observa que el indicador **ya se corrió sobre NQ** y que la configuración de uso está definida: **barra primaria = 120 Tick**. Tiene razón en la consecuencia práctica, y eso corrige el §4.

### 9.1 Qué se corrige

Correr el `.cs` en NT8 sobre NQ produce el **lado de referencia** de la comparación — el oráculo — no la paridad. Según `docs/parity_coverage/README.md`, en este proyecto la paridad es una propiedad de un **par** de implementaciones (oráculo NT8 contra kernel Python), con estados `parity_exact`, `parity_covered`, `parity_pending`, `parity_failed`.

De ahí la consecuencia que tenía mal encuadrada:

| | Camino A — nativo | Camino B — port Python |
|---|---|---|
| Qué se mide | El CSV que emite el `.cs` en NT8 | Una réplica en Python sobre el store de ticks |
| Gate de paridad | **No aplica.** No hay segunda implementación que pueda discrepar | `parity_pending` ⇒ oráculo obligatorio |
| Techo | Una corrida por chart, CSV en modo overwrite, sin barrido de configs | Escala, grillas, Kaggle |
| Deudas abiertas | §9.4 y §9.6 | §9.3, §9.4, §9.6 y §9.7 |

**Si el embudo se mide en el camino A, la paridad no está en el camino crítico.** Aparece recién cuando queramos barrer configuraciones o correr a escala.

### 9.2 Vinculación de configuración

`instrument = NQ`, `bar_spec = tick:120`, resto = defaults v0.5 del `.cs`. **Origen: declaración de Nico en chat, 2026-09-01 — declarado, no medido por mí.** Falta declarar todavía: rango de fechas, plantilla de Trading Hours, TZ y mes de contrato.

### 9.3 Deuda medida — barras de tick (camino B, y quizá también A)

`docs/campaigns/TICKBAR-001_paridad_en_barras_de_tick.md`, **estado ABIERTA desde 2026-07-25**:

- `tick:25` → FAIL con **89,12 % de `FOOTPRINT_MISMATCH`** (26.661 de 29.916 barras).
- Clasificación confirmada: **H2 BAR BUILDER**. H1 (stream) descartada con evidencia dura: digests de 64 bits **idénticos** sobre 4.229 eventos, calculados por dos implementaciones independientes.
- Mecanismo exacto: el `take + reset` que corre en `OnBarUpdate(BarsInProgress == 0)` captura un conjunto de eventos de la subserie de 1 tick que **no** es el que le corresponde a la barra primaria que acaba de cerrar.
- Medido: `vol_fp == vol_bar` en **40/150** barras a 25 t y **19/150** a 10 t.
- Dueño declarado del defecto: **el `.cs`**. Textual del acta: «NT8 no está en desacuerdo con Python: está en desacuerdo consigo mismo».

**Por qué aplica a aVolClusterPOI.** Construye el perfil con el mismo patrón: `AddDataSeries(BarsPeriodType.Tick, 1)`, acumula en `tickProfile` bajo BIP 1, y en BIP 0 hace el snapshot a `blockCells` y `tickProfile.Clear()`. No es una analogía: es la misma estructura en el mismo callback.

### 9.4 Hallazgo nuevo H7 — el filtro de rango convierte mala atribución en pérdida silenciosa

En el snapshot el código hace `if (kv.Key < lowTick || kv.Key > highTick) continue;`. Si por el desfase de la subserie llegan eventos de la barra siguiente y su precio cae fuera de `[low, high]` de la barra que cerró, **se descartan**: no se reasignan a la barra correcta, se pierden. En TICKBAR-001 el volumen total se conservaba (desvío de 0,94 %, mala asignación); acá el filtro puede producir **pérdida neta** en las celdas — justo lo que alimenta mediana → nivel hot → masa del cluster.

**Atenuante esperado, no medido:** a 120 ticks por barra el borde es ~1/120 del contenido, contra 1/25 y 1/10 de las mediciones existentes, y el bloque suma 10 barras consecutivas, con lo cual parte del corrimiento se compensa dentro del bloque. Es una hipótesis con signo esperado, **no un número**.

### 9.5 Cómo se cierra, barato, con instrumental que ya existe

`nt8/TickBarDiag.cs` y `tools/tickbar_diag.py` ya están escritos, y el runbook de captura está en `docs/campaigns/TICKBAR-001_captura_nt8.md`. Repetir esa captura con **NQ a 120 Tick** (pocos minutos, 150 barras) da la tasa `vol_fp == vol_bar` a la resolución real de trabajo. Ramas declaradas de antemano:

- tasa ≈ 100 % ⇒ el defecto es despreciable a 120 t, se declara **con número**, y deja de bloquear.
- tasa baja ⇒ el CSV nativo **también** está afectado ⇒ **el camino A tampoco es seguro**: no sería un problema de traducción sino del objeto medido.

Esa segunda rama es la razón por la que la medición vale la pena aunque nunca hagamos el port.

### 9.6 Hallazgo nuevo H6 — el meta del CSV no identifica la corrida

Verificado leyendo `EmitEvent`: la línea 1 registra indicador, versión, instrumento, `tick_size`, `window_bars`, `median_mult`, `max_gap_ticks`, `min_cluster_ticks`, `bucket_minutes`, `percentile`, `lookback_sessions`, `min_samples`, filtro predictivo, `min_quality`, los tres `reaction_*`, `session_buckets`, `invalidation`, `max_age_bars`, `max_touches`, `one_cluster_per_block`, `kinds`, `export`, `footprint`, `quantile` y `write_mode`.

**No registra `bar_spec`, ni plantilla de Trading Hours, ni rango de fechas, ni TZ.**

Consecuencia: dos corridas a 120 t y a 500 t producen **metas idénticas** y objetos completamente distintos. Un CSV de este indicador **no puede autoidentificarse como «120 ticks»**. Es la misma clase de falla que el 2026-07-25 produjo una captura mal rotulada y un `BAR_BUILDER_MISMATCH` falso, y que se cerró agregando el sufijo automático de resolución al nombre del archivo.

**Regla de admisión para esta línea:** ningún CSV de aVolClusterPOI se admite sin `bar_spec`, plantilla de sesión, rango y TZ declarados por fuera del archivo y registrados junto al hash del CSV. Lo correcto de fondo es agregarlos al meta del `.cs` — cambio chico, pero toca el detector congelado y por lo tanto es decisión de Nico.

### 9.7 Deuda medida — calendario de sesiones (camino B)

El único oráculo real que corrió en el proyecto (`aVolCellPOI2`, 2026-07-26) **falló por calendario**: Python contó 28 sesiones y NT8 25 sobre el mismo tramo, por el feriado del 3 de julio; con `min_sessions = 15` cada lado empezó a detectar en sesiones distintas (16 contra 22). Las 2 zonas que ambos vieron **coincidieron**: el desacuerdo no era sobre qué es una anomalía, sino sobre cuándo hay suficiente historia. aVolClusterPOI tiene exactamente la misma dependencia (`LookbackSessions = 20`, `MinSamplesPerBucket = 20`, buckets relativos a `ActualSessionBegin`) ⇒ **el mismo modo de falla está precargado**. La decisión de cuál calendario es la referencia sigue **pendiente de Nico** desde julio.

### 9.8 Con `tick:120` fijado, H3 ya es calculable (ESTIMADO)

Insumos **medidos** del store de ticks congelado de NQ (auditoría Gate 1, 2026-08-31): 119.153.201 ticks en 298 sesiones sobre 5 contratos ⇒ **~399.843 ticks por sesión**.

| Magnitud | Valor | Clase |
|---|---:|---|
| Ticks por sesión | ~399.843 | derivado de medido |
| Barras por sesión a 120 t | ~3.332 | estimado |
| Bloques por sesión (`WindowBars = 10`) | **~333** | estimado |
| Buckets de 30 min en sesión ETH (~23 h) | 46 | declarado |
| Muestras por bucket por sesión (promedio) | **~7,2** | estimado |

**Lectura:** con ~7 muestras por bucket por sesión, `MinSamplesPerBucket = 20` se alcanza en **~3 sesiones** en los buckets activos — H3 es mucho menos restrictivo de lo que temía en la V1.

**Pero el promedio miente por construcción:** los ticks no se reparten parejo. En los buckets nocturnos un bloque de 1.200 ticks puede abarcar 30 minutos o más, o sea **menos de una muestra por bucket por sesión**, y con FIFO de 20 sesiones esos buckets **nunca** llegan al mínimo. Predicción falsable derivada: el detector es **estructuralmente ciego fuera de RTH**, y la cobertura por bucket va a tener forma de U invertida. Esto se mide en `EF0-A` A2 y decide si la unidad de análisis debe restringirse a RTH antes de escribir cualquier hipótesis.

Supuesto declarado: una fila del parquet = un evento de trade, y las barras de tick de NT8 cuentan trades recibidos. Si NT8 cuenta de otra forma (por ejemplo, agregando por timestamp), el conteo de barras cambia y con él toda esta tabla.

### 9.9 Qué queda igual

Todo el resto de la V1: prerregistrar el mapa antes de ver los números, efecto mínimo ≥ 1 tick, unidad = sesión, H1–H5, y el orden `EF0-A` → `EF1` → `EF2`. H2 (umbral degenerado) y H3 (warm-up) siguen siendo las primeras mediciones — ahora con el `bar_spec` que faltaba para poder calcularlas.

---

## 10. Enmienda V1.2 (2026-09-01) — sí hay contraparte Python, y el alcance real del gate

**Origen.** Nico ofrece exportar un oráculo. Al preparar el pliego verifiqué el otro lado del par y encontré que **dos afirmaciones de este documento eran falsas**.

### 10.1 Corrección de hecho

La V1 declaraba `PROVISIONAL_UNPARITIED` con «ausencia verificada: no existe `docs/parity_coverage/aVolClusterPOI.md`». El archivo ahora existe, pero eso es lo menos importante: **la inferencia de fondo estaba mal.** Confundí ausencia de **registro** con ausencia de **implementación**.

Sí existe contraparte Python: `edgelab/bridge/indicators/avolclusterpoi.py` v0.5, blob `e472a06899e3d76287072fdbeef4b95604101eb3`, 6.138 B, leído completo. No estaba en `edgelab/bridge/kernels/` — donde sólo viven `bigtrap2_port.py` y `hftzones_es_pure_v2_flat.py` — sino en `edgelab/bridge/indicators/`, junto a los otros nueve ports. Por eso no apareció cuando busqué el port.

Registro de la falla de método, para el ledger: **la ausencia de un documento de cobertura no es evidencia de la ausencia del kernel.** Es el mismo error de clase que el falso negativo de `search_code` del 2026-08-31, y la corrección es la misma: listar el árbol en vez de inferir de un índice.

### 10.2 El kernel es parcial, y eso define qué puede validar el oráculo

6 KB contra 42 KB del `.cs`, y la diferencia es de alcance, no de estilo. Su propio docstring lo dice: «No QualityScore gate, no target/stop, no BigTrap2».

**Cubre:** mediana superior de las celdas · hot `≥ med × MedianMultiplier` · clusters por `MaxGapTicks`/`MinClusterTicks` · score = suma de volumen · `GetTimeBucket` con el anchor `close − 1 s` · `EmpiricalQuantile` p98 con `ceil` · `CommitSession` con FIFO por **sesión** completa · abstención por `MinSamplesPerBucket` · un cluster de masa máxima por bloque · `AT_PRICE` vs `OFF_PRICE` con `direction` y `distance_ticks`. Los 10 parámetros de su `RESEARCH_DEFAULTS` **coinciden** con el censo del `.cs` del 2026-08-13.

**No cubre:** la construcción de barras ni la acumulación del `tickProfile` — `detect_block` recibe las celdas **ya armadas** — ni `PriceToTick`, ni el filtro `[lowTick, highTick]`, ni `ProcessLifecycle` (`FIRST_TOUCH`, `ZONE_INVALIDATED`, `MaxAgeBars`, `MaxTouches`), ni `UpdateOutcome` (`mfe_ticks`, `mae_ticks`, `outcome`), ni `QualityScore`, ni el filtro predictivo, ni el burst, ni `EmitEvent`.

**Consecuencia:** la paridad alcanzable hoy es la de **creación de zonas**. El ciclo de vida y los outcomes quedan afuera **por ausencia de implementación**, no por decisión metodológica. Y eso alcanza: `EF0-A` y `EF1` son target-free y sólo necesitan que el objeto que crea zonas sea reproducible.

Corolario sobre el camino B del §9.1: el port **no es escribir de cero, es completar**. Cambia el costo estimado de ese camino, no su gate.

### 10.3 El gate no atribuye la culpa (leído en `edgelab/bridge/parity.py`)

Matching bipartito greedy por `created_ms` más geometría en **medio-ticks** (para evitar el banker's rounding que produjo `GEOMETRY_DIFF` falsos en BigTrap2 y VolTicksPOC2; nuestras zonas tienen bordes en ticks enteros, así que no aplica).

- **FAIL:** `MISSING_IN_NT8`, `MISSING_IN_PYTHON`, `GEOMETRY_DIFF`. Geometría **exacta** por defecto (`tol_geom_ticks = 0`).
- **WARN:** `TIMESTAMP_DIFF`, `STATE_ORDER_DIFF`, `FEATURE_DIFF`, `CALIBRATION_DIFF`, **`FOOTPRINT_MISMATCH`** — que entra por `extra_diags` y por lo tanto **no bloquea**.

Pero el efecto indirecto sí bloquea: si NT8 arma las celdas con el defecto de `TICKBAR-001` y Python las arma desde el tick store, difieren las celdas ⇒ difieren los clusters ⇒ aterriza como `GEOMETRY_DIFF` o como huérfanas. **El matcher no puede distinguir «el kernel está mal traducido» de «el bar builder está en desacuerdo consigo mismo»:** los dos escenarios producen los mismos códigos.

De ahí la regla operativa: **la captura `TickBarDiag` a 120 t va pareada con el oráculo, en la misma corrida, no después.** Sin ella, un FAIL manda a depurar el kernel teniendo el defecto ya declarado en el `.cs` desde el 2026-07-25.

### 10.4 Antecedente útil sobre dónde falla este par

El docstring del kernel registra que la paridad de `SessionProfile` **ya fue corregida el 2026-08-14**: la versión previa aplanaba los scores en un `deque` con tope `lookback`, retenía ~6-7 sesiones cuando `lookback = 20`, y descartaba la primera sesión completa. Las dos cosas contradecían `CommitSession`.

Lectura: los desacuerdos históricos de este par aparecieron en la **contabilidad de la historia**, no en la geometría del cluster. Coincide con el modo de falla de `aVolCellPOI2` (§9.7) y con el riesgo de calendario. Es dónde hay que mirar primero si el gate da FAIL.

### 10.5 Pliego del oráculo

El pliego completo vive en `docs/parity_coverage/aVolClusterPOI.md` §4 y no se duplica acá. Los dos puntos que condicionan el diseño del embudo:

1. **Forzar `EnablePredictiveFilter = false`, `MinQualityScore = 0`, `MaxAgeBars = 0`, `MaxTouches = 0`.** Si el `.cs` descarta eventos que el kernel no sabe descartar, el gate los reporta como `MISSING_IN_NT8`: sería un FAIL de configuración disfrazado de FAIL de paridad.
2. **≥ 35 sesiones cargadas**, siguiendo el precedente de `aVolCellPOI2`, y rango fuera del holdout declarado antes de exportar.

### 10.6 Qué no cambia

El mapa prerregistrado, el efecto mínimo ≥ 1 tick, la unidad = sesión, H1–H7 y el orden `EF0-A` → `EF1` → `EF2`. La paridad de creación es condición de reproducibilidad, **no** evidencia de borde: un `PASS` no dice nada sobre si las zonas anticipan algo.
