# Cobertura de paridad — BigTrap2

Oráculos pre-registrados: **O1 Diagonal/time:1** (default), **O2 SameLevel/tick:25**
(`imbalance_mode=SameLevel`, `--bars tick:25`), **O3 wick off**
(`use_wick_filter=false`). Especificación en
`../nt8_indicator_parity_contract.md` §6. Formato pipe; cada resolución de barra
es un oráculo distinto (el `--bars tick:N` debe coincidir con el chart NT8).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `row_anchor` | ticks_per_row | O1 | pendiente |
| `imbalance_detection` | imbalance_mode, imbalance_ratio | O1 (Diagonal), O2 (SameLevel) | pendiente |
| `trap_volume` | trap_volume_source | O1 | pendiente |
| `wick_filter` | use_wick_filter, wick_zone_pct | O1 (on), O3 (off) | pendiente |
| `delta_filter` | min_delta_filter | O1 | pendiente |
| `export_floor` | min_export_volume | O1 | pendiente |
| `trap_selection` | min_trap_volume | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode | O1 | pendiente |
| `lifecycle_max_touches` | max_touches | O1 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |

Nota: O1 y O3 corren en `time:1`; O2 en `tick:25` — el bar_key entra al
`config_id`, así que O2 cubre además el camino de reconstrucción sobre barras de
tick.

## Resultado del primer oráculo real (2026-07-24) — **FAIL, causa raíz en el `.cs`**

Oráculo: `oracles/BigTrap2_diag_tick25_6E_0926.csv` (Diagonal, **25 Tick**, 6E
09-26, defaults; combinación no pre-registrada en §7 del contrato — se agrega
acá como O4). Ventana comparada: 2026-07-13T22:00 → 07-16T21:00 UTC.

**Gate P2: FAIL.** Python 324 zonas vs NT8 620 (matched 129, MISSING_IN_PYTHON
391, MISSING_IN_NT8 95, GEOMETRY_DIFF 48).

### Causa raíz: el footprint reconstruido de NT8 está corrupto en charts de TICK

El propio indicador lo denuncia: **26.661 `FOOTPRINT_MISMATCH` sobre 29.916
barras = 89% de las barras**. Comparando barra a barra los eventos `TRAP` (que
exportan `fp_vol` y `bar_vol`):

| barra NT8 | `fp_vol` NT8 | `bar_vol` NT8 | `fp_vol` Python | `bar_vol` Python |
|---|---|---|---|---|
| 7384 | **150** | 50 | 50 | 50 |
| 7471 | **344** | 62 | 62 | 62 |
| 7417 | 34 | 36 | 36 | 36 |

- **Python es exacto por construcción**: `bars.build_footprints` particiona los
  ticks por `tick_bar_idx`, así que `fp_vol == bar_vol` siempre (gate P1A PASS,
  0 mismatches en las 9.195 barras de la ventana).
- **NT8 acumula ticks de varias barras en una**: el `take+reset` del pending
  ocurre en `OnBarUpdate(BarsInProgress==0)`, pero en datos históricos de un
  chart de tick la subserie de 1 tick (BIP1) se entrega **desfasada/en lotes**
  respecto de la serie primaria (BIP0). Resultado: unas barras quedan cortas y
  otras absorben el lote (hasta 5,5× su volumen real). El volumen total se
  conserva (suma global desviada solo 0,94%), lo que confirma **mala asignación
  entre barras**, no pérdida de datos.
