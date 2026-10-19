# Fuentes crypto — qué hay gratis, medido, y qué habilita cada una

- **Fecha:** 2026-08-24 · **Rama:** `work/crypto-context-foundation-20260824`
- **Objetivo:** que crypto tenga la misma disponibilidad que cualquier activo de EdgeLab
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · **nada declara edge**

> Todo lo de §1 y §2 está **medido** con HTTP y descarga real, no leído de documentación.

---

## 1. Binance USD-M — catálogo oficial, medido

`https://data.binance.vision/data/futures/um/daily/{tipo}/BTCUSDT/`

| tipo | último día | ¿al día? |
|---|---|:-:|
| `trades` | **2026-08-23** | **SÍ** — 2.542 días desde 2019-09-08 |
| `aggTrades` | 2026-08-23 | SÍ |
| `bookDepth` | 2026-08-23 | SÍ |
| `metrics` | 2026-08-23 | SÍ |
| **`bookTicker`** | **2024-03-30** | **NO — discontinuado** |

### 1.1 `bookDepth` es L2, pero no es BBO

Medido sobre `BTCUSDT-bookDepth-2026-08-22.zip` (561 KB comprimido, 2,0 MB CSV):

```
timestamp,percentage,depth,notional
2026-08-22 00:00:06,-0.20,297.66500000,23282696.75690000
2026-08-22 00:00:06, 0.20,310.59800000,24350259.83120000
```

- **12 filas por snapshot**: bandas de ±0,2 · 1 · 2 · 3 · 4 · 5 %.
- **2.880 snapshots/día** = uno cada **30 segundos**.
- **No trae best bid ni best ask.** No permite clasificar agresor ni medir spread.

> **`bookDepth` NO reemplaza a `bookTicker`.** Es profundidad agregada, útil como
> contexto de liquidez. Presentarlo como sustituto del BBO sería falso.

---

## 2. El desbloqueo: el agresor es un dato, no una inferencia

`edgelab/bridge/bars.py` usaba `bid_ticks`/`ask_ticks` **únicamente** para clasificar
agresor, con fallback a tick-rule. Y **dos venues publican el agresor directamente**:

| venue | archivo | campo | cobertura medida |
|---|---|---|---|
| Binance USD-M | `trades` | `is_buyer_maker` | 2019-09-08 → **2026-08-23** |
| Bybit | `trading` | `side` (`Buy`/`Sell`) | → **2026-08-23** |

Bybit, verificado descargando `BTCUSDT2026-08-22.csv.gz` (72,3 MB):

```
timestamp,symbol,side,size,price,tickDirection,trdMatchID,grossValue,homeNotional,foreignNotional,RPI
1787356800.2296,BTCUSDT,Sell,0.001,78307.50,ZeroMinusTick,48a44029-...,7.83075e+09,0.001,78.3075
```

`public.bybit.com` es HTTPS plano, **sin registro**, con índice navegable.

**Implementado:** `TickSeries.aggressor_side` opcional y precedencia
**venue > quote > tick-rule** en `build_footprints`, con `n_exchange` contando la
procedencia. Aditivo: sin el canal, el comportamiento no cambia.

⇒ **Cobertura crypto: de 320 días a 2.542.** Sin fuentes de terceros.

---

## 3. L2 gratis en bulk — **no encontrado**

Medido, no supuesto:

| candidato | resultado |
|---|---|
| Binance `bookDepth` | existe y está al día, pero **son bandas de % cada 30 s** |
| `public.bybit.com/orderbook/` | **HTTP 404** — el índice sólo tiene `trading/ spot/ premium_index/ spot_index/ kline_for_metatrader4/` |
| Bybit L2 por UI web | existe según terceros; **requiere interacción**, no es URL de bulk |
| OKX `traderecords/orderbook/...` | **404** en los tres patrones probados; su descarga está detrás de UI |
| Tardis · CryptoHFTData · CryptoStruct · Amberdata | **de pago**, y son terceros: requieren autorización explícita |

