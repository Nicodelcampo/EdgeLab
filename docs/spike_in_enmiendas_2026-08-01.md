# Spike-in end-to-end — enmiendas antes de correrlo

Enmienda el diseño de §108.K. Punto de inyección y forma funcional siguen
siendo los decididos: `tools/atlas_asimetrico.py::procesar_dia`, línea 189,
sobre `delta`, con `señal(Δt) = m·(Δt/H)`. Lo que cambia es **cómo** se inyecta
y **qué se sortea**.

---

## Enmienda 1 — el control `m = 0` tiene que recorrer el mismo código

### El defecto

`m = 0` estaba especificado como el control que debe reproducir el atlas nulo
bit a bit. Pero si se implementa como `delta + señal` con `señal ≡ 0`, el
control **no controla nada**, y por dos razones distintas:

1. **Rama muerta.** Escrito como `if m: delta = delta + señal`, el caso `m=0`
   no ejecuta la inyección. Se estaría verificando que el código *sin* inyección
   reproduce el atlas *sin* inyección — una tautología. Si la inyección tiene un
   bug, el control pasa igual.

2. **Cambio de dtype, que es peor porque es silencioso.** En el código real,
   `delta = (fut - p0) * direccion` es **int64**: los precios son `price_ticks`
   enteros. Sumarle un array float lo promueve a **float64**, y las
   comparaciones de barrera `delta >= P` / `delta <= -N` pasan a evaluarse en
   coma flotante. En los bordes exactos (`delta == P`) eso puede cambiar el
   resultado del primer toque. Es decir: `delta + 0.0` **no** es `delta`.

### La corrección

La inyección se ejecuta **siempre**, para todo `m` incluido 0, con dtype
invariante:

```python
# frac in [0,1]: fracción del horizonte transcurrida en cada tick futuro
frac  = (ts[i + 1:e] - t0) / float(H * 60 * 10**9)
senal = np.trunc(signo * m * frac).astype(np.int64)   # SIEMPRE int64
delta = (fut - p0) * direccion + senal                # SIEMPRE se suma
```

Con `m = 0`, `senal` es un array de ceros int64 y `delta` conserva dtype y
valor exactos ⇒ el resultado es **bit a bit** el del atlas nulo, y aun así se
recorrió la misma línea de código que en el tratamiento.

**Regla de discretización, pre-declarada:** `np.trunc`, no `round` ni `floor`.
Es la única simétrica respecto de cero, y eso importa para la Enmienda 2: con
`floor`, una señal de −0,5 ticks se convertiría en −1 y una de +0,5 en 0,
metiendo un sesgo direccional espurio en el experimento que existe justamente
para medir dirección.

**Verificación del control (condición de fracaso 1, sin cambios):** `m = 0`
debe reproducir el atlas nulo sellado bit a bit. Ahora esa verificación tiene
contenido, porque el camino recorrido es el mismo.

---

## Enmienda 2 — signo sorteado por ancla

### El defecto

`delta` ya viene orientada por `direccion` (`# a favor = positivo`). Una señal
`+m` siempre empuja hacia el lado favorable **de la dirección que el ancla ya
tiene asignada**. O sea: el experimento le regala el signo al pipeline y sólo
le pide medir la magnitud.

Eso responde "¿desde qué tamaño el pipeline mide un efecto cuyo signo ya
conoce?", que es una pregunta legítima pero **no** es la pregunta de
descubrimiento.

### La corrección: dos variantes, no una

**Variante A — magnitud (la ya especificada).**
`signo = +1` para toda ancla. La señal se alinea con `direccion`.
Da el MDE del test que el proyecto correría **si la estrategia declara su
dirección a priori**. Se conserva tal cual.

**Variante B — descubrimiento de signo (nueva).**
`signo = s_k ∈ {−1, +1}` sorteado **por ancla**, con
`s_k` independiente de `direccion`.

> **Requisito duro:** `s_k` sale de un stream de RNG **propio**, no del que
> genera `direccion` (`A0._rng(seed, contrato, fecha, ronda, k)`). Si se
> reusa ese stream, `s_k` y `direccion` quedan correlacionados y B degenera
> en A sin que se note. Semilla nueva declarada:
> **`_rng(seed, contrato, fecha, ronda, k, "spike_signo")`**, sufijo de
> dominio distinto de todos los existentes.

### Qué se espera de B, y por qué es la variante informativa

Bajo B, `E[señal] = 0` sobre el conjunto de anclas. El estadístico agregado
`p_favorable` es **insensible a B por simetría**: en promedio, la mitad de las
anclas se empuja hacia el objetivo y la otra mitad hacia el stop.

Eso **no** es una falla del experimento: es el resultado. Significa que
`p_favorable`, tal como está definido, **no puede detectar un edge cuyo signo no
esté declarado de antemano**, por grande que sea. Si B no se recupera a ninguna
magnitud de la grilla —ni siquiera en `M_forzado`— la conclusión no es "no hay
potencia", es **"el estadístico agregado es ciego al descubrimiento de signo"**,
y eso obliga a un estadístico condicionado al signo predicho antes de que
cualquier campaña de descubrimiento tenga sentido.

Por eso B se corre **aunque se anticipe que da nulo**: es la única forma de
convertir esa anticipación en un hecho medido.

### Condición de fracaso para B, escrita antes de correr (regla 91)

A las tres condiciones ya declaradas (m=0 no reproduce; `M_forzado` no fuerza
`p_favorable → 1`; no monotonía) se agrega una cuarta, específica de B:

4. **Si B recupera señal en `p_favorable`, hay un bug.** Una señal de media
   cero no puede mover un estadístico simétrico. Si lo mueve, lo más probable
   es que `s_k` esté correlacionado con `direccion` —o sea, que el requisito
   duro de arriba se haya violado— y no que el pipeline sea sensible al signo.
   Antes de celebrar nada, se verifica `corr(s_k, direccion) ≈ 0` sobre la
   muestra completa.

Ese chequeo de correlación se reporta **siempre**, con B o sin B.

---

## Resumen de lo que cambia respecto de §108.K

| | antes | ahora |
|---|---|---|
| control `m=0` | `delta + 0` (rama muerta, promoción a float64) | inyección siempre ejecutada, `senal` int64 de ceros |
| discretización | no declarada | `np.trunc`, simétrica respecto de cero |
| signo | siempre alineado con `direccion` | variante A (alineado) + variante B (sorteado) |
| stream del signo | — | sufijo de dominio propio `"spike_signo"` |
| condiciones de fracaso | 3 | 4 (se agrega la de correlación bajo B) |

**Irreversible (va al preregistro):** las dos variantes, la regla `np.trunc`, la
independencia de streams y las cuatro condiciones de fracaso.
**Ajustable:** número de rondas y el valor de `M_forzado` (se calcula del MAE
observado, no se elige).
