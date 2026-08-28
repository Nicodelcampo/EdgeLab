# H-Z2A v3 — investigación del fenómeno, estructura medible y plan integral

**Fecha** 2026-08-16 · **Origen** pedido explícito de Nico (19:55 ART): «1- informarse en internet porque este fenómeno está estudiado. 2- traducir toda esta información en una estructura, real, aplicable, que refleje la idea de manera correcta y la traduzca en análisis acordes, es decir, que se mida lo que se tiene que medir, no creerse a priori que lo que se mide lo que se quiere medir. 3- diseñar un plan que contemple cada variable, métodos a utilizar, formas de medir el movimiento del precio (ticks, tiempo, etc) y que contemple lo que se sabe hasta ahora sobre esta idea.»
**Predecesor** `docs/research/H_Z2A_V2_OPERACIONALIZACION_2026-08-16.md` (commit `901ca82a4fe47b6cb865f5e877e23f41ebf73d52`), que ya incorpora la opinión de Nico de las 19:35 (el core no se mata rápido; se matan variantes).
**Estado** `HYPOTHESIS_DEFINED_NOT_RUN` · **Outcomes** `false` · **P&L** `false` · **Holdout** intacto · **Multiplicidad gastada** cero
**NORTH_STAR** sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

> Este documento **no autoriza F4**. Es el mandato 1+2+3 de Nico: (1) mapear la literatura del fenómeno, (2) fijar la estructura con **validez de constructo** explícita, (3) escribir el plan integral variable por variable. Nada acá lee un outcome ni promueve estado.

---

## Parte 1 — El fenómeno está estudiado: mapa de la literatura

La dinámica de Nico —aproximación desde lejos, giro **antes** de llegar a la zona evidente, rebalanceo, y segunda aproximación con dirección y fuerza que esta vez sí accede y atraviesa— aparece estudiada en **cuatro tradiciones independientes**. Ninguna la describe entera con ese nombre; juntas cubren cada pieza.

### 1.1 El mecanismo de órdenes: Osler (2003, Journal of Finance)

Carol Osler, *Currency Orders and Exchange-Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis* (JoF 58(5), 2003; FRBNY Staff Report 125): con datos reales de órdenes individuales de un gran banco, documenta que **las take-profit se agrupan EN los números redondos** y **las stop-loss se agrupan JUSTO MÁS ALLÁ de los redondos**, y que ese clustering explica dos predicciones clásicas del chartismo: (1) las tendencias **se revierten en niveles predecibles** de soporte/resistencia, y (2) las tendencias se **aceleran una vez que el nivel se cruza**.

Es la pieza más importante del mapa para H-Z2A: describe **las dos mitades** de la dinámica de Nico con mecanismo observado, no con narrativa. El giro antes de la zona = absorción por el muro de take-profits/límites agregados; la travesía acelerada = el disparo de los stops agrupados detrás. El seguimiento *Stop-Loss Orders and Price Cascades in Currency Markets* (Osler 2005, JIMF) muestra que las ejecuciones de stop-loss llegan **en olas** y que su respuesta de precio es mayor y más duradera que la de los take-profits — eso es exactamente «accede e incluso atraviesa».

### 1.2 Las zonas son el libro: Kavajecz & Odders-White (2004, RFS)

*Technical Analysis and Liquidity Provision* (Review of Financial Studies 17(4)): los niveles de soporte/resistencia **coinciden con picos de profundidad en el libro de órdenes límite**, y las medias móviles revelan información sobre la posición relativa de la profundidad. La relación viene de que las reglas técnicas **localizan liquidez que ya estaba puesta**.

Consecuencia para el constructo: una «zona de interés» no es un objeto místico del gráfico; es **inventario visible en el libro**. Esto (a) valida definir zonas por **densidad de indicadores** —varios métodos convergiendo al mismo precio es exactamente cómo se forma un pico de profundidad— y (b) advierte: sin L2, la zona se mide por sus huellas (niveles donde los indicadores confluyen), no por el mecanismo mismo.

