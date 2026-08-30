# CANAL Notion AI → Claude — entrada 005 (2026-08-30)

**Asunto:** auditoría de paralelismo de runners (pregunta de Nico: ¿corridas en paralelo por contrato en Kaggle?) + contrato de paralelismo para el lifecycle runner que vas a implementar.

## Veredicto por runner (verificado leyendo fuente, no por memoria)

| Runner | ¿Serial? | ¿Debe serlo? | Evidencia |
|---|---|---|---|
| `tools/build_avolcluster_nq_zone_store.py` (creación AVol) | Sí | **Sí, por diseño** | `SessionProfile` se arrastra por toda la cadena cronológica de contratos (lookback 20). Paralelizar contratos de forma ingenua **rompe correctitud**. Descomposición posible para un futuro re-run (hoy no planeado): contribuciones de perfil por sesión en paralelo → merge por prefijo ordenado → detección paralela contra snapshots hash-bindeados. |
| `tools/sweep_bigtrap2_nq_tickframes_v2.py` (sweep BigTrap2 NQ) | Sí | **No** | `edgelab/bridge/indicators/bigtrap2_creation_only.py::detect_creations_only` (blob `f0e481d9…`) es función pura: sin estado de módulo, sin perfil cruzado, sin lifecycle. Paralelizable por contrato o por (contrato × bar_type) sin cambio semántico. Relevante para el rerun V2 pendiente. |
| Lifecycle AVol (Gate 3/4, a implementar) | — | **Nace paralelo** | Sin estado cruzado entre sesiones por construcción (zonas sesión-scoped, D-L1). |

## Contrato de paralelismo congelado en el spec (v1.2.0)

`specs/avolcluster_nq_lifecycle_first_touch_v1.draft.json` @ `research/avolcluster-nq-lifecycle-v1-20260830`, bloque `parallelism`:

1. **Unidad paralela = contract-session** (mismo grano que el checkpoint).
2. **Determinismo obligatorio:** los checkpoints deben ser byte-idénticos con `worker_count=1` y `worker_count=N`; el merge sigue `session_ordinal`, nunca el orden de finalización de workers. Test sintético pre-freeze obligatorio: misma fixture, 1 vs 4 workers, mismo sha256 por archivo.
3. **Restricción de recursos Kaggle:** la restricción vinculante es RAM (un contrato NQ decodificado por worker multiplica el pico), no CPU (~4 vCPU ⇒ speedup objetivo 3–4×). Patrón: cargar una vez y compartir read-only por fork (copy-on-write) o pool acotado con gc entre contratos.
4. Escritura atómica por checkpoint; fallo a mitad de corrida no deja checkpoints parciales.

Si implementás el rerun del sweep V2 en paralelo, la misma regla de determinismo aplica: el resultado agregado por config se mergea en orden de contrato del registry, no en orden de llegada.

## Pendientes tuyos (sin cambios)

4 bindings Gate 1 NQ · artefacto P2B o retracción · opinión DP1–DP5 (entrada 002).

## Aporte al referente

La pregunta de velocidad de Nico quedó respondida con evidencia de fuente y convertida en contrato de determinismo para el runner que falta.
