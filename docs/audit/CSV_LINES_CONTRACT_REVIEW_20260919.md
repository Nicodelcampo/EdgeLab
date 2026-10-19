# `csv_lines` contract review — 2026-09-19

## Status

`CONTRACT_REGRESSION_CONFIRMED — FIX NOT YET APPLIED`

## Expected API

`edgelab.bridge.indicators.REGISTRY` documents:

```text
run(...) -> dict(indicator, params, header, csv_lines, events, zones, params_line)
```

`tests/bridge/test_store_v2.py::test_zones_reconstructable_from_events_all_kernels` computes a zone digest directly from `zones`, reconstructs it from `csv_lines` through `store.zones_core_digest_from_events`, and requires equality. `csv_lines` is a reconstructable event artifact, not a cosmetic field.

## Actual API

Six registered kernels expose the documented keys. `BigTrap2Absorption` returns `indicator`, `params`, `zones`, `n_zones`, and `events`; it omits `csv_lines`, `header`, and `params_line`. Its internal `log_event` emits strings into `events`, but those strings have not been shown to reconstruct its zone core through the canonical oracle parser.

## History

- Store-v2 reconstructability test: commit `685c991`.
- `BigTrap2Absorption` registered later: commit `1f8a5b6`.
- The documented common contract remained unchanged.
- The initial kernel omitted event serialization; later changes added `events` but did not restore the shared API.

No code or documentation shows an intentional contract migration. This is an integration omission.

## Reproduction

Python 3.12 with canonical locked dependencies:

```text
KeyError: 'csv_lines'
tests/bridge/test_store_v2.py:152
```

`--maxfail=1`: 454 passed, 25 skipped, 2 xfailed before the failure. Full `tests/bridge`: 3 failed, 556 passed, 31 skipped, 2 xfailed.

## Decision proposal

**Restore compatibility, but not with a fictitious empty value.**

1. Give `BigTrap2Absorption` a canonical serializer producing `header`, `csv_lines`, and `params_line` from actual lifecycle events.
2. Normalize zones to the fields required by the oracle/store path: `id`, `top`, `bottom`, `created_ms`, optional `ended_ms`, `state`, `touches`.
3. Require digest parity between direct zones and event reconstruction.
4. Add a focused kernel regression test, then re-run `tests/bridge`.

Do not skip this kernel and do not set `csv_lines=[]`: either change would hide the regression. Replacing CSV with a versioned canonical event artifact may be a future all-kernel schema migration, not the minimal repair.
