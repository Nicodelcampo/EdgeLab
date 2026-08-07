# ESPEC_TEST_EXPLORE-001 — especificación del primer gate real

> ## SUPERSEDED — no usar aisladamente para ejecutar EXPLORE-001
>
> Para trabajo futuro este documento queda reemplazado por:
> **`docs/predictions/ESPEC_TEST_EXPLORE-001_v0.3.md`** (2026-08-07).
>
> **Se conserva como registro histórico.** Su contenido NO se reescribe: las
> decisiones que tomó, y las que después cambiaron, son parte del expediente.
> Toda decisión futura de EXPLORE-001 parte de v0.3; ningún borrador anterior
> —este incluido— puede invocarse para reemplazar una regla de v0.3.
>
> Motivo del reemplazo: editar cualquiera de las dos especificaciones existentes
> habría mezclado **registro histórico con reglas actuales**. Ver v0.3 §0.


> **Estado: INCOMPLETA.** §3.3 (las 3 hipótesis) está vacía a propósito y no se
> llena hasta tener la tabla de tasa de señales del §1. Elegir hipótesis antes
> de esa tabla es elegirlas a dedo.
>
> Referente: `docs/NORTH_STAR.md`, sha256 `21bb3b01a33e2b37…`
> Intérprete: `E:\EdgeLab\.venv\Scripts\python.exe` (30 paquetes = lock exacto)

## Justificación económica

Este documento existe para permitir **matar o confirmar** hipótesis. Un aparato
que mide y no decide no acorta la distancia al referente. Todo lo que sigue está
subordinado a producir un veredicto por hipótesis.

## Cómo podría refutarse

Si al correr el gate ninguna hipótesis termina en VIVE o MUERE —si todas caen en
zona gris y sobreviven— la espec falló, porque la zona gris es la cláusula que
impide la vida eterna. Ver §3.2.

---

## 1. Tasa empírica de señales — PENDIENTE

`f` (señales/día) **no es una perilla de diseño: es una salida de la hipótesis.**
Un indicador emite las señales que emite. La tabla del MDE por geometría no se
puede leer hasta saber a qué `f` opera cada candidato.

**Esta medición NO consume presupuesto de multiplicidad.** Cuenta disparos: no
evalúa resultados, no mira si la señal ganó o perdió, no la compara contra
ningún umbral económico. Es censo de actividad, del mismo tipo que contar
cuántos días tiene el universo. Queda declarado acá para que nadie lo cobre
después.

Medición en curso: `diag/tasa_senales/medir_tasa.py`, sobre los **200 días de
research** que entrega la puerta única (18 descartados por holdout, 18 por
cuarentena INC-005; fecha máxima `2026-06-30`).

---

## 2. Filtro de operabilidad — LucidFlex 50K

### 2.1 Reglas verificadas en la fuente oficial

Verificado en `support.lucidtrading.com` —no en reseñas de afiliados— con el
navegador, porque el sitio devuelve 403 a fetch directo.

| regla | valor | artículo | fecha del artículo |
|---|---|---|---|
| Profit target (evaluación) | **$3.000** | LucidFlex Evaluation Account | 2026-04-15 |
| Max Loss Limit | **$2.000** | Evaluation + Drawdown + Funded | 2026-04-15 / 2025-11-26 / 2026-06-02 |
| Initial Trail Balance | **$52.100** | LucidFlex Drawdown | 2025-11-26 |
| Locked MLL Balance | **$50.100** | LucidFlex Drawdown | 2025-11-26 |
| Consistencia | **50%**, sólo evaluación | Evaluation / Funded | 2026-04-15 / 2026-06-02 |
| Daily loss limit | **ninguna**, en las dos fases | Evaluation / Funded | 2026-04-15 / 2026-06-02 |
| Tamaño máximo | **4 minis / 40 micros** | Evaluation / Funded | 2026-04-15 |

Citas textuales: *"There is no DLL on LucidFlex evaluation accounts"*;
*"LucidFlex funded accounts have no daily loss limit, no consistency rule, and no
payout buffer"*; *"At the end of each trading session, the system calculates the
account's highest closing balance"* (el trailing es **EOD**, sobre balance de
cierre, no sobre picos intradiarios).

