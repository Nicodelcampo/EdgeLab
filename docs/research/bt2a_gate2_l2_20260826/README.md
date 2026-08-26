# BT2A — Puerta 2 y Puerta L2

**Fecha de corte:** 2026-08-26  
**Estado:** `AUDIT_COMPLETE_CONTRACTS_PROPOSED_IMPLEMENTATION_PENDING`  
**Rama:** `work/bt2a-gate2-l2-audit-20260826`  
**Base:** `work/bt2a-gate1-all5-20260826@3e639e150bcd7b4691da3d1ba8049a33f586c217`

## Propósito

Este directorio ordena el estado de Gate 1, la auditoría de los procesos nocturnos de
Antigravity, el contrato propuesto de Puerta 2 y el contrato propuesto de Puerta L2.
No se abrieron nuevos outcomes durante esta auditoría.

## Orden de lectura

1. [`01_GATE1_AND_ANTIGRAVITY_AUDIT.md`](01_GATE1_AND_ANTIGRAVITY_AUDIT.md)
2. [`02_GATE2_FIRST_PASSAGE_CONTRACT.md`](02_GATE2_FIRST_PASSAGE_CONTRACT.md)
3. [`03_GATE_L2_CONTEXT_CONTRACT.md`](03_GATE_L2_CONTEXT_CONTRACT.md)
4. [`04_WEB_RESEARCH.md`](04_WEB_RESEARCH.md)
5. [`05_EXECUTION_PLAN.md`](05_EXECUTION_PLAN.md)
6. [`CLAUDE_CODE_LOCAL_AUDIT.md`](CLAUDE_CODE_LOCAL_AUDIT.md)
7. [`STATUS.json`](STATUS.json)

Specs:

- [`specs/bt2a_gate2_first_passage_v1.json`](../../../specs/bt2a_gate2_first_passage_v1.json)
- [`specs/bt2a_gate_l2_context_v2.json`](../../../specs/bt2a_gate_l2_context_v2.json)

## Dictamen corto

| Objeto | Estado auditado | Uso permitido hoy |
|---|---|---|
| Gate 1 all5 | Completo, post-outcome | evidencia de asimetría de excursiones; no P&L |
| Extracción L2 nocturna | ejecución plausible; paquete probatorio no versionado | piloto local, no extracción formal cerrada |
| Event Store all5 nocturno | inventario bruto provisional | no usar como población canónica de Gate 1/Puerta 2 |
| Sweep 99 configs | código target-free; 190 parciales sólo locales | progreso diagnóstico; no reanudar desde otro commit sin adjudicar procedencia |
| Puerta 2 | contrato propuesto, runner pendiente | no correr aún |
| Puerta L2 | extractor/HMM implementado; join y N insuficientes | no abrir outcomes |

## Decisiones de arquitectura

1. Gate 1 mide `median(MFE)-median(MAE)` y no conserva el orden TP/SL.
2. Puerta 2 debe tener una capa first-passage y otra de ejecución con costos.
3. El G2 genérico sólo se usa después de que P2 produzca trades/P&L.
4. Gate L2 prueba una interacción contexto × efecto; no vuelve a probar la señal.
5. Los 99 parámetros del sweep no se cruzan con 16 barreras para elegir un ganador.
   El headline congelado es primary; el sweep queda como sensibilidad target-free.
6. Las 234 sesiones all5 ya tienen outcomes abiertos. La confirmación exige sesiones
   nuevas.

## Claims prohibidos

- llamar a `+4,84 ticks` ventaja neta;
- inferir `TP_FIRST` de MFE/MAE;
- llamar canónico al Event Store nocturno antes de reconciliarlo;
- declarar la extracción L2 formal sin manifiesto/modelo/reporte y hashes;
- decir que el sweep es 100 % reanudable si cambió el commit de los parciales;
- seleccionar barrera, configuración o contexto mirando los outcomes all5;
- declarar edge o promoción.
