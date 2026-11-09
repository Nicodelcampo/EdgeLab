# Reel @davidtrades_model - DffkN31PrN7 - Bias Tracker + Market Intraday Momentum - Documento Completo con Respaldo Académico

Estado: REFERENCIA (material externo juntado por Nico; no es evidencia, ver ../INDICE.md).

**URL:** https://www.instagram.com/reel/DffkN31PrN7/?rpxt=MXRreHAwYzRja2YyOQ==
**Post ID:** 532053983152457387692
**Fecha:** 2026-11-08 (hoy, recién subido)
**Autor:** @davidtrades_model - David Trades - Hombre joven, círculo overlay abajo derecha, pantalla PC detrás
**Formato:** 70 seg - Habla a cámara + paper PDF + chart NinjaTrader / TradingView con Bias Tracker
**CTA:** Comenta 'GATES' to see the system I use

## Resumen Ejecutivo

Este es el reel más académico de todos los que me pasaste. No es un indicador mágico, es **una tesis de paper peer-reviewed** convertida en indicador.

**Tesis reel:** Existe mucha investigación sobre intraday momentum pero nadie la usa porque todos leen velas subjetivamente: '¿Estamos bullish o bearish?' Él usa un **Bias Tracker** que combina varios factores en un % objetivo.
**Paper citado:** 'Market Intraday Momentum' - Lei Gao (Iowa State), Yufeng Han (UNC Charlotte), Sophia Zhengzi Li (Rutgers), Guofu Zhou (Washington University St. Louis) - First Draft March 2014, Current Version June 2017, publicado Journal of Financial Economics 129 (2018) 394-414.
**Hallazgo paper:** El retorno de la primera media hora (9:30-10:00, medido desde cierre ayer) predice el retorno de la última media hora (15:30-16:00). Más fuerte en días volátiles, alto volumen, recesión, y días macro news.
**Bias Tracker mostrado:** BIAS: 50.00 STATE: Bullish - Parámetros: Initial Move Long, VWAP Long, Daily Candle Long, Session HL Neutral, Value Area Shift Long, ORB Long, Gap Short. Muestra niveles en verde y rojo que usa como referencia para sus niveles.
**PERO - Alerta respaldo:** Replicaciones 2025-2026 dicen que el efecto NO existe en US 2015-2026, que era el gap overnight, y que la estrategia de timing pierde -1 a -3 bp/día neto. Y el paper OOS de Zarattini 2025-2026 también se deteriora. Hay que leer esto con los dos lados.

## Transcripción Completa Frame por Frame

**0-3s - Hook Paper:**
- Mano señala PDF: 'Market Intraday Momentum' - Lei Gao, Yufeng Han, Sophia Zhengzi Li, Guofu Zhou - First Draft March 2014, Current Version June 2017.
- Texto: 'this is one of the best trading strategies in the world and NOBODY USES THIS STRATEGY'
- David: 'This is one of the best trading strategies in the world and nobody uses it'

**3-12s - Research Existe:**
- Texto: 'there is a lot of research on intraday momentum'
- David: 'There is a lot of research on intraday momentum'
- Texto: 'the way the market moves on its biggest days'
- David: 'The way the market moves on its biggest days'
- Texto: 'so why does this actually work? because it gives you a statistical...'
- David: 'So why does this actually work? Because it gives you a statistical...'

**12-27s - Problema Subjetivo:**
- Chart NQ velas blancas subiendo fuerte, líneas horizontales.
- Texto: '...problems when we look at a chart say... just say are we bullish or bearish?'
- David: 'Problems when we look at a chart, say... just say are we bullish or bearish?'
- Texto: 'and we decide that only by looking at the candles but the truth is that is not objective'
- David: 'And we decide that only by looking at the candles but the truth is that is not objective'
- Interpretación: Critica lectura subjetiva de velas, busca objetividad numérica.

