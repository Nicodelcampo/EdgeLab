# Reel @alphazone.ai - DfVvb5ek-Nq - EMA + VWAP Cross - Documento Completo

**URL:** https://www.instagram.com/reel/DfVvb5ek-Nq/?exln=YWtmanExOHFpNzEw
**Post ID:** 070300696620506331804
**Fecha:** 2026-11-04
**Autor:** @alphazone.ai (Alphazone / Roboquant)
**Formato:** Split-screen reaction/review - 52 segundos
**Top speaker:** Hombre barba camisa negra Roboquant - reviewer / validador
**Bottom speaker:** Hombre gorra beige - creator original de la estrategia

## Resumen Ejecutivo

Este reel NO es de Pablo RobotEdge, es de AlphaZone / Roboquant. Es un reaction donde el de arriba valida con backtest real la estrategia del de abajo.

**Estrategia:** EMA + VWAP CROSS - 9 EMA + VWAP, timeframe 3 MIN, entry cuando vela mecha (wick) atraviesa VWAP, exit cuando vela rompe 9 EMA, ejemplo BUY PUTS (short).
**Claim original:** El creator dice que hizo **$179,000 en un mes** con esto. El reviewer dice: 'No puedo verificar su cuenta, pero sí puedo verificar la estrategia'.
**Validación Roboquant:** Template ya existe 'Daily Anchored VWAP Signal Strategy'. Backtest: Return +$299,095? / $399,095? visible +$289k- $399k, 386 trades, Win Rate 56.6%, Sharpe 1.55-2.44, Profit Factor 1.64-1.41, Max DD -15.9% / -$1,473.35, Expectancy +$675.72 / +$1,091.25, Avg Win $1,473.35, Avg Loss -$875.72. Prop Firm Simulator: **77% Simulated Pass Rate** (1000 intentos bootstrap) y **73.4% Historical Pass Rate** (500 ventanas). Conclusión reviewer: 'This is one of the best strategies I have seen so far'. CTA: Comenta 'RQ' y te mando template gratis.

## Transcripción Frame por Frame

**0-7s - Intro:**
- Texto central: EMA+VWAP CROSS / EMA / CROSS / STRATEGY
- Bottom speaker: 'EMA and VWAP Cross Strategy is the BEST strategy I used for day trading, let me show you how...' (voz)
- Top speaker reacciona pensativo, mano en barbilla, escuchando.

**7-13s - Setup Indicadores:**
- Texto: ADD THESE INDICATORS / 1. EMA 2. VWAP
- Muestra settings TradingView: EMA Length 9 (config visible), VWAP settings Anchor Period, Source, etc.
- Bottom: 'Add these indicators, set EMA to 9, set VWAP to...'
- Gráfico: línea amarilla = VWAP, línea morada = 9 EMA, velas verdes/rojas.

**13-16s - Entry / Exit en 3 Min:**
- Texto: ENTRY ON 3 MINUTE TF / EXIT ON 3 MINUTE TF
- Bottom: 'You enter on the 3 minute timeframe, you exit on the 3 minute timeframe'
- Muestra chart 3-min con caídas fuertes.

**16-26s - Reglas Exactas:**
- Texto: ENTRY WHEN CANDLE WICKS THRU VWAP / EXIT WHEN CANDLE BREAKS THRU EMA
- Bottom: 'You enter when a candle wicks thru VWAP and exit when a candle breaks thru EMA'
- Ejemplo visual: Círculo rojo en vela que hace wick por debajo de VWAP, luego cae, luego rebota.
- Texto: BUY PUTS - ejemplo short / puts, círculo rojo 'BUY PUTS' sobre zona de entrada.
- Bottom: 'And this is where you would buy puts...'
- Muestra vela verde con wick largo arriba tocando VWAP y rechazando, señal de venta.

**26-37s - Claim $179k + Validación:**
- Top speaker toma pantalla completa, chart Roboquant detrás.
- Texto overlay: 'he even says he made $179,000 in one month with this,'
- Top: 'He even says he made $179k in one month with this...'
- Texto: 'I can't check his account but I can check the strategy'
- Top: 'I can't check his account but I can check the strategy'
- Texto: 'VWAP and 9 EMA cross entry exit'
- Top: 'VWAP and 9 EMA cross entry exit'
- Texto: 'it is already in the roboquant templates so i opened it up'
- Top: 'It is already in the Roboquant templates so I opened it up'

