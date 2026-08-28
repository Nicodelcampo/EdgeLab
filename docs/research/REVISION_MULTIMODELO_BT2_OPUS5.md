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
- **`TapeWindowTicks`** pasa a ser parametro real (en Fill era `const 25`).

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

**Fecha**: 2026-08-22 · **Rol**: auditor (pre-registro) · **Modelo**: GPT
**Snapshot revisado**: `foundation/f0b-compatibility-probe` @ `06becaf`
**Alcance**: razonamiento + research. No se corrio NT8, no se abrieron parquets y no se
midieron outcomes nuevos.

**Dictamen adelantado**: el evento viejo debe cambiar. No apruebo, sin embargo, correr
`BigTrap2Absorption.cs` v1.0 con la interpretacion actual. Hay tres bloqueos previos: el score
por defecto no exige desplazamiento absoluto bajo; la literatura citada valida OFI de libro y
el codigo calcula imbalance de trades; y la puerta `>=10 sesiones` no cabe en una ventana del
24 al 30 de junio.

### Q1 — Que es hoy el evento, operativamente

Con los defaults versionados, BigTrap2 toma una cubeta de 25 prints, clasifica cada print
`buy/sell` por bid/ask y usa tick rule como fallback, agrega el volumen por fila de 1 tick y
evalua un imbalance diagonal:

```
buy_ratio[r]  = ask[r] / max(bid[r-1], 1)
sell_ratio[r] = bid[r] / max(ask[r+1], 1)
```

Una fila califica si el ratio es `>=3`, esta del lado perdedor del close y cae en el 30 % de
mecha correspondiente. `TRAP` se exporta por lado desde volumen agregado `>=1`; la burbuja y
la zona exigen despues `MinTrapVolume>=30`.

Por lo tanto, en el caso frecuente de celda diagonal opuesta vacia, el minimo operativo es:

> al menos 3 contratos agresores en una fila de mecha, del lado perdedor del close, con cero
> volumen opuesto diagonal.

No es simplemente "tres contratos al ask" en cualquier lugar. El lado respecto del close, la
mecha, la diagonal y la agregacion por lado tambien definen el evento. Los minimos versionados
`trap_vol=3` y `trap_ratio=3` son compatibles con esa degeneracion; no miden por si solos cuantas
filas tuvieron denominador cero. Para medir esa prevalencia haria falta exportar el denominador
o recomputar el footprint. Aca no se hizo.

### Q2 — Evidencia del repo

Medido y versionado en `docs/research/h_gc_bt2x_oracle_inspect.json`, GC DEC26, 17–21 ago:

| magnitud | valor medido | lectura |
|---|---:|---|
| `BARRA_PROCESADA` | 24.093 | denominador de cubetas procesadas |
| `TRAP` | 11.964 | **0,497 eventos TRAP por cubeta procesada** |
| lados | 6.126 sellers / 5.838 buyers | balance 51/49 |
| `trap_vol` p25/p50/p75 | 3 / 4 / 7 | tamano central minimo |
| `trap_ratio` p25/p50/p75 | 3 / 4 / 5 | pegado al piso operativo |
| `trap_nrows` p25/p50/p75 | 1 / 1 / 1 | la celda aislada domina |
| `ZONE_CREATED` | 122 | 1,02 % de los TRAP exportados |

Correccion de lenguaje: `11.964 / 24.093 = 49,7 %` es densidad de eventos por cubeta, no una
fraccion demostrada de **cubetas unicas**. El codigo puede emitir dos lados en una misma cubeta.
Sin contar `bar` unicos no corresponde afirmar que 49,7 % de las cubetas tuvieron al menos un
TRAP.

Medido y versionado en `docs/research/h_gc_bt2x_path_overfit.json`:

| poblacion | n | MFE p50 | MAE p50 | MFE media | MAE media |
|---|---:|---:|---:|---:|---:|
| todos | 11.962 | 38 | 36 | 46,036 | 44,923 |
| `vol>=30` | 122 | 40 | 39 | 46,410 | 48,582 |

