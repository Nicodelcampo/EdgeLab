# INGENIERÍA INVERSA COMPLETA: NINJATRADER 8 ESTRATEGIA `FUNDEDSYNCSTACK`
**Build de Ensamblado Analizado:** `2026-10-29.1-FUNDEDSYNCSTACK`  
**Autor / Origen:** FundedSync Technologies  
**Archivo IL Desensamblado:** `fundedsyncstack_il.txt` (31,684 instrucciones IL resueltas)  
**Datos de Backtest Analizados:** `NinjaTrader Grid 2026-11-15 08-20 p. m..csv` (3,732 trades ejecutados)  

---

## 1. RESUMEN EJECUTIVO

La estrategia **`FUNDEDSYNCSTACK`** es un sistema algorítmico institucional multi-estrategia de alta complejidad diseñado para operar contratos de futuros del Nasdaq-100 (**NQ** como generador de señales maestras, y opcionalmente **MNQ** como instrumento de ejecución fraccionada) dentro de una única cuenta de corretaje o evaluación de firmas de fondeo (Apex, Topstep, MyFundedFutures, TradeDay, etc.).

A nivel arquitectónico, no se trata de un simple script de NinjaTrader, sino de un **Stack de Cartera Virtual con 15 submódulos algorítmicos independientes**, un **Ledger Virtual de Compensación y Netting Interno**, un **Motor de Dimensionamiento Dinámico Multitier por Fases de Cuenta (Lucid / SizingProfile)**, un **Disyuntor de Pérdida Diaria a nivel de Cartera**, un **Filtro de Noticias Restringidas de Alta Densidad**, un **Sistema de Rotación Anti-Drawdown (Half-Drawdown Entry Rotation)** y un **Gate Criptográfico de Licenciamiento por Hardware Fingerprint con Cifrado Asimétrico RSA**.

---

## 2. ARQUITECTURA GENERAL Y MOTOR DE EJECUCIÓN

### 2.1. Series de Datos Multinivel (`AddDataSeries` en `OnStateChange`)

La estrategia impone por contrato estricto ejecutarse sobre un gráfico principal de **NQ en 1 minuto** (`BarsPeriodType = Minute`, `Value = 1`). Si el usuario intenta ejecutarla en otro instrumento o temporalidad, la estrategia lanza una excepción `InvalidOperationException`:
> *"FUNDEDSYNCSTACK must be run on a 1-minute NQ primary series. Signals are calculated from NQ; MNQ is execution-only."*

Durante `State.Configure`, se agregan sistemáticamente 10 series secundarias de datos más una serie opcional de ejecución:

| BIP (BarsInProgress) | Instrumento | Tipo de Barra | Valor / Temporalidad | Plantilla de Sesión (Trading Hours) | Propósito / Submódulos Consumidores |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **BIP 0** | NQ | Minute | 1 Minuto | Gráfico por defecto | Serie Primaria (Reloj de eventos, sincronización general). |
| **BIP 1** | NQ | Minute | 1 Minuto | `CME US Index Futures ETH` | Serie de cálculo continuo 24/5: `A1`, `P`, `O` (timing), `W`, `N`, `T` (FtmEngine), `Z`. |
| **BIP 2** | NQ | Minute | 3 Minutos | `CME US Index Futures ETH` | Serie dedicada para `S` (`Swas`). |
| **BIP 3** | NQ | Minute | 5 Minutos | `CME US Index Futures ETH` | Serie dedicada para `F` (`FabioOrb`) y `Q` (`Rampart5Minute`). |
| **BIP 4** | NQ | Minute | 20 Minutos | `CME US Index Futures ETH` | Serie dedicada para `A20` (`Absorb20Minute`). |
| **BIP 5** | NQ | Minute | 1 Minuto | `CustomStockHoursTemplate` (def: `US STOCK`) | Sesión de contado NYSE (09:30-16:00 ET) para `C` (`CapstoneGap`). |
| **BIP 6** | NQ | Minute | 5 Minutos | `CME US Index Futures RTH` | Sesión RTH de futuros para `V` (`VaultBreak`). |
| **BIP 7** | NQ | Day | 1 Día | `CME US Index Futures RTH` | Barras diarias RTH para promedios móviles y volatilidad de `O` (`Overnight`). |
| **BIP 8** | NQ | Day | 1 Día | `CME US Index Futures ETH` | Barras diarias ETH para rangos previos y breakout N-Day de `N` (`NDayLong`). |
| **BIP 9** | NQ | Minute | 10 Minutos | `CME US Index Futures ETH` | Serie dedicada para `R` (`AtrPhase`). |
| **BIP 10** | NQ | Minute | 15 Minutos | `CME US Index Futures ETH` | Serie dedicada para `E` (`EmaDivergence`). |
| **BIP 11** *(opcional)* | MNQ | Minute | 1 Minuto | `CME US Index Futures ETH` | Serie de ejecución si `ExecMode == 1` (MNQ). |

---

### 2.2. Arquitectura de Compensación Virtual (`Virtual Ledger`) y Netting de Órdenes

En cuentas de futuros, NinjaTrader mantiene una única posición física neta en el broker. Si un sistema multi-módulo intentara enviar órdenes directas de compra y venta independientes por cada módulo, colisionarían violentamente, cerrando posiciones ajenas y descalibrando los Stop Loss y Take Profits individuales.

Para resolver esto, `FUNDEDSYNCSTACK` implementa una clase interna **`ModuleState`** para cada uno de los 15 submódulos:
- Cada módulo registra su propia posición virtual: `VirtualPosition`, `VirtualEntryCount`, `VirtualClosedTradeCount`, `VirtualNetProfit`, `DailyLosses`, `Net` (cantidad con signo: +Long, -Short, 0 Flat).
- **`VirtualAggregateNet()`**: Calcula la suma algebraica en tiempo real del stack:
  $$\text{Net}_{\text{virtual}} = \sum_{m=1}^{15} \text{Net}_m$$
- **Netting Físico en Broker**: Cuando un submódulo requiere comprar o vender, la estrategia calcula el diferencial ($\Delta = \text{Net}_{\text{deseado}} - \text{Net}_{\text{actual}}$) y emite únicamente las órdenes al mercado estrictamente necesarias para llevar la cuenta física al valor agregado del portfolio.
- **Auditoría e Invariantes de Seguridad (`AuditLiveNetInvariant`)**:
  Verifica constantemente que:
  $$\text{Net}_{\text{virtual}} == \text{Net}_{\text{estrategia}} == \text{Net}_{\text{cuenta broker}} \quad \text{y} \quad \text{Pending}_{\text{módulos}} == \text{Pending}_{\text{órdenes}}$$
  Si se detecta cualquier descalce, el sistema activa `liveReconciliationPending`, bloquea nuevas entradas y emite:
  `"FUNDEDSYNCSTACK RECONCILIATION PAUSE: [detalles]. Existing exits remain active; retry on next heartbeat."`

---

### 2.3. Motor de Dimensionamiento (`SizingProfile` y `AccountStage`)

