# Corrección — leí mal «margen», y la celda **no** es ciega

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado
**Corrige:** el veredicto «CIEGA» de `E-R1 v0.3 DRAFT` §9.3 y del commit `3d6668a`.

---

## 1. El error

Calculé el margen como **efecto / MDE**, deduciendo un efecto de 0,6175 ticks a
partir del *«margen medido a f=10 es 1,60×»* de la spec. Con eso concluí que a
`f = 2,13` la celda quedaba **ciega** (margen 0,78).

**`margen` no es eso.** La tabla canónica de `docs/spike_in/MDE_EXPLORE-001.md`
lo define como **fricción / MDE**, y se verifica en las cuatro filas:

| trades/día | MDE | fricción | margen publicado | `2,704 / MDE` |
|---:|---:|---:|---:|---:|
| 1 | 1,14 | 2,704 | 2,4× | 2,37 |
| 3 | 0,67 | 2,704 | 4,0× | 4,04 |
| 10 | 0,39 | 2,704 | 7,0× | 6,93 |
| 30 | 0,25 | 2,704 | 10,8× | 10,82 |

Mide si el MDE es lo bastante chico **frente al obstáculo de la fricción** — no
si supera un efecto esperado. Yo inventé el efecto.

## 2. El veredicto corregido

Con la definición canónica y la fricción vigente de **2,768**:

| `T` | `f` medida (orden B) | `MDE`~ | **margen = 2,768/MDE** | veredicto |
|---:|---:|---:|---:|---|
| 3 | 6,91 | 0,460 | **6,02×** | alcanza |
| 8 | 5,62 | 0,506 | **5,47×** | alcanza |
| 13 | 4,55 | 0,558 | **4,97×** | alcanza |
| 21 | 3,39 | 0,637 | **4,34×** | alcanza |
| **34** | **2,13** | **0,794** | **3,49×** | **alcanza** |

> **Ninguna celda es ciega.** La conclusión que te di —que `EXPLORE-001` no podía
> adjudicar— **era un artefacto de mi error de lectura**, no un hallazgo.

Y es coherente con lo que el propio spike-in concluye: *«Cero geometrías ciegas,
en cualquier régimen de frecuencia»*.

## 3. Lo que SÍ sobrevive de la medición

El error estaba en la **interpretación**, no en los números. Sigue en pie:

- **`f` real es 2,13-3,64/sesión, no ≈ 8,3.** El valor publicado venía de la
  población sin `sep_min`. Confirmado por dos implementaciones independientes.
- **Los dos órdenes de composición difieren en factor 5-6.** Sigue sin decidirse.
- **`DESACUERDO_001` sigue abierto** — la condición de validez, factor ~2.
- El MDE a la `f` real **sí** es peor que el publicado (0,79 contra 0,39): la
  potencia baja. Sólo que no lo suficiente para cegar la celda.

## 4. Contradicción que queda abierta, y no la resuelvo

**El `1,60×` de la spec no coincide con el `7,0×` del spike-in**, los dos a
`f = 10`:

- `docs/spike_in/MDE_EXPLORE-001.md` §tabla: margen **7,0×** a f=10.
- `docs/ESPEC_TEST_EXPLORE-001.md:365`: *«El margen medido a f=10 es **1,60×**»*.

No se reconcilian con el costo de multiplicidad declarado en esa misma línea
—`MDE +11,8 %`— que daría 7,0/1,118 = 6,3×, no 1,60×. Y con las *«3 hipótesis
preregistradas»* del spike-in (MDE 0,32 a f=10) daría 8,45×.

**Registrada, no resuelta**, según la regla del proyecto. Si el `1,60×` fuera el
correcto y el `7,0×` estuviera mal, mi veredicto original de «ciega» volvería a
estar sobre la mesa. **Es la pregunta más importante que queda abierta hoy**, y
es para Nico y el referente.

## 5. Cómo se produjo el error, para el registro

El mismo patrón que los otros dos de hoy: **una lectura plausible que no
cuantifiqué contra su fuente.** Tomé un número de la spec (`1,60×`), le asigné un
significado que nunca verifiqué (efecto/MDE), y construí cinco tablas encima.

Lo que lo destapó fue ir a comprobar **mi propia advertencia** — había escrito
que el efecto de 0,6175 ticks *«no lo verifiqué y pesa»*. Pesaba.

## 6. Qué decido y qué no

**Decido** retirar el veredicto «CIEGA» y la afirmación de que `EXPLORE-001` no
puede adjudicar. **No hay evidencia de eso.**

**No resuelvo** la contradicción `1,60×` contra `7,0×` del §4.

**No sello** nada: `f` sigue dependiendo de `DESACUERDO_001` y del orden de
composición.