El corte absoluto `vol>=30` no rompe la simetria central y en medias la invierte en contra. El
mismo archivo esta rotulado `OVERFIT_DECLARED_HOLDOUT_AUG17_21` y `no_elige_config=true`; sirve
para describir la barrera, no para seleccionar ni confirmar.

F2.9 usa otro estimand, la carrera target-free `r_i`, y tambien refuta exclusividad del kernel:

| regla | Delta | IC 95 % |
|---|---:|---|
| `K0` creadora BigTrap2 | +0,0215 | [+0,0029; +0,0400] |
| `S1` vela extrema generica | **+0,0383** | [+0,0276; +0,0490] |
| `N0` no-creadora emparejada | +0,0182 | [+0,0020; +0,0344] |
| `F0` TRAP emitido | +0,0424 | [+0,0312; +0,0535] |

`K0-S1=-0,0168` con IC `[-0,0306; -0,0031]`; `K0-N0` cruza cero; y `F0-S1=+0,0041`
con IC `[-0,0057; +0,0138]`. La conclusion admisible es que BigTrap2 no agrega informacion
incremental demostrada sobre el sello barato `S1`. No es que `F0` sea peor: es indistinguible
de `S1` en ese contraste.

### Q3 — Fortalezas reales

La fortaleza principal sigue siendo la infraestructura, no la senal. `BigTrap2.cs` usa ticks
enteros, clasificacion de agresor declarada, disponibilidad al cierre, export continuo y
politica fail-closed para atribucion ambigua. Eso permite falsar una definicion sin mezclarla con
fills o P&L.

En `BigTrap2Absorption.cs` hay decisiones de diseno utiles, revisadas en codigo pero **no
medidas**: el percentil se calcula antes de insertar la cubeta corriente; las residuales no
entran al historial ni disparan; el fill se registra en el primer print posterior; y el export
incluye `signed_flow`, `d_ticks`, `a_score`, `a_thr`, `run_rows`, `run_frac` y los campos del
kernel viejo. Esa observabilidad permite auditar y hacer analisis offline sin esconder los
rechazos.

La literatura si respalda una pregunta general: el impacto de precio debe estudiarse junto con
flujo y liquidez. Cont–Kukanov–Stoikov encuentran una relacion contemporanea aproximadamente
lineal entre OFI y cambio de midprice, con pendiente inversa a profundidad. Gould–Bonart
encuentran poder predictivo de queue imbalance para el siguiente movimiento de midprice. Eso
justifica investigar flujo, desplazamiento y profundidad. No valida este score particular, no
valida una reversa en GC y no demuestra rentabilidad.

### Q4 — Debilidades reales

1. **El evento viejo nace de un artefacto numerico.** Con opuesto cero, el ratio es conteo. El
   piso de 3 contratos cambia de significado por instrumento, hora y regimen.
2. **La evidencia de frecuencia estaba sobreinterpretada.** Hay 0,497 TRAP/cubeta; no esta
   medido el porcentaje de cubetas unicas con evento.
3. **`signed_flow` no es OFI.** El codigo suma volumen de trades iniciados por comprador menos
   volumen iniciado por vendedor. Eso es trade imbalance (`TI`). El OFI de
   Cont–Kukanov–Stoikov incluye cambios de cola por limit orders, market orders y cancelaciones
   en best bid/ask. En su muestra, OFI explico en promedio 65 % del cambio de precio contra 32 %
   para TI. Invocar ese paper como validacion directa del score actual excede la evidencia.
4. **`A` no es un residuo.** No estima `beta`, no usa profundidad y no resta impacto esperado.
   Es un cociente de flujo por movimiento: una proxy de inversa de impacto o profundidad,
   emparentada conceptualmente con `1/lambda` de Kyle y con la inversa del ratio de iliquidez de
   Amihud. Un percentil rodante la normaliza por rango local; no vuelve adimensional al score,
   que conserva unidades de contratos por tick.
