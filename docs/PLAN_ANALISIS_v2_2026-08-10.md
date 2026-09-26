# PLAN DE ANÁLISIS v2 — BigTrap2, con el espacio de entradas abierto

**Fecha** 2026-08-10 · **NORTH_STAR** sha256 `21bb3b01a33e2b37…`
**Reemplaza** `ANALISIS_DISPONIBLES_BIGTRAP2_2026-08-10.md` (v1), que queda como
historia: su revisión de literatura sigue vigente, su ordenamiento no.

**Insumos**
- `ACTA_MUERTE_H1_2026-08-09.md` — el resultado y el diagnóstico
- `SESGO_DE_DISENO_2026-08-10_EL_TOQUE_COMO_UNICA_ENTRADA.md` — por qué v1 estaba mal ordenado
- v1 §1 — la literatura

---

## 1. Los dos ejes

v1 ordenaba por «target-free vs outcomes». Faltaba un eje, y es el que la
objeción de Nico expuso.

### Eje A — ESTADO vs EVENTO

**Evento**: instante discreto (un toque, una creación, una ruptura). Da una
población de N observaciones. Es lo único que se midió hasta hoy.

**Estado**: la configuración de zonas **vale en cada barra**, exista o no un
evento. `active_zone_count`, `distance_to_nearest_zone`, `nearest_zone_side`,
`zone_age`, `inside_zone`. No requiere que el precio vaya a ningún lado.

Consecuencia de potencia, con su techo declarado: un estimador por estado usa
todas las barras de todas las sesiones en vez de **2,11 eventos por sesión**. El
*design effect* medido en H1 fue **1,14**, o sea **~88 % de la varianza era
intra-sesión/idiosincrática** — justo la componente que promediar destruye.
**Techo honesto:** el número de bloques independientes sigue siendo **201
sesiones**; la ganancia no es √(280.000/424). Pero el MDE de 6,58 ticks brutos
no es una propiedad del mercado: **es una propiedad de haber muestreado 424 veces.**

### Eje B — INFORMACIÓN vs MONETIZACIÓN

H1 confundió las dos: probó *una forma de cobrar* y, al fallar, no dijo casi nada
sobre si hay *información*. Son separables, y la de información es más fácil, más
potente y más barata.

**Asimetría que hay que declarar de entrada:** un test de información es un
**falsador fuerte y un confirmador débil**. Si no hay información, la familia
muere. Si la hay, todavía no hay edge — falta que sobreviva a fricción y
ejecución. Por eso va primero: máximo poder de matar por mínimo costo.

### La matriz

|  | **TARGET-FREE** (gratis, sin multiplicidad) | **OUTCOMES** (requiere STOP) |
|---|---|---|
| **ESTADO** | F0.3 features de estado · F2 barrido | F4 test de información condicional |
| **EVENTO** | F0.2 censo completo · F1 nulo, supervivencia, depleción | F5 hipótesis de monetización |

---

## 2. El espacio de entradas — enumerado, que es lo que nunca se hizo

Familias de eventos que BigTrap2 genera, además del toque:

| # | familia | instante | estado hoy |
|---|---|---|---|
| E1 | **Creación de zona** | el trap acaba de ocurrir | censado (`post_sepmin.py`), **degradado a diagnóstico** en 2026-08-04, nunca evaluado |
| E2 | **Primer toque** | el precio llega | **lo único medido**; H1 muerta acá |
| E3 | **Toque n-ésimo** | toques 2, 3, … | `touches` existe en la zona; nunca se usó |
| E4 | **Invalidación / close-through** | la zona se rompe | **el desenlace dominante: 93 %.** H1 lo peleaba en contra |
| E5 | **Expiración por edad** | muere sin ser tocada ni rota | 16 casos observados; nunca analizado |
| E6 | **Aproximación sin toque** | se acerca y no llega | no medido |
| E7 | **Confluencia / apilamiento** | varias zonas al mismo precio | no medido |

Estados (valen en toda barra):

| # | estado | fuente |
|---|---|---|
| S1 | nº de zonas activas, por lado | `active_zone_count` |
| S2 | distancia a la zona más cercana y de qué lado | `distance_to_nearest_zone`, `nearest_zone_side` |
| S3 | precio dentro de una zona | `inside_zone` |
| S4 | antigüedad de la zona relevante | `zone_age` |
| S5 | **asimetría neta de volumen atrapado** arriba vs abajo | derivable de `vol` + `is_bull` |

> **E4 merece un renglón aparte.** El acta de muerte muestra que el close-through
> es el desenlace del 93 % de la población, con **0 de 394 ganadores** para el
> lado nativo. Eso es una regularidad enorme y H1 estaba parada del lado
> equivocado de ella. **No se sigue que la operación inversa gane** —su espejo
> exacto da bruto −0,30, también negativo— pero sí que la familia E4 es un objeto
> con estructura fuerte que nunca se estudió por derecho propio.