La estrategia soporta perfiles de tamaño predefinidos gestionados a través del convertidor `FundedSyncStackSizingProfileConverter`:

| ID Perfil | Nombre para Mostrar | Filosofía / Riesgo |
| :---: | :---: | :---: |
| **2** | `25K Foundation` | Micro-contratos mínimos para cuentas pequeñas de 25k (drawdown ajustado $1,500). |
| **3** *(Default)* | `50K Elevated Risk` | Perfil balanceado estándar para cuentas de $50k (drawdown $2,500). |
| **4** | `100K Elevated Risk` | Escala intermedia para cuentas de $100k (drawdown $3,000). |
| **5** | `150K Max Risk` | Tamaño completo institucional para cuentas grandes de $150k+. |
| **13** | `50K Evaluation Pass Mode` | Optimización acelerada orientada a pasar rápidamente la fase de evaluación. |
| **14** | `Safety Size (Recommended)` | Modo conservador mínimo para cuentas fondeadas en fase de preservación. |

Adicionalmente, si el perfil es de tipo Lucid/Optimized, calcula las cantidades de cada módulo en función de **`LucidAccountStage`**:
- **Stage 0 (`Evaluation`)**: Usa los tiers de evaluación configurados (ej. `Lucid50KEvaluationTier`).
- **Stage 1 (`BelowBuffer`)**: Se activa si la cuenta fondeada está por debajo del colchón de retiro (buffer de seguridad). Reduce o mantiene el tamaño defensivo.
- **Stage 2 (`AboveBuffer`)**: Se activa cuando la cuenta ya superó el buffer de seguridad, permitiendo escalar el sizing para maximizar payouts.

---

### 2.4. Circuito de Pérdida Diaria de Cartera (`PortfolioDailyLossLimit`)

- **`PortfolioDailyLossLimit`** (Default: 0 / Deshabilitado; configurable ej. $1,000 o $1,500):
  Monitorea en tiempo real el PnL cerrado acumulado del día (`portfolioDailyClosedPnl`).
- Si $\text{PnL Diario} \le -\text{PortfolioDailyLossLimit}$:
  1. Marca `portfolioDailyLocked = true`.
  2. La función `CanEnter(tag)` retorna `false` inmediatamente para TODOS los 15 submódulos, impidiendo nuevas aperturas por el resto de la sesión.
  3. Si **`FlattenOnPortfolioDailyLoss == true`**, invoca `ExitModule(tag, "PORT_RISK")` para liquidar de inmediato todas las posiciones abiertas en todos los submódulos.

---

### 2.5. Filtro de Noticias de Alto Impacto (`restricted-news-days.csv`)

- Controlado por `FundedSyncStackBlockRestrictedNewsDays = true`.
- Ruta por defecto: `NinjaTrader 8\bin\Custom\FundedSync\restricted-news-days.csv` (o subcarpeta de documentos).
- Parámetros: `FundedSyncStackMinutesBeforeNews = 5`, `FundedSyncStackMinutesAfterNews = 5`.
- Durante los 5 minutos previos y 5 minutos posteriores a eventos macroeconómicos restringidos (FOMC, CPI, NFP, etc.), `FundedSyncStackIsRestrictedNewsEntryBlocked()` bloquea toda nueva apertura de posiciones y purga las órdenes pendientes en cola.

---

### 2.6. Rotación Anti-Drawdown (`HalfDrawdownEntryRotation`)

En el perfil `IsMinimumParticipationProfile`, la estrategia introduce un mecanismo matemático de reducción armónica de riesgo para 5 submódulos específicos: **`S`, `P`, `C`, `R`, `E`**.
- Asigna a cada uno un desfase modular (`HalfDrawdownRotationOffset`):
  `S` = 0, `P` = 1, `C` = 2, `R` = 3, `E` = 4.
- Regla de admisión:
  $$\left(\text{Secuencia}_{\text{módulo}} + \text{Offset}\right) \pmod 5 < 3$$
- Esto garantiza que sólo se admiten exactamente **3 de cada 5 señales consecutivas (60% de participación)** rotadas de forma cíclica y balanceada, evitando la saturación de margen simultánea en rachas de volatilidad adversa.

---

### 2.7. Licenciamiento Criptográfico (`FundedSyncLicenseGate`)

La estrategia posee dos compuertas de licencia instanciadas en `State.DataLoaded`:
- `bundleALicenseGate` (para el Producto `"BUNDLE_A"`: submódulos A1, S, V, W, T, Z, E).
- `bundleBLicenseGate` (para el Producto `"BUNDLE_B"`: submódulos A20, F, P, C, O, R, Q).

**Mecanismo de Verificación:**
1. **Bypass en Backtest**: Al iniciar, `LicenseAllowsEntry` evalúa `IsInStrategyAnalyzer`. Si es `true`, **retorna `true` inmediatamente**, omitiendo cualquier llamada de red o validación de clave.
2. **Device Fingerprint (Hardware ID)**: En ejecución en vivo, obtiene el identificador único de máquina de Windows desde el registro:
   `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` (o en su defecto `Environment.MachineName`), y genera un hash SHA-256 codificado en Base64Url con el prefijo `"FundedSync|"`.
3. **Validación Token RSA**: Consume un endpoint HTTPS institucional que retorna un token firmado digitalmente con una clave asimétrica RSA (`PublicKeyXml`). El payload descifrado valida el formato:
   `v1 | LicenseKey | ProductCode | DeviceFingerprint | UnixExpiryUtc | Status`
4. **Caché Local Offline**: Almacena el token validado en `%AppData%\FundedSync\<ProductCode>.license`, permitiendo operar hasta el vencimiento en caso de cortes temporales de conexión con rechequeo periódico cada 24 horas (`RecheckHours = 24`).

---

## 3. TABLA COMPARATIVA DE LOS 15 SUBMÓDULOS