**Corrección a la tabla de entrada:** el "días mínimos = 2" **no es una regla
declarada**. La fuente dice *"The LucidFlex evaluation 50% consistency has
cushion built in, so you can pass in two days"* — o sea, dos días es el mínimo
**alcanzable** que se deriva de la aritmética de la consistencia, no un
requisito independiente. La restricción que ata es el **50% de consistencia**.

### 2.2 Conversión a ticks

`1 tick 6E = $6,25` · fricción = **2,768 ticks = $17,30 round turn**.

> **Actualizado 2026-08-06 — la comisión dejó de ser una estimación.**
> Confirmada en la fuente oficial de Lucid («Approved Products and Commissions»,
> artículo del 2026-02-09): `6E · Euro FX Futures · **2.40 per side** · CME`.
> El manifiesto de CAMP-001 llevaba **$2,20 pre-registrada como estimación** —el
> «dato faltante #1»—, o sea que la fricción estaba **subestimada**.
>
> | | comisión RT | + slippage 2t | total RT | ticks |
> |---|---|---|---|---|
> | estimado | $4,40 | $12,50 | $16,90 | 2,7040 |
> | **real** | **$4,80** | $12,50 | **$17,30** | **2,7680** |
>
> **+$0,40 por round turn = +0,064 ticks = +2,37 %.**
>
> **Qué NO cambia:** el MDE (1,14 a f=1 · 0,39 a f=10) y el margen medido de
> 1,60× — dependen del error estándar, no de la fricción. **Qué SÍ cambia:** toda
> excursión bruta tiene que superar **2,768** en vez de 2,704, y toda expectativa
> neta medida con el valor viejo estaba **sobreestimada en 0,064 ticks/trade**.
>
> **CAMP-001 no se re-abre y su veredicto se sostiene:** dio **negativo** con los
> costos **subestimados**, y corregirlos hacia arriba sólo puede hacerlo más
> negativo. El manifiesto sellado **no se toca** — la corrección rige de acá en
> adelante.
>
> **Límite declarado:** `edge_validation_contract.md` §G3 pide el modelo
> **desglosado** (broker + exchange/clearing + NFA). Lucid publica **un solo
> número all-in por pata** y no lo abre. El total es real; el desglose por
> componente **no es acreditable desde esta fuente**, y no se inventa.

| | dólares | ticks (1 contrato) |
|---|---|---|
| Profit target | $3.000 | **480** |
| Max Loss Limit | $2.000 | **320** |

### 2.3 Los cuatro filtros de admisión — duros

Sobre la serie de trades simulada:

1. **Drawdown EOD**: máxima caída desde el pico de equity **de cierre diario**
   (no intradiario) vs **320 ticks**.
2. **Consistencia**: máximo % del beneficio total concentrado en un solo día,
   hasta alcanzar los 480 ticks, vs **50%**.
3. **Días operados** vs 2.
4. **Tiempo esperado hasta el profit target**, por número de contratos.

Una hipótesis que sale VIVE estadísticamente pero viola cualquiera de los cuatro
**no es un edge operable y no pasa**. Es el referente aplicado: la jerarquía pone
"ejecutabilidad real" por encima de la elegancia estadística.

### 2.4 Detectable ≠ operable — la cuenta que faltaba

**Días hasta el profit target** = `480 / (edge × f × contratos)`:

| edge (ticks netos/trade) | f | c=1 | c=2 | c=4 |
|---|---|---|---|---|
| **1,14** (= MDE a f=1) | 1 | **421 d (1,7 años)** | 211 d | 105 d |
| 1,14 | 3 | 140 d | 70 d | 35 d |
| 2,00 | 1 | 240 d | 120 d | 60 d |
| 4,00 | 1 | 120 d | 60 d | 30 d |

**Escalar contratos NO compra margen.** El MLL es fijo en dólares, así que en
ticks se divide por el tamaño:

| contratos | target (ticks) | MLL (ticks) | ratio |
|---|---|---|---|
| 1 | 480 | 320 | **1,50** |
| 4 | 120 | 80 | **1,50** |

El **ratio target/MLL = 1,50 es invariante al tamaño**: hay que ganar 1,5× el MLL
antes de tocarlo, se opere 1 contrato o 4. Escalar acelera el calendario y
comprime la tolerancia al drawdown en la misma proporción.

