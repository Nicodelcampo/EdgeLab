# H-Z2A-1 — Segunda aproximación a una zona tras *near-miss* y reset

- **Fecha:** 2026-08-16
- **Origen:** hipótesis propuesta por Nico en el hilo de auditoría.
- **Estado:** `HYPOTHESIS_DEFINED_NOT_RUN`.
- **Alcance:** especificación conceptual, causal y operacional; revisión de microestructura; diseño de falsación.
- **Firewall:** `outcomes_accessed=False`, `pnl_accessed=False`, `holdout_included=False`.
- **Autorización:** este documento **no autoriza F4**, no afirma un edge y no abre una campaña de múltiples indicadores.

---

## 1. Veredicto ejecutivo

La dinámica propuesta es una **buena hipótesis para buscar información**, pero todavía no es una hipótesis causal identificada ni una estrategia.

La versión fuerte —«el precio no entró porque existía un impedimento; después del rebalanceo ese impedimento desapareció; por eso el segundo ataque atraviesa»— es plausible, pero no puede inferirse del precio por sí solo. El mismo patrón puede surgir por persistencia de una orden madre, impacto transitorio, cancelaciones, reposición de liquidez, comportamiento coordinado alrededor de niveles, noticias o simple geometría de primer pasaje.

La versión defendible y testeable es:

> Dada una zona creada y congelada ex ante, al inicio de una segunda aproximación posterior a un *near-miss*, una reversión y un reset, ¿la historia del primer intento agrega capacidad predictiva para el acceso o la penetración de la zona por encima de lo que ya explican la distancia actual, la volatilidad, el spread, el régimen y la fuerza direccional presente?

Hay dos incógnitas principales y una tercera barrera económica:

1. **Q-ZONA:** ¿qué zonas son realmente informativas, frente a pseudozonas comparables?
2. **Q-DINÁMICA:** dentro de una zona válida, ¿el camino `near-miss → reversión → reset → segunda aproximación` cambia la distribución futura?
3. **Q-ECONÓMICA:** aun si cambia, ¿queda recorrido ejecutable neto de spread, slippage y comisión?

El orden importa. Si se optimizan simultáneamente la definición de zona, el *near-miss*, el reset, la fuerza, el horizonte y la penetración, el resultado será casi inevitablemente un ganador retrospectivo.

---

## 2. Lo que la microestructura sí permite sostener

### 2.1 Persistencia de flujo y órdenes partidas

El signo del flujo de órdenes es persistente porque órdenes grandes suelen dividirse en muchas órdenes hijas. Esa persistencia hace plausible que, después de una pausa o reversión transitoria, vuelva a aparecer presión en la dirección original. No prueba que haya «la misma institución» ni que la zona de destino sea especial.

### 2.2 Impacto transitorio y resiliencia

El impacto no es necesariamente permanente. El libro se repone y el precio puede revertir parcialmente mientras llegan nuevas órdenes límite. En E-mini, la evidencia de resiliencia muestra que participantes pacientes vuelven a colocar órdenes con rapidez, y que la reposición depende de ejecuciones, nuevas órdenes y cancelaciones. Por lo tanto, el reset puede ser una pausa de liquidez; pero también puede reconstruir la barrera en vez de eliminarla.

### 2.3 OFI, profundidad y desequilibrio de colas

A horizontes muy cortos, cambios de precio se relacionan con el desequilibrio del flujo de órdenes y con la profundidad disponible. El *queue imbalance* contiene información sobre el siguiente movimiento, con fuerza distinta según la microestructura del instrumento. Esto respalda usar OFI, profundidad, microprice y adiciones/cancelaciones como variables; no respalda asumir que cualquier desequilibrio produce una ganancia neta.

### 2.4 Liquidez oculta

El volumen visible no es la liquidez total. Icebergs y reposición pueden hacer que un nivel aparentemente consumido siga existiendo. Tampoco una cancelación significa que «la intención desapareció»: la orden puede reubicarse. Sin MBO y aun con MBO, la identidad económica y el inventario de los participantes siguen siendo parcialmente latentes.

