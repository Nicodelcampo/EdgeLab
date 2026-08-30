# Incidente: exposición de outcomes no autorizada — corrida abortada de Gate 1 NQ (diseño MFE-MAE descartado)

**Fecha:** 2026-08-29
**Rama:** `research/bt2a-nq-gate1-v1-20260829`
**Kernel:** `nicolasbuttaro/bt2a-nq-gate1-all5-v1`, versión 2, commit `efbe19685ad33a351693326a925670e5119a4252`
**Estado:** el diseño MFE-MAE simplificado de esta rama queda **descartado**. Nico eligió seguir el protocolo de 16 celdas ya construido (`docs/research/BT2A_NQ_CAMPAIGN_SEQUENCE_V1_2026-08-28.md`, `tools/preflight_bt2a_nq_gate1.py`). Esta rama no se retoma como camino de ejecución.

## Corrección de clasificación

Clasificación inicial (incorrecta): "cero datos de outcome persistidos, exposición mínima/teórica".

Corrección (auditor, canal Notion, 2026-08-29 22:56 ART): **cero checkpoints persistidos no equivale a cero outcomes abiertos**. Si una sesión computó MFE/MAE en memoria antes de crashear, el acceso ya ocurrió, aunque el resultado se haya perdido.

## Estado real, verificado

```text
CAMPAIGN_OUTCOMES_OPENED       = true
OUTCOMES_ACCESSED              = true
N_OUTCOME_SESSIONS_COMPUTED    = 1   (sesión índice 0: NQ 09-25, 20250804)
N_CHECKPOINTS_PERSISTED        = 0
RESULTS_INSPECTED              = false
```

`RESULTS_INSPECTED=false` es verificable, no "unknown": el traceback (`KeyError: 'registry_payload_sha256'`) ocurrió dentro de la construcción del diccionario de retorno de `compute_session()`, antes de que la función devolviera nada. Lo único que llegó al log fue la traza de Python -- ningún valor de K_ABS, K_BT2, MFE o MAE fue impreso, guardado ni visto por nadie.

## Causa técnica del crash (no relacionada con la exposición en sí)

El registro de sesiones de NQ (`specs/bt2a_gate1_nq_all5_sessions_2026-08-27.json`) en esta rama fue modificado (commit `7a5b4fff...`) para agregar `registry_payload_sha256` faltante. El kernel de Kaggle reusó un clone previo (`/kaggle/working/EdgeLab/.git` ya existía de la versión 1 del kernel) y el checkout del commit correcto no dejó el árbol de trabajo en el estado esperado por `compute_session()` en ese momento -- causa exacta no diagnosticada porque la rama se abandonó al mismo tiempo que se descartó el diseño.

## Nota sobre el archivo modificado

El registro de sesiones modificado en esta rama (`7a5b4fff...`) vive **aislado** en `research/bt2a-nq-gate1-v1-20260829`. Verificado: la rama original de la selección target-free (`research/bt2a-nq-target-free-selection-v1-20260828`), de la que depende el binding de hash `f50350ee67d53be38cd00e0f3e548cc877e980aebb3b08e422cdde007b39c6cb` fijado en `specs/bigtrap2_nq_tickframes_sweep_v2.draft.json` y `specs/bt2a_nq_target_free_selection_v1.draft.json`, **nunca fue tocada** por este commit. No hay colisión de hash real en la rama desde la que se retomaría cualquier trabajo futuro.

## Aporte al referente

Deja registrada, con clasificación corregida, la única exposición de outcomes NQ producida por el diseño MFE-MAE descartado. No autoriza ni habilita ninguna corrida futura bajo ese diseño.
