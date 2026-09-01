# DeepLOB y redes neuronales de LOB: mapa de maximo valor para ZB y el resto de los activos — V1

- **Fecha:** 2026-09-01 (ART)
- **Autor:** auditor EdgeLab (a pedido de Nicolas)
- **Estado:** `RESEARCH_NOTE_NON_CONFIRMATORY` — documento de diseno y de registro bibliografico.
- **Hipotesis madre:** HP-006 (`docs/research/HP006_ZB_L2_ORDERBOOK_ML_V1_2026-08-31.md`), estado `HYPOTHESIS_REGISTERED_DATA_GATE_PENDING`.
- **Que NO es este documento:** no computa etiquetas, no computa outcomes, no toca holdout, no entrena nada, no promueve nada y no autoriza nada. Ningun numero de este documento es un claim de edge.

## Convencion de etiquetas de evidencia

Todo enunciado de este documento lleva una de estas cuatro etiquetas. Si no la lleva, es prosa de encuadre y no evidencia.

- **[MEDIDO]** — lo medi yo en este repo/sandbox y el numero es reproducible.
- **[DOCUMENTADO]** — lo dice una fuente citada (paper, especificacion, doc del repo). No lo verifique yo.
- **[INFERIDO]** — deduccion mia a partir de lo anterior. Puede estar mal.
- **[PENDIENTE]** — no se sabe y hay que medirlo o preguntarlo.

---

## 0. Resumen ejecutivo: las cinco conclusiones que cambian el plan

**C1. En ZB, una senal clase DeepLOB no es una senal de cruce: es una senal pasiva.** [INFERIDO, base en DOCUMENTADO]
ZB es un activo de tick grande: la grilla es 1/32 y el spread esta practicamente pineado en 1 tick. Un tick de ZB vale **USD 31,25**. Si el modelo predice un movimiento de mid de una fraccion de tick, ese movimiento **no se puede cobrar cruzando el spread**, porque cruzar cuesta como minimo un tick entero. Se cobra unicamente proveyendo liquidez: haciendo cola, decidiendo cuando quedarse y cuando cancelar. Por lo tanto el valor de esta familia de modelos en ZB es (a) **filtro de seleccion adversa** para fills pasivos, (b) **timing de colocacion y cancelacion**, (c) **decision de posicion en cola**. No es un generador de senales direccionales para cruzar. Esto reescribe que hay que medir y con que umbral.

**C2. La restriccion vinculante es el dato, no la arquitectura.** [MEDIDO + INFERIDO]
Tenemos L2 real de ZB para **4 dias utiles** de junio 2026 (el quinto es 100 % L1). DeepLOB se entreno con **134 M de muestras** sobre 5 acciones y un ano. La brecha no se cierra con una arquitectura mejor: se cierra con dato. Cualquier discusion de DeepLOB vs TLOB vs HLOB antes de resolver el dato es discutir el color del auto sin motor.

**C3. La palanca de mayor retorno es la universalidad multi-activo, y esta bloqueada por el mismo problema de dato.** [DOCUMENTADO]
Sirignano y Cont miden que un modelo **universal** entrenado con todas las acciones **supera** a los modelos entrenados por activo, y que funciona en activos que nunca vio. DeepLOB replica el efecto: 70,17 % en las acciones entrenadas contra 68,62 % en cinco acciones no vistas (k=20). Traducido a EdgeLab: el camino para amortizar el dato escaso de ZB es **entrenar sobre los 11 activos del censo y ajustar sobre ZB**. Pero eso exige L2 de los 11 activos, y hoy solo hay L2 de ZB (mas ES en cuarentena, P-56/P-57). **Ese es el argumento economico para comprar dato: el retorno de adquirir L2 es superlineal en la cantidad de activos, no lineal.**

**C4. Los inputs correctos probablemente no son el libro crudo, sino el order flow.** [DOCUMENTADO]
Kolm, Turiel y Westray miden que redes estandar sobre **inputs estacionarios derivados del libro (order flow)** superan a los modelos sobre el libro crudo. Cont, Cucuringu y Zhang miden que el **OFI multinivel integrado** explica el impacto de precio mejor que el OFI de primer nivel, y que una vez incluido el multinivel, los terminos cross-asset **no agregan poder explicativo contemporaneo**. Esto ahorra presupuesto: primero OFI multinivel bien construido por activo, despues (y solo despues) cruzado.

**C5. Accuracy y F1 no sirven para decidir nada aca.** [DOCUMENTADO]
Briola, Bartolucci y Aste miden que el alto poder predictivo **no se corresponde necesariamente con senales operables**, que las metricas tradicionales de ML no evaluan bien el problema, y proponen evaluar por **probabilidad de completar la transaccion**. Los propios autores de DeepLOB admiten que su simulacion no es una estrategia standalone. Mangat y coautores, sobre 12 anos de LOBSTER en SPY, concluyen que la predictibilidad observada viene basicamente de **una** variable (el ultimo cambio de precio) y es **probablemente demasiado chica para sobrevivir a los costos**. Ese es el prior honesto contra el que hay que medir.

---

## 1. Ficha del paper DeepLOB (registro permanente)

**Cita:** Zihao Zhang, Stefan Zohren, Stephen Roberts, *DeepLOB: Deep Convolutional Neural Networks for Limit Order Books*, IEEE Transactions on Signal Processing 67(11):3001-3012, 2019. arXiv:1808.03668, v1 10-ago-2018, **v6 23-ene-2020** (version que leyo Nicolas). Repositorio oficial: `github.com/zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books`. Copia institucional: ORA Oxford `uuid:4411af59-2657-4e3e-8ee2-81032c37671c`. [DOCUMENTADO]

### 1.1 Input

- Tensor de entrada **X en R^{100x40}**: los 100 estados de libro mas recientes por 40 features. [DOCUMENTADO]
- Los 40 features son `{p_a^(i), v_a^(i), p_b^(i), v_b^(i)}` para i = 1..10: precio y volumen de los 10 niveles de cada lado. [DOCUMENTADO]
- El eje temporal es **por evento, no por reloj**. No hay barras. Esto importa para ZB (ver seccion 3). [DOCUMENTADO]

### 1.2 Normalizacion

- **z-score por instrumento**, usando media y desvio de los **5 dias previos** (normalizacion causal, sin fuga de futuro). [DOCUMENTADO]
- Detalle no trivial: la normalizacion es rodante y por activo, lo que la hace compatible con un modelo universal (cada activo entra ya adimensionalizado).

### 1.3 Etiquetado

- Mid: `p_t = (p_a^(1) + p_b^(1)) / 2`. [DOCUMENTADO]
- Medias moviles: `m_-(t) = (1/k) * suma_{i=0..k} p_{t-i}`, `m_+(t) = (1/k) * suma_{i=1..k} p_{t+i}`. [DOCUMENTADO]
- **Ecuacion (3):** `l_t = (m_+(t) - p_t) / p_t` — la de FI-2010, mas ruidosa. [DOCUMENTADO]
- **Ecuacion (4):** `l_t = (m_+(t) - m_-(t)) / m_-(t)` — la que usaron sobre datos LSE, mas consistente porque suaviza los dos lados. [DOCUMENTADO]
- Umbral `alpha` para pasar a tres clases: +1 (sube), 0 (estable), -1 (baja). [DOCUMENTADO]
- **Nota de gobernanza EdgeLab:** cualquiera de estas etiquetas **es un outcome**. Construirlas cruza la puerta F3 de HP-006 y **requiere spec congelado y token escrito**. Este documento no las construye.