**27-35s - Solución Bias Tracker:**
- Chart cambia, aparece panel Bias Tracker arriba derecha.
- Texto: 'personally i use the ... indicator'
- David: 'Personally I use the ... indicator'
- Texto: 'it's called a bias tracker and it measures the pressure behind the bias'
- David: "It's called a bias tracker and it measures the pressure behind the bias"
- Texto: 'it gives the trend a percentage'
- David: 'It gives the trend a percentage'

**35-50s - Ejemplo 50% Bullish:**
- Panel visible: BIAS: 50.00 STATE: Bullish
- Parámetros listados (captura nítida):
  * Initial Move: Long (verde)
  * VWAP: Long (verde)
  * Daily Candle: Long (verde)
  * Session HL: Neutral (gris)
  * Value Area Shift: Long (verde)
  * ORB: Long (verde)
  * Gap: Short (rojo)
- Texto: 'for example right now we're at 50 percent and it combines several parameters into one bias reading'
- David: 'For example right now we're at 50 percent and it combines several parameters into one bias reading'
- Texto: 'in this case it's 50 percent bullish and it shows me each parameter as a ...'
- David: 'In this case it's 50 percent bullish and it shows me each parameter as a...'

**50-70s - Objetivo + Niveles:**
- Texto: 'this is an objective way to read the market and you don't just look at candles to define today's trend'
- David: 'This is an objective way to read the market and you don't just look at candles to define today's trend'
- Texto: 'you also see how strong it is and as you can see there's also levels in green and in red and i use them as reference levels for my ...'
- David: 'You also see how strong it is and as you can see there's also levels in green and in red and I use them as reference levels for my...'
- Visual: Abajo chart Bias Tracker línea azul oscilando entre niveles verdes (resistencia) y rojos (soporte), con líneas horizontales verdes/rojas.
- Texto final: 'so comment gates to get the system' / COMMENT GATES / TO SEE THE SYSTEM I USE
- David: 'So comment GATES to see the system I use'

## Bias Tracker Decodificado para EdgeLab

**Nombre:** DavidTrades Bias Tracker - Multi-Factor Intraday Bias %

**Componentes visibles (7 factores):**
1. **Initial Move:** Dirección primer movimiento (9:30-10:00?) - Long en ejemplo = primer move alcista. Esto es exactamente el predictor de Gao et al. (first half-hour return).
2. **VWAP:** Precio vs VWAP - Long = precio encima VWAP. Conecta con RobotEdge VWAP Dual y AlphaZone VWAP.
3. **Daily Candle:** Vela diaria - Long = vela diaria verde / encima open.
4. **Session HL:** High/Low sesión - Neutral = precio entre high y low sesión, sin breakout.
5. **Value Area Shift:** Desplazamiento Value Area (Volume Profile) - Long = VA se desplaza arriba.
6. **ORB:** Opening Range Breakout - Long = rompió ORB arriba. Conecta con FlexingJoe ORB 9:30-10:00 y TheAgent ORB.
7. **Gap:** Gap overnight - Short = gap up pero precio debajo? O gap negativo? En ejemplo Gap Short mientras otros 5 Long + 1 Neutral = 5 Long vs 1 Short + 1 Neutral => Bias 50% Bullish (no 85% porque pesos no iguales o Gap pesa más).

**Cálculo Bias %:**
No muestra fórmula exacta. Hipótesis: Bias = (suma pesos Long - suma pesos Short) / total * 100? En ejemplo 5 Long, 1 Short, 1 Neutral => si pesos iguales, Bias = (5-1)/7 = 57% Bullish, cercano a 50% mostrado. Si Gap pesa doble, (5-2)/7 = 42%. Si Initial Move pesa más, etc. Necesita reverse-engineer con CTA GATES.
**STATE:** Bullish si Bias >0, Bearish si Bias <0, Neutral si Bias ~0. En ejemplo 50% Bullish = moderadamente bullish, no extremo.
**Niveles Verde/Rojo:** Bias Tracker abajo muestra niveles en verde (resistencia / bias bullish) y rojo (soporte / bias bearish) que usa como referencia para sus niveles de entrada / TP / SL. No son niveles precio, son niveles bias? O son niveles precio derivados de bias? Video no aclara.

