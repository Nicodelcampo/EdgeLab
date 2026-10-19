# Landscape target-free — **51/51 OAT completo**, GC 02-26

- **Fecha:** 2026-08-24 · **Rama:** `fix/sweep-finalize-contract-scope`
- **Corrida:** `bt2a_sweep_20260824_7953443_gc0226` · parciales bajo `7953443`, uniformes
- **Status:** `COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS` · `promotion_eligible=false`
- **Alcance:** 51 configs · **1 de 4 contratos** · 39 sesiones reportables · etapa `oat`
- **Firewall:** `CAMPAIGN_OUTCOMES_OPENED=false` · **nada declara edge**

> **Las 48 interacciones NO se corrieron** (`--stage oat`). Esto es el barrido de un eje
> por vez.

---

## 1. El resultado estructural: **tres familias, no dos**

El censo no encontró «parámetros que importan y parámetros que no». Encontró tres clases
con semántica distinta:

| familia | qué cambia | ejes |
|---|---|---|
| **creación** | cuántas zonas existen | `TapeWindowTicks` `MinStackedRows` `MinDeltaFilter` `AbsorptionPct` `ImbalanceRatio` `WickZonePct` `TicksPerRow` `MinTrapVolume` `MinTrapFrac` `ScoreMode` `UseWickFilter` `ImbalanceMode` `TrapVolumeSource` `AbsorptionLookback` `RequireFlowSideMatch` |
| **ciclo de vida** | **las mismas zonas, distinta vida** | `MaxAgeBars` `MaxTouches` `InvalidationMode` |
| **no-op real** | nada | `DrawZoneBand` `MinExportVolume` `MinHistoryBuckets` |

### 1.1 La familia de ciclo de vida es invisible al conteo de zonas

Los tres actúan **después** de crear la zona, así que `n_zones` no los ve. Medirlos por
conteo daría «no-op» y sería falso:

| eje | valor | zonas | invalidadas | expiradas | activas | **touches** |
|---|---|---:|---:|---:|---:|---:|
| *(headline)* | — | 3.878 | 3.790 | 88 | 0 | **9.448** |
| `InvalidationMode` | `None` | 3.878 | **0** | 3.866 | 12 | **223.720** |
| `MaxTouches` | 1 | 3.878 | 3.844 | 34 | 0 | 3.831 |
| `MaxAgeBars` | 0 | 3.878 | 3.873 | 0 | 5 | 9.639 |

`InvalidationMode=None` multiplica los touches por **23,7×**. Las zonas son las mismas;
viven muchísimo más.

> **El campo `identical_to_headline_oat_axes` acertó y yo no.** Marcó exactamente tres
> ejes. Yo había contado doce mirando `n_zones` y jaccard, que no distinguen creación de
> ciclo de vida. El `target_free_fingerprint` incluye los contadores de ciclo, así que
> separa las dos cosas.

---

## 2. Sensibilidad por eje — ordenado por magnitud

| eje | valor | zonas | Δ% | jaccard |
|---|---|---:|---:|---:|
| `MinStackedRows` | 1 | 8.680 | **+123,8 %** | 0,447 |
| `MinDeltaFilter` | 50 · 100 | **0** | **−100 %** | 0,000 |
| `MinTrapVolume` | 100 | 5 | −99,9 % | 0,001 |
| `TapeWindowTicks` | 5 | 12 | −99,7 % | 0,000 |
| `MinStackedRows` | 4 | 16 | −99,6 % | 0,004 |
| `TicksPerRow` | 4 | 129 | −96,7 % | 0,000 |
| `WickZonePct` | 10 | 181 | −95,3 % | 0,029 |
| `AbsorptionPct` | 80 | 6.599 | +70,2 % | 0,588 |
| `ScoreMode` | `AbsDirectional` | 6.274 | +61,8 % | 0,356 |
| `ImbalanceRatio` | 2 | 6.167 | +59,0 % | 0,507 |
| `UseWickFilter` | `False` | 6.157 | +58,8 % | 0,357 |
| `ImbalanceMode` | `SameLevel` | 4.534 | +16,9 % | 0,778 |
| `RequireFlowSideMatch` | `False` | 3.973 | +2,4 % | 0,976 |
| `TrapVolumeSource` | `TotalLevel` | 3.888 | +0,3 % | 0,997 |
| `AbsorptionLookback` | 200 · 1000 | 3.914 · 3.828 | ±1,1 % | 0,86–0,91 |

