# Trend Context Composition Contract

**Contract:** `CAUSAL_TREND_CONTEXT_V1`  
**Status:** `TARGET-FREE / SYNTHETIC / PRE-HOLDOUT`  
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Justificación económica

EdgeLab already has event carriers—BigTrap2, BigTrap2Absorption, HFT zones and causal density structures—but a carrier is not an edge. Trend context can separate continuation, pullback/re-entry, and failure/exhaustion mechanisms. Pooling them can cancel real conditional effects or manufacture one through post-hoc relabeling.

## Cómo podría refutarse

The contract is invalid if any future bar changes a prior context, session VWAP does not reset, an event consumes context before it is available, raw BigTrap/HFT direction is guessed, or a named indicator is presented as evidence of profitability.

## Research synthesis

Long-horizon multiasset time-series momentum has broad historical evidence, but strong implementations combine breadth, multiple horizons and volatility scaling. A material share of reported performance may come from volatility scaling rather than the directional rule. Moving-average filters are linear trend representations, not independent causal proof. VWAP has an execution-benchmark mechanism, but public evidence for standalone intraday VWAP/EMA profitability is much weaker.

EdgeLab's record is stricter: the GC BigTrap/EMA audit found OOS reuse, multiplicity and missing entry costs; after entry slippage, absolute profitability died and only an underpowered conditional contrast remained. The NQ HFT/EMA dossier reports regime dependence and causal-retest fragility. YM density-wall continuation adjudicated 2,304 policies with zero survivors. The context census already declared SMA20/SMA50, EMA9/EMA21 and prior-bar session VWAP target-free.

Therefore this increment implements representation and ablation support, not a new strategy or a claim that trend following works intraday in EdgeLab.

## Frozen representation

For each closed bar: EMA9/21, SMA20/50, session VWAP, EMA-fast and VWAP slopes over three bars, price distances, and state `UP`, `DOWN`, `NEUTRAL` or `NOT_READY`. `UP` requires price above VWAP, fast EMA above slow EMA, fast SMA above slow SMA, and positive EMA/VWAP slopes. `DOWN` is symmetric. Mixed evidence is neutral.

EMA/SMA state remains continuous over the supplied contract stream; VWAP resets at `session_id`. Contract rolls and untrusted gaps must be split upstream.

## Application to existing EdgeLab tools

### BigTrap2 / BigTrap2Absorption
The detector remains unchanged. Later campaigns can preregister trap aligned with trend continuation, trap against trend as pullback/exhaustion, neutral control, and shuffled trend-state placebo. No losing family may be rescued after outcomes.

### HFT zones
Use causally available V2 zones. Distinct mechanisms are zone birth aligned with trend, pullback to a zone while EMA/SMA/VWAP remain aligned, breach continuation, and counter-trend absorption/reversion. Each requires separate preregistration and multiplicity charge.

### VWAP, EMA and SMA
VWAP is session-relative location and slope, not magical support. EMA is responsive state and a possible trailing reference. SMA is slower confirmation. Distances are context variables, never post-outcome thresholds.

## Required ablations before an economic claim

1. event carrier without trend context;
2. trend context without event carrier;
3. shuffled trend state within session;
4. EMA-only, SMA-only and VWAP-only;
5. parameter neighbourhood charged to the trial budget;
6. volatility-scaled and unscaled sizing separately;
7. with-trend, counter-trend and neutral cells declared first;
8. session-clustered uncertainty and instrument replication.

## Measured / not measured

**Measured:** prefix invariance, warmup abstention, VWAP reset, zero-volume behavior, deterministic digests and causal event alignment on synthetic bars.

**Not measured:** returns, P&L, optimal periods, best carrier mapping, fill quality, capacity, trend-day classification or holdout performance.

## Aporte al referente

EdgeLab gains a causal composition layer that can test whether existing event carriers add information within a trend regime without changing their detectors, opening the holdout or treating EMA/VWAP folklore as an edge.
