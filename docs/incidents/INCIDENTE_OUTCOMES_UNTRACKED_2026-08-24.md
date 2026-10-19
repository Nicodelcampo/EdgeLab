# INC-OUTCOMES-UNTRACKED · outcomes abiertos por fuera del preregistro, detectados en el worktree

- **Fecha:** 2026-08-24 · **Rama:** `foundation/f0b-compatibility-probe`
- **HEAD de detección:** `b58dd4e011606b6b37d6d16795f58e1c615b9580`
- **HEAD de registro:** `dc63c2feec1bb451ee39da6a5f43d175385c252d`
- **Manifest:** `INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.manifest.json`
- **Cuarentena:** `C:\Users\nicoc\OneDrive\Documentos\DataNT8\quarantine\INC_OUTCOMES_UNTRACKED_20260824\`

> **Esto no lo produjo la campaña target-free del 2026-08-24.** Se encontró
> preexistente en el worktree durante el Paso 0 de esa campaña, antes de lanzar nada.

---

## 1. Qué se encontró

Once archivos sin seguimiento de git, **ajenos a `dc99def` y `dc63c2f`**: seis scripts
en `tools/` y cinco CSV de resultados en la raíz del repo.

**Los once tienen el mismo `mtime` al segundo: `2026-08-23T20:58:34Z`.** Eso es firma de
copia en bloque, no de once corridas — los CSV tendrían timestamps posteriores a los
scripts si se hubieran generado ejecutándolos acá.

Las columnas de los CSV son inequívocamente de outcomes:

```
WinRate · Net · p-val · Veredicto · TP · SL · MFE · MAE · Asimetria
```

`TP`/`SL` es monetización — territorio de Puerta 3, ni siquiera de Puerta 1.

---

## 2. Matriz de exposición

| clasificación | valor |
|---|:-:|
| `P1_133_OUTCOME_EXPOSURE` | **YES** |
| `SEALED_19_OUTCOME_EXPOSURE` | **YES** |
| `TEMPORAL_HOLDOUT_EXPOSURE` | **YES** |
| `CONTEXT_FILTER_SEARCH` | **YES** |
| `CROSS_ASSET_OUTCOME_SEARCH` | **YES** |
| `YM_FAMILY_EXPOSURE` | **YES** |

### 2.1 El vector sobre el universo de Puerta 1

**Un solo script** toca fechas pre-holdout del universo GC: `tools/validate_oos_gold.py`.

```
cinta       GC 08-26.Last.txt
max_ticks   1.500.000
rango leido 2026-05-24 .. 2026-06-12
metricas    WinRate, Net, Monte Carlo p-value, Veredicto
```

**11 sesiones de las 133 de Puerta 1** quedaron expuestas:

```
20260528  20260529  20260601  20260602  20260603  20260604
20260605  20260609  20260610  20260611  20260612
```

**Y 1 de las 19 selladas: `20260608`.**

El propio docstring del script dice que evalúa *«si el filtro de contexto descubierto
en GC 12-26»* generaliza. O sea: **descubrimiento en agosto, validación sobre junio**.
Junio es el universo de Puerta 1.

### 2.2 Holdout temporal — clasificado por fecha medida, no por nombre

La ventana de holdout es `2026-07-01 .. 2026-12-31`. Para cada script se midió el rango
**efectivamente leído**, aplicando su `max_ticks` sobre la cinta real:

| cinta | `max_ticks` | leído | en holdout |
|---|---:|---|:-:|
| GC 12-26 | — | `20260817..20260821` | **SÍ** |
| YM 09-26 | — | `20260818..20260821` | **SÍ** |
| ES 09-26 | 350.000 | `20260816..20260817` | **SÍ** |
| NQ 09-26 | 350.000 | `20260816..20260817` | **SÍ** |
| YM 03-26 | — | `20260115..20260123` | no |
| YM 06-26 | 2.000.000 | `20260329..20260508` | no |

Cuatro contratos leídos **enteramente dentro del holdout temporal**. GC 12-26 no se
descartó por llamarse «DEC26»: se descartó de la lista de inocentes porque sus fechas
reales son de agosto.

`YM 03-26` y `YM 06-26` son pre-holdout — comprometen la familia YM por otra vía, no
por el holdout temporal.

### 2.3 Búsqueda de contexto con outcomes

`reports_context_filter_sweep_GC_DEC26.csv` (126 filas) y su gemelo de YM (69 filas)
cruzan:

```
Sesion (Asia / London / RTH Open / RTH Tarde / Todas)  x  Tendencia  x  VelocidadTape  x  Bracket
```

contra `WinRate`, `Net`, `p-val` y `Veredicto`.

> **`Sesion` acá es franja horaria, no fecha.** Es decir: se barrió **hora del día contra
> outcomes** — exactamente uno de los tres ejes a los que
> `specs/bt2_absorption_gate1_v1.json` exige que un candidato de contexto sea
> **ortogonal** (`candidate_must_be_orthogonal_to: [a_thr, time_of_day, tick_rate]`).

**Consecuencia:** `context_hypothesis_status: NONE_PREREGISTERED` deja de ser una
descripción global válida para GC 12-26 y YM 09-26. Cualquier hipótesis de contexto
sobre hora del día o velocidad de tape en esos datasets es **post-hoc**, no
pre-registrada.

### 2.4 Barrido cross-asset y familia YM

`reports_cross_asset_evaluation.csv` cubre `6E · ES · GC · NQ · YM` con `MFE`, `MAE`,
`Asimetria`, `WinRate`, `Net`, `Veredicto`.
`reports_ym_multi_quarter_audit.csv` cubre `YM 03-26 · 06-26 · 09-26` con `TP`/`SL` y
`p-val`.
`reports_bigtrap2_tickframe_sweep_GC.csv` barre `10 · 25 · 50 · 100 · 200 ticks` contra
`TP`/`SL`/`WinRate`/`Net`/`p-val`.

---

## 3. Consecuencias, sin borrar nada

1. **Puerta 1 ya no puede presentarse como confirmatoria pura** sobre las 11 sesiones
   listadas en §2.1. Va **enmienda**, no reescritura: el preregistro original queda
   intacto.
2. **`SEALED_BLOCK_COMPROMISED`** — la sellada `20260608` fue tocada. Ese bloque **no
   puede presentarse como validación nueva** sin declarar la exposición.
3. **Holdout temporal comprometido** para las familias y configuraciones efectivamente
   exploradas (§2.2). No se extiende la contaminación a mecanismos que no se midieron,
   pero tampoco se oculta.
4. **La familia YM** queda comprometida junto con cualquier afirmación cross-asset
   asociada.
5. **Los `Veredicto` de esos CSV no se leyeron.** La auditoría extrajo únicamente
   metadatos: nombres de columna, conteos de fila, instrumento, rango y presencia de
   métricas. No se consumió ningún resultado económico, ni signo, ni magnitud.

---

## 4. Qué NO cambia

**La campaña target-free del 2026-08-24 sigue siendo válida**, y ésta es la distinción
que hay que sostener con precisión:

```
CAMPAIGN_OUTCOMES_OPENED      = false     <- la corrida de hoy
PREEXISTING_OUTCOME_EXPOSURE  = YES       <- lo que ya estaba
```

> El flag `outcomes_opened=false` que emite `tools/bt2_absorption_param_sweep.py`
> describe **únicamente esa corrida**. **No es una afirmación global sobre el
> proyecto**, y el reporte final tiene prohibido escribir `OUTCOMES_NOT_OPENED` como
> enunciado global.

El landscape target-free puede correr igual porque no abre outcomes, no elige ganadores
y sólo mide estructura, población, score, geometría, lifecycle y redundancia. **La
contaminación cambia la interpretación futura; no vuelve outcome-dependent a una
medición que no mira outcomes.**

---

## 4-bis. Corrección del inventario: son **12**, no 11

El inventario inicial declaró 11 archivos. **Son 12.**

`git status --short` **colapsa los subdirectorios sin seguimiento en una sola línea**
(`?? scratch/`), así que el archivo de adentro nunca apareció como entrada propia del
inventario.

```
scratch/test_session_kernel.py
  11.241 bytes
  last write   2026-08-23 17:58:34.393956600 -0300   <- MISMO SEGUNDO que los otros 11
  sha256       b0568ada86cdea75c9ee383dc3399bc040c5f6a4e50152d81d8ffd268dae2e1e
