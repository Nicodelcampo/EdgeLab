# HFTZones ES — capa 2 de research: microestructura, regímenes y plan de features

**Estado:** `RESEARCH_REGISTERED_NOT_EXECUTED`  
**Fecha:** 2026-08-20  
**Rama:** `foundation/f0b-compatibility-probe`  
**HEAD remoto de partida:** `6a15255709bf6020406397edcc57d11415213b1a`  
**Registro legible por máquina:** `docs/research/hft_es_context_feature_registry_2026-08-20.json`

> Pedido explícito de Nico: profundizar una capa más la investigación y dejar
> registrado todo el razonamiento para que no se pierda.

---

## 0. Procedencia y límites de este documento

Este documento es **research y diseño**, no una medición nueva.

- No se ejecutó ningún script del repo.
- No se observó ningún outcome posterior a las zonas.
- No se calculó retorno, P&L, MAE/MFE ni ejecutabilidad.
- No se tocó el holdout `2026-07-01 → 2026-12-31`.
- No se modificó el detector `HFTZonesESPureV2Flat` ni sus parámetros.
- No se declara ninguna feature como edge.
- El resultado R1 v2 informado localmente —62 sesiones de universo, 59 elegibles,
  `18/59 = 30,51 %`, p mediana `0,1796`, B=400— sigue siendo
  **`USER_REPORTED_LOCAL_UNCOMMITTED`** al momento de este registro. No confundir este
  memo con el sellado de R1.

Este memo complementa, no sustituye,
`docs/research/HFT_ZONAS_ES_MEDIDO_Y_NO_MEDIDO.md` y
`docs/audits/HFT_CTX_HANDOFF_AUDIT_2026-08-20.md`.

---

## 1. Dictamen que queda registrado

| Posible uso de HFTZones ES Flat | Esperanza actual |
|---|---|
| Soporte/resistencia o costo de cruce universal | **Baja** |
| Señal autónoma operable | **Baja** |
| Detector de un estado/evento de microestructura | **Moderada, no demostrada** |
| Feature dentro de un modelo condicionado por régimen | **Moderada, no demostrada** |
| Estrategia lista para live | **Muy baja** |

### Lectura corta

El control casi-zona es un prior negativo serio: en el agregado, las zonas no cuestan
más de cruzar que casi-zonas comparables. Por lo tanto, **no hay base para vender la
zona cruda como edge**.

La esperanza que queda es más acotada: el mismo nombre parece agrupar objetos distintos
según fase, liquidez y estado del episodio. Asia/Europa/premarket producen zonas más
anchas y con otra composición que RTH; además, Fano `7,78` y `81,1 %` de proximidad
muestran que gran parte de las filas son ráfagas relacionadas, no eventos IID. Un nulo
agregado no descarta a priori un efecto condicional escrito **antes** de mirar outcomes.

La nueva capa de literatura fortalece la plausibilidad de esa heterogeneidad, **no la
existencia de un edge**.

---

## 2. Qué agregó la segunda capa de research

### 2.1 Evidencia directa sobre ES: el precio del flujo cambia durante el día

Takahashi estudia E-mini S&P 500 a frecuencia de un segundo, estimando cada intervalo
de 15 minutos. Encuentra variación intradiaria marcada, asociación con profundidad,
actividad y spreads, y un cambio estructural alrededor de anuncios macro: sube el
impacto de precio, baja la respuesta del flujo, sube la volatilidad de retornos y se
retira liquidez. Los impulsos se disipan casi por completo dentro de un segundo.

**Implicación EdgeLab:** fase, liquidez normalizada por horario y noticias son filtros
estructurales defendibles. También implica que una hipótesis de microestructura debe
usar horizontes cortos. Por P-28 —`sequence` no es secuencia del exchange y hay hasta
182 ticks en el mismo milisegundo— no se autoriza inferencia sub-segundo con estos datos.

Fuente: Takahashi, *Returns and Order Flow Imbalances: Intraday Dynamics and
Macroeconomic News Effects*  
<https://arxiv.org/html/2508.06788v4>

Andersen, Bondarenko, Kyle y Obizhaeva documentan patrones intradiarios sistemáticos de
volumen, volatilidad, tamaño y liquidez en ES con datos BBO de CME.