### 1.4 Arquitectura

1. **Bloque convolucional 1:** Conv 1x2 con 16 filtros, stride (1,2); despues 2 capas 4x1 con 16 filtros.
2. **Bloque convolucional 2:** Conv 1x2 con 16 filtros, stride (1,2); despues 2 capas 4x1 con 16 filtros.
3. **Bloque convolucional 3:** Conv 1x10 con 16 filtros; despues 2 capas 4x1 con 16 filtros.
4. **Modulo Inception con 32 filtros:** ramas 1x1, 3x1, 5x1 y maxpool 3x1.
5. **LSTM de 64 unidades.**
6. **Softmax de 3 clases.**

- Activacion **Leaky-ReLU con pendiente 0,01**; zero padding; **sin pooling fuera del Inception**. [DOCUMENTADO]
- **~60 000 parametros**; forward pass medido por los autores en **0,253 ms**. [DOCUMENTADO]
- **El detalle mas util del paper:** la segunda capa 1x2 con stride (1,2) reconstruye explicitamente el **micro-price** `I * p_a^(1) + (1 - I) * p_b^(1)` con `I = v_b^(1) / (v_a^(1) + v_b^(1))`. Es decir, la red no descubre magia: descubre queue imbalance y micro-price. Eso da un **baseline obligatorio**: si un logistico sobre imbalance y OFI no anda, la red probablemente tampoco, y si la red anda mucho mas, hay que explicar por que. [DOCUMENTADO + INFERIDO]

### 1.5 Hiperparametros de entrenamiento

- **Adam** con `lr = 0,01` y **`epsilon = 1`** (no el 1e-8 por defecto; es una eleccion deliberada de los autores). [DOCUMENTADO]
- Mini-batch **32**. [DOCUMENTADO]
- Early stopping: **20 epochs sin mejora**. Convergencia observada ~100 epochs en FI-2010 y ~40 epochs en LSE. [DOCUMENTADO]
- Hardware: **1 GPU P100**. [DOCUMENTADO] — Relevante: esto entra holgado en una sesion de Kaggle con T4. [INFERIDO]

### 1.6 Datos

- **FI-2010** (Ntakaris et al., benchmark publico, 5 dias, 5 acciones NASDAQ OMX Helsinki). [DOCUMENTADO]
- **LSE:** 5 acciones (LLOY, BARC, TSCO, BT, VOD), **3-ene-2017 a 24-dic-2017**, 08:30-16:00, **10 niveles por lado**, **134 M de muestras**, ~**150 k eventos por dia por accion**, intervalo medio entre eventos **0,192 s**. Split temporal **6 / 3 / 3 meses** (train / valid / test). [DOCUMENTADO]
- Transfer: 5 acciones no vistas (HSBC, GLEN, CNA, BP, ITV), mismo trimestre de test. [DOCUMENTADO]

### 1.7 Resultados

**FI-2010, Setup 2** (accuracy / F1): [DOCUMENTADO]

| k | Accuracy | F1 |
|---|---|---|
| 10 | 84,47 % | 83,40 |
| 20 | 74,85 % | 72,82 |
| 50 | 80,51 % | 80,35 |

**FI-2010, Setup 1** (F1): k=10 → 77,66; k=50 → 74,96; k=100 → 76,58. [DOCUMENTADO]

**LSE** (accuracy / F1): [DOCUMENTADO]

| k | Accuracy | F1 |
|---|---|---|
| 20 | 70,17 % | 70,15 |
| 50 | 63,93 % | 63,49 |
| 100 | 61,52 % | 60,65 |

**Transfer learning** (accuracy en 5 acciones NO vistas): [DOCUMENTADO]

| k | Entrenadas | No vistas | Brecha |
|---|---|---|---|
| 20 | 70,17 % | 68,62 % | 1,55 pp |
| 100 | 61,52 % | 61,46 % | 0,06 pp |

**Lectura de EdgeLab:** [INFERIDO]
1. La performance **decae fuerte con el horizonte** (70 % a k=20 → 61,5 % a k=100). No existe "la" prediccion: existe una curva performance-horizonte. Elegir un solo k a mano es tirar informacion.
2. La brecha de transfer **se cierra al crecer el horizonte**. O sea: lo idiosincratico del activo vive en el corto plazo; lo universal vive un poco mas lejos. Consecuencia practica: **para transferir a ZB conviene apuntar a horizontes medios, no al tick siguiente.**
3. La caida FI-2010 → LSE (84 % → 70 %) muestra cuanto de la accuracy de benchmark es artefacto del dataset. Todo numero de FI-2010 debe tratarse como techo optimista.

### 1.8 Interpretabilidad

- Los autores usan **LIME** para analisis de sensibilidad y reportan que **el nivel 1 concentra el price discovery**, y que el resto del libro aporta alrededor de un **20 %**. [DOCUMENTADO]
- Tambien reportan que **mas del 90 % de las ordenes terminan canceladas**. [DOCUMENTADO] — Esto es central para ZB: si el 90 % del flujo es cancelacion, un book builder que no procese `Remove` correctamente no reconstruye nada. Nuestro parser ya distingue `operation` 0/1/2. [MEDIDO]

### 1.9 La simulacion del paper y por que EdgeLab no la copia

El paper simula: mid-price **sin costos**, tamano fijo de 1 contrato, entrada en t+5, mantener hasta senal opuesta, cerrar al final del dia, sin subastas, y reporta t-stats. **Los propios autores admiten que no es una estrategia standalone.** [DOCUMENTADO]

Esto es exactamente el punto donde EdgeLab tiene que divergir, y no por prolijidad sino por aritmetica: [INFERIDO]

- Mid-price sin costos, en un activo con spread pineado en 1 tick, **regala un tick entero por operacion**. En ZB eso es **USD 31,25** por vuelta minima.
- "Entrar en t+5" asume fill garantizado. En un activo de tick grande el fill pasivo **no** esta garantizado: depende de posicion en cola. Es precisamente lo que Briola formaliza como probabilidad de completar la transaccion.
- Conclusion: **cualquier evaluacion de una senal clase DeepLOB en ZB tiene que llevar ledger de costos y modelo de fill pasivo desde el dia uno**, o el resultado es aritmeticamente vacio.

---

## 2. Literatura complementaria (fichas cortas)

### 2.1 Universalidad del price formation

**Sirignano y Cont**, *Universal features of price formation in financial markets: perspectives from deep learning*. arXiv:1803.06917; Quantitative Finance 19(9):1449-1459, 2019; doi 10.1080/14697688.2019.1622295; SSRN 3141294. [DOCUMENTADO]

