# EdgeLab — Acta de Intake Forense L2: ES 09-26 (NRD → CSV) — TARGET-FREE

- **Fecha de intake:** 2026-08-21
- **Referente canónico:** [`docs/NORTH_STAR.md`](../NORTH_STAR.md) (sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`)
- **Instrumento:** CME E-mini S&P 500 — `ES 09-26` (Tick Size = 0.25)
- **Rango temporal observado:** `2026-08-10` → `2026-08-21` (11 pares de archivos NRD/CSV)
- **Estado M0:** `L2-M0: INTAKE_COMPLETADO_SELLADO_HOLDOUT_QUARANTINE`
- **Manifiesto JSON canónico:** [`runs/intake_l2/manifest_es_sep26_l2.json`](../../runs/intake_l2/manifest_es_sep26_l2.json) (sha256 `5a43f3a5c79f767e1bc08cf7a240ab50ad12de08f44de59fba5122e3414bcc63`)

---

## 1. Advertencia de Gobernanza y Firewall de Holdout

> [!WARNING]
> **DATOS EN PERÍODO HOLDOUT — USO EXCLUSIVAMENTE TARGET-FREE (P-56)**
> Todos los archivos de este intake corresponden a fechas dentro de la ventana sellada de holdout (**2026-07-01 → 2026-12-31**).
> 
> En estricto cumplimiento de la jerarquía rectora de `docs/NORTH_STAR.md` y la regla 95:
> - **Permitido:** Auditoría forense de esquema, integridad de archivos, relojes/timezone, orden/secuencia, cobertura de sesiones y consistencia de exportación.
> - **Estrictamente Prohibido:** Cómputo de señales, outcomes, retornos futuros, forward P&L, correlaciones direccionales o backtests sin autorización explícita y escrita de Nico.
> - **Inmutabilidad de fuentes:** Los archivos originales NRD y CSV son de sólo lectura y quedan intactos en sus rutas de origen.

---

## 2. Localización y Cadena de Custodia (11 Pares de Archivos)

### 2.1 Raíces del Sistema de Archivos
- **Archivos fuente `.nrd` (Market Replay NinjaTrader 8):**
  `C:\Users\Usuario\Documents\NinjaTrader 8\db\replay\ES 09-26\`
- **Archivos exportados `.csv` (NRD to CSV):**
  `E:\NicoPro\ES SEP26\`

### 2.2 Tabla Forense de Hashes y Denominadores Exactos

| Sesión / Archivo | Bytes NRD | SHA-256 NRD | Bytes CSV | SHA-256 CSV | Filas CSV | Minutos Activos | Max Gap (s) | Inversiones | Empates $\mu s$ (%) |
|---|---:|:---:|---:|:---:|---:|---:|---:|---:|---:|
| **20260810** | 62.679.659 | `9ba1704a60546adc88442e7920e5b92ba93a11b50fd992f2696efb350d2ee5c8` | 547.771.250 | `94afe88a57c1efba8af786e17b82251b0bb2fb7e871a40bf4ca4572c56a28803` | 13.304.901 | 1.387 | 2.700,7 | 0 | 80,44 % |
| **20260811** | 41.615.091 | `1c2a8d3facde8438874148a817d3ccc2f3256c8f80a422d24fcffc371b5b5c36` | 343.991.918 | `92f050b5c572fc57ff60e453f9cc8544c2ad4f7d94a4265bdcb6243b2e3e58ab` | 8.630.008 | 1.385 | 2.702,9 | 0 | 79,21 % |
| **20260812** | 59.078.122 | `51ca3ea5c764011dd2676ddffa6fd1bdfed6cc49f2eac48abe8888c964542fa5` | 512.188.315 | `6fc3d7ed7c583f8c240fc30ea3082e375f999e7de89b0fbb48f8a4c779676a19` | 12.439.820 | 1.388 | 2.701,5 | 0 | 79,89 % |
| **20260813** | 57.605.356 | `bbffa2f807e289c81510545b61e9c266e9d7399b3752084b3168644f8838d92f` | 499.323.748 | `18e8d9cc1a0db164e918f30a6045a71fc9fca67f81e31815a95c7f4e11e12055` | 12.114.185 | 1.382 | 2.702,9 | 0 | 79,88 % |
| **20260814** | 46.129.256 | `3f8fdbbffb2104ec046f39435f1b20143032798d606979e5faa3a1d70c145b09` | 399.994.188 | `5b772b72a452e933e804708ee34c7f44d3297c7ea365b6c95d9eac6f70e6877c` | 9.703.213 | 1.021 | 48,0 | 0 | 78,57 % |
| **20260816** | 2.255.795 | `56e8e45a0cb16931ddbe0cc9f34865f65b39d87c82920529a54e98b42dfd2464` | 18.344.965 | `d7265e840f2cc4ce0da4c8a6e6965f83a734f3defc66a1a6d5136c38a2dd0ad0` | 446.022 | 368 | 1.069,9 | 0 | 77,20 % |
| **20260817** | 51.940.132 | `ed6fca6f090a71280b6ce1e22e94100a1b51895abe3e1e45c6e9cb46beabe517` | 448.382.511 | `05f40727677e41be4e0a243029249daaa316d5494f80dceafa13aead23f51c07` | 10.881.392 | 1.386 | 1.805,2 | 0 | 79,28 % |
| **20260818** | 76.364.392 | `82b96a2ae06647fc83aa6ac9f1a15d0221249289538133680e098d226592287b` | 670.953.795 | `b88615f8af86b32161fc166d7dabbb1f2c94948f14128bbe6c2cae0674a4512b` | 16.299.519 | 1.384 | 2.702,2 | 0 | 80,48 % |
| **20260819** | 88.236.385 | `c65d3e57ae388b027d10cee5f479b7a1e19eca663033c3ae84467fc8f7995749` | 773.266.923 | `ad1106cefde35b82042595b351c99fd599ce44ba74ca24bb7d1c7ae77c422e1a` | 18.780.506 | 1.386 | 2.704,2 | 0 | 80,95 % |
| **20260820** | 90.815.143 | `b13b5b32235041016f70eea27f3296a4fcf1b3a75c9ec1800db2b6b696324244` | 798.544.270 | `0173fb6b7eaad5c06151964b45c77b7899097af88af44b73b507e99ccdd4922c` | 19.417.972 | 1.389 | 1.803,7 | 0 | 81,19 % |
| **20260821\*** | 15.424.423 | `10a82b26c2792dbbce6fcbbf252e76809d206d92f941ceb6b65daa9a1be61928` | 121.696.903 | `8126b215496ac5f13ea492f2f4875beaba65c542eb15cfba36c46302476a9f5a` | 3.163.877 | 658 | 46,2 | 0 | 94,30 % |
| **TOTAL** | **591.144.174** | — | **5.134.458.190** | — | **106.182.208** | — | — | **0** | — |

*\*Nota sobre `20260821`: Captura parcial de la sesión en curso (hasta 11:57:28 ART). **Contiene 100 % filas L1 y 0 % filas L2** (debido a que no se mantuvo abierta una ventana DOM/SuperDOM durante la grabación NT8).*

---

## 3. Identidad de la Herramienta Conversora (NRD to CSV)

- **Nombre del AddOn:** `NRDToCSV` (versión 1.2.0, empaquetado para NT 8.0.1.0).
- **Archivo ejecutable:** `C:\Users\Usuario\Documents\NinjaTrader 8\bin\Custom\AddOns\NRDToCSV.cs` (18.682 bytes).
- **Hash SHA-256 del AddOn:** `d409e751c6b6ae104a36d28d62f588301e745131b56f807b7ebf4f1842c903e5`
- **Archivo zip de origen:** `D:\Descargas\NRDToCSV-1.2.0.zip` (4.317 bytes, sha256 `f915fb379203e833a4d676f3b2a4b02275405167802284365003b8852afd7ae9`).
- **Mecanismo de conversión:**
  El código del AddOn es un contenedor UI en WPF sobre la API nativa de NinjaTrader 8. En la línea 360 ejecuta:
  ```csharp
  MarketReplay.DumpMarketDepth(entry.Instrument, entry.Date.AddDays(1), entry.Date.AddDays(1), entry.CsvFileName);
  ```
- **Dictamen de procedencia (P-57):**
  Se asienta formalmente como **código de procesamiento externo NO versionado** en el repositorio. Depende de la biblioteca compilada interna de NinjaTrader 8 (`NinjaTrader.Data.MarketReplay`) y del huso horario local de la máquina anfitriona. No se debe volver a ejecutar ni modificar.

---

## 4. Esquema, Formato y Semántica de Columnas

### 4.1 Formato de Archivo
- **Separador:** Punto y coma (`;`).
- **Encoding:** UTF-8 (sin BOM).
- **Fin de línea:** CRLF (`\r\n`).
- **Header:** Sin fila de cabecera (inicia directamente con eventos de datos).

### 4.2 Esquema de Eventos L2 (Market Depth / 10 Niveles)
Representa el libro de órdenes CME Market-By-Price (MBP):
```text
L2;side;timestamp;microsecond;operation;level;;price;size
```
- **`[0]` Tipo:** Literal `"L2"`
- **`[1]` Lado (`side`):**
  - `0`: **ASK / Offer** (precios ascendentes a partir del Best Ask)
  - `1`: **BID** (precios descendentes a partir del Best Bid)
- **`[2]` Timestamp:** Formato `YYYYMMDDHHMMSS` (14 dígitos, hora local ART)
- **`[3]` Microsegundo:** 6 dígitos (0 a 999.999)
- **`[4]` Operación (`operation`):**
  - `0`: **Insert / Add** (inicialización o entrada de nuevo nivel)
  - `1`: **Update / Modify** (actualización de volumen en nivel existente, >95% de los eventos L2)
  - `2`: **Remove / Delete** (eliminación de nivel)
- **`[5]` Nivel de libro (`level`):** Entero `0` a `9` (Nivel 0 = Top of Book / Best Bid/Ask, Niveles 1..9 = profundidad hasta 10 niveles). *Nota: existe residualmente un valor 10 originado por buffers de transición de NT8*.
- **`[6]` Campo vacío:** Delimitador doble `;;` generado por la API de NT8.
- **`[7]` Precio (`price`):** Decimal en múltiplos de Tick Size (0.25 para ES).
- **`[8]` Tamaño (`size`):** Entero con número de contratos en el nivel.

### 4.3 Esquema de Eventos L1 (Top of Book & Market Events)
Representa trades ejecutados y estadísticas de mercado:
```text
L1;side;timestamp;microsecond;price;size
```
- **`[0]` Tipo:** Literal `"L1"`
- **`[1]` Tipo de dato / Lado (`MarketDataType` enum NT8):**
  - `0`: **Last Trade** (impresión de trade ejecutado, 32,8 % del total L1)
  - `1`: **Best Bid Quote** (actualización de mejor compra, 33,7 %)
  - `2`: **Best Ask Quote** (actualización de mejor venta, 16,7 %)
  - `5`: **Low Price** / Estadística diaria de mínimo (16,7 %)
  - `3, 4, 6, 7, 8`: Opening, High, Settlement, OpenInterest, Volume (<0,01 %)
- **`[2]` Timestamp:** Formato `YYYYMMDDHHMMSS` (14 dígitos, hora local ART)
- **`[3]` Microsegundo:** Entero de microsegundos
- **`[4]` Precio (`price`):** Decimal
- **`[5]` Tamaño (`size`):** Entero de volumen comerciado o en BBO

### 4.4 Muestra de Filas Reales

**Primeras 5 filas de `20260810.csv`:**
```csv
L2;0;20260810010000;320000;0;0;;7783.75;9
L2;0;20260810010000;320000;0;1;;7784;16
L2;0;20260810010000;320000;0;2;;7784.25;19
L2;0;20260810010000;320000;0;3;;7784.5;13
L2;0;20260810010000;320000;0;4;;7784.75;17
```

**Últimas 5 filas de `20260810.csv`:**
```csv
L1;1;20260811005959;944000;7813.5;26
L1;0;20260811005959;972000;7813.75;1
L1;1;20260811005959;972000;7813.5;26
L2;1;20260811005959;9720000;1;0;;7813.5;26
L2;0;20260811005959;9720000;1;0;;7813.75;26
```

---

## 5. Análisis Forense de Relojes y Estructura de Sesión CME

### 5.1 Determinación Rigurosa del Huso Horario
Los timestamps registrados en los CSVs están en **Hora Estándar de Argentina (ART = UTC-3)**, correspondiente a la zona horaria del sistema operativo donde se ejecutó NinjaTrader 8 (`America/Argentina/Buenos_Aires`).

**Pruebas empíricas medidas:**
1. **Pausa diaria de mantenimiento CME (Maintenance Halt):**
   - Regla CME: Lunes a jueves, el mercado cierra de **16:00 a 17:00 Central Time (CDT, UTC-5)** = **21:00 a 22:00 UTC**.
   - En ART (UTC-3), este intervalo corresponde exactamente a **18:00 a 19:00 ART**.
   - En todos los archivos de lunes a jueves (`20260810` a `20260813`, `20260817` a `20260820`), la hora 18 registra un corte de actividad de **~45 minutos** (gap de 17:59:59 a 18:45:00 / 18:55:00 ART) y un volumen casi nulo (entre 9 y 55 eventos residuales de reconexión).
2. **Apertura de sesión dominical (Sunday Session Open):**
   - Regla CME: La semana abre el domingo a las **17:00 CDT** (22:00 UTC) = **19:00 ART**.
   - En `20260816.csv`, las impresiones preliminares de setup ocurren a las 16:01:22 ART y el flujo continuo de trading arranca a las **19:00 ART** (hora 19 registra 8.179 filas; hora 20: 4.074; hora 21: 12.675).
3. **Picos de liquidez RTH (Regular Trading Hours):**
   - La sesión RTH abre a las 08:30 CDT = **10:30 ART** y cierra a las 15:00 CDT = **17:00 ART**.
   - En los archivos CSV, la hora 10 (10:00–11:00 ART) muestra el salto abrupto de liquidez (de ~30k a >350k filas por hora), y la hora 16 registra el cierre de RTH antes del halt de las 18:00 ART.

### 5.2 Estructura de Archivos y Fechas de Trading
- La partición de cada archivo CSV diario inicia a las **01:00:00 ART** (21:00 CDT del día anterior) y termina a las **00:59:59 ART** del día siguiente.
- Por tanto, el archivo `20260810.csv` abarca desde `2026-08-10 01:00:00 ART` hasta `2026-08-11 00:59:59 ART` (cubriendo la sesión asiática, europea y RTH completa del lunes 10 de agosto).

---

## 6. Secuencia y Limitación de Orden Intra-Microsegundo

> [!IMPORTANT]
> **ORDEN INTRA-TIMESTAMP NO SOPORTADO POR ESTA FUENTE (MISMA CLASE QUE P-28)**
> 1. **Inversiones temporales:** Se midieron **0 inversiones** en los 106.182.208 eventos (la serie es monotónicamente no decreciente).
> 2. **Ausencia de secuencia de exchange:** El formato de exportación NT8 `DumpMarketDepth` **no incluye columna de número de secuencia** de CME (`sequence` / `msg_seq_num`).
> 3. **Concentración de empates:** Entre el **77,20 % y el 94,30 %** de todas las filas comparten microsegundo idéntico con la fila anterior (bloques atómicos de ráfagas L2).
> 
> **Declaración explícita:** En cualquier subconjunto de eventos con marca de tiempo idéntica, el orden relativo es el orden de volcado interno del buffer de NinjaTrader 8, no un orden de red verificado por CME.

---

## 7. Cobertura y Tabla de Gaps Mayores

| Archivo | Filas Totales | Minutos Activos | Gaps > 300s | Detalle de Gaps Mayores (> 300s) |
|---|---:|---:|---:|---|
| **20260810** | 13.304.901 | 1.387 | 1 | 17:59:59 → 18:45:00 (2.700,7 s — CME Daily Halt) |
| **20260811** | 8.630.008 | 1.385 | 1 | 17:59:59 → 18:45:02 (2.702,9 s — CME Daily Halt) |
| **20260812** | 12.439.820 | 1.388 | 1 | 17:59:58 → 18:45:00 (2.701,5 s — CME Daily Halt) |
| **20260813** | 12.114.185 | 1.382 | 1 | 17:59:57 → 18:45:00 (2.702,9 s — CME Daily Halt) |
| **20260814** | 9.703.213 | 1.021 | 0 | Max gap: 48,0 s (Cierre de semana 21:02 ART) |
| **20260816** | 446.022 | 368 | 2 | 18:20:40 → 18:30:04 (563,7 s), 18:30:04 → 18:47:54 (1.069,9 s — Sunday Pre-Open) |
| **20260817** | 10.881.392 | 1.386 | 3 | 17:59:59 → 18:30:04 (1.805,2 s), 18:30:04 → 18:45:30 (925,1 s), 18:45:30 → 18:55:00 (570,3 s) |
| **20260818** | 16.299.519 | 1.384 | 2 | 17:59:59 → 18:45:01 (2.702,2 s), 18:49:37 → 18:54:48 (311,6 s) |
| **20260819** | 18.780.506 | 1.386 | 2 | 17:59:58 → 18:45:02 (2.704,2 s), 18:47:42 → 18:55:00 (437,9 s) |
| **20260820** | 19.417.972 | 1.389 | 3 | 18:00:00 → 18:30:04 (1.803,7 s), 18:30:04 → 18:45:30 (925,4 s), 18:45:30 → 18:53:33 (483,0 s) |
| **20260821** | 3.163.877 | 658 | 0 | Max gap: 46,2 s (Sesión parcial en curso hasta 11:57 ART) |

---

## 8. Verificación de Conversión NRD → CSV

- **Relación de expansión física:** El ratio entre el CSV de texto y el NRD binario oscila entre **8,13×** (`20260816`) y **8,79×** (`20260820`), consistente con el overhead de caracteres ASCII sobre floats y ticks comprimidos.
- **Estructura binaria del `.nrd`:**
  - Inicia con encabezado de 72 bytes con dobles IEEE 754 de OHLCV, TickSize (`0.25`), PointValue (`1.0`) y fecha de sesión en ticks `.NET` (`100 ns` desde `0001-01-01`).
  - Los registros posteriores son bloques propietarios serializados por NinjaTrader.
- **Estado de verificación:** **`NO VERIFICADO`** a nivel de conteo binario independiente de bajo nivel. El volcado es realizado opacamente por la API nativa `NinjaTrader.Data.MarketReplay.DumpMarketDepth`. La consistencia macroscópica está verificada por continuidad temporal, rangos de precios OHLC y número de minutos activos.

---

## 9. Registro de Decisiones Abiertas en el Board

En estricto cumplimiento de la regla del 15 de agosto (*asentar en el mismo commit que el acta*), se registran en [`PENDIENTE.md`](../../PENDIENTE.md):

1. **P-56 · Fuente L2 dentro del período Holdout — Cuarentena de Uso Estricto Target-Free.**
2. **P-57 · Conversor NRD→CSV (`NRDToCSV.cs`, AddOn NT8 v1.2.0) — Código no versionado y acoplado a timezone local (ART).**

---

## 10. Conclusiones y Próximos Pasos Permitidos

1. **Estado M0 alcanzado:** La fuente L2 (ES 09-26) queda catalogada, sellada con hashes SHA-256 inmutables y con semántica de columnas y relojes plenamente establecida.
2. **Cuarentena activa:** La data permanece bloqueada para cualquier evaluación económica hasta la fase correspondiente y con autorización formal.
3. **Conversión a Parquet:** Cualquier procesamiento futuro para compresión (e.g. `convert_l2_to_parquet.py`) debe mantener el aislamiento target-free y respetar la conversión de reloj ART (UTC-3) $\to$ UTC / CT.
