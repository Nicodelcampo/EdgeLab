# EdgeLab — next-agent handoff (2026-09-19)

## Current branch state

Branch: `feat/edge-discovery-brain-foundation-20260919`
Last published functional/audit HEAD before this handoff: `fac9da5`.

Published commits:
- `8919a3b`: optional Playwright import guard.
- `86a831d`: six-state coverage mask, eligibility gate, and dependency triangulation.
- `a098c3a`: requested/effective model provenance and backend-based reviewer independence.
- `fac9da5`: grouped CI evidence and `csv_lines` contract review.

No external model provider was connected and no account or credential was created.

## CI state

Python 3.12, canonical locks, `--maxfail=1`:
- first failure: `tests/bridge/test_store_v2.py::test_zones_reconstructable_from_events_all_kernels`
- `KeyError: csv_lines`
- 454 passed, 25 skipped, 2 xfailed before stopping.

Grouped results:
- `tests/bridge`: 3 failed, 556 passed, 31 skipped, 2 xfailed.
- `tests/research`: 4 failed, 1 error, 692 passed, 5 skipped.
- edge-brain foundation: 5 passed.
- edge-factory schemas: 9 passed.
- new brain focused tests: 19 passed.

Evidence: `artifacts/audit/CI_GROUP_RESULTS_20260919.json`.

## `csv_lines` — next isolated commit

Diagnosis and decision are published in `docs/audit/CSV_LINES_CONTRACT_REVIEW_20260919.md`. Do not use `csv_lines=[]` and do not weaken the all-kernels reconstructability test.

Expected common API:

```text
run(...) -> dict(indicator, params, header, csv_lines, events, zones, params_line)
```

Actual `BigTrap2Absorption` API omits `csv_lines`, `header`, and `params_line`.

History:
- reconstructability invariant: `685c991`;
- `BigTrap2Absorption` joined the registry later: `1f8a5b6`;
- no intentional contract migration was found.

Latest inspection before handoff:
- `BigTrap2Absorption.log_event` already emits pipe strings into `events` (`seq|iso|type|payload`).
- its `ZONE_CREATED` payload contains `zone_id`, `lo`, `hi`, side, volume, score, and causal availability.
- lifecycle events include `ZONE_TOUCHED`, `ZONE_INVALIDATED`, and `ZONE_EXPIRED`.
- the canonical store reconstructs through `oracle.parse_records`.
- `oracle._detect_indicator` currently does **not** list `BigTrap2Absorption`; verify `_parse_pipe` indicator detection before editing.

Required acceptance criterion: direct zone-core digest must equal the digest reconstructed through the canonical event parser. Add a focused regression first, implement a real serializer/parser path, run only `tests/bridge/test_store_v2.py`, then all `tests/bridge`.

## Other CI families — separate commits

Do not mix these with `csv_lines`:
1. ULP candidates missing from `tools/ulp_sweep_baseline.json`; measure them before sealing.
2. `GexLevels.cs` lacks required `version=` metadata.
3. Research failures include worktree/data-root behavior, F0/F22 structural output/provenance, and `test_placebos_and_gates`.

## Custody dependency

Audit branch still needs the rectifier output committed. Do not synchronize custody into this branch until the generated manifest passes all 15 reconciliation tests. NQ 09-26 remains `BLOCKED_BY_CUSTODY` until real remote presence, download, hash, schema, monotonicity, and holdout gates all pass.

## Non-negotiable rules

- Do not open/profile/cross holdout `1782856800000000000`.
- Missing periods are not zero activity.
- No contract concatenation without certified rolls.
- LLM output is non-evidentiary and never `VALIDATED_RESULT`.
- Generator and reviewer effective backends must differ.
- No provider connections or account creation yet.
