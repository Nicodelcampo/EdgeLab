# L3 PreRange Double Sweep - Protocolo formal

**Fecha:** 2026-08-14
**Spec:** `specs/prerange_sweep_v0.json`
**Runner:** `diag/tasa_senales/prerange_sweep_formal.py`
**Tests:** `tests/research/test_prerange_sweep_formal.py`
**Estado:** `PREREGISTERED` (sin correr sobre datos reales)

---

## 1. Que llego

Un analisis sobre 210 sesiones de YM afirmando que el rango de 08:12-09:12 EST
es barrido de los dos lados en el 72,38% de las sesiones (IC95 66,33-78,43%),
con replicacion en NQ (71,6%) y ES (69,5%), 80,6% cuando el rango esta
comprimido, 83,7% los martes, y 51% de sincronizacion simultanea en los tres
indices. Framing recibido: "Universalidad Sistemica", "especialmente letal".

**Veredicto: `NO_ADJUDICABLE`.** No porque los numeros esten mal calculados,
sino porque **la cantidad medida no puede sostener la conclusion**.

---

## 2. Los tres errores

### Error 1: el estimando es una tautologia geometrica

"Frecuencia con la que el precio cruza los dos bordes de un rango" es una
propiedad de la **difusion**, no del mercado. Un random walk sin drift barre
las dos fronteras de un rango angosto con altisima frecuencia. El propio
analisis lo reconocio: su nulo browniano daba **68,33%**, el observado 72,38%,
exceso +4,06%, **Z=1,26, p=0,103**. Eso es *no significativo* y aparecio
escrito en el mismo informe que concluia "tremendo hallazgo".

### Error 2: el split por compresion amplifica la tautologia

Rango comprimido (<=108 pts) 80,6% vs expandido (>108) 63,7%. Fronteras mas
cerca => mas cruces. **Es geometria, no absorcion de liquidez.** El split
reportado como "el hallazgo mas fuerte" es en realidad la demostracion mas
clara de que la metrica esta midiendo distancia, no comportamiento.

### Error 3: seleccion sin costo

- La ventana `08:12-09:12` fue elegida mirando resultados. Un p-value sobre una
  ventana elegida post-hoc no es interpretable.
- Martes 83,7% con N=43: IC de ~+/-12 puntos, 5 dias testeados, sin correccion
  de multiplicidad. ~1,2 sigma. No es un hallazgo.
- El barrido `edgelab/research/kaggle_multiverse_sweep.py` evalua
  **921.600 combinaciones por activo** (288 horas de inicio x 100 duraciones x
  4 stops x 4 targets x 2 modos) y ordena por `profit_factor`. Eso no es
  research: es un catalogo de maximos accidentales, y ademas abre P&L, que esta
  cercado.
- La "sincronizacion 51% en 3 indices" (vs ~36% esperado bajo independencia,
  y 9,7% de dias sin ninguno vs ~2,4%) no muestra barridos coordinados: muestra
  un **factor comun de regimen diario**. YM, NQ y ES son el mismo trade macro.

---

## 3. El fix 1: un estimando cuyo nulo es exactamente 0

No medir la frecuencia del barrido. Medir, **despues** del segundo barrido, una
carrera de primer pasaje **simetrica por construccion**:

```
ventana  = [start, start+60)  ->  w_high, w_low, rango = w_high - w_low
1er barrido = primera barra post-ventana con High>=w_high o Low<=w_low
2do barrido = primera barra posterior que toca el lado OPUESTO

anchor = close(barra del 2do barrido)        [enteros de tick]
d      = round(rango * 0.5)                  [ticks]

si el 2do barrido fue ARRIBA:  revert = anchor - d ,  cont = anchor + d
si fue ABAJO:                  revert = anchor + d ,  cont = anchor - d

r = +1 si revert se toca primero
    -1 si cont se toca primero
     0 si empatan en la misma barra, o si ninguno se toca antes de las 16:00
```

`revert` y `cont` son **equidistantes** del anchor. Bajo difusion sin drift,
`P(revert primero) = P(cont primero)` **exactamente**, asi que `E[r] = 0` por
geometria.

Consecuencias practicas:

