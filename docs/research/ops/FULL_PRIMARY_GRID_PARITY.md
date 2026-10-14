# Prespecified full primary-grid replay (not a new scientific experiment)

Follow-up to the60-cell resampling test. Source baseline system241cc0c;
frozen analyzer9125197dc6098100459f36a3d90a5c7b7aa4f9c0. Reuse only the completed
MNQ09-26 primary-thinned events and manifest and independently stored original
primary-effects.csv. All files size/hash pinned to original artifact inventory.
Private event rows remain in Kaggle; no .bin, detector, new outcomes or holdout.

Fixed COMPLETE grid:3dedups x2origins x7landmarks x3endpoints x3visit definitions
x5visit groups x3speed groups x2gap policies =11,340rows. Preserve all46sessions,
zero counts and empty cells. No sampling favorable cells. Frozen seed17331,
10,000 whole-session draws. Existing integer multiplicity helper computes bands.

Compare every row, in original order, to the separately emitted frozen CSV:
all9identity fields,7integer fields and3floating fields (point estimate/lower/upper).
Integers exact; floats exact IEEE bytes after Python CSV round-trip; missing
values must match, never replaced by zero. No widening tolerance after failure.
This tests count formation AND resampling against already stored evidence, not
only two algorithms fed the same prepared counts. No estimates get exported.

Instrument identity/input load, draw/weight formation, cell count formation,
resampling+metrics and reference comparison/hash. Candidate-only timing is NOT
comparable to historical full-job wall time. No new broad speedup ratio will be
inferred. Scope excludes matched contrasts, incremental models, other families,
primary thinning, detector, feature generation and ticks; full pipeline parity
and actual longevity detector profile remain explicitly false.

One private technical replay, maximum900seconds including acquisition and a
4GiB address-space cap on its one Python process. Driver enforces outer alarm;
temporary files removed, aggregate-only output. No signer/receiver approval,
canonical writer or execution coordinator added. No adoption or merge.

Local447Research Ops +18navigation +19canonical store tests PASS; catalog
PASS_NAVIGATION_ONLY.6new tests cover full grid/empty rows, unknown sessions,
frozen formula parity and exact float/reference mismatches. No remote CI claim.
Actual launch/results are recorded separately in LATEST_CONTINUATION.json and
FULL_PRIMARY_GRID_PARITY_PLAN.json. Check status before any repeat.

## Observed result

Private kernel138362721 v1, output execution357738247, source checkpoint
8d08c657ac8eba76abe9959bd80a037f97e466a6 COMPLETE. All11,340rows, all19fields,
215,460field comparisons PASS.1,128empty rows preserved;46sessions and68,499
already-thinned input rows retained. Exact point estimates and bands match the
original CSV after round-trip; no tolerance or outcomes exported.

| Technical replay stage | Seconds |
| --- | --- |
| Input load / identity | 0.565102 |
| Frozen draws / weights | 0.010442 |
| Count formation | 28.178636 |
| Resampling / metrics | 42.218542 |
| Original reference compare / hashes | 1.195306 |

Internal wall72.217170seconds, outer75.284791seconds including acquisition.
Unassigned0.049141seconds. Self high-water199,852,032bytes for this technical
replay ONLY; not historical job RSS or signed custody. No claim about actual
longevity detector, whole campaign speed, cold/warm full-grid pairs or all five
contracts. Largest measured replay stage is resampling/metrics, not evidence of
a detector bottleneck. No baseline full-grid timing measured in this execution.

`FULL_PRIMARY_GRID_AGGREGATE.json` preserves exact aggregate result bytes;
`FULL_PRIMARY_GRID_INTERPRETATION.json` preserves scope, provenance, checked
headline and stage comparison. Nested JSON could not be tabular-profiled; all
five normalized timing rows were profiled without duplicates/missing values.
The chart uses these same direct counters and no hidden performance estimate.

New offline `review_primary_grid_receipt.review` rejects incomplete grid/fields,
unknown fields, altered source/plan pins, bool/int plan aliases, missing/false
parity, self-promotion and impossible stage/resource accounting. It requires
externally supplied program/receipt/checkpoint hashes. PASS is STRUCTURAL_SOURCE_
PINNED_TECHNICAL_RECEIPT_NOT_CUSTODY, not independent event recount or approval.
456Research Ops +18navigation +19canonical tests pass; catalog unchanged.9new
receipt tests supplement6new grid tests. No remote CI claim.

This execution was MANUAL through Kaggle MCP, not proof of a live supervisor,
queue budget reservation, authenticated producer or24x7deployment. Original
analyzer/driver, scientific evidence branch and canonical ledgers unchanged.
Preserve candidate isolation; full-pipeline coverage and reviewed integration
remain pending. Source/reviewer keys, canonical live destination, complete
scientific history, SSRN export and latest/fencing witness remain unbound.