### 1.3 La atracción tiene análogo externo: el efecto imán

Cho, Russell, Tiao & Tsay, *The Magnet Effect of Price Limits: Evidence from High-Frequency Data on Taiwan Stock Exchange* (Journal of Empirical Finance 10, 2003): los precios **aceleran hacia el límite diario al acercarse** (efecto imán, fuerte al alza). Du et al. (2009, Korea) lo replican con libro completo; Goldstein & Kavajecz (2004) documentan el comportamiento de estrategias durante circuit breakers.

Para H-Z2A: es el análogo externo de F1.1 (atracción +47,07 pp). Los límites regulatorios no son zonas BigTrap2, pero la física es la misma: **un borde conocido reorganiza el flujo antes de ser tocado**. Refuerza que «la zona atrae» está bien apoyado; lo que falta probar es la **historia** (near-miss → rechazo → reset).

### 1.4 Formalización de patrones: Lo, Mamaysky & Wang (2000, JoF)

*Foundations of Technical Analysis* (JoF 55(4); NBER WP 7613): reconocimiento **sistemático y automático** de diez patrones clásicos vía regresión kernel no paramétrica, comparando distribuciones condicionadas vs incondicionadas (1962–1996). Varios patrones **aportan información incremental**.

Es el precedente metodológico directo para el eje «formas de determinar un cluster de interés» de Nico: la definición de zona/cluster debe ser **algorítmica, con parámetros declarados** (suavizado, densidad mínima, ventana), no visual. Cada definición alternativa es una **variante** con costo de multiplicidad, exactamente como pidió Nico a las 19:35.

### 1.5 La tradición estructurada de práctica: Auction Market Theory / Market Profile

El Market Profile de Steidlmayer (CBOT, años 80) nombra **precisamente** el evento condicionante de H-Z2A:

- **Poor high / poor low**: un extremo de sesión sin *excess* (sin cola de rechazo) se considera una **subasta incompleta**: el precio tiende a **volver** a ese nivel. Es el near-miss de Nico con nombre propio.
- **Excess**: la cola que marca rechazo genuino; niveles con excess son referencias de alta probabilidad. La «regla 80 %» de la literatura de perfil: si el excess se forma temprano y el precio vuelve a testearlo, el test **falla ~80 %** de las veces — o sea, la segunda aproximación **se revierte**, no atraviesa. Esto es un **contraejemplo parcial** a la narrativa de Nico y debe quedar registrado como predicción rival: la tradición de perfil espera que el retorno al nivel con excess falle; Nico hipotetiza que cuando el giro fue *antes* de la zona (sin tocarla, sin excess **en la zona**), la re-aproximación sí accede. La distinción empírica entre ambas predicciones es exactamente `d_min ≤ δ_nm` sin toque vs toque con rechazo. **H-Z2A es, en rigor, la hipótesis que separa estas dos tradiciones.**
- **Failed auction / look-above-and-fail**: sondeo que no atrae contraparte y revierte; inventario atrapado que **combustiona** la rotación de vuelta. Es la pieza «rebalanceo / recarga de inventarios» de Nico, declarada como mecanismo a verificar con flujo, no como dato.

### 1.6 Wyckoff: la segunda aproximación es el «test»

La secuencia de acumulación Wyckoff —clímax → rally automático → **secondary test** → spring → **test** → sign of strength → last point of support— contiene la segunda aproximación como evento canónico: el *test* exitoso se define por **menor volumen y menor spread** que el episodio previo (agotamiento de oferta), y el *test de mala calidad* (más bajo, más volumen) **se vuelve a testear después**. Es decir: Wyckoff ya clasifica las segundas aproximaciones por su **calidad** y predice revisitas condicionales. Lo tomo como ontología de eventos (nombres, secuencia), no como evidencia estadística: es teoría de práctica sin inferencia formal.

