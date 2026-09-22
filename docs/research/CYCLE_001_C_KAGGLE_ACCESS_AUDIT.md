# CYCLE-001 — Agent C Kaggle access audit

**WORK-ID:** `CYCLE-001-C-KAGGLE-ACCESS-001`  
**Owner:** C  
**Reviewer:** D  
**Starting HEAD:** `84eea9758ca50fd07e07076dd346e0947bffcf3f`  
**North Star SHA-256:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Inventory observed

Read-only workspace census at 2026-09-21T12:18-03:00 found three Workers:

| Worker | Created | Capability | Cycle status |
| --- | --- | --- | --- |
| `edgelab-kaggle-access` (`01a0c0eb-ab1c-7942-b223-0384016535b3`) | 2026-09-20T22:24:25Z | four metadata/list/download-url capabilities reported by A | `QUARANTINED_NO_USE` |
| `edgelab-kaggle-agent-c` (`01a0c47c-fd21-78ac-ad94-a0e04209ca61`) | 2026-09-21T15:02:00Z | `kaggleConnectionStatus` | `SUPERSEDED_NO_USE`; first hosted observation HTTP `400` |
| `edgelab-kaggle` (`01a0c47e-c7f9-7fe0-ab70-7f90204f3188`) | 2026-09-21T15:03:58Z | `checkKaggleAccess` | `CANONICAL_HOSTED_BLOCKED` |

The credential name was observed only by name; no value was read or logged. HTTP `400` remains `ABSTAIN_AUTH_OR_ENDPOINT`. Agent A reports a pre-cycle HTTP `200` for the canonical Worker, but C does not promote that report to measured evidence without an exact durable run artifact.

No Worker or credential was created after CYCLE-001 activation. Agent A adjudicated the inventory without execution or deletion: canonical Worker remains hosted-blocked, duplicate is superseded/no-use, and the older access Worker is quarantined/no-use. Local/synthetic contract testing remains allowed; hosted execution remains forbidden.

## Measurement contract

Construct: ability of one adjudicated hosted Worker to authenticate to one documented Kaggle API endpoint without exposing credentials.

Observable: sanitized HTTP status plus independently validated JSON response shape.

What it does **not** measure: dataset existence, ownership, immutability, downloadability, content, file count, row count, or SHA-256 agreement.

Fail-closed rule after D-C-001/002/003 correction:

- only `200` + known endpoint ID + internally validated sanitized payload → `AUTHENTICATED_ENDPOINT_ONLY`;
- caller-supplied `json_shape_valid=true` is legacy/untrusted and cannot authenticate;
- `200` without internal endpoint-schema validation → `ABSTAIN_RESPONSE_SHAPE_UNVERIFIED`;
- `400/401/403` → `ABSTAIN_AUTH_OR_ENDPOINT`;
- network error → `ABSTAIN_NETWORK`;
- any other response → `ABSTAIN_UNCLASSIFIED`.

Even a successful authentication leaves `dataset_verified=false` and `hashes_verified=false`.

## Reproducible runner

```bash
python tools/kaggle_access_probe.py --self-test
python tools/kaggle_access_probe.py --status 400 --run-id CYCLE-001-FIRST-HOSTED
```

Every invocation emits a `RUN-LEARNING-PACKET`. Secret-bearing keys are normalized across case/whitespace/separators; secret-bearing values are rejected; raw network errors are reduced to bounded enums before persistence.

## Gates

- `PREEXISTING_OUTCOME_EXPOSURE=YES`
- `HOLDOUT_CONTAMINATED_FOR_THIS_HYPOTHESIS=YES`
- `holdout_enabled=false`
- `outcomes_inspected=false`
- `promotion_ceiling=LESSON_CANDIDATE`
- `hosted_execution=BLOCKED_PENDING_WORKER_ADJUDICATION`

## Review response to D

D reported `CHANGES_REQUIRED` on 3a90f888: D-C-001 caller-controlled shape boolean, D-C-002 raw exception leakage, and D-C-003 key-normalization bypasses. C corrected all three locally and reran D's exact four-test suite: 4/4 PASS. Baseline expanded to eight status cases plus normalized secret-value/key rejection. Hosted execution remains blocked.

## Custody incident — dataset publicly listable (2026-09-22)

Recorded from PR #48 head `68182282e613a33b9831f4b8fe51f3a9ff411f1c` commit declaration (not independently re-probed by C):

- Dataset `nicolasbuttaro/edgelab-l2-gc-bookmap-audit-20260921` was **publicly listable** (`isPrivate:false`) despite the authoring session reporting it private.
- The exposure was confirmed by an unauthenticated public-search listing; the dataset was deleted and recreated, then verified `403` without auth.
- Lesson for the measurement contract: **authenticated-session privacy reports are not evidence of privacy**. Any future visibility claim requires an unauthenticated probe.
- This incident is operational/custody metadata only: it does not verify dataset content, hashes, or REMOTE_VERIFIED status, and it does not unblock hosted execution.

```txt
packet_type: RUN-LEARNING-PACKET
run_id: CYCLE-001-C-KAGGLE-CUSTODY-INCIDENT-001
work_id: CYCLE-001-C-KAGGLE-ACCESS-001
construct_id: KAGGLE-DATASET-VISIBILITY-V1
source_ref: 68182282e613a33b9831f4b8fe51f3a9ff411f1c (commit declaration; unverified by C)
verdict: CUSTODY_CONTROL_FAILURE_REMEDIATED_UNVERIFIED
observation: dataset publicly listable despite private intent; remediation claimed (delete/recreate + 403 unauthenticated check)
negative_results: authenticated-session report disagreed with unauthenticated reality
new_constraints: visibility claims require unauthenticated probe; visibility != content/hash/custody verification
dataset_verified: false
hashes_verified: false
outcomes_inspected: false
holdout_enabled: false
preexisting_outcome_exposure: true
holdout_contaminated_for_this_hypothesis: true
promotion_ceiling: LESSON_CANDIDATE
next_action: D falsify visibility-probe contract if hosted probes are ever re-enabled; B ingest as Hippocampus lesson
```

## Aporte al referente

Converts ambiguous Worker/API state into a reproducible fail-closed contract and a three-Worker inventory without treating API access as scientific or custody evidence; records the public-dataset incident so privacy-by-report can never again substitute for privacy-by-probe.
