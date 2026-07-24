# Cobertura de paridad — HFTZones2

Oráculos pre-registrados: **O1 adaptativo** (default), **O2 manual**
(`adaptive_mode=false`). Especificación en
`../nt8_indicator_parity_contract.md` §6. El rango DEBE arrancar en borde de
sesión con ≥1 sesión completa previa (calibración congelada); feriados →
`CALIBRATION_DIFF` (WARN).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `calibration_mode` | adaptive_mode | O1 (adaptive), O2 (manual) | pendiente |
| `calibration_adaptive` | q_predator, q_ultra, q_max_avg, pause_mult, total_ms_mult, vol_mult_median_tick, pause_exclude_ms, min_calib_samples, calib_sample_cap | O1 | pendiente |
| `calibration_manual` | manual_predator_ms … manual_min_total_vol | O2 | pendiente |
| `streak_structure` | min_pasos, min_absorb_pasos, detect_absorb, fallos_tolerados | O1 | pendiente |
| `sweep_vs_absorb` | min_sweep_ticks | O1 | pendiente |
| `retro` | use_relative_retro, retro_floor_ticks, retro_pct_height | O1 | pendiente |
| `geometry` | zone_height_ticks | O1 | pendiente |
| `export_floor` | min_export_valid_steps | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode, penetration_ticks | O1 | pendiente |
| `lifecycle_max_touches` | max_touches | O1 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |
| `touch_logging` | max_logged_touches | O1 | pendiente |

O1 cubre la calibración adaptativa; O2 cubre el camino manual (que O1 nunca
ejercita, `adaptive_mode` distinto).