- Es la versión amplificada del caveat ya declarado en la guía §11 ("ticks con
  timestamp igual al cierre pueden fugarse a la barra siguiente"): en un chart
  de **25 ticks cada frontera de barra ES una frontera de tick**, así que el
  desfase ocurre en casi todas las barras, no ocasionalmente.
- Consecuencia: NT8 detecta imbalances sobre volúmenes por fila que no
  corresponden a esa barra ⇒ crea ~2× las zonas que Python. **La discrepancia no
  es del kernel Python.**

Verificación de alineación de barras (descarta otra hipótesis): el offset de
numeración NT8→Python es **constante = 7377** en toda la ventana (762 barras
coincidentes), o sea que **las barras de 25 ticks están perfectamente alineadas**
entre ambos lados. El problema es el CONTENIDO del footprint, no el corte.

### Implicación para los demás oráculos

El patrón `AddDataSeries(Tick,1)` + take/reset es el mismo en **VolTicksPOC2** y
**aVolCellPOI2** (y en el `aVolCellPOI2.cs` reescrito). Todo oráculo de estos
kernels sobre charts de **TICK** hereda el riesgo. Sobre charts de **TIEMPO** el
cierre de barra no coincide con un tick, así que se espera una tasa de mismatch
mucho menor — es exactamente lo que mide el oráculo O1 (Diagonal/`time:1`) ya
pre-registrado, y es el próximo experimento decisivo.

**No se relaja el gate ni se amplían tolerancias**: FAIL queda registrado.

## O1 (Diagonal / `time:1`, 2026-07-24) — hipótesis del footprint CONFIRMADA, pero **FAIL por una segunda causa**

Oráculo: `oracles/BigTrap2_diag_time1_6E_0926.csv`, sha256
`698eac589c7c4f3e7c717ea8766ed4396d97c566198d5df955482b5f0f270e92`, defaults,
corrida única (0 resets de `seq`). Misma ventana: 2026-07-13T22:00 → 07-16T21:00
UTC. Comparación por el árbol de decisión pre-registrado por Nico.

### 1) El footprint sobre charts de TIEMPO es sano — hipótesis confirmada

| chart | `FOOTPRINT_MISMATCH` | barras | tasa |
|---|---|---|---|
| 25 Tick (O4) | 26.661 | 29.916 | **89,12 %** |
| 1 Minute (O1) | 4 | 15.939 | **0,03 %** |

Factor ~3.000×. Queda demostrado que la corrupción del footprint de NT8 es
**específica de charts de tick**, tal como predecía la sección anterior.

### 2) Segunda causa raíz: artefacto de **1 ULP** en la comparación del `.cs`

El gate sigue en **FAIL** (rama (b) del árbol: *mismatch bajo + FAIL ⇒ hay un
segundo bug que el ruido del footprint tapaba*). Resultado:

```
py_zones 226 | nt8_zones 257 | matched 225
MATCHED 224 · GEOMETRY_DIFF 1 · FEATURE_DIFF 1 · MATURITY_TAIL 6
MISSING_IN_NT8 1 · MISSING_IN_PYTHON 32
```

Comparando los eventos `TRAP` barra a barra (offset de numeración NT8→Python
constante = **4048**): **549 TRAPs comunes, 548 idénticos en `(vol, n_rows)`**.
Los sobrantes tienen una firma exacta, no ruidosa:

- **101 TRAPs solo-NT8, el 100 % `trapped_buyers` con `n_rows=1`.** Cero
  `trapped_sellers` sobrantes (Python acierta 304/304 sellers).
- En los 101, `close − centroid = 0,0 ticks` **exacto**. En los 245 buyers
  comunes es siempre negativo (−1…−6) y en los 304 sellers siempre positivo
  (+1…+6). Es decir: **el único caso que difiere es el empate `row_price == close`**.

Los operadores son **idénticos** en ambos lados (`.cs` L349/L361 y
`bigtrap2.py`: `row_price > close` / `row_price < close`, ambos estrictos). La
discrepancia no es de regla sino de **aritmética**:

| | expresión | `double` |
|---|---|---|
| `close` (NT8) | `Close[0]` del feed | `0x1.240ebedfa43fe p+0` = `1.14085` |
| `rowPrice` (NT8) | `RowCenterPrice(r, rowTicks)` = `r * tickSize` | `0x1.240ebedfa43ff p+0` = `1.1408500000000001` |

Difieren en **1 ULP** (2,22e-16 ≈ 4,4e-12 ticks). El error de redondeo de
`r * tickSize` es **sistemáticamente hacia arriba** en esta magnitud de precio:
de los 101 empates, **101 dan `rowPrice > close` y 0 dan `<`** — por eso el
sesgo es puramente hacia `trapped_buyers` y nunca hacia `sellers`.

Python compara dos valores construidos **ambos** desde la grilla entera de ticks
(`close_t * tick_size` vs `r * row_ticks * tick_size`), así que el empate le da
bit-exacto y lo descarta de los dos lados, que es el comportamiento
aritméticamente correcto.

### 3) Los 34 diffs residuales se explican por esa única causa

| diff | n | explicación |
|---|---|---|
| `MISSING_IN_PYTHON` | 32 | **32/32** son zonas nacidas de los 101 TRAPs del artefacto (solo 32 superan `min_trap_volume`) |
| `GEOMETRY_DIFF` | 1 | zona `py 567_B / nt8 4615_B`: NT8 arma 2 filas y Python 1; la fila extra está a **+0 ticks del close** y `22853*5e-05 > close` da `True`. Mismo artefacto |
| `FEATURE_DIFF` | 1 | **misma zona**: `touches` 3 vs 2, consecuencia de que la zona quede 1 tick más alta |
| `MISSING_IN_NT8` | 1 | **no es discrepancia de kernel**: TRAP de Python con `ts == W1` exacto, excluido por el filtro semiabierto `[W0, W1)` del lado NT8. NT8 sí lo generó (su bar 8081) |
| `MATURITY_TAIL` | 6 | regla de frontera de madurez ya pre-registrada (§4) |

Un síntoma directo del mismo fenómeno queda visible en el propio export de esa
zona: `close` vale `1.14265` en NT8 y `1.1426500000000002` en Python.

### 4) Veredicto y decisión PENDIENTE de Nico

**Gate P2 sobre O1: FAIL. No se relaja ninguna tolerancia** (`tol_geom_ticks=0`,
`tol_created_ms=60000` intactos) ni se toca la semántica del matcher.

Resolver esto **cambia la semántica de validación**, así que por la regla
permanente queda **frenado y elevado a Nico**. Opciones, sin recomendación
aplicada:

- **(A) Corregir el `.cs`** para comparar sobre la grilla entera de ticks
  (`rowTick > closeTick`, enteros). Deja a NT8 aritméticamente correcto y alinea
  con Python. Requiere recompilar y **regenerar todos los oráculos** de BigTrap2.
- **(B) Reproducir el artefacto en Python.** Daría PASS, pero **propaga un bug de
  punto flotante al research**: las 32 zonas afectadas son económicamente vacías
  (una fila *en* el close no es agresión compradora que quedó *por encima* del
  close), y el sesgo depende de la magnitud del precio, así que no es estable
  entre instrumentos.
- **(C) Declarar el empate explícitamente** en el contrato (p. ej. `>=` o `>` por
  decisión pre-registrada) y fijar **ambos** lados a esa regla sobre enteros.

Impacto para dimensionar la decisión: **32 de 257 zonas NT8 en la ventana
(12,5 %)** existen solo por el artefacto.

