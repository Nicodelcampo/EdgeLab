# IPC — abanico completo de mecanismos «la acumulación atrae» (diseño, 2026-09-27)

**North Star:** `ed4293b5587bb38b3070dba739b2b5f93a949402be0428c98e05ef385593a5f8`
**Estado:** DISEÑO. Nada medido con esto. Pedido enfático de Nico: iterar sobre **todas** las maneras de probar si la
acumulación de picos atrae, porque la etapa A cubría una parte chica del abanico. La spec `SPEC-IPC-REP-20260927`
(hash `2edc23b3bc4f`) **se descarta sin registrar**: ni la replicación ni sus resultados se abren.

## 1. Lecciones del Cerebro y de EdgeLab que condicionan el diseño
| Lección | Qué obliga |
|---|---|
| `LESSON-RH-BIGTRAP2-MAGNET` (F2.8): el «imán» de BigTrap2 murió contra un control sin zona de igual geometría | control sin zona siempre (C-SZ) y pico reciente (C-SW) |
| `LESSON-RH-TOUCH-ONLY-POPULATION`: todo BigTrap2 midió sólo el toque | enumerar creación / aproximación / toques / ruptura / vencimiento / estado antes de congelar |
| `LES-CTRL-TIMING-20260924`: un control previo al evento hereda el camino | controles de otras sesiones a la misma hora o posteriores a t0+h |
| `LES-R3-TRADE-PRICE-BOUNCE-20260925`: con TP/SL ≤ 3 t en ES, el rebote bid/ask domina el acierto | medir sobre el **precio medio** (bid+ask)/2 cuando las distancias son chicas; siempre contra control |
| `LES-R3-ENTRY-AT-LEVEL-GAP-20260925`: entrar «al nivel» cuando el trade ya lo saltó regala ticks | entrada al precio del trade que dispara (o al medio), con latencia |
| `LESSON-TICKS-F2-TIMING-NOT-COST` / TBZX-R3 (0 de 66.000 celdas con P&L > 0) | «hay información» no alcanza: la geometría tiene que poder pagar costo/W |
| ESPEJO (27/09): una barrera de fracaso puede esconder un efecto que llega más tarde | medir también **sin barrera**: probabilidad y tiempo hasta tocar dentro de un horizonte |
| Regla de dos canales y MDE | direccional (toca / no toca) **y** no direccional (distribución de penetración, excursión); MDE por celda |

## 2. El abanico (ejes), y qué cubrió la etapa A
| Eje | Alternativas | Etapa A |
|---|---|---|
| **Objeto** | detector estándar / estricto; picos (5–12+); ancho de la banda; pendiente; duración; techo / piso; escala 25t / 500t | 2 detectores, techo+piso juntos |
| **Liquidez del objeto** | volumen negociado en los picos; **profundidad L2 en reposo en el nivel** (jul–sep); confluencia con zonas HFT u otras acumulaciones | no |
| **Estado de la zona** | virgen / tocada n veces / penetrada parcialmente; edad; si ya se atravesó parte de la banda | virgen sí/no |
| **Alejamiento** | k·R (2, 4, 8), k·ATR, ticks absolutos; velocidad del alejamiento | k·R |
| **Volumen antes del acercamiento** | desde la creación, durante el alejamiento, durante el acercamiento; relativo a la sesión | terciles, sólo hasta el alejamiento |
| **Momento de entrada (evento)** | al confirmarse el alejamiento; **a mitad del acercamiento** (volvió f = 0,5 de D); **al final del acercamiento** (f = 0,8–0,9); primer toque; estado continuo (cada vela, distancia a la zona virgen más cercana) | sólo alejamiento |
| **Objetivo (qué es «atraer»)** | tocar el último pico; tocar el primer pico (final de la zona); **atravesar el nivel +1 / +3 / +10 t**; atravesar la banda completa; tiempo hasta tocar | último y primer pico, toque exacto |
| **Fracaso / horizonte** | barrera simétrica a D; barrera a k·D; **sin barrera, sólo horizonte** (N velas, fin de sesión, varios días) | barrera a 2D desde el nivel |
| **Medición** | precio de trade vs **precio medio**; latencia | precio de trade (máximo/mínimo de vela) |
| **Controles** | C-SZ, C-SW, entrada al azar con las mismas salidas, misma zona sin el evento | C-SZ, C-SW |
| **Contexto** | hora, lado del VWAP, tendencia de fondo, volatilidad, clima L2 (calm/normal/volatile/toxic) | no |
| **Economía** | TP en el nivel ± x t, SL, BE, tiempo máximo; costos propios por activo; una posición a la vez | no (sólo cuenta a posteriori: ES k 4 no puede pagar) |

