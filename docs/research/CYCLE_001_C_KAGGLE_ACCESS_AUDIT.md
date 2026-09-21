# CYCLE-001 — Agent C Kaggle access audit

**WORK-ID:** `CYCLE-001-C-KAGGLE-ACCESS-001`  
**Owner:** C  
**Reviewer:** D  
**Starting HEAD:** `84eea9758ca50fd07e07076dd346e0947bffcf3f`  
**North Star SHA-256:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Inventory observed

- Existing Worker: `edgelab-kaggle-agent-c`.
- Capability: `kaggleConnectionStatus`.
- Credential name present: `KAGGLE_API_TOKEN`; value was not read or logged.
- First hosted observation: HTTP `400`.
- Current verdict: `ABSTAIN_AUTH_OR_ENDPOINT`. This is not evidence that the token is invalid because endpoint semantics are not independently certified.
- No new Worker or credential was created for CYCLE-001.

## Measurement contract

Construct: ability of the existing hosted Worker to authenticate to one documented Kaggle API endpoint without exposing credentials.

Observable: sanitized HTTP status plus independently validated JSON response shape.

What it does **not** measure: dataset existence, ownership, immutability, downloadability, content, file count, row count, or SHA-256 agreement.

Fail-closed rule:

- `200` + valid JSON shape → `AUTHENTICATED_ENDPOINT_ONLY`;
- `200` + invalid shape → `ABSTAIN_RESPONSE_SHAPE`;
- `400/401/403` → `ABSTAIN_AUTH_OR_ENDPOINT`;
- network error → `ABSTAIN_NETWORK`;
- any other response → `ABSTAIN_UNCLASSIFIED`.

Even a successful authentication leaves `dataset_verified=false` and `hashes_verified=false`.

## Reproducible runner

```bash
python tools/kaggle_access_probe.py --self-test
python tools/kaggle_access_probe.py --status 400 --run-id CYCLE-001-FIRST-HOSTED
```

Every invocation emits a `RUN-LEARNING-PACKET`. Secret-bearing output keys are rejected.

## Gates

- `PREEXISTING_OUTCOME_EXPOSURE=YES`
- `HOLDOUT_CONTAMINATED_FOR_THIS_HYPOTHESIS=YES`
- `holdout_enabled=false`
- `outcomes_inspected=false`
- `promotion_ceiling=LESSON_CANDIDATE`

## Review request to D

Falsify status classification, response-shape assumptions, secret redaction, non-claims, and the distinction between authentication and `REMOTE_VERIFIED` custody.

## Aporte al referente

Converts an ambiguous HTTP 400 into a reproducible fail-closed measurement contract and reusable learning packet, without treating API access as scientific or custody evidence.
