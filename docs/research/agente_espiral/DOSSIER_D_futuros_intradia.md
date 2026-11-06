Dossier D — anexo de docs/research/AGENTE_ESPIRAL_20261004.md — verificado 2026-10-04

# Dossier verificado: falsificación de estrategias intradía en micro/e-mini CME (MNQ, MES, MGC, M2K/RTY, MYM/YM)

**Fecha de corte:** 2026-10-04.
**Cómo verifiqué:** leí las fuentes primarias. Los dos papers centrales (Mesfin 2605.04004 y Arnott-Harvey-Markowitz) los descargué y les extraje el texto con pypdf.
**Etiquetas:** [VERIFICADO] lo leí en la fuente primaria. [SECUNDARIO] viene de una fuente secundaria. [NO VERIFICADO] no lo pude confirmar.
**Lo que no pude leer:**
- Los PDF de tarifas de CME (fee schedules y SER 9799) bloquean bots.
- La página de abstract de SSRN devuelve 403.

---

## 1. Mesfin (2026), "Structural Limits of OHLCV-Based Intraday Momentum Signals in MNQ Futures: A Systematic Falsification Study", arXiv:2605.04004 [VERIFICADO, texto completo]

**Ficha**
- Autor único, investigador independiente.
- Enviado el 5-may-2026; versión v3 del 15-sep-2026.
- Categoría q-fin.TR. No tiene revisión por pares.
- Declara que usó IA para edición.
- Antes de ser un estudio de falsificación fue una búsqueda de estrategias. El autor lo admite y aclara que eso cambia la epistemología.

**Datos**
- 72.604 barras OHLCV de 5 minutos de MNQ front-month, solo RTH (09:30–16:00 ET).
- Período: dic-2021 a ago-2025. Quedan 947 días completos después de sacar sesiones parciales y barras con volumen cero.
- Fuente: NinjaTrader, agregado desde barras de 1 minuto.
- Contrato continuo: concatenación trimestral de archivos, sin back-adjustment y sin calendario de feriados (los feriados caen por dropna).
- MGC: 1.091 días de barras de 5 minutos.
- Sesión Asia: 20:00–02:00 ET.

**Ejecución**
- Señal al cierre de la barra; entrada en el open de la barra siguiente.
- Fricción round-trip fija:
  - MNQ: 2,0 pts ($4,00), que cubre spread, fees de NinjaTrader/exchange y slippage conservador.
  - MGC: 0,50 pts (5 ticks, $5).
- Un borrador previo le aplicaba a MGC la fricción en puntos de MNQ. El autor lo reconoce como error.

**Walk-forward expansivo, 3 folds OOS**

| Fold | Entrenamiento | Test OOS |
|---|---|---|
| 1 | 2022 | 2023 |
| 2 | 2022–23 | 2024 |
| 3 | 2022–24 | 2025 (parcial, ene–ago) |

- Los parámetros salen solo del entrenamiento.
- 2022 no entra en la estabilidad anual porque usarlo sería circular.

**Cinco criterios simultáneos, con gating secuencial**
1. t ≥ 2,0 sobre retornos NETOS OOS. Es un t-test de una muestra, de dos colas, con H0: media neta = 0.
2. Al menos 30 trades por fold OOS.
3. Media neta positiva después de fricción.
4. Mismo signo en 2023, 2024 y 2025.
5. Test de permutación, solo para las señales que pasan 1 a 4.

*Inconsistencia interna en el punto 5:*
- El abstract del PDF pide p < 0,05.
- La Tabla 3 y el abstract de arXiv piden p < 0,001.
- Ninguna señal candidata llegó a ese gate, así que el umbral solo afecta a los controles positivos.

**Las 14 familias testeadas**
- ORB con OR 09:30–09:55 (3 variantes).
- Expansión de rango en sesión Asia.
- Liquidity grab en sesión Asia.
- Gap fill.
- Gap continuation con velocidad Kalman sobre barras de 1 minuto.
- Volume spike.
- Volume dry-up.
- Clasificador VVG: reversal, continuation y close fade.
- Drift post-evento (FOMC y otros; 993 eventos de ForexFactory).
- Reversión a la media Ornstein-Uhlenbeck (OU) en MGC.

**Resultado: ninguna pasa los cinco criterios. Hay tres modos de falla distintos:**
- **(a) Techo de edge bruto (11 familias).** El retorno bruto máximo es de 0,07 a 1,50 pts por trade, por debajo de la fricción de 2,0 pts.
  - Asia expansion 1,5x a b+1: t = −11,52.
  - Liquidity grab: t = −14,12 haciendo fade y −13,24 a favor (6.442 eventos).
  - Volume spike y dry-up: t entre −2,2 y −5,3 con N de 723 a 2.412. El autor insiste en que es un nulo preciso, no falta de potencia.
  - OU en MGC: todas las configuraciones negativas; la half-life a 60 minutos es de unas 8 horas, incompatible con trading intradía.
