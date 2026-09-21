# YM / BigTrap2Absorption retest — Kaggle pilot preregistration

**Status:** `BLOCKED_BY_CUSTODY_AND_SIGNAL_SEMANTICS`  
**Scope:** target-free, pre-holdout only  
**Outcomes:** closed

## Question

Once a BigTrap2Absorption zone is causally available, does waiting for the first qualified return to its rectangle define a materially different entry population than immediate entry?

## Contamination disclosure

The hypothesis was motivated by viewing YM SEP26 around 2026-07-24, inside the holdout.

- `PREEXISTING_OUTCOME_EXPOSURE=YES`
- `HOLDOUT_CONTAMINATED_FOR_THIS_HYPOTHESIS=YES`
- The 2026-07-01..2026-12-31 holdout cannot confirm this hypothesis.
- No parameter may be selected from that screenshot.

## Temporal contract

`formation_start < formation_end <= available_at < entry_at`

Touches during formation never count as retests. Tick identity is `(ts_ns, sequence)`.

Two signal adapters remain allowed but unresolved: `M5_FORMATION` and `TICK_BUCKET_FORMATION`. Execution remains disabled until exact producer provenance is published.

## Frozen target-free policies

- Immediate: first tick strictly after `available_at`.
- Fixed waits: 25 and 100 ticks.
- Retests: departure `{2,4}` ticks × depth `{0,.5,1}` × max wait `{250,1000}` ticks.
- Total: 15 policies.
- Missing retest: `NO_ENTRY_CENSORED`, never a loss or zero activity.

## Target-free outputs

Counts, coverage, departure, first retest, depth, wait, invalidation, expiry, session end and censoring only. PnL, returns, MFE, MAE, stops, targets and winner selection are forbidden.

## Gates

1. Custody classification reconciled.
2. Effective indicator and viewer provenance published.
3. Pre-holdout YM contract scope frozen.
4. Code/data hashes recorded.
5. Zero decoded holdout rows.

## Epistemic ceiling

The first episode may become `LESSON_CANDIDATE`; never `EDGE_VALIDATED` or `LEARNING_RULE_ACTIVE`.
