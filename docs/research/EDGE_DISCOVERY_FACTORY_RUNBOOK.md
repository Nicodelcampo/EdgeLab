# Edge Discovery Factory — Runbook Operativo

> **Referencia:** `docs/research/EDGE_DISCOVERY_FACTORY_SPEC.md`  
> **Entorno:** `E:\EdgeLab-edgefactory`  
> **Datos de Entrada:** `E:\EdgeLab-multiasset\viewer\nt8_bridge\bundles` (Read-Only)  
> **Fecha:** 2026-09-19  

---

## 1. Modos de Ejecución

El pipeline de Edge Discovery Factory está diseñado para operar en fases independientes y reanudables.

### 1.1 Inventario de Schemas y Capacidades
Inspecciona bundles existentes y construye la matriz de disponibilidad causal vs exploratoria:
```powershell
python tools/audit_edge_factory_schemas.py
```
Outputs:
- `artifacts/edge_factory/schema_inventory.json`
- `artifacts/edge_factory/schema_coverage.md`
- `artifacts/edge_factory/indicator_capabilities.json`

### 1.2 Extracción del Feature Store Target-Free
Convierte bundles JSON/JS a almacenamiento columnar Parquet particionado:
```powershell
python tools/build_edge_factory_target_free_store.py --bundles-dir E:\EdgeLab-multiasset\viewer\nt8_bridge\bundles
```
Reglas:
- Lectura estrictamente de sólo lectura.
- Escritura atómica a `artifacts/edge_factory/zone_events/` y `corridor_events/`.
- Segmentación obligatoria de zonas `ORIGIN_FALLBACK_UNVERIFIED` hacia `zone_events_exploratory/`.

### 1.3 Censo Descriptivo Target-Free
Calcula estadísticas de población, duraciones, espesores y densidades sin outcomes:
```powershell
python tools/run_edge_factory_census.py
```
Outputs:
- `artifacts/edge_factory/TARGET_FREE_CENSUS.json`
- `artifacts/edge_factory/TARGET_FREE_CENSUS.md`
- `artifacts/edge_factory/TARGET_FREE_ANOMALIES.json`

### 1.4 Generación y Registro de Hipótesis
Formula el backlog creativo de hipótesis basado en el censo y las capacidades de los indicadores:
```powershell
python tools/generate_hypothesis_backlog.py
```
Outputs:
- `artifacts/edge_factory/HYPOTHESIS_REGISTRY.jsonl`
- `artifacts/edge_factory/HYPOTHESIS_BACKLOG.md`
- `artifacts/edge_factory/HYPOTHESIS_DEPENDENCY_GRAPH.json`

---

## 2. Guardrails y Verificaciones Operativas

Antes de iniciar cualquier proceso:
1. Confirmar memoria libre en el sistema $> 4$ GB.
2. Confirmar que ningún proceso escribe sobre el directorio de bundles de entrada.
3. Verificar la variable de entorno `OMP_NUM_THREADS=1` y equivalentes.
4. Asegurar que `DEFAULT_HOLDOUT_NS = 1782856800000000000` está activo en todos los extractores.

---

## 3. Procedimiento de Recuperación ante Fallos

Si un proceso es interrumpido o excede el presupuesto de memoria:
1. El archivo parcial `*.tmp` es ignorado o eliminado automáticamente por el runner.
2. El checkpoint conserva el último contrato o mes completamente auditado.
3. Reanudar con el flag `--resume`.
