# HANDOFF 2026-08-22 — continuar en otro chat de Notion

**Punto de entrada unico.** Si sos un modelo nuevo entrando al proyecto por el chat de
Notion: lee este archivo entero antes de tocar nada. Despues lee, en este orden,
`CONTRATO_LLM.md`, `EDGES_DISCOVERED.md` y
`docs/research/REVISION_MULTIMODELO_BT2_OPUS5.md`.

**Rama**: `foundation/f0b-compatibility-probe` · **Tip**: `ba77bfd`
**Usuario**: Nicolas Buttaro (ART, UTC-3) · **Rol del asistente**: auditor

---

## 0. Rol e identidad del asistente

Auditor de un programa de investigacion cuantitativa, no colaborador entusiasta.
El trabajo es **pre-registro**: se escribe que se va a medir y con que criterio se
falsa, **antes** de medir. Lo que se descubre despues de mirar los datos se marca
como exploratorio y no corona nada.

Cuatro reglas que no se negocian:

1. **Nunca tocar outcomes, retornos, P&L ni holdout sin autorizacion escrita de Nico.**
2. **Todo numero se mide; no se estima ni se infiere de un razonamiento plausible.**
   Si no se pudo medir, se dice "no medido", no se aproxima.
3. **El control no es cero.** Siempre hay un comparador declarado (hoy: `S1` de F2.9).
4. **Contradecir a Nico cuando los datos lo contradicen**, con el numero al lado.
   Ya paso varias veces y es la funcion principal del rol.

---

## 1. Donde esta parado el proyecto

`EDGES_DISCOVERED.md`: **ningun edge promovido**. Tres hipotesis refutadas con acta:

| linea | veredicto |
|---|---|
| H1 / BigTrap2 T=34 | **MUERTA**. 424 eventos, bruto +0,2995 t, friccion −2,7680 t, **neto −2,4685 t** |
| Soporte/resistencia | **FUERTEMENTE REFUTADA**, ~96 % de ruptura |
| Iman / revisita | **CERRADA-REFUTADA** (`BIGTRAP2_MAGNET_LINE_CLOSED`) |

Y el resultado que ordena todo lo demas, **F2.9**: la vela extrema generica `S1`
da **+0,038** y **supera** al creador BigTrap2 `K0` = **+0,021**, que a su vez es
indistinguible de la no-creadora emparejada `N0`. Es decir: **el kernel hoy no aporta
nada por encima de "vela grande"**. Cualquier cambio se mide contra `S1`, no contra 0.

H-GC-BT2-1: **holdout gastado** (`5814f1f`, 16/16 configuraciones no pagan). **No se
reabre.**

---

## 2. Cadena de commits (rama viva)

```
5814f1f  H-GC-BT2-1: holdout gastado, 16/16 no pagan
312a04a  \
fea1ef3   >  handoff 23:00 del 21-ago
0cdd0c6  /
b88d097  doc BIGTRAP2_UNIVERSAL_FILL.md + nt8/README.md
783b0b6  nt8/BigTrap2UniversalFill.cs v1.0        <- el .cs faltaba en b88d097
e9b6422  nt8/BigTrap2UniversalEdge.cs v1.0        (Claude Opus 5 local)
20d2c7b  nt8/BigTrap2Absorption.cs v1.0           <- indicador nuevo
ba77bfd  acta multimodelo + nt8/README.md         <- TIP
```

**Leccion operativa de `b88d097`**: ese push declaraba subir el `.cs` y subio solo el
doc. **Siempre verificar con `get_commit` y contar los `files[]`.** Se aplico en esta
tanda: `20d2c7b` = 1 archivo / 800 lineas, `ba77bfd` = 2 archivos / 295 adiciones.

---

## 3. Estado de la tarea en curso: revision multimodelo

Acta: **`docs/research/REVISION_MULTIMODELO_BT2_OPUS5.md`**.

Nico pidio revisar BigTrap2 con **tres modelos distintos**, cada uno respondiendo
**las mismas 7 preguntas**, sin editar las secciones de los otros:

1. Que es hoy el evento, **operativamente**.
2. Que evidencia del repo lo respalda o lo refuta, con numeros.
3. Fortalezas reales. 4. Debilidades reales.
5. La barrera economica: cuanto hace falta y cuanto hay.
6. Corresponde cambiar el indicador. Que exactamente.
7. Con que prueba **falsable y pre-registrada** se decide.

