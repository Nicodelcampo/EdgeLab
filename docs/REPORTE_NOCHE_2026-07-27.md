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
| rondas | 160+ |
| anclas (N bruto) | **284.363** |
| **N efectivo** | **163 días** |
| convergencia | alcanzada en la ronda 4 |
| config hash | `67288bfce87cd184` |

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

## 5. Kronos — paso 2

*(sección completada al cierre — ver §5-bis)*

---

## 6. Recursos

*(sección completada al cierre)*

---

## 7. Decisiones pendientes

*(sección completada al cierre)*

---

## 8. Pedidos de NT8

Lista consolidada en **`docs/parity_coverage/PEDIDOS_NT8_2026-07-27.md`**.