---

## 3. Las fases

### F0 — Reparar el marco · target-free · costo cero

**F0.1 · Enumerar y justificar.** Este documento §2 es el entregable. Toda
población futura declara de qué familia sale y por qué, con condición de
refutación (regla nueva de `SESGO_DE_DISENO…` §7).

**F0.2 · Censo COMPLETO de zonas.** ⭐ *la cifra que falta hace todo el programa*

Hoy se sabe que hubo 15.577 primeros toques. **No se sabe cuántas zonas
nacieron.** Medir: zonas creadas, cuántas se tocan alguna vez, cuántas mueren
por edad sin toque, distribución de `touches`, y el desglose de `end_reason`
sobre **todas** las zonas —no sólo las tocadas—.

*Por qué importa:* durante todo el programa se midió **un numerador sin
denominador**. Si la mayoría de las zonas nunca se toca, la población de H1 era
una minoría no representativa.

**F0.3 · Materializar features de estado.** Correr `materialize_features()` sobre
la serie de barras de las 201 sesiones y caracterizar S1–S5: distribución,
cobertura, autocorrelación, estacionalidad intradía. Sin retornos.

*Nota:* estrena en research una API construida el 2026-07-24 y jamás usada. Su
test existe (`tests/bridge/test_features.py`), pero conviene un control de
no-look-ahead explícito antes de apoyarse en ella.

---

### F1 — ¿La zona es un objeto real? · target-free · costo cero · **falsador fuerte**

**F1.1 · Nulo contra zonas aleatorias.** ⭐ *el test más decisivo y el más barato*

Generar zonas sintéticas que preserven **geometría, horario y frecuencia** de las
reales, pero **ubicadas al azar**. Comparar todo lo target-free: supervivencia,
tasa de ser tocadas, tasa de ruptura al toque, distribución de `end_reason`.

Es el diseño de `arXiv 2101.07410`, generalizado de «niveles» a «zonas» — la
corrección que v1 necesitaba, porque v1 lo formulaba como «tasa de ruptura al
primer toque» y volvía a meter el sesgo del toque por la ventana.

> **GATE DE MUERTE.** Si las zonas reales no se distinguen de las aleatorias en
> **ninguna** métrica, la familia entera muere y no se corre nada más. Ningún
> barrido de parámetros salva a un objeto que es indistinguible del azar.

**F1.2 · Supervivencia con riesgos competitivos.** ⭐ *el más informativo*

La vida de una zona **es** un problema de supervivencia: nace y muere por
`close_through`, `max_age` o `max_touches`, o queda censurada por fin de sesión.
Ignorar los riesgos competitivos y censurar el resto **sesga el hazard**.

- Kaplan-Meier y **función de incidencia acumulada** por causa.
- **Cox** del hazard de `close_through` sobre: altura (`hi`−`lo`), `vol`,
  `touches`, antigüedad, hora del día.

*Hipótesis mecánica pre-declarada:* **la altura domina**, porque close-through
exige cerrar más allá del borde lejano — más alta es más difícil de romper **por
construcción, no por correlación**.
*Cómo se refutaría:* si la altura no reduce el hazard, o si lo reduce a costa de
una pérdida proporcionalmente mayor cuando sí rompe, el efecto es contable y no
económico.

**F1.3 · Depleción por toques.** Tasa de ruptura por índice de toque (1º, 2º,
3º…) y su decaimiento temporal. La literatura dice que el rebote sube con toques
previos y decae con el tiempo — **H1 midió exclusivamente el toque nº 1, el caso
virgen, señalado como el más propenso a romper.** Si se confirma, la población de
H1 estaba mal elegida y corregirlo **no cuesta un parámetro nuevo**: cuesta
mirar otro toque.

---

### F2 — Barrido de fuerza bruta · target-free · costo cero

Grilla sobre los 12 parámetros de `PARAM_SPEC`, midiendo por celda **sólo** las
métricas de F0.2 y F1.2.

**Criterio de selección:** no la celda con más zonas, sino la que **minimiza la
fracción muerte-en-≤2-barras** (hoy 92,9 %) y maximiza la supervivencia mediana.

**Cómo leer el paisaje:** meseta estable, **no pico**. Un óptimo aislado rodeado
de celdas malas es ruido (`GT-Score`, `arXiv 2602.00080`); es la regla de banda
contigua del sello §2-ter, aplicada ya en fase target-free.

**Controles negativos declarados:** `invalidation_mode=FirstTouch` y
`max_touches=1` son **degenerados** para hipótesis de primer toque —matan la zona
en el mismo evento que la selecciona—. Entran sólo como control.

---

### F3 — Potencia · costo cero · sin hipótesis nueva

Sumar **ES y NQ**: los oráculos están y no se usaron. `SE ∝ 1/√n`. Es la mejora
de potencia más barata disponible, y hoy el MDE está 22× por encima del efecto
observado.