**Lectura honesta:** la etapa A probó un único evento (alejamiento), un único resultado (toque exacto antes de una
barrera) y un único tipo de medición (precio de trade). Cubre quizás un 10 % del abanico. Su positivo es real dentro de
ese alcance, y no dice nada del resto.

## 3. Cómo cubrir el abanico sin fabricar falsos positivos
Una grilla cartesiana de todos los ejes daría decenas de miles de celdas: con 181 sesiones, la corrección por
multiplicidad no dejaría nada, y lo que sobreviviera sería selección. Propuesta en tres escalones, todo sobre
**descubrimiento** (jul-2025–mar-2026); la replicación (abr–sep) queda intacta para lo que sobreviva a los tres.

### Escalón 1 — Atlas del mecanismo (información, curvas completas, pocas decisiones)
En vez de una celda por combinación, **una curva por eje**: para cada evento se guarda el camino posterior completo
(sobre el precio medio) y se publican, real contra C-SZ y C-SW:
- probabilidad acumulada de tocar el nivel en función del tiempo (sin barrera) y con barrera a 1D / 2D;
- distribución de la penetración más allá del nivel (0, +1, +3, +10 t, banda completa);
- lo mismo condicionado a la fracción recorrida del acercamiento (f = 0 / 0,25 / 0,5 / 0,75 / 0,9), con el nulo de
  reflexión que ya usamos en espejo (desde la fracción f, P(llegar al nivel antes de volver a D) = f sin memoria);
- cortes de a un eje por vez (virginidad, edad, volumen previo, liquidez L2 en jul–sep sólo como descriptivo, contexto).
Es un perfil de respuesta en EXPLORACIÓN: descriptivo, no promueve nada. Lo que hace es **mostrar dónde está la
diferencia** (en qué momento de entrada, a qué profundidad de penetración, bajo qué estado).

### Escalón 2 — Grilla económica acotada (P&L, con presupuesto de pruebas)
Con lo que muestre el atlas se pre-registra una grilla chica (del orden de decenas de combinaciones, no miles):
momento de entrada × objetivo (nivel ± x t) × stop × tiempo máximo, **sólo con geometrías que puedan pagar el costo**
(objetivo ≥ ~5 × costo). Costos propios por activo, entrada al precio del trade que dispara con latencia, una posición
a la vez, control de entrada al azar con las mismas salidas. PBO/DSR con el número real de combinaciones del atlas + la
grilla (todas cuentan). Requiere el STOP: manifiesto + número efectivo de hipótesis + OK de Nico.

### Escalón 3 — Replicación única (abr–sep, HOLDOUT-A3)
Sólo las combinaciones que sobreviven al escalón 2, con A y B juntas, una sola vez, por la vía del Cerebro (spec
confirmada en revisión ciega → campaña → prueba). Después, el holdout a futuro.

## 4. Qué necesito de Nico antes del escalón 1
1. ¿El atlas con curvas completas (y no celdas) le parece la forma correcta de explorar el abanico?
2. ¿Agrega ejes que no estén en §2? (el pedido nombraba virginidad, alejamiento, volumen previo, entrada a mitad y al
   final del acercamiento, objetivo al final / al inicio de la zona, atravesando 3 y 10 t: están todos).
3. El atlas mira resultados (retornos) aunque sea descriptivo: por la regla STOP va con manifiesto propio y su OK.

## 5. Parametrización de la zona misma (pedido de Nico, 27/09)
Al entrenar el detector se vio que hay muchas maneras de decidir qué cuenta como zona. **Ese es un eje del abanico por
derecho propio**, y además el más delicado: si la definición de zona se elige mirando si atrae, se fabrica el imán.

### 5.1 Parámetros de la definición (hoy en `tools/peaks_rule.py`)
| Parámetro | Qué controla | Hoy (ES 25t) | Alternativas a enumerar |
|---|---|---|---|
| `w` | qué es un pico (pivote de w velas a cada lado) | 2 | 1, 2, 3 |
| `nmin` / picos mínimos | cuántos picos forman zona | 6 (+ filtro 8 estándar / 12 estricto) | 5 … 16 |
| `max_step` | cuánto puede cambiar un pico respecto del anterior (horizontalidad) | 2 t | 0, 1, 2, 4 t; en ATR |
| `min_pull` | retroceso mínimo entre picos (que sean picos de verdad) | 2 t | 0, 1, 2, 4 t; en ATR |
| `max_gap` | cercanía temporal entre picos | 60 velas | 15, 30, 60, 110 |
| tope de pendiente | qué tan empinada puede ser la serie | p90 de las marcas de Nico | sin tope, p75, p90 |
| duración mínima | tiempo total de la acumulación | 0 (ES), 40 velas (NQ) | 0, 20, 40, 80 |
| **comercio entre picos** | volumen negociado entre picos (liquidez acumulada) | no existe | volumen total, por pico, relativo a la sesión |
| **retesteo exacto** | picos al mismo precio vs escalonados | no existe | proporción de picos iguales al anterior |
| backfill | extender la serie hacia atrás | sí | sí / no |
| escala de vela | 25t, 500t, tiempo | 25t (y 500t aparte) | — |