**Edge mínimo OPERABLE** (pasar la evaluación en ≤ 1 año, 1 contrato):

| f | edge mínimo operable | contra el MDE (1,14) |
|---|---|---|
| **1** | **1,92 ticks/trade** | **1,7× — el detectable NO alcanza** |
| 3 | 0,64 ticks/trade | 0,6× — alcanza |
| 10 | 0,19 ticks/trade | 0,2× — alcanza |

**A 1 trade/día existe una banda entre lo detectable (1,14) y lo operable
(1,92).** Un edge ahí adentro se ve con significancia estadística y aun así no
pasa la evaluación. A f ≥ 3 la banda desaparece.

Cruzado con el MDE por geometría (22 de 40 ciegas a f=1, 1 de 40 a f=3): **f=1
está doblemente restringido** —la mayoría de las geometrías es ciega Y el edge
detectable no basta para operar— y **f ≥ 3 relaja las dos restricciones a la
vez**.

---

## 2.5 Selección de cuenta — `P(pasar)`, no `E[días]`

**`E[días]` no es el filtro correcto.** LucidFlex no tiene límite de tiempo: con
horizonte libre el profit target no ata, ata el **piso**. La cantidad que decide
es `P(alcanzar +target antes de −MLL)` sobre la distribución empírica de trades.

Insumo **medido**, no supuesto: `SD` por trade = **8,77 ticks** (mediana de las
40 geometrías sobre `diag/spike_in/por_geom_nulo.json`, el mismo artefacto del
que salen `SE`, `DEFF` y `M_eff`). Reproducible con
`diag/spike_in/p_pasar_prop_firm.py`.

### El ratio target/MLL es invariante a CONTRATOS, no a tamaño de cuenta

| cuenta | target (t) | MLL (t) | ratio |
|---|---|---|---|
| 25K | 200 | 160 | **1,25** |
| 50K | 480 | 320 | 1,50 |
| 100K | 960 | 480 | 2,00 |
| 150K | 1.440 | 720 | 2,00 |

### `P(pasar)` con edge = 0,39 ticks/trade (el MDE a f=10)

| cuenta | c=1 | c=2 | c=3 | c=4 |
|---|---|---|---|---|
| **25K** | **82,4 %** | 66,2 % | 59,3 % | 55,7 % |
| **50K** | **96,1 %** | 81,7 % | 70,8 % | 64,0 % |
| **100K** | **99,2 %** | 91,3 % | 80,9 % | 72,2 % |
| **150K** | **99,9 %** | 97,4 % | 91,3 % | 84,2 % |

### Dos lecturas, y la primera contradice una recomendación vigente

**1. La 25K NO es la más pasable, es la PEOR** — aunque tenga el mejor ratio.

El ratio dice cuánto hay que ganar respecto de lo que se puede perder. **Pero
`P(pasar)` depende del tamaño ABSOLUTO en unidades de `SD` por trade.** La 25K
tiene 200/160 ticks: apenas ~20 `SD` de margen, y el ruido resuelve la partida
antes de que la deriva se exprese. La 150K tiene 1.440/720: cientos de `SD`, y
ahí la ley de los grandes números trabaja a favor.

**Un ratio peor con mucho más espacio absoluto pasa más que un ratio bueno sin
espacio.** La recomendación de preferir la 25K por su ratio de 1,25 queda
retirada.

**2. Los contratos no compran margen.** `P(pasar)` cae monótonamente al escalar,
en **todas** las celdas. Cambian probabilidad de pasar por tiempo hasta pasar.

### Recomendación operativa

**La cuenta más grande que se pueda, 1 contrato.** No 4.

*Salvedad declarada:* es aproximación browniana a ruina del jugador
(`P = (1−e^(−θb))/(1−e^(−θ(a+b)))`, `θ = 2μ/σ²`). Con barreras P/N discretas y
cientos de trades es razonable, pero no exacta. Y supone el edge real y
constante.

---

## 3. El test

### 3.1 Estadístico primario — una sola formulación

> **Expectativa NETA por trade, en ticks, con la fricción de 2,768 ya restada
> DENTRO del estadístico. Umbral = 0.**

