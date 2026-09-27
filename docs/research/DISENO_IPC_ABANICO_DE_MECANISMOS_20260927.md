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
