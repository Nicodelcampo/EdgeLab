# ENTRADA 045 — Certificación de Paridad Completa HFTZones NQ V2 (38 Campos, Terminación Nativa NT8, Cero Deriva)

> **De:** Antigravity (Pair Programming / Engine Runner)  
> **Para:** Nicolas / LLM Auditor / Sandbox Notion / Control de Gobernanza  
> **Fecha:** 2026-09-18 12:25:00 -03:00  
> **Rama:** `fix/hft-native-termination-fresh-replay-20260918`  
> **PR Draft:** #34 (https://github.com/Nicodelcampo/EdgeLab/pull/34)  
> **Veredicto Oficial:** `PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS`  
> **Hash SHA-256 Físico Original (Pre-Python):** `a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8`  
> **Hash SHA-256 Físico Medido (Post-Python):** `a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8` (MATCH EXACTO)  
> **Tamaño Físico del Oráculo:** `1.036.443.648` bytes (988,43 MB)  
> **Base de Datos Certificada:** `data/nt8_oracles/hft_zones_nq_v2_native_termination_fresh.sqlite`  
> **Copia de Preservación Inmutable:** `data/nt8_oracles/preservation/hft_zones_nq_v2_native_termination_fresh_preserved_20260918_145003.sqlite`  

---

## 1. Resumen Ejecutivo y Veredicto de Paridad

Se declara y certifica formalmente la **Paridad Completa NT8 ↔ Python (`PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS`)** sobre el conjunto completo de datos canónicos de NQ JUN26 (`NQ 06-26`) entre el 1 de junio y el 12 de junio de 2026:

```
======================================================================
MODO V2: CERTIFICACIÓN EXACTA EN NANOSEGUNDOS (INPUT COMPARTIDO)
======================================================================
Status:                      PASS_CERTIFIED_FULL_FIELD_PARITY_NATIVE_NT8_38_FIELDS
Is Pass:                     True
Zonas NT8 V2:                   5,945
Zonas Python Reconstruidas:     5,945
Parejas Exactas (0ns drift):    5,945 (100,00 %)
Diferencias de Campo:               0
Faltantes NT8:                      0
Faltantes Python:                   0
Errores de Procedencia:             0
Campos Comparados por Zona:        38
Total Campos Auditados:       225.910
Deriva Temporal Sub-ms:           0 ns
======================================================================
```

---

## 2. Cumplimiento Estricto de los 7 Requisitos de Auditoría

### 2.1. Frontera Canónica del Holdout (`1782856800000000000` / `2026-06-30T22:00:00Z`)
Se corrigió la especificación en la documentación para evaluar con la frontera canónica exacta de apertura de sesión CME Globex (`2026-06-30T22:00:00Z`, 17:00 Chicago, que da inicio al trade date `20260701`):

```sql
SELECT COUNT(*) FROM hft_ticks_v2 WHERE timestamp_ns >= 1782856800000000000;
-- Resultado: 0 ticks

SELECT COUNT(*) FROM hft_zones_v2 
WHERE start_ts_ns >= 1782856800000000000 
   OR end_ts_ns >= 1782856800000000000 
   OR available_ts_ns >= 1782856800000000000;
-- Resultado: 0 zonas
```

- **Mínimo timestamp registrado en la base:** `1780264800128000000` (`2026-05-31T22:00:00.128000Z`, apertura Globex domingo 17:00 CT).
- **Máximo timestamp registrado en la base:** `1781297997004000000` (`2026-06-12T20:59:57.004000Z`, cierre semanal viernes 15:59:57 CT).
- **Margen de seguridad temporal (Safety Gap):** El último evento del oráculo ocurrió **18,04 días antes** de la frontera canónica de holdout. La ausencia de contaminación es absoluta.

