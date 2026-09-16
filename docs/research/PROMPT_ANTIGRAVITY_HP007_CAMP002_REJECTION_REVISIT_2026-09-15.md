# Antigravity execution brief — HP007-CAMP-002

## Rejection → excursion/trading → revisit of a liquidity void

Read this entire document before acting and reread it before each phase. This is a structural-mechanism campaign, **not an edge search and not a trading-strategy optimization**.

## 1. Research question

Determine whether the liquidity-field logic is a sound base for later edge research, especially this ordered episode: a causal void exists; price approaches its near boundary; it is rejected before traversing; it moves materially away; enough clock time and/or traded volume passes; it returns to the same frozen void; and the second approach may traverse more often, faster or deeper.

The mechanistic hypothesis is that resistance responsible for the first rejection may have decayed, been consumed, moved, invalidated or lost supporting zones. With L1/ticks this remains a proxy hypothesis. Do not claim hidden order-book depletion is proven; later L2 work must test depletion/replenishment directly.

Primary question: **Does prior rejection followed by qualified separation change the conditional traversal process on revisit?** P&L, entries, stops, Sharpe, strategy promotion and holdout confirmation are not primary outcomes.

## 2. Foundation and branch

Start from `work/hp007-campaign-v2-foundation-20260915` at or after `c417d36c05b0a1484b4bf275ffe56119e3f35f97`. Use:
- `edgelab/research/corridor_campaign_v2.py`
- `edgelab/research/void_revisit_episodes.py`
- their tests
- `HP007_CAMPAIGN_V2_FOUNDATION_2026-09-15.md`

Integrate contract/session logic from `work/universal-contract-regime-v2-20260915` commit `4f84eabb8e6717cc83beb1acd226378d08ca76c6`, preserving history. Create `work/hp007-rejection-revisit-campaign-v2-20260915`. Do not merge to foundation/main.

## 3. Safety

- Never read/derive outcomes at or after `2026-07-01T00:00:00Z`.
- Do not alter/delete/move datasets, old artifacts or branches.
- Preserve CAMP-001; mark superseded, never erase it.
- No force push, merge, secrets or raw data in Git.
- Use only current contract/session eligibility; otherwise label exploratory/abstain.
- Commit and push preregistration before structural outcomes are generated.

## 4. Required separation

Keep four layers independent:
A. causal indicator zone events;
B. target-free price-level liquidity field;
C. episode state machine;
D. structural traversal/penetration/time outcomes.

Do not let D select A-C. This is not target/stop optimization.

## 5. Fix CAMP-001 mechanics

- Remove every 1,000-tick cap; slice by timestamp with `searchsorted`.
- Incomplete horizons are `DATA_EDGE`, not `TIMEOUT`.
- Validate `(timestamp, sequence)` across every row.
- Use `America/Chicago` and certified calendars, including DST.
- Hash caches by data, code, params, contract, bars, sessions, cutoff and schema.
- Reconstruct touches/lifecycle/geometry as-of; no final snapshots projected backward.
- Zero episodes => `ABSTAIN_NO_CAUSAL_EVENTS`.
- Exact sign flips where feasible or >=100,000 deterministic draws; validate Holm resolution.
- Publish actual pytest collection counts.
- Add a non-destructive CAMP-001 supersession addendum.

## 6. Frozen-void state machine

At first approach freeze: void ID/version, indicator, contributing zone IDs, lower/upper/near/far ticks, direction, complete field vector, creation/availability, as-of lifecycle, contract, trade date, regime and roll-manifest hash. Primary analysis follows this frozen geometry; live geometry evolution is recorded separately. Moving geometry is sensitivity only.

For approach from below (`side=+1`), near=lower and far=upper; mirror for `side=-1`.

### First approach
Enter when price reaches `{0,1,2}` ticks from near boundary.

### Rejection
Require no full traversal followed by movement away at least `{4,6,10,14}` ticks. Classify first penetration: none, 0–25%, 25–50%, >50% without traversal. Never define rejection using P&L.