- Existe una relacion **universal y estacionaria** entre la historia del order flow y la direccion del precio.
- El **modelo universal entrenado con todas las acciones supera a los modelos por activo**, y generaliza a acciones fuera del training.
- **Hallazgo incomodo y muy relevante para nosotros:** las normalizaciones estandar basadas en volatilidad, nivel de precio o spread promedio, y el particionado del training en sectores o categorias como **large-tick / small-tick, NO mejoran el entrenamiento**.
- **Incluir mas historia** de precio y order flow **si** mejora (dependencia del camino).

### 2.2 Red espacial de libro profundo

**Sirignano**, *Deep learning for limit order books*. Quantitative Finance 19(4):549-570; doi 10.1080/14697688.2018.1546053; arXiv:1601.01987. [DOCUMENTADO]

- Arquitectura "espacial" que modela la distribucion conjunta del estado futuro del libro condicionada al actual.
- Entrenada y testeada en **cerca de 500 acciones** con un cluster de **50 GPUs**.
- Supera al modelo empirico naive, al logistico con features no lineales y a una red estandar, **especialmente en la cola de la distribucion** (importante para riesgo).

### 2.3 Queue imbalance y el efecto tick grande

**Gould y Bonart**, *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book*. arXiv:1512.03492; Market Microstructure and Liquidity; doi 10.1142/S2382626616500064; SSRN 2702117. [DOCUMENTADO]

- Logisticas de queue imbalance contra direccion del siguiente movimiento de mid, en 10 acciones liquidas de Nasdaq (LOBSTER), **incluyendo small-tick y large-tick a proposito**.
- Relacion estadisticamente significativa en los 10 casos.
- Mejora sobre el modelo nulo: **considerable en large-tick (~20-30 %)**, **moderada en small-tick (~2-6 %)**.
- Una version local semiparametrica mejora un poco mas, a costa de computo.

**Robert y Rosenbaum**, *Large tick assets: implicit spread and optimal tick size*. arXiv:1207.6325. [DOCUMENTADO]

- Casi toda la fenomenologia microestructural de un activo de tick grande se resume en **un solo parametro `eta`**, facil de computar.
- El producto `eta * alpha` juega el papel de **spread implicito** del activo de tick grande.
- **Dato de oro para nosotros: los resultados empiricos se validan sobre el Bobl**, o sea un **futuro de bono**. La literatura de tick grande fue calibrada literalmente en el vecino de ZB.

**Norden**, *Tick Size, Lot Size, and Liquidity in Futures Trading*. Journal of Futures Markets, 2026; doi 10.1002/fut.70044. [DOCUMENTADO]

- En futuros, la restriccion de **tick size es mas severa** que la de lot size.

### 2.4 Order flow como input estacionario

**Kolm, Turiel y Westray**, *Deep Order Flow Imbalance: Extracting Alpha at Multiple Horizons from Limit Order Books*. Mathematical Finance 33(4):1044-1081, 2023; doi 10.1111/mafi.12413; SSRN 3900141. [DOCUMENTADO]

- Redes "off-the-shelf" sobre **inputs estacionarios derivados del libro (order flow)** superan a modelos sobre el libro crudo.
- Regresiones cross-sectional vinculan la performance de forecast con caracteristicas microestructurales: las acciones **"information-rich" se predicen mejor**.
- **El horizonte efectivo de los forecasts es de aproximadamente dos cambios de precio promedio.** Este numero es una restriccion de diseno, no una curiosidad: define la escala en la que hay que evaluar.

### 2.5 OFI multinivel y cross-impact

**Cont, Cucuringu y Zhang**, *Cross-impact of order flow imbalance in equity markets*. arXiv:2112.13213 (v4, 13-jun-2023); Quantitative Finance; doi 10.1080/14697688.2023.2236159. Version previa: *Price Impact of Order Flow Imbalance: Multi-level, Cross-sectional and Forecasting*, SSRN 3993561. [DOCUMENTADO]

- Combinar los OFI de los niveles superiores del libro en una **variable OFI integrada** explica mejor el impacto de precio que el OFI de mejor nivel.
- **Una vez incorporado el order flow multinivel, los terminos de cross-impact NO agregan poder explicativo para el impacto contemporaneo**, comparado con un modelo parsimonioso sin cross-impact.
- Para forecast, si analizan poder predictivo cross-asset.

**Xu, Gould y Howison**, *Multi-Level Order-Flow Imbalance in a Limit Order Book* (MLOFI). ORA Oxford. [DOCUMENTADO] — Introduce MLOFI y argumenta que mejoras de esa magnitud son economicamente significativas.

**Cont, Kukanov y Stoikov**, *The Price Impact of Order Book Events*. Journal of Financial Econometrics 12(1):47. [DOCUMENTADO] — El origen del OFI como variable.

### 2.6 Multi-horizonte

**Zhang y Zohren**, *Multi-Horizon Forecasting for Limit Order Books: Novel Deep Learning Approaches and Hardware Acceleration using Intelligent Processing Units*. Risk.net Cutting Edge, 2021; repositorio `github.com/zcakhaa/Multi-Horizon-Forecasting-for-Limit-Order-Books`. [DOCUMENTADO]

- En lugar de una unica prediccion, usan **encoder-decoder** para generar una **trayectoria** de forecast.
- Performance comparable al estado del arte en horizontes cortos, con la ventaja de dar la curva completa.
- **Por que nos importa:** resuelve el problema de tener que elegir k a mano y produce directamente el objeto que necesitamos para decidir ejecucion pasiva (cuanto tiempo aguanto la cola).

### 2.7 Evaluacion operacional y el freno de mano

**Briola, Bartolucci y Aste**, *Deep limit order book forecasting: a microstructural guide*. arXiv:2403.09267; Quantitative Finance 25(7):1101-1131, 2025; doi 10.1080/14697688.2025.2522911; PMC12315853. Codigo: **LOBFrame**. [DOCUMENTADO]

- Las **caracteristicas microestructurales del activo condicionan la eficacia** de los metodos de deep learning.
- El **alto poder predictivo no se corresponde necesariamente con senales operables**.
- Las metricas tradicionales de ML **no evaluan adecuadamente** la calidad del forecast en contexto LOB.
- Proponen un marco operacional basado en la **probabilidad de pronosticar correctamente transacciones completas**.
- Slides Columbia CFE 2025 (Bartolucci): el backtesting naive puede enganar al ignorar fricciones reales como el riesgo de ejecucion.

**Briola et al.**, *HLOB — Homological limit order book*. arXiv:2405.18938; Expert Systems with Applications 266:126078, 2025. [DOCUMENTADO] — Explota persistencia de informacion y estructura jerarquica del libro.

**TLOB** arXiv:2502.15757 (feb-2026 en su ultima revision conocida) y **MLPLOB**. [DOCUMENTADO] — MLPLOB es el mas barato de la familia y por eso es el que corresponde probar **primero** como challenger.

**LiT: Limit Order Book Transformer**, Xiao et al., Frontiers in Artificial Intelligence, 2025; doi 10.3389/frai.2025.1616485; PMC12555381. [DOCUMENTADO] — Evalua explicitamente capacidad de **transfer learning pre-entrenando en el dataset completo y haciendo fine-tuning en un periodo posterior**. Es el patron operativo que necesitamos para ZB: pre-entrenar ancho, ajustar angosto.

