# Arquitectura de Traducción y Paridad con NinjaTrader 8 Strategy Analyzer y Ejecución de Canastas de Regímenes (`2026-10-29`)

## 1. Diagnóstico de Paridad entre `edgelab/research/analizador.py` (`grilla_generica`) y NinjaTrader 8 Strategy Analyzer

Para garantizar que cada edge descubierto y validado en EdgeLab (`ACTA_HOLDOUT` o `PISTAS_VIVAS`) produzca **exactamente el mismo resultado** al trasladarse a una `Strategy` de NinjaTrader 8 (o a un motor de ejecución en vivo/VPS), auditamos las 5 dimensiones mecánicas donde suelen divergir los motores de investigación y las plataformas de ejecución:

| Dimensión de Ejecución | Motor de Grilla (`areas_expansion.simular`) | Motor Secuencial (`analizador.Mercado.simular` / NT8 Strategy) | Mecanismo de Paridad 1-a-1 Implementado (`paridad_nt8_canastas.py` + `EdgeLabSpiralBasketExecutor.cs`) |
|---|---|---|---|
| **1. Superposición de posiciones en una misma regla (`Flat-Only`)** | Evalúa cada disparo `t` de la celda en paralelo aunque una operación previa de esa misma celda siga abierta en la sesión. | Con `EntriesPerDirection = 1` (`MarketPosition.Flat`), rechaza cualquier señal nueva mientras la posición previa siga abierta (`if i <= abierta: continue`). | `filtrar_solapadas_nt8(ops_df, duracion_s=900)` en Python y `if (slot.Direction != 0) return false;` por slot virtual en `EdgeLabSpiralBasketExecutor.cs`. |
| **2. Llenado de órdenes Límite y Objetivos (`Trade-Through`)** | Exige **1 tick de cruce real** (`low <= limit - tick` en compra, `high >= limit + tick` en venta) dentro de `120` barras M1; resuelve la barra del llenado tick a tick (`_primero_en_ticks`). | En NT8 por defecto, una orden límite puede llenarse al simple toque si no se modela la cola FIFO. | La grilla de EdgeLab ya exige **1 tick de trade-through** en entradas límite y en `TargetPrice` (`hi >= TargetPrice + tk` / `lo <= TargetPrice - tk`), por lo que el backtest de EdgeLab es **estrictamente más conservador** que el llenado optimista por toque de NT8. |
| **3. Momento de entrada a mercado (`E1A` vs `E1C`)** | `E1C` (`limite=0`) entra al cierre `c[k]`; `E1A` (`limite=2`) entra en el primer tick de la barra siguiente `o[k+1]`. | Con `Calculate = Calculate.OnBarClose`, `EnterLong()` enviado en `OnBarUpdate()` se llena en el **primer tick de la barra `k+1`** (`E1A`). | Para `E1A` y entradas Límite (`E2`/`E3`), `Calculate.OnBarClose` en NT8 es **100% idéntico**; para `E1C`, se evalúa al último tick de la barra o se verifica que pasa el control de `latencia 1 vela` en `INTEGRIDAD`. |
| **4. Tope de pérdida por construcción (`aplicar_tope`) y `Break-Even` (`BE=1`)** | `aplicar_tope` acota `|e - st| <= d_max` redondeando siempre hacia la entrada (`ceil` en compra, `floor` en venta). `BE=1` se arma al cierre de la primera barra M1 cuya excursión alcance `>= 1R`. | Si el `StopLoss` se mueve intrabar sin esperar el cierre de M1, puede saltar prematuramente en mechas. | `EdgeLabSpiralBasketExecutor.ApplyConservativeStopCap` replica el redondeo exacto (`Math.Ceiling` / `Math.Floor`) y arma el `Break-Even` únicamente al cierre de la barra M1 en `OnBarUpdate()`. |
| **5. Cruce Sensor CFD -> Ejecución Futuro (`DK:... -> NQ/ES/GC`)** | `_trasladar` calcula la base instantánea `base = c_ej[j] - c_sensor[k]` al cierre del minuto `k` y redondea el stop hacia afuera. | Requiere serie secundaria o sidecar que entregue niveles ya trasladados al futuro de ejecución. | En NT8 se añade la serie secundaria o el sidecar Python calcula `base = Close_Futuro - Close_CFD` al cierre M1 antes de invocar `TrySubmitSignal(...)`. |

