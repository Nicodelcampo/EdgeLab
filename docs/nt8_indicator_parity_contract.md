# Contrato de paridad NT8 ↔ Python — primer oráculo real: Gaps2

> Este documento sirve al referente rector: ver [`NORTH_STAR.md`](NORTH_STAR.md).

> Objetivo: producir el `EventLogPath` de **Gaps2** en NT8 sobre un rango
> idéntico al que corre el kernel Python, y pasar el gate **P2**:
> PASS = cero zonas huérfanas y cero discrepancias geométricas (en ticks).

## 1. Selección pre-registrada

| Ítem | Valor |
|---|---|
| Indicador | Gaps2 v2.0 (el MISMO .cs que exporta EventLogPath) |
| Instrumento/contrato | **6E 06-26** (contrato más denso: 5.56M ticks) |
| Dataset Python | `data/nt8/6E/6E_06-26_ticks.parquet` (F2, UTC verificado) |
| Rango UTC (2 sesiones CME completas consecutivas) | **2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z** (sesiones del mié 6 y jue 7 de mayo; CDT: abren 17:00 CT, cierran 16:00 CT) |
| Timeframe primario | **1 minuto** |
| Parámetros | defaults del kernel (tabla abajo) — NO cambiar ninguno sin re-registrar |
| Timezone del chart NT8 | la que tenga tu UI (ART); se pasa a la CLI como `--chart-tz America/Argentina/Buenos_Aires`. El matching de Gaps2 usa `unix_ms` (absoluto), así que la tz del chart solo afecta la columna legible `ts` |

Parámetros default (deben coincidir 1:1 con la UI del indicador en NT8):
`min_gap_ticks=5 · export_floor_ticks=2 · reopen_pause_minutes=60 ·
reopen_warmup_minutes=30 · atr_period=14 · vol_baseline_ticks=2000 ·
min_vol_baseline_samples=500 · partial_fill_pct=50 · reversal_confirm_ticks=2 ·
max_age_bars=2000 · max_logged_touches=20`

### Desviación del pre-registro — primer oráculo real ✅ PASS

El primer oráculo real NO fue el 06-26 de mayo de arriba, sino **6E 09-26**
(el contrato que estaba cargado con tick data completa en la instalación):

| Ítem | Valor |
|---|---|
| Oráculo | `oracles/Gaps2_6E_0926.csv` (export real, 1776 zonas) |
| Contrato · barras | **6E 09-26** · **1 minuto** |
| Ventana comparada (UTC) | **2026-07-13T22:00:00 → 2026-07-16T21:00:00** (borde de sesión CME) |
| Params | defaults salvo **`min_gap_ticks=2`** (declarados por la línea `# params` del CSV) |
| Dataset Python | `data/nt8/6E/6E_09-26_ticks.parquet` (cubre 2026-06-08 → 2026-07-21) |
| **Gate P2** | **PASS** — 1316/1316 zonas, 0 `MISSING_*`, 0 `GEOMETRY_DIFF`; 15 `MATURITY_TAIL` (cola de ventana, lifecycle no comparable) |

Motivo de la desviación: 6E 06-26 no tenía tick data cargada en esta
instalación; 6E 09-26 sí (mismo feed). `min_gap_ticks=2` en vez de 5 es solo el
umbral de **display** (para ver zonas en el chart); no afecta el export ni la
paridad (ver `nt8_bridge.md` "Dibujo ≠ export"). Evidencia completa (oracle
sha256, config_id, ventana, regla) en el `parity.json` de la partición del store.

## 2. Pasos en NT8 (tu parte)

1. Chart nuevo: **6E 06-26** (contrato individual, NO continuo ni rollover),
   **1 minuto**, con datos históricos de tick completos para el rango
   (el mismo feed del que salieron los `.Last.txt`).
2. Rango del chart: que cubra **desde antes del 2026-05-05 17:00 CT hasta
   después del 2026-05-07 16:00 CT** (dejá margen de 1 día a cada lado; el
   kernel Python recorta exacto por UTC, NT8 puede tener warmup extra — los
   eventos fuera de rango se excluyen del diff).
