# aVolClusterPOI — cobertura de paridad

**Estado:** `parity_pending`
**Creado:** 2026-09-01
**Etiquetas:** `NO_AUTORIZA_OUTCOMES` · `NO_ABRE_HOLDOUT` · no habilita operar las zonas.

| Lado | Artefacto | Blob | Tamaño |
|---|---|---|---|
| Oráculo (NT8) | `nt8/aVolClusterPOI.cs` v0.5 | `d512d91a606d41609b21ef244c896ead1dc52a10` | 42.386 B |
| Kernel (Python) | `edgelab/bridge/indicators/avolclusterpoi.py` v0.5 | `e472a06899e3d76287072fdbeef4b95604101eb3` | 6.138 B |
| Matcher | `edgelab/bridge/parity.py` | `600844aec7f3a7bd38338372368d2db18eb10b0e` | 7.730 B |

**Oráculos registrados: ninguno.** La cabecera del `.cs` dice: «ESTADO: DETECTOR CONGELADO para paridad P2 con el kernel Python. No usar sus zonas para operar hasta pasar el pipeline estandar».

## 0. Por qué existe este archivo

Hasta hoy no había `docs/parity_coverage/aVolClusterPOI.md`, y esa ausencia **era** el estado `PROVISIONAL_UNPARITIED`. Nico ofreció exportar un oráculo (chat 2026-09-01). Este archivo fija, **antes** de exportar, qué puede y qué no puede validar ese oráculo — para que la corrida en NT8 no se desperdicie y para que un FAIL sea interpretable.

## 1. Sí existe contraparte Python, y es parcial

El kernel no está en `edgelab/bridge/kernels/` (ahí sólo hay `bigtrap2_port.py` y `hftzones_es_pure_v2_flat.py`) sino en `edgelab/bridge/indicators/`. Leído completo. Son 6 KB contra 42 KB del `.cs`, y la diferencia no es estilo: es alcance. Su propio docstring lo dice — «No QualityScore gate, no target/stop, no BigTrap2».

| Etapa del `.cs` | Kernel Python | Cobertura |
|---|---|---|
| `AddDataSeries(Tick,1)` + acumulación de `tickProfile` en BIP 1 | ausente | **NO** |
| snapshot a `blockCells` + `Clear()` en BIP 0, con filtro `[lowTick, highTick]` | ausente | **NO** |
| `PriceToTick` | ausente | **NO** |
| mediana superior de las celdas | `median_upper` | sí |
| hot = celdas `>= med × MedianMultiplier` | `cluster_hot_ticks` | sí |
| clusters por `MaxGapTicks` / `MinClusterTicks` | `cluster_hot_ticks` | sí |
| score = suma de volumen del cluster | `cluster_hot_ticks` | sí |
| `GetTimeBucket(Time[0])` con anchor `close − 1 s` | `session_relative_bucket` | sí (espejo declarado) |
| `EmpiricalQuantile` p98 (ceil) | `empirical_quantile` | sí |
| `CommitSession` — FIFO por **sesión** completa | `SessionProfile.commit` | sí (corregido 2026-08-14) |
| `MinSamplesPerBucket` → abstención | `detect_block` → `abstain="warmup"` | sí |
| un cluster de masa máxima por bloque | `detect_block` | sí |
| `AT_PRICE` vs `OFF_PRICE` + `direction` + `distance_ticks` | `classify_kind` | sí |
| `ProcessLifecycle`: `FIRST_TOUCH`, `ZONE_INVALIDATED`, `MaxAgeBars`, `MaxTouches` | ausente | **NO** |
| `UpdateOutcome`: `mfe_ticks`, `mae_ticks`, `outcome`, `ReactionHorizon/Target/Stop` | ausente | **NO** |
| `QualityScore` (35/25/15/15/10) + `MinQualityScore` + filtro predictivo | ausente | **NO** |
| burst: `CountNearbyCreations`, `BurstMinZones/WindowBars/RangeTicks` | ausente | **NO** |
| `EmitEvent` / las 25 columnas del CSV | ausente | **NO** |

