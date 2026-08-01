# MDE del atlas de excursiones nulas — spike-in end-to-end

**Fecha:** 2026-08-01 · **Código de inyección:** `diag/spike_in/` (este turno)
**Especificación:** `docs/spike_in_enmiendas_2026-08-01.md` (commit `17d47a6`)
**Atlas replicado:** `runs/atlas_pnk/atlas_asimetrico.json`, `config_hash`
`3c5e32e2785fc9cd`, grilla `pnk`.

## Alcance — leer antes que los números

El atlas usa **anclas placebo**: instantes aleatorios, con separación mínima de
120 min. Esto valida la **agregación y la potencia del test**, NO el kernel de
detección de zonas. Además, las anclas placebo están máximamente dispersas; una
estrategia real ancla en *clusters*, que tienen menos observaciones efectivas.
Por eso **el MDE de acá es un piso optimista**: el test real tendrá menos
potencia, no más.

Consecuencia práctica de esa asimetría: **este experimento puede matar de forma
concluyente, pero no puede bendecir.**

## Parámetros

| | |
|---|---|
| días | 185 (de las 188 fechas del atlas sellado; 3 no resueltas, ver abajo) |
| rondas | 25 |
| anclas | ~10-11 por día-ronda (la separación de 120 min recorta 480 candidatos) |
| geometrías | 40 = 4 horizontes {30,60,90,120} × 10 pares P/N |
| grilla de m | 0 · 0,1 · 0,2 · 0,5 · 1 · 2 · 4 ticks al horizonte |
| forma | rampa `señal(Δt) = m·(Δt/H)`, discretizada con `np.trunc` |
| bootstrap | apareado, bloques de DÍA, 2000 réplicas, semilla `20260801` |
| semilla de anclas | `20260727` (la del atlas, sin cambiar) |
| semilla del signo (B) | `_rng(seed, contrato, fecha, ronda, k, "spike_signo")` |

Las 3 fechas no resueltas son `2025-10-31`, `2025-11-19`, `2025-12-15`: no
tienen fila en el censo vigente. Es el mismo hallazgo abierto de la ronda X;
no se forzó una atribución.

## Unidad 1 — los dos extremos

### 1A · control `m = 0`: **PASA, bit a bit**

Comparado contra `atlas_asimetrico.procesar_dia` **real** importado del módulo
de producción, **ancla por ancla y campo por campo** — no contra el JSON
agregado, que sólo tiene S/T por día y no vería una compensación entre anclas.

> **116 anclas · 6 días × 2 rondas · IDÉNTICO en todos los campos.**

La enmienda de `17d47a6` era necesaria y se verificó: `senal` se construye
siempre en `int64`, así que con `m=0` es un array de ceros y `delta` conserva
dtype y valor. Un `delta + 0.0` habría promovido a `float64` y cambiado la
semántica de las comparaciones de barrera en los bordes exactos.

### 1B · control de forzado: **la condición estaba mal especificada. Es mía.**

`M_forzado = P_max + max|MAE| = 13 + 160 = 173` ticks **no** lleva
`p_favorable` a 1,0 con la señal en rampa: fallan **19 de 40** geometrías, y
fallan concentradas en los horizontes largos:

| horizonte | geometrías que no llegan a 1,0 |
|---|---|
| H30 | 0 de 10 |
| H60 | 1 de 10 |
| H90 | 8 de 10 |
| H120 | 10 de 10 |

**No es defecto del pipeline. Es defecto de la fórmula que escribí en
`17d47a6`.** Con una rampa, `señal(Δt→0) → 0`: una caída adversa temprana
dispara el stop antes de que la rampa haya entregado nada. **No existe ningún
`m` finito que fuerce el resultado con señal en rampa**, y el patrón por
horizonte lo confirma (a mayor H, más lenta la rampa, más fallas).

Corregido con un **escalón** sólo para este control (`señal = m` constante),
que sí tiene magnitud de forzado bien definida y ejercita el mismo camino de
inyección:

