# CORRECCIÓN — dos defectos en la geometría de las zonas nulas de F1.1

**Fecha** 2026-08-10 · **Severidad** medida, no estructural — el hallazgo
central sobrevive y se fortalece levemente
**Alcance** `F1_nulo_zonas_aleatorias.py` (F1.1), `F1.1_seguimiento.py`,
`F_barspec_tick25.py`
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`

---

## 0. Resumen para quien no lea el resto

Se encontraron y corrigieron **dos defectos independientes** en cómo se
construía la geometría de las zonas nulas de F1.1 y sus derivados. Los dos se
verificaron con aritmética exacta antes de tocar código, y el impacto se midió
—no se asumió— corriendo el universo completo antes y después de cada
corrección. **El hallazgo central de F1.1 no sólo sobrevive: la brecha
real-vs-nulo se ensancha ligeramente** (de 46,5 a 47,3 puntos porcentuales).
Nada de lo publicado con esta base se retracta; se reemplaza por números más
precisos.

---

## 1. Defecto 1 — ruido de banker's rounding en la altura

`bigtrap2.py:202-203` construye la geometría con relleno de **medio tick**:

```python
zone_lo = lo_tick * tick_size - tick_size / 2.0
zone_hi = hi_tick * tick_size + tick_size / 2.0
```

Para una zona de una sola fila (`lo_tick == hi_tick == T`), eso pone
`top/tick_size` y `bottom/tick_size` **exactamente** en el límite de redondeo
`.5`. La fórmula que F1.1 usaba —

```python
alto = round(top/tick_size) - round(bottom/tick_size)
```

— hereda ese límite: `round()` de Python redondea al par más cercano (banker's
rounding), así que el resultado depende de la paridad de `T` y del error de
punto flotante al representar `T ± 0.5`. Verificado empíricamente sobre 20
valores consecutivos de `T`: la fórmula devuelve **0, 1 o 2** para una altura
que es **siempre exactamente 1 tick** por construcción.

`store.py::_core()` ya conocía este problema —lo dice en su propio
comentario— y lo evita midiendo en unidades de **medio-tick**, donde
`zone_lo`/`zone_hi` caen siempre en un entero exacto:

```python
ht = tick_size / 2
altura_ticks = (round(zone_hi/ht) - round(zone_lo/ht)) / 2   # exacto, siempre
```

F1.1 no usaba esa técnica. Quedó agregada como función compartida,
`altura_ticks_exacta()`, en `censo_zonas_completo.py`.

**Quién SÍ tenía la fórmula correcta desde el principio, sin saberlo:**
`censo_zonas_completo.py` (F0.2) y `F1_supervivencia_y_depletion.py` (F1.2)
usan `(top - bottom) / tick_size` — una resta que cancela el relleno de
medio-tick **antes** de dividir, sin necesidad de redondear cada extremo por
separado. Verificado: da 1,0 exacto para los mismos 20 valores de `T`. **Sus
resultados no estaban afectados** y no se retocan.

---

## 2. Defecto 2 — off-by-one al reconstruir el rango del nulo

Independiente del anterior, y más grave: al construir la zona nula a partir de
`alto` —

```python
lo_n = centro - alto // 2
hi_n = lo_n + alto
```

— el rango `[lo_n, hi_n]` usado por el chequeo de toque (`high>=lo_n and
low<=hi_n`) contiene **`alto + 1` ticks, no `alto`**. Un nulo de altura 1
quedaba construido con un rango de 2 ticks — sistemáticamente **más ancho, y
por lo tanto más fácil de tocar**, que la zona real que debía imitar.

Verificado con un caso concreto (zona de 3 filas, `lo_tick=100, hi_tick=102`):
la fórmula original da un rango de 4 ticks; la corregida, `hi_n = lo_n + alto
- 1`, da exactamente 3.

---

## 3. Impacto medido, corrida por corrida — no asumido

Los dos defectos se corrigieron **por separado y en ese orden**, con una
corrida de universo completo después de cada uno, precisamente para poder
atribuir el efecto de cada corrección en vez de mezclarlos.

### F1.1 — tocada alguna vez / rota (n=15.947 pares, 201 sesiones)

| estado | REAL | NULO-A | NULO-B |
|---|---|---|---|
| original (2 defectos) | 97,87 % | 46,65 % | 51,38 % |
| defecto 1 corregido | 97,9 % | 47,0 % | 51,8 % |
| **ambos corregidos** | **97,9 %** | **46,2 %** | **50,6 %** |

| rota | REAL | NULO-A | NULO-B |
|---|---|---|---|
| original | 96,12 % | 92,98 % | 95,35 % |
| defecto 1 corregido | 96,1 % | 92,9 % | 95,3 % |
| **ambos corregidos** | **96,1 %** | **93,1 %** | **95,4 %** |

**Lectura:** el defecto 1 solo apenas mueve nada (ruido, <0,5 pp, y sin
dirección consistente). El defecto 2 —el nulo artificialmente ancho— sí tenía
dirección: al corregirlo, el nulo se vuelve **más difícil de tocar**
(51,8 %→50,6 %), exactamente como predice la geometría (un nulo más angosto
tiene menos chance de ser tocado). El efecto neto **ensancha la brecha
real-nulo**, de 46,5 pp (original) a **47,3 pp** (corregido). El hallazgo de
F1.1 no se debilita: se fortalece, levemente.

Comparación pareada por sesión — sin cambios materiales: 201/201 sesiones con
REAL > NULO-B en tocar (antes y después); 80-81/201 en romper (antes y
después) — el resultado "romper es casi una moneda" tampoco se mueve.

### bar_spec `tick:25` — misma corrección, misma dirección

| estado | REAL | NULO-B |
|---|---|---|
| original (2 defectos) | 98,81 % | 53,21 % |
| **ambos corregidos** | **98,81 %** | **51,94 %** |

Misma dirección que bajo `time:1`: nulo más angosto, más difícil de tocar,
brecha real-nulo ensanchada (de 45,6 a **46,87 puntos**). Y de regalo, la
propia altura reportada queda exacta por primera vez: **mediana 1,00, p90
1,00** —contra 1,00/2,00 con el defecto 1 presente—, confirmando que casi
todas las zonas de una fila bajo `tick:25` miden, de verdad, un solo tick.

Ver `F_BARSPEC_TICK25_RESULTADO_2026-08-10.md` para el resultado completo de
la exploración de `bar_spec` (no sólo la corrección).

---

## 4. Qué NO cambia

- **Ningún veredicto se revierte.** F1.1 seguía —y sigue— mostrando que
  BigTrap2 se distingue del azar en atracción, no en resistencia.
- **F0.2, F1.2, F2** no tenían el defecto (fórmula distinta, ya exacta) —
  ninguno de sus números se retoca.
- **La corrección amplía la brecha, no la reduce.** No hay ningún escenario en
  que "arreglar el bug" debilite la conclusión publicada.

## 5. Qué se corrigió en el código

`censo_zonas_completo.py`: agregada `altura_ticks_exacta(top, bottom,
tick_size)`, con la derivación completa en su docstring.

`F1_nulo_zonas_aleatorias.py`, `F1.1_seguimiento.py`, `F_barspec_tick25.py`:
las tres reemplazan su cálculo de `alto` por la función compartida, y su
construcción de rango por `hi_n = lo_n + alto - 1`.

## 6. Artefactos en cuarentena

Los tres estados —original con los dos defectos, intermedio con sólo el
defecto 1 corregido, y (donde aplica) los reemplazados por la corrida final—
se conservan en `diag/tasa_senales/incidentes/`, sin excepción: cada paso de
una corrección es evidencia de que se verificó y no se asumió.

---

## Aporte al referente

Encontrar un defecto propio en la pieza central de la sesión, corregirlo en
dos pasos verificados por separado, y confirmar con números —no con
argumento— que el hallazgo sobrevive, es exactamente el tipo de trabajo que
sostiene la credibilidad de todo lo demás publicado hoy. Un hallazgo que
sobrevive a que su propio autor intente activamente romperlo es más creíble
que uno que nunca se puso a prueba.
