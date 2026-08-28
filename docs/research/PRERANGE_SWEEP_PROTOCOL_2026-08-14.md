# L3 PreRange Double Sweep - Protocolo formal

**Fecha:** 2026-08-14
**Spec:** `specs/prerange_sweep_v0.json`
**Runner:** `diag/tasa_senales/prerange_sweep_formal.py` (`prerange_sweep_formal_v0_1`)
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

Ademas el gate `MIN_USABLE_PLACEBOS = 19` (piso `1/20 = 0,05`) vive **dentro de
`decide()`**: si menos de 19 placebos tienen datos suficientes, `PRERANGE_EDGE`
es inalcanzable y el runner se **niega** a emitirlo. Este gate se agrego porque
el propio test lo caza: en la primera corrida el runner emitio `PRERANGE_EDGE`
con `p_perm=0,1` cuando el piso era `0,0833`.

---

## 5. El fix 3: la procedencia de la ventana es el techo de la etiqueta

El usuario declaro (2026-08-14) que `08:12-09:12` es **a priori, visto en
internet**: no salio de mirar este dataset ni del barrido de Kaggle.

`apply_provenance_cap()` implementa el techo:

| `window_provenance` | Habilita `PRERANGE_EDGE` |
| --- | --- |
| `a_priori_external` | si |
| `a_priori_mechanism` | si |
| `chosen_from_this_data` | **no** -> degrada a `WINDOW_UNSPECIFIC` |
| `unknown` (default) | **no** -> degrada a `WINDOW_UNSPECIFIC` |

El cap **solo baja** etiquetas, nunca las sube, y el default asume lo peor.

**Lo que esto habilita:** el rank contra los placebos pasa a ser interpretable
sobre datos `<= 2026-08-13`, porque no hubo flujo de informacion desde esos
datos hacia la eleccion de la ventana.

**Lo que esto NO resuelve (T5):** una ventana publicada es el **sobreviviente de
una busqueda ajena**, de tamanio desconocido, sobre datos desconocidos, con
sesgo de publicacion. La seleccion no desaparecio: se terceriza. Un rank 1 sobre
datos historicos sigue siendo compatible con "esto funciono en alguna muestra y
por eso se publico". El unico test limpio de T5 es forward-only.

---

## 6. LEMA DE IDENTIFICACION: los placebos no pueden salvar el confusor macro

**Enunciado.** Ninguna ventana placebo puede contener la publicacion de 08:30.

**Demostracion.** Una ventana de 60 minutos que contenga las 08:30 debe arrancar
entre 07:31 y 08:30. Todos esos arranques estan a menos de 60 minutos de la
primaria (08:12), o sea que **se solapan** con ella, y por definicion de la
familia (`|offset| >= 60`) estan excluidos.

**Consecuencia.** La ventana primaria es la **unica de su estrato estructural**.
Un rank 1 es igual de compatible con "esta ventana absorbe liquidez" que con
"esta ventana contiene el dato macro de 08:30". El test de permutacion **no las
distingue**, y esto es geometrico: **no se arregla con mas datos**.

Esto invalida la mitigacion que yo mismo habia propuesto para T1. La
identificacion correcta no pasa por los placebos:

**Split de la propia ventana primaria por dia con/sin evento programado.**

```bash
--macro-dates macro_2025_2026.csv   # una fecha YYYY-MM-DD por linea
```

- Si el subconjunto **sin** evento mantiene `IC95 > 0` con `n >= 30`, el efecto
  no es la reaccion al dato.
- Si solo aparece en dias con evento, **es** el dato, y la linea cambia de
  hipotesis (deja de ser liquidez y pasa a ser event-response).

Adicionalmente, `classify_window()` etiqueta cada ventana con su estrato
estructural declarado a priori (`contains_0830_macro`, `contains_0930_cash_open`,
`overnight`, `rth_quiet`) y el payload guarda `placebo_strata` para permitir
recomputar subfamilias sin post-hoc encubierto.

---

## 7. Etiquetas (las emite el codigo, no la narrativa)

| Etiqueta | Condicion |
| --- | --- |
| `PRERANGE_EDGE` | IC95 HAC > 0 **Y** familia >= 19 **Y** rank 1 **Y** procedencia habilitante |
| `PRERANGE_WINDOW_UNSPECIFIC` | IC95 > 0 pero falla familia, rank o procedencia |
| `PRERANGE_NO_EDGE` | IC95 cruza cero |
| `PRERANGE_FADE` | IC95 < 0: continuacion. Falsacion, no promocion: no exige familia ni procedencia |
| `PRERANGE_UNDERPOWERED` | algun gate de datos falla |
| `ABSTAIN_DATA` | parsing o cobertura insuficiente |

Gates de datos: `sessions_ge_30`, `resolution` (>=0,30), `ties` (<=0,10),
`coverage` (>=0,40). Agregacion: una observacion por sesion (ceros adentro),
HAC Bartlett con `lag = ceil(sqrt(n))`, IC95. Igual que F2.7.

---

## 8. Potencia: el constraint real