### 2.5 Evidencia contraria al relato de agotamiento simple

Investigaciones sobre soporte/resistencia encontraron que más rebotes previos pueden asociarse con mayor probabilidad de volver a rebotar, aunque esa memoria decae con el tiempo. Esto compite directamente con la idea retail de que «cada test debilita el nivel».

Por eso deben convivir dos mecanismos rivales:

- **M-AGOTAMIENTO:** el primer episodio consume/cancela la liquidez que frenaba el acceso; la segunda aproximación penetra más.
- **M-REFUERZO:** el primer rechazo revela o coordina interés, atrae nueva liquidez y aumenta otro rebote.

Que ambos tengan sentido es una virtud: la hipótesis puede ser refutada.

---

## 3. Definición canónica del objeto

### 3.1 Zona ex ante

Una zona `Z_i = [L_i, U_i]` es elegible solo si:

- fue creada en `t_z` con información disponible hasta `available_at_z`;
- sus bordes, origen, score, lado, expiración e invalidación quedan congelados;
- no utiliza futuros toques, rebotes ni outcomes para existir o graduarse;
- cada modificación posterior crea una nueva versión identificable;
- su primera interacción solo puede ocurrir estrictamente después de `available_at_z`.

«Evidentemente de interés» no es una definición. En el experimento se reemplaza por una familia de generadores ex ante y se compara contra pseudozonas.

### 3.2 Distancia orientada

Para cada lado de aproximación se define una distancia `d_t` en ticks desde el precio transable pertinente hasta el borde cercano:

- `d_t > 0`: precio fuera de la zona;
- `d_t = 0`: acceso al borde;
- `d_t < 0`: penetración.

Debe fijarse si el evento usa trades, bid/ask o ambos. Para un claim de acceso real, el primario debe ser una transacción dentro de la zona; un cruce del mid no basta.

### 3.3 Máquina de estados causal

1. **ZONA_DISPONIBLE.** Zona viva y disponible ex ante.
2. **APROXIMACIÓN_1.** El precio viene desde una distancia mínima `D_far` y `d_t` cae durante actividad suficiente.
3. **NEAR_MISS_1.** La aproximación alcanza un mínimo `0 < d_min ≤ δ_nm` sin transacción dentro de la zona.
4. **RECHAZO_1.** Antes de tocar, `d_t` aumenta al menos `R_min` o se alcanza una barrera de reversión equivalente.
5. **RESET.** Sin tocar la zona, transcurre una separación mínima y las variables de corto plazo dejan de estar en el estado de la primera aproximación. «Reset» es una definición observable; no se llama rebalanceo de inventario salvo evidencia adicional.
6. **APROXIMACIÓN_2 / LANDMARK `t2`.** Primer instante posterior al reset en el que la distancia vuelve a disminuir y la fuerza direccional cumple la regla predefinida. La predicción nace aquí, no después de ver el desenlace.
7. **OUTCOME.** Compiten acceso, penetración, travesía, nueva reversión, timeout, borde de sesión o borde de datos.

Los umbrales `D_far`, `δ_nm`, `R_min`, duración del reset y fuerza **no se fijan mirando outcomes**. Si se evalúan varias alternativas, cada una cuenta en `N_eff`.

### 3.4 Reset no es «inventario recargado»

Con datos públicos no se observa el inventario agregado de quienes proveen liquidez. La primera versión debe hablar de **reset observable** y medir, según disponibilidad:

- retorno de velocidad y aceleración a banda neutral;
- reversión/normalización de OFI y delta agresor;
- caída de intensidad o pausa en reloj de eventos;
- normalización de spread y microprice;
- recuperación/reubicación de profundidad;
- tasa de adiciones, cancelaciones y ejecuciones;
- tiempo desde el rechazo y distancia máxima alcanzada.

La interpretación «rebalancearon cartera» queda como variable latente, no como dato.

