# AVZVOL: full-grid coverage and long-lived-zone campaign — progress, not strategy validation

## Completed and preserved

MNQ_12-26: 1,536 detector configurations × 1,260 predeclared departure/return rules = 1,935,360 configuration-rule pairs. Every checkpoint was independently verified against its source and engine pins, count totals and selected-session dimensions. The 1,536 configuration birth counts exactly reproduce the prior frequency census. 608 configurations have no births; 928 have births. An empty configuration is not a predictive rate of 0%.

The same 1,935,360 distinct pairs are scheduled on each of six contracts (11,612,160 contract-pair evaluations, not 11,612,160 unique strategies). The five other contracts are not complete at this progress snapshot.

## Calculation incident, correction and invalidation

A serialization defect in the separate long-lived-zone runner mapped a 16-element feature tuple to CSV columns one position too far right. It left visits1 blank, shifted the other features, and overwrote the correctly calculated local hour with age_seconds. This is a code defect, not tick-dataset corruption. It was found during result QA before any longevity performance finding was published. No raw source was edited.

All affected pilot analyses and model diagnostics were invalidated and archived privately. The incomplete MNQ_09-25 attempt was stopped and will restart from its beginning. The complete pilot's 2,538,085 overlapping signal rows were repaired losslessly: all 16 feature values were preserved and remapped explicitly; the hour was independently reconstructed from the pinned raw timestamp for every one of 250,439 unique trigger sequences. A digest verifies that all unaffected columns, including status, identities and causal trigger indices, remain unchanged. Raw SHA-256 matches before and after. No event rows or sequences are included in this PR.

The independent original full-grid engine does not use the longevity features, and its completed pilot checkpoints are unaffected. New named serialization has 388 checks, covering CSV round trips for every local hour and invalid-range rejection. Feature calculations retain 274 causal tests and 400 direct-versus-cached comparisons with future-prefix invariance. Analyses now fail closed on unverified or invalid feature columns. Corrected launch source is snapshotted locally.

## Requested longevity hypothesis and measurement

Separate campaign: 18 detector families, seven closed-bar age landmarks (0,250,500,1000,2000,3000,5000), eleven distance/retracement/endpoint rules and two origins = 2,772 groups per contract. Age means closed 25-Last-record bars since observable frozen birth, not the final lifetime and not the detector's lookback. It records first actual visits after each landmark, repeat trading episodes based on inside prints rather than OHLC intersections, observed inside volume/duration, return speed, bars per tick, efficiency and quote-inferred flow coverage.

Targets and equal-distance opposite barriers use ordered observed Last records. Main chronology uses only causal features and fully closed bars for revisit counts, with current-bar volume restricted to the prefix already observed at trigger. The first signal per fixed 6,250-record bin is retained before subgroup filters. Frozen birth deduplication is a sensitivity, not proof of statistical independence. Session-end, waiting, gap and unresolved outcomes are retained separately.

Primary effects use whole-session bootstrap pointwise intervals, not independent-event binomial certainty. Translated geometry is a non-randomized control; comparisons retain only overlapping session/hour/price-span/distance strata and must report support lost. The fixed ridge diagnostic uses train-only imputation/scaling and a chronological split of previously inspected dates; it is not a virgin holdout. No best-cell promotion, familywise significance correction, executable fills, fees/slippage or P&L validation is claimed here.

## Remaining work

Finish corrected pilot inference, run both campaigns on the other five contracts, verify all checkpoints, then evaluate frequency/effective support and stability before promoting candidates. No claim yet that 2,000–3,000-bar zones have an edge, or that revisits, speed or imbalance improve predictions. Cross-session carry, unknown visits across gaps, original-export certification and MNQ_09-26 warmup discontinuity sensitivity remain unresolved limitations.
