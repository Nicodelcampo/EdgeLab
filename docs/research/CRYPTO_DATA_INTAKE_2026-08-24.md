# Ingesta de datos crypto — Binance USD-M · BTCUSDT

- **Fecha:** 2026-08-24 · **Rama:** `work/crypto-context-foundation-20260824`
- **HEAD inicio:** `4f4829a9b3ad3c90866d25dcc598c60368f78df9`
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · retornos, P&L, MAE/MFE, labels y holdout **no accedidos**
- **Nada de este documento declara edge.**

---

## 1. MEDIDO

### 1.1 Disponibilidad oficial — el hallazgo que condiciona todo

Catálogo S3 oficial de Binance Data Vision, paginado completo:

| tipo | archivos | rango |
|---|---:|---|
| `futures/um/daily/trades/BTCUSDT/` | 2.542 | `2019-09-08` → **`2026-08-23`** |
| `futures/um/daily/bookTicker/BTCUSDT/` | 320 | `2023-05-16` → **`2024-03-30`** |

> **Binance dejó de publicar `bookTicker` diario de USD-M después del 2024-03-30.**
> `IsTruncated=false` en el listado, o sea que el catálogo está completo, no paginado a
> medias. Idéntico para ETHUSDT y SOLUSDT: los tres cortan el mismo día.

`trades` está al día; `bookTicker` lleva ~17 meses discontinuado.

### 1.2 Fechas elegidas — regla aplicada antes de mirar contenido

Regla: excluir el día UTC incompleto (`2026-08-24`), tomar los **dos días completos y
contiguos más recientes con ambos archivos disponibles**.

```
BTCUSDT  ->  2024-03-29  y  2024-03-30
ETHUSDT  ->  2024-03-29  y  2024-03-30
SOLUSDT  ->  2024-03-29  y  2024-03-30
```

Las fechas se registraron **antes** de inspeccionar métricas o contenido. No se
eligieron por cantidad de eventos ni por comportamiento del precio.

### 1.3 Descargas — los cuatro checksums oficiales coinciden

Base: `https://data.binance.vision/data/futures/um/daily/{kind}/BTCUSDT/`

| archivo | bytes | sha256 (12) | `.CHECKSUM` oficial |
|---|---:|---|:-:|
| `BTCUSDT-trades-2024-03-29.zip` | 24.514.449 | `b10ed9a4c565` | **coincide** |
| `BTCUSDT-bookTicker-2024-03-29.zip` | 119.997.573 | `c95c1d9afe1d` | **coincide** |
| `BTCUSDT-trades-2024-03-30.zip` | 12.403.562 | `a385248e48e3` | **coincide** |
| `BTCUSDT-bookTicker-2024-03-30.zip` | 87.758.829 | `6c6310b48a0d` | **coincide** |

HTTP 200 en los cuatro. `Content-Length` verificado contra bytes recibidos. Descarga
atómica `.part` → verificar → rename. Raw inmutable, fuera del repo.

Schema `trades`: `id,price,qty,quote_qty,time,is_buyer_maker`, con header.
Miembro del ZIP: `BTCUSDT-trades-YYYY-MM-DD.csv`.

### 1.4 Metadata del exchange

`https://fapi.binance.com/fapi/v1/exchangeInfo` · HTTP 200 · 1.077.489 B ·
sha256 `c23b0b2f24be5578…` · `timezone=UTC` · `serverTime=1787594411103`

| símbolo | status | `tickSize` | `stepSize` | `minQty` | `qtyPrecision` |
|---|---|---:|---:|---:|---:|
| BTCUSDT | TRADING | **0.10** | 0.001 | 0.001 | 3 |
| ETHUSDT | TRADING | 0.01 | 0.001 | 0.001 | 3 |
| SOLUSDT | TRADING | 0.0100 | 0.01 | 0.01 | 2 |

`tick_size = PRICE_FILTER.tickSize = 0.10` para BTCUSDT.

**`0.001` se usó como `PROVISIONAL_EXCHANGE_STEP_SIZE`**, y el manifest lo registra como
`quantity_unit_status = PROVISIONAL_USER_SUPPLIED`. **No es una unidad económica
validada**: es el incremento mínimo permitido y nada más.

### 1.5 Gates de integridad — resultado

| día | trades | book updates | joined | cobertura | strict-prior viol. | ID gaps | IDs faltantes |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-03-29 | 2.898.780 | 10.315.644 | 2.898.780 | **100,0000 %** | **0** | 20 | 20 |
| 2024-03-30 | 1.469.266 | 7.398.592 | 1.469.266 | **100,0000 %** | **0** | 8 | 8 |

- Join causal estricto `bookTicker.transaction_time < trade.time`: **0 violaciones**.
- Cobertura **completa**: ningún trade quedó sin book previo. No se invocó
  `--allow-partial-join`.
- `duplicate_trade_ids = 0` en ambos días.
- Book cruzado: **0** — ninguno abortó por esa causa.
- Acuerdo maker/quote: **100 %** sobre 2.891.659 y 1.466.509 trades clasificables.
- `outcomes_opened = false` en los dos manifests.

### 1.6 La anomalía off-tick — medida, **no explicada**

Escaneo exhaustivo de los dos días completos, `tick_size = 0.10`:

```
2024-03-29   2.898.786 trades   ->  6 fuera de tick
2024-03-30   1.469.267 trades   ->  1 fuera de tick
             4.368.053 total    ->  7   (0,00016 %)
```

