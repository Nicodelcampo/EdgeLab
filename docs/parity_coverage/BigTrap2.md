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
