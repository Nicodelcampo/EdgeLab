# H-Z2A v2 — operacionalización, autocorrección y anclaje en EdgeLab

**Fecha** 2026-08-16 · **Origen** hipótesis de Nico (dinámica de segunda aproximación), iteración multimodelo pedida explícitamente
**Predecesor** `docs/research/H_Z2A_SEGUNDA_APROXIMACION_ZONA_2026-08-16.md` (blob `eff5e661c61485374397bb9fee45d8a304c6b172`, commit `7e5f341e85dbf37f6b5ca1dfc754406c8dd212ce`)
**Estado** `HYPOTHESIS_DEFINED_NOT_RUN` · **Outcomes** `false` · **P&L** `false` · **Holdout** intacto · **Multiplicidad gastada** cero
**NORTH_STAR** sha256 `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

> Este documento **no autoriza F4**. Define estimand, población, espacio de eventos, controles, presupuesto de multiplicidad y precondiciones de ingeniería. La corrida exige STOP y aprobación explícita de Nico.

---

## 0. Qué hizo esta pasada y por qué el resultado es distinto

La v1 se escribió sin leer la evidencia interna que el propio proyecto ya había producido sobre zonas. Esta pasada leyó el repositorio antes de razonar, y eso **cambió cuatro conclusiones de la v1**, no las decoró.

La v1 tenía razón en la estructura (dos incógnitas separables, landmark predictivo, nulos apareados, escalera de modelos). Se equivocó en tres cosas verificables y omitió una cuarta:

| # | v1 decía | corrección con evidencia |
|---|---|---|
| 1 | «empezar con `aVolClusterPOI OFF_PRICE`, es la familia lista» | **No está lista.** `HIPOTESIS_PENDIENTES.md` HP-003 (blob `0225746e798f96ff4629252d0ca441c72352d3f2`): *«PROTOTIPO DE INVESTIGACIÓN. No tiene kernel Python ni paridad»*; su EventLog **emite `ZONE_OUTCOME` con `outcome`/`mfe_ticks`/`mae_ticks`** ⇒ *«NO puede consumirse tal cual por ningún censo outcome-free»*; su `QualityScore` con pesos fijos `35/25/15/15/10` es una preselección congelada. Y `NORTH_STAR.md` tiene **F9 PAUSADA sellada por Nico**. |
| 2 | «agotamiento y refuerzo son dos mecanismos simétricos, ambos abiertos» | **Hay evidencia interna direccional, y va contra el agotamiento.** F1.3 (blob `4dba1fc4bb0bfdca8dac83a5616123cef25a74b5`): la tasa de ruptura **baja** con los toques previos, 30,3 % (ordinal 1) → 16,7 % (>10), factor 1,81×. Más toques ⇒ **menos** ruptura. La versión ingenua de «la barrera se consume» ya está en tensión con lo medido en casa. |
| 3 | «Q-ZONA está abierta: hay que probar si la zona informa» | **Parcialmente contestada para una familia.** F1.1 (blob `609c5b3f51ae4d468af6f64113ecaa262a066b85`): zona real tocada **97,9 %** vs nulo-B apareado **50,6 %**, brecha **+47,07 pp**, **201 de 201 sesiones**. Pero en **romper** la brecha es **0,54 pp** (40 % de sesiones). Conclusión textual del repo: *«BigTrap2 no identifica niveles que aguanten. Identifica niveles que el precio vuelve a visitar.»* |
| 4 | (omitido) | **No verificó si la población existe.** Con 15.947 zonas, **97,9 % tocadas**, **altura mediana 1 tick** y **vida mediana ~6 barras**, un *near-miss estricto* (llegar a ≤δ y **no** operar dentro) es un evento raro por construcción. El primer artefacto no puede ser un test: tiene que ser un **censo de elegibilidad**. |

**Consecuencia de método:** H-Z2A v2 ya no pregunta «¿la zona informa?». Pregunta algo más angosto y más fuerte:

> Dado que ya se sabe que ciertas zonas **atraen** al precio, ¿la historia `near-miss → rechazo → reset` agrega capacidad predictiva sobre **acceso y penetración** por encima de (a) la atracción ya medida, y (b) distancia, volatilidad, spread, régimen y fuerza actuales en el instante del segundo acercamiento?

---

## 1. Evidencia interna que H-Z2A hereda (y no puede volver a gastar)

### 1.1 La zona como estado ya está construida, y research casi no la usó

`docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md` (blob `523eed6ec53bc15abca4c3a782ffc028495b4daa`) documenta que toda la línea H1 se construyó sobre **primeros toques**, que el marco alternativo —zona como estado continuo— existía **trece días antes**, y que sus únicos consumidores eran su propio test y un demo.

**H-Z2A es exactamente el tipo de hipótesis que ese documento pedía y nadie escribió:** un espacio de eventos **sin toque** en el evento condicionante. El near-miss es, por definición, *no-toque*. Eso la vuelve la primera hipótesis del programa que ataca el sesgo declarado en vez de heredarlo.

La regla permanente que ese documento adoptó se cumple acá literalmente: enumerar por escrito el espacio de eventos, con alternativas y condición de refutación, **antes** de congelar población (§4, §7, §11).

### 1.2 Números que fijan el terreno

De F1.2/F1.3, F1.1, F0.2 y F0.3 (`d343733f5925c849ff51d6359a398d4896811078`):

```
zonas BigTrap2                     15.947      (34 censuradas)
tocadas alguna vez                 97,9 %
altura mediana                     1 tick
vida mediana                       ~6 barras
incidencia acumulada de ruptura    96,28 %     (close_through 0,9081 + gap 0,0547)
expira sin romper                  3,72 %
supervivencia  1 / 10 / 120 barras 0,8463 / 0,4303 / 0,1445
eventos de toque totales           48.768      (H1 midió sólo los primeros: 32 %)
tasa de ruptura en la misma barra  29,6 % global; 30,3 % ord.1; 31,9 % ord.2; 16,7 % >10
barras con >=1 zona activa         99,31 %     (254.323 barras, 201 sesiones)
precio dentro de alguna zona       7,95 %
distance_to_nearest                mediana 7,00 ticks, p90 27,36
active_zone_count                  mediana 7,6, p90 15, max 34
```

Tres lecturas obligatorias para H-Z2A:

1. **La altura mediana de 1 tick descalifica a BigTrap2 como portador semántico.** «Penetración de k ticks» y «travesía del borde lejano» son casi lo mismo en un objeto de 1 tick, y `Y_traverse` colapsa. BigTrap2 sirve como **fixture de ingeniería**, no como familia de la hipótesis.
2. **La cobertura del 99,31 % vuelve al «hay una zona de interés cerca» casi vacuo si no se condiciona.** El near-miss debe definirse contra una zona **específica y congelada**, con `zone_id`, no contra «la más cercana».
3. **La vida mediana de 6 barras acota la población.** La secuencia necesita que la zona sobreviva aproximación 1 + rechazo + reset + aproximación 2. Cota superior grosera: zonas con vida ≥ 10 barras = 43,03 % ⇒ **≈ 6.862 zonas** como techo, antes de exigir la geometría del near-miss estricto. El número real hay que **contarlo**.

### 1.3 El nulo apareado ya existe y no hay que inventarlo

F1.1 construyó, por cada zona real, dos (después tres) zonas nulas que **preservan sesión, barra de creación, altura y lado**, sorteando sólo el precio central, con semilla publicada `20260810`, y resolviendo la vida de la zona nula con **la misma regla del kernel**:

- **NULO-A**: barra uniforme en la sesión (confusor de distancia conocido de antemano).
- **NULO-B**: desplazamiento local `creación ± 180 barras` ⇒ distancia mediana 13 ticks (p10 2, p90 46).
- **NULO-C** (seguimiento): apareado por volumen de barra comparable ⇒ toca **menos** (47,9 %) que el nulo-B simple (50,8 %).
- **F1.1b**: incluso en el estrato de 0–2 ticks, el nulo-B toca **86,6 %** contra 97,9 % real. La brecha se achica y **no se cierra**.

H-Z2A **reusa este generador** con semilla nueva y declarada. Inventar otro nulo sería gastar multiplicidad y perder comparabilidad.

---

## 2. Evidencia externa nueva de esta pasada

La v1 citaba impacto, colas y resiliencia. Faltaban cuatro piezas que cambian el diseño:

### 2.1 Precedente directo de la pregunta, con nulo aleatorio

Carol Osler, *Support for Resistance: Technical Analysis and Intraday Exchange Rates* (FRBNY Economic Policy Review, jul-2000): usa niveles de soporte/resistencia **publicados por seis firmas** (1996–1998) contra cotizaciones de 1 minuto, y encuentra que el precio **rebota más después de tocar niveles publicados que después de tocar niveles generados al azar**, con poder predictivo que persiste días.

Importa por tres motivos: (a) la unidad medida es la **interrupción de tendencia**, o sea el rechazo, que es justo el evento condicionante de H-Z2A; (b) el diseño es exactamente el de F1.1 —real contra nivel aleatorio—, lo que valida la arquitectura de control que el repo ya usa; (c) el poder predictivo **varía por firma y por par**, es decir el efecto es específico del generador de niveles, que es la razón por la cual Q-ZONA no puede resolverse «para zonas en general».

### 2.2 El método correcto para el instante t2 tiene nombre y literatura

Lo que la v1 describió como «landmark predictivo» es **landmarking** (van Houwelingen; Putter): en el landmark `s` se arma un dataset **sólo con los sujetos en riesgo en s**, se congelan las covariables tiempo-dependientes en su valor en `s`, y se censura administrativamente en `s+v`. Se estima `P(T > t | T > s, Z(s))` con un modelo de supervivencia ordinario.

Consecuencias operativas: no hace falta un joint model; el sesgo por condicionar en «llegó a la segunda aproximación» se **declara** como parte del estimando (predicción condicional al estado, no efecto causal del rechazo); y se puede evaluar en **varios landmarks** para ver si el aporte de la historia decae con el tiempo desde el rechazo.

### 2.3 Riesgos competitivos: cause-specific, no Fine–Gray múltiple

El acceso a la zona compite con retirada sin toque, invalidación de la zona, cierre de sesión y borde de datos. La literatura (Austin; Putter; *«Why you should avoid using multiple Fine–Gray models»*, JRSS-A 2024) recomienda **hazards cause-specific por causa** y CIF por Aalen–Johansen; usar varios Fine–Gray en paralelo produce incidencias cuya suma puede exceder 1.

**Y el repo ya lo hizo así:** F1.2 estimó incidencia acumulada con **Aalen–Johansen**, sin `lifelines`, porque `CLAUDE.md` prohíbe dependencias pesadas nuevas. H-Z2A hereda ese estimador y esa restricción. Cero dependencias nuevas.

### 2.4 Escalas reales de reset, y por qué un umbral fijo está mal

- **Xu, Chen, Xiong, Zhang, Zhou, Stanley (2016/2017)**: spread y profundidad vuelven al promedio en **~20 actualizaciones de mejor límite**; el estímulo a nuevos límites es **asimétrico** cuando el spread inicial es 1 tick y persiste **3–5 minutos**; y —crítico para H-Z2A— las órdenes de mercado efectivas llegan **cuando el spread está bajo, la profundidad del mismo lado es alta y la del lado opuesto es baja**. Es decir: la «fuerza» de la segunda aproximación es **endógena al estado del libro**. Si no se condiciona por estado del libro, se mide selección, no información.
- **Lo y Hall**: el libro se repone de forma confiable sólo el **~40 %** de las veces; si se repone, la vida media es **~20 s**. El agotamiento no está garantizado ni siquiera cuando hubo consumo.
- **Tóth, Kertész y Farmer (2009)**: tras cambios grandes de precio, las medidas del libro relajan como **ley de potencia con exponente ≈0,4**, no exponencial. Un «reset» definido con un único umbral temporal es una mala aproximación: hay que preregistrar **varias escalas** (tiempo, eventos, volumen) y reportar sensibilidad.
- **Degryse et al.**: hay **persistencia fuerte en la sumisión de órdenes agresivas**, y ocurren cuando spreads y profundidades son bajos. Esto da plausibilidad a «la presión vuelve» sin necesidad de invocar la misma institución.

### 2.5 Lo que sigue siendo inobservable, y ahora con cita

- **Metaórdenes**: identificarlas requiere históricamente identificadores de trader/broker; el intento reciente de hacerlo con **datos públicos** (Goliath y Gebbie, 2026) usa clustering de estrategias, no reconstrucción. ⇒ `M` (metaorden/información) queda **latente**. Prohibido escribir «se recargaron inventarios» como dato.
- **Liquidez oculta en CME**: existe metodología específica —Christensen y Woodmansey (2013), *Prediction of Hidden Liquidity in the LOB of GLOBEX Futures*; y detección/predicción de icebergs CME vía **Kaplan–Meier sobre MBO** (Zotikov, 2019)—. Es implementable, pero exige **MBO**, no L2 agregado. Entra en M3, detrás de su propio gate.
- **Fills**: en libros reales **~99,9 % de las órdenes límite se cancelan**, **>90 % de las ejecuciones ocurren en los mejores precios** y las profundidades mayores a 1 tick aportan marginalmente. Coincide con G0.4 del contrato (*«un limit tocado NO es un fill»*) y **mata de entrada** cualquier diseño de entrada pasiva dentro de la zona.

---

## 3. Redacción canónica v2

> **H-Z2A-2.** Para una zona creada y congelada ex ante, con `zone_id` propio y `available_at` declarado, se observa una primera aproximación desde distancia que termina en **near-miss** (mínimo `0 < d_min ≤ δ_nm`, sin ningún trade dentro de la zona), seguida por **rechazo** (`d` aumenta al menos `R_min` antes de cualquier toque) y por un **reset observable** medido en escalas múltiples. En el primer **landmark** `t2` posterior al reset en que la distancia vuelve a caer y la fuerza cumple una regla preregistrada, se estima si esa historia aumenta el **hazard cause-specific** de acceso y de penetración, condicionando por distancia, ancho, edad, lado, volatilidad, spread, intensidad, régimen, hora y fuerza actuales. En paralelo se estima si el incremento es **específico de la familia de zonas** frente a pseudozonas apareadas. **Agotamiento** y **refuerzo** son mecanismos rivales; la evidencia interna disponible (F1.3) favorece hoy al refuerzo, y adjudicar entre ellos exige L2/MBO.

Tres preguntas, en este orden, y ninguna se saltea:

- **Q-POBLACIÓN** (nueva, primera): ¿existen suficientes eventos elegibles para detectar algo? Censo outcome-free.
- **Q-DINÁMICA**: ¿la historia agrega sobre estado actual + zona?
- **Q-ECONÓMICA**: ¿queda recorrido neto de fricción, con fills que el contrato admita?

---

## 4. Definición formal

### 4.1 Zona elegible

`Z_i = [L_i, U_i]` entra sólo si: nace en `t_z` con información ≤ `available_at_z`; bordes, lado, score, expiración e invalidación **congelados**; ninguna actualización retroactiva (cualquier cambio ⇒ otra versión con otro `config_id`); la primera interacción ocurre **estrictamente después** de `available_at_z`; e `integrity_state = api_verified` como mínimo (G0.6).

### 4.2 Distancia firmada, en ticks

`d_t` = ticks desde el precio transable al borde **próximo por el lado de aproximación**:

```
d_t > 0   fuera
d_t = 0   acceso   (exige TRADE dentro de [L,U]; cruzar con el mid no es acceso)
d_t < 0   penetración
```

La orientación se fija por el lado del que llega la primera aproximación y **no** se recalcula después.

### 4.3 Máquina de estados

```
ZONA_DISPONIBLE      zona viva, ex ante, virgen (sin trade dentro desde available_at)
  -> APROXIMACION_1  d cae desde >= D_far con actividad suficiente
  -> NEAR_MISS_1     min d = d_min, 0 < d_min <= delta_nm, cero trades dentro
  -> RECHAZO_1       antes de todo toque, d sube >= R_min desde d_min
  -> RESET           sin toque; separacion minima cumplida en las tres escalas
  -> APROXIMACION_2  primer instante post-reset con d decreciente y fuerza >= umbral
     = LANDMARK t2   <-- la prediccion nace ACA. Nada posterior entra a las covariables.
  -> OUTCOME         riesgos competitivos (4.4)
