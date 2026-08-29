# Decisión: selección target-free NQ cortada en 2/5 contratos

**Fecha:** 2026-08-29
**Decidido por:** Nico
**Rama:** `research/bt2a-nq-target-free-selection-v1-20260828`

## Contexto

La campaña de selección target-free de BigTrap2Absorption para NQ (`specs/bt2a_nq_target_free_selection_v1.draft.json`)
completó 2 de 5 contratos en Kaggle (NQ 09-25, NQ 12-25 — 104 configs
cada uno) antes de que Nico decidiera no continuar con los 3 restantes
(NQ 03-26, NQ 06-26, NQ 09-26).

## Evidencia que sostuvo la decisión

Comparación directa de `n_events` por config entre los dos contratos
completos (no es el score estructural formal — ver más abajo):

- Correlación de rangos (Spearman) entre NQ 09-25 y NQ 12-25: **0,976**
- Top-10 configs por `n_events`: **100% idéntico** entre los dos contratos
  (mismo conjunto, solo cambia el orden interno)

## Config adoptado (informal)

```
bt2a_nq_7e84981882b0b380
```

Parámetros: idénticos al headline/baseline (`AbsorptionPct=90`,
`TapeWindowTicks=25`, `ImbalanceRatio=3`, `ImbalanceMode=Diagonal`,
`ScoreMode=AbsMagnitude`, `AbsorptionLookback=500`, `MinHistoryBuckets=200`,
`TrapVolumeSource=AggressiveSide`, `UseWickFilter=true`, `WickZonePct=30`,
`TicksPerRow=1`, `RequireFlowSideMatch=true`), con una sola diferencia:
`MinStackedRows=1` en vez de `2` (el baseline pide 2 filas apiladas para
confirmar una trampa; bajarlo a 1 relaja el criterio).

Eventos: 18.538 (NQ 09-25) + 44.546 (NQ 12-25) = 63.084 sobre los dos
contratos completos.

## Estado formal — no confundir con una selección cerrada

**Esto NO es `SELECTED_STABLE_NQ_CONFIGURATION`.** El protocolo congelado
exige `minimum_contracts_with_events: 4` para declarar elegible a un
config, precisamente para descartar configs cuyo comportamiento sea un
artefacto de un solo contrato. El score real de selección
(`0.45×jaccard_vecinos + 0.25×cobertura_sesiones + 0.20×(1-concentración_por_contrato)
+ 0.10×estabilidad_vecinos`) nunca se calculó — lo que se comparó acá es
solo `n_events`, un proxy razonable para chequear consistencia, no la regla
de selección formal.

Si en el futuro se decide usar `bt2a_nq_7e84981882b0b380` como config de
Gate 1 para NQ, queda declarado que la evidencia detrás es esta comparación
de 2 contratos, no una corrida cerrada del selector.

## Estado del kernel

El kernel de Kaggle (`nicolasbuttaro/bt2a-nq-target-free-selection-v1`)
seguía corriendo sobre NQ 03-26 al momento de esta decisión. No se
relanzará más. El progreso ya subido a
`nicolasbuttaro/edgelab-nq-selection-checkpoints` (2/5 contratos) queda
como registro de lo que sí se completó formalmente.

## Aporte al referente

Cierra la selección target-free de NQ con evidencia de consistencia entre
contratos, sin gastar el presupuesto de tiempo de cómputo de los 3
contratos restantes. Deja explícito que el config adoptado es una lectura
informal, no una `SELECTED_STABLE_NQ_CONFIGURATION` formal — cualquier uso
posterior en Gate 1 de NQ debe citar esta distinción.