5. **El default contradice el nombre.** En `AbsDirectional`, si `signed_flow>0` y `dPx=-10`, el
   denominador es 1, exactamente igual que con `dPx=0`. El score premia tanto inmovilidad como
   un movimiento adverso arbitrariamente grande. Eso puede definir *agresion fallida*, pero no
   "desplazamiento bajo". `AbsMagnitude` si penaliza `|dPx|`, aunque sigue siendo proxy.
6. **El precio medido no es el de la literatura citada.** `dPx` usa primer y ultimo trade de la
   cubeta, no cambio de midquote. Puede incorporar bid-ask bounce. Ademas el score usa flujo de
   toda la cubeta mientras la geometria `run_*` es local a filas de mecha; no esta demostrado que
   ambas piezas describan al mismo absorbedor.
7. **`MinStackedRows=2` es una hipotesis de practica, no evidencia academica.** La busqueda no
   encontro validacion peer-reviewed directa para "stacked footprint imbalances" como predictor
   economico. Debe entrar como perilla pre-registrada, no como hecho establecido.
8. **La paridad del indicador nuevo esta no medida.** El nuevo archivo se autocorta cada 25
   prints; el viejo usa atribucion OHLCV verificada. La afirmacion "reproduce exactamente el
   kernel viejo" sigue pendiente de paridad. Ademas `OpenLog()` pisa la ruta exacta y silencia
   excepciones; eso no es fail-closed y puede destruir o perder evidencia sin aviso.
9. **El export amplio no autoriza un sweep de outcomes.** Poder barrer `q`, filas y fraccion
   offline es una ventaja de observabilidad, pero elegir despues de mirar MFE/P&L seria
   multiplicidad. Debe haber una configuracion headline congelada y el resto quedar
   exploratorio.

### Q5 — La barrera economica

Fuente: `docs/research/h_gc_bt2x_path_overfit.json`. Son numeros del holdout gastado, rotulados
como overfit y sin friccion; no adjudican una configuracion.

| concepto | valor |
|---|---:|
| mejor celda publicada, todos (`SL13/TP30/BE off`) | +0,7226 ticks brutos |
| friccion declarada | 1,5 ticks |
| neto mecanico de esa media | **-0,7774 ticks** |
| bruto minimo para netear +1 tick | **2,5 ticks** |
| brecha desde +0,7226 | **1,7774 ticks** |
| multiplicador de bruto requerido | **3,46x** |

Para `SL13/TP30`, el camino sin deriva exige 30,23 %; el archivo mide 31,91 %. Llegar a 2,5
ticks brutos exige 36,05 %: +5,82 pp sobre el nulo y +4,14 pp sobre lo observado. El factor
~3,4 compara deriva requerida con deriva observada; no es una probabilidad de exito.

La celda `vol>=30`, `n=122`, muestra +3,7025 ticks brutos en ese mismo archivo. No se esconde,
pero tampoco se corona: es una cola chica vista en holdout, dentro de una exploracion declarada,
y no pertenece al evento nuevo.

`S1=+0,0383` no esta expresado en ticks ni expectancy: es el Delta de la carrera `r_i` de F2.9.
Sirve como control de la puerta target-free. No se puede restar de 0,7226 ni usarlo como barrera
economica. Las dos puertas tienen estimands distintos y deben permanecer separadas.

### Q6 — Corresponde cambiar el indicador. Que exactamente

**Si corresponde cambiar el evento viejo. No corresponde aprobar v1.0 sin enmienda semantica y
tecnica.** El archivo no se toca en esta pasada; primero deben cerrar las tres revisiones.

Cambio exacto que propongo para la sintesis:

1. Nombrar la variable actual correctamente: `trade_imbalance`, no OFI. Reservar OFI para cuando
   el join L2 de junio este cerrado y entren altas, bajas y cancelaciones del libro.
2. Separar dos hipotesis antes de ver outcomes:
   - **Absorcion literal**: `ScoreMode=AbsMagnitude`, flujo alto y movimiento absoluto bajo.
     Idealmente `dPx` debe ser cambio de midquote; con last trade es una proxy declarada.
   - **Agresion fallida**: el `AbsDirectional` actual, que acepta movimiento adverso. Es otra
     hipotesis y no puede reemplazar a la primera si falla.
