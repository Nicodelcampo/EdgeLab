# Hipótesis pendientes

Observaciones con forma testeable que todavía no tienen campaña. No son
resultados: son cosas que alguien vio y que vale la pena medir cuando toque.

---

## HP-001 — Burst de zonas HFT al cierre, en **ES**

**Fecha**: 2026-08-04 · **Origen**: observación visual de Nico ·
**Estado**: registrada, sin medir · **Instrumento**: ES (no 6E)

Nico observa que al cierre del mercado aparecen muchas zonas HFT en ES, y
sospecha que de ahí puede salir un edge.

**Pospuesta a propósito**: el foco actual es 6E. No se mide todavía.

### Lo que sí se midió (y no aplica)

Se corrió el kernel `HFTZones2` sobre **6E 09-26**, 4 sesiones
(2026-06-15 → 06-18), 1.775 zonas, contadas por hora CT (cierre 16:00 CT):

| hora CT | 7–10 | 13 | 14 | 15 | 17–23 |
|---|---:|---:|---:|---:|---:|
| zonas | 32,4 % | 16,2 % | 13,4 % | **2,5 %** | **6,0 %** |

En 6E las zonas se concentran en las horas de máxima liquidez, no al cierre —
lo contrario a la observación. **Pero esto no refuta HP-001**: otro instrumento
y, en la observación original, otro indicador (`HFTZonesESPureV2`).

### Cómo medirla cuando se retome

1. Parquet canónico F2 de ES (no existe todavía; hoy solo hay 6E).
2. Correr `HFTZones2` v2.3, contar `created_ms` por hora CT — mismo
   procedimiento que arriba, que ya está probado.
3. Comparar contra la distribución de volumen por hora: si las zonas siguen al
   volumen, no hay nada específico del cierre.

### Precondición que puede invalidarla antes de empezar

En 6E la **mediana del intervalo entre ticks es 0 ms durante toda la sesión**
⇒ `Q(0.50)=0` ⇒ `resolution_limited=1` por el gate P0 del propio indicador: los
buckets de velocidad (PREDATOR/ULTRA/FAST) **no son confiables** porque se
clasifican por `avg_ms` y el feed no tiene esa resolución.

**Hay que verificar esto en ES antes de interpretar cualquier zona HFT.** Si ES
también da `resolution_limited=1`, la clasificación por velocidad no significa
nada y HP-001 habría que replantearla sobre volumen/rango en vez de timing.

*(`HFTZonesESPureV2` no tiene este gate ni ningún otro control de resolución, y
clasificaría todo como PREDATOR sin avisar. Ver la comparación de indicadores en
el reporte del 2026-08-04.)*


---

## HP-002 — `VolTicksDef` — **NO agregar.** Es un mecanismo que ya está dos veces

**Fecha:** 2026-08-06 · **Origen:** propuesta de Nico · **Estado:** evaluado, no adoptado

Marca velas con volumen excepcionalmente alto (ratio vs media móvil, umbral por
percentil). **Es la misma construcción que `VolTicksPOC2`**, que se describe a sí
mismo como *«ratio vs baseline → detección por percentil empírico»*.

### Y los existentes ya resolvieron sus dos defectos

**1. La barra entra en su propio promedio.** `rollingVolumeSum += Volume[0]`
(línea 215) y después `ratio = Volume[0] / avg` (223): una barra enorme **infla
su propio denominador**. `VolTicksPOC2` declara lo contrario — *«baseline = media
de `Volume[1..AvgPeriod]` EXCLUYENDO la barra actual»*.

**2. La barra entra en su propio umbral.** `quantileGlobal.Add(ratio)` (226) se
ejecuta **antes** de `GetActiveThreshold()` (229). `VolTicksPOC2`: *«Las ventanas
se actualizan DESPUÉS de la comparación»*. `aVolCellPOI2`: *«La sesión actual
nunca entra al perfil contra el que se compara (anti look-ahead)»*.

Los dos sesgos van en la misma dirección: **subestiman lo excepcional**.

### Y aunque se arreglaran

Sin ciclo de vida (`ZONE_CREATED`/`TOUCHED`, `zone_id`, `touch_count`) y **sin
EventLog**: no hay oráculo de paridad posible sin construirle el camino entero.
Sería además la **tercera** variante de anomalía de volumen, y §3.3 pide
mecánicamente distintas — *«no tres variantes de zonas de volumen, que inflan
M_eff sin diversificar»*.

### Lo que sí vale, y no es un indicador

**El estimador P²**: cuantil por streaming con memoria **O(1)** —cinco
marcadores, sin guardar la muestra— y reset por sesión. `VolTicksPOC2` usa una
ventana de ratios: más memoria y más frágil con ventanas largas.

