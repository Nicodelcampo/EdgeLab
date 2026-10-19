# Reporte Event Store Canónico — 5 Contratos de Oro (GC)

- **Fecha UTC:** 2026-08-26
- **Estado:** `EVENT_STORE_GC_ALL5=COMPLETE`
- **Total de eventos extraídos:** **24.549 eventos de microestructura**
- **Datos procesados:** **40.552.525 ticks** (100% libre de lookahead, 0 retrocesos temporales).
- **Directorio de salida local:** `E:\DatosNT8\event_store_gc_all5\`

---

## 1. Distribución de Eventos por Contrato

| Contrato | Ticks Procesados | Eventos BigTrap2Absorption | Eventos BigTrap2 | Total Eventos | Tamaño Parquet |
|---|:---:|:---:|:---:|:---:|:---:|
| **GC 12-25** | 16.206.425 | 6.625 | 2.637 | 9.262 | 281.2 KB |
| **GC 02-26** | 7.841.934 | 4.694 | 977 | 5.671 | 173.9 KB |
| **GC 04-26** | 6.965.053 | 2.718 | 1.074 | 3.792 | 117.1 KB |
| **GC 06-26** | 4.857.838 | 2.250 | 481 | 2.731 | 86.8 KB |
| **GC 08-26** | 4.681.275 | 2.392 | 701 | 3.093 | 97.3 KB |
| **TOTAL** | **40.552.525** | **18.679** | **5.870** | **24.549** | **756.3 KB** |

---

## 2. Esquema de Datos Canónico PIT (`event_store_gc_all5_v1`)

Cada fila en los parquets de eventos contiene la tupla exacta de ejecución:
- `ts_utc_ns` (int64): Timestamp UTC en nanosegundos del evento.
- `source_row` (int64): Fila de origen del tick disparador.
- `contract` (string): Nombre del contrato de futuros.
- `session_id` (string): Sesión de trading CME (`YYYYMMDD`).
- `indicator` (string): Identificador del indicador (`BigTrap2Absorption`, `BigTrap2`).
- `direction` (int8): Dirección de la señal (`+1` Long, `-1` Short).
- `price_ticks` (int64): Precio en ticks de la señal.
- `fill_ts_utc_ns` / `fill_source_row` / `fill_price_ticks`: Coordenadas del fill causal inmediatamente posterior ($t_0 + 1$).
- `metadata_json` (string): Métricas internas (score de absorción, volumen absorbido, volumen de trampa).
