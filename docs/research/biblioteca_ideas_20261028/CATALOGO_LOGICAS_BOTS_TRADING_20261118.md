# Catálogo Maestro de Lógicas y Parámetros de Bots de Trading

Estado: REFERENCIA — catálogo de ideas externas (commit c8d0e912); encabezado agregado el 2026-11-18 para el protocolo de documentación.

> **Fecha de actualización:** 2026-11-18  
> **Cobertura:** 7 plataformas profundizadas en navegador e investigación web (**Option Alpha, TradingView, QuantConnect LEAN, Composer, WunderTrading, Coinrule, Gainium**) + 4 ecosistemas adicionales de navegador (**Altrady, Pionex, TradersPost, Cryptohopper**) + 4 ecosistemas algorítmicos open-source / mecánicas (**Freqtrade, Hummingbot, Mecánicas QFL/Grid/DCA/TWAP, MQL5/cTrader**).  
> **Nota de rigor:** Cada regla, símbolo, fórmula y parámetro citado proviene exclusivamente de lo observado en sesiones de navegador y resultados verificados de investigación. Donde una fuente pública omite un sub-parámetro, se marca explícitamente como **[Gap]**.

---

## Tabla Maestra de Fuentes y Acceso

| Fuente / Ecosistema | Activos | Estado de Acceso (Navegador / Web) | Tipo de Lógica Extraída |
| :--- | :--- | :--- | :--- |
| **Option Alpha** | Opciones EE. UU. | Prueba gratuita ~29d sin tarjeta (navegador + web) | Árboles visuales (*Scanners*, *Monitors*, *Exit Options*, filtros VIX/IV Rank) |
| **TradingView** | Multi-activo | Sesión activa plan gratuito + prueba 30d | Código **Pine Script** abierto + *Strategy Tester* |
| **QuantConnect LEAN** | Futuros, Opciones, Acciones, FX, Crypto | Logueado vía Google (`nicolas.buttaro.ices@gmail.com`), Lab (94 plantillas) | Algoritmos completos **Python / C#** + investigación académica |
| **Composer** | Acciones, ETFs, Crypto | Investigación web (`defsymphony`) *(app dio timeout)* | DSL `defsymphony` con árboles `IF/THEN`, RSI/SMA/Drawdown/Vol. Inversa |
| **WunderTrading** | Crypto (Spot/Futuros) | Logueado vía Google: Trial **PRO 7 días** + Demo `10,000 USDT` | DCA, Grid, Market Neutral (Z-score), Spread/Arbitraje |
| **Coinrule** | Crypto | Logueado vía Google: Plan gratuito + Demo Wallet | Motor visual *IF-THIS-THEN-THAT* (7 plantillas extraídas) |
| **Gainium** | Crypto (Spot/Futuros) | Logueado vía Google: Demo Mode + 50 backtests | DCA escalado, Grid, Combo Bots y métricas de backtest |
| **Altrady** | Crypto | Logueado vía Google: Trial **5 días** sin tarjeta | 6 tipos de bot incl. señal **QFL / CBS**, TradingView, DCA, Grid |
| **Pionex** | Crypto | Terminal de bots inspeccionada sin tarjeta | 12 bots nativos + fórmulas exactas de Grid, Infinity Grid, Martingala y TWAP |
| **TradersPost** | Acciones, Opciones, Futuros | Google OAuth completado; pausado en campo obligatorio de teléfono | Webhook-to-Broker (NinjaTrader, Tradovate, IBKR, Alpaca) |
| **Cryptohopper** | Crypto | Consentimiento Google OAuth completado; redirigido a `/login` | Mecánicas documentadas de DCA (*Double/Triple Down*) y QFL |
| **Freqtrade** | Crypto | Investigación open-source (`freqtrade-strategies`, `NFI`) | Estrategias Python + tablas ROI, `stoploss`, *hyperopt* y protecciones |
| **Hummingbot** | Crypto (Spot/Perps) | Investigación open-source (`hummingbot`) | Ecuaciones **Avellaneda-Stoikov**, Pure MM y V2 Controllers + Triple Barrier |
| **MQL5 & cTrader** | Forex, Futuros, CFDs | Investigación open-source (`CodeBase` & cBots nativos C#) | EAs/cBots de ruptura, Tortugas, Martingala, London Breakout y Mean Reversion |

---

## 1. Option Alpha (`optionalpha.com`)

### 1.1 *Monthly Iron Condors (`$3k` Portfolio)* & *Iron Condor Manager w/ Challenged Exit Switch*
* **Configuración del bot (observada en navegador):** Paper Trading, asignación `` `$1,000` ``, tope diario `6` trades/día, tope simultáneo `6`, escaneo cada `1m`, tamaño `1 contract`, vencimiento `30 - 45 days`, precio entrada `` `$.04` `` desde *mid*, salida `Profits: 30%`, `Expiration: 1 day`.
* **Scanner (`Iron Condor Scanner for $3k Portfolio`):**
  * **Criterios de entrada:** Capital disponible, `< 1 open position` en el símbolo, `IV Rank` entre `20` y `100`.
  * **Criterios de posición:** `Bid/ask spread < $0.40`, vence antes de ex-dividendo, `Alpha > 5%`, `EV per contract > $5`, `Reward/risk ratio >= 50%`, `Probability of profit > 70%`, `Max loss per contract < $300`, ordenado por `Alpha`.
* **Variante estándar (`Monthly Iron Condors`):** Canasta ETF descorrelacionada (`XSP, GLD, TLT, XOP, XBI, XLP, XLU, XRT, EEM, FXI`), `45 DTE`, strikes cortos `15–20` delta (`~70% POP`), alas de `` `$5–$20` ``, TP `30%–50%` (hasta `70%`), salida temporal a `21 DTE` (o `1 DTE`).
* **Árbol del Monitor (`Challenged Exit Switch`):**
  1. Itera sobre Iron Condors abiertos.
  2. Comprueba `Current DTE <= Expiration Threshold` (default `3 DTE` o `5 DTE`).
  3. Comprueba `Challenged Exit Switch == ON`.
  4. Verifica si el precio subyacente cruzó/rompió alguno de los strikes cortos *(en variantes 0DTE comprueba si la probabilidad ITM de la pata amenazada supera `20%` cerca del cierre)*.
  5. Ejecuta `Exit Position` de inmediato *(o en variantes `Synthetic Iron Condor` abre un credit spread contralateral para convertirlo en iron butterfly sintético)*.

### 1.2 *Opening Range Breakout* (`Opening Range Breakout 60m`, `Orb Weaver`, `ORB Bot_0-1DTE`)
* **`Opening Range Breakout 60m` (Template oficial):** `SPY`/`SPX`; mide `ORH`/`ORL` en los primeros `60` min (hasta `10:30 AM ET`). Dispara al romper el rango con corte horario `<= 12:00 PM ET` y filtro de movimiento mínimo (ej. `0.2%`). Abre credit spreads `0DTE`/semanales (ej. `` `$15` `` o `` `$10` `` de ancho, tope de pérdida `` `$950` ``).
* **`Orb Weaver` (`0DTE SPX` por Anthony):** Ventana asimétrica: `30` min para Call spreads (ruptura alcista) y `15` min para Put spreads (ruptura bajista). Corre `<= 1:00 PM ET` con filtro `ROC(25) < 5`. Compra opción ATM + vende pata a `10` puntos (debit spread `10`-wide, R:R `>= 1:1`), mantenido hasta expiración (`0DTE`).
* **`ORB Bot_0-1DTE` (por simplitee):** Watchlist `SPY, QQQ, DIA, IWM`, `posLimit: 2`, `posLimitDay: 2`. Scanner (~33 inputs) activo `10:20 AM – 11:00 AM EST` con piso de `VIX` (`15–20`) y filtro de rango lateral `ADX(14)`. Monitor (~13 inputs) corre cada `1` minuto con objetivo límite `~15%` y salida de monitor `~10%`.

### 1.3 *0DTE Iron Butterfly* & *0DTE Credit Spreads*
* **`Theta Harvest Butterfly` (`0DTE SPX`):** Escáner `1:30 PM – 1:35 PM ET`; filtros `SMA(10)` y `EMA(10)` por encima; evita **FOMC** y fin de mes. Iron Butterfly ATM (`~ -0.50` delta), alas simétricas de `` `$45` ``, asignación base `` `$10,000` `` por `1` contrato; mantenido hasta expiración.
* **`Flat Fly` / `Flat Flyer` (`0DTE SPX`):** Entrada matutina `10:00 AM – 10:15 AM ET` (L/X/V); bloquea eventos **PMI** y **Consumer Event** para evitar anomalías de precios a las `10:00 AM`.
* **`WiFly 1DTE $60 Wide` (`SPX 1DTE`):** Escáner `1:30 PM – 1:40 PM ET`; strike corto al precio actual, alas de `` `$60` `` (`` `$30–$40` `` en forks), `VIX < 25`, `Reward/Risk >= 180%`, evita FOMC/CPI; TP en `15%` del crédito inicial.
* **`0DTE - Research Insights Bot`:** `SPY` (o `SPXW`); `1` posición/día, `1` contrato; entra Short Put/Call Credit Spread a las `10:30 AM ET`; TP `85%` y cierre forzado `1h` antes del cierre (`3:00–3:30 PM ET`).
* **`Theta Fly Trap` (NFH/FFH):** Evalúa Expected Move de `SPX 0DTE` (`EM% of EM at Open`) e `IV Rank < 50`. La cascada FFH ensancha alas en incrementos de `` `$5` `` solo si el crédito neto sube proporcionalmente, acotando R:R entre `25` y `100`. Monitor vigila distancia a strikes cortos y cierra antes de `3:00–3:30 PM ET`.
* **`Trendy Short Put Spread`:** Filtro de tendencia (`EMA 50/200` o RSI/MACD), strike corto `0.15–0.30` delta, TP `25%–50%` + `SmartStops` (trailing dinámico).

### 1.4 *Wheel Strategy* & *Filtros de Régimen VIX / IV Rank (`Hexabot`)*
* **Wheel Fase 1 (CSP Scanner):** `30–45 DTE`, `0.16–0.30` delta OTM, `Open Interest > 100`, evita *earnings*, filtro de tendencia (`SMA(5)` subió al menos 1 vez en últimos `3` días).
* **Wheel Fase 2 (Monitor & Asignación):** Cierre temprano al `50%` de ganancia máxima. Si detecta acciones asignadas, desactiva CSP y activa **Covered Call** (`~0.30` delta sobre *cost basis*). En modo *Advanced Wheel*, abre un 2.º tramo CSP simultáneo si hay *buying power*; al ejecutarse el call, resetea etiquetas y reinicia Fase 1.
* **Recetas VIX / IV Rank & Calendario:** Soporta `VIX`, `VIX1D`, `VIX9D`, `VIX3M`, `VIX6M`, `VVIX` (techos usuales `VIX < 25` o `< 30`). `IV Rank = (IV_actual - Min_52S) / (Max_52S - Min_52S)` (créditos piden `> 25` o `> 50`; butterflies `< 50` o `0–25`). Bloqueos en **FOMC, CPI, PPI, PCE, NFP, Triple Witching y vencimientos VIX**. **`Hexabot`:** máx. `5%` por ticker, `10%` NLV del bot por trade, `30–60 DTE`, `0.30` delta, alas `5`-pt, TP `20%–50%` (acelerado con menos DTE) y revisión/roll a `1 DTE`.

---

## 2. TradingView (Estrategias Abiertas en Pine Script)

1. **`Gaussian Trend Targets | Supertrend Strategy w/ 3R Exits` (`blitz_algo`, 404 líneas):** Mediana suavizada por filtro gaussiano + bandas ATR/desviación gaussiana tipo Supertrend. Tres vetos opcionales: `RMI = (RSI + MFI)/2`, WMA lenta de régimen, EMA HTF (barra cerrada previa). Riesgo fijo `1%` equity por trade; costos default `0.05%` comisión + `2 ticks` slippage; salidas **TP1 `40%` a `1R` (stop a BE)**, **TP2 `30%` a `2R` (stop a TP1)**, **Runner `30%` a `3R` o trailing por banda**.
2. **`Supertrend Strategy` (`Built-in` / `KivancOzbilgic`):** `ATR(10)`, `mult = 3.0`, `hl2` (`changeATR = true` alterna RMA/SMA). Stop-and-reverse al giro (`direction` o `trend`).
3. **`AlphaTrend` (`KivancOzbilgic`):** `coeff = 1.0`, `AP = 14`, `ATR = sma(tr, 14)`, `upT = low - ATR`, `downT = high + ATR`; filtro `MFI(14)` (`hlc3`) o `RSI(14)` (`novolumedata = true`); señales confirmadas contra 2 barras previas (`O1 > K2` / `O2 > K1`).
4. **`UT Bot` (`QuantNomad` / `Yo_adriiiiaan`):** `Key Value = 1` (antes `3`), `ATR(10)`, opcional Heikin Ashi. Trailing stop con trinquete (`nLoss = Key Value * atr(10)`) y stop-and-reverse al cruce de precio.
5. **`Chandelier Exit` (`everget`):** `length = 22`, `mult = 3.0`, `useClose = true`. `longStop = highest(close, 22) - 3*atr(22)` y `shortStop = lowest(close, 22) + 3*atr(22)` con trinquete; señales en cambio de `dir`.
6. **`Squeeze Momentum` (`LazyBear`):** `BB(20)` dentro de `KC(20, 1.5*TR)` *(nota: el código original usa `multKC` en `dev = multKC * stdev`)*; histograma `val = linreg(close - avg(avg(highest(high,20), lowest(low,20)), sma(close,20)), 20, 0)`. Entra al salir del squeeze según signo de `val` y sale al desacelerar (`val < val[1]`).
7. **`Bollinger + RSI Double Strategy v1.1` (`ChartArt`):** `BB(200, 2)` + `RSI(6)` (`50/50`). Largo: `crossover(close, BBlower) and rsi < 50`; Corto: `crossunder(close, BBupper) and rsi > 50`.
8. **`ATR Mean Reversion Strategy` (`ZenAndTheArtOfTrading`):** Solo largos. Entra si `close < EMA(20) - ATR(5)*1.0` **AND** `close > EMA(200)`; sale cuando `close >= EMA(20)`.
9. **`Turtle Trade Channels Indicator (TuTCI)` (`@KivancOzbilgic`):** `length = 20` (entrada) y `len2 = 10` (salida). Largo al cruzar `upper[1]` (`highest(high, 20)`), sale al cruzar `sdown[1]` (`lowest(low, 10)`); inverso para cortos.
10. **`Profit Maximizer (PMax)` (`@KivancOzbilgic`):** `hl2`, `Periods = 10`, `Multiplier = 3.0`, `mav = "EMA"`, `length = 10`, `changeATR = true`. Construye bandas Supertrend alrededor de `MA` en lugar del precio (`MA ± 3*ATR`) y hace stop-and-reverse al cruzar `MA` vs `pMax`.
11. **`SSL Hybrid` (`Mihkel00`):** `Baseline = HMA(60)`, bandas `± 0.2 * ATR(14)` (suavizado WMA); `SSL2 = JMA(5)` (o HMA) con filtro de continuación `abs(Close - SSL2) <= 0.9 * ATR`; salida al cruzar `Exit = HMA(15)`.
12. **`Gaussian Channel [DW]` (`DonovanWall`):** `src = hlc3`, `sampling = 14` (preset macro `144`), `poles = 4`, `mult = 1.414`. Filtro recursivo Ehlers de 9x polos (`f_filt9x`) aplicado al precio (`filt`) y al True Range (`tr_filt`); entra largo en `crossover(close, filt + tr_filt * 1.414)` y sale en `crossunder`.
13. **`WaveTrend [LazyBear]` (`WT_LB`):** `n1 = 10`, `n2 = 21`, `hlc3`, niveles `±53` / `±60`. `esa = ema(hlc3, 10)`, `d = ema(|hlc3 - esa|, 10)`, `ci = (hlc3 - esa)/(0.015*d)`, `wt1 = ema(ci, 21)`, `wt2 = sma(wt1, 4)`. Cruces filtrados en zonas extremas (`wt1 < -53` / `wt1 > 53`).
14. **`Smart Money Concepts [LuxAlgo]` (OB / FVG / BOS / CHoCH):** `Swing Length = 50`, `ShowIOB = true` (`Show Last = 5`), `OBFilter = "Atr"` (o `"Cumulative Mean Range"`), `FVGAuto = true`, `EQLen = 3`, `EQThreshold = 0.1`. FVG alcista: `low > high[2] and close[1] > high[2]`. Envoltorios estratégicos entran al retesteo de OB/FVG sin mitigar, stop bajo zona/mecha y TP a `2.0R`.
15. **Larry Connors `RSI(2)` Mean Reversion:** Solo largos: `close > sma(close, 200) and rsi(close, 2) < 5` (entra siguiente apertura); sale en `close > sma(close, 5)`.
16. **Built-ins & Patrones Clásicos Pine:**
    * `Bollinger Bands directed` (`20, 2.0`, órdenes stop con `oca.cancel`); `Keltner Channels` (`20, 2.0, EMA, ATR 10`); `ChannelBreakOutStrategy` (Donchian `5`); `MACD Strategy` (`12, 26, 9`).
    * Patrón `MACD + ADX` (`ADX(14) > 25` + `+DI/-DI`, SL `2%` / TP `4%` comunes) *(plantilla comunitaria, sin ID único)*.
    * Patrón `VWAP StDev Bands` (`±1, ±2, ±3 SD` ponderado por volumen; reversión a `vwap` o breakout) *(plantilla comunitaria)*.
    * Patrón `ORB` (`0930–0945`/`1000` NY, stop en borde opuesto o `1.5*ATR(14)`, TP `2.0R`, cierre `1545–1600`).

---

## 3. QuantConnect LEAN (Plantillas del Lab + Algoritmos Documentados)

### 3.1 Plantillas Inspeccionadas del Lab (17 de las 94 disponibles)
1. **Equity RSI Overbought/Oversold** *(Clonado en Proyecto `39640998`)*: `QQQ`, `RSI(14)` (`<30` largo, `>50` sale; `>70` corto, `<50` cubre).
2. **Equity Bollinger Mean Reversion:** `SPY`, `BB(20, 2 SD)`, rebalanceo diario; compra bajo banda inferior y liquida en banda media.
3. **Equity Aroon Trend:** `SPY`, `AroonOscillator(25)`; largo en `+50`, salida en `-50`.
4. **Equity Parabolic SAR Trailing Stop:** `SPY` (solo largos) con Parabolic SAR.
5. **Option SPY Iron Condor:** Semanales `SPY`, cortos ~10 delta, alas largas 3 strikes afuera.
6. **Equity Pairs Trading (Cointegration):** `KO` vs `PEP`, ratio OLS `60` días + z-score.
7. **Equity Dual Momentum (Antonacci):** `SPY`, `EFA`, `AGG`, retorno `12m`, fallback a `AGG`.
8. **Equity Options Universe:** Filtra semanales `SPY` a calls & puts ATM y ejecuta **long straddle**.
9. **Intraday Index Options Selection:** Carga cadena semanal `SPX` diaria y refiltra calls ATM cada `5` min.
10. **Intraday Greeks-Based Options Selection:** Opciones sobre índice `RUT` seleccionadas intradía por delta objetivo desde señales `EMA`.
11. **Futures (E-mini S&P 500):** Futuro continuo `ES` con roll por `SymbolChangedEvents`.
12. **Crypto Futures:** Futuros `BTC`, `ETH`, `LTC` en Binance margen `USDT`, rebalanceo semanal con tracking de interés de margen.
13. **Crypto Universe:** Top 10 criptos por volumen USD en Coinbase, rebalanceo diario al mediodía.
14. **Forex (Spread-Filter):** Opera 3 pares FX usando indicador `Minimum` sobre el spread bid-ask para entrar solo con spreads estrechos.
15. **Equity ADX Trend Filter:** Cruce `50/200 EMA` + filtro de régimen `ADX(14) > 25` en `SPY`.
16. **Equity Fisher Transform Reversal:** `QQQ` con `FisherTransform`, operando en contra de extremos `> 2.0` y `< -2.0`.
17. **Equity Donchian Turtle Breakout:** Canal Donchian `20/10` en ETFs líquidos EE. UU. con sizing basado en `ATR`.

### 3.2 Estrategias Documentadas de Futuros, Stat-Arb, Intradía y Regímenes
* **Dual Thrust (Michael Chalek):** `SPY` horario + barras diarias (`N = 4`, `k1 = k2 = 0.5`). `rng = max(hh - lc, hc - ll)`, `buytrig = open + 0.5*rng`, `selltrig = open - 0.5*rng`; reversión pura `±100%`.
* **Dynamic Breakout II (George Pruitt):** Diario. `numdays` adaptativo `[20, 60]` actualizado por `deltavol = (todayvol - yesterdayvol) / todayvol` (`31` cierres). Entrada largo si `yesterdayclose > upband` (`BB(numdays, 2, EMA)`) **AND** `price > max(high[-numdays:])`; liquida al cruzar `mean(close[-numdays:])`.
* **ORB Stocks in Play (Zarattini, Barbon & Aziz, 2024):** Top `1,000` acciones EE. UU., precio `` `> $5.00` ``, `ATR(14) > $0.50`, top `20` por **RVOL** de los primeros `5` min (`09:30–09:35 EST` vs media `14d`). Ruptura high/low de `5m`, stop basado en `ATR(14)` **[Gap: multiplicador ATR exacto no impreso]**, sizing `Shares = (Equity * Risk%) / |Entry - Stop|`, cierre EOD.
* **TSMOM & TSMOM-CF (31 Futuros CME):** Contratos continuos `OPEN_INTEREST` + `BACKWARDS_RATIO`, rebalanceo mensual, `12m` (~`252d`). TSMOM-CF usa volatilidad objetivo `12%`, señal continua por *t-stat* acotada `[-1, +1]`, estimador OHLC Yang-Zhang y ajuste por correlación cruzada `CF(ρ̄_t)`: $\text{Weight}_{i,t} = (0.12 / \sqrt{N_t}) \cdot (X_{i,t} / \sigma_{i,t}) \cdot CF(\bar{\rho}_t)$.
* **HMM Intradía (`5m`):** Top `10` acciones por market cap, `ROC` sobre `~150` barras (`5m`), HMM de `3` estados reentrenado mensualmente; largo si `P(pos) > P(neg)` sino corto, peso `10%` c/u.
* **Kalman Filter Stat-Arb:** `pykalman` recursivo sobre pares FX/acciones (`y_t = β_t * x_t + α_t + ε_t`); entra cuando `|Z| > 2`, sale en `Z = 0`.
* **PCA Mean-Reversion:** Acciones `> $5` ordenadas por volumen en dólares; `ln(Price)` proyectado sobre `3` Componentes Principales; largo en residuales negativos y corto en positivos.
* **Intraday Pairs Trading 10m (Miao & Jing Wu):** Bancos EE. UU., correlación `>= 0.9`, Engle-Granger `p <= 0.05`, filtro *half-life* `1 día <= HL <= 1 año` (Miao). Entra en `|Z| > 2` (o `±2.33` en Wu) y sale en `Z = 0` (`±0.5` en Wu).
* **Copula vs. Cointegration Pairs:** Cointegración (`ADF p < 0.05`) vs. Cópulas (**Clayton, Gumbel, Frank**) sobre CDFs empíricas, disparando cuando `P(A <= u | B <= v) > 0.95` o `< 0.05`.
* **Anomalías Académicas Documentadas:**
  * *Short-Term Reversal (De Groot et al.):* Top `100` por volumen USD, `ROC(22d)` semanal; largo bottom `10%`, corto top `10%`.
  * *Momentum + Volatilidad:* Mitad superior de market cap (`` `> $5` ``), lookback `6` meses saltando `1` semana; dentro del quintil superior de volatilidad a 6m, largo quintil superior de retorno / corto quintil inferior (rebalanceo escalonado `1/6` mensual).
  * *Intraday ETF Momentum (Gao et al.):* Retorno de los primeros `30` min (`9:30–10:00`) replicado en los últimos `30` min (`15:30–16:00`).
  * *VIX `504d` Deciles*, *Turn of the Month* (Day `-1` a Day `+3`), *Volatility Risk Premium* (vende Straddle ATM + compra Put `15%` OTM mensual `~30 DTE`), *Asset Class Trend Following* (`Close > SMA(10m)`).
* **Repositorio Oficial `QuantConnect/Lean/Algorithm.Python/` & Modelos Built-in:**
  * `FuturesMomentumAlgorithm.py` (`ES`, señal `SPY` `EMA(20) > EMA(60)*1.001`), `EmaCrossFuturesFrontMonthAlgorithm.py` (`GC` front month `EMA(100) > EMA(300)*1.001`), `BasicTemplateContinuousFutureAlgorithm.py` (`ES` `SMA(4) - SMA(10) > 0.001`), `BasicTemplateFuturesConsolidationAlgorithm.py` (`ES` consolida a `30m`), `BasicTemplateFuturesHistoryAlgorithm.py` (`ES` & `GC`).
  * Defaults built-in: `EmaCrossAlphaModel(12, 26, DAILY)`, `MacdAlphaModel(12, 26, 9)`, `RsiAlphaModel(14)`, `PearsonCorrelationPairsTradingAlphaModel(lookback=15, bar_count=30, min_corr=0.5)`, `StandardDeviationExecutionModel(deviations=2, period=60)`, `MaximumDrawdownPercentPerSecurity(0.05)`, `TrailingStopRiskManagementModel(0.05)`.

---

## 4. Composer (`composer.trade`) — *Symphonies* (`defsymphony`)

1. **Dual Momentum (`SPY, QQQ, ACWX, AGG`):** Mensual, retorno `12m` (`252d`). `100%` al mejor ETF accionario si `> 0%`, si no `100% AGG`.
2. **Big Tech Momentum (`AAPL, MSFT, GOOGL, AMZN, META, NVDA, ADBE, PYPL/TSLA`):** Mensual (o semanal), top `2` por retorno `20d` (`50%/50%`).
3. **Investment Principles (`Deez`, verbatim):** `:rebalance-threshold 0.01618`. Si `max-drawdown("SPY", 17) > 5%` $\rightarrow$ `100% BIL`; si no: `40%` (`XLF, QQQ, MSTR` por vol. inversa `90d`), `30% DBC`, `30%` (`ARKK, TSLA, NVDA` por vol. inversa `90d`).
4. **Inverse Volatility Core / All-Weather / HFEA:** `VTI, TLT, IEF` por `weight-inverse-volatility 90`; All-Weather `30% VTI / 40% VGLT / 15% VGIT / 7.5% GLDM / 7.5% PDBC`; HFEA `55% UPRO / 45% TMF` si `SPY > SMA(200)`, si no `100% BIL`/`SGOV`.
5. **RSI Tester (`TQQQ, UVXY, BIL`, diario):** Escala gradual por `RSI(TQQQ, 10)`: `<= 80.5` $\rightarrow$ `100% TQQQ`; `(80.5, 81]` $\rightarrow$ `20/80 UVXY/BIL`; `(81, 82.5]` $\rightarrow$ `40/60`; `(82.5, 83]` $\rightarrow$ `60/40`; `(83, 83.5]` $\rightarrow$ `80/20`; `> 83.5` $\rightarrow$ `100% UVXY`. Variante binaria **`RSI 82`**: `> 82` $\rightarrow$ `100% UVXY`, si no `100% TQQQ`.
6. **RSI Test (`BND, SPY` $\rightarrow$ `TQQQ, BIL`):** `IF RSI(BND, 20) > RSI(SPY, 20) THEN 100% TQQQ ELSE 100% BIL`.
7. **`zoop's TQQQ 200d MA 3x Leverage`:** `IF QQQ > SMA(200) THEN 100% TQQQ ELSE cash/defensivo`.
8. **`zoop's 2026 Frontrunner` (`SPY, QQQ, TQQQ, SOXL, TECL, UVXY, VXX, SH, SPXU, BIL`):** Compuertas de volatilidad `RSI(UVXY, 21) > 65` o `RSI(UVXY, 30) > 63` (niveles hasta `84`); con `SPY` sobre MA deriva a `SPXU`, bajo MA a `BIL`/`TQQQ`; sobrecompra `RSI(10) > 77–80.5` $\rightarrow$ `UVXY/VXX/SH/SPXU`; sobreventa `RSI(10) < 30` $\rightarrow$ `TQQQ/SOXL/TECL` **[Gap: orden completo exacto varía entre builds]**.
9. **TQQQ For The Long Term (FTLT):** Diario. Con `SPY > SMA(200)`: si `RSI(10) TQQQ > 79` (o `SPXL > 80`) $\rightarrow$ `UVXY`/cash, si no `TQQQ`. Con `SPY < SMA(200)`: si `RSI(10) < 31` $\rightarrow$ `TECL`/`TQQQ`; bajo `MA(20)` $\rightarrow$ `SQQQ`/defensivo.
10. **`Simon's KMLM Switcher`:** Diario. Evalúa canasta de `11` tickers contra topes `RSI(10)` (`75–80`) $\rightarrow$ `100% UVXY`. Si ninguno dispara, compara `RSI(XLK, 10)` vs `RSI(KMLM, 10)`: si lidera `XLK`, divide `50/50` entre los **2 peores por `RSI(10)`** de `{TECL, SOXL, SVIX}`; si lidera `KMLM`, asigna `100%` al mayor por `RSI(10)` de `{SQQQ, TLT}`.
11. **`Pop / TQQQ or not / SOXX Group`:** `RSI(10) > 79` $\rightarrow$ `UVXY`; puerta `RSI(UVXY, 30) > 63` habilita chequeos de `SMH` en `30d/20d/10d` RSI para alternar `SOXL` vs `SOXS` **[Gap: % exacto de caída/rebote diario]**.
12. **`QLD For The Long Term`:** `SPY > 200d MA` mantiene `QQQ`/`QLD` (rota a `PSQ`/`TLT` en sobrecompra); bajo `200d MA` alterna `SHY`/`BSV`, rebotes en `QLD`/`SSO` o cortos `PSQ`/`QID`.
13. **`Hedged Sector Rotator` / `Feaver Frontrunner` / `Beta Ballers`:** `60%` rotación sectorial SPDRs + `TECL`/`FAS` y `40%` defensivo (`TLT/TMF/TMV/BIL/BND/UVXY/VIXY/SVXY/SH/PSQ`); `Feaver` asigna `40% BIL` + `RSI >= 80 -> UVXY/BTAL`, `RSI <= 30 -> 3x bull`, `200d SMA -> PSQ/SQQQ`; `Beta Ballers` incluye sub-árbol de tasas (`TLT < 200d MA` + momentum `20d < 0` $\rightarrow$ `TMV` vs `TMF`).

---

## 5. WunderTrading (Trial PRO 7 Días + Demo `10,000 USDT`)

* **DCA Bot:** Dirección `Long / Short / Both`; inicio `Immediate`, `Price change`, `Indicator` (presets públicos ej. `ARIA/USDT` Long Immediate, `GTC/USDT` Long/Short Price Change); `Amount per trade: 20` (o `5%–100%`), `Max DCA orders: 20`, `Price deviation: 0.8%`, `Order size mult: 1`, `Price dev. mult: 1.2`, `Take profit: 0.8%` (`Market` sobre precio promedio), `SL`, `Move SL to BE`, `Trailing Stop`.
* **Grid Bot (`wundertrading.com/en/trader/grid_bots`):**
  * Modos: `Long`, `Neutral`, `Short`, `Hedge Grid`; tamaño `Interval` o `Infinite`.
  * Defaults observados (`ETHUSDT`): Lower `1227.24`, Higher `2270.07`, `Profit per Grid: 3%`, `Grids: 20`, `Amount per trade: 20 USDT` (`380 USDT` requeridos).
  * Disparadores y salidas: Inicio (`Immediate`, `Indicator`, `Webhook`); Salida (`Take Profit`, `Stop Loss`, `Trailing Stop`, `Stop Trigger`, `Pump Protection`, `Positions trailing stop`, `Positions stop loss`) + Backtest integrado `1h`.
* **Market Neutral Bot (`wundertrading.com/en/trader/market_neutral`):**
  * Arbitraje estadístico (futuros Long & Short): `Trade direction` (`Mean reverse` / `Trend`), `Z-score rolling window` (`288` o `2880`), `Quantile group` (`1`, `5`, `10`), `Volatility` (`High`, `Low`, `Both`), `Entry Condition` (`Out of the channel`, `Into the channel`, `Outside the channel`).
  * Riesgo y ejecución: `Amount per trade: 50 USDT`, `Max open positions: 1`, `Risk` (`Low: sin apalancamiento` hasta `High: >10x`), `Stop Loss: 5%` (TP y SL por moneda opcionales), `Order type` (`Auto`, `Market`, `Limit-market`).
* **Spreads & Arbitrage (`wundertrading.com/en/trader/spread_arbitrage`):** Spread trading entre dos activos relacionados y arbitraje cross-exchange usando `Z-score`, `Beta (Hedge Ratio)` y `Half-life`.

---

## 6. Coinrule (Demo Wallet — Motor IFTTT)

1. **`Ride The Trend`** (Tope `` `$150 USDT` ``, máx. `10` trades abiertos):
   * **Entrada:** `RSI(14) < 30` (`5m`) **AND** `MACD < zero line` (`5m`) **AND** `MFI < 20` (`5m`) $\rightarrow$ `BUY $15` con `USDT` (`limit`; excluye stablecoins, fiat y `BTTC`, sin recomprar hasta vender).
   * **Salida:** `RSI(14) > 70` (`5m`) **AND** `MACD > zero line` (`5m`) **AND** `MFI > 60` (`5m`) **AND** `price increased by +1%` $\rightarrow$ `SELL 100%` (`limit`).
2. **`Smart DCA`:** Acumula una moneda diaria/semanalmente y toma ganancia con objetivo `10%` (P&L 14d mostrado en plataforma `+22.59%`, `91%` win rate).
3. **`Price Tracker`:** Monitorea precios en marcos cortos y toma beneficios en subidas (`+20.12%` P&L 14d, `100%` win rate).
4. **`Volatility Trend Surge`:**
   * **Entrada:** `ATR(14)` salta `+25%` en `5` minutos **AND** `MA(2) > MA(50)` en velas diarias (`1D`).
   * **Salida:** Precio sube `+5%` **OR** la volatilidad enfría (`ATR(14)` cae `-40%`).
5. **`VWAP & RSI Rebound`:**
   * **Entrada:** Precio `below VWAP` **AND** `RSI < 30`.
   * **Salida:** `VWAP` confirma reversión de tendencia **OR** `RSI > 50` **OR** `+4%` TP / `-2%` SL.
6. **Otras plantillas observadas:** `Buy the Dips` (compras en caídas + trailing SL), `Grid Trading` (escalera fija dentro de un rango) y `Moving Average Scalper` (`4` medias móviles para detectar giros de tendencia bajista).

---

## 7. Gainium (Demo Mode — Paper Trading Spot/Futuros & Backtester)

* **DCA Bot — *Blue Chips DCA* (`Bybit Paper Futures USDM`, PnL realizado `` `+$2,578.33 / +25.82%` ``, `143` deals):** `BTC, ETH, SOL, ADA, BNB` (`USDT`), Long `3x Isolated`, inicio `ASAP`, `Base Order: 100 USDT` (*Chasing Limit* `10s`, `0%`), `Max open deals: 5` (`1` por par), TP `5.00%` `Limit`, DCA `Scaled` (`14` órdenes, `100 USDT`, `step 2%`, `step scale 1.1`, `volume scale 1.2`, `Smart orders: 1`, cobertura `55.95%`, `` `$6,122.30` `` máx. / `` `$2,040.77` `` margen, sin SL).
* **Grid Bots (`app.gainium.io/grid`):**
  * `BTC Grid` (`Binance Paper Spot`): Presupuesto `` `$100.02` ``, `10` niveles, `52` transacciones en `189d`, PnL neto `` `+$6.83 (+6.86%)` `` (`+18.34%` anualizado).
  * `SHIB Grid` (`Bitget Paper Spot`): Presupuesto `` `$999.54` ``, `50` niveles, `76` transacciones en `315d`, `+4.02%` anualizado.
  * `SUIUSDT / UNIUSDT Grid Mid-term` (`Binance` / `OKX Paper Futures USDM`): Presupuesto `` `$299.96` `` / `` `$249.97` ``, `20` niveles.
* **Combo Bots (`app.gainium.io/combo`, DCA + Grid combinado):**
  * `ETH Combo` (`Hyperliquid Paper Futures USDM`, `ETH/USDC` Long): Tope `` `$917.11` ``, `6` deals en `357d`, PnL realizado `` `+$132.13 (+14.02%)` `` (`+12.25%` anualizado).
  * `Hyperliquid Linear Combo`: Tope `` `$913.67` ``, `20` deals en `357d`, `+55.78%` anualizado.
* **Presets del Backtester (`app.gainium.io/bot/backtests`, 50 guardados):**
  * `BTCUSDT DCA Mid-term 2026-10-29` (Variante 1): `TechnicalIndicators` start, `1h`, `1124d`, retorno `+76.65%`, max DD `-11.92%`, PF `1.41`, `5,052` deals.
  * Variante 2: `TechnicalIndicators` start, `1h`, `1124d`, retorno `+69.35%`, max DD `-11.70%`, PF `1.39`, `5,654` deals.

---

## 8. Nuevas Plataformas Exploradas en Navegador

### 8.1 Altrady (`app.altrady.com`, Trial 5 Días vía Google Sign-In sin tarjeta)
* **6 tipos de bots inspeccionados en onboarding:**
  1. **DCA Bot:** Entrada inmediata o por indicadores + escalera de *safety orders*.
  2. **Grid Bot (solo Spot):** Compra/venta en grilla dentro de rango de precios.
  3. **TradingView Bot:** Automatiza cualquier estrategia Pine Script (entradas, salidas, reversiones).
  4. **Signal Bot:** Opera señales nativas de **Crypto Base Scanner (CBS / QFL)** y **The Better Traders**.
  5. **HODL Bot (solo Spot):** Compras recurrentes programadas.
  6. **Webhook Bot:** Ejecución personalizada vía webhook.

### 8.2 Pionex (`pionex.com/en/trade/BTC_USDT/Bot`, Terminal de Bots Gratuita)
* **12 bots integrados categorizados por régimen (`Sideways`, `Bullish`, `Bearish`):** Grid Trading Bot, DCA Bot (Martingale), Rebalancing Bot (índice multi-moneda), TWAP, Spot-Futures Arbitrage Bot (arbitraje de *funding rate*), Margin Grid Bot (hasta 5x), Reverse Grid Bot, Infinity Grid Bot, Smart Trade (entrada + trailing TP + SL), Trailing Sell, Trailing Buy, Stop Limit.

### 8.3 TradersPost & Cryptohopper (Estado de Acceso)
* **TradersPost (`app.traderspost.io`):** Login con Google completado (`nicolas.buttaro.ices@gmail.com`); pausado en Paso 1 porque exige campo obligatorio de `Phone number`.
* **Cryptohopper (`cryptohopper.com/login`):** Consentimiento Google OAuth completado, pero redirigió de vuelta a `/login` (*"Please login first"*) sin persistir sesión.

---

## 9. Freqtrade (`freqtrade-strategies` & `NostalgiaForInfinity`)

1. **`SampleStrategy` (`5m`, `startup_candle_count = 200`):**
   * **Config:** `minimal_roi = {"60": 0.01, "30": 0.02, "0": 0.04}`, `stoploss = -0.10`, `trailing_stop = False`.
   * **Indicadores:** `RSI` (**[Gap: período default TA-Lib 14 no impreso verbatim]**), `Bollinger(typical_price, 20, 2)`, `TEMA(9)`.
   * **Entrada / Salida:** Largo si `crossed_above(rsi, 30) & (tema <= bb_middleband) & (tema > tema.shift(1)) & (volume > 0)`. Salida si `crossed_above(rsi, 70) & (tema > bb_middleband) & (tema < tema.shift(1)) & (volume > 0)`.
2. **`CombinedBinHAndCluc` (`5m`):**
   * **Config original:** `minimal_roi = {"0": 0.05}`, `stoploss = -0.05` *(forks `V5/V6` usan `-0.99` + custom stoploss/trailing **[Gap: valores exactos en V5/V6]**)*.
   * **Bloque BinHV45:** `BB(close, 40, 2)`, `bbdelta = |mid - lower|`, `closedelta = |close - close.shift()|`, `tail = |close - low|`. Condición: `(lower.shift() > 0) & (bbdelta > close*0.008) & (closedelta > close*0.0175) & (tail < bbdelta*0.25) & (close < lower.shift()) & (close <= close.shift(1))`.
   * **Bloque ClucMay72018:** `BB(typical_price, 20, 2)`, `ema_slow = EMA(50)`, `volume_mean_slow = rolling(30).mean()`. Condición: `(close < ema_slow) & (close < 0.985 * bb_lowerband) & (volume < volume_mean_slow.shift(1) * 20) & (volume > 0)`.
   * **Entrada (`OR` de ambos bloques) / Salida:** Sale cuando `close > bb_middleband`.
3. **`ADXMomentum` (`1h`, `startup_candle_count = 20`):**
   * `minimal_roi = {"0": 0.01}`, `stoploss = -0.25`. Indicadores: `ADX(14)`, `PLUS_DI(25)`, `MINUS_DI(25)`, `SAR`, `MOM(14)`.
   * **Entrada:** `(adx > 25) & (mom > 0) & (plus_di > 25) & (plus_di > minus_di)`. **Salida:** `(adx > 25) & (mom < 0) & (minus_di > 25) & (plus_di < minus_di)`.
4. **`ReinforcedSmoothScalp` (`1m` + `resample_factor = 5`):**
   * `minimal_roi = {"0": 0.02}`, `stoploss = -0.10`. Indicadores `MFI`, `STOCHF (fastk/fastd)`, `ADX`, `CCI`, `EMA(high/low/close)` **[Gap: períodos internos exactos]** + tendencia `5m`.
   * Defaults hyperopt: compra `adx=32, fastd=30, fastk=26, mfi=22`; venta `adx=53, cci=183, fastd=79, fastk=70, mfi=92` con condición `open > ema_high`.
5. **`NostalgiaForInfinity` (`NFI X`–`X8`, `5m` + `1h/4h`):**
   * `NFI X` moderno usa `stoploss = -0.99` con salidas personalizadas (`doom`/`dead-fish`), `derisk` y ajuste DCA (`rebuy_mode`/`grind_mode`); variante previa observada: `minimal_roi = {"0": 0.218, "19": 0.088, "49": 0.038, "141": 0.012}`, `stoploss = -0.247`, `trailing_stop = True` (`0.01` / offset `0.011`).
   * Familias etiquetadas (`entry_tag` `1`, `21`, `41`, `61`, `101`, `120`, `141`, `161`): `normal_mode`, `pump_mode`, `quick_mode`, `rapid_mode`, `rebuy_mode`, `grind_mode`. Indicadores: `EMA`, `ZEMA`, `BB`, `RSI`, `StochRSI`, **EWO** (Elliott Wave Osc.), **CTI** (Chande Trend Index), más **compuerta macro BTC (`1h/4h`)** y filtros anti-pump / *flying-knife* **[Gap: fórmulas booleanas completas de cada tag]**.

---

## 10. Hummingbot (Market Making & V2 Controllers)

### 10.1 Avellaneda-Stoikov Market Making
* **Precio de reserva:**
  $$r(s, q, t) = s - q \cdot \gamma \cdot \sigma^2 \cdot (T - t)$$
* **Spread óptimo simétrico:**
  $$\delta_a + \delta_b = \gamma \cdot \sigma^2 \cdot (T - t) + \frac{2}{\gamma} \ln\left(1 + \frac{\gamma}{\kappa}\right), \qquad \delta_a = \delta_b = \frac{1}{2}(\delta_a + \delta_b)$$
* **Calibración y defaults Pydantic:**
  * $\gamma$ (`risk_factor`): default `1`; `inventory_target_base_pct`: default `50`; $\eta$ (`order_amount_shape_factor`): default `0`; `min_spread`: default `0`; `order_levels`: default `2`; `order_optimization_enabled`: `True`.
  * $\sigma$: `InstantVolatilityIndicator` (`volatility_buffer_size = 200`); $\kappa$: `TradingIntensityIndicator` (`trading_intensity_buffer_size = 200`, modelo $\lambda(\delta) = A e^{-\kappa \delta}$); $(T-t)$ por `InfiniteModel` / `FromDateToDateModel` / `DailyBetweenTimesModel`. **[Gap: fórmula Cython exacta de skew por $\eta$ y `level_distances`.]**

### 10.2 Pure Market Making
* `bid_spread`, `ask_spread`, `order_refresh_time`, `order_refresh_tolerance_pct`, `filled_order_delay = 60`, `order_levels`, `order_level_spread`, `inventory_skew_enabled` (`inventory_range_multiplier = 50`), `hanging_orders_enabled` (`hanging_orders_cancel_pct`), `ping_pong_enabled`. **[Gap: ecuación interna exacta usando `inventory_range_multiplier`.]**

### 10.3 V2 Directional Controllers + Triple Barrier (`PositionExecutor`)
* **`BollingerV1`:** `BBP_{bb_length}_{bb_std}_{bb_std}` (ej. `100, 2.0`, umbrales `0.0` / `1.0`). Largo si `bbp < bb_long_threshold`; Corto si `bbp > bb_short_threshold`.
* **`MACDV1` (`MACD BB V1`):** Ej. `3m`, `BB(100, 2.0)` + `MACD(21, 42, 9)`. Largo: `(bbp < bb_long_threshold) & (macdh > 0) & (macd < 0)`; Corto inverso.
* **`SuperTrendV1`:** Defaults `length = 20`, `multiplier = 4.0`. Largo: `(SUPERTd == 1) & (|close - SUPERT|/close < percentage_threshold)`; Corto: `(SUPERTd == -1) & (percentage_distance < percentage_threshold)` **[Gap: valor numérico default exacto de `percentage_threshold`]**.
* **Triple Barrier (`TripleBarrierConfig`) + Control:** `cooldown_time` (ej. `300s`), `max_executors_per_side` (ej. `2`), `leverage` (ej. `20`), `stop_loss` (ej. `0.03`), `take_profit` (ej. `0.02`), `time_limit` (ej. `2700s`) y 4.ª barrera `trailing_stop` (`activation_price`, `trailing_delta`).

---

## 11. Mecánicas Matemáticas de Bots Comerciales (Pionex / Altrady / 3Commas / Cryptohopper)

### 11.1 QFL (Quickfingers Luc) Base Scanner / CBS
* Detecta **Base** (soporte histórico con rebote fuerte) y **Crack** (ruptura bajo base); mide **Median Drop** y **Success Rate** en ventana móvil (`1,000h`). Altrady CBS exige `Median Drop > 3%`.
* **Perfiles Altrady CBS:** `Original` (`1h`, cuerpos de vela); `Day Trading` (`1h Heikin Ashi`, bases activas `12h`, separación `>= 2%`, limpieza si crack `< 3%`); `Conservative` (`2h HA`, `24h`); `Position` (`4h HA`, `48h`). **[Gap: rebote mínimo inicial de base y % exactos hardcoded en 3Commas QFL.]**

### 11.2 Grid Aritmético, Geométrico, Infinity Grid & TWAP (Pionex)
* **Aritmético:** $\Delta P = \frac{P_{\text{upper}} - P_{\text{lower}}}{N}$, $P_i = P_{\text{lower}} + i \cdot \Delta P$, ganancia bruta por grilla $\approx \frac{\Delta P}{P_i}$.
* **Geométrico:** $r = \left(\frac{P_{\text{upper}}}{P_{\text{lower}}}\right)^{1/N}$, ganancia bruta constante $= r - 1$. Requiere $> 2 \times \text{Fee Rate}$ (`0.05%` spot c/u en Pionex).
* **Infinity Grid:** Sin techo superior, acotado solo por `Min. Price`; mantiene constante el valor en quote del activo base vendiendo fracciones en pasos $\text{Price}_n = \text{Price}_{n-1} \cdot (1 + G)$ (guía típica `G ~ 0.6%` vs `0.05%` fee) **[Gap: fórmula inicial exacta de partición base/quote]**.
* **TWAP:** Ejecuta porciones fijas en intervalos (`10s`, `30s`, `1m`, `5m`), modo `Limited` o `Perpetual`.

### 11.3 Martingala / DCA Escalado (3Commas, Pionex, Cryptohopper)
* **3Commas (Long):** Desviación acumulada $CD_k = D \sum_{j=0}^{k-1} SS^j$, precio disparo $TP_k = P_0 (1 - CD_k)$, tamaño $V_k = V_1 \cdot VS^{k-1}$, promedio ponderado $\text{AvgPrice} = \frac{\sum P_i Q_i}{\sum Q_i}$, TP objetivo $\text{AvgPrice} \times (1 + \text{TP\%}/100)$.
* **Cryptohopper DCA:** Dispara `Percentage Lower` ($X\%$) debajo del *precio promedio fusionado actual*; modos **Double Down** ($1\times$ valor abierto $\rightarrow 2\times$), **Triple Down** ($2\times \rightarrow 3\times$) o **Custom %**; `DCA Max Retries`, `DCA After X Time Open`, `DCA Buy Immediately` (o señal TA + Trailing Stop-Buy).

---

## 12. MQL5 CodeBase & cTrader Open cBots

1. **`Sample Breakout cBot` (cTrader C#):** Bollinger (`Periods=20, Deviations=2`), `bandHeight = (top - bottom) / PipSize <= BandHeightPips (40.0)` durante `ConsolidationPeriods = 2` barras; compra si `Last(1) > top` o vende si `< bottom`; `SL = 20`, `TP = 40` pips, `Quantity = 1` lote.
2. **`Original Turtle Rules Trader` (MQL5):** Donchian Sistema 1 (`20` entrada / `10` salida) y Sistema 2 (`55/20`); unidad de volatilidad $N$ (ATR Wilder), piramidado cada `0.5N` hasta `MaxTradesSingleDirection = 4`, stop unificado a `2N` **[Gap: defaults numéricos de `AcctSize`/`AcctPercent`]**.
3. **`Ilan 1.6` / `Dynamic HT` (MQL) & `Sample Martingale cBot` (cTrader):**
   * `Ilan 1.6`: Promedia cada `PipStep` (`~30` pips o rango dinámico) multiplicando lotes por `LotExponent` (`1.4–1.6`) hasta `MaxTrades`; cierra toda la canasta al TP promedio + `UseEquityStop`/`UseTimeOut`.
   * `Sample Martingale cBot`: `InitialQuantity = 1`, `SL = 40`, `TP = 40`; duplica volumen si `NetProfit <= 0` y resetea a `1` tras ganancia.
4. **`London Breakout` (`N22` / `Gold` / `Simple` MQL5):** Caja asiática (`00:00–07:00` o `03:00–08:00`, M15); órdenes OCO `BuyStop`/`SellStop` (`InpUseOCO = true`) fuera de caja + buffer, filtros `MaxSpread`, `Min/MaxRangeATRFrac`, `MaxDailyLossPct`, `InpRiskPercent = 1.0`, SL en borde opuesto/ATR, TP por RR (ej. `1.5R–2.5R`) + `UseBreakEven` y cierre fin de sesión.
5. **`Sample RSI cBot` (cTrader) & `Bollinger Bands Mean Reversion EA` (MQL5):**
   * `Sample RSI cBot`: `Periods = 14`, compra `< 30`, vende `> 70`, `Quantity = 1`.
   * `BB Mean Reversion EA`: `BB(20, 2.0, PRICE_CLOSE)` + `RSI(14, 30/70)` (compra en banda inferior + RSI `< 30`; inverso venta), salida en SMA 20 / RSI ~50 o `InpStopLoss = 300`, `InpTakeProfit = 500` pts, `InpLot = 0.1`.

---

## 13. Módulos Traducidos y Listos para Correr en EdgeLab (`edgelab/research/estrategias/`)

Todas las lógicas extraídas fueron traducidas al contrato del analizador (`edgelab/research/analizador.py`: `NOMBRE`, `FAMILIA`, `INSTRUMENTO`, `PARAMETROS`, `senales`), apoyadas sobre el núcleo estrictamente causal [`_indicadores_ext.py`](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab/edgelab/research/estrategias/_indicadores_ext.py) y el registro por lotes [`catalogo_externo.py`](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab/edgelab/research/estrategias/catalogo_externo.py).

**Verificación (`pytest`):** `66 passed in 130.08s` en [`test_estrategias_catalogo_externo.py`](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab/tests/research/test_estrategias_catalogo_externo.py) y [`test_analizador.py`](file:///C:/Users/nicoc/.gemini/antigravity/scratch/EdgeLab/tests/research/test_analizador.py) (causalidad estricta sin *look-ahead*, registro de variantes, generación de operaciones y deducción única de fricción canónica).

| # | Módulo Python | `NOMBRE` | `FAMILIA` | Inst. | Grilla `PARAMETROS` |
| :-: | :--- | :--- | :--- | :---: | :--- |
| 1 | `supertrend_atr.py` | `EXT-SUPERTREND-ATR` | `EXT_TV_SUPERTREND` | `NQ` | `periodo=[10, 20], mult=[2.5, 3.5]` |
| 2 | `gaussian_supertrend_3r.py` | `EXT-GAUSSIAN-TREND-3R` | `EXT_TV_GAUSSIAN` | `NQ` | `sampling=[14, 21], mult_banda=[1.414, 2.0]` |
| 3 | `pmax_explorer.py` | `EXT-PMAX-EXPLORER` | `EXT_TV_PMAX` | `NQ` | `ma_len=[10, 14], mult_atr=[2.5, 3.0]` |
| 4 | `alphatrend_mfi.py` | `EXT-ALPHATREND-MFI` | `EXT_TV_ALPHATREND` | `NQ` | `ap=[10, 14], coeff=[1.0, 1.5]` |
| 5 | `ut_bot_chandelier.py` | `EXT-UTBOT-CHANDELIER` | `EXT_TV_UTBOT` | `NQ` | `modo=["utbot", "chandelier"], mult=[1.5, 2.5]` |
| 6 | `ssl_hybrid_nnfx.py` | `EXT-SSL-HYBRID` | `EXT_TV_SSL` | `NQ` | `len_base=[40, 60], len_ssl=[5, 10]` |
| 7 | `donchian_turtle_breakout.py` | `EXT-DONCHIAN-TURTLE` | `EXT_TURTLE_DONCHIAN` | `ES` | `n_entry=[20, 40], mult_tp=[2.0, 3.0]` |
| 8 | `macd_adx_trend.py` | `EXT-MACD-ADX-TREND` | `EXT_MACD_ADX` | `NQ` | `adx_min=[20, 25], mult_tp=[2.0, 3.0]` |
| 9 | `orb_rvol_intradia.py` | `EXT-ORB-RVOL` | `EXT_ORB_INTRADIA` | `NQ` | `n_velas=[15, 30], rr=[1.5, 2.0]` |
| 10 | `dual_thrust_chalek.py` | `EXT-DUAL-THRUST` | `EXT_QC_DUAL_THRUST` | `ES` | `k=[0.35, 0.50], mult_tp=[1.0, 1.5]` |
| 11 | `dynamic_breakout_ii.py` | `EXT-DYNAMIC-BREAKOUT-II` | `EXT_QC_DYN_BREAKOUT` | `ES` | `base_len=[20, 30], bb_mult=[1.2, 1.8]` |
| 12 | `squeeze_bollinger_keltner.py` | `EXT-SQUEEZE-MOMENTUM` | `EXT_TV_SQUEEZE` | `NQ` | `kc_mult=[1.3, 1.6], mult_tp=[2.0, 3.0]` |
| 13 | `london_asian_box_breakout.py` | `EXT-LONDON-ASIAN-BREAKOUT` | `EXT_MQL5_LONDON_BOX` | `GC` | `box_bars=[30, 60], rr=[1.5, 2.0]` |
| 14 | `intraday_first_last_momentum.py` | `EXT-INTRADAY-MOM-GAO` | `EXT_QC_GAO_INTRADAY` | `ES` | `n_open=[30, 45], umbral_atr=[0.5, 1.0]` |
| 15 | `connors_rsi2_atr_mr.py` | `EXT-CONNORS-RSI2-ATR-MR` | `EXT_TV_CONNORS_ATR` | `ES` | `rsi_os=[10, 15], atr_mult=[1.0, 1.5]` |
| 16 | `bollinger_rsi_double.py` | `EXT-BOLLINGER-RSI-DOUBLE` | `EXT_TV_BB_RSI` | `NQ` | `len_bb=[20, 50], len_rsi=[6, 14]` |
| 17 | `wavetrend_lazybear.py` | `EXT-WAVETREND-LB` | `EXT_TV_WAVETREND` | `NQ` | `n1=[10, 14], nivel_ob=[45, 53]` |
| 18 | `vwap_stdev_rebound.py` | `EXT-VWAP-STDEV-REBOUND` | `EXT_COINRULE_VWAP` | `NQ` | `k_sigma=[1.5, 2.0], rsi_lim=[35, 45]` |
| 19 | `coinrule_ifttt_ride_surge.py` | `EXT-COINRULE-IFTTT` | `EXT_COINRULE_IFTTT` | `NQ` | `modo=["ride_trend", "vol_surge"], mult_tp=[1.5, 2.5]` |
| 20 | `freqtrade_binh_cluc_scalp.py` | `EXT-FREQTRADE-BINH-CLUC` | `EXT_FREQTRADE_SCALP` | `NQ` | `variante=["binh_cluc", "sample_tema"], mult_tp=[1.5, 2.0]` |
| 21 | `qfl_base_crack_scanner.py` | `EXT-QFL-BASE-CRACK` | `EXT_ALTRADY_QFL` | `NQ` | `win_base=[20, 35], crack_atr=[0.8, 1.2]` |
| 22 | `smc_fvg_ob_retest.py` | `EXT-SMC-FVG-OB` | `EXT_TV_LUX_SMC` | `NQ` | `disp_atr=[0.8, 1.2], max_edad=[15, 30]` |
| 23 | `kalman_zscore_statarb.py` | `EXT-KALMAN-ZSCORE` | `EXT_QC_KALMAN` | `ES` | `z_entry=[1.8, 2.2], mult_tp=[1.5, 2.0]` |
| 24 | `fisher_aroon_psar_qc.py` | `EXT-QC-FISHER-AROON-PSAR` | `EXT_QC_LAB_TEMPLATES` | `NQ` | `modelo=["fisher", "aroon", "psar"], mult_tp=[1.5, 2.5]` |
| 25 | `composer_symphony_rotator.py` | `EXT-COMPOSER-SYMPHONY` | `EXT_COMPOSER_SYMPHONY` | `NQ` | `rsi_ob=[75, 80], rsi_os=[25, 30]` |
| 26 | `grid_dca_martingale_envelope.py` | `EXT-GRID-DCA-ENVELOPE` | `EXT_PIONEX_GAINIUM_GRID` | `NQ` | `step_scale=[1.1, 1.3], n_steps=[3, 5]` |
| 27 | `avellaneda_stoikov_skew.py` | `EXT-AVELLANEDA-STOIKOV` | `EXT_HUMMINGBOT_AS` | `ES` | `gamma=[0.5, 1.5], kappa=[1.5, 3.0]` |
| 28 | `optionalpha_expected_move_wall.py` | `EXT-OA-EXPECTED-MOVE-WALL` | `EXT_OPTIONALPHA_0DTE` | `ES` | `modo=["fade_em", "challenged_switch"], mult_em=[0.8, 1.1]` |

### Comandos para Correr en `EdgeLab`

```powershell
# Correr una estrategia puntual en local (requiere carpeta de datos de ticks)
python tools/analizar.py edgelab.research.estrategias.orb_rvol_intradia 20240102 20260331 --entrada /ruta/datos

# Correr una estrategia en Kaggle tick a tick o sobre barras M1
python tools/analizar.py edgelab.research.estrategias.dual_thrust_chalek 20240102 20260331 --kaggle --cuenta auto
python tools/analizar.py edgelab.research.estrategias.avellaneda_stoikov_skew 20240102 20260331 --kaggle --resolucion m1
```