- **(b) Pasa la fricción pero falla t o estabilidad:**
  - ORB long a bar+15: neto +2,82, t = 0,88, N = 447.
  - VVG reversal: neto +13,49, t = 1,26, N = 35.
- **(c) Gap continuation short (el near-miss más creíble):**
  - Bruto +16,53, neto +14,52, t = 1,46.
  - Falla por 2024 (−11,87) y por tener unos 12 trades por fold.

**Mecanismo clave (sección 4.2)**
- En la expansión de Asia, el movimiento se consume dentro de la barra que lo genera:
  - open → next open: +32,24 pts;
  - close → next open: −0,17 pts.
- Con entrada al cierre de la barra se captura la reversión posterior al agotamiento.

**Controles positivos (vienen de un programa de investigación compañero)**
- **RTH Confluence**
  - Régimen GMM de 3 componentes (= 1) + probabilidad de transición de Markov R1→R2 en 200 barras > 0,15 + z-score de volumen en 50 barras > 0,5.
  - Entrada en pullback de 25 × ATR_ratio; salida en la barra 13.
  - OOS: t = 3,11, neto +11,82 pts, N = 196.
  - Benchmark long incondicional: t = −0,75.
- **London Signal B**
  - Transición GMM R0→R2 en barras de 15 minutos, 03:00–08:30 ET; hold de 60 minutos.
  - OOS: t = 4,30, neto +4,09 pts, N = 247, p = 0,000025.
  - Bootstrap P(media neta > 2 pts) = 98,9 %.

**Debilidades de los controles que reconoce el propio autor**
- Probó más de 53 combinaciones de 7 parámetros antes de fijar la especificación, y no aplicó DSR ni PBO.
- El GMM de RTH se ajustó con todo 2022, lo que contamina el fold W1.
- El baseline de ATR (10,34) se calculó con todo 2022–2024: es look-ahead.
- **Los stops se llenan exactamente al precio de stop (fill idealizado).**
- Sensibilidad al delay en London B: con 1 barra de demora t pasa de +4,30 a −2,78, y con 2 barras a −2,16. **El signo se invierte, no decae.** El autor no puede distinguir si es un artefacto del borde de barra o un edge real pero inaccesible. Dice que hace falta data tick y la pone como extensión prioritaria.

**Conclusión del paper**
- Hay un techo de edge bruto de 1–2 pts para predicciones direccionales de una barra con OHLCV público a 5 minutos en MNQ.
- Lo presenta como observación empírica consistente con la Hipótesis de Mercados Eficientes (EMH), no como un teorema.
- Paper hermano del mismo autor: arXiv:2605.17724 (LSTM vs gradient boosting en MNQ a 5 minutos).
  - Ninguna configuración supera de forma significativa el 51,8 % de tasa base: GBM 50,00–50,89 %, LSTM 50,59 %, p = 0,135 y 0,515.
  - Las importancias de features son inestables entre folds.

**Para tu funnel:** este paper es la mejor justificación publicada para trabajar con tick/25-tick, porque los dos hallazgos más fuertes (la reversión post-expansión y la inversión de signo con delay) son fenómenos del borde de barra.

## 2. Yin, Miki, Lesnichenko, Gural (2026), "Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error", arXiv:2603.20319 [VERIFICADO, HTML]

**Definición:** implementation risk es la divergencia sistemática en las métricas que aparece solo por cómo cada engine implementa la misma estrategia lógica.

**Diseño**
- 15 estrategias benchmark.
- Engines: bt 1.1.0, vectorbt 0.26.2, Backtrader 1.9.78, cvxportfolio 1.3.0 y una implementación de referencia.
- Universo: 180 acciones del S&P 500 en 30 buckets.
- Cuatro regímenes de costo: 0, 18, 36 y 60 bps.
- Forense de código fuente.

**Siete defectos en tres engines**

| Engine | Defecto |
|---|---|
| Backtrader | Divide por 100 la tasa de comisión: cobra 100 veces menos salvo que uses percabs=True |
| Backtrader | Rechaza por margen antes de que las ventas pendientes financien las compras |
| Zipline-Reloaded | Caché de calendario inconsistente |
| NautilusTrader | Confunde HEDGING y NETTING |
| NautilusTrader | Trunca en silencio después de 62 de 1.258 días |
| NautilusTrader | Cobra la comisión dos veces (wrapper + modelo interno) |
| NautilusTrader | Overflow de aritmética de punto fijo |

