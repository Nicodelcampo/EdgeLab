# Indicator onboarding roadmap — 2026-08-11

This work prepares every known indicator for inclusion without executing outcomes, opening the holdout or selecting by P&L. The latest operator decision enables **onboarding preparation**; research execution remains gated by a campaign manifest and explicit approval.

## What was actually outside

Python kernels already exist for the original five indicators (`Gaps2`, `BigTrap2`, `HFTZones2`, `VolTicksPOC2`, `aVolCellPOI2`) plus `AACloseOpenDiffs`. They were outside a single auditable queue, not outside the codebase. `config/indicator_registry_v1.json` now records source, kernel, tests, parity, bar-spec limits, blockers and next action for all of them.

The registry also includes `LUX-IMB OG/VI` under existing PR #6, the newly received `aVolClusterPOI`, and the two bridge diagnostics. `YM-PRERANGE` is intentionally absent because it is a fixed time-window family, not an indicator.

## Admission sequence

1. **S0 source:** exact bytes, SHA-256, origin and immutable raw artifact.
2. **S1 static preparation:** one Indicator class, CRLF, balanced delimiters, no generated tail in install candidate.
3. **S2 real NT8 compile:** sandbox static checks never substitute the NT8 editor.
4. **S3 legacy kernel:** reproduce the received detector before redesign.
5. **S4 truth-known tests:** determinism, anti-lookahead, sessions, integer ticks and loud failures.
6. **S5 oracle/parity:** same installation, range, parameters, timezone and bar spec.
7. **S6 target-free landscape:** every cell, seed and null, with `M_eff`, MDE, density and coverage.
8. **S7 information/economics:** separate preregistered campaign under STOP; holdout remains sealed.

Static preparation is not compilation; compilation is not parity; parity is not an edge.

## aVolClusterPOI v0.4

- Raw SHA-256: `3420519de9b4a1456f812040b62af419b0c323486281424a84aaaab126100c98`
- Prepared SHA-256: `33028abd28b706191b5a455e47989252e0ff33035fa75bc23e1dc0f6ec94ec1c`
- Raw artifact: `incoming/nt8/aVolClusterPOI/v0.4/aVolClusterPOI.raw.manifest.json` (gzip+base64 determinístico)
- Materialized candidate: `nt8/candidates/aVolClusterPOI_v0.4.cs` (generated locally; not committed before NT8 compile)
- Current status: `STATIC_PREPARED_NOT_COMPILED`

The source has useful causal choices: `OnBarClose`, availability from the next bar, integer-tick state, completed-session history and a one-tick subseries. It also embeds forward target/stop evaluation and a heuristic quality filter. Those parts are excluded from the first Python kernel.

### Parameter separation

**Detector state:** `WindowBars`, `MedianMultiplier`, `MaxGapTicks`, `MinClusterTicks`, `UseSessionBuckets`, `TimeBucketMinutes`, `LookbackSessions`, `DetectionPercentile`, `MinSamplesPerBucket`.

**Lifecycle / separate burst hypothesis:** `InvalidationMode`, `MaxAgeBars`, `MaxTouches`, `BurstMinZones`, `BurstWindowBars`, `BurstRangeTicks`.

**Never optimized:** paths, opacity, rendering limits, labels and dashboard.

**Outcome-blocked:** predictive filter, quality cutoff, distance/rejection score, horizon, target and stop.

### Brute-force architecture

Compute the one-tick footprint and continuous cluster observations once per expensive state configuration. Replay cheap percentile, geometry and lifecycle cuts offline. A full Cartesian grid is allowed only after it is frozen and sized; the report retains every cell and charges multiplicity at family level.

## Admission queue

| Indicator | Admissible scope | Next action |
|---|---|---|
| Gaps2 | exact parity on `time:1` | canonicalize exact reviewed source; target-free manifest |
| BigTrap2 | blocked | close P0.1 NT8 v2.5.1 ↔ Python v2.2 drift |
| HFTZones2 | exact parity on `time:1` | freeze target-free landscape and nulls |
| VolTicksPOC2 | exact parity on `time:1` only | port causal sequencer before `tick:N` |
| aVolCellPOI2 | exact parity on `time:1` only | same sequencer restriction; retain session warm-up |
| AACloseOpenDiffs | kernel present, oracle pending | dedicated source/hash/window parity |
| LUX-IMB | active PR #6 | finish that path; do not duplicate |
| aVolClusterPOI | source pinned | real NT8 compile, legacy kernel, tests, parity |

## Priority and concurrency

G2-A1, YM-PRERANGE and P0 remain ahead of new measurements. This branch is source/infrastructure preparation only and does not edit their reserved files. No fourth outcome campaign starts here.