> **forma = escalón, m = 173 ticks → `p_favorable = 1,0` en las 40 de 40.**

El camino de inyección queda **probado correcto**. La grilla sigue usando la
rampa, que es la forma realista.

### Condición 3 · monotonía: **PASA**

`Δ` es monótona no decreciente en `m` en **las 40 geometrías**, sin una sola
violación.

## Unidad 2 — la grilla (variante A: signo alineado)

### Hallazgo estructural: no existe edge sub-tick

`Δ` es **exactamente +0,0000** para `m ∈ {0,1 · 0,2 · 0,5 · 1,0}` en las 40
geometrías. No es "pequeño": es cero exacto, y la causa no es falta de potencia.

Los precios viven en una **grilla de ticks enteros**. Una deriva de menos de un
tick acumulado se cuantiza a cero:

| m | señal máx (ticks) | fracción del horizonte con señal ≠ 0 |
|---|---|---|
| 0,1 – 0,5 | 0 | 0,000 |
| 1,0 | 1 | 0,001 |
| 1,5 | 1 | 0,334 |
| 2,0 | 2 | 0,501 |
| 4,0 | 4 | 0,751 |

**Un edge sub-tick no es indetectable por falta de datos: no existe como objeto
en un mercado cuantizado.** Es una propiedad del problema, no del test.

### El MDE es una COTA, no una estimación puntual

> **MDE ≤ 2 ticks**, con la señal en **RAMPA**.

No es "entre 1 y 2". Como todo lo sub-tick se cuantiza a cero, el `m` más chico
representable es 1 tick: **la medición está censurada por abajo**. Es una cota
superior y, como estimación puntual, **no puede entrar al preregistro**.

**Forma de señal, declarada:** la grilla se corrió con **rampa**
(`unidad2_grilla.py::FORMA = "rampa"`). El **escalón** se usó **sólo** para la
validación del camino de inyección en 1B (40/40), **no** como fuente del MDE: un
edge real se parece a una deriva, no a un salto instantáneo. No hizo falta
re-correr nada.

**Re-especificación de la condición de forzado** (la reparación va en la spec, no
en la señal): *con señal en **escalón** de magnitud `P_max + max|MAE|`,
`p_favorable` debe dar 1,0 en 40/40; ése es el control del camino de inyección.
Con señal en **rampa** no existe magnitud de forzado —`señal(Δt→0)→0`— así que la
rampa no admite ese control y se usa sólo para la grilla.*

### Efecto recuperado

Todas las geometrías recuperan señal con IC95 que excluye cero en `m = 2` y
`m = 4`. Rango del efecto:

| m | Δ mínimo | Δ máximo |
|---|---|---|
| 2 ticks | +0,0031 (H120_P5_N5) | +0,0311 (H30_P8_N13) |
| 4 ticks | +0,0132 (H120_P5_N5) | +0,0987 (H30_P8_N13) |

## Unidad 2 — variante B (signo sorteado): **la condición 4 estaba mal escrita**

**Chequeo obligatorio de independencia de streams: PASA.**

> `corr(s_k, direccion) = −0,00191` sobre **47.213** anclas. Los streams son
> independientes; B **no** degeneró en A. El sufijo de dominio `"spike_signo"`
> en `_rng` hizo su trabajo.

**B recupera efecto**, con IC95 que excluye cero en `m = 4` en 40/40 y en
`m = 2` en las 10 geometrías de H30. Según la condición de fracaso 4 que escribí
en `17d47a6`, eso sería un bug: *"una señal de media cero no puede mover un
estadístico simétrico"*.

**Esa condición era incorrecta, y el error es mío.** `p_favorable` es una
probabilidad de **primer paso**, que es una función **no lineal** de la deriva.
Si es convexa, una señal de media cero la mueve hacia arriba por desigualdad de
Jensen, sin que haya bug alguno: `E[p(±m)] > p(0)` aunque `E[±m] = 0`.