**PROHIBIDO** volver a restar la fricción del lado derecho de la comparación
(sería contarla dos veces). **PROHIBIDO** reintroducir `2,768/(P+N)`: ése es el
umbral del estadístico de **tasa**, no del de expectativa, y confundirlos fue un
error real de este expediente.

`BE_g` **no depende de la geometría**: con el estadístico con signo el umbral es
0 (la fricción ya está adentro). Lo que varía por geometría es el `p_req`
implícito, no el umbral.

- **`p_favorable`: descriptiva, nunca decisoria.** Es convexa en la deriva, así
  que la volatilidad sola la infla (Jensen). Medido: basta 2,2× más volatilidad
  que la deriva honesta para fabricar el lift económico entero sin ningún edge.
- **`p_req`: filtro de plausibilidad a priori**, no regla de decisión.

### 3.2 Criterio de muerte — frontera de futilidad

α = 0,05 bilateral ajustado por `M_eff`; potencia 80%; IC bootstrap con
deflación por bloques diarios.

| veredicto | condición | consecuencia |
|---|---|---|
| **VIVE** | cota **inferior** del IC ajustado > 0 | replicación ES/NQ, después UNA mirada al holdout |
| **MUERE** | cota **superior** del IC ajustado < 0 | descartada. No vuelve. |
| **GRIS** | el IC contiene al 0 | **muere por defecto** |

La cláusula que hace que esto funcione es la tercera. Sin ella la zona gris es
vida eterna y el aparato vuelve a medir sin decidir.

**Excepción única y preregistrada:** una hipótesis sobrevive la zona gris **una
sola vez** si al preregistrarla ya está escrito **qué dato específico la
resolvería y cuánto cuesta conseguirlo**. Sin ese texto escrito ANTES de ver el
resultado: gris = muerta.

Cuatro reglas que van con el criterio:

1. **Una hipótesis muerta no vuelve con parámetros retocados.** Si vuelve, cuenta
   como hipótesis nueva contra el presupuesto de multiplicidad. Sin esto la
   corrección por `M_eff` es decorativa.
2. **El holdout se mira una sola vez por hipótesis**, y sólo después de VIVE +
   replicación.
3. **El veredicto de cada desenlace se escribe antes de correr.**
4. **Las tres hipótesis se juzgan juntas, en una sola pasada.** Nada de correr
   una, ver, y elegir la siguiente.

### 3.3 Las 3 hipótesis — **VACÍO, PENDIENTE DEL §1**

No se llena hasta tener la tabla `(indicador × geometría)` leída al `f` que cada
indicador realmente entrega.

Regla de selección, en orden:

1. Descartar las que caen en geometrías **ciegas** al `f` que ese indicador emite.
2. Preferir **mecánicamente distintas** — no tres variantes de zonas de volumen,
   que inflan `M_eff` sin diversificar.
3. Preferir las que ya tienen **gate y oráculo montados** (`aVolCellPOI2` y
   `BigTrap2` los tienen), para reducir superficie de error en el primer disparo.

**Filtrar geometrías con la tabla de 40 filas NO consume multiplicidad.** Usa
sólo la varianza bajo el nulo placebo y la aritmética de la fricción, sin mirar
ninguna señal real. Es decisión de diseño previa a los datos, del mismo tipo que
fijar α.

**`M_eff = 21,2` es piso optimista.** Sale de la correlación 0,669 entre las 40
series placebo, que comparten camino de precios por construcción. Con señales
reales la correlación baja y `M_eff` sube hacia 40, o sea la corrección por
multiplicidad empeora.

### 3.4 Replicación

**ES / NQ como gate de confirmación, no como palanca de potencia.** Un edge que
aparece en 6E y no replica fuera es sospechoso de sobreajuste. Los parquets están
en disco (`data/nt8/ES_parquet/`, `NQ_parquet/`).

Advertencia: los instrumentos están correlacionados, así que la replicación **no**
multiplica `n` por 3, y cada uno tiene su propia estructura de fricción — el
2,768 es de 6E y hay que recalcularlo por instrumento antes de usarlo como umbral.

---

## 4. Decisiones que quedan abiertas y son de Nico

