# HFTZonesRange — spec (2026-08-19)

- **Estado:** `SPEC_WRITTEN_NOT_IMPLEMENTED` · **Alimenta P-48**, no abre un `P-NN` nuevo
- **Origen:** `docs/research/HFTZONES_ES_RANGE_ADAPTATIVO_2026-08-19.md`
- **No es F4.** Sin MAE/MFE, sin P&L, sin holdout.
- **`HFTZones2` NO se parcha.** Queda intacto para la paridad vieja (P-43).

> Nico prefiere `HFTZonesESPureV2` (rango entero) a `HFTZones2` (filo de 1 tick).
> Esta spec toma **el objeto del ES** y **la ingeniería de HFTZones2**.

---

## 1. El objeto: la zona es el rango transado

```
zona = [swL, swH]          el intervalo donde corrió la racha
```

No `[swL − 1, swL]` ni un filo de 1 tick sobre `swH`. Ahí estuvo la subasta; el
origen es sólo dónde empezó.

`HFTZones2` con `zone_height_ticks = 1` **no tiene un bug**: dibuja lo que declara. Es
otro objeto. Por eso esto es un indicador nuevo y no un parche.

Precios en **ticks enteros** siempre — se hereda de `HFTZones2`, y es lo que permite
comparar sin float.

## 2. ABSORB: ocupación, no altura corta

Hoy **los dos** indicadores dicen `absorb` si `height < MinSweepTicks`. Eso no es
absorción: **es una racha corta**. Una racha de 3 ticks sin volumen y una de 3 ticks
con 4.000 contratos son el mismo evento para ese criterio, y no son el mismo evento.

**Definición nueva**, con lo que el ES ya calcula y no usa:

```
occ = no_move_vol / total_vol            ocupación: volumen que NO movió el precio
absorb  ⟺  occ ≥ eff_absorb_occ   Y   |Δp| ≤ MinSweepTicks
```

Las **dos** condiciones. Mucho volumen sin avance es absorción; poco avance a secas es
una racha que no llegó.

`eff_absorb_occ` es **calibrado** (§4). **Si no hay historia de rachas, `absorb` va
apagado hasta tener N.** Sin fallback lindo.

> **Sin DOM no hay icebergs.** Esto mide **ocupación de nivel**, que es un proxy. La
> palabra «iceberg» no aparece en la salida. Y `tick-rule` clasifica el agresor al
> **76–81 %** (Lee–Ready; Chakrabarty et al.): CVD es un proxy de flujo, no «la
> institución». Se publica como *feature*, nunca como semáforo.

## 3. Merge: dos rachas que se pisan son una zona

Sin esto, cualquier umbral adaptable vuelve a llenar el chart — que es exactamente el
síntoma que Nico vio.

```
merge(A, B)  ⟺  mismo lado
             Y  [swL_A, swH_A] ∩ [swL_B, swH_B] ≠ ∅
             Y  t_inicio_B − t_fin_A  <  MERGE_GAP_MS

zona resultante = [min(swL), max(swH)],  pasos y volumen sumados,
                  occ recomputada sobre los totales
```

**`MERGE_GAP_MS = 500`, estructural y fijo.** No se tunea. El anclaje es la escala de
duración de **una** racha: `HFTZones2` ya declara `manual_max_total_ms = 500` como el
techo de una racha completa. Dos rachas separadas por menos que la duración de una
racha, y solapadas en precio, son el mismo evento de subasta.

## 4. Escalas congeladas: adaptar es congelar, no elegir mirando

**Todo lo calibrado se congela al cierre de una sesión y rige la SIGUIENTE.** Nunca la
propia. Es la regla anti look-ahead que `HFTZones2` ya tiene.

### 4.1 Lo que se hereda igual de `HFTZones2` (mismas fórmulas, sin tocar)

Muestras: `ms` = intervalos inter-tick con **pausas afuera**
(`pause_exclude_ms = 1000`); `vol` = volumen por tick.

