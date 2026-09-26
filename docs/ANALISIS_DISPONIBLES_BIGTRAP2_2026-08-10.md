# Qué análisis conviene hacer sobre BigTrap2 — literatura y mapeo a lo medible

> **SUPERSEDIDO POR `PLAN_ANALISIS_v2_2026-08-10.md` el mismo día.**
>
> **Qué sigue vigente:** la revisión de literatura (§1), el mapeo de
> discriminantes a campos del dict de zona (§2) y las descripciones de cada
> análisis.
>
> **Qué está mal:** el **ordenamiento**, y por una razón de fondo. Este
> documento razona íntegramente dentro del marco del toque —hasta A1, el test
> nulo, está formulado como «tasa de ruptura **al primer toque**»—, así que
> reintroduce por la ventana el sesgo que `SESGO_DE_DISENO_2026-08-10_EL_TOQUE_
> COMO_UNICA_ENTRADA.md` documenta. Le falta el eje estado-vs-evento entero, y
> con él la palanca de potencia más grande disponible.
>
> Se conserva sin editar el cuerpo, por la misma razón por la que los incidentes
> van a cuarentena y no al tacho.

**Fecha** 2026-08-10 · Posterior a `ACTA_MUERTE_H1_2026-08-09.md`
**NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Motivo** determinar, con base en literatura, los análisis más informativos
posibles sobre lo que EdgeLab ya puede medir hoy.

---

## 0. El hallazgo que gobierna todo lo que sigue

Del acta de muerte de H1: para el **92,9 %** de la población el primer toque y
la muerte de la zona son el mismo evento (mediana 2 barras), y **0 de 394**
close-throughs ganan. «Primer toque» selecciona rupturas, no rechazos.

Por lo tanto la pregunta central ya no es *«¿en qué dirección operar una zona?»*
sino **«¿qué distingue, al momento del toque, una zona que se rompe de una que
aguanta?»**. Todo análisis se ordena por cuánto aporta a esa pregunta.

---

## 1. Lo que dice la literatura — y lo que no dice

### 1.1 Sobre soportes/resistencias hay evidencia formal

`arXiv 2101.07410` (*Evidence and Behaviour of Support and Resistance Levels in
Financial Time Series*) es lo más cercano y usa el diseño correcto:

- Detecta niveles por toques previos, calcula probabilidad de rebote vs ruptura,
  y **compara contra niveles generados al azar por Monte Carlo**.
- Halla que la probabilidad de rebote **sube con el número de toques previos**
  pero **decae con el tiempo** — los niveles se gastan.

`Osler` (Fed NY, *Currency Orders and Exchange-Rate Dynamics*, SR-125) aporta el
mecanismo: los niveles existen **por desbalances de órdenes límite y de mercado**,
y cuando se cruzan **el movimiento se acelera** — el diferencial post-ruptura es
significativo al 1 %.

Y sobre la fuerza del nivel: *zonas formadas con alto volumen transaccional
muestran mayor estabilidad y menor probabilidad de ruptura*.

### 1.2 Sobre order flow hay evidencia fuerte

Cont, Kukanov & Stoikov (`arXiv 1011.6402`, *The Price Impact of Order Book
Events*): la relación entre **order flow imbalance (OFI)** y cambio de precio es
**lineal, con pendiente inversamente proporcional a la profundidad**, estable
entre escalas y activos. El corolario operativo es que **OFI crudo no sirve: hay
que normalizarlo por profundidad/liquidez**.

### 1.3 Sobre footprint / trapped traders NO hay literatura

Esto hay que decirlo con todas las letras: **la búsqueda de evidencia empírica
revisada sobre imbalances de footprint, stacked imbalances, absorción y
«trapped traders» devuelve exclusivamente material educativo comercial.** Cero
papers. Cero effect sizes publicados. Cero réplicas.

Corta para los dos lados:

- **En contra**: no hay ningún prior externo con el que calibrarse. La carga de
  la prueba es 100 % interna. Nadie publicó que funcione — y tampoco que no.
- **A favor**: es un espacio sin arbitraje documentado.

Lo que la literatura sí da son **las covariables discriminantes** — volumen en
el nivel, altura de la zona, toques previos, antigüedad — y todas, sin
excepción, ya están en el objeto zona de BigTrap2.

---

## 2. Mapeo — la literatura nombra exactamente lo que ya tenemos

Campos del dict de zona (`bigtrap2.py:156-192`):

| campo | qué es | qué discriminante de la literatura cubre |
|---|---|---|
| `vol` | volumen atrapado | «alto volumen ⇒ mayor estabilidad, menor ruptura» |
| `hi` − `lo` | **altura de la zona** | close-through exige cerrar más allá del borde lejano: más alta ⇒ mecánicamente más difícil de romper |
| `touches` | contador de toques | «rebote sube con toques previos» / depleción |
| `created_bar` | antigüedad al toque | «la fuerza decae con el tiempo» |
| `is_bull` | lado | dirección nativa |
| `end_reason` | `close_through` · `close_through_gap` · `max_age` · `max_touches` | **riesgos competitivos** |
| `ended_ms` | instante de muerte | duración → análisis de supervivencia |