1. **No hay que simular brownianos ni estimar volatilidad.** El nulo es cero por
   construccion. Todo el aparato de "nulo browniano P2=68,33%" desaparece.
2. **La compresion sale del numerador**: `d` escala con el rango, asi que un
   rango angosto produce objetivos proporcionalmente angostos.
3. Cualquier asimetria observada **es** el efecto. No hay que restar nada.

### El fix 1b: se ancla en el CLOSE, no en el extremo

Anclar la carrera en el `High` de la barra del segundo barrido sesgaria el test
a favor de la reversion: al cierre de esa barra el precio ya esta por debajo de
ese High, entonces `revert` arrancaria mas cerca que `cont`. Se ancla en el
**close** para que la simetria sea exacta. Este es el tipo de defecto que
habria producido un "edge" del 60% sin que nada ocurra en el mercado.

---

## 4. El fix 2: la familia de placebos absorbe la seleccion de ventana

Medir bien el estimando no arregla que la ventana haya sido elegida a ojo. Fix:
declarar una familia de **ventanas placebo** que corren el mismo estimando en
otros horarios de arranque.

```
PLACEBO_OFFSETS = [o for o in range(-480, 331, 30) if abs(o) >= 60]   # 25 placebos
p_perm = rank(media primaria entre todas las medias) / (n_usables + 1)
```

La exclusion `|offset| >= 60` evita que un placebo se solape con la ventana
primaria (seria un placebo contaminado por el tratamiento).

### El piso de significancia es parte del diseno

La primera version de este runner usaba 8 placebos. Con 8, el minimo p-value
alcanzable es `1/9 = 0,111`: **ningun resultado, ni uno perfecto, podia ser
significativo.** El test estaba muerto antes de empezar. La grilla de 30
minutos da 25 placebos y un piso de `1/26 = 0,038`.

Ademas se agrego el gate `MIN_USABLE_PLACEBOS = 19` (piso `1/20 = 0,05`)
**dentro de `decide()`**: si menos de 19 placebos tienen datos suficientes,
`PRERANGE_EDGE` es inalcanzable y el runner se **niega** a emitirlo. Este gate
se agrego porque el propio test lo caza: en la primera corrida el runner emitio
`PRERANGE_EDGE` con `p_perm=0,1` cuando el piso era `0,0833`.

---

## 5. Etiquetas (las emite `decide()`, no la narrativa)

| Etiqueta | Condicion |
| --- | --- |
| `PRERANGE_EDGE` | IC95 HAC > 0 **Y** familia suficiente (>=19) **Y** rank 1 contra todos los placebos |
| `PRERANGE_WINDOW_UNSPECIFIC` | IC95 > 0 pero no gana a sus placebos, o familia insuficiente. Hay reversion, pero **no es propiedad de esta ventana** |
| `PRERANGE_NO_EDGE` | IC95 cruza cero |
| `PRERANGE_FADE` | IC95 < 0: continuacion, no reversion. Falsa la hipotesis en direccion opuesta |
| `PRERANGE_UNDERPOWERED` | algun gate de datos falla |
| `ABSTAIN_DATA` | parsing o cobertura insuficiente |

Gates de datos: `sessions_ge_30` (n>=30), `resolution` (decididos/n >= 0,30),
`ties` (empates misma barra <= 0,10), `coverage` (>= 0,40).
El requisito de familia aplica **solo** a `PRERANGE_EDGE`: `FADE` es una
falsacion, no una promocion, y no necesita defenderse de la seleccion.

Agregacion: **una observacion por sesion** (ceros adentro), media por sesion,
HAC Bartlett con `lag = ceil(sqrt(n))`, IC95. Igual que F2.7.

---

## 6. Firewall de quemado

El barrido de Kaggle cubrio YM, NQ, ES y GC con M1 hasta **2026-08-13**
(NQ 674.848 barras / 598 dias; YM 667.390 / 600; GC 660.784 / 587;
ES 656.069 / 584), optimizando `profit_factor` sobre toda la superficie
`(hora de inicio x duracion)`. Eso quema la ventana primaria **y la familia de
placebos** en esos cuatro activos.

