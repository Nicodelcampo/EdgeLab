# EF0 de aVolClusterPOI sobre el intervalo operable de NQ 06-26 — 2026-09-02

**`execution_status = COMPLETE`, integridad `PASS`,
`scientific_status = EF0_COMPLETE_REGIME_NOT_CERTIFIED`.**
Kernel `avolcluster-operable-ef0-20260902`, code_commit `b48675a`.
`outcomes_accessed=false`, `holdout_accessed=false`, `auto_execute_ef1=false`.
`trace_sha256` `83207e18…8219bd`.

## Qué se hizo distinto

El trace previo (`avolclusterpoi-tracedump-full-nq0626`) recorrió las **72 sesiones del
archivo** NQ 06-26, de las cuales **6 no pertenecen a ese contrato**: 3 pre-roll son de
NQ 03-26 y 3 post-roll son de NQ 09-26. Filtrar sus bloques a posteriori **no** deshace que
la historia del indicador (`SessionProfile`, buckets) se acumuló cruzando el roll.

Acá se **reconstruyó desde ticks**: el recorte al intervalo operable `[20260317, 20260616)`
se aplica a los **ticks**, *antes* de construir barras, footprints y correr el indicador.
Barras, footprints y `SessionProfile` arrancan limpios en el borde — cumple
`state_boundary = RESET_AT_CONTRACT_ROLL`.

## Efecto del reset

| | trace previo (72 sesiones) | operable con reset (66) |
|---|---|---|
| bloques | 28.477 | **28.147** |
| CREATE candidates | 658 | **653** |
| zonas OFF_PRICE | 414 | **409** |
| candidatos AT_PRICE | 244 | **244** |

El efecto es chico y asimétrico: las 6 sesiones removidas aportaban **5 zonas off-price y
cero at-price**. Es coherente con que sean tramos en que NQ 06-26 aún no era, o ya no era,
el contrato líquido.

## Perfil estructural (EF0-B)

- 33.804.950 ticks → 281.739 barras de 120 ticks → 28.147 bloques completos, **65 sesiones
  con bloques**, 46 buckets.
- Población: `n_universe = n_available = n_eligible = n_processed = 28.147` (sin pérdida).
- **63 de 65 sesiones** tienen al menos un candidato CREATE; **60 de 65** tienen al menos
  una zona off-price.

Tasas por 100 bloques:

| decisión | por 100 bloques |
|---|---|
| `ABSTAIN_BELOW_THRESHOLD` | 87,73 |
| `ABSTAIN_NO_CLUSTER` | 5,96 |
| `ABSTAIN_NO_HISTORY` | 3,99 |
| CREATE candidates | 2,32 |
| — de ellos, zonas off-price | 1,45 |
| — de ellos, at-price | 0,87 |

Distribuciones (p10 / p50 / p90):

| métrica | p10 | p50 | p90 | max |
|---|---|---|---|---|
| bloques por sesión | 334 | 429 | 567 | 816 |
| CREATE por sesión | 6 | 10 | 16 | 24 |
| zonas off-price por sesión | 3 | 6 | 11 | 16 |
| `history_samples` | 44 | 323 | 807 | 1246 |
| celdas por bloque | 50 | 87 | 151 | 480 |
| clusters candidatos | 1 | 2 | 5 | 29 |
| ancho de zona (ticks) | 14 | 23 | 36 | 57 |
| distancia off-price (ticks) | 3 | 19 | 55 | 169 |
| `score/threshold` (todos los listos) | 0,088 | 0,289 | 0,725 | 2,045 |
| `score/threshold` (sólo CREATE) | 1,018 | **1,095** | 1,267 | 2,045 |

Concentración por sesión: HHI 0,019 y CV ≈ 0,50 para ambas familias; el 10 % de sesiones
más activas concentra el 21 % de los CREATE. No hay una sesión dominante.

## Dos observaciones que saltan del perfil

1. **El sistema vive muy cerca de su umbral.** La mediana de `score/threshold` entre los
   CREATE es **1,095** — apenas 9,5 % por encima del corte — y el p10 es 1,018. Un
   movimiento pequeño de `detection_percentile` reasigna una fracción grande de los 653
   candidatos. Es exactamente lo que la tarjeta `Q-THRESHOLD-PRESSURE` pide revisar.
2. **`ABSTAIN_BELOW_THRESHOLD` domina con 87,7 %**, y la mediana de `score/threshold` sobre
   todos los bloques listos es 0,289. La detección es rara por construcción, no por falta
   de historia (`ABSTAIN_NO_HISTORY` es sólo 3,99 %).

## Estado y qué NO significa

`epistemic_status = PROVISIONAL_UNPARITIED_FOR_FORMAL_SELECTION`,
`stage = EF0_B_STRUCTURAL_PROFILE`, `population_id = NQ_06-26_120tick_preholdout_complete_blocks_v1`.

Las **5 tarjetas de pregunta** (`Q-HISTORY-STATE`, `Q-THRESHOLD-PRESSURE`, `Q-GEOMETRY`,
`Q-ATPRICE-OFFPRICE`, `Q-SESSION-STABILITY`) están todas en
`REVIEW_REQUIRED_NOT_A_GATE` con `auto_execute=false`: **describen y proponen, no habilitan
EF1**.

El manifiesto de régimen **sigue sin certificar** (falta evidencia de completitud aprobada
y Juneteenth 2026-06-19 sin adjudicar), por eso `regime_certified=false`. El intervalo usado
proviene del scan v2 y de la sensibilidad P-68, que mostró las 4 fechas de roll idénticas a
6 decimales con y sin feriados — robusto, no certificado.

`all_blocks.json` (53 MB) no se versiona; se reproduce con el kernel pineado a `b48675a`.
