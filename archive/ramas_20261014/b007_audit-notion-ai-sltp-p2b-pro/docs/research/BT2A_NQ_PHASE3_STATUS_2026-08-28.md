# BT2A NQ — estado de Fase 3

**Fecha:** 2026-08-28  
**Rama:** `research/bt2a-nq-target-free-selection-v1-20260828`  
**Anchor de implementación auditado:** `d194b50fca0559525ba592b371d6aa1eb173409b`  
**Estado:** `PHASE3_FAIL_CLOSED_PREFLIGHT_IMPLEMENTED_NOT_RUN`

## Corrección de trazabilidad

Esta rama no está meramente creada ni vacía. En el anchor auditado ya contiene:

- `tools/preflight_bt2a_nq_gate1.py`;
- `tests/research/test_bt2a_nq_gate1_preflight.py`;
- `specs/bt2a_nq_gate1_v1.draft.json`;
- `.github/workflows/bt2a-nq-target-free-contract.yml`.

El commit de implementación es:

```text
d194b50fca0559525ba592b371d6aa1eb173409b
research(bt2a): add fail-closed NQ Gate 1 preflight
```

## Estado operativo

```text
PHASE3_DEVELOPMENT_STARTED    = true
GATE1_PREFLIGHT_IMPLEMENTED   = true
SPEC_STATUS                   = DRAFT
BT2A_NQ_SWEEP_AUTHORIZED      = false
BT2A_NQ_GATE1_AUTHORIZED      = false
SCIENTIFIC_RUN_AUTHORIZED     = false
HOLDOUT_AUTHORIZED            = false
OUTCOMES_OPENED               = false
EDGE_DECLARED                 = false
```

La implementación del preflight no sustituye freeze, token de campaña ni autorización científica.

## Aporte al referente

Fase 3 BT2A NQ ya tiene preflight fail-closed y contrato en desarrollo; la corrida, los outcomes y el holdout continúan cerrados.