| pasada | estado |
|---|---|
| Grok 4.6 | hecha en chat, **sin acta escrita** |
| **Claude Opus 5** | **COMPLETA** — seccion 1 del acta |
| GPT | **PENDIENTE** — seccion 2, vacia y esperando |
| Kimi K3 | **PENDIENTE** — seccion 3, vacia y esperando |
| Sintesis | seccion 4, tabla armada, se llena con las tres |

**Regla de cierre ya escrita**: si los tres coinciden en Q4 y Q6, se implementa y se
mide. Si difieren en Q1, hay un problema de definicion y **eso** se resuelve antes que
cualquier codigo.

### El hallazgo central de la pasada Opus 5

`ratio = agresivo / max(opuesto, 1)`. El `max(..., 1)` **no es un piso de seguridad:
es la definicion efectiva del evento**. Con la celda opuesta vacia — lo normal en una
cubeta de 25 ticks — el cociente degenera en el conteo absoluto. Con
`ImbalanceRatio = 3` el evento real es **"tres contratos al ask y nada abajo"**.

Confirmado por datos, no por lectura de codigo: el minimo de `trap_vol` es **3** y el
minimo de `trap_ratio` es **3**, exactos. Coinciden porque son la misma cosa.

GC DEC26, 17–21 ago (`h_gc_bt2x_oracle_inspect.json`):

| magnitud | valor |
|---|---|
| `BARRA_PROCESADA` | 24.093 |
| `TRAP` | **11.964 = 49,7 % de las cubetas** |
| `trap_vol` p25/p50/p75 | **3 / 4 / 7** (max 144) |
| `trap_nrows` p25/p50/p75 | **1 / 1 / 1** (max 4) |
| `ZONE_CREATED` (vol>=30) | 122 = 1,02 % |

### La barrera economica, que es la que manda

GC: 1 tick = 10 USD. Friccion 1,5 t = 15 USD round-trip.
Sin deriva, `P(TP) = SL/(SL+TP)` y el EV bruto es **cero por construccion** — por eso
el barrido de 960 celdas no corona nada: no puede.

| concepto | valor |
|---|---|
| mejor celda (SL 13 / TP 30) | 31,9 % de aciertos |
| camino sin deriva | 30,2 % |
| exceso medido | **+1,7 pp = +0,72 ticks brutos** |
| necesario para netear +1 tick | 36,1 % = **+5,8 pp** |
| **factor faltante** | **~3,4x** |

---

## 4. El indicador nuevo: `nt8/BigTrap2Absorption.cs` v1.0

sha256 `3f47878d2220b163b86ddc353782f21e9ba009501c2307448327a214262bf417`
git blob `301123daf94775c4291d22a88dc9eef52ffe6986` · 30.880 bytes · 800 lineas CRLF

**Es un indicador NUEVO. No modifica ni reemplaza a BigTrap2, Universal, Fill ni Edge.**
Conviven los cinco.

### Que cambia

El evento deja de ser un umbral absoluto y pasa a ser un **residuo**: cuanto flujo
firmado se comio el mercado por cada tick que se movio.

```
dFav = sign(flujo_firmado) * (closeTick - openTick)     en ticks
A    = |flujo| / (1 + max(0, dFav))      [AbsDirectional, default]
A    = |flujo| / (1 + |dPx|)             [AbsMagnitude]
dispara si A >= percentil q de las ultimas L cubetas
```

El percentil es **CAUSAL**: `PushAbs(aScore)` se llama **despues** de evaluar, asi que
la cubeta en curso no esta en su propio umbral. Las cubetas **residuales** (fin de
sesion, bloque parcial) tienen `aPass = false` y **no entran al historial**.

Mas dos endurecimientos, como **parametros** y no como constantes nuevas:

- **`MinStackedRows`** (default 2): exige filas desbalanceadas **contiguas**.
  Mata la celda suelta (`trap_nrows` p50 = 1 en el kernel viejo).
- **`MinTrapFrac`** (default 0,20): el trap tiene que ser una **fraccion** del volumen
  de la cubeta. `MinTrapVolume` absoluto queda en **0 (apagado)**.
- **`TapeWindowTicks`** pasa a ser parametro real (en Fill era `const 25`).

### La decision de diseno que ahorra computo