```

**Mismo drop, confirmado por el `mtime` idéntico al segundo.** Cuarentenado con el mismo
procedimiento y verificación bit a bit.

**Pero es target-free y no cambia la matriz de exposición.** Grep sin coincidencias para
`mfe|mae|pnl|winrate|net_|p_val|p-val|veredicto|take_profit|stop_loss|TP|SL|retorno|hit_rate`,
y su propio docstring lo declara verificador de paridad contra
`bt2_absorption__TW25_2.csv`.

```
12 archivos del mismo drop  =  11 con outcomes  +  1 target-free
```

**Ninguna de las seis clasificaciones de §2 se mueve.**

### Cómo apareció

No lo encontró una revisión: lo encontró el **fail-closed del runner**.
`tools/bt2_absorption_param_sweep.py::clean_commit()` se negó a arrancar con el árbol
sucio, y al ir a limpiarlo apareció el archivo que el inventario no había visto.

> Un guardrail que aborta la corrida formal atrapó un hueco de la auditoría manual que
> la auditoría manual no iba a encontrar sola.

---

## 5. Procedimiento de cuarentena

1. Inventario inmutable de los 11: ruta, bytes, `creation_time`, `last_write`, sha256.
2. Copia a `quarantine\INC_OUTCOMES_UNTRACKED_20260824\`.
3. **Verificación bit a bit** sha256 origen ↔ copia. Las 11 coincidieron.
4. Sólo después de esa igualdad, retiro de los originales del worktree hacia
   `quarantine\...\originales\`.
5. **No se borró nada. No se usó `git clean`.** Timestamps y contenido intactos.
6. Los 11 archivos **no se commitean** — ni los scripts ni los CSV.

---

## Aporte al referente

Queda registrado, con fecha medida y no inferida, exactamente qué sesiones del universo
de Puerta 1 y cuál de las selladas fueron tocadas por outcomes previos, y con qué
métricas. Un `FAIL` o un `PASS` futuro de Puerta 1 sobre esas 11 sesiones ahora se lee
con la exposición delante, en vez de heredarla en silencio. Y queda separado lo que abre
esta campaña —nada— de lo que el proyecto ya tenía abierto, que es la distinción que un
`OUTCOMES_NOT_OPENED` global habría borrado.

## Nota de método

El hallazgo salió del Paso 0 de otra tarea: verificar que el worktree estuviera limpio
antes de lanzar el sweep. Los archivos llevaban ahí desde el día anterior y ninguna de
las corridas previas de la jornada los había mirado, porque `git status` con `??` es
fácil de leer como ruido. La lección operativa no es «revisar untracked»: es que **un
worktree sucio es un hallazgo, no un preámbulo** — y que el `mtime` común al segundo,
que fue lo que delató la copia en bloque, sólo estaba disponible porque el inventario se
hizo **antes** de mover nada.
