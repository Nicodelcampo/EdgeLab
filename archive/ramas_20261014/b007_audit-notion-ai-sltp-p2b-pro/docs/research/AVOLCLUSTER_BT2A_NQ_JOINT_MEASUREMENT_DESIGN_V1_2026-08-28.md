# AVolClusterPOI + BigTrap2Absorption NQ — diseño integral de medición conjunta V1

**Fecha:** 2026-08-28  
**Estado:** `DRAFT_DESIGN_ONLY_PREAUTHORIZATION`  
**Instrumento primario:** NQ  
**Autoridad AVol:** kernel Python research v0.5; no se reclama paridad-oráculo NT8.  
**Holdout:** `20260701–20261231`, cerrado.  
**Ejecución autorizada:** no.

## 1. Propósito y límites

Este documento registra el catálogo completo de ideas para medir AVolClusterPOI,
BigTrap2Absorption (BT2A), sus relaciones temporales y espaciales, heterogeneidad
horaria y moderación por contexto L2. Es un diseño; no autoriza build, lifecycle,
first touch, first passage, MFE/MAE, P&L, join L2 ni acceso al holdout.

La infraestructura vigente de PR #22 sólo cubre creación target-free de zonas
`OFF_PRICE`. Toda medición de futuro requiere specs, freezes y tokens separados.

## 2. Qué representa cada componente

| Componente | Rol científico |
|---|---|
| AVolClusterPOI | Geometría de una concentración anómala de volumen por precio |
| `ZONE_CREATED` | Instante causal en que la geometría queda disponible |
| `FIRST_TOUCH` | Reloj de interacción posterior entre precio y zona |
| BT2A / `K_ABS` | Hipótesis de absorción/trampa con dirección causal propia |
| `K_BT2` | Brazo BigTrap2 de comparación y confluencia |
| L2 | Estado microestructural observable antes del evento |
| Fase horaria | Régimen institucional ex ante |
| Outcomes | Recorridos posteriores; nunca forman parte del detector target-free |

`geometric_side` sólo indica si la zona quedó por debajo o por encima del cierre.
No es una predicción direccional ni un sustituto de BT2A.

## 3. Configuración AVol primaria ya seleccionada target-free

```text
instrument                 = NQ
tick_size                  = 0.25
bar_type                   = tick_120
window_bars                = 5
nominal_ticks_per_block    = 600
median_multiplier          = 2.0
max_gap_ticks              = 1
min_cluster_ticks          = 4
detection_percentile       = 95.0
min_samples_per_bucket     = 10
lookback_sessions          = 20
one_cluster_per_block      = true
config_id                  = tick_120_W5_M20_C4_P950
```

Resumen target-free observado que el Event Store de creación deberá reproducir:

```text
contract-sessions          = 234
OFF_PRICE                  = 5876
AT_PRICE excluded          = 3728
sessions with OFF_PRICE    = 233
coverage                   = 99.6%
mean width                 = 14.8 ticks
width p95                  = 26 ticks
fitness target-free        = 0.9987
```

Estos números caracterizan densidad, cobertura y geometría. No prueban valor
predictivo ni optimalidad universal de 120 ticks.

## 4. Capas de medición de AVolClusterPOI

### 4.1 Creación target-free

Por zona se registra:

- `event_id`, `identity_sha256`, configuración, contrato y sesión;
- `created_ts_utc_ns` y primer instante causal disponible;
- límite inferior, límite superior y ancho en ticks;
- cierre del bloque, lado geométrico y distancia a la zona;
- `zone_score`, threshold, exceso sobre threshold;
- conteos de historia y sesiones históricas;
- frecuencia, cobertura y estabilidad por sesión/contrato/hora/configuración;
- persistencia geométrica y solapamiento entre configuraciones.

Esta capa no puede contener first touch, retornos, recorridos, P&L ni outcomes.

### 4.2 Lifecycle y primer toque

Una spec futura separada deberá medir:

- si la zona fue tocada;
- timestamp, tick, barra y edad del primer toque;
- tiempo, ticks y barras desde creación;
- contacto con borde inferior, superior o penetración;
- probabilidad acumulada de toque y supervivencia sin toque;
- hazard por edad de zona;
- expiración sin toque;
- reingresos y segundos toques como familia secundaria;
- invalidación y colapso de zonas solapadas mediante reglas congeladas.

La barra de creación es inelegible para first touch. El reloj empieza en el
primer dato causalmente disponible después del cierre creador.

### 4.3 Expansión no direccional