---

## 2. Resultados Empíricos de Paridad NT8 (`EntriesPerDirection = 1`, `Flat-Only`) en Ventana OOS (`2026-04-01 .. 2026-09-30`)

### 2.1. Las 6 Reglas Individuales con `ACTA_HOLDOUT.json` (Listas para Ventana Sellada `>= 2026-10-01`)

| Campaña (`cid`) | Instrumento (`Valor/pt Micro`) | Celda Ganadora + Tope | `n` (Grilla -> NT8 Flat) | Paridad Ops (`%`) | P&L Neto Grilla (`pts`) | **P&L Neto NT8 Flat (`pts`)** | **Media NT8 (`pts/op`)** | **Profit Factor NT8** | **Max DD NT8 (`pts`)** | **P&L Neto `1 Micro` (`USD`)** | **P&L Neto `1 Mini` (`USD`)** |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`CVGAP-NQ`** | `NQ -> NQ` (`$2 / $20`) | `[0,0,1,2,2,2,3,2,0,2,11]` (`mult:4.0`) | `88 -> 81` | `92.0%` | `+1,683.75` | **`+1,425.06`** | **`+17.59`** | **`1.65`** | `-399.98` | **`+$2,850.12`** | **`+$28,501.20`** |
| **`CVGAP-CFD-NQ`** | `USATECH -> NQ` (`$2 / $20`) | `[0,1,0,0,2,3,2,1,2,0,10]` (`pts:50`) | `110 -> 108` | `98.2%` | `+1,155.25` | **`+947.34`** | **`+8.77`** | **`1.30`** | `-480.34` | **`+$1,894.68`** | **`+$18,946.80`** |
| **`U1-RACIMOS-GRILLA-NQ`** | `NQ -> NQ` (`$2 / $20`) | `[1,0,0,9,1,0]` (`pts:100`) | `13 -> 13` | **`100.0%`** | `+257.16` | **`+257.16`** | **`+19.78`** | **`2.60`** | `-129.34` | **`+$514.32`** | **`+$5,143.20`** |
| **`U1-ZONAS-BT2-ES`** | `ES -> ES` (`$5 / $50`) | `[0,2,0,2,2,2,1,3,1,0,0,6]` (`pts:50`) | `29 -> 29` | **`100.0%`** | `+71.74` | **`+71.74`** | **`+2.47`** | **`2.59`** | `-43.46` | **`+$358.70`** | **`+$3,587.00`** |
| **`U1-RACIMOS-GRILLA-ES`** | `ES -> ES` (`$5 / $50`) | `[0,0,0,16,2,2]` (`pts:50`) | `46 -> 43` | `93.5%` | `-24.71` | **`+52.55`** | **`+1.22`** | **`1.17`** | `-93.18` | **`+$262.75`** | **`+$2,627.50`** |
| **`U1-ZONAS-BT2-NQ`** | `NQ -> NQ` (`$2 / $20`) | `[0,2,0,1,2,2,3,2,3,0,0,4]` (`pts:50`) | `42 -> 40` | `95.2%` | `-734.41` | `-767.57` | `-19.19` | `0.61` | `-870.73` | `-$1,535.14` | `-$15,351.40` |
| **Subtotal 5 Reglas OOS+** | `MNQ + MES` | `5 Reglas Confirmadas en OOS` | `286 -> 274` | **`95.8%`** | — | — | — | **`1.58`** | **`-$995.20`** | **`+$5,880.57`** | **`+$58,805.70`** |

> **Hallazgo clave en `U1-RACIMOS-GRILLA-ES`:** Al aplicar el bloqueo `EntriesPerDirection = 1` (`Flat-Only`) de NinjaTrader 8, las 3 operaciones solapadas que ocurrían durante barridos tendenciales se eliminan automáticamente y la regla pasa de `-24.71 pts` en grilla cruda a **`+52.55 pts` (`PF = 1.17`, `+$262.75` en `1 MES` / `+$2,627.50` en `1 ES`)** en OOS.