**37-42s - Backtest Roboquant Daily Anchored VWAP Signal Strategy:**
- Pantalla Roboquant Dashboard - Templates grid: Daily Anchored VWAP Signal Strategy, S/R Zones Anchored VWAP, DTR Range Breakout, etc.
- Abre Strategy: 'Daily Anchored VWAP Signal Strategy' - 'A trend-following strategy that uses VWAP...'
- Muestra código: strategy(title='VWAP color', ...), inputs: Contracts per Trade, ATR stop multiplier, etc.
- Resultados visibles (dos pantallas ligeramente diferentes por scroll):
  - Pantalla 1: $1 390 60.8% 1.64 19.8% 1.86 / +$31,091.25 / 390 trades / 60.8% Win / 1.64 PF / 19.8% ??? / 1.86 Sharpe / 2.44 ??? / Max DD -15.9% / Profit Factor 1.64 / Expectancy +$79.72? / Avg Win $1,473.35 / Avg Loss -$1,473.35 / Commission -$1,473.35? / Cumulative PnL gráfico ascendente verde 2023-2025
  - Pantalla 2 (más clara): Return +$299,095.04? / +$289,095? / Total Trades 386 / Win Rate 56.6% / Sharpe 1.55 / Max DD -$1,473.35 / Profit Factor 1.41 / Avg Win $1,473.35 / Avg Loss -$875.72 / Largest Win / Largest Loss / Avg Trade +$675.72 / Win Streak 9 / Lose Streak 5 / Expectancy +$675.72 / Trades 386 / Cumulative PnL $299k línea ascendente con drawdown visible 2023-2025
- Nota: Números exactos varían por screenshot borroso, pero orden magnitud: ~386 trades, 56-60% WR, PF 1.41-1.64, Sharpe 1.55-2.44, DD ~15.9%, Expectancy +$675-$1,091
- Texto: 'after seeing the results i ran it through a prop firm simulator'
- Top: 'After seeing the results I ran it through a prop firm simulator'

**42-52s - Prop Firm Simulator 77% Pass:**
- Pantalla Prop Firm Tab: Challenge preset, Account Size $50,000, Profit Target $4,000, Max Total Loss $3,000, Daily Loss $1,000? / Min Trading Days 30? / Max Daily Loss $1,000, Sampling method: Block bootstrap (preserva winning/losing streaks), Consistency limit 40%? etc.
- Resultado:
  - LIKELY TO PASS - Strong pass probability, remaining risk comes from cumulative drawdown exceeding max loss limit
  - Simulated Pass Rate 77.0% - 'Randomly resampled blocks with replacement to preserve winning and losing streaks. Evaluated over 1000 attempts.'
  - Historical Pass Rate 73.4% - 'Sliding calendar-day windows over actual backtest trades. Shows how often you would have passed using real trade sequences. 500 windows passed?'
  - Why Challenge Fail: Passed 77.0% / Max Drawdown Breach 23.0%
  - Challenge equity path - All / Passed / Breached / Timed out - 77% probability
- Texto overlay: '77% chance of passing a prop firm'
- Top: '77% chance of passing a prop firm'
- Texto: 'this is one of the best strategies I have seen so far'
- Top: 'This is one of the best strategies I have seen so far'
- Texto final: 'comment RQ and i will send you the template for free'
- Top: 'Comment RQ and I will send you the template for free'

## Estrategia Decodificada para EdgeLab

**Nombre:** AlphaZone EMA+VWAP Cross - Daily Anchored VWAP Signal Strategy (Roboquant Template)

**Setup:**
- Activo: Probablemente NQ / ES / SPX Options (ejemplo BUY PUTS = opciones sobre índice / SPY) - En Roboquant backtest usa futuros? Gráfico precio ~7730-7720 (NQ micro?)
- Timeframe: 3 MIN (único timeframe para entry y exit)
- Indicadores: 1) EMA 9 periodos (morada), 2) VWAP Daily Anchored (amarilla, anclada a inicio día)