3. Describir `a_score` como **proxy de inversa de impacto con percentil causal**, no como residuo
   OFI ni como score escala-libre. Un residuo real requiere estimar causalmente el impacto
   esperado y, de ser posible, condicionarlo por profundidad.
4. Mantener `TapeWindowTicks`, `MinStackedRows` y `MinTrapFrac` como parametros. Congelar un
   headline; no crear constantes nuevas ni rescatar con grilla.
5. Antes de cualquier outcome, corregir el contrato de evidencia del logger, verificar
   compilacion, CRLF, sha256/blob, conteo `files[]` y paridad de cortes/campos contra Python.

La mejora conceptual no es "mas filtro". Es dejar de llamar absorcion a cualquier imbalance de
mecha y decidir si se estudia baja respuesta absoluta o agresion fallida. Mezclarlas en un enum
y elegir despues seria dos trials, no robustez.

### Q7 — Prueba falsable y pre-registrada

El protocolo escrito **no es ejecutable tal como esta**. Del 24 al 30 de junio hay como maximo
7 fechas calendario; bajo una sesion CME por trade date no puede cumplir `>=10 sesiones`. Ese
conflicto debe enmendarse antes de abrir outcomes: extender discovery hasta al menos 10 sesiones
o cambiar el piso por escrito, sabiendo que lo debilita. No se corrige despues de correr.

Orden propuesto:

**Puerta 0 — validez tecnica, sin outcomes.** Congelar hash y parametros; compilar; exigir log
unico sin overwrite silencioso; 0 errores de escritura; corte de cubetas, `signed_flow`, `dPx`,
percentil causal, `run_*`, `available_at` y fill post-senal en paridad NT8/Python. Cualquier falla
invalida la corrida completa.

**Headline congelado.** `TapeWindowTicks=25`, `q=90`, `L=500`, `MinHistoryBuckets=200`,
`MinStackedRows=2`, `MinTrapFrac=0,20`, `RequireFlowSideMatch=true`, y un solo `ScoreMode`
resuelto por la sintesis antes de medir. La otra semantica es otro trial. Las grillas quedan
exploratorias y no pueden sustituir al headline.

**Puerta 1 — seleccion target-free.** En discovery no gastado y con `n>=200` y `>=10` sesiones:
`MFE_p50 / MAE_p50 >= 1,25` para la direccion declarada. La inferencia debe reagrupar por sesion,
porque los caminos de eventos cercanos comparten ticks. Si falla, se cierra sin SL/TP.

**Puerta 2 — control S1, no cero.** Recomputar `S1` sobre las mismas sesiones GC y con el mismo
estimand de F2.9. Contraste primario pareado por sesion: `nuevo - S1`; pasa solo si el limite
inferior del IC 95 % es `>0`. Comparar el IC del nuevo contra el punto historico `+0,0383` ignora
la incertidumbre del control y mezcla muestras. Si no puede instanciarse S1 en la misma ventana,
la puerta queda no medida, no aprobada.

**Puerta 3 — economia sin pesca.** Fijar antes una sola monetizacion. Si se hereda
`SL13/TP30/BE off`, declarar que fue elegida mirando el holdout gastado y que esta corrida solo
puede ser discovery. Exigir media bruta `>=2,5 ticks`; la grilla completa es secundaria y no
puede sustituir al headline. Fills y costos los calcula el motor comun, nunca el indicador.

**Regla de parada.** Fallar cualquier puerta cierra la linea y se asienta en
`EDGES_DISCOVERED.md`. Pasar las tres produce `SURVIVES_DISCOVERY`, no "edge": no queda holdout
intacto para promocion. Harian falta datos futuros y autorizacion escrita para una confirmacion
nueva.

### Research consultado en esta pasada