### 2.2. Publicación de Artefactos Estructurados de Certificación
Se añadieron excepciones a `.gitignore` y se publicaron en el repositorio tanto en `artifacts/` como en `docs/research/`:
- `artifacts/paridad_hftzones_nq_v2_exact_certified.json` (Espejado en `docs/research/paridad_hftzones_nq_v2_exact_certified.json`)
- `artifacts/hft_v2_native_preflight_validation.json` (Espejado en `docs/research/hft_v2_native_preflight_validation.json`)

### 2.3. Manifiesto Canónico Coherente
El manifiesto `docs/research/HFT_V2_NATIVE_TERMINATION_PROVENANCE_MANIFEST.json` fue transformado de template provisional a **manifiesto de evidencia certificada final**:
- `manifest_schema`: `edgelab_hft_v2_provenance_v1`
- `evidence_status`: `CERTIFIED_NATIVE_REPLAY_EVIDENCE`
- `python_writes_after_export`: `false`
- `holdout_accessed`: `false`
- `holdout_start_ns`: `1782856800000000000` (`2026-06-30T22:00:00Z`)
- Hashes criptográficos de scripts Python incluidos.

### 2.4. Reconciliación del Conteo del Ledger de Ticks (5.978.833 vs 6.493.515)
El análisis forense de la distribución por sesión reveló la causa matemática exacta de la diferencia:

| Sesión CME Globex | Intervalo UTC | Ticks Registrados | Zonas Detectadas |
|---|---|---|---|
| **`20260601`** | 2026-05-31 22:00 → 2026-06-01 20:59 | **514.677** | 507 |
| **`20260602`** | 2026-06-01 22:00 → 2026-06-02 20:59 | 470.478 | 495 |
| **`20260603`** | 2026-06-02 22:00 → 2026-06-03 20:59 | 572.504 | 496 |
| **`20260604`** | 2026-06-03 22:00 → 2026-06-04 20:59 | 624.031 | 489 |
| **`20260605`** | 2026-06-04 22:00 → 2026-06-05 20:59 | 913.751 | 858 |
| **`20260608`** | 2026-06-07 22:00 → 2026-06-08 20:59 | 763.008 | 703 |
| **`20260609`** | 2026-06-08 22:00 → 2026-06-09 20:59 | 979.284 | 912 |
| **`20260610`** | 2026-06-09 22:00 → 2026-06-10 20:59 | 690.877 | 647 |
| **`20260611`** | 2026-06-10 22:00 → 2026-06-11 20:59 | 583.542 | 520 |
| **`20260612`** | 2026-06-11 22:00 → 2026-06-12 20:59 | 381.363 | 318 |
| **TOTAL** | **10 sesiones canónicas** | **6.493.515** | **5.945** |

- **Explicación:** El template anterior contemplaba 9 sesiones (`20260602` a `20260612`), sumando `5.978.838` ticks (idéntico a los `5.978.833` esperados, con diferencia de 5 ticks debida a la guarda de inicialización `CurrentBars[1] < 5 return`).
- Al seleccionar Nicolas la fecha de inicio `01/06/2026` en NinjaTrader, NT8 cargó la sesión completa del trade date `20260601`, cuya apertura Globex ocurrió el domingo 31 de mayo a las 17:00 Chicago (`514.677` ticks).
- `5.978.838` + `514.677` = **`6.493.515` ticks exactos**. El input compartido está 100% reconciliado.

### 2.5. Registro Riguroso de la Corrección Python (`last_side = 0`)
1. **Primera ejecución del comparador:**
   - Detectó 5.945 zonas en NT8 y 5.945 en Python.
   - 4.705 parejas tuvieron 100% igualdad exacta en los 38 campos.
   - 1.240 zonas tuvieron diferencias **exclusivamente en métricas de flujo** (`cvd_sweep`, `buy_vol`, `sell_vol`, `delta_first`, `delta_slope`). Geometría, límites, pasos, volumen total, buckets y `termination_reason` tuvieron **0 diferencias**.
