# CURRENT — empezar acá

**Fecha:** 2026-08-28

> Estado operativo posterior al hardening Gate 2/L2, a la reproducción canónica de Gate 1 BT2A y a la preparación target-free de AVolClusterPOI NQ.

**Línea BT2A:** `work/bt2a-gate2-p2a-freeze-20260826`
**Infraestructura AVol activa:** `research/avolcluster-nq-gate1-infra-v1-20260828`
**Base AVol target-free:** `3961b67d80cd62aa6adab101e79739db3bc0005b`
**Referente:** `docs/NORTH_STAR.md`

## Línea primaria BT2A

BigTrap2Absorption Gate 1 all5 está cerrada como réplica post-outcome:

- 234 sesiones CME;
- K_ABS=16.940 y K_BT2=5.262;
- K_ABS−N_RAND=+4,84 ticks, IC95% [+3,36; +6,32];
- K_ABS−shuffle=+1,74 ticks, IC95% [+0,17; +3,31];
- K_ABS−K_BT2=+0,10 ticks, IC95% [−3,93; +4,16];
- `confirmatory_eligible=false`, `promotion_eligible=false`, `EDGE_DECLARED=false`.

`d_hat` es asimetría de recorrido, no P&L. Gate 1 no se reabre para elegir SL/TP.

## Puerta 2 BT2A

- P2-A: ejecutado y soportado como diagnóstico post-selección (`results/bt2a-p2a-v1-r1-20260827`, payload `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`, clasificación `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`).
- P2-B: implementado, no ejecutado.
- Diagnóstico de Heterogeneidad Horaria GC V1: congelado preautorización (`specs/bt2a_p2a_gc_clock_heterogeneity_v1.json`).
- P2-A no declara edge ni habilita promoción.

## AVolClusterPOI NQ-120t

La selección target-free quedó completa para `tick_120_W5_M20_C4_P950`:

```text
sessions              = 234
OFF_PRICE zones       = 5876
AT_PRICE excluded     = 3728
sessions with zones   = 233
coverage               = 99.6%
mean width             = 14.8 ticks
width p95              = 26 ticks
fitness target-free    = 0.9987
```

La rama activa agrega, sin ejecutar datos reales:

- contrato lógico genérico de Event Store;
- Event Store AVol limitado a `ZONE_CREATED` y `OFF_PRICE`;
- inputs y sesiones hash-bound;
- builder NQ-120t reanudable con checkpoints por contract-session;
- snapshot hash-bound de `SessionProfile` a través de la cadena de contratos;
- lectura PyArrow limitada a ventanas CME registradas, con frontera del holdout en `2026-06-30T22:00:00Z`;
- build, finalize y validate separados por tokens de runtime;
- finalización condicionada a 234 checkpoints, 5.876 eventos y equivalencia Parquet ↔ checkpoints.

La spec se encuentra congelada bajo autorización formal (`status = FROZEN_ZONE_CREATION_EVENT_STORE`, `projected_frozen_payload_sha256 = 1f2ef16548ab6a9d413a7871351800a9868e9ede9725f46c9e2f482588abe59c`). No se autorizó la ejecución real del build ni se emitieron tokens de build/finalize/validate. No se construyó el Event Store real, no se abrió lifecycle/first touch y no se evaluaron outcomes.

## Diseño conjunto AVol + BT2A NQ + L2

Quedó registrado un diseño futuro completo, todavía no ejecutable, para:

- creación y geometría AVol;
- lifecycle, first touch, supervivencia y riesgos competitivos;
- expansión no direccional y recorrido direccional;
- confluencia temporal y espacial con BT2A NQ;
- acuerdo/desacuerdo de `K_ABS` y `K_BT2`;
- interacción incremental versus AVol solo, BT2A solo y controles;
- nulls N_RAND, Mirror, Time-Shuffle, geometry-match y placebo leads;
- configuración primaria más robustez de un factor;
- familia BT2A completa de 16 celdas para NQ;
- cuatro fases NQ primarias y ocho ventanas descriptivas;
- contexto L2 causal `as-of backward` como estratificador;
- gates jerárquicos para evitar 84.480 comparaciones cartesianas;
- inferencia agrupada por sesión CME y control de multiplicidad.

