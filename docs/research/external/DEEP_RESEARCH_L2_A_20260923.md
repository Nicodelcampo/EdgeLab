# Datos L2 en futuros CME para edges netos con latencia minorista: manual de implementación para EdgeLab

El L2 (MBP-10) de EdgeLab tiene más valor económico como instrumento de medición de costos, filtro de contexto y selector de ejecución (pasiva vs. agresiva) que como predictor direccional autónomo. La literatura revisada por pares ubica el horizonte útil de la señal del libro en unas pocas variaciones de precio, cuando la latencia minorista de ida y vuelta es de ~100–250 ms hasta el fill. Con spread y comisión, eso deja fuera casi toda estrategia *taker* basada en predecir el mid-price. La prioridad #1 es medir costos reales con el L2 propio. La #2 es comprar historia MBO barata (Databento) para escapar del problema de los 90 días y de las ~30 sesiones pre-holdout, que no tienen potencia estadística. Recién después conviene entrenar modelos, y conviene empezar por modelos simples sobre features de flujo, no por deep learning.

## TL;DR

- **Predecir el mid-price con el libro no es un edge ejecutable para EdgeLab.** El poder predictivo del libro decae en ~2 cambios de precio promedio (Kolm, Turiel & Westray 2023). Los modelos profundos de LOB pierden rendimiento fuera de muestra (Prata et al. 2024), y una alta precisión predictiva "no corresponde necesariamente a señales de trading accionables" (Briola et al. 2025). Con ~100–250 ms de latencia y ≥1 tick de spread más comisión, una señal solo sirve si predice movimientos de ≥1,5–2 ticks a horizontes de segundos a minutos.
- **Qué hacer ya con los datos pre-holdout:** (1) una tabla de costos por instrumento, hora y tamaño, medida con el L2 propio; (2) curvas de decaimiento de información *target-free* por horizonte, con ablación de latencia (libro retrasado 250 ms); (3) validar la heurística de agresor contra los ticks con agresor que ya existen para el mismo período; (4) usar el L2 como filtro o meta-label de entradas de horizonte medio (1–15 min) que ya existan, no como generador de señales.
- **Qué comprar y qué no hacer:** Databento ofrece MBO de CME desde 2017 (COMEX desde 01/2017), con precio pay-as-you-go por GB y, según su propia página, $125 de crédito alcanzan para ~14 meses de MBO de ES. Eso resuelve la potencia estadística mejor que cualquier arquitectura. No usar VPIN, no tratar los detectores de spoofing/iceberg de MBP como predictivos, y no confiar en fills pasivos simulados con MBP sin un escenario pesimista.

## 1. Resumen ejecutivo: las 10 conclusiones que más cambian el plan

Ordenadas según la jerarquía del §1 (expectativa neta → OOS → robustez → ejecutabilidad):

1. **El cuello de botella es el horizonte, no el modelo.** Kolm, Turiel & Westray (2023), con 115 acciones de Nasdaq, concluyen que "el horizonte efectivo de los pronósticos específicos de cada acción es aproximadamente dos cambios de precio promedio". En GC o ES, dos cambios de mid pueden ocurrir en fracciones de segundo en horas activas. Toda señal debe evaluarse en horizontes ≥ latencia × 3 y con libro retrasado.
2. **Medir costos antes que alpha.** Sin una tabla de spread efectivo, profundidad y slippage por 1..N contratos y por hora, cualquier P&L neto es ficción. El L2 permite construirla hoy (receta en §D.3).
3. **Una estrategia taker necesita que el movimiento esperado supere ~1,3–1,5 ticks por round-trip.** Supuesto a verificar: GC con tick de 0,10 = $10 y ES con tick de 0,25 = $12,50, cruzando un spread de 1 tick más ~$4–5 de comisión round-trip [comisión = supuesto, NO VERIFICADO por broker]. La predicción del mid a un tick (Gould & Bonart) no alcanza a cubrir eso.
4. **Features de flujo simples le ganan al deep learning sobre libro crudo en generalización.** Kolm et al. hallan que los modelos entrenados sobre *order flow* superan a los entrenados sobre el libro. Prata et al. (2024, 15 modelos) reportan caída significativa de todos con datos nuevos. Berti & Kasneci (2025) muestran que un MLP adaptado supera al estado del arte. Empezar por OFI integrado + logística/LightGBM.
5. **30 sesiones no alcanzan para descubrir microestructura rentable con multiplicidad honesta.** Con errores agrupados por sesión y n≈30, el MDE para t≥2 es ≈0,37 desvíos estándar de la media diaria de P&L, y para t≥3 (Harvey-Liu-Zhu) ≈0,55. Hay que comprar historia o usar réplica entre instrumentos como sustituto.
6. **La compra de datos MBO es barata frente al valor que aporta.** Databento cubre GLBX.MDP3 desde 2010-06-06, con MBO real desde 2017. El historial se cobra por GB sin licencia. El plan Standard ($199/mes desde el 22/06/2026) solo incluye 1 mes de historia L2/L3; conviene más pay-as-you-go.
7. **La ablación de latencia es obligatoria y decisiva.** Todo modelo se reentrena y evalúa con features calculadas sobre un libro retrasado 100, 250 y 500 ms, con entrada al precio disponible *después* de la latencia. Si el edge desaparece a 250 ms, no existe para EdgeLab.
8. **Los fills pasivos simulados con MBP son sistemáticamente optimistas.** El propio Databento advierte que todas las plataformas de "market replay" L2 que evaluaron sobreestiman fills buenos y subestiman fills adversos. Toda estrategia con órdenes límite necesita un escenario pesimista (cola al final más *trade-through*) que siga siendo positivo.
9. **La clasificación de agresor es una fuente de error que se puede cuantificar ya.** EdgeLab tiene ticks con campo agresor para mayo–junio 2026 en GC, 6E y ES, que se solapan con el L2. Hay que usarlos como verdad de referencia (o al menos como segunda opinión) para la regla quote+tick. La literatura muestra accuracies de 80–93 % que dependen del mercado, y errores que invierten conclusiones (caso VPIN).
10. **VPIN, spoofing e iceberg sobre MBP: forense, no alpha.** Andersen & Bondarenko (2014) no encuentran poder predictivo incremental de VPIN sobre volatilidad en E-mini una vez que se controla por volumen y volatilidad. Los detectores de spoofing/iceberg sin ID de orden son inferencias ruidosas: su primer uso honesto es como *features de estado* a testear, no como señales.

## Bloque A. Fundamentos del dato

### A.1 MBP-10 vs MBO

**Qué es.** MBO (L3) transmite cada orden con ID: alta, modificación, cancelación y ejecución, con prioridad. MBP-10 (L2) transmite solo el tamaño agregado por nivel de precio en los 10 mejores niveles.