**Cinco modos de falla:** cost-model, infraestructura, arquitectura, divergencia de especificación y sensibilidad a la complejidad.

**Resultados**
- Con costo cero todos los engines son idénticos (0 % de divergencia): **el único canal de desacuerdo es el modelo de costos.**
- Con costo, la divergencia queda bajo 0,75 pp en la mayoría de las estrategias, pero llega a 3,71 % en rotación de alto turnover.
- Spearman ρ = 0,93 entre intensidad de costo y spread entre engines.
- Ningún engine cambió el signo de una métrica (CSI = 0).

**Recomendaciones**
- Testing diferencial con al menos dos engines de arquitectura distinta (event-driven vs vectorizado) cuando el costo es intenso.
- Auditar el modelo de costos contra una especificación de referencia.
- Correr un baseline con costo cero.
- Tratar este riesgo como ortogonal al overfitting: aplicar DSR y además comparar engines.

**Para tu funnel:** en intradía con muchos trades el costo domina. Implicación: un oráculo de costos independiente más una corrida con costo cero por cada engine.

## 3. Predictibilidad intradía en futuros 2024–2026: qué está respaldado y qué es folklore

**Respaldado (con matices)**

- **Market intraday momentum.**
  - Gao, Han, Li, Zhou (2018, JFE 129:394–414): en SPY 1993–2013, el retorno de la primera media hora predice el de la última media hora.
  - Baltussen, Da, Lammers, Martens (2021, JFE 142:377–403): más de 60 futuros entre 1974 y 2020; el retorno del resto del día predice los últimos 30 minutos.
    - Lo atribuyen al gamma hedging de market makers de opciones y de ETFs apalancados.
    - Revierte en los días siguientes.
    - [SECUNDARIO] Reportan rentabilidad después de costos.
  - Hay evidencia de decaimiento post-publicación en replicaciones (resultados de búsqueda; no leí el paper primario de la caída).
  - Base general de decaimiento: McLean & Pontiff (2016, JF 71:5–32) miden −26 % fuera de muestra y −58 % post-publicación en anomalías de acciones.
- **Order-flow imbalance (OFI).**
  - Cont, Kukanov, Stoikov (2014, JFEc 12(1):47–88): sobre intervalos cortos, el cambio de precio es lineal en el OFI, con pendiente proporcional a 1/profundidad. Es una relación **contemporánea**.
  - Cont, Cucuringu, Zhang (2023, Quant. Finance 23(10)): el OFI integrado de varios niveles explica el impacto contemporáneo; el cross-impact rezagado mejora el forecast pero "decays rapidly".
  - Kolm, Turiel, Westray (2023, Math. Finance 33(4)): con deep learning sobre order flow de 115 acciones Nasdaq logran forecast de alta frecuencia a horizontes cortos. No es evidencia de rentabilidad neta.
  - Takahashi (arXiv:2508.06788, v4 oct-2025): en ES a 1 segundo, los shocks precio-flujo se disipan casi por completo dentro del segundo, y las noticias macro cambian los parámetros de impacto.
  - Jeon (arXiv:2607.09230, cripto): lo que predice de primer orden es el estado de liquidez L2; el order flow solo agrega encima de eso. No reporta costos.
  - **Veredicto:** el OFI es real, pero el horizonte útil es de segundos o menos. Con la latencia de un retail y barras de 25 ticks no hay evidencia publicada de que sobreviva a costos.
- **ORB.**
  - Holmberg, Lönnbark, Lundström (2013, Finance Research Letters 10(1):27–33) en crude oil futures: retornos "significantly higher than zero". En el abstract no hay tratamiento explícito de costos.
  - En MNQ a 5 minutos, Mesfin lo refuta: todas las variantes con t ≤ 0,88.
- **Iceberg / liquidez oculta.**
  - Christensen & Woodmansey (2013, J. Trading 8(3)): estiman que alrededor del 9 % del volumen del libro de ES en 2011 son icebergs, y proponen un predictor de baja latencia.
  - Predice liquidez, no dirección.

