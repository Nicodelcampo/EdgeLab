# INC-006 — La frontera del holdout venció sola

**Estado:** cerrado (revertido y blindado en el mismo turno).
**Severidad:** alta. Des-selló un mes de holdout y dejó la suite en rojo 9 horas
sin que nadie lo notara.

## Qué pasó

El commit `e82f090`, **etiquetado `chore`**, cambió una línea:

```
-HOLDOUT_START_ISO = "2026-07-01T00:00:00"
+HOLDOUT_START_ISO = "2026-08-01T00:00:00"
```

y ajustó `docs/NORTH_STAR.md` y `docs/edge_validation_contract.md` §G4 para que
lo acompañaran, con la justificación de que julio de 2026 "fue absorbido
formalmente a la muestra pre-holdout tras las validaciones estructurales de
INC-002 e INC-005".

Eso no es una repartición metodológica. Es **des-sellar** un mes que ya estaba
protegido, que es exactamente lo que un holdout existe para impedir.

## La parte que lo hace distinto de un error común: venció solo

El daño no fue inmediato. Con frontera en 2026-08-01 y reloj en 2026-07-31, la
frontera apuntaba al **futuro**: no había ni un día del lado sellado, pero
tampoco había data posterior, así que nada se veía raro.

Cuando el reloj cruzó el 2026-08-01, la misma línea, sin que nadie la tocara,
pasó a des-sellar julio entero. **El commit era una bomba de tiempo, no un
error de estado.** Ninguna revisión del diff en el momento de escribirlo lo
habría mostrado como dañino.

## Cronología

| cuándo | qué |
|---|---|
| 2026-08-01 03:16 | `e82f090` escrito y commiteado, etiquetado `chore` |
| 2026-08-01 00:00 | el reloj cruza la frontera: julio queda des-sellado |
| 2026-08-01 12:36 | detectado al correr la suite de referencia (3 en rojo) |
| 2026-08-01 (este turno) | revertido, blindado con la regla 95, INC-006 abierto |

## Por qué los tests no lo atajaron

Había tres tests del firewall y **los tres fallaron cuando ya era tarde**, no
antes. El motivo es de diseño, no de cobertura: comparaban contra
`HOLDOUT_START_ISO`, es decir **contra la misma constante que el commit había
corrompido**. Un test que lee el valor bajo prueba como referencia no prueba
nada; se mueve junto con el error.

Los tres que quedaron en rojo:

- `tests/research/test_holdout_guard.py::test_development_touching_holdout_raises_and_logs`
- `tests/research/test_puerta_unica_holdout.py::test_por_defecto_el_holdout_no_sale_nunca`
- `tests/research/test_puerta_unica_holdout.py::test_los_atlas_reales_no_devuelven_holdout`

El tercero es el que mide el daño real: corre contra el manifiesto **real** y
asserta `all(d["fecha"] < "2026-07-01")`. Falló. O sea que la puerta única
estaba entregando días de julio como material de research — el modo de falla de
INC-002, reabierto por otra vía.

## Hallazgo colateral: la suite ya estaba en rojo antes

`35c71a6` (cuarentena INC-005 de 07-01 a 07-16) introdujo un `continue` que
descartaba los días quemados **antes** de clasificarlos por el sello. Eso puso
`descartados_holdout` en 0 y rompió dos de los tres tests de arriba, sin tocar
ningún test. `e82f090` rompió el tercero.

Conclusión: el baseline "510 passed" **no es reproducible en ninguno de los dos
commits**, y las tres líneas reportadas como *skipped* en el traspaso eran en
realidad *failed*. Se conecta con INC-004 (procedencia de las líneas de suite).

## Corrección

**1. Revertida la frontera** a `2026-07-01T00:00:00` en `holdout_guard.py`, y
reconciliados `docs/NORTH_STAR.md`, `docs/edge_validation_contract.md` §G4 y
`CLAUDE.md` (que nunca había dejado de decir 2026-07-01 → 2026-12-31; el commit
dejó el código contradiciendo la instrucción permanente del proyecto).

**2. Blindaje estructural (regla 95).** La frontera efectiva ya no es un literal
editable:

```python
_SELLO_ORIGINAL_ISO     = "2026-07-01T00:00:00"   # historia, no configuración
_FRONTERA_DECLARADA_ISO = "2026-07-01T00:00:00"   # editable
HOLDOUT_START_ISO = _resolver_frontera()          # = min(sello, declarada)
```

Adelantarla (sellar **más**) sigue siendo posible. Atrasarla es aritméticamente
imposible: reescribir `_FRONTERA_DECLARADA_ISO` a `2026-08-01` hoy es un no-op,
y hay un test que lo verifica reproduciendo el edit exacto de este incidente.

**3. Blindaje temporal.** `verificar_sello()` levanta `SelloInvalido` si la
frontera queda por delante de **la fecha del sistema** — la condición de "no
hay un solo día sellado". Es la única forma de atajar una bomba de tiempo: el
test corre contra el reloj, no contra un literal, y habría fallado el 2026-07-31,
el día que se escribió el commit, no nueve horas después del daño.

**4. Cuarentena de INC-005 portada** a esta rama (reimplementada, no
cherry-pick — ver abajo), y corregido el orden que rompía la contabilidad.

## Regla 96 — la etiqueta del commit es parte del control de cambios

`chore` significa "no cambia comportamiento". Este commit movía la frontera del
holdout, que es la separación metodológica más fuerte del proyecto. La etiqueta
es lo que lo hizo invisible: nadie relee un `chore`.

**Regla:** un cambio que toca el firewall del holdout, los gates G0–G5, el
preregistro o la semántica de validación **no puede** ir como `chore`,
`docs`, `style` ni `refactor`. Va como `fix(...)` o `feat(...)` con el
mecanismo afectado en el scope, y se consulta con Nico antes (`CLAUDE.md`:
"cambios de semántica de validación se consultan con Nico"). Una etiqueta
que subdeclara el alcance de un cambio es un defecto de control de cambios,
no una cuestión de estilo.

## Regla 95 — la frontera es un sello, no un cursor

Ya enunciada arriba y ejecutada en código. Se registra acá para que quede
citable: **ningún mecanismo del proyecto puede reducir el material protegido
como efecto del paso del tiempo.** Si hay que abrir holdout, se abre por el
protocolo de apertura (una por candidato, registrada en el log), nunca moviendo
la frontera.

## Sobre la cuarentena portada (declaración de método)

`342bbfd` (cuarentena ampliada a 2026-07-24) vivía sólo en `spike_in_38` y nunca
llegó a `foundation/f0b-compatibility-probe`. **Se reimplementó, no se hizo
cherry-pick**, por dos razones:

1. `342bbfd` reintroduce el `continue` previo a la clasificación por sello, que
   es el defecto de contabilidad descrito arriba. Un cherry-pick habría traído
   el bug junto con el rango.
2. Su rama de origen arrastra `e82f090` (la frontera corrompida) como ancestro;
   traer el commit tal cual mezclaba dos decisiones opuestas en el mismo árbol.

Lo portado es el **rango** (2026-07-01 → 2026-07-24) y su justificación (censo
con `min()`/`max()` reales: la extracción de oráculos alcanza 2026-07-24T17:59:20
en `BigTrap2_diag_tick25`, `BigTrap2_time1_v2` y `Gaps2`). La implementación es
nueva.

**Cuarentena y frontera son mecanismos distintos y hacen falta los dos.** La
cuarentena quema días por contaminación de *procedencia* (el dato no sirve para
nada, ni siquiera para una apertura sancionada). La frontera sella por
*metodología* (el dato es bueno y justamente por eso no se mira). Hoy el rango
de cuarentena cae entero dentro del holdout, así que se solapan; eso es
coincidencia del calendario, no equivalencia. Se contabilizan por separado
(`descartados_holdout` y `descartados_cuarentena`).

## Pendiente declarado (no resuelto en este turno)

`tools/censo_es_nq.py:91` define `HOLDOUT_DESDE = "2026-07-01"` **hardcodeada**:
una segunda fuente de verdad en código. Hoy coincide con el sello, así que no
hay conflicto activo, pero el docstring de `holdout_guard.py` afirmaba que no
existía ninguna otra definición y eso era falso. Unificarla es cambio de
semántica y se decide con Nico.
