# EdgeLab — Auditoría de Paridad Lógica del Store Analítico Target-Free

**Fecha:** `2026-09-19T14:55:56.116395+00:00`  
**Dataset Analizado:** `nicolasbuttaro/edgelab-edge-factory-target-free-audited`  
**Referencia Local:** `E:\EdgeLab-edgefactory\artifacts\edge_factory_audit`  
**Estado Dictaminado:** `ANALYTICAL_STORE_PARTIAL_REQUIRES_DERIVATION`  
**Entregable JSON:** [`artifacts/audit/EDGELAB_ANALYTICAL_STORE_PARITY.json`](file:///E:/EdgeLab-edgefactory/artifacts/audit/EDGELAB_ANALYTICAL_STORE_PARITY.json)  

---

## 1. Declaración Obligatoria de Semántica de Cobertura

En cumplimiento estricto del documento de alcance autoritativo (`docs/research/25T_BUNDLE_SCOPE_AND_KAGGLE_CUSTODY_20260919.md`):

```yaml
coverage_mode: PARTIAL_CONTRACT_MONTH_SLICES
is_complete_continuous_series: false
includes_all_contracts: false
has_certified_roll_methodology: false
eligible_for_continuous_backtest: false
missing_periods_mean_no_data: false
holdout_boundary_ns: 1782856800000000000
holdout_boundary_utc: 2026-06-30T22:00:00Z
```

Los 147 contract-month slices auditados **no representan un histórico continuo completo ni libre de huecos**, sino muestras de alta resolución temporal por instrumento, contrato y mes calendario. La ausencia de un mes no certifica ausencia de mercado ni de zonas.

---

## 2. Resumen de Comparación Lógica: Store vs. 147 Bundles

| Métrica / Dimensión | Bundles Visor (147 Slices) | Feature Store Target-Free Audited | Estado de Paridad |
| :--- | :--- | :--- | :--- |
| **Zonas HFT Totales** | **3,328,710** | **3,328,710** | **100.0% EXACT MATCH** |
| **Slices con Zonas Coincidentes** | 147 / 147 | 147 / 147 | **100.0% PASS (147/147)** |
| **Discrepancias de Zonas** | 0 | 0 | **0 discrepancias** |
| **Sesiones Inventariadas** | 3,439 sesiones | 3,439 sesiones | **100.0% EXACT MATCH** |
| **Velas 25 Ticks (`bar_series`)** | **40,380,402** | No materializadas en este dataset | **REQUIRES_ON_DEMAND_DERIVATION** |
| **Violaciones de Holdout** | 0 filas | 0 filas | **0 violaciones** (`max_ts < 1782856800000000000`) |
| **Fills Sintéticos** | Hallucinados en bundles viejos | **PURGADOS** (`fill_status: NO_EXECUTABLE_FILL_AVAILABLE`) | **CORREGIDO Y AUDITADO** |
| **Pseudo-Corredores** | Pairing N-1 estático | **EXCLUIDOS** (`BLOCKED_PENDING_CANONICAL_CORRIDOR_ENGINE`) | **CORREGIDO Y AUDITADO** |

---

## 3. Hallazgos Críticos de Arquitectura

1. **Las Zonas HFT están 100% Cubiertas en Parquet ZSTD:**
   El dataset remoto `edgelab-edge-factory-target-free-audited` ya contiene las **3,328,710 zonas HFT** estructuradas en 144 particiones Parquet por instrumento y contrato, con:
   - timestamps causales (`origin_ts` y `signal_available_ts`);
   - tick sizes exactos de CME;
   - métricas de volumen (`total_vol`, `vol_rate`);
   - métricas temporales (`formation_duration_ms`, `causal_delay_ms`);
   - provenance algorítmica (`engine_version`, `indicator_version`, `source_sha256`).
   
   Por ende, **para el análisis de zonas HFT, no se requiere subir ningún bundle adicional ni duplicar este store**.

2. **Las Barras 25t (`bar_series`) Pertenecen a Tier 1:**
   Las 40,380,402 barras de 25 ticks están presentes en el inventario local de los bundles, pero no fueron particionadas como Parquet en `target-free-audited`.
   - Según la arquitectura de custodia de Nicolas:
     - **Tier 0 (Ticks Crudos):** Es la fuente primaria de verdad.
     - **Tier 1 (Barras 25t):** Son barras determinísticamente reconstruibles desde los ticks crudos de Tier 0.
     - **Tier 2 (Features Target-Free):** Zonas HFT auditadas (ya en Kaggle).
     - **Tier 3 (Viewer Artifacts):** JSON/JS para browser (no se migran).
   - Por lo tanto, no se debe subir el JSON del visor. Las barras 25t pueden materializarse como Parquet ZSTD bajo demanda a partir de los ticks crudos canónicos de Tier 0.

---

## 4. Dictamen Final

```
======================================================================
ESTADO FINAL: ANALYTICAL_STORE_PARTIAL_REQUIRES_DERIVATION
======================================================================
1. Paridad de Zonas: 100% IDÉNTICA (3,328,710 zonas). Cero discrepancias.
2. Formato Analítico: Parquet ZSTD columnar listo para DuckDB / Polars / PyArrow.
3. Decisión Operativa: NO DUPLICAR LA SUBIDA DE ZONAS.
4. Política de Barras 25t: Derivación determinista bajo demanda desde Tier 0.
======================================================================
```