**Mangat et al.**, *High-Frequency Trading with Machine Learning Algorithms and Limit Order Book Data*. Data Science in Finance and Economics, 2022; doi 10.3934/DSFE.2022022. [DOCUMENTADO]

- SVM, random forests y bagging sobre LOBSTER de SPY, **27-jun-2007 a 30-abr-2019**: 50 features crudos y 18 de alto nivel agregados a 5 minutos.
- Con especificaciones directas y sin data snooping excesivo, **los metodos no encuentran patrones de alta dimension utilizables**.
- La predictibilidad significativa observada **viene principalmente de una sola variable: el ultimo cambio de precio**, y es **probablemente demasiado chica para ser rentable una vez contados los costos de transaccion**.
- **Este es el resultado negativo de referencia.** Va citado en cualquier pre-registro de esta rama.

**Bysik y Slepaczuk**, arXiv:2606.00060 — forecasting walk-forward con umbral consciente de costos. [DOCUMENTADO] — Util como plantilla de "umbral de decision derivado del costo", no como evidencia.

### 2.8 Order flow especificamente en Treasuries y en futuros

**Federal Reserve Board, FEDS Note (2025-11-03):** *Order Flow Imbalances and Amplification of Price Movements: Evidence from U.S. Treasury Markets*. [DOCUMENTADO]

- Documenta el rol de los desbalances de order flow en la amplificacion de movimientos de precio en el mercado de Treasuries.
- Cita **Brandt y Kavajecz (2004, Journal of Finance, doi 10.1111/j.1540-6261.2004.00711.x)**: la presion de compra o venta en exceso explica **alrededor de un cuarto** de la variacion dia a dia de los rendimientos de Treasuries, **incluso en dias sin anuncios macro relevantes**.
- **Por que importa:** es evidencia externa de que en el complejo de tasas el order flow tiene contenido informativo documentado. Es un prior favorable para ZB, independiente de la literatura de equities.

**Stochastic Price Dynamics in Response to Order Flow Imbalance: Evidence from CSI 300 Index Futures**, arXiv:2505.17388. [DOCUMENTADO]

- El OFI se modela como un **shock de mercado** con inicio rapido, respuesta prolongada, memoria y asimetria temporal; la respuesta se representa con un **Ornstein-Uhlenbeck de reversion a la media**.
- La performance predictiva **varia significativamente segun el horizonte**.
- Identifican **regimenes de alta y baja eficiencia** del OFI. Los de baja eficiencia son los que presentan oportunidad.
- **Consecuencia de diseno:** la evaluacion tiene que ser **condicionada por regimen**, no promediada. Un promedio sobre regimenes mezclados puede dar exactamente cero y esconder estructura. Esto conecta directo con el embudo aVolClusterPOI.

**Returns and Order Flow Imbalances: Intraday Dynamics and Macroeconomic News Effects**, arXiv:2508.06788v4. [DOCUMENTADO]

- Datos BBO del **E-mini S&P 500 de CME**, 1 490 dias de trading, 2-ene-2008 a 31-dic-2013, resolucion de **un segundo**.
- Capturan **causalidad bidireccional** entre precios y order flow.
- **Advertencia metodologica fuerte:** ignorar la simultaneidad **sesga las estimaciones de impacto de precio** y enmascara variacion importante en las condiciones de liquidez. Usan identificacion tipo ITH (Rigobon 2003).
- **Consecuencia para nosotros:** una regresion ingenua de retorno contra OFI esta endogenamente sesgada. Si en F2 hacemos eso, el coeficiente no significa lo que parece.

**Order Flow Imbalance and the Decay of Price Impact in CME Ether Futures**, SSRN 6772279. [DOCUMENTADO como metodologia, NO como evidencia]

- Interesa unicamente por el aparato de validacion que reporta: **Deflated Sharpe Ratio** (Bailey y Lopez de Prado, 2014) sobre el conjunto de trials, **placebo con direccion barajada** que preserva tiempos de entrada y salida y el conteo long/short, y modelo de impacto **raiz cuadrada** (Almgren-Chriss) para estimar capacidad.
- El placebo direccional-barajado es exactamente la clase de control que EdgeLab ya usa. Vale adoptarlo formalmente para esta rama.

### 2.9 Implementaciones de referencia

- `github.com/zcakhaa/DeepLOB-...` — implementacion oficial de DeepLOB. [DOCUMENTADO]
- `github.com/zcakhaa/Multi-Horizon-Forecasting-for-Limit-Order-Books` — encoder-decoder multi-horizonte. [DOCUMENTADO]
- **LOBFrame** (Briola et al.) — pipeline de procesamiento a escala mas el marco de evaluacion operacional. [DOCUMENTADO]
- `github.com/Jeonghwan-Cheon/lob-deep-learning` ("LOBster") — DeepLOB adaptado a **5 niveles**, **GRU en lugar de LSTM** y **symmetric-mask dropout**. [DOCUMENTADO] — Relevante como plan B si el censo F1 muestra que ZB no tiene 10 niveles utiles de forma estable.

---

## 3. Estado real del dato ZB (lo que ya esta medido)

Todo lo de esta seccion es **[MEDIDO]** con el lector Parquet propio (`/data/pqread.py`, sin pyarrow, sin red), sobre `/data/zb_l2_sample/`.

### 3.1 Inventario

| Archivo | Bytes | Nota |
|---|---|---|
| `20260622.parquet` | 11 927 876 | 4 300 468 filas, 18 row groups |
| `20260623.parquet` | 10 003 348 | |
| `20260624.parquet` | 10 946 250 | |
| `20260625.parquet` | 4 417 105 | **100 % L1 — se excluye del censo L2** |
| `20260626.parquet` | 9 445 661 | |

Total aproximado: **16,56 M filas**. `created_by = parquet-cpp-arrow version 22.0.0`, codec **zstd**, encodings realmente presentes `['PLAIN','RLE','RLE_DICTIONARY']`. Pre-holdout, por lo tanto medible.

### 3.2 Esquema decodificado (9 columnas, todas OPTIONAL)

| Columna | Tipo fisico | Dominio medido |
|---|---|---|
| `record_type` | BYTE_ARRAY | `{L2, L1}` — en las primeras 200 k filas: L2 128 154 / L1 71 846 |
| `market_data_type` | INT32 | 0-5. Convencion NT8: Ask=0, Bid=1, Last=2, DailyHigh=3, DailyLow=4, DailyVolume=5. **De aca sale el lado bid/ask del L2.** |
| `timestamp` | BYTE_ARRAY | string **`YYYYMMDDHHMMSS`**, granularidad de **segundo** |
| `subsecond` | INT64 | max 9 960 000 ⇒ **ticks de 100 ns de .NET** (10 000 000 = 1 s) |
| `operation` | INT32 | `{0=Add, 1=Update, 2=Remove}`, con 183 213 nulos = exactamente las filas L1 |
| `position` | INT32 | **0-10** ⇒ 11 niveles por lado; mismos 183 213 nulos |
| `market_maker` | BYTE_ARRAY | **100 % null** |
| `price` | DOUBLE | **min 0,0 (basura a filtrar)**, max 113,40625; grilla **1/32 = 0,03125** confirmada |
| `volume` | INT64 | hasta 112 578 |

