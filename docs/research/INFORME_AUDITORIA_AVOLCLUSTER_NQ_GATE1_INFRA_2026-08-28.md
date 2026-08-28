# INFORME DE AUDITORÍA: Infraestructura Event Store AVolClusterPOI NQ-120t (Gate 1)

**Fecha:** 2026-08-28  
**Auditor:** Antigravity (Auditor Cuantitativo, Metodológico y de Integridad de EdgeLab)  
**Objeto:** PR #22 (`research/avolcluster-nq-gate1-infra-v1-20260828`)  
**HEAD Auditado:** `9ddcca8912d8e72bf44bc7bd4cfb5ba872d7b668`  
**Base:** `3961b67d80cd62aa6adab101e79739db3bc0005b` (`research/avolcluster-nq-microticks-v1-20260828`)  
**Spec Evaluada:** `specs/avolcluster_nq_zone_event_store_v1.json`  

---

## 1. Veredicto y Dictamen Formal

### Dictamen: `PASS_RESEARCH_ONLY_PYTHON_KERNEL`

**Justificación:**
1. **Integridad Técnica y Separación de Capacidades:** PASS. La infraestructura implementa una separación estricta y fail-closed entre `--run-all` (solo checkpoints atómicos), `--finalize` (requiere token independiente y 234 checkpoints íntegros) y `--validate-artifacts` (requiere token independiente). No hay mutación de capacidades post-freeze.
2. **Fronteras CME, DST y Aislamiento de Holdout:** PASS. La lectura PyArrow está acotada estrictamente antes de decodificar datos; la frontera superior `2026-06-30T22:00:00Z` (apertura de la sesión `20260701`) garantiza que ninguna fila del holdout sea leída ni decodificada.
3. **Equivalencia con el Sweep Target-Free:** PASS EXACTO. La infraestructura reproduce exactamente la semántica, configuración (`tick_120_W5_M20_C4_P950`) y anclaje de buckets del sweep `tools/sweep_avolcluster_nq_microticks.py`.
4. **Autoridad respecto a NT8:** No existe un export o golden run independiente de NinjaTrader 8 sobre las 234 sesiones de NQ 120t en el repositorio. Aunque el kernel Python v0.5 sigue el diseño de `nt8/aVolClusterPOI.cs`, existen diferencias declaradas (anclaje de bucket horario desde el primer tick bar de la sesión vs hora programada de template en NT8). Por tanto, la clasificación formal vinculante es **Implementación de Investigación basada en el Kernel Python (`PASS_RESEARCH_ONLY_PYTHON_KERNEL`)**, sin reclamar paridad de oráculo NT8 certificada.

---

## 2. Preflight y Estado de Integridad

| Dimensión | Estado Verificado |
|---|---|
| **Rama Git** | `research/avolcluster-nq-gate1-infra-v1-20260828` |
| **HEAD Exacto** | `9ddcca8912d8e72bf44bc7bd4cfb5ba872d7b668` |
| **Worktree Clean** | Sí (`git status --short` vacío) |
| **Python** | `3.12.7` / PyArrow `20.0.0` |
| **Lockfile SHA-256** | `cabea651c495a01bf6d94c2461c16c3a7abd81b8d7fee268138ab26e36f0e85f` |
| **CI Contractual Dedicado** | **SUCCESS (37s–41s)** en GitHub Actions (`aVolClusterPOI NQ zone-store contract`) |
| **Tests Dedicados** | **20/20 PASAN (100%)** en 1.14s |
| **Artefactos Reales Nuevos** | Ninguno (cero Parquets reales, cero checkpoints reales) |

### Estado Inmutable Verificado

```text
SPEC_STATUS                  = DRAFT_PREAUTHORIZATION_FAIL_CLOSED
REAL_ZONE_STORE_BUILD        = NOT_RUN
FIRST_TOUCH_IMPLEMENTED      = false
FUTURE_PRICE_PATH_ACCESSED   = false
MFE_MAE_ACCESSED             = false
FIRST_PASSAGE_ACCESSED       = false
PNL_ACCESSED                 = false
HOLDOUT_ROWS_DECODED         = false
EDGE_DECLARED                = false
PROMOTION_ELIGIBLE           = false
```

---

## 3. Matriz de Equivalencia Técnica y Comparación con NT8