**Todos son salidas del kernel. Ninguno requiere leer un precio post-entrada.**
Es decir: son target-free y **no gastan presupuesto de multiplicidad**.

---

## 3. Los análisis, ordenados por información por unidad de riesgo

### TIER 1 — target-free · costo de multiplicidad CERO · ejecutables hoy

---

#### A1 · Modelo nulo contra niveles aleatorios ⭐ *el más decisivo y el más barato*

**Qué.** Generar niveles horizontales al azar —misma altura, mismo horario,
misma distribución de distancia al precio— y comparar tasa de ruptura al primer
toque y supervivencia contra las zonas reales de BigTrap2.

**Por qué primero.** Es el diseño de `arXiv 2101.07410` y contesta la pregunta
que ninguna otra contesta: **¿BigTrap2 aporta algo por encima de «una línea
horizontal donde hubo volumen»?** Si la respuesta es no, ningún barrido de
parámetros lo va a salvar y hay que saberlo antes de gastar un peso.

**Costo.** Cero outcomes, cero multiplicidad. La maquinaria de permutación ya
existe (`explore.py`).

---

#### A2 · Supervivencia de la zona con riesgos competitivos (Kaplan-Meier + Cox) ⭐ *el más informativo*

**Qué.** La vida de una zona **es literalmente un problema de supervivencia con
riesgos competitivos**: nace, y muere por `close_through`, por `max_age`, por
`max_touches`, o queda censurada por el fin de sesión. Ignorar los riesgos
competitivos y censurar el resto **sesga el hazard** — es el error que la
literatura clínica lleva treinta años documentando.

- **Kaplan-Meier / función de incidencia acumulada**: tiempo desde el primer
  toque hasta la muerte, desagregado por causa.
- **Cox de riesgos proporcionales**: hazard de `close_through` en función de
  altura, `vol`, `touches`, antigüedad, hora del día.

**Qué compra.** El coeficiente de cada covariable **es** la respuesta a la
pregunta central del punto 0, obtenida sin tocar un solo outcome.

**Hipótesis mecánica pre-declarada** (para que no sea pesca): *la altura de la
zona domina*, porque close-through exige que el precio cierre más allá del borde
lejano — una zona más alta es más difícil de romper por construcción, no por
correlación. **Contra-hipótesis que la refutaría**: si la altura no reduce el
hazard, o si lo reduce a costa de una pérdida proporcionalmente mayor cuando sí
rompe, el efecto es contable y no económico.

---

#### A3 · El barrido de fuerza bruta, versión target-free

**Qué.** Para cada celda de la grilla de los 12 parámetros: nº de zonas, nº de
primeros toques, `f`, distribución de `end_reason`, **mediana de barras entre
primer toque y muerte**, altura, `vol`, cobertura de sesiones. Sin P&L.

**Criterio de selección de celdas.** No «la que más zonas produce» sino **la que
minimiza la fracción muerte-en-≤2-barras**. Hoy esa fracción es 92,9 %; una
celda que no la baje no puede ganar y no merece un test.

**Cómo leer el paisaje.** El `GT-Score` (`arXiv 2602.00080`) formaliza algo que
acá ya es regla: en un barrido, **lo que vale es una meseta estable, no un
pico**. Un óptimo aislado rodeado de celdas malas es ruido. Esto es exactamente
la regla de banda contigua del sello (§2-ter), y conviene aplicarla ya en Fase A.

**Advertencia declarada.** `invalidation_mode=FirstTouch` y `max_touches=1` son
**degenerados** para cualquier hipótesis de primer toque: matan la zona en el
mismo evento que la selecciona. Van en la grilla sólo como control negativo.

---

#### A4 · Depleción por toques

**Qué.** Toda la evidencia de H1 es sobre el toque nº 1 — el caso **virgen**,
que la literatura señala como **el más propenso a romper**. Medir la tasa de
ruptura por índice de toque (1º, 2º, 3º…) y su decaimiento temporal.

**Por qué importa.** Es corroboración independiente del hallazgo estructural, y
si la tasa de ruptura cae con el índice de toque, **la población entera de H1
estaba mal elegida** — y la corrección no cuesta un parámetro nuevo del
indicador, cuesta cambiar qué toque se mira. `touches` ya está en la zona.

---

### TIER 2 — requieren outcomes · requieren preregistro y tu OK

---

#### B1 · MFE/MAE (triple barrera) sobre la población

**Qué.** Excursión favorable y adversa máxima por evento, para diseñar barreras.

**Por qué.** El problema de potencia es **varianza**: `sd = 19,63` con máximo
+209 y mediana −2. Barreras acotadas la derrumban, y `SE ∝ sd`. Es la palanca de
potencia más grande que existe después de sumar instrumentos.

**El costo honesto, que hay que decir antes.** MFE/MAE **es outcome** (fijado en
INC-002). Y elegir las barreras mirando la distribución de MFE/MAE **es
selección sobre outcomes**: o se hace sobre una partición separada, o se cuenta
en la multiplicidad. No hay tercera opción, y el número redondo de la literatura
comercial —«mejora la expectativa 20-30 %»— es exactamente el tipo de cifra sin
procedencia que este proyecto no acepta.