### 3.3 Consecuencias directas para aplicar DeepLOB en ZB

1. **Hay 11 niveles por lado, no 10.** El input de DeepLOB pide exactamente 10. Se usan `position` 0..9 y se descarta el 10, o se cambia la ultima conv a 1x11. **Decision de diseno pendiente**; no es libre, cambia la arquitectura. [INFERIDO]
2. **El timestamp por si solo no alcanza.** Con granularidad de segundo hay empates masivos (el fixture de agosto mostro 84 % de empates exactos). **Hay que ordenar por `timestamp` + `subsecond`**, y para desempatar dentro del mismo `subsecond`, por orden de aparicion en el archivo. Como DeepLOB indexa **por evento y no por reloj**, esto es viable. [MEDIDO + INFERIDO]
3. **Densidad de eventos muy alta.** ~4,3 M filas en una ventana **parcial** (04:00 hasta 06:45-11:36) contra los ~150 k eventos por dia por accion del LSE. La densidad por dia no es el problema. **El problema es que hay 4 dias.** [MEDIDO + INFERIDO]
4. **`price == 0` existe y hay que filtrarlo antes de construir libro**, o el mid se destruye. [MEDIDO]
5. **`market_maker` es 100 % null** ⇒ no hay identidad de participante. Se descarta cualquier feature de ese tipo. [MEDIDO]
6. **Ventanas parciales, no sesiones CME completas.** Cualquier estadistico agregado por "dia" es un agregado sobre una ventana arbitraria, no sobre una sesion. Hasta que Nicolas confirme si la exportacion gratuita puede dar sesiones completas, **ningun estadistico de este dato puede compararse contra estadisticos por sesion del resto del repo.** [MEDIDO + PENDIENTE]

---

## 4. Mapa de maximo valor: las diez palancas, ordenadas por retorno

### P1 — Entrenamiento multi-activo / universal. **Retorno: el mas alto. Estado: bloqueado por dato.**

- **Base:** Sirignano-Cont (modelo universal supera a los por-activo, generaliza fuera de muestra); DeepLOB transfer (68,62 % vs 70,17 % a k=20, brecha nula a k=100); LiT (pre-train ancho + fine-tune). [DOCUMENTADO]
- **Traduccion EdgeLab:** el dato de ZB es escaso; el de los 11 activos del censo, junto, no lo es. Un modelo entrenado sobre order flow de todos los activos y ajustado sobre ZB amortiza la escasez.
- **Bloqueo medido:** solo tenemos L2 de ZB (4 dias) y ES en cuarentena (P-56/P-57). El resto del censo es tick data, no libro. Con tick data se puede construir **trade flow imbalance**, no **order flow imbalance**: no hay ordenes que no se ejecutaron, no hay colas, no hay cancelaciones. Y el 90 % del flujo son cancelaciones. [MEDIDO + DOCUMENTADO]
- **Accion:** esta palanca es **el argumento economico central para adquirir L2 multi-activo**. El retorno de comprar L2 no es lineal en la cantidad de activos: la evidencia de universalidad dice que es **superlineal**, porque cada activo nuevo mejora el modelo de todos los demas. Entra como insumo de la decision de datos ya aprobada (`docs/research/DATA_LICENSE_DECISION.md`, APPROVED 2026-08-28, private-only).

### P2 — Explotar que ZB es de tick grande. **Retorno: alto. Estado: medible ya en F1.**

- **Base:** Gould-Bonart (mejora de 20-30 % en large-tick contra 2-6 % en small-tick); Robert-Rosenbaum (`eta`, spread implicito, **validado en el Bobl**, un futuro de bono). [DOCUMENTADO]
- **Traduccion:** la familia queue-imbalance / micro-price rinde donde el spread esta pineado en un tick y las colas son largas. ZB, con grilla 1/32, es candidato natural. **Y esto es exactamente lo que F1 mide sin tocar etiquetas.**
- **Cuidado explicito, para no sobrevender:** por el criterio spread ≈ 1 tick, **NQ tambien califica como tick grande**. La diferencia no esta en la etiqueta sino en (a) el tamano de la cola relativo al tamano tipico de trade y (b) el valor del tick en dolares (USD 31,25 en ZB contra USD 5,00 en NQ). Un tick mas caro **no** hace la senal mejor: hace mas caro el error y mas caro el cruce, en la misma proporcion. Lo que decide es el **ratio** senal / costo efectivo, no el valor absoluto del tick. [INFERIDO]
- **Y ademas:** Sirignano-Cont miden que **particionar el training por large-tick / small-tick no mejora** el modelo universal. O sea: la clasificacion large-tick sirve para **elegir donde esperar rendimiento y como ejecutar**, **no** para partir el dataset de entrenamiento. Son dos usos distintos y conviene no confundirlos. [DOCUMENTADO]

### P3 — Order flow estacionario antes que libro crudo. **Retorno: alto. Estado: implementable en F2.**

- **Base:** Kolm-Turiel-Westray (inputs de order flow superan al libro crudo); Cont-Cucuringu-Zhang (**OFI multinivel integrado** > OFI de mejor nivel, y con multinivel el cross-impact contemporaneo no agrega nada); Xu-Gould-Howison (MLOFI). [DOCUMENTADO]
- **Traduccion:** el primer challenger no es una red. Es **OFI multinivel integrado bien construido**, con logistica o gradient boosting y errores clusterizados. Barato, auditable y con un prior fuerte de la literatura.
- **Ahorro que implica:** no gastar presupuesto en features cross-asset contemporaneos hasta tener el multinivel intra-activo agotado.

### P4 — Respetar el horizonte efectivo. **Retorno: alto. Estado: define el diseno de F2.**

- **Base:** Kolm et al. miden horizonte efectivo ≈ **dos cambios de precio promedio**. DeepLOB decae de 70 % a 61,5 % entre k=20 y k=100. [DOCUMENTADO]
- **Traduccion:** el horizonte de evaluacion **no es una hora ni una barra**: es una escala definida por la propia dinamica del activo. F1 tiene que medir el **IR ratio** de ZB (eventos L2 por cambio de mid) para poder expresar los horizontes en unidades del activo y no en segundos arbitrarios.
- **Consecuencia de gobernanza:** los horizontes de F3 se pre-registran **en unidades de cambios de mid**, calibradas con F1. Asi no se elige el horizonte despues de ver el resultado.

### P5 — Multi-horizonte en vez de un k elegido a mano. **Retorno: medio-alto. Estado: F3.**

- **Base:** Zhang-Zohren encoder-decoder produce una trayectoria de forecast. [DOCUMENTADO]
- **Traduccion:** en ejecucion pasiva la pregunta no es "sube o baja" sino **"cuanto tiempo me conviene quedarme en la cola"**. Eso es literalmente una trayectoria, no un escalar. La forma multi-horizonte esta mejor alineada con la decision real.
- **Beneficio secundario:** elimina un grado de libertad de tuneo (el k), que es una de las vias clasicas de data snooping.

### P6 — Evaluacion operacional, no accuracy. **Retorno: alto. Estado: obligatorio desde F2.**