> **El aporte real no es un indicador nuevo: es un mejor estimador para uno que
> ya existe.** Candidato a mejora de `VolTicksPOC2`, o a filtro en la **capa de
> estrategia**, donde no cuesta ningún oráculo.

---

## HP-003 — `aVolClusterPOI` v0.4 — **sí vale, con dos condiciones**

**Fecha:** 2026-08-06 · **Origen:** propuesta de Nico · **Estado:** evaluado,
pospuesto por F9

A diferencia de HP-002, **éste no repite un mecanismo existente**: detecta por
**masa de cluster** —niveles «hot» contiguos agrupados, comparados contra el
perfil histórico del mismo bucket horario— y agrega **ráfaga** (tasa de
formación) como señal de segundo orden. Su propio encabezado lo sitúa como
complemento de `aVolCellPOI2`, no como reemplazo. Eso **sí** es mecánicamente
distinto en el sentido de §3.3.

### Está escrito CONTRA los contratos del proyecto, no de espaldas

| exigencia | estado |
|---|---|
| `OnBarClose`, `non_repainting`, la barra creadora no toca su zona | declarado **e implementado** (`if (z.CreatedBar >= CurrentBar) continue`) |
| ticks enteros, cero ULP | declarado, citando **AUDIT-002** y `tools/ulp_exposure.py` |
| `footprint=reconstructed_1tick_subseries` | sí — mismo contrato que BigTrap2 |
| cuantil empírico **sin interpolar** | sí |
| perfil de sesiones **anteriores** completas | sí — la actual acumula aparte |
| EventLog con `# meta`, `zone_id`, `touch_count`, `bar_index` | **sí, completo** |
| una corrida por archivo | `write_mode=overwrite`, *«nunca append»* — ataca P6 de frente |
| orden intrabar indemostrable | **`AMBIGUOUS`**: *«si target y stop ocurren en la misma barra, no inventa el orden»* |

Ese último punto es la misma disciplina que se acaba de implementar en el
extractor tick-based. **Llega con el contrato de eventos que a cuatro
indicadores hubo que agregarles.**

### La observación de Nico sobre la subserie es la parte más valiosa

`AddDataSeries(BarsPeriodType.Tick, 1)` en `State.Configure`: el footprint se
reconstruye **igual en cualquier chart**. El bloque son `WindowBars` barras
**primarias**, así que **la resolución primaria es un parámetro libre** — cambia
lo que abarca un bloque sin tocar la exactitud del footprint.

Es exactamente la forma del barrido de resolución de §2-ter (`10, 15, 25, 50,
100` + `time:1` como control). **Un eje de búsqueda que ya está construido.**

### Condición 1 — emite OUTCOMES, y eso lo inhabilita para el censo

`ZONE_OUTCOME` con `outcome`, `mfe_ticks`, `mae_ticks` —TARGET/STOP/TIMEOUT/
AMBIGUOUS— es una **evaluación forward del precio después de la entrada**, y
viaja en las columnas del CSV.

> **Su EventLog NO puede consumirse tal cual por ningún censo outcome-free.**
> Declarar `outcomes_accessed: false` leyendo ese archivo entero sería falso.

Se resuelve de dos formas, y hay que elegir **antes**: un modo de export que
emita sólo columnas target-free, o un lector probadamente ciego a esas columnas
—probado, no prometido—.

### Condición 2 — el `QualityScore` es una preselección escondida

Los pesos `35/25/15/15/10` son fijos y arbitrarios. Como fórmula congelada es una
elección de hipótesis tomada antes de medir. O los pesos entran a la grilla como
parámetros, o el score se publica **descompuesto** y no se usa para filtrar.

Su default ya ayuda: `EnablePredictiveFilter = false`.

### Estado

**F9 sigue pausada**, y el propio encabezado coincide: *«PROTOTIPO DE
INVESTIGACIÓN. No tiene kernel Python ni paridad. No usar sus zonas para operar
hasta pasar el pipeline estándar»*.

Cuando F9 se reabra, **éste es el primer candidato** — es el único que llega con
el contrato de eventos, la disciplina anti look-ahead y un eje de resolución ya
construido.


---

## HP-004 — `aVolZonePOI` — **NO. Ya está superado, y una de sus fallas es descalificante**

**Fecha:** 2026-08-06 · **Estado:** evaluado, descartado

Es el **predecesor** de HP-003: `aVolClusterPOI` se declara *«reescritura desde
cero de `aVolZonePOI.cs` rescatando sus dos ideas útiles»*. Su encabezado lista
cinco cosas que le eliminó. **Verificadas una por una en el fuente, no aceptadas
por palabra del sucesor:**

