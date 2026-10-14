# AVolClusterPOI NQ — infraestructura Gate 1B / roadmap Gate 3 (draft fail-closed)

**Fecha:** 2026-08-30
**Base lógica:** `research/avolcluster-nq-gate1-infra-v1-20260828`
**HEAD reportado por Claude:** `7bbb33828c9e0efb02af850463b4957943934d43`
**Estado:** `DRAFT_DECISIONS_REQUIRED_FAIL_CLOSED`
**Ejecución autorizada:** no.

## 1. Alcance y reconciliación de nombres

El informe de Gate 1A llama **Gate 1B** al siguiente bloque de lifecycle/first touch. El roadmap del diseño conjunto llama **Gate 3** al diseño/freeze de lifecycle y episode collapse, y Gate 4 a su ejecución. Este paquete cubre sólo el diseño y la infraestructura de contratos/preflight. No implementa Gate 4 ni abre outcomes.

Gate 1A ya está materializado y es la única entrada aceptada:

- 5.876 zonas `OFF_PRICE`;
- 234 checkpoints de contract-session;
- 233 contract-sessions con zonas;
- SHA-256 físico del archivo de manifest publicado en el repo `5e4e515d744b7dbe51116b8e071766f3765f63e999ffbf0197a1f71fa2da61c3` (el informe histórico registra `df802941...` para el artefacto runtime anterior a su publicación);
- payload `f87061427d884dac3290c52144bdcf0ab079d4a4b4674237c279072eae51cacc`;
- identidad lógica `7c254009dc4ccd58f4187360a861f76a692945b94c7091766cce6cf3e46f3a77`;
- Parquet físico `4dad91f6a572bfb5edc714dfb13daa4a0bbee6b96301a4d734466a9da7a06674`.

Los cuatro blobs normativos informados para la rama objetivo se recalcularon localmente y coinciden exactamente. El HEAD no pudo verificarse por Git porque el conector requiere re-aprobación administrativa; por eso la entrega es un draft rebaseable, no un supuesto push sobre la rama viva.

## 2. Qué sí implementa

1. Dos specs separadas y no autorizadas:
   - `specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json`;
   - `specs/avolcluster_nq_episode_collapse_v1.draft.json`.
2. Primitivas puras de contrato:
   - validación de specs y evidencia de decisiones;
   - clasificación de **una observación suministrada por el caller**, sólo después de freeze;
   - validación de filas lifecycle ya construidas;
   - collapse target-free de filas de creación, sólo después de freeze y sin I/O.
3. Preflight de metadatos que verifica blobs, manifest de Gate 1A, hashes, firewalls y decisiones faltantes.
4. Tests sintéticos de causalidad, determinismo, holdout y ausencia de runner.

No hay loader de ticks, `read_parquet`, scanner de trayectoria, builder de first touch, MFE/MAE, first passage, P&L ni runner de Kaggle.

## 3. Decisiones ya cerradas por las autoridades vigentes

- instrumento NQ, tick size 0,25;
- configuración `tick_120_W5_M20_C4_P950`;
- población de zonas `OFF_PRICE` del Event Store Gate 1A;
- barra creadora inelegible;
- disponibilidad causal desde `availability_ts_utc_ns`;
- `geometric_side` no es dirección;
- una sola ancla primaria por episodio: `FIRST_ELIGIBLE_EVENT_WINS`;
- segundos toques y reingresos son secundarios;
- episode collapse debe preceder outcomes;
- unidad estadística de cluster: sesión CME;
- holdout desde `20260701` permanece cerrado.

## 4. Decisiones deliberadamente no inventadas

### Lifecycle/first touch — 27