| Componente / Campo | Sweep Target-Free NQ | Infraestructura Gate 1 (`build_avolcluster_nq_zone_store`) | Indicador C# NT8 (`aVolClusterPOI.cs` v0.5) | Clasificación |
|---|---|---|---|---|
| **Tipo de Barra** | Tick 120 (`reiniciar_por_sesion=True`) | Tick 120 (`reiniciar_por_sesion=True`) | Tick 120 (Reset on Session) | **EXACT** (vs sweep) / **SEMANTICALLY_EQUIVALENT** (vs NT8) |
| **Bloque de Detección** | 5 barras (600 ticks nominales) | 5 barras (600 ticks nominales) | `WindowBars = 5` | **EXACT** |
| **Multiplicador Mediana** | 2.0x | 2.0x | `MedianMultiplier = 2.0` | **EXACT** |
| **Cálculo de Mediana** | Superior (`sorted[n // 2]`) | Superior (`sorted[n // 2]`) | Superior (`sorted[n/2]`) | **EXACT** |
| **Min Cluster Ticks** | 4 ticks | 4 ticks | `MinClusterTicks = 4` | **EXACT** |
| **Max Gap Ticks** | 1 tick | 1 tick | `MaxGapTicks = 1` | **EXACT** |
| **Percentil Detección** | 95.0% | 95.0% | `DetectionPercentile = 95.0` | **EXACT** |
| **Cuantil Empírico** | $\lceil p \cdot n \rceil$ sin interpolar | $\lceil p \cdot n \rceil$ sin interpolar | $\lceil p \cdot n \rceil$ sin interpolar | **EXACT** |
| **Min Muestras / Bucket** | 10 | 10 | Configurable (default 20 en research censo) | **EXACT** (vs sweep) / **DECLARED** (vs NT8 default) |
| **Clusters por Bloque** | 1 (máxima masa) | 1 (máxima masa) | 1 (máxima masa) | **EXACT** |
| **Time Buckets** | 30 min, clamp a 45 | 30 min, clamp a 45 | 30 min, `AddSeconds(-1)` sobre inicio programado | **DIFFERENT_DECLARED** (anclaje primer tick bar vs scheduled session) |
| **Trade Date / Timezone** | 17:00 America/Chicago | 17:00 America/Chicago | Session Template CME 24/5 | **EXACT** |
| **Perfil Histórico** | `SessionProfile` FIFO 20 sesiones | `SessionProfile` FIFO 20 sesiones | `bucketHistory` FIFO 20 sesiones | **EXACT** |
| **Reanudación / State** | En memoria | Snapshot JSON con payload SHA-256 | Estado en memoria | **EXACT** |
| **Clasificación Zona** | `OFF_PRICE` vs `AT_PRICE` | `OFF_PRICE` (5.876 esperadas) | `OFF_PRICE` vs `AT_PRICE` | **EXACT** |
| **Geometría de Nivel** | `[lower_tick, upper_tick]` | `[lower_tick, upper_tick]` | `[LowerTick, UpperTick]` | **EXACT** |
| **Exposición ULP** | 0 (aritmética de ticks enteros) | 0 (aritmética de ticks enteros) | 0 (aritmética de ticks enteros) | **EXACT** |
| **Ciclo de Vida** | N/A (solo creación) | `ZONE_CREATION_ONLY` (fail-closed) | `FirstTouch`, `CloseThrough`, `MaxAge` | **NOT_IMPLEMENTED** (Stage Gate 1 creación) |

---

## 4. Auditoría de Separación de Capacidades y Fail-Closed

1. **`--run-all`:**
   - Escribe exclusivamente checkpoints atómicos (`session_000.json` ... `session_233.json`).
   - Retorna `finalize_executed = False`.
   - No invoca `finalize()` directa ni indirectamente.
   - Requiere `--authorization-token AUTHORIZE_BUILD_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1` y spec en `FROZEN_PREAUTHORIZATION`.
2. **`--finalize`:**
   - Exige la existencia de los 234 checkpoints íntegros validados contra `SessionProfile` contiguo.
   - Exige coincidencia exacta de `5.876 zonas OFF_PRICE` y 233 sesiones con zonas.
   - Escribe `avolcluster_nq_zone_creation_event_store.parquet` y valida equivalencia 1:1 contra los checkpoints.
   - Requiere token independiente: `AUTHORIZE_FINALIZE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`.