### 2.1 Dos acantilados

**`MinDeltaFilter` en 50 o 100 mata la población entera: 0 zonas.** No es sensibilidad
alta, es un interruptor. El headline lo tiene en 0, o sea apagado.

**`MinStackedRows`** es el eje más brusco en las dos direcciones: `1 → +124 %`,
`3 → −88 %`, `4 → −99,6 %`. Y cambia la geometría: con 1, `zone_rows_p50` cae de 2 a 1 y
el ancho de 2 ticks a 1.

---

## 3. El hallazgo que más importa: **solapamiento ≠ redundancia**

`specs/bt2_absorption_target_free_sweep_v1.json` lleva escrito
`"event overlap is descriptive; it is not an effective test count"`, con prohibición de
derivar número efectivo de tests del jaccard. **Ahora hay evidencia:**

```
TapeWindowTicks = 50   ->  -29,3 % de zonas   pero jaccard 0,035
TapeWindowTicks = 15   ->  -44,4 % de zonas   pero jaccard 0,023
AbsorptionPct   = 85   ->  +36,0 % de zonas   y   jaccard 0,735
```

Cambios de conteo **comparables** producen solapamientos que difieren en **un orden de
magnitud**. `TapeWindowTicks=50` conserva el 70 % de las zonas y sin embargo comparte
**3,5 %** de los eventos: son casi disjuntos.

**Razón:** cambiar el tamaño de cubeta reparticiona el tiempo, así que ninguna zona cae
en el mismo instante. Cambiar un umbral percentil conserva la partición y sólo filtra.

> Dos ejes que mueven la población lo mismo pueden ser **casi el mismo test** o **dos
> tests distintos**. El conteo no lo dice. El jaccard tampoco, en la otra dirección: alto
> solapamiento no prueba redundancia.

---

## 4. Geometría — notablemente rígida

`zone_rows_p50 = 2` y `zone_width_ticks_p50 = 2` en **casi todas** las configuraciones.
Sólo tres ejes la mueven:

- `MinStackedRows` — por construcción, es el mínimo de filas.
- `TicksPerRow` — `2 → ancho 4`, `4 → ancho 8`. Escala lineal, esperable.
- `TapeWindowTicks=100` — `rows_p50 = 3`.

El resto cambia **cuántas** zonas hay, no **cómo son**.

---

## 5. Lo que NO se puede leer de acá

- **Ningún ganador.** No se miraron outcomes y no se pueden mirar.
- **Un solo contrato.** GC 02-26, 39 sesiones reportables de las 133.
- **Sin interacciones.** Las 48 configs de cruce no se corrieron.
- **Nada justifica el headline.** Que `TW=25` esté en un máximo de población no dice que
  sea correcto para nada.
- **`promotion_eligible=false`** por subconjunto de contratos.

---

## 6. Procedencia

```
parciales          51/51, todos code_commit 7953443, uniforme
1a agregacion      INVALID_PROVENANCE  (commits en la rama durante la corrida)
2a agregacion      COMPLETE_TARGET_FREE_PARTIAL_CONTRACTS  desde worktree en 7953443
recomputo          CERO configs
```

El guardrail se negó a emitir un resultado con procedencia mezclada. La recuperación fue
correr desde el commit que coincide con los parciales — **no** relajar el chequeo.

---

## Aporte al referente

El censo contesta la pregunta que lo motivó —qué parámetros mueven la población— y
devuelve una que nadie había formulado: **hay una familia entera de parámetros que el
conteo de zonas no puede ver.** `MaxAgeBars`, `MaxTouches` e `InvalidationMode` actúan
después de la creación, y medirlos con la métrica equivocada los habría archivado como
no-op cuando uno de ellos multiplica los touches por 23,7×.

## Nota de método

Conté doce no-op mirando `n_zones` y jaccard. El campo `identical_to_headline_oat_axes`
del runner marcó tres. **Tenía razón el campo.** La diferencia es que su
`target_free_fingerprint` incluye los contadores de ciclo de vida y mi lectura no.

Lo anoto porque el error tiene una forma reconocible: elegí la métrica más visible
—cuántas zonas hay— y la traté como si midiera todo el objeto. Nueve de los doce
«no-op» que declaré cambiaban el comportamiento de manera sustancial en una dimensión
que yo no estaba mirando.
