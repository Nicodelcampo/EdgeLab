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