---

### 2.2. Las 10 Mejores Reglas Individuales OOS de las Olas 7–10 (`PISTAS_VIVAS`)

En las familias `ASIA-BOS-GAPS`, `OTR-930-SWEEP`, `ORO-ALMUERZO-RUPTURA`, `CONFLUENCIA-CVGAP-RACIMOS` y `TORI-TREND-TOQUE3`, la estructura del disparador (a lo sumo un barrido por ventana horaria o un 3er toque de línea de tendencia con enfriamiento de 4 horas) produce una **paridad del `96.6%` al `100.0%` con NinjaTrader 8 Strategy Analyzer**:

| Campaña (`cid`) | Instrumento (`Micro`) | Mejor Celda OOS | `n` (Grilla -> NT8 Flat) | Paridad NT8 | **P&L Neto NT8 (`pts`)** | **Media NT8 (`pts/op`)** | **Profit Factor** | **Max DD (`pts`)** | **P&L Neto `1 Micro` (`USD`)** | **P&L Neto `1 Mini` (`USD`)** |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`ASIA-NQ`** | `NQ` (`MNQ $2/pt`) | `[1,0,0,2,1,3,3,2,2,3]` | `18 -> 18` | **`100.0%`** | **`+998.43`** | **`+55.47`** | **`4.02`** | `-136.55` | **`+$1,996.86`** | **`+$19,968.60`** |
| **`OTR930-CFD-NQ`** | `USATECH->NQ` (`MNQ $2/pt`) | `[1,1,2,2,0,0,3,2,2,2]` | `58 -> 56` | **`96.6%`** | **`+1,008.70`** | **`+18.01`** | **`1.52`** | `-454.82` | **`+$2,017.40`** | **`+$20,174.00`** |
| **`OTR930-NQ`** | `NQ` (`MNQ $2/pt`) | `[0,1,1,0,3,3,0,1,1,10]` | `26 -> 26` | **`100.0%`** | **`+779.32`** | **`+29.97`** | **`1.60`** | `-509.11` | **`+$1,558.64`** | **`+$15,586.40`** |
| **`CONF-CVR-NQ`** | `NQ` (`MNQ $2/pt`) | `[1,1,0,1,0,2,0,1,2,3]` | `79 -> 79` | **`100.0%`** | **`+531.66`** | **`+6.73`** | **`1.25`** | `-668.34` | **`+$1,063.32`** | **`+$10,633.20`** |
| **`ASIA-CFD-NQ`** | `USATECH->NQ` (`MNQ $2/pt`) | `[0,2,1,2,2,2,1,0,0,1]` | `15 -> 15` | **`100.0%`** | **`+348.32`** | **`+23.22`** | **`2.04`** | `-182.68` | **`+$696.64`** | **`+$6,966.40`** |
| **`CONF-CVR-CFD-NQ`** | `USATECH->NQ` (`MNQ $2/pt`) | `[0,2,2,0,2,0,2,0,2,2]` | `31 -> 31` | **`100.0%`** | **`+305.09`** | **`+9.84`** | **`2.47`** | `-107.09` | **`+$610.18`** | **`+$6,101.80`** |
| **`ORO-ALM-GC`** | `GC` (`MGC $10/pt`) | `[1,2,3,2,1,0,0,2,1,11]` | `18 -> 18` | **`100.0%`** | **`+252.01`** | **`+14.00`** | **`2.49`** | `-50.61` | **`+$2,520.10`** | **`+$25,201.00`** |
| **`ASIA-GC`** | `GC` (`MGC $10/pt`) | `[1,1,0,2,0,1,0,1,1,1]` | `33 -> 33` | **`100.0%`** | **`+193.73`** | **`+5.87`** | **`1.75`** | `-113.14` | **`+$1,937.30`** | **`+$19,373.00`** |
| **`CVGAP-ES`** | `ES` (`MES $5/pt`) | `[0,1,1,2,2,2,3,2,0,2,11]` | `14 -> 14` | **`100.0%`** | **`+134.32`** | **`+9.59`** | **`2.05`** | `-112.05` | **`+$671.60`** | **`+$6,716.00`** |
| **`TORI-GC`** | `GC` (`MGC $10/pt`) | `[2,0,1,0,1,0,0,2,0,1]` | `44 -> 44` | **`100.0%`** | **`+91.18`** | **`+2.07`** | **`1.52`** | `-48.07` | **`+$911.80`** | **`+$9,118.00`** |
| **Total Portafolio 10 Campeonas** | `MNQ + MES + MGC` | `1 Micro por Familia/Activo` | `336 -> 334` | **`99.4%`** | — | — | **`1.79`** | **`-$1,142.00`** | **`+$13,983.84`** | **`+$139,838.40`** |

