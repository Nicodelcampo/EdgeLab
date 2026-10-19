# Spec del simulador de ejecución mínimo (CAMP-001)

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md).
> **Semántica cerrada ANTES de codear.** La implementación (turno mecánico
> posterior) debe reproducir EXACTAMENTE los golden tests de §9: son parte del
> contrato, no ejemplos ilustrativos.
>
> **Decisión de Nico:** simulador propio mínimo. `edgelab/engine.py` (legacy) NO
> se usa para evidencia formal: su contrato de señal es a nivel de tick crudo con
> entrada al *tick siguiente*, incompatible con la política G0 sellada
> (`available_at` de barra → ejecución posterior), y no tiene tests
> (`docs/edge_pipeline_inventory.md`). Los módulos estadísticos legacy
> (`mcpt`/`pbo`/`spa`) SÍ se reutilizan, previa caracterización.

## 1. Justificación económica (campo obligatorio del ritual)

Sin un simulador con fills y costos honestos no existe "expectativa NETA": el
objetivo 1 del North Star es inobservable. Este simulador es el instrumento que
convierte zonas verificadas en P&L defendible, y su conservadurismo (adverso
gana los empates) está puesto para **no descubrir edges que no existen**.

## 2. Cómo podría refutarse (campo obligatorio del ritual)

La spec es incorrecta si: (a) los golden de §9 no son reproducibles por una
implementación independiente; (b) la identidad aditiva de costos (§7) no cierra;
(c) alguna regla permite un fill imposible (ejecutar en el mismo tick de la
decisión, llenar un límite sin que el precio lo alcance, o cerrar a un precio no
observado en los datos).

## 3. Alcance y no-objetivos

- **Sí**: 1 instrumento, 1 posición simultánea, órdenes market y stop/target,
  costos desglosados, determinismo bit a bit.
- **No** (declarado): fills parciales, piramidado, órdenes limit de entrada,
  cartera multi-instrumento, margen/financiación, latencia variable.

## 4. Interfaz de entrada

```
simulate(signals, steps, *, params, scenario, instrument) -> SimResult
```

### 4.1 `signals` — señales con `available_at`

Generadas desde features del store vía `features.materialize_features`
(as-of, sin look-ahead), consumidas por `config_id`/`bar_spec`; **prohibido
importar kernels**. Toda carga de datos para esto pasa por
`edgelab.research.holdout_guard.check_holdout(..., purpose="development")`.

| Campo | Tipo | Semántica |
|---|---|---|
| `signal_id` | str | único, estable |
| `available_at` | int (ms UTC) | instante en que la señal EXISTE (cierre de la barra que la generó) |
| `dir` | int | `+1` long / `-1` short |
| `target_ticks` | int ≥ 1 | distancia al target desde el fill de entrada |
| `stop_ticks` | int ≥ 1 | distancia al stop desde el fill de entrada |
| `time_stop_ms` | int ≥ 0 | 0 = sin time stop |

**Invariante de causalidad (dura):** ninguna decisión puede usar datos con
`ts >= available_at`. Es responsabilidad del generador de señales; el simulador
lo **verifica** rechazando cualquier señal con `available_at` posterior al
último step disponible o no monótona respecto de su origen.

### 4.2 `steps` — stream de ejecución

Secuencia ordenada por `ts` (no decreciente). Cada step:

| Campo | Semántica |
|---|---|
| `ts` | ms UTC |
| `last` | último precio operado |
| `bid`, `ask` | mejor bid/ask en ese instante (`ask >= bid`) |
| `low`, `high` | rango de precio del step. **Para steps de tick: `low = high = last`** (punto). Para steps de barra: el rango real de la barra |
| `session_id` | identificador de sesión (para §6.4) |

`low`/`high` existen para que la regla de ambigüedad (§6.3) sea expresable en
ambos modos. Con steps de tick puros la ambigüedad es **inalcanzable por
construcción** (un punto no puede contener dos niveles distintos) — se declara
igual porque en modo barra sí es alcanzable y el desempate debe estar
pre-registrado, nunca improvisado.

## 5. Entrada a mercado

- La entrada ocurre en el **primer step con `ts` ESTRICTAMENTE mayor que
  `available_at`**.