### 3.5 Fuerza de segunda aproximación

No conviene inventar de entrada un único *force score*. La primera prueba debe conservar un vector transparente:

- pendiente y aceleración del precio orientadas hacia la zona;
- retorno por reloj de eventos o volumen;
- intensidad de trades;
- volumen y delta agresor;
- OFI;
- queue imbalance y microprice, cuando exista L2 validado;
- retirada de profundidad del lado que bloquea y reposición del lado que empuja;
- spread y volatilidad local.

Si se aprende una combinación de pesos, se aprende dentro de cada fold de entrenamiento. Una PCA sin outcome puede reducir dimensión; no elimina el costo de haber probado distintas representaciones.

---

## 4. Outcomes: no reducir todo a «tocó»

El objeto natural es de primer pasaje con riesgos competitivos.

Outcomes primarios posibles:

- `Y_touch`: primera transacción dentro de `[L_i,U_i]` antes del límite;
- `T_touch`: tiempo/eventos/volumen hasta ese acceso;
- `Y_pen_k`: penetración de al menos `k` ticks desde el borde cercano;
- `Y_traverse`: transacción más allá del borde lejano más un buffer;
- `max_penetration`: máxima penetración continua;
- `retreat_before_touch`: nueva reversión antes del acceso;
- `session_boundary`, `timeout`, `data_edge`.

«Tocar» y «atravesar» son hipótesis diferentes. También lo son atravesar un punto y sostenerse después. No deben fusionarse en un único éxito.

Para F4, antes de SL/TP, interesa:

- hazard de acceso/penetración;
- distribución de `max_penetration`;
- retorno orientado a horizontes predeclarados;
- MFE/MAE diagnóstico desde `t2`;
- calibración de probabilidades.

---

## 5. El nulo difícil: la hipótesis puede ser una tautología geométrica

Un precio que ya está cerca, con velocidad hacia una barrera y volatilidad elevada, tiene mayor probabilidad mecánica de tocarla. Si el grupo tratado tiene más cercanía o fuerza que el control, se «descubrirá» la dinámica aunque la historia anterior no importe.

La comparación correcta se hace en `t2`, igualando o modelando:

- distancia actual a la zona;
- lado;
- ancho y edad de zona;
- velocidad/aceleración actual;
- volatilidad y actividad;
- spread y profundidad;
- hora/sesión/noticias;
- instrumento y contrato;
- fuerza actual;
- régimen de mercado.

Estimand predictivo central:

`Δ_historia(z,x) = P(Y=1 | historia near-miss/reset, Z=z, X_t2=x) − P(Y=1 | sin esa historia, Z=z, X_t2=x)`

Esto es una diferencia condicional predictiva. No se la llama efecto causal del *near-miss*.

---

## 6. Tres incrementos que separan las incógnitas

En evaluación temporal fuera de muestra:

- **M0 — Geometría:** distancia, velocidad, volatilidad, spread, hora y régimen.
- **M1 — M0 + Zona:** familia, score, ancho, edad, lado, estado y features ex ante de la zona.
- **M2 — M1 + Historia:** *near-miss*, profundidad de rechazo, duración/reset, cambio de flujo entre episodios.
- **M3 — M2 + Mecanismo L2:** OFI multinivel, colas, microprice, profundidad, adiciones/cancelaciones/ejecuciones, reposición e iceberg proxies.

Lectura:

- `M1 > M0`: la zona aporta información frente a la geometría.
- `M2 > M1`: la secuencia propuesta aporta información frente al estado actual.
- `M3 > M2` con signos coherentes: hay apoyo observacional al mecanismo microestructural.
- solo `M0` funciona: es primer pasaje/momentum genérico, no una dinámica de zonas.
- `M1` funciona y `M2` no: la zona importa; la historia del primer intento no.
- `M2` funciona también en pseudozonas: hay una dinámica de reaproximación genérica, pero no de zonas de interés.

