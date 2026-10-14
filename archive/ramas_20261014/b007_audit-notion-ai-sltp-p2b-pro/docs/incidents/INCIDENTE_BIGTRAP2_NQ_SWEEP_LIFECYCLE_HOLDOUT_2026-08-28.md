# INCIDENTE: Exposición de Lifecycle y Lectura No Acotada en Sweep BigTrap2 NQ

**Fecha:** 2026-08-28  
**Rama:** `research/bigtrap2-nq-tickframes-sweep-v1-20260828`  
**Identificador:** `INCIDENTE_BIGTRAP2_NQ_SWEEP_LIFECYCLE_HOLDOUT_20260828`  
**Severidad:** `MEDIA / PROCEDIMENTAL` (Afecta validez target-free del sweep retrospectivo; no compromete P&L ni holdout de producción).  
**Estado:** `REMEDIADO_CON_DISEÑO_FAIL_CLOSED_V2`  

---

## 1. Resumen del Incidente

El runner inicial [`tools/sweep_bigtrap2_nq_tickframes.py`](../../tools/sweep_bigtrap2_nq_tickframes.py), diseñado para mapear la sensibilidad de resolución de barra (112 configuraciones) sobre NQ, incurrió en dos violaciones epistemológicas y metodológicas:
1. **Lectura no acotada en memoria:** Invocó `load_canonical_parquet` sin acotar por `start_utc_ns` ni `end_utc_ns`, decodificando ticks de la sesión holdout (`>= 20260701`) en el contrato `NQ 09-26` antes de filtrar barras por máscara booleana en memoria.
2. **Ejecución de Lifecycle y First Touch:** Invocó el kernel completo `run_bigtrap2()`, el cual internamente ejecuta `update_zones()`, computando toques (`touches`), traspasos (`CloseThrough`), expiraciones y recorriendo trayectorias de precios futuros respecto de cada zona creada.
3. **Spec Retrospectiva y Hashes:** La spec `v1` fue emitida con timestamp posterior a la finalización de la corrida y registró hashes no canónicos de los registries.

---

## 2. Reclasificación Contractual del Resultado V1

El artefacto [`docs/research/bigtrap2_nq_tickframes_sweep_result.json`](../research/bigtrap2_nq_tickframes_sweep_result.json) se preserva formalmente como evidencia histórica expuesta bajo la clasificación declarada en [`docs/research/bigtrap2_nq_tickframes_sweep_result_classification.json`](../research/bigtrap2_nq_tickframes_sweep_result_classification.json):

```text
SWEEP_EXECUTION_COMPLETE               = true
CREATION_COUNTS_PUBLISHED              = true
STRICT_TARGET_FREE_EXECUTION           = false
FUTURE_PRICE_PATH_ACCESSED             = true
FIRST_TOUCH_ACCESSED                   = true
PNL_ACCESSED                           = false
HOLDOUT_ROWS_DECODED                   = true
HOLDOUT_FIREWALL_PROVEN                = false
WINNER_SELECTED                        = false
CONFIRMATORY_ELIGIBLE                  = false
EVENT_STORE_BUILD_ELIGIBLE             = false
CLASSIFICATION                         = COMPLETE_RETROSPECTIVE_SWEEP_PUBLICATION_WITH_EXPOSURE
```

---

## 3. Causa Raíz Detallada

### A. Ausencia de Filtro PyArrow a Nivel de Archivo
En el runner v1:
```python
ticks = load_canonical_parquet(pq_path, contract=contract, instrument="NQ")
```
El archivo `NQ_09-26_ticks.parquet` contiene ticks que se extienden dentro del segundo semestre de 2026 (holdout). Al no pasarle la cota superior `max_end_ns = 2026-06-30T22:00:00Z`, PyArrow decodificó todas las filas en el array antes de que el script aplicara `valid_bar_mask = np.isin(ses_ids, valid_sessions)` a nivel de barras.

### B. Invocación de `update_zones()` en el Kernel
El pipeline de `edgelab.bridge.indicators.bigtrap2.run()` contiene un bucle secuencial por barra que llama a:
```python
update_zones(zones, bar_high, bar_low, bar_close, bar_time, bar_idx, params)
```
Esto calcula la vida útil de cada burbuja, verifica intersecciones de precios futuros y marca zonas como tocadas/cerradas. Por ende, la ejecución no fue puramente estática ni *creation-only*.

---

## 4. Medidas de Remediación Implementadas

1. **Creación del Detector Estricto Creation-Only:**
   Implementar [`edgelab/bridge/indicators/bigtrap2_creation_only.py`](../../edgelab/bridge/indicators/bigtrap2_creation_only.py) con paridad matemática 1:1 contra el kernel canónico (`row_price > close` para buyers, `row_price < close` para sellers), que únicamente extrae absorciones en la barra actual y **nunca** evalúa barras posteriores, ni toques, ni estados de salida.
2. **Runner Fail-Closed V2:**
   Implementar [`tools/sweep_bigtrap2_nq_tickframes_v2.py`](../../tools/sweep_bigtrap2_nq_tickframes_v2.py):
   * Acota la lectura PyArrow a `[min_start_ns, max_end_ns)` por sesión CME registrada, con corte tajante en `2026-06-30T22:00:00Z`.
   * Verifica estrictamente el tamaño y SHA-256 de los 5 Parquet de NQ leyendo el diccionario canónico de `contracts` en el input registry (`fail-closed`).
   * Valida spec vinculada, hashes físicos de registries, commit esperado, árbol git limpio y token de autorización en runtime.
   * Graba en un archivo nuevo `docs/research/bigtrap2_nq_tickframes_sweep_v2_result.json` sin sobrescribir el V1 expuesto.
3. **Spec V2 en Draft:**
   Publicar [`specs/bigtrap2_nq_tickframes_sweep_v2.draft.json`](../../specs/bigtrap2_nq_tickframes_sweep_v2.draft.json) con los hashes canónicos de Gate 1A (`f50350ee...` y `2ce11410...`).
4. **Tests Contractuales, Adversariales y CI Dedicado:**
   Incorporar tests que validen paridad 1:1 de creaciones, hashes de registries y CI dedicado en [`.github/workflows/bt2_nq_sweep.yml`](../../.github/workflows/bt2_nq_sweep.yml).

---

## 5. Veredicto y Estado de Autorizaciones

```text
BIGTRAP2_SELECTION_FREEZE_TOKEN_ISSUED = false
BIGTRAP2_RERUN_AUTHORIZED              = false
BIGTRAP2_EVENT_STORE_AUTHORIZED        = false
AVOL_ES_SWEEP_RUN                      = HOLD
```

Aporte al referente: se identifica, aísla y documenta la exposición metodológica de lifecycle y holdout en el sweep retrospectivo V1 de BigTrap2 NQ; se crea la infraestructura creation-only y fail-closed V2 para asegurar una repetición matemáticamente incontestable antes de autorizar cualquier selección.
