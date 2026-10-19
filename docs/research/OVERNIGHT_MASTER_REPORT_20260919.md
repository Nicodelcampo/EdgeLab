# EdgeLab — Informe Maestro de Ejecución Nocturna (2026-09-19)

> **Estado Rector:** `OVERNIGHT_FOUNDATION_COMPLETE`  
> **Expansión Multiactivo:** `PASS_MULTI_CONTRACT_25T_HFT_EXPANSION`  
> **Auditoría de Custodia:** 55 `COMPLETE_VERIFIED` / 1 `BLOCKED_BY_CUSTODY` (`NQ 09-26`)  
> **Holdout Firewall:** `ENFORCED` (0 filas decodificadas post 2026-07-01)  
> **Outcomes Firewall:** `ENFORCED` (0 retornos futuros, 0 PnL calculados)  
> **Worktree Factory:** `E:\EdgeLab-edgefactory` (`local/edge-discovery-factory-foundation-20260919`)  

---

## 1. Resumen Ejecutivo de la Expansión Multiactivo 25t/HFT

1. **Contratos Procesados:** Se completaron determinísticamente los 39 contratos pendientes bajo concurrencia 1, orden instrumento $\rightarrow$ vencimiento.
2. **Resultado de Inventario:**
   - `COMPLETE_VERIFIED`: 55 contratos (11 instrumentos: 6B, 6E, 6J, ES, GC, MBT, MES, MNQ, NQ, YM, ZB).
   - `BLOCKED_BY_CUSTODY`: 1 contrato (`NQ 09-26`, debido a 0 ticks en el parquet fuente; preventivamente excluido sin detener la ejecución).
   - `TOTAL`: 56 contratos planificados.
3. **Métricas de Datos:**
   - **Bundles Generados:** 147 bundles mensuales/individuales.
   - **Barras 25t Calculadas:** 40,380,402 barras.
   - **Zonas HFT Generadas:** 3,328,710 zonas causales.
   - **Paridad JSON/JS:** 100% de paridad canónica SHA-256 verificado en los 147 bundles.
4. **Presupuesto y Gestión de Recursos:**
   - Memoria máxima observada: 512.4 MB (muy por debajo del límite de 1.5 GB).
   - Liberación de memoria con `trim_working_set()` y streaming JSON/JS atómico directo a disco.

---

## 2. Catálogo y Smoke del Visor NinjaTrader 8

- **Manifiestos Generados:** `viewer/nt8_bridge/bundles/manifest.json` y `manifest.js` (147 activos verificados).
- **Smoke HTTP Machine-Readable:** 147/147 activos respondieron con HTTP 200 sin errores (`FINAL_VIEWER_SMOKE.json`).
- **Capturas de Pantalla Representativas:**
  - 6E: `screenshot_viewer_6e.png`
  - ES: `screenshot_viewer_es.png`
  - MNQ: `screenshot_viewer_mnq.png`
  - NQ: `screenshot_viewer_nq.png`
  - ZB: `screenshot_viewer_zb.png`
  - Perfil de Densidad Causal: `screenshot_viewer_causal_density.png`
  - Mismatch deliberado de `bar_key`: `screenshot_viewer_bar_key_mismatch.png` (verificación de abstención visual en rojo).

---

## 3. Fundación de Edge Discovery Factory (Issue #42)

En el worktree aislado `E:\EdgeLab-edgefactory`:
1. **Especificación Canónica:** `docs/research/EDGE_DISCOVERY_FACTORY_SPEC.md` materializando visión, etapas científicas, interfaz canónica, motores, guardrails, schemas, criterios de promoción, políticas de holdout, resultados negativos y autonomía.
2. **Runbook y Estado:** `docs/research/EDGE_DISCOVERY_FACTORY_RUNBOOK.md` y `docs/research/EDGE_DISCOVERY_FACTORY_STATUS.md`.
3. **Inventario de Schemas:** 147 bundles auditados, clasificando el indicador `HFTZonesUniversal` como `CAUSAL_READY` con `PARITY_ABSTAIN` explícito (`schema_inventory.json` y `schema_coverage.md`).
4. **Schemas JSON Canónicos:** Implementados bajo `schemas/edge_factory/` para:
   - `zone_events.json` (estricto causal, rechaza `ORIGIN_FALLBACK_UNVERIFIED`);
   - `zone_events_exploratory.json` (segregado para zonas no causales);
   - `corridor_events.json`;
   - `hypothesis_registry.json`;
   - `experiment_registry.json`;
   - `negative_results_registry.json`;
   - `analysis_dependencies.json`.