- **Timestamps idénticos:** todo step con `ts == available_at` es **inelegible**
  (la información de la señal es simultánea, no anterior; permitirlo sería un
  fill en la misma barra/tick de la decisión). Con timestamps duplicados
  legítimos —el data contract F1 los declara— se descartan TODOS los que
  empatan y se toma el primero estrictamente posterior.
- Si no existe tal step (fin de datos): la señal queda **`not_executed`** con
  `reason="no_execution_step"`. **Nunca** se ejecuta hacia atrás ni en el mismo
  step.
- **Cruce de sesión:** la entrada debe ocurrir en la **misma sesión** que
  `available_at`. Si el primer step estrictamente posterior pertenece a otra
  sesión, la señal **expira**: `not_executed`, `reason="session_boundary_no_fill"`.
- **Concurrencia:** una sola posición simultánea. Una señal que llega con
  posición abierta se descarta con `reason="position_open"` (queda registrada,
  no se pierde silenciosamente).

## 6. Fills y salidas

### 6.1 Reglas de fill (uniformes y declaradas)

| Orden | Precio de fill |
|---|---|
| **Entrada market** | `book + dir * slip_entry * tick`, con `book = ask` si `dir=+1`, `bid` si `dir=-1` (cruza el spread: honesto) |
| **Target** (nivel) | `target_px - dir * slip_target * tick` |
| **Stop** (nivel) | `stop_px - dir * slip_stop * tick` |
| **Salida market** (time stop, cierre de sesión, borde de datos) | `book - dir * slip_exit * tick`, con `book = bid` si `dir=+1`, `ask` si `dir=-1` |

Niveles calculados desde el **fill de entrada** (no desde el precio de señal):
`target_px = entry_fill + dir*target_ticks*tick`,
`stop_px = entry_fill - dir*stop_ticks*tick`.

**Simplificación declarada:** las salidas por nivel no cargan spread adicional
(el nivel ES la referencia); el conservadurismo lo aporta el slippage, que los
escenarios escalan a 2 y 3 ticks. Las salidas market SÍ cruzan el spread en
ambas patas. Esta asimetría es deliberada y está contemplada en la
descomposición de costos (§7).

### 6.2 Disparo

- Long: target si `high >= target_px`; stop si `low <= stop_px`.
- Short: target si `low <= target_px`; stop si `high >= stop_px`.
- (Con steps de tick, `low = high = last`.)
- La barra/tick **de la entrada** también puede disparar salidas: la posición ya
  existe desde el fill. No hay "gracia" de un step.

### 6.3 Empate stop/target en el mismo step — **GANA EL ADVERSO**

Si en un mismo step ambos niveles resultan alcanzables y el orden intra-step **no
es resoluble** con la información disponible, se ejecuta el **STOP**
(`reason="stop_ambiguous"`). Regla conservadora pre-declarada: prohibido asumir
el orden favorable. Nunca se resuelve por probabilidad ni por interpolación.

### 6.4 Salidas por tiempo, sesión y borde de datos

- **Time stop**: si `time_stop_ms > 0`, se cierra a market en el **primer step con
  `ts >= entry_ts + time_stop_ms`** (`reason="time_stop"`). Si en ese mismo step
  también se dispara stop o target, **prevalece la salida por nivel** (ocurre
  dentro del step, antes del vencimiento por definición del disparo), y si esa
  salida por nivel es ambigua rige §6.3.
- **Cierre forzado de sesión**: parámetro `close_at_session_end`. Si está activo,
  toda posición abierta se cierra a market en el **último step de su sesión**
  (`reason="session_close"`).
- **Borde de datos**: una posición todavía abierta cuando se agotan los steps se
  cierra a market en el **último step disponible** (`reason="data_edge"`).
  **Nunca** se descarta (sesgaría al eliminar trades vivos) ni se deja abierta
  (P&L irrealizable). Los trades cerrados por `data_edge` se **cuentan y
  reportan por separado** para poder medir su peso en el resultado.

## 7. Costos — desglosados, sin doble conteo

Fuente única de verdad de los escenarios: `edge_validation_contract.md` §G3. El
simulador **no duplica números**: recibe el escenario y lee de ahí
`slippage_entry/target/stop/exit` y los componentes de comisión.

| Escenario | Slippage (ticks/pata) | Comisión |
|---|---|---|
| `ideal` (solo diagnóstico) | 0 | 0 |
| `base` | 1 (stops 1) | plena |
| `adverso` | 2 (stops 2) | plena |
| `severo` | 3 (stops 3) | plena |