Hipótesis H1: el primer toque de una zona `OFF_PRICE` cataliza expansión absoluta,
sin asumir dirección. Medidas candidatas:

- rango absoluto posterior;
- volatilidad realizada pre/post;
- excursión máxima absoluta;
- tiempo hasta cualquiera de dos barreras simétricas;
- probabilidad de alcanzar ±5, ±9, ±18 o ±30 ticks;
- velocidad de expansión;
- compresión previa versus expansión posterior;
- número de cambios de dirección;
- timeout por horizonte en ticks, segundos y barras.

### 4.4 Resolución direccional

Una vez congelado el reloj de toque se podrán medir:

- `TP_FIRST`, `SL_FIRST`, `TIMEOUT`;
- `d_hat` con la definición vinculante del repositorio;
- MFE y MAE;
- dirección y tiempo del primer pasaje;
- continuación versus reversión;
- velocidad favorable y adversa;
- sensibilidad por barrera y horizonte.

Esto es recorrido, no P&L. Costos, órdenes y ejecución pertenecen a otro gate.

## 5. Hipótesis conjuntas AVol + BT2A

### H1 — Catalizador no direccional

El first touch AVol aumenta la expansión absoluta frente a `N_RAND`, Mirror y
Time-Shuffle, sin atribuirle una dirección a la geometría.

### H2 — Resolución direccional por absorción

BT2A ocurrido causalmente cerca del toque mejora la resolución direccional del
recorrido frente a AVol solo y BT2A solo.

### H3 — Complementariedad incremental

La combinación aporta información adicional, no explicada por la suma simple de
ambos indicadores.

```text
interaction = E[Y | AVol + BT2A]
            - E[Y | AVol only]
            - E[Y | BT2A only]
            + E[Y | neither]
```

### H4 — Secuencia causal

El efecto depende de si BT2A ocurre antes, durante o después del primer toque.

### H5 — Moderación L2

La profundidad, OFI, spread, depleción y absorción del libro modifican el efecto
conjunto.

### H6 — Heterogeneidad horaria

La interacción cambia entre fases institucionales predefinidas, sin seleccionar
la “mejor hora”.

### H7 — Consenso multiconfiguración

Las zonas detectadas por varias configuraciones target-free presentan distinta
estabilidad o respuesta que zonas detectadas por una sola configuración.

## 6. Política de instrumento

La corrida primaria debe usar el mismo instrumento y reloj:

```text
AVol NQ + BT2A NQ + L2 NQ
```

Antes del join hace falta un Event Store BT2A NQ con detector, coordenadas,
paridad/autoridad y población congelados. Las celdas positivas observadas en GC
no se trasladan automáticamente a NQ.

Una corrida `AVol NQ + BT2A GC` sería un estudio cross-market de lead-lag. Debe
usar otra spec, otra familia y otra autorización; no puede presentarse como
confluencia sobre un mismo mercado.

## 7. Taxonomía completa de relaciones lógicas

### 7.1 Secuencia temporal

1. `AVOL_CREATED → BT2A → AVOL_TOUCH`.
2. `AVOL_CREATED → AVOL_TOUCH → BT2A`.
3. `BT2A → AVOL_CREATED → AVOL_TOUCH`.
4. BT2A y toque dentro de la misma ventana causal.
5. Toque AVol sin BT2A próximo.
6. BT2A sin zona AVol elegible próxima.
7. Ningún evento: control de base comparable.

Ventanas temporales candidatas alrededor del toque:

```text
[-120s,-30s)
[-30s,-5s)
[-5s,0)
[0,+5s)
[+5s,+30s)
[+30s,+120s]
```

Se deben congelar también ventanas en ticks o barras, porque 120 ticks no tiene
una duración constante. Ningún timestamp posterior puede alimentar un feature
pre-touch.

### 7.2 Relación espacial

BT2A se clasifica como:

- dentro de la zona;
- sobre borde inferior;
- sobre borde superior;
- fuera y cerca, hasta 25% del ancho;
- entre 25% y 100% del ancho;
- lejos, a más de un ancho;
- durante penetración;
- después de atravesar por completo;
- aproximándose a la zona;
- alejándose de la zona.

```text
normalized_distance = distance_to_zone_ticks / zone_width_ticks
```

### 7.3 Acuerdo y desacuerdo direccional

La dirección proviene de BT2A/delta, no de `geometric_side`:

- absorción alcista en borde inferior;
- absorción bajista en borde superior;
- absorción alcista en borde superior;
- absorción bajista en borde inferior;
- BT2A a favor del movimiento de llegada;
- BT2A contra el movimiento de llegada;
- `K_ABS` y `K_BT2` coincidentes;
- `K_ABS` y `K_BT2` en desacuerdo;
- ausencia de dirección causal elegible.

