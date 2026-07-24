# Cobertura de paridad — aVolCellPOI2

Oráculos pre-registrados: **O1 SessionRelative/TotalVolume/Quantile** (default),
**O2 WallClock/AbsDelta** (`bucket_anchor=WallClock`, `detection_source=AbsDelta`).
Especificación en `../nt8_indicator_parity_contract.md` §6.

**Requisito de historia** (contrato §5): con `min_sessions=15` y
`lookback_sessions=20` el chart NT8 necesita **≥ 35 sesiones ≈ 7 semanas**
cargadas antes del rango a comparar. Los `.cs` deben ser rev **190ed59+**
(footprint reconstruido 1-tick; los generados con Volumetric nativo NO valen).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `bucket_anchor` | bucket_anchor | O1 (SessionRelative), O2 (WallClock) | pendiente |
| `bucket_size` | time_bucket_minutes | O1 | pendiente |
| `lookback` | lookback_sessions | O1 | pendiente |
| `weighting` | profile_weighting | O1 | pendiente |
| `detection_source` | detection_source | O1 (TotalVolume), O2 (AbsDelta) | pendiente |
| `detection_method` | detection_method | O1 (Quantile) | pendiente |
| `export_floor` | export_floor_percentile | O1 | pendiente |
| `quantile_cut` | detection_percentile | O1 | pendiente |
| `robustz_cut` | robust_z_threshold | (RobustLogZ, sin oráculo mínimo — variante futura) | pendiente |
| `min_vol` | min_absolute_volume | O1 | pendiente |
| `profile_gate` | min_sessions, min_cell_samples | O1 | pendiente |
| `geometry_merge` | merge_gap_ticks | O1 | pendiente |
| `geometry_min_cells` | min_zone_cells | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode | O1 | pendiente |
| `lifecycle_max_touches` | max_touches | O1 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |

`detection_method=RobustLogZ` (rama `detection_method` camino alterno) y
`robustz_cut` no están en la campaña mínima: una config que los use queda
`parity_pending` hasta pre-registrar un tercer oráculo RobustLogZ.
