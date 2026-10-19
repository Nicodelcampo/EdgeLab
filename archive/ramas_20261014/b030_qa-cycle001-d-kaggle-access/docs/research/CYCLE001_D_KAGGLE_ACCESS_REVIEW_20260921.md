# CYCLE-001 — Agent D adversarial review of Kaggle access contract

- Review: `REVIEW-CYCLE-001-001`
- D work: `CYCLE001-D-KAGGLE-REVIEW-001`
- Reviewed commit: `5a053204304cd2760e284233e53971a2de6afc63`
- Review branch: `qa/cycle001-d-kaggle-access-review`
- Scope: local/synthetic only; no hosted Worker call, credential access, dataset access, outcomes, validation or holdout
- Verdict: `CHANGES_REQUIRED`

## Reproduction

```bash
python tools/kaggle_access_probe.py --self-test
python tools/kaggle_access_probe.py --status 400 --run-id CYCLE-001-D-BASELINE
python tests/qa/test_cycle001_kaggle_access_review.py
```

Baseline self-test passes 7 status cases plus one exact-key redaction case. The independent review suite executes four contract properties: one passes and three methods produce five failures.

## Findings

### D-C-001 — CRITICAL — response shape is not independently validated

`classify()` accepts a caller-supplied `json_shape_valid=True` without accepting or checking any response payload, endpoint identity or schema. Therefore `ProbeObservation(200, True)` produces `AUTHENTICATED_ENDPOINT_ONLY` even though the runner has no evidence of a Kaggle JSON response.

Required correction: move response-shape validation inside the runner. Accept a sanitized payload plus an explicit endpoint/schema identifier, validate required fields/types, and make the boolean an internal result that callers cannot assert directly. Until then, `200` must remain `ABSTAIN_RESPONSE_SHAPE_UNVERIFIED`.

### D-C-002 — CRITICAL — exception text can leak secrets

`assert_redacted()` scans dictionary keys but ignores string values. `network_error` is copied verbatim into the durable packet. Exception strings can contain authorization headers, signed URLs, query tokens or provider diagnostics. The adversarial string `Authorization: Bearer KGAT_REDACT_ME` is emitted unchanged.

Required correction: never persist raw network exceptions. Map them to a bounded enum such as `timeout`, `dns`, `tls`, `connection`, `http_client`, keep a local non-durable diagnostic if needed, and reject/redact secret-bearing substrings before serialization.

### D-C-003 — HIGH — key redaction is bypassable by normalization variants

Exact `key.lower()` matching does not reject `Authorization `, `api-key` or `Kaggle-Api-Token`.

Required correction: normalize keys by stripping whitespace and removing separators/non-alphanumerics before comparison; use a deny pattern that covers authorization, token, api key, password, secret, cookie and credential families recursively.

## What survived falsification

Even for a nominal `200`, the emitted packet keeps:

- `dataset_verified=false`;
- `hashes_verified=false`;
- `outcomes_inspected=false`;
- `holdout_enabled=false`;
- `promotion_ceiling=LESSON_CANDIDATE`.

The 400/401/403 and network classifications are fail-closed at the verdict layer. Authentication remains distinct from custody in the documented non-claims.

## RUN-LEARNING-PACKET

```txt
run_id / parent_episode: CYCLE001-D-KAGGLE-REVIEW-001 / CYCLE-001
code commit + dirty state: reviewed 5a053204304cd2760e284233e53971a2de6afc63; review artifacts uncommitted before push
dataset version + hashes: none; no dataset accessed
config/prompt hash: contract 1040fe7a74d058fb7525e84de4f8ae3f119318e25157f79b94f57f328648aabb
construct_id + measurement contract: KAGGLE-ACCESS-CERTIFICATION-V1
causal window and availability: not applicable; operational access probe only
cardinality / coverage / missingness: 4 review methods; 1 pass; 3 methods/5 subcases fail
result summary: CHANGES_REQUIRED
negative results: untrusted shape boolean authenticates; raw network error leaks secret text; three normalized key variants bypass denylist
triangulation agreement/disagreement: baseline self-test passes but adversarial suite contradicts completeness of shape validation and redaction
measurement failures: observable is not independently derived because caller supplies json_shape_valid
software/data defects: D-C-001, D-C-002, D-C-003
repairs attempted: none by reviewer; exact corrections specified for C
sensitivity / robustness: 200/true, raw exception secret, whitespace/hyphen/case key variants
new counterexamples: authenticated verdict without payload; secret in network_error; Authorization-space/api-key/Kaggle-Api-Token
new constraints/gates: no hosted execution or integration until all three defects are fixed and rerun by D
novelty class: MEASUREMENT_INVALID + SECRET_REDACTION_GAP
next best hypothesis: internal schema validator over sanitized Kaggle endpoint payload with bounded error enums
artifacts + hashes: adversarial test and this report; hashes recorded at checkpoint
hippocampus records emitted: counterexample requested to B under B-CYCLE001-LEARNING-PACKET-001
review status: CHANGES_REQUIRED
```

## Limits

This review does not assess the duplicated Worker, the correctness of a live Kaggle endpoint, credential validity, dataset existence, custody or file hashes. Those remain blocked by A's adjudication and independent evidence.

Aporte al referente: impide elevar un booleano declarado por el caller a autenticación y evita que errores de red conviertan secretos en artefactos durables; conserva los gates fail-closed que sí sobrevivieron.