**Implicación EdgeLab:** toda tasa, velocidad, volumen y volatilidad debe expresarse
contra su distribución para ese horario/fase; un umbral global mezcla estados que no
son comparables.

Fuente: *Intraday Trading Invariance in the E-Mini S&P 500 Futures Market*  
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2693810>

### 2.2 Resiliencia: reversión y continuación son dos mecanismos distintos

Fishe, Haynes y Onur estudian directamente la reposición de liquidez en E-mini futures.
Los participantes que usan órdenes límite tienden a reingresar rápido; quienes demandan
inmediatez con market orders tardan más. Las demoras dependen del tipo de participante,
del estado —por ejemplo, si la orden mejora precio— y de covariables como el volumen
durante el gap. En mercados activos ciertos proveedores retrasan liquidez para evitar
flujo informado.

**Implicación EdgeLab:** un sweep no fija el signo. Puede ser agotamiento con reposición
y reversión, o continuación de una metaorden/retirada de liquidez. La pregunta más
mecánica es **resiliencia/impacto**, no «la zona atrae».

Fuente: Fishe, Haynes y Onur, *Resiliency in the E-mini futures market*, Journal of
Futures Markets 42(1), 2022  
<https://onlinelibrary.wiley.com/doi/10.1002/fut.22259>

### 2.3 OFI es superior al volumen bruto, pero exige libro verdadero

Cont, Kukanov y Stoikov encuentran una relación aproximadamente lineal entre order-flow
imbalance y cambio de precio; la pendiente es inversamente proporcional a la profundidad.
La relación volumen-precio es más ruidosa y menos robusta. OFI incluye cambios en bid,
ask, órdenes límite y cancelaciones; no es sinónimo de volumen clasificado de trades.

**Implicación EdgeLab:** con BBO/L2 sincronizado, `spread`, `depth`, OFI, queue imbalance
y reposición serían las features de mayor contenido mecánico. Con trades solos se
permiten proxies, claramente etiquetados, pero no se los llama OFI ni verdad de libro.

Fuente: Cont, Kukanov y Stoikov, *The Price Impact of Order Book Events*  
<http://arxiv.org/abs/1011.6402>

Queue imbalance predice el próximo movimiento de mid-price en una muestra de acciones,
con mayor utilidad en activos de tick grande. Es evidencia externa general, **no prueba
directa sobre ES**, y requiere colas bid/ask reales.

Fuente: Gould y Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor*  
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2702117>

### 2.4 Proxies trade-only: útiles como aproximación, no como sustituto del libro

Un proxy tipo Amihud (`|retorno| / volumen`) puede representar impacto por unidad de
volumen, pero es grueso: volumen alto puede coexistir con iliquidez y el resultado
mezcla información, volatilidad y liquidez. Numerador y denominador deben cubrir la
misma ventana y normalizarse por horario.

**Implicación EdgeLab:** se admite como `trade_only_illiquidity_proxy`, nunca como
profundidad observada. Debe convivir con sus componentes por separado para verificar
que no sea sólo volatilidad disfrazada.

Fuente original: Amihud, *Illiquidity and stock returns*  
<https://www.cis.upenn.edu/~mkearns/finread/amihud.pdf>

### 2.5 El clustering justifica episodios, no obliga a ajustar un Hawkes ahora

La literatura modela llegadas de compras y ventas como procesos autoexcitados: las
operaciones llegan en ráfagas y las del mismo signo se agrupan. Una explicación natural
es el fraccionamiento de metaórdenes. El precio racional incorpora la persistencia
esperada del flujo, por lo que contar cada impresión o cada zona de una ráfaga como
observación independiente es incorrecto.

**Implicación EdgeLab:** primero definir episodios y publicar features causales como
`es_primera`, `n_previas` y `tiempo_desde_previa`. No hace falta ajustar un Hawkes
complejo antes de saber si una descripción episódica simple agrega información.

Fuente: Hewlett, *Clustering of order arrivals, price impact and trade path
optimisation*  
<https://users.iems.northwestern.edu/~armbruster/2007msande444/Hewlett2006%20price%20impact.pdf>

### 2.6 VPIN queda explícitamente rechazado