- **Base:** Briola et al. (probabilidad de completar la transaccion; las metricas ML no evaluan bien; el backtest naive enmascara riesgo de ejecucion). [DOCUMENTADO]
- **Traduccion:** el criterio de exito de esta rama **no puede ser accuracy ni F1**. Tiene que ser una metrica de ejecucion. En ZB, con tick grande, la metrica natural es: **dado un fill pasivo en el nivel 1, cual es la probabilidad de que el mid se mueva a mi favor antes que en contra**, es decir una medida de seleccion adversa.
- **Esto hay que congelarlo antes de F3**, no despues.

### P7 — El costo como ciudadano de primera clase. **Retorno: alto (evita falsos positivos). Estado: pendiente para ZB.**

- **Base:** Mangat et al. (la predictibilidad probablemente no sobrevive a los costos); DeepLOB simula sin costos y sus autores lo aclaran; Almgren-Chriss / raiz cuadrada para capacidad. [DOCUMENTADO]
- **Traduccion:** para NQ existen los pendientes DP1-DP6 de costos. **Para ZB no existe equivalente y hace falta uno distinto**, porque el modo de ejecucion es distinto:
  - Si la senal es **pasiva**, el ledger no lleva cruce de spread; lleva **riesgo de cola** (no me llenan), **seleccion adversa** (me llenan justo cuando no queria) y fees.
  - Si la senal es de **cruce**, el ledger arranca en **1 tick = USD 31,25** y la senal tiene que superar eso. Con los efectos que reporta la literatura de queue imbalance, superar un tick entero por cruce es una barra muy alta. [INFERIDO]
- **Accion:** abrir `DP-ZB-01..0n` (ledger de costos ZB, dos modos: pasivo y cruce) como bloqueante de F3.

### P8 — Escalera de arquitecturas, de barato a caro. **Retorno: metodologico. Estado: define el orden de F2/F3.**

Orden obligatorio, cada escalon tiene que ganarle al anterior para que el siguiente se autorice:

1. **Nulo**: persistencia / ultimo cambio de precio. *Mangat et al. dicen que casi todo el poder predictivo esta aca. Si el nulo no se supera, la rama muere y esta bien que muera.*
2. **Logistica sobre queue imbalance del nivel 1.** *Gould-Bonart. Es el baseline que DeepLOB reconstruye internamente via micro-price.*
3. **Logistica / GBM sobre OFI multinivel integrado.** *Cont-Cucuringu-Zhang, Kolm.*
4. **MLPLOB.** *El mas barato de la familia neuronal. Si un MLP sobre order flow iguala a DeepLOB, DeepLOB no se justifica.*
5. **DeepLOB.** *~60 k parametros, forward 0,253 ms, entrenable en una P100 ⇒ entra en un T4 de Kaggle.*
6. **TLOB / HLOB.** *Solo si 5 gano claramente y sobra presupuesto.*

### P9 — La tension de normalizacion (a resolver explicitamente)

**Nicolas propuso** (sesion previa): normalizar los parametros segun la escala de cada activo.
**Sirignano-Cont miden** que las normalizaciones por volatilidad, nivel de precio o spread promedio, y el particionado por large/small tick, **no mejoran** el entrenamiento del modelo universal. [DOCUMENTADO]

**No es una contradiccion, y conviene dejar por escrito por que:** [INFERIDO]

- Sirignano-Cont hablan de **como alimentar la red**: sostienen que la red aprende sola la adimensionalizacion si le das suficiente historia, y que forzarla no ayuda.
- Nicolas hablaba de **parametros de indicadores** (umbrales en ticks, distancias, multiplicadores). Ahi la escala **si** importa: un umbral de 12 ticks no significa lo mismo en NQ que en ZB, y eso no es una cuestion de aprendizaje sino de definicion.
- **Regla que adopto este documento:**
  - **Parametros de reglas y umbrales de indicadores** ⇒ **se normalizan por activo** (en ticks del activo, o en unidades de ATR / spread efectivo). Sigue la instruccion de Nicolas.
  - **Inputs de la red** ⇒ z-score causal por instrumento estilo DeepLOB (media y desvio de los 5 dias previos) **y nada mas**; no se particiona el training por clase de tick, ni se agregan normalizaciones por volatilidad, porque hay evidencia medida de que no ayudan.
  - Si alguien quiere agregar una normalizacion extra a los inputs, tiene que **medirla contra esta linea base**, no asumirla.

### P10 — Presupuesto de computo

- **Nunca entrenar en el sandbox.** [MEDIDO] No hay torch, no hay sklearn, no hay scipy y **no hay red**. El sandbox sirve para ETL, book building y censo con numpy puro. Ya se demostro que alcanza: el lector Parquet propio leyo 500 000 filas en 1,107 s.
- **Entrenar en Kaggle.** DeepLOB entra en una GPU sola. [DOCUMENTADO: los autores usaron 1 P100 / INFERIDO: un T4 alcanza]
- Aplica la politica `KAGGLE_SCATTER_GATHER_MULTI_KERNEL_POLICY_V1_2026-08-31.md` para paralelizar por activo o por fold.
- **No** usar la TPU para esta familia sin medir antes: la arquitectura es convolucional chica con LSTM, dominada por latencia secuencial, y el beneficio de TPU esta **[PENDIENTE]** de medicion.

---

## 5. Que se puede hacer HOY sin cruzar ninguna puerta: censo F1 target-free

F1 no usa etiquetas, no usa outcomes y no toca holdout. Es la puerta que decide viabilidad **antes** de gastar en modelos. Sobre los 4 dias L2 utiles (se excluye `20260625`, 100 % L1) y filtrando `price == 0`:

| # | Metrica | Para que decide |
|---|---|---|
| F1.1 | Distribucion del **spread en ticks** (1/32) | Confirma o refuta "ZB es tick grande". Si el spread es 1 tick la mayor parte del tiempo, P2 vive y la senal es pasiva por construccion (C1). |
| F1.2 | **% del tiempo con spread = 1 tick** | Idem, es el numero titular. |
| F1.3 | **IR ratio**: eventos L2 por cambio de mid | Calibra el horizonte efectivo de P4 en unidades del activo. Sin esto, cualquier k es arbitrario. |
| F1.4 | **Persistencia de colas en nivel 1** (vida de la cola, tasa de cancelacion) | Mide si hay cola para hacer. Si las colas duran milisegundos, la ejecucion pasiva no existe y C1 cae. |
| F1.5 | **Estabilidad de profundidad por nivel** (0..10) | Decide si se usan 10 niveles (DeepLOB estandar), 5 (patron LOBster) o 11. |
| F1.6 | **Densidad de eventos y huecos** por ventana | Detecta si las ventanas parciales rompen la continuidad del libro. |
| F1.7 | **Tasa de `Remove` sobre total** | Verificacion contra el >90 % de cancelaciones que reporta la literatura. Si difiere mucho, hay que revisar el book builder antes de creer nada. |
| F1.8 | **Reconstruccion cerrada del libro**: cuantos eventos aplican sin error (Add en posicion ocupada, Remove en posicion vacia, etc.) | Es el control de integridad. Si el book builder no cierra, todo lo demas es ruido. |