| # | lo que el sucesor dice que eliminó | verificado en `aVolZonePOI.cs` |
|---|---|---|
| 1 | SQLite y «mitigación» por proceso externo | **sí** — `using System.Data.SQLite` (23); línea 136: cada 30 s en tiempo real llama `CheckAndRemoveMitigatedZones()` |
| 2 | precios `double` como clave de diccionario | **sí** — `Dictionary<double, double>` en 33, 56, 95, 103 |
| 3 | fallback a cola global mezclando horas | **sí** — `Queue<double> globalQueue` (35), usado en 283 |
| 4 | bloques anclados al punto de carga del chart | **sí** — cero apariciones de `IsFirstBarOfSession` o `SessionIterator` |
| 5 | percentil con interpolación lineal | **sí** — `sorted[lo] + (rank-lo)*(sorted[hi]-sorted[lo])` (452) |

### La primera es descalificante por sí sola

```csharp
// línea 135-139
// Check for mitigated zones in SQLite every 30 seconds (real-time only)
if (State == State.Realtime && (DateTime.UtcNow - lastMitigationCheck).TotalSeconds >= 30)
{
    CheckAndRemoveMitigatedZones();
    ...
}
```

**El conjunto de zonas en una barra depende de lo que un proceso externo escribió
en una base de datos, consultado por reloj de pared.** Eso no es un defecto de
precisión: es **irreproducible por construcción**. No se puede repetir la corrida
y obtener lo mismo, porque el estado no vive en el indicador.

G0 exige lo contrario, literal: *«re-ejecutar la campaña con el mismo manifiesto
produce los mismos digests»*. Ningún indicador que consulte un proceso externo
por reloj puede satisfacer eso, con cualquier cantidad de trabajo de traducción.

### Las otras cuatro, en el orden en que importan acá

- **`Dictionary<double, double>`** es la familia de bugs ULP de **AUDIT-002**: dos
  precios que deberían ser la misma celda pueden diferir en el último bit y
  fabricar dos claves. El sucesor usa ticks enteros y declara «exposición ULP = 0
  por construcción».
- **El fallback global** mezcla horas cuando falta historia del bucket, y
  reintroduce el sesgo de estacionalidad intradiaria que el perfil por bucket
  existe para eliminar. El sucesor prefiere **no detectar**: *«sin historial del
  bucket ⇒ no detecta»*. Fail-closed contra fail-open.
- **Sin anclaje a sesión**, los bloques dependen de dónde arrancó el chart: dos
  personas con la misma configuración ven zonas distintas.
- **La interpolación** del percentil inventa un valor que no está en la muestra.
  Los tres kernels del proyecto usan cuantil empírico **sin interpolar**.

### Veredicto

**No hay nada que rescatar que HP-003 no haya rescatado ya**, y lo hizo
explicitando qué tiraba y por qué. Lo útil de este archivo es servir de **control
negativo documentado**: cinco decisiones de diseño que el proyecto ya rechazó,
con el fuente al lado para mostrar cómo se ven cuando están mal.

---

## HP-006 — ZB L2 order book + ML: imbalance/OFI de baseline, DeepLOB-family de challenger

**Fecha:** 2026-08-31 · **Origen:** propuesta de Nico (chat Notion AI) · **Estado:** registrada, data gate pendiente · **Instrumento:** ZB

*(HP-005 queda reservada para el diseño GC SL/TP/BE — ver §14 de
`BT2A_GC_SLTP_BREAKEVEN_DESIGN_V1_2026-08-30.md` en
`research/bt2a-gc-sltp-breakeven-design-v1-20260830`.)*

Nico plantea que para ZB conviene L2 y que, si obtiene el dato, quiere empezar
a entrenar (DeepLOB / redes). El análisis lo respalda como el mejor paciente
del universo para señal de libro: tick más grueso del proyecto ($31,25),
colas persistentes, libro de rates profundo y lento. Diseño completo con
research de mejores prácticas, fases con puertas y refutaciones pre-escritas:
`docs/research/HP006_ZB_L2_ORDERBOOK_ML_V1_2026-08-31.md`.

Reglas cardinales asentadas: baseline (queue imbalance + OFI, Gould & Bonart /
Kolm et al.) antes que cualquier red; challenger de arquitectura simple
(MLPLOB) antes que DeepLOB (TLOB 2025: el MLP supera al SoTA); normalización
fit-en-train; la métrica de veredicto es expectativa neta por sesión, nunca
accuracy (LOBFrame); entrenar con etiquetas = acceso a outcomes = spec + token
propios; el L2 de ES cuarentenado (P-56/P-57) no se toca.
