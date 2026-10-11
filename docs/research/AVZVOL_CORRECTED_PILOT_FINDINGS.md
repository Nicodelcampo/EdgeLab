# AVZVOL — corrected pilot findings and full-grid support

Exploratory results for MNQ_12-26 only, on ten selected sessions. The other five contracts are not complete. No virgin holdout, familywise significance, source certification, executable fills, transaction costs or P&L are claimed.

## Full-grid support, not performance-based selection

All 1,935,360 configuration-rule cells were included. Only 120,758 (6.24%) have at least 100 resolved signals after the fixed 6,250-record-bin thinning. 1,681,303 (86.87%) have fewer than 30 resolved signals, including cells with no signal or no resolved outcome. These are cell counts, not independent events. A 100-outcome threshold is a descriptive support screen, not guaranteed statistical power.

P80/Window5 is the largest frequency-support group in this pilot. Counts below are the number of 96 detector configurations within each percentile/window combination having at least one of the 1,260 rules with ≥100 resolved thinned signals. All 267 configurations passing this screen have support on at least eight of the ten sessions. This does not establish their predictiveness. Choosing a short barrier/horizon can alter resolution frequency; cells must be compared within the intended event definition before strategy selection.

| Percentile | Window5 | Window10 | Window20 | Window40 |
|---|---:|---:|---:|---:|
| P80 | 79 | 50 | 19 | 0 |
| P90 | 57 | 20 | 1 | 0 |
| P95 | 31 | 4 | 0 | 0 |
| P97.5 | 6 | 0 | 0 | 0 |

## Old-zone partial return: contact is more promising than crossing, but unconfirmed

Primary geometry P80/W5/R18/lookback2000/height20, departure D40 ticks, 50% retracement, frozen birth dedup75 and first signal per temporal bin before feature filters. Landmarks are age since observable frozen birth, not lookback or final lifetime.

| Landmark | Target before opposite | Resolved | Target rate | Pointwise session-bootstrap95 |
|---|---:|---:|---:|---|
| 2000 bars | 97 | 177 | 54.80% | 46.75–61.68% |
| 3000 bars | 83 | 139 | 59.71% | 50.41–68.60% |

More important than the standalone target rate is comparison with geometry-matched translated zones. Every paired real-control interval below includes zero. Common-support weights are not numbers of independent trades. Support is lost when matching, and the translated control is not randomized.

| Age | Endpoint | Real minus control, pp | Pointwise paired-session95, pp | Matched weight |
|---|---|---:|---|---:|
| 2000 | touch near boundary | +15.21 | -1.15 to +26.91 | 80 |
| 2000 | zone center | +1.92 | -12.50 to +14.00 | 71 |
| 2000 | cross far boundary by1tick | +2.30 | -17.17 to +15.74 | 77 |
| 3000 | touch near boundary | +9.00 | -2.88 to +21.33 | 65 |
| 3000 | zone center | +3.36 | -10.94 to +15.67 | 59 |
| 3000 | cross far boundary by1tick | -0.29 | -11.95 to +10.08 | 63 |

## Revisit counts and incremental predictors

The primary old cohorts have too little variation in coarse revisit bins to infer a monotonic repeat-interest effect. At age2000, 170 of177 resolved signals have five or more prior visits; at age3000, 137 of139 do. Zero/one-visit groups have no resolved cases and the2–4 groups have only7and2. Future work should consider finer within-5+ distributions, volume, time spent and recency, with thresholds chosen on development data and then fixed for replication, not outcome-selected in the same pilot.

A fixed ridge-logit diagnostic trained on the earlier six dates and evaluated on100signals from the later four previously inspected dates did not demonstrate incremental benefit from the joint revisit/volume/speed/flow/efficiency/recency features. Context-only Brier: 0.259310; extended: 0.264419 (lower is better). Extended minus context Brier: +0.005109; session-bootstrap95 [-0.004158, +0.017392]. Log loss also worsened at the point estimate. This tests this fixed joint model only, not each feature's usefulness under every variant; four test sessions are weak support and not a virgin holdout.

## Validation and current execution

All pilot headline counts were independently recounted from the corrected signal CSV or full2million-cell support census, separately from the original aggregate computations. The column repair, source hashes, code snapshots, serialization tests and invalidation history are documented in AVZVOL_FULL_GRID_LONGEVITY_PROGRESS.md. MNQ_09-25 is now executing the corrected age/revisit campaign; its original full grid and subsequent contracts remain queued. Support analysis is automatically scheduled after each contract coverage-verification file appears. Raw data and event-level files remain private.

Canonical frequency and matched-difference chart artifacts passed static validation, but the session file-transfer helper failed with a non-retryable computer_helper_failed error. No substitute PNG/generic chart was used; the exact reconciled tables above remain the accessible numeric result.
