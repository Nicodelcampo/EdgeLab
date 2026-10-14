# INFORME FINAL DE CERTIFICACIÓN: Event Store Canónico de Creación AVolClusterPOI NQ-120t (Gate 1A)

**Fecha:** 2026-08-28  
**Rol:** Auditor Cuantitativo y de Integridad de EdgeLab  
**Rama:** `research/avolcluster-nq-gate1-infra-v1-20260828`  
**PR:** [#22](https://github.com/Nicodelcampo/EdgeLab/pull/22)  
**Base:** `3961b67d80cd62aa6adab101e79739db3bc0005b`  
**Commit Productor de Artefactos (`ARTIFACT_PRODUCING_COMMIT`):** `910c4dd75a6e6494f01497b4ff073d5a1e8e9637`  
**Token de Build Ejecutado:** `AUTHORIZE_BUILD_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`  
**Token de Finalización Ejecutado:** `AUTHORIZE_FINALIZE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`  
**Token de Validación Ejecutado:** `AUTHORIZE_VALIDATE_AVOLCLUSTER_NQ_ZONE_EVENT_STORE_V1`  

---

## 1. Identidades Criptográficas y Lógicas Certificadas

| Objeto | Hash SHA-256 | Tipo | Descripción |
|---|---|---|---|
| **Spec Payload Congelado** | `c9792d00da4f15311acdd13f965d06d601e0d08ae0e961766338d04e5e9440ba` | Lógico JSON | Spec de creación vinculada ex-ante |
| **Input Registry Git Blob** | `09d09dec961ebe091fe68d4062b63f9faf34610e` | Git Blob SHA-1 | Registry de 5 contratos verificado contra `docs/datos_manifiesto.json` |
| **Event Store Lógico (5.876 filas)** | `7c254009dc4ccd58f4187360a861f76a692945b94c7091766cce6cf3e46f3a77` | Lógico Determinista | Checksum de payload canónico tipado |
| **Parquet Físico** | `4dad91f6a572bfb5edc714dfb13daa4a0bbee6b96301a4d734466a9da7a06674` | Físico Disco | `avolcluster_nq_zone_creation_event_store.parquet` |
| **Manifest Físico (`Get-FileHash`)** | `df80294138d0401d979bceb5416c6006d05fd7d143b00a1bab2323260fea0cd3` | Físico Disco | `avolcluster_nq_zone_store_manifest.json` |
| **Manifest Payload Interno** | `f87061427d884dac3290c52144bdcf0ab079d4a4b4674237c279072eae51cacc` | Lógico JSON | Payload interno declarado en manifest |

---

## 2. Resumen Científico de la Creación (Gate 1A)

- **Configuración:** `tick_120_W5_M20_C4_P950`
- **Total Sesiones CME Registradas:** 234 sesiones continuas sin solapamiento
- **Total Checkpoints Generados:** 234 archivos JSON (prefijo `000` a `233`)
- **Total Filas Canónicas Creadas:** **5.876 zonas `OFF_PRICE`** (100% de coincidencia exacta con la selección target-free)
- **Sesiones con Zonas Creadas:** **233 sesiones** (99.6% de cobertura)
- **Sesión de Calentamiento sin Zonas:** 1 sesión (`20250804`, ordinal 000)
- **Rango Operativo:** `20250805` (primera sesión con eventos) a `20260630` (límite superior pre-holdout)

### Distribución por Contrato
- **NQ 09-25:** 31 sesiones, 655 eventos
- **NQ 12-25:** 64 sesiones, 1.580 eventos
- **NQ 03-26:** 63 sesiones, 1.612 eventos
- **NQ 06-26:** 64 sesiones, 1.789 eventos
- **NQ 09-26:** 12 sesiones, 240 eventos

---

## 3. Certificación de Validación Independiente

La validación independiente (`tools/validate_avolcluster_nq_zone_store.py --validate-artifacts`) certificó formalmente:
- `status: READY_ZONE_CREATION_EVENT_STORE`
- `logical_identity: PASS`
- `parquet_matches_checkpoints_1to1: true`
- `transport_matches_checkpoints_1to1: true`
- `parquet_readable: true`
- `rows: 5876`

---

## 4. Estado de Firewalls y Separación de Capacidades

```text
ZONE_CREATION_GATE_1A_COMPLETE = true
ZONE_STORE_FINALIZED           = true
INDEPENDENT_VALIDATION_PASS    = true
PARQUET_CHECKPOINTS_MATCH      = true
CHECKPOINT_FILES               = 234
CANONICAL_ROWS                 = 5876
SESSIONS_WITH_EVENTS           = 233
REGISTERED_SESSIONS            = 234
HOLDOUT_TOUCHED                = false
FUTURE_PRICE_PATH_ACCESSED     = false
FIRST_TOUCH_ACCESSED           = false
MFE_MAE_ACCESSED               = false
FIRST_PASSAGE_ACCESSED         = false
PNL_ACCESSED                   = false
EDGE_DECLARED                  = false
PROMOTION_ELIGIBLE             = false
```

- **Frontera del Holdout:** Intacta (`2026-07-01` a `2026-12-31` no tocado).
- **Gate 1B:** Lifecycle, first touch y medición conjunta permanecen como gates independientes en borradores no autorizados.

---

## Aporte al referente

Se certifica y publica formalmente la conclusión de Gate 1A para AVolClusterPOI NQ-120t. El Event Store canónico de creación queda reproducido deterministamente (5.876 zonas en 233 sesiones), consolidado en Parquet y validado independientemente, preservando de forma fail-closed todos los firewalls hacia Gate 1B.
