# Reporte de la noche — 2026-07-27

**Referente**: `docs/NORTH_STAR.md` sha256 `21bb3b01a33e2b37…`
Tres procesos de fondo + TICKBAR-001 completo. Todo commiteado.

---

## 1. TICKBAR-001 / PRED-003

**Implementado, verde en la suite, sin gastar un solo oráculo.**

La enmienda de PRED-003 con P1–P11, los dos defectos y la frontera demostrada se
escribió **antes** de tocar código.

### Los dos defectos, corregidos juntos

**`BigTrap2.cs` v2.1 → v2.2 — secuenciador causal auto-verificante.** Snapshot
inmutable por barra (7 valores), FIFO de eventos en bloques de exactamente K, dos
colas y `DrainReadyBars()` que empareja snapshot N con bloque N en orden
cronológico estricto y **sólo cuando las dos piezas están**. Frontera por
timestamp del evento contra `SessionIterator`. Bloque residual 1..K−1. Verificador
OHLC en ticks enteros. Política de rotura: mismatch ruidoso, sesión marcada, y
resincronización sólo en la frontera siguiente.

**`bars.py` — `build_tick_bars` con reinicio por sesión.** Particionaba global
mientras NT8 reinicia en cada frontera; se separaban en la **primera** (23 ticks
con K=25, 392 tras 33 sesiones). Este defecto **no lo mide** `FOOTPRINT_MISMATCH`,
que compara NT8 consigo mismo: estaban superpuestos y sólo uno estaba
diagnosticado.

### P6 — el invariante crítico, cumplido

Ledger `time:1` regenerado **bit-idéntico**: sha256 `998e12b29fd598e1…`, mismo
`config_id`, 225 zonas, `paridad=PASS`. El refactor no movió una línea de la
salida.

### Condiciones para gastar oráculo

| condición | estado |
|---|---|
| suite verde | ✅ **377 passed** |
| `time:1` bit-idéntico (P6) | ✅ |
| tests sintéticos de frontera / residual / orden / OHLC | ✅ **25 tests** |

Commits: `3686d35` (secuenciador + kernel), `587ed91` (tests + reglas de familia).

---

## 2. Gates de los oráculos — **7 de 8 en PASS**

| oráculo | resultado | py / nt8 / matched |
|---|---|---|
| **Gaps2** | ✅ **PASS** | 1316 / 1316 / 1316 |
| **BigTrap2** `time:1` (O1) | ✅ **PASS** | 225 / 225 / 225 |
| **BigTrap2** `wick off` (O3) | ✅ **PASS** | 393 / 393 / 393 |
| **BigTrap2** `SameLevel` (O2′) | ✅ **PASS** | 425 / 425 / 425 |
| **HFTZones2 v2.3** | ✅ **PASS** | 1599 / 1599 / 1599 |
| **AACloseOpenDiffs v1.2** | ✅ **PASS** | 1803 / 1803 / 1803 |
| **VolTicksPOC2** (warmup) | ✅ **PASS** | 23 / 23 / 23 |
| **aVolCellPOI2 v2.1** | ⛔ **DATA_INTEGRITY_FAIL** | 140 / 144 / 117 |

### Lo que se ganó esta noche

- **`AACloseOpenDiffs v1.2`**: el fix de enteros queda **validado con paridad
  exacta**. Era el que descartaba el 47,6 % de los gaps de 1 tick.
- **`HFTZones2 v2.3`**: PASS completo. El `.cs` había quedado en v2.2 mientras el
  kernel ya era v2.3; corregido y validado.
- **`BigTrap2` O3 y O2′**: las dos ramas que O1 no podía ejercitar
  (`wick_filter` apagado, `imbalance_mode=SameLevel`) quedan **cubiertas**.
- **`VolTicksPOC2`**: PASS **sin** necesitar la regla de ventana llena — con
  warmup real, las 23 zonas coinciden. La regla queda como salvaguarda, no como
  muleta.

### El único FAIL, y por qué NO se le gasta el veredicto al indicador

`aVolCellPOI2` necesita **20 sesiones limpias** de warmup y 6E 09-26 tiene
**8**: el bloque duplicado de 06-22 → 07-02 cae **justo donde iría el warmup**.

```
sesiones aptas antes de la ventana: 06-15 06-16 06-17 06-18 07-06 07-07 07-08 07-09
lookback_sessions = 20  ->  faltan 12
```

**No hay ningún rango limpio posible en este parquet** con su configuración por
defecto. Es `DATA_INTEGRITY_FAIL`, no `KERNEL_FAIL`.