La condición 4 asumió linealidad sin decirlo. La evidencia de que es Jensen y no
un defecto:

| prueba | resultado |
|---|---|
| geometría con `p₀` más cercana a 0,5 (H120_P5_N5, `p₀=0,4973`) | `Δ_B = 0,0000` **exacto** — la convexidad se anula en el punto de inflexión |
| geometrías lejos de 0,5 (`\|p₀−0,5\|>0,20`) | `Δ_B` medio = +0,0087 |
| geometrías cerca de 0,5 (`\|p₀−0,5\|<0,05`) | `Δ_B` medio = +0,0041 (**la mitad**) |
| `corr(Δ_B, 0,5 − p₀)` | +0,41 |
| `corr(Δ_B, Δ_A)` | +0,95 |
| magnitud relativa | `Δ_B / Δ_A` ≈ **0,105** (B recupera ~10% de A) |

### Lo que B sí demuestra, que es lo que importa

**El efecto de B no es descubrimiento de signo: es un artefacto de convexidad.**
Una inyección de puro ruido sin ningún contenido direccional produciría la misma
firma. Es decir, el estadístico agregado **no puede distinguir** "la mitad de mis
anclas deriva hacia arriba y la otra mitad hacia abajo" de "mis anclas
simplemente tienen más volatilidad de camino".

Dos consecuencias, y las dos son de primer orden para el diseño del test:

1. **Un edge de signo desconocido es invisible** para `p_favorable` en el sentido
   que importa. Lo poco que se recupera (~10% de A) no identifica *qué* anclas
   tenían el signo favorable, que es lo único accionable.
2. **`p_favorable` premia la volatilidad sin dirección.** Una estrategia que sólo
   agregue varianza alrededor del ancla, sin ningún edge, se vería levemente
   mejor en este estadístico. Es una patología suave pero real, y hay que tenerla
   en cuenta antes de usar esta tasa como criterio de selección.

Cualquier campaña de descubrimiento tiene que declarar el signo **a priori**, o
usar un estadístico condicionado al signo predicho. Con el agregado no alcanza.

## La comparación que responde la pregunta

El MDE suelto no contesta "¿alcanzan 188 días?". Lo que contesta es el MDE
**contra el break-even económico**.

**Fricción, reconstruida y verificada:**

```
6E: tick = 0,00005 × 125.000 USD  =  6,25 USD/tick
comisión  2,20 USD/pata × 2 patas =  4,40 USD  =  0,704 ticks
slippage  1 tick/pata × 2 patas   =  2,000 ticks   (escenario "base")
                            TOTAL =  2,704 ticks round-trip
```

Coincide exacto con el `delta = 2,704/(P+N)` declarado en la config del atlas.

**El lift de tasa que hay que mover para pagar esa fricción** es
`Δ_BE = 2,704/(P+N)`, o sea entre **11,8 y 27,0 puntos de tasa** en esta grilla
(P+N va de 10 a 23).

**Traducido a ticks de deriva** (interpolando el Δ medido entre m=2 y m=4):

| | m_BE (ticks de deriva al horizonte) |
|---|---|
| geometría más favorable (H30_P8_N13) | **4,89** |
| mediana de las 40 | **9,95** |
| peor (H120_P5_N5) | 54,70 |

## Deflación por N_eff — y acá se cae la conclusión anterior

El MDE placebo **no** se compara directo contra el break-even. Hay que
deflactarlo:

```
MDE_real ≈ MDE_placebo · sqrt( N_eff_placebo / N_eff_real )
```

`N_eff` se **midió**, no se asumió, con el mismo bootstrap de bloques de día que
usa producción, vía el efecto de diseño `DEFF = Var_bloque / Var_iid` y
`N_eff = n_anclas / DEFF`:

| | valor medido |
|---|---|
| anclas placebo | 47.213 sobre 185 días (255,2/día = 25 rondas × ~10,2) |
| DEFF | mediana **4,86** (rango 0,86 – 10,57) |
| **N_eff placebo** | mediana **9.707** |
| correlación intra-día implícita `ρ` | **0,0152** |

Escenario real parametrizado por frecuencia `f` y por un multiplicador de
clustering `k` sobre el `ρ` medido (`DEFF_real = 1 + (f−1)·k·ρ`, `n = f·197`):

| clustering | trades/día | N_eff | deflación | **MDE real** | vs 4,89 (mejor) | vs 9,95 (mediana) | banda ciega |
|---|---|---|---|---|---|---|---|
| cualquiera | **1** | 197 | 7,02× | **14,0 t** | **CIEGA** | **CIEGA** | **9,2 t** |
| sin extra | **3** | 574 | 4,11× | **8,2 t** | **CIEGA** | ok | **3,3 t** |
| ×2 | 3 | 557 | 4,17× | 8,3 t | **CIEGA** | ok | 3,5 t |
| ×4 | 3 | 527 | 4,29× | 8,6 t | **CIEGA** | ok | 3,7 t |
| sin extra | **10** | 1.733 | 2,37× | **4,7 t** | ok | ok | **no** |
| ×2 | 10 | 1.547 | 2,51× | 5,0 t | **CIEGA** | ok | 0,1 t |
| ×4 | 10 | 1.273 | 2,76× | 5,5 t | **CIEGA** | ok | 0,6 t |

### Reconciliación de DEFF — las tres columnas

| columna | valor |
|---|---|
| `N` (anclas por geometría) | 47.213 |
| `n_dias` (conglomerados) | 185 |
| `m̄` (anclas por día) | **255,21** |
| `ρ` medido | 0,0152 |
| `DEFF = 1+(m̄−1)·ρ` | **4,86** |
| `DEFF` medido `= Var_bloque/Var_iid` | **4,86** |

Las dos vías dan **el mismo número**: la fórmula canónica de conglomerados y la
medición por bootstrap coinciden, que es el control de consistencia que faltaba.

**El "factor 10" contra las 474.914 del atlas sellado no es discrepancia:** el
atlas usó **245 rondas**, esta corrida usó **25** (245/25 = 9,8). El
conglomerado es el **día**, no la ronda: `m̄ = 255` son las 25 rondas × ~10,2
anclas/día que caen en el mismo día y comparten régimen.

### α y potencia — el MDE reportado NO estaba a 80%

El criterio que venía usando ("IC95 excluye cero") es `z = 1,960`, o sea
**~50% de potencia**, no 80%. Un MDE sin (α, potencia) declarados no es un
número comparable con nada.

**Declarado: α = 0,05 bilateral, potencia = 80%** → `z = 1,960 + 0,842 = 2,802`.
**Factor de corrección: ×1,429.**

### Multiplicidad — medida, no asumida

Las 40 geometrías **no son 40 tests independientes**: comparten anclas y se
solapan en `H` y en `P/N`.

| | |
|---|---|
| correlación media entre las 40 series diarias | **0,669** |
| autovalor máximo | 27,62 de 40 (independientes daría ~1) |
| **`M_eff` (Li–Ji, sobre autovalores)** | **21,2 tests independientes** |

Con `M_eff = 21,2`: `α_corr = 0,00236`, `z = 3,041`, factor ×1,552 (Bonferroni
ingenuo sobre 40 daría ×1,647 — medir la correlación ahorra un poco, no mucho).

**Factor total sobre el MDE que había reportado: ×1,981.**

### Tabla final — MDE a 80% de potencia y con multiplicidad