Andersen y Bondarenko, usando ticks de futuros S&P 500, muestran que VPIN está por
construcción correlacionado con innovaciones de volumen y volatilidad; al controlarlas
no encuentran poder incremental robusto. El comportamiento cambia materialmente con
la clasificación de trades y la bulk volume classification empeora precisamente en
períodos activos/volátiles.

**Decisión:** no implementar VPIN en esta línea.

Fuente: *Reflecting on the VPIN Dispute*  
<https://repec.econ.au.dk/repec/creates/rp/13/rp13_42.pdf>

### 2.7 La capa de contexto aumenta la multiplicidad

Harvey y Liu enfatizan que hay que registrar todo lo probado, incluidas interacciones;
20 variables no producen sólo 20 tests cuando se exploran combinaciones. Modificar un
modelo después de mirar un holdout convierte ese holdout en in-sample.

**Implicación EdgeLab:** una whitelist corta, feature registry versionado, contextos y
horizontes congelados, y holdout intacto. No torneo automático de indicadores.

Fuente: Harvey y Liu, *A Backtesting Protocol in the Era of Machine Learning*  
<https://people.duke.edu/~charvey/Research/Published_Papers/G138_A_backtesting_protocol.pdf>

---

## 3. Registro de decisiones de diseño

### D-HFT-CTX-01 — congelar el detector base

`HFTZonesESPureV2Flat` y el snapshot quedan congelados. Las nuevas variables se calculan
en una tabla offline, usando la creación de zona como tiempo `t0`. Si una combinación
sobrevive, se crea después una variante filtrada con otro nombre; no se sobreescribe
Flat.

### D-HFT-CTX-02 — no mezclar features con outcomes

Cada columna lleva una etiqueta de disponibilidad:

- `PRE`: conocida antes de `t0`;
- `AT_EVENT`: conocida al terminar la construcción causal de la zona;
- `POST`: requiere observaciones posteriores y es outcome, no feature.

No se admite una columna `POST` como filtro de régimen. Resiliencia posterior es un
outcome; sólo una medida de resiliencia histórica, computada sobre shocks previos, podría
ser feature.

### D-HFT-CTX-03 — whitelist inicial, no ensalada de indicadores

Las familias primarias son cinco:

1. fase de sesión;
2. actividad/volatilidad previas normalizadas por horario;
3. estado causal del episodio;
4. esfuerzo contra resultado dentro del barrido;
5. noticia macro programada.

`trend_score`, geometría y filtro fallado quedan como diagnósticos secundarios. L1/L2 se
difiere hasta tener datos y paridad de reloj adecuados.

### D-HFT-CTX-04 — noticias desde fuentes oficiales

Primera versión: flag binario y minutos hasta/desde anuncio, usando hora programada. No
se incorpora la sorpresa del dato todavía. Fuentes canónicas candidatas:

- BLS: <https://www.bls.gov/schedule/news_release/cpi.htm>
- Federal Reserve/FOMC: <https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm>
- New York Fed: <https://www.newyorkfed.org/research/calendars/nationalecon_cal>

### D-HFT-CTX-05 — no outcomes antes de R2 y R3

Orden obligatorio:

1. sellar R1;
2. R2: auditar matchability y el `18,3 %` sin control;
3. R3: congelar inferencia clusterizada y equivalencia;
4. construir atlas target-free con la whitelist;
5. seleccionar contextos sin outcomes;
6. pre-registrar dirección, horizonte y estimando;
7. recién entonces medir.

### D-HFT-CTX-06 — unidad de dependencia: sesión y episodio

Nunca se reporta un CI IID por zona. La sesión es la unidad mínima de resampleo. El
episodio se usa para no duplicar un mismo burst dentro de sesión.

### D-HFT-CTX-07 — datos actuales no soportan verdad de libro

P-28 sigue vigente: `sequence` es fila de origen, no secuencia del exchange. Las features
deben ser invariantes al orden dentro del mismo timestamp. No se autoriza:

- inferencia sub-milisegundo;
- queue position;
- cancelaciones;
- reposición de profundidad;
- OFI verdadero;
- agresor side como verdad sin auditoría.

### D-HFT-CTX-08 — prohibiciones explícitas

No agregar en esta fase:

- RSI/MACD/colecciones de medias;
- VPIN;
- GEX;
- flecha retroactiva de `AAAAAAbsorptionV3`;
- barrido masivo de parámetros;
- M1/M5 como sustituto del detector tick-native;
- HMM/regímenes aprendidos mirando toda la muestra;
- combinación con indicadores sin paridad y timestamp causal.

---

## 4. Feature registry humano

| ID | Feature/familia | Disponibilidad | Definición v0 | Normalización | Prioridad |
|---|---|---|---|---|---|
| F01 | `session_phase` | PRE | Asia / Europa / premarket / RTH-AM / RTH-PM / cierre, DST real | ninguna | primaria |
| F02 | `activity_regime` | PRE | tick rate, volume rate, mediana intertick, cambios de precio en 5 min previos | percentil del mismo bucket de 15 min, sólo referencia pasada | primaria |
| F03 | `volatility_regime` | PRE | RV, rango y path de precio en 5 min previos | percentil del mismo bucket horario | primaria |
| F04 | `episode_state` | PRE/AT_EVENT | primera zona, previas causales, tiempo desde previa, repeticiones del nivel | por sesión/fase | primaria |
| F05 | `effort_result_event` | AT_EVENT | volumen/desplazamiento, desplazamiento/path, posición final, volumen en extremo | percentil por fase y ancho | primaria |
| F06 | `scheduled_news` | PRE | tipo, minutos hasta/después, dentro/fuera de ventana | calendario oficial | primaria/exógena |
| F07 | `trend_score` | PRE | retorno firmado 5 min dividido por RV; distancia a VWAP/RV | por fase | secundaria, una sola variable |
| F08 | `failed_filter_identity` | AT_EVENT | filtro que falla el near-miss y distancia al umbral | por filtro | diagnóstico R2 |
| F09 | `trade_only_illiquidity` | PRE | `abs(return_5m)/volume_5m` junto con ambos componentes | bucket horario; proxy explícito | secundaria |
| F10 | `geometry_direction` | AT_EVENT | ancho, lado, barrido con/contra tendencia, posición en rango | ticks/volatilidad | secundaria |
| L01 | spread/depth/OFI | PRE/AT_EVENT | sólo con BBO/L2 sincronizado | intradía | diferida |
| L02 | queue imbalance/microprice | PRE | sólo con colas reales | instrumento/hora | diferida |
| L03 | replenishment half-life | POST | recuperación de depth/spread tras shock | estado previo | outcome diferido |

### Restricción de normalización

Los percentiles no pueden usar observaciones futuras. La implementación live-compatible
debe usar una referencia expansiva o un bloque de calibración anterior. Para atlas
puramente descriptivo se puede publicar también la normalización full-training, pero
con nombre distinto y prohibida para evaluación predictiva.

---

## 5. R2 — auditoría obligatoria del matching antes de buscar contextos

Población conocida:

- 9.234 zonas elegibles para cruce;
- 7.542 con control;
- 1.692 sin control;
- match rate 81,7 %.

R2 no mira outcomes. Debe publicar:

1. matched contra unmatched por fase, ancho, dirección y tipo `ABSORB/SWEEP`;
2. actividad, volatilidad, tendencia y posición en rango previas;
3. episodio limpio/apilado usando sólo historia causal;
4. cantidad de controles candidatos por zona;
5. identidad del filtro fallado y distancia a su umbral;
6. distribución de separación temporal control-zona;
7. matching con/sin reemplazo;
8. cantidad máxima y distribución de reutilización de controles;
9. dependencia del orden de matching;
10. cobertura por sesión, fase y ancho.

Diagnósticos mínimos de balance:

- SMD antes/después, con `|SMD| < 0,10` como referencia, no como verdad automática;
- ratios de varianza;
- máxima diferencia eCDF/KS;
- N unmatched y descartado por soporte común;
- interacción de fase × volatilidad y fase × actividad;
- denominadores explícitos.

Fuente metodológica: MatchIt, *Assessing Balance*  
<https://cran.r-project.org/web/packages/MatchIt/vignettes/assessing-balance.html>

Si el 18,3 % sin control se concentra en Asia, noticias, extremos de liquidez o zonas
apiladas, el nulo agregado no representa esas subpoblaciones. Eso no demuestra edge:
obliga a redefinir el soporte o limitar el estimando.

---

## 6. R3 — protocolo de inferencia clusterizada

