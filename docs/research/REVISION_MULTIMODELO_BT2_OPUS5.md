# Revision multimodelo de BigTrap2 — pasada 1: Claude Opus 5

**Fecha**: 2026-08-22 · **Rol**: auditor (pre-registro) · **Modelo**: Claude Opus 5
**Pasada previa**: Grok 4.6 (sin acta escrita) · **Pasadas siguientes**: GPT, Kimi K3
**Rama**: `foundation/f0b-compatibility-probe` · **Tip al revisar**: `e9b6422`
**Alcance**: definicion del evento del indicador. NO se reabre H-GC-BT2-1 (holdout gastado).

---

## 0. Regla de la revision multimodelo

Cada modelo responde **las mismas 7 preguntas** en su propia seccion y **no edita las de los
otros**. Al final se comparan respuesta contra respuesta. Un modelo que cambie de tema o que
no conteste una pregunta cuenta como no-respuesta, no como acuerdo.

Las 7 preguntas:

1. Que es hoy el evento, **operativamente** (no que dice el nombre).
2. Que evidencia del repo lo respalda o lo refuta, con numeros.
3. Fortalezas reales.
4. Debilidades reales.
5. La barrera economica: cuanto hace falta y cuanto hay.
6. Corresponde cambiar el indicador. Que exactamente.
7. Con que prueba **falsable y pre-registrada** se decide.

---

## 1. Pasada Claude Opus 5

### Q1 — Que es hoy el evento, operativamente

El kernel BigTrap2 corta el tape en cubetas de N ticks, arma un footprint por fila de precio y
marca una fila como desbalanceada si

```
ratio = agresivo / max(opuesto, 1)  >=  ImbalanceRatio
```

El `max(opuesto, 1)` **no es un piso de seguridad: es la definicion efectiva del evento**. Cuando
la celda opuesta esta vacia — que es el caso normal en una cubeta de 25 ticks — el cociente
degenera en el conteo absoluto. Con `ImbalanceRatio = 3` el evento real es:

> "tres contratos al ask y nada abajo".

No es una hipotesis de lectura de codigo. Los datos lo confirman en
`diag/tasa_senales/h_gc_bt2x_oracle_inspect.json`: el minimo observado de `trap_vol` es
**exactamente 3** y el minimo de `trap_ratio` es **exactamente 3**. Coinciden porque son la misma
cosa.

### Q2 — Evidencia del repo

GC DEC26, 17–21 ago 2026 (`oracle_events__Tick25.csv`, 36.584 lineas):

| magnitud | valor |
|---|---|
| `BARRA_PROCESADA` | 24.093 |
| `TRAP` | **11.964 = 49,7 % de las cubetas** |
| reparto | 6.126 sellers / 5.838 buyers (51/49) |
| `trap_vol` p25/p50/p75 | **3 / 4 / 7** (max 144) |
| `trap_ratio` p25/p50/p75 | 3 / 4 / 5 (max 99) |
| `trap_nrows` p25/p50/p75 | **1 / 1 / 1** (max 4) |
| `ZONE_CREATED` (vol>=30) | 122 = **1,02 %** |

Un evento que ocurre en la mitad de las cubetas y cuyo tamano mediano es **4 contratos en una
sola fila** no es un evento: es el tape. Y el corte que si discrimina (`MinTrapVolume=30`) deja
122 casos en 5 dias, que es N insuficiente para cualquier cosa.

Caminos (`h_gc_bt2x_path_overfit.json`, horizonte 2000 ticks / 900 s, 11.962 caminos):

| subconjunto | n | MFE p50 | MAE p50 | RR p50 |
|---|---|---|---|---|
| todos | 11.962 | 38 | 36 | 0,96 |
| `vol>=30` (los de zona) | 122 | 40 | 39 | — |

Y en medias, el subconjunto "fuerte" es **peor**: MAE medio 48,58 contra MFE medio 46,41. El
filtro de volumen absoluto no selecciona, **empeora**.