- Cont, Kukanov, Stoikov, *The Price Impact of Order Book Events*, JFEc 2014,
  arXiv:1011.6402. OFI incluye market/limit/cancel; impacto contemporaneo lineal y dependiente de
  profundidad; OFI explica mejor que trade imbalance.
- Kyle, *Continuous Auctions and Insider Trading*, Econometrica 1985. `lambda` es impacto por
  unidad de order flow; su inversa es profundidad. Respalda interpretar flujo/movimiento como
  liquidez, no como edge de reversa.
- Amihud, *Illiquidity and Stock Returns*, JFM 2002. `|return|/dollar volume` es una proxy gruesa
  de impacto; el cociente inverso es mas cercano a liquidez que a un residuo estructural.
- Gould y Bonart, *Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book*,
  arXiv:1512.03492. Evidencia predictiva en acciones Nasdaq usando colas del libro, no footprint
  de trades ni GC.
- Xu, Gould y Howison, *Multi-Level Order-Flow Imbalance in a Limit Order Book* (2019). La
  informacion de niveles del libro mejora el ajuste de cambios contemporaneos; refuerza que el
  L2 pendiente es sustantivo, no cosmetico.

No encontre respaldo peer-reviewed directo para `MinStackedRows=2`, `MinTrapFrac=0,20` ni para
el score exacto `|TI|/(1+max(0,dFav))`. Son hipotesis falsables de este proyecto.

### Veredicto de la pasada GPT

Coincido con Opus en Q4: el evento actual esta mal definido y no supera al control barato.
Coincido parcialmente en Q6: hay que cambiar la definicion, pero **no** llamaria al default v1.0
"residuo OFI, escala-libre, de desplazamiento bajo". Es una proxy rankeada de inversa de impacto
sobre trade imbalance y, en modo direccional, detecta agresion fallida.

Probabilidad cualitativa de pasar una prueba corregida: **baja**. No asigno porcentaje: no fue
medido. No corresponde correr outcomes hasta cerrar Kimi, aplicar la regla del acta y enmendar
la incompatibilidad de sesiones.

---

## 3. Pasada Kimi K3

**Fecha**: 2026-08-22 · **Rol**: auditor (pre-registro) · **Modelo**: Kimi K3 (selector del chat
de Notion, maximo nivel de razonamiento)
**Snapshot revisado**: `foundation/f0b-compatibility-probe` @ `9f11f7a`
**Alcance**: definicion del evento. No se corrio NT8, no se midieron outcomes nuevos, no se toco
el holdout.

**Declaraciones de trazabilidad** (pedidas por el auditor del chat, quedan aca):

- La identidad del modelo es la del selector de Notion; **no es verificable desde adentro del
  chat**. Si el selector mintiera, esta seccion no la escribio Kimi K3 y la revision pierde una
  pasada. Riesgo declarado, no bloqueante.
- Esta pasada tuvo **visibilidad** de las secciones 1 y 2 y de la auditoria de paridad del mismo
  dia (`PARIDAD_BT2_ABSORPTION_2026-08-22.md`). No es revision ciega: la sintesis tiene que pesar
  los acuerdos con eso en cuenta.
- La evidencia se releyo de los artefactos (`h_gc_bt2x_oracle_inspect.json`,
  `h_gc_bt2x_path_overfit.json`), no de los resumenes ajenos.

### Q1 — Que es hoy el evento, operativamente

Dos definiciones conviven y no hay que mezclarlas.

**Kernel viejo (BigTrap2 v2.5.1, el medido):** cubetas de 25 ticks, footprint por fila de 1 tick,
imbalance diagonal `ratio >= 3`, fila del lado perdedor del close y dentro del 30 % de mecha.
El `max(opuesto, 1)` hace que con celda opuesta vacia el ratio sea el conteo absoluto. En el
artefacto: `trap_vol` min = **3** y `trap_ratio` min = **3**, exactos. El evento real es "al
menos 3 contratos agresores en una fila de mecha, del lado perdedor, sin oposicion diagonal" —
con la precision de GPT: el lado, la mecha y la diagonal tambien definen el evento, y el 49,7 %
es **densidad de eventos por cubeta** (11.964/24.093), no fraccion de cubetas unicas: el
artefacto no cuenta `bar` unicos con TRAP. Queda como no medido ahi.