### 7.4 Estados y episodios

```text
ZONE_CREATED
  → WAITING_FOR_TOUCH
  → FIRST_TOUCH
  → BT2A_CONFIRMATION | NO_CONFIRMATION
  → EXPANSION | REJECTION | TIMEOUT
```

Zonas solapadas necesitan una regla de episode collapse previa a outcomes. El
análisis primario debe usar una sola ancla por episodio (`FIRST_ELIGIBLE_EVENT_WINS`).
Segundos toques, reingresos y recurrencia quedan como familias secundarias.

### 7.5 Intensidad o dosis

Variables AVol:

- percentil del score;
- exceso sobre threshold;
- ancho;
- distancia inicial;
- edad al toque;
- número de configuraciones coincidentes;
- persistencia espacial.

Variables BT2A:

- brazo `K_ABS`/`K_BT2`;
- magnitud de absorción y delta absorbido;
- cantidad de eventos próximos;
- lag respecto del toque;
- distancia espacial normalizada;
- posición dentro/borde/fuera de la zona.

Se prueban gradientes y cuantiles congelados; no se busca el umbral óptimo después
de abrir outcomes.

## 8. Catálogo de comparaciones

Poblaciones mínimas:

1. AVol + `K_ABS`.
2. AVol + `K_BT2`.
3. AVol sin BT2A.
4. `K_ABS` sin AVol.
5. `K_BT2` sin AVol.
6. AVol + BT2A en acuerdo.
7. AVol + BT2A en desacuerdo.
8. AVol tocada versus AVol no tocada dentro de un horizonte.
9. AVol multiconfiguración versus configuración única.
10. Controles sin AVol ni BT2A.

Estimandos:

- efecto AVol versus control;
- efecto BT2A versus control;
- interacción difference-in-differences;
- hazard ratio de toque;
- hazard competitivo favorable/adverso/timeout;
- cambio de volatilidad pre/post;
- cambio en `d_hat`;
- diferencia MFE/MAE;
- incremento de información fuera de muestra.

## 9. Controles y nulls

- `N_RAND`: timestamps comparables en sesión, hora, volatilidad y disponibilidad.
- Mirror Null: geometría reflejada sin usar futuro.
- Time-Shuffle: timestamps permutados dentro de bloques compatibles.
- Matched Geometry: mismo ancho, distancia, score, hora y régimen.
- BT2A-shuffle: preservar densidad por sesión/fase, romper proximidad al toque.
- L2-shuffle: preservar distribución, romper correspondencia temporal.
- Placebo leads: “efectos” antes de que la zona estuviera disponible.

Un placebo lead distinto de cero invalida interpretación causal y exige revisión
de leakage o sesgo de selección.

## 10. Familias de configuración

### 10.1 AVol primaria

`tick_120_W5_M20_C4_P950` es la única configuración primaria.

### 10.2 Robustez local

Sólo se admiten configuraciones realmente presentes en el sweep target-free.
Perturbaciones propuestas de un factor:

- barras: 60, 120, 240 ticks;
- ventanas: 3, 5, 8 barras;
- multiplicador: 1.5, 2.0, 2.5;
- cluster mínimo: 3, 4, 5 ticks;
- percentil: 90, 95, 97.5.

Las alternativas miden estabilidad; no compiten por el máximo outcome.

### 10.3 BT2A

Para NQ se congela la familia completa de primer pasaje:

```text
B = 5, 9, 18, 30 ticks
H = 25, 50, 100, 250 observaciones
family = 16 celdas
```

Las celdas GC `9×25`, `30×100`, `30×250` son sólo anotaciones externas. No
pueden reducir la familia NQ ni recibir prioridad.

## 11. Ventanas horarias NQ

Todas usan `America/Chicago`, DST IANA e intervalos `[inicio,fin)`.

### Familia primaria gruesa

| Fase | CT |
|---|---:|
| `NQ_ASIA_ETH` | 17:00–01:00 |
| `NQ_EUROPE_PRE_US` | 01:00–07:30 |
| `NQ_US_PREOPEN_OPEN` | 07:30–09:30 |
| `NQ_US_CORE_PM` | 09:30–16:00 |

### Desglose fino descriptivo

