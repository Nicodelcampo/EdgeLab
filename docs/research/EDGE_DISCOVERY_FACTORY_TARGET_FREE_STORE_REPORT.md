# Edge Discovery Factory — Informe del Feature Store Target-Free

- **Estado:** `PASS_TARGET_FREE_FEATURE_STORE`
- **Activos Procesados:** 147 / 147
- **Formato:** Parquet Columnar particionado con compresión ZSTD
- **Entrada:** `E:\EdgeLab-multiasset\viewer\nt8_bridge\bundles` (Read-Only)
- **Tiempo de Extracción:** 198.64s

## 1. Métricas de Almacenamiento

| Componente | Registros | Ubicación |
| :--- | :--- | :--- |
| **Zonas Causales (`zone_events`)** | 3,328,710 | `artifacts/edge_factory/zone_events/` |
| **Zonas Exploratorias (`zone_events_exploratory`)** | 0 | `artifacts/edge_factory/zone_events_exploratory/` |
| **Eventos de Corredor (`corridor_events`)** | 3,325,972 | `artifacts/edge_factory/corridor_events/` |
| **Inventario de Sesiones (`session_inventory`)** | 3,439 | `artifacts/edge_factory/session_inventory/` |

## 2. Invariantes de Seguridad y Causalidad

- **Outcomes Firewall:** ESTRICTO. Cero retornos futuros, cero labels, cero PnL calculados.
- **Disponibilidad Causal:** 100% de las zonas en `zone_events` cumplen `origin_ts <= signal_available_ts < executable_fill_ts`.
- **Zonas Segregadas:** Zonas sin verificación causal estricta se derivan exclusivamente a `zone_events_exploratory`.
- **Holdout Firewall:** Timestamp límite estricto `1782856800000000000` respetado; cero filas decodificadas post 2026-07-01.

## 3. Diccionario de Features Target-Free

Se declararon e indexaron 18 features formales en `manifests/FEATURE_DICTIONARY.json`, todas con estado `target_free: true` y `causal_status: CAUSAL_VERIFIED`.