**Bot Logic Pseudocode:**
```python
# edgelab/strategies/david_bias_tracker.py
factors = {
    'initial_move': sign(return_0930_1000), # Gao predictor
    'vwap': 1 if price > vwap else -1,
    'daily_candle': 1 if close_daily > open_daily else -1,
    'session_hl': 1 if price > session_high else -1 if price < session_low else 0,
    'value_area_shift': 1 if va_shift > 0 else -1,
    'orb': 1 if price > orb_high else -1 if price < orb_low else 0,
    'gap': 1 if gap > 0 else -1, # Short en ejemplo = gap up pero factor Short?
}
bias_pct = sum(weights[f] * factors[f] for f in factors) / sum(weights) * 100
state = 'Bullish' if bias_pct > 0 else 'Bearish' if bias_pct < 0 else 'Neutral'
if bias_pct > 50: enter_long() # Fuerte bullish
if bias_pct < -50: enter_short()
```

## Documentos de Respaldo - Internet - 5 Fuentes Clave

### 1. PAPER ORIGINAL - Gao, Han, Li, Zhou (2018) - Journal of Financial Economics 129, 394-414
- **SSRN:** https://ssrn.com/abstract=2440866 - 48 páginas, Posted 24 May 2014, Last Revised 20 Jun 2017, Downloads 16,554
- **Autores:** Lei Gao (Iowa State / George Mason), Yufeng Han (UNC Charlotte), Sophia Zhengzi Li (Rutgers), Guofu Zhou (Washington University St. Louis - Olin)
- **Datos:** High frequency S&P 500 ETF (SPY) 1993-2013 (en abstract, en algunas versiones 1999-2012)
- **Hallazgo core:** First half-hour return (desde cierre ayer hasta 10:00 NY) predice last half-hour return (15:30-16:00). Predictability statistically and economically significant.
- **Condiciones más fuerte:** En días más volátiles, mayor volumen, días recesión, y días macro news release.
- **También presente:** Para 10 otros ETFs más activamente traded domestic e international.
- **Mecanismo teórico:** Consistente con Bogousslavsky (2016) modelo infrequent rebalancing + modelo trading on late-informed news near market close.
- **Estrategia paper:** En algunas réplicas, timing Sharpe ~1.08 vs 0.29 buy-and-hold, IS Sharpe 1.84 full sample, 0.93 post-2004 post-decimalization. Pero paper original reporta NO costos.
- **Cita exacta abstract:** 'Based on high frequency data of the S&P 500 ETF from 1993-2013, we document an intraday momentum pattern: the first half-hour return on the market since the previous day's market close predicts the last half-hour return.'