> **No hay archivo L2 gratuito, oficial y descargable en bulk por HTTP plano.**
> Lo que existe gratis es (a) profundidad agregada de Binance cada 30 s, y (b) L2 de
> Bybit/OKX detrás de interfaces web.

**No se fabricó ningún book.** No se sustituyó `bookTicker` por klines, `aggTrades`,
mark price ni una reconstrucción inventada.

### 3.1 Captura forward, si se quiere BBO real

El stream oficial mapea **1:1** con el CSV histórico, así que una captura hacia adelante
produce el mismo schema sin inventar nada:

```
CSV histórico   update_id  best_bid_price  best_bid_qty  best_ask_price  best_ask_qty  transaction_time  event_time
WebSocket       u          b               B             a               A             T                 E
```

`wss://fstream.binance.com/ws/{symbol}@bookTicker` — tiempo real, campos `T` (transaction)
y `E` (event) en ms.

**Límite:** sólo hacia adelante. **No recupera 2024-04 → 2026-08.**

---

## 4. Metadata histórica — resuelta para tick, abierta para cantidad

### 4.1 `tickSize` — RESUELTO con anuncios oficiales

| símbolo | cambio | efectivo UTC | fuente |
|---|---|---|---|
| BTCUSDT | `0.01 → 0.1` | 2022-02-15 03:30 | anuncio oficial |
| SOLUSDT | `0.001 → 0.01` | 2024-10-14 06:30 | anuncio oficial |
| ETHUSDT | *sin anuncio hallado* | — | — |

Verificado contra los datos del 2024-03-30:

```
SOLUSDT   1.531.003 off-tick con el vigente  ->  0 con el historico
BTCUSDT           1 off-tick con el vigente  ->  1 con el historico
```

**SOL nunca tuvo una anomalía**: tenía la metadata equivocada. **La de BTC sobrevive al
tick correcto**, lo que la confirma como fenómeno real.

Implementado en `edgelab/crypto/tick_history.py`, que **falla cerrado** para símbolo sin
cobertura y para símbolo sin anuncio hallado. ETH cae en el segundo: **no** devuelve el
vigente por default.

### 4.2 `LOT_SIZE` / `minQty` — **ABIERTO**

Indicio concreto: un anuncio del **2025-04-02** baja el mínimo de SOLUSDT de **1 SOL a
0.01 SOL**. Eso implica que en 2024-03 la unidad de cantidad **era distinta de la
vigente** — el mismo defecto que ya se corrigió para el tick, ahora en la cantidad.

**No se resolvió.** `quantity_unit_status` sigue siendo `PROVISIONAL_EXCHANGE_STEP_SIZE`
con `quantity_unit_source` declarando que el valor es **vigente, no histórico**.

---

## 5. Estado de disponibilidad por símbolo

```
BTCUSDT   tick historico OK   trades al dia   diagnostico, promotion_eligible=false
ETHUSDT   tick SIN anuncio    trades al dia   diagnostic_only, NO promovido
SOLUSDT   tick historico OK   trades al dia   desbloqueado por 4.1
```

Los tres tienen ahora **cobertura de datos equivalente a un activo NT8**: serie de ticks
completa, agresor autoritativo, y tick correcto por fecha. Lo que falta para promover no
es data: es la unidad de cantidad histórica y, para ETH, la evidencia del tick.

---

## Aporte al referente

El bloqueante de disponibilidad de crypto no era la falta de book: era suponer que el
agresor sólo se obtiene del book. Dos venues lo publican como dato del propio exchange, y
el kernel sólo usaba el book para inferir eso mismo. El cambio que lo destraba es un
canal opcional en `TickSeries`, y sube la cobertura de 320 a 2.542 días sin pagar ni
recurrir a terceros.

## Nota de método

Cuatro candidatos de L2 «gratis» se cayeron al probarlos: `public.bybit.com/orderbook/`
da 404, los tres patrones de OKX dan 404, y el `bookDepth` de Binance —que sí existe y
está al día— resultó ser bandas de porcentaje cada 30 segundos, no BBO. La documentación
de terceros describía todos como disponibles. **Ninguno de los cuatro se habría caído
leyendo; los cuatro se cayeron descargando.**