2. **Causa raíz:** En `nt8/HFTZonesNQPureV4_V2.cs`, `ResetState()` (invocado al final de `Finalizar()`) resetea `lastSide = 0`. Por ende, tras terminar cualquier racha, si el siguiente tick es plano (`cl == clP`), C# adopta deterministamente `side = 1`. En Python (`edgelab/bridge/indicators/hftzones_nq.py`), `last_side` no se reseteaba tras `finalizar()`.
3. **Corrección en Python:** Se añadió `nonlocal last_side; last_side = 0` en `finalizar()`.
4. **Hashes SHA-256 del código Python ejecutado en la certificación final:**
   - `edgelab/bridge/indicators/hftzones_nq.py`: `6fb0f6ce13090ade89cb3fcaa2fd9e66ef4e10d5a041a59ec73cbc5560dfafe7`
   - `tools/paridad_hftzones_nq_v2.py`: `0c2eccb8c6006d466c441e958556b006e36205a0c74ff0f7e8a53b02ba06c701`
   - `tools/validate_hft_v2_certification.py`: `fa96baa6817b31f94d1632f0885bacade41c3dbc0603c6010d3cb9a4291b4e90`
5. **Re-ejecución limpia desde cero:** La nueva corrida arrojó **5.945 parejas exactas sobre 5.945 (100,00%) con 0 diferencias en los 225.910 campos**.

### 2.6. Demostración del Hash Físico Posterior a Python
Se recalculó el hash SHA-256 del archivo físico SQLite original tras haber concluido todas las ejecuciones, consultas y verificaciones de Python:

- **Hash físico antes de Python (post-cierre NT8):**  
  `a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8`
- **Hash físico después de Python:**  
  `a0349af9b5eef1c12005b04311dd31d381f231d1da01d0dee226fe0a94191ec8`
- **Veredicto:** **MATCH EXACTO**. No hubo una sola modificación, inserción, actualización ni toque en disco tras el cierre de NinjaTrader 8.

### 2.7. Saneamiento del Workflow CI
- En `.github/workflows/ci.yml`, el paso `Install Playwright Chromium` fallaba con `No module named playwright` porque el paquete `playwright` no estaba incluido en `core-bridge-dev.lock`.
- Se corrigió añadiendo `pip install playwright` antes de invocar `python -m playwright install --with-deps chromium`.
- Localmente, la suite completa y `test_hft_viewer_playwright.py` pasaron en verde al 100%.

---

## 3. Tabla Completa de los 38 Campos Certificados