> **Rango limpio que haría falta**: regenerar F2 en **2026-06-19 → 2026-07-03**.
> Con esos 11 días recuperados habría 19–20 sesiones limpias de warmup y el gate
> pasaría a ser informativo. **No se toca el parquet para conseguir un PASS.**

---

## 3. Censo de integridad

**164 días aptos de 349.** Batería de 8 chequeos; front month medido por volumen
para los 4 contratos con contrato anterior comparable (6E 09-25 queda fuera por
fail-closed: no hay contra qué medir el cruce).

### El detector tuvo un falso negativo y se corrigió

La primera versión hasheaba bloques **no solapados** en dos pasadas desfasadas.
Dio **0 duplicaciones** sobre un parquet donde hay una de 3577 ticks **demostrada**.
Causa geométrica: un bloque duplicado empieza en posición arbitraria, así que los
bloques alineados del original caen en posiciones no alineadas de la copia.

Corregido a **hash rodante en cada posición, vectorizado** — 256 pasadas numpy
sobre el array en vez de 5M iteraciones de Python. 3,8 s sobre 2M ticks.

### Duplicaciones nuevas

| parquet | pares | patrón |
|---|---:|---|
| `6E_09-26` | **40** | `2026-06-19 09:00:16 → 12:00:16` (+3 h) |
| `6E_06-26` | **36** | `2026-05-27 13:01:32 → 16:01:32` (+3 h) |

**El 19-jun no estaba entre los 9 días conocidos**: ahí la copia cayó en horario
**activo**, donde ninguna regla de sesión la delata. Es exactamente el caso que
motivaba el censo — se encontró porque se buscó, no por accidente.

Las duplicaciones ahora alimentan el veredicto diario. Antes el 19-jun caía por
`SIN_HUECO_DE_MANTENIMIENTO`, o sea **por casualidad**.

---

## 4. Atlas de excursiones nulas — **NULL / DESCRIPTIVO**

**No es un edge. No hay indicador, no hay zona, no hay señal: son anclas placebo.**

| | |
|---|---|
| anclas (N bruto) | ver `runs/atlas/atlas_null.json` |
| **N efectivo** | **163 días** |
| convergencia | alcanzada en la **ronda 4** |
| config hash | `67288bfce87cd184` |

**El atlas se reinició una vez, a propósito.** El primer tramo llegó a la ronda
188 con 333.209 anclas, pero el proceso padre acumula las filas en memoria y
crecía lineal: proyectado al hard stop original de las 07:10 daba ~2,2 M de
anclas y ~9,6 GB, o sea riesgo cierto de OOM **perdiendo la corrida entera**.
Como el criterio de convergencia —declarado antes de ejecutar— ya estaba
cumplido desde la ronda 4, seguir acumulando no compraba nada: el N efectivo son
los **días**, y ésos son 163 desde la primera ronda.

Se relanzó con hard stop a las 03:00, misma `CFG_HASH`. El checkpoint del primer
tramo quedó en `runs/atlas/checkpoint_ronda188_prereinicio.json`.

**Chequeo de reproducibilidad, gratis**: tras el reinicio, con otro sorteo de
anclas, las medianas de MFE volvieron a dar **exactamente** `[2, 4, 6, 8, 12]`.

**El N efectivo son los días, no las anclas**: las del mismo día comparten
régimen, y el bootstrap remuestrea por bloques de día. Reportar 284.363 como si
fueran independientes sería el error que el atlas existe para no cometer.

### Validación interna del nulo

Con `L=2, H=120` la tasa favorable da **0,499**. Un placebo con dirección sorteada
50/50 tiene que dar 0,5 — y lo da. Si hubiera dado 0,55 el atlas estaría roto.

### LA TABLA para decidir P/N/K

**Percentiles nulos de MFE / MAE (ticks)** — qué recorre el precio desde un
instante al azar:

| horizonte | MFE p10/25/50/75/90 | MAE p10/25/50/75/90 |
|---|---|---|
| 5 min | 0 / 1 / **2** / 5 / 8 | −8 / −5 / **−2** / −1 / 0 |
| 15 min | 0 / 2 / **4** / 8 / 14 | −14 / −8 / **−4** / −2 / 0 |
| 30 min | 1 / 2 / **6** / 12 / 20 | −20 / −12 / **−6** / −3 / −1 |
| 60 min | 1 / 4 / **8** / 17 / 28 | −28 / −17 / **−8** / −4 / −1 |
| 120 min | 2 / 5 / **12** / 23 / 39 | −39 / −23 / **−12** / −5 / −2 |