**Folklore o sin soporte de revisión por pares (lo busqué y no encontré evidencia primaria)**
- **Volume profile (POC/VA) y auction market theory.** Solo encontré material de practicantes y un SSRN en cripto (SOL/USDT perps, 2026) donde los stops ajustados resultan inviables por costos.
- **Absorption/exhaustion de footprint.** Solo encontré blogs de vendors (Bookmap, etc.).
- **VWAP trend.** Zarattini & Aziz, SSRN 4631351, en QQQ/TQQQ 2018–2023, Sharpe 2,1. Es un SSRN de practicantes, sin revisión por pares y sin OOS independiente.
- **"Beat the Market"** (Zarattini, Aziz, Barbon, SSRN 4824172, SFI RP 24-97):
  - Noise area con trailing stops en SPY 2007–2024: Sharpe 1,33, 19,6 % anual neto.
  - Costos: $0,0035 por acción + $0,001 por acción de slippage, medido en más de 1.000 trades propios. [VERIFICADO en el PDF]
  - Existe una replicación independiente en GitHub (codecat-ops/zarattini-2024-momentum-spy) que, según el snippet del buscador, reporta compresión del edge desde 2025 con Sharpe cerca de 0 en SPY y ES. El repo da 404 y no lo pude verificar.
- **ML y LLM sobre OHLCV.**
  - Mesfin 2605.17724: nulo.
  - Gençay (arXiv:2608.27734): con tools que excluyen look-ahead por construcción más deflación que tiene en cuenta la búsqueda, se rechaza toda estrategia descubierta por LLM y solo se certifican los benchmarks pasivos. Un oráculo con look-ahead y Sharpe 35 pasaba las correcciones estadísticas convencionales.

## 4. Engines tick-exact / event-driven

| Engine | Granularidad | Cola | Latencia | Ambigüedad stop/target intra-barra | Notas |
|---|---|---|---|---|---|
| **hftbacktest** (nkaz001) | L2 MBP y L3 MBO, tick a tick | Sí. ProbQueueModel (PowerProbQueueFunc 1/2/3, LogProbQueueFunc 1/2) y L3 FIFO | Sí. Latencia de feed, de entrada de orden y de respuesta: ConstantLatency, IntpOrderLatency (interpolada desde latencias reales medidas) o un trait propio | No existe a nivel tick: se resuelve por la secuencia real de eventos | Rust con bindings Numba. Tiene `hftbacktest.data.utils.databento.convert()` para MBO de CME (GLBX.MDP3), con snapshot de inicio de día para reconstruir prioridad precio-tiempo. **No modela impacto de mercado.** Los ejemplos de trading en vivo son Binance/Bybit |
| **NautilusTrader** | L3/L2/L1, quote ticks, trade ticks, barras | Sí. `queue_position=True` y `liquidity_consumption=True` en trade execution | Sí. `LatencyModel` (base, insert, update, cancel en ns) por venue | Con barras: orden fija O→H→L→C o `bar_adaptive_high_low_ordering`, que la propia doc llama "deterministic heuristic, not a reconstruction". "First visited level determines which order can fill first" | FillModel: `prob_fill_on_limit`, `prob_slippage` (1 tick adverso en L1), seed. `ts_init` tiene que ser el cierre de la barra. Yin et al. 2026 le encontraron 4 defectos |
| **LEAN** (QuantConnect) | Tick, QuoteBar, TradeBar | No encontré modelo de cola | No encontré modelo de latencia en la doc consultada | StopMarketFill no llena con data igual o anterior a la orden (`pricesEndTime <= order.Time`). En gap llena al peor entre el stop y el precio actual ± slippage. Con ticks usa bid/ask | Para futuros por defecto usa FutureFillModel |
| **Backtrader** | Barras OHLC; los ticks se ven como barras sin cerrar | No | No | Orden a mercado al open de la barra siguiente; stops y límites por toque de high/low. "Volume does not play a role" | El bug de comisión ÷100 está documentado (Yin et al.). **No sirve** para resolución tick-exact |

**Para tu funnel**
- La resolución stop-first solo es exacta con ticks (o con barras de 25 ticks bajando a los ticks que la componen).
- Si una estrategia cambia de veredicto entre el orden pesimista y el optimista dentro de la barra, eso es motivo de kill.
- Mesfin llenó stops al precio exacto, que es precisamente la idealización que hay que prohibir.

## 5. Screening de grillas en GPU y cuotas de Kaggle

**Patrones**
- Numba CUDA: `cuda.grid(1)`, chequeo de límites, bloques múltiplos de 32 (warp), lanzamientos asíncronos más `cuda.synchronize()`.
- **El target CUDA integrado en Numba está deprecado; el desarrollo pasó al paquete NVIDIA `numba-cuda`.** [VERIFICADO en la doc de Numba]
- Kernel de first-passage. Esto es diseño mío y no está publicado como paper:
  - un hilo por (combinación de parámetros × evento de entrada);
  - escaneo hacia adelante sobre el array de bid/ask hasta tocar stop, target o tiempo, con el stop evaluado primero;
  - para reducir la divergencia de warps conviene precomputar tablas de rango máximo/mínimo (sparse table) y hacer búsqueda binaria del primer cruce, que cuesta O(log n) por evento.
