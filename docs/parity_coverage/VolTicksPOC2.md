# Cobertura de paridad — VolTicksPOC2

Oráculos pre-registrados: **O1 default (CloseThrough)**, **O2 FirstTouch**
(`invalidation_mode=FirstTouch`). Especificación en
`../nt8_indicator_parity_contract.md` §6.

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `baseline_window` | avg_period | O1 | pendiente |
| `ratio_window` | ratio_window_bars, min_ratio_samples | O1 | pendiente |
| `export_floor` | export_floor_percentile | O1 | pendiente |
| `detection_cut` | detection_percentile | O1 | pendiente |
| `geometry` | price_mark_ticks | O1 | pendiente |
| `lifecycle_invalidation` | invalidation_mode | O1 (CloseThrough), O2 (FirstTouch) | pendiente |
| `lifecycle_max_touches` | max_touches | O2 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |

Requisito de historia (contrato §5): ≥ `avg_period` barras + ≥ `min_ratio_samples`
ratios antes de detectar.