Métricas: log-loss/Brier y calibración para probabilidad; C-index o modelos de hazard/competing risks para tiempo; IC/Spearman para outcomes continuos. AUC sola no alcanza.

---

## 7. Controles y placebos obligatorios

1. **Pseudozonas desplazadas:** misma sesión, lado, edad, ancho y distribución de distancia; nivel desplazado sin generador económico.
2. **Primera aproximación equivalente:** mismo estado actual, sin historia previa.
3. **Segunda aproximación sin near-miss:** hubo alejamiento y regreso, pero no un casi-toque definido.
4. **Near-miss sin reset:** separa pausa/rebalance observable de mera oscilación.
5. **Reset sin fuerza renovada:** prueba que «volver» no basta.
6. **Historia permutada por bloques:** conserva sesión y dependencia local, rompe la asociación específica.
7. **Generador de zona frente a precio aleatorio condicionado:** evita que cualquier nivel cercano parezca especial.
8. **Regímenes adversos:** apertura, noticias, roll, baja liquidez y borde de sesión deben separarse o excluirse ex ante.

No se deben partir entre train y test eventos de la misma zona. Una zona con varias aproximaciones es una unidad dependiente.

---

## 8. Grafo causal mínimo

Variables latentes/observadas:

- `Z`: tipo/calidad/edad de zona;
- `C`: volatilidad, hora, noticias, régimen y cross-asset;
- `M`: metaorden o información persistente, latente;
- `L0/L1`: liquidez visible y latente antes/después del primer episodio;
- `R1`: near-miss + rechazo;
- `B`: reset observable;
- `A2`: segunda aproximación con fuerza;
- `Y`: acceso/penetración.

Relaciones plausibles:

`Z,C,M,L0 → R1`

`R1,C,M → cambios en L1 y B`

`C,M,L1,B → A2`

`Z,C,M,L1,A2 → Y`

Condicionar la muestra a que `A2` haya ocurrido selecciona caminos comunes de `M`, `C` y `L1`; por eso puede crear sesgo de collider. La solución práctica es definir un **landmark predictivo** en `t2`, declarar que el estimand es condicional a llegar a `A2`, y no venderlo como «R1 causa Y».

---

## 9. Cómo resolver las dos incógnitas sin producto cartesiano

No se descubre a la vez la mejor zona y la mejor dinámica en el mismo panel final.

### Fase A — una zona

Usar una única familia congelada y una semántica de evento. En EdgeLab, la candidata natural es `aVolClusterPOI` `OFF_PRICE`:

- detecta un cluster de masa de volumen anómala relativo a historia previa;
- produce bordes y `available_at` ex ante;
- `AT_PRICE` es ocupación, no soporte/resistencia, y queda fuera;
- ya es la familia indicada para el próximo F4.

Esta fase responde primero si la dinámica contiene información dentro de un objeto coherente.

### Fase B — generalización de zonas

Solo después, preregistrar una lista pequeña de familias y tratarlas como interacción, no como concurso libre:

`outcome ~ estado_actual + zona + historia + zona×historia`

Cada familia, score cut, horizonte, buffer y outcome entra al ledger de `N_eff`. La selección ocurre en folds internos; el fold externo solo estima generalización. Puede usarse *partial pooling* jerárquico para reducir el sesgo del «mejor de muchos».

### Situación de los generadores actuales

- **aVolClusterPOI OFF_PRICE:** primera opción.
- **BigTrap2:** solo geometría; la hipótesis de «imán» está cerrada y el cruce con aVol está prohibido por el acta vigente.
- **HFTZones2:** genera zonas de rachas rápidas/absorción, pero la paridad formal sigue pendiente; además, usarlo como zona y como fuerza puede duplicar la misma información.
- **VolTicksPOC2:** POC de volumen anómalo; útil después, no en la primera campaña.
- **Gaps2:** zona mecánica útil como control o familia separada; no prueba interés económico por sí sola.
- **L2/GEX:** covariables de régimen o mecanismo después de sus gates, no columnas añadidas en masa.