Control que ya existia y que nadie deberia saltear: F2.9 midio que la **vela extrema generica
`S1` = +0,038** supera al creador BigTrap2 **`K0` = +0,021**, y que `K0` es indistinguible de la
no-creadora emparejada `N0`. Traducido: el kernel hoy **no aporta nada por encima de "vela
extrema"**.

### Q3 — Fortalezas reales

1. **La infraestructura es solida y es lo caro.** Subserie de 1 tick, corte propio, misma zona en
   cualquier tickframe, fill al tick siguiente sin look-ahead, log de eventos reproducible,
   paridad `.cs` <-> kernel Python verificable con `tools/check_nt8_cs.py`. Nada de esto hay que
   rehacerlo.
2. **La clasificacion de agresor es correcta**: bid/ask primero, tick rule solo como respaldo. El
   tick rule solo acierta ~77 % (Pascual/Chakrabarty/Shkilko, JFM 2015); usarlo como fallback y
   contar `n_quote`/`n_rule` en el export es la practica correcta.
3. **El muestreo por cubetas de tape** esta alineado con la literatura de information-driven bars
   (Lopez de Prado, *AFML* cap. 2; Easley–Lopez de Prado–O'Hara, *The Volume Clock*): muestrear
   por actividad y no por reloj da series con mejores propiedades estadisticas.
4. **Hay una asimetria medida, chica pero real.** Con SL 13 / TP 30 sin BE: sin deriva
   P(TP)=13/43=30,2 %; observado 3.775/11.829 = **31,9 %**. Son +1,7 pp reales, +0,72 ticks
   brutos. Es poco, pero no es cero.
5. **La honestidad del repo es una fortaleza tecnica.** `EDGES_DISCOVERED.md` no tiene ni un edge
   promovido y si tiene tres hipotesis refutadas con acta. Eso es lo que permite que esta
   revision valga algo.

### Q4 — Debilidades reales

1. **El evento no esta definido, esta implicito.** El umbral operativo es un artefacto del
   `ratio_floor`, no una decision. Nadie eligio "3 contratos".
2. **No es escala-libre.** Un umbral en contratos depende del instrumento, del contrato, de la
   hora y del regimen de volumen. El mismo `.cs` en NQ y en GC mide cosas distintas.
3. **`TapeWindowTicks` es `const`** en `BigTrap2UniversalFill`. La perilla que mas cambia el
   evento no es un parametro. (Corregido en el indicador nuevo.)
4. **Una celda aislada es ruido.** `trap_nrows` p50 = 1. La literatura de order flow (p. ej.
   OrderflowLabs) es explicita: el patron son **imbalances apilados**, no una celda suelta.
5. **El filtro de volumen absoluto no discrimina, y en la cola empeora** (MAE medio > MFE medio en
   `vol>=30`).
6. **Falta la variable que la literatura si valida.** Cont–Kukanov–Stoikov (*JFEc* 2014, 12(1):47-88)
   muestran que el desplazamiento de precio es aproximadamente **lineal en el Order Flow
   Imbalance**, con pendiente inversa a la profundidad, y que la relacion con el **volumen** es
   "noisy and less robust". BigTrap2 mide volumen desbalanceado; **no** mide OFI ni desplazamiento.
7. **Ninguna definicion de absorcion de la practica coincide con la del indicador.** Las
   implementaciones que se usan afuera combinan tres cosas: z-score de volumen **+** desbalance de
   tomadores **+ impacto de precio bajo**. BigTrap2 tiene la segunda, a medias, y no tiene la
   tercera, que es justamente la que define "absorcion".

### Q5 — La barrera economica

GC: 1 tick = **10 USD**. Friccion asumida en el repo: **1,5 ticks = 15 USD** ida y vuelta.

Para un camino sin deriva, cualquier par (SL, TP) cumple `P(TP) = SL / (SL + TP)` y el EV bruto es
**cero por construccion**. Por eso el barrido de 960 celdas no corona nada: no puede.

Lo unico que importa es **cuanta deriva hay por encima de esa linea**:

| concepto | valor |
|---|---|
| mejor celda medida (SL 13 / TP 30) | 31,9 % de aciertos |
| lo que daria un camino sin deriva | 30,2 % |
| exceso medido | **+1,7 pp** = +0,72 ticks brutos |
| lo necesario para netear **+1 tick** | 36,1 % = **+5,8 pp** |
| factor faltante | **~3,4x** |

**Conclusion Q5**: el indicador actual esta a un tercio de la vara, y la brecha no se cierra
tocando SL/TP/BE — el barrido ya demostro que ahi no hay nada. Se cierra **solo si el evento
selecciona mejor**.

### Q6 — Corresponde cambiar el indicador. Que exactamente

**Si, corresponde. Pero no donde se venia mirando.** No es la posicion de la bolita, no es el
SL/TP, no es el tickframe. Es **la definicion del evento**.

Propuesta: **absorcion = flujo alto con desplazamiento bajo**. Es decir, el residuo atipico de la
relacion OFI -> Delta precio que Cont–Kukanov–Stoikov muestran que es estable y lineal. Si el
flujo firmado fue grande y el precio no se movio, alguien lo absorbio. Eso **si** es absorcion.

```
dFav  = sign(flujo_firmado) * (close - open)   en ticks
A     = |flujo_firmado| / (1 + max(0, dFav))
dispara si A >= percentil q de las ultimas L cubetas   (percentil CAUSAL)
```

Por que este cambio y no otro:

| propiedad | efecto |
|---|---|
| escala-libre | mata el artefacto de los "3 contratos" **por construccion** |
| percentil rodante | la tasa de disparo la fija `q`, no el instrumento ni la hora |
| score continuo | permite ordenar eventos y medir monotonia, no solo pasa/no pasa |
| N controlable | con q=90 hay ~2.400 eventos donde antes habia 122 |
| respaldo externo | es la unica pieza con literatura revisada detras |

Mas dos endurecimientos que el usuario pidio como **parametro** y no como constante nueva:

- **`MinStackedRows`** (default 2): exige filas desbalanceadas **contiguas**. Mata la celda suelta.
- **`MinTrapFrac`** (default 0,20): el trap tiene que ser una **fraccion** del volumen de la
  cubeta. Reemplaza `MinTrapVolume` absoluto, que se deja en 0 (apagado).
- **`TapeWindowTicks`** pasa a ser parametro real (era `const 25`).

Implementado en **`nt8/BigTrap2Absorption.cs` v1.0**. Decision de diseno importante: el evento
`TRAP` se exporta **siempre** que haya geometria, con `a_score`, `a_thr`, `a_pass`, `trap_frac`,
`signed_flow`, `d_ticks` y el agregado del kernel viejo. Una sola corrida deja barrer `q`,
`MinStackedRows` y `MinTrapFrac` **offline**, y reproducir el kernel viejo exactamente desde el
mismo archivo. No hace falta recomputar el indicador por cada configuracion.

### Q7 — Prueba falsable y pre-registrada

Se corre en **discovery: GC 08-26, 24–30 junio** (`56f7d1c4...`, 1.081.633 ticks). El holdout de
agosto **no se toca**: ya se gasto en H-GC-BT2-1.

**Puerta 1 — romper la simetria.** Hoy MFE p50 = 38 y MAE p50 = 36 para *todos* los eventos. Si el
decil superior de `a_score` **no** rompe esa simetria (criterio: MFE p50 / MAE p50 >= 1,25 con
n >= 200 eventos y >= 10 sesiones), la hipotesis de absorcion **se corta ahi**. No se pasa a
buscar SL/TP.

**Puerta 2 — batir el control, no el cero.** El benchmark no es 0: es **`S1` = +0,038** de F2.9
(vela extrema generica). Si el evento nuevo no supera a `S1` con intervalo de confianza que no lo
toque, es una forma cara de detectar una vela grande.

**Puerta 3 — la vara economica.** Bruto necesario **>= 2,5 ticks** (friccion 1,5 + 1 de margen).
Hoy hay 0,72. Si el mejor par (SL, TP) sobre el decil superior no llega a 2,5 brutos, no hay
negocio, haya o no significancia estadistica.

Orden de ejecucion: Puerta 1 -> Puerta 2 -> Puerta 3. Fallar cualquiera cierra la linea y se
escribe el acta de refutacion en `EDGES_DISCOVERED.md`.

### Lo que NO hay que hacer

- No reabrir H-GC-BT2-1. El holdout esta gastado (16/16 no pagan).
- No coronar 15t / SL5 / TP55 del barrido: n = 55, es una celda de 960 y no es un edge.
- No tunear con la L2 hasta cerrar el join de junio. El join actual es **3 de 20.486**.
- No usar `SizeScaling` ni `TopPercentFilter` para decidir nada: son look-ahead.
- No medir contra cero. El control es `S1`.

### Literatura consultada en esta pasada

- Cont, Kukanov, Stoikov — *The Price Impact of Order Book Events*, Journal of Financial
  Econometrics 2014, 12(1):47-88 (arXiv 1011.6402). Delta precio ~ OFI / profundidad; lineal;
  la relacion con volumen es "noisy and less robust".
- Chakrabarty, Pascual, Shkilko — comparacion BVC / tick rule / Lee-Ready, Journal of Financial
  Markets 2015, 25:52-79. Tick rule ~77 % de acierto.
- Lopez de Prado — *Advances in Financial Machine Learning*, cap. 2 (imbalance / information-driven
  bars). Easley, Lopez de Prado, O'Hara — *The Volume Clock*.
- Contra-nota: MQL5 art. 23310 — las mejores propiedades estadisticas del muestreo **no** se
  transfieren automaticamente al resultado de la estrategia.
- Practica: definiciones operativas de absorcion que combinan z-score de volumen + desbalance de
  tomadores + **impacto relativo bajo**; y el criterio de **imbalances apilados** frente a la celda
  aislada.

### Veredicto de la pasada 1

**Cambiar la definicion del evento: SI.** Cambiar la bolita, el SL/TP o el tickframe: **NO**, ya se
midio y no esta ahi. Probabilidad subjetiva de que el cambio propuesto pase las tres puertas:
**baja**. Se propone igual porque es la primera version del evento que es **falsable, escala-libre
y con respaldo externo**, y porque el costo de medirlo es una corrida sobre datos que ya estan.

---

## 2. Pasada GPT

> Pendiente. Responder Q1–Q7 sin editar la seccion 1.

---

## 3. Pasada Kimi K3

> Pendiente. Responder Q1–Q7 sin editar las secciones 1 y 2.

---

## 4. Sintesis (se escribe recien con las tres pasadas cerradas)

| pregunta | Opus 5 | GPT | Kimi K3 | acuerdo |
|---|---|---|---|---|
| Q1 evento real | conteo absoluto disfrazado de ratio | | | |
| Q2 evidencia | 49,7 % de cubetas, vol p50 = 4, 1 fila | | | |
| Q3 fortaleza principal | infraestructura 1-tick + fill sin look-ahead | | | |
| Q4 debilidad principal | el evento no esta definido | | | |
| Q5 brecha economica | 0,72 de 2,5 ticks (~3,4x) | | | |
| Q6 cambio propuesto | absorcion = flujo / desplazamiento, percentil causal | | | |
| Q7 prueba | 3 puertas en discovery de junio | | | |

**Regla de cierre**: si los tres modelos coinciden en Q4 y en Q6, se implementa y se mide. Si
difieren en Q1, hay un problema de definicion y **eso** se resuelve antes que cualquier codigo.