### Qualified away period
Measure independently: clock time, cumulative traded volume, trade count, completed bars, maximum excursion and volatility-normalized excursion. Target-free candidate thresholds:
- time `{30,60,180,600}` seconds;
- excursion `{4,6,10,14}` ticks;
- volume/trade count prior-session percentiles `{25,50,75}` plus disabled.

Normalizations use prior eligible sessions only. Require strict ordering:
`first_approach < rejection_confirm < away_qualified < second_approach`.

No overlapping episodes for the same frozen void in primary analysis. Define deterministic ownership and ambiguity counters when voids overlap.

### Second approach terminals
- `TRAVERSED`: reaches far boundary plus preregistered buffer.
- `REJECTED_AGAIN`: moves away by rejection excursion before traversal.
- `CENSORED`: data/session/max-followup ends first.

Secondary structural outcomes: entered, maximum penetration, 25/50/75/100% depth, time/ticks/trades/volume to each depth, direction-adjusted traversal speed, competing risks and live-field change. Never convert censored/incomplete episodes into failures.

## 7. Mechanism variables

Between approaches, causally measure: elapsed time; volume/trades; excursion; changes in forward, wall and backstop fields; contributor zones added/lost; touches; invalidations/expirations/depletions; strength decay; entropy/concentration; volatility/activity changes. Treat these as proxies. The claim “the reason no longer exists” requires measured weakening/removal to explain the changed traversal process and still cannot establish L2 depletion from L1 alone.

## 8. BigTrap2Absorption configurations

Read exact `PARAM_SPEC`, defaults, PIT tests and historical sweep ledgers. Do not invent parameter names. Build default, historical HP-007, one-at-a-time useful values, structural extremes, pairwise covering array, prior target-free stable configs and negative controls.

Before outcomes, measure zones/session, coverage, widths, lifetimes, touches, field sparsity/saturation, void incidence/duration, stability to +/-1 tick/contract, causal failures and compute cost. Deduplicate exact `zone_stream_sha256` and then `field_stream_sha256`; only representatives proceed.

## 9. Weight and decay logic

Required strength transforms: count; power p `{0.15,0.25,0.5,1}`; sqrt; log; winsorized power caps `{2,3,5}`; optionally prior-session empirical percentile, robust-z softplus and saturation. Spatial kernels: hard box sigma 0 and Gaussian sigma `{0.75,1.5,3}` ticks.

Full causal weight:
`strength × maturation × temporal_decay × wear(touches_asof) × validity × spatial_kernel`.

Required one-component-off family:
- `FULL`
- `NO_MATURATION`
- `NO_TIME_DECAY`
- `NO_WEAR`

Optional `NO_DECAY_ALL` is diagnostic. Holm-adjust the three FULL-vs-ablation contrasts. The objective is to identify which mechanism represents weakening between rejection and revisit—not profitability. Use target-free screening, reject empty/saturated/duplicate fields, then preregister a compact family.

## 10. Secondary indicator

Preferred candidate is `Gaps2`, but visible synthetic tests explicitly do not prove real NT8 parity. Before use, prove real-oracle parity for exact C#/Python hashes, oracle hash, instrument, bars, timezone, tick size, params, geometry, timestamps, touches, lifecycle and unmatched counts. Otherwise set `ABSTAIN_REAL_ORACLE_PARITY_NOT_PROVEN` and skip confirmatory secondary/mixed work.

Do not use aVolClusterPOI confirmatorily while audited bar partition is 89.81%, despite exact kernel parity on equal inputs. Do not prioritize HFTClusterZonesNQ now: v2 has historical/realtime double-counting and lacks a clean contemporary oracle certificate. Create its parity plan only after this campaign.

## 11. Mixed indicator field

Only if secondary parity passes, build identical-session arms `BT2A_ONLY`, `SECONDARY_ONLY`, `MIXED`. Preserve source contributions. Test sum, max, noisy-or and consensus-product with source weights `1:1`, `2:1`, `1:2` after causal per-source normalization. Compare structural revisit processes, not P&L. MIXED is useful only if it adds stable structural information beyond both individual fields.