**Indicador nuevo (BigTrap2Absorption v1.1.1):** el evento es `A = |TI| / (1 + max(0, sgn(TI) *
dTicks))` superando el percentil 90 causal rodante (L=500, warmup=200), mas `MinStackedRows=2`,
`MinTrapFrac=0,20` y `RequireFlowSideMatch`. `TRAP` se exporta siempre que hay geometria; la zona
exige todos los cortes. TI es **trade imbalance**, no OFI.

### Q2 — Evidencia del repo

Kernel viejo, GC DEC26 17–21 ago (`h_gc_bt2x_oracle_inspect.json`):

| magnitud | valor |
|---|---|
| `BARRA_PROCESADA` | 24.093 |
| `TRAP` | 11.964 (0,497 por cubeta) |
| `trap_vol` p25/p50/p75 | 3 / 4 / 7 (min 3, max 144) |
| `trap_ratio` p25/p50/p75 | 3 / 4 / 5 (min 3, max 99) |
| `trap_nrows` p25/p50/p75 | 1 / 1 / 1 (max 4) |
| `ZONE_CREATED` | 122 |
| ciclo de vida | 122 creadas / 279 touched / **119 invalidadas** / 3 expiradas |

Caminos (`h_gc_bt2x_path_overfit.json`, rotulado `OVERFIT_DECLARED_HOLDOUT_AUG17_21`,
`no_elige_config=true`, EV bruto sin friccion):

| poblacion | n | MFE p50 | MAE p50 | nota |
|---|---:|---:|---:|---|
| todos | 11.962 | 38 | 36 | rr p50 = 0,96 |
| `vol>=30` (zona) | 122 | 40 | 39 | **medias invertidas**: MAE 48,58 > MFE 46,41 |

Grilla: `SL13/TP30/BE off` sobre todos: winrate 31,91 % (n_tp=3.775), EV **+0,7226 t**; el nulo
sin deriva pide 30,23 %; para netear +1 t hacen falta 36,05 %. Sobre `vol>=30`: winrate 38,84 %,
EV +3,7025 t con n=122 — cola chica en holdout gastado, exploratoria, no corona nada.

F2.9: `S1` = **+0,0383** > `K0` = +0,0215 ≈ `N0` = +0,0182; `F0` = +0,0424 indistinguible de S1
(IC del contraste cruza cero).

Evidencia nueva del mismo dia (auditoria de paridad, export v1.1.1 de la misma ventana):
28.042 cubetas, 13.904 TRAP, **647 zonas creadas / 628 invalidadas / 18 expiradas**. El 97,1 %
de las zonas del indicador nuevo mueren por close-through. Es consistente con la tesis de trampa
(el atrapado queda barrido), pero dice que el contenido informativo del evento esta en la
creacion/fill, no en la persistencia de la zona. Y la semantica del `.cs` resulto portable con
exactitud: 635/635 zonas reproducidas en el rango cubierto, con una salvedad de fill (1/635).

### Q3 — Fortalezas reales

1. **La infraestructura es lo caro y ya esta.** Subserie 1-tick, corte propio, fill al tick
   siguiente sin look-ahead, log reproducible. Nada de eso se rehace.
2. **Clasificacion de agresor correcta**: bid/ask primero, tick rule de respaldo, y `n_quote` /
   `n_rule` contados en el export — la practica que la literatura (Chakrabarty–Pascual–Shkilko)
   exige para saber cuanto del flujo es medido y cuanto inferido (~77 % de acierto del tick rule).
3. **Observabilidad disenada para falsar**: el export amplio permite auditar cada rechazo y
   barrer cortes offline sin recomputar el indicador.
4. **La paridad medida hoy es una fortaleza del proceso, no solo del indicador**: la semantica
   del `.cs` se reprodujo exacta (signed_flow y d_ticks 27.328/27.328, zonas 635/635 en rango).
   La maquina de auditar funciona.