R3 se escribe antes de re-medir retorno o costo condicionado.

Debe congelar:

- estimando primario: zona ponderada vs sesión ponderada;
- estadístico por sesión;
- resampleo de sesiones completas, no filas;
- B y seed;
- tratamiento de sesiones con pocos pares;
- margen de equivalencia económico;
- cinco métricas y su multiplicidad;
- reporte de heterogeneidad sin promover cortes post hoc.

La opción simple y auditable es bootstrap no paramétrico de sesiones completas. Si se
usa una regresión, se justifica cluster-robust/wild-cluster bootstrap y se diagnostican
clusters desbalanceados. No se elige el método después de mirar cuál da significancia.

Referencia general: Cameron y Miller, *A Practitioner’s Guide to Cluster-Robust
Inference*  
<https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf>

---

## 7. Outcomes candidatos — registrados, todavía no pre-registrados

La literatura separa al menos tres mecanismos:

1. **continuación:** desplazamiento firmado en la dirección del barrido;
2. **reversión:** recuperación de parte del impacto inicial;
3. **resiliencia:** tiempo de normalización del impacto, spread o profundidad.

Por el dato disponible, no usar horizontes menores de un segundo. Candidatos para una
campaña futura: `1 s`, `5 s`, `30 s`. Una hipótesis de atracción/revisita a `1–5 min`
es otra familia y no debe mezclarse con microestructura.

Plantillas mecánicas —no resultados—:

- libro fino/noticia + alto impacto por esfuerzo → candidato a continuación;
- alto esfuerzo + poco desplazamiento + reposición → candidato a reversión;
- primera zona del burst vs repetición/apilamiento → efectos potencialmente distintos.

La dirección, umbrales y outcome final siguen abiertos hasta terminar R2 y el atlas.

---

## 8. Criterios de continuación y cierre

### Continuar la familia sólo si

- R2 muestra soporte y balance suficientes para el estimando declarado;
- los contextos se eligen target-free;
- el efecto condicionado tiene CI por sesión;
- supera un margen económico declarado, no sólo `p < 0,05`;
- sobrevive el presupuesto de multiplicidad;
- no depende de un único período, sesión o control reutilizado;
- el holdout permanece intacto hasta una única apertura gobernada.

### Considerar cerrada la zona como señal si

- los contextos predeclarados siguen equivalentes a casi-zonas;
- la heterogeneidad desaparece al trabajar por episodio/sesión;
- el resultado sólo aparece con umbrales elegidos post hoc;
- o el efecto bruto no paga fricción realista.

Cerrar como señal no impide conservarla como descriptor de microestructura.

---

## 9. Fuentes y grado de transporte

| Fuente | Mercado | Uso permitido | Limitación |
|---|---|---|---|
| Takahashi 2025 | ES directo | hora, noticias, impacto, horizonte | working paper reciente |
| Andersen et al. | ES directo | normalización intradiaria | no prueba HFTZones |
| Fishe et al. 2022 | E-mini directo | resiliencia/reposición | requiere libro para medida directa |
| Cont et al. 2014 | acciones LOB | OFI/depth como mecanismo | no ES; transporte conceptual |
| Gould/Bonart 2016 | acciones Nasdaq | queue imbalance | no ES; requiere colas reales |
| Andersen/Bondarenko | S&P futures | rechazo de VPIN/BVC | disputa específica, no veto universal a todo proxy |
| Hewlett/Hawkes | FX | clustering/metaórdenes | no exige usar Hawkes en ES |
| Harvey/Liu | finanzas empíricas | gobernanza/multiplicidad | no especifica estimando HFT |
| MatchIt/CEM | metodología | balance y soporte | matching no convierte esto en causalidad |
| Cameron/Miller | econometría | inferencia clusterizada | método exacto debe congelarse en R3 |

---

## 10. Frase de cierre

> La segunda capa de research no rescató una zona universal. Sí reforzó una hipótesis
> más estrecha y científicamente defendible: HFTZones podría estar etiquetando shocks
> de flujo cuyo signo depende de liquidez, resiliencia, noticias y posición dentro de
> un episodio. La forma correcta de averiguarlo es una capa offline causal y pequeña,
> no modificar el indicador ni agregar una ensalada de señales.
