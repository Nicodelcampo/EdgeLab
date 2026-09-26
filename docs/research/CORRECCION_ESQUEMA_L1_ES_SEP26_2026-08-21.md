# Corrección forense del esquema L1 — ES 09-26 (NRD→CSV)

- **Fecha**: 2026-08-21 · **Estado**: `MEASURED_COMMITTED`
- **Corrige**: `docs/research/INTAKE_L2_ES_NRD_2026-08-21.md` §4.3 (commit `152b35b`)
- **Alcance**: **target-free**. Sólo esquema, integridad y relojes. Sin señales, sin
  outcomes, sin P&L. Los datos están en período de holdout — **P-56 vigente**.
- Fuente auditada: `E:\l2_parquet\ES_09-26\` (11 sesiones) y
  `E:\l2_parquet\ES_09-26_ticks.parquet`.

---

## 1. El mapeo de `side` en L1 estaba mal, y cambia el veredicto

El acta interpretó el campo `[1]` de las filas `L1` como sigue. **Tres de los cuatro
códigos son incorrectos**:

| código | acta decía | **es en realidad** | evidencia |
|---|---|---|---|
| `0` | Last Trade | **Ask** (BestAsk) | reconstrucción corrida sobre 2.000.000 de eventos consecutivos: bajo `0=Ask` las violaciones `ask ≤ bid` son **0,044 %**; bajo `1=Ask` son **99,998 %** |
| `1` | BestBid | **Bid** ✅ | único que estaba bien |
| `2` | BestAsk | **Last** (trade) | `size` mediano **1** contra **15** de las cotizaciones; y el conteo coincide con el export de ticks (ver §3) |
| `5` | Low Price | **DailyVolume** | `price` = 0 en el **100 %** de las filas, en las 11 sesiones; `size` **estrictamente creciente** (3.119.321 → 4.489.272 en la sesión del 19) |

### Por qué importa

Con el mapeo del acta, los números parecían una captura rota:

- «`Ask` aparece 3,4× menos que `Bid`» → **falso**. Son `3.470.695` contra `3.491.045`:
  **simétricos**, como corresponde.
- «`side=5` duplica exactamente a `Ask`» → **falso**. Es el contador de volumen diario,
  que se emite una vez por trade, y por eso empareja 1:1 con los trades.

**El diagnóstico se invierte: la data no está rota.** El libro reconstruido es de manual:

| spread implícito | valor |
|---|---|
| mediana | **1 tick** |
| exactamente 1 tick | **92,41 %** |
| cruzado o trabado (`≤ 0`) | **0,056 %** |

## 2. Esquema L1 corregido

```text
L1;side;timestamp;microsecond;price;size

