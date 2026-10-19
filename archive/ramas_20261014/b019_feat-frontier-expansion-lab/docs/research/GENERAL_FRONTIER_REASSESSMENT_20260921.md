# General Frontier reassessment after trend integration

**Status:** `PRE-HOLDOUT / RESEARCH + IMPLEMENTATION`  
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Veredicto actualizado

EdgeLab now has causal trend composition, explicit BigTrap/HFT semantics, charged ablations and non-executable placebo runtime. This closes representation gaps, not economic evidence. Highest remaining gaps:

1. adverse selection and execution shortfall after passive fills;
2. captured MBO calibration and shadow fill reconciliation;
3. point-in-time multiasset/residual infrastructure with leg-risk abstention;
4. portfolio aggregation, correlation concentration, turnover and capacity;
5. promotion through net costs, multiplicity and sealed OOS.

Additional indicators, meta-labeling and broader grids remain lower priority.

## Research and implementation

Execution research warns that passive fills are selected events: an order often fills because price is moving through it. Fill probability without post-fill drift can manufacture phantom gains. Implementation shortfall compares execution with arrival price; markouts isolate favorable/adverse post-fill movement. Queue position changes both fill probability and adverse-selection exposure.

`MARKOUT_OBSERVED_QUOTES_V1` measures quantity-weighted signed markouts and spread capture after observed fills. Missing anchors/horizons, stale quotes, sequence gaps and resets abstain; crossed quotes fail; results are deterministic. No market outcomes or holdout were opened.

## Justificación económica

A passive strategy is not viable because a queue model says it filled. If adverse markouts plus fees consume spread capture, the apparent edge is non-executable. This tests North Star priorities 1 and 4 before promotion.

## Cómo podría refutarse

Technical failure: imputation through gaps/resets, stale quotes, wrong sign, ignored partial weights or nondeterminism. Economic failure: adverse markouts plus fees exceed spread capture on preregistered horizons and certified data.

## Measured / not measured

Measured: synthetic semantics and abstention invariants. Not measured: real markout distributions, calibration, P&L, capacity, shadow/live or holdout.

## Aporte al referente

EdgeLab can now falsify passive execution using observed post-fill movement rather than treating a simulated fill as realized edge.