- Triple barrier en GPU: blog de QuantInsti (practicante).
- Librería spectre (factores y backtest en GPU).
- STAC-A3 de NVIDIA: 20 millones de simulaciones por hora en DGX-2, un benchmark de vendor (HPCwire 2019).
- **No encontré** un paper de revisión por pares específico sobre backtest vectorizado de grillas en GPU.
- VectorBT evalúa los stops contra el OHLC de la barra: la ambigüedad intra-barra se resuelve por supuesto, no por hecho.

**Kaggle [VERIFICADO en la doc, renderizada con un browser headless]**
- **GPU:** "30 hours or sometimes higher depending on demand", con reset semanal (Efficient GPU Usage Tips).
- **Duración de sesión:** "12 hours execution time for CPU and GPU notebook sessions and 9 hours for TPU". Save & Run All tiene que terminar dentro de 12 h.
- **Hardware:**
  - CPU: 4 cores, 30 GB de RAM.
  - P100: 1 GPU, 4 cores, 29 GB.
  - T4 x2: 2 GPUs, 4 cores, 29 GB.
  - TPU 1VM: 96 cores, 330 GB.
  - Salida persistente: 20 GB en /kaggle/working, más scratch no persistente.
- **Inactividad:** la doc de Notebooks dice 20 minutos; la de GPU tips dice "Interactive sessions remain active until they reach the 60 minute idle timeout". Las dos páginas se contradicen.
- **Cuota extra:** Colab Pro y Pro+ dan +15 y +30 h de GPU por semana en Kaggle (experimental).
- **Corridas no interactivas (Kaggle API, `kernel-metadata.json`):**
  - `enable_gpu` (default false) y `enable_internet` (**default false**).
  - `machine_shape`, por ejemplo NvidiaTeslaT4 o NvidiaL4.
  - Inputs: `dataset_sources`, `kernel_sources`, `model_sources`, `competition_sources`.
  - La doc recomienda la API para no gastar cuota en sesiones interactivas.
  - Varias corridas batch del mismo notebook pueden correr en paralelo y todas consumen cuota.
- **Verificación telefónica** para GPU e internet: [SECUNDARIO] (guías de terceros y foros de Kaggle).

## 6. Construcción del contrato continuo

- **Databento** [VERIFICADO]:
  - Símbolos `ROOT.c.N` (calendario), `ROOT.n.N` (ranking por open interest "at the previous day's close") y `ROOT.v.N` (ranking por "previous day's trading volume").
  - Estas reglas son causales: no tienen look-ahead.
  - Los precios se entregan "original, unadjusted": no hace back-adjustment.
- **CME** [VERIFICADO vía snippet de cmegroup.com]:
  - El roll de índices de acciones es "the Monday prior to the third Friday" del mes de vencimiento. Ejemplo 2026: vencimiento 18-sep, roll 14-sep.
  - Muchas fuentes de practicantes citan otra convención, "jueves 8 días antes"; la usaban históricamente.
  - El dato confiable es el cruce de volumen y OI, que puede caer un día antes o después de esa fecha.
- **Carchano & Pardo** (2009, J. Futures Markets 29(7):684–694): con cinco métodos de roll, las series de retornos de futuros de índice no difieren significativamente.
- **López de Prado** (AFML, §2.4.1 ETF trick y §2.4.3 single future roll): acumular los gaps de roll y trabajar con la serie del valor de $1 invertido o con retornos. Hay que evitar precios Panama, que pueden volverse negativos y no sirven para retornos porcentuales.
- **Práctica recomendada para intradía flat al cierre:**
  - elegir el contrato de cada sesión con la regla v o n del día anterior;
  - usar precios crudos de ese contrato;
  - no calcular indicadores a través del roll sin ajuste;
  - registrar en cada resultado la regla, el ajuste y la fecha as-of.
- Mesfin concatenó sin ajuste y sin calendario, y lo admite como limitación.

## 7. Preregistro y protocolos

- **Harvey (2017), "Presidential Address: The Scientific Outlook in Financial Economics"**, JF 72(4):1399–1440.
  - Diagnóstico: pruebas no reportadas, falta de ajuste por pruebas múltiples, p-hacking directo e indirecto.
  - Propone el minimum Bayes factor / "Bayesianized p-value", P(H0 | datos), con prior odds.
