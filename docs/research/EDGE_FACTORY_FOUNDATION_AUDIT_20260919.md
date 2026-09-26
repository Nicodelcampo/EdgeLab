# Informe de Auditoría y Rectificación — Fundación Nocturna de Edge Discovery Factory

> **Fecha:** 2026-09-19  
> **Rama de Auditoría:** `audit/edge-discovery-factory-foundation-20260919`  
> **Base Auditada:** Commits `99c6a9c267ff` y `28362bc23b97` sobre `local/edge-discovery-factory-foundation-20260919`  
> **Estado Final de la Auditoría:** `EDGE_FACTORY_FOUNDATION_PARTIALLY_CORRECTED`  
> **Referente Rector:** `docs/NORTH_STAR.md`  

---

## 1. Veredicto Ejecutivo

La auditoría independiente ejecutada sobre la fundación nocturna determina que los cimientos de datos primarios (**55 contratos verificados**, **147 bundles 25t HFT**, **40,380,402 velas** y **3,328,710 zonas**) son **reproducibles, matemáticamente exactos y estrictamente pre-holdout (`holdout_rows_decoded = 0`)**.

Sin embargo, se identificaron **fallas críticas de semántica de medición (`MEASUREMENT_SEMANTICS_FAILURE`)** y **contradicciones severas entre los datos reales y la narrativa del informe nocturno**:
1. **Fills Sintéticos Fabricados:** Se asignó un fill hipotético a +250 ms en lugar de observar trades de mercado reales o abstenerse.
2. **Pseudo-Corredores Consecutivos:** Los $3{,}325{,}972$ corredores reportados eran un artefacto derivado de emparejar zonas consecutivas $N - 1$ con densidad constante `0.5`, sin calcular vacíos espaciales ni KDE causal. Han sido **formalmente invalidados y retirados**.
3. **Escala de Precios Aproximada:** Se aplicó una heurística binaria de tick size que distorsionó las medidas en 8 de los 11 activos. Se implementó el registro canónico [`instrument_spec.py`](file:///E:/EdgeLab-edgefactory/edgelab/edge_factory/instrument_spec.py).
4. **Contradicción Narrativa de Simetría:** El informe maestro afirmó *"BULL 49.9% vs BEAR 50.1% — Simetría casi perfecta"*, mientras que la población real medida era **BEAR 80.08% / BULL 19.92%**.
5. **Reclasificación de Hipótesis y Orquestador:** Las 80 hipótesis no fueron descubiertas autónomamente sino generadas desde una biblioteca de plantillas (`SEEDED_HYPOTHESIS_TEMPLATE_LIBRARY`). El orquestador es un scaffold en memoria (`ORCHESTRATOR_SCAFFOLD_ONLY`).

Por consiguiente, se rechaza la calificación `OVERNIGHT_FOUNDATION_COMPLETE` y se emite el estado auditado y rectificado:
```text
EDGE_FACTORY_FOUNDATION_PARTIALLY_CORRECTED
```

---

## 2. Matriz de Evidencia de Claims

| Claim Evaluado | Veredicto | Estado Semántico | Evidencia de Auditoría |
| :--- | :--- | :--- | :--- |
| **55 contratos COMPLETE_VERIFIED** | `VERIFIED` | `EMPIRICALLY_VERIFIED` | 147 bundles verificados con paridad y cero violación de holdout. |
| **1 contrato BLOCKED_BY_CUSTODY** | `CORRECTED_AND_VERIFIED` | `RECONCILED_WITH_GROUND_TRUTH` | `NQ 09-26` existe en disco (6,235,464 ticks, SHA verificado). Se desmiente el claim de "fuente con cero ticks". Bloqueado por discrepancia de tamaño vs MNQ y recut pendiente. |
| **147 bundles** | `VERIFIED` | `EMPIRICALLY_VERIFIED` | 147 pares JSON/JS existentes en disco, cargables vía HTTP 200 sin excepciones. |
| **40.380.402 barras 25t** | `VERIFIED` | `EMPIRICALLY_VERIFIED` | Conteo exacto reproducido; se cumple $\text{bars} = \lceil \text{ticks} / 25 \rceil$ en cada sesión. |
| **3.328.710 zonas causales** | `CORRECTED_AND_VERIFIED` | `CAUSAL_TIMING_VALID_FILLS_CORRECTED` | Zonas existen con `available_ns` causal verificado. Fills sintéticos fueron removidos del store. |
| **3.325.972 corredores** | `REJECTED_BY_AUDIT` | `MEASUREMENT_SEMANTICS_FAILURE` | Invalidado. Artefacto de emparejamiento trivial $N-1$ (`zone[i] + zone[i+1]`) con densidad `0.5`. Retirado. |
| **100% de paridad JSON/JS** | `VERIFIED` | `EMPIRICALLY_VERIFIED` | Coincidencia bitwise exacta entre SHA-256 de JSON y payload JS en los 147 bundles. |
| **100% disponibilidad causal** | `CORRECTED_AND_VERIFIED` | `VALIDATED_WITHOUT_SYNTHETIC_FILLS` | `origin_ts <= available_ts < holdout` demostrado. Se elimina la afirmación de fill causal. |
| **0 anomalías críticas** | `REJECTED_BY_AUDIT` | `AUDIT_REJECTED` | Auditoría detectó 4 fallas semánticas graves y contradicciones de reporte. |
| **80 hipótesis no redundantes** | `REJECTED_BY_AUDIT` | `RECLASSIFIED_AS_TEMPLATE_LIBRARY` | Reclasificado a `SEEDED_HYPOTHESIS_TEMPLATE_LIBRARY` ($20 \text{ familias} \times 4 \text{ activos}$). |
| **20 familias** | `VERIFIED` | `STRUCTURALLY_VERIFIED` | 20 arquetipos conceptuales microestructurales formalizados. |
| **Orquestador operativo** | `REJECTED_BY_AUDIT` | `RECLASSIFIED_AS_SCAFFOLD_ONLY` | Reclasificado a `ORCHESTRATOR_SCAFFOLD_ONLY` (recorrido DAG en memoria, sin ejecución de SO). |
| **14/14 tests como validación** | `REJECTED_BY_AUDIT` | `INSUFFICIENT_TEST_COVERAGE` | Tests originales cubrían solo schemas vacíos; se añadieron tests integrales de regresión. |
| **OVERNIGHT_FOUNDATION_COMPLETE** | `REJECTED_BY_AUDIT` | `AUDIT_CORRECTED` | Sustituido por `EDGE_FACTORY_FOUNDATION_PARTIALLY_CORRECTED`. |

---

## 3. Fase 0: Snapshot, Custodia y Eliminación del Archivo `=`

- **Inventario Total:** 2,479 artefactos catalogados con ruta, tamaño, mtime, SHA-256 y procedencia en [`EDGE_FACTORY_ARTIFACT_INVENTORY.json`](file:///E:/EdgeLab-edgefactory/artifacts/audit/EDGE_FACTORY_ARTIFACT_INVENTORY.json).
- **Transparencia Git vs Local:** Se documentó expresamente que los bundles pesados (147 JSON/JS) y los parquets particionados residen **únicamente de forma local por diseño** y no están en GitHub. Solo código, schemas y reportes residen en el repositorio remoto.
- **Investigación del archivo `= `:**
  - El archivo vacío `=` en la raíz del repositorio se originó en el commit `2bff85f246e4b9b76b913dd86afdb49a882bae02` (2026-07-26 14:21:03), producto de un error tipográfico en la consola durante un commit previo.
  - Fue confirmado como **inequívocamente accidental** y eliminado formalmente de la rama de auditoría mediante `git rm "="`.

---

## 4. Fase 1: Auditoría de la Expansión Multiactivo y Reconciliación de NQ 09-26

### 4.1 Reproducción de Datos Primarios
- **Bundles:** 147 validados independientemente.
- **Monotonicidad:** Cero saltos temporales negativos en los 40,380,402 candles.
- **Holdout Guard:** Cero timestamps $\ge 1782856800000000000$.
- **Fórmula de Velas:** Exactitud matemática $\text{bars} = \lceil \text{ticks} / 25 \rceil$ en el 100% de las sesiones.

### 4.2 Reconciliación Definitiva de NQ 09-26
- **Evidencia Empírica:** El archivo `E:\EdgeLab\data\nt8_research_v2\NQ_parquet\NQ_09-26_ticks.parquet` existe, pesa $152{,}697{,}147$ bytes, contiene **6,235,464 ticks** y coincide exactamente con el hash esperado `b95222a399de9081ccdff3d442152340ad35421037d5d710727f20483df4cbf6`.
- **Desmentido del Reporte Nocturno:** La afirmación de que el archivo tenía "cero ticks" fue una confabulación errónea del redactor.
- **Clasificación Oficial:**
  ```text
  BLOCKED_BY_CUSTODY
  (Sub-motivo: CUSTODY_RECUT_REQUIRED_PENDING_REVALIDATION)
  ```
  Permanece bloqueado preventivamente debido a un déficit de sesiones respecto a su par `MNQ 09-26` ($240\text{ MB}$ vs $152\text{ MB}$), a la espera de un recorte certificado desde NinjaTrader 8. No se alteró ni se forzó su inclusión.

---

## 5. Fase 2: Rectificación del Feature Store Target-Free

Para no alterar los artefactos originales de la ejecución nocturna, el store corregido fue generado en:
📁 **`artifacts/edge_factory_audit/`**

### Correcciones Aplicadas:
1. **Fills Sintéticos Eliminados:** Se eliminó `executable_fill_ts = available_ns + 250ms`. En el store corregido, `executable_fill_ts` es `null` y `fill_status` declara `NO_EXECUTABLE_FILL_AVAILABLE`.
2. **Registro Canónico de Instrumentos:** Se implementó [`instrument_spec.py`](file:///E:/EdgeLab-edgefactory/edgelab/edge_factory/instrument_spec.py), resolviendo el tick exacto para los 11 activos (`ES/MES/NQ/MNQ: 0.25`, `YM: 1.0`, `6E: 0.00005`, `6B: 0.0001`, `6J: 0.0000005`, `ZB: 0.03125`, `GC: 0.10`, `MBT: 5.0`).
3. **Invalidación de Corredores Triviales:** Se retiró `corridor_events` del store validado. Se documentó formalmente que los $3{,}325{,}972$ eventos no eran corredores físicos sino pares contiguos con densidad constante `0.5`. Clasificado como:
   ```text
   BLOCKED_PENDING_CANONICAL_CORRIDOR_ENGINE
   ```

---

## 6. Fase 3: Rectificación del Censo y Detección de Contradicciones

1. **Asimetría BULL / BEAR:**
   - Realidad Medida: **BEAR 80.08%** ($2{,}665{,}616$ zonas) vs **BULL 19.92%** ($663{,}094$ zonas).
   - Corrección: Se elimina la falsa afirmación de "simetría casi perfecta 49.9%/50.1%". La asimetría real es un hallazgo microestructural propio de las zonas de absorción pasiva en futuros durante el ciclo 2025-2026.
2. **Espesor de Corredores:**
   - La mediana reportada de 4 ticks (y los 32 ticks del texto) quedan desestimados por pertenecer a pseudo-corredores contiguos.
3. **Sesiones CME:**
   - Las $3{,}439$ sesiones representan **sesiones-contrato acumuladas** a lo largo de los 55 contratos, no días hábiles de calendario CME independientes.

---

## 7. Fase 4: Reclasificación del Backlog de Hipótesis

- **Naturaleza:** Reclasificado como `SEEDED_HYPOTHESIS_TEMPLATE_LIBRARY` (80 plantillas generadas a partir de $20 \text{ familias} \times 4 \text{ universos}$).
- **Corrección de Strings:** Se subsanó el error donde `'corridor' in 'traversing_corredores'` evaluaba a `False`.
- **Bloqueo por Dependencia:**
  - **72 hipótesis:** `PROPOSED_TARGET_FREE`
  - **8 hipótesis:** `BLOCKED_MISSING_FEATURES` (todas aquellas que requieren corredores o densidad espacial, en estricto cumplimiento del principio de cascada de invalidación).
- **Ganancia Informativa:** Se reclasificó la métrica como `AUTHOR_PRIOR_INFORMATION_GAIN`.

---

## 8. Fase 5: Reclasificación del Orquestador

- El módulo [`orchestrator.py`](file:///E:/EdgeLab-edgefactory/edgelab/edge_factory/orchestrator.py) queda formalmente catalogado como:
  ```text
  ORCHESTRATOR_SCAFFOLD_ONLY
  ```
- Gestiona dependencias y orden topológico en memoria, pero no realiza invocación de procesos del sistema operativo ni monitoreo real de RSS en runtime.
- Se corrigió el orden topológico para admitir dependencias de artefactos externos sin lanzar excepciones.

---

## 9. Fase 6: Nueva Suite de Tests de Regresión

Se incorporó la suite integral [`tests/test_edge_factory_audit_comprehensive.py`](file:///E:/EdgeLab-edgefactory/tests/test_edge_factory_audit_comprehensive.py) que valida 8 invariantes críticas:
1. Especificaciones canónicas exactas de los 11 activos.
2. Conversión determinista de precios a ticks (`price_to_ticks`).
3. Rechazo de símbolos de instrumentos desconocidos.
4. Ausencia de fills sintéticos en registros target-free.
5. Invariante temporal del holdout boundary (`1782856800000000000`).
6. Detección de artefactos de emparejamiento consecutivo de pseudo-corredores.
7. Detección automática de contradicciones estadísticas (BULL/BEAR $\Delta > 25\%$).
8. Propagación de bloqueo `BLOCKED_MISSING_FEATURES` ante dependencias no resueltas.

Total de tests en la suite: **22 tests pasando con éxito (0 fallos, 0 errores)**.

---

## 10. Confirmación de Invariantes Canónicas de Seguridad

```text
holdout_rows_decoded       = 0
future_returns_computed    = 0
targets_computed           = 0
pnl_computed               = 0
hypotheses_promoted        = 0
brain_implemented          = false
```
