# Comunidades del grafo — CerebroSSRN (Fase 4)

Detectadas con Louvain (NetworkX, local) sobre `grafo_final.json`, ponderando
las aristas por tipo (USA/PARTE_DE con peso bajo por ser pegamento genérico;
PREDICE/CAUSA/MEJORA_A/MITIGA con peso alto) para que las constelaciones se
formen alrededor de contenido, no de composición técnica. 254 comunidades,
171 nodos aislados (cola larga de mención única, normal), 28 con ≥5 nodos.

Cada constelación es una **familia temática** del corpus: un conjunto de
conceptos/técnicas que co-ocurren en los mismos papers. Abajo, las 20 más
grandes con su lectura y, donde aplica, su gancho al ecosistema ES.

---

**[108] Microestructura del libro y selección adversa**
bid-ask spread, adverse selection, limit order book, informed trading, latency, tick size, spoofing, quote stuffing, liquidity provision, order book depth.
La constelación más grande: cómo se forma el spread y cómo la información asimétrica (informed trading, adverse selection) lo mueve. El corazón teórico de por qué existen las zonas de liquidez. Gancho ES: el marco conceptual de qué *son* las zonas HFT que loguea el indicador — resting liquidity que sufre selección adversa cuando llega flujo informado.

**[78] Impacto de precio y flujo de órdenes**
market impact, order flow imbalance, realized volatility, mid-price, tick data, Kyle lambda, market depth, order splitting, linear market impact model.
El clúster de "cómo el flujo mueve el precio": OFI, Kyle's lambda (impacto por unidad de flujo), impacto lineal vs raíz cuadrada. Gancho ES directo: **estas son las features candidatas #1 para construir sobre tus ticks L1** — OFI y sus primos son la fábrica de señales de la que hablábamos.

**[75] Anti-overfitting y validación (el auditor metodológico)**
backtest overfitting, walk-forward validation, look-ahead bias, data snooping, out-of-sample testing, regime switching, survivorship bias, model uncertainty, false discovery rate, deflated Sharpe.
El clúster que convierte al cerebro en auditor. Todo lo que hace que un backtest mienta y las técnicas para no engañarse. Gancho ES: es el checklist que se le pasa a *cualquier* corrida de `brute_excursions`/Optuna antes de creerle — incluido el problema del split IS/OOS cayendo en el roll que ya vimos.

**[74] Estadística de series temporales y (in)eficiencia**
mean reversion, volatility clustering, cointegration, momentum, GARCH, efficient market hypothesis, Hurst exponent, adaptive markets hypothesis, geometric Brownian motion.
La caja de herramientas econométrica: reversión vs momentum, memoria de la volatilidad, Hurst como test de persistencia. Gancho ES: tests para caracterizar el régimen de una serie antes de elegir familia de estrategia.

**[68] Pairs trading y arbitraje estadístico**
transaction costs, pairs trading, statistical arbitrage, market neutral strategy, minimum distance method, cointegration method, short-term reversal, MODWT wavelets, shrinkage.
La familia stat-arb completa: selección de pares, distancia mínima, cointegración, market-neutral. Menos aplicable al ES intradía de un solo instrumento, pero el andamiaje de costos y neutralidad es transferible.

**[62] Métricas de performance y RL**
Sharpe ratio, Sortino ratio, Probabilistic Sharpe Ratio, information ratio, expectancy, reinforcement learning, Q-learning, Ornstein-Uhlenbeck process, reward function.
Cómo se mide una estrategia (familia Sharpe + expectancy, que ya usás en quantlab) cruzado con RL (el reward como la métrica que el agente optimiza). Gancho ES: PSR/deflated Sharpe son mejoras directas a los reportes de tearsheet.

**[60] HFT, market making y fragilidad**
high-frequency trading, market making, flash crash, latency arbitrage, liquidity taking, order-to-trade ratio, hybrid market, cancel-to-trade.
El ecosistema HFT y sus patologías (flash crash, latency arb). Contexto de quién genera y consume las zonas. Ojo con la brecha de datos: mucho de esto asume L2/L3.

**[49] Ejecución óptima**
optimal execution, Almgren-Chriss framework, queue position, Monte Carlo simulation, Lobster database, level II order book data, power-law order arrival, cancellation rate.
Cómo entrar/salir minimizando impacto (Almgren-Chriss) y la posición en la cola. Gancho ES: relevante si alguna vez modelás fills realistas en las zonas; requiere L2 que hoy no tenés (declarar la brecha).