### 2. REPLICACIÓN CRÍTICA - Krueger Algorithms (2026-09-17) - 'Market Intraday Momentum, Replicated on Five Indices: The Effect Is the Overnight Gap'
- **URL:** https://kruegeralgorithms.com/en/research/intraday-momentum-paper-replication - 7 páginas PDF full study
- **Datos:** NQ, SPX, Dow, DAX, FTSE - M1 CFD cash session, 05 Jan 2015 - 05 Jun 2026, 2,832-2,916 sesiones por mercado. Regresión como paper: last 30 min on first 30 min desde previous cash close, OLS. Variantes: mismo predictor sin gap (open to open+30), rest-of-day instead of last 30. In-sample 2015-2020, OOS 2021-2026. Timing strategy net spread+slippage 1.4-2.4 bp.
- **Resultado paper spec (con gap):** SPY 1993-2013 slope 6.94, R2 1.6%, significant 1%. En 2015-2026: NQ slope -0.003 t -0.4 R2 0.01% sign 50.4%, SPX -0.013 t -1.7 R2 0.11% sign 49.0%, Dow -0.008 t -1.1 R2 0.04% sign 47.8%, DAX +0.021 t +4.2 R2 0.60% sign 52.6%, FTSE +0.032 t +6.1 R2 1.28% sign 49.7%.
- **Hallazgo clave:** Sin gap, slope va a cero en TODOS: NQ +0.005 t 0.4, SPX -0.010 t -0.6, Dow -0.013 t -0.8, DAX +0.002 t 0.1 (de 4.2 a 0.1), FTSE +0.000 t 0.0 (de 6.1 a 0). First 30 min trading NO carry info sobre last 30. Overnight gap SÍ, en DAX/FTSE solo, y solo ahí.
- **OOS:** DAX efecto solo 2015-2020 (slope +0.034 t 4.5 R2 1.32%), desde 2021 gone (+0.002 t 0.3). FTSE mantiene 1/3 slope. US indices OOS reversal: SPX -0.025 t -2.5, Dow -0.024 t -2.6, R2 0.5% reversal no momentum.
- **Timing strategy:** Pierde en todos: NQ -3.15 bp/día t -5.5 costo 2.3 bp, SPX -2.88 t -5.6 costo 2.4 bp, Dow -2.66 t -5.4 costo 1.4 bp, DAX -1.10 t -2.8 costo 1.9 bp, FTSE -1.79 t -5.2 costo 2.0 bp. R2 1.3% significa predictor explica 1.3% varianza last half hour, 98.7% ruido que spread cobra cada día.
- **Conclusión:** 'The paper is right that first half hour measured from previous close predicts last half hour on some markets. It is wrong to call that intraday momentum. On DAX and FTSE entire effect sits in overnight gap; strip gap out and nothing remains, and gap effect itself shrinking since 2021. On Nasdaq, S&P and Dow, markets closest to paper's SPY, effect does not exist in 2015-2026 at all. A regression with R2 1% is description, not signal. Timing strategy loses 1-3 bp/day net in all five markets.'
- **Method point para EdgeLab:** Any predictor that starts at previous close carries overnight return inside it. Before calling result intraday anything, measure same predictor from open. If effect disappears, it was gap.

### 3. REPLICACIÓN ES FUTURES - RipBacktest (Oct 2026) - 'Intraday Momentum Backtest: ES First to Last Half-Hour' - Buried, No Proven Edge
- **URL:** https://ripbacktest.com/posts/intraday-momentum-es/ - Protocolo v1.0 + 8 Oct 2026 rules, rules frozen 11 Oct 2026 antes de computar.
- **Datos:** ES futures 1-min, US session, Jan 2020 - 25 Sep 2026, NinjaTrader back-adjusted. Development 2020-2023, Validation Jan 2024-Mar 2025, Holdout Apr 2025-Sep 2026 (already used). Costos $30.76/trade ($5.76 commission + 1 tick slippage cada fill, $50/pt).
- **4 variantes:** IM-ES-OV-LS (from previous close, long+short), IM-ES-OV-L (long only), IM-ES-RTH-LS (from 09:30 open), IM-ES-RTH-L (long only). Trade: in open minuto 15:30, out close minuto 16:00, 1 contrato, 1 trade/día max.
- **Resultados:** IM-ES-OV-LS 1,728 trades Net -$64,991 Net/trade -$37.61 Gross/trade -$6.85 Winners 45.3% PF 0.84 DD -$92,017 Buried. IM-ES-OV-L 959 trades -$37,661 -$39.27 Gross -$8.51 PF 0.82. IM-ES-RTH-LS 1,715 trades -$76,078 -$44.36 Gross -$13.60 PF 0.82. IM-ES-RTH-L 912 trades -$42,341 -$46.43 Gross -$15.67 PF 0.79. Todas perdieron en TODOS los periodos, incluso antes costos.
- **Control shifted-signal:** Mismo mix longs/shorts movido a otros días, 500 runs. Percentiles 20.6-38.8 (95 needed). Signal hizo PEOR que random days. Last half-hour solo: Up 49.1% días, avg move -0.08 pts, comprar cada día -$60,412 después costos. Coin toss.
- **Gates:** Todas fail PF >=1.2 validation, t >=2.5 development, >95th percentile control, positive sin 10 best trades, holdout positive. Verdict: No proven edge, negative before costs and below control.
- **Mismo test NQ:** También buried, first half-hour said nothing about last. (Link en post ES a post NQ).

