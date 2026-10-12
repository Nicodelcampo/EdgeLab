# Read-only cgroup-v2 accounting: multiprocess diagnostics, not RSS custody

## Why this milestone

The authenticated receiver intentionally accepts only fresh Linux SINGLE-PROCESS
ru_maxrss. Historical MNQ drivers spawned children; no authenticated whole-job
RSS was measured. Summing RUSAGE_CHILDREN or sampled /proc RSS would not recover
the simultaneous peak (and samples can miss short-lived descendants).

New `tools/research_ops/cgroup_telemetry.py` observes a kernel memory.peak counter
for an EXTERNALLY prepared fresh bounded job leaf. This is ACCOUNTED MEMORY,
including charged file cache/kernel memory, not summed RSS. Units remain a
separate `peak_accounted_memory_bytes` field/schema. No reader relabels it RSS,
imputes a configured cap as actual usage, or reconstructs old MNQ telemetry.
The existing authenticated receiver is unchanged and rejects either mislabeled
cgroup units or diagnostic-schema input even with a valid fixture signature.

## Implemented, fail-closed observation

- Fixed verified Linux cgroup2 mount; explicit non-root job leaf opened component
  by component with no-follow directory/file FDs; no subgroups accepted.
- Externally supplied execution identity SHA/source commit and exact finite
  memory.max <=4GiB, pids.max <=64; no automatic controller changes.
- Empty fresh start with zero peak/current/tasks/events; prior/shared group fails.
- Pinned directory dev/inode/controls, monotone peak/events, no frozen/changed
  state; inconsistent concurrent snapshots fail rather than inventing values.
- Kernel peak catches between-poll spikes; task count remains a sampled lower
  bound, explicitly NOT an exact peak count. Returning polls cannot mutate the
  internal event history. No process IDs or raw scope path are exported.
- Final group must be empty. Empty alone does NOT prove successful completion,
  exclusive job membership, absence of escape, or coverage before admission.
- OOM/max events or observed cap overshoot produce LIMIT_EVENT_DIAGNOSTIC_NOT_
  SUCCESS, preserving measured values. Kernel limits can transiently overshoot;
  observed peak is never clamped to cap. Context exit/errors close FDs, not jobs.
- No launches, signals, moves, creates, reset writes or process kills. No new
  executor, market action, canonical write, custody key or receiver permission.

Every receipt says exclusive_scope_attested=false, whole_workload_coverage_
attested=false, workload_success_proven=false, authenticated_custody=false.
Kernel accounting is meaningful only for the precisely observed group; it is
not proof that every allocation/process of a job was placed there. Unobserved
privileged counter/controller changes and subgroup/membership movement cannot
be excluded by this read-only observer. It is a DIAGNOSTIC API, not a sandbox or
containment/security boundary, and not a production-success receipt.

## Required production integration (not fabricated here)

An externally authorized coordinator must provision an isolated delegated job
leaf, control its namespace/permissions, prevent escape and unreviewed joins/
resets, and admit the fixed source-pinned workload BEFORE its allocations. Moving
an already-running Python process after imports does not reconstruct previous
charges. The observer must stay outside the measured leaf. Whole-job lifecycle,
provider execution, input/build/census, exit status and clock require independently
reviewed custody and real trusted signing identities. No production keys exist.

A future signed resource receipt needs resource-kind-aware budget/observation
schema: ACCOUNTED_CGROUP_MEMORY cannot enter existing peak_rss_bytes. Updating
that schema/receiver is a separately reviewed migration, not allowed by a raw
counter or capability probe. Historic jobs remain RSS-unknown. Do not relaunch
them merely to fill a field, and do not use the root/shared group as a substitute.

## Data-free capability probe

`python -m tools.research_ops.cgroup_telemetry` reads ONLY mount/controller
availability and whether memory.peak is readable; its numeric value is discarded.
It hashes the process cgroup scope instead of exposing it. It performs no writes,
resource workloads, data access or private URL acquisition. Write-access hints
and interfaces do NOT establish delegation, isolation or whole-job coverage.

The local host has readable memory.peak, but no directory write-access hint and
no approved job leaf. A separately pinned private Kaggle probe will determine
interface availability there. Full result/status is recorded in latest state;
do not treat a COMPLETE kernel or directory-access hint as operational authority.

## Validation

492 Research Ops +18navigation +19canonical-store tests PASS; catalog
PASS_NAVIGATION_ONLY.34 new observer/reader tests cover mocked lifecycle and
real file-FD fixtures, not real isolated cgroup multiprocess load.2 additional
authenticated-closeout tests reject resource-unit/schema substitution. A real
read-only LOCAL capability probe passed, never claiming an approved leaf.
No remote CI, live coordinator, exact job-tree RSS or actual cgroup-contained
workload stress test is claimed. Existing analyzer/campaign and canonical
ledgers are untouched; source checkpoint is saved before the Kaggle probe.

## Actual Kaggle result and final validation

Private data-free kernel138364980 v1, output execution357743635 COMPLETE.
Source checkpoint74ecc896894f7c3d28e4d78738a68f666e8fa0ae and both program
hashes verified. Probe body took0.045927seconds (not scheduler/startup time).
Linux cgroup2 mount verified; memory.peak readable; memory controller available.
Mount READ-ONLY and directory write-access hint false. No delegated job leaf,
whole-job containment or usage measurement proven. Source contains no market
inputs/download URLs and had internet disabled. Nothing changed in cgroup state.

Consequences: the counter interface exists, but this kernel cannot provision an
isolated leaf by writing through that mount. An externally prepared scope could
in principle be readable even through a read-only mount; availability alone is
not evidence that such a scope is present. Do NOT use its root/shared/unattested
peak as the MNQ peak, change privileges or fake a new single-process receipt.
Continue preserving historical RSS as unknown. Next production prerequisite is
externally approved scope/lifecycle/provider custody, not another launch or a
sampling fallback presented as exact memory. Market computation stays Kaggle.

`CGROUP_KAGGLE_CAPABILITY_RESULT.json` preserves exact output; its offline review
verifies externally supplied receipt/checkpoint/program pins and rigid flags.
Even a fixture with writable hints returns execution_allowed=false.8new review
tests block autoapproval, source changes, unknown/RSS fields, integer/bool aliases
and invalid time/interface states. Final500Research Ops +18navigation +19canonical
store tests PASS; catalog PASS_NAVIGATION_ONLY. No remote CI or live isolated
multiprocess cgroup stress test claimed. Authenticated RSS receiver unchanged.
The code/plan and all evidence are in the same PR117; no merge or deployment.