Autoridades:

- `docs/research/AVOLCLUSTER_BT2A_NQ_JOINT_MEASUREMENT_DESIGN_V1_2026-08-28.md`;
- `specs/avolcluster_bt2a_nq_joint_measurement_v1.draft.json`.

Estado: `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`. No autoriza lifecycle, outcomes,
BT2A NQ, join L2, first passage, P&L ni acceso al holdout.

## Línea C / Gate L2

La adquisición L1/L2 sigue target-free. No ejecutar HMM final, join de outcomes ni CTX-3 hasta pasar los gates de `docs/research/bt2a_gate2_l2_20260826/03_GATE_L2_CONTEXT_CONTRACT.md`.

## Firewall

- Holdout `20260701–20261231` sellado.
- P2-A outcomes ya abiertos (`P2A_OUTCOMES_ALREADY_OPENED=true`).
- No abrir P2-B sin autorización separada y costos GC confirmados.
- AVol NQ: `FUTURE_PRICE_PATH_ACCESSED=false`, `FIRST_TOUCH_ACCESSED=false`, `PNL_ACCESSED=false`, `HOLDOUT_TOUCHED=false`.
- No usar `aVolClusterPOI` como oracle ni interpretar `geometric_side` como pronóstico.
- El diseño conjunto registrado no concede ninguna capacidad runtime.

## Estado compacto

```text
GATE1_ALL5                              = COMPLETE_POST_OUTCOME_REPLICATION
CANONICAL_EVENT_STORE_234              = PASS
P2A                                     = COMPLETE_POST_OUTCOME_DIAGNOSTIC
P2A_CLOCK_HETEROGENEITY                 = FROZEN_PREAUTHORIZATION
P2B                                     = IMPLEMENTED_NOT_RUN
GATE_L2_SAMPLE_POWER                    = NOT_READY
AVOL_NQ_TARGET_FREE_SELECTION           = COMPLETE
AVOL_NQ_ZONE_STORE                      = FROZEN_ZONE_CREATION_EVENT_STORE
AVOL_NQ_ZONE_STORE_REAL_BUILD           = NOT_RUN
AVOL_NQ_FIRST_TOUCH                     = NOT_IMPLEMENTED
AVOL_NQ_GATE1_OUTCOMES_OPENED           = false
AVOL_BT2A_NQ_JOINT_DESIGN               = DRAFT_DESIGN_ONLY_PREAUTHORIZATION
AVOL_BT2A_NQ_JOINT_EXECUTION            = NOT_AUTHORIZED
NEW_OUTCOMES_OPENED_BY_AVOL_PREPARATION = false
EDGE_DECLARED                           = false
```

## Primer chequeo AVol

```powershell
git rev-parse HEAD
git branch --show-current
git status --short --untracked-files=all
python -m pytest -q tests/research/test_event_store_contract.py tests/research/test_avolcluster_nq_zone_store.py tests/research/test_avolcluster_nq_zone_builder.py tests/research/test_avolcluster_bt2a_nq_joint_measurement_spec.py
python tools/validate_avolcluster_nq_zone_store.py --preflight-only --expected-commit <REVIEWED_HEAD_SHA>
python tools/build_avolcluster_nq_zone_store.py --preflight-only --expected-commit <REVIEWED_HEAD_SHA>
```

## Índices canónicos

- `AUDITOR_START_HERE.md`
- `docs/NORTH_STAR.md`
- `docs/research/AVOLCLUSTER_NQ_GATE1_INFRA_PROTOCOL_V1_DRAFT_2026-08-28.md`
- `docs/research/AVOLCLUSTER_BT2A_NQ_JOINT_MEASUREMENT_DESIGN_V1_2026-08-28.md`
- `specs/avolcluster_nq_zone_event_store_v1.json`
- `specs/avolcluster_bt2a_nq_joint_measurement_v1.draft.json`
- `specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json`
- `specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json`
- `PENDIENTE.md`

## Aporte al referente

La configuración NQ-120t conserva su ruta de creación fail-closed y ahora suma un diseño integral de medición conjunta con BT2A, clock y L2, registrado sin abrir lifecycle, outcomes ni holdout.