### 4. MECANISMO - Baltussen, Da, Lammers, Martens (2021) - 'Hedging Demand and Market Intraday Momentum' - JFE 142, 377-403
- **SSRN:** Date Written Jan 2, 2021, JFE Vol 142 Issue 1 Oct 2021 Pages 377-403
- **Autores:** Guido Baltussen, Zhi Da, Sten Lammers, Martin Martens
- **Hallazgo:** Hedging short gamma exposure requires trading in direction of price movements, thereby creating price momentum. Using intraday returns on over 60 futures on equities, bonds, commodities, currencies 1974-2020, find strong market intraday momentum everywhere.
- **Mecanismo:** Market makers / leveraged ETFs short gamma tienen que hedgear comprando cuando sube y vendiendo cuando baja, creando momentum hacia cierre. Continuation debe vivir donde dealers short gamma, y estar ausente o revertir donde long gamma.
- **Para Bias Tracker:** Baltussen dice predictor no es first 30 min, es rest-of-day return (desde previous close hasta last 30 min) predice last 30 min. Es más amplio que Gao (first 30 -> last 30). Bias Tracker con Initial Move + VWAP + Value Area Shift podría estar capturando gamma hedging indirectamente, pero sin medir gamma directamente no lo prueba.
- **Test 0DTE era:** Firmtape / Dev.to retest 1,085 SPX sesiones 2022-04-14 a 2026-08-20, rest-of-day vs last 30, hedging-demand mechanism sharper prediction: continuation should live where dealers short gamma.

### 5. ESTRATEGIA DERIVADA - Zarattini, Aziz, Barbon (2024/2025) - 'Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)' + OOS 2026
- **Original:** SSRN 4824172, May 2024, 2007-early 2024, total return 1,985% net costs, annualized 19.6%, Sharpe 1.33, near-zero correlation, Quantpedia Awards 2025 4th place. Estrategia: Noise area breakout - Para cada minuto sesión, avg how far price has usually moved from open at that time over last 14 days, band around open is 'noise area', breakout = trade trend-following, VWAP trailing stops, flat at close, volatility-targeted, checks at HH:00/HH:30.
- **OOS Independiente:** Paz Serpa, June 2026, 'Out-of-Sample Evaluation of an Intraday Momentum Strategy for S&P 500 ETF (SPY)', SSRN, replica con IQFeed 1-min, evalúa May 2024-Mar 2026 (~2 años post-original). In-sample replica Sharpe 1.34 (confirma reproducibilidad), OOS deteriora sustancialmente: total return solo 9.4% vs 29.5% buy-and-hold pasivo. Sharpe OOS cae, estrategia no bate mercado OOS.
- **RipBacktest 3 papers:** Noise area breakout de Zarattini pasó every gate en NQ futures NY session (+$231,557 per contract over 1,504 trades después costos) y failed everywhere else. Muestra que intraday momentum puede funcionar en NQ con noise area, no con first->last simple.
- **Para EdgeLab:** Zarattini es mejor implementación que Gao simple: Usa noise area (volatilidad 14 días) + VWAP trailing + checks cada 30 min, no solo first 30 -> last 30. Bias Tracker podría mejorar si usa noise area en vez de Initial Move simple.

## Síntesis - Qué Es Verdad y Qué No

**Verdad (con respaldo):**
- Paper Gao et al. 2018 es real, peer-reviewed JFE, 16,554 downloads SSRN, citado 100s veces. First half-hour -> last half-hour existió 1993-2013 en SPY.
- Mecanismo gamma hedging (Baltussen 2021) es real y explica parte del momentum intradía en 60+ futuros 1974-2020.
- Zarattini noise area breakout funcionó in-sample 2007-2024 con Sharpe 1.33 y en NQ OOS con +$231k.
- Bias Tracker como idea (combinar varios factores en % objetivo) es correcta: No leer velas subjetivamente, usar score cuantitativo. Es lo mismo que EdgeLab hace con 47 filtros.