**Primero se descartó que fuera un `tick_size` mal declarado:** sobre 400.000 precios de
muestra, **399.999 tienen exactamente 1 decimal**. `0.10` es correcto para estos
archivos. *No se bajó el tick a 0.01 para que pasara el gate* — eso habría sido ajustar
el parámetro al dato.

Los 7 tienen estructura:

| | |
|---|---|
| `qty` | **0.001 en los siete** (= `LOT_SIZE.minQty`) |
| precios | sólo **3 distintos**: `70428.34`×2 · `70344.83`×2 · `69856.92`×3 |
| `quote_qty` | `price × 0.001` exacto en los siete |

**Y aparece también del lado del book.** BTCUSDT 2024-03-29 abortó en
`book.bid = 70428.34`, uno de esos mismos tres precios. **13 filas de `bookTicker`
fuera de tick** ese día, 0 el 2024-03-30.

> Que la anomalía esté en **las dos fuentes** y en **los mismos precios** descarta
> corrupción del archivo de trades.

**No se afirma la causa.** Queda como hallazgo abierto.

### 1.7 Sensibilidad de unidad

**NO CORRIDA.** Sólo se materializó `1×` (`0.001`). Falta `0.5×` y `2×`.

---

## 2. INFERIDO

- Que `tickSize = 0.10` regía en 2024-03 se infiere de la granularidad observada
  (99,99975 % con 1 decimal), **no** de metadata histórica.
- Que la anomalía off-tick es del venue y no del archivo se infiere de su presencia
  simultánea en `trades` y `bookTicker` con los mismos precios.

## 3. ESTIMADO

- Nada relevante. Todos los tamaños y conteos de §1 son medidos.

## 4. NO MEDIDO

- **Metadata histórica de 2024-03.** El `exchangeInfo` congelado es **vigente al
  2026-08-24**. Binance no publica `exchangeInfo` histórico en Data Vision. El
  bloqueante #1 del contrato causal **sigue abierto**.
- **Causa de los 7 off-tick.**
- **Los 20 y 8 ID gaps** — cuantificados, no explicados. No son los «siete gaps del
  piloto original» del bloqueante #2: ese número no reaparece acá.
- **ETHUSDT y SOLUSDT** — descargados no; el piloto no corrió.
- **Sensibilidad `0.5× / 2×`.**
- **Cualquier variable de respuesta.**

---

## 5. Modo diagnóstico invocado ⚠

Los dos días corrieron **sólo con `--allow-offtick-prices`**, que es un modo declarado y
apagado por default.

```
offtick_exclusion_invoked = true   en los dos dias
n_offtick_prices_excluded      = 6  /  1
n_offtick_book_rows_excluded   = 13 /  0
```

Por contrato, **un modo de diagnóstico parcial no se promueve**. Estas corridas no
cuentan como paso limpio de los gates: cuentan como diagnóstico con exclusiones
declaradas y contadas.

**Por eso no se avanzó a ETHUSDT.** La regla es avanzar sólo si los gates pasan, y acá
pasaron con una excepción invocada.

---

## 6. Procedencia

Datos grandes **fuera del repo**, en `raw/ · staging/ · derived/ · manifests/ · logs/`.
No se commiteó ningún ZIP, CSV ni Parquet.

Salidas por día: `BTCUSDT_bt2_ticks.parquet`, `BTCUSDT_bt2_sidecar.parquet`,
`BTCUSDT_bt2_manifest.json`, con hashes de inputs y outputs y procedencia HEAD
dirty-aware.

---

## 7. Próximos pasos

1. **Decidir si el modo con exclusiones autoriza avanzar a ETHUSDT.** Es decisión de
   contrato, no mía. La lectura literal dice que no.
2. **Sensibilidad de unidad `0.5× / 2×`** sobre los dos días ya materializados.
3. **Bloqueante #1**: conseguir metadata histórica de 2024-03 o declarar por escrito que
   se acepta la inferencia de §2.
4. **Captura forward de `bookTicker`** si se quieren fechas recientes — ver §8.

## 8. Sobre `bookTicker` reciente

No existe histórico oficial después de `2024-03-30`. Opciones, con sus límites:

| opción | límite |
|---|---|
| WebSocket `<symbol>@bookTicker` a archivo | sólo hacia adelante; nada de 2024-04 → 2026-08 |
| `futures/um/daily/bookDepth/` | snapshots de profundidad, **no** es el mismo objeto que BBO |
| terceros (Tardis, Amberdata, Kaiko) | **fuera de fuente oficial; requiere autorización** |

**No se fabricó el book.** No se sustituyó por klines, aggTrades ni mark price.

---

## Aporte al referente

Queda medido y con checksum oficial que el par `trades + bookTicker` de USD-M sólo existe
hasta `2024-03-30`, lo que acota de entrada cualquier programa crypto que dependa del BBO
histórico. Y queda documentada una anomalía de microestructura —7 prints fuera de la
grilla de tick, con `qty` exactamente en el mínimo, presentes en trades **y** en book—
que el pipeline detectó porque falla cerrado en vez de redondear.

## Nota de método

El gate de tick disparó y la primera hipótesis natural era «el `tickSize` de 2024 era
otro». Medir la distribución de decimales antes de tocar el parámetro la descartó en un
comando: 399.999 de 400.000 con un decimal. La tentación concreta era bajar el tick a
`0.01`, que habría hecho pasar el gate y **habría convertido siete anomalías reales en
cero**, borrando el hallazgo en vez de encontrarlo.