**Qué se pierde sin ID de orden:**
- **Posición en cola.** Solo se aproxima con modelos probabilísticos (ver D.1).
- **Cancelación individual vs. ejecución parcial.** Una caída de tamaño en un nivel puede ser una cancelación o un trade. Se desambigua cruzando con trades en la misma ventana, con error proporcional a la asincronía del reloj NT8.
- **Icebergs reales.** El MDP 3.0 MBO tampoco muestra la cantidad oculta, pero sí la recarga con el mismo ID u orden nueva al final de la cola. Con MBP solo se ve "nivel consumido y repuesto", que es indistinguible de liquidez nueva de otro participante.
- **Vida de órdenes grandes (spoofing).** Con MBP, "una orden grande que vive <5 s" es en realidad "un incremento de tamaño en un nivel que luego desaparece". Puede ser el agregado de muchas órdenes.
- **Censura por profundidad.** Un nivel que sale del top-10 deja de observarse. Databento advierte que eso vuelve mucho más difícil estimar la posición en cola.

**Qué se aproxima bien con MBP:** OFI (Cont-Kukanov-Stoikov se definió sobre el mejor nivel, sin ID), OFI multinivel, queue imbalance, microprice, profundidad, spread, *resiliencia* (tiempo de recarga) y costos de cruce.

**Aplicabilidad.** El núcleo de features con mejor evidencia (OFI, QI, microprice) es 100 % MBP. Lo que requiere MBO (cola, iceberg, spoofing) es justamente lo de menor valor demostrado para un minorista.

### A.2 CME MDP 3.0: semántica y qué sobrevive en NT8

**Semántica relevante (documentación CME):**
- **Tag 5797-AggressorSide** (1=Buy, 2=Sell) en Trade Summary. No hay agresor en la apertura, tras un pre-open, tras una pausa, ni cuando la orden disparadora es una implícita generada por Globex.
- **Tag 5799-MatchEventIndicator.** Bitmap que marca el fin de trades, volumen, cotizaciones reales, estadísticas, cotizaciones implícitas y fin de evento. Permite aplicar actualizaciones transaccionalmente.
- **Tag 60-TransactTime.** "Todos los mensajes que resultan de una misma acción de orden entrante tienen valores consistentes de tag 60 que representan el momento en que CME Globex comenzó a procesar el evento, en granularidad de nanosegundos."
- **Libro implícito.** "CME Group provee un best bid y ask de 2 niveles de profundidad para cada futuro elegible para implícitos" (MDEntryType E/F). La elegibilidad está en la Security Definition (bit 19, *Implied Matching Eligibility*).

**¿GC o 6E tienen implícitos?** Los contratos con calendar spreads listados suelen ser elegibles; el roll GC 06-26 → 08-26 se opera como spread. Que GC y 6E sean elegibles y que NT8 consolide implícito con outright es **[NO VERIFICADO]**. Cómo verificarlo:
1. Comprar un día de Databento MBP-10 del mismo contrato y fecha.
2. Comparar nivel a nivel el top-of-book contra el replay NT8.
3. Si NT8 muestra tamaños mayores en el mejor nivel en momentos de actividad de spreads, está consolidando implícitos.

**Qué se pierde en el replay NT8:** el tag 60 (reemplazado por el reloj de pared de la PC), el tag 5797 (NT8 no lo expone), la secuencia del exchange (reemplazada por source_row) y el 5799 (sin marcas de evento). **Consecuencia clave:** los eventos de un mismo match (un trade que barre 3 niveles) aparecen como varias filas con timestamps posiblemente distintos. Las features calculadas "entre filas" de un mismo evento son artefactos.

**Receta: agrupar pseudo-eventos.**
- Agrupar filas consecutivas con el mismo timestamp de 100 ns, o con Δt < ε (empezar con ε = 1 ms, sensibilidad 0,1–5 ms).
- Tratar cada grupo como una transacción atómica.
- Calcular las features solo en el estado final del grupo.

### A.3 Reconstrucción y validación del libro

**Invariantes a verificar por evento (fallar ruidosamente si no se cumplen):**
- best_bid < best_ask. Un libro cruzado o bloqueado fuera de un grupo atómico se marca.
- Precios estrictamente monótonos por lado.
- Tamaños > 0.
- Posición 0..9 contigua.
- Coincidencia del top-of-book reconstruido con el L1 intercalado. Ya miden ≥99,7 %; reportar la distribución del 0,3 % restante por hora y por volatilidad, porque si se concentra en momentos de alta actividad sesga justo la muestra interesante.

**Gestión de datos defectuosos:**
- **Bootstrap.** Descartar features hasta que el libro tenga 10 niveles por lado y haya pasado un tiempo mínimo (p. ej. 60 s) tras el último ADD de la ráfaga inicial.
- **Días defectuosos.** Construir una lista de exclusión inmutable, versionada en el Edge Brain, con motivo, antes de cualquier análisis. El archivo solapado del 11/08/2026 cae en el holdout, pero la regla de detección (timestamps no monótonos entre archivos, solapamiento >1 min) debe codificarse ya.
- **Huecos.** Si Δt entre eventos supera el percentil 99,99 de la hora del día, marcarlo como hueco e invalidar ventanas de features que lo crucen.

### A.4 Alineación trades–libro y clasificación de agresor

**Evidencia:**
- **Lee & Ready (1991).** Regla de cotización con fallback de tick-test.
- **Chakrabarty, Pascual & Shkilko (2015, JFM)**, con ITCH como verdad: en barras de ~1 h, BVC clasifica bien el 79,7 % del volumen, el tick rule el 90,8 % y Lee-Ready el 92,6 %.
- **Andersen & Bondarenko (2014)**, con datos BBO de CME para E-mini: BVC es inferior al tick rule estándar, y VPIN predice volatilidad solo porque la volatilidad induce errores sistemáticos de clasificación en BVC.
- **Conflicto:** Panayides, Shohfi & Smith (2019, *Journal of Banking & Finance* 103:113–129), con datos de Euronext NextHistory con timestamps al segundo (2007–2008) y de la LSE, concluyen que "BVC-estimated trade flow is the only algorithm related to proxies of informed trading" y que "BVC appears to be the most versatile algorithm", aunque admiten que BVC "may identify trade aggressors less accurately". El resultado depende del mercado, de la precisión temporal y de si se mide exactitud por trade o contenido informativo.

**Aplicabilidad.** EdgeLab tiene ~50/50 compras/ventas con <0,03 % neutral. Esa simetría no valida nada: un clasificador aleatorio también la produce.

**Receta de validación (hacer ya):**
1. Unir los ticks de operaciones con agresor (mayo–junio 2026, GC) con los trades del L2 por precio, tamaño y ventana temporal de ±50 ms.
2. Medir la tasa de acuerdo global y por régimen (spread >1 tick, ráfagas, apertura).
3. **Advertencia:** hay que averiguar de dónde sale el agresor del dataset de ticks. Si también es inferido por NT8 o el proveedor, el acuerdo mide consistencia y no exactitud [NO VERIFICADO].
4. Una sola compra de un día de Databento `trades` (que trae el tag 5797 nativo) da la verdad de referencia real.
5. Propagar el error: recalcular delta y OFI de trades con un p% de signos invertidos al azar y en ráfagas, y reportar la sensibilidad de cada resultado.

