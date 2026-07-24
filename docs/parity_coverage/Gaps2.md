# Cobertura de paridad — Gaps2

Oráculos pre-registrados: **O1 default**, **O2 min_gap denso**
(`min_gap_ticks=3, export_floor_ticks=2`). Contrato/rango en
`../nt8_indicator_parity_contract.md` §1 (O1, ya pre-registrado) y §6 (O2).

| Rama | Params | Cubierta por | Estado |
|---|---|---|---|
| `gap_detection` | export_floor_ticks | O1, O2 (floor bajo, más gaps) | pendiente |
| `gap_display` | min_gap_ticks | O2 (min_gap denso) | pendiente |
| `session_gap` | reopen_pause_minutes, reopen_warmup_minutes | O1 | pendiente |
| `atr_feature` | atr_period | O1 | pendiente |
| `vol_baseline` | vol_baseline_ticks, min_vol_baseline_samples | O1 | pendiente |
| `lifecycle_partial` | partial_fill_pct | O1 | pendiente |
| `lifecycle_invalidation` | reversal_confirm_ticks | O1 (rct=2), O2 | pendiente |
| `expiration` | max_age_bars | O1 | pendiente |
| `touch_logging` | max_logged_touches | O1 | pendiente |

`parity_covered` de una config Gaps2 = todas estas ramas con oráculo PASS.