- **Harvey, Liu, Zhu (2016)**, RFS 29(1):5–68: más de 316 factores publicados; un factor nuevo necesita t > 3,0.
- **Arnott, Harvey, Markowitz (2019), "A Backtesting Protocol in the Era of Machine Learning"**, JFDS 1(1):64–74. Exhibit 2, "Seven-Point Protocol", que decodifiqué del PDF:
  1. **Motivación.** ¿Hay fundamento económico? ¿Existía antes de la investigación?
  2. **Pruebas múltiples.** Registrar todos los modelos y variables probados, exitosos y fallidos; contar todas las interacciones; ¿se cortó la búsqueda apenas apareció un modelo bueno?
  3. **Datos.** Integridad; transformaciones y winsorización elegidas ex ante (y una sola); reglas de outliers.
  4. **Validación cruzada.** El OOS real solo existe en vivo; no iterar sobre el OOS; el OOS tiene que ser representativo, con costos y revisiones de datos.
  5. **Dinámica.** Cambio estructural, crowding, no tocar un modelo en vivo.
  6. **Complejidad.** Maldición de la dimensionalidad, especificación más simple, interpretabilidad.
  7. **Cultura.** Premiar la calidad científica; asumir que la mayoría de los tests van a fallar.
- **"A Protocol for Quantitative Research" de López de Prado: [NO VERIFICADO], no encontré un trabajo con ese título.** Lo más cercano:
  - "Tactical Investment Algorithms" (SSRN 3459866, 2019): tres paradigmas (walk-forward, resampling, Monte Carlo) y la recomendación de backtestear contra datos sintéticos de un proceso generador estimado (Monte Carlo backtesting).
  - "A Data Science Solution to the Multiple-Testing Crisis in Financial Research" (SSRN 3177057).
  - Fabozzi & López de Prado (2018, JPM), "Being Honest in Backtest Reporting: A Template for Disclosing Multiple Tests".
  - Bailey & López de Prado (2014): Deflated Sharpe Ratio (SSRN 2460551).
  - Bailey, Borwein, López de Prado, Zhu (2017, J. Comp. Finance): PBO.
- **Registered reports en finanzas:**
  - RFS Climate Finance (2017): convocatoria con formato RR y 106 propuestas; el resultado es Hong-Karolyi-Scheinkman, RFS 33(3), 2020.
  - Journal of Accounting Research: conferencia RR desde 2017, cada 3 años.
  - Pacific-Basin Finance Journal: vía de pre-registro.
  - Review of Finance: opción "registered report" según un snippet de búsqueda; no lo verifiqué en la fuente.
  - JF y RFS no la ofrecen como vía estándar.
- **Tests de data snooping:**
  - White (2000), Reality Check, Econometrica 68(5):1097–1126.
  - Hansen (2005), SPA, JBES 23:365–380: tiene más potencia y es menos sensible a reglas pobres.

## 8. Costos para micro futuros

**Especificaciones** [SECUNDARIO, agregadores de specs]

| Contrato | Multiplicador | Tick | Valor del tick |
|---|---|---|---|
| MNQ | $2 × índice | 0,25 | $0,50 |
| MES | $5 | 0,25 | $1,25 |
| M2K | $5 | 0,10 | $0,50 |
| MYM | $0,50 | 1,0 | $0,50 |
| MGC | 10 oz | 0,10 | $1,00 |

**Fees de exchange para no miembros**, según las páginas pass-through de IBKR [VERIFICADO en ibkr.com]:
- Micro E-mini (MES, MNQ, M2K): $0,353 por lado. CME publica $0,35.
- MYM (CBOT): $0,35.
- MGC (COMEX): $0,70 (primera columna; asumo que es la de no miembro).
- E-mini ES, NQ, RTY: $1,386.
- Recupero regulatorio: $0,011.

**NFA** [VERIFICADO en nfa.futures.org]:
- "$.01 per side" desde el 1-jul-2026; sube a $0,02 por lado el 1-jul-2027.
- Es igual para micros.

**Pendiente de verificar:**
- CME publicó la SER 9799 (11-ago-2026) y un fee schedule CBOT con fecha 2026-10-01: es probable que haya cambios de fees vigentes desde el 1-oct-2026. No pude descargar los PDF.
- La comisión del broker no la verifiqué; varía según broker.

**Supuestos en estudios publicados**
- Mesfin: 2,0 pts MNQ ($4) round-trip todo incluido, unas 8 ticks. Fees y NFA solos suman unos $0,72 round-trip, así que es conservador.
- Mesfin: 0,5 pts MGC.
- Zarattini et al.: $0,0035 por acción + $0,001 por acción de slippage, medido en real.

**Recomendación:** un modelo de costos explícito, separado en fees + spread efectivo (medido desde bid/ask tick) + slippage del stop (gap a través del stop). Hacer sensibilidad a ×1, ×1,5 y ×2.

