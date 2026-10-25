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

## Auditoría del filtro (2026-10-25, pedido de Nico: «es raro que descarte todo siendo tantas variantes»)
- **El tamiz cobra multiplicidad, no está roto.** La mejor celda de EXPZ-NQ dio +26 pts/op con p 0,0015 (n 63): con 9.960 celdas
  evaluables el FDR pide p ≈ 1e-5. Por eso existe la réplica de pistas.
- **Réplica:** 16 de 17 pistas evaluables de EXPZ-NQ dieron media positiva (+1 a +14) en abr–sep, ninguna significativa sola. No es
  señal amplia: las pistas comparten operaciones (1.363 operaciones = 438 decisiones distintas). Promediando por decisión, la réplica
  da **+1,39 pts/op, IC90 [−4,27, +7,07], p 0,34** (118 sesiones); EXPZ-CFD +0,21, p 0,46. Descriptivo, posterior al resultado.
- **El embudo sí deja pasar un candidato real:** re-chequeo de U1 sobre los mismos arreglos (`FALSOS_NEGATIVOS_EMBUDO_20261024.md`):
  el lote de USATECH rechaza en el primer paso y confirma 2 de 5 celdas.
- **Lo que sí se corrigió hoy:** una pista con < 30 operaciones entraba al lote con un p de B=500 que no podía resolver el umbral.
- **Diseño, no filtro:** el 96 % de las 233.280 celdas no llega a 30 operaciones (33.480 operaciones en total). Una grilla tan fina
  gasta multiplicidad registrada en celdas que no se pueden evaluar; en las campañas nuevas conviene menos perillas por evento.