### 5.2 Cómo elegirlos sin mirar si atraen
1. **Target-free primero:** la definición se valida con los juicios de Nico (✓/✗ en el visor, precisión fuera de
   muestra), como ya se hizo en ES (69 %), NQ (filtro sin validar) y 500t (73–86 %). La calidad de detección no mira
   retornos.
2. **Pocas definiciones, declaradas antes:** 3–5 definiciones de zona que cubran el espacio (p. ej. la validada, una
   estricta por cantidad de picos, una por horizontalidad exacta, una por comercio entre picos), congeladas antes del
   atlas. Cada una entra al atlas como un corte más y **cuenta en la multiplicidad**.
3. **Censo as-of de todas:** incluye zonas rotas y vencidas (regla de supervivencia del render).
4. **Prohibido** ajustar parámetros de zona después de ver curvas de atracción. Si el atlas sugiere que una
   definición atrae más, eso se prueba en replicación, no se re-optimiza en descubrimiento.

## 6. Uso posterior como imán en el experimento de espejos
Esta zona de picos es el candidato a «zona de alta liquidez» de la idea
`IDEA_ESPEJO_INTENTO_FALLIDO_LIQUIDEZ_20260927.md` (espejo como intento fallido de llegar a liquidez). Consecuencias
para el diseño de ahora:
- La definición de zona se implementa como **módulo único y causal** (conocida en el instante en que existe), para que
  el experimento de espejos use exactamente el mismo objeto, con su hash.
- Se publica, por zona, la geometría que espejos va a necesitar: nivel, banda, fecha de creación, estado (virgen,
  tocada, rota) en cada vela.
- **No se transportan resultados:** que la zona atraiga en IPC no es evidencia para espejos. Espejos la usa como objeto
  y hace su propia prueba, con sus controles (espejo sin zona, zona sin espejo).

## 7. Tanda ciega de definiciones de zona (27/09, congelada antes de juzgar y antes de cualquier curva)
Herramienta: `tools/build_zone_def_batch.py`. ES febrero 2026 (fuera de la muestra de enero con que se ajustó el detector). 125 zonas: 25 por definición, sin repetir, mezcladas; el visor no muestra a qué definición pertenece cada una (la membresía está en `artifacts/ipc/zone_defs/tanda_20260927.json`).
| Definición | Regla | Zonas en febrero |
|---|---|---|
| D1 validada | w 2, separación ≤ 60, escalón ≤ 2 t, retroceso ≥ 2 t, ≥ 8 picos, tope de pendiente p90 | 1.259 |
| D2 estricta | D1 con ≥ 12 picos | 776 |
| D3 horizontal | escalón 0 t (retesteo exacto), ≥ 5 picos | 949 |
| D4 comercio | D1 + volumen por vela entre picos ≥ 1,2 × la mediana previa de la sesión | 266 |
| D5 laxa | w 1, separación ≤ 30, escalón ≤ 4 t, retroceso ≥ 1 t, ≥ 5 picos, sin tope | 31.729 |
Criterio: precisión fuera de muestra por definición (✓ / juzgadas); vara ~70 %. D5 es de referencia (probablemente demasiado laxa).

### 7.1 Resultado de la tanda (28/09, juicios de Nico a ciegas con cortina; 125 zonas: 64 ✓ (2 «más larga»), 61 ✗)
| Definición | Juzgadas que la contienen | ✓ | Precisión |
|---|---|---|---|
| D1 validada | 77 | 61 | **79 %** |
| D2 estricta | 60 | 50 | **83 %** |
| D3 horizontal (retesteo exacto) | 25 | 2 | **8 %** — rechazada |
| D4 comercio entre picos | 38 | 26 | **68 %** — en el límite |
| D5 laxa | 47 | 14 | **30 %** — rechazada |
- Pasan a la etapa siguiente **D1, D2 y D4** (D4 en el límite de la vara del 70 %, se declara así). D3 y D5 quedan en el censo de **definiciones rechazadas** (auditoría 046 §9).
- La membresía se superpone (una zona puede estar en varias definiciones): las precisiones no son independientes.
- **Sólo precisión.** La cobertura (recall: zonas reales que cada definición no detecta) no está medida; requiere rangos marcados por Nico.
