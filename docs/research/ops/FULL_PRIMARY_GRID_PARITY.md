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
