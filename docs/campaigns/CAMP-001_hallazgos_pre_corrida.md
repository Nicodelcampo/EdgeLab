# CAMP-001 — Hallazgos del dry run, PREVIOS a la corrida

**Fecha:** 2026-07-25 · **Estado:** requiere decisión de Nico antes de correr.
El manifiesto v1.0 está **sellado e inmutable**: nada de acá lo modifica. Si Nico
decide corregir, se hace por **enmienda versionada aprobada ANTES de correr**.

Todo lo medido acá es **target-free**: frecuencias de zonas e interacciones
precio-zona. **No se miró ningún retorno ni P&L.** El STOP sigue vigente.

## 1. La etiqueta de config en E1 es imprecisa, pero NO es material ✅

E1 dice haber calibrado sobre "la partición de la config de campaña
(`d1289a36`)", mientras el runner usa `a6c32c0e9dbeb79a` (§4). Son configs
distintos: difieren **solo** en `min_gap_ticks` (5 vs 2), con
`export_floor_ticks=2` en ambos.

Verificado empíricamente, restringiendo a la ventana común:

```
d1289a36 : 2130 zonas   (ventana 2025-08-01 00:00 -> 20:59)
a6c32c0e : 2130 zonas   (misma ventana)
geometria + created_ms IDENTICA: True
```

`min_gap_ticks` es **display-only** (gobierna el flag `display`, no la
exportación), que es exactamente la razón por la que está declarado
coverage-neutral en §8.3 del contrato de paridad. **La calibración de E1 se hizo
sobre el conjunto de zonas correcto.** Solo la etiqueta está mal escrita.

## 2. La tabla numérica de E1 sobreestima entre 5× y 10× ⚠️ BLOQUEANTE

E1 calibró sobre **un solo día**, el 2025-08-01, y extrapoló linealmente. Ese día
tuvo **2.130 zonas**; los promedios reales por fold son mucho menores:

| Fold | zonas | días op. | zonas/día | `≥5 ticks` | `≥5`/día |
|---|---:|---:|---:|---:|---:|
| 6E 09-25 | 21.375 | 45 | 475 | 597 | 13,3 |
| 6E 12-25 | 19.975 | 79 | 253 | 466 | 5,9 |
| 6E 03-26 | 30.634 | 79 | 388 | 674 | 8,5 |
| 6E 06-26 | 25.474 | 79 | 322 | 308 | 3,9 |

**2025-08-01 fue un día atípico, 4–8× más activo que la media.** Comparación de
lo que E1 declaró contra lo medido sobre las 4 particiones completas:

| Filtro | E1 (extrapolado) | Real (4 folds) | Factor |
|---|---:|---:|---:|
| `zone_min_size ≥ 2` | ~494.000 | **97.458** | 5,1× |
| `zone_min_size ≥ 3` | ~86.000 | **9.801** | 8,8× |
| `zone_min_size ≥ 5` | ~20.000 | **2.045** | 9,8× |

## 3. Qué sobrevive y qué no

**Sobrevive el umbral operativo.** Los 48 configs superan el mínimo de 50 de E1:
el más ralo (F4, `zone_min_size=5`) da **344 disparos agregados**. El gate de E1
se cumple y **no hace falta relajarlo**.

**No sobrevive la justificación de E1.** E1 argumenta textualmente:

> La restricción binding NO es la escasez de señales sino la regla de una sola
> posición simultánea […] o sea **≥ ~1.160 trades en desarrollo para cualquier
> celda** […] Por lo tanto **50 no cuesta poder estadístico**.

Los disparos son **cota superior** de los trades (la regla de una posición solo
puede reducirlos). La celda más rala tiene **≤ 344 trades**, no ≥ 1.160. Es
decir: **para las celdas `zone_min_size = 5` la restricción binding SÍ es la
escasez de señales**, exactamente lo contrario de lo que afirma E1.

Consecuencias concretas, por fold (los folds se evalúan por separado en el
walk-forward de G2):

| config más ralo | 09-25 | 12-25 | 03-26 | 06-26 | agregado |
|---|---:|---:|---:|---:|---:|
| F4, `zmin=5` | 84 | 75 | 108 | 77 | 344 |
| F3, `zmin=5` | 94 | 80 | 111 | 73 | 358 |

Con 73–108 disparos por fold — y eso siendo **cota superior** — las 12 celdas con
`zone_min_size=5` quedan cerca del umbral de promoción de G1
(`n_trades ≥ 100`), y podrían caer por debajo una vez aplicada la regla de una
posición simultánea.

## 4. Qué NO se hizo

- **No se relajó ningún umbral.** E1 sigue en 50, G1 sigue en 100.
- **No se tocó el manifiesto sellado.**
- **No se eligió ninguna corrección.** La decisión es de Nico.

## 5. Opciones para Nico (sin recomendación aplicada)

- **(i) Correr igual.** El gate de E1 se cumple. Se acepta que las 12 celdas
  `zmin=5` son de baja potencia y probablemente fallen G1 por `n_trades` — lo
  cual es **informativo y se registra**, tal como E1 ya previó para el caso
  50–99 ("dice que la familia es demasiado rala").
- **(ii) Enmienda E6 pre-corrida**: corregir la tabla de calibración de E1 con
  los números reales medidos acá y re-derivar la justificación del umbral, sin
  cambiar el umbral 50. Es una corrección de **hecho**, no de criterio.
- **(iii) Enmienda E6 alternativa**: sacar `zone_min_size=5` de la grilla por
  baja potencia, bajando N_eff de 48 a 32. **Ojo**: cambia la corrección por
  múltiples pruebas, así que debe decidirse **antes** de correr y quedar
  registrado — sacarlo después de ver resultados sería data snooping.

Cualquiera de las tres es legítima **solo porque se decide antes de correr** y
sin haber mirado un solo retorno.