3. **`validate_avolcluster_nq_zone_store.py`:**
   - Requiere token independiente: `AUTHORIZE_VALIDATE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`.
   - Comprueba integridad física y lógica del dataset final.
4. **Inmutabilidad Post-Freeze:**
   - Las capacidades (`build_capability_after_freeze`, etc.) no mutan el payload del spec ni permiten saltar los tokens explícitos.

---

## 5. Auditoría de Fronteras CME, DST y Holdout

1. **Lectura Acotada en PyArrow:**
   - `start_ns`: `cme_session_start_utc_ns(first_session)`
   - `end_ns`: `next_calendar_session_start_utc_ns(last_session)`
   - El filtro en `load_canonical_parquet` lee únicamente el rango `[start_utc_ns, end_utc_ns)` a nivel de metadatos de Parquet antes de cargar ticks a memoria.
2. **Frontera del Holdout:**
   - Sesión pre-holdout máxima: `20260630`.
   - Fin de ventana pre-holdout: `2026-06-30T22:00:00Z` (inicio de la sesión CME `20260701`).
   - Cualquier tick $\ge \text{2026-06-30T22:00:00Z}$ queda físicamente fuera del rango de lectura.
3. **Transiciones DST:**
   - La conversión usa `tz_localize("America/Chicago", ambiguous="raise", nonexistent="raise")` asegurando que las transiciones de primavera y otoño de Chicago se manejen de forma determinista y sin ambigüedades.

---

## 6. Hallazgos y Severidad

| ID | Hallazgo | Severidad | Estado |
|---|---|---|---|
| **H-01** | Clasificación de autoridad respecto a NT8: la infraestructura no cuenta con un golden run de NT8 para NQ 120t en 234 sesiones; el anclaje de bucket difiere sutilmente en el tiempo base de sesión. | MEDIA (Documental / Autoridad) | **RESUELTO** (Declarado explícitamente como `PASS_RESEARCH_ONLY_PYTHON_KERNEL` con diferencias declaradas en spec y protocolo). |
| **H-02** | Validación de Parquet en `--finalize` exige `5.876` zonas exactas. Si la corrida real difiere por un evento, aborta fail-closed. | BAJA (Control de Calidad) | **CORRECTO** (Garantiza reproducibilidad determinista del sweep). |

---

## 7. Recomendación Operativa para Freeze

- **`FREEZE_ELIGIBLE`:** **`true`** (la infraestructura está lista para recibir el token formal de freeze `APPROVE_FREEZE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`).
- **`READY_TO_BUILD`:** **`false`** (bloqueado hasta completar la ceremonia de freeze y emitir el token de build separado).
- **`READY_TO_FINALIZE`:** **`false`** (bloqueado hasta completar el build de checkpoints y emitir el token de finalización).

## 8. Addendum de Reconciliación de Identidad y CI (2026-08-28)

### 8.1 Reconciliación de Commits
| Rol | Commit SHA | Descripción |
|---|---|---|
| `IMPLEMENTATION_AUDITED_COMMIT` | `9ddcca8912d8e72bf44bc7bd4cfb5ba872d7b668` | Commit de infraestructura ejecutable, builder y contrato auditado inicialmente. |
| `AUDIT_REPORT_COMMIT` | `ea528cf70a1b2540bbc5ca6166cefe81b64a1bb8` | Commit que incorporó el informe de auditoría inicial. |
| `CURRENT_FREEZE_CANDIDATE` | `f05ccceb454e989315ccc5911bf0f0414c3a0123` | HEAD actual del PR #22 (agrega diseño conjunto `avolcluster_bt2a_nq_joint_measurement_v1.draft.json` sin alterar el código ejecutable de creación). |
| `POST_AUDIT_EXECUTABLE_CHANGES` | `false` | Se verificó mediante `git diff` que ningún componente de creación/builder fue mutado. |

### 8.2 Clasificación de Deuda CI
- **CI Contractual Dedicado (`aVolClusterPOI NQ zone-store contract`):** **SUCCESS (40s)** en PR y push.
- **CI General Pytest (Python 3.12):** 8 fallos y 1 error preexistentes en la base `ef7f5c9` / `3961b67` por tests heredados que requieren rutas locales `data/nt8/`.
- **Regresiones AVol:** **`AVOL_REGRESSIONS = 0`**. 26/26 tests dedicados de AVol pasan al 100%.