```
eff_pred          = max(1, Q(ms, 0.02))
eff_ultra         = max(eff_pred,  Q(ms, 0.05))
eff_max_avg       = max(eff_ultra, Q(ms, 0.15))
eff_max_pausa     = min(5000, max(eff_max_avg, 5.0 × max(1, Q(ms, 0.50))))
eff_max_total     = eff_max_avg × MinPasos × 2.0
eff_min_total_vol = 3.0 × Q(vol, 0.50) × MinPasos
eff_min_vol_rate  = eff_min_total_vol / (eff_max_total / 1000)
```

**El volumen va en múltiplos de la mediana del tick, no en 200 contratos.** Por eso MES
(1/10 de ES) y 6E no comparten umbral.

### 4.2 Lo nuevo: altura en ticks **del activo**

`5 ticks de ES ≠ 5 ticks de 6J ≠ 5 ticks de YM`. La altura mínima de barrido deja de
ser una constante:

```
h1s  = high−low, en ticks enteros, por bucket de 1 s NO solapado, buckets vacíos afuera
eff_min_sweep_ticks = max(H_FLOOR, round(Q(h1s, 0.90)))
```

- **`H_FLOOR = 2`** — estructural. Con 1 tick, cualquier movimiento es un «barrido».
- **`Q_HEIGHT = 0.90`** — un barrido tiene que ser **más alto que la excursión ordinaria
  de un segundo**, así que el piso vive en la cola alta de los rangos de 1 s.
  **Se declara acá, antes de correr nada, y no se mueve mirando densidad de zonas.**

### 4.3 Lo nuevo: ocupación

```
eff_absorb_occ = Q(occ_historico, 0.80)      sobre rachas de la sesión previa
```

Requiere historia de rachas. **Sin ella, `absorb` apagado.** `Q_OCC = 0.80` se declara
acá por la misma razón que `Q_HEIGHT`.

### 4.4 Lo que NO se calibra nunca

`MinPasos` · `FallosTolerados` · `MERGE_GAP_MS` · `H_FLOOR` · la definición de zona, de
absorb y de merge.

**Son la hipótesis.** Moverlos mirando cuántas zonas salen es elegir el umbral después
del dibujo — el mismo pecado que P-47, y por eso está prohibido acá por escrito.

## 5. Primera sesión: `CALIBRATION_PENDING`

Sin calibración congelada **no se crean zonas**. Se emite un evento
`CALIBRATION_PENDING` una vez y se espera. **Sin fallback lindo.**

Recalibración sólo con `len(ms) ≥ 100`, `len(vol) ≥ 100` y `seen ≥ MinCalibSamples`; si
no alcanza, se mantiene la calibración previa o se sigue pendiente. Igual que
`HFTZones2`.

Cada calibración emite un evento `CALIBRATION` con **todos** los `eff_*`, replicable
1:1 en numpy.

## 6. Semilla offline: el catálogo por contrato

`diag/tasa_senales/hftzones_calibrar.py` corre **las mismas fórmulas** sobre el store de
ticks (holdout afuera) y escribe `docs/research/hftzones_calib_catalog.json`:

```
instrument → { eff_*, n_sesiones, dispersión, head_commit, asof, holdout_included:false }
```

El indicador **puede leer el catálogo como semilla**; si no está, espera una sesión.
**Nunca inventa.**

## 7. Ingeniería heredada de `HFTZones2` (y lo que no)

**Sí:** grilla de ticks enteros · no arrancar en plano ni `isDown`-first · calibración
congelada · **CSV de eventos** · dibujo sólo en la barra primaria · expiración
(`close_through` + `MaxAgeBars`) · `CALIBRATION` auditable.

