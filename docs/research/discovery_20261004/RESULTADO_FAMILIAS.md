# Resultado del barrido pre-registrado por familias (15 combinaciones)

Pre-registro: `PREREGISTRO_FAMILIAS.md` (commit `39d0b78b`, antes de correr). Motor CPU (referencia), nulo de máximo con signos por sesión, 20.000 sorteos, D0 = primera mitad cronológica, D1 = réplica, **D2 sellado** (no se leyó), nada desde 2026-10-01. Archivos crudos en `resultados/`; contador (`trial_registry.jsonl`) y libro (`funnel_ledger.jsonl`) con 15 asientos cada uno.

## Veredicto
**Ninguna de las 15 combinaciones (familia × grupo) pasa a confirmación.** El punto (i) de la regla (Holm al 5 % sobre los 15 `p_max`) falla en todas; el menor p ajustado es 0,112.

| Grupo | Familia | Celdas probadas (D0) | máx \|z\| real | cuantil 95 % del nulo | `p_max` | Holm sobre 15 |
|---|---|---:|---:|---:|---:|---:|
| GC | f1_momentum | 2.884 | 4,11 | 3,80 | **0,0074** | 0,112 |
| GC | f2_vwap | 2.996 | 3,37 | 3,79 | 0,359 | 1 |
| GC | f3_flujo_absorcion | 8.288 | 4,11 | 3,92 | 0,0145 | 0,188 |
| GC | f4_regimen | 6.248 | 4,11 | 3,88 | 0,0127 | 0,178 |
| GC | f5_medias | 9.760 | 4,11 | 3,91 | 0,0146 | 0,188 |
| ZB | f1_momentum | 1.943 | 3,41 | 3,77 | 0,263 | 1 |
| ZB | f2_vwap | 2.219 | 3,32 | 3,79 | 0,396 | 1 |
| ZB | f3_flujo_absorcion | 5.471 | 3,64 | 3,88 | 0,179 | 1 |
| ZB | f4_regimen | 3.816 | 3,41 | 3,86 | 0,379 | 1 |
| ZB | f5_medias | 6.673 | 3,58 | 3,88 | 0,244 | 1 |
| FX (6E+6J) | f1_momentum | 3.937 | 3,39 | 3,89 | 0,409 | 1 |
| FX | f2_vwap | 4.101 | 3,23 | 3,89 | 0,647 | 1 |
| FX | f3_flujo_absorcion | 14.598 | 3,49 | 4,04 | 0,608 | 1 |
| FX | f4_regimen | 6.537 | 3,39 | 3,97 | 0,549 | 1 |
| FX | f5_medias | 12.607 | 3,73 | 4,01 | 0,209 | 1 |

BH sobre los p normales de las celdas: 0 celdas con q < 0,05 en las 15 combinaciones (exploración).

## Lo que aparece en GC
- Las cuatro familias de GC con `p_max` bajo (f1, f3, f4, f5) tienen **la misma celda ganadora**: franja 04:30 CT, **largo** tras una caída de 15 minutos (`mom_15 < 0`), holding 15 minutos, z = 4,11 en D0 (136 operaciones sobre las 225 sesiones, +13,6 ticks netos de media, que incluyen D1). No son cuatro hallazgos: es uno solo contado cuatro veces (las familias comparten la condición `mom`).
- **No replica en D1:** z = −0,30 (p = 0,61, 30 operaciones). La señal vive en D0.
- Esta es la combinación sobre la que ya se había declarado una filtración parcial (la calibración contaminada mostró estructura en f1/GC). Se corrió igual y falla la corrección entre combinaciones (Holm 0,112) y la réplica.
- La celda de la etapa anterior (04:15 CT, corto tras alza, 15 min) no apareció como titular. Era esperable: potencia ≈ 0,15 a 0,3 desvíos por debajo de lo detectable en D0 con esta rejilla.

## Réplicas en D1 con p de Holm ≤ 0,05 (descriptivo)
| Combinación | Celda | z en D0 | z en D1 (signo fijo) | p Holm |
|---|---|---:|---:|---:|
| GC f1 (y f3, misma celda) | 19:30 CT, hold 15, `mom_15 < 0`, largo | 3,25 | 2,35 | 0,036 |
| FX f1 | 12:45 CT, hold 15, `mom_60 > 0`, corto | −3,14 | 2,57 en la dirección elegida | 0,011 |

Ninguna tenía significación en D0 tras el nulo de máximo (`p_max` 0,0074 en GC con otra celda como máximo; 0,41 en FX), así que por la regla fijada no cuentan. Con 15 combinaciones × 5 celdas replicadas, ver 1 o 2 réplicas con p ≤ 0,05 en D1 es compatible con el azar (esperado ≈ 0,75 por combinación independiente al 5 %, sin ajustar entre combinaciones). **No son candidatas a edge**; si se quisieran seguir, cada una exigiría un pre-registro nuevo y datos posteriores.

## Otras lecturas
- ZB y FX: nada distinguible del azar en ninguna familia. Titulares con media neta ≈ 0 o negativa en ticks (ZB f1: −0,10; FX 6J mayormente negativo).
- Ninguna celda de ZB o FX se acerca al cuantil 95 % del nulo.
- Coherente con la expectativa pre-registrada: «la mayoría de las 15 combinaciones salga sin nada».

## Qué se concluye y qué no
- Con estos datos (225, 211 y 232 sesiones; D0 de ≈ 105 a 116) **no hay estructura distinguible del azar** en las cinco familias de variables (momentum, VWAP, flujo/absorción, régimen, medias).
- No se prueba ausencia de edge: la potencia en D0 es baja por debajo de ≈ 0,5 desvíos por operación (ver calibración).
- El efecto de GC a las 04:30 no es un hallazgo: no replica y no pasa la corrección entre combinaciones.
- D2 sigue sellado y el holdout formal sigue sin abrirse.
