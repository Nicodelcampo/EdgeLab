# MNQ local closeout producer: technical-only receipt projection

Status: implemented and tested locally; NOT a deployed Kaggle hook, remote attestation, canonical-memory writer or optimization activation path.

## What is implemented

`tools/research_ops/mnq_closeout.py` reads four externally pinned JSON receipts: campaign status, independent review, timing evidence and artifact inventory. It requires the explicit contract, scientific scope and frozen scientific-code commit. Bounded no-follow reads, input checksums, inventory/state binding, terminal semantic state, exact completed census and serial stage-timing checks fail closed.

The output is a narrow technical projection: coverage counts, wall/stage time, receipt hashes and declared code binding. It does not export candidates, target rates, winners, P&L or research conclusions. Focal completion means completion of the focal scope, even if the same contract's matrix is pending; it never means global campaign completion.

The independent-review receipt is a prerequisite. This module does not repeat the scientific auditor or verify every underlying scientific artifact. Checksums verify bytes, not the publisher's identity or source permissions. The caller must separately authenticate acquisition/custody and the execution-to-input/build binding.

## Missing measurements must not become invented learning

`build_mnq_envelope` needs an external execution identity, a positive measured peak RSS and a pinned memory-measurement receipt. If any are absent, it returns `BLOCKED_MISSING_MEASUREMENTS_OR_BINDING` and emits no envelope. It does not replace missing RSS with zero, a cap, local-host measurements or a synthetic number.

The real-receipt diagnostic covers two focal and two matrix bundles already independently reviewed. All four pass local projection validation and are blocked from envelope production because verified execution/input/build identity, measured RSS and its measurement receipt are not available to this adapter. Pins are derived from locally reviewed bytes, not signed remote custody. No real bundle was ingested into the learning outbox or canonical Brain.

See `MNQ_PRODUCER_REAL_RECEIPT_DIAGNOSTIC.json`.

## API and trust boundary

1. A trusted coordinator acquires receipts and supplies external pins, expected contract, scope and scientific-code commit.
2. `inspect_mnq_closeout(...)` verifies local receipts and returns a sealed technical projection. A projection digest is integrity metadata, NOT authorization. Keep the coordinator-to-builder call in the same trusted process; do not accept a user-resealed projection as authenticated evidence.
3. `build_mnq_envelope(...)` gates on complete, externally bound measurements. Its output remains a local candidate, NOT remote authority.
4. `write_mnq_envelope(...)` exclusively writes a bounded local file. It neither enqueues nor delivers it. A synthetic end-to-end test verifies compatibility with the existing local importer and duplicate/no-op behavior.
5. The existing outbox keeps drafts review-pending. Benchmark policy and parity/census/memory gates remain mandatory before any future proposal could be adopted.

The memory-receipt hash is a sidecar link, not validation of the receipt's contents or authenticity. Persist that sidecar with authenticated custody before production use. This adapter alone cannot authorize adoption.

## Reproducible local tests

```sh
python -m unittest discover -s tests/research_ops -v
python -m unittest discover -s tests/navigation -v
python tools/edgelab_catalog.py check --json
```

321 research-ops tests and 18 navigation tests passed locally, including 28 new producer tests. Catalog status is navigation-only. These are not a claim that remote CI, live ingestion or production deployment passed.

## Claude continuation

Do not change or restart the frozen jobs to retrofit telemetry. For future runs, add measured process-tree peak RSS, immutable execution-version and input/build/protocol bindings at the producer boundary; pin and preserve the evidence sidecar. Then implement authenticated acquisition/terminal hooks and a destination deduplication/ack protocol for the canonical technical-learning ledger. Test recovery, conflicts and duplicate delivery before enabling it.

A completed run should always be reviewed, but it need not produce an optimization. Preserve negative evidence and retain the baseline unless repeated bounded benchmarks demonstrate speedup with full scientific parity, complete coverage and no memory regression. The current producer is the receipt bridge, not that benchmark executor or automatic optimizer.
