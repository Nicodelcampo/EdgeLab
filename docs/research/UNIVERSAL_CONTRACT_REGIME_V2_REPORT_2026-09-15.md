# Informe Integral de Auditoría y Certificación: Régimen Contractual Universal (V2)

- **Fecha:** `2026-09-15`
- **Autor / Auditor:** `Antigravity / EdgeLab Baseline`
- **Rama Git:** `work/universal-contract-regime-v2-20260915`
- **Base Trackeada:** `foundation/f0b-compatibility-probe` (`12af195`)
- **Directorio de Datos Auditado:** `E:\EdgeLab\data\nt8_research_v2`
- **Estado Global:** `AUDITORÍA Y CERTIFICACIÓN V2 COMPLETADAS`

---

## 1. Resumen Ejecutivo

Se auditó de forma exhaustiva y sistemática el universo completo de contratos de futuros pre-holdout disponibles en EdgeLab, abarcando **11 raíces de productos**, **56 archivos parquet** y **1.015.108.799 filas** con un volumen agregado de **1.407.249.709 contratos**.

Se certificó formalmente la capa universal causal de contratos operables bajo el estándar `previous_complete_session_volume_leader_monotonic_v1` (`UNIVERSAL_CONTRACT_REGIME_V2`), garantizando:

1. **Aislamiento Absoluto del Holdout**: Verificación estricta de que $\max(ts\_utc\_ns) < 1782856800000000000$ (2026-06-30T22:00:00Z) en los 56 parquets (`holdout_violation: False`).
2. **Causalidad Estricta ($D-1$)**: La selección del contrato operable en $D$ se realiza previo al inicio de la sesión basada exclusivamente en el volumen de la sesión completa anterior.
3. **Precios Reales sin Distorsión**: Cero back-adjustment y cero ratio-adjustment. Concatenación continua sobre cotizaciones reales negociadas.
4. **Frontera de Estado y Reinicio**: Obligatoriedad de reinicio (`state_reset_flag = True`) en cada cambio de régimen (`RESET_AT_CONTRACT_ROLL`).
5. **Separación Conceptual y Abstención**: Clasificación estricta entre evidencia de calendario CME y completitud de captura. Abstención rigurosa (`ABSTAIN_CALENDAR_EVIDENCE_REQUIRED`) en activos que carecen de calendario oficial en el repositorio.
6. **Resolución de Anomalías Previas**: Auditoría y esclarecimiento definitivo de la anomalía de volumen 0 en `CADENA_FRONTMONTH_GC.json`, del estado de candidatos en NQ y de los ticks en ventana de mantenimiento en NQ 09-26.

---

## 2. Censo Universal de Datos Pre-Holdout (56 Contratos, 11 Activos)

