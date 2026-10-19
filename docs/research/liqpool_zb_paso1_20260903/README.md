# H-LIQPOOL-ZB paso 1 — la repetición de niveles NO supera al nulo de grilla

Fecha: 2026-09-03 · Diseño: `H-LIQPOOL-ZB_DISENO_2026-09-03.md` · commit pineado
`ac2d0eaf` · Kaggle · **target-free, sin outcomes, holdout intacto**.
Datos: ZB 03-26, 06-26, 12-25 pre-holdout · barras de 200 ticks · **205 sesiones**.

## Primero, el dato que justificaba hacer este test

| grilla de precios de ZB, por sesión | |
|---|---:|
| precios distintos (mediana) | **27** |
| precios distintos p10 – p90 | 19 – 41 |
| rango (mediana) | 26 ticks |
| barras por sesión (mediana) | 588 |

**Una sesión de ZB vive sobre ~27 precios y tiene ~588 barras.** Que varios
máximos caigan en el mismo nivel no es sorprendente: es casi inevitable.

## El test

Nulo: paseo aleatorio con los **mismos incrementos de la sesión barajados**,
conservando la grilla entera, la escala y la longitud. Destruye la estructura de
niveles y preserva todo lo demás. 200 réplicas por sesión.

Se cuentan los grupos de **3 o más pivotes** al mismo nivel (dentro de una
tolerancia), observado contra nulo.

| variante | obs ≥3 | nulo | p95 nulo | ratio | p |
|---|---:|---:|---:|---:|---:|
| K=2 tol=0 | 1.633 | 2.303 | 2.345 | **0,71** | 1,000 |
| K=2 tol=1 | 564 | 559 | 591 | 1,01 | 0,395 |
| K=2 tol=2 | 316 | 308 | 322 | 1,03 | 0,175 |
| K=3 tol=0 | 906 | 1.424 | 1.470 | **0,64** | 1,000 |
| K=3 tol=1 | 585 | 625 | 660 | 0,94 | 0,970 |
| K=3 tol=2 | 357 | 350 | 369 | 1,02 | 0,290 |
| K=5 tol=0 | 333 | 591 | 621 | **0,56** | 1,000 |
| K=5 tol=1 | 492 | 601 | 630 | 0,82 | 1,000 |
| K=5 tol=2 | 359 | 394 | 414 | 0,91 | 1,000 |

`K` = PivotStrength, `tol` = LevelToleranceTicks.

## Qué dice

**Ninguna de las nueve variantes supera al nulo.** Las que usan tolerancia exacta
dan **claramente por debajo** (0,56–0,71): el ZB real tiene *menos* máximos
exactamente repetidos que un paseo aleatorio sobre su misma grilla. Con tolerancia
de 1–2 ticks queda indistinguible (0,82–1,03, ningún p por debajo de 0,17).

Es decir: **la existencia de un grupo de picos al mismo nivel no es un hecho
informativo en ZB.** Ocurre tanto —o menos— que por azar sobre esa grilla. Lo que
se ve en el chart como «acumulación de liquidez» es, en su frecuencia, lo que
produce un instrumento que se mueve sobre 27 precios.

El signo por debajo de 1 tiene lectura mecánica: el precio real tiene persistencia
y los extremos se dispersan; el paseo barajado revierte más y repite niveles más
seguido.

## Qué NO dice, y es importante

**Esto mide la FRECUENCIA del objeto, no su efecto.** Es perfectamente posible que
los grupos aparezcan a tasa de azar y que, aun así, los que aparecen atraigan al
precio. Son dos afirmaciones distintas y esta sólo cierra la primera.

Lo que sí hace es **bajar el prior**: si el objeto no se distingue del azar en su
existencia, la hipótesis pasa a depender enteramente de que la atracción sea real
—y esa es exactamente la que murió en `BIGTRAP2_MAGNET_LINE_CLOSED`, contra un
control sin zona con la misma geometría.

## Limitación declarada

Todo esto es sobre **barras de 200 ticks**. La estructura de pivotes depende de la
resolución, y las capturas de Nico podrían ser otra. Si la resolución cambia el
resultado, este acta no lo sabe. Es la primera cosa a variar si se sigue.

## Cómo podría refutarse este resultado

Que a otra resolución de barra, o con otra definición de pivote, la tasa observada
supere al nulo de grilla de forma consistente. El barrido de `K` × `tol` ya cubre
nueve combinaciones y ninguna lo hace, pero la resolución quedó fija.

## Recomendación

Antes de construir el detector completo y el censo, **variar la resolución de
barra**: es la única dimensión no explorada que podría cambiar el veredicto, y
cuesta una corrida. Si a ninguna resolución el objeto se distingue del azar, la
familia se cierra sin haber construido el detector — que era el punto de hacer
este paso primero.

## Aporte al referente

Costó una corrida y ordena la decisión: el objeto que la hipótesis supone especial
aparece en ZB tanto como el azar lo produce. No refuta la atracción, pero mueve la
carga de la prueba entera hacia ella, y evita construir un detector con seis
parámetros sobre un objeto que todavía no se distingue del ruido.