Con ~210 sesiones y fraccion resuelta ~0,6: `sd(r) ~ 0,76`, `SE ~ 0,054`, y el
**MDE a 80% de potencia es `|mean r| ~ 0,15`**, equivalente a un split de
**~63/37** entre carreras resueltas.

Un edge real de **55/45 necesitaria ~1.250 sesiones (~5 anios)**.

Y sumar YM+NQ+ES **no triplica el n**: la propia sincronizacion reportada (51%
en 3 indices vs ~36% esperado bajo independencia) demuestra un factor comun de
regimen diario. Valen como **~1,3 activos independientes**, no 3.

---

## 9. Firewall de quemado (revisado)

El barrido de Kaggle cubrio YM, NQ, ES y GC con M1 hasta 2026-08-13 optimizando
`profit_factor` sobre la superficie `(hora de inicio x duracion)`, y **fue
detenido sin completar**.

El quemado solo contamina si informacion fluyo **de los datos hacia la eleccion
de la ventana**. Con `a_priori_external` ese flujo no existio. De estos datos si
se observo la **tasa** de doble barrido y sus splits sobre 210 sesiones YM, pero
ese es un funcional distinto: el estimando de reversion **nunca se computo**
sobre estos datos.

**Regla revisada.** Primera corrida sobre datos `<= 2026-08-13`:
`CONFIRMATORY_WITH_CAVEATS`, condicionada a (a) registrar la fuente externa,
(b) no reportar descriptivos como hallazgos, (c) reportar el split macro.
Set limpio de T5: **forward-only desde 2026-08-14, minimo 60 sesiones**.

---

## 10. Amenazas declaradas

- **T1 - evento macro en la ventana.** Contiene 08:30 EST. **Los placebos no lo
  pueden controlar (ver lema).** Requiere `--macro-dates`.
- **T2 - zona horaria.** Declarar el reloj del archivo antes de correr.
- **T3 - DST.** `08:12 EST` fijo vs horario de verano.
- **T4 - empates en M1.** Si falla el gate `ties`, ir a ticks
  (`tick_first_touch` de F2.7).
- **T5 - seleccion lavada / publication bias.** La ventana viene de una
  publicacion: sobreviviente de una busqueda ajena de tamanio desconocido.
  Unico test limpio: forward-only.

---

## 11. Validacion sintetica (antes de tocar datos reales)

`python3 tests/research/test_prerange_sweep_formal.py` -> **12 bloques, todos PASS**

| Bloque | Resultado |
| --- | --- |
| Nulo random walk, 160 sesiones | `n=97`, `coverage=0,606`, `mean=-0,0206`, IC `[-0,199,+0,158]`, `p_rev=0,489` -> **`PRERANGE_NO_EDGE`** |
| Reversion plantada (bias 0,45) | `mean=+0,9868`, IC `[+0,963,+1,011]` -> detecta el efecto |
| Continuacion plantada | `mean=-1,0000` -> **`PRERANGE_FADE`** |
| Familia insuficiente (11 de 25) | se **niega** a emitir EDGE, `family_ok=False` |
| 12 sesiones | `PRERANGE_UNDERPOWERED` |
| Cap de procedencia | `unknown` y `chosen_from_this_data` degradan EDGE; el cap nunca sube una etiqueta |
| Lema de identificacion | verificado por enumeracion: toda ventana que contiene 08:30 se solapa con la primaria |
| Split macro | suma exacta de eventos, IC HAC propio por subconjunto, `None` sin calendario |

El bloque del nulo es el importante por dos razones: (1) el estimando da ~0 sin
simular nada, confirmando la simetria; (2) en ese **mismo** dataset sintetico la
tasa de doble barrido es **60,6% con cero edge**, **reproduciendo la tautologia
original en un random walk puro**.

---

## 12. Como correrlo

```bash
python3 diag/tasa_senales/prerange_sweep_formal.py YM_M1.csv \
    --tick 1.0 --asset YM \
    --window-provenance a_priori_external \
    --macro-dates macro_2025_2026.csv \
    --out payload_ym.json
```

Tick sizes: YM 1.0, ES 0.25, NQ 0.25, GC 0.1, 6E 0.00005.
CSV con header `Time,Open,High,Low,Close[,Volume]` o export NT8 headerless.
Antes de correr: **declarar la zona horaria del archivo** (T2/T3).
Sin `--window-provenance` el default es `unknown` y `PRERANGE_EDGE` no es
emitible.

---

## 13. Que NO hace este protocolo

- No mide P&L (`pnl_accessed=false`, `outcomes_accessed=false`). No hay stops,
  targets ni costos. Un edge en `r` es condicion **necesaria y no suficiente**
  para que algo sea transable.
- No toca el holdout (`holdout_included=false`).
- No barre parametros. `d_frac`, duracion, horizonte y familia de placebos
  quedan fijos por el spec. Cualquier variante es una linea nueva con spec nuevo.
- No promueve descriptivos: `by_weekday`, `by_range` y `by_second_side` se
  calculan y se guardan, pero **no adjudican**.