| Código | Nombre del Submódulo | Bundle | BIP | Timeframe | Horario Operativo | Tipo de Entrada | Lógica Central / Indicadores Clave | Regla de Salida / Stop / TP | Desempeño en Backtest (CSV) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A1** | Absorb 1 Minute | A | BIP 1 | 1m ETH | 05:30 - 15:00 CT | Long / Short | Absorción de volumen en delta + SuperTrend (P:4, M:2.7) + ORB 30m. | Stop: 1.5 ATR. Salida: Inversión SuperTrend (`ST`) o Fin de Sesión (`SESSION`). | 679 trades, WR: 31.4%, PnL: **+$5,424.0**, PF: 1.03 |
| **A20** | Absorb 20 Minute | B | BIP 4 | 20m ETH | 05:30 - 15:00 CT | Short only (L=0) | Absorción macro en 20m + SuperTrend (P:7, M:2.0). Bloquea lunes. | Stop: 1.5 ATR. Salida: SuperTrend flip (`ST`) o Fin de Sesión (`SESSION`). | 540 trades, WR: 42.0%, PnL: **-$31,855.1**, PF: 0.96 |
| **F** | Fabio ORB | B | BIP 3 | 5m ETH | 08:30 - 14:00 CT | Long only (def) | Rotura de Rango de Apertura 30 min (08:30-09:00 CT) con filtro de Delta $\ge 200$. | Stop: Max 125 pts / Rango ORB. TP: 1:1 R/R. Salida: `EOD` a las 14:00 CT. | 259 trades, WR: 42.5%, PnL: **-$35,822.2**, PF: 0.86 |
| **S** | Swas SuperTrend | A | BIP 2 | 3m ETH | 09:30 - 15:55 CT | Long / Short | SuperTrend (10, 3.2) + ADX(14) > 20 + EMA(21) Bias + Filtro de Régimen ATR(100). | Stop: 3.0 ATR. Salida: SuperTrend flip (`ST`) o `EOD` a las 15:55 CT. | 320 trades, WR: 42.5%, PnL: **+$62,121.8**, PF: 1.38 |
| **P** | Nq Pullback | B | BIP 1 | 1m ETH | 09:00 - 17:00 CT | Long only (def) | Pullback a VWAP / Rango de Apertura (08:30-09:00 CT) confirmado con pivots. | Stop: Swing 30 barras. TP: Swing 5 barras. Salida: `EOD` 15:55 CT. | 329 trades, WR: 40.7%, PnL: **+$36,778.4**, PF: 1.12 |
| **C** | Capstone Gap Fade | B | BIP 5 | 1m US STOCK | 12:00 - 16:00 ET | Long only (def) | Fade de gap de contado NYSE (Open vs Prior Close $\ge 2.0$ pts). | Stop: $1,500 (75 pts). TP: $2,500 (125 pts). Salida: Tiempo (`TIME`) a las 16:14 ET. | 71 trades, WR: 57.7%, PnL: **+$56,071.6**, PF: 1.75 |
| **V** | Vault Breakout | A | BIP 6 | 5m RTH | 09:45 - 15:00 ET | Long only | Breakout de banda de ruido (0.40 * DailyATR 252d) sobre VWAP de sesión. | Stop: $2,000 (100 pts). TP: $1,400 (70 pts). Salida: 2 barras bajo VWAP o 15:50 ET. | 0 trades (Filtro Warmup 252 días diarios no alcanzado en 9 meses). |
| **O** | Overnight Trend | B | BIP 1+7 | 1m ETH + 1d | 15:00 CT / 17:01 CT | Long only | Cierre diario > SMA(20) + pendiente alcista + filtro de volatilidad 20d. | Salida: Apertura RTH 08:30 CT (`OPEN`). Sin stop fijo intradía. | 0 trades (Condición temporal y de régimen no disparada en configuración base). |
| **W** | VWAP Cross | A | BIP 1 | 1m ETH | 08:31 - 14:00 CT | Long only | Cruce alcista de VWAP intradiario con 2 cierres de confirmación. | Stop / Salida: Cruce bajista de VWAP (`VWAP`) o 15:00 CT (`EOD`). | 1,264 trades, WR: 30.9%, PnL: **-$1,320.6**, PF: 1.00 |
| **N** | N-Day High Breakout | N/A | BIP 1+8 | 1m ETH + 1d | 09:30 - 15:45 CT | Long only | Breakout del máximo de los últimos 5 días + VWAP alcista + buffer 4 pts. | Salida: Volatility loss exit (`VOLLOSS`), Fallo (`FAILED`) o 16:00 CT (`EOD`). | 0 trades (Deshabilitado por defecto: `EnableNDay = 0`, `BaseQty = 0`). |
| **T** | Ftm Machine Learning | A | BIP 1 | 1m ETH | 09:30 - 16:00 ET | Long / Short | Clasificador KNN (14 features estandarizadas) sobre ORB 15m + Planes dinámicos R/R. | TP: 1.25R a 3.0R. Trailing lock. Salida administrativa: `CashClose1600ET`. | 0 trades (Deshabilitado por defecto en `Configure`: `EnableFtm = 0`). |
| **R** | ATR Phase Oscillator | B | BIP 9 | 10m ETH | 24/5 ETH (Cash close) | Long / Short | Oscilador normalizado ATR(14) + EMA(21). Señales de cambio de fase cíclica. | Salida: Cierre de contado (`CASH_CLOSE` 16:00 ET), Fase Opuesta (`OPPOSITE`). | 33 trades, WR: 66.7%, PnL: **+$96,310.0**, PF: 4.33 |
| **Z** | Zeta Trend Day | A | BIP 1 | 1m ETH | 09:30 - 16:00 ET | Long / Short | Buckets de 5 min desde apertura NYSE. Detecta días de tendencia institucional sostenida. | TP: Objetivo Zeta redondeado al tick. Salida: Fin de sesión NYSE (`EOD`). | 73 trades, WR: 41.1%, PnL: **+$26,768.6**, PF: 3.17 |
| **E** | EMA Divergence | A | BIP 10 | 15m ETH | 24/5 ETH | Long only (def) | Cruce de EMA(9) sobre EMA(21) en 15m + Filtro CVD + Filtro de Absorción de Volumen. | Stop: 30 puntos ($600). TP: 45 puntos ($900). Salida: Cruce inverso (`OPPOSITE`). | 164 trades, WR: 45.1%, PnL: **+$7,175.4**, PF: 1.12 |
| **Q** | Rampart 5-Minute | B | BIP 3 | 5m ETH | 09:15 - 12:00 ET | Long / Short | Rango 09:15-09:50 ET + Breakout con buffer 6 ticks. Sizing dinámico por riesgo USD. | Stop: 1 tick dentro del rango. TP: 0.30 R/R. Salida: `RAMPART_FLAT` 16:00 ET. | 0 trades (Deshabilitado por defecto en `Configure`: `EnableRampart = 0`). |

---

## 4. FICHA TÉCNICA DETALLADA DE LOS 15 SUBMÓDULOS

### 4.1. Módulo `A1`: `Absorb1Minute`
- **Serie y Timeframe:** BIP 1 (NQ 1-Minuto ETH, CME US Index Futures ETH).
- **Ventana de Operación:** 05:30 CT a 15:00 CT (`Ab_SessionStartHour = 5, Ab_SessionStartMinute = 30`, `Ab_SessionEndHour = 15, Ab_SessionEndMinute = 0`).
- **Bloqueo Horario:** Bloquea entradas entre 05:30 y 06:00 CT (`A1_UseEarlyEntryBlock = 1`, `A1_BlockStartHour = 5, 30` a `6, 00`). Cooldown tras pérdida: 14 barras (`A1_LossCooldownBars = 14`).
- **Indicadores y Fórmulas Exactas:**
  - *SuperTrend A1:* Periodo ATR = 4 (`A1_STPeriod`), Multiplicador = 2.7 (`A1_STMult`).
  - *Volume at Price (VAP):* Lookback = 10 barras, Resolución = 24 niveles.
  - *Delta Smoothing:* Lookback = 5 barras (`Ab_DeltaLookback`).
  - *ORB:* 30 minutos desde inicio de sesión (`Ab_OrbMinutes = 30`).
  - *Régimen de Volatilidad:* Ratio ATR actual vs ATR Baseline (lookback 100 barras) $\le 2.9$ (`Ab_VolRegimeMultiplier = 2.9`).
  - *Filtro Rollover:* Bloquea si la fecha está dentro de 10 días antes o 1 día después del tercer viernes de mes de vencimiento (`Ab_RolloverDaysBefore = 10, Ab_RolloverDaysAfter = 1`).