```

Reglas duras: **un evento elegible por `zone_id`** (el primero); zona completa en un solo fold; el toque superficial es hipótesis **separada** (v3), no una variante silenciosa.

### 4.4 Outcomes como riesgos competitivos

Código de causa (0 = censurado):

| código | causa | definición |
|---|---|---|
| 1 | `touch` | primer trade en `[L,U]` |
| 2 | `retreat` | `d` supera `D_far` otra vez sin toque |
| 3 | `zone_invalidated` | la zona muere por su propia regla sin ser tocada |
| 4 | `session_boundary` | cierre de sesión CME antes del desenlace |
| 5 | `data_edge` | borde de partición / hueco declarado |
| 0 | censura | horizonte `v` alcanzado sin causa |

Outcomes secundarios, sólo condicionales a `touch`: `Y_pen_k` (penetración de k ticks), `max_penetration`, `T_touch` en tiempo/eventos/volumen. `Y_traverse` **se declara no medible** en familias de altura mediana 1 tick.

### 4.5 Estimand

```
Delta_historia(z, x, v)
  = P(causa=1 antes de s+v | historia near-miss/reset, Z=z, X_t2=x, en riesgo en t2)
  - P(causa=1 antes de s+v | sin esa historia,        Z=z, X_t2=x, en riesgo en t2)
