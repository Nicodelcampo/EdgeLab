# EXPANSION_ZONAS — MEDIDO / NO MEDIDO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cada resultado).
Campañas: `config/autopilot/grillas/campanas/EXPZ-NQ.json`, `EXPZ-CFD.json`; bitácoras en `embudo/<cid>/MEDIDO.md`. Spec: `SPEC.md`.

## MEDIDO
| fecha | qué | datos | resultado |
|---|---|---|---|
| 2026-10-24 | DESC (código anterior al arreglo de falsos negativos) | NQ 2025-08-05 → 2026-03-31 | **DESCARTADO sin mirar**: los módulos de medición cambiaron después (GUIA_GRILLA_MASIVA); también la réplica PISTAS lanzada sobre él |
| 2026-10-25 | EXPZ-NQ DESC (código vigente) | NQ 2025-08-05 → 2026-03-31, 233.280 celdas por canal (9.960 evaluables) | 0 nominadas por FDR q 0,10; 40 pistas sin nominación |
| 2026-10-25 | EXPZ-NQ PISTAS (ATJ-25): top-20 congeladas, réplica en una ventana no usada | NQ 2026-04-01 → 2026-09-25 | **SIN_CANDIDATAS**: un paso de LORD++ del lote (t=1, nivel 0,0109) con p de Simes 0,59; 0 de 20 confirmadas |
| 2026-10-25 | EXPZ-CFD DESC (código vigente) + PISTAS top-20 | señal USATECH, operación NQ; DESC 2025-08-05 → 2026-03-31, réplica 2026-04-01 → 2026-09-30 | **SIN_CANDIDATAS**: 0 nominadas por FDR; pistas: LORD++ t=2 nivel 0,0036, p de Simes 0,82, 0 de 20 confirmadas. Una pista chica tenía p de B=500 (no podía resolver el umbral): corregido en el embudo; con p de Simes 0,82 no cambia el resultado |

## NO MEDIDO
- EXPZ en el oro (XAU → GC): no se corre; ninguna de las dos campañas sobrevivió.
- Alcance de la muerte de EXPZ-NQ: la familia EXPANSION_ZONAS con señal en NQ, sus 233.280 celdas y las ejecuciones declaradas; EXPZ-CFD murió con su propio DESC y réplica.
