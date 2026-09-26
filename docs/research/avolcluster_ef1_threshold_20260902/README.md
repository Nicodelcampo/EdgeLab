# EF1 — sensibilidad a `detection_percentile` (aVolClusterPOI, NQ 06-26 operable)

**`PROVISIONAL_DIAGNOSTIC_REGIME_NOT_CERTIFIED`.** Autorizado por Nico el 2026-09-02
como diagnóstico provisional. Plan: `specs/avolclusterpoi_ef1_plan_v1.draft.json`.
Kernel `avolcluster-ef1-threshold-20260902`, code_commit `3a2b2ab`.
`winner_selected=false`, `outcomes_accessed=false`, `holdout_accessed=false`,
`promotion_eligible=false`. `roll_schedule_sha256 = PENDING_REGIME_CERTIFICATION`.

Responde `Q-THRESHOLD-PRESSURE` y `Q-ATPRICE-OFFPRICE` de EF0.

## Control de método (pasa)

El barrido se hizo **post-hoc**: `SessionProfile.add_block()` acumula `best_score`, que no
depende de `detection_percentile`, así que la historia por bucket es idéntica para toda la
grilla y los 6 niveles se recomputan re-simulando el profile **desde los bloques**, sin
recorrer ticks. Una corrida en vez de seis.

Self-check: el replay al baseline 98,0 debía reproducir el trace real.

| | |
|---|---|
| `replay_create_at_baseline` | 653 |
| `trace_create` | 653 |
| **match** | **true** |

## Resultado

| percentil | CREATE | off-price | at-price | `ABSTAIN_BELOW_THRESHOLD` |
|---|---|---|---|---|
| 96,0 | 1.171 | 752 | 419 | 24.174 |
| 97,0 | 884 | 550 | 334 | 24.461 |
| 97,5 | 775 | 479 | 296 | 24.570 |
| **98,0** (baseline) | **653** | **409** | **244** | 24.692 |
| 98,5 | 512 | 319 | 193 | 24.833 |
| 99,0 | 380 | 234 | 146 | 24.965 |

Regla de parada declarada en el plan (turnover de CREATE entre 97,5 y 98,5 > 50 %):
`worst_mid_turnover = 0,2159` → **no se disparó**.

## Hallazgo principal: las poblaciones están perfectamente anidadas

Si los conjuntos están anidados, `jaccard(a,b)` debe ser exactamente `n_b / n_a`. Se cumple
en los cinco pasos, a cuatro decimales:

| paso | jaccard | n_b/n_a | coincide |
|---|---|---|---|
| 96,0 → 97,0 | 0,7549 | 0,7549 | ✔ |
| 97,0 → 97,5 | 0,8767 | 0,8767 | ✔ |
| 97,5 → 98,0 | 0,8426 | 0,8426 | ✔ |
| 98,0 → 98,5 | 0,7841 | 0,7841 | ✔ |
| 98,5 → 99,0 | 0,7422 | 0,7422 | ✔ |

**Subir el percentil sólo remueve candidatos; nunca agrega uno nuevo.** Lo que EF0 leyó como
"presión de umbral" no es inestabilidad: es un **filtro monótono**. El llamado *turnover*
(12–26 %) es puro descarte, no reemplazo.

Esto matiza el hallazgo de EF0. El indicador **sí** vive pegado a su umbral —la mediana de
`score/threshold` entre los CREATE era 1,095— y el tamaño de la población es muy elástico
(**3,1×** entre 96,0 y 99,0). Pero el ranking por score es invariante y el conjunto no se
reordena. Elegir el percentil decide **cuántos** eventos, no **cuáles**.

Consecuencia metodológica: en este eje el riesgo de data snooping es menor de lo que
sugería EF0, porque no hay reordenamiento que explotar — sólo un corte más o menos estricto
sobre un orden fijo.

## `Q-ATPRICE-OFFPRICE`: respondida

`blocks_reclassified_at_off = 0` **en los cinco pasos**. Cambiar el percentil **nunca**
reclasifica un bloque entre AT_PRICE y OFF_PRICE: sólo altera qué bloques se detectan, no
cómo se clasifican. La proporción off-price es notablemente estable — 0,6158 a 0,6422 en
todo el rango, sin tendencia.

Es exactamente lo que la tarjeta pedía distinguir: **el eje afecta detección, no
clasificación**. Los denominadores at/off pueden mantenerse separados sin temor a que una
perturbación del umbral los mezcle.

## Lo que esto NO dice

No se eligió configuración ganadora ni se midió calidad de ninguna. No se abrieron outcomes,
retornos, MFE/MAE ni P&L. El régimen sigue sin certificar, así que nada de esto es promovible
a resultado formal.

Los tres ejes diferidos (`Q-GEOMETRY`, `Q-HISTORY-STATE`, `Q-SESSION-STABILITY`) siguen sin
medir; el anidamiento demostrado acá vale **sólo** para `detection_percentile` y no debe
suponerse para los parámetros de geometría.