| clustering | trades/día | N_eff | MDE 50% | **MDE 80%+mult** | vs 4,89 | banda ciega |
|---|---|---|---|---|---|---|
| sin extra | **1** | 197 | 14,0 | **27,8 t** | CIEGA | **22,9 t** |
| ×4 | 1 | 197 | 14,0 | 27,8 t | CIEGA | 22,9 t |
| sin extra | **3** | 574 | 8,2 | **16,3 t** | CIEGA | **11,4 t** |
| ×4 | 3 | 527 | 8,6 | 17,0 t | CIEGA | 12,1 t |
| sin extra | **10** | 1.733 | 4,7 | **9,4 t** | CIEGA | **4,5 t** |
| ×4 | 10 | 1.273 | 5,5 | 10,9 t | CIEGA | 6,1 t |
| sin extra | **30** | 4.102 | 3,1 | **6,1 t** | CIEGA | **1,2 t** |
| ×4 | 30 | 2.139 | 4,3 | 8,4 t | CIEGA | 3,6 t |

### Conclusión, en una línea

**Ningún régimen de frecuencia alcanza con los días que hay.** Incluso a 30
trades/día queda una banda ciega de 1,2 ticks contra la mejor geometría.

Es la **tercera** revisión de este número en el mismo turno, y las tres fueron en
la misma dirección:

| versión | MDE a 10 trades/día | qué faltaba |
|---|---|---|
| "188 alcanzan con margen 2,5×" | 2,0 t | sin deflactar por N_eff |
| tras deflación | 4,7 t | sin (α, potencia) ni multiplicidad |
| **final** | **9,4 t** | — |

### Cuántos días harían falta

Como el MDE escala `1/√n`, para llegar a la mejor geometría (4,89 t):

| trades/día | factor de días | días | años de 6E |
|---|---|---|---|
| 1 | 32,4× | 6.376 | **25,5** |
| 3 | 11,1× | 2.190 | **8,8** |
| 10 | 3,7× | 725 | **2,9** |
| 30 | 1,6× | 306 | **1,2** |

**Esto mata la captura manual día por día.** Diez días capturados a mano mueven
el MDE un 2,5%. Hacen falta dos órdenes de magnitud más de los que produce
cargar un chart por vez.

**La única palanca real es la frecuencia.** Pasar de 1 a 30 trades/día mejora el
MDE 4,6× (27,8 → 6,1) **sin un solo dato nuevo** — más de lo que comprarían 25
años de captura. La frecuencia de operación no es un detalle de la estrategia:
es el parámetro de diseño que decide si el proyecto puede probar algo, y hoy no
está fijado por nadie.

---

## CORRECCIÓN FINAL — todo lo de arriba mide el estadístico equivocado

Toda la tabla de bandas ciegas está calculada sobre **`p_favorable`**, que en la
sección anterior se determinó que **no puede ser el estadístico primario**
(contaminación de Jensen). Calcular el MDE del estadístico que ya se descartó y
concluir "no alcanzan los días" es un error de encadenamiento: **el mío**.

El estadístico primario es la **expectativa neta en ticks**, y tiene una ventaja
que `p_favorable` no tiene: **se compara DIRECTO contra la fricción de 2,704
ticks**, sin pasar por tasas ni por el lift `2,704/(P+N)`.

### MDE del estadístico con signo (misma deflación, misma potencia, misma multiplicidad)

`SE` placebo medida = **0,0420 ticks/ancla** (`N_eff` = 9.707).

| trades/día | N_eff | deflación | **MDE (ticks)** | fricción | margen | veredicto |
|---|---|---|---|---|---|---|
| **1** | 197 | 7,02× | **1,14** | 2,704 | **2,4×** | **ALCANZA** |
| 3 | 574 | 4,11× | 0,67 | 2,704 | 4,0× | ALCANZA |
| 10 | 1.733 | 2,37× | 0,39 | 2,704 | 7,0× | ALCANZA |
| 30 | 4.102 | 1,54× | 0,25 | 2,704 | 10,8× | ALCANZA |

*(α=0,05 bilateral, potencia 80%, multiplicidad `M_eff`=21,2 medida sobre las 40
geometrías. Con 3 hipótesis preregistradas: 0,95 / 0,56 / 0,32 / 0,21 ticks.)*