| Ventana | CT |
|---|---:|
| `ASIA_ETH` | 17:00–01:00 |
| `EUROPE` | 01:00–07:30 |
| `US_PREOPEN` | 07:30–08:30 |
| `CASH_OPEN` | 08:30–09:30 |
| `US_MORNING` | 09:30–11:30 |
| `US_LUNCH` | 11:30–13:00 |
| `US_AFTERNOON` | 13:00–15:00 |
| `POST_CASH` | 15:00–16:00 |

La familia gruesa puede ser primaria; las ocho ventanas son descriptivas salvo
freeze separado. Se aplica blackout macro FOMC/CPI/NFP `[release,release+5m)`.

## 12. Contexto L2

### 12.1 Join causal

El join debe ser `as-of backward`: para creación, toque o BT2A sólo se utiliza el
último snapshot conocido antes del evento. Debe congelar:

- mismo instrumento y contrato;
- clock acreditado y unidad temporal;
- staleness máximo;
- política ante gaps;
- cobertura por sesión y fase;
- hash de fuente y contrato común;
- cero forward-fill a través de gaps no permitidos.

### 12.2 Features candidatas

- spread y spread relativo;
- profundidad bid/ask por niveles;
- order-flow imbalance;
- microprice;
- trades agresivos;
- cancelaciones y adiciones;
- queue depletion;
- pendiente y convexidad de profundidad;
- liquidez dentro y alrededor de la zona;
- absorción pasiva;
- velocidad de mensajes;
- resiliencia después de barrer niveles.

### 12.3 Estados congelables

```text
LIQUIDITY_THIN | LIQUIDITY_NORMAL | LIQUIDITY_THICK
OFI_SELL | OFI_NEUTRAL | OFI_BUY
SPREAD_NORMAL | SPREAD_WIDE
QUEUE_STABLE | QUEUE_DEPLETING
L2_CONFIRMS_BT2A | L2_CONTRADICTS_BT2A | L2_NEUTRAL
```

L2 entra primero como estratificador, no como filtro que elimina señales. Sólo
una spec posterior puede convertir un estado en gate operativo.

### 12.4 Gates L2

- reloj resuelto;
- procedencia limpia;
- mismo instrumento/contrato;
- contrato común acreditado;
- al menos 40 sesiones efectivas por estrato;
- cobertura y staleness reportados;
- HMM final no ejecutado con outcomes;
- CTX-3 cerrado hasta cumplir el contrato L2 existente.

## 13. Modelos complejos permitidos

### 13.1 Supervivencia y riesgos competitivos

- tiempo a first touch;
- expiración sin toque;
- tiempo a barrera favorable;
- tiempo a barrera adversa;
- timeout;
- BT2A/L2 como covariables dependientes del tiempo cuando el clock lo permita.

### 13.2 Información incremental fuera de muestra

Modelos anidados:

1. base: hora, volatilidad, ancho, distancia y edad;
2. base + AVol;
3. base + BT2A;
4. base + AVol + BT2A;
5. base + AVol + BT2A + L2.

Métricas: Brier score, log loss, calibración, error de tiempo a toque y estabilidad
entre contratos. Splits por sesiones completas y orden temporal; nunca eventos
de una misma sesión en train y validación.

### 13.3 Interacciones

```text
AVol × BT2A
AVol × BT2A × phase
AVol × BT2A × L2
AVol × BT2A × phase × L2
```

La interacción de cuarto orden es secundaria salvo potencia y cobertura
preacordadas. No se interpreta una celda escasa como ausencia de efecto.

## 14. Control de explosión combinatoria

No se ejecuta el producto cartesiano completo de configuraciones, ventanas,
contextos y outcomes. Ejemplo prohibido:

```text
11 AVol configs × 16 BT2A cells × 8 windows × 6 L2 states × 10 outcomes
= 84,480 comparisons
```

Gates jerárquicos:

1. **Gate A — AVol:** configuración primaria, lifecycle y expansión absoluta.
2. **Gate B — Confluencia:** AVol primaria + familia BT2A completa, sin hora/L2.
3. **Gate C — Clock:** sólo estimandos congelados de B, cuatro fases primarias.
4. **Gate D — L2:** moderación sobre familias que completaron cobertura.
5. **Gate E — Robustez:** perturbaciones target-free de un factor.

Cada gate tiene su familia de multiplicidad. Un gate incompleto produce
`ABSTAIN`, no selección oportunista de subconjuntos.

## 15. Inferencia y potencia