---

## 10. Qué puede probar EdgeLab hoy y qué necesita L2

### Con el árbol actual

Puede probarse la versión **reducida y predictiva**:

- zona aVol OFF_PRICE ex ante;
- dos aproximaciones y sus distancias;
- near-miss, rechazo, reset por precio/actividad/volumen;
- fuerza por retorno, intensidad y volumen;
- touch/penetración/travesía;
- modelos M0–M2.

No puede sostenerse:

- que se agotó una cola concreta;
- que se retiró una institución;
- que se recargaron inventarios;
- que la misma orden madre regresó.

`sequence == source_row` no es secuencia del exchange. Un claim fino de colas requiere un pipeline L2/MBO con secuencia, integridad, reconstrucción y paridad propias.

### Con L2 validado

Agregar:

- OFI por nivel;
- queue imbalance;
- microprice;
- profundidad y pendiente del libro;
- ejecuciones vs cancelaciones vs adiciones;
- tiempo/half-life de reposición;
- migración de liquidez hacia/desde el borde;
- detección conservadora de replenishment/iceberg;
- cambios entre ventana pre-near-miss, rechazo/reset y `t2`.

Aun así, se hablará de **proxies de inventario**, no de inventarios observados.

---

## 11. Dependencia, multiplicidad y validación

- Unidad primaria de clustering: `zone_id`; segundo nivel: sesión/`trade_date` CME.
- Una zona completa debe quedar en un solo fold.
- Purge/embargo al menos por vida de zona y horizonte máximo.
- Bootstrap por bloques/estacionario; no filas IID.
- Walk-forward temporal; CPCV o múltiples paths si el tamaño lo permite.
- Resultados separados por instrumento antes de cualquier pooling.
- Contar en `N_eff`: familias de zona, thresholds, definiciones de reset, fuerza, horizontes, penetraciones, modelos, exclusiones y variantes abandonadas.
- El holdout permanece cerrado. Todo esto ocurre en desarrollo.

El riesgo principal no es que la idea sea absurda; es que sus muchas piezas permitan construir retrospectivamente la versión ganadora.

---

## 12. De información a posible operación

Una mayor probabilidad de tocar una zona no garantiza monetización. Deben separarse al menos dos estrategias futuras:

1. **Pre-touch continuation:** entrar en `t2`, buscar el borde o una penetración. Tiene más recorrido, pero mayor riesgo de otra reversión.
2. **Post-penetration continuation:** esperar una transacción más allá del borde y buscar continuación. Tiene menos ambigüedad, pero menos recorrido y más costo/adverse selection.

No se elige ahora. F4 pregunta por información. Solo si existe se construyen triple barrera/simulador con `available_at → step estrictamente posterior`, escenario base y costos W7 por instrumento.

Una dinámica puede ser estadísticamente real y económicamente inútil si:

- la mejora de touch es pequeña;
- el recorrido al borde es menor que la fricción;
- el fill ocurre después de consumido el recorrido;
- la cola/latencia vuelve inalcanzable el precio;
- la mayor penetración viene con MAE o tails incompatibles con el sizing.

---

## 13. Criterios de falsación

### Muere Q-ZONA si

- M1 no mejora M0 fuera de muestra;
- la zona no supera pseudozonas condicionadas;
- el efecto depende de bordes definidos con futuro;
- solo aparece al elegir el mejor score/edad/horizonte después de mirar.

### Muere Q-DINÁMICA si

- M2 no mejora M1;
- la historia desaparece al igualar distancia y fuerza actuales;
- solo funciona en una definición estrecha no estable;
- el efecto se explica por una aproximación genérica también en pseudozonas.

### Muere el mecanismo de agotamiento si

- la liquidez se repone o fortalece en vez de retirarse;
- no hay cambio consistente en OFI/profundidad/cancelaciones/replenishment;
- la probabilidad de rebote aumenta tras el primer rechazo;
- la evidencia es compatible con memoria de soporte/resistencia, no con agotamiento.

