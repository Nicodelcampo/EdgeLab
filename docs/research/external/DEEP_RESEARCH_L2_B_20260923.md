# Manual de implementación de L2 para buscar y ejecutar edges netos

**EdgeLab · Deep Research L2 · 23 de septiembre de 2026**  
**Propósito:** guía de investigación e implementación; no es asesoramiento financiero ni afirmación de que exista un edge.  
**Lectura rápida:** con el feed, la muestra y la latencia descritos, L2 sirve primero para medir estados, costes, riesgo de selección adversa y ejecución. La evidencia publicada sobre predicción de mid-price—sobre todo en milisegundos y en acciones—no demuestra rentabilidad neta para un trader minorista en GC/ES/6E.

## Convenciones de evidencia y decisión

- **[Revisado por pares]** evidencia publicada; su mercado, muestra y tarea originales limitan cualquier transferencia. **[Preprint]** estado editorial no confirmado. **[Práctica]** documentación/producto o experiencia reportada. **[Hipótesis EdgeLab]** a comprobar.
- **[NO VERIFICADO]** fuente, coste, licencia o cifra no se pudo confirmar; no tratar como hecho.
- Secuencia de evidencia: integridad → geometría/lifecycle *target-free* → información condicional → P&L bruto → coste/fill/latencia → multiplicidad/robustez → réplica/operación.
- El holdout sellado **2026-07-01 a 2026-12-31** queda fuera de diseño, selección de features/horizontes, calibración de costes, hiperparámetros y elección de candidatos. Solo visor e integridad según el protocolo; cualquier apertura futura será única y autorizada por candidato.

# 1. Resumen ejecutivo: diez conclusiones

1. **NT8 Replay no es el reloj del matching engine.** `source_row` es orden de archivo, no secuencia CME; precisión de 100 ns no es exactitud. No inferir causalidad en empates sin verificar secuencia nativa.
2. **MBP-10 no es MBO.** Hay profundidad agregada hasta diez niveles; no IDs de orden/prioridad, cola propia identificada ni iceberg/spoof inequívocos. Nombrarlos proxies cuando se infieren de MBP.
3. **Comenzar con baseline económico simple.** Trades-only y features manuales L2 (OFI, queue imbalance, microprice) con regresión lineal/logística; boosting después. No empezar por Transformers con decenas de sesiones.
4. **La pregunta clave es valor L2 después de latencia.** Medir markouts desde que la señal habría sido observable hasta el arribo simulado. Stress grid primero; sustituir por distribución propia medida. AUC a 10 ms no equivale a fill minorista.
5. **Predicción académica no es P&L neto.** OFI en 50 acciones NYSE y queue imbalance en 10 acciones Nasdaq son motivación, no evidencia directa de edge ejecutable en CME.
6. **Fills pasivos son el mayor riesgo del backtest MBP.** Touch no llena. Reportar bandas de fill conservador/intermedio/optimista; mercado histórico no responde a nuestra orden.
7. **Costes por instrumento, hora, tamaño y orden.** Fee schedule real + spread + slippage + fill ratio + latency + markouts. Walk-the-book L2 es impacto mecánico observado, no efecto causal contrafactual.
8. **No rescatar por subgrupos post hoc.** BigTrap2, HP-008, HFTZones, HP-007 y aVolClusterPOI son antecedentes/limitaciones, no nuevos hallazgos. Preregistrar universo, falsador, búsqueda, N efectivo, MDE y nulo.
9. **Un nulo bien acotado vale.** 30 sesiones GC (roll/contratos simultáneos) y pocos días 6E no justifican universalidad, eventos raros ni generalización temporal. Capturar datos nuevos y mantener holdout sellado.
10. **Matar si se esfuma al retrasar, cobrar o ajustar por búsqueda.** Sin ventaja neta robusta con fills adversos y latencia observada, no operar capital real.

# 2. A. Fundamentos de datos

## A1. MBP-10 vs MBO

CME describe MBP como cantidades y recuento agregados por precio en hasta diez niveles; MBO expone órdenes individuales anónimas, OrderID/PriorityID y profundidad completa. Con MBO se puede seguir prioridad/cola; con MBP no se determina con alta exactitud tamaño individual ni posición. [CME, “Market by Order (MBO)”](https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html)

**Observable en MBP:** cambios agregados por nivel/precio, spread, profundidad, OFI, desplazamientos y secuencias de replenishment; trades/L1 si su sincronización es válida. **No identificado:** quién canceló, si reducción agregada fue cancelación o una o varias ejecuciones, cola propia, prioridad individual, iceberg nativo inequívoco, intención manipulativa, ni niveles >10. La desaparición de una posición también desplaza el resto; reconstruir el book según semántica de update, no tratar fila posicional como orden.

Para un límite, la cantidad agregada al precio en llegada aproxima cola delante, pero cancelaciones, trades, eventos empatados, volumen detrás y latencia hacen la cola incierta. No hay “error universal”: medir contra propios fills/MBO validado.

## A2. CME MDP 3.0, Replay y reloj

MDP incluye semántica más rica: incremental refresh, secuencias, trade summaries, indicadores de evento, implied quotes y marcas de agresor según mensaje/producto. Fuentes: [MDP 3.0 Market Data](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457219613/CME+MDP+3.0+Market+Data), [Event Based Messaging](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457325420/MDP+3.0+-+Event+Based+Market+Data+Messaging). **No suponer** que el export NT8 conserva `MatchEventIndicator`, secuencia CME, `AggressorSide`, implied flag o exchange timestamp: no figuran en el esquema informado. Comprobar columnas y cotejar muestra con feed que sí los tenga.