### A.5 Fuentes alternativas de L2/MBO

| Fuente | Profundidad | Historia CME | Costo / licencia | Timestamps | Veredicto |
|---|---|---|---|---|---|
| Databento GLBX.MDP3 | MBO, MBP-10, MBP-1, trades | Desde 2010-06-06; MBO real desde 2017 (COMEX 07/01/2017, CME 13/05/2017) | Pay-as-you-go por GB sin comprimir; historial sin licencia; Standard $199/mes (1 mes de L2/L3); Unlimited $4.500/mes (16+ años en todos los schemas) | Captura + exchange (ns) desde 2017-05-21 | **Primera opción** |
| CME DataMine | MBO/MBP FIX | Larga | Institucional, caro [NO VERIFICADO precio actual] | Exchange | Solo si Databento no alcanza |
| Rithmic / CQG / dxFeed | Tiempo real, historia limitada | Corta | Vía broker | Variable | Para ejecución, no para research |
| AlgoSeek, Tardis, LOBSTER | Acciones (LOBSTER), cripto (Tardis) | No CME o sin verificar | Variable | — | Solo para preentrenamiento o comparación |

**La forma más barata de conseguir 1–3 años de MBO:** según la página de precios de Databento, los $125 de crédito inicial alcanzan para "MBO 14 months" de un solo producto (ES). Por extrapolación, ~$9/mes de MBO de ES; GC y 6E, con menos mensajes, deberían costar menos [inferencia; calcular con `metadata.get_cost` antes de comprar]. Tres años de ES+NQ+GC+6E probablemente cuestan del orden de cientos a pocos miles de USD [estimación NO VERIFICADA]. Los tamaños por día no son oficiales: un tercero (NexusFi) estima ~50 GB/mes de MBO de ES front-month, con cifras internamente contradictorias.

### A.6 El problema de los 90 días

**Recomendación: migrar el research a Databento y dejar NT8 para ejecución y paridad en vivo.** Mantener la captura NT8 mensual, porque el feed de ejecución es el que importa para medir la latencia y la paridad feed-vivo vs. research.

**Test de paridad obligatorio:** para 5 días solapados, comparar features (OFI, QI, spread) calculadas en NT8 vs. Databento. Si la correlación a 1 s es <0,95, los modelos entrenados en Databento no son transportables a NT8 sin recalibrar.

## Bloque B. Microestructura: fenómenos y valor económico

Veredicto transversal: casi todos los fenómenos tienen evidencia fuerte como **explicación contemporánea** o predicción a muy corto plazo, y evidencia débil o nula de **rentabilidad neta para un participante lento**.

### B.1 Order Flow Imbalance

**Qué es.** Para cada evento n en el mejor nivel:
e_n = 1{P^b_n ≥ P^b_{n-1}} q^b_n − 1{P^b_n ≤ P^b_{n-1}} q^b_{n-1} − 1{P^a_n ≤ P^a_{n-1}} q^a_n + 1{P^a_n ≥ P^a_{n-1}} q^a_{n-1}.
OFI_k = Σ e_n en el intervalo k. El modelo es ΔP_k = β·OFI_k + ε, con β ∝ 1/profundidad.

**Evidencia:**
- **Cont, Kukanov & Stoikov (2014, JFEC 12(1):47–88).** 50 acciones NYSE (TAQ), ventanas de 10 s. Relación lineal con R² ≥ 50 % en 44 de 50 acciones (presentación de los autores). **Es contemporáneo, no predictivo.**
- **Xu, Gould & Howison (2018).** OFI multinivel.
- **Cont, Cucuringu & Zhang (2023, QF 23(10):1373–1393).** OFI integrado (PCA sobre los niveles) mejora la explicación in- y out-of-sample. Los OFI rezagados de otros activos mejoran el pronóstico, pero ese efecto "se manifiesta principalmente a horizontes cortos y decae rápidamente".

**Fuerza.** Revisado por pares y replicado ampliamente en acciones. En futuros CME hay menos evidencia publicada [buscar réplica específica: pregunta abierta].

**Aplicabilidad.** Alta como feature y como medidor de impacto, baja como señal autónoma a horizontes cortos.

**Experimento target-free.** Curva de R² de OFI_k contra ΔP_k contemporáneo, y de OFI_k contra ΔP_{k+1..k+h} predictivo, para k ∈ {100 ms, 1 s, 5 s, 30 s} y h ∈ {1 s … 5 min}, por hora del día, con el libro retrasado 0/250 ms.

**Hipótesis pre-registrable (económica).** "En GC, el OFI integrado de los últimos 30 s calculado con libro retrasado 250 ms tiene correlación de rango con el retorno del mid a 60 s ≥ 0,05, con IC inferior > 0 bajo bootstrap por sesión." Se refuta si el IC inferior ≤ 0 o si el efecto desaparece al exigir un movimiento > 1,5 ticks.

**Trampas:**
- Usar la fila del trade para calcular un OFI que ya incluye el movimiento de precio (fuga intra-evento; ver A.2).
- Normalizar por la profundidad futura.

### B.2 Queue imbalance y microprice

**Qué es.** QI = (q^b − q^a)/(q^b + q^a) en el mejor nivel. El microprice de Stoikov es P^micro = P^mid + g(QI, spread): el límite de la esperanza de los mids futuros, estimado empíricamente por discretización de QI y spread y construcción de una cadena de Markov.

**Evidencia:**
- **Gould & Bonart (2016, MML).** 10 acciones de Nasdaq, logística del QI sobre la dirección del próximo movimiento del mid. Mejora "considerable" en *large-tick* y moderada en *small-tick*.
- **Stoikov (2018, QF 18(12):1959–1966).** El microprice predice mejor que el mid y que el mid ponderado.
- **Briola et al. (2025).** En large-tick el MCC a H10 sin umbral es 0,29, contra ~0,11–0,13 en small/medium-tick. Su clasificación práctica: large-tick si ⟨spread⟩ ≲ 1,5 ticks, small-tick si ≳ 3 ticks.

**Aplicabilidad.** GC, ES y 6E suelen cotizar con spread de 1 tick en horas líquidas, es decir, en régimen large-tick [verificar con la tabla de costos]. El QI tiene ahí su máximo poder, **pero predice el próximo tick**, que un minorista no captura como taker. Uso realista: (a) decidir si una entrada ya decidida conviene pasiva o agresiva; (b) valorar el inventario con el microprice.

**Experimento.** Función empírica P(próximo movimiento del mid = up | QI por deciles, spread), estable entre semanas. Económico: "ejecutar entradas de la estrategia X como límite en el mejor bid cuando QI > q* y como mercado cuando QI < −q*" contra "siempre mercado", midiendo el costo de implementación.

### B.3 Impacto: Kyle, raíz cuadrada, propagador, resiliencia

