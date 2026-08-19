# Diagnóstico v2 del store — HFTZonesRange

- **2026-08-19** · reemplaza `hftzones_calib_catalog.json` (`19e8713`, **SUPERSEDED**)
- Artefactos: `hftzones_diagnostico_v2.json` · **`hftzones_diagnostico_v2_1.json`** (vector completo del sampler + procedencia corregida)
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

### 1.b El eje temporal **no** es enteramente constante

| | 6E | 6J | ES | GC | NQ | **YM** | ZB |
|---|---|---|---|---|---|---|---|
| `eff_max_avg_ms` | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `eff_max_total_ms` | 16 | 16 | 16 | 16 | 16 | 16 | 16 |
| **`eff_max_pausa_ms`** | 5 | 5 | 5 | 5 | 5 | **20** | 5 |

**Conclusión precisa:** los umbrales derivados de `q2`/`q5`/`q15` **colapsan** contra su
piso `max(1, …)`; el umbral de **pausa**, derivado de `p50`, **conserva adaptación
parcial en YM** (20 ms contra 5). Decir que «todo el eje temporal es constante» era
demasiado amplio.

## 2. Integridad: limpia

**0 `dt` negativos** y **0 sesiones no monótonas** sobre 1.793 sesiones. El filtro del
kernel (`0 <= ms <= …`) y el que usaba el calibrador (`ms <= …`) coinciden **en estos
datos** — pero eso había que medirlo, no suponerlo.

## 3. Muestra completa vs sampler — **NO son idénticos: NQ discrepa**

v2 declaró `identicos = true` comparando **sólo** `eff_max_avg_ms` y
`eff_min_total_vol` — **justamente los dos campos saturados por sus pisos**, que
coinciden casi por construcción. No miraba `eff_max_pausa_ms`, ni `p50`, ni
`resolution_limited`: precisamente donde YM conserva variación.

**v2.1 compara los 10 campos, y aparece la discrepancia** (`hftzones_diagnostico_v2_1.json`):

| campo | 6E | 6J | ES | GC | **NQ** | YM | ZB |
|---|---|---|---|---|---|---|---|
| `eff_predator/ultra/max_avg/max_total` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `eff_min_total_vol` · `eff_min_vol_rate` · `_median_vol` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **`_p50_ms`** | 0 | 0 | 0 | 0 | **4** | 0 | 0 |
| **`eff_max_pausa_ms`** | 0 | 0 | 0 | 0 | **15** | 0 | 0 |
| **sesiones con `resolution_limited` distinto** | 0 | 0 | 0 | 0 | **2** | 0 | 0 |

**En 2 de 263 sesiones de NQ (0,76 %), la decimación cambia `p50` hasta 4 ms, mueve
`eff_max_pausa_ms` hasta 15 ms, y llega a invertir el flag `resolution_limited`.**

**Consecuencia, con la corrección del auditor.** `resolution_limited` **no gobierna
ninguna rama del motor**: se calcula (`hftzones2.py` l. 248) y sólo se emite en el log
de `CALIBRATION` (l. 258). Mi frase «es un flag que decide comportamiento» era falsa.

Lo que **sí** puede cambiar comportamiento es **`eff_max_pausa_ms`**: el motor corta una
racha cuando `ms > eff["max_pausa"]` (l. 397). En esas 2 sesiones de NQ la decimación
mueve ese umbral hasta 15 ms, o sea **puede cambiar dónde termina una racha**.
`resolution_limited` también se invierte, pero hoy es diagnóstico.

**Y la conclusión operativa:** para reproducir el indicador vivo, el catálogo offline
debe usar **el mismo sampler**. La muestra completa queda como **análisis de
sensibilidad**, no como configuración canónica.

**Y no es «más decimación, más divergencia».** ES tiene el stride más agresivo
(4, con 182.654 muestras de 922.342 ticks) y **cero** discrepancias; NQ tiene stride 2 y
sí discrepa. Lo que importa es que NQ tiene sesiones con `p50` justo en la frontera
`0 / no-0`, y la decimación la cruza.

