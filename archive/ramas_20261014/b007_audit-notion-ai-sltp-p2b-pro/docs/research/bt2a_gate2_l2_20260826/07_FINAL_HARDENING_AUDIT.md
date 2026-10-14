# Gate 2 / Gate L2 final hardening audit

Date: 2026-08-26  
Implementation tip audited: `6d38294777c103cf6db78a6734f6283032a4cb56`

## Scope

This note records implementation hardening only. No P2-A, P2-B, or Gate-L2 outcome run was authorized or executed. The Gate-2 spec remains proposed and unfrozen.

## P2-A

Implemented and not run:

- canonical 234-session Gate-1 Event Store as the only event input;
- checkpoint, sample-registry, input-registry, event-payload, and per-event identity validation;
- full input-Parquet SHA-256 verification;
- explicit reassertion that every K_ABS and K_BT2 fill remains eligible under the frozen Gate-1 path cache;
- endpoint-inclusive first passage for TP, SL, and TIMEOUT;
- 16 primary tick-horizon cells with Holm correction over the K_ABS-minus-N_RAND family;
- 12 secondary clock-horizon cells, reported separately and explicitly descriptive/unadjusted;
- strict-JSON serialization when a session/cell contains only TIMEOUT outcomes (`p_tp_given_resolved = null`).

## P2-B

Implemented and not run:

- canonical Event Store identity and input-Parquet SHA-256 validation;
- nanosecond/source-row causality;
- first executable signal wins and one open position at a time;
- entry on the next executable observation and exit strictly after the fill observation;
- target, stop, time stop, hard session close, and data-edge handling;
- explicit GC tick value, commission per side, and auditable commission source;
- ideal/base/adverso/severo cost scenarios;
- session-cluster inference for net ticks and net USD, both per eligible signal and per trade;
- the surface is labelled descriptive post-outcome sensitivity with no cell-selection authority.

## Gate L2

Implemented validation, but extraction evidence and power remain unresolved:

- three-way `model_id` equality across manifest, model, and target-free report;
- stable code commit and clean-worktree checks;
- required labels, model, report, manifest, and `features/*.parquet` artifacts;
- declared-versus-actual SHA-256 checks for every required output and every feature Parquet;
- strict causal join `available_source_row < event_source_row`, with no timestamp fallback;
- state mapping, coverage, physical-order, duplicate, and minimum-session gates;
- degenerate/constant width checks serialize as `correlation = null` and fail closed;
- context interaction uses CME-session cluster resampling and a CME-session sign-flip null, preserving sessions that contribute to both context groups;
- low-power cases abstain before interpreting outcomes.

## Verification completed

Local executable checks:

```text
REMOTE_LOGIC_MIRROR_COMPILE_PASS
P2A_ALL_TIMEOUT_JSON_PASS
L2_CLUSTER_BOOTSTRAP_PASS
P2A_ELIGIBILITY_REASSERTION_PASS
P2A_16_PRIMARY_12_SECONDARY_STRUCTURE_PASS
P2B_FOUR_METRICS_STRUCTURE_PASS
LOCAL_SECRET_SCAN_PASS
```

The repository-level GitHub secret-scanning endpoint was unavailable because GitHub Advanced Security is not enabled. A local pattern scan over the actual changed source files found no private keys or known GitHub, AWS, Slack, or OpenAI token formats and no generic hard-coded secret assignment.

## Remaining blockers

1. Rebuild and reconcile all 234 canonical Event Store checkpoints and verify totals exactly: K_ABS = 16,940 and K_BT2 = 5,262.
2. Review and freeze `specs/bt2a_gate2_first_passage_v1.json` only after explicit human review.
3. Confirm GC tick value and per-side commission with an auditable source.
4. Receive separate explicit authorization tokens before P2-A or P2-B execution.
5. Ingest and review Claude Code's `LOCAL_AUDIT_RESULT.json` and `LOCAL_AUDIT_RESULT.md`.
6. Classify the existing dirty Gate-L2 extraction formally; do not use it as clean evidence.
7. Obtain a common L1/L2/event capture with shared `source_row`, coverage >= 0.99, and at least 40 effective sessions in each primary context group.
8. Expose or derive `zone_width_ticks` in the joined Event Store without post-event information.
9. Review the original L2 extractor implementation before selective integration; do not copy it blindly.
10. Do not use `--resume` on the old partial sweep.

## Current decision

```text
P2-A = IMPLEMENTED_NOT_RUN
P2-B = IMPLEMENTED_NOT_RUN
GATE2_SPEC = PROPOSED_NOT_FROZEN
GATE1_EVENT_STORE_234 = NOT_REBUILT_YET
GC_COST_IDENTITY = NOT_CONFIRMED
GATE_L2_VALIDATION = IMPLEMENTED
GATE_L2_EXTRACTION_EVIDENCE = PENDING_LOCAL_AUDIT
GATE_L2_SAMPLE_POWER = NOT_READY
NEW_P2_OR_L2_OUTCOMES_OPENED = false
EDGE_DECLARED = false
```
