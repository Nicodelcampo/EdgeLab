# Paso 2 — inventario de insumos, y un bloqueante que no depende del recuento

**Fecha:** 2026-08-09 · Trabajo **sin cómputo**, hecho en paralelo mientras corre
`recuento_kT.py`. Sólo lectura de artefactos y de la spec.
**Motivo:** verificar que cuando el recuento cierre no aparezca *otro* insumo
faltante. Hoy ya perdimos ~10 h de máquina por no anticipar.

---

## 1. Las columnas que pide §7 Paso 2, y de dónde sale cada una

| columna | fuente | estado |
|---|---|---|
| indicador · clase de kernel | `CLASE_KERNEL`, sondas | **listo** |
| `T` | `T_DESIGN` `[1,2,3,5,8,13,21,34]` | **listo** |
| sesiones | universo, 201 | **listo** |
| zonas elegibles | `recuento_kT.json` | corriendo |
| `k_T == 0` | `recuento_kT.json` | corriendo |
| excursiones válidas | `recuento_kT.json` | corriendo |
| retornos válidos | `recuento_kT.json` | corriendo |
| frecuencia corregida/sesión | `recuento_kT.json` | corriendo |
| días sin eventos | `censo_primeros_toques.json` (`zero_raw_sessions`) | **listo** |
| MDE aplicable | `diag/multiplicidad/reconstruir_mde.py` — 1,14 a `f=1`, exit 0 | **listo** |
| estado de paridad/oráculo | `docs/parity_coverage/` | **listo** |
| **gate direccional** | §5.3 | **FALTA para dos de tres** |

Todo lo que no produce el recuento **ya existe**, salvo una columna.

## 2. El bloqueante: la regla direccional

§5.3 es explícita y no admite atajo:

> **`BigTrap2`** posee dirección nativa (`trapped_sellers` / `trapped_buyers`).
>
> **Indicadores sin dirección nativa** (`aVolCellPOI2`, `Gaps2`, `HFTZones2`): no
> se puede elegir *fade* o *break* después de observar cuál gana… **una prueba
> bilateral no concede gratuitamente la dirección de trading**.
>
> Antes de entrar a E-R1, cada candidato debe tener una **regla direccional
> target-free derivada de su semántica**. Si no existe:
> *el candidato puede seguir como fenómeno exploratorio, pero **NO como hipótesis
> confirmatoria de edge**.*

**No hay ninguna regla direccional redactada** para `aVolCellPOI2`. Buscado en
`docs/`: sólo aparece el criterio en la spec y la evaluación negativa del
traspaso —

> `ref_side` es **posición, no dirección**: da un estratificador… Además **muta
> durante la vida de la zona**, así que exportar el valor final sería lookahead.
> Si se exporta, tiene que ser el de **creación**.

## 3. Estado real de H1–H3, con las tres puertas juntas

| | indicador | censo autoritativo | dirección | veredicto |
|---|---|---|---|---|
| **H1** | `BigTrap2` | admitido · 9,08/ses · 201 ses | **nativa** | **hipótesis confirmatoria** |
| **H2** | `aVolCellPOI2` | admitido · 6,71/ses · 177 ses | **no existe** | fenómeno exploratorio, **no confirmatoria** |
| **H3** | `Gaps2` | **RECHAZADO** (invariante) | — | fuera |

Las tres puertas son independientes: el censo, el invariante y la dirección.
`aVolCellPOI2` pasa la primera y falla la tercera. `Gaps2` falla la primera.

**Consecuencia: EXPLORE-001 podría correr con UNA sola hipótesis confirmatoria.**

## 4. Y eso ya estaba anticipado

`ESTADO_2026-08-07_TRASPASO.md` §5.2 lo dice sin dramatismo:

> **Consecuencia que conviene tener clara: el camino a E-R1 no está bloqueado.**
> Con `BigTrap2` solo —dirección nativa— se puede avanzar. Los otros dos entran
> si hay regla defendible, y si no, no entran. **Menos hipótesis, no menos
> camino.**

Y §6.4 de la spec autoriza correr con menos de tres: *«Completar "tres" no
justifica admitir una hipótesis mal definida»*.

## 5. Lo que esto cambia para el Paso 3

Con una sola hipótesis confirmatoria, dos cosas se simplifican y una se pierde:

- **Baja la multiplicidad.** El presupuesto se declaró para tres hipótesis más el
  barrido de resolución. Correr una es conservador respecto de lo declarado, pero
  **hay que declararlo** — no se aprovecha el margen sin registrarlo.
- **La regla de banda contigua sigue aplicando** a `BigTrap2` sobre el barrido de
  resolución, que PRED-006 dejó completo (`10, 15, 25, 50, 100`).
- **Se pierde la diversificación mecánica.** §3.3 pedía mecanismos distintos
  justamente para que un negativo no matara una familia entera. Con uno solo, el
  resultado —sea cual sea— habla de `BigTrap2`, no de una clase de fenómeno.

## 6. Las dos salidas, y no las elijo yo

**A · Correr con una hipótesis confirmatoria.** Inmediato, honesto, y autorizado
por §6.4. `aVolCellPOI2` y `Gaps2` quedan como fenómenos exploratorios
registrados.

**B · Redactar la regla direccional de `aVolCellPOI2` antes de E-R1.** §5.3 lo
permite si es *target-free y derivada de su semántica*. El traspaso ya marcó el
camino y su trampa: tendría que usar `ref_side` **de creación**, nunca el final,
que sería lookahead. Exige enmienda fechada.

**Advertencia de momento.** Ya vimos las tasas de los tres. Redactar ahora una
regla direccional para el candidato que la necesita es hacerlo **con la curva a
la vista**. Es la misma razón por la que la spec dejó afuera a
`AACloseOpenDiffs`. Si se hace, tiene que ser antes de mirar un solo outcome y
con la enmienda registrada.

## 7. Lo que NO cambia

Nada de esto depende de `recuento_kT`, que sigue corriendo. Cuando cierre aporta
las cinco columnas que faltan y la respuesta a la **segunda pregunta**: si los
retornos de `Gaps2` vienen de zonas genuinamente vacías. Esa pregunta conserva
valor aunque `Gaps2` ya esté fuera por el censo — decide si cae **por mecanismo o
por estadística**, y son motivos distintos para el registro.
