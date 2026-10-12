# Faster equivalent runs, and more informative future experiments

## Durable status

Before this investigation, a recovery checkpoint and both independent auditors were published in system commit `9e5fecec6076d32ee6f0bc0538920165e9a051e4`. System source/tests before the investigation are pinned at `e98b76ee8abfe58495a0a72dcd2dba7e99a3f391`; scientific exports at research commit `4e5861838a8d31a0eafbd635cb1a6cc73040a269`. The last focal remains active at this observation; no active job was changed. Private source data are not uploaded to GitHub.

This investigation implements one local experimental helper, not automatic optimization adoption or a faster deployed scientific engine. The current frozen campaign remains untouched. Read `RECOVERY_CHECKPOINT.md` and `CLAUDE_HANDOFF.md` to resume.

## What the measured evidence says

Four completed focal jobs have recovered timing receipts. Longevidad plus primary analysis account for **91.01% of their summed observed wall time**. Primary analysis alone accounts for **16.94%**. Total observed job durations range from **66.6 to 144.6 minutes**. These are different contracts, not controlled baseline/candidate runtime comparisons.

Four completed matrix jobs have recovered timing receipts; the full-matrix stage accounts for **80.77%** of summed observed wall time. The completed MNQ12-25 matrix lacks a timing receipt in this recovery set and is excluded; the active focal has no imputed timing. Outer-log stage times are not CPU profiles and do not identify whether the bottleneck inside a stage is CPU, memory, gzip or I/O.

The denominator counts each job's outer total once; it does not sum repeated total columns. Nonoverlapping stage seconds plus a visible unassigned residual reconcile to that total. See `PERFORMANCE_INVESTIGATION_EVIDENCE.json` and the reproduction script. Summing job durations is not calendar campaign elapsed time: jobs may overlap.

## Source-level findings and priorities

Sources were decoded without executing the existing frozen driver payload. Their hashes are recorded in the evidence; embedded signed download URLs were neither printed nor published.

1. **Longevidad: highest end-to-end priority.** The frozen runner loops over births × origins × seven ages × eleven rules, performs scalar evaluation, causal feature extraction and per-row gzip CSV serialization. It already caches zone prefixes and some same-trigger features. Profile each substep before deciding which dominates. Candidate: batch the eleven rule evaluations at the same anchor; reuse an outcome scan only when the complete semantic key matches. Key must include source/input selection, zone/geometry, session stop, anchor/trigger, side, endpoint, horizon and gap policy. Preserve record ordering, endpoint ties, next-observed-record outcome start, causal cutoffs and every registered row/alias.
2. **Primary analysis: demonstrated micro-optimization opportunity.** The frozen analyzer creates 10,000 whole-session draws once, but each cell repeatedly materializes indexed count arrays. It also refilters pandas by session for each definition/cell. Candidate implemented below removes repeated indexed resampling without changing draws. Future separate candidate: aggregate session/status counts once then index them; retain empty sessions and independent thinning audit. Bootstrap/multiplicity inference itself must not be silently changed.
3. **Repeated causal metadata.** Frozen longevity computes a preceding-256-bar price span and UTC→Chicago hour for each emitted row. Investigate one causal precompute per eligible trigger/bar, with identical session boundaries, DST, exclusion of current/future bars and index semantics. Prove exact parity before reuse. Never key a cache only by rounded price or parameter label.
4. **Matrix is already batched.** It groups 1,260 rules into 70 trigger groups and reuses some same-trigger outcomes. Do not promise a new 18× improvement by rediscovering batching already present. Inspect remaining trigger scans, best/labels memory and reductions. Configuration-level independent shards are preferable to parallel writes into shared counters; reduce deterministically and cross-foot the full 1,935,360 pairs.
5. **Persist prepared data and bounded checkpoints.** Content-address selection/build/protocol versions, detector tapes and completed shard receipts. Reuse only on complete key and checksum agreement; explicit invalidation on any input or semantic change. Atomic per-shard outputs plus small append-only receipts permit restart without redoing a completed shard. Publish enough receipts remotely to survive notebook/session expiry. Local cache alone does not preserve recovery after machine loss.
6. **I/O and CPU parallelism are measurements, not slogans.** Compare columnar internal intermediates versus gzip CSV, preserving a canonical export and independent audit. Test thread/process budgets on actual Kaggle allocation with source snapshots and peak process-tree RSS. No GPU recommendation until kernel profile shows a suitable compute-bound batch. Keep durability guarantees: SQLite WAL allows one writer at a time; do not disable fsync or weaken the learning-outbox durability to gain speed.