5. **La honestidad del repo**: tres hipotesis refutadas con acta, cero edges promovidos. Es lo
   que hace que esta revision valga algo.

### Q4 — Debilidades reales

1. **El evento viejo esta implicito, no definido** — artefacto del `max(opuesto,1)`. Coincido con
   Opus y GPT: es el hallazgo central y no hace falta un tercer numero para verlo.
2. **No es escala-libre**: un piso en contratos mide cosas distintas por instrumento, hora y
   regimen.
3. **TI no es OFI** (GPT, suscripto): el 65 % vs 32 % de Cont–Kukanov–Stoikov es sobre OFI de
   libro con altas/bajas/cancelaciones. El score actual es trade imbalance; citar ese paper como
   validacion directa excede la evidencia. El join L2 de junio (3/20.486) es el camino
   sustantivo, no cosmetico (Xu–Gould–Howison).
4. **`A` no es un residuo ni escala-libre en sentido estricto** (GPT, suscripto): es una proxy de
   inversa de impacto con percentil causal; conserva unidades de contratos por tick.
5. **El default contradice el nombre** (GPT Q4.5, suscripto y lo llevo a terreno medible): en
   `AbsDirectional`, flujo positivo con `dPx=-10` tiene denominador 1, identico a `dPx=0`. Eso
   mide *agresion fallida*, no *desplazamiento bajo*. Censo target-free pendiente para junio:
   que fraccion de los `a_pass` proviene de `denom=1`. Si es la mayoria, el indicador es volumen
   con otro nombre y la Puerta 2 ya esta contestada de antemano.
6. **`dPx` con first/last trade incorpora bid-ask bounce**; la literatura usa cambio de midquote.
   Corregible cuando cierre el join L2; hasta entonces, declarado como proxy.
7. **`MinStackedRows=2` y `MinTrapFrac=0,20` son hipotesis de practica** sin validacion
   peer-reviewed directa (busqueda de GPT). Entran como perillas pre-registradas, no como hechos.
8. **El kernel Python commiteado no reproduce al `.cs`** (medido hoy, no en la pasada de GPT que
   lo tenia como pendiente): sin concepto de sesion, diverge desde la cubeta 3947; corrido
   verbatim sobre la cinta produce 605 zonas y solo 32 coinciden con el export. Es material de
   Puerta 0: la corrida de junio tiene que ser del codigo versionado o la paridad no vale.
9. **El export amplio no autoriza sweeps de outcomes** (GPT, suscripto): headline congelado y el
   resto exploratorio.

### Q5 — La barrera economica

Mismos numeros, misma conclusion: EV bruto +0,7226 t contra 2,5 t necesarios (brecha 1,7774 t,
factor 3,46x); 31,91 % observado contra 30,23 % del nulo y 36,05 % requerido. El barrido de 960
celdas no puede coronar por construccion: sin deriva el EV bruto es cero por definicion. La
brecha se cierra solo si el evento selecciona mejor, no tocando SL/TP/BE. Y suscribo la
separacion de GPT: `S1` (Delta de la carrera `r_i` de F2.9) y los ticks de la grilla son
estimands distintos; no se restan entre si.

### Q6 — Corresponde cambiar el indicador. Que exactamente

**Si: la definicion del evento. Y la divergencia Opus–GPT se resuelve con precision, no con
voto.**

Son dos estimands distintos:

- **`AbsMagnitude`** (`A = |TI| / (1 + |dPx|)`): absorcion literal, simetrica — flujo alto con
  desplazamiento absoluto bajo. Es la fiel al nombre y a la practica (baja respuesta de precio).
- **`AbsDirectional`** (`A = |TI| / (1 + max(0, sgn(TI)*dPx))`): agresion fallida — penaliza solo
  el desplazamiento a favor del flujo. El movimiento adverso no castiga: es la forma fuerte de
  "empujaron y no ganaron terreno", que es la tesis de trampa original de BigTrap.