---

### 2.3. Las 11 Canastas de Regímenes OOS Positivas (`20 Pistas por Canasta`: `M1 Subcuentas Virtuales 1/K` vs `M2 Cuenta Única Flat-Only`)

| Canasta (`cid`) | Activo Ejecución (`Micro`) | Sesiones OOS | **Modo `M1` (`Subcuentas Virtuales 1/20`) P&L `1x` (`pts`)** | **Modo `M1` Suma `20 Pistas` (`pts`)** | **Modo `M1` Media (`pts/op`)** | **Modo `M2` (`Cuenta Única Flat Global`) Ops** | **Modo `M2` P&L Neto (`pts`)** | **Modo `M2` Media (`pts/op`)** | **Modo `M2` `1 Micro` (`USD`)** |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`OTR930-NQ`** | `NQ` (`MNQ $2`) | `94` | **`+498.19`** | `+9,963.80` | `+17.18` | `129` | **`+980.63`** | `+7.60` | **`+$1,961.26`** |
| **`ASIA-NQ`** | `NQ` (`MNQ $2`) | `102` | **`+446.62`** | `+8,932.40` | `+11.74` | `180` | **`+2,004.56`** | `+11.14` | **`+$4,009.12`** |
| **`OTR930-CFD-NQ`** | `NQ` (`MNQ $2`) | `102` | **`+324.12`** | `+6,482.40` | `+3.77` | `142` | **`+125.04`** | `+0.88` | **`+$250.08`** |
| **`ASIA-CFD-NQ`** | `NQ` (`MNQ $2`) | `100` | **`+180.80`** | `+3,616.00` | `+6.20` | `103` | **`+545.06`** | `+5.29` | **`+$1,090.12`** |
| **`CVGAP-ES`** | `ES` (`MES $5`) | `65` | **`+87.15`** | `+1,743.00` | `+2.84` | `119` | **`+163.36`** | `+1.37` | **`+$816.80`** |
| **`CONF-CVR-CFD-NQ`** | `NQ` (`MNQ $2`) | `119` | **`+40.54`** | `+810.80` | `+0.67` | `380` | **`+330.96`** | `+0.87` | **`+$661.92`** |
| **`TORI-GC`** | `GC` (`MGC $10`) | `123` | **`+34.26`** | `+685.20` | `+0.69` | `170` | **`+1.45`** | `+0.01` | **`+$14.50`** |
| **`OTR930-CFD-ES`** | `ES` (`MES $5`) | `86` | **`+31.09`** | `+621.80` | `+0.93` | `113` | **`+77.44`** | `+0.69` | **`+$387.20`** |
| **`OTR930-ES`** | `ES` (`MES $5`) | `52` | **`+23.28`** | `+465.60` | `+0.86` | `55` | `-22.57` | `-0.41` | `-$112.85` |
| **`ORO-ALM-CFD`** | `GC` (`MGC $10`) | `52` | **`+21.91`** | `+438.20` | `+1.96` | `64` | **`+313.68`** | `+4.90` | **`+$3,136.80`** |
| **`ORO-ALM-GC`** | `GC` (`MGC $10`) | `37` | **`+7.44`** | `+148.80` | `+0.49` | `51` | `-36.35` | `-0.71` | `-$363.50` |

---