### Se convierte en candidato a edge solo si

1. hay lift/calibración OOS estable sobre M0;
2. la zona y la historia aportan incrementos separados;
3. existe recorrido neto bajo costos base;
4. G2 pasa con `N_eff` completo y dependencia no IID;
5. una apertura de holdout pasa;
6. shadow y luego capital mínimo replican.

---

## 14. Dictamen para EdgeLab

**Sí, es un buen approach para probar edges**, con cuatro condiciones:

1. formularlo como predicción incremental, no como relato causal ya resuelto;
2. empezar con `aVolClusterPOI OFF_PRICE` sola;
3. demostrar primero que la historia agrega información sobre geometría y fuerza actual;
4. reservar L2 para adjudicar el mecanismo, después de su gate.

Valoración cualitativa:

- **plausibilidad microestructural:** media-alta;
- **falsabilidad:** alta si se conserva la especificación anterior;
- **identificabilidad causal con datos actuales:** baja;
- **testabilidad predictiva con EdgeLab actual:** media;
- **riesgo de data mining:** alto por las dos incógnitas y los muchos grados de libertad;
- **potencial como familia F4:** alto respecto de probar indicadores sin mecanismo.

Esta hipótesis no abre una ruta paralela: puede aportar el estimand, event-space y grafo causal que faltan en el manifiesto F4 de aVol. El orden sigue siendo población + `N_eff` + grafo causal → STOP de Nico → F4 IC/hazard → simulador si hay información.

---

## 15. Redacción canónica para la próxima iteración entre modelos

> Para una zona `Z` creada y congelada ex ante, se observa una primera aproximación desde una distancia mínima que termina en un near-miss sin acceso, seguida por un rechazo y un reset observable. En el primer landmark posterior en el que el precio vuelve a aproximarse con fuerza, se evalúa si la historia del near-miss/reset aumenta la probabilidad y el hazard de touch, penetración o travesía, condicionando por distancia, volatilidad, spread, régimen y fuerza actuales. En paralelo se evalúa si ese incremento es específico de ciertas familias de zona frente a pseudozonas. La explicación de agotamiento/rebalanceo se trata como mecanismo rival que requiere L2, no como premisa.

Preguntas que otra iteración debe intentar romper:

1. ¿El primer episodio debe ser un *near-miss* estricto o también un toque superficial?
2. ¿La segunda aproximación debe venir del mismo lado?
3. ¿Qué reset observable no usa futuro ni duplica la regla de fuerza?
4. ¿Touch, penetración y travesía requieren modelos separados?
5. ¿Qué control reproduce la misma geometría sin interés de zona?
6. ¿Qué evidencia distinguiría agotamiento de refuerzo/reposición?

---

## 16. Fuentes iniciales

- Cont, Kukanov y Stoikov, *The Price Impact of Order Book Events*: https://arxiv.org/abs/1011.6402
- Gould y Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor*: https://arxiv.org/abs/1512.03492
- Bouchaud et al., *Price Impact*: https://arxiv.org/pdf/0903.2428
- Fishe, Haynes y Onur, *Resiliency in the E-mini Futures Market*: https://doi.org/10.1002/fut.22259
- Chung y Bellotti, *Evidence and Behaviour of Support and Resistance Levels*: https://arxiv.org/abs/2101.07410
- Lo y Hall, *Resiliency of the Limit Order Book*: http://opus.lib.uts.edu.au/bitstream/10453/98964/1/Lo_Hall_Resiliency_of_the_limit_order_book_Accepted_Manuscript.pdf
- Frey y Sandås, *The Impact of Hidden Liquidity in Limit Order Books*: https://conference.nber.org/confer/2008/mms08/sandas.pdf

Aporte al referente: convierte una intuición rica pero narrativa en dos preguntas separables, una máquina de estados causal, nulos difíciles y una ruta de falsación que puede incorporarse al F4 sin abrir el producto cartesiano de indicadores.