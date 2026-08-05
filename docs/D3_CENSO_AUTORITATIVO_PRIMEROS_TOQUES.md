# D3 y el censo autoritativo — **cinco de seis no pueden entrar; queda UNO**

> **CORRECCIÓN (piloto de 30 sesiones, posterior a la primera versión de este
> documento).** Escribí que entraban dos. **Entra uno.** Dos errores míos, los
> dos por afirmar sin medir:
>
> 1. **`aVolCellPOI2` NO entra.** Vi que emitía `touch_count` y di por hecho el
>    resto. Nunca verifiqué el **tipo** de su `zone_id`: `avolcellpoi2.py:229`
>    hace `zone_id=zone_id` —el valor crudo, entero—; el `str()` está sólo en la
>    línea del CSV. Rechazado igual que `VolTicksPOC2`.
> 2. **`AACloseOpenDiffs` no es "rechazado": es peor.** Ver §3-bis.
>
> **Sólo `BigTrap2` produce la población autoritativa.** Y es el que está
> bloqueado por PRED-004.

**Fecha:** 2026-08-05 · **Tip:** `e1ee142` + este trabajo
**Nada abierto:** sin outcomes, sin holdout, sin NT8. El universo sale de la
puerta única.

## Justificación económica

§3.3 de `ESPEC_TEST_EXPLORE-001.md` —**las tres hipótesis**— está vacía. Se creía
que el bloqueo era **D3** (*"la tasa post-`sep_min` no discrimina entre
indicadores"*), o sea una decisión de criterio. **No es eso.** El bloqueo es que
la población sobre la que §3.3 puede congelarse **no se puede construir hoy para
cuatro de los seis candidatos.**

## Cómo podría refutarse

Si algún indicador rechazado expusiera el ordinal de toque en un campo tipado
que yo no encontré, o si `build_first_touch_census` admitiera otra vía para
identificar el primer toque, la tabla de abajo sería falsa. Se cita archivo y
línea de cada emisión para que se pueda verificar.

---

## 1. El censo que existía mide la población equivocada

`diag/tasa_senales/post_sepmin.py:170` lee `z["created_ms"]`: aplica `sep_min`
sobre **creaciones de zona**.

La enmienda `EXPLORE-001-2026-08-04_first_touch_decongestion.md`, **congelada
antes de ejecutar el censo**, dice que esa población es la equivocada:

> *"EXPLORE-001 define la entrada primaria en el primer toque posterior. La
> restricción representa capacidad de exposición, por lo que debe operar sobre el
> instante de entrada y no sobre el instante en que nació una zona todavía no
> operable."*

Y su efecto de autoridad es explícito:

> *"Las tasas de creaciones siguen siendo **diagnósticas**. H1–H3 sólo pueden
> congelarse con tasas producidas por **esta** población y **esta** política."*

**Consecuencia:** el censo de 201 sesiones —verificado y correcto— **no es
autoritativo para §3.3**. Es diagnóstico, tal como su propia enmienda declara.

## 2. La maquinaria correcta existía, y nadie la había corrido

| módulo | estado |
|---|---|
| `edgelab/research/first_touch_population.py` | construido |
| `edgelab/research/first_touch_decongestion.py` | construido |
| `edgelab/research/first_touch_census.py` | construido |
| `tests/research/test_first_touch_*.py` | **10/10 en verde** |
| **runner que las llame** | **NO EXISTÍA** |

Verificado: fuera de los módulos y sus propios tests, **ningún programa del repo
llamaba a `build_first_touch_census`**. Se agrega
`diag/tasa_senales/censo_primeros_toques.py`, que reusa el mismo warm-up
(`lead_days=20`) y la misma carga de parquet que `post_sepmin.py` — si
difirieran, las dos tasas no serían comparables y la contrastación
diagnóstico-vs-autoritativo perdería sentido.

## 3. El hallazgo: cuatro de seis son RECHAZADOS por el censo

`build_first_touch_census` exige, para poder probar la regla anti look-ahead:

- `zone_id` **string no vacío**
- `ZONE_TOUCHED` con **`touch_count` entero**, donde `touch_count == 1` identifica
  el primer toque

Medido sobre 6E 03-26, y verificado en la fuente de cada indicador:

| indicador | `zone_id` | `touch_count` | ¿entra? | por qué |
|---|---|---|---|---|
| **BigTrap2** | `str` `'10_B'` | **sí** | **SÍ** | — |
| ~~aVolCellPOI2~~ | **`int`** | sí | **NO** | `avolcellpoi2.py:229` pasa el valor crudo; el `str()` está sólo en el CSV |
| VolTicksPOC2 | **`int`** `1` | sí (`voltickspoc2.py:125`) | **NO** | `zone_id` entero, no string |
| Gaps2 | `str` `'G000001'` | **NO** | **NO** | ordinal enterrado en `"epoch=" + str(...)`, `gaps2.py:141` |
| HFTZones2 | `str` `'Z000001'` | **NO** | **NO** | idem, `hftzones2.py:362` |
| AACloseOpenDiffs | `str` `'D000001'` | **NO** | **SIN POBLACIÓN** | no emite `ZONE_TOUCHED`: **no es rechazo, es un cero silencioso**. Ver §3-bis |

Claves reales de `ZONE_TOUCHED`, medidas sobre 6E 03-26 (2025-12-12 → 2026-01-20):

```text
Gaps2         ['extra','price','seq','state','ts_ns','type','unix_ms','zone_id']
HFTZones2     ['extra','reason','seq','ts_ns','type','unix_ms','zone_id']
aVolCellPOI2  [...,'touch_count',...]                     <- entra
AACloseOpenDiffs   NO EMITE ZONE_TOUCHED: 16.090 ZONE_CREATED, CERO toques
```

Confirmado en fuente: `touch_count` lo emiten **sólo tres** de los seis
(`grep -l touch_count edgelab/bridge/indicators/*.py` → `avolcellpoi2`,
`bigtrap2`, `voltickspoc2`). Los otros tres codifican el ordinal como
**texto libre** dentro de un campo `reason`.

### Lo que esto significa

**La población autoritativa se puede construir hoy para UNO de los seis:
`BigTrap2`.**

Y hay que separar **dos clases de rechazo**, porque no se arreglan igual:

- **Desajuste de contrato** — `VolTicksPOC2` (`zone_id` entero), `Gaps2` y
  `HFTZones2` (ordinal en texto libre). Son **fallas de tipo**: el dato existe,
  está mal expuesto. Arreglables.
- **Ausencia semántica** — `AACloseOpenDiffs` emite **16.090 `ZONE_CREATED` y
  CERO `ZONE_TOUCHED`**. No es un campo mal tipado: **el concepto de "primer
  toque" no existe** para ese indicador. La entrada primaria que EXPLORE-001
  define **no está definida** ahí. Normalizar el contrato no lo resuelve; habría
  que **definir qué es un toque** para ese indicador, que es una decisión de
  diseño, no un arreglo. Y el que sí entra sin dudas —**BigTrap2**— es justamente aquel cuyo
hábitat son las barras de tick, donde **la paridad sigue rota** (PRED-003
refutada: 3,91 % en K=25, 81,78 % en K=10). Su tasa en `time:1` es la del
laboratorio, no la de su hábitat.

## 3-bis. Un FAIL-OPEN en el censo: el cero que parece un dato

`AACloseOpenDiffs` emite **23.629 eventos, todos `ZONE_CREATED`, cero
`ZONE_TOUCHED`**. `extract_first_touch_events` devuelve lista vacía, y el censo
sale:

```json
{"status": "COMPLETE", "raw_count": 0, "post_sep_count": 0,
 "zero_raw_sessions": 30, "session_count": 30}
```

**Eso es peor que un rechazo.** Un rechazo grita; un cero parece un dato. Quien
lea `raw_count: 0` va a entender *"este indicador no produce señales"*, cuando la
verdad es *"este indicador no tiene concepto de toque"*. Son dos afirmaciones
completamente distintas y el JSON no las distingue.

**Es la cuarta instancia del patrón de esta sesión** —B3, H2, H-GPT-1, y ahora
ésta—: un número publicado cuyo significado nadie puede reconstruir. Acá con una
vuelta de tuerca: no es que falte el denominador, es que **la ausencia de la
población produce un resultado con formato de medición.**

**Arreglo, sin tocar el módulo congelado:** el runner clasifica aparte. Cero
toques **con** creaciones ⇒ `sin_poblacion`, no un censo de cero. Verificado en
piloto: `AACloseOpenDiffs → SIN POBLACION (7.861 creaciones, 0 toques)`.

`first_touch_census.py` **no se tocó** —tiene tests propios—; si conviene que la
abstención viva ahí adentro en vez del runner, es decisión de Nico.

## 4. Qué NO hice, y por qué

**No relajé el contrato del censo.** Habría bastado un `str(zone_id)` para que
`VolTicksPOC2` pasara, y aceptar el `epoch=N` parseado del texto para los otros
dos. Las dos cosas son **relajar un gate fail-closed después de ver que
rechaza**, que es exactamente lo que `CLAUDE.md` prohíbe. Además el rechazo no es
caprichoso: un ordinal en texto libre no es un campo tipado, y la regla anti
look-ahead de EXPLORE-001 se apoya en poder **probar** cuál fue el primer toque.

## 5. D3, revisada

D3 preguntaba si `sep_min` sirve como criterio de selección. **La pregunta está
mal planteada mientras cinco de seis no puedan producir la población.** Con UN
candidato no hay selección que hacer, y §3.3 pide **tres** hipótesis
mecánicamente distintas.

Y el único que entra, `BigTrap2`, es el que está bloqueado por PRED-004: su
hábitat son las barras de tick, donde la paridad sigue rota. **Su censo en
`time:1` es del laboratorio.**

> **§3.3 no se puede llenar hoy por ningún camino.** No es que falte elegir: no
> hay entre qué elegir.

D3 se **suspende**, y en su lugar queda una decisión anterior y más concreta:

### Decisión para Nico — dos caminos, y no los elijo yo

**A · Normalizar el contrato de eventos de los indicadores.** Que los emisores con
falla de tipo (`VolTicksPOC2`, `Gaps2`, `HFTZones2`) expongan
`zone_id` string y `touch_count` entero. Es trabajo mecánico y acotado, **pero
toca kernels con paridad declarada** — y cambiar lo que emite un kernel puede
invalidar su oráculo. Hay que verificar por indicador si el campo agregado entra
en la comparación de paridad antes de tocarlo.

**B · Reducir el alcance de §3.3 a los indicadores que ya pueden.** Honesto e
inmediato, pero deja la elección de hipótesis entre uno o dos candidatos, cuando
la regla de selección de §3.3 pide **preferir mecánicamente distintos** — con uno
no hay nada que preferir. Y `AACloseOpenDiffs` queda fuera en los dos
caminos hasta que se decida qué es un toque para él.

**Mi lectura:** **A**, y ya no como preferencia sino porque **B no existe**: con
un solo candidato no hay §3.3 reducida posible. Empezar por `VolTicksPOC2` y
`aVolCellPOI2`, que son el mismo arreglo de una línea (el tipo de `zone_id`) y el único cuya tasa post-filtro
**dice algo del indicador** —sobrevive el 46,6 % contra el 1,8 % de
`AACloseOpenDiffs`—, así que es el que más aporta a la selección. Requiere
verificar antes si `zone_id` participa de su comparación de paridad.

## 6. Estado del runner

`diag/tasa_senales/censo_primeros_toques.py`. Piloto de 6 sesiones ejecutado:
pipeline end-to-end funcionando, `BigTrap2` produce censo, `VolTicksPOC2`
rechazado con el mensaje correcto. El rechazo se reporta **por indicador** en
`rechazados`, sin abortar la corrida: un indicador que no puede entrar no
invalida a los que sí.