### 1.7 Stop hunting / liquidity sweeps (lore institucional, marcar como tal)

La literatura de práctica FX/futuros describe «liquidity sweeps»: los pools de stops **no tocados siguen ahí** como combustible; las barridas válidas requieren confirmación de volumen/flujo y fallan lejos de pools establecidos. Coincide con la intuición de Nico («el motivo por el cual no accedió ya no existe» ⇒ la defensa se gastó o el pool quedó intacto y atrae). **Estado epistémico: hipótesis de mecanismo sin validación académica directa.** Se registra porque motiva variables (distancia al pool, consumo previo) y porque Osler 2003/2005 le da base real de clustering, pero prohibido escribirlo como hecho.

### 1.8 GEX y cobertura de dealers: la zona de interés exógena

La exposición gamma agregada de dealers genera niveles mecánicos: con **gamma positiva** los dealers compran dips y venden rallies (estabiliza, «pinnea» al strike); con **gamma negativa** persiguen el movimiento (amplifica). Los niveles operativos son **call wall** (resistencia), **put wall** (soporte) y **gamma flip** (cambio de régimen). Base teórica de pinning: Avellaneda & Lipkin (2003); literatura reciente de expiración 0DTE.

Para H-Z2A: GEX es (a) un **generador exógeno de zonas de interés** (independiente de los indicadores internos ⇒ cruce de familia sin contaminación), y (b) una **variable de régimen** (signo de GEX modula si la zona rebota o se atraviesa). Nico ya lo tenía en la lista («lo antes posible sumar gex y data l2»): queda preregistrado como **Fase 4**, detrás de su propio gate de datos, con costo de multiplicidad propio.

### 1.9 Cómo medir el tiempo y el movimiento: relojes de eventos

La pieza metodológica que faltaba para el mandato 3:

- **Ané & Geman (2000, JoF 55(5))** — *Order Flow, Transaction Clock and Normality of Asset Returns*: los retornos se normalizan bajo **cambio de tiempo estocástico** al reloj de transacciones. El tiempo del mercado no es el calendario.
- **Easley, López de Prado & O'Hara (2012, JPM 39(1))** — *The Volume Clock*: el HFT opera en **reloj de volumen**; la actividad (no los minutos) pauta la llegada de información. Misma familia: VPIN / flow toxicity (RFS 2012).
- **Guillaume et al. (1997) y Glattfelder, Dupuis & Olsen (2011, Quantitative Finance 11(4))** — **directional-change intrinsic time**: discretizar la serie por **cambios direccionales de tamaño δ** en vez de por tiempo; descubren 12 leyes de escala en FX. El rechazo de H-Z2A **es** un directional change de tamaño `R_min`: este es el **reloj nativo del fenómeno**. Primer arXiv reciente: Glattfelder & Olsen (2024), *The Theory of Intrinsic Time: A Primer* (arXiv:2406.07354).
- **López de Prado, AFML cap. 2** — barras de tick/volumen/dólar, **imbalance bars** (muestrean cuando cambia el desequilibrio de flujo) y **run bars** (muestrean secuencias direccionales). Las run bars son la discretización natural de «aproximación con dirección y fuerza».

Conclusión: H-Z2A se mide en **cuatro relojes simultáneos** (calendario, ticks/eventos, volumen, directional-change), con resultados reportados en todos y sensibilidad obligatoria entre ellos. Un resultado que sólo existe en un reloj es un artefacto del reloj.

---

## Parte 2 — La estructura real y aplicable: validez de constructo primero

### 2.1 La regla de Nico, formalizada

> «No creerse a priori que lo que se mide es lo que se quiere medir.»

Cada concepto de la hipótesis pasa por cuatro eslabones, y **ninguno se salta**:

```
CONSTRUCTO (qué creo que es)
  -> OBSERVABLE (qué registro en el dato)
  -> ESTIMADOR (con qué código/estadístico lo computo)
  -> CHEQUEO DE VALIDEZ (cómo demuestro que el estimador captura el constructo)
```

