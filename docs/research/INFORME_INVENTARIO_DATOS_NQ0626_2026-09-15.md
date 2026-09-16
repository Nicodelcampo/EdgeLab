# Informe de Inventario de Datos: NQ 06-26 (Pre-Holdout)

> **Fecha de corte:** 2026-09-15  
> **Rama viva:** `work/nq-causal-foundation-v1-20260915` (base `foundation/f0b-compatibility-probe`)  
> **Instrumento:** `NQ 06-26`  
> **Objetivo:** Certificar la identidad del parquet canónico y del histórico nativo NT8 antes de ejecutar la paridad y la compuerta causal.

---

## 1. Parquet Canónico de Ticks

| Atributo | Valor Declarado / Esperado | Valor Real Medido | Estado |
| :--- | :--- | :--- | :--- |
| **Ruta relativa** | `data/nt8/NQ_parquet/NQ_06-26_ticks.parquet` | `data/nt8/NQ_parquet/NQ_06-26_ticks.parquet` | PASS |
| **Ruta absoluta** | `E:\EdgeLab\data\nt8\NQ_parquet\NQ_06-26_ticks.parquet` | `E:\EdgeLab\data\nt8\NQ_parquet\NQ_06-26_ticks.parquet` | PASS |
| **Tamaño (bytes)** | `675240935` | `675240935` | **PASS (EXACT)** |
| **SHA-256** | `3de249b9b8d8ada01c5b485aa893ccdf1315ae3f7bbebcaf72024de12e1b25f6` | `3de249b9b8d8ada01c5b485aa893ccdf1315ae3f7bbebcaf72024de12e1b25f6` | **PASS (EXACT)** |
| **Total de filas (ticks)** | N/A | `34,203,535` | PASS |
| **Primer timestamp** | Pre-holdout | `2026-03-12 03:02:25.604 UTC` (`1773284545604000000` ns) | PASS |
| **Último timestamp** | Pre-holdout (< 2026-07-01) | `2026-06-18 13:29:55.044 UTC` (`1781789395044000000` ns) | PASS |
| **Filas en Holdout (>= 2026-07-01)** | `0` (Estrictamente prohibido) | `0` | **PASS (INTACTO)** |
| **Zona horaria detectada** | UTC en `ts_utc_ns` / Nanosegundos epoch | UTC | PASS |
| **Origen del archivo** | Local / Kaggle | **Local** (`E:\EdgeLab`) | PASS |
| **Veredicto Parquet** | — | — | **PASS** |

### Esquema de Columnas y Tipos PyArrow
* `ts_utc_ns`: `int64` (Timestamp UTC en nanosegundos)
* `ts_local_ns`: `int64` (Timestamp local en nanosegundos)
* `sequence`: `int64` (Índice secuencial estricto)
* `price_ticks`: `int64` (Precio expresado en número entero de ticks)
* `bid_ticks`: `int64` (Mejor oferta en ticks)
* `ask_ticks`: `int64` (Mejor demanda en ticks)
* `volume`: `int32` (Volumen del tick)
* `aggressor`: `string` (Dirección agresora: Buy / Sell)
* `tick_type`: `string` (Trade / Quote)
* `instrument`: `string` ('NQ')
* `contract`: `string` ('06-26')
* `source_file`: `string` (Archivo fuente de captura)
* `source_row`: `int64` (Fila en archivo fuente)

---

## 2. Histórico Nativo NinjaTrader 8

| Atributo | Valor Requerido | Valor Real Observado | Estado |
| :--- | :--- | :--- | :--- |
| **Directorio de ticks** | `db\tick\NQ 06-26` en NT8 | `C:\Users\Usuario\Documents\NinjaTrader 8\db\tick\NQ 06-26` | PASS |
| **Ventana requerida** | `2026-06-03` -> `2026-06-11` | Cobertura horaria continua en archivos `.Last.ncd` para todas las sesiones 03 a 11-jun-2026 | PASS |
| **Archivo fuente del indicador** | `HFTClusterZonesNQ.cs` | `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\Indicators\HFTClusterZonesNQ.cs` | PASS |
| **Versión del indicador** | `v2.0.0` | `2.0.0` | PASS |
| **SHA-256 del indicador `.cs`** | Documentar | `b9437f3f4b4045d45f3b01f91a19f347ec6de7615e46b2ddaf24943472ebef07` | REGISTRADO |
| **Veredicto NT8 Nativo** | — | — | **PASS** |

---

## 3. Conclusión de la Fase 1

El parquet local coincide **exactamente** en tamaño en bytes y firma criptográfica SHA-256 con el estándar canónico del proyecto. No se requiere descarga de Kaggle. El archivo está listo para ser utilizado como contraparte de paridad frente al oráculo de NT8.
