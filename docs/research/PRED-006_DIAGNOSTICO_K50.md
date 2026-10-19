# Diagnóstico de K=50 — el ancla juzgó unicidad con el rango truncado

**Fecha:** 2026-08-09 · Clasificación **hecha y medida**, sin capturas nuevas.
**Origen:** Nico — *«me parece bastante raro que funcione todo menos 50 tick.
Tan raro que no creo que la causa sea tan difícil de determinar.»* Tenía razón:
la causa estaba en el log y en los datos ya capturados.

---

## 1. Hecho 1 — las barras de NT8 son correctas

Se comparó el OHLCV de la barra que declara cada mismatch (`open_bar`,
`high_bar`, `low_bar`, `close_bar`, `vol_bar`) contra
`bars.build_tick_bars(tk, 50)`:

```
offset  +0 : OHLCV de NT8 == Python en 790/790 (100.0%)
offset  -1 : 1/790     offset +1 : 0/790
```

**El constructor de barras no es la causa.** Python reproduce las barras de NT8
exactamente, volumen incluido. El problema es la **atribución**: qué eventos se
le asignan a cada barra.

## 2. Hecho 2 — la firma OHLCV no es inyectiva en barras monótonas

Para cada K, cuántos offsets `d ∈ [0, 4K]` reproducen el OHLCV de la barra 1:

| K | OHLCV de la barra 1 | offsets que la reproducen |
|---:|---|---|
| 10 | (23303, 23305, 23293, 23297) | **[10]** |
| 15 | (23293, 23305, 23293, 23298) | **[15]** |
| 25 | (23300, 23305, 23296, 23296) | **[25]** |
| **50** | **(23296, 23296, 23292, 23292)** | **[49, 50]** |
| 100 | (23291, 23296, 23290, 23294) | **[100]** |

En K=50 la barra 1 es **monótona descendente**: `open == high` y
`close == low`. Con los ticks a la vista:

```
tick[49] = 23296 vol=1        tick[98]  = 23292 vol=1
tick[50] = 23296 vol=1        tick[99]  = 23292 vol=1
                              tick[100] = 23291 vol=8

ventana [49, 99)  -> o=23296 h=23296 l=23292 c=23292 vol=215
ventana [50,100)  -> o=23296 h=23296 l=23292 c=23292 vol=215
```

`px[49] == px[50]`, `px[98] == px[99]` y `vol[49] == vol[99]`. **Dos ventanas
adyacentes producen exactamente la misma firma**, volumen incluido.

Cuando la barra abre en su máximo y cierra en su mínimo, correr un tick no mueve
ni el extremo ni el otro: sólo intercambia un evento de cada borde. Si esos dos
eventos tienen el mismo volumen, la firma completa sobrevive al corrimiento.

## 3. Hecho 3 — el rango de búsqueda se trunca, y "único" queda vacío

`nt8/BigTrap2.cs`, líneas 429–444:

```csharp
int maxOff = 4 * K;
int tope   = Math.Min(maxOff, disp - largo);   // 430: trunca por lo bufereado
...
if (hallados != 1)
{
    if (hallados == 0 && pendCutAt < 0 && disp < largo + maxOff)
        return;                                 // 441: SOLO espera si no hallo nada
    Abstener(s, hallados, disp, largo);
    return;
}
```

Si `hallados == 1` pero `tope` quedó corto —porque todavía no hay `5K` eventos
en el buffer— **ancla igual**. *«Único»* pasa a significar **«único entre los
offsets que alcancé a probar»**, que no es unicidad.

Con el rango completo, K=50 habría encontrado `hallados == 2` y se habría
**abstenido** — el comportamiento correcto. El defecto no es el criterio OHLCV:
es la ventana sobre la que se lo evaluó.

## 4. Hecho 4 — la cadena causal cierra exacta

Offsets elegidos en `bar=1`, de los propios logs:

| K | 10 | 15 | 25 | **50** | 100 |
|---|---|---|---|---|---|
| offset | 5 | 1 | 1 | **0** | 1 |
| resultado | PASS | PASS | PASS | **FAIL** | PASS |

**Separación perfecta**: las cuatro que pasan saltearon eventos huérfanos del
arranque; la que falla no salteó nada.

Y en K=50:

```
ancla MALA        bar=1     offset=0
mismatches        barras 2..1285      (los 790, sin excepción)
re-ancla          bar=1286  offset=0  (frontera de sesión)
mismatches después                     0        -> 4.900 barras limpias
```

El tramo de mismatch es **exactamente** `[ancla mala, re-ancla)`. Ni uno afuera.

## 5. La implicación seria: las otras cuatro pasaron por suerte

El defecto es **latente en todas las resoluciones**. Que 10, 15, 25 y 100 hayan
dado cero depende de dos cosas que no son propiedades de K:

1. que su barra de anclaje **no** tuviera firma degenerada, y
2. cuántos eventos hubiera bufereados en ese instante — **batching de NT8**.

Con otra ventana, el mismo defecto puede morder en 25 o en 100.

**Esto califica el PASS de PRED-004**: es real para esa ventana, pero **no está
garantizado estructuralmente**. La corrección lo convierte en estructural.

## 6. Por qué no hizo falta `TickBarDiag`

`TickBarDiag` separa H1 (stream) / H2 (cortes) / H3 (atribución). El §1 ya
resolvió esa pregunta con datos que teníamos: las barras coinciden 790/790, así
que es H3. Lo demás salió de los offsets que el propio `.cs` ya publicaba y de
una consulta al parquet.

Vale registrarlo como método: **el instrumento correcto a veces es leer lo que
el log ya dice.** Se ahorró una captura y una sesión de NT8.

## 7. Lo que sigue

El fix está pre-registrado en
`docs/predictions/PRED-006_anclaje_rango_completo.json` **antes** de tocar
código, con su criterio de refutación. Y se declara por adelantado algo que
importa:

> **Si K=50 pasa a ABSTENERSE, es un resultado aceptable, no un fallo.**
> Abstenerse ante una firma ambigua produce menos zonas, no zonas equivocadas.
> La grilla de §2-ter se recortaría por una razón medida y declarada, en vez de
> por un defecto silencioso.