`TRAP` **se exporta siempre** que haya geometria (`vol >= MinExportVolume`), con los
campos viejos identicos a BigTrap2 (`vol, centroid, zone_lo, zone_hi, n_rows,
max_ratio, close, bar_vol, fp_vol, n_quote, n_rule`) **mas** `trap_frac, signed_flow,
d_ticks, a_score, a_thr, a_pass, side_match, n_runs, run_vol, run_rows, run_frac,
run_lo, run_hi, run_centroid, available_at`.

**Una sola corrida permite barrer `q`, `MinStackedRows` y `MinTrapFrac` OFFLINE y
reproducir el kernel viejo exactamente desde el mismo archivo.** Ademas emite
`ABS_SCORE` por cubeta. `ZONE_CREATED` y `FILL` salen solo con **todos** los cortes.

### Defaults

`TapeWindowTicks=25` · `ScoreMode=AbsDirectional` · `AbsorptionPct=90` ·
`AbsorptionLookback=500` · `MinHistoryBuckets=200` · `RequireFlowSideMatch=true` ·
`TicksPerRow=1` · `ImbalanceMode=Diagonal` · `TrapVolumeSource=AggressiveSide` ·
`UseWickFilter=true` · `WickZonePct=30` · `ImbalanceRatio=3` · `MinStackedRows=2` ·
`MinTrapFrac=0.20` · `MinDeltaFilter=0` · `MinTrapVolume=0` · `MinExportVolume=1` ·
`InvalidationMode=CloseThrough` · `MaxAgeBars=2000` · `TopPercentFilter=100` (visual,
**es look-ahead**) · Teal = `trapped_buyers` (corto) · Red = `trapped_sellers` (largo).

---

## 5. Las 3 puertas pre-registradas — NO negociables

Se corre en **discovery: GC 08-26, 24–30 junio**. El holdout de agosto **no se toca**.

| # | criterio | corta si |
|---|---|---|
| **1** | decil superior de `a_score`: **MFE p50 / MAE p50 >= 1,25**, con n >= 200 eventos y >= 10 sesiones | hoy MFE p50 = 38 y MAE p50 = 36 para *todos*. Si el decil no rompe la simetria, se cierra la linea **ahi**, sin pasar a SL/TP |
| **2** | superar `S1` = **+0,038** de F2.9 con IC que **no lo toque** | si no, es una forma cara de detectar una vela grande |
| **3** | bruto **>= 2,5 ticks** (friccion 1,5 + 1 de margen) | hoy hay 0,72. Sin esto no hay negocio, haya o no significancia |

**Orden 1 → 2 → 3.** Fallar cualquiera cierra la linea y se escribe acta de refutacion
en `EDGES_DISCOVERED.md`.

Probabilidad subjetiva declarada por Opus 5 de que las pase: **baja**. Se propuso igual
porque es la primera version del evento que es **falsable, escala-libre y con respaldo
externo**, y porque medirlo cuesta una corrida sobre datos que ya estan.

---

## 6. Inventario de indicadores NT8 versionados

| archivo | version | sha256 |
|---|---|---|
| `nt8/BigTrap2.cs` | v2.1 | `77af06ee…0a557fbf5` |
| `nt8/BigTrap2UniversalFill.cs` | v1.0 | `794110f0…fc99e071` |
| `nt8/BigTrap2UniversalEdge.cs` | v1.0 | `dad03a1e…3548c9a` |
| **`nt8/BigTrap2Absorption.cs`** | **v1.0** | `3f47878d…262bf417` |

Reglas de `nt8/README.md`, que vienen del incidente 2026-07-25:
**sin `#region NinjaScript generated code`** (lo prohibe `CONTRATO_LLM.md` §5),
**CRLF obligatorio** (con LF, NT8 anexa una segunda region generada y no compila),
reemplazo in place, respaldos a `archive/nt8_cs_backup/` **fuera** de `bin\Custom`.
Verificacion: `python tools/check_nt8_cs.py nt8/X.cs`.

`BigTrap2Universal.cs` (v1.1/v1.2) **sigue sin versionar** y **tiene 1 region
generated**, o sea que hoy no puede entrar al repo tal como esta. Ver P-62.

---

## 7. Datos disponibles (gitignoreados)

