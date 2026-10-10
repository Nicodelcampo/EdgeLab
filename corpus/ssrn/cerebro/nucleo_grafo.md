# Núcleo del grafo — CerebroSSRN (trading cuantitativo)

596 conceptos centrales (de 2488 totales; el resto en el índice de cola larga).
Formato: **Nombre** [tipo] (docs=N) — definición. Relaciones: TIPO → Objeto (n_docs).

**transaction costs** [concepto] (docs=42) [también: Transaction Cost, Transaction Costs] — Costos de ejecutar un bet, descompuestos en un componente de bid-ask spread (fijo) y un componente de market impact (variable con el tamaño). La función de costo porcentual C(Q̃) se escribe como el producto de una medida de iliquidez específica del activo 1/L y una función inv...  
  Relaciones: MITIGA → backtest overfitting (6); MITIGA → pairs trading (3); APLICA_A → algorithmic trading (1); PARTE_DE → pairs trading (1); SE_OPONE_A → momentum (1); PARTE_DE → realistic trading simulation (1); CAUSA → signal-to-noise ratio (1); MITIGA → statistical arbitrage (1)

**high-frequency trading** [estrategia] (docs=39) [también: High Frequency Trading, High Frequency Trading (HFT), High-Frequency Trading, High-Frequency Trading (HFT)] — Trading de alta frecuencia definido por: (1) uso de infraestructura tecnológica avanzada para minimizar latencia, (2) algoritmos de generación, ruteo y ejecución de órdenes, (3) colocation/proximity hosting, (4) altos ratios de cancelación/modificación, (5) posiciones intradía...  
  Relaciones: REQUIERE → latency (4); APLICA_A → market making (4); USA → latency (4); PARTE_DE → algorithmic trading (3); CAUSA → adverse selection (2); MITIGA → transaction costs (2); EQUIVALE_A → algorithmic trading (2); USA → electronic trading (1)

**bid-ask spread** [concepto] (docs=36) [también: Bid-Ask Spread, Bid-ask spread] — Diferencia entre el mejor precio de compra (bid) y de venta (offer/ask) en el libro de órdenes. Los autores argumentan que el spread reportado es casi inútil porque los precios reales de ejecución son significativamente mejores, ya que órdenes ligeramente dentro del spread se ...  
  Relaciones: MIDE → market liquidity (7); PARTE_DE → limit order book (7); MIDE → liquidity provision (3); PARTE_DE → market making (3); CAUSA → adverse selection (3); MIDE → transaction costs (3); PARTE_DE → transaction costs (3); MIDE → limit order book (2)

**Sharpe ratio** [metrica] (docs=36) [también: Sharpe Ratio] — Retorno anualizado menos tasa libre de riesgo (4%) sobre desviación estándar anualizada; el paper advierte que es manipulable según cómo se calcule la desviación estándar y que no distingue volatilidad positiva de negativa, por lo que lo complementa con VaR, skewness, kurtosis...  
  Relaciones: MIDE → pairs trading (5); MIDE → reinforcement learning (2); MIDE → algorithmic trading (1); MIDE → non-stationary model for statistical arbitrage trading (1); SE_OPONE_A → weak stochastic dominance (1); SE_OPONE_A → R-multiple (1); MIDE → trading performance degradation (1); MIDE → market making (1)