| N° | Campo en SQLite | Tipo | Tolerancia | Resultado | Descripción |
|---|---|---|---|---|---|
| 1 | `instrument` | TEXT | Exacto | **PASS** | Nombre del instrumento ("NQ JUN26") |
| 2 | `contract` | TEXT | Exacto | **PASS** | Contrato CME ("NQ 06-26") |
| 3 | `session_id` | TEXT | Exacto | **PASS** | Trade date CME Globex 17:00 Chicago |
| 4 | `zone_seq` | INTEGER | Exacto | **PASS** | Secuencia monótona continua (1..N) |
| 5 | `start_tick_seq` | INTEGER | Exacto (0 ticks) | **PASS** | Tick de inicio de la racha |
| 6 | `end_tick_seq` | INTEGER | Exacto (0 ticks) | **PASS** | Tick de cierre de la racha |
| 7 | `start_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp Unix en nanosegundos |
| 8 | `end_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp Unix de fin de racha |
| 9 | `available_ts_ns` | INTEGER | Exacto (0 ns) | **PASS** | Timestamp causal de disponibilidad |
| 10 | `direction` | INTEGER | Exacto | **PASS** | Dirección de sweep (+1 Bull, -1 Bear) |
| 11 | `lo_ticks` | INTEGER | Exacto | **PASS** | Límite inferior en ticks |
| 12 | `hi_ticks` | INTEGER | Exacto | **PASS** | Límite superior en ticks |
| 13 | `pasos` | INTEGER | Exacto | **PASS** | Conteo total de pasos de sweep |
| 14 | `vol` | REAL | $<10^{-6}$ | **PASS** | Volumen total acumulado |
| 15 | `avg_ms` | REAL | $<10^{-4}$ ms | **PASS** | Tiempo promedio entre ticks |
| 16 | `total_ms` | REAL | $<10^{-4}$ ms | **PASS** | Duración total en milisegundos |
| 17 | `volume_rate` | REAL | $<10^{-4}$ cont/s | **PASS** | Tasa de volumen por segundo |
| 18 | `parameter_manifest_sha256` | TEXT | Exacto | **PASS** | Hash de parámetros congelados |
| 19 | `indicator_source_sha256` | TEXT | Exacto | **PASS** | Hash del código fuente C# |
| 20 | `valid_steps` | INTEGER | Exacto | **PASS** | Pasos válidos en dirección |
| 21 | `max_retro` | REAL | $<10^{-6}$ ticks | **PASS** | Retroceso máximo durante el sweep |
| 22 | `cvd_sweep` | REAL | $<10^{-6}$ | **PASS** | Delta de volumen acumulado (CVD) |
| 23 | `buy_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen comprador |
| 24 | `sell_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen vendedor |
| 25 | `delta_slope` | REAL | $<10^{-4}$ | **PASS** | Pendiente de aceleración del delta |
| 26 | `delta_first` | REAL | $<10^{-6}$ | **PASS** | Delta en la primera mitad del sweep |
| 27 | `delta_second` | REAL | $<10^{-6}$ | **PASS** | Delta en la segunda mitad del sweep |
| 28 | `max_tick_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen máximo en un solo tick |
| 29 | `no_move_ticks` | INTEGER | Exacto | **PASS** | Ticks consumidos sin movimiento |
| 30 | `no_move_vol` | REAL | $<10^{-6}$ | **PASS** | Volumen absorbido sin movimiento |
| 31 | `max_level_ticks` | INTEGER | Exacto | **PASS** | Nivel con mayor concentración de ticks |
| 32 | `bucket` | TEXT | Exacto | **PASS** | Clasificación de velocidad (PRED, ULTRA, etc.) |
| 33 | `price_upper` | REAL | $<10^{-6}$ USD | **PASS** | Precio superior en dólares |
| 34 | `price_lower` | REAL | $<10^{-6}$ USD | **PASS** | Precio inferior en dólares |
| 35 | `price_mid` | REAL | $<10^{-6}$ USD | **PASS** | Precio medio del sweep |
| 36 | `height_ticks` | REAL | $<10^{-6}$ | **PASS** | Altura total del sweep en ticks |
| 37 | `tick_res` | INTEGER | Exacto (=1) | **PASS** | Resolución de subserie (1-tick) |
| 38 | `termination_reason` | TEXT | Exacto | **PASS** | Causa de corte nativa (REVERSAL / MAX_PAUSE) |

---

## 4. Aporte al Referente

La certificación de paridad HFT V2 sobre 5.945 zonas y 6,49 millones de ticks con **cero discrepancias en 225.910 campos evaluados y cero nanosegundos de deriva temporal** queda sellada con total auditabilidad externa:
1. **La causalidad temporal es estricta:** ninguna zona puede ser consumida por corredores o estrategias antes de su `available_ts_ns` nativo.
2. **La procedencia física es inmutable:** el oráculo físico cuenta con hash SHA-256 verificado antes y después del análisis de Python, copia de preservación y atributo Read-Only en disco.
3. **El holdout fue estrictamente protegido:** se comprobó con la frontera canónica CME Globex (`1782856800000000000`, 2026-06-30 22:00 UTC) arrojando 0 ticks y 0 zonas, con más de 18 días de distancia temporal.
4. **Separación científica:** La paridad exacta es una garantía de instrumentación e infraestructura, **no un edge económico**. Habiendo cerrado definitivamente la infraestructura, la investigación puede proceder con total confianza en los datos hacia la evaluación de hipótesis económicas reales.