Numba's own guidance prioritizes profiling real data; native parallelism can help independent work, while fastmath relaxes numerical semantics. Existing kernels already use `njit(cache=True)`. Keep fastmath disabled for exact parity and do not parallelize earliest-signal selection through shared best/counter writes. References: https://numba.readthedocs.io/en/stable/user/performance-tips.html and https://numba.readthedocs.io/en/stable/user/parallel.html . WAL/durability reference: https://www.sqlite.org/wal.html .

## Implemented experiment: exact remuestreo reuse

`tools/research_ops/session_resampling.py` converts an already-chosen session draw-index matrix into integer multiplicities **once**, then computes `multiplicities @ daily_counts` for each cell. It does not draw new samples, change the seed, thin events differently, drop empty sessions or change quantiles. Bounds reject invalid indices, negative counts, excessive allocations and integer overflow. It is not connected to current or future scientific jobs by default.

The isolated synthetic microbenchmark uses 57 sessions, 10,000 draws, 48 cells and three subprocess pairs, reversing execution order in the second pair. Measured calls include candidate multiplicity construction, exclude imports/data generation and compare identical resulting quantile hashes. First/warm call medians were **3.82× / 4.05× faster** on the local sandbox, with identical synthetic quantiles. Peak process RSS is measured, not imputed, but includes imports/workload and is not Kaggle telemetry.

**These figures do not predict campaign speedup.** The helper covers one substep. Even if the whole primary-analysis stage improved 4×, the illustrative Amdahl improvement for the full focal would be only about **1.15×** with everything else unchanged. That is a hypothetical bound, not a promised result. The bigger win must address longevity, not only this helper. Real-MNQ/full-output parity and equivalent Kaggle wall/RSS measurements are pending.

Reproduce:

```sh
python -m unittest discover -s tests/research_ops -p test_session_resampling.py -v
python tools/research_ops/benchmarks/session_resampling_benchmark.py --output /tmp/session-resampling-benchmark.json
```

## Gate before adoption on future runs

Use the existing conservative `post_run` benchmark policy, not a speed-only leaderboard. The local helper benchmark is not automatically eligible for adoption: it lacks real scientific coverage, complete output/input/build authority and full-job receipts.

1. Freeze baseline and candidate build IDs, protocol, selected data hashes and complete expected census. Separate discovery experiments from implementation optimization.
2. Use identical fixed input shards spanning both sides, gaps, DST/session boundaries, censoring, duplicate triggers and endpoint ties. Independently compare full ordered outputs/counts/feature and artifact hashes, not only a final scalar. All attempted variants, failures and costs remain visible.
3. Measure isolated baseline/candidate pairs, cold and warm, on equivalent resources with reversed order, bounded repeats, measured process-tree RSS, compilation/cache status and I/O bytes. Record end-to-end plus substep timings.
4. Require exact scientific parity, complete coverage, memory budget and no regressions under the existing policy. Any failure → reject or investigate; no hidden retries or cherry-picked fastest run.
5. Save proposal, benchmark evidence and decision. Promote only after an authorized gate, version the baseline, canary future runs and keep rollback. A proposal/checksum alone cannot authorize deployment.

## Make each future scientific run reduce uncertainty

Faster execution and more useful experiments are different objectives. A research run cannot guarantee finding an edge. It can falsify a mechanism, identify insufficient support, distinguish censoring/control effects, or validate reproducibility. Those are useful outputs even when nothing wins.

Current recovered focals show relative/control-positive candidates but no joint absolute/control success under the existing gate. That means the next experiment should discriminate explanations; it is not permission to lower thresholds until a cell passes. Current matrix support is descriptive. Target-first rate is not net profitability: execution assumptions, spread/slippage/fees, risk and capacity would require a separately authorized protocol, not an inferred P&L.