- `clock.observation_source`
- `clock.observation_clock_unit`
- `clock.age_origin`
- `touch.price_field`
- `touch.interval_boundary_policy`
- `touch.contact_definition`
- `touch.penetration_definition`
- `touch.intrabar_ordering_policy`
- `touch.same_timestamp_tie_policy`
- `touch.source_row_identity_field`
- `touch.missing_ticks_policy`
- `expiration.max_age_value`
- `expiration.max_age_unit`
- `expiration.expiration_boundary_policy`
- `expiration.session_carry_policy`
- `invalidation.rule`
- `invalidation.penetration_ticks`
- `precedence.touch_vs_invalidation`
- `precedence.expiration_vs_touch`
- `reentries.reentry_definition`
- `reentries.second_touch_definition`
- `reentries.primary_inclusion_policy`
- `censoring.end_of_sample_policy`
- `censoring.roll_boundary_policy`
- `raw_data.source_registry_path`
- `raw_data.source_registry_sha256`
- `raw_data.kaggle_dataset_slug`

### Episode collapse — 20

- `spatial.link_rule`
- `spatial.minimum_overlap_ticks`
- `spatial.minimum_overlap_fraction_of_smaller_zone`
- `spatial.maximum_adjacency_gap_ticks`
- `temporal.anchor_field`
- `temporal.window_value`
- `temporal.window_unit`
- `temporal.interval_boundary_policy`
- `grouping.partition_keys`
- `grouping.transitivity_policy`
- `grouping.algorithm`
- `grouping.cross_session_policy`
- `grouping.cross_contract_policy`
- `anchor.eligibility_definition`
- `anchor.tie_break_policy`
- `anchor.anchor_replacement_policy`
- `lifecycle_relation.collapse_timing`
- `lifecycle_relation.shared_touch_policy`
- `multiconfig.policy`
- `null_controls.episode_collapse_policy`

El valor histórico `sep_minutes=120` de `first_touch_decongestion.py` no se importó: pertenece a otra campaña y no es autoridad para NQ Gate 1B. Tampoco se trasladaron defaults de lifecycle de otros indicadores.

## 5. Resultado esperado del preflight ahora

```text
status                       = NOT_READY_DECISIONS_REQUIRED
lifecycle_missing_decisions  = 27
episode_missing_decisions    = 20
ready_for_freeze_review      = false
ready_for_execution          = false
RAW_TICK_DECODED             = false
FIRST_TOUCH_ACCESSED         = false
FUTURE_PRICE_PATH_ACCESSED   = false
MFE_MAE_ACCESSED             = false
FIRST_PASSAGE_ACCESSED       = false
PNL_ACCESSED                 = false
HOLDOUT_TOUCHED              = false
```

Un `NOT_READY` es el resultado correcto: el código vuelve mecánico el faltante real sin elegir thresholds ni semántica por conveniencia.

## 6. Secuencia segura siguiente

1. Nico/auditor resuelve por escrito las 47 decisiones o reduce explícitamente el alcance antes de outcomes.
2. Se asienta evidencia por decisión (`decision_id`, autoridad, timestamp).
3. Preflight debe pasar `PASS_READY_FOR_FREEZE_REVIEW` todavía sin capacidad de ejecución.
4. Auditoría de semántica y freeze de ambas specs.
5. Sólo en otro paquete/commit: builder de first-touch con fuente raw hash-bound y Kaggle-only.
6. Autorización de ejecución separada; la autorización de freeze nunca equivale a run.

## 7. Criterios de refutación

El paquete falla si una fila de barra creadora entra como touch, si el collapse cambia al permutar inputs, si cruza sesión/contrato sin regla, si usa first touch para agrupar antes de autorizar futuro, si los hashes de Gate 1A derivan o si aparece cualquier superficie de P&L/outcomes/holdout.

## Aporte al referente

La etapa siguiente de AVol deja de ser un pedido ambiguo: quedan contratos ejecutables sólo sobre fixtures sintéticos, 47 decisiones visibles y un preflight que se niega a abrir first touch hasta que la semántica, la procedencia y la autorización estén realmente cerradas.