**Qué es:**
- **Kyle λ:** ΔP = λ·flujo firmado.
- **Ley de raíz cuadrada:** impacto de un metaorden ≈ Y·σ·√(Q/V).
- **Propagador (Bouchaud et al.):** P_t = Σ G(t−s)ε_s + ruido, con decaimiento de G.

**Referencia.** Bouchaud, Bonart, Donier & Gould (2018), *Trades, Quotes and Prices*, Cambridge University Press.

**Aplicabilidad.** Con 1–5 contratos, el impacto propio de EdgeLab es despreciable frente al spread salvo en horas finas. Lo relevante es el **costo de barrer niveles** (D.3) y la **resiliencia** (tiempo para reponer el nivel consumido), que sirve como feature de estado de liquidez.

### B.4 Hawkes y queue-reactive

**Evidencia.** Huang, Lehalle & Rosenbaum (2015, JASA 110(509):107–122): dentro de períodos con precio de referencia constante, el libro es un sistema de colas markoviano con intensidades que dependen del estado. Sirve como simulador de mercado.

**Aplicabilidad.** Media como **simulador para estimar la probabilidad de fill pasivo** y para generar nulos que preserven la dinámica de colas. Baja como predictor. Se calibra con MBP (intensidades por tamaño de cola en los mejores niveles). CPU: minutos por sesión.

### B.5 Toxicidad: VPIN, realized spread, markouts

**Evidencia.** Easley, López de Prado & O'Hara (2012, RFS) proponen VPIN. Andersen & Bondarenko (2014, JFM 17:53–64), con E-mini: controlando por volumen y volatilidad actuales "no encontramos evidencia de poder predictivo incremental de VPIN para la volatilidad futura", y VPIN no alcanzó extremos antes del Flash Crash. Los autores originales respondieron en Easley, López de Prado & O'Hara (2014), "VPIN and the Flash Crash: A rejoinder", *Journal of Financial Markets* 17:47–52: "This conclusion is wrong, and it is refuted both by other independent research finding just the opposite and by AB's own results"; el mismo volumen incluye el artículo de Andersen & Bondarenko "VPIN and the flash crash" (JFM 17:1–46).

**Veredicto.** No usar VPIN. Usar en su lugar **markouts** de los propios fills simulados: el retorno del mid a +1 s, +10 s y +60 s desde el fill, firmado por lado. Es la métrica directa de selección adversa.

### B.6 Spoofing y layering

**Casos.** La CFTC multó a JPMorgan con $920,2 M (récord) por "cientos de miles" de órdenes spoof en oro, plata, platino, paladio y Treasuries entre 2008 y 2016 (COMEX, NYMEX, CBOT). En agosto de 2022 un jurado federal del Northern District of Illinois condenó a Gregg Smith y Michael Nowak, ex-traders de metales preciosos de JPMorgan, por spoofing, intento de manipulación, fraude de commodities y wire fraud, en un esquema que según el DOJ se extendió "between approximately May 2008 and August 2016"; John Edmonds y Christian Trunz se declararon culpables en casos relacionados, y en 2023 Smith recibió 2 años de prisión y Nowak 1 año y 1 día (Bloomberg Law). Esto confirma que GC fue un mercado con spoofing documentado.

**Implicación.** El spoofing existe en GC. Sin embargo, (a) se detectó con datos de órdenes y comunicaciones internas, no con MBP; (b) si el detector se aplica con éxito, el efecto sobre el precio es justamente engañar, así que seguir la señal aparente es perder. El detector actual (p95 que vive <5 s y ejecuta <20 %) mide *flickering liquidity* agregada.

**Uso honesto.** Feature de estado ("tasa de cancelaciones grandes en el mejor nivel, últimos 60 s") testeada como condicionante de volatilidad (canal no direccional), no como señal direccional.

### B.7 Icebergs

Con MBP se detecta una "recarga repetida", que es consistente con iceberg o con market makers que reponen. Sin ID no hay forma de distinguirlo. **Primer experimento target-free:** tasa base de recarga ≥3 por nivel bajo un nulo de reposición (queue-reactive simulado o permutación de tiempos de ADD dentro de la sesión). Si el detector no supera al nulo, es folklore.

### B.8 Absorción, agotamiento, muros, vacíos

**Evidencia académica directa: escasa.** Los conceptos de Bookmap y footprint son material de practicantes, sin validación publicada fuera de muestra con costos [evidencia de practicante, no prueba]. Lo más cercano académicamente es "el OFI predice el precio con pendiente ∝ 1/profundidad" (Cont et al.): una absorción es un OFI grande con ΔP pequeño, es decir, **profundidad oculta o repuesta**.

**Antecedentes propios.** Coincide con que HP-008 esté falsado y con que HP-007 (vacíos) sea un fenómeno sin edge.

**Reformulación recomendada.** "Residual de impacto": r_k = ΔP_k − β̂·OFI_k. Testear si r_k predice volatilidad o reversión a 1–5 min, con nulo de desplazamiento circular.

### B.9 Estacionalidad y eventos

El poder de todas las features varía por hora (apertura RTH, cierre, fixing de Londres para GC, datos macro 8:30 ET). **Regla:** toda curva de información se estratifica por bloque horario, y los minutos ±2 de datos macro programados se excluyen o se analizan por separado (distribución completa, no media). Rolls: excluir los días de transición de volumen entre contratos o tratarlos como población aparte.

### B.10 Relaciones entre activos

**Evidencia.** Cont, Cucuringu & Zhang (2023): el cross-impact rezagado mejora el pronóstico pero decae rápido.

**Aplicabilidad.** El lead-lag ES/NQ/YM a escala de milisegundos pertenece a los colocados. A escala de segundos a minutos, **GC vs. 6E** (dólar) es plausible como contexto. Con relojes NT8 de la misma PC la sincronía relativa es aceptable, pero la jitter de feed es desconocida. Solo testear con horizonte ≥ 5 s.

## Bloque C. Modelos: qué entrenar y cómo

### C.0 Protocolo común (vale para todos los modelos)

- **Reloj.** Features en *event time* agrupado (A.2) y muestreo en tiempo calendario de 1 s para las etiquetas; así se evita que la densidad de eventos defina la muestra.
- **Etiqueta económica primaria (no F1):**
  - y = +1 si mid(t+L+h) − ask(t+L) > c; −1 si bid(t+L) − mid(t+L+h) > c; 0 en otro caso.
  - L = latencia (250 ms base) y c = comisión + slippage medido.
  - Variante triple barrier: TP/SL en ticks y tiempo máximo h.
- **Horizontes:** h ∈ {5 s, 30 s, 60 s, 300 s, 900 s}.
- **Trampa FI-2010.** Su etiqueta suavizada promedia precios futuros y la normalización usa estadísticas de todo el dataset. No replicar ninguna de las dos cosas.
- **Particionado:**
  - Por sesiones completas, walk-forward o CPCV (López de Prado).
  - *Purging* de muestras cuya ventana de etiqueta cruce el borde.
  - *Embargo* ≥ max(h) más la ventana de features.
  - Normalización con estadísticas solo de train (z-score rolling causal intrasesión o por sesión previa).