### Two linked but separate memories

- **Technical learning:** runtime, memory, failure/recovery, cache hit rate, parity and coverage. May propose an implementation optimization. No candidate returns/P&L flow into this optimizer's selection score.
- **Scientific learning:** preregistered mechanism, evidence source, population, falsification criterion, support/uncertainty, controls, negative results, alias/cluster lineage and next discriminating experiment. Never changes a frozen manifest or self-labels exploratory evidence as validated.

Both link by run/build/input/protocol hashes and require custody/verification. The current technical outbox is pending-review local infrastructure; scientific canonical write and authenticated delivery remain future work.

### Research loop and mandatory output

1. **Recall before run:** canonical Brain/EdgeBrain knowledge plus existing article/research records and all previous negative/inconclusive trials. If a mechanism or methodological fact is missing, research primary sources, record applicability/limitations and propose a falsifiable hypothesis. Articles generate hypotheses, not proof of this market's edge.
2. **Ask one discriminating question:** specify what uncertainty the run can resolve and what result changes the next action. A repeated experiment with no new population, control, data, method or replication purpose is deferred instead of silently rerun. A previous null does not ban replication after meaningful changed conditions.
3. **Preregister an experiment charter:** mechanism, primary estimand, population/session/source, controls, minimum support, uncertainty method, multiple-testing ledger, costs/budget, fixed decision gates and bounded stopping rule. Include warmup/formation history so shards cannot leak future data or break semantics.
4. **Separate stages:** cheap source/schema/support checks → exact discovery screen on eligible research data → replicated shortlist by stable hypothesis cluster → locked validation on untouched future/authorized data → economic feasibility only under its own approved execution protocol. A reduced future screen is a NEW experiment, not an equivalent replacement for today's full-grid census. Coverage of skipped hypotheses is declared, never marked complete.
5. **Pair controls and uncertainty:** compare real/control under shared eligible context; distinguish `no_signal`, unresolved/censored, low-support and evidence-against-mechanism. Session-block resampling preserves within-session dependence but does not magically make sessions/regimes independent. Predeclare appropriate dependence blocks and lookback/embargo; inspect sensitivity on eligible development data.
6. **Count the whole search:** retain all tried protocols and nominal definitions plus semantic aliases/effective clusters. Millions of overlapping cells are not millions of independent observations. Pointwise intervals are not global significance. Choose a justified hierarchical/family-level multiplicity procedure before selection. Do not apply DSR to target-first rates without a valid return-series Sharpe estimand.
7. **Close with a decision:** `evidence_against`, `inconclusive_low_support`, `inconclusive_censoring`, `relative_only`, `needs_replication`, `validation_eligible`, or `validated_under_protocol`. State why, preserved uncertainty and next action. Abstention is valid; do not force a winning cell or an optimization.
8. **Choose next run by marginal learning per cost:** prioritize unresolved high-value mechanisms and tests that separate rival explanations, with dependency readiness and cost as tie-breakers. Until a probabilistic model is calibrated, call this a rubric, NOT numerically estimated information gain or probability of edge. Reserve a preregistered exploration budget to avoid a self-reinforcing shortlist.

Backtest-overfitting research explicitly warns that repeated trials and hiding unsuccessful trials distort conclusions; holdout alone does not account for the search. Preserve the ledger and keep today's holdout closed. CSCV/PBO is a possible later analysis only with suitable comparable time-series outputs and a preregistered dependence-aware design, not something computed from the current aggregate target rates. Reference: https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf .

## Deliverables and next implementation priority

Implemented now: exact local resampling helper, nine tests, reproducible synthetic benchmark, reconciled timing analysis and this continuation design. Not implemented: full longevity batch kernel, real-MNQ parity benchmark, Kaggle adoption, scientific charter enforcement, canonical scientific writer, calibrated information-gain scoring or autonomous deployment.

Next: instrument a bounded future longevity shard, identify the dominant substep, implement one parity-preserving batch/reuse candidate and run the real-output regression suite. Independently add a validated experiment-charter admission gate linked to the existing queue and knowledge recall. Do not retrofit changes into the active focal.