| dato | sha256 / tamano |
|---|---|
| `oracle_events__Tick25.csv` (GC DEC26, 17–21 ago) | `e89fed22…1e3050a84`, 36.584 lineas |
| `GC 12-26.Last.txt` | `dd67cacb…f45757d581aa`, 683.188 ticks |
| **`GC 08-26.Last.txt`** (discovery 24–30 jun) | `56f7d1c4…566519c4ff014`, 1.081.633 ticks |
| L2 GC, 12 parquets ZSTD | jun 21–26 ~37,6 M + ago 16–21 ~34,3 M filas |

Esquema L2: `record_type, market_data_type, timestamp, subsecond, operation,
position, market_maker, price, volume`.

**El join L2 <-> ticks de junio esta en 3 de 20.486.** Hasta cerrarlo, la L2 **no**
sirve para elegir configuracion. Cerrarlo es lo que habilita OFI, que es el cambio con
mayor respaldo academico disponible.

---

## 8. Prohibiciones vigentes

- **No reabrir H-GC-BT2-1.** Holdout gastado.
- **No coronar 15t / SL5 / TP55** del barrido: n = 55, es 1 celda de 960, y el propio
  JSON se llama `EXPLORATORY_DISCOVERY_JUN24_30_NOT_EDGE`.
- **No tunear con la L2** hasta cerrar el join de junio.
- **No usar `SizeScaling` ni `TopPercentFilter`** para decidir nada: son look-ahead.
- **No medir contra cero.** El control es `S1` = +0,038.
- **No confundir tres capturas ganadoras con un edge.** Ya paso; el sesgo de seleccion
  visual es exactamente lo que el pre-registro existe para frenar.

---

## 9. Orden de trabajo a partir de aca

1. **Pasada GPT** sobre las 7 preguntas → seccion 2 del acta. No tocar la 1.
2. **Pasada Kimi K3** → seccion 3. No tocar la 1 ni la 2.
3. **Sintesis** (seccion 4) y aplicar la regla de cierre.
4. **Instalar `BigTrap2Absorption.cs` en NT8** y correr GC 08-26, 24–30 jun con
   `EventLogPath` seteado.
5. **Paridad `.cs` <-> kernel Python** (`bigtrap2.py` + `bars.py`) en Claude local:
   `check_nt8_cs.py`, 0 `FOOTPRINT_MISMATCH`. **Esto no se hace en el chat de Notion**,
   que no tiene los datos ni NT8.
6. **Medir las 3 puertas**, en orden.
7. **Asentar en `PENDIENTE.md`**: primero P-58/P-59/P-60 de
   `BOARD_H-GC-BT2-X_2026-08-21.md`, despues P-61/P-62/P-63 de
   `BOARD_P61_P63_2026-08-22.md`.
8. **Semantica de los parquets L2** y join L2 <-> ticks de junio.

**Reparto de tareas por entorno**, porque no es lo mismo:

| entorno | sirve para | no sirve para |
|---|---|---|
| **Chat de Notion** (sandbox + GitHub MCP) | escribir/leer el repo, redactar actas, escribir `.cs`, razonar sobre numeros ya medidos | correr NT8, tocar los parquets, medir paridad |
| **Claude local / Antigravity** | correr los kernels, paridad, mediciones sobre datos | — |

---

## 10. Literatura que respalda el cambio propuesto

- **Cont, Kukanov, Stoikov** — *The Price Impact of Order Book Events*, JFEc 2014,
  12(1):47-88 (arXiv 1011.6402). Delta precio ~ OFI / profundidad, **lineal**; la
  relacion con **volumen** es "noisy and less robust". Es el fundamento de medir
  flujo contra desplazamiento en vez de volumen solo.
- **Chakrabarty, Pascual, Shkilko** — JFM 2015, 25:52-79. Tick rule ~77 % de acierto:
  por eso se usa bid/ask primero y tick rule solo como respaldo, contando
  `n_quote` / `n_rule`.
- **Lopez de Prado**, *AFML* cap. 2 (information-driven bars); **Easley–Lopez de
  Prado–O'Hara**, *The Volume Clock*.
- Contra-nota (MQL5 art. 23310): las mejores propiedades estadisticas del muestreo
  **no** se transfieren automaticamente al resultado de la estrategia.
- Practica: absorcion = z-score de volumen + desbalance de tomadores + **impacto
  relativo bajo**; y **imbalances apilados** frente a la celda aislada.