---

#### B2 · Meta-labeling — pero con el filtro derivado de A2 ⭐ *la idea central*

El meta-labeling (López de Prado, *AFML* cap. 3) es la respuesta de manual a
«30 ganadores y 394 perdedores»: un modelo primario da el lado, un modelo
secundario decide **si tomar o pasar**, y su función explícita es **filtrar
falsos positivos y recortar costos de transacción**. Es literalmente el problema
del peaje: 424 peajes para cobrar 30 boletos.

**El riesgo obvio.** Con 30 positivos, un clasificador ML sobreajusta de forma
catastrófica. `arXiv 2604.15531` (*Spurious Predictability in Financial Machine
Learning*) y el propio análisis crítico de QuantConnect sobre meta-labeling
apuntan al mismo lugar.

**La salida, y es lo mejor que tiene este mapa:**

> **El modelo de supervivencia de A2 *es* el meta-label — y se ajusta sin tocar
> un solo outcome.**

Si el Cox identifica que altura y `vol` predicen «no muere al primer toque», esas
covariables son el filtro de meta-labeling, **derivadas del ciclo de vida y no
del P&L**. Después se gasta **un** test de outcomes sobre la población ya
filtrada, en vez de gastar uno por cada combinación de covariables.

Eso convierte un ejercicio de minería con 30 positivos en **una hipótesis
preregistrada con una covariable mecánicamente justificada**. Es la diferencia
entre buscar y predecir.

---

#### B3 · CSCV / PBO y Deflated Sharpe sobre el paisaje de parámetros

Bailey, Borwein, López de Prado & Zhu: la **CSCV** está diseñada específicamente
para estimar la probabilidad de que un óptimo de grid search sea sobreajuste, y
el **DSR** corrige selección bajo pruebas múltiples y no-normalidad. Con la
asimetría de esta distribución (máximo +209, mediana −2) la corrección por
no-normalidad **no es cosmética**.

Con `M_eff` ya declarado, es directamente aplicable al barrido de Fase B.

---

### TIER 3 — potencia e infraestructura

- **C1 · Sumar ES y NQ.** Los oráculos están y no se usaron. `SE ∝ 1/√n`: 4×
  eventos = 2× potencia. **Sin costo de multiplicidad y sin hipótesis nueva.**
  Es la mejora de potencia más barata disponible, y hoy el MDE está 22× por
  encima del efecto observado.
- **C2 · OFI normalizado por profundidad** como covariable del hazard de A2,
  siguiendo Cont-Kukanov-Stoikov. El dato tick con clasificación de lado
  agresivo ya existe (`trap_volume_source=AggressiveSide`).

---

## 4. Secuencia recomendada

```
A1  nulo vs niveles aleatorios     ->  ¿BigTrap2 aporta algo? decisivo y gratis
A2  supervivencia + Cox            ->  QUE distingue romper de aguantar
A4  depleción por toques           ->  ¿el toque 1 era el toque equivocado?
A3  barrido target-free            ->  paisaje de parámetros, meseta no pico
C1  sumar ES y NQ                  ->  potencia, gratis
      |
      v  ---- STOP: manifiesto + M_eff + riesgos + datos faltantes + OK de Nico ----
B1  MFE/MAE en partición separada  ->  diseño de barreras (baja la varianza)
B2  meta-label = filtro de A2      ->  UNA hipótesis, no una búsqueda
B3  CSCV/PBO + DSR                 ->  control de sobreajuste del barrido
```

Todo el Tier 1 más C1 se puede correr **sin gastar una sola hipótesis del
presupuesto** y sin acercarse al holdout. Y si A1 sale nulo, el resto no se corre.

---

## 5. Lo que la literatura recomienda y este proyecto ya hace

Las cinco recomendaciones de `arXiv 2604.15531` para búsquedas grandes de
parámetros: preregistrar, holdout estricto nunca mirado, corrección family-wise
sobre **todas** las combinaciones probadas, **documentar los intentos fallidos**
y validar contra intuición económica.

EdgeLab tiene las cinco instaladas: sellos preregistrados, firewall del holdout,
`M_eff` declarado, incidentes en cuarentena en vez de borrados, y el campo
obligatorio «justificación económica» en toda plantilla generadora. **El aparato
ya está construido; lo que falta es gastarlo en las preguntas correctas.**

---

## Aporte al referente

Este mapa reordena la pregunta de investigación: de «qué parámetros de BigTrap2
son rentables» —que exige outcomes, gasta multiplicidad y con 30 positivos
sobreajusta— a «qué hace que una zona aguante», que se contesta con el ciclo de
vida del propio indicador, target-free y a costo de multiplicidad cero. Y
localiza la única prueba que puede matar toda la familia por menos de lo que
cuesta un test (A1, contra niveles aleatorios). La distancia al edge neto se
reduce porque el orden de las mediciones cambió: primero lo que es gratis y
decisivo, después lo que es caro y condicional.
