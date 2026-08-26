# BT2A — Puerta 2 y Puerta L2

**Fecha de corte:** 2026-08-26  
**Estado:** `HARDENING_IMPLEMENTED_NOT_RUN_LOCAL_EVIDENCE_PENDING`  
**Rama:** `work/bt2a-gate2-l2-hardening-20260826`  
**Base Gate 1:** `work/bt2a-gate1-all5-20260826@3e639e150bcd7b4691da3d1ba8049a33f586c217`

## Propósito

Este directorio ordena el resultado de Gate 1, la auditoría de los procesos nocturnos, los contratos de Puerta 2/Puerta L2 y su implementación fail-closed. No se abrieron outcomes nuevos durante el hardening.

## Orden de lectura

1. [`01_GATE1_AND_ANTIGRAVITY_AUDIT.md`](01_GATE1_AND_ANTIGRAVITY_AUDIT.md)
2. [`02_GATE2_FIRST_PASSAGE_CONTRACT.md`](02_GATE2_FIRST_PASSAGE_CONTRACT.md)
3. [`03_GATE_L2_CONTEXT_CONTRACT.md`](03_GATE_L2_CONTEXT_CONTRACT.md)
4. [`04_WEB_RESEARCH.md`](04_WEB_RESEARCH.md)
5. [`05_EXECUTION_PLAN.md`](05_EXECUTION_PLAN.md)
6. [`06_HARDENING_IMPLEMENTATION.md`](06_HARDENING_IMPLEMENTATION.md)
7. [`CLAUDE_CODE_LOCAL_AUDIT.md`](CLAUDE_CODE_LOCAL_AUDIT.md)
8. [`STATUS.json`](STATUS.json)

Specs:

- [`specs/bt2a_gate2_first_passage_v1.json`](../../../specs/bt2a_gate2_first_passage_v1.json)
- [`specs/bt2a_gate_l2_context_v2.json`](../../../specs/bt2a_gate_l2_context_v2.json)

## Dictamen corto

| Objeto | Estado | Uso permitido hoy |
|---|---|---|
| Gate 1 all5 | completo, post-outcome | evidencia de excursión; no P&L |
| Event Store canónico | builder implementado; 234 checkpoints pendientes | preflight y reconstrucción, no P2 aún |
| P2-A | kernel + runner implementados, no corridos | revisión/freeze |
| P2-B | motor + runner implementados, no corridos; costos GC sin confirmar | revisión de ejecución/costos |
| Puerta L2 | join, validador e interacción implementados; evidencia local pendiente | validación target-free, no outcomes |
| Sweep 99 configs | 190 parciales locales, procedencia por adjudicar | no reanudar todavía |

## Claims prohibidos

- llamar a `+4,84 ticks` ventaja neta;
- inferir `TP_FIRST` de MFE/MAE;
- reutilizar comisión/tick value de 6E como si fueran GC;
- llamar canónico al Event Store nocturno sin reconciliación;
- declarar extracción L2 formal sin manifiesto, hashes y worktree limpio;
- reanudar parciales producidos por un commit distinto;
- seleccionar barrera, configuración o contexto mirando outcomes;
- declarar edge, confirmación o promoción.