Mi posicion para la sintesis: **headline = `AbsMagnitude`**, por tres motivos: es fiel al nombre
del indicador; su falsacion es limpia ("bajo desplazamiento absoluto" no admite ambiguedad); y si
la tesis viva es la trampa, `AbsDirectional` queda como segundo trial pre-registrado, no como
rescue-post-hoc.

Y una precision que le baja el costo a la decision: el export `ABS_SCORE` incluye `signed_flow` y
`d_ticks` por cubeta, asi que **las dos cadenas de score se recomputan offline desde el mismo
archivo** (el percentil es deterministico dado el score). Lo que hay que congelar no es el export
sino el **estimand headline**: cual cadena define la Puerta 1. Eso se elige antes de medir, una
sola vez.

`MinStackedRows`, `MinTrapFrac` y `TapeWindowTicks` quedan como parametros congelados en el
headline (2 / 0,20 / 25). No crear constantes nuevas.

### Q7 — Con que prueba falsable y pre-registrada se decide

Adopto el protocolo corregido de GPT, con la enmienda de sesiones como condicion de ejecutabilidad:

1. **Puerta 0 (tecnica, sin outcomes)**: hash y parametros congelados, compilacion limpia, log
   unico sin overwrite silencioso, y paridad NT8/Python con el kernel **versionado** (cortes de
   sesion incluidos) mas el artefacto de la corrida subido al repo. Estado hoy: la semantica esta
   medida exacta; el kernel commiteado aun no la implementa. Cualquier falla invalida la corrida.
2. **Enmienda de sesiones, antes de abrir outcomes**: del 24 al 30 de junio hay a lo sumo 7 trade
   dates; el piso de `>=10 sesiones` no cabe. Se extiende la ventana de discovery o se baja el
   piso por escrito, declarando que lo debilita. No se corrige despues de correr.
3. **Puerta 1 (target-free)**: decil superior de `a_score`, `MFE p50 / MAE p50 >= 1,25`, n >= 200,
   sesiones segun la enmienda, inferencia reagrupada por sesion. Si falla, la linea se cierra ahi.
4. **Puerta 2 (control)**: `S1` recomputado en las mismas sesiones de junio con el estimand de
   F2.9; contraste pareado por sesion `nuevo - S1`; pasa solo si el limite inferior del IC 95 %
   es > 0. Si S1 no puede instanciarse en la ventana, la puerta queda **no medida**, no aprobada.
5. **Puerta 3 (economia)**: una sola monetizacion congelada de antemano (si se hereda
   `SL13/TP30/BE off`, se declara que fue elegida mirando el holdout gastado); media bruta
   >= 2,5 ticks. La grilla es exploratoria y no sustituye al headline.
6. **Regla de parada**: fallar cualquier puerta cierra la linea y se asienta en
   `EDGES_DISCOVERED.md`. Pasar las tres produce `SURVIVES_DISCOVERY`, no "edge": no queda
   holdout intacto para promocion.

**Prediccion pre-registrada de la Puerta 1** (pedida por el auditor; declarada antes de medir
nada en junio):

> **No pasa.** El decil superior de `A` esta dominado por cubetas de alto |TI|, que son cubetas
> de alta actividad. MFE y MAE escalan con actividad, asi que su cociente hereda la base medida
> de 38/36 = 1,055. Nada en la construccion del score induce asimetria de caminos: el score es
> de magnitud, no de direccion de respuesta. Prediccion: `MFE p50 / MAE p50` del decil superior
> cae **entre 0,95 y 1,15** (punto ~1,05), lejos de 1,25, y la linea se cierra en la Puerta 1
> sin llegar a SL/TP. Si pasa, esta lectura queda refutada con el mismo numero — que es para lo
> que esta la puerta.

### Veredicto de la pasada Kimi K3

Cambiar la definicion del evento: **SI**. Aprobar v1.x sin enmienda semantica (nombre del score,
dos hipotesis separadas, headline congelado): **NO**. Probabilidad cualitativa de que pase las
puertas corregidas: **baja**, y por primera vez con una prediccion puntual escrita que la hace
falsable.

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