**Falso / Exagerado / Decaído:**
- 'Nobody uses this strategy' - Falso. Miles de quants, papers, y estrategias (Zarattini, Baltussen, RipBacktest, Krueger) la usan y la testearon. No es secreta.
- 'Best strategy in the world' - Exagerado. R2 1.6% en paper original, R2 0.01% en NQ 2015-2026. Es descripción, no señal tradeable sola.
- Efecto NO existe en US 2015-2026 sin gap. Krueger y RipBacktest lo enterraron: NQ slope 0, ES -$64k a -$76k, timing -1 a -3 bp/día. Si tradeas Gao simple hoy, pierdes.
- Gap es el driver, no intraday momentum. Si mides predictor desde open (sin gap), efecto desaparece en todos los mercados. David no distingue gap vs intraday en Bias Tracker, pero su panel SÍ tiene Gap como factor separado (Short en ejemplo), lo que es correcto: Gap debe ser factor separado, no mezclado con Initial Move.
- OOS Zarattini deteriora: 9.4% vs 29.5% buy-and-hold May 2024-Mar 2026. Estrategias intraday momentum decaen post-publicación.
- Bias 50% Bullish en ejemplo con 5 Long vs 1 Short: Si pesos iguales, debería ser 57-71% Bullish, no 50%. Fórmula no transparente, puede ser overfit o pesos arbitrarios. Sin fórmula, no puedes replicar ni validar.
- Niveles verde/rojo: No explica cómo se calculan, si son niveles precio, bias, o VWAP/Value Area. Sin fórmula, no es objetivo, es caja negra.

## Por Qué Es Valioso para EdgeLab - Conexión

- Conecta con Kemet Gap [DfSn9phMxuX]: Kemet dice gap <10 cierra 90%, gap 20+ cierra 33%, si a 10:30 sigue abierto solo 25% cierra. Krueger dice gap es TODO el efecto Gao. Kemet y Krueger dicen lo mismo: Gap es predictor, no first 30 min trading. Bias Tracker que separa Gap (Short) de Initial Move (Long) es correcto: Gap debe ser factor independiente.
- Conecta con FlexingJoe ORB [DfJdAz6xa_B]: Joe usa ORB 9:30-10:00 + 20 EMA pullback. Bias Tracker ORB Long es mismo factor. Joe no usa gap, Bias Tracker sí. Combinar Joe ORB + Kemet Gap + Gao Initial Move = Bias Tracker real.
- Conecta con RobotEdge VWAP Dual [DfStO27s4Sz]: RobotEdge VWAP Long es factor en Bias Tracker. RobotEdge usa 2 VWAPs (Diario + NY), Bias Tracker usa 1 VWAP (no especifica cuál). Mejora: Usar VWAP Diario + NY como 2 factores separados.
- Conecta con AlphaZone EMA+VWAP [DfVvb5ek-Nq]: AlphaZone usa EMA 9 + VWAP wick. Bias Tracker no tiene EMA, tiene VWAP + ORB + Value Area. Añadir EMA 9/20 como factor mejoraría Bias Tracker.
- Conecta con Italian Founder Backtests Lie [DfO091jBtvQ]: Italian Founder dice backtests mienten por spread $7 + comisión $2.50 + slippage 0.5 pts + swap. Gao paper reporta NO costos. Krueger y RipBacktest SÍ incluyen costos y estrategia pierde. Bias Tracker sin costos es inútil. Hay que backtestear Bias Tracker con costos reales.
- Conecta con Ayaan / QuantGuild: Ayaan dice necesitas 5 tests (Monte Carlo, Bonferroni, Power 400+, Noise, Outlier). Gao paper original NO pasó esos tests modernos. Krueger y RipBacktest SÍ los pasaron y enterraron Gao. Bias Tracker necesita pasar Ayaan 5 tests antes de usar en EdgeLab.

## Estrategia Derivada para EdgeLab - Bias Tracker Mejorado