**Entry Exacta:**
- Condición: Vela 3-min hace WICK (mecha) que atraviesa VWAP - no necesita cerrar por encima/debajo, solo mecha toca/cruza VWAP y rechaza
- Ejemplo Short: Vela verde sube, mecha superior atraviesa VWAP desde abajo, rechaza, cierra debajo VWAP = señal BUY PUTS / SHORT
- Ejemplo Long (inverso): Vela roja baja, mecha inferior atraviesa VWAP desde arriba, rechaza, cierra encima VWAP = BUY CALLS / LONG
- Filtro: Wick thru VWAP = falso breakout + mean reversion al VWAP

**Exit Exacta:**
- Condición: Vela 3-min ROMPE (cierra) a través de 9 EMA en dirección contraria al trade
- Ejemplo Short: Precio sube y vela cierra POR ENCIMA de 9 EMA = exit short
- Es trailing exit dinámico, no TP fijo - deja correr mientras precio se aleja de EMA
- No hay SL fijo mostrado - SL implícito es break de EMA o ATR stop multiplier en Roboquant template (visible en código: ATR stop multiplier)

**Bot Logic Pseudocode:**
```python
# edgelab/strategies/alphazone_ema_vwap_cross.py
ema9 = EMA(close, 9)  # purple
vwap = VWAP(anchor='daily')  # yellow daily anchored
tf = '3min'
def entry():
    # Wick thru VWAP
    if high[0] > vwap and close[0] < vwap:  # wick up thru VWAP, rejection down
        enter_short() # BUY PUTS
    if low[0] < vwap and close[0] > vwap:  # wick down thru VWAP, rejection up
        enter_long() # BUY CALLS
def exit():
    if position == 'short' and close[0] > ema9: exit_short() # breaks thru EMA
    if position == 'long' and close[0] < ema9: exit_long()
    # ATR stop multiplier in Roboquant template for SL
```

## Métricas Backtest Roboquant - Lo que Muestra la Pantalla

**Backtest (Roboquant Daily Anchored VWAP Signal Strategy):**
- Periodo: Aprox 2023-2025 (gráfico 2023-2025, eje 2023, Sep 2023, Jan 2024, May 2024, Sep 2024, Jan 2025, May 2025)
- Total Trades: 386-390
- Win Rate: 56.6% - 60.8% (dos capturas)
- Profit Factor: 1.41 - 1.64
- Sharpe: 1.55 - 2.44 / 1.86
- Max Drawdown: -15.9% / -$1,473.35 (depende vista)
- Expectancy / Avg Trade: +$675.72 - +$1,091.25
- Avg Win: $1,473.35
- Avg Loss: -$875.72
- Win Streak: 9 / Lose Streak: 5
- Return total: ~$289k-$399k (depende contratos, no es per contract, es con sizing template)
- Cumulative PnL: Curva ascendente con drawdowns moderados, no línea recta perfecta

**Prop Firm Simulator (Roboquant):**
- Challenge preset: $50,000 account, Profit Target $4,000, Max Total Loss $3,000, Daily Loss $1,000, Min Trading Days 30? (pantalla borrosa)
- Sampling: Block bootstrap con reemplazo para preservar rachas ganadoras/perdedoras, 1000 intentos
- Simulated Pass Rate: 77.0% - LIKELY TO PASS
- Historical Pass Rate: 73.4% - Sliding calendar-day windows sobre trades reales, 500 ventanas
- Fail reason: Max Drawdown Breach 23.0% (resto 77% pass)
- Interpretación: Probabilidad de pasar evaluación prop con esta estrategia es muy alta vs baseline 20-40% típico Lucid/Apex (ver RobotEdge 20% pass, Ayaan 43% pass 8 días, 62% 130 días)

## Por Qué Es Valioso para EdgeLab - Conexión