Comisión = comisión broker + exchange/clearing + NFA, **por pata**, en USD
(pre-registrada en `CAMP-001` §7, pendiente de confirmar con estados de cuenta
reales).

**Descomposición aditiva EXACTA por trade** (verificada algebraicamente):

```
neto_ticks = bruto_ticks − spread_ticks − slippage_ticks
neto_usd   = neto_ticks * tick_value − comision_usd
```

donde, con `entry_mid = (bid+ask)/2` del step de entrada:

- `bruto_ticks` = P&L mid→referencia de salida, **sin** spread ni slippage:
  - salida por nivel: `dir * (nivel_salida − entry_mid) / tick`
  - salida market: `dir * (exit_mid − entry_mid) / tick`
- `spread_ticks` = `dir*(entry_book − entry_mid)/tick` **+**, solo en salidas
  market, `dir*(exit_mid − exit_book)/tick`
- `slippage_ticks` = `slip_entrada + slip_salida`
- `comision_usd` = 2 × comisión por pata

**Prohibido el doble conteo:** `spread` y `slippage` NO se restan otra vez del
P&L calculado con precios de fill — son la *descomposición* de la diferencia
entre el P&L bruto (mid) y el P&L de fills. La implementación debe verificar en
cada trade que `neto_ticks == dir*(exit_fill − entry_fill)/tick` (identidad
exacta, tolerancia 0 en aritmética de ticks enteros/medios).

## 8. Salida (`SimResult`)

- `trades`: lista reproducible, una fila por trade:
  `signal_id, dir, entry_ts, entry_px, exit_ts, exit_px, exit_reason,
   bruto_ticks, spread_ticks, slippage_ticks, comision_usd, neto_ticks, neto_usd,
   mae_ticks, mfe_ticks, bars_held`.
  `exit_reason` ∈ `{target, stop, stop_ambiguous, time_stop, session_close, data_edge}`.
- `rejected`: señales no ejecutadas con su motivo
  (`no_execution_step`, `session_boundary_no_fill`, `position_open`).
  **Se reportan siempre**: una campaña con muchos rechazos es información, no ruido.
- `summary`: nº de trades, expectancy bruta y neta (ticks y USD), suma por
  componente de costo, y conteo por `exit_reason`.
- `digest`: sha256 sobre la lista de trades serializada canónicamente
  (`identity.canonical_json`, mismas primitivas que el store). **Mismo input ⇒
  mismo digest**, entre corridas y entre máquinas.

## 9. Golden tests — números exactos (parte del contrato)

Instrumento **6E**: `tick = 0.00005`, `tick_value = $6.25`,
comisión `$2.20`/pata (RT `$4.40`). Escenario **`base`** (slippage 1 tick/pata).
Precios expresados en **ticks enteros** (precio real = ticks × 0.00005).
Todos los steps son de tick (`low = high = last`) salvo donde se indique.

Identidad aditiva verificada en los 7 casos.

### G1 — entrada + TARGET
Steps: `s0(ts=1000,last=23000,bid=23000,ask=23001)`,
`s1(1100, 23000, 23000, 23001)`, `s2(1200, 23010, 23009, 23010)`,
`s3(1300, 23013, 23012, 23013)`.
Señal: `dir=+1, available_at=1000, target_ticks=10, stop_ticks=5`.

| Resultado | Valor |
|---|---|
| step de entrada | `s1` (primero con `ts > 1000`) |
| `entry_fill` | `23001 (ask) + 1 = 23002` |
| niveles | target `23012`, stop `22997` |
| disparo | `s3` (`last 23013 >= 23012`) |
| `exit_fill` | `23012 − 1 = 23011` · `exit_reason=target` |
| bruto | `11.5` ticks = `$71.875` |
| spread / slippage / comisión | `0.5 t` (`$3.125`) / `2.0 t` (`$12.50`) / `$4.40` |
| **neto** | **`9.0` ticks = `$56.25` bruto de comisión ⇒ `$51.85`** |

### G2 — entrada + STOP
Steps: `s0(1000,23000,23000,23001)`, `s1(1100,23000,23000,23001)`,
`s2(1200,22996,22996,22997)`. Señal igual a G1.

