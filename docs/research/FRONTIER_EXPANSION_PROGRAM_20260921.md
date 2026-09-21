# EdgeLab Frontier Expansion Program

**Branch:** `feat/frontier-expansion-lab-20260921`  
**Baseline:** `feat/ym-density-corridor-discovery-20260921@1532b875`  
**Status:** `ACTIVE / PRE-HOLDOUT / FAIL-CLOSED`

## Mandate
Expand only where capability reduces distance to net, robust, executable edge. Preserve `LLM_PROPOSAL_NOT_EVIDENCE`, `NO_SELF_APPROVAL`, `LEDGER_APPEND_ONLY`, sealed holdout, negative results and dependency invalidation.

## Evidence ladder
1. contract; 2. invariant tests; 3. synthetic replay; 4. captured replay after custody; 5. shadow; 6. preregistered economics; 7. separately authorized holdout/live.

## Workstreams
- W0 canonical integration/reproducibility.
- W1 Execution Lab: latency, queue, partial fills, gaps, adverse selection.
- W2 L2/MBO observability: lifecycle, sequence, identity, provenance; `NOT_OBSERVED != ZERO_ACTIVITY`.
- W3 multiasset point-in-time residuals and leg risk.
- W4 portfolio/capacity.
- W5 shadow/live reconciliation and kill rules.
- W6 conditional ML only when primary signal and overlapping labels justify it.

## Research loop
Research mechanism; enumerate event-space; declare observables; freeze falsification; implement smallest slice; adversarial review; update measured/not-measured; only then consider outcomes.

## Checkpoints

### C1 — Fail-closed passive queue kernel
Implemented conservative queue fills without calibration/profit claims.

### C2 — L2/MBO observability boundary
`L2_MBO_OBSERVABILITY_V1` prevents MBP promotion to exact FIFO.

### C3 — Causal trend context
`CAUSAL_TREND_CONTEXT_V1`: prefix-invariant EMA9/21, SMA20/50 and session VWAP without outcomes.

### C4 — Carrier semantics and causal joins
`TREND_CARRIER_SEMANTICS_V1`: BigTrap fades, HFT formation, confirmed bounce and confirmed breach are distinct lineage-bound events. Exact availability, same-session joins and certified V2 provenance fail closed.

### C5 — Trend-component ablation manifest
`TREND_ABLATION_MANIFEST_V1` charges carrier-only, EMA/SMA/VWAP-only, all-component and shuffled-placebo cells. Default 48 policies; every parameter neighbourhood multiplies the budget. See `TREND_CARRIER_ABLATION_CONTRACT_20260921.md`.

## Immediate next increments
1. independent queue reference/property tests;
2. post-fill adverse-selection markouts;
3. vendor-neutral MBO adapters;
4. calibrate only after source intake;
5. point-in-time multiasset joins;
6. portfolio/capacity;
7. shadow reconciliation.

## Aporte al referente
The branch replaces hypothetical execution and indicator folklore with falsifiable fail-closed contracts while preserving the holdout.