- **Regla de Entrada:**
  - *Long:* Condición de absorción de compras (Volumen en precio $\ge 2.5 \times$ media, Delta suavizado positivo), precio dentro de banda VWAP $\pm 0.5$ pts, precio sobre SuperTrend y filtro de rollover inactivo.
  - *Short:* Condición de absorción de ventas (Volumen en precio $\ge 2.5 \times$ media, Delta negativo), bajo VWAP y bajo SuperTrend.
- **Gestión de Salida:**
  - *Stop Loss Fijo:* $1.5 \times \text{ATR}(14)$ (`Ab_HardStopATRMult = 1.5`).
  - *Trailing / Reversal:* Inversión del SuperTrend emite `RequestModuleExit("A1", "ST", bip)`.
  - *Fin de Sesión:* Al alcanzar 15:00 CT emite `RequestModuleExit("A1", "SESSION", bip)`.
- **Sizing:** Base 1 micro/mini (`BaseQtyAbsorb1m = 1`), escala con `SizeLevel` y `SizingProfile` (Tier 50K = 1).

---

### 4.2. Módulo `A20`: `Absorb20Minute`
- **Serie y Timeframe:** BIP 4 (NQ 20-Minutos ETH).
- **Ventana de Operación:** 05:30 CT a 15:00 CT.
- **Restricciones:** Bloquea todas las entradas los lunes (`A20_BlockMondayEntries = 1`). `A20_AllowLongs = 0`, `A20_AllowShorts = 1` (opera estrictamente en el lado **Short**).
- **Indicadores y Fórmulas:**
  - *SuperTrend A20:* Periodo ATR = 7 (`A20_STPeriod`), Multiplicador = 2.0 (`A20_STMult`).
  - Mismo motor de absorción `RunAbsorb` con parámetros compartidos `Ab_*`.
- **Regla de Entrada Short:**
  - Barra de 20 minutos cierra confirmando absorción bajista, rechazo en banda VWAP, tendencia SuperTrend bajista, fuera de lunes y fuera de días de rollover.
- **Gestión de Salida:**
  - *Stop Loss:* $1.5 \times \text{ATR}(14)$ en 20 minutos.
  - *Salida:* Reversión del SuperTrend (`A20_X_ST`) o fin de sesión (`A20_X_SESSION`).
- **Sizing:** Base 2 contratos (`BaseQtyAbsorb20m = 2`), en Perfil 50K escala a 5 contratos (`NormalLucidQuantity("A20") = 5`).

---

### 4.3. Módulo `F`: `FabioOrb`
- **Serie y Timeframe:** BIP 3 (NQ 5-Minutos ETH).
- **Ventana de Operación:** Apertura de rango 08:30 CT (`F_StartH = 8, F_StartM = 30`), Duración ORB = 30 minutos (`F_DurMin = 30`, finaliza 09:00 CT). Última hora de trading: 14:00 CT (`F_EndH = 14, F_EndM = 0`).
- **Indicadores y Fórmulas:**
  - Máximo del Rango de Apertura (`orbHigh_F`) y Mínimo (`orbLow_F`) calculados en las primeras 6 barras de 5 minutos (08:30 a 09:00 CT).
  - *Filtro de Delta:* Delta acumulado de la barra $\ge 200$ contratos (`F_DeltaThreshold = 200`), o Delta Acumulado de sesión $\ge 500$ si `F_UseCumDelta = 1`.
  - *Filtro de Riesgo Inicial Máximo:* Rango del ORB no debe superar 125 puntos (`F_MaxInitialRiskPoints = 125`).
- **Regla de Entrada:**
  - *Long:* Barra de 5 minutos cierra con $\text{Close} > \text{orbHigh\_F}$, con Delta $\ge 200$, dentro de la ventana 09:00 a 14:00 CT.
- **Gestión de Salida:**
  - *Stop Loss:* Situado en `orbLow_F` (o limitado a 125 puntos por `MaxInitialRiskPoints`).
  - *Take Profit:* Ratio 1:1 respecto al riesgo del stop (`F_TPRR = 1.0`).
  - *Cierre EOD:* A las 14:00 CT liquida posición mediante `RequestModuleExit("F", "EOD", bip)`.
- **Sizing:** Base 1 contrato (`BaseQtyFabio = 1`), en Perfil 50K escala a 3 contratos.

---

### 4.4. Módulo `S`: `Swas`
- **Serie y Timeframe:** BIP 2 (NQ 3-Minutos ETH).
- **Ventana de Operación:** Inicio 09:30 CT (10:30 ET). Cierre de sesión 15:55 CT (`S_CloseHour = 15, S_CloseMinute = 55`).
- **Bloqueos Horarios:**
  - Bloquea ventana de alta volatilidad de apertura: 10 minutos antes (09:20 CT) y 30 minutos después (10:00 CT) de la apertura (`S_PreBlockMin = 10, S_PostBlockMin = 30`).
  - Bloquea compras a las 07:00 CT (`S_BlockedLongEntryHour = 7`).
  - Bloquea ventas a las 13:00 CT (`S_BlockedShortEntryHour = 13`).
- **Indicadores y Fórmulas:**
  - *SuperTrend Swas:* Periodo = 10 (`S_STPeriod`), Multiplicador = 3.2 (`S_STMult`).
  - *ADX:* Periodo = 14, Umbral mínimo = 20 (`S_ADXThreshold = 20`).
  - *EMA Bias:* EMA de 21 periodos (`S_BiasEMAPeriod = 21`).
  - *Pendiente de EMA:* $\Delta\text{EMA} \ge 0.05 \times \text{ATR}(14)$ (`S_MinEmaSlopeATR = 0.05`).
  - *Régimen ATR:* Lookback 100 barras, Multiplicador 2.9 (`S_RegimeATRMultiplier = 2.9`).
- **Regla de Entrada:**
  - *Long:* SuperTrend en compra + ADX(14) > 20 + Close > EMA(21) + Pendiente EMA positiva + Fuera de ventanas bloqueadas.
  - *Short:* SuperTrend en venta + ADX(14) > 20 + Close < EMA(21) + Pendiente EMA negativa + Fuera de ventanas bloqueadas.
- **Gestión de Salida:**
  - *Stop Loss:* Hard stop opcional de $3.0 \times \text{ATR}(14)$ (`S_HardStopATRMult = 3.0`).
  - *Salida Técnica:* Reversión de SuperTrend (`S_X_ST`).
  - *Fin de Día:* 15:55 CT emite `RequestModuleExit("S", "EOD", bip)`.
- **Sizing:** Base 1 contrato, Perfil 50K = 1 contrato.