- **Early stopping.** Sobre sesiones de validación distintas de test.
- **Semillas.** ≥5 semillas; reportar la varianza entre semillas. Si la varianza entre semillas es comparable al efecto, el efecto no existe.
- **Multiplicidad.** Cada combinación (horizonte × features × hiperparámetros × arquitectura) cuenta como prueba en el registro. N_eff se estima por la correlación de los P&L candidatos (p. ej. clustering) para DSR/PBO.
- **Ablaciones obligatorias:**
  - (a) solo trades, sin libro;
  - (b) libro barajado entre sesiones (placebo);
  - (c) libro retrasado 100/250/500 ms;
  - (d) sin la hora del día.
- **Traducción económica.** Regla completa: umbral de probabilidad → orden de mercado a t+L; salida por h o por barrera; 1 contrato; kill switch diario (−X R) y por deriva de calibración. Métricas netas: expectativa por trade en ticks netos, IC por sesión, hit-rate, P&L por hora y PBO/DSR.

### C.1 Catálogo

| # | Modelo | Entrada | Etiqueta / horizonte | Cómputo (30 sesiones GC) | Evidencia OOS | Aplicabilidad |
|---|---|---|---|---|---|---|
| M0 | Baseline sin libro (trades, retornos, volatilidad, hora) | Agregados de 1 s | Costo, 30–900 s | CPU, segundos | — (referencia obligatoria) | Alta como control |
| M1 | Logística / ridge sobre OFI integrado, QI, microprice−mid, spread, profundidad | ~20–60 features | Costo, 5–300 s | CPU, segundos | Fuerte (CKS, Gould-Bonart, CCZ) | **Alta** |
| M2 | LightGBM sobre M1 + features de estado (resiliencia, residual de impacto, cancelaciones) | ~100 features | Costo / triple barrier | CPU, minutos | Moderada; riesgo de overfitting | **Alta** |
| M3 | L2 como meta-labeling de señales existentes (familias vivas sobre ticks) | Features de M2 en el instante de la señal | ¿La señal supera costos? | CPU | Metodología de López de Prado; evidencia empírica propia a generar | **Alta** (mejor encaje con la latencia) |
| M4 | Clasificador de ejecución: pasiva vs. agresiva / P(fill) | QI, cola, spread, OFI | Fill en T y markout | CPU | Queue-reactive, Gould-Bonart | **Alta** para costos |
| M5 | Hawkes / queue-reactive | Eventos por nivel | Simulación | CPU, minutos a horas | JASA 2015 | Media (simulador, nulos) |
| M6 | DeepLOB (CNN+LSTM) | 10 niveles × 100 eventos | 3 clases de mid | GPU; Kaggle 30 h/semana alcanza | Cae OOS (Prata 2024); no accionable (Briola 2025) | Baja con 30 días |
| M7 | Transformers LOB (TransLOB, TLOB, HLOB, LiT) | Igual | Igual | GPU | TLOB: un MLP ya supera el SoTA; HLOB depende de la microestructura | Baja |
| M8 | Mamba / SSM | Igual | Igual | GPU | Sin evidencia robusta revisada por pares en LOB [NO VERIFICADO] | Muy baja |
| M9 | Preentrenamiento auto-supervisado (LOBERT, MarketGPT) | Mensajes MBO | Representación | GPU grande | Preprints 2024–2025 | Baja hasta tener MBO |
| M10 | Modelo universal pooled (Sirignano & Cont) | Order flow multi-activo | Dirección | GPU | Revisado por pares: universal y estable en acciones de EE. UU. | Media, **después** de comprar datos |
| M11 | Generativos (ABIDES, GAN/difusión, LOB-Bench) | — | Aumento de datos | GPU | LOB-Bench: los datos sintéticos a menudo no mejoran e incluso empeoran el pronóstico | Baja; no usar para descubrir |

### C.2 Fichas resumidas

**M1 (logística sobre features de flujo)**
- **Features:** OFI a 1, 5 y 30 s (niveles 1–10 e integrado vía PCA ajustada en train); QI nivel 1 y QI acumulado de 1–5 niveles; microprice−mid en ticks; spread; profundidad total; volatilidad realizada a 60 s; hora (dummies por bloque).
- **Estandarización** causal.
- **Receta:** 1) calcular sobre el libro retrasado L; 2) muestreo a 1 s; 3) walk-forward de 5 folds por sesión con embargo de 15 min; 4) regularización L2 elegida en validación (grid de 7 valores, contabilizados); 5) calibración de Platt en validación; 6) umbral de operación fijado en validación (p. ej. p>0,6).
- **Mata la hipótesis:** expectativa neta por trade con IC inferior ≤ 0 en test, o si no supera a M0.

**M2 (LightGBM)**
- **Parámetros iniciales:** num_leaves 15, min_data_in_leaf 500, learning_rate 0,03, feature_fraction 0,7, bagging por bloques de sesión, early stopping 200.
- **Riesgo:** con 30 sesiones, las muestras de 1 s están muy autocorrelacionadas; el N efectivo es cercano al número de sesiones × regímenes.
- **Mata la hipótesis:** mejora sobre M1 < varianza entre semillas, o PBO > 0,5.

**M3 (meta-labeling con L2)**
- Tomar eventos de las familias vivas (p. ej. aVolClusterPOI, "vela extrema → carrera asimétrica") definidas sobre ticks.
- Etiqueta: ¿el trade primario fue neto positivo?
- Clasificador M1/M2 con features L2 en el instante del evento. La población es de eventos, no de estados.
- **Ventaja:** horizonte de minutos; la latencia importa poco.
- **Mata la hipótesis:** si filtrar por la probabilidad no mejora la expectativa neta del primario con IC inferior > 0.
- **Advertencia:** el N de eventos puede ser de decenas; publicar el MDE.

**M4 (ejecución)**
- Etiqueta: una orden límite colocada en el mejor nivel en t (supuesto de cola al final, pesimista) ¿se llenaría en T ∈ {5, 30, 60 s}?, y markout a +30 s del fill.
- **Salida:** costo esperado de pasiva = −(prob. de fill × medio spread ganado) + selección adversa + costo de no-fill (perseguir). Se compara con el cruce inmediato.

**M6/M7 (deep learning)**
- Solo tras la compra de MBO de ≥12 meses.
- **Cómputo:** Kaggle ofrece GPU P100 o 2×T4; según su documentación, la cuota "resets weekly and is 30 hours or sometimes higher depending on demand and resources" (se reinicia los sábados a medianoche UTC) y "individual sessions can run up to 9 hours". Alcanza para DeepLOB/TLOB sobre algunos meses de un instrumento (esos modelos tienen del orden de 10⁵–10⁶ parámetros [orden de magnitud NO VERIFICADO por modelo]).
- **Mata la hipótesis:** no supera a M2 en P&L neto con libro retrasado, o la caída OOS entre meses supera el margen.