**No uses Bias Tracker de David tal cual (caja negra). Usa Bias Tracker Mejorado con factores transparentes y pesos validados:**

```python
# edgelab/filters/bias/david_bias_tracker_improved.py
factors = {
    'gap_pct': gap / atr14,  # Kemet Gap, separado, no mezclado con Initial Move (Krueger)
    'initial_move_rth': (close_1000 - open_0930) / atr14,  # Gao sin gap, desde open
    'vwap_daily': 1 if price > vwap_daily else -1,
    'vwap_ny': 1 if price > vwap_ny else -1,  # RobotEdge mejora: 2 VWAPs
    'orb': 1 if price > orb_high else -1 if price < orb_low else 0,  # FlexingJoe
    'ema9_20': 1 if ema9 > ema20 else -1,  # AlphaZone
    'value_area_shift': sign(va_shift),
    'daily_candle': sign(close_daily - open_daily),
    'session_hl': 1 if price > session_high else -1 if price < session_low else 0,
    'noise_area': 1 if price > noise_area_high else -1 if price < noise_area_low else 0,  # Zarattini
    'gamma': 1 if dealer_gamma_short else -1,  # Baltussen, si tienes data gamma
}
bias = sum(weights[f] * factors[f]) / sum(weights) * 100  # Pesos via regresión logística OOS, no arbitrarios
if bias > 60 and time == '15:30': enter_long_last_30() # Solo si bias fuerte y hora es last 30, no todo día
if bias < -60 and time == '15:30': enter_short_last_30()
else: no_trade() # No trade si bias débil o no es last 30, evita overtrading
```

**Validación requerida antes de usar:**
- Backtest 2015-2026 NQ/ES 1-min con costos $30.76/trade (RipBacktest) + spread 2.3 bp (Krueger)
- Separar gap vs RTH (Krueger method): Si efecto desaparece sin gap, no es intraday momentum, es gap persistence.
- OOS 2021-2026 (Krueger OOS) + OOS May 2024-Mar 2026 (Zarattini OOS)
- Control shifted-signal (RipBacktest): Percentile >95 needed
- Gates: PF >=1.2 validation, t >=2.5 development, positive sin 10 best trades, holdout positive
- Si no pasa gates, no usar. Si pasa solo en DAX/FTSE con gap, usar solo ahí, no en NQ/SPX.

## Advertencias

- Paper original no es estrategia tradeable sola: R2 1.6% significa 98.4% ruido. Necesitas combinar con otros factores (como Bias Tracker intenta) y aún así puede no ser suficiente.
- Replicaciones matan Gao simple: Krueger y RipBacktest son 2025-2026, con datos más recientes y costos, y dicen NO edge en US.
- Bias Tracker de David es caja negra: No muestra pesos, no muestra fórmula, no muestra backtest. No puedes validar sin CTA GATES.
- 'Nobody uses' es marketing: Paper tiene 16,554 downloads, 100s citas, y estrategias derivadas (Zarattini, Baltussen) son conocidas. No es secreto.
- Gap Short en ejemplo: Si gap es up (+), ¿por qué factor Gap es Short? ¿Significa gap up es bearish (fade gap) o gap down es bullish? Video no explica. Kemet dice gap <10 vuelve (fade gap), gap 20+ no vuelve (trend gap). Gap factor debe ser condicional por tamaño, no simple Long/Short.
- Niveles verde/rojo: Sin fórmula, no sabes si son niveles de bias, precio, VWAP, Value Area, o inventados.

## Filter Mapping Sugerido EdgeLab

- strategy: david_bias_tracker
- filter: intraday_momentum_gao_first_last_halfhour
- filter: gap_vs_rth_separation_krueger
- filter: bias_tracker_multi_factor
- factor: initial_move_long
- factor: vwap_long
- factor: daily_candle_long
- factor: session_hl_neutral
- factor: value_area_shift_long
- factor: orb_long
- factor: gap_short
- indicator: bias_pct_50_bullish
- validation: gao_2018_jfe_129_394_414
- validation: krueger_2026_replication_gap_effect
- validation: ripbacktest_2026_es_nq_buried
- validation: baltussen_2021_gamma_hedging
- validation: zarattini_2024_beat_market_oos_2026_deterioration
- bot_logic: edgelab/filters/bias/david_bias_tracker_improved.py
- next_steps: Pedir sistema GATES para pesos/fórmula, replicar con costos, OOS, control shifted-signal, gates Ayaan