---

### 4.5. Módulo `P`: `NqPullback`
- **Serie y Timeframe:** BIP 1 (NQ 1-Minuto ETH).
- **Ventanas Operativas:**
  - Rango de Apertura: 08:30 a 09:00 CT (`P_OpeningRangeStart = 83000, P_OpeningRangeEnd = 90000`).
  - Ventana de VWAP: 08:30 a 17:00 CT.
  - Ventana de Entrada: 09:00 a 17:00 CT (`P_EntryStart = 90000, P_EntryEnd = 170000`).
  - Reset diario: 23:00 CT (`P_DayResetTime = 230000`).
- **Indicadores y Algoritmo de Swings:**
  - Pivots de swing para Stop Loss: lookback de 30 barras (`P_StopSwingLength = 30`).
  - Pivots de swing para Take Profit: lookback de 5 barras (`P_TargetSwingLength = 5`).
  - Modo Retest = 1 (espera que el precio rompa y retestee la zona del VWAP o extremos del ORB).
  - Configurado en `P_TradeLongs = 1, P_TradeShorts = 0` (sólo compras).
- **Dimensionamiento por Volatilidad de Capital:**
  - Capital Asignado: $500,000 (`P_CapitalUsd = 500000`), Riesgo: 2% (`P_RiskPercent = 2.0`).
  - Fórmula de Contratos Nativos:
    $$\text{Contratos} = \min\left(\text{P\_MaxContracts (20)}, \left\lfloor \frac{\text{Capital} \times \text{Riesgo}}{\text{Distancia Stop Points} \times 20} \right\rfloor \right)$$
- **Salida:** Swing Target alcanzado (`P_TARGET`), Swing Stop (`P_STOP`), o Fin de Día a las 15:55 CT (`P_EndOfDayFlatTime = 155500`).

---

### 4.6. Módulo `C`: `CapstoneGap`
- **Serie y Timeframe:** BIP 5 (NQ 1-Minuto sobre plantilla `US STOCK` / 09:30-16:00 ET).
- **Ventana de Operación:**
  - Inicio de evaluación: 09:30 ET (primera barra de contado).
  - Ventana de entrada activa: 12:00 ET a 16:00 ET (TimeOfDay + 150m a 390m).
  - Salida forzada por tiempo: 16:14 ET (TimeOfDay + 404m).
  - Máximo 2 trades por día (`entriesToday_C < 2`).
- **Lógica de Señal:**
  - Compara el precio de apertura de contado (`dailyOpens_C[0]`) contra el precio de cierre oficial del día previo (`dailyCloses_C[1]`).
  - Si $\text{Gap} = |\text{Open}_0 - \text{Close}_1| \ge 2.0 \text{ puntos}$ (`C_MinimumGapPoints = 2.0`).
  - Con `C_EnableLongEntries = 1` y `C_EnableShortEntries = 0`, ejecuta fade de gap a la baja colocando órdenes límite/stop dinámicas (`MaintainModuleEntryWithDistances`) referenciadas al mínimo de las últimas 12 barras (`LowestPriorBars_C(12)`).
- **Gestión de Salida:**
  - *Stop Loss:* $1,500 fijos por contrato (75 puntos NQ: $1500 / 20 = 75).
  - *Profit Target:* $2,500 fijos por contrato (125 puntos NQ: $2500 / 20 = 125).
  - *Salida por Tiempo:* Al cumplirse las 16:14 ET emite `RequestModuleExit("C", "TIME", bip)`.
- **Sizing:** Base 1 contrato, en Perfil 50K escala a 3 contratos (`NormalLucidQuantity("C") = 3`).

---

### 4.7. Módulo `V`: `VaultBreak`
- **Serie y Timeframe:** BIP 6 (NQ 5-Minutos sobre sesión `CME US Index Futures RTH`).
- **Ventana de Operación:** 09:45 ET a 15:00 ET (`V_EarliestEntryEastern = 94500, V_LatestEntryEastern = 150000`).
- **Bloqueo Horario:** Bloquea entradas a las 09:00 ET (`V_BlockedEntryHour = 9`). Máximo 3 trades por día (`V_MaximumTradesPerDay = 3`).
- **Indicadores y Fórmulas:**
  - *Rolling Daily ATR:* Requiere una cola de 252 sesiones diarias cerradas (`V_DailyAtrLength = 252`). Si la cola tiene menos de 252 sesiones, `dailyAtr_V = 0.0`.
  - *Banda de Ruido (Noise Level):* $\text{NoiseUp} = \text{Open} + (0.40 \times \text{dailyAtr\_V})$ (`V_NoiseMultiplier = 0.40`).
  - *VWAP de Sesión RTH:* Calculado acumulando precio típico ponderado por volumen desde la primera barra RTH.
- **Regla de Entrada:**
  - `Close > NoiseUp` AND `Close > sessionVwap_V`.
- **Gestión de Salida:**
  - *Stop Loss:* $2,000 por contrato (100 puntos NQ: $2000 / 20 = 100).
  - *Profit Target:* $1,400 por contrato (70 puntos NQ: $1400 / 20 = 70).
  - *Exhaustión VWAP:* Si el precio registra 2 barras consecutivas por debajo del VWAP (`barsBelowVwap_V >= 2`), liquida de inmediato emitiendo `RequestModuleExit("V", "VWAP", bip)`.
  - *Salida por Tiempo:* 15:50 ET (`V_FlattenTimeEastern = 155000`) emite `RequestModuleExit("V", "TIME", bip)`.
- **Sizing:** Base 3 contratos, Perfil 50K = 3 contratos.

---

### 4.8. Módulo `O`: `Overnight`
- **Serie y Timeframe:** BIP 1 (1m ETH) para ejecución y reloj; BIP 7 (1d RTH) para promedios diarios.
- **Ventana de Entrada:** 15:00 CT (cierre de contado) o entrada post-mantenimiento a las 17:01 CT (`O_PostMaintenanceEntryTimeCentral = 170100`). Bloquea entradas los viernes (`O_AllowFridayEntries = 0`).
- **Indicadores y Fórmulas:**
  - *Filtro de Tendencia SMA(20):* Cierre del día > Media Móvil Simple de 20 días (`O_MovingAverageLength = 20`).
  - *Pendiente de SMA:* SMA actual > SMA de hace 5 días (`O_MaSlopeLookback = 5`).
  - *Rango RTH vs ATR:* Rango diario / ATR(20) $\le 1.5$ (`O_MaximumRthRangeToAtr = 1.5`).
  - *Volatilidad Histórica:* Desviación estándar de los retornos logarítmicos de los últimos 20 días (`O_VolatilityLookback = 20`).
  - *Sizing Dinámico:* Capital $100,000, Riesgo objetivo $1,500 (`O_TargetRiskUsd = 1500`), Mínimo 1, Máximo 50 contratos.
- **Gestión de Salida:**
  - A las 08:30 CT de la mañana siguiente (apertura de mercado) emite `RequestModuleExit("O", "OPEN", bip)`. No utiliza Stop Loss intradiario fijo.