Si el chequeo no existe o falla, la variable entra como **proxy declarado** con su limitación escrita, nunca como el constructo mismo. El repo ya sufrió violaciones de esta regla: los **seis defectos de `features.py`** documentados en v2 §7 son fallas de validez de constructo (distancia sin signo, sin `zone_id`, semánticas mezcladas, edad con sesgo de longitud, unidades de precio en vez de ticks). La regla no es decoración: es la lección del propio proyecto.

### 2.2 Tabla de constructos de H-Z2A

| constructo | qué ES (y qué no) | observable primario | proxies aceptables | proxies prohibidos | chequeo de validez |
|---|---|---|---|---|---|
| **Zona de interés** | concentración ex ante de intención en `[L,U]` con `zone_id` | nivel + ancho de la familia generadora, congelado en `available_at` | confluencia de indicadores (densidad), niveles GEX (Fase 4) | «la zona más cercana»; cualquier zona definida mirando el futuro | nulo apareado F1.1: la atracción real debe superar al nulo-B/C en la misma configuración |
| **Aproximación** | movimiento dirigido hacia la zona desde `d ≥ D_far` | `d_t` firmada en ticks decreciente, en reloj de eventos | run bar hacia la zona | velas verdes/rojas sueltas (dirección sin distancia) | en tiempo permutado por bloques, la tasa de «aproximaciones» no debe cambiar (si cambia, es ruido de muestreo) |
| **Near-miss** | giro con `0 < d_min ≤ δ_nm` y **cero trades dentro** | `d_min` en ticks + flag `no_trade_inside` | — | tocar con el mid; wicks sin trade; `inside_zone` de OTRA zona | recontar con `δ_nm ± 1 tick`: el evento no debe desaparecer/explotar (sensibilidad preregistrada) |
| **Rechazo** | reversión ≥ `R_min` antes de cualquier toque | directional change de tamaño `R_min` (reloj intrínseco) | retorno acumulado en N eventos | «mecha larga» visual | distribución de reversiones en caminatas sin zona (nulo de drift): el rechazo debe ser más profundo/rápido que el azar apareado |
| **Reset** | reacomodamiento post-rechazo sin toque | separación mínima cumplida en **tres escalas**: tiempo, eventos, volumen | — | una sola escala fija (Tóth: relajación es ley de potencia ≈0,4, no exponencial) | reportar las tres escalas; declarar cuál dispara; sensibilidad cruzada |
| **Fuerza** (2ª aprox.) | presión direccional neta en `t2` | delta agresor acumulado + intensidad de ticks (hoy); OFI multinivel (Fase 4, L2) | imbalance de tick/volumen en ventana de eventos | tamaño de vela; «volumen alto» sin signo; cualquier cosa endógena no condicionada (Xu: la fuerza depende del estado del libro) | condicionar por spread/estado; la fuerza debe predecir en pseudozonas **menos** que en reales, si no es momentum genérico |
| **Acceso** | primer trade dentro de `[L,U]` | evento de trade con precio ∈ `[L,U]` | — | cruce del mid; toque de bid/ask sin trade | consistencia con G0.4: un limit tocado NO es fill; lo mismo para «acceso» |
| **Penetración / travesía** | `d < 0` y salida por borde lejano | `max_penetration_ticks`, `Y_pen_k` | — | travesía en familias de altura 1 tick (degenerada, ya declarado) | declarar no medible donde colapsa (v2 §4.4) |
| **Régimen / contexto** | estado agregado que modula la dinámica | volatilidad local, hora CT, sesión, día; signo GEX (Fase 4) | clusters de volatilidad | cualquier régimen definido con información posterior al landmark | estabilidad temporal del etiquetado; purge/embargo |

### 2.3 La estructura (qué se construye, en qué orden lógico)

La máquina de estados de v2 §4.3 **es** la estructura; v3 le cuelga a cada transición su spec de medición y su chequeo de la tabla 2.2. La arquitectura física queda:

```
edgelab/research/z2a/
  zone_panel.py   panel (zone_id, evento): d firmada en ticks, lado, ancho, edad propia  [defectos 1-5]
  states.py       máquina de estados con umbrales inyectados; test de no-futuro           [defecto 6: reloj de eventos, no ticks crudos]
  census.py       Q-POBLACIÓN outcome-free por (familia × activo × sesión × config)       [mata variantes baratas, §3.4]
  landmark.py     una fila por (zone_id, t2); censura en s+v                              [estimand landmark]
  nulls.py        wrapper del generador F1.1, semilla nueva declarada                     [no reinventar]
  clocks.py       relojes: calendario, eventos, volumen, directional-change(δ)            [nuevo en v3]
  validity.py     chequeos de la tabla 2.2 como tests ejecutables                         [nuevo en v3]
```

`validity.py` es la respuesta directa al mandato 2: cada fila de la tabla 2.2 se convierte en **un test que corre sobre los datos** (no un párrafo). Ejemplos: el test del near-miss recomputa eventos con `δ_nm ± 1`; el test de aproximación corre la permutación por bloques; el test de acceso verifica que ningún evento se derive del mid.

Reglas de construcción heredadas (v2): `census.py`, `states.py` y `validity.py` **no importan nada que lea** `outcome`/`mfe_ticks`/`mae_ticks`/P&L; test de ceguera que falla si esas columnas se tocan (condición 1 de HP-003, por código).

---

## Parte 3 — El plan integral

### 3.1 Diccionario de variables (todas, con unidad, reloj, fuente y estado)

| variable | rol | unidad | reloj | fuente hoy | estado |
|---|---|---|---|---|---|
| `zone_id`, `config_id`, familia, lado | exposición | — | — | store de zonas (paridad) | disponible (B) / bloqueado (A) |
| `L`, `U`, `width_ticks` | exposición | ticks | — | zona congelada `available_at` | disponible |
| `d_t` firmada | eje del evento | ticks | eventos | `zone_panel` (a construir) | **defecto 1-3, bloqueante** |
| `D_far`, `δ_nm`, `R_min` | umbrales | ticks | — | manifiesto (auditor, pre-censo) | a fijar |
| `d_min`, `rejection_depth` | historia (M2) | ticks | directional-change | derivado del panel | tras panel |
| `reset_len` ×3 | historia (M2) | ms / eventos / volumen | triple | derivado | tras panel |
| `vel_t2`, `accel_t2` | estado (M0) | ticks/evento | eventos | parquets F2 + `bars.py` | disponible |
| retorno en reloj de volumen | estado (M0) | % | volumen | F2 | disponible |
| `intensity`, `volumen` | estado (M0) | trades/ventana, contratos | eventos/volumen | F2 | disponible |
| `spread_t2` | estado (M0) | ticks | eventos | quotes si existen; si no, **declarado faltante** | verificar |
| volatilidad local | estado (M0) | ticks | calendario+eventos | F2 | disponible |
| hora CT, sesión, contrato, día | contexto | — | calendario | `sessions.py` | disponible |
| edad propia de zona | zona (M1) | barras/eventos | eventos | panel | **defecto 5** |
| `active_zone_count`, dist. a 2ª zona | confluencia (M1) | #, ticks | eventos | panel | tras panel |
| delta agresor entre episodios | historia (M2) | contratos firmados | eventos | F2 (tick rule) | disponible, proxy declarado |
| `cause_code` 0–5, `time_to_event` | outcome | — | eventos+calendario | derivado post-manifiesto | **vedado hasta F4 aprobado** |
| OFI multinivel, colas, microprice, adds/cancels, iceberg proxies | mecanismo (M3) | varios | eventos | L2/MBO | **no disponible — Fase 4** |
| GEX: signo, call wall, put wall, flip | régimen + zonas exógenas | $/strikes | diario | proveedor externo | **no disponible — Fase 4** |