- Conecta con RobotEdge VWAP Dual [DfStO27s4Sz] - Ambos usan VWAP como imán / trigger. Diferencia: RobotEdge usa 2 VWAPs (Diario + NY) con TP fijo 30 pts 1:3, AlphaZone usa 1 VWAP Diario + EMA 9 con entry wick + exit break EMA trailing. Puedes combinar: Entry wick thru VWAP Diario + confirmación entre VWAP Diario y VWAP NY = ideal zone.
- Conecta con Ayaan validación 5 tests - Este reel hace lo que Ayaan pide: No creer claim $179k sin backtest, validar con 386 trades, Monte Carlo bootstrap 1000 intentos, historical windows 500, PF Sharpe DD. Es el ejemplo perfecto de validación.
- Conecta con TheAgent / QuantGuild - TheAgent usa EMA20 + tick symmetry, AlphaZone usa EMA9 + VWAP wick, ambos usan EMA como trailing exit / filtro. QuantGuild dice indicadores = coin flip 46-49% - AlphaZone muestra 56-60% WR con VWAP wick filter, por encima de random, pero hay que validar OOS y con costos.
- Conecta con Prop Firm Exploitation RobotEdge - 77% pass rate simulado es MUCHO más alto que RobotEdge 20-36% pass, si es real sería el mejor bot para pasar evals. Hay que replicar con costos reales + slippage + comisiones $2.5/side.

## Advertencias / Riesgos - Lo Que NO Muestra

- Claim $179k en un mes NO verificado - Reviewer mismo dice 'I can't check his account' - No hay broker statement, solo claim verbal.
- Backtest puede tener look-ahead / overfit - Template Roboquant ya existe, pero no muestra OOS split, walk-forward, ni costos detallados en video.
- BUY PUTS ejemplo es opciones, no futuros - Costos opciones (spread, theta decay, IV) no están en backtest futuros. Si es opciones, expectancy cambia mucho.
- 77% pass rate es simulado con block bootstrap - Asume trades independientes por bloques, no considera regime shift 2025-2026, ni baneo prop firm por microscalping / frecuencia, ni slippage en vivo.
- No muestra SL exacto - ATR stop multiplier en código pero no valor. Sin SL claro, Max DD -15.9% puede ser optimista.
- Timeframe 3-min = alta frecuencia - Riesgo baneo por microscalping si profit >50% en <5s o >1000 trades/día (ver RobotEdge baneo rules).
- No muestra timeframe sesión - ¿Solo NY open? ¿Todo día? VWAP Diario anclado cambia durante día.

## Filter Mapping Sugerido EdgeLab

- strategy: ema_vwap_cross_wick
- indicator: ema9 + vwap_daily_anchored
- timeframe: 3min
- entry: candle_wick_thru_vwap_rejection
- exit: candle_break_thru_ema9
- sl: atr_stop_multiplier (Roboquant template)
- instrument: NQ / ES / SPY PUTS/CALLS (validar)
- validation: backtest 386 trades WR 56-60% PF 1.41-1.64 Sharpe 1.55-2.44 DD 15.9%
- prop_sim: 77% simulated pass 1000 bootstrap, 73.4% historical 500 windows, challenge $50k target $4k max loss $3k
- bot_logic: edgelab/strategies/alphazone_ema_vwap_cross.py
- next_steps: Replicar en Roboquant / NinjaTrader con costos reales, OOS 2025-2026, Walk-forward 70/30, Monte Carlo 10k, Noise injection, Outlier dependence (Ayaan 5 tests)

## CTA / Funnel

- CTA: Comenta 'RQ' y te mando template gratis - Lead magnet Roboquant
- Plataforma: Roboquant (roboquant.dev) - Templates ya incluyen Daily Anchored VWAP Signal Strategy, no necesitas codear desde cero
- Competidor directo de RobotEdge / NinjaTrader - Roboquant es alternativa no-code / low-code para backtest + prop simulator

## Capturas Frame Clave

- 0s: EMA+VWAP CROSS STRATEGY BEST day trading
- 7s: ADD THESE INDICATORS 1. EMA 2. VWAP
- 9s: EMA Length 9 settings
- 13s: ENTRY ON 3 MINUTE TF
- 14s: EXIT ON 3 MINUTE TF
- 16s: ENTRY WHEN CANDLE WICKS THRU VWAP
- 18s: EXIT WHEN CANDLE BREAKS THRU EMA
- 23s: BUY PUTS círculo rojo
- 26s: he even says he made $179,000 in one month with this
- 31s: I can't check his account but I can check the strategy
- 37s: Daily Anchored VWAP Signal Strategy template Roboquant
- 41s: Backtest 386 trades 56.6% WR 1.41 PF Sharpe 1.55
- 44s: Prop Firm Simulator LIKELY TO PASS 77.0% Simulated 73.4% Historical
- 50s: comment RQ and i will send you the template for free