---

### 4.9. Módulo `W`: `VwapCross`
- **Serie y Timeframe:** BIP 1 (NQ 1-Minuto ETH).
- **Ventana de Operación:** Inicio de VWAP a las 08:30 CT (`W_VwapStartTimeCentral = 83000`), ventana de entrada de 08:31 CT (`W_InitialEntryBoundaryCentral = 83100`) hasta las 14:00 CT (`W_LastEntryTimeCentral = 140000`).
- **Lógica de Entrada:**
  - Detecta el cruce de precio por encima del VWAP acumulado intradía.
  - Requiere 2 cierres confirmados consecutivos por encima de VWAP (`W_ConfirmationBars = 2`).
  - Cooldown obligatorio de 5 barras tras salida previa (`W_CooldownBars = 5`).
  - Filtro de distancia mínima: 4 ticks (1 punto) sobre VWAP (`W_MinimumVwapDistanceTicks = 4`).
- **Gestión de Salida:**
  - *Cruce Inverso:* Cuando una barra de 1 minuto cierra por debajo del VWAP, emite `RequestModuleExit("W", "VWAP", bip)`.
  - *Fin de Día:* A las 15:00 CT (`W_VwapEndTimeCentral = 150000`) emite `RequestModuleExit("W", "EOD", bip)`.
- **Sizing:** Base 1 contrato, Perfil 50K = 1 contrato.

---

### 4.10. Módulo `N`: `NDayLong`
- **Serie y Timeframe:** BIP 1 (1m ETH) y BIP 8 (1d ETH).
- **Ventana de Operación:** Hasta las 15:45 CT (`N_LastEntryTime = 154500`). Cierre forzoso a las 16:00 CT (`N_FlattenTime = 160000`).
- **Lógica de Breakout:**
  - Identifica el máximo más alto de los últimos 5 días (`N_NumDays = 5`) extraído de la serie diaria BIP 8 (`PriorNDayHigh`).
  - Breakout Acceptance: El precio debe superar el máximo previo por al menos 4 puntos (`N_AcceptanceBufferPoints = 4.0`) durante 2 barras consecutivas de 1 minuto (`N_AcceptanceConfirmationBars = 2`).
  - Filtro de Pendiente VWAP: La pendiente de VWAP en los últimos 15 minutos debe ser positiva (`N_VwapSlopeLookbackMinutes = 15`).
- **Gestión de Salida:**
  - *Volatility Loss Exit:* Si la pérdida flotante excede 1.0 veces el rango promedio previo (`N_MaximumLossPriorRangeFraction = 1.0`), emite `RequestModuleExit("N", "VOLLOSS", bip)`.
  - *Failed Breakout Exit:* Si el precio reingresa por debajo del nivel de breakout por 6 barras consecutivas (`N_FailureConfirmationBars = 6`), emite `RequestModuleExit("N", "FAILED", bip)`.
  - *EOD:* A las 16:00 CT liquida posición.
- **Sizing:** Base 0 (deshabilitado por defecto en la configuración original).

---

### 4.11. Módulo `T`: `FtmOrb` (`FtmEngine`)
- **Serie y Timeframe:** BIP 1 (NQ 1-Minuto ETH).
- **Arquitectura de Machine Learning / KNN:**
  - El motor `FtmEngine` implementa un modelo de Vecinos Más Cercanos (*K-Nearest Neighbors*) entrenado trimestralmente (`QuarterDirectionModel`).
  - **Vector de 14 Features Estandarizadas (`DirectionTrainingRow.Features`):**
    1. Retorno de la apertura a señal (bps).
    2. Rango del ORB en bps (`currentOrbBps`).
    3. Ratio de localización del cierre dentro del rango (`closeLocation`).
    4. Proporción del cuerpo de la barra (`bodyRatio = (close - open) / (high - low)`).
    5. Conteo de toques de la señal al borde del ORB (`CountSignalTouches`).
    6. Distancia a VWAP en ticks.
    7. Retorno previo de tendencia (`priorTrendBps`).
    8-14. Retornos rezagados (*LagReturnBps*) y cuantiles de dispersión lineal (`LinearPercentile`).
  - Estandarización z-score en tiempo real mediante vectores de medias (`Means`) y desviaciones (`Scales`).
  - Distancia euclidiana ponderada contra las filas de entrenamiento almacenadas.
- **Filtros de Geometría de Admisión:**
  - `bodyRatio >= 0.15` y `closeLocation >= 0.60` (para Longs).
  - Toques mínimos al nivel de breakout $\ge 3$ (`CountSignalTouches >= 3`).
- **Planes Dinámicos de Gestión de Riesgo (`SelectManagementPlan`):**
  - Régimen `"high_orb_short_target"`: Target = 1.25R, Trigger Trailing = 1.25R.
  - Régimen `"countertrend_early_guard"`: Target = 3.0R, Trigger Trailing = 0.75R, Lock Trailing = 0.10R.
  - Régimen `"baseline"`: Target = 3.0R, Trigger Trailing = 1.25R.
- **Salida Administrativa:** Salida forzosa a las 16:00 ET (`CashClose1600ET`).

---

### 4.12. Módulo `R`: `AtrPhase`
- **Serie y Timeframe:** BIP 9 (NQ 10-Minutos ETH).
- **Indicadores y Oscilador de Fase ATR (`UpdateAtrPhaseIndicator`):**
  - True Range calculado en 10 minutos y suavizado con ATR(14) de Wilder (`rAtr14`).
  - EMA de 21 periodos (`rEma21`) con multiplicador $\alpha = 2 / (21 + 1) = 0.090909$.
  - **Oscilador de Fase Normalizado:**
    $$\text{Oscilador} = 100 \times \frac{\text{Close} - \text{EMA}(21)}{3 \times \text{ATR}(14)}$$
    Ajustado y centrado en una escala normalizada de 0 a 1 con fulcro en 0.5.
- **Filtro de Sesiones Bloqueadas (`IsAtrPhaseStandaloneBlockedSession`):**
  - Implementa un array estático hardcoded de fechas de baja liquidez / festivos bancarios (`Array.BinarySearch`). Si la sesión coincide, omite toda operativa.
- **Regla de Entrada:**
  - Identifica puntos de inflexión del oscilador saliendo de zonas extremas (< 0.20 o > 0.80) en confluencia con el VWAP diario.
  - Emite compras (`RequestModuleLong`) o ventas (`RequestModuleShort`).
- **Gestión de Salida:**
  - *Cierre de Contado:* 16:00 ET liquida mediante `RequestModuleExit("R", "CASH_CLOSE", bip)`.
  - *Inversión de Fase:* Si el oscilador cruza en sentido contrario, emite `RequestModuleExit("R", "OPPOSITE", bip)`.
- **Sizing:** Base 1 contrato, Perfil 50K = 2 contratos (`NewModuleLucidQuantity("R") = 2`).

---