```

Es **predictivo condicional al landmark**. No es el efecto causal del rechazo: condicionar en que la segunda aproximación ocurrió abre un camino de colisión (`R1 → B → A2 ← M → Y`) que ningún ajuste con datos públicos cierra.

### 4.6 Grafo mínimo (sin cambios respecto de v1, ahora con roles de dato)

```
Z,C,M,L0 -> R1        Z zona (observada)   C regimen (observado)
R1,C,M   -> L1,B      M metaorden (LATENTE, no proxyable con datos publicos)
C,M,L1,B -> A2        L0,L1 liquidez (L2/MBO, no disponible hoy)
Z,C,M,L1,A2 -> Y      R1 rechazo, B reset, A2 segunda aproximacion, Y outcome
```

---

## 5. Escalera de modelos, con procedencia de cada feature

| modelo | bloque | features | de dónde salen hoy |
|---|---|---|---|
| **M0** | estado actual | `d_t2` (ticks, firmada), velocidad y aceleración orientadas en reloj de eventos, retorno en reloj de volumen, intensidad de ticks, volumen, `spread`, volatilidad local, hora CT, sesión, contrato | parquets F2 v1 + `bars.py`; hora/sesión por `sessions.py` |
| **M1** | + zona | familia, `config_id`, ancho en ticks, edad **de la zona propia** (no de la más cercana), lado, `active_zone_count`, distancia a la 2ª zona más cercana | `features.py::get_zones_df` + panel nuevo (§7) |
| **M2** | + historia | `d_min` del near-miss, profundidad del rechazo, duración del reset en las 3 escalas, tiempo desde `RECHAZO_1`, cambio de delta agresor entre episodios, nº de aproximaciones previas | derivable de M0/M1 con el panel por zona |
| **M3** | + mecanismo | OFI multinivel, queue imbalance, microprice, profundidad por nivel, adds/cancels/trades, half-life de reposición, proxies conservadores de iceberg | **no disponible**: exige L2/MBO con secuencia de exchange y su propio gate |

**Matriz interpretativa** (preregistrada, no se reinterpreta después):

- sólo M0 informa ⇒ primer pasaje / momentum genérico. H-Z2A **muere**.
- M1 > M0, M2 ≈ M1 ⇒ la zona aporta (consistente con F1.1), la historia no. H-Z2A **muere**, la atracción sobrevive.
- M2 > M1 también en pseudozonas ⇒ reaproximación genérica, no zona de interés. H-Z2A **muere como hipótesis de zona**.
- M2 > M1 sólo en zonas reales ⇒ **primera evidencia a favor de H-Z2A**.
- M3 coherente y con signo estable ⇒ apoyo observacional al mecanismo (no prueba causal).
- M3 muestra reposición en vez de depleción ⇒ el patrón sobrevive bajo **M-REFUERZO**, y la narrativa de Nico se cumple en el resultado pero **no en el mecanismo**.

Métricas: log-loss, Brier, **calibración** y CIF por Aalen–Johansen. AUC sola no alcanza y no es la métrica primaria. Métrica primaria única, declarada en el manifiesto, sin metric-shopping (regla anti-gaming del contrato).

---

## 6. Controles obligatorios

1. **Pseudozonas apareadas** con el generador de F1.1 (NULO-A distancia no controlada, NULO-B local ±180 barras, NULO-C apareado por volumen), semilla nueva publicada.
2. **Primera aproximación con estado actual equivalente** (mismo `d`, fuerza y volatilidad, sin historia previa).
3. **Segunda aproximación sin near-miss previo**.
4. **Near-miss sin reset** y **reset sin fuerza renovada** (descomponer la conjunción; si la conjunción entera es necesaria hay que mostrarlo, no asumirlo).
5. **Historia permutada por bloques** dentro de régimen y sesión.
6. **Apertura, roll, noticias y baja liquidez** excluidos o estratificados ex ante, nunca después de ver el resultado.
7. **Toques por ordinal** como control de consistencia contra F1.3: si H-Z2A afirma agotamiento, tiene que explicar por qué la ruptura **baja** con los toques previos.

---

## 7. Precondiciones de ingeniería: seis defectos concretos que hoy bloquean H-Z2A

Auditados sobre `edgelab/bridge/features.py` (blob `98f9034cfbb6b856c410b4accf75afeed3b97809`). La API de estado es la base correcta —y la que el documento del sesgo pedía usar— pero **no puede servir a H-Z2A sin extenderse**:

| # | defecto | evidencia en el código | impacto en H-Z2A |
|---|---|---|---|
| 1 | `tick_size` se declara y **nunca se usa** | firma `materialize_features(..., tick_size=None)`; el identificador no aparece en el cuerpo | `distance_to_nearest_zone` sale en **unidades de precio**, no en ticks. Todos los umbrales de H-Z2A (`D_far`, `δ_nm`, `R_min`, `k`) son en ticks. |
| 2 | distancia **sin signo** | `d = np.where(inside, 0.0, np.minimum(np.abs(p-at), np.abs(p-ab)))` | no hay lado de aproximación ni penetración negativa. `d_t` firmada es el objeto central de la hipótesis. |
| 3 | colapso a **la más cercana** | `k = int(np.argmin(d))`; no devuelve `zone_id` | la zona más cercana **cambia de barra a barra**; no existe trayectoria por zona. La máquina de estados necesita un panel por `zone_id`. |
| 4 | semánticas mezcladas en la misma fila | `inside_zone` es «alguna activa contiene al precio»; `distance`/`zone_age`/`nearest_side` son «de la más cercana» | un near-miss podría convivir con `inside_zone=True` de **otra** zona. Ambigüedad inaceptable en el evento condicionante. |
| 5 | `zone_age` con **sesgo de longitud** | documentado en F0.3 §2: mediana 54,3 barras contra vida mediana ~6 | como covariable de M1 hay que usar la edad de la **zona propia**, no de la más cercana. |
| 6 | bucle `O(n_barras × n_zonas)` en Python | `for i in range(n)` con máscara booleana sobre todas las zonas | 254.323 barras × hasta 34 activas es tolerable; **a nivel tick es inviable**. H-Z2A corre en barras / reloj de eventos, nunca sobre 1.015.587.419 ticks crudos. |

Detalle menor pero declarable: `active` usa `em > t` estricto, así que una zona que termina exactamente en `t` no cuenta; y `ended_ms` nulo se mapea a `inf`, o sea «sigue activa» ⇒ los landmarks sobre zonas aún vivas **tienen que censurarse**, no descartarse.

### Arquitectura propuesta (no implementada)

```
edgelab/research/z2a/
  zone_panel.py   panel por (zone_id, barra): d firmada en ticks, lado, ancho, edad propia
  states.py       maquina de estados 4.3, umbrales inyectados, cero futuro
  census.py       Q-POBLACION: conteos outcome-free, sin leer ningun outcome
  landmark.py     dataset de landmark: una fila por (zone_id, t2), censura en s+v
  nulls.py        wrapper del generador de F1.1 con semilla nueva
