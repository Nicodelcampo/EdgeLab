# AVolClusterPOI NQ-120t — protocolo de infraestructura Gate 1 (draft)

**Fecha:** 2026-08-28  
**Rama:** `research/avolcluster-nq-gate1-infra-v1-20260828`  
**Base target-free:** `3961b67d80cd62aa6adab101e79739db3bc0005b`  
**Estado:** `DRAFT_PREAUTHORIZATION_FAIL_CLOSED`

## 1. Objetivo

Convertir la selección target-free `tick_120_W5_M20_C4_P950` en un Event Store canónico de **creación** de zonas `OFF_PRICE`, sin abrir first touch, recorridos futuros, MFE/MAE, first passage, P&L ni holdout.

Este bloque prepara infraestructura; no prueba edge ni vuelve óptimo a 120 ticks en forma aislada.

## 2. Población y configuración vinculantes

```text
instrument                 = NQ
tick_size                  = 0.25
bar_type                   = tick_120
window_bars                = 5
nominal_ticks_per_block    = 600
median_multiplier          = 2.0
max_gap_ticks              = 1
min_cluster_ticks          = 4
detection_percentile       = 95.0
min_samples_per_bucket     = 10
lookback_sessions          = 20
one_cluster_per_block      = true
bucket clamp               = 45
contract_sessions          = 234
holdout starts             = 20260701
```

Resultado target-free a reproducir, no a reinterpretar:

```text
OFF_PRICE                  = 5876
AT_PRICE excluded          = 3728
sessions with OFF_PRICE    = 233
coverage                   = 99.6%
mean width                 = 14.8 ticks
width p95                  = 26 ticks
fitness                    = 0.9987
```

## 3. Fuentes congelables

- kernel `edgelab/bridge/indicators/avolclusterpoi.py`, versión 0.5;
- resultado `docs/research/avolcluster_nq_microticks_result.json`;
- registry de 234 contract-sessions;
- registry de cinco Parquet con SHA-256, bytes y filas;
- spec `specs/avolcluster_nq_zone_event_store_v1.json`.

Ninguna ruta de input se descubre durante la corrida. Los hashes y tamaños se verifican antes de decodificar cada contrato.

## 4. Semántica del builder

1. Expande el registry en orden contractual y cronológico.
2. Rehidrata sólo un prefijo contiguo de checkpoints válidos.
3. Mantiene un `SessionProfile` global a través de toda la cadena de contratos.
4. Lee cada Parquet con predicate pushdown entre el inicio CME de la primera sesión registrada y el inicio de la sesión calendario posterior a la última.
5. Para `20260630`, la exclusión superior es `2026-06-30T22:00:00Z`, comienzo de la sesión holdout `20260701`.
6. Construye barras de 120 ticks con reset por sesión.
7. Procesa bloques disjuntos de cinco barras con la misma semántica del sweep.
8. Emite sólo `ZONE_CREATED` para zonas `OFF_PRICE`.
9. Escribe un checkpoint JSON atómico por contract-session con snapshot hash-bound del perfil.
10. No decodifica filas posteriores al rango registrado.

## 5. Identidad e integridad

Cada fila tiene `event_id` determinista e `identity_sha256`. La identidad lógica se calcula sobre columnas declaradas y no depende del encoding físico de Parquet.

Cada checkpoint queda vinculado a:

- payload científico proyectado de la spec;
- SHA-256 del Parquet fuente;
- commit exacto;
- contrato, sesión y ordinal;
- eventos canónicos;
- estado posterior del `SessionProfile`.

Resume rechaza gaps, mutaciones, cambio de commit, cambio de source hash o drift de spec.

## 6. Separación de capacidades y autorizaciones

La spec congela capacidades estables; las decisiones de ejecución son tokens de runtime y no requieren mutar el payload científico después del freeze.

```text
freeze    = APPROVE_FREEZE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1
build     = AUTHORIZE_BUILD_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1
finalize  = AUTHORIZE_FINALIZE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1
validate  = AUTHORIZE_VALIDATE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1
```

`--run-all` produce **solamente checkpoints**. Nunca llama a finalización. `--finalize` exige el token independiente y 234 checkpoints válidos. La validación final también exige su token separado.

Mientras la spec sea draft, build/finalize/validate abortan antes de leer datos reales.

## 7. Gates de finalización

- exactamente 234 checkpoints;
- prefijo completo y continuo;
- exactamente 5.876 zonas `OFF_PRICE`;
- exactamente 233 contract-sessions con eventos;
- esquema y dominio válidos;
- identidad lógica única;
- equivalencia 1:1 Parquet ↔ checkpoints;
- cero sesión `>=20260701`;
- cero columna de first touch u outcome.

## 8. Estado epistemológico

```text
ZONE_STORE_REAL_BUILD      = NOT_RUN
FIRST_TOUCH_IMPLEMENTED    = false
FUTURE_PRICE_PATH_ACCESSED = false
MFE_MAE_ACCESSED           = false
FIRST_PASSAGE_ACCESSED     = false
PNL_ACCESSED               = false
HOLDOUT_TOUCHED            = false
EDGE_DECLARED              = false
PROMOTION_ELIGIBLE         = false
```

## 9. Próxima decisión válida

Tras CI verde y revisión de paridad/semántica, la siguiente decisión posible es **freeze del contrato de creación**. Eso no autoriza build. Build, finalize, validate y cualquier lifecycle/outcome son decisiones posteriores e independientes.

## 10. Diseño futuro conjunto registrado

El diseño completo para medir AVol, BT2A NQ, secuencias temporales, relaciones
espaciales, varias configuraciones, fases horarias, nulls, supervivencia y
moderación L2 quedó registrado en:

- `docs/research/AVOLCLUSTER_BT2A_NQ_JOINT_MEASUREMENT_DESIGN_V1_2026-08-28.md`;
- `specs/avolcluster_bt2a_nq_joint_measurement_v1.draft.json`.

Esos artefactos son `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`. No amplían la capacidad
del Event Store de creación ni autorizan first touch, BT2A NQ, L2, outcomes o P&L.

## Aporte al referente

La selección NQ-120t queda convertida en una especificación de creación reproducible y fail-closed; el roadmap conjunto está preservado sin abrir ningún outcome.