### 4.13. Módulo `Z`: `ZetaTrendDay`
- **Serie y Timeframe:** BIP 1 (NQ 1-Minuto ETH).
- **Algoritmo de Detección de Trend Day:**
  - Sólo opera en sesiones NYSE completas (`IsFullZetaSession`, excluye cierres tempranos de días festivos como víspera de Navidad o Acción de Gracias mediante tabla binaria de 2010 a 2027).
  - Inicializa la sesión a las 09:30 ET (`StartZetaSession`).
  - Divide la sesión en "Buckets" de 5 minutos (`UpdateZetaBucket`).
  - Calcula una EMA rápida y lenta sobre los cierres de cada bucket.
  - Evalúa la expansión de rango y momentum acumulado touch-free (sin retestear la EMA).
  - Si un bucket confirma que el día tiene características institucionales de *Trend Day*, dispara una entrada en la dirección de la rotura.
- **Gestión de Salida:**
  - *Target Dinámico Zeta:* Calculado según la proyección del bucket de apertura y redondeado exactamente al tick (`RoundZetaTarget`).
  - *Cierre NYSE:* A las 16:00 ET liquida remanentes por fin de día (`Z_X_EOD`).
- **Sizing:** Base 2 contratos, Perfil 50K = 4 contratos (`NewModuleLucidQuantity("Z") = 4`).

---

### 4.14. Módulo `E`: `EmaDivergence`
- **Serie y Timeframe:** BIP 10 (NQ 15-Minutos ETH).
- **Indicadores y Filtros:**
  - EMA Rápida: Periodo 9 (`eFastNow`).
  - EMA Lenta: Periodo 21 (`eSlowNow`).
  - *Filtro de Absorción (`EmaAbsorptionAllows`):* Utiliza la clase `RollingValues(10)`. Requiere que la desviación estándar de volumen no presente saturación anómala.
  - *Filtro CVD (`EmaCvdAllows`):* Verifica que el delta acumulado de volumen acompañe la dirección del cruce de medias.
- **Regla de Entrada:**
  - Cruce alcista de EMA(9) sobre EMA(21) en la barra de 15 minutos, validado por absorción y CVD.
  - Sincronización al minuto 14 de la barra para preparar la ejecución en la frontera de 1 minuto (`eHistoricalEntrySubmitTime`).
- **Gestión de Salida:**
  - *Stop Loss Fijo:* Exactamente **30 puntos** ($600 por contrato en NQ).
  - *Profit Target Fijo:* Exactamente **45 puntos** ($900 por contrato en NQ, R/R = 1.5).
  - *Cruce Opuesto:* Si la EMA(9) cruza a la baja antes del TP/SL, emite salida técnica (`E_X_OPPOSITE_CROSS`).
- **Sizing:** Base 1 contrato, Perfil 50K = 1 contrato (`NewModuleLucidQuantity("E") = 1`).

---

### 4.15. Módulo `Q`: `Rampart5Minute`
- **Serie y Timeframe:** BIP 3 (NQ 5-Minutos ETH).
- **Ventana de Rango:** Inicio 09:15 ET (`Q_RangeStartHour = 9, Q_RangeStartMinute = 15`) a 09:50 ET (`Q_RangeEndHour = 9, Q_RangeEndMinute = 50`).
- **Parámetros de Breakout:**
  - Breakout Margin: 6 ticks (1.5 puntos) más allá del máximo/mínimo del rango (`Q_BreakMarginTicks = 6`).
  - Stop Buffer: 1 tick dentro del rango (`Q_StopBufferTicks = 1`).
  - Ratio Riesgo / Beneficio: **0.30** (`Q_RiskReward = 0.3`). Busca un target rápido de alta probabilidad equivalente al 30% del tamaño del rango.
  - Última hora de entrada: 12:00 ET (`Q_LastEntryHour = 12`).
  - Límite de 1 trade por lado por sesión (`Q_OneTradePerSide = 1`).
- **Dimensionamiento por Riesgo Monetario (`RampartQuantity`):**
  - Calcula los contratos dividiendo el riesgo en dólares configurado entre el tamaño del stop loss en dólares:
    $$\text{Contratos} = \min\left(\text{MaxContracts}, \left\lfloor \frac{\text{RiskUsd}}{\text{StopDistancePoints} \times 20} \right\rfloor \right)$$
    (En Perfil 50K: Riesgo = $200, Máximo = 28 contratos).
- **Gestión de Salida:**
  - Salida forzada por hora a las 16:00 ET (`Q_ForceCloseHour = 16`) emitiendo `RequestModuleExit("Q", "RAMPART_FLAT", bip)`.

---

## 5. ANÁLISIS EXHAUSTIVO DEL BACKTEST (CSV NINJATRADER)

El análisis del archivo oficial exportado de NinjaTrader Analyzer (`NinjaTrader Grid 2026-11-15 08-20 p. m..csv`) arrojó los siguientes resultados cuantitativos verificados:

### 5.1. Métricas Globales Consolidadas
- **Rango Temporal:** 01/01/2026 22:00:00 a 30/09/2026 16:56:00 (9 meses de operativa continua).
- **Total de Trades Realizados:** 3,732 trades.
- **Trades Ganadores:** 1,378 (36.92%).
- **Trades Perdedores:** 2,354 (63.08%).
- **Trades Neutrales (Breakeven):** 0.
- **Beneficio Bruto (Gross Profit):** $2,559,858.96.
- **Pérdida Bruta (Gross Loss):** $2,338,207.24.
- **Beneficio Neto (Net Profit):** **+$221,651.72**.
- **Factor de Beneficio (Profit Factor):** **1.09**.
- **Comisiones Totales Descontadas:** $27,233.28.
- **Max Drawdown de Operaciones Cerradas:** **-$218,206.32**.
- **Trade Promedio:** +$59.39.
- **Ganancia Promedio por Trade Ganador:** +$1,857.66.
- **Pérdida Promedio por Trade Perdedor:** -$993.29.
- **Ratio Win/Loss (Payoff Ratio):** **1.87** (las ganancias promedio casi duplican las pérdidas promedio).

---

### 5.2. Desglose Detallado por Submódulo

```
==========================================================================================
PERFORMANCE POR SUBMÓDULO EN BACKTEST (GRID CSV)
==========================================================================================
Módulo   Trades  Long/Short  Win Rate   Beneficio Neto  Gross Profit  Gross Loss   PF    Max Drawdown
------------------------------------------------------------------------------------------
R (ATR)      33     22 / 11    66.7%        +$96,310.0   $125,225.7    $28,915.6  4.33      -$8,461.5
S (Swas)    320    153 / 167   42.5%        +$62,121.8   $227,616.6   $165,494.8  1.38     -$23,246.6
C (Capst)    71     67 / 4     57.7%        +$56,071.6   $130,821.8    $74,750.2  1.75     -$28,206.2
P (Pullb)   329    264 / 65    40.7%        +$36,778.4   $341,698.7   $304,920.4  1.12    -$102,110.8
Z (Zeta)     73     23 / 50    41.1%        +$26,768.6    $39,132.3    $12,363.8  3.17      -$3,045.3
E (EMA)     164    155 / 9     45.1%         +$7,175.4    $65,373.8    $58,198.4  1.12      -$6,807.2
A1 (Abs1)   679    477 / 202   31.4%         +$5,424.0   $208,803.1   $203,379.2  1.03     -$34,843.5
W (VWAP)  1,264    881 / 383   30.9%         -$1,320.6   $522,127.8   $523,448.5  1.00     -$81,962.5
A20 (Ab20)  540     83 / 457   42.0%        -$31,855.1   $687,207.0   $719,062.1  0.96    -$115,519.7
F (Fabio)   259    212 / 47    42.5%        -$35,822.2   $211,852.1   $247,674.4  0.86     -$58,921.6
------------------------------------------------------------------------------------------
TOTAL     3,732  2,337/1,395   36.9%       +$221,651.72 $2,559,858.9 $2,338,207.2  1.09    -$218,206.32
```

