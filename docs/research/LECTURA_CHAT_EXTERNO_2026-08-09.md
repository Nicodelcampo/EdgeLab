# Lectura del chat externo de ChatGPT — qué resuelve y qué no

**Fecha:** 2026-08-09 · Outcome-free · Holdout no tocado
**Fuente:** chat compartido por Nico, `chatgpt.com/share/6a78949b-…`, leído completo
(71.471 caracteres). Título *«Algoritmos HFT <10ms»*, del 1-ago al 9-ago.

> **Estatus de la fuente.** Es **ChatGPT leyendo un PDF exportado del proyecto**
> (aparece como `EDGELA~1`), con búsqueda web. **No es el auditor de EdgeLab** y no
> tiene autoridad de gate. Lo trato como **insumo asesor**: se evalúa por su
> contenido, no por su origen. Nada de lo que dice se ejecuta sin acto de Nico.

---

## 1. Lo primero, y es importante: no resuelve el bloqueante abierto

Nico lo compartió preguntando si resolvía cuestiones pendientes. **La cuestión que
hoy bloquea el Paso 2 no la toca.**

El chat **nunca menciona** `aVolCellPOI2`, `ref_side`, *fade* / *break*, §5.3, el
censo de primeros toques, ni PRED-004 a PRED-007. La pregunta de la regla
direccional no aparece en ninguna de sus 52 secciones.

Y su diagnóstico de situación es el de **julio**: dice que el cuello de botella
*«es de autoridad, identidad y reproducibilidad»* y ordena el roadmap con G8/G9
por delante. Eso describe el PDF que leyó, no el estado de hoy — el trabajo de
PRED-004 a 007, la atribución de barras de tick y el censo autoritativo son
posteriores al export.

**No hay contradicción con el repo. Hay desfase de fecha.** Queda registrado, no
resuelto en su contra.

## 2. Lo que sí aporta, y me hizo verificar un cuarto camino

Su tesis central es un reencuadre real:

> *«No preguntaría "¿Esta señal gana?". Preguntaría "¿Qué ocurre después de que
> aparece esta señal?"»*

Un *event study* con curva de respuesta, MFE/MAE, cuantiles y vida media **no
necesita elegir un signo**. Eso choca de frente con el impasse del borrador de
hoy, así que lo verifiqué en vez de descartarlo.

### 2.1 Camino D — descubrir la dirección midiendo la respuesta. **No cierra.**

La idea sería: correr el estudio de respuesta sobre una porción de sesiones,
quemarla como exploración, y sellar E-R1 con la dirección que salga para el resto.
Es la separación descubrimiento/confirmación que el propio chat exige.

**El presupuesto de potencia no lo permite.** `aVolCellPOI2` tiene **177 sesiones
con señal** y el piso es `MIN_STUDENTIZED_SESSIONS = 160`. Se pueden quemar **17
sesiones como máximo** — y 17 sesiones es demasiado poco para establecer un signo
que después se congela para las 160 restantes.

No es una objeción de principio: es aritmética, y da negativo.

### 2.2 Camino E — que la hipótesis no sea direccional. **Colapsa en C, con contenido.**

La letra de §5.3 es más precisa de lo que yo venía citando:

> *el candidato puede seguir como fenómeno exploratorio, pero **NO como hipótesis
> confirmatoria de edge**.*

Dice *«de edge»*, no *«confirmatoria»* a secas. Eso abre la puerta a una hipótesis
de **magnitud de respuesta** sin signo — que es exactamente lo que el chat
propone.

Pero §5.3 también dice, en la misma sección: *«no se puede usar valor absoluto
para afirmar un edge operable»*; y el Paso 6 *«aplica fricción 2,768 dentro del
resultado»* y emite VIVE/MUERE. **H1–H3 son hipótesis de edge.** Una
caracterización de respuesta no es una de ellas.

Así que E no rescata a `aVolCellPOI2` como H2. **Pero mejora a C**: en vez de
*«queda exploratorio»* —una etiqueta vacía— define **qué hacer con él**: curva de
respuesta, MFE/MAE, cuantiles, vida media, sin dirección y sin reclamar edge.

## 3. Consecuencia para el borrador de hoy

Los caminos siguen siendo tres, y el chat **no agrega uno cuarto viable**. Lo que
cambia es la recomendación:

| | antes | después de leer el chat |
|---|---|---|
| **A** dos brazos | recomendado si la multiplicidad lo absorbe | igual |
| **B** tesis de Nico | mejor que A si es genuina | igual |
| **C** exploratorio | *«salida honesta»* | **ahora tiene programa**: event study sin dirección |

## 4. Lo que verifiqué de sus afirmaciones sobre el proyecto

No repito lo que dice sin comprobarlo.

| afirmación del chat | verificación |
|---|---|
| *«el nulo permutado actual está roto»* | `edge_pipeline_inventory.md:66` describe permutación **por sesión, preservando OHLC intrabar, un shuffle por día** — o sea, no es el `np.random.shuffle` plano que critica. **Su objeción concreta no aplica**; si hay un defecto es otro. |
| *«\hat d = 0,2519, IC95% [0,073, 0,431]»* (memoria larga) | **No existe en este repo.** Viene del PDF exportado, probablemente de `CerebroSSRN`. **No verificable acá.** |
| *«N_eff extremadamente pequeño (~11–15)»* | `camp001.py:37` fija `N_EFF = 48`. Órdenes distintos; puede referirse a otro estimando. **Discrepancia registrada, no resuelta.** |
| ledger de trials → DSR | parcialmente construido: `g2_decision.py:35` ya tiene `n_trials_effective` y `n_effective`. |
| purged / embargoed validation, *overlap graph* | **ausentes**. Ver §5. |

## 5. Lo que sí conviene anotar como pendiente real

Tres cosas del chat que EdgeLab **no tiene** y que son pertinentes cuando se abran
outcomes — no antes:

1. **Solapamiento de ventanas y `N_eff`.** Con `T` hasta 34 y `sep_min=120`, dos
   eventos cercanos comparten futuro. El chat lo llama *overlap graph*; el efecto
   es que `n` bruto sobreestima la información. Toca directamente al MDE.
2. **Purga / embargo entre research y replicación.** Si un evento de research
   tiene ventana que se solapa con el inicio de la ventana de replicación, el
   *«OOS»* no es limpio.
3. **Placebo temporal como control negativo.** Correr la misma hipótesis con los
   eventos desplazados en el tiempo. Es barato y detecta *leakage* de timestamp.

Las tres son **outcome-free de diseño** y ninguna requiere abrir nada hoy.

## 6. Lo que NO adoptaría de su roadmap

Su Fase A pone G8/G9 antes de toda investigación. **Eso ya no describe al
proyecto**: EXPLORE-001 está autorizado y en curso, con la disciplina de
pre-registro cumpliendo esa función. Adoptar su orden sería retroceder.

Y su lista larga —Hawkes, PID, causal forests, MLOFI, subgroup discovery, GAM—
está bien priorizada *hacia el final*, pero depende de datos L2/order-book que
**EdgeLab no consume**. No es accionable hoy.

## 7. Qué decido y qué no

**Decido** registrar la lectura, la verificación de sus cuatro afirmaciones sobre
el repo, el rechazo aritmético del camino D y el contenido nuevo del camino C.

**No decido** entre A, B y C: sigue siendo de Nico y del auditor.

**No adopto** ninguna técnica del chat. Las tres del §5 quedan como pendientes
anotados, sin implementar.
