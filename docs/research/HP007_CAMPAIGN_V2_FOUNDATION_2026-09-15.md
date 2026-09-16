# HP-007 Campaign V2 — foundation and execution contract

This additive foundation supersedes the execution mechanics of HP007-CAMP-001 without deleting its evidence.

## Mandatory corrections
- Full timestamp horizon via `searchsorted`; never cap by row count. Incomplete horizons are `DATA_EDGE`, never `TIMEOUT`.
- Validate `(timestamp, sequence)` ordering over every row.
- Derive CME trade date in `America/Chicago`; no fixed UTC boundary.
- Distinguish absolute candidate net expectancy from candidate-minus-control delta. Equal costs may cancel from the latter and must not be described as cost sensitivity.
- For 54 tests, 1,000 permutations cannot pass Holm. Use exact sign flips when feasible or >=100,000 deterministic draws.
- Zero causal candidates means `ABSTAIN_NO_CAUSAL_EVENTS`, not failure against a control.
- Cache keys include data, code, parameters and contract hashes.
- Publish preregistration in a separate commit before outcomes.

## Indicators
1. **BigTrap2Absorption**: primary source. Sweep useful construction and lifecycle configurations, not arbitrary Cartesian combinations.
2. **Gaps2**: preferred secondary source only after a real NT8 oracle manifest proves parity for the exact instrument, bar construction and parameters. Synthetic unit tests do not prove parity.
3. **aVolClusterPOI**: not eligible for confirmatory mixed testing yet. Kernel parity on equal inputs is exact, but audited primary-bar partition is 89.81%.
4. **HFTClusterZonesNQ**: deferred. Current v2 has historical/realtime double-counting and lacks a current real-oracle parity certificate. Work on parity only after Campaign V2 deliverables.

## Weight model
Each price tick receives the causal sum of zone contributions:
`strength(zone) * maturation(age) * temporal_decay(age) * wear(touches_asof) * kernel(distance)`.
Required strength transforms: count, power, square-root, log, winsorized power. Required source combiners: sum, max, noisy-or and consensus-product. Normalize strength references only from prior eligible sessions.

Required ablations, changing exactly one switch at a time:
- FULL
- NO_MATURATION
- NO_TIME_DECAY
- NO_WEAR

Treat the ablations as one preregistered family and correct multiplicity.

## Minimum useful grid
Read BT2A dimensions from its `PARAM_SPEC` and existing sweep ledger. Include defaults plus defensible nearby values for bar size, imbalance/absorption threshold, width, volume threshold and lifecycle. Deduplicate configurations producing identical zone streams before outcome evaluation.

Weight grid: strength mode `{count,power,log,sqrt,winsorized_power}`; power `{0.15,0.25,0.5,1}` where applicable; sigma `{0,0.75,1.5,3}` ticks; time half-life `{4,12,36}` hours; maturation `{0,1,4}` hours; wear coefficient `{0.25,0.5,1}`; wear power `{0.5,1}`. Use staged target-free screening before freezing a compact outcome family.

## Mixed indicator analysis
Run only if secondary parity and causal availability pass. Build BT2A-only, secondary-only and mixed fields on identical eligible sessions. Preserve source identity. Compare additive, max, noisy-or and consensus-product combiners and source weights `{1:1,2:1,1:2}`. Controls, horizons, costs and folds must be identical across arms.

## Gates
Target-free first: coverage, density distribution, corridor count, width, duration, source contribution, overlap, stability to +/-1 tick/contract perturbations, and duplicate-field collapse. Then freeze variants. Outcomes only after preregistration commit. Require positive absolute net expectancy, positive incremental delta, adequate sessions/contracts, multiplicity-adjusted inference, and multi-fold transfer. Keep holdout sealed.