A partir del escaneo seguro consolidado en [`UNIVERSAL_CONTRACT_INVENTORY_2026-09-15.json`](file:///E:/EdgeLab/docs/research/UNIVERSAL_CONTRACT_INVENTORY_2026-09-15.json), la distribución por raíz es la siguiente:

| Raíz | Clase de Activo | Contratos | Filas Totales | Volumen Total | Rango Trade Dates | Estado Certificación V2 | Manifiesto SHA-256 (prefijo) |
|---|---|---|---|---|---|---|---|
| **ES** | Equity Index | 5 | 262.806.610 | 347.672.482 | 2025-07-18 → 2026-06-30 | **CERTIFIED** | `85c483f4ba09be19...` |
| **MES** | Equity Index Micro | 5 | 167.065.860 | 298.212.276 | 2025-08-01 → 2026-06-30 | **CERTIFIED** | `dbf71ab8ae8edb88...` |
| **NQ** | Equity Index | 5 | 119.153.201 | 129.503.221 | 2025-08-01 → 2026-06-30 | **CERTIFIED** | `d796c34696b5cd99...` |
| **MNQ** | Equity Index Micro | 5 | 334.506.728 | 381.459.605 | 2025-08-01 → 2026-06-30 | **CERTIFIED** (con gaps) | `375b20504045e5ee...` |
| **YM** | Equity Index | 5 | 21.051.454 | 22.737.066 | 2025-08-15 → 2026-06-30 | **CERTIFIED** | `7ffe42cc9af807c5...` |
| **6B** | FX (GBP/USD) | 5 | 7.791.752 | 18.093.062 | 2025-08-01 → 2026-06-30 | **ABSTAIN_CALENDAR** | `d910012bd4aeec69...` |
| **6E** | FX (EUR/USD) | 5 | 18.755.187 | 36.698.275 | 2025-07-25 → 2026-06-30 | **ABSTAIN_CALENDAR** | `71fe8beead5d4cc0...` |
| **6J** | FX (JPY/USD) | 5 | 14.627.578 | 31.496.193 | 2025-08-01 → 2026-06-30 | **ABSTAIN_CALENDAR** | `4b33d26e043101d7...` |
| **GC** | Metales (Gold) | 5 | 38.154.926 | 43.210.065 | 2025-08-01 → 2026-06-30 | **ABSTAIN_CALENDAR** | `95d0cd2b2e2e34bb...` |
| **ZB** | Tasas (30Y Bond) | 5 | 27.204.693 | 92.973.549 | 2025-08-18 → 2026-06-30 | **ABSTAIN_CALENDAR** | `edcf9b67834de554...` |
| **MBT** | Cripto (Micro BTC) | 6 | 4.581.994 | 8.018.213 | 2025-08-18 → 2026-06-30 | **ABSTAIN_CALENDAR** | `9317a8bb71856363...` |
| **TOTAL** | *11 Activos* | **56** | **1.015.108.799** | **1.407.249.709** | **2025-07-18 → 2026-06-30** | — | — |

---

## 3. Resolución Formal de Anomalías Históricas

### 3.1. Anomalía de Volumen Cero en GC (`CADENA_FRONTMONTH_GC.json`)

**Contexto del Problema**:
En el archivo de investigación preexistente `docs/research/CADENA_FRONTMONTH_GC.json`, los rolls:
- `GC 04-26 -> GC 06-26` (efectivo `2026-03-30`)
- `GC 06-26 -> GC 08-26` (efectivo `2026-05-28`)
figuraban con `vol_pred: 0` y ratios extremos de $145.613,0\times$ y $133.692,0\times$, sugiriendo que el contrato saliente no tenía volumen registrado.

**Hallazgo de la Auditoría**:
1. Se inspeccionó el script generador `tools/bt2_absorption_frontmonth_chain.py`. Dicho script leía de archivos de texto sin procesar `.Last.txt` en una ruta externa (`C:\Users\nicoc\OneDrive\Documentos\DataNT8`).
2. Dicho archivo `.Last.txt` presentaba huecos de extracción y desalineación horaria en la función `sesion()`.
3. Se auditó la fuente de verdad primaria en `E:\EdgeLab\data\nt8_research_v2\GC_parquet`:
   - **Roll 04-26 $\rightarrow$ 06-26**:
     - En `2026-03-27` (día de señal causal $D-1$): `GC 04-26` tuvo **21.187** contratos negociados, mientras que `GC 06-26` tuvo **149.438** contratos. El líder de volumen estricto fue `GC 06-26` con una razón real de $7,05\times$.
     - En `2026-03-30` (día efectivo $D$): `GC 04-26` negoció **3.547** contratos y `GC 06-26` negoció **145.613** contratos (los 145.613 que erróneamente se comparaban contra 0).
   - **Roll 06-26 $\rightarrow$ 08-26**:
     - En `2026-05-27` (día de señal causal $D-1$): `GC 06-26` tuvo **26.328** contratos negociados, mientras que `GC 08-26` tuvo **147.467** contratos ($5,60\times$).
     - En `2026-05-28` (día efectivo $D$): `GC 06-26` tuvo **4.867** contratos negociados y `GC 08-26` tuvo **133.701** contratos.

**Conclusión y Veredicto**:
El contrato saliente **NUNCA tuvo volumen cero en la realidad**. Existió liquidez real, decreciente pero observable. El rollover fue un traspaso natural de liquidez. La anomalía queda formalmente archivada como un defecto de la extracción previa en texto de OneDrive, completamente resuelto en los parquets canónicos.

---

### 3.2. Diagnóstico de NQ y Ticks de Mantenimiento en NQ 09-26

**Contexto**:
En `docs/research/nq_contract_regime_v2_20260902/README.md`, el régimen candidato quedó en estado `ABSTAIN_COMPLETENESS_EVIDENCE_REQUIRED`, y se detectaron **363.601 ticks** de NQ 09-26 dentro de la ventana de mantenimiento (16:00 a 17:00 CT).

**Tratamiento y Solución V2**:
1. **Compuerta `ContractSessionEligibilityGateV2`**: Incorpora el método determinista `is_maintenance_window_ct(hour, minute)` que identifica cualquier transacción ocurrida entre las 16:00:00 y las 16:59:59.999 CT.
2. **Exclusión de Sesión Regular**: Dichos ticks quedan segregados y no participan en la sumatoria de volumen de sesión que compite para el rollover causal.
3. **Certificación Equity Index**: Bajo el calendario estructurado `cme_equity_index_session_calendar_v1.json`, las sesiones pre-roll de NQ han sido auditadas y catalogadas en `UNIVERSAL_SESSION_COMPLETENESS_2026-09-15.json`.

---

### 3.3. Hallazgos de Cobertura en MNQ y MBT

1. **MNQ (Micro E-mini Nasdaq)**:
   - Se detectó una discontinuidad física en el repositorio pre-holdout entre `MNQ_03-26` (cuya última fecha observada es `2026-03-20`) y `MNQ_06-26` (cuya primera fecha observada es `2026-04-06`).
   - Asimismo, entre `2026-06-10` y `2026-06-25` se registra una interrupción en los parquets pre-holdout disponibles.
   - Conforme al principio de fail-closed, el motor de régimen evalúa esos periodos como `SOURCE_INCOMPLETE` y se abstiene de declarar un contrato activo en esas fechas, protegiendo la investigación contra sesgos de datos omitidos.

2. **MBT (Micro Bitcoin)**:
   - Se identificó un salto de cobertura entre `MBT_05-26` (finaliza `2026-05-29`) y `MBT_07-26` (comienza `2026-06-22`).
   - Idénticamente, el sistema marca ineligibilidad en ese intervalo en lugar de forzar una serie contigua irreal.

---

## 4. Arquitectura de Módulos y Verificación Automatizada

Se implementaron y probaron exhaustivamente los siguientes componentes:

1. [`edgelab/data/contract_session_gate.py`](file:///E:/EdgeLab/edgelab/data/contract_session_gate.py):
   - Compuerta causal multi-activo `ContractSessionEligibilityGateV2`.
   - Soporta perfiles específicos de producto, umbrales de ticks/volumen, detección de festivos (`EARLY_CLOSE`, `CLOSED`), exclusión post-roll y filtro de mantenimiento.
2. [`edgelab/data/continuous_contract.py`](file:///E:/EdgeLab/edgelab/data/continuous_contract.py):
   - Generador causal continuo `build_continuous_series`.
   - Ensambla `<ROOT>_CONT_CAUSAL_D1.parquet` con precios reales y linaje criptográfico inmutable (`root, contract, trade_date, regime_id, roll_manifest_sha256, source_file, source_row, ts_utc_ns, sequence, state_reset_flag`).
   - Prohíbe estrictamente la mezcla de contratos micro y estándar.
3. [`.gitignore`](file:///E:/EdgeLab/.gitignore):
   - Actualizado para incluir `*.parquet` y `*_CONT_CAUSAL_D1.parquet`, garantizando que ninguna salida pesada sea rastreada o commiteada por Git.

### Batería de Tests Unitarios (41 Tests Pasando)
- `tests/data/test_contract_session_gate.py`: 11/11 PASSED
- `tests/data/test_continuous_contract.py`: 6/6 PASSED
- `tests/data/test_contract_regime.py`: 12/12 PASSED (incluye ciclos bimensuales GC, mensuales MBT, invariancia de día D, desempate y monotonía)
- `tests/data/test_nq_session_gate.py`: 12/12 PASSED
- **Total:** 41 tests ejecutados con éxito sin ninguna falla ni warning bloqueante.

---

## 5. Artefactos Entregados en `docs/research/`

1. [`UNIVERSAL_CONTRACT_INVENTORY_2026-09-15.json`](file:///E:/EdgeLab/docs/research/UNIVERSAL_CONTRACT_INVENTORY_2026-09-15.json): Inventario criptográfico y métrico de los 56 archivos parquet.
2. [`UNIVERSAL_CONTRACT_REGIME_V2_SPEC_2026-09-15.md`](file:///E:/EdgeLab/docs/research/UNIVERSAL_CONTRACT_REGIME_V2_SPEC_2026-09-15.md): Especificación matemática formal del estándar V2.
3. [`UNIVERSAL_SESSION_COMPLETENESS_2026-09-15.json`](file:///E:/EdgeLab/docs/research/UNIVERSAL_SESSION_COMPLETENESS_2026-09-15.json): Matriz consolidada de 3.833 evaluaciones de completitud de sesión.
4. Manifiestos de régimen validados por activo en [`docs/research/contract_regimes/`](file:///E:/EdgeLab/docs/research/contract_regimes/):
   - `ES_contract_regime_v2_20260915.json`
   - `MES_contract_regime_v2_20260915.json`
   - `NQ_contract_regime_v2_20260915.json`
   - `MNQ_contract_regime_v2_20260915.json`
   - `YM_contract_regime_v2_20260915.json`
   - `6B_contract_regime_v2_20260915.json` (Abstención por calendario)
   - `6E_contract_regime_v2_20260915.json` (Abstención por calendario)
   - `6J_contract_regime_v2_20260915.json` (Abstención por calendario)
   - `GC_contract_regime_v2_20260915.json` (Abstención por calendario)
   - `ZB_contract_regime_v2_20260915.json` (Abstención por calendario)
   - `MBT_contract_regime_v2_20260915.json` (Abstención por calendario)