### 3.2 Relojes de medición (mandato 3 explícito)

| reloj | definición | para qué se usa en H-Z2A | fuente |
|---|---|---|---|
| calendario | ms/barras fijas | contexto, sesiones, horarios, vida de zona | Ané-Geman: sabido insuficiente solo |
| ticks / eventos | cada trade (o cada N) | `d_t`, intensidad, estados | Ané & Geman 2000 |
| volumen | cada V contratos | reset por volumen, retorno volumétrico | Easley-LdP-O'Hara 2012 |
| directional-change(δ) | cada reversa de δ ticks | **rechazo, aproximación, near-miss (reloj nativo)** | Guillaume 1997; Glattfelder 2011 |
| imbalance/run bars | cada cambio de desequilibrio / racha | fuerza y segunda aproximación | LdP AFML cap. 2 |

Regla: todo estimando se reporta en calendario + eventos + directional-change como mínimo. Sensibilidad entre relojes es obligatoria (G2, ±1 paso aplica también al δ del reloj).

### 3.3 Métodos por pregunta

1. **Q-POBLACIÓN** — censo outcome-free (`census.py`): conteos de elegibles por cada celda (familia × activo × sesión × config × reloj). Umbrales de potencia de v2 §8 **a nivel variante**: `N < 403` ⇒ esa variante muere barata; `≥ 1.566` ⇒ testeable a 5 pp. **Aquí es donde la opinión de Nico se vuelve procedimiento**: el censo mapea el espacio de alta dimensionalidad y mata brazos sin gastar un outcome.
2. **Q-DINÁMICA** — landmark en `t2` (van Houwelingen–Putter), hazards **cause-specific** + CIF Aalen–Johansen (heredado de F1.2, sin Fine–Gray múltiple), escalera M0→M2 con matriz interpretativa preregistrada, métricas log-loss/Brier/calibración, selección dentro del fold y evaluación fuera.
3. **Q-ECONÓMICA** — recorrido vs `spread + slippage + comisión` (W7: falta comisión real), fills admisibles bajo G0.4, sin limit-fills optimistas (literatura: ~99,9 % de límites se cancelan).
4. **Validación transversal** — nulos F1.1 (A/B/C, semilla nueva), permutación por bloques, bootstrap estacionario por sesión, walk-forward **por contrato**, DSR con `N_eff` declarado, PBO ≤ 0,50 (CSCV S=8), instrumentos separados antes de poolear.

### 3.4 El espacio de variantes y su presupuesto (integración de la opinión de Nico, 19:35)

Ejes del espacio (verbatim de Nico entre paréntesis): activos («muchos activos»), familias/indicadores («muchos indicadores», hoy 6 con paridad), definición del cluster («densidad de indicadores, direcciones, configuraciones, parámetros»), umbrales (`D_far`, `δ_nm`, `R_min`, `v`), fuerza, relojes («ticks, tiempo, etc»), contexto («sesiones, horarios»), outcomes.

Reglas preregistradas:

- **Presupuesto `N_eff` por eje**, escrito en el manifiesto antes de correr. Orden de magnitud: 3–5 valores por eje, una configuración central + sensibilidad ±1; el producto cartesiano completo queda **explícitamente prohibido** (v2: 11.664 combinaciones = lo que NO se hace).
- **El censo recorre el espacio; el test no.** El censo es outcome-free: puede reportar `N` por celda para todo el espacio sin gastar multiplicidad. Las celdas con `N` suficiente y motivo teórico pasan a manifiesto; el resto muere **como variante**, sin tocar el core.
- **Core vs variante**: el core de H-Z2A (la historia near-miss→rechazo→reset agrega sobre atracción + estado) muere sólo por la matriz M0/M1/M2 fuera de muestra, por equivalencia con pseudozonas, o por economía. Ningún `N` chico mata el core: mata la celda.
- Todo eje agregado después (GEX, L2, una familia nueva) = **campaña nueva** que hereda el presupuesto acumulado.