**Cero geometrías ciegas, en cualquier régimen de frecuencia.**

### El contraste, a 1 trade/día, con todas las correcciones aplicadas

| estadístico | MDE | umbral | resultado |
|---|---|---|---|
| `p_favorable` | 27,8 t | break-even 4,89 t | **CIEGA por 22,9 t** |
| **expectativa neta** | **1,14 t** | fricción 2,704 t | **ALCANZA, margen 2,4×** |

Un factor de **24×** entre los dos estadísticos, sobre exactamente los mismos
datos, las mismas anclas y el mismo bootstrap. `p_favorable` es binario y tira a
la basura la magnitud de cada excursión; la expectativa neta usa toda la
información.

### Respuesta final

**Sí alcanzan los 197 días, en cualquier régimen de frecuencia — incluido 1
trade/día — usando la expectativa neta en ticks como estadístico primario.**

La frecuencia **no** es la palanca: es aproximadamente neutra para la
detectabilidad y estrictamente cara en fricción (se paga 2,704 ticks `f` veces
por día). El régimen de operación queda libre para decidirse por criterios
operativos, no estadísticos.

### Las otras palancas, cuantificadas

| palanca | ganancia medida | ¿hace falta? |
|---|---|---|
| **3. estadístico con signo** | **×24** | **es la única que hacía falta** |
| 1. multiplicidad 40 → 3 preregistradas | ×1,20 | no, pero es gratis y conviene igual |
| 2. sumar instrumentos (ES/NQ ya en disco) | ≤ ×1,73 | no. Amplía margen, no cierra brecha |
| 4. condicionar por volatilidad | no cuantificada | sí, pero por el nulo roto, no por el MDE |

Sobre la palanca 1: medida con `z` de Bonferroni sobre `M_eff` da **×1,20**, no
×1,83. La diferencia es la formulación — `√(2·ln N)` es la del Deflated Sharpe
Ratio, no la del MDE. Se reporta la que corresponde al cálculo que se está
haciendo.

Sobre la palanca 2: los parquets de ES, NQ, MES, MNQ y GC **están en disco**
(`data/nt8/*_parquet/`). Con margen de 2,4× ya no hace falta agruparlos para
cerrar la brecha, y agruparlos tiene un costo metodológico propio (los
instrumentos están correlacionados, así que la ganancia real es menor que √3, y
mezclar regímenes de fricción distintos exige justificarlo). Queda como reserva.

---

## MDE POR GEOMETRÍA — la objeción (a) era correcta y material

El 1,14 ticks agregado **escondía heterogeneidad real**. La `SD` por trade va de
**4,82 a 10,79 ticks** (2,2×) según el ancho de barreras y el horizonte.

| trades/día | geometrías ciegas (MDE > 2,704 t) |
|---|---|
| **1** | **22 de 40** |
| **3** | **1 de 40** (H120_P8_N13, 2,71 vs 2,704 — marginal) |
| 10 | 0 de 40 |
| 30 | 0 de 40 |

**"Cero geometrías ciegas" era falso a 1 trade/día.** El agregado estaba
dominado por las geometrías de baja varianza. La ceguera escala con `P+N` y con
`H`: las anchas y largas (P+N=21-23, H90-H120) son ciegas a f=1; las angostas y
cortas (P+N=10-16) sirven en todo régimen.

### Y el cruce que la espec necesita: testeable × económicamente alcanzable

`p_req` = tasa de acierto para que la expectativa bruta supere la fricción
(`p > (2,704+N)/(P+N)`). Hay un **trade-off duro**:

| | angostas (P5_N5) | anchas (P13_N8) |
|---|---|---|
| testeable a f=1 | **sí** | no (necesita f≥3) |
| `p_req` | **77,0%** — brutal | **51,0%** — alcanzable |

Las geometrías fáciles de testear son las económicamente imposibles, y viceversa.

**Conjunto viable (testeable Y con `p_req` < 70%): 28 de 40.** Las mejores:

| geometría | `p_req` | régimen |
|---|---|---|
| H30_P13_N8 · H60/H90/H120_P13_N8 | 51,0% | f ≥ 3 |
| **H30_P13_N10** | 55,2% | **f ≥ 1** |
| **H30_P12_N10** | 57,7% | **f ≥ 1** |
| **H30_P10_N8 · H60/H90_P10_N8** | 59,5% | **f ≥ 1** |

**`H30_P13_N10` es la única con `p_req` ≤ 55% testeable a 1 trade/día.** Si el
régimen operativo va a ser de baja frecuencia, ése es el pool real de
candidatas, y es chico.

### Reconciliación de un número que aparecía dos veces

El texto decía "margen 2,4× a 16,6×". El 16,6× era `fricción/MDE` **sin
deflactar** y el 10,8× de la tabla era el deflactado a f=30: dos objetos
distintos citados juntos. **El rango correcto de la tabla agregada es 2,4×
(f=1) a 10,8× (f=30)** — y esa tabla queda superada por la de por-geometría,
que es la que vale.

## `2025-10-31` — resuelto, y la puerta aguantó

**No estaba "sin procedencia".** Está en `runs/censo/censo.json`, en la entrada
de `6E_12-25_ticks.parquet`, con **`estado: DEFECTUOSO`** y tres chequeos
fallados:

| código | detalle |
|---|---|
| `TIPO_DE_DIA_IMPOSIBLE` | derivado `COMPLETO` pero `dow=4` (viernes) |
| `COBERTURA_HORARIA_INSUFICIENTE` | 17 h contra un mínimo de 20 |
| `CIERRE_SEMANAL_TARDIO` | último tick 23:37, límite 16:00 |

**El censo hizo su trabajo** y el manifiesto vigente la excluye correctamente
(sólo lleva días APTO). El atlas sellado la consumió desde un estado de
manifiesto anterior, previo a que el censo la reclasificara.

**La puerta no está comprometida.** `atlas_asimetrico.py:323` llama
`cargar_dias_de_estudio`; no hay un solo `glob`/`listdir`/`walk` para elegir
días en ninguno de los dos atlas. El censo **es** la puerta.

**Materialidad: nula, y por una razón más fuerte que "es 1 de 188".** Todos los
números de este documento —`SE`=0,0420, `DEFF`, `M_eff`, las 40 filas— se
midieron sobre **185 días que ya excluyen esa fecha**, porque
`dias_del_atlas_sellado()` sólo resuelve fechas presentes en el censo vigente.
El día vive únicamente en el atlas sellado, no en nada medido acá.

**No se re-emite el atlas.** Re-emitirlo invalidaría la cadena de procedencia de
todo lo anterior, y no hay causa: el efecto medido es exactamente 0,00%.

## Vocabulario: esto ya tiene nombre

El atlas es un **triple-barrier method** (TP / SL / barrera temporal) sin que
nadie lo hubiera llamado así. Y el hallazgo de que el estadístico agregado no
descubre signo tiene solución publicada: **meta-labeling** (López de Prado) — un
modelo primario declara el lado, un secundario decide tamaño/confianza. Conviene
adoptar el vocabulario para no re-derivar lo ya resuelto.

## La contaminación por volatilidad no es una nota al pie

Si `p_favorable` es convexa en la deriva, la **volatilidad sola** la infla sin
ninguna dirección. Declarar el signo a priori **no** lo evita: una estrategia que
ancle en momentos de alta volatilidad muestra `p_favorable` elevada con edge
direccional cero.

Cuantificado. `Δ_B` es cuadrático en `m` (efecto de segundo orden, verificado:
`Δ_B(4)/Δ_B(2) ≈ 4`). Resolviendo qué amplitud de volatilidad de media cero
iguala el lift económico `2,704/(P+N)`:

| | ticks |
|---|---|
| `m_vol` que finge TODO el lift económico | mín **11,9** · mediana 21,8 |
| `m_BE` direccional, que lo gana de verdad | mín **4,9** · mediana 9,7 |
| razón `m_vol / m_BE` | mediana **2,24** |

**Mismo orden de magnitud.** Basta con ~2,2× más volatilidad que la deriva
honesta para fabricar el lift entero sin edge. `p_favorable` **no sobrevive como
estadístico primario.**

### El estadístico con signo sí sobrevive

Expectativa neta en **ticks por ancla** (v=+1 → +P, v=−1 → −N, v=0 → marcado a
mercado):

| | A (signo alineado) | B (signo sorteado, media cero) |
|---|---|---|
| geometrías con efecto significativo (m=4) | **40 de 40** (+0,13 a +2,08 t) | **0 de 40** |

Bajo una señal de media cero da **exactamente lo que debe dar: nada**. Es inmune
a la contaminación de Jensen que arruina `p_favorable`.

### Lo que va al preregistro

1. **`p_favorable` deja de ser primario.** Pasa a co-primario, y sólo como
   descriptivo.
2. **El estadístico primario es la expectativa neta en ticks** (con signo).
3. **El nulo tiene que controlar volatilidad.** El nulo actual estratifica por
   `vol_prev` en terciles (`vol_cortes=[0.33,0.66]`) para los *estratos*, pero el
   agregado que se usa como benchmark **no** condiciona por volatilidad. Con
   `p_favorable` convexa, eso deja el benchmark **inflado**. Es el tercer nulo
   roto que encuentra este proyecto, y hay que decirlo así.

## n canónico — con fechas, no con conteos

| número | qué es | ¿correcto? |
|---|---|---|
| **200** | **filas** (pares archivo–fecha) que devuelve la puerta única | sí, pero son filas, no días |
| **197** | **fechas únicas** = 200 − 3 viernes de roll duplicados (`2025-12-12`, `2026-03-13`, `2026-06-12`) | **sí. El 197 sellado NO es un número falso.** |
| **188** | fechas que consumió el atlas sellado | sí, pero sobre un censo anterior |
| 185 | fechas usadas en esta corrida (188 − 3 huérfanas) | — |

Aritmética exacta: **197 − 12 + 3 = 188**.

### Los 12 que entran hoy y no entraron al atlas

`2025-10-17` · `2026-05-27` · `2026-05-28` · `2026-06-01` · `2026-06-19` ·
`2026-06-22` · `2026-06-23` · `2026-06-24` · `2026-06-25` · `2026-06-26` ·
`2026-06-29` · `2026-06-30`

**Razón:** el censo vigente se generó el **2026-07-28T00:47:03Z**, cinco horas y
dieciséis minutos **después** de que se generara el atlas
(**2026-07-27T19:31:03Z**). El censo anterior tenía 164 días. Los 12 son días que
entraron al censo después de que el atlas corriera. Ninguno figura en el censo
previo.

**Verificación de brecha: NINGUNO cae en `≥ 2026-07-01` ni en la cuarentena
`2026-07-01 → 2026-07-24`.** El más tardío es `2026-06-30`. **No hay brecha.**

### Las 3 huérfanas — hallazgo de integridad

`2025-10-31` · `2025-11-19` · `2025-12-15` están **en el atlas y no en el censo
de hoy**:

| fecha | ¿censo previo? | ¿censo hoy? |
|---|---|---|
| `2025-11-19` | SÍ | NO |
| `2025-12-15` | SÍ | NO |
| `2025-10-31` | **NO** | **NO** |

**Las 188 del atlas no son un subconjunto de las 197 de hoy.** Dos son
rastreables a un censo superado; `2025-10-31` **no figura en ningún censo
conocido**. No se fuerza una atribución.

### n canónico declarado

**`n = 197` fechas únicas** es el universo canónico disponible. El atlas sellado
midió sobre 188, de las cuales 3 no tienen procedencia en el censo vigente. La
tabla de deflación usa `D = 197`.
