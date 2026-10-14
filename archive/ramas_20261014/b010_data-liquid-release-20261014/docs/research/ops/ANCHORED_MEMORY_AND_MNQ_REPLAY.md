# Existing operational memory and bounded MNQ technical replay

## Recovered actual memory, not a new ledger

At source commit `3d363492453b12e5da4a32d49d677fea57e3f367` the existing
`artifacts/hippocampus/kaggle_aggregates_20261009.jsonl` contains 10 canonical
records from two target-free technical episodes. Both historical anchors (5 and
10 records), the receipt and hash-chain tip were independently replayed.
`config/research_ops_operational_snapshot.json` pins all three original files.
They have NOT been modified or duplicated as another operational ledger.

The new `recall-anchored-brain` CLI calls the existing canonical replay/retrieval
interfaces against captured immutable bytes. It checks all anchors and census,
receipt agreement, explicit no-outcome episodes, closed binding and file hashes.
No append, queue initialization, approval or execution occurs. Retrieved text
remains untrusted operational context, not strategy evidence.

One recovered lesson: saving a Kaggle kernel does not prove its input mounts;
verify actual file identity and exact approved-session conservation first.
The separate MGC scientific JSONL has another format and is excluded. This small
operational snapshot is NOT complete scientific trial history, a live writer
destination, publisher authentication or an external latest/fencing witness.
The canonical article export is still absent; do not manufacture it or a ledger.

Example from repo root (pin copied from the externally reviewed binding):

```bash
python -m tools.research_ops.cli recall-anchored-brain . \
  config/research_ops_operational_snapshot.json 'input mounts session conservation' \
  --expected-binding-sha256 BINDING_SHA256
```

## Prespecified real-data technical replay

`tools/research_ops/benchmarks/mnq_resampling_replay.py` seals PLAN before running.
It uses only the completed MNQ09-26 primary-thinned event CSV and its manifest,
verified by byte size/SHA256 against the original artifact inventory. Private
rows and per-session counts remain inside Kaggle temporary storage. No ticks,
new detector pass, new outcomes, controls or recipe changes. No job is relaunched.

Fixed Cartesian scope: 60 cells, real/dedup75/endpoint0/visits1, landmarks2000/3000,
all five visit groups x all three speed groups x both gap policies, retaining
empty cells and all46 approved preholdout sessions. Exact seed17331 and10000
whole-session resamples reproduce the frozen analyzer expressions for wins,
resolved counts and pointwise quantiles. Candidate computes integer session
multiplicities once per pass, including that cost in both cold/warm timings.
Input counts, draw indices and each complete result are hashed; float/int parity
must hold across all pairs. No estimates or confidence-band values are exported.

Three fresh-process baseline/candidate pairs; second reverses order. Each process
runs cold then warm. OpenBLAS/OMP/MKL threads=1. Per-worker120seconds and4GiB
address-space cap; outer900-second deadline including acquisition. RSS is Linux
RUSAGE_SELF for each isolated worker including imports/input load, NOT historical
whole-job RSS. Cold here means first compute in a fresh worker after preparation,
not fresh market parsing/JIT. No assertion about complete pipeline parity or
longevity speed; independent substep profiling and broader parity remain pending.

Only a successful aggregate JSON may leave Kaggle. Launch uses private signed
URLs injected into a private kernel, never committed. They expire after72hours.
No production signing authority, adoption approval or scientific edge is inferred.
The old probe kernels edgelab-probe-mount-a/b/c can be deleted separately.

## Local validation

441 Research Ops tests (18 new snapshot tests and5 replay tests),18 navigation,
19 canonical hippocampus tests pass. Catalog PASS_NAVIGATION_ONLY. A separate
synthetic fresh-worker smoke passed exact hashes. Local tests do not constitute
remote CI or real-data performance evidence. See ANCHORED_MEMORY_TEST_EVIDENCE.json.

## Observed result (private Kaggle replay v1)

Kernel138361151, output execution357734641, source checkpoint
`4e3ecb3cdd2b005272547c3cec94b47de548e9c8`: COMPLETE. Identity-pinned original
CSV had68,499 primary-thinned rows; all46 sessions retained.60 cells including20
empty cells. Both algorithms produced the same complete-result digest across
all12 passes (3pairs x2methods x cold/warm), including pointwise-quantile bytes.

| Compute pass | Frozen median seconds | Candidate median seconds | Ratio of medians |
| --- | --- | --- | --- |
| First (cold worker) | 0.758649 | 0.224386 | 3.3810x |
| Second (warm worker) | 0.751016 | 0.222210 | 3.3798x |

Paired speedup range: cold3.21–3.88x, warm3.30–3.52x. Preparation4.31seconds;
outer elapsed13.63seconds including acquisition. Only3pairs on this CPU/image:
no confidence/performance guarantee beyond this fixed substep. Identical
Linux ru_maxrss counters150,224,896bytes give NO evidence of a memory reduction;
the process-creation counter may retain pre-exec inherited footprint. Not
historical whole-job telemetry or an authenticated custodian receipt.

`MNQ_RESAMPLING_REPLAY_AGGREGATE.json` preserves aggregate output unchanged;
`MNQ_RESAMPLING_REPLAY_INTERPRETATION.json` preserves provenance, exact hashes,
independent median cross-check and comparison scope. Nested aggregate JSON was
not tabular-profiler-readable; normalized12timing rows were profiled, no missing
or duplicate records, only the constant-RSS warning addressed above. Candidate
has NOT been wired into analyzer/driver and no frozen campaign was modified.
The next safe performance milestone is actual longevity substep profiling and
broader independent output parity, not a claim of3.38x whole-job acceleration.