---

## 4. Feature Store Target-Free

- **Implementación:** `tools/build_edge_factory_target_free_store.py` (lectura read-only de bundles).
- **Almacenamiento Columnar:** Parquet comprimido con ZSTD particionado por `instrument/contract/month/`.
- **Volumen Procesado:**
  - `zone_events`: 3,328,710 zonas causales.
  - `zone_events_exploratory`: 0 zonas (100% causalidad verificada).
  - `corridor_events`: 3,325,972 eventos de canal/corredor.
  - `session_inventory`: 3,439 sesiones CME.
- **Diccionario de Features:** 18 features formales declaradas con linaje y trazabilidad (`FEATURE_DICTIONARY.json`).

---

## 5. Censo Descriptivo Autónomo

- **Resultados:** `TARGET_FREE_CENSUS.json`, `TARGET_FREE_CENSUS.md` y `TARGET_FREE_ANOMALIES.json`.
- **Anomalías Críticas:** 0 anomalías de inversión temporal o lookahead.
- **Simetría Microestructural:** BULL 49.9% vs BEAR 50.1%.
- **Espesor de Zonas:** Mediana de 0.0 ticks en divisas (libro ultra-denso) hasta 4-12 ticks en NQ/MNQ.
- **Espesor de Corredores:** Mediana de 32 ticks entre murallas activas sucesivas.
- **Vocabulario Seguro:** Ningún término prohibido (*alpha*, *edge confirmado*, *rentabilidad*, *estrategia ganadora*) fue empleado.

---

## 6. Registro Autónomo de Hipótesis

- **Total:** 80 hipótesis no redundantes formalizadas en `HYPOTHESIS_REGISTRY.jsonl` y `HYPOTHESIS_BACKLOG.md`.
- **Familias Cubiertas:** 20 familias científicas (continuación, reversión, rechazo, ruptura, traversing de corredores, pared opuesta, edad, consumo, densidad, first touch, retoques, conflicto de indicadores, confluencia, régimen, horario, persistencia multisesión, interacción entre escalas, transferencia entre activos, estabilidad de parámetros, controles y placebos).
- **Ranking Target-Free:** Ponderación determinista por ganancia informativa esperada, cobertura de activos y coste computacional.
- **Grafo de Dependencias:** `HYPOTHESIS_DEPENDENCY_GRAPH.json`.
- **Estado Inicial:** Todas en `PROPOSED_TARGET_FREE`. Cero hipótesis promovidas prematuramente.

---

## 7. Scaffold del Orquestador y Pruebas Unitarias

- **Módulo:** `edgelab/edge_factory/orchestrator.py` con DAG topológico, detección de ciclos, control de presupuesto (`ResourceBudget`) y reanudación atómica por checkpoint.
- **Pruebas:** 14 pruebas unitarias pasando (`test_edge_factory_schemas.py` y `test_edge_factory_orchestrator.py`).

---

## 8. Decisiones que Requieren a Nicolas

1. **Custodia de NQ 09-26:** Confirmar si se recorta un nuevo archivo parquet fuente desde NT8 para este contrato o si se conserva formalmente excluido.
2. **Aprobación de Prerregistro:** Revisar el top 10 del backlog de hipótesis para autorizar formalmente el primer paquete de experimentos sobre el train set.
3. **Apertura de Outcomes:** Confirmar el momento oportuno para implementar el motor de cálculo de excursiones causales una vez congelado el prerregistro.