### 3.5 Fases con condiciones de entrada y salida

| fase | contenido | entrada | salida / kill |
|---|---|---|---|
| **0** | manifiesto de umbrales hasheado (auditor, antes del censo) | Nico aprueba scope | STOP si Nico no aprueba |
| **1** | `zone_panel` + `states` + `clocks` + `validity` sobre **BigTrap2 (B, fixture)** | aprobación de fase 0 | tests de no-futuro y validez verdes; si fallan, muere la instrumentación, no la hipótesis |
| **2** | censo outcome-free sobre el espacio (B para instrumentación + conteo por celdas) | fase 1 verde | celdas con `N<403` mueren como variantes; si TODAS las celdas razonables mueren, se reporta y el core queda **no testeable hoy** (no falsificado) |
| **3** | Q-DINÁMICA en la familia elegida (recomendación v2: A cuando se desbloquee) | censo con ≥1 celda viable + manifiesto F4 aprobado por Nico | matriz M0/M1/M2; kill por equivalencia con nulos o por no-superación |
| **4** | Q-ECONÓMICA (fricción, fills) | lift OOS estable | muere si el neto no paga fricción en base |
| **5** | M3: L2/MBO + GEX (gate de datos propio) | Nico aprueba adquisición | adjudica mecanismo (agotamiento vs refuerzo); recuerdo: F1.3 ya apunta contra agotamiento |

### 3.6 Lo que ya se sabe (restricciones duras que el plan hereda)

- Atracción probada, resistencia no (F1.1: +47,07 pp tocar; +0,54 pp romper) ⇒ H-Z2A no vuelve a preguntar «¿la zona informa?».
- La ruptura **cae** con los toques previos (F1.3: 30,3 % → 16,7 %) ⇒ «agotamiento» escrito sin L2 se marca como error.
- Fricción medida −2,7680 ticks (H1) + altura mediana 1 tick ⇒ margen estructuralmente hostil; entrada pasiva dentro de la zona, descartada.
- Cobertura 99,31 % ⇒ todo evento es contra una zona **específica con `zone_id`**, nunca «la más cercana».
- Nulos apareados listos (F1.1) con semilla publicada ⇒ se reusan.
- 6 defectos de `features.py` ⇒ `zone_panel.py` nuevo; no se patchea la API vieja para esto.
- aVolClusterPOI sin kernel/paridad, EventLog con outcomes, QualityScore congelado, F9 pausada ⇒ A requiere desbloqueo que decide Nico.
- Hash drift NORTH_STAR (`21bb3b01…` en F1.x vs `d85364e2…` vigente) ⇒ los manifiestos citan el vigente y anotan la diferencia.

### 3.7 Decisiones pendientes de Nico

1. Portador Fase A: **B (fixture) + A (hipótesis)** recomendado; C (Gaps2) como control mecánico.
2. GEX y L2: cuándo entra Fase 5 (adquisición de datos, gate propio).
3. Comisión real del bróker (W7) — sin eso no hay afirmación neta.
4. Aprobación del manifiesto de umbrales (Fase 0) cuando lo presente el auditor.

---

## Firewalls

```
outcomes_accessed     = false
pnl_accessed          = false
holdout_included      = false
multiplicidad_gastada = 0
F4_autorizado         = false
estado                = HYPOTHESIS_DEFINED_NOT_RUN
```

---

## Fuentes

**Internas**: v2 (`H_Z2A_V2_OPERACIONALIZACION_2026-08-16.md`, commit `901ca82a…`) y todo su aparato (F1.1, F1.2/F1.3, F0.3, sesgo de diseño, HP-003, `features.py` blob `98f9034c…`, NORTH_STAR, contrato de validación).