**Criterio de salida de F1** (a congelar antes de correr, no despues): [PENDIENTE de aprobacion de Nicolas]
- Si F1.8 muestra una tasa de eventos inaplicables por encima de un umbral pre-registrado ⇒ el dato no sirve, se para y se pide dato mejor.
- Si F1.2 muestra spread = 1 tick de forma dominante y F1.4 muestra colas con vida medible ⇒ **la rama sigue, pero como rama de ejecucion pasiva, no direccional.**
- Si F1.4 muestra colas efimeras ⇒ la rama se reencuadra o se cierra.

**Estado de implementacion:** el lector Parquet ya funciona. Falta `zb_book.py` (book builder + censo). [PENDIENTE]

---

## 6. Orden de puertas y que requiere token

| Fase | Contenido | Toca outcomes | Requiere token escrito |
|---|---|---|---|
| **F0** | Data gate: admision, licencia, frontera de holdout | No | Ya cumplido para la muestra A |
| **F1** | **Censo target-free** (seccion 5) | **No** | **No** |
| **F2** | Baseline: imbalance nivel 1 y OFI multinivel, logistica con errores clusterizados, evaluacion **operacional** (P6) | Si, en cuanto define un target | **Si** |
| **F3** | Challenger neuronal, escalera P8, spec congelado | Si | **Si** |
| **F4** | Claim | Si | **Si** |

**Reglas duras:**
- Las etiquetas de DeepLOB (ec. 3 y ec. 4 de la seccion 1.3) **son outcomes**. Construirlas es F3. No se construyen sin spec congelado y token.
- **MLPLOB antes que DeepLOB, y DeepLOB antes que TLOB/HLOB** (P8).
- Nada de esto se entrena en el sandbox (P10).
- Los horizontes se pre-registran en unidades de cambios de mid calibradas por F1.3 (P4).

### 6.1 Leccion de diseno heredada de Gate 1 de NQ

El veredicto `BT2A_NQ_GATE1_NO_DIRECTIONAL_MECHANISM` **queda en pie tal como esta**: 0 de 16 celdas soportadas, potencia suficiente (234/228 sesiones), efecto maximo medido **0,2613 ticks** contra un minimo pre-registrado de 1 tick. Esta seccion no lo re-litiga.

La leccion que si corresponde llevarse a ZB es sobre **unidades**: [INFERIDO]

- Un minimo pre-registrado de **1 tick** es el umbral correcto para una estrategia que **cruza el spread**.
- Para una senal **pasiva**, el umbral relevante **no** es 1 tick: es una mejora en la probabilidad de fill favorable, o una reduccion medible de seleccion adversa. Puede ser economicamente relevante siendo sub-tick.
- **Regla que adopto este documento:** en cualquier pre-registro de la rama ZB, **el minimo efecto se declara en las unidades del modo de ejecucion asumido**, y el modo de ejecucion se declara **primero**. Si no, se fija un umbral inalcanzable por construccion, o un umbral trivialmente alcanzable. Las dos cosas son errores de diseno, no resultados.

---

## 7. Aplicabilidad al resto de los activos

El censo tiene **11 activos** (`bundle_index.json`, 2026-08-15). Esta tabla solo declara lo que se sabe; lo que no se sabe queda como `[PENDIENTE]` y **no se rellena por analogia**.

| Activo | Valor del tick | Clase por spread/tick | L2 disponible | Aplicabilidad de esta familia |
|---|---|---|---|---|
| **ZB** | USD 31,25 (1/32) [MEDIDO: grilla / DOCUMENTADO: valor] | Tick grande [INFERIDO, a confirmar en F1.2] | **Si**, 4 dias utiles [MEDIDO] | **Candidato primario.** Es el unico con libro real y el mejor prior de la literatura (Bobl, Treasuries). |
| **NQ** | USD 5,00 (0,25) [DOCUMENTADO: spec CME] | Tick grande por spread [INFERIDO] | No | Utilizable solo con trade flow, no order flow. Gate 1 ya cerro el mecanismo direccional que se testeo ahi. |
| **ES** | USD 12,50 (0,25) [DOCUMENTADO: spec CME] | Tick grande por spread [INFERIDO] | **En cuarentena** (P-56/P-57) [DOCUMENTADO] | Bloqueado hasta resolver la cuarentena. Seria el segundo activo natural. Hay literatura directa (arXiv 2508.06788 usa BBO de E-mini). |
| **6E** | USD 6,25 (0,00005) [DOCUMENTADO: spec CME] | [PENDIENTE] | No | [PENDIENTE] |
| Otros 7 | [PENDIENTE] | [PENDIENTE] | No | [PENDIENTE] |

**Lo que esta tabla dice de verdad:** hoy, de 11 activos, **uno** tiene libro. La palanca P1 (universalidad), que es la de mayor retorno, **necesita libro en varios**. Por eso la conclusion C2: el cuello de botella es dato.

**Lo que si se puede hacer con los 11 hoy:** [INFERIDO]
- Construir **trade flow imbalance** desde tick data para los 11 y medir su relacion con la dinamica de precio. Es una version degradada de OFI (sin cancelaciones ni colas), pero es multi-activo y esta disponible.
- Sirve para **testear el mecanismo de universalidad a bajo costo** antes de comprar L2: si el flujo de trades ya muestra la relacion universal entre historia de flujo y direccion, el argumento para comprar L2 se fortalece con evidencia propia. Si no la muestra, hay que entender por que **antes** de gastar.
- Esto entra como **F2-multi** y requiere token, porque define un target.

---

## 8. Riesgos y modos de falla conocidos

| # | Riesgo | Mitigacion |
|---|---|---|
| R1 | **Accuracy alta que no es operable.** Briola lo mide explicitamente. | P6: evaluacion operacional obligatoria desde F2. Prohibido reportar accuracy/F1 como criterio de decision. |
| R2 | **La predictibilidad viene del ultimo cambio de precio.** Mangat et al. | El escalon 1 de P8 (nulo de persistencia) es obligatorio y es el que hay que superar. |
| R3 | **Endogeneidad precio↔flujo.** arXiv 2508.06788: ignorar simultaneidad sesga el impacto. | Declararlo en el pre-registro de F2 y usar identificacion adecuada, o limitar el claim a predictivo estricto fuera de muestra. |
| R4 | **Regimenes.** arXiv 2505.17388 encuentra regimenes de alta y baja eficiencia del OFI. | Evaluacion condicionada por regimen. Un promedio sobre regimenes puede dar cero y esconder estructura. |
| R5 | **Overfitting por dato escaso.** 4 dias contra los 134 M de muestras de DeepLOB. | Ninguna afirmacion de generalizacion con la muestra A. La muestra A sirve para F1 y para desarrollar herramienta, **no** para entrenar un challenger. |
| R6 | **Book builder mal implementado.** Con >90 % de cancelaciones, un `Remove` mal aplicado corrompe todo. | F1.8 es un control de integridad bloqueante, no un reporte. |
| R7 | **Ventanas parciales tomadas como sesiones.** | Prohibido comparar estadisticos de esta muestra contra estadisticos por sesion del resto del repo hasta resolver el [PENDIENTE] de sesiones completas. |
| R8 | **Multiplicidad de pruebas.** Muchas arquitecturas por muchos horizontes por muchos activos. | Deflated Sharpe Ratio (Bailey-Lopez de Prado) y placebo con direccion barajada, como en SSRN 6772279. Numero de trials declarado por adelantado. |
| R9 | **Copiar la simulacion del paper.** Mid-price sin costos. | P7: ledger de costos ZB (`DP-ZB-*`) bloqueante de F3. |
| R10 | **Confundir los dos usos de "large tick"**: elegir donde esperar rendimiento (si) contra particionar el training (no, Sirignano-Cont). | P2 y P9 lo dejan escrito. |