**Horizonte de información (cuantificación).**
- La literatura da ~2 cambios de mid (Kolm et al.).
- Briola et al. miden que para acciones large-tick los horizontes de 10–100 actualizaciones ocurren a menudo en <1–10 s.
- **Tarea propia:** estimar, para GC/ES/6E y por hora, el tiempo físico mediano de 2, 10 y 100 cambios de mid. Ese número decide qué horizontes son físicamente alcanzables con 250 ms.

### C.3 Plan: primeros modelos, en orden

1. **M0 + M1 en GC** con etiqueta de costo y ablación de latencia. Datos: 30 sesiones pre-holdout. Muere si no hay IC inferior > 0 a h ≥ 30 s con L = 250 ms.
2. **M4 (ejecución)** en GC y 6E. Muere si la pasiva pesimista no ahorra costo frente al mercado en ningún régimen de QI.
3. **M3 (meta-labeling)** sobre 1–2 familias vivas. Muere si no mejora la expectativa neta.
4. **M2**, solo si M1 muestra señal. Muere si PBO > 0,5.
5. **M10/M6 con MBO comprado** (ES, NQ, GC; 2–3 años). Muere si no supera a M2 neto.

## Bloque D. Ejecución y costos

### D.1 Fills sin MBO

**Modelos de cola (hftbacktest).** Asumir la llegada al final de la cola (cantidad por delante = tamaño visible del nivel en t+L). Luego:
- los trades en ese precio consumen primero lo que está por delante;
- las cancelaciones se reparten según un modelo probabilístico (hftbacktest incluye modelos de cola probabilísticos: power, log, etc.);
- **Pesimista:** las cancelaciones nunca adelantan la posición; solo hay fill si el precio *atraviesa* el nivel (trade-through).
- **Optimista:** fill al tocar el precio.

**Regla.** Reportar ambos escenarios. Solo aceptar estrategias positivas en el pesimista. Los fills pasivos se evalúan siempre con su markout (selección adversa).

### D.2 Latencia

**Órdenes de magnitud** (fuentes de practicantes y vendedores, no auditadas):
- Un usuario del foro de NinjaTrader midió órdenes de mercado MNQ desde un servidor en Nueva York de "~170 ms" ida y vuelta hasta el fill (Rithmic ≤140 ms, CQG hasta 250 ms), con ping de ~16 ms a Chicago.
- Una prop firm (Phidias) cita 120–180 ms de París a Chicago.
- Proveedores de VPS citan 50–150 ms desde conexiones residenciales y <1–2 ms de ping desde un VPS en Chicago.
- Desde Argentina, lo esperable es ≥150–300 ms hasta el fill [inferencia NO VERIFICADA].

**Receta para medir la latencia propia:**
- Registrar en NT8 los timestamps de envío, de acknowledgment (OnOrderUpdate "Working") y de fill (OnExecutionUpdate) en una cuenta sim y en una real con 1 contrato micro.
- Registrar también el timestamp local del tick de mercado que muestra el fill.
- Construir la distribución empírica y usarla (p50/p95) en el backtest; hftbacktest acepta latencia interpolada desde datos.

**Pérdida de alpha por latencia.** Se mide con la curva de ablación (C.0-c). La forma teórica es el decaimiento de la correlación señal–retorno.

### D.3 Medir costos con el L2 propio: receta

Por instrumento, bloque de 30 min y día:
1. Spread cotizado medio y distribución (% del tiempo a 1 tick).
2. Profundidad acumulada por lado en los niveles 1..10.
3. **Costo de barrido** de N contratos (N = 1, 2, 5, 10): VWAP de consumir el libro visible en t+L menos el mid(t), en ticks. Es un límite inferior, porque la liquidez puede retirarse durante la latencia.
4. **Slippage por latencia:** mid(t+L) − mid(t), firmado por la dirección de la señal. Sin señal es cero en media; con señal es el costo de llegar tarde.
5. **Spread efectivo** de los trades de mercado: 2·|P_trade − mid| y *realized spread* a +5 s y +60 s.
6. **Comisión real** del broker/prop, por contrato y round-trip.
7. **Salida:** una tabla parquet (instrumento, hora, N, p50/p90 del costo), versionada. Prohibido transportarla entre instrumentos.

### D.4 Mercado vs. límite

**Break-even.** La límite gana si P(fill)·(s/2) − E[selección adversa | fill] − (1−P(fill))·costo de perseguir > −(s/2 + slippage). A horizontes de minutos con spread de 1 tick, la límite suele ganar si la tasa de fill es alta y el markout moderado. A horizontes de segundos, la pérdida por no-fill en los trades ganadores (selección adversa inversa) domina. **Se decide empíricamente con M4.**

### D.5 Prop firms (solo mecánica)

**Reglas típicas** [NO VERIFICADAS para 2026 en esta investigación; consultar las reglas vigentes de la firma elegida]:
- drawdown trailing (intradía o de cierre);
- límite de pérdida diaria;
- regla de consistencia (el mejor día ≤ X % del total);
- límite de contratos.

**Efectos sobre el sizing:**
- El trailing convierte la varianza temprana en riesgo de ruina: dimensionar para P(tocar DD antes de +DD) < 5 % mediante simulación de Monte Carlo con la distribución empírica de trades.
- La consistencia penaliza estrategias de cola derecha.
- El kill switch diario debe ser más estricto que el límite de la firma.

### D.6 Herramientas de backtest con libro

| Herramienta | L2 MBP | L3 MBO | Cola | Latencia | Encaje |
|---|---|---|---|---|---|
| hftbacktest (Python con Numba / Rust) | Sí | Sí | Modelos de cola probabilísticos y custom | Constante o interpolada desde datos | **Mejor encaje**: Python, CPU, conversión desde parquet a su formato npz de eventos |
| NautilusTrader | L2_MBP | L3_MBO | Matching engine; con L2 ignora quotes/trades para ejecución | Configurable | Bueno si se compra Databento (adaptador nativo DBN); curva de aprendizaje mayor |
| Simulador propio (polars/numpy) | — | — | Pesimista/optimista explícito | Distribución empírica | Recomendado como verificación cruzada de uno de los dos anteriores |

## Bloque E. Validación estadística de alta frecuencia

### E.1 Dependencia y potencia

**La unidad efectiva es la sesión.** Las muestras de 1 s son pseudo-réplicas. Usar el bootstrap estacionario por bloques de sesiones (el PrimaryCI actual es correcto) o t-tests sobre las medias diarias.

**MDE con n sesiones:** MDE ≈ (z_{1−α} + z_{1−β})·σ_día/√n. Con n = 30, α = 0,05 bilateral y potencia 0,8: ≈ 0,51·σ_día. Con t ≥ 3: ≈ 0,69·σ_día. Esto es más exigente que el umbral mínimo de significancia del resumen ejecutivo (0,37/0,55), porque aquí se exige además potencia de 0,8. Hay que publicarlo en cada pre-registro.