---

```
════════════ STOP ════════════
Antes de F4: manifiesto de campaña + número efectivo de hipótesis + riesgos +
datos faltantes → aprobación de Nico. Sin ese OK no se corre.  (CLAUDE.md)
══════════════════════════════
```

---

### F4 — ¿La información es económica? · outcomes · **UNA** hipótesis

**Test de información condicional.** ¿La distribución de retornos forward cambia
dado el estado de zonas (S1–S5), contra la incondicional? Muestreo **por barra,
no por evento**.

*Por qué es la mejor relación potencia/multiplicidad de todo el plan:* una sola
hipótesis, con la varianza intra-sesión —el 88 % del error de H1— atacada por
muestreo en vez de por suerte.

*Caveat declarado antes de correrlo:* información condicional **no** implica edge
cobrable; quedan fricción y ejecución. Falsador fuerte, confirmador débil.

---

### F5 — Monetización · outcomes · hipótesis preregistradas

**F5.1 · Meta-label derivado del hazard.** ⭐ *la idea central*

El meta-labeling es la respuesta de manual a «30 ganadores y 394 perdedores»:
modelo primario da el lado, secundario decide **tomar o pasar**, con función
explícita de filtrar falsos positivos y recortar costos de transacción — el
problema del peaje, literal.

Con 30 positivos un clasificador sobreajusta seguro (`arXiv 2604.15531`). La
salida:

> **El modelo de supervivencia de F1.2 *es* el meta-label, y se ajusta sin tocar
> un solo outcome.**

Las covariables del Cox que predicen «no muere al primer toque» **son** el
filtro, derivadas del ciclo de vida y no del P&L. Después se gasta **un** test
sobre la población filtrada. Convierte una minería en una hipótesis
preregistrada con covariable mecánicamente justificada.

**F5.2 · MFE/MAE para diseñar barreras.** Ataca la varianza (`sd` 19,63, máximo
+209, mediana −2). *Costo honesto:* MFE/MAE **es outcome** (INC-002), y elegir
barreras mirándolo **es selección sobre outcomes** — o se hace en partición
separada, o se cuenta en la multiplicidad. No hay tercera opción.

**F5.3 · Familias de entrada más allá del toque.** E1 (creación), E4
(invalidación), E5 (expiración) como hipótesis por derecho propio, cada una con
su justificación económica y su condición de refutación.

**F5.4 · Control de sobreajuste.** CSCV/PBO sobre el barrido y **Deflated Sharpe**.
Con esta asimetría (máx +209, mediana −2) la corrección por no-normalidad **no es
cosmética**.

---

### F6 — Holdout

Una sola apertura por candidato, por protocolo. No antes.

---

## 4. Secuencia y condiciones de muerte

```
F0.1  enumerar el espacio                    gratis   [hecho: este documento §2]
F0.2  censo COMPLETO de zonas                gratis   <- el denominador que falta
F0.3  features de estado                     gratis
   |
F1.1  nulo vs zonas aleatorias               gratis   ### GATE: si es nulo, MUERE LA FAMILIA ###
F1.2  supervivencia + Cox                    gratis   <- produce el meta-label de F5.1
F1.3  depleción por toques                   gratis
   |
F2    barrido target-free (meseta)           gratis
F3    sumar ES y NQ                          gratis
   |
   v ═══ STOP: manifiesto + M_eff + riesgos + datos faltantes + OK ═══
   |
F4    información condicional                1 hipótesis   ### si no hay información, no hay nada que monetizar ###
F5    monetización (meta-label, barreras, E1/E4/E5, CSCV)
F6    holdout — una sola apertura
```

**Todo lo anterior al STOP —F0 a F3— se corre sin gastar una sola hipótesis del
presupuesto y sin acercarse al holdout.**

---

## 5. Qué NO hace este plan

- **No reabre H1.** Está muerta por regla y así queda.
- **No reinterpreta el resultado de H1** a la luz del sesgo. El sesgo acota el
  *alcance* de la conclusión; no cambia el veredicto.
- **No promete que exista un edge.** F1.1 puede matar la familia entera en la
  primera fase, y ese es un resultado válido y barato.
- **No amplía tolerancias ni relaja gates.** Las reglas que mataron a H1 siguen
  vigentes con la misma dureza para todo lo que sigue.

---

## Aporte al referente

El plan reordena el programa alrededor de dos separaciones que hasta hoy estaban
colapsadas —estado vs evento, información vs monetización— y pone adelante los
dos análisis que pueden **matar toda la familia por costo cero** (F1.1) o
**producir el filtro de selección sin gastar outcomes** (F1.2). Reduce la
distancia al edge de la única forma barata que queda: dejando de gastar
presupuesto de multiplicidad en la familia de eventos equivocada y atacando por
muestreo el 88 % del error que era intra-sesión.