## CTA / Funnel

- CTA: Comment 'GATES' to see the system I use
- Lead magnet: Bias Tracker system (indicador + niveles verde/rojo)
- Competidor: DavidTrades (GATES) vs RobotEdge (GUÍA) vs AlphaZone (RQ) vs Italian Founder (ALGO) vs FlexingJoe (VIDEO) - Todos mismo funnel comment keyword -> DM -> sistema/PDF/video -> curso

## Fuentes de Respaldo - Links para Verificar

- Paper original SSRN: https://ssrn.com/abstract=2440866 - Gao, Han, Li, Zhou, Market Intraday Momentum, JFE 2018, 48 páginas, 16,554 downloads
- Paper JFE ScienceDirect: https://www.sciencedirect.com/science/article/pii/S0304405X1830143X - Market Intraday Momentum, JFE 129 (2018) 394-414
- Replicación Krueger: https://kruegeralgorithms.com/en/research/intraday-momentum-paper-replication - 2026-09-17, 7 páginas PDF, 5 índices 2015-2026
- Replicación RipBacktest ES: https://ripbacktest.com/posts/intraday-momentum-es/ - ES 2020-2026, 4 variantes, Buried, No proven edge
- Replicación RipBacktest NQ: https://ripbacktest.com/posts/intraday-momentum-nq/ - NQ 2020-2026, también Buried
- Baltussen JFE 2021: https://papers.ssrn.com/sol3/papers.cfm?abstract_id= - Hedging Demand and Market Intraday Momentum, JFE 142 (2021) 377-403, 60+ futuros 1974-2020
- Zarattini Original: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172 - Beat the Market, SPY 2007-2024, 19.6% anual, Sharpe 1.33
- Zarattini OOS 2026: https://papers.ssrn.com/sol3/papers.cfm?abstract_id= - Out-of-Sample Evaluation, May 2024-Mar 2026, 9.4% vs 29.5% buy-and-hold, deterioro
- RipBacktest 3 Papers: https://ripbacktest.com/posts/intraday-momentum-3-papers/ - Comparación Gao vs Baltussen vs Zarattini
- Firmtape 0DTE Era: https://firmtape.com/research/is-intraday-momentum-still-alive - 1,085 SPX sesiones 2022-2026, 0DTE era

## Capturas Frame Clave

- 0s: Market Intraday Momentum - Lei Gao, Yufeng Han, Sophia Zhengzi Li, Guofu Zhou - First Draft March 2014 Current Version June 2017 - NOBODY USES THIS STRATEGY
- 5s: there is a lot of research on intraday momentum
- 9s: the way the market moves on its biggest days
- 13s: so why does this actually work? because it gives you a statistical...
- 18s: problems when we look at a chart say... just say are we bullish or bearish?
- 23s: and we decide that only by looking at the candles but the truth is that is not objective
- 28s: personally i use the ... indicator - BIAS: 50.00 STATE: Bullish
- 30s: it's called a bias tracker and it measures the pressure behind the bias
- 35s: it gives the trend a percentage - for example right now we're at 50 percent
- 39s: it combines several parameters into one bias reading - Initial Move Long, VWAP Long, Daily Candle Long, Session HL Neutral, Value Area Shift Long, ORB Long, Gap Short
- 45s: in this case it's 50 percent bullish and it shows me each parameter as a...
- 50s: this is an objective way to read the market and you don't just look at candles to define today's trend
- 55s: you also see how strong it is and as you can see there's also levels in green and in red and i use them as reference levels for my...
- 68s: so comment gates to get the system - COMMENT GATES TO SEE THE SYSTEM I USE