**Tasa nula de primer toque favorable** (con P = N = L, simétrico). Es el
denominador que hoy falta para leer cualquier "las zonas reaccionaron el X %":

| P=N (ticks) | 5 min | 15 min | 30 min | 60 min | 120 min |
|---|---|---|---|---|---|
| 2 | 0,460 | 0,494 | 0,498 | 0,499 | 0,499 |
| 3 | 0,387 | 0,473 | 0,492 | 0,498 | 0,498 |
| 5 | 0,241 | 0,392 | 0,451 | 0,482 | 0,497 |
| 8 | 0,108 | 0,261 | 0,356 | 0,429 | 0,475 |
| 13 | 0,030 | 0,123 | 0,214 | 0,318 | 0,405 |
| 21 | 0,007 | 0,038 | 0,092 | 0,176 | 0,277 |
| 34 | 0,001 | 0,009 | 0,026 | 0,064 | 0,133 |

**Cómo leerla.** Si un estudio dice "el 45 % de las zonas alcanzó +5 ticks antes
de −5 en 30 minutos", la tabla dice que el azar da **0,451**. No hay señal.
Para que P=N=5 a 30 min signifique algo, hay que superar holgadamente ese 45 %.

Y muestra dónde el azar es más fácil de batir: **horizontes cortos con objetivos
grandes** (L=13, H=5 → 3 %) dejan mucho margen; **objetivos chicos con horizontes
largos** (L=2, H=120 → 49,9 %) son indistinguibles de tirar una moneda.

Hay 11 estratos (franja horaria × régimen de vol rezagada) en
`runs/atlas/atlas_null.json`; 1 quedó oculto por N insuficiente.

---

## 5. Kronos — paso 2: **corrió**, y R5 no lo mató

**Target-free. No evalúa P&L, así que no cae bajo el STOP.**

| | |
|---|---|
| muestras útiles | **121** |
| lotes | 7 (**1 murió**) |
| `corr(sigma_pred, vol_rezagada)` Pearson | **0,383** |
| ídem Spearman | **0,563** |
| `corr(sigma_pred, ATR rezagado)` | **0,522** |
| umbral de refutación (pre-registrado) | 0,95 |
| **veredicto** | **SOBREVIVE R5** |

### Qué significa, y sobre todo qué NO

R5 preguntaba una sola cosa: **¿`sigma_pred` es lo mismo que una vol realizada
rezagada?** La respuesta es **no** — 0,38 de correlación lineal está muy lejos
del 0,95 que habría cerrado la línea. Kronos aporta variación propia.

**Eso no es evidencia de que sirva.** Una correlación baja con el baseline
trivial es igual de compatible con *"aporta información distinta"* que con
*"es ruido"*. R5 es un filtro de **redundancia**, no de utilidad: lo único que
se puede afirmar es que el cierre barato no se activó.

Lo que sí queda establecido: **el paso (b) tiene sentido correrlo**. Ahí es donde
se decide si esa variación propia **paga**, contra el baseline trivial y con el
criterio de lift incremental — y eso sí requiere tu OK, porque toca P&L.

### Tres desviaciones declaradas

**1. `lookback = 128` en vez de los 400 recomendados.** Forzado por un crash:
`Fatal Python error: PyEval_SaveThread` dentro de la atención del modelo. Se
descartaron por medición dos causas —la cantidad de hilos (falla igual con 1) y
la versión de torch (2.13.0 y 2.5.1 fallan idéntico)— y se acotó la que sí
manda: el **tamaño del tensor**. 400 crashea; 320 y 256 crashean con 30 caminos;
128 con 30 caminos aguanta. **Es un Kronos más chico que el que recomiendan los
autores**, y eso hay que tenerlo presente al leer el 0,383.

**2. Cada lote corre en su propio proceso.** El error es *fatal*, no una
excepción: `try/except` no lo atrapa, se lleva el proceso entero. Con hijos por
lote y escritura fila por fila, el lote que murió costó 19 muestras en vez de
las 140. **La metodología no cambió**: mismos puntos de muestreo (misma seed),
mismo baseline, mismo criterio.

**3. El contrato usado fue `6E 12-25`**, no 09-26: el runner elige el que más
días aptos tiene (52 contra 14), porque más muestras de la **misma** pregunta es
exactamente lo que el pre-registro autoriza cuando sobra tiempo.