---

## Kill rules citables (preregistrables)

| # | Criterio | Base |
|---|---|---|
| K1 | Hipótesis económica escrita antes de mirar datos, más un registro completo de trials (incluidos los fallidos) | Arnott-Harvey-Markowitz 2019, ítems 1–2; Fabozzi & López de Prado 2018 |
| K2 | t neto OOS ≥ 2,0 por familia preregistrada; ≥ 3,0 si la familia salió de una búsqueda amplia | Mesfin 2026; Harvey-Liu-Zhu 2016 |
| K3 | Deflated Sharpe Ratio con el N real de trials del ledger, más PBO por CPCV (el umbral, por ejemplo PBO < 0,5, es convención y no viene del paper) | Bailey & López de Prado 2014; Bailey et al. 2017 |
| K4 | Edge bruto medio > fricción round-trip, con P_bootstrap(media neta > costo) ≥ 95 % | Mesfin 2026 (11/14 mueren acá; London B 98,9 %) |
| K5 | Al menos 30 trades por fold OOS (no por el total combinado) | Mesfin 2026 |
| K6 | Mismo signo neto en cada año OOS (o régimen) excluyendo los años de entrenamiento | Mesfin 2026 |
| K7 | Test de permutación sobre los timestamps de la señal, más White RC o Hansen SPA sobre la familia completa de reglas probadas | Mesfin 2026; White 2000; Hansen 2005 |
| K8 | Robustez a 1 barra o N ticks de delay: muerte si el signo se invierte | Mesfin 2026, London B |
| K9 | Ordenamiento intra-barra pesimista (stop primero): muerte si el veredicto depende del supuesto OHLC; prohibidos los fills idealizados de stop | Doc Nautilus bar-execution; Mesfin, Tabla A1 |
| K10 | Superar el benchmark incondicional (long en la misma ventana horaria) dentro de cada fold OOS | Mesfin 2026, limitación 3 |
| K11 | Ninguna estadística global de muestra completa en features (baselines de ATR, ajustes de GMM): ajuste por fold, solo con entrenamiento | Mesfin 2026, limitaciones 2–3; Gençay 2026 (look-ahead excluido por construcción) |
| K12 | Testing diferencial de engines: con costo cero tienen que coincidir; con costo, divergencia menor al umbral de materialidad | Yin et al. 2026 |
| K13 | Regla de roll causal (volumen u OI del día previo) y el resultado se mantiene con un roll alternativo | Databento; Carchano & Pardo 2009 |
| K14 | Haircut por decaimiento: exigir margen que sobreviva ~50 % de reducción del edge | McLean & Pontiff 2016 (−58 % post-publicación) |

## Familias de señales

**Con algún soporte publicado**
1. Market intraday momentum en la última media hora (Gao et al. 2018; Baltussen et al. 2021, mecanismo de gamma hedging). Es la más sólida, aunque hay reportes de decaimiento post-publicación.
2. OFI: impacto contemporáneo robusto (Cont et al. 2014, 2023), pero el forecast vive en horizontes de segundos (Kolm et al. 2023; Takahashi 2025). Viable solo con ejecución de baja latencia.
3. Regímenes GMM con hold de 60–75 minutos (controles de Mesfin). Soporte débil: un solo autor, sin revisión por pares, 53+ trials y fills idealizados.
4. ORB en crude oil (Holmberg et al. 2013, sin costos explícitos) y noise area/VWAP en SPY/QQQ (Zarattini et al., SSRN de practicantes, sin revisión por pares).

**Refutadas repetidamente o sin evidencia**
- ORB a 5 minutos en MNQ.
- Expansión y liquidity grab de Asia (refutadas con t muy negativo).
- Gap fill.
- Volume spike y dry-up.
- Drift post-noticia.
- OU intradía en MGC.
- ML (LSTM y GBM) sobre OHLCV a 5 minutos.
- Estrategias descubiertas por LLM bajo evaluación honesta.
- Sin evidencia de revisión por pares: volume profile (POC/VA), auction market theory, absorption/exhaustion de footprint.

---

## URLs

**Papers centrales y MNQ**
- https://arxiv.org/abs/2605.04004
- https://arxiv.org/pdf/2605.04004
- https://arxiv.org/abs/2605.17724
- https://arxiv.org/abs/2603.20319
- https://arxiv.org/html/2603.20319
- https://arxiv.org/abs/2608.27734