```

Regla dura de construcción: `census.py` y `states.py` **no importan nada que lea `outcome`, `mfe_ticks`, `mae_ticks` ni P&L**, y el lector se prueba ciego con un test que falla si esas columnas se tocan (la condición 1 de HP-003, resuelta por código y no por promesa).

### Esquema del dataset de landmark

```
zone_id, config_id, instrument, contract, session_date, bar_key
available_at_z, t_z, side, width_ticks, zone_age_own_bars, score_decomposed...
d_min_ticks, rejection_depth_ticks, reset_len_time, reset_len_events, reset_len_volume
t2_ms, d_t2_ticks, vel_t2, accel_t2, spread_t2, vol_t2, intensity_t2, delta_t2
horizon_v, cause_code (0..5), time_to_event, y_pen_k..., max_penetration_ticks
arm (real | null_a | null_b | null_c), fold_id, seed, north_star_sha256
outcomes_accessed=false, holdout_included=false
```

---

## 8. Q-POBLACIÓN: criterio numérico de factibilidad **antes** de cualquier test

Para un outcome binario con tasa base `p1`, detectar un lift `Δ` con α=0,05 bilateral y potencia 80 % requiere por brazo:

```
n = (1,96 + 0,8416)^2 * [p1(1-p1) + p2(1-p2)] / Δ^2 ,  p2 = p1 + Δ
```

Con `p1 = 0,30` (tasa de ruptura en la misma barra medida en F1.3, la referencia interna más cercana) y el **design effect 1,14** medido en H1:

| lift buscado | n IID por brazo | n corregido (×1,14) |
|---|---:|---:|
| Δ = 10 pp | 353 | **≈ 403** |
| Δ = 5 pp | 1.374 | **≈ 1.566** |
| Δ = 3 pp | 3.760 | **≈ 4.286** |

**Criterio de aceptación del censo, preregistrado:**

- `N_elegible ≥ 1.566` por brazo ⇒ H-Z2A es testeable a 5 pp. Se puede escribir el manifiesto F4.
- `403 ≤ N_elegible < 1.566` ⇒ testeable sólo a 10 pp. Se declara MDE grosero y se decide si vale.
- `N_elegible < 403` ⇒ **H-Z2A muere por potencia en esa familia**, sin gastar un solo outcome. Se registra y se busca otra familia o se relaja `δ_nm` **una sola vez**, cobrando la variante a `N_eff`.

Cota superior conocida para BigTrap2: **≈ 6.862 zonas** (43,03 % con vida ≥ 10 barras). El near-miss estricto es un subconjunto y hay que medirlo.

---

## 9. Dependencia, multiplicidad y mapeo a gates

### 9.1 Estructura de dependencia

Cluster primario `zone_id`; secundario sesión CME. Zona completa en un fold. **Purge/embargo** por vida de zona + horizonte `v`. Bootstrap por bloques de sesión (nunca filas IID). Walk-forward **por contrato**, como exige G2. Instrumentos separados antes de cualquier pooling.

### 9.2 Presupuesto `N_eff` declarado ex ante

Toda variante corrida se cobra, se promueva o no (regla del contrato). Declaración inicial:

| eje | variantes previstas |
|---|---:|
| familia de zona | 1 (la que Nico elija en §11) |
| `D_far` | 3 |
| `δ_nm` | 3 |
| `R_min` | 3 |
| escala de reset | 3 (tiempo, eventos, volumen) |
| umbral de fuerza | 3 |
| horizonte `v` | 2 |
| outcome primario | 2 (`touch`, `Y_pen_k`) |
| brazos de control | 4 (real + A + B + C) |
| modelos | 3 (M0, M1, M2) |

Producto cartesiano completo = **11.664 combinaciones**, que es exactamente lo que **no** se va a hacer. Diseño real: **una** configuración central preregistrada + sensibilidad ±1 paso en cada eje (regla de G2), con selección **dentro** de cada fold y evaluación fuera. `N_eff` declarado del orden de **20–30**, no de 11.664, y se escribe en el manifiesto **antes** de correr. Cualquier eje agregado después = campaña nueva que hereda el presupuesto acumulado.

### 9.3 Gates

| gate | qué exige a H-Z2A |
|---|---|
| **G0** | features as-of (`created_ms <= t`), `available_at` con ejecución **posterior**, `config_id`+`bar_spec` externos, `integrity_state = api_verified`, determinismo con mismo manifiesto |
| **pre-G1** | el censo de §8 es **target-free**: multiplicidad cero, holdout intacto, no promueve estado |
| **G1** | `n_trades ≥ 100`, neta base > 0, P&L sin top-5 > 0, ningún fold > 80 % |
| **G2** | bootstrap estacionario-t por sesión con `lower > 0`, `n_sessions ≥ 160`, PBO ≤ 0,50 (CSCV S=8, 70 particiones), **DSR ≥ 0,95 con el `N_eff` del manifiesto**, walk-forward por contrato, sensibilidad ±1 |
| **G3** | escenario base gate, adverso > −0,5 × base, costos desglosados por instrumento (W7 pendiente: falta comisión real de bróker) |
| **G4** | holdout `2026-07-01 → 2026-12-31`, frontera `min(sello, declarada)`, **una sola apertura** |
| **G5** | paridad research↔live ≥ 95 %, sizing ≤ 1 %, −3R/día, kill switch |

**Firewall**: toda carga de datos llama a `holdout_guard.check_holdout(..., purpose="development", caller="z2a.census")`. El censo es `development` pre-holdout ⇒ permitido sin log. Nada de H-Z2A entra como `target_free_validation` para colarse al holdout.

**Nota de trazabilidad**: F1.x y F0.x citan `NORTH_STAR` sha256 `21bb3b01a33e2b37…`; el cuerpo vigente hashea `d85364e2…`. El referente **cambió** desde que esos resultados se sellaron. Los manifiestos de H-Z2A citan el hash vigente, y la diferencia queda anotada para que nadie lea una discrepancia como fraude.

---

## 10. De información a operación (todavía no)

Dos estrategias posibles, ninguna elegida:

1. **Pre-touch continuation**: entrar en `t2`, objetivo borde/penetración.
2. **Post-penetration continuation**: esperar el cruce, buscar continuación.

Restricciones que ya están fijadas por el contrato y por la literatura:

- Sin limit fills optimistas: un limit tocado **no** es un fill (G0.4), y en libros reales las profundidades más allá de 1 tick aportan ejecución marginal. Entrada pasiva dentro de la zona: **descartada**.
- Fill estrictamente posterior a `available_at`; `ts == available_at` es inelegible.
- Ambigüedad intrabar ⇒ `stop_ambiguous` / STOP, nunca orden inventado.
- Escenario base es el único que decide.

Puede existir el fenómeno y **no** el edge: lift chico, recorrido menor que la fricción, cola inalcanzable, MAE que impide sizing. Con altura mediana 1 tick y `−2,7680` ticks de fricción medidos en H1, el margen es estructuralmente hostil: cualquier familia cuyo recorrido esperado sea de pocos ticks está muerta antes de empezar.

---

## 11. Bloqueo abierto: quién es el portador de la Fase A

La v1 dio por lista una familia que no lo está. Las opciones reales, con su costo:

**Opción A — `aVolClusterPOI OFF_PRICE` (semánticamente correcta, hoy bloqueada).** Es la única familia con **ancho real** (clusters de niveles contiguos), lo que vuelve medibles `δ_nm`, `k` y travesía. Precondiciones: (1) kernel Python + paridad NT8; (2) modo de export **sin columnas de outcome** o lector probadamente ciego; (3) `QualityScore` descompuesto o sus pesos como parámetros; (4) `AT_PRICE` excluido por ser ocupación, no nivel; (5) resolver la relación con **F9 pausada** —H-Z2A no es «un indicador nuevo», pero aVol tampoco está entre los 5 con paridad, así que esto lo decide Nico, no yo.

**Opción B — BigTrap2 como fixture de ingeniería (dato listo, semántica degenerada).** Store verificado, paridad hecha, 15.947 zonas, nulos ya construidos. Permite implementar y validar `zone_panel`/`states`/`census` **hoy**. Límites duros: altura mediana 1 tick ⇒ penetración y travesía degeneradas; y **no reabre H1 ni el imán**: el uso queda restringido a **conteos y validación de instrumentación**, prohibido publicar lift, hazard o cualquier afirmación de hipótesis sobre BigTrap2 desde este canal.

**Opción C — `Gaps2` o `VolTicksPOC2`.** Gaps2 tiene geometría mecánica y sirve como familia de control genuina; VolTicksPOC2 es candidato posterior. `HFTZones2` queda fuera por paridad pendiente y por riesgo de duplicar información (sería a la vez generador de zona y medida de fuerza).

**Recomendación del auditor:** **B para instrumentación + A para la hipótesis**, en ese orden y sin mezclar los resultados. Correr B primero cuesta poco, no gasta multiplicidad de la hipótesis y produce el censo que dice si H-Z2A es viable **antes** de invertir en desbloquear aVol.

---

## 12. Reparto de trabajo

**Claude Code (máquina de Nico, con datos):**
1. `zone_panel.py` con distancia **firmada en ticks** y panel por `zone_id`; tests contra `features.py` en el caso degenerado (una zona) para probar que no contradice la API existente.
2. `states.py` con la máquina de §4.3, umbrales inyectados, y un test de **no-futuro**: barajar el futuro no debe cambiar ni un estado.
3. `census.py` ⇒ `N_elegible` por brazo, por contrato y por sesión, con los tres criterios de §8. **Sin leer un solo outcome**, con test que lo prueba.
4. Reusar el generador de nulos de F1.1 con semilla nueva declarada.
5. Reportar el censo como artefacto JSON con digest, sin interpretar.

**Auditor (este canal, sin datos):**
1. Fijar los valores numéricos de `D_far`, `δ_nm`, `R_min`, escalas de reset, umbral de fuerza y `v` **antes** de ver el censo, en un manifiesto hasheado.
2. Escribir el manifiesto F4 completo (estimand, población, nulo, MDE, `N_eff`, grafo causal, hash de NORTH_STAR) y llevarlo al STOP.
3. Auditar que `census.py` es ciego a outcomes leyendo el código, no el reporte.
4. Mantener la corrección de F1.3 visible: si alguien escribe «agotamiento» sin L2, se marca.

**Nico:** elegir portador (§11), aprobar o rechazar el manifiesto, entregar la comisión real del bróker (W7 sigue incompleto y sin eso no hay afirmación neta).

---

## 13. Cómo se refuta H-Z2A-2

- **Muere por potencia** si `N_elegible < 403` por brazo.
- **Muere Q-DINÁMICA** si M2 no supera a M1 fuera de muestra, o si el aporte desaparece al igualar distancia y fuerza en `t2`, o si aparece igual en pseudozonas.
- **Muere el mecanismo de agotamiento** si L2 muestra reposición o refuerzo, o si la coherencia con F1.3 no se puede explicar.
- **Muere económicamente** si el lift existe pero el recorrido neto no paga `spread + slippage + comisión` en escenario base, o si el fill exigible no es admisible bajo G0.4.
- **Sólo es candidato a edge** tras lift OOS estable, aportes separados de zona e historia, neto base positivo, G2 con `N_eff` y no-IID, **una** apertura de holdout y réplica shadow.

---

## 14. Firewalls de este documento

```
outcomes_accessed   = false
pnl_accessed        = false
holdout_included    = false
multiplicidad_gastada = 0
F4_autorizado       = false
estado              = HYPOTHESIS_DEFINED_NOT_RUN
```

---

## Fuentes

**Internas** (mismo commit base `7e5f341e85dbf37f6b5ca1dfc754406c8dd212ce`): `docs/SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md` · `docs/F1.1_NULO_ZONAS_ALEATORIAS_RESULTADO_2026-08-10.md` · `docs/F1_SUPERVIVENCIA_DEPLECION_RESULTADO_2026-08-10.md` · `docs/F0.3_FEATURES_ESTADO_RESULTADO_2026-08-10.md` · `docs/HIPOTESIS_PENDIENTES.md` · `docs/NORTH_STAR.md` · `docs/edge_validation_contract.md` · `docs/event_identity_v2.md` · `edgelab/bridge/features.py` · `tools/avolcluster_census.py`

**Externas**
- Osler, *Support for Resistance: Technical Analysis and Intraday Exchange Rates*, FRBNY Economic Policy Review 6(2), 2000.
- van Houwelingen y Putter, *Dynamic Prediction in Clinical Survival Analysis*, 2011 (landmarking).
- Austin y Fine, *Practical recommendations for reporting Fine–Gray model analyses*; Putter et al., *Why you should avoid using multiple Fine–Gray models*, JRSS-A 187(3), 2024.
- Xu, Chen, Xiong, Zhang, Zhou y Stanley, *Limit-order book resiliency after effective market orders: spread, depth and intensity*, arXiv:1602.00731.
- Lo y Hall, *Resiliency of the Limit Order Book*, JEDC 2015.
- Fishe, Haynes y Onur, *Resiliency in the E-mini futures market*, JFM 42(1), 2022.
- Tóth, Kertész y Farmer, *Studies of the limit order book around large price changes*, EPJ B 71, 2009 (arXiv:0901.0495).
- Degryse et al., *Aggressive Orders and the Resiliency of a Limit Order Market*, Review of Finance 2005.
- Christensen y Woodmansey, *Prediction of Hidden Liquidity in the Limit Order Book of GLOBEX Futures*, Journal of Trading 8(3), 2013; Zotikov, *CME Iceberg Order Detection and Prediction*, 2019.
- Goliath y Gebbie, *Metaorder modelling and identification from public data*, arXiv:2602.19590.
- Cont, Kukanov y Stoikov, *The Price Impact of Order Book Events*; Gould y Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor*; Bouchaud et al., *Price Impact*.

---

## Aporte al referente

La pasada multimodelo convirtió una hipótesis narrativa en un objeto con población contable, estimand de landmark, riesgos competitivos, nulos ya existentes y un criterio numérico de muerte por potencia (`N < 403`) que puede matarla **antes** de gastar un outcome. Y corrigió tres afirmaciones propias con evidencia del repositorio: aVol no está lista, el agotamiento está en tensión con F1.3, y la pregunta «¿la zona informa?» ya tiene respuesta parcial (atracción sí, resistencia no). Además dejó seis defectos concretos de `features.py` documentados con su impacto, que era la pieza que el documento del sesgo de diseño pedía usar y nadie había ejercitado.