### 8.3 Semántica de Estado de Freeze
- Estado congelado exacto según código (`edgelab/research/avolcluster_nq_zone_store.py`):
  `status = "FROZEN_ZONE_CREATION_EVENT_STORE"`
- Payload congelado proyectado:
  `projected_frozen_payload_sha256 = "1f2ef16548ab6a9d413a7871351800a9868e9ede9725f46c9e2f482588abe59c"`
- Diseño conjunto borrador (`specs/avolcluster_bt2a_nq_joint_measurement_v1.draft.json`): permanece en estado borrador y **completamente fuera** de la autorización de creación.

## 9. Addendum de Incidente de Procedencia de Inputs y Corrección Controlada (2026-08-28)

### 9.1 Incidente y Aborto Fail-Closed
Al ejecutar `--run-all` bajo el token `AUTHORIZE_BUILD_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1` con binding al HEAD `69f5868c09b6628819b041c6734c041cedffef1f`, el runner ejecutó `verify_input_file` y abortó fail-closed de inmediato:
`status: ABSTAIN_EVENT_STORE_CONTRACT`, `message: source SHA-256 mismatch for NQ 09-25`.
- **Cero checkpoints creados** (`checkpoints = 0`).
- **Cero filas decodificadas del holdout**.
- **Ausencia total de Parquet final**.

### 9.2 Causa Raíz Forense
Los archivos físicos en disco (`E:\EdgeLab\data\nt8\NQ_parquet`) y sus manifiestos locales coinciden al 100% con [`docs/datos_manifiesto.json`](docs/datos_manifiesto.json). No obstante, el archivo `specs/bt2a_gate1_nq_all5_input_registry_2026-08-27.json` (introducido en commit `ee357e1`) presentaba una divergencia en la segunda mitad del string SHA-256 para 4 contratos (NQ 09-25, NQ 12-25, NQ 06-26 y NQ 09-26), coincidiendo únicamente NQ 03-26.

### 9.3 Corrección Controlada (`APPROVE_CORRECT_AVOLCLUSTER_NQ_INPUT_REGISTRY_V1`)
1. **Invalidación Formal del Freeze Anterior:**  
   `OLD_BUILD_AUTHORIZATION_HEAD = 69f5868c09b6628819b041c6734c041cedffef1f`  
   `OLD_FROZEN_PAYLOAD = 1f2ef16548ab6a9d413a7871351800a9868e9ede9725f46c9e2f482588abe59c`  
   `OLD_BUILD_AUTHORIZATION_VALID = false`
2. **Retorno Temporal a Estado Borrador:**  
   `status = "DRAFT_PREAUTHORIZATION_FAIL_CLOSED"`, `freeze_authorized = false`, `execution_authorized = false`.
3. **Alineación de Hashes:**  
   Se corrigieron los 4 hashes para alinearlos estrictamente con `docs/datos_manifiesto.json` y el almacenamiento físico.
4. **Nuevo Blob SHA-1 del Input Registry:**  
   `input_registry_git_blob_sha1 = "09d09dec961ebe091fe68d4062b63f9faf34610e"`
5. **Nuevo Payload Científico Proyectado:**  
   `new_projected_frozen_payload_sha256 = "c9792d00da4f15311acdd13f965d06d601e0d08ae0e961766338d04e5e9440ba"`
6. **Tests Automatizados:**  
   Se incorporó `test_input_registry_matches_official_datos_manifiesto()` asegurando consistencia continua con el manifiesto canónico.

---

## Aporte al referente

Se audita y certifica la infraestructura de creación de zonas AVolClusterPOI NQ-120t bajo la autoridad `PASS_RESEARCH_ONLY_PYTHON_KERNEL`. El control fail-closed de procedencia detectó con éxito la divergencia de hashes en el registry histórico. Se completa la corrección controlada en estado borrador, vinculando el nuevo blob `09d09dec961ebe091fe68d4062b63f9faf34610e` y proyectando el nuevo payload congelado `c9792d00da4f15311acdd13f965d06d601e0d08ae0e961766338d04e5e9440ba` para una nueva ceremonia formal de freeze.