NinjaTrader indica sincronía L1/L2 en Replay, timestamps almacenables con resolución de 100 ns, pero la granularidad depende de proveedor; Replay futures servido por NT cubre últimos ~90 días. [NinjaTrader Playback](https://support.ninjatrader.com/s/article/How-Do-I-Connect-to-NinjaTrader-Desktop-s-Playback-Feature?language=en_US). Esto no vuelve al wall clock timestamp del matching engine.

**Regla causal:** mantener timestamp raw, `source_row`, tipo/canal y `ordering_ambiguous`; no inventar secuencia dentro de empates. Principal: usar features después de cerrar el empate. Sensibilidad: ordenamientos extremos si el resultado cambia. Registrar UTC y hora original UTC-3, calendario de sesión, contrato/roll, daylight-saving, gap y checksum.

## A3. Reconstrucción y QA

Contrato por archivo: instrumento/contrato, sesión, zona horaria, proveedor, parser/schema, escala/tick, hash raw, rango y conteos L1/L2, duplicados, gaps, overlaps, bootstrap y estado `usable/quarantined`. Preservar raw inmutable. Invariantes: bootstrap completo; precios sobre tick; bids y asks ordenados; tamaños no negativos; deletes válidos; niveles coherentes tras insert/change/delete/shift; cruces persistentes explicados; comparación best book vs L1 con convención explícita para empates; gaps/duplicados/overlaps; archivos “Success” sin L2 rechazados; reset al inicio o tras gap no reparable. Medir discrepancias con ejemplos, no solo PASS.

La coincidencia L1 ≥99,7% referida por usuario es dato de contexto, no revalidación independiente ni garantía de niveles profundos. No imputar un día faltante con el próximo; cuarentena a la sesión defectuosa y a overlap hasta resolverla. Auditar el DELETE excepcional nivel 10 sin normalizarlo silenciosamente.

Primero target-free: QA, distribuciones de spread/depth, continuidad y lifecycle; excluir segmentos mediante reglas previamente fijadas, no según retorno observado.

## A4. Lado agresor y sincronización trades/book

Quote rule: trade al ask/bid clasifica comprador/vendedor agresor; dentro del spread, con quote stale o simultaneidad puede ser desconocido. Tick-test compara con trade previo; Lee–Ready aplica midpoint/lag; BVC infiere buckets, no observa agresor. Con timestamps de pared, matching nearest quote puede inducir error. Preservar `UNKNOWN`, distancia a bid/ask y clasificador usado.

Un preprint reciente de 14,3 M trades ES compara clasificadores con exchange flags y sugiere que clasificación quote-based depende críticamente de sincronía/empates; no valida NT8. [Silverman, “Trade Classification Error Is Not Where You Would Expect…”](https://papers.ssrn.com/sol3/Delivery.cfm/7435320.pdf?abstractid=7435320&mirid=1) **[Preprint; estatus editorial no verificado].** Chakrabarty et al. comparan tick/BVC y muestran dependencia de instrumento y especificación. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2182819). Andersen & Bondarenko encuentran que VPIN-BVC no agrega poder para volatilidad futura una vez controlados intensidad/volatilidad. [Paper](https://pure.au.dk/ws/files/68359010/rp13_43.pdf).

**Validar:** obtener periodo solapado con lado agresor nativo/IDs o etiquetas exchange; medir matriz de confusión, balanced accuracy, coverage y error por contrato/hora/spread/empates. Si ground truth no existe, informar sensibilidad entre quote, tick, BVC y neutralización; no afirmar exactitud.

## A5. Fuentes de historia y licencias

| Fuente | Evidencia pública | Uso recomendado / brecha |
|---|---|---|
| NT8 Replay | Replay de futuros últimos 90 días según NinjaTrader; L1/L2 sincronizados, granularidad de timestamp heredada del proveedor. | Capturar ahora cada mes; útil para MBP/visor, no recupera meses perdidos. |
| Databento GLBX.MDP3 | CME; schemas MBP-10 y MBO; pricing histórico usage-based/planes, historial anunciado de 16+ años. Docs distinguen timestamps. | Pedir cotización idéntica y muestra antes de elegir. [Pricing](https://databento.com/pricing), [MBP-10](https://databento.com/docs/schemas-and-data-formats/mbp-10), [MBO](https://databento.com/docs/schemas-and-data-formats/mbo), [timestamps CME](https://databento.com/docs/venues-and-datasets/glbx-mdp3). |
| CME DataMine | Catálogo oficial con categorías históricos Market Depth y MBO. | Pedir quote por contrato/fechas/formato/licencia. [DataMine](https://www.cmegroup.com/datamine.html), [data products](https://www.cmegroup.com/market-data/real-time-and-historical-data.html). |
| Rithmic, dxFeed, AlgoSeek | Servicios comerciales; productos/licencias difieren. | Profundidad, timestamps, fees/licencia vigentes **[NO VERIFICADO]**. Exigir data dictionary, muestra y términos. |
| LOBSTER/FI-2010 | Equity LOB, no futuros CME. | Debug/benchmark reproducible; no validación de GC. |
| Tardis | Cripto/exchanges. | Transferencia de código/pretraining solamente; régimen y venue distintos. |

**Más barato para 1–3 años MBO:** no determinable sin cotizaciones comparables y derechos escritos. Comparar Databento usage-based y CME DataMine para una muestra idéntica (1 mes GC/ES/6E, MBO y MBP-10), incluyendo fees de exchange, licencia de uso interno/derivados/publicación, almacenamiento y egress. No publicar datos reconstructibles sin permiso. MBO solo si el falsador requiere cola/orden individual; OFI/estado quizá basta MBP-10.

# 3. B. Fenómenos de libro: fórmula, evidencia y límite

## B1. OFI, queue imbalance, microprice

OFI combina cambios en bid/ask best price y size: suma entradas de demanda y retiros de oferta, resta entradas de oferta y retiros de demanda; fijar signo/fórmula exactos. Variante multi-level pondera niveles por distancia/depth. Cont, Kukanov & Stoikov reportan relación lineal de cambio de precio con OFI y pendiente inversa a depth, en 50 acciones NYSE, no CME: *The Price Impact of Order Book Events*, *Journal of Financial Econometrics* 12(1), 47–88 (2014), DOI [10.1093/jjfinec/nbt003](https://academic.oup.com/jfec/article/12/1/47/816163).

`QI=(Q_bid−Q_ask)/(Q_bid+Q_ask)`. Microprice pondera bid/ask por size opuesto, por ejemplo `(ask·Q_bid+bid·Q_ask)/(Q_bid+Q_ask)` según convención. Gould & Bonart observan predicción del próximo cambio de mid en 10 acciones Nasdaq y dependencia large-/small-tick; no net P&L a latencia minorista. *Queue Imbalance as a One-Tick-Ahead Price Predictor…* (2016), DOI [10.1142/S2382626616500064](https://arxiv.org/abs/1512.03492). Medir por contrato tick/spread, horizon y demoras.

## B2. Impacto/resiliencia

Kyle lambda: `Δp=λ·signed_volume+ε`. Estimar por horizon y depth/vol controls; distinguir impacto transitorio/permanente. Square-root law para metaórdenes `I(Q)≈Yσ√(Q/V)` es regularidad agregada bajo contextos/supuestos, no slippage de 1 contrato. Propagator models separan impacto transitorio y autocorrelación de flujo; estimarlos con suficiente longitud.

Resiliencia = curva de recuperación de spread/depth/intensidad tras choque, medible con impulse response por tamaño relativo/volatilidad y reloj de eventos/tiempo. Un estudio de equity china reporta recuperación de algunas variables dentro de hasta 20 updates en su muestra, no reloj universal CME. [“Limit-order book resiliency after effective market orders”](https://arxiv.org/abs/1602.00731). EdgeLab debe medir curvas por sesión/hora.

## B3. Hawkes/queue-reactive, toxicidad

Hawkes: `λ_i(t)=μ_i+Σ_j∫φ_ij(t−s)dN_j(s)`, modela clustering de trades/add/cancel. Queue-reactive condiciona intensidades al estado de cola. Huang, Lehalle & Rosenbaum, JASA 110(509), DOI 10.1080/01621459.2014.982278, [arXiv](https://arxiv.org/abs/1312.0563). Sirve descripción, forecast de dinámica, fill/riesgo y simulación; exige timestamps/eventos razonables y goodness-of-fit. Con wall-clock NT, ajustar resolución acorde y reportar incertidumbre de empates.

VPIN/BVC depende de buckets y etiquetas aproximadas, puede ser proxy de volatilidad/intensidad. Preferir realized spread y markout directo para fills. Convención de coste positivo: trade sign `s=+1` buy/`−1` sell; execution P; mid inicial m0; a horizon h, markout del liquidity provider `−s·(m_h−P)`. Separar fees, spread y markout.

## B4. Spoof, iceberg, absorción, walls/vacuums

Spoofing CFTC requiere intención de cancelar antes de ejecución; size p95, vida <5 s y baja ejecución no prueba intención. [CFTC enforcement metals futures (2019)](https://www.cftc.gov/PressRoom/PressReleases/7946-19). En MBP, describir “cambio/cancelación/replenishment inusual”, no “spoof detectado”. Iceberg nativo CME puede renovar display manteniendo OrderID; MBP solo ve consumos/replenishments agregados, confundibles con nuevas órdenes. Zotikov & Rej, *CME iceberg order detection and prediction*, *Quantitative Finance* 21(11), DOI 10.1080/14697688.2020.1813904, usan profundidad completa; detección no prueba edge. [Publisher](https://www.tandfonline.com/doi/full/10.1080/14697688.2020.1813904).

“Absorption”, “wall”, “vacuum”, “trapped trader” necesitan definición contable, no intención. Medir agresión vs desplazamiento/depth y lifecycle. Visual que oculta zonas mitigadas tiene supervivorship bias: conservar censo as-of. Historial EdgeLab: BigTrap2 refutado como soporte/imán; HP-008 refutado incondicionalmente; HFTZones sin potencia en 2/3 terciles; HP-007 fenómeno sin edge; aVolClusterPOI sin nulo propio. No presentarlos como novedades ni reabrir mediante subgrupo post hoc.

## B5. Estacionalidad/relaciones

Separar open, maintenance, settlement/close, macro releases, FOMC, roll/expiry, front y segundo contrato. Controlar hora, spread, volatilidad, profundidad y roll. Lead-lag ES/NQ/YM, GC/6E o calendar spreads son hipótesis; feed wall-clock sin exchange timestamps vuelve sub-second lead-lag frágil. Primero medir sincronía y estabilidad; luego preguntar si el activo líder retrasado por el peor caso observable añade valor neto. Costos/multiplicidad separados por instrumento.

# 4. C. Catálogo de modelos y recetas

| Prioridad | Modelo/representación | Target/horizon | Dato/cómputo | Aplicabilidad |
|---|---|---|---|---|
| 1 | Ridge/logistic en OFI, QI, microprice, spread/depth, trades-only; niveles top-10, features tick-normalized | Mid/markout 100ms, 500ms, 1s, 5s, 30s como grilla de investigación; luego delay real | CPU; debug con datos actuales, no confirmación temporal | **Alta como baseline**, edge no probado. |
| 2 | Boosting LightGBM/XGBoost en las mismas features/lag | Classification, magnitude, volatility, markout | CPU viable; cada trial cuenta | **Media**, solo si mejora el baseline temporal neto. |
| 3 | Cox/hazard, Markov/HMM, Hawkes/queue-reactive | Tiempo a next event/refill/depletion; intensidades/estados | CPU; pocos parámetros y goodness-of-fit | **Media** descriptiva/fill, no alpha asumido. |
| 4 | CNN/LSTM DeepLOB sobre tensor de 10 niveles y ventana | Mid-change/futuro trend, más label neta | GPU agiliza; decenas de sesiones no sostienen generalización | **Baja inicial**. DeepLOB original cash equities/LSE. |
| 5 | Transformers TransLOB/HLOB/TLOB | Tensores top-N con codificación espacial/temporal | GPU, costo y multiplicidad altos | **Baja**; papers mayormente acciones, prediction no net P&L. |
| 6 | Mamba/SSM y otros | Secuencia eventos/book | Evidence net CME en estas condiciones **[NO VERIFICADO]** | Exploratorio después de baselines. |
| 7 | Self-supervised/contrastive y transfer universal | Pretrain sin labels, finetune | Requiere datos/licencia parecidos y prueba downstream | Exploratorio; universalidad entre acciones no implica futures. |
| 8 | Generativos ABIDES/GAN/diffusion | Stress/synthetic book/simulator | Alta complejidad; validar realismo causal/impacto | No evidencia de trading; no usar datos sintéticos como holdout. |

DeepLOB: Zhang, Zohren & Roberts (2019), IEEE TSP 67, DOI 10.1109/TSP.2019.2907260, [arXiv](https://arxiv.org/abs/1808.03668). TransLOB [arXiv:2003.00130](https://arxiv.org/abs/2003.00130); HLOB [arXiv:2405.18938](https://arxiv.org/abs/2405.18938); TLOB [arXiv:2502.15757](https://arxiv.org/abs/2502.15757), preprint. Sirignano & Cont, *Universal Features of Price Formation…*, Quantitative Finance (2019), DOI 10.1080/14697688.2019.1622295, [arXiv](https://arxiv.org/abs/1803.06917): equities, not proof cross-CME.

FI-2010 es 10 días, 5 Nordic stocks, normalized features/labels; debugging only. Ntakaris et al. (2018), *Journal of Forecasting*, DOI 10.1002/for.2543, [dataset](https://etsin.fairdata.fi/dataset/73eb48d7-4dbc-4a10-a52a-da745b47a649). Verificar preprocessing exacto; no afirmar fuga específica sin inspección. LOBCAST/Prata et al. benchmarkea 15 DL models; reporta sobreajuste/generalización débil desde FI-2010 a stocks no vistos. *Artificial Intelligence Review* (2024), DOI 10.1007/s10462-024-10715-4, [paper](https://link.springer.com/article/10.1007/s10462-024-10715-4), [repo](https://github.com/matteoprata/LOBCAST). LOB-Bench (Nagy et al., ICML 2025, PMLR 267, 45437–45460) mide realismo estadístico/impacto, no profitability: [paper](https://proceedings.mlr.press/v267/nagy25a.html). ABIDES (Byrd et al. 2020, ACM ICAIF; DOI 10.1145/3384441.3395986) es multi-agent simulator, no calibrated CME retail venue: [arXiv](https://arxiv.org/abs/1904.12066).

## C1. Entrenamiento/evaluación paso a paso

1. Preregistrar mecanismo, falsador, instrumento/contrato/sesiones, universo event/state (creación, aproximación, primer/n-ésimo toque, invalidación, expiración, confluencia y estado continuo), features, horizons, latency, costs, nulo, búsqueda/seed, N efectivo, MDE y regla stop.
2. Solo sesiones pre-holdout y orden cronológico. Train temprano, validation posterior, bloque development final; no random events. Purge ventanas de label/holding solapadas y embargo en fronteras. Con ~30 GC sesiones, no fingir muchos folds independientes.
3. Fit normalization solo en train/pasado; price en ticks relativo a mid, sizes transformados con parámetros train; eliminar global future z-score. Hash raw/derivados y versionar calendario.
4. Baselines: no-trade/zero; mid/trades-only; tick/trade features; L1; L2 manual. Reportar Brier/log-loss/MAE/accuracy como secundarios; principal: markout, magnitud, calibración y P&L económico.
5. Labels desde el momento realista de llegada, no un timestamp anterior al cómputo. Targets direccional + no-direccional (vol/magnitud) + distribución completa. Cost-label long solo si retorno ejecutable esperado excede fees+spread+slippage+incertidumbre; thresholds elegidos solo en dev.
6. Ablaciones obligatorias: trades-only, no book; depth barajado dentro de bloques de sesión preservando autocorrelation/hora; L2 retrasado 50/100/250/500ms y 1/2s como escenarios; clasificadores alternativos de agresor; top-of-book vs depth. Stress-grid no es afirmación de latency real.
7. Logistic/ridge primero; boosting con búsqueda pequeña; early stopping solo validation; calibración en bloque dedicado; varias seeds reportadas, no escoger semilla ganadora. Contar features, horizons, thresholds, seeds, subgrupos, arquitecturas y ensayos visuales.
8. CNN pequeña solo si baselines muestran señal a delays plausibles; mismos splits/labels; medir inferencia CPU/host, memory/GPU. No escalar Transformers si no agrega net expectancy bajo igual búsqueda.
9. Regla operacional completa antes de P&L: signal/threshold, entry/order, cancel, exit, sizing/cap, cooldown, kill switch, feed stale. Reportar bruto, fee, spread, slippage, fill uncertainty; expectancy/sesión, fill ratio, missed fills, adverse excursion, drawdown/tail, exposure, capacity.
10. Repetir en sesiones futuras no vistas y/o vendor history. Holdout solo tras congelar un candidato y protocolo.

**Primer plan y kill tests:** (1) QA/lifecycle OFI target-free; matar si depende de timestamps ambiguos o libro malo. (2) Logistic trades-only vs trades+L2; matar si L2 no añade markout tras latency. (3) Boosting; matar si no replica por sesiones tras corrección por búsqueda. (4) Hawkes/queue-reactive para estados/fill, no signal; matar si intensidades no calibran OOS. (5) CNN pequeña si queda muestra/sesiones; matar si no aporta P&L neto sobre baseline/latency.

# 5. D. Ejecución, latencia y costos

## D1. Latencia

No se verificó cifra pública que represente NT8+este broker/ISP+orden CME. Un estudio CFTC sobre E-mini mide tiempo entre ciertos eventos y nuevas órdenes, no el RTT actual de un trader minorista: [Fishe, Haynes & Onur, “New Order Latency in the E-Mini Futures Market”](https://www.cftc.gov/sites/default/files/2019-05/FisheHaynesOnur_Determinants%20of%20New%20Order%20Latency_ada.pdf). Rango absoluto: **[NO VERIFICADO]**.

Instrumentar monotonic clock en market data receive, feature complete, decision, send, ack, partial/full fill, cancel y fill update; registrar jitter, disconnect, p50/p90/p99 por sesión y tipo de orden. Exchange arrival/one-way no es observable salvo timestamp exchange confiable. Stress test 50,100,250,500ms,1,2s solo como grilla; reemplazar por medición propia. Diferenciar signal→ack, order→fill, network vs compute.

## D2. Fills límite con MBP

- **Marketable:** en arrival book caminar levels con qty disponible, partial fill, fees y movimiento durante llegada/ack. Si book stale/gap, no conceder fill favorable. Historical replay no cambia por nuestra ejecución; limitar capacity y confesar impacto endógeno no modelado.
- **Conservador passive:** toda qty observada a precio al llegar está delante; solo trades compatibles reducen cola; cancelaciones no mejoran prioridad; touch no llena; fill al trade-through/volumen que excede cola + nuestra qty; excluir empates; charge adverse markout tras fill.
- **Intermedio:** probabilidad de cancelación delante calibrada con MBO/propios fills, sin optimizar para P&L; validate en segmento independiente de fills.
- **Optimista techo:** fracción de cancel delante y fills en touch; solo límite superior. Nunca base única de despliegue.

Estimar fill probability/survival por horizon, depth-ahead, orderflow, volatility, latency, size y tipo; calibration y markouts de filled vs unfilled. Passive fills pueden concentrarse cuando el precio va en contra.

`hftbacktest` soporta MBP, modelos de cola/latencia; advierte que replay no modifica el mercado y algunas simulaciones de partial/taking fills son irreales: [fills](https://hftbacktest.readthedocs.io/en/latest/order_fill.html), [latency](https://hftbacktest.readthedocs.io/en/latest/latency_models.html). NautilusTrader soporta L2/L3, fill model configurable y declara que datos históricos no revelan cómo nuestra orden cambia el book: [data/venues](https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues), [fills](https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models). Ambos son herramientas, no truth.

## D3. Coste por instrumento/hora/size

1. Congelar fee schedule broker+exchange/clearing/regulatory por cuenta, fecha, mini/micro, entrada/salida.
2. Features L2: quoted/effective spread, depth, volatility, hora, contrato/roll. No sumar series heterogéneas.
3. Guardar fills propios: signal, send/ack/fill/cancel, side/order type/size, bid/ask/mid at decision/arrival/fill, markouts multi-horizon, partials.
4. Slippage: signed(fill−mid at decision/arrival), ticks, implementation shortfall; reportar percentiles/CI agrupada por sesión y estratos. Sin fill log real, estimación = escenario.
5. Walk book para N=1..N da impacto mecánico visible; no respuesta de mercado. Comparar con execution logs y stress multipliers.
6. Tabla por GC/ES/6E, hora, spread/vol, side/size/order type: fee, spread paid/captured, slippage, fill probability, missed opportunity, adverse markout, CI/p95/p99.
7. Break-even market vs limit: `E[net]=P(fill)·(gross edge−fee−adverse markout−impact)−opportunity cost(no fill)`. Publicar sensibilidad a latency y queue model. No trasladar costos entre instrumentos.

## D4. Prop firm y riesgo

Reglas varían por producto/fecha: trailing drawdown (realized/unrealized/high-water/lock), daily loss, max contracts/scaling, consistency/payout, overnight/news, automation/feed and disconnect. Modelar threshold contra equity path intradía si aplica; no solo EOD. Verificar acuerdo oficial vigente del proveedor; reglas cambian. [Apex official page, ejemplo no generalizable](https://apextraderfunding.com/). Sin aconsejar qué firma/cuenta elegir. Paper/live risk: fixed 1 contract first where approved, max exposure, daily kill, stale feed kill, disconnect cancel, reconciliation, roll/limit safeguards; no deployment sin owner/approval.

# 6. E. Estadística de alta frecuencia

## E1. N efectivo, MDE y dependencia

Millones de updates/sesión no son millones independientes. Reportar raw N, N sesiones, N efectivo (autocorrelation/cluster) y overlap labels. Bootstrap por sesión si hay suficientes sesiones; stationary/circular/block bootstrap para dependencia, sensibilidad a longitud de bloque. Para diferencia media por sesión, MDE esquemático: `(z_(1−α*)+z_(1−β))·SE_cluster`; preferir simulación/bootstrap preregistrado que preserve clustering, autocorrelation y tails. Publicar MDE también para nulos. Si MDE > break-even edge, inconcluso; no “prueba que no existe edge”.

## E2. Multiplicidad

Contar cada feature, horizon, threshold, contract, subgroup, seed, architecture, filtro, dashboard/revisión visual y resultado fallido. White Reality Check y Hansen SPA ajustan comparación con muchas alternativas; Romano–Wolf step-down; DSR por selection bias/no-normalidad; PBO/CSCV para overfit del proceso. Complementarios, no sellos automáticos. Harvey–Liu–Zhu sugieren umbrales elevados (>3 en contextos de factores cross-sectional), no convertirlo en ley de intradía.

Fuentes: White (2000), *Econometrica* 68(5), DOI 10.1111/1468-0262.00152; Hansen (2005), *JBES* 23(4), DOI 10.1198/073500105000000063; Romano & Wolf (2005), *Econometrica* 73(4), DOI 10.1111/j.1468-0262.2005.00615.x; Harvey, Liu & Zhu (2016), *RFS* 29(1), DOI 10.1093/rfs/hhv059; Bailey & López de Prado (2014), *JPM* 40(5), DOI 10.2139/ssrn.2460551; Bailey et al. (2017), *Journal of Computational Finance* 20(4), DOI 10.21314/JCF.2016.322.

## E3. Nulos, leakage, splits

Usar block/circular shift dentro de sesión que preserve autocorrelation/hora para tests de información incremental; shuffle individual de filas destruye dependencia e infla significancia. Testear leakage con labels/features desplazados, feature sentinel futuro, timestamps empatados, bootstrap resets y retraso causal. Labels empiezan tras momento observable + latency, no antes de cómputo. Purge máximo label/holding horizon; embargo de overlap/positions. `PrimaryCI` por sesión con lower>0 es útil, pero el resultado principal es net/session con incertidumbre de fills/costes.

Pre-holdout: train temprano, validación posterior, development test bloqueado; series completas por sesión; no random split. Sealed H2 2026 no se usa ni para calibrar costes. Futuras sesiones 2027 y vendor history son replicación; otro instrumento también es búsqueda adicional salvo preregistro.

# 7. F. Estado de la evidencia y qué sobrevive a la latencia minorista

En la investigación consultada no se verificó evidencia genérica de P&L **neto** de L2 CME futures para operador minorista con este feed/costes/latencia. La literatura muestra estructura predictiva en mercados y horizons selectos, no permiso de transferibilidad. Medir curva EdgeLab `markout(L)` desde signal observable a arrival delay L y después coste/fill; horizonte explotable es aquel que conserva net edge bajo delays/fees/fills pesimistas, no el de mayor score.

Hipótesis posible: usar L2 como **filtro/contexto** de una regla a minutos, incluso si no es directional alpha standalone. Comparar incremental value vs trades/price-only y contabilizar falso veto/coste de oportunidad; preregistro separado. Cursos/visualizadores Bookmap son heurísticas, no prueba. No reportar cifras de crowding/decay como universal sin series CME.

# 8. G. Herramientas, datos y visualización para investigar

DuckDB/Polars/PyArrow/NumPy/Pandas bastan para QA, logistic/linear, estadística y features; parquet por sesión/contrato, precios integer ticks, schema y hashes versionados. PC/servidor CPU alcanzan para baseline, event counts y boosting modesto; no hace falta GPU para limpieza.

Kaggle anunció retiro de P100 el 15-sep-2026 y T4x2 como opción en Notebook editor: [announcement](https://www.kaggle.com/discussions/product-announcements/735239). Guía genérica aún cita P100 y 30h/semana, parece obsoleta en lo de GPU: [generic docs](https://www.kaggle.com/docs/efficient-gpu-usage). **Quota individual/T4x2 disponible actual [NO VERIFICADO]**: consultar Settings/usage del notebook account. CNN pequeña probablemente viable en T4x2, pero hacer pilot con subset; esta investigación no certifica Kaggle Worker (contexto EdgeLab dice source/access bloqueados).

FI-2010 para debugging; LOBSTER equity; Tardis crypto: pretraining transfer solo con licencia y evaluación downstream. Visualizador: preservar universo completo/as-of, incluir bootstrap/gaps/roll, zona no mitigada y mitigada, no look-ahead, sincronización, hash de fuentes y motivo de exclusión. Blinding de outcomes en auditoría target-free. Una captura no es una muestra estadística.

# 9. Hoja de ruta y criterios de parada

| Fase | Tarea/inputs | Entregable | Stop/avance |
|---|---|---|---|
| 0 Custodia | Freeze raw hashes/schema/calendar/exclusions; guardar Replay antes de 90 días | Manifest + QA por sesión | Falta L2, overlap irresuelto, parser/invariante roto → cuarentena. |
| 1 Target-free | Bootstrap, best vs L1, gaps, spread/depth/lifecycle por sesión | Reporte geometry/event census | Semántica/timestamps inestables → no return test. Raras con N bajo → no claims. |
| 2 Preregistro | 1–2 hipótesis por instrumento; mecanismo, falsador, universe, MDE/N, latency, nulo, costs, search ledger | Frozen protocol | No query de retornos antes del gate. |
| 3 Incremental info | Logistic trades-only vs L2, latency grid, nulos y ablaciones | Curvas markout+distribution+CI session | Kill si L2 no aporta sobre baseline tras delay o depende de labels ambiguos. |
| 4 Gross/fills | Entry/exit/order logic; 2–3 MBP queue models | Bandas fill/P&L | Kill si positivo solo con touch/optimistic queue. |
| 5 Net | Fees reales, latency/fills medidos, por instrumento | Net report, risk/tails/capacity | Kill si lower CI no>0, net no supera break-even/MDE, o muere p90/p99. |
| 6 Robustez | SPA/Reality Check/DSR/PBO según diseño; model escalation limitada | Trial ledger/frozen candidate | No promote si falla multiplicidad, una sesión/roll domina o modelo no agrega net value. |
| 7 Replicación | 2027 fresh sessions o licensed history; holdout solo por protocolo | Independent dossier | Sin réplica/ops/risk approval, no deploy. |

**Ya:** QA, target-free, features, baseline descriptivo en sesiones disponibles; medir fees/latency y paper fills permitidos. 6E y ES quarantine no soportan broad claims. **Requiere tiempo/datos:** meses nuevos desde 2027, propios fills, quote/licence para MBO si cola es esencial, vendor history multi-year si reduce el uncertainty relevante. No abrir holdout mientras tanto.

# 10. Lista de “no hacer”

1. No llamar MBO/cola a MBP-10 ni spoof a heurística de tamaño/duración.
2. No tratar `source_row` o 100ns como matching-engine sequence/time.
3. No validar aggressor por visual sanity; conservar UNKNOWN y sensibilidad.
4. No “fill at touch”, fill completo a best quote, cancel gratis ni replay que supuestamente predice reacción de mercado.
5. No empezar por DeepLOB/Transformer/Mamba con poca historia ni elegir horizon mirando retornos.
6. No random event split, normalización global, labels solapadas sin purge, señal cero-latency.
7. No tocar sellado julio-diciembre para costes/diseño/selección/rescate de estrategia.
8. No trasladar costes/multiplicity entre instrumentos/familias; no rescatar subgrupos post hoc.
9. No confundir accuracy/AUC, heatmap, synthetic book o folklore de practitioner con net edge.
10. No tratar VPIN/BVC como ground truth; medir markout/realized spread.
11. No inferir lead-lag subsecond sin sincronía nativa.
12. No comprar MBO/publicar datos antes de quote/licence review; no asumir derechos de derivados/redistribución.
13. No mergear PR #56 mientras CI falla; no declarar Kaggle Worker listo sin source/access verificado.
14. No desplegar capital por backtest, paper model o score positivo; este manual no es consejo financiero.

# 11. Preguntas abiertas

1. Latencia signal→ack/fill, jitter y feed lags por broker/ISP/order: logs instrumentados monotonic + clocks confiables.
2. % updates NT8 empatados, perdidos, consolidados/reordered: feed paralelo con secuencia native.
3. Precisión de aggressor por contrato/hora: ground truth exchange flags/MBO y trade IDs.
4. Fee/costo/impacto real para 1..N GC/ES/6E: schedules y fills propios.
5. Calibration de passive fills/adverse selection MBP: suficientes propios fills o MBO independiente.
6. Qué eventos sobreviven roll/sesión y tienen N efectivo: más meses y census congelado.
7. ¿Aporta L2 sobre tick data del usuario a >p90 measured latency net costs?: matched sessions, preregistered incremental test.
8. Vendor MBO más barato con derechos deseados: quotes idénticos Databento/CME DataMine/alternativos y muestra/licencia.
9. ¿Paper CME L2 documenta net profitability minorista after retail costs? No verificado aquí; buscar fuentes originales específicas.
10. Cuota Kaggle/account/Worker current: UI + manifest/source oficial; no asumidos en este reporte.
11. Reglas firm permitidas y vigentes: contrato oficial concreto.
12. Potencia de cada falsador: cluster-bootstrap MDE frente a break-even medido; no existe N universal.

# 12. Bibliografía y fuentes primarias

## Feed, data, execution
- CME Group, “Market by Order (MBO).” https://www.cmegroup.com/articles/faqs/market-by-order-mbo.html
- CME Group Client Systems Wiki, “MDP 3.0 Market Data” y “Event Based Market Data Messaging.” https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457219613/CME+MDP+3.0+Market+Data ; https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457325420/MDP+3.0+-+Event+Based+Market+Data+Messaging
- NinjaTrader, “Market Replay (Playback Connection).” https://support.ninjatrader.com/s/article/How-Do-I-Connect-to-NinjaTrader-Desktop-s-Playback-Feature?language=en_US
- Databento: pricing / MBP-10 / MBO / GLBX.MDP3. https://databento.com/pricing ; https://databento.com/docs/schemas-and-data-formats/mbp-10 ; https://databento.com/docs/schemas-and-data-formats/mbo ; https://databento.com/docs/venues-and-datasets/glbx-mdp3
- CME DataMine: https://www.cmegroup.com/datamine.html ; https://www.cmegroup.com/market-data/real-time-and-historical-data.html
- hftbacktest: fills / latency. https://hftbacktest.readthedocs.io/en/latest/order_fill.html ; https://hftbacktest.readthedocs.io/en/latest/latency_models.html
- NautilusTrader: data/venues / fill models. https://nautilustrader.io/docs/latest/concepts/backtesting/data-and-venues ; https://nautilustrader.io/docs/latest/concepts/backtesting/fill-models
- Kaggle, P100 retirement 15 Sep 2026; generic GPU guide. https://www.kaggle.com/discussions/product-announcements/735239 ; https://www.kaggle.com/docs/efficient-gpu-usage

## Market microstructure / models
- Cont, Rama, Arseniy Kukanov & Sasha Stoikov (2014), “The Price Impact of Order Book Events,” *Journal of Financial Econometrics* 12(1), 47–88. DOI 10.1093/jjfinec/nbt003. https://academic.oup.com/jfec/article/12/1/47/816163
- Gould, Martin D. & Julius Bonart (2016), “Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book,” *Market Microstructure and Liquidity* 2(2), DOI 10.1142/S2382626616500064. https://arxiv.org/abs/1512.03492
- Stoikov, Sasha (2018), “The micro-price: a high-frequency estimator of future prices,” *Quantitative Finance* 18(12), DOI 10.1080/14697688.2018.1489139. https://www.tandfonline.com/doi/full/10.1080/14697688.2018.1489139
- Huang, Weibing, Charles-Albert Lehalle & Mathieu Rosenbaum (2015), “Simulating and Analyzing Order Book Data: The Queue-Reactive Model,” JASA 110(509), DOI 10.1080/01621459.2014.982278. https://arxiv.org/abs/1312.0563
- Andersen, Torben G. & Oleg Bondarenko (2014), “Assessing Measures of Order Flow Toxicity via Perfect Trade Classification.” https://pure.au.dk/ws/files/68359010/rp13_43.pdf
- Chakrabarty et al., “Bulk Classification of Trading Activity.” https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2182819
- Silverman (2026), “Trade Classification Error Is Not Where You Would Expect,” SSRN preprint. https://papers.ssrn.com/sol3/Delivery.cfm/7435320.pdf?abstractid=7435320&mirid=1
- Fishe, Raymond P. H., Richard Haynes & Esen Onur, “New Order Latency in the E-Mini Futures Market.” https://www.cftc.gov/sites/default/files/2019-05/FisheHaynesOnur_Determinants%20of%20New%20Order%20Latency_ada.pdf
- Zotikov & Rej (2021), “CME iceberg order detection and prediction,” *Quantitative Finance* 21(11), DOI 10.1080/14697688.2020.1813904. https://www.tandfonline.com/doi/full/10.1080/14697688.2020.1813904
- CFTC (2019), Merrill Lynch precious-metals futures spoofing order. https://www.cftc.gov/PressRoom/PressReleases/7946-19
- Ntakaris et al. (2018), “Benchmark Dataset for Mid-Price Forecasting…,” *Journal of Forecasting*, DOI 10.1002/for.2543. https://onlinelibrary.wiley.com/doi/10.1002/for.2543 ; dataset https://etsin.fairdata.fi/dataset/73eb48d7-4dbc-4a10-a52a-da745b47a649
- Zhang, Zihao, Stefan Zohren & Stephen Roberts (2019), “DeepLOB…,” IEEE TSP 67, DOI 10.1109/TSP.2019.2907260. https://arxiv.org/abs/1808.03668
- Wallbridge (2020), TransLOB, arXiv:2003.00130. https://arxiv.org/abs/2003.00130
- Sirignano & Cont (2019), “Universal Features of Price Formation…,” *Quantitative Finance*, DOI 10.1080/14697688.2019.1622295. https://arxiv.org/abs/1803.06917
- Prata et al. (2024), “LOB-Based Deep Learning Models for Stock Price Trend Prediction: A Benchmark Study,” *Artificial Intelligence Review*, DOI 10.1007/s10462-024-10715-4. https://link.springer.com/article/10.1007/s10462-024-10715-4 ; https://github.com/matteoprata/LOBCAST
- Briola et al. (2025), “Deep limit order book forecasting: a microstructural guide,” DOI 10.1080/14697688.2025.2522911. https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/
- Briola et al., HLOB, arXiv:2405.18938. https://arxiv.org/abs/2405.18938
- Berti et al., TLOB, arXiv:2502.15757. https://arxiv.org/abs/2502.15757
- Byrd et al. (2020), “ABIDES: Towards High-Fidelity Market Simulation for AI Research,” ACM ICAIF, DOI 10.1145/3384441.3395986. https://arxiv.org/abs/1904.12066
- Nagy et al. (2025), “LOB-Bench: Benchmarking Generative AI for Finance,” ICML, PMLR 267. https://proceedings.mlr.press/v267/nagy25a.html

## Multiple testing
- White (2000), “A Reality Check for Data Snooping,” *Econometrica* 68(5), DOI 10.1111/1468-0262.00152.
- Hansen (2005), “A Test for Superior Predictive Ability,” *JBES* 23(4), DOI 10.1198/073500105000000063.
- Romano & Wolf (2005), “Stepwise Multiple Testing as Formalized Data Snooping,” *Econometrica* 73(4), DOI 10.1111/j.1468-0262.2005.00615.x.
- Harvey, Liu & Zhu (2016), “… and the Cross-Section of Expected Returns,” *RFS* 29(1), DOI 10.1093/rfs/hhv059. https://academic.oup.com/rfs/article/29/1/5/1843824
- Bailey & López de Prado (2014), “The Deflated Sharpe Ratio,” *Journal of Portfolio Management* 40(5), DOI 10.2139/ssrn.2460551. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado & Zhu (2017), “The Probability of Backtest Overfitting,” *Journal of Computational Finance* 20(4), DOI 10.21314/JCF.2016.322

## Límites explícitos

No se verificaron cotizaciones vigentes de todos los vendors, licencia del usuario, cuota individual Kaggle, RTT de esta instalación, current Worker access ni evidencia neta específica de EdgeLab en CME. Inventario de datos/refutaciones internas son contexto aportado, no re-mediciones de este documento. Sources de equities y preprints no prueban edge en CME. Toda cifra/afirmación con **[NO VERIFICADO]** exige verificación previa a operación.