side = 0  ->  Ask   (BestAsk quote)      size = profundidad en el toque
side = 1  ->  Bid   (BestBid quote)      size = profundidad en el toque
side = 2  ->  Last  (trade ejecutado)    size = tamaño del trade
side = 5  ->  DailyVolume                price = 0, size = volumen acumulado
side = 3,4,6,7,8  ->  estadísticas de sesión, <0,01 %
```

Coincide con el enum `MarketDataType` de NT8 (`Ask=0, Bid=1, Last=2, …`), no con la
lectura del acta.

## 3. Los dos feeds SÍ describen el mismo mercado

Era la pregunta bloqueante: los ticks históricos venían de Lucid y el L2 de NT8.
**Ahora hay un export de ticks del propio NT8** (`ES 09-26.Last.txt`), y coinciden:

| | sesión 2026-08-19 |
|---|---|
| ticks exportados (`.Last.txt`) | **1.040.619** |
| `L1 side=2` (trades) | **1.032.300** |
| diferencia | **0,80 %** |
| rango de precios, ticks | [30.793 · 31.059] |
| rango de precios, L1 | [30.789 · 31.060] |

La diferencia del 0,8 % se explica por la ventana: el export de ticks cubre el día
calendario completo y el archivo L1 va de `01:00` a `01:00`.

## 4. Lo que sigue bloqueado

### 4.1 Desfase de reloj de ~1 hora — **sin resolver**

Los ticks abarcan `00:00:00 → 23:59:59`; el archivo L1 del mismo día, `01:00:00 →
01:00:08`. **Exactamente +1 h.**

El acta declara los CSV en hora local ART; el manifiesto del parquet de ticks declara
`ts_utc_ns = ts_local_ns (offset 0)`. **No se sabe cuál de los dos define el origen.**
Hay que resolverlo **antes** de cualquier unión — no estimarlo por correlación.

### 4.2 No hay columna de orden de fila en L1/L2 — **el bloqueo más serio**

| parquet | columnas |
|---|---|
| ticks | `ts_utc_ns, ts_local_ns, sequence, price_ticks, bid_ticks, ask_ticks, volume, aggressor, tick_type, instrument, contract, source_file, **source_row**` |
| L1 | `side, price, size, ts_us, price_tick` |
| L2 | `side, operation, level, price, size, ts_us, price_tick` |

**A L1 y L2 les falta `source_row`.** El acta midió **~80 % de empates en microsegundo**,
así que sin el índice de fila del CSV **el orden de los eventos dentro de un mismo
timestamp no es recuperable**.

Eso rompe cualquier cosa que dependa de secuencia: reconstruir el libro evento a evento,
clasificar agresor contra el quote vigente, o medir OFI. **Es reparable**: los CSV siguen
en `E:\NicoPro\ES SEP26\` y basta reconvertir agregando el número de línea.

### 4.3 Otros hallazgos

- **`level = 10`** en **1,7–2,8 %** de los eventos L2, en las 11 sesiones. El acta lo
  llama residual de buffers; con esa magnitud y esa consistencia, **no es residual** y hay
  que decidir si se descarta o se interpreta.
- **`20260821` no tiene L2**: 0 filas. Ya declarado en el acta (no había ventana DOM).
- El export de ticks cubre **2026-08-07 → 2026-08-20**; el L2, **2026-08-10 → 2026-08-21**.
  Solapan 9 sesiones completas.

## 4.4 Dos defectos más, encontrados al reconvertir

### El total del acta está mal sumado

La tabla forense del acta declara **`106.182.208`** filas CSV. Sumando **sus propias
cifras por sesión** da **`125.181.415`** — y ese es también el conteo de líneas real de
los 11 CSV, verificado uno por uno.

**Los números por sesión son correctos; la fila TOTAL está errada** en 18.999.207. Es un
error aritmético del acta, no un problema de dato.

### `ts_us` dependía de la versión de pandas — 1000× de error

El parser hacía:

```python
pd.to_datetime(...).astype("int64") // 1000 + usec
```

| pandas | dtype | `astype(int64)` | `//1000` |
|---|---|---|---|
| 2.x (el sandbox) | `datetime64[ns]` | nanosegundos | **microsegundos** ✅ |
| 3.0.3 (esta máquina) | `datetime64[us]` | microsegundos | **milisegundos** ❌ |

El mismo código producía unidades distintas según la máquina. Los parquets del sandbox
salieron bien; esta máquina los escribía en milisegundos **con el campo de microsegundos
sumado encima**.

Se detectó porque un test del fixture dio `1787101280000` donde el parquet real tenía
`1787101200080000`. Alcanzó a reescribir 4 sesiones antes de frenar. Ningún análisis
publicado los usó: la auditoría del reloj corrió sobre los parquets del sandbox.

Corregido con conversión explícita a `datetime64[us]` y **asercion dura de rango epoch**
que aborta si las unidades vuelven a correrse.

## 4.5 Reconversión completa — `MEASURED_COMMITTED`

Las 11 sesiones regeneradas desde los CSV originales, que nunca se tocaron:

- **125.181.415 filas**, coincidencia **exacta** con el conteo de líneas de cada CSV
- `source_row` presente en L1 y L2, monótono, sin huecos ni duplicados
- `ts_us` en microsegundos verificado en las 11
- 4,90 GB de CSV → 550 MB de parquet (−88,8 %)
- `20260821` sin L2, como ya declaraba el acta

**Los dos bloqueos de §4.1 y §4.2 quedan resueltos**, salvo el origen absoluto del reloj,
que sigue abierto y que **deja de ser bloqueante**: L1 y L2 comparten un solo reloj entre
sí, así que todo análisis interno del libro es válido sin resolverlo.

## 5. Estado

**La materia prima es buena.** Libro de manual, trades que cuadran con el export de ticks,
ask y bid simétricos, 10 niveles de profundidad con tamaño.

**Dos cosas hay que arreglar antes de medir nada**: el origen del reloj, y la columna de
orden de fila. Las dos son de ingeniería, no de dato — el dato está.

Y sigue vigente **P-56**: todo esto es holdout. Auditoría forense sí; señales, outcomes o
P&L **no**, sin autorización escrita.
