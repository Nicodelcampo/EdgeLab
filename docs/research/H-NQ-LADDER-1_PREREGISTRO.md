# H-NQ-LADDER-1 — Escaleras de liquidez sobre NQ — PRE-REGISTRO v0 (borrador)

**Fecha:** 2026-09-10
**Origen:** observación de Nico + sesión de investigación (Grok, luego revisión
adversarial de Notion AI con literatura)
**Estado:** `DRAFT_V0_PENDING_NICO_REVIEW` — ninguna corrida autorizada.
**Instrumento:** NQ · **Firewall:** todo pre-holdout, target-free hasta el
escalón 5 · `CAMPAIGN_OUTCOMES_OPENED=false`

> Este documento escribe QUÉ se va a medir y CON QUÉ CRITERIO se falsa ANTES
> de medir. Lo que se descubra mirando datos queda marcado exploratorio.

---

## 1. La hipótesis (lo que Nico ve en el chart)

> Cuando hay una escalera de liquidez —picos consecutivos de highs/lows casi
> iguales— sobre o debajo de una zona de interés como un cluster HFT, el precio
> suele ir a tomarla con fuerza.

**Declarada como hipótesis, no como hecho.** EQH/EQL como imán de liquidez es
folklore extendido del trading sin evidencia publicada que la sostenga. El
proyecto existe para medir esto, no para creerlo.

## 2. Event-space: qué cuenta como escalera (v0, a corregir por Nico contra el chart)

Una **escalera candidata** es, en su forma mínima:

- **Pivote:** extremo local con `k` barras (o ticks) más bajos a cada lado
  (pivot high) o más altos (pivot low). `k` abierto — ver decisiones.
- **Escalera:** `n` pivotes consecutivos del mismo signo cuyos precios caen
  dentro de una tolerancia `tol` en ticks respecto de su mediana (o del primero).
- **Ventana:** todos los pivotes dentro de una ventana máxima `W` de tiempo o
  barras.
- **Lado:** EQH (highs) y EQL (lows) son dos familias separadas.
- **Regla de no-superposición:** un pivote no puede pertenecer a dos escaleras;
  en caso de solape se define regla de adjudicación (propuesta: la de mayor `n`,
  empate → la más reciente).

**Decisiones abiertas de Nico (ninguna se fija mirando outcomes):**

| Parámetro | Rango candidato | Pregunta |
|---|---|---|
| Escala de análisis | barras 25t / 120t / pivots por swings | ¿sobre qué la ves en el chart? |
| `k` (barras por lado del pivote) | 3 / 5 / 8 | ¿qué tan "limpio" tiene que ser el pico? |
| `n` mínimo de picos | 2 / 3 | ¿dos iguales ya son escalera o hacen falta tres? |
| `tol` tolerancia | ±0,25 / ±0,50 / ±1,00 tick | ¿a qué distancia dejás de llamarlos iguales? |
| `W` ventana máxima | 15 min / 1 h / sesión | ¿cuánto puede estirarse en el tiempo? |

Estos rangos se proponen para conversar, no para barrer: el barrido de
umbrales sobre la etiqueta humana NO gasta presupuesto estadístico (target-free),
pero el detector final queda congelado antes del escalón 5.

## 3. Por qué reglas antes que ML (registrado para que no se rediscuta)

- Cohen, Balch & Veloso, *Trading via Image Classification* (ICAIF 2020,
  arXiv:1907.10046): los clasificadores sobre imágenes de candlesticks
  **recuperan reglas definidas algebraicamente** — la visión decodifica reglas,
  no las inventa. Si la escalera es escribible, el PNG es redundante; si no lo
  es, el modelo tampoco puede explicar qué aprendió y no pasa paridad.
- Snorkel / weak supervision (Stanford DAWN): expertos escriben labeling
  functions imperfectas y el sistema aprende su precisión; 2,8× más rápido que
  etiquetado manual. Las reglas de candidatos del escalón 2 son eso.
- El loop aprobar/descartar es active learning estándar; se implementa con un
  visor mínimo propio sobre los parquets (no Label Studio: overkill para un
  anotador y datos local-only).
- **Condición que puede reabrir ML:** si en el escalón 3 ninguna combinación de
  reglas reproduce las etiquetas de Nico con precisión/recall aceptable contra
  un set congelado.

## 4. Consistencia del etiquetador (precondición)

Antes de entrenar o ajustar nada: Nico etiqueta ~30 tramos (sí/no/dudoso),
espera al menos un día, re-etiqueta los mismos 30 a ciegas, se mide acuerdo
(Cohen's kappa). **Si κ < 0,6 la definición está ambigua y se vuelve al escalón
0.** Un detector no puede aprender lo que el etiquetador no se replica a sí
mismo.

## 5. Embudo

| Escalón | Contenido | Gasta presupuesto |
|---|---|---|
| 0 | Esta definición, corregida por Nico contra el chart | No |
| 1 | Test de consistencia del etiquetador | No |
| 2 | 3–5 reglas deterministas de candidatos sobre parquets NQ; censo target-free (cuántas, dónde, duración, lado) | No |
| 3 | Loop activo: visor → sí/no/dudoso → CSV append-only firmado; modelo/regla propone dudosos primero; set de etiquetas congelado por hash | No |
| 4 | Detector congelado `DETECTOR_LADDER_V1` evaluado sobre sesiones no usadas en 2–3 | No (evaluación del detector, no del precio) |
| 5 | **La hipótesis real:** ¿el precio toma la escalera más rápido/seguido cuando hay cluster HFT vivo cerca que un nivel placebo emparejado por distancia, horario y régimen? | **Sí — outcomes. Requiere OK escrito de Nico y manifiesto propio antes de correr** |

Controles declarados de antemano para el escalón 5:

- Placebo: mismo nivel desplazado del lado opuesto / mismo horario sin escalera.
- Control de co-localización: el 74 % de los contactos de nivel caen dentro de
  un cluster vivo (medido en H2, 2026-09-08) — estratificar por intensidad
  reciente de formación, o se mide régimen y no objeto.
- Escala: el desenlace debe resolverse con horizonte acorde al rango mediano de
  la barra elegida (lección H2 VOID POR ESCALA, 2026-09-08: umbral de 4 ticks
  sobre barras de 12 no mide nada).
- Look-ahead de runners: las zonas se entregan al FINALIZAR el streak
  (defecto registrado 2026-09-08, `f579ad4`); cualquier uso de zonas/clusters
  como covariable respeta el orden causal corregido.

MDE: se calcula y se publica ANTES de correr el escalón 5.

## 6. Muerte y alcance

La hipótesis muere si el contraste del escalón 5 queda dentro del MDE con la
potencia pre-registrada, en cuyo caso el alcance de la muerte es: "escaleras
EQH/EQL detectadas por DETECTOR_LADDER_V1, sobre NQ, en la ventana medida, con
cluster HFT como covariable" — nada más amplio.

## 7. Qué NO está medido hoy

- Que las escaleras existan como objeto estable (censo pendiente, escalón 2).
- Que el ojo de Nico sea replicable (escalón 1).
- Que el precio las busque (escalón 5).
- Que agreguen algo sobre el cluster HFT solo.

## Aporte al referente

Convierte una observación de chart en un objeto medible con su criterio de
falsación escrito antes del primer dato, reserva el gasto estadístico para la
única pregunta que lo requiere, y deja explícito que el aprendizaje humano-máquina
sirve para construir el detector, no para validar el edge.