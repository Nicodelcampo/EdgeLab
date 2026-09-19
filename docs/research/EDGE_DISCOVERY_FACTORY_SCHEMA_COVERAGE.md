# Edge Discovery Factory — Inventario de Schemas y Cobertura de Indicadores

- **Activos Auditados:** 147 bundles
- **Directorio Fuente:** `E:\EdgeLab-multiasset\viewer\nt8_bridge\bundles` (Read-Only)
- **Fecha:** 2026-09-19

## 1. Clasificación de Capacidades

| Indicador | Versión | Activos | Zonas | Disponibilidad Causal | Clasificación | Paridad |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| HFTZonesUniversal | V2_UNIVERSAL | 11 (55 contratos) | 3,328,710 | 100.0% Causal | `CAUSAL_READY` | `PARITY_ABSTAIN` |

## 2. Detalle de Campos y Tipos

### HFTZonesUniversal
- **Origen:** `origin_ts_ns` (int / nanosegundos UTC), `t0` (int / segundos UTC)
- **Disponibilidad:** `available_ns` (int / nanosegundos UTC), `available_ts` (int / segundos UTC)
- **Fill:** `derivable` as-of next trade/candle open
- **Geometría:** `top` (float64), `bottom` (float64), `height_ticks` (float64)
- **Lado:** `kind` (`HFT_BUY` -> `BULL`, `HFT_SELL` -> `BEAR`)
- **Microestructura:** `pasos` (int), `valid_steps` (int), `total_vol` (float), `vol_rate` (float), `total_ms` (float), `avg_ms` (float)
- **Terminación:** `termination_reason` (`MAX_PAUSE`, `MAX_RETRO`, `SESSION_END`)
- **Estado:** `state` (`ACTIVE`)
- **Contexto:** `session_id`, `contract`, `instrument`, `tick_size`

## 3. Compatibilidad con Corredores e Interfaz Canónica

- **Corredores Universales:** SÍ. Las zonas poseen `top`, `bottom`, `origin_ts_ns` y `available_ns`, permitiendo proyección horizontal y culling temporal determinista.
- **Disponibilidad Causal:** 100% explícita en todos los 147 bundles generados (`CANONICAL_CAUSAL_T0`).
- **Faltantes para Interfaz Canónica:** Ninguno estructural; `executable_fill_ts` y `availability_quality` se annotan canónicamente al ingresar al store columnar.
- **Clasificación Global:** `CAUSAL_READY` (con `PARITY_ABSTAIN` explícito).