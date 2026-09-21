# EdgeLab Frontier Expansion Program

**Branch:** `feat/frontier-expansion-lab-20260921`  
**Baseline:** `feat/ym-density-corridor-discovery-20260921@1532b875`  
**Status:** `ACTIVE / PRE-HOLDOUT / FAIL-CLOSED`

## Mandate

Expand EdgeLab only where a new capability can reduce the distance to a net,
robust and executable edge. The program does not rescue saturated hypotheses by
adding thresholds, narratives or exit grids. Every workstream must add a new
dataset, observable, mechanism or execution contract and must preserve:

- `LLM_PROPOSAL_NOT_EVIDENCE`;
- `NO_SELF_APPROVAL`;
- `LEDGER_APPEND_ONLY`;
- the sealed holdout and explicit outcome authorization;
- negative-result publication and dependency invalidation.

## Evidence ladder

1. **Contract:** semantics, observability and abstention states are frozen first.
2. **Unit/generative checks:** invariants, causality, determinism and malformed input.
3. **Synthetic replay:** adversarial streams including gaps, resets and ambiguous events.
4. **Captured-data replay:** only after source identity, packet completeness and hashes pass.
5. **Shadow:** research/live parity, fill calibration, markouts and drift without capital.
6. **Economic campaign:** preregistered population, costs, multiplicity and capacity.
7. **Holdout/live:** separate human authorization; never implied by prior gates.

## Workstreams and gates

### W0 — Canonical integration and reproducibility

Create a reproducible integration line from the current living branches. No
research result may depend on an unrecorded local merge. Record source refs,
patches, environment and data hashes.

**Gate:** a clean checkout can reproduce contract tests and identify every
non-versioned dependency. **Current risk:** this branch inherits a broad research
lineage; it is not a declaration that all open PRs are integrated.

### W1 — Execution Lab

Replace fixed-slippage-only assumptions where the proposed strategy depends on
passive fills. Model latency, queue ahead, partial fills, resets, sequence gaps,
adverse selection and empirical calibration.

First contract implemented here: `QUEUE_FIFO_L2_V1`.

**Hard semantics:** anonymous cancellations never improve queue priority;
observed executions are the only queue-consuming evidence; missing activation
depth, packet gaps and resets abstain.

**Gate:** synthetic invariants first; captured L2/MBO calibration later. This
module must not silently alter the sealed legacy market simulator.

### W2 — L2/MBO observability

Define normalized add/cancel/modify/execute/replenishment events, exchange
sequence continuity, packet-gap states, order lifetime and source provenance.

**Gate:** `NOT_OBSERVED != ZERO_ACTIVITY`; no fill evidence from reconstructed
footprints alone.

### W3 — Multiasset residual engine

Build point-in-time asynchronous joins, futures roll-safe identities, hedge-ratio
formation/trading separation, residual/z-score mechanics and explicit leg risk.

**Gate:** no same-timestamp look-ahead; formation data cannot leak into trading
adjudication; stale-leg and missing-leg states abstain.

### W4 — Portfolio and capacity

Aggregate independent mechanisms rather than a single winning configuration.
Add correlation clustering, risk budgets, turnover, exposure limits, marginal
capacity and concentration stress.

**Gate:** portfolio claims require component-level lineage and cost/capacity
curves, not just a higher combined Sharpe.

### W5 — Shadow/live validation

Measure signal-to-order latency, observed-vs-simulated fill deltas, markouts,
drift and kill rules. Promotion requires research/live identity and documented
operator controls.

### W6 — Conditional ML validation

CPCV, purging/embargo, triple barrier and meta-labeling are conditional tools,
not default sources of edge. They are admitted only when a primary signal exists,
labels overlap, tuning is nested and the effective trial count is charged.

## Research loop

For each increment:

1. state the mechanism and public evidence supporting plausibility;
2. list the event-space and alternatives before measuring;
3. declare required new observables and what remains unobserved;
4. freeze contract plus falsification criteria;
5. implement the smallest independently testable vertical slice;
6. run adversarial review and record failures;
7. update the measured/not-measured ledger in the same commit;
8. only then decide whether the next slice deserves data or outcome access.

## First checkpoint

Implemented the conservative queue-fill kernel and contract tests. It closes a
specific methodological gap: EdgeLab can now represent a passive order that
fails to fill, fills partially, or becomes unknowable because the feed is
incomplete. It does **not** claim calibration, profitability or L2 availability.

## Immediate next increments

1. add a normalized L2/MBO event schema with provenance and gap certification;
2. add queue-model property tests and independent reference implementation;
3. add post-fill markout/adverse-selection measurement;
4. calibrate with observed order lifecycle data, if a source passes intake;
5. implement point-in-time multiasset joins and leg-risk abstention;
6. add portfolio/capacity contracts;
7. design shadow-mode reconciliation and kill-rule state machine.

## Aporte al referente

The branch begins to replace hypothetical passive execution with a falsifiable,
fail-closed contract while preserving the holdout and refusing to convert
missing market-depth evidence into optimistic fills.
