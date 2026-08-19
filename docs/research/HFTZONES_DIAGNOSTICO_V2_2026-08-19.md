# Diagnóstico v2 del store — HFTZonesRange

- **2026-08-19** · reemplaza `hftzones_calib_catalog.json` (`19e8713`, **SUPERSEDED**)
- Artefacto: `docs/research/hftzones_diagnostico_v2.json`
- **HFTZonesRange congelado**: no se tocó `Q_HEIGHT`, `H_FLOOR`, `MinPasos` ni ningún
  umbral. El indicador **no** se implementó.

---

## 0. La corrección que más pesó: la segmentación de sesiones

El calibrador agrupaba con `(t + 7 h) // día` → cortes a las **17:00 UTC**. La sesión
CME abre 17:00 **CT** = 22:00 UTC en DST, 23:00 fuera. Cortaba 5–6 h antes **e ignoraba
el DST**, con `sessions_cme.trade_date_ymd` disponible en el repo.

**No era cosmético.** El conteo de sesiones cambia en todos:

| | 6E | 6J | ES | GC | NQ | YM | ZB |
|---|---|---|---|---|---|---|---|
| viejo | 307 | 293 | 331 | 306 | 318 | 293 | 289 |
| **v2** | **260** | **253** | **276** | **255** | **263** | **244** | **242** |

## 1. El `any()` escondía un gradiente — y YM confirma la predicción del auditor

| inst | limited | | p50 ms | q15 |
|---|---|---|---|---|
| 6E · 6J · ZB | 260/260 · 253/253 · 242/242 | **100 %** | 0,00 | 0,00 |
| ES | 273/276 | 99 % | 0,00 | 0,00 |
| GC | 236/255 | 93 % | 0,00 | 0,00 |
| NQ | 226/263 | 86 % | 0,00 | 0,00 |
| **YM** | **115/244** | **47 %** | **4,00** | 0,00 |

El auditor predijo `p50 ≈ 4 ms` para YM despejando `eff_max_pausa = 5 × max(1, p50)`
desde el catálogo viejo. **Da 4,00 exacto.**

Mi afirmación —«la mediana inter-tick es 0 ms en los siete»— era falsa: **YM tiene más
de la mitad de sus sesiones con resolución utilizable.**

**Y `eff_max_avg` colapsa por `q15`, no por `p50`.** `q15 = 0,00` en los siete, así que
`max(1, …)` lo fija en 1 ms **incluso en YM**, donde `p50 = 4`. La causa del «1,00
universal» estaba en el cuantil 15, no en la mediana.

## 2. Integridad: limpia

**0 `dt` negativos** y **0 sesiones no monótonas** sobre 1.793 sesiones. El filtro del
kernel (`0 <= ms <= …`) y el que usaba el calibrador (`ms <= …`) coinciden **en estos
datos** — pero eso había que medirlo, no suponerlo.

## 3. Muestra completa vs sampler del kernel: idénticos en los 7

`dif_max_avg_ms_max = 0` y `dif_min_total_vol_max = 0` en todos. La decimación por
stride no cambia estos cuantiles en este store. Ahora **sí** se puede decir «la misma
calibración», porque se comparó.

## 4. Timestamps repetidos: la escala del problema

| inst | 6E | 6J | ES | GC | **NQ** | YM | ZB |
|---|---|---|---|---|---|---|---|
| máx trades con el mismo ts | 246 | 319 | 739 | 334 | **14.837** | 1.697 | 1.714 |
| `dt = 0` (mediana) | 65 % | 69 % | 80 % | 48 % | 52 % | 41 % | 86 % |

**14.837 trades de NQ comparten un mismo timestamp.** Entre el 41 % y el 86 % de los
intervalos son exactamente 0. Cualquier medida de velocidad sobre este reloj está
midiendo la resolución del registro, no el mercado.

## 5. Volumen: la estadística es degenerada

`frac(volume == 1)` va de **67 % (ZB, 6J)** a **96 % (NQ, YM)**, y los cuantiles altos
separan poco: `q99` va de 3 (NQ, YM) a 37 (ZB).

Que la impresión mediana sea 1 contrato en todos los futuros **es plausible** — el flujo
viene fragmentado. El error fue esperar que `3 × mediana × 8` distinguiera instrumentos:
el tamaño contractual de ES o 6E no implica que su **impresión** mediana difiera. Los
siete dan 24 y **no es un error de cálculo: es una estadística que no sirve para este
fin.**

## 6. Altura: el único eje que separa, con su letra chica

| inst | `sweep` | sesiones pegadas a `H_FLOOR` |
|---|---|---|
| 6E · 6J · ZB | 2 | **100 %** |
| ES | 2 | 83 % |
| YM | 3 | 37 % |
| GC | 5 | 9 % |
| NQ | **9** | **0 %** |

Sólo **GC y NQ** están genuinamente por encima del piso. En 6E, 6J y ZB el valor es
`H_FLOOR` en **todas** las sesiones: el eje no está midiendo la escala del activo, está
devolviendo la constante. **Eso no se arregla bajando `Q_HEIGHT`** — sería elegir el
umbral después de ver el resultado.

## 7. Diff viejo → v2

`eff_max_avg_ms` y `eff_min_total_vol` dan **igual** (1,00 y 24,0) pese al cambio de
segmentación. Los valores no se movieron; **lo que cambió es que ahora se sabe qué
significan** y sobre qué sesiones se calcularon.

## 8. Lo que sigue abierto — y no es mío

Con `q15 = 0` en los siete y hasta 14.837 trades por timestamp, la compuerta de
velocidad no discrimina. Tres caminos, y ninguno se resuelve bajando un cuantil:

1. **Aceptarlo** y declarar la compuerta desactivada.
2. **Ventanas muy superiores a la resolución** (100 ms, 1 s) o **event-time** en vez de
   tiempo de reloj. *Corrección aceptada del auditor: «ticks por unidad de tiempo no
   depende del reloj» es **falso** — toda velocidad depende del reloj; lo que se puede
   hacer es elegir una escala donde la resolución no domine.*
3. **Timestamps con resolución real**, que toca el frente de datos.

Y una consecuencia de nombre: **si el reloj no alcanza, tampoco corresponde llamarlo
detector «HFT»**.

## 9. Nota de método

`medicion_comprometida = false` significa **árbol de trabajo limpio**. No significa que
la medición sea metodológicamente válida — el catálogo viejo lo tenía en `false` y
estaba mal segmentado. El artefacto v2 lo dice en su propia procedencia.