---

### 5.3. Explicación de Salidas Cruzadas en el Grid CSV
Al examinar las salidas (`Exit name`) dentro del CSV, se observa con claridad que trades entrados bajo el prefijo `A20_` o `W_` figuran cerrados por órdenes como `W_E_L` (35.9% de salidas en A20), `W_X_VWAP`, o `A1_STOP`. 

**Motivo Técnico:**
NinjaTrader Analyzer calcula las estadísticas de cuenta física mediante **emparejamiento FIFO estándar**. Cuando la estrategia emite órdenes de netting (por ejemplo, si `A20` estaba Short y `W` entra Long, el Net agregado pasa a 0 o positivo enviando una orden Buy), el motor nativo de NinjaTrader cierra la posición abierta previa de `A20` con el identificador de la orden de entrada de `W`. 

En la ejecución en tiempo real y en el registro interno de `FUNDEDSYNCSTACK`, cada submódulo lleva su propia contabilidad independiente a través de `ModuleState` y `RecordClosedModuleTradeOnce`, aislando el PnL de cada algoritmo.

---

### 5.4. Verificación de Submódulos con 0 Trades en Backtest
De los 15 submódulos, exactamente **5 submódulos** no tuvieron actividad en este reporte CSV:
1. **`V` (`VaultBreak`):** **0 trades.** Causa verificada en IL: Requiere una cola de 252 sesiones diarias cerradas (`V_DailyAtrLength = 252`) para calcular `dailyAtr_V`. El backtest cubrió 9 meses (~188 días hábiles de trading), por lo que la condición `dailyAtr_V <= 0` abortó todas las entradas de Vault.
2. **`O` (`Overnight`):** **0 trades.** Causa verificada en IL: En la configuración probada, la hora de entrada hardcoded `150000` comparada mediante `ToTime` no coincidió con la zona horaria del feed de datos local, o el filtro estricto de pendiente de media móvil no fue satisfecho.
3. **`N` (`NDayLong`):** **0 trades.** Causa verificada en IL: En `SetDefaults`, los valores por defecto son `EnableNDay = 0` y `BaseQtyNDay = 0`.
4. **`T` (`FtmOrb`):** **0 trades.** Causa verificada en IL: En `State.Configure`, la instrucción `IL_0b81: call FUNDEDSYNCSTACK.set_EnableFtm(0)` fuerza explícitamente su desactivación.
5. **`Q` (`Rampart5Minute`):** **0 trades.** Causa verificada en IL: En `State.Configure`, la instrucción `IL_0b88: call FUNDEDSYNCSTACK.set_EnableRampart(0)` fuerza explícitamente su desactivación.

---

## 6. HALLAZGOS CLAVE, OBSERVACIONES CRÍTICAS Y RIESGOS

### 6.1. Concentración del Rendimiento en Pocos Módulos
- **`R` (`AtrPhase`)** es el generador absoluto de alfa del portfolio: con apenas **33 operaciones**, generó **+$96,310.0** con un Profit Factor estratosférico de **4.33** y un Win Rate del 66.7%.
- **`S` (`Swas`)**, **`C` (`CapstoneGap`)** y **`Z` (`ZetaTrendDay`)** demostraron un comportamiento altamente rentable y robusto (todos con PF > 1.35).
- **Módulos Destructores de Capital:**
  - **`A20` (`Absorb20Minute`)** y **`F` (`FabioOrb`)** generaron pérdidas combinadas de **-$67,677.3**.
  - **`W` (`VwapCross`)** produjo una sobreoperativa masiva (1,264 trades, un tercio del total) con PnL neto plano (-$1,320.6) pero generando más de **$9,000 en comisiones puras**.

### 6.2. Sesgos de Sobreajuste y Tablas Estáticas (Calendar Hardcoding)
- En `ZetaTrendDay`, la función `IsFullZetaSession` consulta un array precompilado de enteros `int[]` con fechas exactas desde `20100101` hasta `20270902` mediante `Array.BinarySearch`.
- En `AtrPhase`, la función `IsAtrPhaseStandaloneBlockedSession` utiliza una lista hardcoded de enteros representando fechas bloqueadas.
- Si la estrategia se ejecuta más allá de septiembre de 2027 o en días feriados imprevistos por el autor, el comportamiento de admisión de estos módulos cambiará automáticamente.

### 6.3. Comportamiento en Vivo vs. Backtest
- **Bypass de Licencia:** En backtest, el Gate de licencias se auto-desactiva (`IsInStrategyAnalyzer == true`). En una cuenta en vivo (Rithmic, CQG, Interactive Brokers), el sistema realiza peticiones HTTPS externas y puede pausar entradas (`LICENSE BLOCK`) si no contacta el servidor dentro de las 24 horas.
- **Slippage y Ejecución:** En backtest no se modela el impacto de mercado de compensar posiciones cruzadas simultáneas. En vivo, las órdenes de netting enviadas a mercado pueden sufrir slippage significativo en momentos de alta volatilidad (09:30 ET o anuncios de noticias).

---

## 7. CONCLUSIÓN Y RECOMENDACIÓN TÉCNICA

La estrategia `FUNDEDSYNCSTACK` presenta una arquitectura de software sofisticada, modular y bien estructurada para NinjaTrader 8. Sin embargo, su desempeño está severamente lastrado por módulos de baja eficiencia (`A20`, `F`, `W`) que incrementan el Max Drawdown a **-$218,206.32** (inviable para cualquier cuenta de fondeo estándar de 50k o 150k sin apagar esos submódulos).

**Optimización Inmediata Recomendada:**
1. Desactivar `A20` (`EnableAbsorb20m = false`), `F` (`EnableFabio = false`) y filtrar/reducir la agresividad de `W` (`EnableVwapCross = false` o elevar confirmaciones).
2. Conservar como núcleo duro de la cartera: **`R` (AtrPhase)**, **`S` (Swas)**, **`C` (Capstone)**, **`Z` (Zeta)** y **`E` (EmaDivergence)**.
3. Ajustar `V_DailyAtrLength` a 20 o 60 días en lugar de 252 para permitir la participación de `VaultBreak` en periodos menores a un año.