**Externas (nuevas en v3)**
- Osler, *Currency Orders and Exchange-Rate Dynamics*, Journal of Finance 58(5), 2003 (FRBNY SR-125): clustering de stop-loss/take-profit; reversión en S/R y aceleración post-cruce. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf
- Osler, *Stop-Loss Orders and Price Cascades in Currency Markets*, JIMF 24(2), 2005: ejecución en olas, respuesta mayor y más duradera. https://www.sciencedirect.com/science/article/abs/pii/S0261560604001147
- Kavajecz & Odders-White, *Technical Analysis and Liquidity Provision*, RFS 17(4), 2004: S/R coinciden con picos de profundidad del libro. https://academic.oup.com/rfs/article-pdf/17/4/1043/24435929/hhg057.pdf
- Cho, Russell, Tiao & Tsay, *The Magnet Effect of Price Limits*, JEF 10(1-2), 2003: aceleración hacia el límite. https://www.sciencedirect.com/science/article/abs/pii/S0927539802000245
- Lo, Mamaysky & Wang, *Foundations of Technical Analysis*, JoF 55(4), 2000 (NBER w7613): patrones formales por kernel; información incremental. https://www.nber.org/system/files/working_papers/w7613/w7613.pdf
- Ané & Geman, *Order Flow, Transaction Clock, and Normality of Asset Returns*, JoF 55(5), 2000. https://onlinelibrary.wiley.com/doi/pdf/10.1111/0022-1082.00286
- Easley, López de Prado & O'Hara, *The Volume Clock*, JPM 39(1), 2012. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2034858
- Guillaume et al. 1997; Glattfelder, Dupuis & Olsen, *Patterns in high-frequency FX data: 12 scaling laws*, Quantitative Finance 11(4), 2011; Glattfelder & Olsen, *The Theory of Intrinsic Time: A Primer*, arXiv:2406.07354, 2024. https://arxiv.org/abs/2406.07354
- López de Prado, *Advances in Financial Machine Learning*, cap. 2 (tick/volume/dollar, imbalance y run bars).
- Market Profile / AMT (Steidlmayer; síntesis: poor highs/lows, excess, failed auction, regla 80 %): https://nexusfi.com/a/market-structure/auction-market-theory · https://tradebrigade.co/poor-high-poor-low/
- Wyckoff (spring, secondary test, SOS, LPS; calidad del test por volumen/spread): https://www.wyckoffanalytics.com/wyckoff-method/
- GEX / dealer hedging (pinning, call/put walls, gamma flip; base: Avellaneda & Lipkin 2003): https://spotgamma.com/max-pain-options-explained/ · https://menthorq.com/guide/what-is-gamma-pinning/

**Externas (heredadas de v2, siguen vigentes)**: Osler 2000 FRBNY; van Houwelingen & Putter (landmarking); Putter et al. JRSS-A 2024 (Fine–Gray múltiple); Xu et al. arXiv:1602.00731 (resiliencia LOB); Lo & Hall 2015; Fishe-Haynes-Onur 2022; Tóth-Kertész-Farmer 2009 (arXiv:0901.0495); Degryse et al. 2005; Christensen & Woodmansey 2013; Zotikov 2019; Goliath & Gebbie arXiv:2602.19590; Cont-Kukanov-Stoikov; Gould & Bonart; Bouchaud et al.

---

## Aporte al referente

v1 escribió la narrativa; v2 la ancló al repo y le dio censo, estimand y muerte barata; **v3 le da genealogía y física**: el fenómeno resulta estar estudiado por separado en cuatro tradiciones (microestructura de órdenes, libro límite, tiempo intrínseco y práctica estructurada), y H-Z2A queda identificada como la hipótesis que **las conecta y las separa**: es exactamente el caso que distingue la predicción de Osler (los niveles revierten Y aceleran) de la del Market Profile (el retorno al excess falla 80 %). Además, el mandato de validez de Nico quedó convertido en una tabla constructo→observable→estimador→chequeo y en un módulo ejecutable (`validity.py`), y el plan fija cinco relojes de medición con sensibilidad obligatoria entre ellos.