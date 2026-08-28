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

- P2-A: implementado, no ejecutado.
- P2-B: implementado, no ejecutado.
- El spec P2-A queda congelado por este cambio sólo después de revisión humana del diff.
- La ejecución exige el token literal `AUTHORIZE_BT2A_P2A_POST_OUTCOME_DIAGNOSTIC`.
- P2-A es diagnóstico post-outcome; no puede declarar edge ni promoción.
- La familia primaria son 16 celdas B×H_ticks con Holm; las 12 celdas de reloj son descriptivas secundarias.
- La regla `P2_DIAGNOSTIC_MECHANISM_SUPPORTED` está codificada y congelada en el spec.

Runner: `tools/run_bt2a_gate2_p2a.py`.

Candidato V1-R1: el fail-closed adversarial rechaza checkpoints malformados, mutaciones del contrato, valores no finitos y `NOT_READY` con código de éxito. Validación Python 3.12 exacta: 45 tests aprobados; outcomes no abiertos.

## Línea C / Gate L2

La adquisición L1/L2 sigue target-free. La entrega auditada tiene integridad de bytes, pero no está lista para contexto:

- reloj sin resolver;
- procedencia parcialmente dirty;
- contrato y captura común con eventos no acreditados;
- menos de 40 sesiones efectivas por grupo.

No ejecutar HMM final, join de outcomes ni CTX-3 hasta pasar los gates de `docs/research/bt2a_gate2_l2_20260826/03_GATE_L2_CONTEXT_CONTRACT.md`.

## Firewall

- Holdout `20260701–20261231` sellado.
- No abrir P2-A sin spec congelado, Event Store exacto y autorización literal.
- No abrir P2-B sin autorización separada y costos GC confirmados.
- No usar `aVolClusterPOI` como oracle.
- No elegir una celda por el máximo observado.

## Estado compacto

```text
GATE1_ALL5                    = COMPLETE_POST_OUTCOME_REPLICATION
CANONICAL_EVENT_STORE_234    = PASS
P2A_SPEC                      = FROZEN_POST_OUTCOME_DIAGNOSTIC
P2A                           = IMPLEMENTED_NOT_RUN
P2B                           = IMPLEMENTED_NOT_RUN
GATE_L2_SAMPLE_POWER          = NOT_READY
NEW_P2_OR_L2_OUTCOMES_OPENED  = false
EDGE_DECLARED                 = false
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
