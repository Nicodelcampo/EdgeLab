# HFT causal certification hardening — 2026-09-17

## Adjudication

The 2026-09-16 shared-replay result is preserved as evidence: 5,438 NT8 rows and 5,438 Python rows matched on every field actually compared.  The label `PASS_CERTIFIED` was broader than the implemented comparison and is not propagated downstream.

Current precise status:

```text
PASS_EXACT_ON_COMPARED_FIELDS_SINGLE_SHARED_REPLAY_NOT_FULLY_CERTIFIED
```

## Defects fixed

1. The corridor adapter previously preferred `end_ts_ns` over `available_ts_ns`. V2 now requires and uses `available_ts_ns` exclusively.
2. V2 requires exact session, contract, zone sequence, parameter hash, source hash and termination reason.
3. `available_ts_ns < end_ts_ns` is rejected.
4. V1 and V2 rows cannot be mixed in one bundle.
5. Legacy availability is labelled diagnostic and cannot inherit V2 parity status.
6. Fractional timestamps are rejected instead of being rounded through float conversion.
7. The visual configuration score is explicitly a display heuristic, not scientific model selection.
8. A hardened SQLite preflight now checks schemas, sequence continuity, timestamp monotonicity and causal availability.

## Remaining certification blocks

- `termination_reason` must be exported by NT8 and compared against Python.
- Every exported metric, rather than the historical subset, must be included in the exact comparison.
- The historical comparator carries `prev_session_close_ticks` across contract transitions. Multi-contract certification therefore abstains until an explicit reset is implemented and independently tested.
- `END_OF_INPUT` cannot be backdated to the last tick. It must become `END_OF_SESSION` with an explicit close timestamp or `CENSORED_END_OF_INPUT` and be excluded from certified causal visibility.
- The 5,438-zone SQLite must be rerun through the hardened preflight and the future full-field comparator.

## Safety

No outcomes, returns, P&L or holdout data were used. No historical evidence file was rewritten. The narrower status is intentionally conservative.
