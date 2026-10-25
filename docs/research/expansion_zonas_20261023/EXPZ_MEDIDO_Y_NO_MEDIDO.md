# EXPANSION_ZONAS — MEDIDO / NO MEDIDO

Estado: VIGENTE (registro vivo; se actualiza en el mismo commit que cada resultado).
Campañas: `config/autopilot/grillas/campanas/EXPZ-NQ.json`, `EXPZ-CFD.json`; bitácoras en `embudo/<cid>/MEDIDO.md`. Spec: `SPEC.md`.

## MEDIDO
| fecha | qué | datos | resultado |
|---|---|---|---|
| 2026-10-24 | DESC (código anterior al arreglo de falsos negativos) | NQ 2025-08-05 → 2026-03-31 | **DESCARTADO sin mirar**: los módulos de medición cambiaron después (GUIA_GRILLA_MASIVA); también la réplica PISTAS lanzada sobre él |
| 2026-10-25 | EXPZ-NQ DESC (código vigente) | NQ 2025-08-05 → 2026-03-31, 233.280 celdas por canal (9.960 evaluables) | 0 nominadas por FDR q 0,10; 40 pistas sin nominación |
| 2026-10-25 | EXPZ-NQ PISTAS (ATJ-25): top-20 congeladas, réplica en una ventana no usada | NQ 2026-04-01 → 2026-09-25 | **SIN_CANDIDATAS**: un paso de LORD++ del lote (t=1, nivel 0,0109) con p de Simes 0,59; 0 de 20 confirmadas |

## NO MEDIDO
- EXPZ-CFD (señal en USATECH, operación en NQ): DESC con el código vigente en curso.
- EXPZ en el oro (XAU → GC): se considera sólo si alguna de las dos campañas sobrevive.
- Alcance de la muerte de EXPZ-NQ: la familia EXPANSION_ZONAS con señal en NQ, sus 233.280 celdas y las ejecuciones declaradas; no alcanza a EXPZ-CFD.