### E.2 Multiplicidad

**Herramientas:** White (2000) Reality Check, Hansen (2005) SPA, Romano & Wolf (2005) stepdown, Harvey, Liu & Zhu (2016) (t > 3), Deflated Sharpe Ratio (Bailey & López de Prado 2014) y PBO (Bailey et al. 2017) mediante CSCV.

**Conteo:** cada configuración evaluada en validación cuenta, incluidas las descartadas mentalmente. Registrar en el Edge Brain *antes* de correr.

### E.3 Pocos datos

- Walk-forward por sesión con ventana expansiva.
- CPCV con purging.
- **Réplica entre instrumentos como sustituto:** diseñar en GC y replicar sin retocar en 6E; ES queda para una segunda réplica cuando salga de cuarentena. Con presupuesto de multiplicidad separado por instrumento, como exige la regla del §2.4.

### E.4 Nulos para microestructura

| Pregunta | Nulo |
|---|---|
| ¿La feature predice el retorno futuro? | Desplazamiento circular de la serie de features dentro de la sesión (preserva la autocorrelación de ambas series) |
| ¿El detector de eventos es más que azar? | Reubicar los eventos al azar dentro de la misma sesión y bloque horario |
| ¿La dinámica de colas es especial? | Simulación queue-reactive calibrada |
| ¿El modelo usa la información del libro? | Libro barajado entre sesiones (placebo) |
| ¿El P&L de la regla es mejor que el azar? | MCPT con permutación de señales por bloques |

### E.5 Diagnóstico de fuga con reloj de pared

- **Test de adelanto.** Correlación de la feature en t con el retorno en (t−Δ, t]. Si la "predicción" es máxima con Δ negativo pequeño, hay fuga intra-evento.
- **Test de retraso.** El edge debe decaer suavemente con L. Si salta de positivo a nulo entre 0 y 10 ms, era fuga o latencia inalcanzable.
- **Toda feature** se calcula solo con filas con timestamp < t − L y fuera del grupo atómico en curso.

## Bloque F. Estado del arte y del mercado

**F.1–F.2.** No se encontró en esta investigación ninguna revisión 2020–2026 revisada por pares que documente rentabilidad **neta** de estrategias basadas en libro para participantes sin ventaja de latencia en futuros CME. Esa ausencia es informativa. La evidencia disponible es de tres tipos:
- **Negativa o cautelosa sobre accionabilidad:** Briola et al. 2025; Prata et al. 2024.
- **Positiva pero predictiva a horizontes ultracortos:** Kolm et al. 2023; Gould-Bonart.
- **Positiva sobre universalidad y estabilidad de la relación flujo→precio:** Sirignano & Cont 2019. Estable implica conocida, y probablemente arbitrada a escala HFT.

La evidencia específica de decaimiento en CME no se verificó (pregunta abierta).

**F.3.** Lo que queda a nivel minorista, por inferencia razonada:
- (a) el libro como **filtro/contexto** de entradas a varios minutos;
- (b) la **optimización de ejecución** (ahorrar ~0,5 tick por trade puede convertir una estrategia marginal en positiva);
- (c) **estados de liquidez** que condicionan volatilidad y magnitud (canal no direccional).

**F.4.** Casos documentados serios de uso de L2 en ejecución: la literatura de ejecución óptima (Cartea, Jaimungal & Penalva 2015) y el uso del microprice/QI para decidir la colocación. Material de practicantes (Bookmap, footprint): **anecdótico**.

## Bloque G. Herramientas, datasets y código

- **FI-2010.** Solo comparación, y con cuidado: etiqueta suavizada, normalización global, 10 días, acciones nórdicas de 2010. No sirve para preentrenar para CME.
- **LOBSTER** (Nasdaq, mensajes y libro): sirve para replicar CKS/Gould-Bonart y para preentrenamiento de M10 si se busca universalidad.
- **Cripto (Tardis, Binance):** abundante y barato, pero con microestructura distinta (fees maker/taker, 24/7). Solo para desarrollo de pipeline.
- **Databento:** según su FAQ, "new users receive $125 in free data credits for historical data. These credits are shared across your team and expire in six months"; es la fuente recomendada para CME.
- **Repositorios:**
  - LOBCAST (benchmark de 15 modelos, Prata);
  - LOBFrame (Briola);
  - TLOB (Berti; incluye el MLP fuerte);
  - hftbacktest (activo, Python + Rust);
  - NautilusTrader (activo, adaptador Databento);
  - ABIDES (simulador de agentes).
  - Licencias y mantenimiento: revisar al clonar [NO VERIFICADO caso por caso].
- **Visualización:** el visor actual está bien como herramienta de *hipótesis*, no de evidencia. Buenas prácticas:
  - heatmap con escala log de tamaño y percentiles por sesión;
  - marcar pseudo-eventos agrupados;
  - panel de invariantes violados;
  - **censo as-of**: nunca borrar zonas mitigadas del render.

## 4. Hoja de ruta priorizada

| Fase | Entregable | Datos | Cómputo | Criterio de parada |
|---|---|---|---|---|
| F0 (ya, 1–2 semanas) | Validador de invariantes, agrupación en pseudo-eventos, lista de días defectuosos, validación de agresor vs. ticks | Pre-holdout GC/6E | CPU, horas | Acuerdo de agresor <85 % → no usar features de delta sin corrección |
| F1 (ya) | Tabla de costos por hora/N y distribución de latencia propia | Pre-holdout + medición en vivo con micro | CPU | — (siempre se completa) |
| F2 (ya) | Curvas target-free: OFI/QI → retorno por h y L; tiempo físico de 2/10/100 cambios de mid | Pre-holdout | CPU | Si con L = 250 ms ninguna h ≥ 30 s tiene información → abandonar predicción direccional y pasar a F3b |
| F3a | M0/M1/M2 con etiqueta de costo | Pre-holdout | CPU | Criterios de C.3 |
| F3b | M4 (ejecución) y M3 (meta-labeling) | Pre-holdout + ticks | CPU | Criterios de C.3 |
| F4 (compra, ~$ cientos) | 2–3 años de MBO/MBP-10 de GC, ES, NQ, 6E en Databento; test de paridad con NT8 | Databento | CPU; Kaggle GPU para M6/M10 | Paridad <0,95 → recalibrar |
| F5 (2027+) | Réplica en vivo en sim y luego real micro, con acumulación mensual de L2 NT8 | NT8 nuevo | — | Kill switch; desvío vivo vs. backtest > 2σ |

El holdout 2026-07-01 a 2026-12-31 se abre una sola vez, para el candidato final de cada familia.

## 5. Lista de "no hacer"

