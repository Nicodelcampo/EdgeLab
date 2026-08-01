# ESPEC_TEST_EXPLORE-001 — especificación del primer gate real

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

`1 tick 6E = $6,25` · fricción = 2,704 ticks = **$16,90 round turn**.

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

## 3. El test

### 3.1 Estadístico primario — una sola formulación

> **Expectativa NETA por trade, en ticks, con la fricción de 2,704 ya restada
> DENTRO del estadístico. Umbral = 0.**

**PROHIBIDO** volver a restar la fricción del lado derecho de la comparación
(sería contarla dos veces). **PROHIBIDO** reintroducir `2,704/(P+N)`: ése es el
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
2,704 es de 6E y hay que recalcularlo por instrumento antes de usarlo como umbral.

---

## 4. Decisiones que quedan abiertas y son de Nico

1. **Cuáles 3 indicadores** — depende del §1.
2. **Los cuatro umbrales de prop firm** — la tabla del §2.1 propone LucidFlex 50K
   como referencia; confirmar o cambiar de cuenta.
3. **El régimen de frecuencia objetivo** — no es estadístico (la frecuencia es
   aproximadamente neutra para detectar) sino operativo, pero el §2.4 muestra que
   f=1 está doblemente restringido.