- unidad de cluster: sesión CME;
- pesos iguales por sesión como estimando primario;
- intervalos bootstrap/wild cluster definidos antes de outcomes;
- Holm dentro de cada familia preregistrada;
- reporte de tamaño de efecto e IC, no sólo p-value;
- cobertura mínima por contraste y por estado;
- `N≥400` eventos no garantiza potencia si hay clustering;
- potencia requiere MDE, ICC, densidad por fase y sesiones efectivas;
- contratos y meses se reportan como estabilidad, no réplicas iid.

## 16. Esquema lógico del join

Cada observación conjunta debería vincular:

- `zone_event_id` y `zone_episode_id`;
- configuración AVol y geometría de creación;
- `first_touch_event_id` y edad;
- BT2A event id, brazo, dirección, lag y distancia espacial;
- fase horaria coarse/fine;
- snapshot L2 causal, edad y staleness;
- null/control id;
- outcome family, barrera y horizonte;
- hashes de todas las fuentes;
- flags de holdout, P&L y acceso a futuro.

Debe existir una vista por zona y otra por evento BT2A para evitar que la elección
del denominador cambie silenciosamente.

## 17. Outputs futuros

1. Event Store de creación AVol.
2. Event Store de lifecycle/first touch.
3. Event Store BT2A NQ.
4. Context Store L2 causal.
5. Join canónico hash-bound.
6. Checkpoints por sesión.
7. Resultado por familia y manifest de cobertura.
8. Tablas de abstención, exclusión y nulls.
9. Reporte descriptivo por contrato/hora/configuración.
10. Resultado de interacción sin selección de ganador.

## 18. Preguntas que la corrida debe responder

1. ¿First touch AVol incrementa expansión absoluta?
2. ¿BT2A mejora la dirección después del toque?
3. ¿La combinación aporta más que cada indicador por separado?
4. ¿Importa el orden creación/toque/BT2A?
5. ¿Importa la posición espacial de BT2A respecto de la zona?
6. ¿El efecto cambia por fase horaria?
7. ¿L2 confirma o contradice la confluencia?
8. ¿La conclusión es estable entre configuraciones y contratos?
9. ¿Sobrevive a N_RAND, Mirror, Time-Shuffle y placebos?
10. ¿Hay cobertura o corresponde `ABSTAIN`?

## 19. Roadmap de autorización

```text
Gate 0  audit/freeze AVol creation contract
Gate 1  build checkpoints de creación
Gate 2  finalize y validate creation store
Gate 3  design/freeze lifecycle y episode collapse
Gate 4  execute first-touch store
Gate 5  build/audit BT2A NQ store
Gate 6  accredit L2 clock/context
Gate 7  freeze causal join
Gate 8  freeze outcome families/nulls/inference
Gate 9  execute pre-holdout measurement
Gate 10 economic protocol, only if separately authorized
```

Ningún token anterior autoriza el gate siguiente.

## 20. Firewalls vigentes

```text
DESIGN_REGISTERED                  = true
JOINT_MEASUREMENT_SPEC_STATUS      = DRAFT_DESIGN_ONLY_PREAUTHORIZATION
AVOL_ZONE_STORE_REAL_BUILD         = NOT_RUN
AVOL_FIRST_TOUCH_IMPLEMENTED       = false
BT2A_NQ_EVENT_STORE_READY          = false
L2_CONTEXT_READY                   = false
CAUSAL_JOIN_BUILT                  = false
FUTURE_PRICE_PATH_ACCESSED         = false
MFE_MAE_ACCESSED                   = false
FIRST_PASSAGE_ACCESSED             = false
PNL_ACCESSED                       = false
HOLDOUT_TOUCHED                    = false
WINNER_SELECTED                    = false
EDGE_DECLARED                      = false
PROMOTION_ELIGIBLE                 = false
EXECUTION_TOKEN                    = null
```

## 21. Criterios de refutación

El diseño falla si:

- `geometric_side` se usa como dirección sin regla causal;
- el join usa datos L2 posteriores;
- una zona se cuenta múltiples veces sin episode collapse;
- la selección de configuración usa outcomes;
- se transfieren celdas GC a NQ como ganadoras;
- se cambian ventanas, barreras o thresholds después de abrir resultados;
- se trata cada evento como independiente;
- se omiten nulls fallidos;
- se decodifica holdout;
- se presenta recorrido bruto como P&L o edge.

## Aporte al referente

AVol aporta geometría y reloj de contacto; BT2A aporta una hipótesis direccional;
L2 aporta régimen microestructural y el clock institucional aporta heterogeneidad.
El diseño registra cómo medir creación, toque, expansión, dirección, interacción,
secuencia, espacio, dosis, supervivencia y robustez sin convertir ningún
indicador en oracle ni autorizar outcomes.
