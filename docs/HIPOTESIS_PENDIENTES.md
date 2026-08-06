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
