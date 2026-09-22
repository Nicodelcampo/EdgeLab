# Trend carrier semantics and ablation contract

**Contracts:** `TREND_CARRIER_SEMANTICS_V1`, `TREND_ABLATION_MANIFEST_V1`  
**Status:** `TARGET-FREE / PRE-OUTCOME / PRE-HOLDOUT`  
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Justificación económica

EMA, SMA and VWAP can only reduce the distance to an executable edge if their marginal contribution is measured against the event carrier. Public trend evidence is strongest across instruments and longer horizons, not as a free intraday rule. Microstructure supports both continuation and reversion because persistent order flow is offset by asymmetric liquidity and transient impact. Those mechanisms must be separate hypotheses.

## Frozen semantics

- BigTrap2 trapped buyers: failed aggressive buying, fade short.
- BigTrap2 trapped sellers: failed aggressive selling, fade long.
- BigTrap2Absorption: explicit `kind` and `dir` must agree.
- HFT formation: native streak continuation.
- Confirmed HFT bounce: later event, same direction as parent.
- Confirmed HFT breach: later event, opposite direction.

Bounce/breach cannot exist at creation. Every event requires exact availability, session identity and `lineage_id`; legacy HFT timing and uncertified parity fail closed.

## Existing momentum miner audit

`validation/momentum_miner.py` remains historical exploratory code: hard-coded paths; one opposite-direction breach story; no formation/bounce alternatives; no lineage or exact availability custody; fixed TP/SL grids; no full multiplicity/capacity gates; and invalid “holy grail” language. Its mapping is represented only as `CONFIRMED_ZONE_BREACH` after an observed breach, not inherited as evidence.

## Components and ablations

`CAUSAL_TREND_CONTEXT_V1` exposes `ema_state`, `sma_state`, `vwap_state` and a combined state that is directional only when all agree. Conflicts are neutral.

Eight carrier/mechanism hypotheses cross six cells: carrier-only, EMA-only, SMA-only, VWAP-only, all-components and within-session shuffled placebo. Default: 48 charged policies. Every additional parameter tuple multiplies the count; duplicates are rejected. Shuffle seed is `20260921` with 100 replicates. Outcomes are forbidden and holdout sealed.

The manifest is not authorization to run outcomes. Dataset, dates, contracts, costs, execution, non-overlap, clustered uncertainty and survival gates still need a separate preregistration.

## Cómo podría refutarse

Failure includes future/cross-session joins, lineage collisions, creation-time bounces/breaches, inconsistent labels accepted, legacy timing admitted, future bars changing prior states, or omitted/duplicated variants. Economically, trend context must add net multiplicity-adjusted cross-contract information versus carrier-only and shuffled controls; one favorable EMA/VWAP cell is insufficient.

## Measured / not measured

Measured synthetically: mappings, timestamp custody, same-session joins, lineage, distinct event mechanisms, component conflicts, digests, exact policy enumeration and sealed flags.

Not measured: market event counts, returns, P&L, costs, significance, optimal periods, stability, capacity, live parity or holdout.

## Aporte al referente

EdgeLab can now test trend alignment as a falsifiable marginal interaction without changing detectors or retrofitting a profitable story after outcomes.