## 12. Controls and estimands

Because the first approach is selected to reject, do not compare its traversal rate (zero by definition) naively with revisit traversal. Estimate:
1. conditional revisit traversal probability;
2. revisit versus matched comparable fresh first approaches;
3. long/high-volume-away versus short/low-volume-away revisits;
4. dose-response/hazard versus elapsed time, volume, excursion and field decay;
5. penetration/speed changes with explicit selection caveats.

Match on pre-approach contract/session, direction/time bucket, initial geometry/width/field, distance/speed, volatility/activity, contributors, age/touches and regime. Do not match on post-rejection mediators when estimating their effects. Report balance, overlap, calipers, unmatched, reuse and standardized differences.

Primary outputs: traversal probability, matched risk difference, competing-risk cumulative incidence, session-clustered hazard/dose-response, penetration/speed effects and exploratory mechanism decomposition. Do not call exploratory mediation causal without justified assumptions.

## 13. Preregistration

Target-free construction may run first. Then commit and push, separately and before labels/outcomes:
- exact episode semantics;
- deduplicated variants;
- estimands;
- censoring/ambiguity;
- controls;
- statistical families;
- minimum events/sessions;
- seeds/draws;
- contracts/folds;
- abstention/stopping rules.

Suggested files: `HP007_CAMP002_REVISIT_PREREGISTRATION_2026-09-15.json`, `...VARIANT_LEDGER...json`, `...STATISTICAL_PLAN...md`. Record prereg SHA. Later definition changes require addendum/new campaign ID.

## 14. Inference and walk-forward

Cluster uncertainty at session level; report contract heterogeneity. Use exact sign flips or >=100,000 draws. Respect censoring/competing risks. Correct within preregistered families and disclose global exploratory multiplicity. Report effects, intervals, counts, censoring and fold stability—not only p-values.

Use multiple chronological eligible folds. Fit normalizations/thresholds on train only and freeze in test. Keep holdout sealed. Report incidence, sign consistency, calibration/discrimination, coverage drift and abstentions.

## 15. Tests

Run full `pytest -q` plus focused suites. Add tests for strict state ordering; long/short symmetry; immediate first traversal exclusion; shallow penetration; time/volume qualifications; non-overlap; frozen/live geometry; session/data censoring; terminal priority; timestamp+sequence; DST; full horizon; as-of lifecycle; cache invalidation; holdout firewall; deterministic reruns; parity gate and mixed-source attribution. Existing detector is a foundation: repair defects with tests without weakening the conceptual contract.

## 16. Deliverables and verdicts

Publish eligibility/provenance inventory, CAMP-001 addendum, parity matrix, BT2A parameter catalog, target-free dedup, prereg commit, episode census, transition/competing-risk results, mechanism results, three ablations, secondary/mixed results or abstentions, folds, provenance manifest, limitations and L2 follow-up.

Allowed final statuses:
- `BASE_LOGIC_STRUCTURALLY_SUPPORTED`
- `BASE_LOGIC_PROMISING_BUT_UNSTABLE`
- `BASE_LOGIC_NOT_SUPPORTED`
- `ABSTAIN_INSUFFICIENT_EPISODES`
- `ABSTAIN_CONTRACT_NOT_CERTIFIED`
- `ABSTAIN_SECONDARY_PARITY_NOT_PROVEN`
- `INVALIDATED_EXECUTION`

Do not emit an edge verdict or trading recommendation. Conclude only whether the framework is causal, frequent enough, stable and mechanistically interpretable enough to justify a later preregistered edge search.

Final handoff must list branch/commits, commands, test counts, file stats, contracts/sessions, holdout rows read (must be zero), parity per indicator, raw/dedup/preregistered variants, state counts, censoring, structural effects, ablations, folds, anomalies and next step. Keep worktree clean and push all non-data artifacts.
