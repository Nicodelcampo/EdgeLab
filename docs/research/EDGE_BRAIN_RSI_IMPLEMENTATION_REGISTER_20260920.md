# Edge Brain — Registro de Implementación y Reconstrucción (2026-09-20)

## 1. Identificación y Estado

- **Fecha:** `2026-09-20T23:50:00Z`
- **Modo de Operación:** `CONTENT_EQUIVALENT_NOT_BYTE_IDENTICAL`
- **Bundle Original:** `ORIGINAL_BUNDLE_UNAVAILABLE` (SHA-256 esperado: `21655a829ba79f397953cd5555712635c61ee26523d3b9cc8f948470e00aeeee` no encontrado en discos locales/remotos).
- **Commits Originales:** `ORIGINAL_COMMITS_UNREACHABLE` (`6c0d90cab7e9956d9a9ffc3832d9c02d336058bc`, `eb69e301f25a9c3d66d0677a0d85e975cf16f9db`, `6081c6faedb6af01b90d658cca45ad67b9bd52dd`).
- **Rama Base:** `feat/edge-discovery-brain-foundation-20260919` @ `84eea9758ca50fd07e07076dd346e0947bffcf3f`
- **Rama de Trabajo:** `feat/reconstruct-edge-brain-complete-20260920`
- **Worktree:** `D:/EdgeLab-brain-reconstruct`

## 2. Inventario de Componentes Reconstruidos

### Módulos Python en `edgelab/edge_brain/`
1. `edgelab/edge_brain/typed_registry.py`: Ledger canónico hash-chained append-only, validación previa al append, verificación de relaciones tipadas declaradas, proyección determinista JSON y Parquet ZSTD con pyarrow, validación de promociones de síntesis.
2. `edgelab/edge_brain/hippocampus.py`: Memoria experimental que administra episodios, pasos, expectativas, fallas, reparaciones, éxitos, lecciones, contraejemplos, reconstrucción secuencial de trayectorias y bloqueo activo de reutilización de artefactos invalidados o desactualizados.
3. `edgelab/edge_brain/context_memory.py`: Memoria de trabajo con presupuestos de tokens estrictos, procedencia obligatoria, razón explícita de inclusión y hashing determinista.
4. `edgelab/edge_brain/measurement_atlas.py`: Validación estructural de catálogos, roles, unidades, temporización, normalización, ablaciones y modos de falla, exigiendo `asserts_edge=False` para estados DRAFT/PROPOSED.
5. `tools/edge_brain_cli.py`: Herramienta CLI con subcomandos `schemas`, `validate-atlas`, `verify-ledger`, `project-parquet`, y `smoke-test`.
6. `edgelab/edge_brain/__init__.py`: Exportación consolidada de todos los módulos y tipos.
7. `edgelab/edge_brain/invalidation.py`: Soporte de todas las relaciones tipadas sin alterar la semántica de propagación dura/blanda.

### Inventario de Schemas (35 exactos)
- 6 conservados: `claim`, `coverage_artifact`, `dependency_edge`, `measurement_contract`, `methodological_learning`, `model_run`.
- 19 declarados explícitamente: `analysis_episode`, `step_execution`, `expectation`, `failure_event`, `causal_hypothesis`, `repair_action`, `success_event`, `lesson_candidate`, `learning_rule`, `skill`, `reuse_event`, `reuse_outcome`, `counterexample`, `synthesis`, `context_pack`, `open_question`, `indicator_definition`, `composition_contract`, `measurement_atlas_catalog`.
- 10 contratos de capas anteriores: `source_artifact`, `evidence_artifact`, `experiment`, `experiment_result`, `adjudication`, `promotion_decision`, `contamination_event`, `custody_verification`, `projection_manifest`, `hypothesis_proposal`.

### Semilla de Configuración
- `config/edge_brain/measurement_atlas_seed.json`: Contiene `ATLAS-FOUNDATION`, `METHODOLOGICAL_CORTEX`, `IND-EMA`, `IND-RSI`, `COMP-EMA-RSI-REGIME-TRIGGER`, y `TREND_STRENGTH`. Todos como `DRAFT`/`PROPOSED` con `asserts_edge=False`.

## 3. Resultados de Pruebas y Validación

- `python -m pytest -q (Get-Item tests\test_edge_brain*.py).FullName`: **34 passed in 0.85s**
- `python -m compileall edgelab/edge_brain tools/edge_brain_cli.py`: **PASS**
- `python tools/edge_brain_cli.py schemas`: **PASS (35/35 schemas válidos)**
- `python tools/edge_brain_cli.py validate-atlas config/edge_brain/measurement_atlas_seed.json`: **PASS**
- `python tools/edge_brain_cli.py smoke-test`: **PASS (bit-for-bit Parquet ZSTD / canonical ledger parity confirmed)**
- `git diff --check`: **PASS**