Los 10 parámetros que el kernel declara en `RESEARCH_DEFAULTS` **coinciden** con el censo del `.cs` del 2026-08-13: `window_bars=10`, `median_multiplier=2.0`, `max_gap_ticks=1`, `min_cluster_ticks=2`, `time_bucket_minutes=30`, `lookback_sessions=20`, `detection_percentile=98.0`, `min_samples_per_bucket=20`, `max_age_bars=0`, `one_cluster_per_block=True`.

Antecedente registrado en el docstring: la paridad de `SessionProfile` **ya fue corregida el 2026-08-14**. La versión previa aplanaba los scores en un `deque` con tope `lookback`, con lo que retenía ~6-7 sesiones cuando `lookback=20`, y además descartaba la primera sesión completa. Las dos cosas contradecían `CommitSession`. Precedente útil: los desacuerdos de este par aparecen en la **contabilidad de historia**, no en la geometría del cluster.

### Consecuencia sobre el alcance del gate

La paridad alcanzable hoy es la de **creación de zonas** (`ZONE_CREATED` / `AT_PRICE_CREATED`). El ciclo de vida y los outcomes quedan afuera **por ausencia de implementación Python**, no por decisión metodológica.

Eso no es un problema para el embudo: EF0-A y EF1 son target-free y sólo necesitan que el objeto que crea zonas sea reproducible. Es exactamente la parte que el kernel cubre.

## 2. Qué compara el matcher (medido en el código)

Matching bipartito greedy por cercanía de `created_ms` más geometría, medida en **medio-ticks** para evitar el banker's rounding que producía `GEOMETRY_DIFF` falsos en BigTrap2 y VolTicksPOC2. Nuestras zonas tienen bordes en ticks enteros (`ticks[0]`, `ticks[-1]`), así que ese problema no aplica acá.

- **FAIL:** `MISSING_IN_NT8`, `MISSING_IN_PYTHON`, `GEOMETRY_DIFF`.
- **WARN:** `TIMESTAMP_DIFF`, `STATE_ORDER_DIFF`, `FEATURE_DIFF`, `CALIBRATION_DIFF`, `FOOTPRINT_MISMATCH`.
- **PASS** = cero huérfanas y cero diferencia geométrica.
- Tolerancias por defecto: `tol_created_ms=60_000` para candidatear, `strict_created_ms=1_000` para marcar `TIMESTAMP_DIFF`, `tol_geom_ticks=0` (geometría **exacta**), y un límite duro de 8 ticks para siquiera considerar un candidato.
- `maturity_frontier_ms`: las zonas creadas cerca del final de la ventana se comparan sólo por geometría y timestamp; su estado y toques se registran como `MATURITY_TAIL` informativo. Con el kernel actual esto es irrelevante — no hay lifecycle que comparar.

## 3. El gate no dice de quién es la culpa

`FOOTPRINT_MISMATCH` está en `WARN_CODES` y entra por `extra_diags`: lo emiten sesiones, kernels o P1A, no el matcher. O sea que el desacuerdo de footprint **degrada a WARN y no bloquea**.

Pero el efecto indirecto sí puede hacer FAIL: si NT8 arma las celdas del bloque con el defecto de `TICKBAR-001` y Python las arma desde el tick store, las celdas difieren, los clusters difieren, y eso aterriza como `GEOMETRY_DIFF` o como huérfanas. El matcher **no puede distinguir** «el kernel está mal traducido» de «el bar builder de NT8 está en desacuerdo consigo mismo». Los dos escenarios producen los mismos códigos.

Por eso la captura de diagnóstico no es opcional ni posterior: sin ella, un FAIL del gate manda a depurar el kernel cuando el defecto ya está declarado en el `.cs` desde el 2026-07-25, con dueño asignado y `89,12 %` de `FOOTPRINT_MISMATCH` medido a `tick:25`.

## 4. Pliego del oráculo #1

Dos exportaciones, **mismo chart, misma plantilla de sesión, misma corrida**:

### 4.1 Oráculo del indicador