1. No usar VPIN (Andersen & Bondarenko 2014).
2. No usar FI-2010 ni su etiqueta suavizada como referencia de éxito.
3. No reportar accuracy/F1 como evidencia: Briola et al. 2025 muestran que las métricas de ML no reflejan la accionabilidad.
4. No entrenar DeepLOB/Transformers con 30 días de un instrumento: Prata et al. 2024 muestran caídas OOS incluso con más datos.
5. No usar datos sintéticos generativos para descubrir edges (LOB-Bench: el aumento puede degradar).
6. No aceptar fills pasivos de un "market replay" L2 sin escenario pesimista (advertencia de Databento).
7. No interpretar los detectores de spoofing/iceberg MBP como intención de un participante.
8. No calcular features dentro de un mismo grupo de timestamp (fuga intra-evento).
9. No transportar costos, umbrales ni resultados entre instrumentos.
10. No perseguir lead-lag sub-segundo entre ES/NQ/YM.

## 6. Preguntas abiertas y cómo resolverlas

1. ¿NT8 consolida el libro implícito en GC/6E? → Comparación de un día contra Databento MBP-10.
2. ¿El agresor del dataset de ticks es nativo (tag 5797) o inferido? → Documentación del proveedor más un día de Databento `trades`.
3. ¿Hay evidencia publicada de decaimiento del poder del OFI en futuros CME 2015–2026? → Revisión dirigida; alternativamente, medirlo con Databento año por año (experimento propio decisivo).
4. ¿Cuál es la latencia real de EdgeLab (Argentina → broker → Aurora)? → Medición D.2.
5. ¿Cuánto cuesta exactamente el MBO de GC/6E? → `metadata.get_cost` de Databento.
6. ¿Las reglas vigentes de la prop firm elegida permiten estrategias de minutos con stops cortos? → Lectura de sus términos actuales.
7. ¿El residual de impacto (absorción reformulada) predice volatilidad? → Experimento B.8 con nulo circular.

## 7. Caveats

- Varias cifras operativas provienen de practicantes o vendedores y están marcadas: latencias de foro, estimaciones de GB/mes, reglas de prop firms.
- Los resultados académicos centrales son mayoritariamente de acciones de Nasdaq/NYSE. Su transporte a futuros CME large-tick es una hipótesis a testear, no un hecho.
- Las comisiones usadas en los ejemplos son supuestos.
- Esto es investigación metodológica, no asesoramiento financiero.

## 8. Bibliografía

- Andersen, T. G., & Bondarenko, O. (2014). Reflecting on the VPIN dispute. *Journal of Financial Markets*, 17, 53–64. (CREATES RP 2013-42).
- Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio. *Journal of Portfolio Management*, 40(5). [DOI no verificado en esta sesión].
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The probability of backtest overfitting. *Journal of Computational Finance*. [DOI no verificado].
- Berti, L., & Kasneci, G. (2025). TLOB: A Novel Transformer Model with Dual Attention for Price Trend Prediction with Limit Order Book Data. arXiv:2502.15757.
- Bouchaud, J.-P., Bonart, J., Donier, J., & Gould, M. (2018). *Trades, Quotes and Prices: Financial Markets Under the Microscope*. Cambridge University Press.
- Briola, A., Bartolucci, S., & Aste, T. (2025). Deep limit order book forecasting: a microstructural guide. *Quantitative Finance*, 25(7), 1101–1131. https://doi.org/10.1080/14697688.2025.2522911
- Briola, A., Bartolucci, S., & Aste, T. (2025). HLOB–Information persistence and structure in limit order books. *Expert Systems with Applications*, 266, 126078.
- Cartea, Á., Jaimungal, S., & Penalva, J. (2015). *Algorithmic and High-Frequency Trading*. Cambridge University Press.
- CFTC (2020, 29 sep.). CFTC Orders JPMorgan to Pay Record $920 Million for Spoofing and Manipulation. Press Release 8260-20.
- Chakrabarty, B., Pascual, R., & Shkilko, A. (2015). Evaluating trade classification algorithms: Bulk volume classification versus the tick rule and the Lee-Ready algorithm. *Journal of Financial Markets*.
- Cont, R., Cucuringu, M., & Zhang, C. (2023). Cross-impact of order flow imbalance in equity markets. *Quantitative Finance*, 23(10), 1373–1393. https://doi.org/10.1080/14697688.2023.2236159
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88. https://doi.org/10.1093/jjfinec/nbt003
- Easley, D., López de Prado, M., & O'Hara, M. (2012). Flow toxicity and liquidity in a high-frequency world. *Review of Financial Studies*, 25(5), 1457–1493.
- Gould, M. D., & Bonart, J. (2016). Queue imbalance as a one-tick-ahead price predictor in a limit order book. *Market Microstructure and Liquidity*. https://doi.org/10.1142/S2382626616500064 (arXiv:1512.03492).
- Hansen, P. R. (2005). A test for superior predictive ability. *Journal of Business & Economic Statistics*, 23(4).
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the cross-section of expected returns. *Review of Financial Studies*, 29(1).
- Huang, W., Lehalle, C.-A., & Rosenbaum, M. (2015). Simulating and analyzing order book data: The queue-reactive model. *Journal of the American Statistical Association*, 110(509), 107–122. https://doi.org/10.1080/01621459.2014.982278
- Kolm, P. N., Turiel, J., & Westray, N. (2023). Deep order flow imbalance: Extracting alpha at multiple horizons from the limit order book. *Mathematical Finance*, 33, 1044–1081. https://doi.org/10.1111/mafi.12413
- Lee, C. M. C., & Ready, M. J. (1991). Inferring trade direction from intraday data. *Journal of Finance*, 46, 733–747.
- LOB-Bench: Benchmarking Generative AI for Finance – an Application to Limit Order Book Data (2025). arXiv:2502.09172.
- LOBERT: Generative AI Foundation Model for Limit Order Book Messages (2025). arXiv:2511.12563.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- Prata, M., Masi, G., Berti, L., Arrigoni, V., Coletta, A., Cannistraci, I., Vyetrenko, S., Velardi, P., & Bartolini, N. (2024). LOB-based deep learning models for stock price trend prediction: a benchmark study. *Artificial Intelligence Review*, 57, 116. https://doi.org/10.1007/s10462-024-10715-4
- Romano, J. P., & Wolf, M. (2005). Stepwise multiple testing as formalized data snooping. *Econometrica*, 73(4).
- Sirignano, J., & Cont, R. (2019). Universal features of price formation in financial markets: perspectives from deep learning. *Quantitative Finance*, 19(9), 1449–1459. https://doi.org/10.1080/14697688.2019.1622295
- Stoikov, S. (2018). The micro-price: a high-frequency estimator of future prices. *Quantitative Finance*, 18(12), 1959–1966. https://doi.org/10.1080/14697688.2018.1489139
- White, H. (2000). A reality check for data snooping. *Econometrica*, 68(5).
- Xu, K., Gould, M. D., & Howison, S. D. (2018). Multi-level order-flow imbalance in a limit order book. *Market Microstructure and Liquidity*, 4(03n04), 1950011.
- Zhang, Z., Zohren, S., & Roberts, S. (2019). DeepLOB: Deep convolutional neural networks for limit order books. *IEEE Transactions on Signal Processing*, 67(11), 3001–3012.