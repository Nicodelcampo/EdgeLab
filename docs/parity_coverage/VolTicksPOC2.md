# Cobertura de paridad — VolTicksPOC2

## ✅ PARIDAD AFIRMADA — 2026-07-27

| | |
|---|---|
| oráculo | `oracles/VolTicksPOC2_6E_0926_warmup.csv` |
| resultado | **PASS — 23 / 23, 0 diffs** |
| tolerancias | **intactas** |

**Sin necesitar la regla de ventana llena.** Con warmup real —la ventana de datos
desde 2026-06-12 en vez de recortada a la de comparación— las 23 zonas coinciden
exactamente. La regla de ventana llena queda como **salvaguarda declarada**, no
como muleta para conseguir un PASS.

El diagnóstico previo era correcto en el mecanismo (la ventana rodante de 2000
ratios arranca en orígenes distintos) pero la causa era el **arnés**, que no le
daba historia al kernel — no el kernel.

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