## 3. Cómo Ejecutar las Canastas de Regímenes en el Mercado Real (`EdgeLabSpiralBasketExecutor.cs` + Sidecar Causal)

Cuando una campaña queda en `PISTAS_VIVAS` (o se aprueba por `tools/holdout_canasta.py`), el edge no reside en una única celda aislada sino en el **ensamble de celdas que se activan en distintos sub-regímenes** (volatilidad alta vs. media, compresión asiática estrecha vs. amplia, impulso con muchos gaps vs. pocos gaps).

### 3.1. Dos Modos de Ejecución Soportados en `nt8/strategies/EdgeLabSpiralBasketExecutor.cs`

1. **Modo `M1` — Multiplexador de Subcuentas Virtuales con Netting en Micro-Futuros (`VirtualSubAccountsNetting`)**:
   - **Cuándo usarlo:** Cuentas con holgura de contratos en micro-futuros (`MNQ`, `MES`, `MGC`) o cuando se selecciona un subconjunto descorrelacionado `Top-K` (`K = 3` a `5` pistas no redundantes de la canasta).
   - **Cómo funciona:** La estrategia de NT8 mantiene en memoria `K` máquinas de estado independientes (`VirtualSlot[0..K-1]`). Cada pista `i` tiene su propio candado `Flat-Only` (`slot.Direction != 0`), su propio `StopPrice` con `ApplyConservativeStopCap`, su propio `TargetPrice` (con exigencia de `1 tick` de trade-through) y su propio armado de `Break-Even` al cierre de `+1R`. En cada cambio de estado, `SyncNetPositionWithMarket()` calcula `targetNetContracts = sum(slot.Direction * ContractsPerSlot)` y envía una sola orden por la diferencia neta a la cuenta de NinjaTrader 8.
   - **Ventaja clave:** Evita pagar doble spread/comisión cuando dos pistas opuestas se cruzan y elimina el bloqueo de órdenes OCO múltiples sobre una misma cuenta de NT8.

2. **Modo `M2` — Bloqueo Global `Flat-Only` Priorizado por Rango (`SingleGlobalFlatLock`, `1 Contrato Total`)**:
   - **Cuándo usarlo:** Challenges de prop firms con límite estricto de contratos o drawdown trailing ajustado (donde sólo se desea tener **1 micro o 1 mini abierto a la vez** por familia/activo).
   - **Cómo funciona:** Las `K` pistas de la canasta actúan como una **red de sensores complementarios** ordenados por su puntaje en `DESC`. Mientras la estrategia está `Flat`, la primera pista de la canasta cuyo sub-régimen dispara toma el único slot disponible (`1 MNQ`, `1 MES` o `1 MGC`); mientras esa operación está viva, las demás pistas quedan en espera hasta que cierre por `Target`, `Stop` o `Time-Stop`.
   - **Evidencia empírica en OOS (`2026-04-01 .. 2026-09-30`):** Con **un solo contrato `1 MNQ` o `1 MGC` abierto a la vez (`M2`)**, `ASIA-NQ` generó **`+2,004.56 pts` (`+$4,009.12` en `1 MNQ` / `+$40,091.20` en `1 NQ`, `180` ops, `+11.14 pts/op`)**, `OTR930-NQ` generó **`+980.63 pts` (`+$1,961.26` en `1 MNQ`)**, `ASIA-CFD-NQ` generó **`+545.06 pts` (`+$1,090.12` en `1 MNQ`)** y `ORO-ALM-CFD` generó **`+313.68 pts` en GC (`+$3,136.80` en `1 MGC`)**.

3. **Compuerta Causal de Régimen al Inicio de Sesión (`RegimeStateFilePath`)**:
   - Antes de la apertura de cada sesión (`Bars.IsFirstBarOfSession`), `EdgeLabSpiralBasketExecutor.cs` recarga el archivo `RegimeStateFilePath` generado por `edgelab/research/persistencia.py` / `regimen.py`, que contiene los IDs de los slots habilitados para la sesión según el régimen causal ex-ante (`rango_sesion_previa`, `vol_diaria`, `eficiencia`), sin mirar jamás datos intradía futuros.