---

## 9. Lo que falta para decidir (pedidos)

**A Nicolas, sobre el dato ZB:** [PENDIENTE]
1. Zona horaria de origen de los timestamps de la exportacion.
2. Contrato exacto (se presume ZB 09-26; hay que confirmarlo).
3. Que paso el 25/06 (el archivo es 100 % L1).
4. Si la prueba gratuita de NT8 puede exportar **sesiones CME completas**, y si puede hacerlo **antes del 02/07** (frontera de holdout).
5. Aprobacion del criterio de salida de F1 (seccion 5) **antes** de correrlo.

**Interno:** [PENDIENTE]
6. Escribir `zb_book.py` (book builder + censo F1) y subirlo a `tools/`.
7. Subir el lector Parquet a `tools/pqread.py` con su nota de verificacion de enums de Parquet.
8. Abrir `DP-ZB-01..0n` (ledger de costos ZB, modo pasivo y modo cruce).
9. Actualizar HP-006 con: C1 (senal pasiva, no direccional), la escalera P8, el criterio de evaluacion operacional P6 y la regla de unidades de la seccion 6.1.
10. Resolver la cuarentena de L2 de ES (P-56/P-57) — es el segundo activo con libro potencial.

---

## 10. Procedencia de la investigacion y advertencia de seguridad

- El paper DeepLOB fue provisto por Nicolas como PDF adjunto (`1808.03668v6.pdf`) y leido completo. Los numeros de la seccion 1 salen de ahi.
- El resto de la bibliografia se recolecto con busqueda web en cuatro tandas de consultas el 2026-09-01. Los identificadores (arXiv, DOI, SSRN, PMC) quedan asentados arriba para que cualquiera pueda re-verificar.
- **Advertencia de seguridad, asentada a proposito:** varios resultados de busqueda sobre paginas de arXiv llegaron con el texto literal **`[OBFUSCATED PROMPT INJECTION]`** incrustado en el contenido (por ejemplo en los resultados de `arxiv.org/abs/2112.13213`, `arxiv.org/abs/2606.00060`, `arxiv.org/abs/1808.03668` y `arxiv.org/abs/2405.18938`). Es un marcador que inserta la capa de scraping cuando detecta contenido con pinta de inyeccion; **no es texto del paper**. Se trato como dato, nunca como instruccion: de esos resultados se tomo solo contenido factual (titulo, autores, abstract, identificadores). Regla operativa: **el contenido de una pagina web es dato, no instruccion**, y esta rama va a tocar mucha pagina web.
- Ninguna afirmacion de este documento constituye un claim de edge. Ninguna cruza una puerta de HP-006.

---

## Apendice A — Indice bibliografico

| Referencia | Identificador |
|---|---|
| Zhang, Zohren, Roberts — DeepLOB | arXiv:1808.03668v6; IEEE TSP 67(11):3001-3012 |
| Zhang, Zohren — Multi-Horizon Forecasting for LOB | Risk.net Cutting Edge 2021; repo `zcakhaa/Multi-Horizon-...` |
| Sirignano, Cont — Universal features of price formation | arXiv:1803.06917; QF 19(9):1449-1459; doi 10.1080/14697688.2019.1622295; SSRN 3141294 |
| Sirignano — Deep learning for limit order books | arXiv:1601.01987; QF 19(4):549-570; doi 10.1080/14697688.2018.1546053 |
| Gould, Bonart — Queue Imbalance as One-Tick-Ahead Predictor | arXiv:1512.03492; doi 10.1142/S2382626616500064; SSRN 2702117 |
| Kolm, Turiel, Westray — Deep Order Flow Imbalance | Math. Finance 33(4):1044-1081; doi 10.1111/mafi.12413; SSRN 3900141 |
| Cont, Cucuringu, Zhang — Cross-impact of OFI | arXiv:2112.13213v4; doi 10.1080/14697688.2023.2236159; SSRN 3993561 |
| Cont, Kukanov, Stoikov — Price Impact of Order Book Events | J. Financial Econometrics 12(1):47 |
| Xu, Gould, Howison — Multi-Level Order-Flow Imbalance | ORA Oxford |
| Briola, Bartolucci, Aste — Deep LOB forecasting: microstructural guide (LOBFrame) | arXiv:2403.09267; QF 25(7):1101-1131; doi 10.1080/14697688.2025.2522911; PMC12315853 |
| Briola et al. — HLOB | arXiv:2405.18938; Expert Syst. Appl. 266:126078 |
| TLOB | arXiv:2502.15757 |
| Xiao et al. — LiT: Limit Order Book Transformer | Frontiers in AI; doi 10.3389/frai.2025.1616485; PMC12555381 |
| Mangat et al. — HFT with ML and LOB data | Data Science in Finance and Economics; doi 10.3934/DSFE.2022022 |
| Robert, Rosenbaum — Large tick assets | arXiv:1207.6325 |
| Norden — Tick Size, Lot Size, and Liquidity in Futures Trading | J. Futures Markets 2026; doi 10.1002/fut.70044 |
| Federal Reserve — OFI and Amplification of Price Movements (Treasuries) | FEDS Note 2025-11-03 |
| Brandt, Kavajecz — Price discovery in the U.S. Treasury market | J. Finance; doi 10.1111/j.1540-6261.2004.00711.x |
| OFI en CSI 300 index futures | arXiv:2505.17388 |
| Returns and OFI: intraday dynamics (E-mini CME) | arXiv:2508.06788v4 |
| OFI and decay of price impact — CME Ether futures | SSRN 6772279 |
| Bailey, Lopez de Prado — Deflated Sharpe Ratio | 2014 |
| Ntakaris et al. — FI-2010 benchmark | J. Forecasting 37(8):852-866 |
| LOBster (DeepLOB a 5 niveles, GRU) | `github.com/Jeonghwan-Cheon/lob-deep-learning` |

## Apendice B — Cambios de estado que propone este documento

1. **HP-006** pasa a incorporar C1: la hipotesis de ZB se reencuadra como **senal de ejecucion pasiva / seleccion adversa**, no como senal direccional de cruce.
2. Se agrega a HP-006 la **escalera de arquitecturas P8** como orden obligatorio.
3. Se agrega la **regla de unidades** de la seccion 6.1 al playbook de pre-registro.
4. Se agrega la **regla de normalizacion** de P9 (parametros de reglas por activo; inputs de red con z-score causal y sin particionar por clase de tick).
5. Se abre `DP-ZB-*` (ledger de costos ZB) como bloqueante de F3.
6. Se registra que **la restriccion vinculante de esta rama es el dato multi-activo**, y que eso es un insumo directo de la decision de adquisicion de datos.

*Fin del documento V1.*