| Resultado | Valor |
|---|---|
| `entry_fill` | `23002` · stop `22997` |
| disparo | `s2` (`last 22996 <= 22997`) |
| `exit_fill` | `22997 − 1 = 22996` · `exit_reason=stop` |
| bruto / spread / slippage | `−3.5 t` (`−$21.875`) / `0.5 t` / `2.0 t` |
| **neto** | **`−6.0` ticks = `−$37.50` ⇒ `−$41.90`** |

### G3 — stop y target alcanzables en el MISMO step ⇒ **gana el adverso**
Steps: `s0(1000,23000,23000,23001)`, `s1(1100,23000,23000,23001)`,
`s2` = **step de barra**: `ts=1200, low=22990, high=23020, last=23015,
bid=23014, ask=23015`. Señal igual a G1.

`target=23012 ∈ [22990,23020]` **y** `stop=22997 ∈ [22990,23020]` ⇒ ambiguo.

| Resultado | Valor |
|---|---|
| resolución | **STOP** · `exit_reason=stop_ambiguous` |
| `exit_fill` | `22997 − 1 = 22996` |
| **neto** | **`−6.0` ticks ⇒ `−$41.90`** (idéntico a G2: lo que se prueba es la RESOLUCIÓN) |

### G4 — TIME STOP
Steps: `s0(1000,23000,23000,23001)`, `s1(1100,23000,23000,23001)`,
`s2(1200,23005,23004,23005)`, `s3(1300,23006,23005,23006)`.
Señal: `dir=+1, available_at=1000, target_ticks=10, stop_ticks=5,
time_stop_ms=200`. Deadline = `entry_ts(1100) + 200 = 1300`.

| Resultado | Valor |
|---|---|
| salida | `s3` (`ts 1300 >= 1300`), market · `exit_reason=time_stop` |
| `exit_fill` | `23005 (bid) − 1 = 23004` |
| bruto (mid→mid) | `23005.5 − 23000.5 = 5.0 t` = `$31.25` |
| spread (2 patas) / slippage | `1.0 t` (`$6.25`) / `2.0 t` (`$12.50`) |
| **neto** | **`2.0` ticks = `$12.50` ⇒ `$8.10`** |

### G5 — señal en el ÚLTIMO step ⇒ NO se ejecuta
Steps: `s0(1000,…)`, `s1(1100,…)` (último). Señal con `available_at = 1100`.
No existe step con `ts > 1100` ⇒ **`not_executed`**,
`reason="no_execution_step"`, **cero trades**, P&L `0`.
Fija la prohibición de fill en el mismo step de la decisión.

### G6 — sesión sin steps posteriores ⇒ la señal EXPIRA
Steps: `s0(ts=1000, session_id=A)`, `s1(ts=1100, session_id=A)`,
`s2(ts=9000, session_id=B)`. Señal con `available_at = 1100` (sesión A).
El primer step estrictamente posterior (`s2`) pertenece a **otra sesión** ⇒
**`not_executed`**, `reason="session_boundary_no_fill"`, cero trades.
Prohíbe ejecutar cruzando el cierre de sesión (fill imposible en la práctica).

### G7 — posición abierta al BORDE DE LOS DATOS ⇒ cierre forzado
Steps: `s0(1000,23000,23000,23001)`, `s1(1100,23000,23000,23001)`,
`s2(1200,23004,23003,23004)` (último). Señal igual a G1; ni stop ni target ni
time stop se alcanzan.

| Resultado | Valor |
|---|---|
| salida | `s2`, market · `exit_reason=data_edge` |
| `exit_fill` | `23003 (bid) − 1 = 23002` |
| bruto / spread / slippage | `3.0 t` (`$18.75`) / `1.0 t` / `2.0 t` |
| **neto** | **`0.0` ticks = `$0.00` ⇒ `−$4.40`** (trade plano en bruto que pierde exactamente la comisión) |

## 10. Determinismo

Sin `random`, sin `datetime.now()` en la ruta de cálculo, sin dependencia del
orden de iteración de diccionarios. Misma entrada ⇒ mismo `digest` (§8). El
digest entra al reporte reproducible por `campaign_id`/`strategy_id`.

## 11. Preguntas abiertas para el sellado de CAMP-001

1. **`close_at_session_end`**: el simulador lo soporta como parámetro; CAMP-001
   debe fijar su valor al sellar (afecta el horizonte real de las 4 familias y,
   por lo tanto, los resultados). No se asume un default silencioso.
2. Confirmar los componentes de comisión con estados de cuenta reales
   (`CAMP-001` §10, dato faltante #1).