**Consecuencia dura:** sobre datos `<= 2026-08-13` el propio test de rank esta
contaminado. Si `08:12` se eligio por su P&L en esa superficie y el P&L
correlaciona con el estimando de reversion, la ventana fue seleccionada **para**
ser rank 1.

**Regla:** corridas sobre datos `<= 2026-08-13` son **EXPLORATORIAS**; la
etiqueta maxima promovible es `PRERANGE_WINDOW_UNSPECIFIC`. `PRERANGE_EDGE`
solo puede emitirse sobre el set de confirmacion **forward-only** (sesiones
`>= 2026-08-14`, minimo 60 sesiones).

`6E` corta en 2026-06-30 (firewall previo respetado) y sirve como replicacion
independiente, aunque su microestructura difiere de los indices.

---

## 7. Amenazas declaradas y sin resolver

- **T1 - evento macro dentro de la ventana.** `08:12-09:12 EST` **contiene la
  publicacion de datos de 08:30 EST**. Los placebos sin evento programado no son
  intercambiables con la primaria. Un rank 1 podria significar "esta ventana
  tiene noticias", no "esta ventana tiene absorcion". Sin calendario economico
  no se puede separar. **Confusor abierto.**
- **T2 - zona horaria.** El reloj debe declararse. Si los parquets estan en hora
  del exchange y no en EST, la ventana no es la que se cree.
- **T3 - DST.** `08:12 EST` fijo vs horario de verano: el offset cambia dos
  veces al ano respecto de la hora del exchange.
- **T4 - empates en M1.** Si el gate de `ties` falla, M1 no resuelve el orden
  intra-barra y hay que reconstruir con ticks (`tick_first_touch` de F2.7).
- **Placebos overnight.** Los offsets de madrugada caen en liquidez overnight.
  Mitigacion: el payload guarda **todas** las medias de placebos para poder
  recomputar subfamilias (p. ej. solo RTH); el `p_perm` de la familia completa
  queda como primario.

---

## 8. Validacion sintetica (antes de tocar datos reales)

`python3 tests/research/test_prerange_sweep_formal.py` -> **9 bloques, todos PASS**

| Bloque | Resultado |
| --- | --- |
| Nulo random walk, 160 sesiones | `n=97`, `coverage=0,606`, `mean=-0,0206`, IC `[-0,199,+0,158]`, `p_rev=0,489` -> **`PRERANGE_NO_EDGE`** |
| Reversion plantada (bias 0,45) | `mean=+0,9868`, IC `[+0,963,+1,011]` -> detecta el efecto |
| Continuacion plantada | `mean=-1,0000` -> **`PRERANGE_FADE`** |
| Familia insuficiente (11 de 25 placebos) | se **niega** a emitir EDGE -> `PRERANGE_WINDOW_UNSPECIFIC`, `family_ok=False` |
| 12 sesiones | `PRERANGE_UNDERPOWERED` |

El bloque del nulo es el importante por dos razones: (1) el estimando da ~0 sin
simular nada, confirmando la simetria; (2) en ese **mismo** dataset sintetico la
tasa de doble barrido es **60,6%** con cero edge, **reproduciendo la tautologia
original en un random walk puro**.

---

## 9. Como correrlo

```bash
python3 diag/tasa_senales/prerange_sweep_formal.py YM_M1.csv \
    --tick 1.0 --asset YM --out payload_ym.json
```

Tick sizes: YM 1.0, ES 0.25, NQ 0.25, GC 0.1, 6E 0.00005.
CSV con header `Time,Open,High,Low,Close[,Volume]` o export NT8 headerless.
Antes de correr: **declarar la zona horaria del archivo** (T2/T3).

---

## 10. Que NO hace este protocolo

- No mide P&L (`pnl_accessed=false`, `outcomes_accessed=false`). No hay stops,
  targets ni costos. Un edge en `r` es condicion **necesaria y no suficiente**
  para que algo sea transable.
- No toca el holdout (`holdout_included=false`).
- No barre parametros. `d_frac`, duracion, horizonte y familia de placebos
  quedan fijos por el spec. Cualquier variante es una linea nueva con spec nuevo.
- No promueve descriptivos: `by_weekday`, `by_range` y `by_second_side` se
  calculan y se guardan, pero **no adjudican** (multiplicidad no corregida).
