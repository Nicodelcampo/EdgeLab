# CURRENT — empezar acá

**Fecha:** 2026-08-28

> Estado operativo posterior al hardening Gate 2/L2 y a la reproducción canónica de Gate 1.

**Rama viva propuesta:** `work/bt2a-gate2-p2a-freeze-20260826`
**Base de hardening:** `761f50ba93158cc78c846b8774b7ac21a31b3b57`
**Gate 1 canónica:** `3e639e150bcd7b4691da3d1ba8049a33f586c217`
**Referente:** `docs/NORTH_STAR.md`

## Línea primaria

BigTrap2Absorption Gate 1 all5 está cerrada como réplica post-outcome:

- 234 sesiones CME;
- K_ABS=16.940 y K_BT2=5.262;
- K_ABS−N_RAND=+4,84 ticks, IC95% [+3,36; +6,32];
- K_ABS−shuffle=+1,74 ticks, IC95% [+0,17; +3,31];
- K_ABS−K_BT2=+0,10 ticks, IC95% [−3,93; +4,16];
- `confirmatory_eligible=false`, `promotion_eligible=false`, `EDGE_DECLARED=false`.

`d_hat` es asimetría de recorrido, no P&L. Gate 1 no se reabre para elegir SL/TP.

## Event Store canónico

La población fue reproducida bajo Python 3.12.14 y el lock exacto:

```text
sessions = 234
K_ABS    = 16940
K_BT2    = 5262
events   = 22202
```

La procedencia y hashes vinculantes viven en `specs/bt2a_gate2_first_passage_v1.json`.

## Puerta 2

- P2-A: ejecutado y soportado como diagnóstico post-selección (`results/bt2a-p2a-v1-r1-20260827`, payload `296f8352a46751c3a9a26a32ec29661ddcecba7ac57874a967dc591a92766e28`, clasificación `P2_DIAGNOSTIC_MECHANISM_SUPPORTED`).
- P2-B: implementado, no ejecutado.
- Diagnóstico de Heterogeneidad Horaria GC V1: congelado preautorización (`specs/bt2a_p2a_gc_clock_heterogeneity_v1.json`, rama `research/bt2a-p2a-clock-heterogeneity-v1-20260827`).
- Incidente epistemológico asentado: 4 sesiones prematuras en cuarentena; ejecución autorizada cerrada.
- P2-A no declara edge ni habilita promoción.

Runner P2-A: `tools/run_bt2a_gate2_p2a.py`.
Runner Clock: `tools/run_bt2a_p2a_gc_clock_heterogeneity.py`.

## Línea C / Gate L2

La adquisición L1/L2 sigue target-free. La entrega auditada tiene integridad de bytes, pero no está lista para contexto:

- reloj sin resolver;
- procedencia parcialmente dirty;
- contrato y captura común con eventos no acreditados;
- menos de 40 sesiones efectivas por grupo.

No ejecutar HMM final, join de outcomes ni CTX-3 hasta pasar los gates de `docs/research/bt2a_gate2_l2_20260826/03_GATE_L2_CONTEXT_CONTRACT.md`.

## Firewall

- Holdout `20260701–20261231` sellado.
- P2-A outcomes ya abiertos (`P2A_OUTCOMES_ALREADY_OPENED=true`).
- No abrir P2-B sin autorización separada y costos GC confirmados.
- No usar `aVolClusterPOI` como oracle.
- No elegir horario por máximo observado (`winner_selection_allowed=false`).

## Estado compacto

```text
GATE1_ALL5                    = COMPLETE_POST_OUTCOME_REPLICATION
CANONICAL_EVENT_STORE_234    = PASS
P2A                           = COMPLETE_POST_OUTCOME_DIAGNOSTIC
P2A_CLOCK_HETEROGENEITY       = FROZEN_PREAUTHORIZATION
P2B                           = IMPLEMENTED_NOT_RUN
GATE_L2_SAMPLE_POWER                    = NOT_READY
NEW_OUTCOMES_OPENED_BY_CLOCK_PREPARATION = false
EDGE_DECLARED                           = false
```

## Primer chequeo

```powershell
git rev-parse HEAD
git branch --show-current
git status --short --untracked-files=all
python -m pytest tests/test_current_md.py tests/research/test_bt2a_gate2_first_passage.py tests/research/test_bt2a_gate2_boundaries.py tests/research/test_bt2a_event_store_identity.py tests/research/test_bt2a_statistical_safety.py
```

## Índices canónicos

- `AUDITOR_START_HERE.md`
- `docs/NORTH_STAR.md`
- `docs/research/bt2a_gate2_l2_20260826/STATUS.json`
- `docs/research/bt2a_gate2_l2_20260826/07_FINAL_HARDENING_AUDIT.md`
- `specs/bt2a_gate2_first_passage_v1.json`
- `PENDIENTE.md`

## Aporte al referente

Gate 1 queda cerrada y reproducida; P2-A queda definido ex ante como diagnóstico de first-passage, con identidad, multiplicidad, semillas y regla de decisión explícitas. La apertura de outcomes continúa bloqueada hasta autorización literal.
