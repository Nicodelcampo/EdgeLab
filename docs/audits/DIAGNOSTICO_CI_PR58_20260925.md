# Diagnóstico del CI del PR #58 (solo lectura, 2026-09-25)

**Qué se leyó:** los logs de las corridas 36087007967 (push, `3b4e98c`) y 36087009895 (pull_request, merge `ed79699`) de `feat/edge-brain-learning-governor-20260924`, y la última corrida del PR #56 (35932416166, `e64f311`). Todo con `gh`, sin tocar ninguna rama.

**Resultado:** 21 fallas y 1 error, **iguales en las dos corridas**.

## 1. Tres fallas son del código nuevo del #58

| Test | Qué pasa | Causa probable |
|---|---|---|
| `test_edge_brain_sealed_audit.py::test_sqlite_triggers_reject_identity_edits_deletes_and_invalid_transitions` | Espera `IntegrityError` con "immutable" y recibe **"invalid sealed audit state transition"** | En el UPDATE del test se dispara primero el trigger de transición de estado, antes que el de identidad inmutable. Opciones: que el test cambie sólo columnas de identidad dejando el estado igual, o que el trigger de transición tenga `WHEN OLD.state <> NEW.state`. |
| `test_edge_brain_sealed_audit.py::test_failed_or_interrupted_attempt_is_burned_not_retried` | **No levanta `AuditAlreadyUsed`** al reintentar después de un intento fallido o interrumpido | La reserva no queda "quemada" en la base cuando el intento falla. Es un defecto real de custodia: justo lo que el componente promete impedir. |
| `test_edge_brain_recursive_eval.py::test_rejects_mismatched_or_insufficient_or_overlapping_eval_sets` | **No levanta `ValueError`** en el caso "insufficient" (los casos "exactly paired" y "disjoint" sí levantan) | Falta, o no se alcanza, el chequeo de tamaño mínimo del conjunto de evaluación. |

## 2. Las otras 18 fallas y el error NO vienen del #58

- El #58 difiere del #56 (`e64f311`) en **sólo 7 archivos nuevos** (`work_governor.py`, `recursive_eval.py`, `sealed_audit.py`, sus tests y un doc). Los tests que fallan no están entre ellos.
- La corrida del #56 del 23/09 sobre ese mismo árbol dio **1 falla** (`test_sonda_identidad`).
- Los mismos tests, sobre archivos idénticos, fallan el 25/09. Es **deriva del entorno o del tiempo**, no el diff del #58:
  - gates que dependen de la fecha: `test_current_md`;
  - calendario: `test_nq_session_gate`, que da `TRADE_DATE_NOT_IN_CME_CALENDAR` → ABSTAIN;
  - estado de git en el checkout: `test_bigtrap2_distance_matched_null` (`dirty_start`, `data_root`);
  - pendientes ya conocidos de P-31: `test_ulp_sweep`, y el fixture `null_out` de `test_prerange_sweep_formal`.
- **Cómo confirmarlo con un clic:** re-correr el CI del #56 hoy. Si da las mismas 18 + 1, es deriva y no del #58.

## 3. Lo que esto significa para la integración

El #58 tiene **tres defectos propios que arreglar**; uno de ellos (la reserva que no se quema) es de fondo. Además, la base arrastra deriva que hay que resolver antes de que cualquier CI de esa cadena pueda estar verde.

Coordinación: la rama `feat/unified-nt8-viewer-20260920` también toca `edgelab/edge_brain/hippocampus_store.py` (guardia de controles `CTRL_TIMING_V1`), y hay que reconciliarla con #56 y #58 antes de mergear.