**backtest overfitting** [riesgo_metodologico] (docs=32) [también: Overfitting, overfitting] — Riesgo mitigado mediante walk-forward validation estricta, BCa bootstrap CIs, y tests de Wilcoxon con corrección por overlap de folds. El paper también aborda survivorship bias (≤3% Sharpe inflation estimado) y false discovery rate en la selección de pares (~17-30% de pares po...  
  Relaciones: MITIGA → walk-forward validation (10); CAUSA → data snooping (4); MITIGA → adversarial training (2); CONTRADICE_A → walk-forward validation (2); PARTE_DE → backtest-to-live deployment gap (1); MITIGA → market microstructure model (1); CAUSA → spurious correlation (1); MITIGA → out-of-sample testing (1)

**pairs trading** [estrategia] (docs=30) [también: Pairs Trading] — Estrategia que implica la compra y venta simultánea de dos instrumentos financieros que tienden a moverse al unísono, explotando desviaciones temporales respecto a la Ley del Precio Único. En este paper se extiende al universo de opciones, formando pares long-short de calls eu...  
  Relaciones: USA → cointegration (16); PARTE_DE → statistical arbitrage (7); REQUIERE → mean reversion (6); USA → Ornstein-Uhlenbeck process (4); APLICA_A → statistical arbitrage (3); USA → mean reversion (3); EQUIVALE_A → statistical arbitrage (3); USA → minimum distance method (2)

**market impact** [concepto] (docs=28) [también: Market Impact, Price Impact, price impact] — Medida del costo de ejecutar una orden debido al movimiento adverso del precio. El paper distingue entre el costo de price impact (transactions cost CB) y el parámetro de price impact (λ), que en el modelo de dealer market resultan ser conceptos relacionados pero distintos. Em...  
  Relaciones: PARTE_DE → transaction costs (4); CAUSA → transaction costs (3); PARTE_DE → optimal execution (2); CAUSA → fire sale (1); PARTE_DE → price-mediated contagion (1); PARTE_DE → limit order book (1); USA → order flow imbalance (1); MIDE → mid-price (1)

**statistical arbitrage** [estrategia] (docs=28) [también: Statistical Arbitrage] — Familia de estrategias donde las posiciones se toman según modelos sistemáticos que detectan desviaciones del valor relativo predicho, con exposición neta acotada (nunca más de 20% long o short según la definición de Morgan Stanley que adopta el paper). El paper lo plantea com...  
  Relaciones: EQUIVALE_A → pairs trading (7); USA → mean reversion (5); USA → pairs trading (5); USA → momentum (2); REQUIERE → transaction costs (2); USA → cointegration (2); PARTE_DE → high-frequency trading (2); REQUIERE → mean reversion (2)

**mean reversion** [fenomeno] (docs=28) [también: Mean Reversion, mean-reversion] — Estrategia donde dos retornos simples negativos consecutivos disparan una compra (esperando reversión al alza) y dos positivos consecutivos disparan una venta. Backtesteada en S&P 500 diario de 1950-1997 resultó no rentable (Sharpe -0.04), pero en el OOS 1998-2016 rindió Sharp...  
  Relaciones: SE_OPONE_A → momentum (9); CAUSA → pairs trading (3); USA → Ornstein-Uhlenbeck process (2); CAUSA → statistical arbitrage (2); SE_OPONE_A → non-stationary behaviour (1); CAUSA → optimal investment strategy (1); PARTE_DE → statistical arbitrage (1); USA → principal component analysis (1)

**limit order book** [concepto] (docs=26) [también: Limit Order Book, Limit Order Book (LOB)] — Registro de órdenes de compra y venta pendientes en un exchange. Los autores cuestionan su utilidad informativa real desde aproximadamente 2008-2010, argumentando que los mejores niveles de precio reportados son demasiado conservadores y que la información real del exchange no...  
  Relaciones: PARTE_DE → market microstructure (8); REQUIERE → order flow (2); USA → order flow (2); PARTE_DE → queue position (2); USA → queue position (2); USA → tick size (2); PARTE_DE → market microstructure model (1); USA → market clearing operator (1)

**adverse selection** [concepto] (docs=25) [también: Adverse Selection] — Riesgo que enfrentan los proveedores de liquidez (especialmente slow traders) de que sus órdenes límite sean pickeadas por HFT firms que conocen el valor fundamental contemporáneo del activo y detectan cuándo una orden límite ha quedado en posición desfavorable. Este riesgo in...  
  Relaciones: CAUSA → bid-ask spread (10); CAUSA → market impact (4); PARTE_DE → market making (2); PARTE_DE → market microstructure (2); PARTE_DE → market microstructure model (1); MITIGA → bid-ask spread (1); PARTE_DE → informed trading (1); SE_OPONE_A → order book convexity (1)

**market making** [estrategia] (docs=23) [también: Market Making] — Estrategia de provisión de liquidez mediante limit orders en ambos lados del libro. El paper formula el problema de market making robusto donde el agente es averso a la ambigüedad sobre la llegada de market orders, la probabilidad de fill y el drift del midprice, usando contro...  
  Relaciones: USA → inventory risk (3); USA → limit order book (3); USA → adverse selection (2); REQUIERE → limit order book (2); PARTE_DE → high-frequency trading (2); USA → high-frequency trading (2); USA → bid-ask spread (2); PARTE_DE → market microstructure model (1)

**maximum drawdown** [metrica] (docs=22) [también: Maximum Drawdown] — Métrica primaria para H2. Kalman reduce fold-mean MaxDD en 71% vs OLS (-0.31% vs -1.07%). HMM conditioning reduce otro 30% adicional (a -0.22%). La reducción de drawdown no es explicable por menores holding periods (Branch D lo confirma).  
  Relaciones: MIDE → pairs trading (3); MIDE → reinforcement learning (2); PARTE_DE → Calmar ratio (1); PARTE_DE → path-dependent diagnostics (1); MIDE → portfolio robustness (1); MIDE → trading performance degradation (1); USA → Kalman filter (1); SE_OPONE_A → mean reversion (1)

**cointegration** [concepto] (docs=20) [también: Cointegration] — Propiedad estadística que garantiza que el spread de un par es estacionario, proporcionando una asociación econométricamente más fiable entre los activos que el método de distancia, aunque el paper muestra que la mayoría de pares pierden la cointegración en el período de test.  
  Relaciones: USA → pairs trading (4); APLICA_A → pairs trading (3); PARTE_DE → pairs trading (2); CAUSA → mean reversion (2); REQUIERE → pairs trading (2); USA → spread (2); EQUIVALE_A → mean reversion (2); PARTE_DE → error correction model (1)

**walk-forward validation** [metodo] (docs=19) [también: Walk-Forward Validation] — Validación out-of-sample secuencial donde la estrategia se prueba en datos posteriores a los de entrenamiento. El paper argumenta que incluso la validación OOS es insuficiente porque la no estacionariedad de las series de precios y las colas gruesas implican que la significanc...  
  Relaciones: MITIGA → backtest overfitting (13); MITIGA → look-ahead bias (6); USA → pairs trading (2); USA → algorithmic trading (1); PARTE_DE → pairs trading (1); USA → hidden Markov model (1); USA → random forest (1); REQUIERE → large language models (1)

**price discovery** [fenomeno] (docs=17) [también: Price Discovery] — Proceso mediante el cual los precios de mercado incorporan nueva información y convergen hacia el valor intrínseco. Índices de mayor capitalización logran un price discovery más veloz (g cercano a 1) mientras los de menor capitalización muestran ajuste más lento y estadísticam...  
  Relaciones: PARTE_DE → market microstructure (3); REQUIERE → interbank market (1); CAUSA → order flow imbalance (1); MITIGA → bid-ask spread (1); MEJORA_A → market efficiency (1); SE_OPONE_A → minimum hold time (1); PARTE_DE → market efficiency (1); APLICA_A → Kyle model (1)

**informed trading** [fenomeno] (docs=16) [también: Informed Trading] — Actividad de trading por agentes con información superior que deben camuflar sus órdenes fragmentándolas para evitar impacto adverso en precio. El resultado es una anomalía sutil: el precio deriva direccionalmente respecto al bajo volumen aparente, indetectable por GARCH pero ...  
  Relaciones: CAUSA → adverse selection (4); CAUSA → market impact (2); USA → Kyle model (1); PREDICE → price discovery (1); PARTE_DE → order flow (1); PREDICE → order flow imbalance (1); CAUSA → informational gap (1); SE_OPONE_A → algorithmic trading deters information acquisition (1)

**volatility clustering** [fenomeno] (docs=15) — No se modela clustering propiamente, pero el paper muestra que niveles más altos de volatilidad de precios deterioran severamente la capacidad del trader de extraer información de las innovaciones de precio, tornando la estrategia más conservadora.  
  Relaciones: PARTE_DE → GARCH (2); CAUSA → cointegration (1); CONTRADICE_A → geometric Brownian motion (1); CAUSA → wick-triggered stop-loss (1); CAUSA → inventory risk (1); MIDE → regime switching (1); CAUSA → GARCH (1); CAUSA → behavioral finance (1)

**look-ahead bias** [riesgo_metodologico] (docs=15) [también: Look-Ahead Bias, Look-ahead Bias] — Sesgo introducido al normalizar el spread usando información futura para calcular media y desviación estándar. El paper usa una ventana móvil de 63 días (3 meses) con solo datos pasados, ya que conocer el rango futuro de la señal otorgaría una ventaja injusta y sesgaría positi...  
  Relaciones: MITIGA → walk-forward validation (2); CONTRADICE_A → walk-forward validation (2); MITIGA → Walk-Forward Optimization (1); MITIGA → rolling window standardization (1); MITIGA → audit trail (1); CONTRADICE_A → large language models (1); MITIGA → transaction costs (1); MITIGA → pairs trading (1)

**algorithmic trading** [estrategia] (docs=14) [también: Algorithmic Trading] — Trading automatizado por computadora. En el lenguaje del modelo, corresponde a un aumento en la tasa rho a la que los inversores contactan el mercado. El paper predice que a mayor rho, mayor ratio de mensajes (órdenes + cancelaciones + modificaciones) a volumen, en línea con l...  
  Relaciones: USA → machine learning (3); SE_OPONE_A → buy-and-hold (1); USA → walk-forward validation (1); MEJORA_A → buy-and-hold (1); PARTE_DE → high-frequency trading (1); MEJORA_A → Revelatory Price Efficiency (1); CAUSA → Liquidity Commonality (1); USA → market making (1)

**order flow imbalance** [concepto] (docs=14) [también: Order Flow Imbalance, order-flow imbalance] — Volume order imbalance usado como predictor de mercado en el nuevo modelo de referencia del Capítulo 4. El imbalance se modela como un proceso de Markov de dos estados que afecta las intensidades de salto del midprice y las tasas de llegada de market orders.  
  Relaciones: PARTE_DE → limit order book (2); USA → queue position (1); PREDICE → bid-ask spread (1); MIDE → informed trading (1); PARTE_DE → Glosten-Milgrom model (1); USA → limit order book (1); PREDICE → midprice dynamics (1); PARTE_DE → regime switching (1)

**reinforcement learning** [metodo] (docs=13) [también: Reinforcement learning] — Aprendizaje para problemas de decisión secuencial donde un agente interactúa con un entorno y ajusta sus acciones para maximizar recompensas futuras acumuladas; usado en market making y ejecución óptima, y propuesto como área subexplotada en trading deportivo.  
  Relaciones: USA → Q-learning (2); APLICA_A → algorithmic trading (2); CAUSA → algorithmic collusion (1); MEJORA_A → distance method (1); MEJORA_A → Ornstein-Uhlenbeck process (1); APLICA_A → statistical arbitrage (1); APLICA_A → high-frequency trading (1); USA → reward function (1)

**momentum** [fenomeno] (docs=13) [también: Momentum] — Estrategia de trend-following basada en moving average: comprar cuando el precio está por encima de la MA y vender cuando está por debajo. El paper la backtestea en el S&P 500 diario de 1950-1997 con períodos m de 2 a 20 días, obteniendo Sharpe máximo de 1.90 para m=2.  
  Relaciones: SE_OPONE_A → mean reversion (10); CAUSA → statistical arbitrage (1); SE_OPONE_A → efficient market hypothesis (1); MITIGA → data snooping (1); PARTE_DE → Style Investing (1); CAUSA → trading volume (1); USA → moving averages (1)

**market microstructure** [concepto] (docs=12) [también: Market Microstructure] — Campo de estudio de los procesos mediante los cuales los mercados financieros transfieren riesgos, enfocándose en mecanismos de formación de precios, costos de transacción, flujo de órdenes y el rol de intermediarios. El paper lo modela como un juego de trading donde los 'bets...  
  Relaciones: USA → bid-ask spread (2); USA → limit order book (2); APLICA_A → bid-ask spread (1); APLICA_A → market liquidity (1); USA → machine learning (1); CAUSA → market liquidity (1); APLICA_A → price discovery (1); USA → auction theory (1)

**Ornstein-Uhlenbeck process** [metodo] (docs=12) [también: Ornstein-Uhlenbeck Process] — Proceso de reversión a la media usado como baseline paramétrico para extracción de señales. El modelo de Yeo y Papanicolaou (2017) basado en OU es el mejor benchmark paramétrico, pero es superado por el convolutional transformer por un factor de ~2x en Sharpe.  
  Relaciones: USA → mean reversion (2); PARTE_DE → statistical arbitrage (2); USA → maximum likelihood estimation (2); EQUIVALE_A → mean reversion (2); PARTE_DE → pairs trading (2); REQUIERE → half-life (2); PARTE_DE → non-stationary model for statistical arbitrage trading (1); MEJORA_A → arithmetic Brownian motion (1)

**liquidity provision** [concepto] (docs=11) — Estrategia por la cual un agente envía órdenes límite al libro, proporcionando liquidez al mercado y capturando el immediacy cost pagado por quienes envían órdenes de mercado. Los HFT pueden usar su ventaja informacional y de velocidad para proveer liquidez más eficientemente ...  
  Relaciones: MEJORA_A → open-outcry trading (1); REQUIERE → electronic trading (1); REQUIERE → tick size (1); MITIGA → adverse selection (1); MITIGA → volatility clustering (1); USA → market making (1); CAUSA → bid-ask spread (1); USA → bid-ask spread (1)

**regime switching** [metodo] (docs=11) — Alternancia del mercado entre estados estructuralmente distintos: régimen 0 (ruido) donde µ exógena domina y ∥ϕ∥≈0, y régimen 1 (criticalidad) donde el branching ratio n→1 y cada evento incrementa la probabilidad de eventos subsecuentes. La transición entre regímenes es la señ...  
  Relaciones: USA → hidden Markov model (3); APLICA_A → pairs trading (2); CAUSA → market liquidity (1); PARTE_DE → central bank intervention (1); MITIGA → backtest overfitting (1); CAUSA → backtest overfitting (1); MIDE → hidden Markov model (1); CAUSA → volatility clustering (1)

**market microstructure noise** [riesgo_metodologico] (docs=11) [también: microstructure noise] — Componente del precio de transacción que lo separa del valor fundamental del activo (pt = vt + ηt). Se reduce monótonamente al aumentar la proporción de fast traders en el mercado, ya que más agentes con ventaja de velocidad reducen las fricciones del sistema.  
  Relaciones: PARTE_DE → limit order book (1); MITIGA → backtest overfitting (1); MIDE → Bid-Ask Bounce (1); CAUSA → realized volatility (1); MITIGA → closing price (1); PARTE_DE → transaction costs (1); MITIGA → high-frequency trading (1); USA → limit order book (1)

**market liquidity** [concepto] (docs=10) [también: liquidity] — Medida de iliquidez definida como 1/L := C̄B / E{|P·Q̃|} que representa el costo porcentual esperado de ejecutar un bet. La invarianza predice que L (liquidez) es proporcional a [P·V̄/σ̄²]^(1/3). Alternativamente, usando variables observables: 1/L ∝ (σ² / P·V)^(1/3). Esta medi...  
  Relaciones: MEJORA_A → transaction costs (2); MIDE → bid-ask spread (2); SE_OPONE_A → administered pricing (1); CAUSA → short-term reversal (1); USA → realized spread (1); USA → Amihud illiquidity (1); USA → Kyle lambda (1); MIDE → transaction costs (1)

**VWAP** [metrica] (docs=10) — Estrategia límite de la solución óptima cuando la aversión al riesgo es cero (lambda=0); se usa también en su variante 'early-end' (finalización anticipada) como referencia heurística para calibrar lambda, siendo subóptima frente a la frontera eficiente salvo en sus puntos ext...  
  Relaciones: MEJORA_A → closing price (2); SE_OPONE_A → Limit Order Book Based Price (1); USA → order book density function (1); APLICA_A → closing auction (1); USA → VWAP beta (1); MITIGA → market microstructure noise (1); EQUIVALE_A → early-end VWAP strategy (1); USA → risk aversion parameter (1)

**latency** [concepto] (docs=10) [también: Latency] — Tiempo de transmisión y procesamiento de datos entre el mercado y el servidor del trader. HFT firms invierten fuertemente en reducir latencia mediante colocation, fiber optics, microwave signals y hardware especializado (FPGA).  
  Relaciones: CAUSA → adverse selection (2); PARTE_DE → high-frequency trading (2); MIDE → electronic trading (1); CAUSA → order anticipation (1); REQUIERE → high-frequency trading (1)

**hidden Markov model** [metodo] (docs=9) [también: Hidden Markov Model (HMM)] — HMM de dos estados Gaussianos con features pair-specific (spread volatility, autocorrelación, rolling ADF p-value) para identificar regímenes 'calm' y 'turbulent'. En régimen turbulento se suprimen nuevas entradas, reduciendo drawdown sin sacrificar retorno.  
  Relaciones: USA → regime switching (3); APLICA_A → regime switching (2); USA → Viterbi algorithm (2); MIDE → market regime (1); PARTE_DE → dual-model alpha system (1); PREDICE → latent regime (1); USA → Baum-Welch algorithm (1); APLICA_A → regime detection (1)

**data snooping** [riesgo_metodologico] (docs=9) [también: Data Snooping] — Sesgo introducido por el uso repetido de los mismos datos en múltiples pruebas. El paper señala que combina tres procesos: optimización de parámetros (overfitting), selección y rechazo de modelos (survivorship bias), y reutilización de datos (data-snooping bias).  
  Relaciones: CAUSA → backtest overfitting (3); SE_OPONE_A → walk-forward validation (2); MITIGA → false discovery rate (2); CAUSA → multiple testing (1); CAUSA → false discovery rate (1); MITIGA → out-of-sample testing (1); PARTE_DE → backtest overfitting (1)

**Monte Carlo simulation** [metodo] (docs=9) [también: Monte Carlo Simulation] — Técnica de simulación que genera miles de escenarios aleatorios para estimar distribuciones de pérdidas en carteras crediticias. Es el método no paramétrico preferido frente a enfoques de varianza-covarianza porque no asume normalidad y captura eventos de cola. Se integra con ...  
  Relaciones: APLICA_A → Value at Risk (2); SE_OPONE_A → backward Kolmogorov equation (1); APLICA_A → limit order book (1); APLICA_A → optimal execution (1); USA → risk-neutral valuation (1); SE_OPONE_A → Markovian Activation Function (1); MIDE → semi-classical approximation (1); MIDE → backtest overfitting (1)

**inventory risk** [concepto] (docs=9) [también: Inventory Risk] — Los dealers son inversores rentables de un día (short-sighted, CARA) que deben absorber el desequilibrio de order flow de sus clientes y son compensados con un cambio en el precio esperado; el canal de balance de portafolio surge de esta aversión al riesgo de inventario.  
  Relaciones: PARTE_DE → market making (3); CAUSA → market impact (1); CAUSA → Liquidity Commonality (1); MIDE → positioning profit (1); MITIGA → position sizing (1); CAUSA → price discovery (1)

**tick size** [concepto] (docs=9) [también: Tick Size] — Tamaño mínimo de variación de precio; el paper argumenta que un tick size grande motiva a los proveedores de liquidez a colocar órdenes más lejos del mercado, generando libros más convexos, y que el SET tiene un tick relativo mayor que otros mercados comparados.  
  Relaciones: PARTE_DE → limit order book (4); MITIGA → adverse selection (2); USA → order book profile (1); MITIGA → opportunistic algorithmic trading (1); MEJORA_A → investment-to-price sensitivity (1); CAUSA → high-frequency trading (1); CAUSA → order book convexity (1); PREDICE → order book convexity (1)

**spoofing** [estrategia] (docs=9) [también: Spoofing] — Estrategia de manipulación donde un trader envía órdenes límite falsas (spoof LOs) sin intención de ejecución para distorsionar el volume imbalance del LOB, creando una ilusión de presión compradora que mejora el precio de ejecución de sus ventas reales.  
  Relaciones: PARTE_DE → manipulative trading (1); PARTE_DE → Market Manipulation (1); CAUSA → bid-ask spread (1); CAUSA → adverse selection (1); USA → limit order book (1); USA → Volume Imbalance (1)

**intraday seasonality** [fenomeno] (docs=9) — Patrón en forma de U de las intensidades de órdenes a lo largo del día de trading: la actividad es máxima tras la subasta de apertura y antes de la de cierre, y mínima a mitad del día. Se modela multiplicando la intensidad Hawkes por un factor f(Q_t) constante por tramos de 30...  
  Relaciones: PARTE_DE → bid-ask spread (2); CAUSA → adverse selection (2); PARTE_DE → limit order book (2); APLICA_A → weighted microprice momentum (1); APLICA_A → Hawkes process (1)

**order flow** [concepto] (docs=8) [también: Order Flow] — Flujo de órdenes que llegan al mercado. Los autores distinguen entre liquidity offer (órdenes entrantes al libro) y liquidity consumption (ejecuciones y cancelaciones), y muestran empíricamente que ambos flujos tienen timing casi idéntico en la escala de milisegundos, haciendo...  
  Relaciones: PARTE_DE → limit order book (3); PREDICE → order aggressiveness (2); USA → market microstructure model (1); USA → Poisson Process (1); USA → diagonal effect (1); MIDE → informed trading (1); USA → Microstructure Tokenization (1); USA → execution rate (1)

**Kalman filter** [metodo] (docs=8) [también: Kalman Filter] — Filtro de Kalman aplicado a la estimación online del hedge ratio βt como estado latente que evoluciona como random walk. El hiperparámetro δ controla la velocidad de adaptación. El paper muestra que, en el período 2020-2024, produce spreads con un término de contaminación no e...  
  Relaciones: PARTE_DE → state space model (1); APLICA_A → breakout strategy (1); USA → Kyle model (1); APLICA_A → state space model (1); APLICA_A → state-space representation (1); MIDE → market impact (1); USA → state space model (1); MEJORA_A → cointegration (1)

**realized volatility** [metrica] (docs=8) [también: Realized Volatility] — Medida de la desviación estándar de los retornos intradía horarios. Se usa como variable explicativa en las regresiones de microestructura para predecir el residual de volatilidad. Computada como la raíz de la varianza de retornos horarios dentro de cada día de trading.  
  Relaciones: MIDE → volatility clustering (2); REQUIERE → tick data (1); MIDE → mid-price (1); USA → order book dynamics model (1); SE_OPONE_A → price clustering (1); MIDE → volatility (1); PARTE_DE → microstructure effects (1); CAUSA → liquidity provision (1)

**sentiment analysis** [metodo] (docs=8) [también: Sentiment analysis] — FinBERT y transformer-based models para extracción de sentimiento en tiempo real de earnings calls, noticias financieras y analyst reports. Parte del ecosistema de alternative data que extiende la ventaja informacional de participantes AI-enabled.  
  Relaciones: USA → NLP (2); PARTE_DE → algorithmic trading (1); USA → natural language processing (1); USA → VADER (1); PARTE_DE → composite score (1); APLICA_A → NLP (1); APLICA_A → algorithmic trading (1); USA → large language models (1)

**GARCH** [metodo] (docs=8) — Modelo de volatilidad condicional usado como baseline. Captura clustering de volatilidad pero asume estacionariedad y no detecta quiebres estructurales. En el paper, GARCH(1,1) sobre retornos por bucket de volumen produce señal de anomalía cuando el retorno excede 3 desviacion...  
  Relaciones: MIDE → volatility clustering (2); APLICA_A → volatility clustering (2); USA → leverage effect (1); PARTE_DE → benchmark comparison (1); SE_OPONE_A → kernel dimension reduction (1); CONTRADICE_A → regime switching (1); MIDE → market impact (1)

**Value at Risk** [metrica] (docs=8) [también: Value-at-Risk, value at risk, value-at-risk] — Medida probabilística de la pérdida máxima esperada en un horizonte temporal y nivel de confianza dados. En carteras de crédito, el VaR se cuantifica mediante simulaciones de pérdidas por default, movimientos de credit spreads y matrices de migración crediticia. Sus limitacion...  
  Relaciones: MIDE → tail risk (2); USA → GARCH (1); MIDE → Tail Dependence (1); MEJORA_A → Conditional Value-at-Risk (1); REQUIERE → Monte Carlo simulation (1); SE_OPONE_A → backtest overfitting (1)

**random forest** [metodo] (docs=7) — Ensemble de árboles de decisión modificado con división de nodos adaptativa que combina criterios CART e ID3 (Resilient Random Forest Classifier). El paper añade un mecanismo de mutación inspirado en el modelo Wild Horse para reemplazar clasificadores débiles.  
  Relaciones: USA → composite score (1); MIDE → feature importance (1); SE_OPONE_A → ARIMA (1); PREDICE → next-day return (1); USA → feature importance (1); MITIGA → backtest overfitting (1); PREDICE → critical edge (1); USA → gradient boosting (1)

**queue position** [concepto] (docs=7) — Prioridad temporal en el libro de órdenes: órdenes enviadas antes tienen prioridad sobre otras al mismo precio. Los traders enfrentan un trade-off entre cancelar una orden (perdiendo su posición en la cola y pagando una cancellation fee) y mantenerla (arriesgándose a ser picke...  
  Relaciones: PARTE_DE → limit order book (7); CAUSA → crowding out effect (2); PREDICE → direction of price moves (1); REQUIERE → order book depth (1); CAUSA → bid-ask spread (1); REQUIERE → liquidity provision (1)

**flash crash** [fenomeno] (docs=7) [también: Flash Crash] — Flash Crash del 6 de mayo de 2010 analizado como ejemplo de falla emergente: ningún sistema individual fue incorrectamente diseñado, pero el comportamiento colectivo produjo un colapso de ~1000 puntos en el Dow en 36 minutos.  
  Relaciones: CONTRADICE_A → high-frequency trading (1); CAUSA → high-frequency trading (1); CAUSA → Market Manipulation (1); CAUSA → algorithmic trading (1)

**Bid-Ask Bounce** [fenomeno] (docs=7) [también: bid-ask bounce] — Rebote de precio entre bid y ask que genera autocorrelación negativa en retornos de corto plazo cuando el spread es constante (Roll 1984); contrasta con el efecto de spreads en periodos más largos.  
  Relaciones: CAUSA → Roll model (1); PARTE_DE → market microstructure noise (1); MITIGA → realistic trading simulation (1); CAUSA → volatility (1); USA → HFT Sharpe Ratio (1); PARTE_DE → Market Microstructure Volatility Channel (1)

**optimal execution** [estrategia] (docs=6) [también: Optimal Execution] — Problema de control estocástico que modela el trade-off entre coste de ejecución y riesgo de precio al liquidar o adquirir una posición. El framework Almgren-Chriss proporciona una frontera eficiente explícita entre coste esperado y varianza del coste.  
  Relaciones: USA → market impact (2); REQUIERE → market impact (2); USA → limit order book (2); APLICA_A → algorithmic trading (1); USA → quadratic programming (1); REQUIERE → queue position (1); USA → Almgren-Chriss framework (1); MITIGA → transaction costs (1)

**order book depth** [concepto] (docs=6) — Cantidad de órdenes acumuladas en el libro. El modelo predice que tras el shock la profundidad es muy baja, luego crece progresivamente porque los vendedores colocan órdenes límite, y eventualmente disminuye por cancelaciones y ejecuciones. Este buildup en el lado ask ocurre p...  
  Relaciones: PARTE_DE → limit order book (6); REQUIERE → liquidity provision (1); PREDICE → ask price increase probability (1); MIDE → liquidity provision (1); MITIGA → market impact (1); APLICA_A → liquidity shock (1)

**large language models** [metodo] (docs=6) [también: Large Language Model, Large Language Models, Large Language Models (LLMs)] — Modelos de lenguaje a gran escala usados como 'psicohistoria financiera moderna' para procesar datos textuales no estructurados (noticias, earnings calls, filings) y extraer señales predictivas de volatilidad, momentum y sorpresas macroeconómicas.  
  Relaciones: APLICA_A → sentiment analysis (2); MEJORA_A → breakout strategy (1); APLICA_A → NLP (1); REQUIERE → walk-forward validation (1); USA → NLP (1); USA → sentiment analysis (1); USA → cross-attention (1)

**effective spread** [metrica] (docs=6) [también: Effective Spread] — Diferencia entre el precio al que un trader compra/vende y el valor fundamental reflejado por el midpoint. Cuantifica el costo real de ejecución incluyendo movimiento de precio e impacto de mercado.  
  Relaciones: MIDE → transaction costs (4); MEJORA_A → bid-ask spread (1); MIDE → market liquidity (1); PARTE_DE → Implementation Shortfall (1); MIDE → market impact (1)

**mid-price** [concepto] (docs=6) [también: Mid-Price, midpoint] — Promedio del bid y ask; en el modelo su dinámica queda determinada enteramente por el order flow en el tope del libro y la profundidad alrededor del midprice, con un coeficiente de impacto θ.  
  Relaciones: PARTE_DE → limit order book (2); USA → market depth (1); PARTE_DE → centred order book (1)

**ARIMA** [metodo] (docs=6) [también: ARMA] — Modelo estadístico autorregresivo de media móvil integrada con configuración p=5, d=1, q=0 usado como baseline de forecasting. Reentrenado diariamente. Predice peor que XGBoost la dirección del spread (~31% de acierto), resultando en pérdidas drásticas del 34,25% anual.  
  Relaciones: SE_OPONE_A → long short-term memory network (1); SE_OPONE_A → XGBoost (1); USA → walk-forward validation (1)

**LSTM** [metodo] (docs=6) — Red neuronal recurrente capaz de aprender dependencias de orden en secuencias reteniendo información pasada por periodos variables; aplicada tanto a predicción de mid-price en limit order books como a predicción de resultados deportivos.  
  Relaciones: USA → deep learning (2); APLICA_A → technical analysis (1); APLICA_A → limit order book (1); PARTE_DE → Recurrent Neural Network (1)

**out-of-sample testing** [metodo] (docs=6) [también: Out-sample testing, out-of-sample validation] — Condición exigida para que el veredicto final del proyecto no dependa solo de accuracy in-sample sino de un desempeño ajustado por riesgo consistente que pase pruebas fuera de muestra y regímenes de mercado cambiantes.  
  Relaciones: MITIGA → backtest overfitting (5); MITIGA → data snooping (2); MIDE → random forest (1)

**order-to-trade ratio** [metrica] (docs=6) [también: Order-to-Trade Ratio, Order-to-trade ratio, order to trade ratio] — Ratio regulatorio introducido por la ley que relaciona submissions, modificaciones y cancelaciones con transacciones ejecutadas. Los venues deben determinar este ratio individualmente y cobrar fees adicionales por comportamiento con volumen excesivo de mensajes.  
  Relaciones: MIDE → high-frequency trading (3); PARTE_DE → financial transaction tax (1); REQUIERE → German HFT Act (2013) (1)

**market efficiency** [concepto] (docs=5) [también: Market Efficiency] — Propiedad de un mercado donde los precios reflejan plena e instantáneamente toda la información disponible, implicando velocidades de ajuste unitarias (g=1) y proceso intrínseco random walk (γ=1). Los resultados muestran que los índices de gran capitalización en India se aprox...  
  Relaciones: MIDE → price discovery (2); PARTE_DE → market microstructure (1); SE_OPONE_A → high-frequency trading (1); MIDE → Intraday Return Predictability (1); MEJORA_A → algorithmic trading (1); SE_OPONE_A → thin trading (1); SE_OPONE_A → overreaction (1); REQUIERE → speed of adjustment (1)

**information asymmetry** [fenomeno] (docs=5) [también: Information Asymmetry] — Acceso desigual a información de mercado (precios en otros exchanges, pronósticos de demanda, datos meteorológicos, congestión de red) que otorga ventaja sistemática a utilities grandes con mejor forecasting frente a DISCOMs pequeños.  
  Relaciones: APLICA_A → informed trading (2); CAUSA → adverse selection (1); PARTE_DE → market microstructure model (1); CAUSA → bid-ask spread (1); CAUSA → statistical arbitrage (1); CAUSA → PIN (1); CAUSA → informed trading (1); USA → adverse selection (1)

**Revelatory Price Efficiency** [metrica] (docs=5) [también: Revelatory Price Efficiency (RPE), revelatory price efficiency, revelatory price efficiency (RPE)] — Grado en que los precios revelan información necesaria para que los tomadores de decisiones (managers) actúen, distinto de la eficiencia predictiva (forecasting price efficiency); concepto tomado de Bond et al. (2012). El paper muestra que AT contribuye positivamente a la RPE.  
  Relaciones: CAUSA → investment-to-price sensitivity (2); SE_OPONE_A → forecasting price efficiency (1); MIDE → price discovery (1)

**position sizing** [concepto] (docs=5) — El tamaño de posición se fija en una acción por operación para eliminar el compounding y así asegurar comparabilidad entre estrategias, lo cual limita la representatividad de los resultados frente a un uso realista de capital.  
  Relaciones: APLICA_A → algorithmic trading (1); USA → short-term alpha (1); PARTE_DE → optimal investment strategy (1); USA → Shannon entropy (1); USA → regime detection (1); PARTE_DE → reinforcement learning (1)

**efficient market hypothesis** [concepto] (docs=5) [también: Efficient Market Hypothesis] — Hipótesis de mercado eficiente mencionada como contrapunto: la teoría clásica sugiere que es imposible batir consistentemente al mercado sin riesgo adicional, pero los systematic traders intentan hacerlo usando análisis técnico y fundamental.  
  Relaciones: SE_OPONE_A → momentum (1); SE_OPONE_A → mean reversion (1); SE_OPONE_A → multifractal scaling (1); SE_OPONE_A → adaptive markets hypothesis (1); SE_OPONE_A → algorithmic trading (1)

**deep reinforcement learning** [metodo] (docs=5) [también: Deep Reinforcement Learning, Deep Reinforcement Learning (DRL)] — Paradigma que formula el trading como un proceso de decisión de Markov donde el agente observa el estado del mercado, ejecuta acciones (comprar/vender/mantener) y recibe recompensa según el desempeño del portafolio; aquí implementado con PPO, SAC y TD3.  
  Relaciones: PARTE_DE → reinforcement learning (1); USA → order flow imbalance (1); APLICA_A → high-frequency trading (1)

**implied volatility** [concepto] (docs=5) — Se deriva del marco de Black-Scholes como parámetro σ del movimiento browniano geométrico del subyacente. El paper no usa implied volatility extraída de opciones cotizadas sino que la modela teóricamente y la predice mediante microestructura del subyacente.  
  Relaciones: MIDE → option pricing expansion (1); USA → mixing representation (1); MITIGA → constant volatility (1); USA → Black-Scholes closed-form solution (1); SE_OPONE_A → distribution volatility (1); EQUIVALE_A → volatility (1)

**survivorship bias** [riesgo_metodologico] (docs=5) [también: Survivorship Bias] — Las bases de precios cripto actuales tienden a sobre-representar criptomonedas exitosas y omitir las desaparecidas, inflando los resultados de backtests; el paper lo ilustra con un ejemplo donde los sobrevivientes rinden +10% pero el universo completo -34%.  
  Relaciones: CAUSA → backtest overfitting (1); CONTRADICE_A → ETF-Based Universe (1)

**quote stuffing** [fenomeno] (docs=5) — Denominada 'order stuffing' por la CFTC, práctica considerada manipulativa o disruptiva que las pre-trade controls buscan mitigar mediante límites de tasa de mensajes.  
  Relaciones: PARTE_DE → manipulative trading (1); REQUIERE → latency (1)

**Kyle model** [metodo] (docs=4) [también: Kyle Model] — Modelo de trading estratégico con información asimétrica donde un dealer fija precios lineales de cero-profit y los informed traders optimizan su demanda de liquidez. El paper extiende FHR16 para tener dos tipos de informed traders distintos en vez de uno que puede ser fast o ...  
  Relaciones: APLICA_A → informed trading (2); PARTE_DE → market microstructure (1); SE_OPONE_A → Glosten-Milgrom model (1); APLICA_A → market making (1); USA → order flow imbalance (1); USA → Kalman filter (1); USA → market microstructure (1); APLICA_A → Market Manipulation (1)

**trading volume** [metrica] (docs=4) [también: Trading Volume] — Volumen de transacciones. El modelo predice que tras el shock, el volumen es inicialmente muy bajo, luego aumenta gradualmente hasta un máximo y después muere progresivamente (patrón hump-shaped). Con monitoreo imperfecto, el volumen es menor que en el equilibrio Walrasiano.  
  Relaciones: MIDE → central bank intervention (1); CAUSA → market liquidity (1); MIDE → limit order book (1); PREDICE → liquidity shock (1); PARTE_DE → trading activity (1); USA → betting volume (1); MIDE → market liquidity (1)

**Hawkes process** [metodo] (docs=4) — Proceso puntual autorregresivo donde la intensidad condicional λ(t) depende de eventos pasados a través de un kernel de autoexcitación ϕ, permitiendo descomponer el flujo de órdenes en componentes exógeno y endógeno. Herramienta central para modelar microestructura de mercado.  
  Relaciones: APLICA_A → limit order book (1); USA → Compound Hawkes Process (1); MEJORA_A → Poisson Process (1); APLICA_A → market microstructure (1); USA → trade sign (1)

**order aggressiveness** [concepto] (docs=4) [también: Order Aggressiveness] — Nivel de agresividad de una orden clasificado en 9 categorías (1-5 límite, 6-9 mercado) según precio y volumen relativo a la cola disponible en el libro; modelado con probit ordenado en función del spread, profundidad y volatilidad.  
  Relaciones: USA → ordered probit model (1); PREDICE → bid-ask spread (1); MIDE → limit order book (1); PREDICE → crowding out effect (1); USA → Limit Order Book State (1)

**technical analysis** [metodo] (docs=4) — Uso de datos históricos de precio y volumen para pronosticar movimientos futuros de precio; identificado como el marco de aplicación dominante entre 143 estudios revisados (2015-2023) sobre IA en trading financiero.  
  Relaciones: USA → random forest (1); REQUIERE → multiple time frame analysis (1); CAUSA → backtest overfitting (1); USA → Bollinger bands (1)

**clustering** [metodo] (docs=4) — Técnica de aprendizaje no supervisado que agrupa datos (acciones) en clusters según similitud, medida por una distancia. En este paper se usa como filtro inicial para seleccionar pares candidatos antes de tradear.  
  Relaciones: APLICA_A → correlation matrix (1); USA → Marchenko-Pastur distribution (1); USA → OPTICS (1); APLICA_A → pairs trading (1); REQUIERE → partial correlation (1)

**feature importance** [metrica] (docs=4) — Contribución relativa de cada variable (sentimiento, volatilidad, retorno, medias móviles, volumen, RSI) a la predicción del Random Forest; en el paper el sentimiento promedio resultó ser el factor más significativo.  
  Relaciones: MIDE → random forest (2); USA → gradient boosting (1); MIDE → SHAP (1)

**tail risk** [fenomeno] (docs=4) — Colas pesadas en retornos financieros ilustradas mediante QQ-plots de retornos t-Student vs normal: las colas se desvían sistemáticamente de la línea de 45°, indicando eventos extremos más frecuentes que lo predicho por Gaussianidad.  
  Relaciones: MITIGA → Walk-Forward Optimization (1); MIDE → Value at Risk (1); SE_OPONE_A → GARCH (1)

**systemic risk** [concepto] (docs=4) [también: Systemic Risk] — Riesgo de que la distress de varios bancos se propague por el sistema financiero afectando la viabilidad del sistema entero o de una parte significativa; el paper lo estudia vía contagio mediado por precios, no por obligaciones interbancarias directas.  
  Relaciones: CAUSA → price-mediated contagion (1); CAUSA → model reflexivity (1)

**Mean-Variance Optimization** [metodo] (docs=4) [también: mean-variance optimization] — Técnica fundacional de Markowitz que maximiza retorno esperado para un nivel dado de varianza. En carteras de préstamos su aplicación es limitada porque los retornos crediticios no son normales (son binarios: default o repago), presentan asimetría y curtosis, y las correlacion...  
  Relaciones: SE_OPONE_A → Stochastic Optimization (1); USA → Value at Risk (1); USA → Equilibrium Strategy (1); REQUIERE → Hamilton-Jacobi-Bellman equation (1); APLICA_A → Almgren-Chriss Model (1)

**stochastic volatility model** [concepto] (docs=4) [también: Heston Stochastic Volatility, Heston stochastic volatility model] — Familia de modelos donde la volatilidad es un proceso aleatorio propio; el paper señala que su distribución puede mapearse al modelo de volatilidad local, por lo que sus resultados también aplicarían a su calibración.  
  Relaciones: USA → jump-diffusion model (1); MEJORA_A → Black-Scholes-Merton model (1); MITIGA → constant volatility (1); EQUIVALE_A → local volatility model (1); MEJORA_A → Moneyness Scaling (1)

**liquidity taking** [concepto] (docs=4) — Estrategia por la cual un agente envía órdenes de mercado para ejecutar inmediatamente contra las órdenes límite existentes en el libro. Los HFT pueden usar órdenes de mercado para pickear órdenes límite desactualizadas de traders lentos cuando el valor fundamental se mueve en...  
  Relaciones: SE_OPONE_A → liquidity provision (3); PARTE_DE → high-frequency trading (1); CAUSA → adverse selection (1); USA → predatory trading (1)

**gradient boosting** [metodo] (docs=4) — Técnica de ensemble learning basada en árboles de decisión que construye modelos secuencialmente corrigiendo errores residuales. El paper cita a Krauss et al. (2017) para justificar que los frameworks basados en árboles producen resultados superiores a redes neuronales en stat...  
  Relaciones: USA → random forest (1); APLICA_A → XGBoost (1); USA → statistical arbitrage (1); EQUIVALE_A → random forest (1)

**Hurst exponent** [metrica] (docs=4) — Exponente característico que relaciona las autocorrelaciones de una serie con su comportamiento de escalamiento; el paper reporta que en series financieras es estocástico y cambia en el tiempo, con saltos abruptos asociados a crisis.  
  Relaciones: MIDE → mean reversion (1); MIDE → long range dependence (1); PARTE_DE → multifractal scaling (1); MIDE → regime detection (1); APLICA_A → position sizing (1); MIDE → rough volatility (1)

**Kyle lambda** [metrica] (docs=4) — Parámetro de price impact lineal, denotado λ(t), que mide cuánto se mueve el precio por cada acción negociada. En el modelo estructural se define como λ(t) · Q̃(t) como el ajuste de precio que los market makers aplican para break-even ante selección adversa. El paper deriva λ(...  
  Relaciones: MIDE → market impact (3); PARTE_DE → Kyle model (1); MIDE → market liquidity (1); USA → transaction costs (1); REQUIERE → trading volume (1)

**market fragmentation** [fenomeno] (docs=4) — Existencia de múltiples venues de trading para un mismo activo. El mercado brasileño es interesante porque tiene un único venue para equities, eliminando las estrategias de arbitraje de latencia entre venues que la literatura asocia con la rentabilidad de HFT en mercados desar...  
  Relaciones: CAUSA → high-frequency trading (1); REQUIERE → market making (1); CAUSA → bid-ask spread (1); CAUSA → transaction costs (1); SE_OPONE_A → high-frequency trading (1); APLICA_A → market liquidity (1)

**probability of informed trading** [metrica] (docs=4) [también: Probability of Informed Trading, Probability of Informed Trading (PIN), Probability of informed trading (PIN)] — Medida de información asimétrica que estima la fracción de trades originados por traders informados en un intervalo, inferida de datos de dirección de trade y duración entre trades mediante modelo estructural de mezcla de Poisson.  
  Relaciones: EQUIVALE_A → PIN (2); PREDICE → bid-ask spread (1); USA → informed trading (1); MIDE → information asymmetry (1); REQUIERE → PIN-AACD Model (1)

**tick data** [dato] (docs=4) — Datos de mercado a nivel de transacción individual e incrementos de milisegundos, los cuales requieren métodos estadísticos robustos (OLS) frente a la falta de normalidad de sus distribuciones de precio.  
  Relaciones: USA → vector-autoregressive model (1); PARTE_DE → limit order book (1)

**Granger causality** [metodo] (docs=4) [también: Granger Causality] — Test estadístico para determinar si los valores pasados de una variable ayudan a predecir otra. Se aplica en un VAR(20) bivariado para cada acción, testeando si el AT rezagado causa (en sentido Granger) cambios en las medidas de liquidez y viceversa. Encuentra causalidad bidir...  
  Relaciones: APLICA_A → VPIN (1); USA → VAR model (1); MIDE → market liquidity (1); USA → Vector Autoregression (VAR) (1)

**half-life** [metrica] (docs=4) [también: Half-Life] — Medida de la velocidad de reversión a la media de un proceso autorregresivo; en este contexto indica el número de días que tarda la divergencia de precios en reducirse a la mitad. Se encontró un promedio de dos días para pares cointegrados.  
  Relaciones: MIDE → mean reversion (4); PARTE_DE → Ornstein-Uhlenbeck process (2); PARTE_DE → multi-objective optimization (1); USA → cointegration (1)

**machine learning** [metodo] (docs=4) [también: Machine learning] — AI como herramienta complementaria al analista humano: eficiente en predicción pero carece de comprensión contextual, consideraciones éticas y accountability. El paper argumenta que AI no reemplaza sino que colabora con analistas.  
  Relaciones: APLICA_A → algorithmic trading (3); USA → backtest overfitting (1)

**Implementation Shortfall** [metrica] (docs=4) [también: implementation shortfall] — Diferencia entre el precio de decisión y el precio final de ejecución, usada como base de la función de recompensa del EOA. Incluye costos de spread, impacto de mercado, timing y costo de oportunidad.  
  Relaciones: MIDE → transaction costs (1); MIDE → institutional trading costs (1)

**Amihud illiquidity** [metrica] (docs=4) — Proxy de impacto de precio de alta frecuencia: valor absoluto del retorno logarítmico dividido por el volumen negociado en el intervalo t de 1 minuto. Mide cuánto mueve el precio cada unidad de volumen.  
  Relaciones: MIDE → market impact (3); MIDE → market liquidity (1)

**Avellaneda-Stoikov model** [estrategia] (docs=4) [también: Avellaneda-Stoikov Model] — Modelo de referencia para market making usado como baseline. El paper extiende este modelo incorporando ambigüedad sobre las intensidades de llegada de órdenes de mercado y la probabilidad de ejecución de limit orders.  
  Relaciones: APLICA_A → market making (4); USA → stochastic optimal control (1); SE_OPONE_A → multivariate Hawkes process (1)

**Kyle Model Extension** [metodo] (docs=4) [también: Kyle (1985) Model Extension, Kyle model extension] — Extensión del modelo de Kyle (1985) a dos activos riesgosos correlacionados con un insider por firma, un market maker competitivo por activo, y noise traders exógenos. Se analiza bajo dos regímenes de información del market maker: opaco (solo ve su propio order flow) y transpa...  
  Relaciones: APLICA_A → adverse selection (1); APLICA_A → market microstructure (1)

**Sortino ratio** [metrica] (docs=4) — Variante del Sharpe ratio que penaliza solo la volatilidad a la baja; el paper muestra que sufre una anomalía análoga a la del Sharpe ratio bajo ciertas secuencias de retornos.  
  Relaciones: EQUIVALE_A → Sharpe ratio (1); MEJORA_A → Sharpe ratio (1)

**RSI (Relative Strength Index)** [metrica] (docs=4) [también: Relative Strength Index (RSI), relative strength index] — Oscilador de fuerza que evalúa el momentum actual: RSI_t = 100 - 100/(1+RS_t) donde RS_t = EMA_n(U)/EMA_n(D), con n usualmente 14. Valores superiores a 70 indican sobrecompra y señales de venta; inferiores a 30 indican sobreventa y señales de compra.  
  Relaciones: PARTE_DE → feature importance (1); PARTE_DE → technical analysis (1)

**Market Manipulation** [fenomeno] (docs=3) [también: market manipulation] — Prácticas abusivas en mercados electrónicos que incluyen front-running (anticiparse a órdenes de clientes), spoofing (colocar y cancelar órdenes para crear impresión falsa de liquidez) y layering (múltiples capas de órdenes falsas).  
  Relaciones: PARTE_DE → high-frequency trading (1); USA → spoofing (1); USA → Manipulative Demand (1); CONTRADICE_A → arbitrage (1); USA → algorithmic trading (1)

**local volatility model** [metodo] (docs=3) — Extensión donde la volatilidad es función determinista del precio del subyacente y del tiempo, calibrada con datos de mercado para dar pricing más preciso que el supuesto de volatilidad constante.  
  Relaciones: APLICA_A → implied volatility surface (1); REQUIERE → no-arbitrage conditions (1); MEJORA_A → Black-Scholes-Merton model (1); REQUIERE → Dupire formula (1); EQUIVALE_A → stochastic volatility model (1); APLICA_A → volatility skew (1)

**Liquidity Commonality** [fenomeno] (docs=3) [también: liquidity commonality] — Comovimiento de la liquidez (spreads, depth) entre distintas acciones; el paper muestra que ha crecido en la última década y que el algorithmic trading explica parte de ese crecimiento.  
  Relaciones: MIDE → liquidity risk (1); CAUSA → liquidity risk (1); USA → bid-ask spread (1); CAUSA → Cross-Asset Lead-Lag (1)

**Stochastic Control** [metodo] (docs=3) [también: stochastic control] — Marco matemático usado para resolver el problema de mezcla óptima de órdenes limit/market bajo un prior dinámico sobre el precio futuro; el paper afirma ser el primero en incorporar aprendizaje dinámico bajo este marco en trading algorítmico.  
  Relaciones: PARTE_DE → optimal execution (1); APLICA_A → optimal execution (1); USA → Hamilton-Jacobi-Bellman equation (1); USA → Ornstein-Uhlenbeck process (1); APLICA_A → pairs trading (1)

**lead-lag effect** [fenomeno] (docs=3) — Fenómeno por el cual los rendimientos de índices de gran capitalización anticipan temporalmente los movimientos de los índices de pequeña capitalización. Se manifiesta como correlación cruzada asimétrica donde la correlación líder (lead) supera a la rezagada (lag).  
  Relaciones: MIDE → price synchronization (1); CAUSA → thin trading (1); CAUSA → speed of adjustment (1); USA → Market Capitalization (1)

**autocorrelation** [metrica] (docs=3) — Correlación serial de retornos. El paper documenta que la autocorrelación rolling de 252 días de los retornos simples diarios del S&P 500 fue positiva y significativa de 1950 a 1997, pero se volvió no significativa y mayormente negativa después de 1997, causando el fracaso de ...  
  Relaciones: MIDE → institution level order flow (1); PREDICE → momentum (1); CAUSA → changing market conditions (1); MIDE → market efficiency (1); USA → cross-correlation (1); CAUSA → lead-lag effect (1)

**Hamilton-Jacobi-Bellman equation** [metodo] (docs=3) [también: Hamilton-Jacobi-Bellman (HJB) equation, Hamilton-Jacobi-Bellman Equation] — Ecuación HJB usada para resolver los problemas de control estocástico robusto. La versión con ambigüedad incluye un término de penalización que penaliza medidas alternativas proporcionalmente a su entropía relativa respecto a la medida de referencia.  
  Relaciones: USA → stochastic optimal control (1); APLICA_A → optimal execution (1); PARTE_DE → Stochastic Control (1); USA → inventory penalty (1)

**Engle-Granger Procedure** [metodo] (docs=3) [también: Engle-Granger procedure] — Procedimiento de dos pasos: primero regresión OLS entre logs de precios para obtener el residuo, luego test de raíz unitaria sobre el residuo para determinar si hay reversión a la media (coeficiente rho).  
  Relaciones: PARTE_DE → cointegration (1); USA → Dickey-Fuller test (1); USA → cointegration (1); APLICA_A → cointegration (1); MEJORA_A → distance method (1)

**order size distribution** [dato] (docs=3) — Distribución del tamaño de las órdenes (aproximadamente bets). El paper encuentra que la distribución de tamaños de órdenes de portfolio transition, ajustadas por actividad de trading, es log-normal con media logarítmica -5.71 y varianza logarítmica 2.53. Esto implica colas mu...  
  Relaciones: USA → order flow (1); PARTE_DE → limit order book (1); APLICA_A → Compound Hawkes Process (1); PARTE_DE → market microstructure invariants (1); USA → betting volume (1); PREDICE → transaction costs (1)

**first-passage time** [metrica] (docs=3) [también: First-Passage Time] — Tiempo aleatorio que tarda el proceso en alcanzar una barrera dada; el paper enmarca la duración del trade (T1, T2) en términos de first-passage times independientes del proceso OU para derivar media y varianza de la duración del trade.  
  Relaciones: MIDE → trade cycle length (1); PARTE_DE → non-stationary model for statistical arbitrage trading (1); MIDE → trade length (1); USA → Ornstein-Uhlenbeck process (1); MIDE → statistical arbitrage (1)

**trade sign** [metodo] (docs=3) — Signo del trade determinado comparando el precio de ejecución con el mid-quote: positivo si precio > mid (compra), negativo si precio < mid (venta), usado en la fórmula del OFI ajustado.  
  Relaciones: USA → tick data (2); PARTE_DE → execution momentum (1); PARTE_DE → order flow imbalance (1); USA → Lee-Ready Algorithm (1)

**latency arbitrage** [estrategia] (docs=3) — Estrategia oportunista de AT que explota cotizaciones desactualizadas ('stale quotes') detectadas cuando el salto del mid-price entre t-1 y t excede el half-spread; medida como LAO (número de oportunidades) siguiendo la metodología de Budish et al. (2015).  
  Relaciones: PARTE_DE → opportunistic algorithmic trading (1); SE_OPONE_A → market making (1); CAUSA → investment-to-price sensitivity (1); EQUIVALE_A → maximal extractable value (1); PARTE_DE → high-frequency trading (1)

**principal component analysis** [metodo] (docs=3) [también: Principal Component Analysis, principal components analysis] — Técnica usada sobre los spreads estandarizados de las 30 acciones del Dow Jones para estimar qué fracción de la variación total es explicada por factores comunes de liquidez, mostrando su crecimiento en el tiempo.  
  Relaciones: MIDE → Liquidity Commonality (1); USA → eigenportfolio (1); USA → Volume Decomposition (1); APLICA_A → Intraday Volume (1)

**volatility skew** [fenomeno] (docs=3) — Asimetría negativa observada empíricamente en la superficie de volatilidad de acciones, que el modelo captura permitiendo saltos en la varianza total y un parámetro de skewness negativo.  
  Relaciones: CAUSA → implied volatility (1); SE_OPONE_A → volatility of variance smile (1); CAUSA → local volatility model (1); PARTE_DE → implied volatility surface (1)

**delta hedging** [metodo] (docs=3) — Argumento de cobertura que consiste en tomar una posición corta de ∆=∂V/∂S unidades del subyacente para eliminar la exposición de primer orden al movimiento del precio y construir un portafolio libre de riesgo.  
  Relaciones: USA → least-squares Monte Carlo (1); REQUIERE → funding risk (1); USA → Black-Scholes PDE (1); REQUIERE → continuous hedging (1)

**Brownian motion** [concepto] (docs=3) — Límite de difusión para las colas best bid y best ask: convergen a una Brownian motion bidimensional con drift y matriz de covarianza explícitamente dadas en términos de las estadísticas de tamaños e intensidades de órdenes.  
  Relaciones: PARTE_DE → local volatility model (1); USA → path integral (1); PARTE_DE → limit order book (1); APLICA_A → stochastic calculus (1); PARTE_DE → LLM-driven drift SDE (1)

**insider trading** [fenomeno] (docs=3) — Trading realizado por insiders con información privada sobre la empresa. El paper usa datos de insider trading ilegal en China para estimar PIN, aprovechando que la prohibición de short-selling implica que solo información positiva es explotable (alpha=1, delta=0).  
  Relaciones: EQUIVALE_A → informed trading (1); REQUIERE → PIN (1); PARTE_DE → Market Manipulation (1); CAUSA → information asymmetry (1)

**Almgren-Chriss framework** [metodo] (docs=3) — Marco clásico de ejecución óptima con impacto temporal y permanente; la estrategia POCV óptima tiene su forma (senos hiperbólicos en el tiempo restante) más correcciones por order-flow futuro esperado.  
  Relaciones: APLICA_A → optimal execution (2); USA → optimal execution (1); MIDE → market impact (1); APLICA_A → market making (1)

**geometric Brownian motion** [concepto] (docs=3) — Proceso estocástico usado como supuesto dinámico del precio del subyacente en BSM; el precio evoluciona con drift y volatilidad proporcionales al nivel actual, generando una distribución lognormal.  
  Relaciones: CONTRADICE_A → volatility clustering (1); PARTE_DE → Black-Scholes-Merton model (1); USA → Wiener process (1)

**Augmented Dickey-Fuller Test** [metodo] (docs=3) [también: Augmented Dickey-Fuller test] — Test de raíz unitaria usado para determinar si una serie temporal es no estacionaria, aplicado tanto a las series individuales como a los residuos de la regresión de cointegración.  
  Relaciones: REQUIERE → cointegration (2); PARTE_DE → Engle-Granger test (1)

**back running** [estrategia] (docs=3) [también: Back Running, back-running] — Estrategia de trading predatoria donde un trader anticipa que una institución (víctima) necesita construir una posición, tomando posiciones anticipadas en la misma dirección para forzar a la institución a pagar un precio más alto.  
  Relaciones: PARTE_DE → algorithmic trading deters information acquisition (1); APLICA_A → informed trading (1); REQUIERE → informed trading (1); CAUSA → market impact (1); CONTRADICE_A → liquidity provision (1)

**quoted spread** [metrica] (docs=3) [también: Quoted Spread] — Diferencia entre el mejor bid y el mejor ask (dólar o proporcional); usada como proxy de liquidez en frecuencia intradía porque medidas como Amihud o Kyle's lambda generan demasiado ruido a 5 minutos.  
  Relaciones: MIDE → Liquidity Commonality (1); MEJORA_A → Amihud illiquidity (1); MIDE → Market Quality (1); EQUIVALE_A → bid-ask spread (1)

**spread** [concepto] (docs=3) — El residual de volatilidad Volϵt = σt − ςt es el spread entre las volatilidades de los dos subyacentes. Constituye la variable objetivo a predecir y sobre la que se construye la estrategia: si se espera que disminuya (Et[Volϵt+1] < 0), se compra call de S y se vende call de Z,...  
  Relaciones: PARTE_DE → pairs trading (2); MIDE → mean reversion (1); USA → cointegration (1); MIDE → cointegration (1); MIDE → volatility (1)

**state space model** [metodo] (docs=3) — Formulación estado-espacio del Kalman filter para pairs trading: ecuación de observación log At = βt·log Bt + εt, ecuación de estado βt = βt-1 + ηt. El estado βt y su varianza posterior Pt se actualizan secuencialmente.  
  Relaciones: USA → Kalman filter (2); PARTE_DE → Kyle model (1); APLICA_A → pairs trading (1)

**risk aversion parameter** [concepto] (docs=3) [también: Risk Aversion Parameter (γ)] — Parámetro lambda que controla el balance entre impacto esperado y varianza del costo en la función objetivo; también llamado nivel de urgencia. En cartera, no puede ser un único valor universal sin distorsionar los cronogramas óptimos de activos no correlacionados.  
  Relaciones: PARTE_DE → CARA exponential utility market making model (1); MEJORA_A → VWAP (1); USA → efficient frontier (1); PARTE_DE → Mean-Variance Optimization (1)

**Trading Frequency** [metrica] (docs=3) [también: trading frequency] — Cantidad de trades por unidad de tiempo (1/T), tratada como un proceso de renovación; su comportamiento no lineal respecto a los niveles de entrada/salida influye fuertemente en la rentabilidad de la estrategia pese a que el retorno por trade es lineal.  
  Relaciones: CAUSA → expected return (1); USA → trade length (1)

**Conditional Value-at-Risk** [metrica] (docs=3) [también: CVaR (Conditional Value at Risk), Conditional Value at Risk (CVaR)] — Medida de riesgo coherente, también llamada expected shortfall, que captura la pérdida promedio más allá del umbral del VaR. A diferencia del VaR, el CVaR es subaditivo y sensible al riesgo de cola, lo que lo hace preferible para optimización de carteras crediticias donde las ...  
  Relaciones: MIDE → tail risk (2); MEJORA_A → Value at Risk (1); MIDE → Tail Dependence (1); APLICA_A → Stochastic Optimization (1)

**Volume Weighted Average Price (VWAP)** [metrica] (docs=3) [también: Volume Weighted Average Price] — Precio promedio ponderado por volumen de todas las transacciones en una sesión. Funciona como ancla de fair value institucional: cuando el precio se desvía significativamente, las órdenes algorítmicas VWAP-targeting crean una fuerza restauradora.  
  Relaciones: REQUIERE → Intraday Volume (1); REQUIERE → Relative Volume Process (1); CAUSA → mean reversion (1)

**wash trading** [fenomeno] (docs=3) [también: Wash Trading] — Manipulación de mercado que consiste en generar un gran volumen de transacciones artificiales con cuatro motivos principales: market making (inflar precio de un activo), rate making (aumentar valor del artista), incentivizing (aprovechar recompensas por trade) y project promot...  
  Relaciones: PARTE_DE → manipulative trading (1); CAUSA → Market Manipulation (1); MITIGA → due diligence (1)

**crowding out effect** [concepto] (docs=3) [también: Crowding Out Effect] — Mecanismo de Parlour (1998) por el cual una cola larga del mismo lado del book reduce la probabilidad de ejecución, empujando a los traders a competir con órdenes más agresivas; el paper lo usa para explicar la relación positiva entre profundidad del mismo lado y agresividad.  
  Relaciones: CAUSA → order aggressiveness (2); PARTE_DE → order flow (1); PARTE_DE → market depth (1)

**frequent batch auction** [metodo] (docs=3) [también: Frequent Batch Auction (FBA)] — Mecanismo de subasta frecuente por lotes introducido por Budish et al. (2014, 2015) que transforma la competencia por velocidad en competencia por precio, eliminando oportunidades de arbitraje libre de riesgo entre HFTs.  
  Relaciones: MITIGA → high-frequency trading (1); MITIGA → aggressive-side order anticipation (1); EQUIVALE_A → Batch Trading Mechanism (1)

**MiFID II** [concepto] (docs=3) — Directiva europea (2014/65/EU) que regula los mercados de instrumentos financieros, introduciendo por primera vez definiciones y supervisión específica para algorithmic trading, high-frequency trading y direct electronic access, efectiva desde enero 2018.  
  Relaciones: APLICA_A → high-frequency trading (3); MITIGA → Market Manipulation (2); APLICA_A → algorithmic trading (1)

**Relative Spread** [metrica] (docs=3) [también: Relative spread] — Proxy de liquidez ex ante definido como (ask - bid) / midpoint. Junto con el effective spread, realized spread, dispersion y slope del order book, constituye el conjunto de métricas usadas para evaluar el impacto del análisis técnico sobre la calidad de mercado.  
  Relaciones: SE_OPONE_A → informed trading (1); MIDE → trading cost (1); MIDE → market liquidity (1)

**trend following** [estrategia] (docs=3) — Sistema de trend following combinado con pairs trading para mejorar puntos de entrada: se espera a que el spread forme una tendencia antes de abrir posiciones de pairs trading.  
  Relaciones: USA → time-series momentum (1); PARTE_DE → quantitative trading (1); MEJORA_A → pairs trading (1)

**order book imbalance** [metrica] (docs=3) [también: Order Book Imbalance, Order Book Imbalance (OBI)] — Diferencia normalizada entre cantidades bid y ask al mejor nivel del libro. Señal de microestructura que indica presión compradora (OBI > threshold) o vendedora (OBI < −threshold) con decaimiento rápido.  
  Relaciones: PARTE_DE → limit order book (1); EQUIVALE_A → order flow imbalance (1)

**dark pool** [concepto] (docs=3) [también: Dark pools] — Plataforma de trading que opera fuera de los mercados centrales para que otros mercados no vean grandes operaciones en bloque, evitando shocks de precio; IEX es descrita como dark pool a pesar de presentarse como solución anti-HFT.  
  Relaciones: PARTE_DE → block trading (1); PARTE_DE → market microstructure (1); CAUSA → information asymmetry (1)

**Roll measure** [metrica] (docs=3) [también: Roll Measure] — Medida de liquidez de mercado inferida de la covarianza de cambios sucesivos de precio. Cuantifica el bid-ask spread efectivo: Roll_t = 2 * sqrt(−cov(ΔP_t, ΔP_{t−1})). El signo negativo revierte la covarianza típicamente negativa causada por el bid-ask bounce.  
  Relaciones: MIDE → bid-ask spread (1); MIDE → Bid-Ask Bounce (1); PARTE_DE → microstructure effects (1)

**PCA** [metodo] (docs=3) — Principal Component Analysis para extraer factores latentes de una gran panel de retornos. IPCA (Instrumented PCA) extiende PCA permitiendo que las loadings sean funciones de características de firms. El paper encuentra que 5 factores IPCA producen Sharpe 4.2; más factores tie...  
  Relaciones: PARTE_DE → asset pricing (1); USA → statistical arbitrage (1); MITIGA → backtest overfitting (1)

**PPO** [metodo] (docs=3) — Proximal Policy Optimization, algoritmo actor-crítico que optimiza políticas de trading con restricciones de confianza para estabilidad. Incluido en la capa de agentes de FinRL.  
  Relaciones: PARTE_DE → reinforcement learning (1); SE_OPONE_A → GRPO (1)

**Calmar ratio** [metrica] (docs=3) — Métrica de retorno ajustado por riesgo que relaciona el retorno anualizado con el máximo drawdown; en el estudio mejora sustancialmente con selección dinámica de pares.  
  Relaciones: USA → maximum drawdown (1); MIDE → maximum drawdown (1)

**Viterbi algorithm** [metodo] (docs=3) — Algoritmo de decoding usado para inferir la secuencia más probable de estados calm/turbulent durante el período OOS. El paper usa Viterbi global (batch) en vez de online filtering, introduciendo un look-ahead limitado dentro de la ventana OOS.  
  Relaciones: USA → hidden Markov model (3); APLICA_A → regime detection (1)

**co-location** [concepto] (docs=3) [también: Co-location] — Servicio ofrecido por las bolsas que permite a traders ubicar físicamente sus servidores dentro de las instalaciones del exchange para reducir latencia. No es un buen proxy del inicio de HFT; más bien es una consecuencia de la demanda de HFT por mayor velocidad.  
  Relaciones: REQUIERE → high-frequency trading (1); APLICA_A → algorithmic trading (1); PARTE_DE → high-frequency trading (1)

**Front-Running** [fenomeno] (docs=3) [también: front running] — Práctica donde un intermediario ejecuta órdenes por cuenta propia antes de ejecutar las de sus clientes, aprovechando el conocimiento anticipado del flujo de órdenes. La tesis lo discute en el contexto de dark pools y HFT.  
  Relaciones: PARTE_DE → Market Manipulation (2); CAUSA → adverse selection (1); USA → high-frequency trading (1)

**RSI** [metrica] (docs=3) — Relative Strength Index de 14 períodos usado como baseline de comparación para el PJI; también se usa en el algoritmo 'Maceta RSI' que detecta inflecciones en U e inverted-U de la serie RSI para anticipar agotamiento de momentum.  
  Relaciones: PARTE_DE → technical analysis (2); MIDE → momentum (1)

**Volume-Synchronized Probability of Informed Trading (VPIN)** [metrica] (docs=3) [también: Volume-Synchronized Probability of Informed Trading] — Métrica de toxicidad de flujo que mide el imbalance de volumen bid-ask en buckets de volumen fijo sincronizados. Valores altos indican mayor probabilidad de trading informado/asimétrico. En crypto alcanza niveles elevados relativos a equities/futuros.  
  Relaciones: MIDE → informed trading (1); PREDICE → volatility (1)

**Statistical limit to arbitrage** [fenomeno] (docs=3) — Limitación que surge cuando arbitrajistas deben aprender alphas de datos históricos en entornos high-dimensional. Con alphas débiles y raros, incluso técnicas óptimas de machine learning no logran explotar todos los verdaderos errores de pricing, ampliando los límites de equil...

**Feasible vs infeasible Sharpe ratio** [metrica] (docs=3) — Divergencia entre el Sharpe ratio óptimo alcanzable por cualquier estrategia de arbitraje factible (que debe aprender alphas de datos) y el Sharpe ratio teórico máximo bajo conocimiento perfecto de alphas (inalcanzable). Esta brecha representa el costo del statistical learning...

**volatility** [metrica] (docs=2) — La volatilidad es la variable central que impulsa la rentabilidad de la estrategia de pairs de opciones. El valor del portfolio π crece con la volatilidad σ del activo S y decrece con la volatilidad ς del activo Z. Los autores modelan la volatilidad como range volatility diari...  
  Relaciones: MIDE → range volatility (1); PARTE_DE → realized volatility (1)

**adversarial attack** [riesgo_metodologico] (docs=2) — Perturbaciones deliberadamente diseñadas sobre el estado observado por el agente DRL para manipular sus predicciones/decisiones de trading, con potencial de pérdidas catastróficas en milisegundos.  
  Relaciones: CAUSA → trading performance degradation (1); APLICA_A → deep reinforcement learning (1); CAUSA → flash crash (1); MITIGA → adversarial training (1)

**informational efficiency** [metrica] (docs=2) — Medida de la cantidad mínima de información que un mecanismo descentralizado debe comunicar para implementar una asignación Pareto-eficiente. Se operacionaliza como el número de dimensiones del espacio de mensajes (message space) del mecanismo, siguiendo la tradición de Mount ...  
  Relaciones: MEJORA_A → high-frequency trading (1); MEJORA_A → free-riding (1); MIDE → message space dimensionality (1); PREDICE → competitive allocation mechanism (1)

**reference-day risk** [riesgo_metodologico] (docs=2) — Riesgo de estimación que surge porque la elección del día inicial (dentro del mes) usado para construir la serie de retornos mensuales genera variaciones grandes en los retornos, varianzas y betas estimados de una acción.  
  Relaciones: CAUSA → beta instability (2); MITIGA → VWAP beta (2); PARTE_DE → backtest overfitting (1)

**Market Quality** [concepto] (docs=2) — Calidad de mercado definida en términos de liquidez bursátil, volatilidad de precios e impacto de precio. Una mayor calidad implica menor spread, menor volatilidad y menor impacto de precio.  
  Relaciones: USA → Relative Quoted Spread (1); USA → Quoted Dollar Depth (1); USA → quoted spread (1); USA → effective spread (1)

**Tail Dependence** [fenomeno] (docs=2) — Fenómeno por el cual pérdidas extremas tienden a ocurrir simultáneamente en múltiples activos o prestatarios, especialmente durante crisis financieras. La correlación de Pearson es insuficiente para capturarlo, como se evidenció en la crisis de 2007-2008. Se modela mediante có...  
  Relaciones: MIDE → Copula Dependency Modeling (1); CAUSA → Model Misspecification Risk (1); MITIGA → stress testing (1); APLICA_A → cointegration (1)

**thin trading** [fenomeno] (docs=2) — Fenómeno microestructural por el cual ciertos activos no negocian en todos los períodos, generando que los precios observados reflejen información con retraso respecto a los precios verdaderos. Es más prevalente en acciones de baja capitalización y en mercados emergentes.  
  Relaciones: CAUSA → beta instability (1); PARTE_DE → market microstructure (1); CAUSA → lead-lag effect (1); CAUSA → autocorrelation (1); SE_OPONE_A → market efficiency (1)

**regime detection** [metodo] (docs=2) — Inferencia de estados latentes del mercado (pasivo, acumulación, distribución, vacío de liquidez) a partir de datos de order flow; los regímenes se usan luego como overlay para filtrado de señales y dimensionamiento de posición.  
  Relaciones: USA → order flow imbalance (2); USA → hidden Markov model (1); APLICA_A → position sizing (1); USA → VWAP (1)

**deep learning** [metodo] (docs=2) — Redes neuronales usadas en tres etapas: (1) autoencoder/IPCA para factores, (2) conv-transformer para señal temporal, (3) feedforward NN para política de asignación. Todo optimizado end-to-end sobre el objetivo de trading (Sharpe), no sobre MSE de predicción.  
  Relaciones: USA → convolutional transformer (1); APLICA_A → statistical arbitrage (1); APLICA_A → option pricing (1); APLICA_A → asset pricing (1); REQUIERE → no-arbitrage pricing (1)

**central bank intervention** [fenomeno] (docs=2) [también: Central bank FX intervention] — Operaciones de compra/venta de divisas por bancos centrales del G-3 (Fed, Bundesbank, BOJ) para influir en niveles y varianza de tipos de cambio. La Fed intervino 273 días entre 1987-1995. Aunque oficialmente anónimas, los bancos centrales informan al mercado vía dealers en mi...  
  Relaciones: CAUSA → exchange rate volatility (1); CAUSA → trading volume (1); APLICA_A → order flow (1); USA → portfolio-balance channel (1)

**VWAP beta** [metodo] (docs=2) — Estimación de beta obtenida reemplazando el precio de cierre mensual por un VWAP ex-ante de 60 días antes de correr la regresión de retornos del activo contra el mercado, propuesta como alternativa independiente del día de referencia.  
  Relaciones: MITIGA → reference-day risk (2); USA → VWAP (2); SE_OPONE_A → standard beta (1); MEJORA_A → standard beta (1)

**informational gap** [concepto] (docs=2) [también: Informational Gap] — Brecha estructural donde el mercado (vía microestructura) integra información antes de que esté reflejada en el consenso público. Su firma empírica es P(|rt+∆t|>kσ | D(t)>τ) ≫ P(|rt+∆t|>kσ).  
  Relaciones: MIDE → standardized price jump (1); CAUSA → algorithmic trading withdrawal (1); MIDE → Informational Divergence Metric D(t) (1)

**Compound Hawkes Process** [metodo] (docs=2) — Extensión del Proceso de Hawkes estándar donde cada evento de llegada incluye un tamaño de salto (orden) muestreado de una distribución calibrada, modelando de manera conjunta los tiempos de inter-llegada y los tamaños de las órdenes.  
  Relaciones: APLICA_A → limit order book (2); USA → Hawkes process (1); MEJORA_A → Poisson Process (1); MEJORA_A → Hawkes process (1)

**exchange rate volatility** [metrica] (docs=2) — Desviación estándar incondicional de la variación del spot rate; el paper muestra que su respuesta a la intervención depende de la ruta elegida (directa vs indirecta) y no es necesariamente monótona en la intensidad de intervención.  
  Relaciones: MIDE → central bank intervention (1); SE_OPONE_A → market liquidity (1); CAUSA → administered pricing (1)

**investment-to-price sensitivity** [concepto] (docs=2) — Sensibilidad de la inversión corporativa futura (CAPEX, cambio en activos) al precio normalizado de la acción (Tobin's Q) hoy; se interpreta como medida del aprendizaje gerencial a partir de los precios de mercado.  
  Relaciones: MIDE → managerial learning (1); USA → algorithmic trading (1)

**difference-in-differences** [metodo] (docs=2) — Regresión con efectos fijos de stock y fecha sobre la variable hybrid (dummy de tratamiento escalonado) para identificar el efecto causal de la hibridización sobre correlaciones de spreads, controlando tendencias temporales comunes.  
  Relaciones: USA → NYSE Autoquote (1); MITIGA → reverse causality (1); MITIGA → backtest overfitting (1); USA → Liquidity Commonality (1)

**liquidity risk** [concepto] (docs=2) — Riesgo de liquidez en FX multi-dealer: los HFT/ultra-HFT se retiran del mercado durante saltos de precio (especialmente en intervenciones de bancos centrales), actuando como market makers de facto sin obligación de proveer liquidez continua. El paper argumenta que esto es más ...  
  Relaciones: MIDE → Liquidity Commonality (1); CAUSA → high-frequency trading (1); SE_OPONE_A → liquidity provision (1)

**short-term alpha** [concepto] (docs=2) — Nombre que dan al factor de co-integración αt: componente común de la deriva de los retornos, un proceso Ornstein-Uhlenbeck mean-reverting que representa desviaciones de corto plazo del retorno esperado y es la fuente principal de ganancias de la estrategia.  
  Relaciones: EQUIVALE_A → cointegration (1); USA → Ornstein-Uhlenbeck process (1); PREDICE → optimal investment strategy (1); MITIGA → adverse selection (1); CAUSA → directional strategy (1)

**asset pricing** [metodo] (docs=2) — Modelos de asset pricing (Fama-French 5, PCA, IPCA) usados para construir portfolios de arbitraje como residuals. La similitud entre activos se captura por exposición similar a factores de riesgo. Los residuals resultantes son débilmente correlacionados cross-sectionalmente y ...  
  Relaciones: PARTE_DE → statistical arbitrage (1); USA → PCA (1); REQUIERE → no-arbitrage pricing (1); USA → deep learning (1)

**implied volatility surface** [concepto] (docs=2) — Representación tridimensional de la volatilidad en función del tiempo a expiración y el precio de ejercicio. En lugar de interpolar directamente, se propone modelarla paramétricamente para asegurar la ausencia de arbitraje espacial y temporal.  
  Relaciones: REQUIERE → no-arbitrage conditions (1); USA → Black-Scholes model (1)

**no-arbitrage pricing** [concepto] (docs=2) — Principio fundamental que restringe los precios de derivados mediante argumentos de replicación dinámica y medidas martingala equivalentes. El paper lo presenta como la restricción más básica que los modelos de AI deben respetar para ser financieramente válidos.  
  Relaciones: MITIGA → economic hallucination (1); REQUIERE → martingale pricing (1)

**arbitrage** [estrategia] (docs=2) — Estrategia de comprar/vender bundles de instrumentos económicamente equivalentes con la casa de cambio (a precio fijo $1) contra órdenes mal cotizadas de otros traders, capturando ganancia libre de riesgo cuando el good spread se cruza.  
  Relaciones: USA → market-making violation of individual rationality (1); MEJORA_A → efficient market hypothesis (1)

**speed of adjustment** [metrica] (docs=2) [también: Speed of adjustment] — Medida de resiliencia de liquidez que captura qué tan rápido el mercado ajusta precios tras nueva información. Se mide como la diferencia entre volatilidad/liquidez real y un benchmark pre-anuncio (t-50 a t-20 minutos). Distinta de medidas estáticas de liquidez como spreads.  
  Relaciones: MIDE → price discovery (1); PREDICE → lead-lag effect (1); REQUIERE → partial adjustment with noise model (1)

**market volatility** [fenomeno] (docs=2) — Variable de mercado cuya relación con el trading algorítmico es objeto de debate: un estudio empírico en el mercado chino encuentra que el trading algorítmico reduce la volatilidad en balance, vía el mecanismo de sentimiento del inversor.  
  Relaciones: MEJORA_A → market efficiency (1); CAUSA → algorithmic trading (1)

**jump-diffusion model** [concepto] (docs=2) — Clase general de modelos con saltos y volatilidad estocástica en la dinámica del subyacente, necesaria para generar suficiente asimetría en retornos de corto plazo y así calzar los skews de volatilidad implícita.  
  Relaciones: PREDICE → implied volatility (1); CAUSA → volatility skew (1); MEJORA_A → Black-Scholes-Merton model (1)

**overreaction** [fenomeno] (docs=2) — Fenómeno conductual por el cual los precios reaccionan de forma excesiva a señales públicas en el corto plazo, desviándose del valor intrínseco. En este paper, el proceso intrínseco (γ) exhibe sobrecreacción leve (γ<1), siendo mayor para índices de menor capitalización. Consis...  
  Relaciones: CAUSA → momentum (1); USA → representativeness heuristic (1); SE_OPONE_A → market efficiency (1); SE_OPONE_A → underreaction (1); PARTE_DE → intrinsic value process (1)

**capital asset pricing model** [concepto] (docs=2) — Modelo de un factor (beta de mercado) para el retorno esperado de un activo, presentado como la solución de Markowitz-Sharpe-Lintner al problema de asignación de portafolio, y luego criticado y extendido.  
  Relaciones: PARTE_DE → factor model (1); SE_OPONE_A → arbitrage pricing theory (1); USA → beta (1); SE_OPONE_A → empirical evidence of inverse risk-return relationship (1)

**beta** [metrica] (docs=2) — Parámetro de riesgo sistemático del CAPM, definido como la covarianza del retorno del activo con el retorno del mercado dividido la varianza del retorno del mercado; describe la sensibilidad de los retornos en exceso del activo a los del mercado.  
  Relaciones: PARTE_DE → capital asset pricing model (1); USA → CAPM (1)

**audit trail** [metodo] (docs=2) — Registro inmutable por predicción de ML requerido por SR 11-7 y EU AI Act que captura: código, datos, modelo, entorno de cómputo y predicción. El paper propone MVAT-7 como estándar mínimo con 7 componentes.  
  Relaciones: REQUIERE → model risk management (1); MITIGA → backtest overfitting (1)

**XGBoost** [metodo] (docs=2) — Modelo de gradient boosting usado para predecir el spread día-siguiente con features técnicas (SMA5/10/15, EMA9, RSI, MACD). Reentrenado cada 5 días con early stopping. Obtiene la mejor rentabilidad del paper (23,8% anual) al predecir correctamente la dirección del spread el ~...  
  Relaciones: PARTE_DE → gradient boosting (2); PREDICE → critical edge (1); MEJORA_A → ARIMA (1); USA → walk-forward validation (1)

**mispricing** [metrica] (docs=2) [también: Mispricing] — Residuo de la regresión de cointegración que mide la desviación del precio del WTI respecto al valor del statistical portfolio. Su estacionariedad (reversión a la media) es la base de la señal de trading.  
  Relaciones: MIDE → price discovery (1)

**LLM-driven drift SDE** [metodo] (docs=2) — Una clase de ecuación diferencial estocástica en la cual el término de tendencia (drift) depende funcionalmente y de manera dinámica de representaciones densas (embeddings) del mercado que se extraen con un LLM.  
  Relaciones: USA → LLM embeddings (1); USA → Brownian motion (1)

**square-root law** [concepto] (docs=2) — Relación funcional según la cual el costo de transacción (impacto de mercado) es proporcional a la raíz cuadrada del tamaño de la orden como fracción del betting volume: C(Q̃) ∝ |Q̃/V̄|^(1/2). Bajo invarianza, con la raíz cuadrada como función de impacto, los costos dependen s...  
  Relaciones: CAUSA → market impact (1); APLICA_A → limit order book (1); MEJORA_A → market impact (1); APLICA_A → transaction costs (1); USA → market microstructure invariants (1)

**Batch Trading Mechanism** [concepto] (docs=2) — Mecanismo alternativo al trading continuo donde las órdenes se acumulan y ejecutan en intervalos discretos (batch), diseñado para mitigar la carrera armamentista de velocidad del HFT y eliminar arbitraje libre de riesgo.  
  Relaciones: MEJORA_A → frequent batch auction (1)

**false discovery rate** [metrica] (docs=2) — Proporción esperada de rechazos falsos entre todos los rechazos en un problema de testeo múltiple; controlada mediante el procedimiento Benjamini-Hochberg, recomendado para evitar el problema del 'factor zoo' al evaluar anomalías de pricing.  
  Relaciones: MITIGA → data snooping (1); USA → multiple testing (1); MIDE → data snooping (1)

**risk-neutral valuation** [metodo] (docs=2) [también: Risk-Neutral Valuation] — Técnica de valuar un derivado como el valor esperado descontado de su payoff bajo una medida de probabilidad Q en la que el drift del activo es la tasa libre de riesgo, eliminando la necesidad de conocer las preferencias de riesgo de los agentes.  
  Relaciones: USA → Girsanov's theorem (1); PARTE_DE → Black-Scholes-Merton model (1); APLICA_A → Coupled Optimal Stopping (1)

**market depth** [concepto] (docs=2) — Cantidad de acciones disponibles en cada cotización del book; la profundidad del mismo lado aumenta la agresividad de la orden, la del lado opuesto la reduce.  
  Relaciones: MIDE → limit order book (2); PREDICE → mid-price (1); CAUSA → order aggressiveness (1)

**Q-learning** [metodo] (docs=2) — Algoritmo de RL que estima iterativamente la función acción-valor óptima usando la ecuación de Bellman, con actualización basada en tasa de aprendizaje y factor de descuento; se usa epsilon-greedy para explorar/explotar.  
  Relaciones: PARTE_DE → reinforcement learning (2); USA → epsilon-greedy strategy (1)

**trade size** [metrica] (docs=2) [también: Trade Size] — Número de acciones negociadas por transacción. Contiene información potencialmente importante sobre insider trading y price impact. Mercados con HFT experimentan reducciones pronunciadas en el trade size promedio.  
  Relaciones: MIDE → algorithmic trading (1); PARTE_DE → abnormal algorithmic trading (1); PARTE_DE → market microstructure (1)

**order book convexity** [metrica] (docs=2) — Variable construida por los autores como el promedio del cambio en la pendiente del price schedule (spread vs profundidad acumulada) a través de los niveles del libro; positiva indica spreads más anchos o profundidad menor lejos del mercado.  
  Relaciones: MIDE → limit order book (2); PREDICE → tick size (2); SE_OPONE_A → order book concavity (1)

**stress testing** [metodo] (docs=2) [también: Stress Testing] — Proceso de evaluación de la resiliencia de una cartera bajo escenarios adversos hipotéticos pero plausibles —recesiones macroeconómicas, shocks de tasas, disrupciones sectoriales— generados mediante modelos macro-financieros. Bajo Basilea III es obligatorio e integra riesgo de...  
  Relaciones: USA → tail risk (1); REQUIERE → Monte Carlo simulation (1); USA → Copula Dependency Modeling (1)

**Shannon entropy** [metrica] (docs=2) — Entropía computada sobre la distribución empírica de signos de trading (buy/sell) en una ventana deslizante de N eventos de volumen. Bajo condiciones normales HS se aproxima a 1 bit (máximo desorden); una caída abrupta de entropía sin pico de volatilidad constituye la firma de...  
  Relaciones: MIDE → regime detection (1); APLICA_A → position sizing (1); USA → trade sign (1); MIDE → regime switching (1); APLICA_A → market microstructure (1)

**Trading Delays** [fenomeno] (docs=2) — Tiempo que transcurre entre la decisión de negociar y la ejecución efectiva de la orden. Varía ampliamente entre mercados: segundos/minutos en equities, 1-3 días en bonos corporativos, 5 días en bonos municipales.

**dispersion trading** [estrategia] (docs=2) — Estrategia que toma una posición corta en volatilidad del índice contra posiciones largas en volatilidad de una canasta de sus componentes, aprovechando que la volatilidad del índice suele cotizar significativamente por debajo de la de sus constituyentes.  
  Relaciones: USA → implied correlation (2); USA → variance swap (1); SE_OPONE_A → correlation swap (1)

**adversarial training** [metodo] (docs=2) — Técnica de defensa que incorpora ejemplos adversariales generados dentro del propio proceso de entrenamiento del agente para mejorar su robustez, aquí aplicada en escala jerárquica (tick, minuto, episodio).  
  Relaciones: MITIGA → adversarial attack (2); PARTE_DE → multi-scale adversarial training (1); USA → reinforcement learning (1)

**SHAP** [metodo] (docs=2) — Técnica de explicabilidad global basada en valores de Shapley de teoría de juegos; el paper usa aproximación TreeSHAP para reducir la complejidad y lograr 8.3ms de latencia promedio con procesamiento GPU en batch.  
  Relaciones: MIDE → feature importance (2); PARTE_DE → explainable AI (1); APLICA_A → high-frequency trading (1)

**cumulative abnormal return** [metrica] (docs=2) [también: cumulative abnormal return (CAR)] — Retorno anormal acumulado estimado mediante el modelo de cinco factores de Fama-French (2015) más momentum, usado para cuantificar la reacción del mercado a un anuncio de dividendo especial.  
  Relaciones: MIDE → special dividend (1); USA → standardized price jump (1)

**diagonal effect** [fenomeno] (docs=2) — Mayor probabilidad de observar un tipo de orden dado justo después de que ese mismo tipo de orden acaba de ocurrir, respecto a la probabilidad incondicional; documentado en el SET tanto para órdenes de mercado como límite, más fuerte en las límite.  
  Relaciones: PARTE_DE → order flow (2); CAUSA → order splitting (1); USA → order splitting (1)

**anomaly detection** [metodo] (docs=2) — Estrategia de identificación de flujo informado como anomalías estructurales en el libro de órdenes, no como predicción de precio futuro. El modelo emite una señal cuando la distancia de Mahalanobis St en el espacio latente supera un umbral, indicando que el punto se ha alejad...  
  Relaciones: USA → Mahalanobis distance (1); USA → Conditional VAE (1)

**NLP** [metodo] (docs=2) — Procesamiento de lenguaje natural aplicado a datos financieros textuales; el paper cita evidencia de que modelos NLP-enhanced superan métricas de sentimiento tradicionales en forecasting de volatilidad, momentum y sorpresas macroeconómicas.  
  Relaciones: USA → large language models (2); APLICA_A → sentiment analysis (1)

**order anticipation** [estrategia] (docs=2) — Práctica donde algoritmos HFT observan una operación en un exchange y reaccionan en otros antes de que se procesen las órdenes restantes del trader original.  
  Relaciones: USA → order flow (1)

**Minimum Trading Unit** [concepto] (docs=2) [también: Minimum Trading Unit (MTU)] — Unidad mínima de acciones o valor monetario necesario para realizar una transacción en un mercado. Actúa como barrera de entrada que afecta la accesibilidad del mercado subyacente y, por ende, al ETF correspondiente.  
  Relaciones: CAUSA → Tracking Error (1); CAUSA → probability of informed trading (1); APLICA_A → Institutional Trading Activity (1); MITIGA → Market Accessibility (1); SE_OPONE_A → Institutional Trading Activity (1)

**Tracking Error** [metrica] (docs=2) — Diferencia entre el precio del ETF y su Net Asset Value (NAV). Barreras de entrada elevadas en el mercado subyacente se asocian con mayores tracking errors.  
  Relaciones: SE_OPONE_A → Arbitrage Activity (1); MIDE → Active ETF (1)

**Institutional Trading Activity** [concepto] (docs=2) [también: Institutional trading activity] — Actividad de inversión de instituciones, aproximada empíricamente en el estudio utilizando la proporción del volumen de operaciones a gran escala (transacciones mayores a $20K o $50K).  
  Relaciones: REQUIERE → Market Accessibility (1); USA → Arbitrage Activity (1)

**DBSCAN** [metodo] (docs=2) — Clustering basado en densidad que identifica regiones de alta densidad separadas por baja densidad. Tiende a formar un cluster gigante con la mayoría de stocks y tratar el resto como outliers. Parametrizado con l1 norm y MinPts = ln(N).  
  Relaciones: PARTE_DE → clustering (1); SE_OPONE_A → K-means (1); SE_OPONE_A → k-Means Clustering (1)

**Almgren-Chriss Model** [metodo] (docs=2) — Modelo fundacional de ejecución óptima que diferencia impacto temporal y permanente del precio debido a la demanda de liquidez, usado como marco de referencia para los problemas de trading algorítmico en la tesis.  
  Relaciones: APLICA_A → optimal execution (1); APLICA_A → VWAP Execution Strategy (1)

**TWAP** [estrategia] (docs=2) — Liquidar el inventario restante en partes iguales sobre el tiempo restante; aparece como el componente base de la estrategia óptima POV y como el límite de ambas estrategias cerca del vencimiento, cuando el objetivo de completar la liquidación domina al de trackear el order-flow.  
  Relaciones: PARTE_DE → percentage of volume strategy (1); USA → market impact (1); PARTE_DE → optimal execution (1)

**permanent price impact** [concepto] (docs=2) — Efecto duradero del order-flow sobre el midprice: el flujo neto (compras menos ventas) empuja el precio linealmente con parámetro b, porque el order-flow transmite información. A diferencia de trabajos previos, acá el impacto permanente incluye el flujo de todos los demás trad...  
  Relaciones: USA → net order flow (1); MIDE → price discovery (1); USA → Structural Vector Autoregression (SVAR) (1)

**multiple testing** [riesgo_metodologico] (docs=2) — Necesidad de ajustes estadísticos (control de FDR, umbrales de t-estadístico elevados) para separar primas de riesgo genuinas de artefactos estadísticos al evaluar muchas señales/factores candidatos, dado el fenómeno del 'factor zoo'.  
  Relaciones: REQUIERE → false discovery rate (1); CAUSA → post-selection adjustment (1); PARTE_DE → backtest overfitting (1)

**Bayesian updating** [metodo] (docs=2) — Actualización recursiva de la media y varianza condicional del valor del activo por parte del market maker a partir del order flow combinado observado (proyección gaussiana); la varianza condicional decrece con la actividad del insider.  
  Relaciones: USA → order flow imbalance (1); APLICA_A → price discovery (1); PARTE_DE → meta-learner spine (1)

**model uncertainty** [riesgo_metodologico] (docs=2) — Incertidumbre sobre los supuestos del modelo, como la forma de la distribución de probabilidad asumida y los parámetros embebidos en ella, que puede llevar a una estimación incorrecta y a una regla de trading mal calibrada.  
  Relaciones: MITIGA → Kullback-Leibler divergence (1); CAUSA → backtest overfitting (1); APLICA_A → optimal investment strategy (1)

**microprice** [concepto] (docs=2) — En la reformulación del equilibrio de Kyle (Ec. 10), el precio se expresa como función lineal de la mejor estimación de la demanda informada, análoga a un precio ponderado por la creencia sobre información privada.  
  Relaciones: MEJORA_A → mid-price (1); USA → order flow imbalance (1); EQUIVALE_A → market impact (1); PARTE_DE → Kyle model (1)

**expectancy** [metrica] (docs=2) — Ganancia esperada por trade en múltiplos de R; calculada tanto teóricamente (E[R]=Pw·Rw−Pl·Rl) como post-costos en la simulación (+0.414R).  
  Relaciones: USA → binary payoff structure (1)

**adaptive markets hypothesis** [concepto] (docs=2) — Propone que la eficiencia de mercado no es constante sino que varía con el tiempo a medida que traders, tecnologías y estrategias se adaptan, lo que abre espacio conceptual para que sistemas de IA exploten patrones temporales.  
  Relaciones: SE_OPONE_A → efficient market hypothesis (1); APLICA_A → algorithmic trading (1); USA → regime switching (1)

**explainable AI** [metodo] (docs=2) — Conjunto de técnicas (aquí SHAP y LIME) integradas para dar transparencia a las decisiones del agente DRL, cumpliendo requisitos regulatorios sin sacrificar la latencia sub-10ms necesaria en HFT.  
  Relaciones: USA → SHAP (1); USA → LIME (1); APLICA_A → high-frequency trading (1)

**vector-autoregressive model** [metodo] (docs=2) [también: Vector Autoregressive (VAR) model] — Modelo econométrico implementado para evaluar simultáneamente y en ultra-alta frecuencia (intervalos de 1 segundo o de 5 minutos) las respuestas y asociaciones dinámicas entre la participación del HFT y la volatilidad realizada.  
  Relaciones: MIDE → realized volatility (1); USA → cointegration (1); APLICA_A → optimal investment strategy (1)

**order splitting** [concepto] (docs=2) — Hipótesis según la cual traders dividen sus órdenes en partes más chicas para reducir el impacto de precio u ocultar información privada; el paper la testea comparando intervalos de tiempo entre órdenes condicionales al tamaño del spread, sin encontrar evidencia consistente.  
  Relaciones: MITIGA → market impact (2); SE_OPONE_A → trade imitation (1); CAUSA → diagonal effect (1)

**synthetic asset** [concepto] (docs=2) — Combinación lineal de un grupo de activos cuyos coeficientes representan cantidades de cada activo en el portfolio, construido para exhibir reversión a la media con volatilidad finita.  
  Relaciones: REQUIERE → oracle risk (1); PARTE_DE → statistical arbitrage (1)

**slippage** [concepto] (docs=2) — Diferencia entre el precio observado al generar la señal y el precio real de ejecución, inducida por tiempo y volumen; en la herramienta se especifica como porcentaje fijo y engloba también el bid-ask spread.  
  Relaciones: PARTE_DE → transaction costs (1); EQUIVALE_A → bid-ask spread (1)

**temporal graphs** [metodo] (docs=2) [también: Temporal Graphs] — Una clase de grafos definidos por un conjunto constante de vértices y un conjunto cambiante de aristas, cada uno conocido como un paso de tiempo (timestep).

**Pigovian tax** [metodo] (docs=2) — Impuesto correctivo que grava a los fast traders para internalizar la externalidad negativa que imponen sobre los slow traders. En el modelo, un impuesto pigouviano de 0.121 ticks mejora el bienestar en 0.095 ticks respecto al caso sin regulación, aunque deteriora las medidas ...  
  Relaciones: MITIGA → adverse selection (1); MEJORA_A → market efficiency (1); MITIGA → overinvestment in HFT (1); SE_OPONE_A → bid-ask spread (1)

**Limits to Arbitrage** [fenomeno] (docs=2) — Restricciones como short-sale restrictions o funding illiquidity que limitan la capacidad del arbitrajista de actuar sobre pricing errors no triviales, particularmente cuando hay riesgo de convergencia.  
  Relaciones: CAUSA → No-Arbitrage Band (1); SE_OPONE_A → arbitrage (1); MITIGA → market efficiency (1)

**Market Capitalization** [metrica] (docs=2) [también: market capitalization] — Tamaño de una empresa medido por el valor de mercado de sus acciones en circulación. Sirve como variable instrumental para el grado de thin trading y como criterio de segmentación para estudiar diferencias en la velocidad de ajuste de precios.  
  Relaciones: PARTE_DE → Style Investing (1); CAUSA → lead-lag effect (1); USA → thin trading (1); PREDICE → speed of adjustment (1)

**non-parametric calibration** [metodo] (docs=2) — Método de estimación de kernels de Hawkes sin imponer forma paramétrica previa, usando mínimos cuadrados sobre conteos binned en una grilla linear-log. Extiende Kirchner 2017 añadiendo constraints de signo unidireccional y estabilidad (máximo autovalor de la matriz de normas <...  
  Relaciones: USA → Hawkes process (1); REQUIERE → Hawkes graph (1); APLICA_A → Compound Hawkes Process (1)

**multivariate Hawkes process** [metodo] (docs=2) [también: Multivariate Hawkes Process] — Proceso puntual estocástico multivariado con función de intensidad condicional λi(t) = µi + Σ∫φij(t−s)dNj(s) que captura auto-excitación (i=j) y cross-excitación (i≠j) entre múltiples flujos de eventos.  
  Relaciones: APLICA_A → order flow imbalance (1)

**Trembling-Hand Perfect Nash Equilibrium (THPNE)** [metodo] (docs=2) — Refinamiento de teoría de juegos que elimina equilibrios de Nash inestables o imperfectos asumiendo que los jugadores pueden cometer errores con pequeña probabilidad, aplicado al juego de tres niveles entre HFTs.  
  Relaciones: MEJORA_A → Nash equilibrium (2); APLICA_A → Batch Trading Mechanism (2)

**linear market impact model** [metodo] (docs=2) — Supuesto de impacto (temporal y permanente) lineal, justificado porque los modelos de impacto tienen poder predictivo bajísimo (R² < 5%) y la complejidad de modelos no lineales no compensa la pérdida de tractabilidad analítica.  
  Relaciones: USA → market impact (1); USA → market making (1); MEJORA_A → market impact (1)

**error correction model** [metodo] (docs=2) [también: Error-Correction Model (ECM)] — VECM que descompone la dinámica de un sistema cointegrado en un término de equilibrio de largo plazo estacionario y una dinámica de corto plazo de ajuste transitorio.  
  Relaciones: PARTE_DE → cointegration (1); APLICA_A → cointegration (1)

**noise trader** [concepto] (docs=2) — Agente cuya demanda yε se distribuye normal con media cero y es independiente del valor del activo; su volatilidad afecta inversamente la sensibilidad del precio al order flow en Kyle.  
  Relaciones: PARTE_DE → market microstructure (1); CAUSA → adverse selection (1); PARTE_DE → Kyle model (1); SE_OPONE_A → informed trading (1)

**market neutral strategy** [estrategia] (docs=2) [también: market-neutral strategy] — Estrategia de trading admisible donde los pesos del portafolio y la riqueza del inversor dependen únicamente de la señal estacionaria del spread, lográndose mediante posiciones largas y cortas compensadas para neutralizar la no-estacionariedad del mercado.  
  Relaciones: USA → statistical arbitrage (1); PARTE_DE → pairs trading (1)

**maximum likelihood estimation** [metodo] (docs=2) — Técnica estadística implementada para estimar los parámetros óptimos (tasa de reversión y volatilidad) del modelo Ornstein-Uhlenbeck a partir de datos históricos del spread.  
  Relaciones: USA → non-stationary model for statistical arbitrage trading (1); APLICA_A → Ornstein-Uhlenbeck process (1)

**long range dependence** [fenomeno] (docs=2) [también: Long Range Dependence (LRD)] — Correlaciones persistentes en el tiempo detectadas de forma clara en retornos absolutos o cuadrados aunque no en retornos crudos (con signo), motivando modelos de memoria larga en volatilidad (FIGARCH, MMAR).  
  Relaciones: CAUSA → volatility clustering (1); MITIGA → efficient market hypothesis (1)

**trailing stop** [metodo] (docs=2) — Stop dinámico anclado a la EMA de 50 periodos, que se activa exclusivamente cuando una vela cierra del lado adverso de la EMA, ignorando penetraciones intrabar (mechas).  
  Relaciones: MITIGA → wick-triggered stop-loss (1); MIDE → portfolio robustness (1)

**Blume regression method** [metodo] (docs=2) — Método de ajuste de beta mediante regresión (Blume, 1971) evaluado como corrector de reference-day risk; según el paper reduce solo la variabilidad más severa y no la reduce de forma consistente en muchas acciones.  
  Relaciones: MITIGA → reference-day risk (2); APLICA_A → beta (1); SE_OPONE_A → Vasicek Bayesian beta (1)

**natural language processing** [metodo] (docs=2) [también: Natural language processing (NLP)] — Técnica utilizada para extraer información de datos no estructurados, como correos electrónicos, redes sociales, noticias y reportes de ganancias, con el fin de realizar análisis de sentimiento o detectar intenciones fraudulentas.  
  Relaciones: USA → sentiment score (1); USA → sentiment analysis (1); APLICA_A → algorithmic trading (1)

**LIME** [metodo] (docs=2) — Técnica de explicabilidad local que ajusta un modelo sustituto lineal interpretable alrededor de una instancia específica para explicar decisiones individuales del agente.  
  Relaciones: PARTE_DE → explainable AI (1); SE_OPONE_A → SHAP (1); APLICA_A → high-frequency trading (1)

**reward function** [concepto] (docs=2) — Mecanismo de incentivo diseñado para el entrenamiento del agente, determinando el objetivo de optimización como el cambio en el valor de la cartera o retornos ajustados.  
  Relaciones: PARTE_DE → reinforcement learning (1)

**information acquisition** [fenomeno] (docs=2) [también: Information Acquisition] — Actividad de adquisición de información por parte de participantes del mercado, proxied por descargas no-robot de datos de reporte financiero desde EDGAR de la SEC; AT puede fomentarla o desalentarla según el tipo de estrategia.  
  Relaciones: MIDE → Revelatory Price Efficiency (1); PREDICE → Revelatory Price Efficiency (1); REQUIERE → informed trading (1); CAUSA → Revelatory Price Efficiency (1)

**ordered probit model** [metodo] (docs=2) — Modelo econométrico usado para estimar los determinantes de la agresividad de la orden como variable ordinal, siguiendo a Hausman, Lo y MacKinlay (1992); estimado separadamente para mercado alcista y bajista.  
  Relaciones: MIDE → order aggressiveness (1); USA → order aggressiveness (1)

**non-stationarity** [riesgo_metodologico] (docs=2) — Propiedad fundamental del mercado según los autores: no existe ningún estado estacionario. El comportamiento típico es de fast excitation and then slow relaxation con una amplia distribución de frecuencias de excitación y tiempos de relajación. Las variables observables son se...  
  Relaciones: SE_OPONE_A → statistical equilibrium (1); CAUSA → volatility (1); PARTE_DE → market dynamics (1)

**LOB convexity** [metrica] (docs=2) [también: LOB Convexity] — Ratio de las pendientes en niveles superiores vs inferiores del LOB. Una mayor convexidad implica que órdenes grandes enfrentan impacto desproporcionadamente mayor, generando colas más gruesas en la distribución de retornos.  
  Relaciones: MIDE → Patient traders (1); CAUSA → tail risk (1)

**infeasible Sharpe ratio** [metrica] (docs=2) [también: Infeasible Sharpe Ratio S*] — Sharpe ratio teóricamente óptimo bajo conocimiento perfecto de alphas y covarianzas: S* = √(α'Σ_u^(-1)α). No es alcanzable por ninguna estrategia factible. Condición de no near-arbitrage requiere S* ≲ 1, pero empíricamente S* explota (4.8-16) mientras el factible es <0.7.  
  Relaciones: MIDE → statistical arbitrage (1); SE_OPONE_A → Feasible Sharpe Ratio Bound (1)

**Benjamini-Hochberg procedure** [metodo] (docs=2) [también: Benjamini-Hochberg (BH) Procedure] — Procedimiento de testeo múltiple que controla la tasa de falsos descubrimientos (FDR). Solo es óptimo cuando pocos alphas son fuertes; con señales débiles es excesivamente conservador. Los alphas que no pasan el umbral se fijan a cero.  
  Relaciones: MITIGA → false discovery rate (1); SE_OPONE_A → optimal feasible strategy (1); SE_OPONE_A → Uniformly Optimal Strategy via Empirical Bayes (1)

**stale quote sniping** [estrategia] (docs=2) — Estrategia donde algoritmos de alta frecuencia ejecutan órdenes para aprovechar cotizaciones desactualizadas antes de que el market maker logre cancelarlas ante un cambio del valor fundamental.  
  Relaciones: CAUSA → adverse selection (1); USA → latency (1); CAUSA → bid-ask spread (1)

**Bertrand competition** [fenomeno] (docs=2) — En el entorno sin fricciones donde los consumidores tienen acceso perfecto a todos los market-makers, la competencia de precios entre al menos dos market-makers conduce la pareja de precios (bid, ask) al precio competitivo único (p*, p*) con beneficios nulos.  
  Relaciones: MITIGA → adverse selection (1); EQUIVALE_A → market making (1); PREDICE → competitive allocation mechanism (1)

**realized spread** [metrica] (docs=2) — Medida de liquidez que captura el costo de transacción implícito como la diferencia de precio entre una transacción en t y el precio 5 minutos después, duplicada y con signo según dirección del trade. Usada como variable dependiente en el VAR.  
  Relaciones: PARTE_DE → effective spread (1); MIDE → market liquidity (1); EQUIVALE_A → effective spread (1)

**Markov Decision Process** [metodo] (docs=2) [también: Markov Decision Process (MDP)] — Formalización matemática del problema de trading automatizado donde el agente observa el estado (precios, volumen, indicadores), toma una acción (comprar/vender/mantener) y recibe una recompensa.  
  Relaciones: USA → state space (1); REQUIERE → deep reinforcement learning (1)

**Branching Ratio** [metrica] (docs=2) [también: branching ratio] — Parámetro n = ∫ϕ(τ)dτ que gobierna la estabilidad del sistema Hawkes; mercados modernos operan cerca de n≈0.95 (criticalidad), donde perturbaciones infinitesimales pueden generar respuestas macroscópicas.  
  Relaciones: PARTE_DE → Hawkes Process de-clustering (1); MIDE → near-critical regime (1)

**Noise Trading (NT) Measure** [metrica] (docs=2) — Medida construida como la diferencia entre las frecuencias de los números 8 (suerte) y 4 (muerte) en los precios diarios de acciones (apertura, máximo, mínimo, cierre) de todas las empresas listadas en China. Un NT más alto indica mayor actividad de noise trading.

**minimum distance method** [metodo] (docs=2) — Técnica de selección de pares que empareja activos basándose en la distancia cuadrática media mínima entre sus precios normalizados a lo largo de un período de formación histórico.  
  Relaciones: PARTE_DE → pairs trading (1); USA → cointegration (1)

**hybrid market** [concepto] (docs=2) — Estructura de mercado donde la liquidez es provista simultáneamente por el market maker/especialista y por limit order traders, como en NYSE/Amex; el paper argumenta que modelar solo una fuente ignora la interacción entre ambas.  
  Relaciones: USA → limit order book (1); USA → market making (1); USA → algorithmic trading (1)

**arbitrage pricing theory** [concepto] (docs=2) [también: Arbitrage Pricing Theory] — Modelo de factores de riesgo que el paper combina con pairs trading para explicar parte del retorno de las series, aislando la reversión a la media en los residuos.  
  Relaciones: MEJORA_A → capital asset pricing model (1); USA → Ornstein-Uhlenbeck process (1)

**quadratic variation** [metodo] (docs=2) — Límite al que converge la varianza realizada cuando el número de fechas de muestreo tiende a infinito para un proceso de salto-difusión; el paper lo usa para derivar la valuación teórica del variance swap.  
  Relaciones: PARTE_DE → variance swap (1)

**calendar spread** [dato] (docs=2) [también: Calendar Spread] — Diferencial de precio entre dos vencimientos del mismo futuro (en el caso de estudio, Natural Gas septiembre-octubre), usado para ilustrar episodios de estrés de liquidez.  
  Relaciones: MIDE → liquidity sweep (1); PARTE_DE → pairs trading (1)

**Kelly criterion** [metodo] (docs=2) — Fracción óptima de riesgo derivada de la distribución empírica de resultados (f* ≈ 0.164); se usa como referencia pero se opera con solo 1% de riesgo por trade, muy por debajo de la mitad de Kelly.  
  Relaciones: MIDE → position sizing (1); APLICA_A → position sizing (1)

**Probabilistic Sharpe Ratio** [metrica] (docs=2) [también: probabilistic Sharpe ratio] — Reformula la evaluación de performance como la probabilidad de que el Sharpe verdadero supere un benchmark elegido, incorporando tamaño de muestra y momentos superiores de la distribución de retornos.  
  Relaciones: MEJORA_A → Sharpe ratio (2); MIDE → Sharpe ratio (1)

**Dimson thin trading adjustment** [metodo] (docs=2) — Método de coeficientes agregados (AC) que corrige el sesgo a la baja en la covarianza de acciones poco transadas, regresionando retornos sobre retornos de mercado rezagados, sincrónicos y adelantados.  
  Relaciones: APLICA_A → beta (1); CONTRADICE_A → reference-day risk (1); MITIGA → reference-day risk (1)

**Vasicek Bayesian beta** [metodo] (docs=2) — Estimador bayesiano de beta (Vasicek, 1973) que resultó ser, entre los métodos tradicionales de ajuste probados en la literatura previa, el único con resultados prometedores para reducir el rango de reference-day risk.  
  Relaciones: MITIGA → reference-day risk (2); APLICA_A → beta (1)

**information ratio** [metrica] (docs=2) — Compara el desempeño de la estrategia contra el S&P 500 como benchmark; resultó negativo (-0.1), indicando desempeño inferior ajustado por tracking error.  
  Relaciones: MIDE → benchmark-relative performance (1); USA → buy and hold benchmark (1); MEJORA_A → Sharpe ratio (1)

**cancel-to-trade ratio** [metrica] (docs=2) — Medida alternativa de AT: número de mensajes de cancelación (totales o parciales) dividido por número de trades, obtenida de datos MIDAS de la SEC; la mayoría de los mensajes de los AT terminan cancelados.  
  Relaciones: MIDE → algorithmic trading (2); PARTE_DE → abnormal algorithmic trading (1); USA → quote-to-trade ratio (1)

**drawdown** [metrica] (docs=2) — Pérdida máxima en un período; el paper reporta un único drawdown severo causado por un problema técnico, aislado del resto de un track record consistentemente rentable.  
  Relaciones: MIDE → market making (1)

**market sentiment** [concepto] (docs=2) — Estado alcista o bajista del mercado usado para segmentar la respuesta de compradores/vendedores y de traders momentum/contrarian ante cambios en el libro de órdenes.  
  Relaciones: PREDICE → order aggressiveness (1); CAUSA → order flow (1); CAUSA → order aggressiveness (1)

**automated market maker** [concepto] (docs=2) [también: Automated Market Maker (AMM)] — Smart contract que opera en DEXs eliminando la necesidad de market makers activos tradicionales. Funciona con algoritmos de pricing predeterminados que facilitan cotización automática y risk sharing, permitiendo que incluso inversores retail provean liquidez.  
  Relaciones: SE_OPONE_A → limit order book (1)

**Limit order book slope** [metrica] (docs=2) [también: Limit Order Book Slope] — Medida de la relación entre profundidad del LOB y distancia al precio de mercado. Refleja la dispersión de creencias de los inversores: mayor pendiente indica mayor consenso sobre el valor fundamental entre los participantes del mercado.  
  Relaciones: MIDE → Investor Beliefs Consensus (1); PREDICE → volatility (1)

**moving average crossover** [estrategia] (docs=2) [también: Moving Average Crossover] — Estrategia trend-following: compra 34% del cash restante cada día que el precio de Bitcoin está sobre su media móvil de 14 días y liquida toda la posición cuando cae debajo; el paper advierte sensibilidad al lookback y al holding period.  
  Relaciones: PARTE_DE → momentum (1); USA → technical analysis (1); PARTE_DE → technical analysis (1)

**stop-loss** [concepto] (docs=2) [también: stop loss] — Mecanismo exit para truncar pérdidas no esperadas, aunque paradójicamente corta el proceso natural de reversión bajando el rendimiento agregado de la estrategia.  
  Relaciones: MITIGA → maximum drawdown (1); PARTE_DE → trading stop (1)

**Long Short Term Memory** [metodo] (docs=2) [también: LSTM (Long Short-Term Memory)] — Red neuronal recurrente con celda de memoria de largo plazo ct y tres compuertas (input it, forget ft, output ot) más compuerta principal gt. La celda se actualiza como ct = ft ⊗ ct-1 + it ⊗ gt. Obtiene RMSE de 2.34 en predicción de precio de IBM.  
  Relaciones: PARTE_DE → Recurrent Neural Network (1)

**batch auction** [concepto] (docs=2) — Mecanismo de mercado que acumula órdenes continuas pero las empareja y compensa en intervalos discretos de tiempo para mitigar las ventajas de velocidad pura.  
  Relaciones: MEJORA_A → limit order book (1); MITIGA → latency (1)

**Z-score normalization** [metodo] (docs=2) — Estandarización del spread residual dividiéndolo por su desviación estándar in-sample, lo cual provee una medida libre de escala de la divergencia del par, usada como umbral de entrada/salida (trading signal).  
  Relaciones: USA → log-price regression spread (1)

**micro-price** [metrica] (docs=2) [también: Micro-Price] — Precio ponderado por volumen al mejor bid y ask: (Vbid·Pask + Vask·Pbid)/(Vbid+Vask). Señal de muy baja latencia (30-50 µs) que indica dirección cuando el mid-price cruza el micro-price más un umbral.  
  Relaciones: USA → order book imbalance (1); USA → bid-ask spread (1)

**hidden order** [concepto] (docs=2) [también: hidden orders] — Órdenes no mostrables (non-displayable) de NASDAQ que no se reportan en el libro de órdenes pero sí en ejecución. Su ID era accesible antes del 6 de octubre de 2010, pero posteriormente NASDAQ dejó de reportarlo, y desde el 14 de julio de 2014 tampoco reporta el tipo de matchi...  
  Relaciones: SE_OPONE_A → displayed limit order book (1); PARTE_DE → limit order book (1); APLICA_A → market microstructure (1)

**Abnormal turnover** [metrica] (docs=2) [también: abnormal turnover] — Diferencia entre la rotación (turnover) diaria de la acción durante la ventana del anuncio de ganancias y el promedio de rotación diaria de un periodo base de no-reporte.  
  Relaciones: MIDE → Governance through trading (grading) (1); MIDE → informed trading (1)

**Liquidity fragility** [fenomeno] (docs=2) [también: liquidity fragility] — Estado del mercado en el que pueden existir múltiples equilibrios y un pequeño shock en los parámetros puede detonar el paso de un equilibrio de alta liquidez a uno de baja liquidez extrema.  
  Relaciones: CAUSA → market impact (1)

**Natural Experiment** [metodo] (docs=2) — La introducción de la regulación de cost recovery de ASIC el 1 de enero de 2012 crea un experimento natural para examinar el impacto causal de los messaging fees sobre HFT y calidad de mercado.  
  Relaciones: USA → Minimum Trading Unit (1); APLICA_A → Panel Regression (1); APLICA_A → Causal Inference (1)

**price slippage** [metrica] (docs=2) [también: Price Slippage] — Desviación del precio de ejecución promedio respecto al precio de llegada inicial (arrival price), modelado como la suma del impacto de mercado permanente, impacto instantáneo, el spread y un componente estocástico.  
  Relaciones: SE_OPONE_A → Statistical Arbitrage Strategy (1)

**Price Dispersion** [metrica] (docs=2) [también: price dispersion] — Dispersión de precios intradía ponderada por volumen, desarrollada por Jankowitsch, Nashikkar y Subrahmanyam (2011). Mide la variabilidad del precio dentro de un día respecto al precio promedio diario, ofreciendo información sobre la volatilidad interna del activo. Mayor dispe...  
  Relaciones: PREDICE → Trading Delays (1); MIDE → volatility (1); PARTE_DE → microstructure effects (1)

**Rolling Cointegration (Log-Price)** [metodo] (docs=2) [también: Rolling Cointegration on Log Prices] — Cointegración sobre log-precios (no residuos de modelo factorial) con ventana rolling de 3 años para evitar relaciones espurias y descartar pares que dejaron de co-moverse.  
  Relaciones: APLICA_A → pairs trading (1); MEJORA_A → pairs trading (1)

**PCA-Based Statistical Arbitrage** [estrategia] (docs=2) — Estrategia que descompone retornos accionarios en componentes sistemáticos (PCA) e idiosincráticos (residuos). Los residuos se modelan como procesos mean-reverting (Ornstein-Uhlenbeck) generando señales contrarian: long en residuos negativos, short en positivos. Portafolio mar...  
  Relaciones: USA → Ornstein-Uhlenbeck process (1); USA → mean reversion (1); APLICA_A → Market-Neutral Portfolio (1)

**Bloc Currency Unit (BCU)** [concepto] (docs=2) — Moneda electrónica de reserva basada en mercado, usada exclusivamente para transacciones entre bancos centrales de un bloque comercial, emitida proporcionalmente a contribuciones de oro.

**Ensemble Q-Learning** [metodo] (docs=2) — Agente de reinforcement learning que mantiene múltiples Q-tables entrenadas independientemente y agrega sus estimaciones para reducir varianza y mejorar estabilidad en decisiones de trading.  
  Relaciones: APLICA_A → pairs trading (2)

**investor sentiment** [concepto] (docs=2) [también: Investor Sentiment] — Una de las posibles interpretaciones del componente sistemático del noise trading: comportamiento irracional de inversores individuales no correlacionado con factores fundamentales pero que sigue patrones autorregresivos.  
  Relaciones: MITIGA → market volatility (1); CAUSA → mispricing (1)

**half-life of mean reversion** [metrica] (docs=2) [también: Half-Life of Mean Reversion] — Tiempo requerido para que la tendencia determinística de un proceso OU recorra la mitad del camino hacia su esperanza de largo plazo. Definido como τ̃ ∝ ln(2)/θ. A mayor θ (mayor velocidad de reversión), menor half-life y menor espera para realizar ganancias.  
  Relaciones: MIDE → mean reversion (1)

**realized variance** [concepto] (docs=2) — Objeto subyacente de los derivados de varianza estudiados (opciones sobre varianza realizada, ligadas al índice VIX de CBOE), cuya dinámica de volatilidad estocástica affine con saltos se modela explícitamente.  
  Relaciones: PARTE_DE → stochastic volatility model (1); APLICA_A → volatility of variance smile (1)

**market concentration** [fenomeno] (docs=2) — Alta concentración de las transacciones interbancarias en pocos bancos, con el banco central dominando el segmento en un grado muy elevado, reduciendo la competencia y la formación de precios descentralizada.  
  Relaciones: CAUSA → price discovery (1); CAUSA → institution level order flow (1)

**Lobster database** [dato] (docs=2) [también: LOBSTER database] — Base de datos de order book utilizada para calibrar y validar empíricamente el modelo, con datos de nivel de libro de la acción Micron Technology (MU) del 1 de julio de 2019.  
  Relaciones: USA → order flow (1); REQUIERE → queue position (1)

**support and resistance** [concepto] (docs=2) — Zonas de confluencia de al menos 2 promedios históricos de precio (8, 21, 34, 55, 89 barras) usadas como niveles de soporte/resistencia estadísticamente significativos en el algoritmo KCE-PD.  
  Relaciones: USA → multiple time frame analysis (1); USA → technical analysis (1)

**t-distribution beta adjustment** [metodo] (docs=2) — Método (Cademartori et al., 2003) que sustituye la distribución normal estándar por una t de Student de colas más pesadas en la regresión de beta, para incorporar mejor outliers y reducir la sensibilidad al día de referencia.  
  Relaciones: MEJORA_A → Blume regression method (2); MITIGA → reference-day risk (2)

**order book manipulation attack** [fenomeno] (docs=2) — Ataque adversarial propuesto por el paper (OBMA) que perturba estratégicamente features del libro de órdenes para engañar al agente sobre la liquidez de mercado; logra 73.4% de éxito contra agentes DRL sin defensa.  
  Relaciones: PARTE_DE → adversarial attack (2); USA → limit order book (2)

**FGSM** [metodo] (docs=2) — Fast Gradient Sign Method: ataque adversarial estándar que perturba el estado en la dirección del signo del gradiente de la pérdida, aquí con epsilon=0.05.  
  Relaciones: PARTE_DE → adversarial attack (2)

**PGD** [metodo] (docs=2) — Projected Gradient Descent: variante iterativa de ataque adversarial con refinamiento en 10 iteraciones y tamaño de paso 0.01, usada como uno de los cinco vectores de ataque evaluados.  
  Relaciones: PARTE_DE → adversarial attack (2); MEJORA_A → FGSM (1)

**quote-to-trade ratio** [metrica] (docs=2) [también: Quote-to-Trade Ratio] — Proxy de algorithmic trading computable del consolidated tape de EE.UU. que mide el número de actualizaciones de best bid-offer quotes relativo al volumen de trading o número de transacciones.  
  Relaciones: MIDE → algorithmic trading (1)

**omitted variable bias** [riesgo_metodologico] (docs=2) [también: Omitted Variable Bias] — Riesgo de que variables no observadas afecten simultáneamente la actividad de trading/order book y las decisiones de inversión de las firmas, sesgando la relación estimada entre AT e investment-to-price sensitivity.  
  Relaciones: MITIGA → two-stage least squares (1)

**earnings surprise** [concepto] (docs=2) [también: Earnings surprise] — Diferencia porcentual entre el resultado real por acción y el pronóstico promedio de analistas; usada para testear asimetría en el aprendizaje gerencial ante información positiva vs. negativa.  
  Relaciones: MEJORA_A → investment-to-price sensitivity (1); CAUSA → Abnormal turnover (1)

**exponential utility** [concepto] (docs=2) [también: Exponential Utility] — Función de utilidad u(x) = −e^(−γx) usada por el agente para evaluar su riqueza terminal, con γ como coeficiente de aversión al riesgo, base del criterio de optimización de la estrategia.  
  Relaciones: USA → optimal investment strategy (1)

**viscosity solution** [metodo] (docs=2) [también: Viscosity Solution] — Concepto de solución débil para EDPs no lineales (como la HJB) que no requieren diferenciabilidad clásica. Esencial para manejar la no-suavidad de la función de valor inducida por los costes de transacción.  
  Relaciones: PARTE_DE → quasi-variational inequality (1); REQUIERE → HJB Variational Inequality (1)

**price-time priority** [concepto] (docs=2) [también: Price-Time Priority] — Regla de prioridad en limit order books: primero por precio, luego por tiempo de llegada (FIFO); fundamento del modelo de colas.  
  Relaciones: PARTE_DE → limit order book (1); APLICA_A → queueing systems (1)

**Baum-Welch algorithm** [metodo] (docs=2) — Algoritmo EM usado para entrenar el HMM de dos estados con covarianza diagonal sobre los features del spread en cada ventana de entrenamiento.  
  Relaciones: USA → hidden Markov model (2)

**CARA utility** [metrica] (docs=2) — Función de utilidad empleada para modelar la aversión al riesgo del large trader, donde la recompensa surge del patrimonio terminal.  
  Relaciones: MIDE → risk aversion (1)

**stylized facts** [concepto] (docs=2) — Conjunto de propiedades empíricas usadas para validar la calidad del simulador: distribuciones de inter-eventos, signature plot, distribución de retornos y spreads, autocorrelación de retornos absolutos y price paths. El modelo CHP replica todas ellas mejor que el benchmark Po...  
  Relaciones: MIDE → limit order book (1)

**insider trading regulation** [fenomeno] (docs=2) [también: Insider Trading Regulation] — Restricciones regulatorias que enfrentan los insiders registrados en operaciones con acciones propias pero no en acciones de competidores, creando incentivos asimétricos para el trading en competidores.  
  Relaciones: MITIGA → private information trading (1)

**Bollinger bands** [metrica] (docs=2) — Bandas de Bollinger usadas como feature de entrada para detectar zonas de breakout y reversión; el modelo las utiliza para capturar cambios dinámicos de precio.  
  Relaciones: PARTE_DE → technical analysis (2)

**noise trading** [estrategia] (docs=2) [también: Noise Trading] — Actividad de negociación no basada en información fundamental. En este modelo, una porción del noise trading es sistemática (autorregresiva, predecible) y el informed trader tiene información superior sobre ella.  
  Relaciones: CAUSA → mispricing (1); PARTE_DE → Market Manipulation (1)

**action space** [concepto] (docs=2) [también: Action Space] — Conjunto de acciones permitidas: vender (-k), mantener (0) o comprar (+k) donde k es el número de acciones. El espacio puede ser discreto {-k,...,-1,0,1,...,k}.  
  Relaciones: PARTE_DE → Markov Decision Process (1); REQUIERE → reward function (1)

**state space** [concepto] (docs=2) [también: State Space] — Conjunto de observaciones que el agente recibe del entorno: balance, posiciones, precios (open/high/low/close), volumen de trading e indicadores técnicos como MACD y RSI.  
  Relaciones: PARTE_DE → Markov Decision Process (1)

**MACD** [metrica] (docs=2) — Moving Average Convergence-Divergence, indicador de momentum mencionado como referencia histórica de indicadores de segunda derivada del precio.  
  Relaciones: EQUIVALE_A → momentum (1); PARTE_DE → technical analysis (1)

**momentum ignition** [estrategia] (docs=2) — Práctica de ejecutar grandes volúmenes direccionales durante períodos de baja liquidez para instigar falsos quiebres e incitar compras/ventas de otros operadores por pánico o inercia.  
  Relaciones: CAUSA → momentum (1); USA → momentum (1)

**order imbalance** [metrica] (docs=2) [también: Order Imbalance] — Diferencia entre volumen iniciado por compradores y vendedores, usada en el análisis cross-seccional para estimar el contenido informativo de las transacciones de competidores sobre la empresa anunciante.  
  Relaciones: EQUIVALE_A → order flow imbalance (1); EQUIVALE_A → order flow (1)

**LLM-conditioned volatility** [metodo] (docs=2) [también: LLM-Conditioned Volatility] — Una extensión del modelo base donde el coeficiente de difusión o volatilidad depende directamente del embedding de texto, permitiendo capturar saltos o regímenes heterocedásticos.  
  Relaciones: PARTE_DE → LLM-driven drift SDE (2)

**power-law kernel** [metodo] (docs=2) — Función de decaimiento phi(t) = alpha * (1 + gamma * t)^(-beta) usada como forma paramétrica para los kernels de excitación del Hawkes. El paper encuentra que la power-law es seleccionada el 100% de las veces sobre la exponencial según AIC para datos de AAPL.  
  Relaciones: USA → Hawkes process (1); PARTE_DE → non-parametric calibration (1)

**inhibitory cross-excitation** [fenomeno] (docs=2) [también: inhibitory cross-excitation kernels] — Fenómeno donde ciertos eventos reducen la intensidad de otros eventos en el proceso Hawkes, en vez de excitarlos. Por ejemplo, limit orders in-spread y cancelaciones en el top del lado opuesto tienen efectos inhibitorios mutuos. Se maneja forzando la intensidad total a cero co...  
  Relaciones: PARTE_DE → Hawkes process (1); PARTE_DE → Compound Hawkes Process (1)

**Kyle's Lambda** [metrica] (docs=2) — Coeficiente de regresión de cambios de precio sobre volumen firmado logarítmico, usado como proxy de profundidad de mercado. Valores altos implican poca profundidad y se correlacionan positivamente con PIN (0.5927).  
  Relaciones: MIDE → market impact (1); MIDE → market depth (1)

**EU Burden Sharing Agreement** [dato] (docs=2) [también: EU Burden Sharing Agreement (EU-BSA)] — Acuerdo que establece metas de reducción de emisiones por país: Alemania debe reducir 21% respecto a 1990. Implementado a través del EU-ETS que cubre solo sectores seleccionados (producción de hierro/acero, cemento, vidrio, cerámica, transformación energética, refinerías).  
  Relaciones: REQUIERE → National Allocation Plan (NAP) (2)

**Sniping** [estrategia] (docs=2) — Estrategia de HFT consistente en anticiparse a las órdenes aprovechando ventanas de latencia para obtener beneficio sin riesgo; limitada en el mecanismo batch por el intervalo discreto.  
  Relaciones: USA → latency arbitrage (2); MITIGA → Batch Trading Mechanism (1)

**Difference-in-Differences (DiD)** [metodo] (docs=2) — Metodología econométrica que compara cambios en liquidez, volatilidad y HFQU entre las eras pre-A10 y post-A10 relativo a niveles base.  
  Relaciones: USA → Amendment 10 (A10) (1); MIDE → institutional trading costs (1)

**EU Emissions Trading Scheme (EU ETS)** [concepto] (docs=2) — Sistema cap-and-trade europeo establecido en 2005 donde empresas reciben un límite anual de emisiones en forma de allowances; deben entregar allowances equivalentes a sus emisiones antes del 30 de abril de cada año o pagar multa de 100 euros por tonelada de CO2.

**defensive distillation** [metodo] (docs=2) — Técnica que entrena una red 'estudiante' a partir de las probabilidades suavizadas (softmax con temperatura) de una red 'maestra' para reducir la sensibilidad del modelo a perturbaciones adversariales; se usa temperatura T=20.  
  Relaciones: MITIGA → adversarial attack (2)

**randomized smoothing** [metodo] (docs=2) — Mecanismo de robustez certificada que promedia la política sobre ruido gaussiano añadido al estado (N=100 muestras, sigma=0.1) para suavizar la decisión frente a perturbaciones.  
  Relaciones: MITIGA → adversarial attack (2)

**latency-based adversarial attack** [fenomeno] (docs=2) — Ataque adversarial (LAA) que explota el ciclo de trading 24/7 introduciendo demoras temporizadas en las observaciones de estado para maximizar la disrupción de la política; logra 68.9% de éxito contra agentes sin defensa.  
  Relaciones: PARTE_DE → adversarial attack (2)

**attack success rate** [metrica] (docs=2) — Métrica de robustez adversarial definida como el porcentaje de ejemplos adversariales que causan una reducción de retorno mayor a 20%; el framework propuesto reduce el ASR promedio a 10.3% frente a 74.2% del PPO vanilla.  
  Relaciones: MIDE → adversarial attack (2)

**copula** [metodo] (docs=2) [también: Copula] — Herramienta matemática que separa las distribuciones marginales de la estructura de dependencia entre variables aleatorias, permitiendo modelar dependencias no lineales.  
  Relaciones: USA → Tail Dependence (1)

**Jensen's alpha** [metrica] (docs=2) [también: Jensen's Alpha] — Alpha de Jensen positivo y significativo para hogares finlandeses e instituciones domésticas al comerciar con extranjeros, usando CAPM aumentado por Fama-French.  
  Relaciones: USA → equity beta (1)

**risk aversion** [fenomeno] (docs=2) — Nivel de tolerancia al riesgo del operador modelado en la función de utilidad, el cual afecta inversamente a la amplitud (distancia) óptima de los stops.

**transaction price** [metrica] (docs=2) [también: Transaction Price] — Precio de transacción observado en trades, usado como medida de precio alternativa al midpoint; los precios de transacción de un activo lideran los retornos de midpoint de otros activos.  
  Relaciones: PARTE_DE → Cross-Asset Lead-Lag (1)

**portfolio allocation** [estrategia] (docs=2) [también: Portfolio Allocation] — Uno de los tres casos de uso demostrados en FinRL, donde el agente DRL asigna pesos de cartera entre múltiples activos para maximizar retorno ajustado por riesgo.  
  Relaciones: USA → deep reinforcement learning (1)

**GAN** [metodo] (docs=2) [también: GANs] — Generative Adversarial Networks aplicadas a generación de escenarios de mercado. El paper destaca TimeGAN, Tail-GAN y VolGAN como ejemplos que alinean el objetivo generativo con restricciones financieras (arbitrage-free surfaces, tail risk estimation).  
  Relaciones: REQUIERE → no-arbitrage pricing (1)

**Herfindahl-Hirschman Index** [metrica] (docs=2) [también: Herfindahl-Hirschman index] — Métrica basada en participaciones de volumen para cuantificar el nivel en el que las transacciones están divididas entre los mercados primarios y alternativos.  
  Relaciones: MIDE → market fragmentation (1)

**trade string** [metodo] (docs=2) [también: Trade Strings] — Técnica heurística para reconstruir la ejecución de órdenes institucionales fragmentadas mediante la agrupación de transacciones consecutivas unidireccionales de un participante realizadas con poco tiempo de separación.  
  Relaciones: MIDE → informed trading (1)

**empirical risk minimization** [metodo] (docs=2) [también: Empirical risk minimization (ERM)] — Procedimiento estadístico y de aprendizaje automatizado aplicado a una discretización Euler-Maruyama del proceso, utilizado para aprender y estimar los parámetros del modelo de drift con los features textuales.  
  Relaciones: APLICA_A → LLM-driven drift SDE (1)

**Minimum Resting Times** [concepto] (docs=2) [también: Minimum Resting Time (MRT)] — Requisito de tiempo mínimo que una orden debe permanecer en el libro antes de poder ser cancelada o modificada. Deutsche Bank Super X: no matchea órdenes stale por más de 1 segundo. Protege a liquidity providers pasivos contra arbitrageurs rápidos.  
  Relaciones: MITIGA → Dark Pool Latency Arbitrage (1)

**Delta-Neutral Strategy** [estrategia] (docs=2) — Estrategia que requiere posiciones largas y cortas con igual número de acciones en ambas patas del par, manteniendo neutralidad de mercado durante el horizonte de trading.  
  Relaciones: EQUIVALE_A → market neutral (1)

**Generalized Ornstein-Uhlenbeck Process** [concepto] (docs=2) [también: Generalized Ornstein-Uhlenbeck (OU) Process] — Proceso estocástico de reversión a la media extendido con media variable en el tiempo µ(t) y conducido por un proceso Lévy estable Lt en lugar de movimiento Browniano: dXt = -α(Xt - µ(t))dt + dLt.  
  Relaciones: USA → Lévy Stable Distribution (1)

**Lévy Stable Distribution** [concepto] (docs=2) [también: Levy Stable Distribution] — Familia de distribuciones con colas pesadas caracterizadas por parámetros de estabilidad (α_L) y asimetría (β_L), que modelan mejor los shocks extremos de mercado que las distribuciones Gaussianas.

**Dynamic Volatility Targeting** [estrategia] (docs=2) — Overlay que escala tamaño de posición diariamente basado en volatilidad realizada del portafolio de 60 días, apuntando a riesgo anualizado constante de 10%.  
  Relaciones: APLICA_A → ARCANA (Adaptive Regime-Constrained Arbitrage with Normalised Allocation) (1)

**ETF-Based Statistical Arbitrage** [estrategia] (docs=2) — Estrategia donde cada acción se regresa contra el ETF de su sector (ej. BBH para biotech). Los residuos de la regresión son la señal: residuo negativo = acción barata (long), residuo positivo = acción cara (short). Generalización natural del pairs trading.

**Hybrid carbon regulation** [concepto] (docs=2) — Esquema donde el mercado de emisiones se segmenta en un mercado internacional (EU-ETS, sectores DIR) y múltiples mercados domésticos (sectores NDIR), destruyendo la eficiencia de mecanismos de mercado descentralizados porque el regulador debe conocer perfectamente el precio in...

**DIR vs NDIR sectors** [concepto] (docs=2) — Sectores cubiertos por la Directiva EU-ETS (DIR: hierro/acero, cemento, vidrio, cerámica, generación eléctrica, refinerías) vs sectores no cubiertos (NDIR: resto de la economía doméstica como transporte). Para Alemania en 2005: DIR = 131.24 MtC, NDIR = 91.20 MtC de un total de...  
  Relaciones: PARTE_DE → Hybrid carbon regulation (2)

**High-Frequency Market Maker (HFM)** [concepto] (docs=2) — Rol dentro del juego de tres niveles: el HFT que gana la competencia para ser market maker y contra el cual todos los demás participantes comercian exclusivamente.  
  Relaciones: PARTE_DE → Three-Tiered Game Model (2)

**High-Frequency Investor (HFI)** [concepto] (docs=2) — HFTs que no logran ser market maker y actúan como inversores, pudiendo enviar órdenes en cualquier momento durante el intervalo del batch con una latencia de respuesta pequeña.  
  Relaciones: PARTE_DE → Three-Tiered Game Model (2)

**Optimal Batch Interval** [metrica] (docs=2) — Intervalo que maximiza el bienestar total; en el modelo multiperíodo, el bienestar por unidad de tiempo disminuye al aumentar el intervalo del batch y la latencia de los HFTs se vuelve inefectiva.  
  Relaciones: MIDE → Market Welfare (2)

**Optimal Currency Area** [concepto] (docs=2) — Teoría de Mundell (1961) que constituye la base teórica para evaluar los beneficios de la integración monetaria regional.  
  Relaciones: APLICA_A → Trading Bloc Exchange (TBE) (1)

**Compliance Pressure** [fenomeno] (docs=2) — Presión inducida por el deadline anual de cumplimiento que convierte al EU ETS en un mercado periódicamente estresado, afectando frecuencia y estrategia de trading.  
  Relaciones: CAUSA → Trading Frequency (2)

**profit factor** [metrica] (docs=2) — Ratio de ganancias brutas sobre pérdidas brutas; usado como métrica central de comparación entre la estrategia propuesta y el benchmark de cruce de EMAs.

**hit ratio** [metrica] (docs=2) [también: Hit ratio] — Porcentaje de predicciones correctas (dirección y magnitud superior a un umbral) sobre el total de oportunidades de trading ejecutadas en el conjunto de validación.

**loss aversion** [fenomeno] (docs=2) — Inclinación a sufrir un impacto psicológico mayor ante pérdidas que ante ganancias equivalentes, medido mediante un instrumento de Holt & Laury.

**Market Order Imbalance** [metrica] (docs=2) [también: Market Order (MO) Imbalance] — Diferencia entre órdenes de mercado iniciadas por compradores y vendedores. Solo los surprises (cambios inesperados) en el order flow contienen información. Su poder predictivo cae 36.53% con más algorithmic trading.

**duplicate paper** [concepto] (docs=2) [también: Duplicate Paper] — Este documento es un duplicado exacto del paper 0226 con SSRN ID 2695705 en lugar de 2403000. El contenido es idéntico: mismo título, mismos autores, mismas secciones, mismas conclusiones empíricas sobre limit order flows y market order flows en FX y equities.

**VWAP Benchmark Trading** [concepto] (docs=2) — Problema de ejecución donde un broker debe ejecutar una orden grande minimizando la diferencia entre el precio promedio de ejecución y el VWAP del mercado en el mismo intervalo, enfrentando un trade-off entre market orders (certeza, coste de spread) y limit orders (ahorro, inc...

**Forward-Backward Boundaries** [metodo] (docs=2) — Par de fronteras óptimas dependientes del tiempo (L̃_t ≤ v_t ≤ M̃_t) que definen la región de no-trading: se colocan limit orders hasta la frontera forward (L̃_t) y se disparan market orders al alcanzar la frontera backward (M̃_t).

**Non-Linear Rational Expectations Equilibrium (REE)** [metodo] (docs=2) — Método de solución de REE usando función implícita de precios P = P(s, D_ui) donde el precio es función de variables de estado y la demanda del uninformed. Evita conjeturar forma explícita de la función de precio y separa el efecto información del efecto sustitución.

**Gate Closure** [concepto] (docs=2) — Punto temporal antes de la entrega física donde el trading bilateral voluntario cesa y el operador del sistema se vuelve contraparte de cualquier transacción en tiempo real subsecuente. Marca la frontera entre forward markets y el balancing market.

**Fulfillment factor (lambda)** [metrica] (docs=2) — Fracción de emisiones business-as-usual que se asigna gratuitamente como allowances a los sectores DIR. Lambda* es el valor eficiente; desviaciones generan pérdidas de eficiencia. Para Alemania, lambda negociado = 1, mientras que lambda* es menor para todos los precios de CO2 ...

**Marginal Abatement Cost (MAC) curves** [metodo] (docs=2) — Curvas polinómicas de tercer grado que representan los costos marginales de reducir emisiones de carbono por sector: -C_i'(e_i) = a_{1,i}(e_{0i} - e_i) + a_{2,i}(e_{0i} - e_i)^2 + a_{3,i}(e_{0i} - e_i)^3. Calibradas con el modelo CGE PACE usando datos GTAP5 para Alemania.

**PACE model** [metodo] (docs=2) — Modelo de equilibrio general computable multi-sector y multi-región de comercio internacional y uso de energía usado para generar observaciones discretas de costos marginales de abatimiento que luego se ajustan por mínimos cuadrados a curvas polinómicas.

**order book dynamics model** [metodo] (docs=1) — Modelo estocástico continuo del libro de órdenes que balancea facilidad de estimación, realismo empírico y tratabilidad analítica, modelando eventos de mercado como procesos de Poisson independientes.  
  Relaciones: USA → limit order book (1); MEJORA_A → equilibrium models of limit order books (1); PREDICE → direction of price moves (1)

**non-stationary model for statistical arbitrage trading** [estrategia] (docs=1) — Modelo propuesto en el paper donde el log-precio del activo sintético St = Xt + Mt es la suma de un proceso Ornstein-Uhlenbeck (Xt) y un movimiento Browniano aritmético (Mt); define una estrategia continua de trading con bandas b1<b2 sobre Xt.  
  Relaciones: USA → Ornstein-Uhlenbeck process (1); USA → arithmetic Brownian motion (1); MIDE → signal-to-noise ratio (1)

**Markovian Activation Function** [metodo] (docs=1) — Función de activación de la red neuronal definida como una puerta de transición markoviana consistente con las ecuaciones de Chapman-Kolmogorov, que reemplaza las activaciones deterministas de las redes convencionales por probabilidades de transición entre estados de mercado.  
  Relaciones: USA → Chapman-Kolmogorov equations (1); APLICA_A → no-arbitrage pricing (1); MEJORA_A → Monte Carlo simulation (1)

**abnormal algorithmic trading** [metrica] (docs=1) — Diferencia entre el nivel de un proxy de AT en la ventana de evento (pre o post anuncio) y su nivel en una ventana de línea base específica de la firma, análoga a la construcción de retornos anormales en estudios de eventos; aísla la variación específica del evento respecto de...  
  Relaciones: PREDICE → informational gap (1); MEJORA_A → raw algorithmic trading level (1); MITIGA → backtest overfitting (1)

**PIN** [metrica] (docs=1) — Probability of Informed Trading, métrica del modelo EKOP (Easley, Kiefer, O'Hara, Paperman 1996) que mide cómo la información privada afecta los precios a través del desbalance de órdenes. El paper demuestra que la estimación de PIN es sensible al parámetro delta (probabilidad...  
  Relaciones: MIDE → informed trading (1); USA → order flow imbalance (1); PARTE_DE → EKOP model (1)

**weighted microprice momentum** [estrategia] (docs=1) — Indicador central del paper: WMPM = SLP + γ×(EM − SLP), que mezcla el precio de liquidez pasiva multi-nivel con el momentum de ejecuciones, ponderado por un factor dinámico, para predecir movimientos de precio de muy corto plazo.  
  Relaciones: USA → standing liquidity price (1); USA → execution momentum (1); USA → dynamic scaling factor (1); MEJORA_A → microprice (1)

**optimal investment strategy** [estrategia] (docs=1) — Solución en forma cerrada (afín en el factor de co-integración) al problema de control estocástico de un agente con utilidad exponencial que maximiza la utilidad esperada de la riqueza terminal operando dinámicamente activos co-integrados.  
  Relaciones: USA → cointegration (1); USA → short-term alpha (1); MEJORA_A → Merton portfolio (1)

**administered pricing** [riesgo_metodologico] (docs=1) — Régimen en el que la autoridad monetaria fija el tipo de cambio oficial y una banda de cotización permitida alrededor de este, actuando como un techo/piso de precio que genera no clearing de mercado y distorsiona las señales de precio.  
  Relaciones: CAUSA → market liquidity (1); CAUSA → parallel market (1); MITIGA → price discovery (1)

**Black-Scholes-Merton model** [metodo] (docs=1) — Modelo de valuación de opciones europeas que da una solución cerrada bajo supuestos de volatilidad constante, sin fricciones y difusión continua; es la base de la mayoría de los modelos de pricing de derivados posteriores.  
  Relaciones: USA → geometric Brownian motion (1); USA → risk-neutral valuation (1); REQUIERE → constant volatility (1)

**dual-model alpha system** [estrategia] (docs=1) — Sistema de generación de señales que combina la predicción de estado del HMM con la predicción de precio de la red neuronal; solo emite señal cuando ambos modelos coinciden en la dirección.  
  Relaciones: USA → hidden Markov model (1); USA → feedforward neural network (1); REQUIERE → signal consensus (1); USA → Black-Litterman model (1)

**market microstructure invariants** [concepto] (docs=1) — Principio de modelización que postula que las características microestructurales que varían en tiempo calendario se vuelven constantes ('invariantes') cuando se miden en tiempo de negocio. Implica que la distribución de transferencias de riesgo, costos de transacción, precisió...  
  Relaciones: APLICA_A → market microstructure (1); USA → business time (1); USA → trading activity (1); PREDICE → square-root law (1)

**firm characteristics similarity** [metodo] (docs=1) — Medida (FCS) construida a partir de 81 características de la firma que cuantifica la cercanía fundamental entre dos acciones de un par, ponderando cada característica por su importancia (coeficiente elastic net) en explicar los retornos de pairs trading.  
  Relaciones: USA → elastic net regression (1); MITIGA → non-convergence risk (1); MEJORA_A → pairs trading (1)

**option pricing expansion** [metodo] (docs=1) — Expansión cerrada del precio de una opción en términos del precio Black-Scholes y Greeks de orden superior, aplicable a modelos con dinámicas gobernadas por movimientos Brownianos con cambio de tiempo (saltos y volatilidad estocástica).  
  Relaciones: APLICA_A → stochastic volatility (1); APLICA_A → jump-diffusion model (1); USA → Taylor series expansion (1)

**Walk-Forward Optimization** [metodo] (docs=1) — Recalibración dinámica de parámetros de estrategia mediante ventanas rodantes de entrenamiento y testeo, usando solo información disponible hasta cada punto para mitigar sesgo de anticipación y evaluar robustez fuera de muestra.  
  Relaciones: MITIGA → look-ahead bias (1); MITIGA → backtest overfitting (1); SE_OPONE_A → combinatorial purged cross-validation (1); USA → Sharpe ratio (1)

**Level 4 order book data** [dato] (docs=1) — Extensión de los datos Level 3 convencionales que agrega identificadores pseudónimos de traders, intentos de órdenes rechazadas y de cancelación fallidos, e información de contraparte para cada trade, con timestamps de precisión nanosegundo.  
  Relaciones: PARTE_DE → limit order book (1); REQUIERE → non-validating blockchain node (1)

**market microstructure model** [metodo] (docs=1) — Modelo de equilibrio de expectativas racionales (RE) del spot rate FX con dealers de aversión al riesgo CARA, brokers pasivos y una plataforma centralizada de subastas walrasianas, usado para derivar cómo la intervención cambiaria se transmite a precios y condiciones de mercado.  
  Relaciones: USA → rational expectations equilibrium (1)

**electronic trading** [concepto] (docs=1) — Modalidad de negociación fuera del piso físico que permite a un market-maker operar en múltiples productos simultáneamente, a diferencia del open-outcry.  
  Relaciones: SE_OPONE_A → open-outcry trading (1); MEJORA_A → open-outcry trading (1)

**empirical mean reversion time** [metrica] (docs=1) — Métrica model-free propuesta por el paper que mide el tiempo promedio que tarda una serie en volver a su media desde un extremo local significativo; se usa para seleccionar coeficientes de un spread multi-activo minimizando este tiempo, sin asumir ningún proceso estocástico.  
  Relaciones: MIDE → mean reversion (1); MEJORA_A → Ornstein-Uhlenbeck process (1); USA → grid search (1)

**institution level order flow** [concepto] (docs=1) — Order flow desagregado por identidad codificada de cada institución participante (en vez de sumado en un flujo agregado), construido a partir de volumen de mercado y de límite ejecutado por institución.  
  Relaciones: MEJORA_A → order flow imbalance (1)

**persona bias** [riesgo_metodologico] (docs=1) — Fenómeno donde un agente del debate domina sistemáticamente las decisiones a través de estructura retórica más que por calidad de evidencia, sesgando el resultado final.  
  Relaciones: MITIGA → debate constitution (1); CAUSA → consensus illusion (1)

**event-driven backtesting** [metodo] (docs=1) — Simulación realista de ejecución de órdenes trade a trade, estrictamente secuencial, que replica un sistema de order routing real con constraints de cash y exposición; el paper la contrapone al backtesting tensorial (vectorizado).  
  Relaciones: USA → trading journal (1); SE_OPONE_A → tensor-based backtesting (1); USA → transaction costs (1)

**VPIN** [metrica] (docs=1) — Volume-Synchronised Probability of Informed Trading: proxy volumétrico de toxicidad de flujo basado en desbalance de volumen por bucket sincronizado por volumen. Estándar industrial desde Easley et al. (2012), pero limitado a una ratio de desbalance sin capturar geometría del ...  
  Relaciones: MIDE → informed trading (1); USA → trade sign (1)

**execution rate** [metrica] (docs=1) — Tasa de ejecución I = dv/dt: número de acciones negociadas por unidad de tiempo. Es el concepto central de la teoría de dinámica de mercado de los autores, considerado el factor clave que define la dinámica del mercado de renta variable estadounidense y la driving force detrás...  
  Relaciones: CAUSA → volatility (1); MIDE → market liquidity (1); USA → price support (1); USA → P&L dynamics (1)

**trading activity** [metrica] (docs=1) — Producto del volumen esperado en dólares (P·V), la volatilidad de retornos (σ) y el precio de la acción, definido como W := σ · P · V. Mide el riesgo agregado en dólares transferido por todos los bets durante un día calendario. Es la variable macroscópica observable a partir d...  
  Relaciones: USA → market microstructure invariants (1); MIDE → business time (1); PREDICE → betting volume (1); PREDICE → order size distribution (1)

**funding risk** [riesgo_metodologico] (docs=1) — Riesgo derivado de que el dealer deba pedir prestado o prestar efectivo a tasas distintas de la tasa libre de riesgo (LIBOR ya no es un buen proxy tras la crisis) para financiar la cobertura de un trato de derivados.  
  Relaciones: CAUSA → funding valuation adjustment (1); MITIGA → collateralization (1)

**composite score** [metodo] (docs=1) — Suma ponderada de volatilidad, retorno y sentimiento por acción, con pesos normalizados y jerárquicos (volatilidad>retorno>sentimiento), usada para rankear y seleccionar acciones/pares.  
  Relaciones: USA → sentiment analysis (1); USA → random forest (1); PARTE_DE → pairs trading (1)

**path-dependent diagnostics** [concepto] (docs=1) — Segunda capa inferencial del framework compuesta por MFE, MAE, maximum drawdown y longest losing streak de la curva de equity en R, con valores benchmark bajo la nula de edge cero.  
  Relaciones: PARTE_DE → R-multiple (1); USA → zero-edge null hypothesis (1)

**Glosten-Milgrom model** [concepto] (docs=1) — Modelo secuencial de un activo binario donde el market maker fija bid y ask actualizando su creencia bayesiana tras cada operación, en función de si el trader es informado o no.  
  Relaciones: USA → adverse selection (1); PARTE_DE → market microstructure noise (1); PREDICE → bid-ask spread (1)

**standardized price jump** [metrica] (docs=1) — Medida generalizada del price jump que cuantifica la proporción de información revelada en el anuncio respecto de la información total acumulable, definida para todo patrón de retornos (incluye reversiones), acotada inferiormente en cero y sin necesidad de truncar la muestra.  
  Relaciones: MEJORA_A → Weller's price jump (1); MIDE → informational gap (1); USA → cumulative abnormal return (1)

**meta-learner spine** [metodo] (docs=1) — Capa de inteligencia adaptativa central que actualiza continuamente los pesos de contribución de cada módulo de estrategia según performance, sensibilidad a drawdown y compatibilidad de régimen, combinando reinforcement learning y actualización bayesiana.  
  Relaciones: USA → reinforcement learning (1); USA → Bayesian updating (1); MITIGA → backtest overfitting (1)

**Markov Perfect Equilibrium** [concepto] (docs=1) — Perfil de políticas π* donde cada agente maximiza su payoff descontado esperado usando políticas medibles respecto al estado de representación y su estado privado, sin incentivo a desviarse unilateralmente.  
  Relaciones: PARTE_DE → Representation-Induced Stochastic Game (1); REQUIERE → Representation Filtration (1)

**liquidity shock** [fenomeno] (docs=1) — Evento que reduce transitoriamente la utilidad de mantener el activo para todos los inversores (de alta a baja valoración). Los inversores revierten a alta valoración a tasa Poisson gamma. La severidad del shock delta determina la caída inicial de precio y el tiempo de recuper...  
  Relaciones: CAUSA → bid-ask spread (1); APLICA_A → limit order book (1)

**Stochastic Optimization** [metodo] (docs=1) — Marco de programación matemática que incorpora parámetros probabilísticos para tomar decisiones secuenciales bajo incertidumbre. En carteras de crédito se implementa mediante programación en dos etapas o multi-etapa, usando generadores de escenarios económicos para simular tas...  
  Relaciones: USA → Monte Carlo simulation (1); MEJORA_A → Mean-Variance Optimization (1); REQUIERE → stress testing (1)

**Probability of Default** [metrica] (docs=1) — Parámetro central de riesgo crediticio que estima la probabilidad de que un prestatario incumpla sus obligaciones en un horizonte temporal definido. Junto con LGD y EAD, forma la tríada de inputs del enfoque IRB (Internal Ratings-Based) de Basilea II. Se estima mediante modelo...  
  Relaciones: PREDICE → Credit Scoring (1); USA → Machine Learning Classifier (1)

**partial adjustment with noise model** [metodo] (docs=1) — Modelo en el que los precios de mercado se ajustan parcialmente hacia sus valores intrínsecos con ruido i.i.d. La ecuación P(i,t)-P(i,t-1)=g(i){V(i,t)-P(i,t-1)}+u(i,t) captura la velocidad de ajuste g(i). Combinado con un proceso general para V(i,t) permite estimar conjuntamen...  
  Relaciones: USA → intrinsic value process (1); REQUIERE → speed of adjustment (1); EQUIVALE_A → ARMA(1,X) model (1)

**market dynamics** [concepto] (docs=1) — Enfoque de estudio del mercado centrado en variables dependientes del tiempo (precios, medias móviles, spreads, volatilidad) tal como lo usan los practitioners, en contraposición al enfoque estadístico que calcula características agregadas sobre escalas temporales fijas. Los a...  
  Relaciones: SE_OPONE_A → statistical equilibrium (1); REQUIERE → execution rate (1); APLICA_A → limit order book (1)

**competitive allocation mechanism** [concepto] (docs=1) — Mecanismo de asignación de referencia (triple µc, Mc, gc) donde los precios se toman como dados y se determinan por el subastador walrasiano. Su espacio de mensajes es N-dimensional, donde N es el número de tipos de consumidores, y es el único mecanismo informacionalmente efic...  
  Relaciones: EQUIVALE_A → Walrasian auctioneer (1); REQUIERE → message space dimensionality (1)

**AlphaQuant framework** [metodo] (docs=1) — Framework end-to-end que integra síntesis de features vía LLM, extracción paralelizada, y evaluación/ranking iterativo con AutoML organizados como un state graph cíclico.  
  Relaciones: USA → AutoML (1); USA → time-series cross-validation (1); USA → LLM-driven feature engineering (1)

**Dickey-Fuller test** [metodo] (docs=1) — Test de raíz unitaria (ADF) usado tradicionalmente para determinar si el residuo de la regresión de cointegración es estacionario; el paper muestra que tiene bajo poder estadístico frente a otras alternativas.  
  Relaciones: USA → cointegration (1); SE_OPONE_A → Phillips-Perron test (1)

**OTC derivative valuation** [concepto] (docs=1) — Marco de valuación general (arbitrage-free) para tratos OTC bajo colateralización, riesgo de crédito de contraparte y costos de funding, derivado a partir del principio de pricing risk-neutral.  
  Relaciones: USA → least-squares Monte Carlo (1); REQUIERE → collateralization (1)

**realistic trading simulation** [metodo] (docs=1) — Plataforma de simulación (Java, arquitectura de plugins de reglas, cuentas separadas long/short/transacción) que incorpora costos, ejecución al cierre, rebalanceo dinámico y reglas de riesgo; el paper la propone como metodología superior al CAR para evaluar estrategias.  
  Relaciones: MEJORA_A → cumulative abnormal return methodology (1); USA → transaction costs (1); MITIGA → backtest overfitting (1)

**Kullback-Leibler divergence** [metodo] (docs=1) — Medida de disimilitud entre medidas de probabilidad (relative entropy), siempre positiva y cero solo si las medidas coinciden; se usa para penalizar la elección de un escenario Q distinto del estimado P, regulando cuánto se aparta la regla de trading del modelo calibrado según...  
  Relaciones: MIDE → model uncertainty (1); USA → optimal stopping (1)

**optimal stopping** [metodo] (docs=1) — Problema matemático de encontrar el tiempo de parada óptimo que maximiza el valor esperado de un proceso; en este paper se resuelve incorporando incertidumbre de modelo para identificar el punto más divergente del valor medio de reversión (frontera de salida) de un spread.  
  Relaciones: USA → Ornstein-Uhlenbeck process (1); APLICA_A → statistical arbitrage (1)

**variance swap** [concepto] (docs=1) — Contrato forward sobre la varianza realizada anualizada del activo subyacente; ofrece exposición a varianza sin necesidad de delta-hedging, a diferencia de comprar/vender opciones vanilla.  
  Relaciones: USA → quadratic variation (1); APLICA_A → dispersion trading (1); MEJORA_A → delta hedging (1)

**fire sale** [fenomeno] (docs=1) — Liquidación forzada de activos ilíquidos por parte de bancos para cubrir un shortfall de caja, cuyo propio volumen deprime el precio obtenido (impacto de mercado endógeno).  
  Relaciones: CAUSA → market impact (1); PARTE_DE → systemic risk (1)

**Limit Order Book Based Price** [concepto] (docs=1) — Esquema de pricing (denominado LOB en el paper) en el que todos los bancos colocan órdenes a la misma velocidad, por lo que quienes venden menos volumen terminan antes y obtienen mejor precio que quienes venden más y siguen erosionando el libro.  
  Relaciones: SE_OPONE_A → VWAP (1); PARTE_DE → limit order book (1); USA → order book density function (1)

**Nash equilibrium** [metodo] (docs=1) — Marco de solución del modelo: cada banco elige su estrategia de liquidación/préstamo óptima dada la estrategia de los demás; el paper prueba existencia vía teorema de punto fijo de Brouwer/Kakutani y condiciones de unicidad vía Banach y Tarski.  
  Relaciones: USA → fire sale (1); APLICA_A → market impact (1)

**constant volatility** [riesgo_metodologico] (docs=1) — Supuesto central de Black-Scholes de que la volatilidad del activo permanece fija en el tiempo; el paper lo señala como la limitación más importante frente a mercados reales.  
  Relaciones: CAUSA → volatility smile (1); MITIGA → stochastic volatility model (1)

**R-multiple** [concepto] (docs=1) — Unidad de medida de resultado de trade normalizada por el riesgo inicial (stop-loss), usada en lugar del retorno de portfolio para evaluar sistemas retail con riesgo fijo por operación.  
  Relaciones: USA → expectancy (1); SE_OPONE_A → Sharpe ratio (1)

**post-selection adjustment** [metodo] (docs=1) — Corrección aplicada al umbral de significancia de R acumulado cuando el setup reportado fue elegido entre múltiples variantes (entradas, filtros, reward-to-risk, reglas de gestión), elevando el umbral de evidencia requerido.  
  Relaciones: MITIGA → backtest overfitting (1); USA → cumulative-R significance threshold (1); EQUIVALE_A → Deflated Sharpe Ratio (1)

**Laplace transform inversion** [metodo] (docs=1) — Técnica de la literatura de colas usada para calcular semi-analíticamente probabilidades condicionales de eventos del book (movimiento de precio, ejecución) sin recurrir a simulación de Monte Carlo.  
  Relaciones: MEJORA_A → Monte Carlo simulation (1); PREDICE → direction of price moves (1); REQUIERE → birth-death process (1)

**direction of price moves** [fenomeno] (docs=1) — Probabilidad de que el próximo cambio en el mid-price sea un incremento, condicional a la configuración del book (cantidades en bid/ask y spread), calculable con el modelo.  
  Relaciones: USA → queue position (1); PARTE_DE → order book dynamics model (1)

**stochastic partial differential equation model** [metodo] (docs=1) — Ecuación en derivadas parciales estocástica con ruido multiplicativo que describe la evolución de la densidad centrada del libro de órdenes u_t(x), combinando términos de convección, difusión y cancelación proporcional.  
  Relaciones: USA → limit order book (1); MEJORA_A → queueing system model (1); APLICA_A → market making (1)

**distance method** [metodo] (docs=1) — Método clásico de formación de pares que selecciona los activos que minimizan la suma de desviaciones cuadradas (SSD) entre sus series de precios normalizadas; luego opera cuando el spread se desvía más de dos desviaciones estándar históricas.  
  Relaciones: PARTE_DE → pairs trading (1); SE_OPONE_A → empirical mean reversion time (1)

**algorithmic trading deters information acquisition** [fenomeno] (docs=1) — El AT detecta el order flow informado, opera en la misma dirección (back-running) y erosiona las rentas económicas extraíbles por traders informados, desincentivando la adquisición de información privada.  
  Relaciones: CAUSA → informational gap (1); USA → back running (1); MITIGA → informed trading (1)

**opportunistic algorithmic trading** [concepto] (docs=1) — Subconjunto de AT que demanda liquidez y explota oportunidades de arbitraje de latencia y estrategias de order anticipation (back-running); el paper muestra que este tipo específico deteriora la sensibilidad inversión-precio pese a que el AT agregado la mejora.  
  Relaciones: SE_OPONE_A → market making (1); MITIGA → Revelatory Price Efficiency (1); USA → latency arbitrage (1)

**CARA exponential utility market making model** [metodo] (docs=1) — Modelo de sizing óptimo de órdenes bid/ask derivado de maximizar una función de utilidad exponencial (equivalente a media-varianza bajo normalidad), parametrizado por spread, volatilidad, tiempo de tenencia esperado, impacto de mercado y aversión al riesgo.  
  Relaciones: USA → inventory risk (1); USA → market impact (1); APLICA_A → market making (1); EQUIVALE_A → mean-variance utility function (1)

**positioning profit** [metrica] (docs=1) — Componente del PnL atribuible a los movimientos favorables o desfavorables del precio sobre el inventario sostenido; en el paper resultó negativo en promedio, evidenciando desventaja informacional del market maker frente a traders humanos.  
  Relaciones: SE_OPONE_A → spread profit (1); MIDE → inventory risk (1)

**crisis mode operating system** [estrategia] (docs=1) — Submódulo que ajusta dinámicamente exposición, ponderación de señales y comportamiento de ejecución cuando se detectan condiciones de crisis, operando en tres fases: Shock, Instability y Stabilization.  
  Relaciones: MITIGA → liquidity fluctuation (1); USA → correlation compression (1); SE_OPONE_A → risk-on/risk-off (1)

**trade length** [metrica] (docs=1) — Duración total del ciclo de trade (entrada a en Xt hasta volver a a pasando por la salida m), es una variable aleatoria cuya media y varianza determinan la frecuencia de trading y por ende el retorno por unidad de tiempo.  
  Relaciones: PREDICE → expected return (1); USA → first-passage time (1)

**expected return** [metrica] (docs=1) — Retorno esperado de la estrategia por unidad de tiempo, calculado como el retorno por trade multiplicado por la frecuencia esperada de trades (inversa de la duración esperada del trade), función de los niveles de entrada, salida y costo de transacción.  
  Relaciones: USA → trade length (1); MEJORA_A → asymmetric trading bands (1); REQUIERE → transaction costs (1)

**stochastic optimal control** [metodo] (docs=1) — Control óptimo estocástico con PDE Hamilton-Jacobi-Bellman usada para derivar políticas óptimas de market making y liquidación. La versión robusta incorpora un término de penalización de entropía relativa para modelar la aversión a la ambigüedad.  
  Relaciones: APLICA_A → market making (1); USA → Hamilton-Jacobi-Bellman equation (1)

**quantitative trading** [concepto] (docs=1) — Uso de modelos matemáticos y algoritmos para analizar datos financieros e identificar oportunidades, ejecutando operaciones automáticamente basadas en reglas predeterminadas.

**model reflexivity** [fenomeno] (docs=1) — Fenómeno donde los participantes del mercado alteran su comportamiento basándose en las acciones anticipadas de los modelos, creando bucles de retroalimentación que invalidan las predicciones. Es uno de los 'Mulas Financieros' que rompen los modelos cuantitativos.  
  Relaciones: CAUSA → regime shifts (1); SE_OPONE_A → backtest overfitting (1)

**Order Book Shape** [concepto] (docs=1) — Perfil de densidad de órdenes límite en función del nivel de precio, con componentes separados para el lado de compra (buy-side shape) y venta (sell-side shape). El límite hidrodinámico produce ODEs que describen estos perfiles.  
  Relaciones: PARTE_DE → limit order book (1); PREDICE → market impact (1)

**changing market conditions** [fenomeno] (docs=1) — Cambios estructurales en la dinámica del mercado que invalidan estrategias previamente rentables. El paper documenta un shift estructural en la autocorrelación de retornos diarios del S&P 500 alrededor de 1997, pasando de positiva y significativa a mayormente negativa, lo que ...  
  Relaciones: CAUSA → backtest overfitting (1); SE_OPONE_A → data snooping (1)

**limit order** [concepto] (docs=1) — Orden no ejecutada inmediatamente que permanece en el libro a un precio específico. En el modelo, los inversores de baja valoración que llegan temprano colocan limit sell orders a precios altos (ejecución tardía); los que llegan más tarde van undercutting con precios progresiv...  
  Relaciones: SE_OPONE_A → market order (1); PARTE_DE → limit order book (1)

**multi-objective optimization** [metodo] (docs=1) — Formulación de la formación de pares como un problema con objetivos contrapuestos: minimizar cointegración (riesgo) y maximizar volatilidad del spread y número de cruces por cero (beneficio). Resuelto con algoritmos genéticos elitistas NSGA II (2 objetivos) y NSGA III (4 objet...  
  Relaciones: USA → NSGA II (1); USA → genetic algorithm (1); MEJORA_A → pairs trading (1)

**NSGA II** [metodo] (docs=1) — Algoritmo genético elitista de referencia para optimización multi-objetivo con 2 funciones objetivo. En este paper se usa con población de 50 individuos, 80 generaciones, selección por torneo y crossover de dos puntos para formar pares bi-objetivo (BOUV, BOMV).  
  Relaciones: PARTE_DE → genetic algorithm (1); APLICA_A → multi-objective optimization (1); USA → pairs trading (1); MEJORA_A → cointegration (1)

**Copula Dependency Modeling** [metodo] (docs=1) — Técnica matemática que construye distribuciones multivariadas acoplando distribuciones marginales individuales mediante una función cópula. En riesgo crediticio, modela el comportamiento conjunto de defaults entre obligados. La cópula Gaussiana es la más usada por simplicidad ...  
  Relaciones: MIDE → Tail Dependence (1); USA → Monte Carlo simulation (1); MEJORA_A → Mean-Variance Optimization (1)

**Conditional VAE** [metodo] (docs=1) — Autoencoder variacional condicionado por el vector θτ del MMHP (intensidad basal µ, norma del kernel ∥ϕ∥₁ y probabilidad de régimen crítico P(Zτ=1)). El conditioning guía al encoder/decoder para proyectar snapshots del libro de órdenes de forma distinta según el régimen estocá...  
  Relaciones: USA → Markov-modulated Hawkes process (1); MEJORA_A → Variational Autoencoder (1); APLICA_A → anomaly detection (1)

**microstructure effects** [concepto] (docs=1) — Efectos de microestructura del mercado (bid-ask bounce, price dispersion, price impact, realized volatility intradía) que influyen significativamente en la volatilidad del subyacente y, por ende, en el desempeño de los pares de opciones. Exhiben persistencia y pueden aprovecha...  
  Relaciones: CAUSA → volatility (1); PARTE_DE → realized volatility (1)

**volume disbalance** [metrica] (docs=1) — Indicador de desbalance relativo de volumen en los mejores niveles del libro: η = (Vbest_sell − Vbest_buy)/(Vbest_sell + Vbest_buy). Los autores muestran que tiene una normalización defectuosa porque elimina los spikes (la información más relevante), y su interpretación es amb...  
  Relaciones: MIDE → order book depth (1); USA → price support (1); USA → liquidity attractor (1); CONTRADICE_A → price formation (1)

**price support** [fenomeno] (docs=1) — Interpretación tradicional del volumen en el libro de órdenes como soporte de precio: el lado con mayor volumen en el mejor nivel proporciona resistencia al movimiento de precio en esa dirección, requiriendo mayor volumen negociado para atravesarlo. Los autores muestran que es...  
  Relaciones: SE_OPONE_A → liquidity attractor (1); USA → volume disbalance (1); PARTE_DE → market impact (1)

**betting volume** [metrica] (docs=1) — Volumen esperado de bets, definido como V̄ := γ · E{|Q̃|} = (2/ζ) · V. Representa el volumen que resultaría si todo el trading fueran bets sin intermediación. Es una variable no observable que se infiere del volumen observado V mediante el multiplicador ζ.  
  Relaciones: EQUIVALE_A → trading volume (1); USA → business time (1); PARTE_DE → order size distribution (1)

**intermediation** [concepto] (docs=1) — Comercio indirecto donde compradores y vendedores no interactúan directamente, sino que intercambian a través de market-makers que fijan precios bid y ask y obtienen un margen. La intermediación externaliza el proceso de formación de precios, permitiendo que los demás agentes ...  
  Relaciones: USA → market making (1); MEJORA_A → informational efficiency (1); SE_OPONE_A → random matching and bargaining (1)

**PIN-AACD Model** [metodo] (docs=1) — Extensión del modelo AACD de Bauwens y Giot que incorpora estados informativos (good news, bad news, no news) en las duraciones condicionales esperadas de trades buy/sell, permitiendo probabilidades de noticias variables en el tiempo vía modelo logístico sobre volumen.

**Path Signature Transform** [metodo] (docs=1) — Transformacion de rough path theory que mapea trayectorias multivariadas en secuencias de integrales iteradas preservando orden temporal e interacciones de alto orden.

**VWAP Execution** [estrategia] (docs=1) — Estrategia de ejecucion que busca minimizar slippage entre precio ejecutado y VWAP de mercado distribuyendo ordenes en el tiempo segun perfil de volumen esperado.  
  Relaciones: PARTE_DE → algorithmic trading (1)

**Active ETF** [concepto] (docs=1) — ETF de gestión activa que bajo norma SEC debe reportar sus tenencias diariamente, otorgando acceso sin precedentes a las estrategias de gestores de alto perfil.

**Limit Up-Limit Down (LULD) Plan** [concepto] (docs=1) — Mecanismo de circuit breaker a nivel de acción individual en EE.UU. que previene que las acciones se comercien fuera de una banda de precio basada en un precio de referencia evolutivo.  
  Relaciones: MITIGA → flash crash (1)

**LLM-driven feature engineering** [metodo] (docs=1) — Uso de un LLM para generar funciones de extracción de features en código (PyTorch) a partir de ejemplos few-shot, orientadas a indicadores de riesgo-retorno interpretables.  
  Relaciones: USA → few-shot prompting (1); PARTE_DE → AlphaQuant framework (1); PREDICE → Sharpe ratio (1)

**competitive market maker** [concepto] (docs=1) — Caso donde la maximización del market maker se reemplaza por la condición de que el precio iguala la expectativa condicional del valor (beneficio cero); bajo esta condición los precios siguen una martingala.  
  Relaciones: SE_OPONE_A → strategic market maker (1); CAUSA → martingale price process (1)

**volatility of variance smile** [fenomeno] (docs=1) — Sonrisa de volatilidad implícita de opciones sobre varianza realizada, que a diferencia del equity muestra pendiente ascendente (upward-sloping); el paper muestra que su forma depende críticamente de la distribución de los saltos en varianza.  
  Relaciones: PREDICE → jump distribution (1); SE_OPONE_A → volatility skew (1)

**collateralization** [concepto] (docs=1) — Práctica de posteo de colateral bajo acuerdos ISDA/CSA que mitiga el impacto del riesgo de crédito y de funding en el precio del derivado, incorporada en el marco de valuación general del paper.  
  Relaciones: MITIGA → counterparty credit risk (1); MITIGA → funding risk (1)

**risk control** [metodo] (docs=1) — Segunda etapa del modelo (tras la generación de señal): entre los 4 mejores candidatos del ranking se elige el que minimiza la suma de la matriz varianza-covarianza del portafolio; incluye stop-loss, corte por precio bajo (<3 SKr), bans sectoriales tras stop-losses agrupados y...  
  Relaciones: USA → stop-loss rule (1); PARTE_DE → statistical arbitrage (1)

**non-stationary behaviour** [riesgo_metodologico] (docs=1) — Efecto no estacionario en series de precios financieras que dificulta distinguir movimientos extremos transitorios de cambios permanentes de nivel, invalidando el uso de medidas estadísticas invariantes en el tiempo para determinar puntos de entrada/salida.  
  Relaciones: CAUSA → trading strategy variance (1); MITIGA → cointegration (1); SE_OPONE_A → mean reversion (1)

**arithmetic Brownian motion** [concepto] (docs=1) — Proceso estocástico no estacionario (dMt = γ dt + θ dZt) que el paper usa para modelar la componente de largo plazo del log-precio del activo sintético, driftando con γ y volatilidad instantánea θ.  
  Relaciones: PARTE_DE → non-stationary model for statistical arbitrage trading (1); CAUSA → trading strategy variance (1)

**signal-to-noise ratio** [metrica] (docs=1) — Ratio S = sqrt(µ²/σ²) definido como función objetivo alternativa al retorno esperado puro, análogo al Sharpe ratio con tasa libre de riesgo cero, usado para hallar la banda óptima que equilibra retorno y varianza.  
  Relaciones: EQUIVALE_A → Sharpe ratio (1); MEJORA_A → expected return maximization (1)

**standing liquidity price** [metodo] (docs=1) — Promedio de precios bid/ask ponderado por volumen a través de N niveles del libro, con pesos que decaen exponencialmente por índice de nivel y por distancia relativa de precio al mejor nivel.  
  Relaciones: PARTE_DE → weighted microprice momentum (1); USA → limit order book (1); USA → exponential decay weighting (1)

**execution momentum** [metodo] (docs=1) — Precio promedio de las últimas M ejecuciones ponderado por volumen y firmado (+1 comprador-iniciado, −1 vendedor-iniciado), que captura la presión de toma de liquidez real en vez de la liquidez pasiva.  
  Relaciones: PARTE_DE → weighted microprice momentum (1); USA → trade sign (1); USA → liquidity taking (1)

**liquidity sweep** [fenomeno] (docs=1) — Movimiento extremo de precio causado por presión de liquidación forzada; el caso de estudio muestra el spread NG U-V moviéndose 4.5 desvíos estándar intradía por la liquidación del fondo MotherRock.  
  Relaciones: CAUSA → calendar spread (1); MIDE → realized volatility (1)

**order book density function** [dato] (docs=1) — Función f que describe el precio marginal del próximo trade infinitesimal a medida que se consume el libro; es el insumo primitivo del que se derivan tanto la función VWAP como la LOB, y se asume estrictamente decreciente y dos veces diferenciable.  
  Relaciones: PARTE_DE → limit order book (1); REQUIERE → market impact (1)

**Black-Scholes PDE** [metodo] (docs=1) — Ecuación diferencial parcial obtenida vía un argumento de cobertura delta-neutral y ausencia de arbitraje, que gobierna el valor de cualquier derivado europeo sobre una acción que no paga dividendos.  
  Relaciones: USA → Ito's Lemma (1); EQUIVALE_A → heat equation (1)

**cumulative-R significance threshold** [metrica] (docs=1) — Umbral S_N > z_alpha * sqrt(N*b) sobre el cual la performance acumulada en R se considera significativa bajo la nula de edge cero, dado el estadístico estandarizado Z_N.  
  Relaciones: USA → zero-edge null hypothesis (1)

**Deflated Sharpe Ratio** [metrica] (docs=1) — Ajusta la inferencia de performance por no-normalidad y por la inflación que surge cuando se testean muchas estrategias candidatas y se reporta la mejor; sirve de análogo al post-selection adjustment del paper en R-space.  
  Relaciones: MEJORA_A → Sharpe ratio (1); MITIGA → backtest overfitting (1); EQUIVALE_A → post-selection adjustment (1)

**making the spread** [estrategia] (docs=1) — Estrategia de arbitraje estadístico que consiste en colocar órdenes límite simultáneas en bid y ask y esperar a que ambas se ejecuten antes de que el mid-price se mueva, capturando el spread bid-ask.  
  Relaciones: USA → bid-ask spread (1); USA → Laplace transform inversion (1); APLICA_A → market making (1)

**manifold learning** [metodo] (docs=1) — Metodología para descubrir una variedad (manifold) de datos de menor dimensión que preserva la información relevante para una regresión no lineal, usada para predecir movimientos de FX.  
  Relaciones: USA → kernel dimension reduction (1); PREDICE → FX price movement (1)

**two-stage least squares** [metodo] (docs=1) — Enfoque de variable instrumental usado para mitigar endogeneidad, empleando la implementación escalonada de Autoquote, el rezago de QT y el QT promedio por cuartil de tamaño como instrumentos.  
  Relaciones: MITIGA → reverse causality (1); USA → NYSE Autoquote (1)

**regime intelligence module** [concepto] (docs=1) — Componente que infiere el entorno estructural prevaleciente a partir de volatilidad, correlación y liquidez, guiando la asignación de pesos del meta-learner, el énfasis de señales y la modulación de riesgo.  
  Relaciones: USA → hidden Markov model (1); USA → Gaussian Mixture Model (1); MIDE → volatility clustering (1)

**debate constitution** [metodo] (docs=1) — Conjunto de cinco reglas explícitas (carga de la prueba, humildad epistémica, actualización bayesiana, incremento de información, resolución de disputas) que gobiernan cómo argumentan los agentes para evitar loops de aserción o consenso hueco.  
  Relaciones: USA → Bayesian update protocol (1); MITIGA → persona bias (1)

**path integral** [metodo] (docs=1) — Formalismo de mecánica cuántica que representa la amplitud de transición como una suma sobre todos los caminos posibles; el paper lo usa para derivar el propagador del modelo de volatilidad local.  
  Relaciones: APLICA_A → local volatility model (1); USA → propagator (1)

**semi-classical approximation** [metodo] (docs=1) — Expansión perturbativa alrededor de la trayectoria clásica (de volatilidad cero) que el paper aplica a la representación de integral de caminos del modelo de volatilidad local para obtener una fórmula analítica aproximada de la distribución.  
  Relaciones: USA → path integral (1); PREDICE → distribution volatility (1)

**short-term reversal** [fenomeno] (docs=1) — Anomalía del mercado donde los retornos a corto plazo revierten su dirección; el pairs trading puede ser una forma disfrazada de explotar este efecto.  
  Relaciones: CAUSA → pairs trading (1)

**correlation matrix** [concepto] (docs=1) — Matriz de similitud construida a partir de retornos residuales que contiene valores positivos y negativos, sirviendo como red signada para encontrar agrupaciones.  
  Relaciones: PARTE_DE → clustering (1)

**derivative** [concepto] (docs=1) — Instrumentos financieros (opciones, swaps, forwards) utilizados para separar el interés económico de la propiedad legal de un activo subyacente.  
  Relaciones: CAUSA → constructive trade (1)

**option pricing** [concepto] (docs=1) — Pricing de opciones como dominio donde las restricciones matemáticas son explícitas: put-call parity, monotonicidad/convexidad en strike, calendar spread restrictions. El paper señala que es un laboratorio natural para AI constraint-aware.  
  Relaciones: REQUIERE → no-arbitrage pricing (1); USA → deep learning (1)

**regime shifts** [fenomeno] (docs=1) — Cambios estructurales en el proceso generador de datos que quiebran los supuestos de estacionariedad, independencia y ergodicidad de los modelos financieros. En la analogía del paper, equivalen a la acción disruptiva del Mula en la psicohistoria de Asimov.  
  Relaciones: CAUSA → model reflexivity (1); SE_OPONE_A → stationarity (1)

**Arbitrage Activity** [estrategia] (docs=1) — Actividad de arbitraje institucional entre el ETF y su subyacente. Mercados subyacentes más accesibles fomentan mayor actividad de arbitraje en ETFs.  
  Relaciones: MITIGA → Tracking Error (1); REQUIERE → Market Accessibility (1)

**price clustering** [fenomeno] (docs=1) — Tendencia de los precios a agruparse en números específicos (ej. terminados en 00, 99 o 01), facilitando la negociación táctica pero distorsionando la distribución uniforme.  
  Relaciones: REQUIERE → transaction costs (1)

**Intraday Volume** [dato] (docs=1) — Volumen de negociación dentro del día, que exhibe un patrón estacional en forma de U. Se decompone en componente común (cross-stock, no estacionario, extraído por PCA) y componente específico (stock-by-stock, estacionario).  
  Relaciones: PARTE_DE → VWAP Strategy (1); USA → principal component analysis (1)

**Volume Decomposition** [metodo] (docs=1) — Separación del volumen observado en dos partes: una que refleja cambios por evoluciones del mercado (componente común) y otra que describe el patrón específico de cada acción (componente específico).  
  Relaciones: USA → principal component analysis (1); APLICA_A → Intraday Volume (1)

**Propensity to Sell** [metrica] (docs=1) — Probabilidad estimada de que un mutual fund venda una acción en función del cambio absoluto en sus características. Se modela con un linear probability model usando datos de holdings de mutual funds.  
  Relaciones: PREDICE → trading volume (1); USA → Linear Probability Model (1)

**Limit Order Book State** [dato] (docs=1) — Vector st que captura los precios y volúmenes de best bid/ask y niveles profundos del LOB en tiempo discreto fino (milisegundos).  
  Relaciones: USA → Microstructure Tokenization (1)

**Informational Divergence Metric D(t)** [metrica] (docs=1) — Métrica definida como D(t) = 1 − cos(vmarket(t), vpublic(t)) ∈ [0, 2], que mide la brecha entre la representación vectorial del estado microestructural y la del consenso público en tiempo real.  
  Relaciones: MIDE → information asymmetry (1); USA → Microstructural Encoder (1); USA → Semantic Encoder (1)

**Hawkes Process de-clustering** [metodo] (docs=1) — Proceso puntual auto-excitante que descompone la intensidad condicional λ(t) en baseline exógeno µ(t) más kernel endógeno ϕ(t), permitiendo separar señal informativa de ruido de cascada.  
  Relaciones: MITIGA → Market Endogeneity (1); USA → Branching Ratio (1)

**Type I error** [metrica] (docs=1) — Error de falsa detección (false discovery) en la evaluación de estrategias: concluir que una estrategia es rentable cuando en realidad no lo es. El paper muestra que la estrategia de moving average genera un Type I error masivo en el OOS a pesar de tener t-statistics extremada...  
  Relaciones: SE_OPONE_A → Type II error (1); CAUSA → changing market conditions (1)

**Credit Scoring** [metodo] (docs=1) — Sistema de evaluación predictiva del riesgo de default de un prestatario usando datos históricos y algoritmos estadísticos o de machine learning. Evolucionó desde el análisis discriminante y la regresión logística hacia modelos no lineales como árboles de decisión, random fore...  
  Relaciones: PREDICE → Probability of Default (1); USA → Machine Learning Classifier (1); APLICA_A → Stochastic Optimization (1)

**Machine Learning Classifier** [metodo] (docs=1) — Algoritmos de aprendizaje supervisado —árboles de decisión, random forests, support vector machines, gradient boosting y redes neuronales— que superan a la regresión logística en precisión predictiva para clasificación de default. Destacan en entornos con datos de alta dimensi...  
  Relaciones: MEJORA_A → Credit Scoring (1); PREDICE → Probability of Default (1); SE_OPONE_A → Model Misspecification Risk (1)

**Model Misspecification Risk** [riesgo_metodologico] (docs=1) — Riesgo de que un modelo cuantitativo falle por supuestos incorrectos sobre la distribución de datos subyacentes. En carteras de préstamos se manifiesta cuando se asume normalidad de retornos (MVO), estabilidad de correlaciones, o independencia de defaults. El uso de MVO subest...  
  Relaciones: CAUSA → Tail Dependence (1); MITIGA → Conditional Value-at-Risk (1); SE_OPONE_A → Stochastic Optimization (1)

**Markov-modulated Hawkes process** [metodo] (docs=1) — Proceso de Hawkes extendido donde tanto la intensidad basal µ como el kernel de autoexcitación ϕ dependen de un estado latente Zt que alterna entre régimen de ruido (n≈0) y régimen crítico (n→1). Permite distinguir ruido de reacciones en cadena iniciadas por actores informados...  
  Relaciones: PARTE_DE → Hawkes process (1); USA → regime switching (1); APLICA_A → market microstructure (1)

**sum of squared deviations** [metodo] (docs=1) — Medida de similitud entre series de precios normalizadas utilizada para seleccionar pares; los pares con la menor suma de desviaciones cuadradas entre sus precios normalizados son elegidos para trading.  
  Relaciones: PARTE_DE → pairs trading (1); USA → normalized price series (1)

**predatory trading** [fenomeno] (docs=1) — Comportamiento de los HFT firms cuando son pocos en el mercado: compiten principalmente mediante órdenes de mercado que pickean (depredan) órdenes límite de la gran masa de traders lentos, en lugar de usar su tecnología para proveer liquidez. Este comportamiento daña la liquid...  
  Relaciones: USA → liquidity taking (1); CAUSA → bid-ask spread (1); SE_OPONE_A → liquidity provision (1)

**free-riding** [fenomeno] (docs=1) — Comportamiento de los slow traders que se benefician pasivamente de las mejoras en eficiencia informacional y reducción de fricciones generadas por los fast traders. Al haber más HFT, los precios son más informativos y las fricciones menores, lo que reduce el gross expected pa...  
  Relaciones: CAUSA → overinvestment in HFT (1); USA → informational efficiency (1); SE_OPONE_A → high-frequency trading (1)

**overinvestment in HFT** [fenomeno] (docs=1) — El equilibrio privado de inversión en tecnología HFT implica una proporción de fast traders (β) mayor que la socialmente óptima (β_opt), porque los FTs no internalizan la externalidad negativa que generan sobre los STs. Existen incentivos para ser FT incluso cuando es socialme...  
  Relaciones: MITIGA → Pigovian tax (1); CAUSA → free-riding (1)

**intrinsic value process** [concepto] (docs=1) — Proceso estocástico que gobierna la evolución del valor intrínseco o fundamental de un activo. Típicamente se asume random walk (γ=1), pero el paper permite γ≠1 para capturar mean reversion o sobrecreacción en el proceso subyacente.  
  Relaciones: REQUIERE → partial adjustment with noise model (1); MIDE → overreaction (1); SE_OPONE_A → market efficiency (1)

**liquidity attractor** [fenomeno] (docs=1) — Fenómeno por el cual un gran volumen en el mejor nivel del libro de órdenes atrae ejecuciones inmediatas en lugar de servir como soporte de precio: los participantes ven la liquidez disponible como una oportunidad y la toman al instante. Es el efecto opuesto al price support y...  
  Relaciones: SE_OPONE_A → price support (1); CAUSA → order flow (1); PARTE_DE → market microstructure (1)

**P&L dynamics** [metodo] (docs=1) — Propuesta de los autores para evaluar la calidad de modelos de trading mediante la dinámica de pérdidas y ganancias (P&L) en lugar de la predicción de precios. El P&L separa el movimiento de precio de las acciones del trader (Enter Long, Exit Long, Enter Short, Exit Short), si...  
  Relaciones: MEJORA_A → price formation (1); USA → execution rate (1); APLICA_A → market dynamics (1)

**statistical equilibrium** [riesgo_metodologico] (docs=1) — Supuesto implícito en muchos estudios académicos del libro de órdenes de que existe un estado estacionario o caso cuasi-estacionario sobre el cual calcular características estadísticas. Los autores lo consideran un error metodológico fundamental porque el mercado nunca tiene e...  
  Relaciones: SE_OPONE_A → non-stationarity (1); CONTRADICE_A → market dynamics (1); USA → limit order book (1)

**business time** [concepto] (docs=1) — Tiempo medido por la tasa de llegada de nuevos bets (γ) al mercado. Para activos muy negociados el tiempo de negocio pasa rápido; para activos poco negociados pasa lento. La velocidad del mercado (market velocity) es precisamente la tasa γ de llegada de bets.  
  Relaciones: PARTE_DE → market microstructure invariants (1); MIDE → trading activity (1)

**price formation** [concepto] (docs=1) — Proceso por el cual los precios incorporan nueva información. En NFTs se realiza mediante dos mecanismos principales: precio fijo (7 a 180 días) y subasta cronometrada (inglesa u holandesa).  
  Relaciones: PARTE_DE → market microstructure (1)

**Moneyness Scaling** [metodo] (docs=1) — Transformación de coordenadas propuesta por Leung y Sircar (2015) que ajusta la coordenada de moneyness de la implied volatility smile de opciones LETF para eliminar la discrepancia visual con el smile del ETF subyacente.  
  Relaciones: APLICA_A → Leveraged ETF (LETF) (1); REQUIERE → stochastic volatility (1)

**Average Directional Index (ADX)** [metrica] (docs=1) — Indicador de Wilder (1978) que cuantifica la fuerza de una tendencia independientemente de su dirección, construido a partir de los indicadores direccionales +DI y −DI suavizados con la técnica de Wilder.  
  Relaciones: PARTE_DE → Momentum Exhaustion Signal (1)

**Excessive Trading** [fenomeno] (docs=1) — Tendencia de inversores minoristas a negociar en exceso, rotando frecuentemente sus carteras sin mejorar retornos brutos pero incurriendo en costes de transacción que reducen el rendimiento neto.  
  Relaciones: USA → Sensation Seeking (1)

**Equilibrium Strategy** [estrategia] (docs=1) — Estrategia que es localmente óptima en cada instante asumiendo que la misma estrategia se seguirá en el futuro, resolviendo la inconsistencia temporal del criterio media-varianza.  
  Relaciones: REQUIERE → Hamilton-Jacobi-Bellman equation (1); MEJORA_A → pairs trading (1)

**Bertram Optimal Trading Model** [metodo] (docs=1) — Modelo de arbitraje estadistico que asume spread OU zero-mean; maximiza retorno esperado por unidad de tiempo determinando niveles optimos de entrada a* y salida m*=-a*.  
  Relaciones: USA → Ornstein-Uhlenbeck process (1); APLICA_A → statistical arbitrage (1)

**Technical Pairs Trading** [estrategia] (docs=1) — Integracion de indicadores tecnicos (Momentum, Bollinger Bands, MACD) con pairs trading para senales de entrada/salida de corto plazo.  
  Relaciones: MEJORA_A → pairs trading (1); USA → technical analysis (1)

**Sequence-Based Flash Events (SFEs)** [metodo] (docs=1) — Metodología de identificación de flash events basada en secuencias de ticks: mientras la curva de equity no revierta se permanece en la misma secuencia. Captura crash completo sin depender de intervalos fijos. Requiere duración <1.5s con 100% de retracement para excluir shocks...  
  Relaciones: MEJORA_A → Mini Flash Crashes (MFCs) (1); MEJORA_A → Extreme Price Movements (EPMs) (1)

**Dark Pool Latency Arbitrage** [fenomeno] (docs=1) — Arbitraje casi libre de riesgo donde traders rápidos detectan cambios en el precio de referencia del mercado lit antes de que el dark pool actualice sus precios, ejecutando contra órdenes pasivas stale. Específico de dark pools por su dependencia de precios de referencia exter...  
  Relaciones: REQUIERE → Stale Reference Price (1)

**Empirical Likelihood Ratio (ELR) test** [metodo] (docs=1) — Test estadístico basado en bloques que evalúa si un portafolio de arbitraje empíricamente óptimo es un SAO poblacional. Se basa en resolver un problema de mínima entropía relativa (Minimum Relative Entropy) sobre distribuciones de bloques, y el estadístico sigue una distribuci...  
  Relaciones: USA → Kullback-Leibler divergence (1); APLICA_A → Stochastic Arbitrage Opportunity (SAO) (1); MITIGA → Type I error (1)

**FinRL** [metodo] (docs=1) — Primer framework open-source full-stack de deep reinforcement learning para trading automatizado en finanzas cuantitativas con arquitectura modular de tres capas.  
  Relaciones: USA → deep reinforcement learning (1)

**Conditional Volatility** [concepto] (docs=1) — Volatilidad de retornos que depende de valores pasados o efectos económicos; central para medir riesgo y determinar el retorno requerido y precio de activos.  
  Relaciones: APLICA_A → asset pricing (1)

**Agency Intermediation** [concepto] (docs=1) — Intermediación donde brokers ejecutan trades en nombre de inversores ganando comisiones sin tomar riesgo de inventario; requiere monitoreo por parte del cliente.  
  Relaciones: SE_OPONE_A → Principal Intermediation (1)

**time-series cross-validation** [metodo] (docs=1) — Técnica de validación cruzada que asegura que las features generalicen a través de splits temporales de los datos, usada como parte de la evaluación robusta de features.  
  Relaciones: MITIGA → backtest overfitting (1); USA → AutoML (1)

**AutoML** [metodo] (docs=1) — Framework (FLAML) usado para entrenar automáticamente un modelo de regresión (LightGBM) sobre la matriz de features extraídas, con warm-starting entre iteraciones y presupuesto de tiempo fijo.  
  Relaciones: USA → gradient boosting (1); MIDE → feature importance (1)

**discount curve** [dato] (docs=1) — Estructura de datos que almacena un conjunto de tasas cero correspondientes a tenores clave, junto con la fecha de hoy y el número total de puntos, usada para calcular factores de descuento.  
  Relaciones: USA → linear interpolation (1); PARTE_DE → discount factor (1)

**net order flow** [concepto] (docs=1) — Diferencia entre volumen de market orders compradoras y vendedoras en un intervalo; empíricamente cuando es positivo el midprice tiende a subir y viceversa. Es el insumo central de la corrección direccional de las estrategias: comprador → frenar la venta, vendedor → acelerarla.  
  Relaciones: EQUIVALE_A → order flow imbalance (1)

**non-convergence risk** [riesgo_metodologico] (docs=1) — Riesgo de que la divergencia de precios de un par identificado no converja, generando pérdidas; se origina en pares espurios identificados por el problema de tests múltiples.  
  Relaciones: MITIGA → firm characteristics similarity (1)

**elastic net regression** [metodo] (docs=1) — Técnica de regresión regularizada usada para estimar qué características de la firma importan en el desempeño del pairs trading, minimizando overfitting y multicolinealidad entre las 81 variables independientes correlacionadas.  
  Relaciones: MITIGA → backtest overfitting (1); USA → firm characteristics similarity (1); MEJORA_A → ordinary least squares (1)

**strategic market maker** [concepto] (docs=1) — Market maker que no está sujeto a una condición de beneficio cero sino que maximiza su beneficio esperado eligiendo cuánta liquidez provee y la pendiente de su regla de precios, tras observar el order flow combinado y el libro.  
  Relaciones: USA → order flow imbalance (1); SE_OPONE_A → competitive market maker (1); APLICA_A → market making (1)

**limit order trader** [concepto] (docs=1) — Agentes que colocan órdenes límite formando el libro; su demanda es lineal en la diferencia entre su estimación del valor y el precio, y su participación se determina por una condición de beneficio esperado cero.  
  Relaciones: PARTE_DE → limit order book (1); USA → zero expected profit condition (1); APLICA_A → liquidity provision (1)

**least-squares Monte Carlo** [metodo] (docs=1) — Algoritmo de simulación (inspirado en Longstaff-Schwartz) usado para resolver recursivamente el sistema de ecuaciones backward-iterativas de la ecuación general de pricing con funding, mediante regresiones across-path.  
  Relaciones: USA → OTC derivative valuation (1); MITIGA → funding risk (1)

**rational expectations equilibrium** [concepto] (docs=1) — Equilibrio lineal donde el spot rate agrega la información dispersa entre dealers; el paper prueba que puede existir multiplicidad de puntos fijos y que para valores altos de la intensidad de intervención el equilibrio deja de existir.  
  Relaciones: PARTE_DE → market microstructure model (1); MITIGA → information asymmetry (1)

**portfolio-balance channel** [concepto] (docs=1) — Canal por el cual la intervención mueve el precio simplemente porque los dealers averse al riesgo exigen compensación de precio para absorber el cambio de inventario, incluso sin contenido informativo.  
  Relaciones: PARTE_DE → central bank intervention (1); USA → inventory risk (1)

**direct intervention scenario** [estrategia] (docs=1) — Ruta de intervención en la que el banco central negocia bilateralmente con un subconjunto pequeño de dealers privilegiados; transmite más información y reduce la volatilidad del spot rate pero aumenta mucho los costos de transacción en ese mercado.  
  Relaciones: SE_OPONE_A → indirect intervention scenario (1); CAUSA → exchange rate volatility (1); REQUIERE → central bank intervention (1)

**parallel market** [fenomeno] (docs=1) — Mercado negro de USD/VND que coexiste con el mercado oficial y cotiza a un premio persistente sobre la tasa comercial legal, sirviendo como indicador del exceso de demanda de divisas no satisfecho.  
  Relaciones: PARTE_DE → administered pricing (1); MIDE → administered pricing (1)

**exchange rate peg** [concepto] (docs=1) — Régimen cambiario de facto identificado por los autores pese a la denominación oficial de 'managed float', caracterizado por cotizaciones comerciales pegadas casi todo el tiempo a los límites de la banda permitida.  
  Relaciones: CAUSA → administered pricing (1); SE_OPONE_A → managed float (1)

**underreaction** [fenomeno] (docs=1) — El retorno tras un anuncio de buenas noticias es mayor que tras malas noticias: el precio incorpora la información lentamente, generando continuación de retornos en el corto plazo.  
  Relaciones: CAUSA → momentum (1); USA → conservatism bias (1)

**stop-loss rule** [metodo] (docs=1) — Liquidar la posición perdedora al cruzar un límite (20% desde el máximo del holding period en el paper); se motiva formalmente con la martingale betting strategy: sin límite de pérdida se necesita capital infinito. El paper además la interpreta como señal contrarian que invali...  
  Relaciones: PARTE_DE → risk control (1)

**market clearing operator** [metodo] (docs=1) — Operador determinista que mapea un estado transitorio del libro (posiblemente no admisible, con bid>=ask) a un estado admisible, ejecutando el emparejamiento de órdenes compatibles por precio y prioridad.  
  Relaciones: PARTE_DE → limit order book (1)

**backward Kolmogorov equation** [metodo] (docs=1) — Ecuación que gobierna la probabilidad de transición del estado del LOB; el paper la resuelve numéricamente mediante discretización de Euler para calcular probabilidades condicionales de movimientos de precio.  
  Relaciones: USA → infinitesimal generator decomposition (1); SE_OPONE_A → Monte Carlo simulation (1)

**ask price increase probability** [metrica] (docs=1) — Probabilidad condicional de que el próximo movimiento del precio ask sea al alza, condicionada al estado (profundidades bid/ask) del libro; métrica objetivo usada para validar el modelo contra datos reales.  
  Relaciones: MIDE → order book depth (1)

**dynamic scaling factor** [metodo] (docs=1) — Parámetro γ = γ0×(1 + δ×|OI|×σ_ratio) que aumenta el peso del momentum de ejecución cuando hay alto imbalance en el tope del libro y volatilidad elevada respecto al promedio histórico.  
  Relaciones: PARTE_DE → weighted microprice momentum (1); USA → order flow imbalance (1); USA → realized volatility (1)

**multifractal scaling** [fenomeno] (docs=1) — Comportamiento de escalamiento con múltiples exponentes (en vez de uno solo, como en procesos monofractales) que el paper atribuye a las series financieras, indicando correlaciones de largo alcance y cambios abruptos en la estructura fractal.  
  Relaciones: CONTRADICE_A → efficient market hypothesis (1); CAUSA → volatility clustering (1)

**no-arbitrage conditions** [concepto] (docs=1) — Restricciones que debe satisfacer una superficie de precios de calls (o de volatilidad implícita) para no permitir arbitraje; el paper las usa para construir su modelo paramétrico de superficie (MixVol).  
  Relaciones: APLICA_A → implied volatility surface (1)

**nodal liquidity** [fenomeno] (docs=1) — Característica propia de los mercados de commodities según la cual el flujo no es naturalmente bidireccional como en renta fija, equity o FX; el flujo comercial (hedging) aparece de forma esporádica y no a demanda.  
  Relaciones: SE_OPONE_A → order flow imbalance (1); CAUSA → liquidity sweep (1)

**sector rotation** [estrategia] (docs=1) — Reasignación dinámica de capital hacia los sectores que históricamente performan bien bajo el régimen de mercado vigente, implementada de forma walk-forward y trimestral.  
  Relaciones: USA → hidden Markov model (1); APLICA_A → pairs trading (1); USA → walk-forward validation (1)

**price-mediated contagion** [fenomeno] (docs=1) — Forma de contagio financiero que se propaga a través del impacto de las liquidaciones sobre los precios de mercado, en contraste con el contagio por obligaciones interbancarias directas.  
  Relaciones: CAUSA → systemic risk (1); USA → market impact (1)

**Black-Scholes closed-form solution** [metodo] (docs=1) — Fórmula analítica para el precio de una call/put europea en función de S0, K, r, σ, T y las funciones N(d1), N(d2) de la normal estándar acumulada.  
  Relaciones: PARTE_DE → Black-Scholes-Merton model (1); USA → lognormal distribution (1)

**binary payoff structure** [concepto] (docs=1) — Modelo base del framework: cada trade rinde +b (múltiplo de reward) con probabilidad p o -1 con probabilidad 1-p, representando el setup retail típico de stop-loss y take-profit fijos.  
  Relaciones: PARTE_DE → R-multiple (1); USA → expectancy (1)

**zero-edge null hypothesis** [metodo] (docs=1) — Hipótesis nula H0: e = 0 (ausencia de edge) sobre la cual se construyen todos los umbrales de significancia del framework en R-space.  
  Relaciones: PARTE_DE → cumulative-R significance threshold (1); APLICA_A → R-multiple (1)

**queueing systems** [metodo] (docs=1) — Analogía y arsenal matemático (colas M/M/∞, procesos de nacimiento-muerte) de la que el paper toma inspiración para modelar el book, considerando las órdenes límite como clientes esperando ejecución o cancelación.  
  Relaciones: USA → order book dynamics model (1)

**CAPM** [concepto] (docs=1) — Modelo lineal que relaciona el retorno esperado de un activo con su riesgo sistemático (beta) vía el retorno esperado del mercado y la tasa libre de riesgo.  
  Relaciones: USA → beta (1)

**economic hallucination** [riesgo_metodologico] (docs=1) — Distorsión de valuación, cobertura y riesgo que surge cuando modelos de IA aprenden patrones en vez de leyes económicas, generando señales anticipatorias erróneas y arbitrajes espurios.  
  Relaciones: CAUSA → spurious arbitrage (1)

**Hedging Valuation Adjustment** [metrica] (docs=1) — Ajuste XVA que cuantifica el valor esperado de las ineficiencias de cobertura como la expectativa descontada de la diferencia entre el valor del portafolio QIS y el valor de la cobertura a lo largo de trayectorias neuronales forward.  
  Relaciones: MIDE → hedge under-replication (1); USA → Markovian Activation Function (1)

**Engle-Granger test** [metodo] (docs=1) — Procedimiento de dos pasos para testear cointegración: primero ADF sobre cada serie individual, luego regresión lineal entre las series y ADF sobre los residuos para verificar estacionariedad.  
  Relaciones: USA → Augmented Dickey-Fuller Test (1); PARTE_DE → cointegration (1)

**z-score** [metrica] (docs=1) — Señal de entrada/salida calculada normalizando el spread sintético del día por la media y desviación estándar del spread durante el período de entrenamiento; umbral de ±1 dispara posiciones largas/cortas.  
  Relaciones: PREDICE → pairs trading (1); MIDE → synthetic spread (1)

**state space design for RL trading** [metodo] (docs=1) — Diseño del estado como vector de variables discretas que codifican dirección y magnitud de los últimos l cambios porcentuales de precio del spread (categorías +2/+1/-1/-2 según umbral k), evitando depender de estimaciones de media/desvío histórico.  
  Relaciones: PARTE_DE → reinforcement learning (1); SE_OPONE_A → Ornstein-Uhlenbeck process (1)

**trading performance degradation** [fenomeno] (docs=1) — Pérdida de rendimiento (retorno, Sharpe) que sufre un agente de trading al ser sometido a ataques adversariales o al aplicarle mecanismos de defensa; el paper reporta que el framework robusto retiene 94.3% del desempeño baseline.  
  Relaciones: CAUSA → adversarial attack (1)

**kernel dimension reduction** [metodo] (docs=1) — Técnica que mapea variables X e Y a espacios de Hilbert con núcleo reproductor (RKHS) y usa el operador de covarianza condicional para hallar el subespacio central que resume la información relevante para la regresión.  
  Relaciones: PARTE_DE → manifold learning (1); MEJORA_A → GARCH (1)

**information incorporation** [concepto] (docs=1) — Velocidad e integridad con que el mercado incorpora en precios la señal proveniente de un anuncio corporativo, medida vía ratio de incorporación, price jump post-anuncio y probabilidad de reversión de retorno.  
  Relaciones: MIDE → standardized price jump (1); USA → abnormal algorithmic trading (1)

**managerial learning** [concepto] (docs=1) — Canal por el cual los gerentes extraen información nueva de los precios de las acciones para tomar decisiones de inversión; el paper argumenta que AT lo potencia al fomentar la producción de información nueva.  
  Relaciones: MIDE → Revelatory Price Efficiency (1); CAUSA → investment-to-price sensitivity (1)

**NYSE Autoquote** [dato] (docs=1) — Evento regulatorio/tecnológico de 2003 que reemplazó la diseminación manual del quote interno por specialists con un quote automatizado, aumentando el tráfico electrónico de mensajes en NYSE; usado como shock exógeno e instrumento.  
  Relaciones: CAUSA → algorithmic trading (1); USA → two-stage least squares (1)

**reverse causality** [riesgo_metodologico] (docs=1) — Riesgo de que la asociación entre AT e investment-to-price sensitivity no sea causal porque los AT se atraen naturalmente a acciones líquidas con mayor informatividad de precio, en lugar de causarla.  
  Relaciones: MITIGA → difference-in-differences (1); MITIGA → two-stage least squares (1)

**good spread** [concepto] (docs=1) — El mejor bid y mejor ask verdaderos del activo de mercado, obtenidos combinando dos valores de mercado (uno de ellos invertido) económicamente equivalentes; contrapuesto al 'bad spread', más ancho e ineficiente.  
  Relaciones: SE_OPONE_A → bad spread (1); USA → efficient price (1)

**price-taking violation of individual rationality** [riesgo_metodologico] (docs=1) — Error de un trader que toma liquidez (market order) en el spread ineficiente ('bad spread') en vez del eficiente ('good spread'), incurriendo en costos de ejecución evitables; el paper mide su frecuencia empírica.  
  Relaciones: CAUSA → arbitrage (1); PARTE_DE → market gaming (1)

**spread profit** [metrica] (docs=1) — Componente del PnL del market maker atribuible a comprar por debajo y vender por encima del precio eficiente; se descompone junto al positioning profit siguiendo la metodología de Menkveld (2011).  
  Relaciones: PARTE_DE → market making (1); SE_OPONE_A → positioning profit (1); MEJORA_A → positioning profit (1)

**efficient frontier** [metodo] (docs=1) — Curva en el espacio costo esperado vs. varianza del costo que separa estrategias factibles de infactibles; las estrategias óptimas parametrizadas por lambda trazan esta curva y se usa para calibrar el parámetro de aversión al riesgo comparándola con la familia de estrategias V...  
  Relaciones: MIDE → market impact (1); MEJORA_A → VWAP (1)

**multi-factor risk model** [metodo] (docs=1) — Descomposición de la matriz de covarianza entre valores de la cartera en exposiciones a factores comunes más una varianza idiosincrática, usada para desacoplar las variables de optimización y estabilizar numéricamente la programación cuadrática cuando aumenta el número de valo...  
  Relaciones: PARTE_DE → quadratic programming (1); MITIGA → numerical instability (1)

**quadratic programming** [metodo] (docs=1) — Técnica de optimización numérica usada para resolver el problema de trading de cartera, dado que la función objetivo es cuadrática y las restricciones (monotonicidad) son lineales; el problema se vuelve numéricamente inestable al crecer el número de valores sin la reformulació...  
  Relaciones: REQUIERE → multi-factor risk model (1)

**block trading** [estrategia] (docs=1) — Oportunidad de ejecutar una parte de la orden sin impacto de mercado (fuera del cronograma); en trading de un solo activo siempre es beneficioso, pero en cartera solo conviene selectivamente según la contribución marginal del valor a la función objetivo, dependiendo de sus cor...  
  Relaciones: USA → marginal contribution (1); APLICA_A → dark pool (1)

**trading cost** [metrica] (docs=1) — Diferencia entre el valor total de ejecución y el valor de referencia (precio de llegada por cantidad); se descompone en un término de impacto esperado y un término de varianza (riesgo) que la función objetivo combina linealmente vía lambda.  
  Relaciones: MIDE → market impact (1); PARTE_DE → arrival price (1)

**ecosystem architecture** [concepto] (docs=1) — Diseño bio-inspirado que organiza el sistema en 'regiones funcionales' análogas a un sistema nervioso (capa sensorial de datos, cortex de señales, núcleo de reconocimiento de régimen, meta-learner, sistema nervioso de riesgo, motor de ejecución) en lugar de un pipeline lineal.  
  Relaciones: USA → signal fabric (1); USA → crisis mode operating system (1); USA → meta-learner spine (1)

**financial transaction tax** [concepto] (docs=1) — Impuesto sobre transacciones ejecutadas y/o órdenes canceladas, propuesto o implementado en EU, Francia, Italia, UK, Canadá y EEUU para desincentivar HFT; el paper documenta que reduce liquidez y volumen de negociación.  
  Relaciones: CAUSA → market liquidity (1); SE_OPONE_A → high-frequency trading (1)

**manipulative trading** [riesgo_metodologico] (docs=1) — Categoría regulatoria de prácticas (layering, spoofing, wash trading, quote stuffing) prohibidas en la mayoría de países independientemente del HFT; el paper argumenta que ya existe marco legal para atacarlas sin regulación adicional específica de HFT.  
  Relaciones: MITIGA → market failure (1)

**multi-agent debate** [metodo] (docs=1) — Arquitectura en la que varios agentes LLM con mandatos opuestos construyen casos independientes y luego deliberan antes de llegar a una decisión de trading, en lugar de que un solo agente decida.  
  Relaciones: MITIGA → persona bias (1); USA → Bayesian update protocol (1); APLICA_A → quantitative trading (1)

**catfish effect** [fenomeno] (docs=1) — En ensembles homogéneos de modelos muy 'compliant', los tres agentes subestiman la intensidad de debate requerida y convergen prematuramente sin presión adversarial genuina; un solo agente menos complaciente basta para elevar el piso de intensidad y forzar debate real en los d...  
  Relaciones: MITIGA → consensus illusion (1); CAUSA → persona bias (1)

**consensus illusion** [riesgo_metodologico] (docs=1) — Falla en la que agentes con disposición de compliance compartida realizan un debate que parece válido en la salida pero carece de presión adversarial genuina, produciendo una recomendación plausible pero sin escrutinio real de sus supuestos débiles.  
  Relaciones: CAUSA → persona bias (1); MITIGA → catfish effect (1)

**distribution volatility** [metrica] (docs=1) — Volatilidad efectiva que caracteriza la distribución del activo bajo la aproximación semi-clásica; se calcula como promedio armónico de la varianza de la volatilidad local a lo largo de la trayectoria recta entre spot y strike.  
  Relaciones: MIDE → local volatility model (1)

**model risk management** [metodo] (docs=1) — Gestión de riesgo de modelo requerida por regulación bancaria (SR 11-7/OCC 2011-12). El paper argumenta que las herramientas actuales de ML (MLflow, W&B, DVC) no producen audit trails compatibles con SR 11-7.  
  Relaciones: REQUIERE → audit trail (1); MITIGA → backtest overfitting (1)

**tensor-based backtesting** [metodo] (docs=1) — Backtesting vectorizado con operaciones matriciales (NumPy/pandas), computacionalmente superior y dominante en investigación académica, pero menos realista para modelar balances de cash, fills parciales y constraints; adecuado sobre todo para estrategias cash-neutral.  
  Relaciones: SE_OPONE_A → event-driven backtesting (1); APLICA_A → statistical arbitrage (1)

**critical edge** [concepto] (docs=1) — Conexión en la red financiera cuya inclusión o eliminación impacta sustancialmente, como valor atípico, en el riesgo sistémico de la misma.  
  Relaciones: CAUSA → systemic risk (1)

**factor model** [metodo] (docs=1) — Modelo de factores usado para generar residuals. El paper prueba Fama-French 5, PCA local con 5 componentes, y IPCA condicional con 46 características de firms. Sorprendentemente, la elección del modelo de factores tiene efecto menor en performance: Sharpe >3.2 incluso con FF5...  
  Relaciones: PARTE_DE → asset pricing (1); USA → statistical arbitrage (1)

**private information trading** [concepto] (docs=1) — Negociación en los mercados de valores basada en información privada no compartida con el público general, lo que genera asimetría de información y selección adversa para inversores desinformados.  
  Relaciones: MIDE → information asymmetry (1)

**price jerk** [concepto] (docs=1) — Tercera derivada temporal del precio (tasa de cambio de la aceleración), adaptada del concepto físico de jerk. El paper la estima mediante regresión cuadrática sobre aceleraciones de precio rodantes; curvatura negativa indica frenado dinámico que precede reversiones alcistas.  
  Relaciones: PREDICE → reversal detection (1); USA → momentum (1)

**deep hedging** [estrategia] (docs=1) — Formulación del hedging como problema de aprendizaje bajo costos de transacción y preferencias de riesgo (Buehler et al., 2019). La red aprende políticas que minimizan la distribución de pérdidas terminales en vez de replicar un delta hedge frictionless.  
  Relaciones: USA → deep learning (1); MEJORA_A → delta hedging (1); REQUIERE → transaction costs (1)

**stochastic volatility** [concepto] (docs=1) — Modelos de volatilidad estocástica (Heston 1993) y rough volatility (Gatheral et al., 2018) que imponen restricciones de calibración. Deep calibration puede acelerarlos pero debe preservar las relaciones modelo-implied entre paths, precios y superficies.  
  Relaciones: APLICA_A → option pricing (1); REQUIERE → deep learning (1)

**EKOP model** [metodo] (docs=1) — Modelo clásico de Easley, Kiefer, O'Hara y Paperman (1996) que extrae PIN de órdenes desbalanceadas asumiendo tres escenarios: sin noticias, malas noticias (alpha*delta), y buenas noticias (alpha*(1-delta)).  
  Relaciones: USA → PIN (1); USA → order flow imbalance (1)

**herding** [concepto] (docs=1) — Tendencia de los participantes del mercado a suprimir sus propias creencias e imitar las acciones de otros o seguir el consenso del mercado, resultando en retornos agrupados y menor dispersión de lo justificado racionalmente.  
  Relaciones: SE_OPONE_A → anti-herding (1)

**non-fundamental herding** [concepto] (docs=1) — Herding intencional guiado por el ruido y el sentimiento, en el cual los inversores (o algoritmos) imitan las acciones de otros sin depender de nueva información fundamental clara.  
  Relaciones: CAUSA → informational cascades (1); USA → high-frequency trading (1)

**price synchronization** [fenomeno] (docs=1) — Ajuste casi instantáneo del precio de un activo en respuesta a movimientos en los precios de otros activos económicamente relacionados.  
  Relaciones: MITIGA → adverse selection (1); CAUSA → price discovery (1)

**aggressive-side order anticipation** [estrategia] (docs=1) — Estrategia donde algoritmos tipo sniper operan agresivamente contra las cotizaciones en otros exchanges tras inferir la dirección de una orden institucional.  
  Relaciones: PARTE_DE → order anticipation (1); CAUSA → adverse selection (1)

**Market Accessibility** [concepto] (docs=1) — Grado de facilidad con que los inversores pueden participar en un mercado, medido a través de la MTU como proxy. Afecta los patrones de inversión y características de los ETFs.  
  Relaciones: CAUSA → Institutional Trading Activity (1)

**Panel Regression** [metodo] (docs=1) — Modelo de regresión con datos de panel aplicado a 40 country ETFs listados en EE.UU. para examinar el impacto de la accesibilidad del mercado subyacente sobre los ETFs.  
  Relaciones: USA → Country ETF (1); APLICA_A → Institutional Trading Activity (1)

**Fluid Approximation** [metodo] (docs=1) — Aproximación determinista del comportamiento transitorio de la forma del order book basada en la interacción de flujos de órdenes. Surge como límite de ley de grandes números cuando el volumen de órdenes límite es grande comparado con órdenes individuales.  
  Relaciones: EQUIVALE_A → Hydrodynamic Limit (1); APLICA_A → Order Book Shape (1)

**Convergence Risk** [riesgo_metodologico] (docs=1) — Riesgo de que el pricing error entre pares no converja dentro del horizonte esperado, exponiendo al arbitrajista a pérdidas intermedias que pueden forzar liquidación anticipada por margin calls.  
  Relaciones: CAUSA → Limits to Arbitrage (1); MITIGA → No-Arbitrage Band (1)

**No-Arbitrage Band** [concepto] (docs=1) — Banda alrededor del equilibrio de pricing error dentro de la cual el arbitraje no es rentable tras costes. En el MGST se determina endógenamente con nivel y ancho de banda específicos para cada par.  
  Relaciones: MITIGA → Convergence Risk (1)

**VWAP Strategy** [estrategia] (docs=1) — Estrategia de ejecución que busca comprar o vender un número fijo de acciones a un precio promedio que siga el VWAP. Solo requiere predecir el volumen intradía, no el precio.  
  Relaciones: USA → VWAP (1)

**DQN** [metodo] (docs=1) — Deep Q-Network, algoritmo DRL basado en valor que aproxima la función Q mediante redes neuronales profundas. Es uno de los algoritmos fine-tuned disponibles en FinRL.  
  Relaciones: PARTE_DE → deep reinforcement learning (1); USA → Q-learning (1)

**Instrumental Variables** [metodo] (docs=1) — Técnica para abordar la endogeneidad de características basadas en precio: se instrumenta la propensión a vender con características no basadas en precio (book leverage, book ROA) para descartar causalidad inversa.  
  Relaciones: APLICA_A → Propensity to Sell (1)

**Country ETF** [concepto] (docs=1) — Exchange-Traded Fund que replica la exposición a un país específico, permitiendo implementar estrategias de asset allocation por país basadas en señales cuantitativas de equity y currency esperados.  
  Relaciones: USA → factor model (1)

**Causal Inference** [metodo] (docs=1) — Estimación de efectos causales (de cambios de política, reglas de ejecución o disclosures) sobre liquidez y volatilidad usando DML cuando el parámetro admite representación de score ortogonal con funciones nuisance de alta dimensión.  
  Relaciones: USA → Double/Debiased Machine Learning (1); APLICA_A → market microstructure (1)

**Factorial Moments** [metodo] (docs=1) — Herramienta de física nuclear para caracterizar distribuciones de multiplicidad. Momentos factoriales normalizados F_q que son iguales a 1 para estadística Gaussiana sin correlaciones y crecen por encima de 1 cuando hay correlaciones y fluctuaciones dinámicas.  
  Relaciones: MIDE → Intermittency (1)

**Intermittency** [fenomeno] (docs=1) — Fenómeno donde los factorial moments aumentan con la resolución (disminución del tamaño del bin), señalando desviaciones de la distribución puramente Gaussiana. En finanzas, aparece en resoluciones temporales por debajo de 4 horas.  
  Relaciones: MIDE → Factorial Moments (1); CAUSA → Non-Gaussian Fluctuations (1)

**Microstructure Tokenization** [metodo] (docs=1) — Mapeo que convierte el estado del LOB, sus cambios, flujo de órdenes, spread e imbalance en un vector de token de dimensión fija mediante una función de embedding φ.  
  Relaciones: USA → order book imbalance (1)

**LLM-Based Encoder** [metodo] (docs=1) — Encoder transformer-style Φ que mapea una ventana de k estados del LOB a un embedding Zt ∈ Rd en espacio de representación, diseñado para preservar estructura económicamente relevante.  
  Relaciones: APLICA_A → Limit Order Book State (1)

**Cross-Asset Lead-Lag** [fenomeno] (docs=1) — Relaciones de liderazgo temporal entre diferentes instrumentos financieros donde uno proporciona información predictiva sobre precios, liquidez o volatilidad futura de otro en escalas de microsegundos a segundos.  
  Relaciones: SE_OPONE_A → market efficiency (1)

**market order** [concepto] (docs=1) — Orden ejecutada inmediatamente al mejor precio disponible. En la primera fase (buyers' market), las market orders de venta golpean repetidamente el bid; en la segunda fase (sellers' market), las market orders de compra golpean el ask.  
  Relaciones: SE_OPONE_A → limit order (1); PARTE_DE → limit order book (1)

**2SLS** [metodo] (docs=1) — Two-Stage Least Squares para abordar endogeneidad. Primera etapa: AT_it regresado sobre el promedio de AT de todas las demás acciones (instrumento). Segunda etapa: la medida de liquidez regresada sobre el AT predicho. El coeficiente beta del instrumento es positivo y significa...  
  Relaciones: MITIGA → endogeneity (1); USA → fixed effects panel regression (1)

**genetic algorithm** [metodo] (docs=1) — Técnica de búsqueda evolutiva que representa cada par como un cromosoma binario de tamaño 2N, donde cada gen indica la pertenencia de un activo a uno de los dos componentes del par. El elitismo garantiza que las mejores soluciones no se pierdan entre generaciones.  
  Relaciones: APLICA_A → multi-objective optimization (1); USA → NSGA II (1)

**Variational Autoencoder** [concepto] (docs=1) — Red generativa no lineal que aprende una proyección latente preservando la topología de la variedad de estados de mercado, a diferencia de PCA que asume linealidad y colapsa estructuras curvas. En este marco, el VAE despliega la geometría interna del libro de órdenes sin destr...  
  Relaciones: APLICA_A → anomaly detection (1); SE_OPONE_A → Kalman filter (1)

**OPTICS** [metodo] (docs=1) — Algoritmo de clustering basado en densidad que detecta clusters de densidades variables, superando una limitación de DBSCAN. En el paper se usa con cardinalidad mínima 2 por cluster para generar muchos clusters pequeños.  
  Relaciones: MEJORA_A → DBSCAN (1); PARTE_DE → clustering (1)

**partial correlation** [metodo] (docs=1) — Métrica de distancia novedosa que aísla la correlación pura entre dos acciones eliminando correlaciones espurias causadas por exposición compartida a un tercer factor (el mercado). Transformada como PC = 1 - |ρ_par| para usarse en clustering.  
  Relaciones: USA → pairs trading (1); MEJORA_A → clustering (1); MITIGA → look-ahead bias (1)

**fully invested** [metodo] (docs=1) — Esquema de ponderación menos conservador que divide el capital solo entre los pares que están abiertos, asumiendo que el dinero de pares cerrados se reinvierte en los pares abiertos restantes.  
  Relaciones: SE_OPONE_A → committed capital (1); USA → value-weighted approach (1)

**make-take decisions** [concepto] (docs=1) — Decisión endógena de los agentes entre proveer liquidez (make) mediante órdenes límite, capturando el coste de inmediatez pagado por otros, o tomar liquidez (take) mediante órdenes de mercado, potencialmente pickeando órdenes límite mal posicionadas de otros agentes.  
  Relaciones: REQUIERE → limit order book (1); PARTE_DE → high-frequency trading (1); CAUSA → bid-ask spread (1)

**options trading** [estrategia] (docs=1) — Negociación de opciones (calls europeas en este estudio) formando carteras long-short de pares, donde la rentabilidad depende exclusivamente de la diferencia de volatilidades de los activos subyacentes. Se construyen pares de opciones con el mismo ratio S/K (moneyness) y venci...  
  Relaciones: PARTE_DE → pairs trading (1); USA → implied volatility (1)

**ARMA(1,X) model** [metodo] (docs=1) — Modelo autorregresivo de media móvil con orden óptimo X determinado por el Schwartz Information Criterion. La componente MA de orden superior captura los efectos de thin trading, permitiendo estimar velocidades de ajuste depuradas de dichos efectos. Es el estimador preferido c...  
  Relaciones: MEJORA_A → cross-covariance ratio estimator (1); MITIGA → thin trading (1); EQUIVALE_A → partial adjustment with noise model (1)

**message space dimensionality** [metrica] (docs=1) — Número de dimensiones del espacio de mensajes que un oráculo debe comunicar a los agentes para verificar que la asignación es óptima. El mecanismo competitivo tiene dimensión N; el market-maker con k intermediarios, aproximadamente kN; y el matching aleatorio, 2(N/2)².  
  Relaciones: MIDE → informational efficiency (1); USA → privacy-preserving mechanism (1)

**Leveraged ETF (LETF)** [concepto] (docs=1) — ETF que busca generar un múltiplo β (ej. +2, −2) del retorno diario del subyacente, menos una comisión de gestión. Ejemplos: SSO (β=+2 sobre S&P500), SDS (β=−2). Sus opciones tienen dinámicas de implied volatility diferentes a las del ETF sin apalancar.  
  Relaciones: USA → Moneyness Scaling (1); REQUIERE → stochastic volatility model (1)

**Momentum Exhaustion Signal** [fenomeno] (docs=1) — Condición conjunta donde ADX está elevado (por encima de su media móvil) pero su primera diferencia es ≤ 0 (ya no crece). Señala que el momentum direccional está decayendo y la susceptibilidad a reversión aumenta.  
  Relaciones: REQUIERE → Average Directional Index (ADX) (1); PREDICE → mean reversion (1)

**Composite Trading Signal** [estrategia] (docs=1) — Señal St ∈ {−1, 0, +1} que requiere conjunción de cuatro condiciones: precio en extremo anterior (Ht−1 o Lt−1), desviación de VWAP > θ, ADX elevado, y ∆ADX ≤ 0. Solo activa si TODAS se cumplen simultáneamente.  
  Relaciones: REQUIERE → Volume Weighted Average Price (VWAP) (1); REQUIERE → Average Directional Index (ADX) (1); REQUIERE → Momentum Exhaustion Signal (1)

**Mid-Price Prediction** [metodo] (docs=1) — Predicción de corto plazo del cambio en el precio medio (average of best bid and best ask) usando información del libro de órdenes sin imponer un modelo paramétrico restrictivo.  
  Relaciones: USA → Limit Order Book State (1); APLICA_A → optimal execution (1)

**Coupled Optimal Stopping** [metodo] (docs=1) — Sistema de problemas de parada óptima donde V0 (sin posición) y V1 (con posición larga) están vinculadas: al entrar se paga Xτ+c y se obtiene V1; al salir se recibe Xτ-c y se obtiene V0.  
  Relaciones: APLICA_A → pairs trading (1); REQUIERE → Free Boundary Problem (1)

**Cointegration Vector z_t** [metodo] (docs=1) — Variable de estado que es combinacion lineal de log-precios (z_t = a + log S1_t + beta * log S2_t) con dinamica OU mean-reverting.  
  Relaciones: EQUIVALE_A → Ornstein-Uhlenbeck process (1); REQUIERE → cointegration (1)

**k-Means Clustering** [metodo] (docs=1) — Método de clustering particional que asigna datos a K clusters minimizando la suma de cuadrados intra-cluster. Requiere eliminación post-hoc de outliers mediante filtro de distancia al centroide versus distancia al vecino más cercano (percentil α=0.5).  
  Relaciones: SE_OPONE_A → DBSCAN (1)

**Extreme Price Movements (EPMs)** [fenomeno] (docs=1) — Movimientos de precio definidos como retornos de midquote en intervalos de 10 segundos que superan el percentil 99.9 de la distribución absoluta de retornos. En la muestra: 28,825 OC-EPMs con retorno absoluto medio de 0.4241%. Crítica: subestiman crash al usar open-to-close en...  
  Relaciones: SE_OPONE_A → Sequence-Based Flash Events (SFEs) (1)

**Pairs trading strategy on ETFs** [estrategia] (docs=1) — Estrategia market-neutral que explota co-movimiento y mean reversion de precios de pares de ETFs internacionales. Se abre una posición long-short cuando los precios divergen y se cierra cuando convergen. Variante metodológica: usa desviaciones absolutas en lugar de suma de cua...  
  Relaciones: USA → mean reversion (1); APLICA_A → International ETFs (1)

**Poisson Process** [dato] (docs=1) — El precio ya no sigue un random walk sino una combinación de dos procesos de Poisson; la distribución de noticias es idéntica en cada batch, y la esperanza del precio converge a un movimiento browniano por el teorema central del límite.  
  Relaciones: USA → Price Jump (1)

**Three-Tiered Game Model** [metodo] (docs=1) — Modelo de tres juegos interconectados: HFT game (competencia por ser HFM), HFM game (estrategia de spread), y HFI game (timing de órdenes).  
  Relaciones: APLICA_A → Batch Trading Mechanism (1); USA → Trembling-Hand Perfect Nash Equilibrium (THPNE) (1)

**Trading Bloc Exchange (TBE)** [concepto] (docs=1) — Mercado unificado donde acciones, bonos, derivados, commodities y FX se comercian exclusivamente en BCUs, operando como infraestructura financiera regional.  
  Relaciones: USA → Bloc Currency Unit (BCU) (1)

**Trade Policy Realignment** [fenomeno] (docs=1) — Cambio en las posiciones de partidos políticos sobre comercio internacional: la izquierda pasa de proteccionista a pro-comercio, la derecha de libre mercado a proteccionista.

**Collection-Level Floor Bids** [estrategia] (docs=1) — Ofertas para comprar cualquier token en una colección; constituyen el best bid efectivo en la mayoría de snapshots del orderbook y reducen spreads medidos en más de un tercio.  
  Relaciones: PARTE_DE → Two-Tier Orderbook (1); MEJORA_A → market liquidity (1)

**Statistical Arbitrage Strategy** [estrategia] (docs=1) — Estrategia basada en disparadores de umbral simple: movimientos del mid-quote del contrato líder pronostican movimientos del contrato rezagado con precisión direccional >85%, generando beneficios de ~GBP 100,000/mes.  
  Relaciones: USA → Lead-Lag Relationship (Sub-Second) (1)