### Sobre el aislamiento

Todo corrió en `sidecar/kronos_env`, **fuera del lock principal**. El repo
principal nunca importó torch: lee el JSON y nada más. `sidecar/` está en
`.gitignore` salvo los scripts.

---

## 6. Recursos

| | |
|---|---|
| pico de RAM | **13,22 GB** de 16 (alerta a las 01:16) |
| RAM en régimen | ~11,4 GB con atlas + Kronos corriendo |
| CPU | atlas 5 workers (BLAS/OMP=1 c/u) + Kronos 2 hilos + sistema |
| GPU | **no se usó** — como estaba pautado |
| disco | censo 2 MB · atlas ~1 MB · sidecar 2,6 GB (fuera del repo, en `.gitignore`) |

### Incidente de memoria — error operativo mío

A la 01:45 la RAM llegó a **15,95 GB de 16**: OOM inminente, que se habría
llevado el atlas *y* Kronos.

**Causa: dejé un atlas huérfano.** Relancé el proceso tres veces (00:24, 00:52,
01:26) y sólo maté el primero. El de las 00:52 siguió acumulando filas en memoria
durante una hora — llegó a **9,8 GB** — mientras yo miraba el consumo del que sí
había relanzado y me parecía normal.

Se resolvió preservando el checkpoint y matando al huérfano: la RAM pasó de
1,67 GB libres a 11,58 GB **sin perder nada** — el atlas legítimo siguió
corriendo y Kronos conservó sus 41 filas.

**Lo que lo hizo detectable**: el vigilante de RAM que dejé armado. Sin él, el
primer síntoma habría sido encontrar los tres procesos muertos a la mañana.

**Lo que lo hizo evitable y no hice**: verificar que un relanzamiento realmente
mata al anterior, en vez de asumirlo. Es la misma clase de error que el proyecto
persigue en los datos —confiar en que algo pasó en vez de comprobarlo— aplicada
a la operación.

El pico previo (13,22 GB a la 01:16) fue distinto y benigno: los gates cargando
1,9 M de ticks mientras Kronos tenía el modelo en memoria. Se resolvió solo al
terminar los gates.

**Advertencia de suspensión**: no verifiqué la política de energía de Windows.
Los procesos sobrevivieron toda la noche, así que en la práctica no hubo
suspensión — pero queda sin comprobar formalmente.

---

## 7. Decisiones pendientes — sólo las reales

1. **Regenerar F2 en 2026-06-19 → 2026-07-03.** Son 11 días con el bloque
   duplicado. Sin ellos `aVolCellPOI2` **no se puede validar** (necesita 20
   sesiones limpias de warmup, hay 8) y el universo pierde 11 días de 6E 09-26.
   Es lo único que bloquea un veredicto de kernel hoy.

2. **Portar el secuenciador causal a `VolTicksPOC2` y `aVolCellPOI2`.** Están
   registrados como **expuestos** en el contrato. Sus PASS son sobre `time:1`,
   donde el patrón no falla; en primaria de ticks estarían igual que BigTrap2.
   No los porté: un cambio por vez, atribución limpia — primero validar el
   secuenciador en BigTrap2 con los oráculos nuevos.

3. **CAMP-002 paso (b): ¿se corre?** R5 no cerró la línea (0,383 contra un umbral
   de 0,95), así que el paso siguiente tiene sentido. Pero **toca P&L** y por lo
   tanto necesita tu OK, con el baseline trivial obligatorio y el criterio de
   lift incremental. Mi lectura: el 0,383 dice que Kronos aporta variación
   propia, **no** que esa variación sirva — una correlación baja con el trivial
   es igual de compatible con "información distinta" que con "ruido".

4. **P/N/K de EXPLORE-001.** La tabla nula está lista (§4). La decisión de qué
   combinación pre-registrar es tuya; lo que aporto es el denominador.

5. **Unidad de observación de EXPLORE-001** (pendiente de la sesión anterior):
   zona cruda (476), colapsada por solape dentro de (sesión, bucket) (**360**), o
   bucket entero (204). La del medio es la que corresponde al argumento de
   pseudo-réplica.

6. **Umbral de mecha de BigTrap2** — sigue como `ESPEJADO_BIT_A_BIT` con 0,0241 %
   documentado. No requiere acción; queda listado porque es una exposición
   declarada y viva.

---

## 8. Pedidos de NT8

Lista consolidada en **`docs/parity_coverage/PEDIDOS_NT8_2026-07-27.md`**.