**Order flow y microestructura**
- https://arxiv.org/abs/2508.06788
- https://arxiv.org/abs/2607.09230
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1712822
- https://academic.oup.com/jfec/article/12/1/47/816163
- https://arxiv.org/abs/2112.13213
- https://www.tandfonline.com/doi/pdf/10.1080/14697688.2023.2236159
- https://onlinelibrary.wiley.com/doi/10.1111/mafi.12413
- https://jot.pm-research.com/content/8/3/68

**Intraday momentum, ORB, VWAP**
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- https://repub.eur.nl/pub/131621
- https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
- https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download
- https://github.com/codecat-ops/zarattini-2024-momentum-spy
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4631351
- https://econpapers.repec.org/RePEc:eee:finlet:v:10:y:2013:i:1:p:27-33
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6932998

**Engines y backtesting**
- https://github.com/nkaz001/hftbacktest
- https://hftbacktest.readthedocs.io/en/py-v2.1.0/order_fill.html
- https://hftbacktest.readthedocs.io/en/latest/latency_models.html
- https://hftbacktest.readthedocs.io/en/latest/tutorials/Probability%20Queue%20Models.html
- https://hftbacktest.readthedocs.io/en/latest/tutorials/Level-3%20Backtesting.html
- https://hftbacktest.readthedocs.io/en/py-v2.1.0/reference/hftbacktest.data.utils.databento.html
- https://nautilustrader.io/docs/latest/concepts/backtesting/
- https://nautilustrader.io/docs/latest/concepts/backtesting/bar-execution
- https://nautilustrader.io/docs/latest/concepts/backtesting/trade-execution
- https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models
- https://docs.nautilustrader.io/api_reference/backtest.html
- https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/trade-fills/key-concepts
- https://raw.githubusercontent.com/QuantConnect/Lean/master/Common/Orders/Fills/FillModel.cs
- https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/
- https://github.com/polakowo/vectorbt

**GPU**
- https://numba.readthedocs.io/en/stable/cuda/kernels.html
- https://blog.quantinsti.com/triple-barrier-method-gpu-python/
- https://github.com/Heerozh/spectre
- https://www.hpcwire.com/2019/05/13/nvidia-claims-6000x-speed-up-for-stock-trading-backtest-benchmark/

**Kaggle**
- https://www.kaggle.com/docs/notebooks
- https://www.kaggle.com/docs/efficient-gpu-usage
- https://github.com/Kaggle/kaggle-api/blob/main/docs/kernels_metadata.md
- https://github.com/andandandand/practical-computer-vision/blob/main/docs/kaggle-gpu-tpu-guide.md

**Contrato continuo y roll**
- https://databento.com/docs/standards-and-conventions/symbology
- https://www.cmegroup.com/trading/equity-index/rolldates.html
- https://econpapers.repec.org/article/wlyjfutmk/v_3a29_3ay_3a2009_3ai_3a7_3ap_3a684-694.htm
- https://github.com/hudson-and-thames/mlfinlab/blob/master/mlfinlab/multi_product/etf_trick.py
- https://www.quantstart.com/articles/Continuous-Futures-Contracts-for-Backtesting-Purposes/

**Preregistro, pruebas múltiples, decaimiento**
- https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12530
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2893930
- https://people.duke.edu/~charvey/Research/Published_Papers/G138_A_backtesting_protocol.pdf
- https://www.pm-research.com/content/iijjfds/1/1/64
- https://academic.oup.com/rfs/article/29/1/5/1843824
- https://caia.org/sites/default/files/tactical.pdf (404 al momento de leerlo)
- https://www.semanticscholar.org/paper/Tactical-Investment-Algorithms-Prado/b7a5878e528603fc828f80b9cc88282f9bc6b45e
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3177057
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- https://onlinelibrary.wiley.com/doi/abs/10.1111/1468-0262.00152
- https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html
- https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- https://academic.oup.com/rfs/article/33/3/1011/5735309
- https://www.chicagobooth.edu/research/chookaszian/journal-of-accounting-research/registered-reports
- https://en.wikipedia.org/wiki/Registered_report
- https://www.sciencedirect.com/science/article/abs/pii/S0927538X22001329
- https://arxiv.org/pdf/2105.01380

**Costos**
- https://www.nfa.futures.org/faqs/members/nfa-assessment-fees.html
- https://www.interactivebrokers.com/en/accounts/fees/CME.php
- https://www.interactivebrokers.com/en/accounts/fees/COMEX.php
- https://www.interactivebrokers.com/en/accounts/fees/CBOT.php
- https://www.cmegroup.com/company/files/cme-fee-schedule-2026-02-01.pdf (bloqueado)
- https://www.cmegroup.com/content/dam/cmegroup/notices/ser/2026/08/ser-9799.pdf (bloqueado)
- https://www.ironbeam.com/micro-e-mini-futures-contract-specs/