**No:** SQLite dentro del indicador · rutas tipo `C:\LoggerHFT\` · MAE/MFE · cualquier
outcome.

## 8. Cómo se refutaría

- Las zonas siguen saliendo igual de densas con merge y con `absorb` por ocupación → el
  problema no era el criterio, era la definición de racha.
- `eff_min_sweep_ticks` sale casi igual en instrumentos de escala muy distinta → el
  cuantil de 1 s no captura la escala y hay que revisarlo.
- `occ` no separa nada: su distribución es la misma en rachas que siguen y en las que
  no → la ocupación no es informativa **sin DOM**, y hay que decirlo.
- El catálogo offline y la calibración en vivo del indicador **no coinciden** → hay dos
  implementaciones de la misma fórmula, que es lo que esta spec existe para evitar.

## 9. Justificación económica

`HFTZones2` como soporte/resistencia ya fue refutado (~96 % de ruptura), y BigTrap2
igual. **Esta spec no promete que el rango transado funcione mejor.** Lo que cambia es
que el objeto medido pasa a ser el intervalo donde hubo subasta en vez de un filo, que
es lo que Nico observa en el chart — y sin eso ni siquiera se puede testear su
observación.

**Aporte al referente:** adaptar es congelar escalas del activo. Elegir umbrales
mirando el dibujo no es calibrar.


---

# Resultado del catálogo offline — 2026-08-19

`docs/research/hftzones_calib_catalog.json` · 7 instrumentos, 289–331 sesiones cada uno.

| inst | `eff_min_sweep_ticks` | p25–p75 | `eff_max_avg_ms` | `eff_min_total_vol` | `resolution_limited` |
|---|---|---|---|---|---|
| 6E | **2** | 2–2 | 1,00 | 24,0 | **True** |
| 6J | **2** | 2–2 | 1,00 | 24,0 | **True** |
| ES | **2** | 2–2 | 1,00 | 24,0 | **True** |
| ZB | **2** | 2–2 | 1,00 | 24,0 | **True** |
| YM | 3 | 2–3 | 1,00 | 24,0 | **True** |
| GC | 5 | 4–6 | 1,00 | 24,0 | **True** |
| NQ | **9** | 7–11 | 1,00 | 24,0 | **True** |

## Los dos ejes heredados NO adaptan nada

**`eff_max_avg_ms = 1,00` en los siete.** `resolution_limited = True` en todos: la
mediana del intervalo inter-tick es **0 ms**, así que los tres cuantiles de velocidad
colapsan contra el piso `max(1.0, …)`. El kernel ya declara esta condición — lo nuevo
es su consecuencia: **la compuerta de velocidad queda en «≤ 1 ms» para todo, que es lo
contrario de adaptarse.**

**`eff_min_total_vol = 24,0` en los siete**, porque la mediana de volumen por tick es
**1 contrato** en todos: `3,0 × 1 × 8 = 24`. El multiplicador de mediana no discrimina
cuando la mediana es la unidad mínima en todos lados.

## El único eje que adapta es el nuevo

`eff_min_sweep_ticks` va de **2 (6E, 6J, ES, ZB)** a **9 (NQ)**, con p25–p75 que no se
pisan entre NQ (7–11) y el resto. Es exactamente lo que la observación *«5 ticks de ES
≠ 5 ticks de 6J»* predecía, y es lo único que separa instrumentos en este store.

**El piso `H_FLOOR = 2` liga en 4 de 7.** `Q(h1s, 0,90) ≤ 2` para 6E, 6J, ES y ZB.

## Lo que NO se hace con esto

**No se mueve `Q_HEIGHT` para que los otros se separen.** Está declarado en §4.2 de
esta misma spec, escrita antes de correr el calibrador. Bajarlo ahora porque el
resultado «quedó chato» es elegir el umbral después de ver el número — literalmente la
prohibición de §4.4.

**Tampoco se toca la fórmula de velocidad.** Que `resolution_limited` sea universal es
un hecho **del store**, no del criterio: los timestamps de estos parquets no separan
por debajo del milisegundo (concuerda con P-28, donde `sequence` resultó ser índice de
fila y no secuencia del exchange).

## La pregunta que queda abierta, para Nico y el auditor

Si la velocidad no discrimina en este store, hay tres caminos y **ninguno es mío**:

1. **Aceptarlo**: la compuerta de velocidad queda efectivamente desactivada y el
   indicador se apoya en altura + volumen. Declararlo, no disimularlo.
2. **Cambiar la unidad**: medir velocidad en **ticks por unidad de tiempo** en vez de
   ms entre ticks, que no depende de la resolución del timestamp.
3. **Conseguir timestamps con resolución real**, que toca el frente de datos y no el
   del indicador.

Es una decisión de definición, igual que P-45. **No se resuelve bajando un cuantil.**