**[48] Volatilidad de opciones y modelos estocásticos**
implied volatility, local volatility model, stochastic volatility model, volatility skew, jump-diffusion, implied volatility surface, martingale, Heston.
El mundo de derivados/vol. Marginal para el ES intradía direccional, salvo como fuente de features de régimen (vol implícita como condicionante).

**[43] price discovery y liquidez (FX/macro)**
price discovery, market liquidity, market microstructure, permanent price impact, exchange rate volatility, portfolio-balance channel, signalling channel.
Cómo el precio incorpora información y el rol de la liquidez; sesgado a FX/intervención. Conceptual.

**[43] Ruido de microestructura y estimación de beta**
market microstructure noise, VWAP, bid-ask bounce, beta y sus ajustes (Dimson, Vasicek Bayesian, t-distribution), CAPM, APT.
El ruido de alta frecuencia que contamina estimadores + la familia de correcciones de beta. Gancho ES: el bid-ask bounce es exactamente el tipo de ruido que ensucia señales tick-by-tick.

**[28] Riesgo de inventario y sizing**
inventory risk, Amihud illiquidity, position sizing, Kelly criterion, stochastic control, order flow correlation, quoted spread.
El problema del market maker (inventario) + cómo dimensionar posición (Kelly). Gancho ES: Kelly/sizing aplican a cualquier estrategia con edge medido.

**[27] Trading algorítmico y sentiment/NLP**
algorithmic trading, sentiment analysis, natural language processing, difference-in-differences, Heckman selection, GARCH(1,1), reverse causality.
Señales de texto + econometría causal (DiD, Heckman) para medir efectos de eventos. La parte causal es útil para el auditor.

**[22] Hedging de derivados y correlación**
delta hedging, dispersion trading, quadratic variation, Black-Scholes PDE, counterparty risk, implied correlation, finite difference.
Cluster técnico de opciones/hedging. Marginal para ES direccional.

**[21] Drawdown control y ML adversarial**
maximum drawdown, Calmar ratio, stop-loss, deep RL, adversarial attack/training, FGSM, PGD, defensive distillation.
Control de riesgo (drawdown/Calmar/stop) mezclado con robustez adversarial de modelos ML. Gancho ES: Calmar y stop-loss son directamente aplicables; lo adversarial importa si algún día ponés un modelo ML en producción.

**[16] ML tabular y feature selection**
ARIMA, random forest, XGBoost, AutoML, feature importance, Shapley values, TPOT, next-day return.
La caja de ML clásico para predecir retornos + interpretabilidad (SHAP/Shapley). Gancho ES: XGBoost + feature importance es un camino concreto para el meta-labeling de las zonas.

**[15] Trading + LLMs como razonadores (meta)**
trend following, refutation-based debate, cognitive incompatibility, persona bias, consensus illusion, constructive debate.
Papers recientes sobre usar LLMs/debate multi-agente en trading. Meta-relevante para *este* proyecto (cómo razona el cerebro), no como señal.

**[13] Procesos de Hawkes y condicionamiento temporal**
Hawkes process, power-law kernel, time-of-day conditioning, near-critical regime, branching ratio, Ogata thinning, Echo State Network, compound Hawkes.
Auto-excitación del flujo de órdenes (Hawkes) + condicionamiento por hora del día. Gancho ES fuerte: **intensidad de Hawkes como feature de "cuán clusterizado está el flujo ahora"** y el time-of-day conditioning valida agregar hora a la grilla.

**[12] Construcción de portfolio por señales**
signal-based portfolio construction, signal consensus, Black-Litterman, false signal rate, rolling window, dual-model alpha, universe selection.
Cómo combinar señales en posiciones (Black-Litterman, consenso de señales, tasa de falsas señales). El dual-model alpha es primo del meta-labeling.

**[8] Arbitraje y (in)eficiencia de mercado**
arbitrage, efficient price, bad/good spread, market structure inefficiency, market gaming, violations of individual rationality.
Cluster chico sobre cuándo el spread es "malo" (ineficiencia explotable) vs "bueno". Conceptual.

---

*Nota de calidad:* algunas islas pequeñas (no listadas) son ruido de papers
off-topic que entraron por keyword de SSRN — p.ej. una comunidad de "temporal
graphs / broadcast networks" (teoría de grafos pura) totalmente desconectada
del núcleo de trading. Son inofensivas: quedan aisladas y con doc_frecuencia 1.