3. Aplicar **Gaps2 v2.0** con TODOS los parámetros en default (tabla arriba) y
   `EventLogPath = C:\ProyectosQuant\EdgeLab\oracles\Gaps2_6E_06-26_may.csv`
   (crear la carpeta `oracles\` si no existe).
4. Dejar que el indicador procese todo el histórico del chart (recalcular si
   hace falta: F5). Cerrar el chart o refrescar para que el log se flushee.
5. Verificar que el CSV tiene el header `event_seq,event_type,ts,unix_ms,...`
   y me avisás.

## 3. Corrida Python (mi parte, cuando exista el CSV)

```bash
.venv\Scripts\python tools\run_nt8_bridge.py ^
  --data data\nt8\6E\6E_06-26_ticks.parquet --contract "6E 06-26" ^
  --start-utc 2026-05-05T22:00:00 --end-utc 2026-05-07T21:00:00 ^
  --bars time:1 --indicator Gaps2 ^
  --chart-tz America/Argentina/Buenos_Aires ^
  --oracle Gaps2=oracles\Gaps2_6E_06-26_may.csv ^
  --out runs\nt8_bridge\parity_gaps2_0626_may
```

## 4. Gate P2 (pre-registrado)

- **PASS**: 0 `MISSING_IN_*`, 0 `GEOMETRY_DIFF` (geometría exacta en ticks).
- **WARN**: solo `TIMESTAMP_DIFF` ≤ 60 s, `STATE_ORDER_DIFF`, `FEATURE_DIFF`
  (touches) o `CALIBRATION_DIFF` declarado → se revisan una por una en el visor
  antes de promover.
- **FAIL**: zonas faltantes o geometría distinta → el kernel NO entra a
  vectorbt; se depura con el visor (modo "solo huérfanas") y se re-corre.

Exclusiones declaradas del diff (documentadas en `nt8_bridge.md`):
`SESSION_END` si el chart NT8 sigue vivo (no hubo OnTermination), y eventos
NT8 anteriores al inicio del rango Python (warmup del chart).

### Convención de ventana semiabierta (pre-declarada, regla de MEDICIÓN)

La ventana de comparación es **`[W0, W1)`**: incluye `W0`, **excluye `W1`**. Se
aplica igual a los eventos del oráculo y a los del kernel.

Consecuencia declarada de antemano: un evento con `ts == W1` **exacto** queda
fuera del lado que se filtra por ventana y puede aparecer como
`MISSING_IN_NT8`/`MISSING_IN_PYTHON` de borde. **No es una discrepancia de
kernel** y no se cuenta como causa raíz pendiente; se identifica verificando que
el otro lado sí generó el evento fuera de la ventana. Caso observado: BigTrap2
O1, zona `py 4033_B` con `ts == W1`, que NT8 sí generó (su barra 8081).

Esta convención se declara **antes** de mirar resultados justamente para que un
diff de borde no pueda usarse después como excusa para mover `W1`.

#### Aplicación SIMÉTRICA de la ventana (decisión de Nico, 2026-07-26)

**Regla mecánica, sin listas manuales:**

> Una zona queda **fuera del gate** —de **los dos lados**— si su `created_ms`
> cae fuera de `[W0, W1)`. Formalmente: se excluye si `created_ms < W0` o
> `created_ms >= W1`.

Es la forma degenerada de la frontera de madurez: aquélla excluye zonas que no
pueden **completar** su ciclo de vida dentro de la ventana; ésta excluye las que
no pueden ni **empezarlo** —una zona creada exactamente en `W1` tiene cero barras
de vida observable adentro—.

Tres condiciones de aplicación, exigidas al autorizarla:

1. **Mecánica**: es el predicado de arriba, evaluado sobre `created_ms`. No hay
   lista de filas ni excepciones nombradas.
2. **Simétrica**: se aplica al oráculo NT8 **y** a las zonas del kernel. Hasta el
   2026-07-26 se aplicaba sólo al oráculo, y esa asimetría era la que producía
   el `MISSING_IN_NT8` de borde.
3. **Reportada siempre**: el runner imprime cuántas filas excluyó de cada lado y
   **cuáles** (por `id`). Una exclusión silenciosa sería indistinguible de un
   diff que no existe.

**Prohibido** usar esta regla para excluir cualquier otra cosa. Si algo fuera del
borde no coincide, el gate da **FAIL** y se reporta.

##### Resultado de aplicarla a BigTrap2 `time:1` v2.1

```
[oráculo BigTrap2] 225/825 zonas NT8 en ventana
[kernel  BigTrap2] 225/226 zonas en ventana; excluidas por borde: 4033_B
MATCHED 225 · MATURITY_TAIL 6 · gate PASS
tol_geom_ticks=0 · tol_created_ms=60000  (SIN modificar)
```

**Gate PASS con 0 diffs**, una sola fila excluida y nombrada, y **ninguna otra
tolerancia tocada**. Junto con `PRED-001` —que predijo las 9 magnitudes exactas
antes de que el oráculo existiera— BigTrap2 en `time:1` queda con paridad
**demostrada**, no sólo aprobada.

### Semántica del EMPATE precio-vs-close (pre-declarada, regla SEMÁNTICA)

Cuando un nivel de precio (fila de footprint, celda, POC) **coincide exactamente**
con el precio de referencia contra el que se lo compara (típicamente el `close`
de la barra), **el empate NO cuenta para ningún lado**.

Fundamento, sellado por Nico el 2026-07-24:

1. **Económico**: no hay volumen atrapado "más allá" del close si el volumen
   está *en* el close. Una fila en el close no es agresión que quedó por encima
   ni por debajo.
2. **Lógico (decisivo)**: si el empate contara, habría que decidir *de qué lado*.
   Con `>=` para buyers y `<=` para sellers la misma fila sería simultáneamente
   `trapped_buyers` y `trapped_sellers` — incoherente. Y asignarla a un solo lado
   por convención reintroduce exactamente el **sesgo direccional** que se quiere
   eliminar. **Excluir el empate es la única regla simétrica y bien definida.**

Refuerzo empírico: las 32 zonas espurias que produjo el empate en BigTrap2 eran
**todas `n_rows=1`**, es decir zonas nacidas íntegramente de la fila del empate
— económicamente vacías.

**Implementación obligatoria**: la comparación se hace en **índices enteros de
tick** (o medios ticks si el centro de fila puede caer en `x.5`), nunca entre
`double`. Ver la lección de §5.

### Semántica del RETROCESO y la ALTURA (pre-declarada) — HFTZones2

Misma familia, mismo criterio. En HFTZones2 la racha se corta cuando el
retroceso **supera** el permitido:

```
allowed  = max(retro_floor_ticks, retro_pct_height/100 × altura)
corta si  retro > allowed          ← estricto: el EMPATE no corta
```

- **Altura y retroceso se miden en índices ENTEROS de tick**, vía
  `PriceToTick` en el `.cs` y `common.snap_to_tick` en el kernel — el mismo
  `Math.Round(precio/tick, AwayFromZero)` de los dos lados.
- **El empate `retro == allowed` NO corta la racha.** Es el mismo criterio que
  el empate fila-vs-close: el operador estricto es el que ya estaba declarado;
  lo que se corrige es que antes lo decidía el punto flotante, no la regla.
- `FinalizeStreak` usa **la misma altura entera** que la detección, para que
  detección y clasificación (`is_sweep`) no puedan discrepar.

Por qué importa, medido: `(swh − price)/tick_size` **nunca** da el entero exacto
en el rango del 6E (falla en el 100 % de los pares 20000–25000, con desvío en
**ambas** direcciones). Con `allowed` entero, eso hacía que Python cortara donde
el `.cs` v2.1 no corta en el **5,0 %** de los niveles de precio en la rama del
piso y en el **22 %** en la rama porcentual con altura par.

**Regla de cambio acoplado:** este par (`HFTZones2.cs` ↔ `hftzones2.py`) se
modifica **junto, en el mismo commit**. Tocar un solo lado rompe la paridad de
forma garantizada, no eventual.

### Regla de VENTANA LLENA para kernels con historia rodante (Nico, 2026-07-26)

**Aprobada como enmienda al pre-registro de VolTicksPOC2.**

> Para todo kernel cuya decisión dependa de una ventana **rodante** de historia,
> la región comparada exige que **los dos lados tengan la ventana completa**. Una
> zona cuya ventana no esté llena en alguno de los dos lados **no entra a la
> comparación**, y la exclusión se **reporta** — cuántas filas y cuáles.

**El problema que resuelve.** `VolTicksPOC2` decide por percentil empírico sobre
una ventana rodante de `ratio_window_bars` (default 2000) ratios, con
`min_ratio_samples` (default 500) de piso. El percentil de la barra *b* depende
de las 2000 barras previas. NT8 arranca esa ventana en la primera barra que
**cargó el chart**; Python la arranca en la primera barra del **parquet**. Si los
dos orígenes no coinciden, las dos ventanas contienen conjuntos de ratios
distintos, y una barra cerca del umbral puede caer de lados opuestos **sin que
haya ninguna discrepancia de kernel**.

Es el mismo error de razonamiento que la ventana asimétrica de §4: se estaba
midiendo el artefacto de medición, no el kernel.

**Por qué no alcanza con la frontera de madurez.** Esa regla pide que la zona
esté madura en el eje de *tiempo*; ésta pide que lo esté en el eje de *historia*,
que es otro. Un kernel puede tener una zona perfectamente madura en tiempo cuya
ventana de ratios todavía está a medio llenar.

**Cómo se aplica**, en este orden:

1. Se determina `b0` = la primera barra en que **ambos** lados tienen
   `>= ratio_window_bars` ratios acumulados (no `min_ratio_samples`: ése es el
   piso para *emitir*, no para que la ventana esté llena).
2. La región comparada arranca en `b0`, y se aplica **idénticamente** a los dos
   lados — igual que la ventana semiabierta.
3. Las zonas excluidas se reportan siempre. Silenciarlas convertiría la regla en
   una tolerancia encubierta, que es justo lo que no se hace acá.

**Alcance.** Hoy aplica a `VolTicksPOC2` (ventana de ratios) y a `aVolCellPOI2`
(`lookback_sessions=20`, ventana rodante de sesiones). `HFTZones2` **no** la
necesita: congela su calibración por sesión contra la sesión anterior completa,
así que su dependencia de historia está acotada a una sesión y ya la cubre el
preflight de calendario.

**Lo que la regla NO autoriza**: no amplía ninguna tolerancia numérica ni relaja
ningún gate. Recorta la **región** comparada por una razón declarada *antes* de
mirar los diffs, y sobre esa región el gate sigue exigiendo 0 diffs.

### Preflight de calendario de sesiones (Nico, 2026-07-26)

Para todo kernel dependiente de sesiones, **antes** de comparar zonas se comparan
las fronteras de sesión de los dos lados. Si difieren, **se aborta con
diagnóstico** (qué sesión, qué fecha) y no se comparan zonas: un calendario
corrido produce diffs de zona que *parecen* diffs de geometría.

Implementación en `edgelab/bridge/session_preflight.py`, conectado a
`tools/run_nt8_bridge.py`. Aplica a `aVolCellPOI2`, `HFTZones2` y a todo
indicador futuro basado en sesiones.

**Lo que se midió al implementarlo** — contra el oráculo real
`HFTZones2_adaptive_6E_0926_v22.csv`, las **7 fronteras de NT8 coinciden
exactamente** con las de `sessions.py` (17:00 CT, DST-aware). El calendario **no**
está desalineado, y el rango 2026-06-08 → 2026-07-21 **no contiene ningún feriado
con cierre completo** (Juneteenth y el 3 de julio operaron con cierre temprano a
las 15:00 CT, verificado sobre los ticks del parquet).

Lo que sí difiere es el **origen del contador**: NT8 numera desde la primera
barra que cargó el chart, Python desde el inicio del parquet — en 6E 09-26 da un
offset constante de **4** (NT8 arranca en 2026-06-12, el parquet en 2026-06-08).
Ése, y no una deriva de calendario, es el origen real del FAIL de `aVolCellPOI2`.

> **Regla derivada**: un `session_index` de NT8 **no es** un índice de Python.
> Se traduce por **trade-date**, nunca por ordinal. El offset se **declara** en el
> reporte, no se absorbe: si cambia entre corridas es que el chart cargó otro
> rango, y eso invalida la comparación igual que un desalineamiento real.

Timezone del chart confirmada por la misma vía: los `ts` del `.cs` son
`America/Argentina/Buenos_Aires` (19:00 local = 17:00 CT = 22:00 UTC).

### Regla de frontera de madurez (pre-declarada)

NT8 exporta más rango que la ventana Python (warmup a ambos lados). Las zonas
creadas a **menos de `max_age_bars` del cierre de la ventana** no pueden
completar su ciclo de vida dentro de la ventana común Python∩NT8: Python las
corta (SESSION_END) y NT8, que sigue procesando, las expira/invalida/toca más.
Regla del matcher (`parity.match_zones(maturity_frontier_ms=...)`):

- **Geometría (top/bottom en ticks) + timestamp de creación**: se comparan para
  el **100%** de las zonas, maduras e inmaduras.
- **Estado final + touches (lifecycle)**: se comparan **solo para zonas maduras**
  (`created_ms <= cierre_barra[n-1-max_age]`). Para las inmaduras se registra
  `MATURITY_TAIL` (informativo, no WARN/FAIL) con lo que se suprimió.

**No es ampliar tolerancia**: es una regla de ventana con principio (la simétrica
del warmup inicial). Una zona **madura** con `STATE_ORDER_DIFF`/`FEATURE_DIFF`
sigue siendo WARN/FAIL — hay un test adversarial que lo fija.

**Prohibido:** generar un CSV NT8 ficticio o editado. El oráculo es el export
real del indicador corriendo en NT8. Sin ese archivo, ningún kernel se declara
"paridad real confirmada".

**Versión de los `.cs`:** los oráculos válidos deben generarse con la versión
**190ed59 o posterior** de los `.cs` (en particular `aVolCellPOI2.cs` reescrito a
subserie 1-tick, sin barras Volumetric nativas de OrderFlow — un solo motor de
footprint, idéntico al port Python). Cualquier export de aVolCellPOI2 generado
con la versión Volumetric anterior **NO es válido** como oráculo y debe
regenerarse. Registrar en cada oráculo la rev de los `.cs` usada.

## 5. Protocolo para los kernels siguientes (F5+ — integrados)

El mismo contrato aplica a VolTicksPOC2, BigTrap2, HFTZones2 y aVolCellPOI2 (los
4 ya integrados: kernel + smoke + P1A real + soporte CLI/visor + parser de
oráculo). Un oráculo por indicador y por configuración paramétrica que se quiera
promover. Requisitos específicos de rango/historia por kernel:

| Kernel | Barras | Requisito de rango / historia para el oráculo NT8 |
|---|---|---|
| **VolTicksPOC2** | time:N | ≥ `avg_period` barras para baseline y ≥ `min_ratio_samples` ratios antes de detectar; export continuo `OBS` desde `export_floor_percentile`. |
| **BigTrap2** | **tick:N** (o time) | el `--bars tick:N` debe coincidir con la resolución del chart NT8; export **pipe** (`seq|iso|type|payload`). Cada resolución es un oráculo distinto. Barra 0 descartada. |
| **HFTZones2** | time:N (tick-driven) | el rango DEBE arrancar en **borde de sesión** con **≥1 sesión completa previa** para tener calibración congelada; si no, la 1ª sesión sale `CALIBRATION_PENDING` y no crea zonas. Feriados → `CALIBRATION_DIFF` (WARN). |
| **aVolCellPOI2** | time:N | pre-registrar que el chart NT8 tenga **≥ `lookback_sessions` + `min_sessions` sesiones** cargadas (con defaults: ≥ 35 sesiones ≈ 7 semanas) antes del rango a comparar; sobre historia pobre el kernel produce 0 zonas (correcto). |

**Regla común:** el rango Python (`--start-utc/--end-utc`), los parámetros, la
timezone del chart (`--chart-tz`) y la resolución de barras deben coincidir 1:1
con el indicador corriendo en NT8. Sin el CSV real, ningún kernel se declara
"paridad real confirmada" (§4).

### REGLA DE DISEÑO (sellada por Nico, 2026-07-26)

> **Ningún umbral de PRECIO DE GRILLA se compara en `double`: todo umbral de
> precio de grilla se compara en índices ENTEROS de tick.**
>
> **Los umbrales intrínsecamente fraccionarios** —los que por definición no caen
> en la grilla, como un porcentaje de rango— **no se convierten**: se espejan
> **bit a bit** (misma secuencia de operaciones en los dos lados) y su exposición
> residual se **mide y se documenta**.

*(La segunda mitad es la Decisión A de Nico, 2026-07-26. Ver §"Umbrales
fraccionarios" más abajo.)*

Deja de ser una lección y pasa a ser una regla que se **verifica sola**. Dejó de
tratarse como bug recurrente porque ya lleva **cinco apariciones**, cada una en
una expresión distinta, y **las cinco** se encontraron gastando un oráculo o
midiendo a mano. Buscarlas leyendo código falló explícitamente una vez:
`AUDIT-001` clasificó como riesgo NULO justamente la comparación que después
resultó ser la causa raíz de los 82 `FEATURE_DIFF` de HFTZones2.

**Cómo se hace cumplir**

| capa | herramienta | qué hace |
|---|---|---|
| estática | `tools/ulp_sweep.py --baseline` | falla ante cualquier expresión de comparación de precios que **nunca se haya clasificado** |
| medición | `tools/ulp_exposure.py` | cuenta, sobre el rango real del instrumento, cuántas decisiones **cambian de lado** entre la representación del feed y la reconstruida |
| suite | `tests/bridge/test_ulp_sweep.py` | 12 tests, incluido uno que **inyecta la regresión** y exige que el barrido la marque |
| pasada única | `tools/check_nt8_cs.py --ulp nt8/*.cs` | estructura + barrido en un solo comando |

El barrido **no decide**: marca candidatos. Un candidato no es un bug — los
bordes a medio tick son inmunes por construcción. Lo que la regla prohíbe es
dejar un candidato **sin medir**. Cada uno de los 49 actuales está sellado con
veredicto y evidencia en `tools/ulp_sweep_baseline.json`; los veredictos
admitidos son `INMUNE_MONOTONO`, `INMUNE_MEDIOTICK`, `CORREGIDO`,
`EXPUESTO_PENDIENTE`, `FUERA_DE_ALCANCE` y `NO_ES_PRECIO`.

**El único argumento válido de inmunidad "porque los dos son precios"**:
`feed()` y `ticks × tick_size` son ambas estrictamente monótonas en el índice de
tick, así que preservan orden **y empates** — pero sólo si los dos operandos
llegan a la comparación **sin aritmética intermedia**. En cuanto aparece un
`± N * TickSize`, un `* pct` o una división, el argumento se cae. Ésa es
exactamente la distinción que AUDIT-001 no hizo.

#### Umbrales fraccionarios — la excepción, y por qué no es una grieta

**Decisión A de Nico, 2026-07-26.** Un umbral como el filtro de mecha de
BigTrap2 —`hi − range × 30 %`— **no es un precio de grilla**. Convertirlo a
enteros exigiría elegir una semántica de redondeo, y esa elección **cambia qué
filas entran al cálculo**: sería redefinir el indicador, no corregirlo. Peor:
invalidaría una paridad ya ganada (BigTrap2 `time:1`, PASS con 0 diffs) a cambio
de un 0,0241 % bidireccional.

El tratamiento es otro, y es exigente:

1. **Espejado bit a bit**: los dos lados computan la **misma secuencia de
   operaciones**, término a término. No basta con que el álgebra coincida —
   `hi − (hi−lo)·k` y `hi·(1−k) + lo·k` son idénticos en álgebra y **distintos**
   en `double`. Un refactor que "simplifica" la expresión rompe el espejado sin
   cambiar ningún resultado visible en un test de valores redondos.
2. **La exposición se mide**, y la medición tiene que separar sus dos fuentes:

   | fuente | contribución medida |
   |---|---|
   | la **aritmética** (¿los dos lados computan igual?) | **0,000000 %** — 0 flips de 2.952.000 |
   | la **representación de entrada** (feed `double` vs `ticks × tick_size`) | **0,024051 %** — 710 flips |

   Ésa es la verificación que convierte "el espejo es exacto" en algo
   falsable. Con `hi`/`lo` en la misma representación de los dos lados la
   exposición es **exactamente cero**; todo el residual es la representación de
   entrada, que es irreducible sin cambiar la semántica.
3. **Se documenta como caveat**, no se esconde: `AUDIT-003` y
   `docs/parity_coverage/BigTrap2.md`.

El veredicto `ESPEJADO_BIT_A_BIT` del triaje **exige** el número medido en su
evidencia. Sin él, la clase sería una puerta de escape para dejar cualquier cosa
en `double` diciendo "es fraccionario". Con él, es una afirmación verificada.

Fijado en `tests/bridge/test_espejo_bit_a_bit.py`, que incluye un test que
demuestra que un reordenamiento algebraicamente válido **sí** rompe el espejado
— o sea, que la exigencia textual no es paranoia.

Resultados del barrido completo en `docs/audits/AUDIT-003_barrido_ulp.md`.

### VENTANA DE DATOS ≠ VENTANA DE COMPARACIÓN (2026-07-27)

> **La ventana de DATOS es una propiedad del ORÁCULO: tiene que espejar lo que
> cargó el chart que lo generó. La ventana de COMPARACIÓN es otra cosa.**

Hasta ahora `run_nt8_bridge.py` recortaba los **ticks** a la ventana de
comparación, así que los kernels corrían **sin warmup**. El efecto era brutal y
se leía como culpa del kernel:

| indicador | sin warmup | **con warmup** |
|---|---|---|
| `aVolCellPOI2` | **0 zonas** (lookback de 10–20 sesiones nunca se llena) | 140 |
| `HFTZones2` v2.3 | 947 de 1599 | ✅ **1599 — PASS** |
| `VolTicksPOC2` | 21 de 23 | ✅ **23 — PASS** |

Dos gates dieron vuelta a PASS sin tocar una línea de kernel. **El defecto era del
arnés.**

**Pero un warmup común tampoco sirve**, y eso se vio en vivo con `Gaps2`: su
oráculo se generó con el chart arrancando **en** la ventana, y darle un mes de
historia hizo que Python dejara de reproducir las 8 primeras zonas — las que NT8
crea en su primera barra (tres de ellas con geometría **y timestamp idénticos
entre sí**, o sea NT8 duplicando en el arranque).

**La regla**: cada oráculo declara su ventana de datos, y el arnés la respeta.
`--data-start-utc` / `--data-end-utc`, separados de `--start-utc` / `--end-utc`.

Corolario para el pre-registro: **el rango de carga del chart es parte de la
identidad del oráculo** y debe quedar escrito junto al `.cs` y su hash. Un
oráculo sin su rango declarado no es reproducible.

### REGLA DE FAMILIA — el secuenciador causal (Nico, 2026-07-27)

> **Ningún indicador con subserie de tick sobre primaria de ticks procesa el
> footprint en el callback de cierre. Se usa el patrón SECUENCIADOR CAUSAL.**

**Por qué es de familia y no de BigTrap2.** NT8 no garantiza que todos los
eventos de la subserie de 1 tick lleguen antes del callback de cierre de la
barra primaria. Cualquier `take + reset` en `OnBarUpdate(BarsInProgress == 0)`
captura *los eventos que llegaron*, no *los que le corresponden a esa barra*.
Medido en `tick:25`: el balde tenía entre **15 y 34** eventos donde debía tener
25, y sólo el **27 %** de las barras cerraba con el volumen correcto.

**El patrón**, una vez y reutilizable:

1. Al cerrar cada barra primaria, **snapshot inmutable** con todo lo que el
   kernel lee vía `[0]` o `CurrentBar`.
2. Los eventos de la subserie van a un **FIFO**, agrupados en **bloques de
   exactamente K** = `BarsPeriod.Value`.
3. **Dos colas ordenadas** (snapshots, bloques) y un drenaje que empareja
   snapshot N con bloque N **en orden cronológico estricto**, y sólo cuando las
   dos piezas están. Nunca N+1 antes que N. **Tomar de menos desalinearía todo
   hacia adelante** — que es exactamente el defecto que se corrige.
4. **Bloque residual** de 1..K−1 en la frontera de sesión: NT8 cierra corta la
   última barra de la sesión (medido: bar 3770 = 19 eventos, volumen idéntico).
5. **Auto-verificación**: el conteo es la *regla de corte*, el OHLC es el
   *verificador*. En ticks enteros: primer precio == Open, último == Close,
   mínimo == Low, máximo == High. **Un secuenciador que no se auto-verifica es
   el bug actual con más pasos.**
6. **Política de rotura**: mismatch ruidoso + sesión marcada no confiable +
   resincronización **sólo** en la frontera siguiente. Prohibido reacomodar el
   buffer para forzar el cierre del par: la deriva silenciosa es el enemigo.

#### Registro de exposición

| indicador | patrón | expuesto en | estado |
|---|---|---|---|
| **BigTrap2** | `AddDataSeries(Tick,1)` + take/reset | `tick:N` | ✅ **corregido en v2.2** |
| **VolTicksPOC2** | idéntico | `tick:N` | ⚠️ **expuesto, sin portar** |
| **aVolCellPOI2** | idéntico | `tick:N` | ⚠️ **expuesto, sin portar** |

Los dos últimos tienen su PASS sobre **`time:1`**, donde el corte es por
timestamp y el patrón no falla. En primaria de ticks estarían expuestos igual
que BigTrap2. `VolTicksPOC2` ya emitió 3 `FOOTPRINT_MISMATCH` en su oráculo de
`time:1` —uno de 199 contratos— que es la firma de la familia asomando.

**No se portan todavía**: un cambio por vez, atribución limpia. Primero se valida
el secuenciador en BigTrap2 con oráculos nuevos.

### REGLA DE FAMILIA — etiquetado entre series (Nico, 2026-07-27)

> **Una señal que pertenece a la serie A no puede usarse para etiquetar datos de
> la serie B. Cada serie se etiqueta con SU PROPIO timestamp contra el calendario
> canónico.**

Dos apariciones, y en las dos la señal era **correcta en su propia serie** y
falsa en la otra:

| # | señal | usada para | error medido |
|---|---|---|---|
| 1 | `session_index` de NT8 | indexar sesiones del lado Python | offset constante de **4** (NT8 numera desde la primera barra del chart, Python desde el inicio del parquet) |
| 2 | `Bars.IsFirstBarOfSession` | etiquetar eventos de la **subserie** | hasta **K−1 eventos tarde**; medido 24 (hueco real entre seq 94268 y 94269, el flag cambia entre 94292 y 94293) |

La segunda es la más traicionera porque el flag *existe* y *es verdadero* — sólo
que describe la barra primaria, que recién cierra tras acumular sus K ticks. Un
`session_index` de NT8 se traduce por **trade-date**, nunca por ordinal; y los
eventos de una subserie se etiquetan por **su propio timestamp** contra
`SessionIterator`, nunca por un flag de la primaria.

### Lección permanente: los precios se comparan en ENTEROS de tick

**Toda comparación de precios se hace sobre índices enteros de tick; los `double`
se usan solo para I/O (leer del feed, escribir al CSV, dibujar).** Convertir a
entero **una sola vez**, con `Math.Round(precio / tickSize,
MidpointRounding.AwayFromZero)` en C# — **nunca** `floor`, `truncate` ni cast
directo, porque `precio/tickSize` puede dar `x.999999…` y el cast crearía un
off-by-one. Si el valor puede caer en `x.5` (p. ej. el centro de una fila con
`ticks_per_row` par), se usa la grilla de **medios ticks**, donde vuelve a ser
entero exacto.

Esta familia de bug ya costó **cinco incidentes distintos** en el proyecto:

| # | dónde | síntoma | causa | estado |
|---|---|---|---|---|
| 1 | `parity._geom_ticks` | la misma zona medía 0, 1 o 2 ticks según la paridad del índice de fila | **banker's rounding** al medir en ticks enteros | corregido |
| 2 | `BigTrap2.cs` L349 (pre-v2.1) | 101 `trapped_buyers` espurios, 12,5 % de las zonas | `r*TickSize` (reconstruido) vs `Close[0]` (feed) | corregido v2.1 |
| 3 | `HFTZones2` bordes de zona (pre-v2.2) | 82 `FEATURE_DIFF` | cada lado derivaba el borde con su propia aritmética | corregido v2.2 |
| 4 | `HFTZones2` `inside` (pre-v2.3) | 272 `FEATURE_DIFF`; **refutó PRED-002** | unificar los bordes en v2.2 rompió una cancelación accidental de error y dejó `inside` expuesto al 24,30 % | corregido v2.3 |
| 5 | `AACloseOpenDiffs.cs` `MinDiffTicks` (pre-v1.1) | descartaba el **47,5 %** de los gaps de 1 tick (43,5 % observado contra el oráculo) | `gapPts < MinDiffTicks * TickSize` en points | corregido v1.1 |

Todos son la misma raíz: aritmética de punto flotante decidiendo un empate que
sobre la grilla de ticks es exacto. Vale mirar el **4** con atención: la
corrección del **3** fue correcta y aun así *empeoró* el conteo de diffs, porque
el bug convivía con un segundo error que lo cancelaba en parte. Una corrección
parcial de esta familia puede subir los diffs sin ser un retroceso.

Auditorías: `docs/audits/AUDIT-001_comparaciones_en_grilla_de_ticks.md` (leyendo
código — falló), `AUDIT-002_exposicion_medida_ulp.md` (midiendo) y
`AUDIT-003_barrido_ulp.md` (barrido estático completo de los 6 `.cs`).

Ojo con el caso simétrico: si un `.cs` y su kernel hacen la **misma** aritmética
inexacta, la paridad da PASS *por bug compartido*. Eso satisface el gate pero no
es corrección; se registra como deuda, no como validación.

## 6. Pre-registro de oráculos — campaña mínima (F7)

Generar en una sola sesión de NT8 (rev `.cs` **190ed59+**; registrar la rev en
cada CSV). Contrato base **6E 06-26** (5.56M ticks). Timezone del chart: la de tu
UI; pasarla a la CLI como `--chart-tz`. Matrices de ramas en
`docs/parity_coverage/`. Todos con defaults salvo lo indicado.

### Rango corto (2 sesiones CME) — reutiliza el de Gaps2
`2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z`, `--bars time:1` (salvo BigTrap2 O2).

| Oráculo | Params NT8 (no-default) | Bars | EventLogPath sugerido |
|---|---|---|---|
| **Gaps2 O1** (ya en §1) | defaults | time:1 | `oracles\Gaps2_6E_06-26_may.csv` |
| **Gaps2 O2** min_gap denso | MinGapTicks=3, ExportFloorTicks=2 | time:1 | `oracles\Gaps2_dense_6E_0626.csv` |
| **VolTicksPOC2 O1** | defaults | time:1 | `oracles\VolTicksPOC2_6E_0626.csv` |
| **VolTicksPOC2 O2** FirstTouch | InvalidationMode=FirstTouch | time:1 | `oracles\VolTicksPOC2_firsttouch_6E_0626.csv` |
| **BigTrap2 O1** Diagonal | defaults | time:1 | `oracles\BigTrap2_diag_time1_6E_0626.csv` |
| **BigTrap2 O2** SameLevel | ImbalanceMode=SameLevel | **tick:25** | `oracles\BigTrap2_samelevel_tick25_6E_0626.csv` |
| **BigTrap2 O3** wick off | UseWickFilter=false | time:1 | `oracles\BigTrap2_nowick_time1_6E_0626.csv` |
| **HFTZones2 O1** adaptativo | defaults (arrancar en borde de sesión) | time:1 | `oracles\HFTZones2_adaptive_6E_0626.csv` |
| **HFTZones2 O2** manual | AdaptiveMode=false (params manuales default) | time:1 | `oracles\HFTZones2_manual_6E_0626.csv` |

> Para HFTZones2 el chart debe cubrir ≥1 sesión CME completa ANTES del
> 2026-05-05 17:00 CT (para calibrar) — dejar margen de 2 días a la izquierda.

### Rango largo (≥ 7 semanas) — aVolCellPOI2
El chart NT8 debe tener **≥ 35 sesiones** cargadas antes del rango a comparar.
Rango de comparación sugerido: `2026-05-05T22:00:00Z → 2026-05-07T21:00:00Z`
(las mismas 2 sesiones), con historia cargada desde **2026-03-09** (inicio del
contrato). `--bars time:1`.

| Oráculo | Params NT8 (no-default) | EventLogPath sugerido |
|---|---|---|
| **aVolCellPOI2 O1** | defaults (SessionRelative/TotalVolume/Quantile) | `oracles\aVolCellPOI2_default_6E_0626.csv` |
| **aVolCellPOI2 O2** WallClock/AbsDelta | BucketAnchor=WallClock, DetectionSource=AbsDelta | `oracles\aVolCellPOI2_wallclock_absdelta_6E_0626.csv` |

Corrida Python (mismo patrón que §3, ajustando indicador/params/bars/oráculo).
`parity_covered` de una config se asigna solo cuando TODAS las ramas que activa
(ver `docs/parity_coverage/<kernel>.md`) tienen un oráculo PASS.

## 7. Próxima tanda de oráculos — 6E 09-26 (contrato ya cargado, tick data OK)

Preferido sobre §6 (06-26 no tenía tick data en esta instalación). Todos sobre
**6E 09-26**, dataset `data/nt8/6E/6E_09-26_ticks.parquet` (cubre 2026-06-08 →
2026-07-21). Rev `.cs` **190ed59+**. Ventana corta reutilizable (borde de sesión
CME): **2026-07-13T22:00:00 → 2026-07-16T21:00:00 UTC**.

Pasos NT8 comunes: chart 6E 09-26, Days to load ≥ 10 (para aVolCellPOI2 ≥ 40),
setear el `EventLogPath` del indicador, F5 para recalcular, cerrar/refrescar para
flushear. Dejar los CSV en `E:\EdgeLab\oracles\`.

| Oráculo | Bars | Params no-default | EventLogPath | Ventana Python |
|---|---|---|---|---|
| **Gaps2 25t** | **25 Tick** | `min_gap_ticks=2` | `Gaps2_6E_0926_tick25.csv` | 07-13→07-16 |
| **VolTicksPOC2** | 1 Minute | defaults | `VolTicksPOC2_6E_0926.csv` | 07-13→07-16 |
| **VolTicksPOC2 FirstTouch** | 1 Minute | `InvalidationMode=FirstTouch` | `VolTicksPOC2_ft_6E_0926.csv` | 07-13→07-16 |
| **BigTrap2 Diagonal** | 1 Minute | defaults | `BigTrap2_diag_time1_6E_0926.csv` | 07-13→07-16 |
| **BigTrap2 SameLevel** | **25 Tick** | `ImbalanceMode=SameLevel` | `BigTrap2_same_tick25_6E_0926.csv` | 07-13→07-16 |
| **HFTZones2 adaptativo** | 1 Minute | defaults (arranca en borde de sesión) | `HFTZones2_adaptive_6E_0926.csv` | 07-13→07-16 |
| **HFTZones2 manual** | 1 Minute | `AdaptiveMode=false` | `HFTZones2_manual_6E_0926.csv` | 07-13→07-16 |
| **aVolCellPOI2** | 1 Minute | defaults (Days to load ≥ 40) | `aVolCellPOI2_6E_0926.csv` | **07-19→07-21** |

- **Gaps2 25t**: el `--bars tick:25` de la corrida Python debe coincidir; es un
  `config_id` distinto al de 1 minuto (el `bar_key` entra a la identidad).
- **HFTZones2**: la ventana arranca en 07-13T22:00 (apertura CME) y trae ≥1
  sesión previa cargada → calibración congelada antes de las detecciones.
- **aVolCellPOI2**: necesita ~7 semanas de historia; cargá desde el inicio del
  contrato (06-08) y comparamos las 2 últimas sesiones del parquet (07-19→07-21).
  Requiere el `.cs` reescrito a subserie 1-tick (rev 190ed59+).

Cada uno: me pasás el CSV y corro `run_nt8_bridge.py … --oracle <ind>=<csv>
--zone-store runs/nt8_bridge/store` (con la frontera de madurez automática) →
`parity_report.json` + gate + evidencia en el store. La ventana corta 07-13→07-16
ya validó Gaps2 (PASS); el resto usa la misma para comparabilidad.

## 8. Semántica de `parity_covered` (F7c) — pre-declarada antes de implementar

> Esta sección define QUÉ significa que una configuración quede cubierta por el
> oráculo de OTRA. Se escribió **antes** de conectar `coverage.py` al flujo, y
> toda afirmación de neutralidad está justificada con el código del matcher
> (`edgelab/bridge/parity.py::match_zones`), no con intuición.

### 8.1 Superficie comparada por el matcher (base de todo el razonamiento)

`match_zones` compara **exactamente** estos campos y ningún otro (verificado
línea por línea en `parity.py`):

| Campo comparado | Diagnóstico que emite |
|---|---|
| pertenencia al conjunto de zonas | `MISSING_IN_NT8` / `MISSING_IN_PYTHON` |
| `created_ms` | `TIMESTAMP_DIFF` |
| `top` / `bottom` (en ticks) | `GEOMETRY_DIFF` |
| `state` (solo zonas maduras) | `STATE_ORDER_DIFF` |
| `touches` (solo zonas maduras) | `FEATURE_DIFF` |

Todo lo demás que produce el kernel (`display`, `size_ticks`, `atr_at_creation`,
`kind`, el resto de `features`) **no lo mira el matcher**. Un parámetro que solo
mueve campos no comparados no puede cambiar el resultado de la paridad.

### 8.2 Definición de la relación de cobertura

Una partición **T** (target) queda `parity_covered` por una partición **S**
(source) si y solo si se cumplen TODAS estas condiciones:

1. `S.parity_state == "parity_exact"` (S tiene oráculo real propio que pasó P2).
2. `T.run_id != S.run_id` — **anti-autootorgamiento** (§8.4).
3. Mismo `indicator`.
4. Mismo `kernel_id` — implica mismo código del kernel y de sus dependencias
   semánticas (`common.py`, `bars.py`, `sessions.py`) y mismas versiones de
   schema. Un cambio de código ⇒ otro `kernel_id` ⇒ cobertura NO se hereda.
5. Mismo `instrument`.
6. Mismo `bar_key` (bar_spec) — **decisión sellada**: el bar_spec es dimensión
   externa de identidad, nunca se cruza.
7. Params canónicos idénticos, **excepto** los declarados coverage-neutral para
   ese kernel (§8.3).
8. `chart_tz` idéntico, **excepto** si `chart_tz` está declarado como eje
   neutral para ese kernel (§8.3).

**`contract` y ventana temporal PUEDEN diferir.** Ese es justamente el contenido
de la cobertura: el oráculo prueba una propiedad del **código con esos
parámetros** (reproduce a NT8 tick a tick), no una propiedad de un tramo de
datos. Con `kernel_id`, params y `bar_spec` fijos, el cómputo es el mismo
programa; cambiar el contrato cambia la entrada, no el programa.

**Riesgo residual declarado (honesto):** un tramo de datos distinto puede
ejercitar ramas que la ventana del oráculo nunca tocó (feriados, huecos de
sesión, bordes de calibración). Las matrices de `docs/parity_coverage/` razonan
sobre ramas **por parámetro**, no sobre qué ramas activó realmente un tramo de
datos concreto — `coverage.config_branches` deriva las ramas de los params, no
de la data. Por eso `parity_covered` es **estrictamente más débil** que
`parity_exact`, y por eso `edge_validation_contract.md` ya exige `parity_exact`
**propio** de la config ganadora para promover a `EDGES_DISCOVERED.md`.

### 8.3 Params y ejes coverage-neutral — lista blanca fail-closed

Regla general por clase de `PARAM_SPEC`:

| Clase | ¿Puede quedar cubierta si difiere? | Razón |
|---|---|---|
| `recompute` | **NUNCA** | cambia el estado histórico / el conjunto de zonas |
| `lifecycle` | **NUNCA** | cambia `state`, `ended_ms` y `touches`: campos comparados |
| `instrument` | **NUNCA** | cambia la escala de precio/tick |
| `visual`, `forbidden` | irrelevante por construcción | no entran a `config_id` (`identity.ANALYTIC_CLASSES`), así que no pueden diferir entre dos `config_id` |
| `offline` | **solo si está en la lista blanca** | la clase `offline` significa "re-filtrable desde el export continuo", que NO es lo mismo que "no afecta la paridad": son criterios distintos y conflarlos sería un error de diseño |

**Lista blanca (fail-closed: lo que no está listado, bloquea la cobertura):**

| Kernel | Params neutrales | Ejes neutrales | Evidencia |
|---|---|---|---|
| **Gaps2** | `min_gap_ticks` | `chart_tz` | ver §8.3.1 |
| VolTicksPOC2, BigTrap2, HFTZones2, aVolCellPOI2 | *(ninguno)* | *(ninguno)* | sin verificar ⇒ bloquean cobertura |

#### 8.3.1 Justificación de la lista blanca de Gaps2

- **`min_gap_ticks` es neutral.** En `gaps2.py` solo alimenta
  `g["display"] = gap_ticks >= min_gap_ticks`; `display` viaja a `features` del
  zone store y el matcher nunca lo lee (§8.1). En el `.cs` de NT8 el efecto es
  simétrico: gobierna únicamente el dibujo (`if (!g.Display) continue` en
  `DrawZones`), mientras que `LogEvent("ZONE_CREATED", …)` se emite sin
  condición para todo gap `>= ExportFloorTicks` — es decir, tampoco cambia el
  CSV que consume el oráculo. Verificado empíricamente sobre 6E 09-25
  (2025-08-01, 6 h, 174 zonas): con `min_gap_ticks` en {2,5,8,12} el conjunto
  `(created_ms, top, bottom, state, touches)` es **idéntico**, y solo cambia el
  conteo de zonas dibujables (174 a 0). Contraste de control: con
  `export_floor_ticks=3` (clase `recompute`) el conjunto pasa de 174 a 20 zonas.
- **`chart_tz` es eje neutral para Gaps2.** El matching usa `unix_ms`
  (absoluto); `chart_tz` solo formatea la columna legible `ts`. Verificado:
  mismas 174 zonas y mismos campos comparables con `UTC` y con
  `America/Argentina/Buenos_Aires`; solo difiere el texto de `ts`
  (`2025-08-01 00:00:01.012` vs `2025-07-31 21:00:01.012`, mismo `unix_ms`).
  **No es generalizable**: un kernel que bucketea por hora civil (p.ej.
  `aVolCellPOI2` con `BucketAnchor=WallClock`) sí cambia su cómputo con la tz,
  por eso la lista es por kernel y arranca vacía para los demás.
- **`max_logged_touches` NO es neutral** (aunque sea clase `offline`). Recorta
  cuántos `ZONE_TOUCHED` se escriben al log. En Python el contador
  `g["touches"]` avanza igual, y en la muestra probada la reconstrucción desde
  el log coincidió; pero la garantía **no es universal**: §4 de este contrato
  declara que `SESSION_END` puede faltar en el export NT8 si el chart sigue
  vivo, y en ese caso el último evento de una zona viva podría ser un
  `ZONE_TOUCHED` recortado, subreportando `touches` — un campo que el matcher SÍ
  compara. Ante una garantía que no se sostiene en todos los casos, la regla es
  bloquear.

### 8.4 Anti-autootorgamiento

La cobertura la asigna **exclusivamente** el proceso de propagación
(`coverage.propagate_coverage`), comparando los campos de identidad de una
partición contra los de un `parity_exact` **preexistente y distinto**. En
particular:

- ninguna corrida puede declararse `parity_covered` a sí misma (`T.run_id !=
  S.run_id`, y una partición nunca es su propia fuente);
- `store.publish_run` jamás escribe `parity_covered` (solo deriva
  `parity_pending` / `parity_exact` / `parity_failed` de su propio gate);
- una partición sin oráculo propio no puede "heredarse" cobertura de otra
  partición que a su vez esté solo `parity_covered` (la fuente debe ser
  `parity_exact`): la cobertura **no es transitiva**, para que no se propague en
  cadena desde una única evidencia.

### 8.5 Degradación: `parity_under_review`

Si **cualquier** configuración con el mismo `kernel_id` que el oráculo fuente
falla un gate de paridad posterior (`parity_failed`), todas las coberturas
otorgadas por ese oráculo pasan a **`parity_under_review`**:

- no es revocación silenciosa (la evidencia y la traza quedan registradas);
- no es permanencia ciega (el estado deja de ser utilizable como
  `parity_covered` a efectos de elegibilidad);
- exige **revisión humana explícita**: analizar la causa raíz del FAIL y decidir
  si la cobertura sigue siendo válida (queda `parity_covered`) o cae
  (`parity_pending`). Esa decisión se consulta con Nico (cambio de semántica de
  validación) y se registra.

### 8.6 Auditabilidad

Toda partición cubierta registra en su `manifest.json` un bloque `coverage` con:
`source_config_id`, `source_run_id`, `source_contract`, `oracle_path`,
`oracle_sha256`, `rule_version` (versión de esta sección), `neutral_params_used`
y `granted_utc`. Sin ese bloque, un `parity_covered` es inválido por definición
(no auditable ⇒ no otorgado).

### 8.7 Aplicación al store vigente (2026-07-24)

Resultado de `coverage.propagate_coverage` sobre `runs/nt8_bridge/campaign_store`
(21 particiones), con la única fuente `parity_exact` disponible: **Gaps2
`a6c32c0e9dbeb79a`** (6E 09-26, oráculo `oracles/Gaps2_6E_0926.csv`).

| Resultado | Particiones | Justificación |
|---|---|---|
| `parity_exact` (fuente) | 1 — `a6c32c0e` | oráculo real propio, gate P2 PASS |
| **`parity_covered`** | **3** — `d1289a36` (`min_gap_ticks=5`), `427ebe95` (`=8`), `9221a51d` (`=12`) | difieren de la fuente SOLO en `min_gap_ticks` (param neutral §8.3.1) y en `chart_tz` (eje neutral); mismo `kernel_id`, `bar_key=time_1`, instrumento 6E |
| `parity_pending` (Gaps2) | 8 | 5 difieren en `export_floor_ticks` (clase `recompute`) y 3 en `reversal_confirm_ticks` (clase `lifecycle`) — ambas **nunca** cubiertas (§8.3) |
| `parity_pending` (BigTrap2) | 8 | otro `indicator` y otro `kernel_id`: no hay oráculo de BigTrap2 (§8.2 puntos 3-4) |

Nota de firewall: la fuente proviene de una ventana **dentro** del holdout
(2026-07-13→16), usada bajo la excepción **target-free** de `edge_validation_contract.md`
§G4 (paridad geométrica, sin mirar P&L ni elegir candidatos) y registrada en
`docs/holdout_access_log.md`. Por eso esa evidencia **no sirve** como oráculo de
promoción de un edge: la promoción exige `parity_exact` propio sobre una ventana
del **período de desarrollo** (pre-holdout) — ver `CAMP-001` §11.
