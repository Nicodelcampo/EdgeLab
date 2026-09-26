# HP007-CAMP-002 — Visual logic design hold

## Authority

This instruction records the research owner's explicit decision and has precedence over any earlier instruction to measure, preregister or infer the rejection → away → revisit hypothesis. It does not remove prior code or smoke artifacts; it limits their interpretation and blocks outcome use.

## Current objective

The current phase is **visual and target-free logic design only**:

1. find useful configurations of BigTrap2Absorption and alternative zone-weighting logic;
2. render the resulting zones, fields, walls and voids on charts;
3. inspect representative sessions and failure modes visually;
4. preserve enough diagnostics for the research owner to decide later how an event sequence should be interpreted;
5. do not measure the revisit hypothesis until that interpretation is explicitly chosen by the research owner.

The research owner will later decide:

- what constitutes a void;
- which boundary is the entry and which is the exit;
- what constitutes first approach, penetration and rejection;
- how far price must move away;
- whether distance is absolute ticks, volatility-scaled or field-relative;
- whether elapsed clock time, bars, trades or traded volume defines separation;
- what constitutes a valid revisit;
- whether geometry is frozen or allowed to evolve;
- what constitutes crossing, partial crossing, second rejection, ambiguity and censoring;
- which variables and horizons are measured.

Do not freeze or infer those choices on the owner's behalf.

## Hard prohibitions until explicit authorization

Do not:

- estimate revisit traversal probability;
- compare first and second approach outcomes;
- calculate risk differences, hazard ratios, p-values or confidence intervals for revisit behavior;
- optimize distances, times, volumes, thresholds or event labels using subsequent price behavior;
- rank configurations by traversal, rejection, P&L, MAE/MFE or any forward outcome;
- preregister the revisit estimand or final episode semantics;
- describe any smoke-census percentage as evidence for or against the revisit hypothesis;
- open or read the institutional holdout;
- promote a configuration as an edge.

Any previously generated counts such as 425 episodes, 60% traversed or 32% rejected again are **software-smoke outputs only**. They are not research results and must not influence configuration selection or the owner's later definitions.

## Work allowed now

### A. Correct infrastructure

Complete the mandatory censoring/reset corrective patch and tests already identified by audit. This is software correctness, not hypothesis measurement.

### B. Parity

Prepare and ingest real NT8 oracles. Verify exact parity independently for each enabled root. Stop interpretive work for any root lacking parity.

### C. Target-free configuration generation

For BigTrap2Absorption, enumerate useful configurations from exact `PARAM_SPEC`, defaults and prior target-free ledgers. Use one-at-a-time changes, structural extremes and pairwise coverage. Deduplicate identical zone streams. Do not use subsequent price behavior to retain or discard configurations.

For weighting logic, render at least:

- count;
- power transforms;
- square root;
- logarithmic;
- winsorized power;
- hard-box and Gaussian spatial kernels;
- FULL;
- NO_MATURATION;
- NO_TIME_DECAY;
- NO_WEAR.

These are visual model variants, not hypotheses yet.

### D. Visual chart package

Produce a deterministic viewer or chart-export package for manual review. Each chart must display, as-of time:

- raw price bars/ticks;
- contract and session identity;
- roll/reset markers;
- zone source and zone ID;
- creation and availability time;
- live/frozen geometry where applicable;
- touches and lifecycle state;
- per-zone weight components;
- aggregated field by price level;
- visually identified walls and low-field corridors;
- configuration ID and complete parameter manifest;
- explicit `PARITY_PROVEN`, `PARITY_ABSTAIN` or `PYTHON_EXPLORATORY_ONLY` watermark.

Provide toggles or separate panels for:

- default versus alternative parameters;
- each strength transform;
- hard box versus Gaussian kernels;
- FULL and each single-decay ablation;
- each indicator separately;
- mixed fields only if the secondary indicator has real parity.

The viewer must not show forward traversal labels, future-colored regions, P&L or outcome-based rankings.

### E. Visual review sample

Choose sessions without future outcomes using deterministic, target-free criteria fixed before rendering, for example:

- earliest eligible session;
- median activity eligible session;
- highest and lowest prior-session activity based only on information available before the rendered session;
- one session around a contract reset shown only to validate reset behavior;
- representative low/high zone-count sessions selected from contemporaneous indicator output, not later price response.

Include multiple roots only after parity. Keep ES/MES and NQ/MNQ segregated.

## Target-free diagnostics allowed

Allowed descriptive diagnostics concern the object itself, not its future consequences:

- zones and fields per session;
- width, age and lifecycle distributions;
- field sparsity, saturation, smoothness and entropy;
- overlap and fragmentation;
- contributor counts;
- configuration-to-configuration similarity;
- sensitivity to +/-1 tick or +/-1 contract input perturbations;
- zone/field stream hashes;
- computation time and memory;
- missingness, warmup and abstention rates;
- visual clipping or canibalization;
- reset correctness.

These diagnostics may identify unusable representations, but must not choose an event interpretation.

## Required deliverables before owner decision

Publish:

1. parity matrix and oracle manifests;
2. corrected censoring/reset infrastructure and tests;
3. target-free configuration catalog;
4. deduplication report;
5. deterministic visual viewer/export instructions;
6. a visual-review index mapping chart/session/configuration IDs;
7. a short neutral description of what each configuration changes;
8. known failure modes and abstentions;
9. no revisit outcome tables.

Then stop and ask the research owner to inspect the charts and define the sequence semantics. Only after explicit owner approval may a new document preregister distances, times, volumes, labels, controls and structural estimands.

## Current status labels

Use:

- `PHASE = VISUAL_LOGIC_DESIGN`
- `REVISIT_HYPOTHESIS_MEASUREMENT = ON_HOLD_BY_OWNER`
- `REVISIT_EVENT_SEMANTICS = OWNER_DECISION_PENDING`
- `SMOKE_CENSUS = SOFTWARE_VALIDATION_ONLY`
- `OUTCOME_BASED_SELECTION = PROHIBITED`
- `HOLDOUT = SEALED`