1. **Cuáles 3 indicadores** — depende del §1.
2. **Los cuatro umbrales de prop firm** — la tabla del §2.1 propone LucidFlex 50K
   como referencia; confirmar o cambiar de cuenta.
3. **El régimen de frecuencia objetivo** — no es estadístico (la frecuencia es
   aproximadamente neutra para detectar) sino operativo, pero el §2.4 muestra que
   f=1 está doblemente restringido.

---

## 2-bis. Régimen de signo — uno por hipótesis, declarado antes de correr

El salto de potencia de 24× vino de pasar a un estadístico **con signo**, y un
estadístico con signo necesita una dirección por ancla. Los candidatos no son
iguales en eso.

**Verificación previa (bloqueante para H1): PASA.** `oracles/BigTrap2_tick25_6E_0926_v22.csv`
emite `side=` en las **482** `ZONE_CREATED`
(`zone_id=3006_S;created_bar=3006;side=trapped_sellers;...`). Balance
**260 `trapped_sellers` / 222 `trapped_buyers` = 54/46**, muy lejos del ~70/30 que
lo descalificaría. El signo es información direccional real.

**RÉGIMEN A — dirección nativa. Sólo H1 (BigTrap2).**
Estadístico = expectativa **neta con signo contra 0**, con la dirección que emite
el indicador. Es el régimen potente: no gasta datos estimando el signo.

**RÉGIMEN B — dirección como salida. H2 y H3 (zonas).**
Estadístico = `|excursión bruta|` contra la fricción 2,768; el signo se lee del
resultado. Es **un** test bilateral, **no dos**: no consume multiplicidad extra.
Razón registrada: con la fricción dentro del estadístico, fade y break no son
espejos (`neto_fade = bruto − 2,768`; `neto_break = −bruto − 2,768`) y no pueden
ser ambos positivos.

**PROHIBIDO:** correr el régimen A con la dirección elegida **después** de ver el
resultado. Es el régimen B con la potencia del A, y es inflación pura.

## 2-ter. Barrido de resolución de BigTrap2

**Grilla declarada hoy, cerrada, no ampliable después de ver resultados:**
`10, 15, 25, 50, 100` ticks, más `time:1` como **control fuera de la familia**.

**Costo ya pagado:** `M_eff` 21,2 → ~106, `z` 3,041 → 3,50, **MDE +11,8%**. El
margen medido a f=10 es **1,60×**, así que entra con holgura. Bonferroni es
conservador con la correlación fuerte entre resoluciones vecinas, así que el
costo real es menor — **anotado, no aprovechado**.

**Criterio de muerte específico de H1, más exigente que el general:**

> H1 **VIVE** sólo si pasa una **banda contigua de ≥3 resoluciones adyacentes**.
> Un pico aislado con los vecinos muertos se declara **MUERTO** aunque su IC
> ajustado supere el umbral.

Fundamento: si el efecto es real es un fenómeno de agregación y debe variar
**suavemente** con la resolución. Esto compra robustez; no es cazar el mejor
número. **Entregable: la curva completa resolución × expectativa neta con IC —
la CURVA, nunca el argmax.**

Si el barrido sale caro, se recorta la grilla **antes** de correr y se declara;
nunca después de ver resultados.


---

## 5. Autorizaciones vigentes (PRED-004 / NT8)

Dadas por Nico, **sin usar todavía**. Se registran acá para que no vivan sólo en
un hilo de chat:

| # | autorización | estado |
|---|---|---|
| 1 | copiar el oráculo histórico `BigTrap2_time1_6E_0926_v2.csv` con su SHA y procedencia | **sí**, sin ejecutar |
| 2 | escribir dentro de la instalación de NT8 en `C:` | **sí**, sin ejecutar |
| 3 | usar la referencia v2.1 para P5 | **sí**, sin ejecutar |
| 4 | actualizar `TickBarDiag` | **no** — fuera de alcance |

**Gate abierto que ninguna de las cuatro cubre:** la ventana real del oráculo
histórico es `2026-07-07T19:04` → `2026-07-24T17:59`, **entera dentro del holdout
sellado y entera dentro de la cuarentena de INC-005**. Correr P5 exige registrar
la apertura en `docs/holdout_access_log.md` con propósito
`target_free_validation` **antes** de leerlo.