- **Instrumento:** NQ (mes de contrato a declarar).
- **Barra primaria:** `120 Tick` (declarado por Nico, chat 2026-09-01).
- **Parámetros:** los defaults del censo. Explícitamente `EnablePredictiveFilter=false`, `MinQualityScore=0`, `MaxAgeBars=0`, `MaxTouches=0`, `UseSessionBuckets=true`, `TimeBucketMinutes=30`, `LookbackSessions=20`, `MinSamplesPerBucket=20`, `DetectionPercentile=98`, `WindowBars=10`, `MedianMultiplier=2.0`, `MaxGapTicks=1`, `MinClusterTicks=2`, `OneClusterPerBlock=true`.
  - Razón de los cuatro primeros: si el filtro predictivo o el umbral de calidad descartan eventos, el CSV tendrá menos zonas que el kernel — que no implementa ninguno de los dos — y el gate lo reportará como `MISSING_IN_NT8`. Sería un FAIL de configuración, no de paridad.
- **Historia cargada:** ≥ 35 sesiones completas en el chart, siguiendo el precedente de `aVolCellPOI2` (≈ 7 semanas). El warm-up de 20 muestras se consume en ~3 sesiones en los buckets activos; el resto es para que los buckets flojos también enciendan y para tener suficientes pares comparables.
- **Rango:** fuera del holdout. Declararlo **antes** de exportar.

### 4.2 Captura pareada de diagnóstico

`nt8/TickBarDiag.cs` a `120 Tick` sobre el mismo NQ, 20 barras de warm-up y 150 registradas, con el runbook de `docs/campaigns/TICKBAR-001_captura_nt8.md`. Son minutos y es lo que hace interpretable al oráculo.

### 4.3 Advertencia de overwrite

El `.cs` exporta en `write_mode=overwrite`. El 2026-07-25 eso produjo **dos archivos idénticos, uno mal rotulado, y un `BAR_BUILDER_MISMATCH` falso**. Renombrar o mover el CSV inmediatamente después de cada corrida, antes de tocar el chart.

### 4.4 Lo que hay que declarar fuera del archivo

La línea de meta registra 26 campos y **ninguno identifica el objeto medido**. Falta `bar_spec`, plantilla de Trading Hours, rango y TZ. Un CSV de este indicador no puede autoidentificarse como «120 ticks». Hay que anotar acá, junto al `sha256` del archivo: `bar_spec`, plantilla de Trading Hours exacta, TZ del chart, mes de contrato, primera y última sesión, y la revisión del `.cs`.

## 5. Riesgos precargados

1. **Calendario de sesiones.** El único oráculo real del proyecto (`aVolCellPOI2`, 2026-07-26) falló por esto: Python contó 28 sesiones y NT8 25 sobre el mismo tramo por el feriado del 3 de julio; con `min_sessions=15` uno detectaba desde la sesión 16 y el otro desde la 22; resultado `MATCHED 2 · MISSING_IN_NT8 29`. Las 2 zonas comunes coincidían: no era desacuerdo sobre qué es una anomalía, sino sobre cuándo hay suficiente historia. aVolClusterPOI tiene la misma dependencia (`LookbackSessions`, `CommitSession`, buckets relativos a sesión), así que el modo de falla está precargado.
2. **`TICKBAR-001`, abierta.** Ver §3.
3. **Identidad del archivo.** Ver §4.4.

## 6. Qué NO valida este oráculo

- No valida el constructor de barras de tick ni la atribución del footprint.
- No valida `FIRST_TOUCH`, `ZONE_INVALIDATED`, ni ningún outcome.
- No mide si las zonas anticipan nada. La paridad es reproducibilidad entre dos implementaciones, no evidencia de borde.
- No autoriza operar las zonas ni levanta el estado de detector congelado.

## 7. Decisiones que requiere Nico

1. **Referencia de calendario:** `edgelab/sessions.py` (CME ETH) o el `SessionIterator` de NT8. Decidir antes de correr el gate, o el FAIL de julio se repite idéntico.
2. **Identidad de la corrida:** mes de contrato, rango de fechas, plantilla de Trading Hours, TZ.
3. **Alcance del gate:** correr sólo la paridad de creación (lo que el kernel puede hoy) o ampliar el kernel primero. La recomendación es la primera: es lo que el embudo necesita y no toca el detector congelado.
4. Si se agrega `bar_spec` al meta del `.cs` — eso **sí** toca el detector congelado y necesita autorización aparte.