| | 6E | 6J | ES | GC | NQ | YM | ZB |
|---|---|---|---|---|---|---|---|
| stride mediano | 1 | 1 | **4** | 1 | 2 | 1 | 1 |
| muestra / total | 57k/57k | 44k/44k | 183k/**922k** | 116k/116k | 191k/464k | 72k/72k | 106k/106k |

**Lo que v2 probó realmente:** los dos umbrales saturados coinciden. **Lo que v2.1
prueba:** los otros ocho campos coinciden en 6 de 7 instrumentos, y **NQ no**. La
afirmación «es la misma calibración» queda **retirada**.

*Límite declarado:* el artefacto registra **cuántas** sesiones discrepan, no en qué
dirección (si el sampler declara `limited` donde la muestra completa no, o al revés).
Se puede agregar si hace falta.

## 4. Timestamps repetidos: la escala del problema

| inst | 6E | 6J | ES | GC | **NQ** | YM | ZB |
|---|---|---|---|---|---|---|---|
| máx trades con el mismo ts | 246 | 319 | 739 | 334 | **14.837** | 1.697 | 1.714 |
| `dt = 0` (mediana) | 65 % | 69 % | 80 % | 48 % | 52 % | 41 % | 86 % |

**14.837 trades de NQ comparten un mismo timestamp.** Entre el 41 % y el 86 % de los
intervalos son exactamente 0.

**Acotado (auditor).** Eso afecta a los **cuantiles bajos** (`q2`, `q5`, `q15`) y a lo
que deriva de ellos —`eff_max_avg` y `eff_max_total`—, que quedan contra su piso. **No
afecta por igual a `eff_max_pausa`**, que deriva de `p50` y sí adapta en YM. Decir
«cualquier medida de velocidad» era demasiado amplio.

## 5. Volumen: lo degenerado es **la fórmula**, no la distribución

`frac(volume == 1)` va de **67 % (ZB, 6J)** a **96 % (NQ, YM)**; `q99` va de **3**
(NQ, YM) a **37** (ZB).

**Conclusión acotada:** `3 × mediana(volume) × 8` no discrimina **porque la mediana
queda en 1 en todos**. Eso **no demuestra** que otros estadísticos de volumen tampoco
discriminen — la distribución sí cambia entre instrumentos, y decir «separa poco» sin
una prueba adicional sería afirmar de más.

**Y los dos «pisos» no son equivalentes**: el de tiempo es un piso **explícito de
código** (`max(1, q15)`); el de volumen es una **masa empírica en la unidad mínima**, no
un `max()`. La invariancia ante el cambio de segmentación es un **resultado observado en
esta corrida**, no una propiedad del método.

## 6. Altura: variación cross-asset visible, pero **adaptación parcial y saturada**

| inst | `sweep` | sesiones pegadas a `H_FLOOR` |
|---|---|---|
| 6E · 6J · ZB | 2 | **100 %** |
| ES | 2 | 83 % |
| **YM** | **3** | **37 %** |
| GC | 5 | 9 % |
| NQ | **9** | **0 %** |

**Redacción corregida (auditor, 2026-08-19).** La altura es el único eje con variación
cross-asset visible, pero su adaptación es **parcial y está saturada en parte del
universo**. La configuración mediana forma **cuatro grupos**: 2 para 6E/6J/ES/ZB, 3 para
YM, 5 para GC y 9 para NQ. **No distingue** 6E, 6J, ES y ZB por su valor final;
6E/6J/ZB están pegados al piso en **todas** las sesiones, mientras que **YM, GC y NQ sí
quedan mayoritariamente por encima**.

> **Retracto mi propia corrección anterior.** Después de publicar esto escribí que la
> altura «separa sólo GC y NQ». Es falso y **el propio artefacto lo contradice**: YM
> está en el piso en el 37 % de sus sesiones, o sea **mayoritariamente por encima**.
> Me pasé primero por exceso y después por defecto sobre el mismo número.

## 7. Diff viejo → v2

`eff_max_avg_ms` y `eff_min_total_vol` dan **igual** (1,00 y 24,0) pese al cambio de
segmentación. Los valores no se movieron; **lo que cambió es que ahora se sabe qué
significan** y sobre qué sesiones se calcularon.

## 8. Lo que sigue abierto — y no es mío

Con `q15 = 0` en los siete y hasta 14.837 trades por timestamp, **los umbrales
derivados de cuantiles bajos** (`eff_max_avg`, `eff_max_total`) no discriminan. **El de
pausa sí adapta parcialmente** (YM: 20 ms contra 5). Tres caminos para esa parte, y
ninguno se resuelve bajando un cuantil:

1. **Aceptarlo** y declarar la compuerta desactivada.
2. **Ventanas muy superiores a la resolución** (100 ms, 1 s) o **event-time** en vez de
   tiempo de reloj. *Corrección aceptada del auditor: «ticks por unidad de tiempo no
   depende del reloj» es **falso** — toda velocidad depende del reloj; lo que se puede
   hacer es elegir una escala donde la resolución no domine.*
3. **Timestamps con resolución real**, que toca el frente de datos.

Y una consecuencia de nombre: **si el reloj no alcanza, tampoco corresponde llamarlo
detector «HFT»**.

## 9. Nota de método

**Corregido.** `medicion_comprometida = false` **no** significa árbol limpio: significa
que no hay archivos sucios **dentro del alcance declarado** (`edgelab/`, `diag/`). Esta
misma corrida tenía `archivos_sucios: ["viewer/hz2a/grafico.js"]` con el flag en
`false` — o sea que la nota original del artefacto **se contradecía con el campo de al
lado**. Ahora el artefacto declara su alcance y lista también los no trackeados.

Y sigue valiendo lo otro: tampoco significa que la medición sea metodológicamente
válida. El catálogo viejo lo tenía en `false` y estaba mal segmentado.
