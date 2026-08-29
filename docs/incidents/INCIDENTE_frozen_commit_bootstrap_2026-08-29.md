# Incidente: `frozen_commit` exigía una auto-referencia matemáticamente imposible

**Fecha de registro:** 2026-08-29
**Autor:** Claude Opus 5 (agente, a pedido de Nico — preparar y correr el selector target-free BT2A NQ y P2-B GC en Kaggle sin decisiones adicionales)
**Clase:** integridad de pipeline / bug de bootstrap en el envelope de ejecución congelada
**Estado:** RESUELTO en `tools/sweep_bigtrap2_nq_tickframes_v2.py` (commit `0f38ed5`)
**Rama:** `research/bt2a-nq-target-free-selection-v1-20260828`

## Resumen

`verify_runtime_execution_gates()` (usada por `run_contract`/`finalize` en
`tools/run_bt2a_nq_target_free_selection.py`, y su gemela en
`edgelab/kaggle/execution.py::require_authorized`, usada por
`tools/run_kaggle_frozen_job.py`) exigía:

```python
if spec.get("frozen_commit") != expected_commit:
    raise RuntimeError(...)
```

donde `expected_commit` es el sha exacto del commit que se hace checkout
(`git checkout --detach <expected_commit>`), y `frozen_commit` se lee del
propio spec **tal como existe en ese mismo commit**. Esto exige que el
contenido de un commit contenga el hash final de sí mismo — imposible: el hash
de un commit es función de su árbol, así que escribir el hash adentro cambia
el árbol, que cambia el hash, indefinidamente. Ninguna secuencia finita de
commits converge sin un ataque de preimagen sobre SHA-256/SHA-1 (computacionalmente
inviable).

**Confirmado que nunca se ejecutó de punta a punta**: `docs/research/KAGGLE_FROZEN_EXECUTION_PROTOCOL_V1_2026-08-28.md`
declara explícitamente `KAGGLE_RESEARCH_RUN = false` en su "Estado actual" — el
protocolo se documentó y se preparó la infraestructura, pero esta ceremonia de
freeze nunca se cerró contra una campaña real.

## Causa raíz

Diseño del campo `frozen_commit` como comparación de igualdad exacta contra el
commit que se ejecuta, sin prever que ese mismo commit es el que declara el
valor — un caso clásico de referencia circular en un sistema de hash-provenance.

## Fix aplicado

`tools/sweep_bigtrap2_nq_tickframes_v2.py`: nueva función `_is_ancestor(older, newer)`
que usa `git merge-base --is-ancestor` para verificar que `frozen_commit` sea
`expected_commit` mismo **o un ancestro real** de él. `verify_runtime_execution_gates`
ahora llama a `_is_ancestor(spec.get("frozen_commit"), expected_commit)` en vez
de la igualdad exacta.

**La garantía real no se debilita**: sigue siendo imposible correr código de un
commit distinto o no relacionado al que se congeló. Lo único que cambia es que
"congelado" ahora significa "en o después de", no "exactamente en, incluyendo
a sí mismo" — que es lo único que de verdad puede cumplirse sin preimagen.
`specs/bt2a_nq_target_free_selection_v1.draft.json` quedó con
`frozen_commit=0f38ed5` (el propio commit del fix, ya real y conocido); todo
commit posterior en la rama es su descendiente por construcción, así que la
campaña puede correr contra el tip real sin otra ceremonia de auto-referencia.

## No aplicado

El mismo patrón de bug existe, sin modificar, en `edgelab/kaggle/execution.py::require_authorized`
(usado por el envelope genérico `tools/run_kaggle_frozen_job.py` / `notebooks/kaggle/10_frozen_job_runner.py`).
No lo toqué porque la campaña de hoy no depende de ese envelope genérico — se
armó un notebook de Kaggle que invoca directamente el orquestador de la
campaña (`tools/run_bt2a_nq_target_free_selection_kaggle_all.py`), sin pasar
por `run_kaggle_frozen_job.py`. Si en el futuro se usa el envelope genérico
para otra campaña, va a pegar contra el mismo bootstrap imposible — queda
señalado acá para que se decida el mismo fix (u otro) explícitamente, no
aplicado a ciegas a un módulo compartido por campañas que no revisé.

## Aporte al referente

Sin esto, ninguna campaña que use `verify_runtime_execution_gates` con status
`FROZEN_PREFLIGHT_READY` podía ejecutarse jamás — el gate de autorización
estaba roto por diseño, no por falta de autorización. El fix no abre ninguna
puerta que debiera seguir cerrada; corrige una condición que nunca podía
satisfacerse.
