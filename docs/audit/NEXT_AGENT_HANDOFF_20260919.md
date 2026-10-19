# EdgeLab — next-agent handoff (2026-09-19)

## Non-negotiable rules

- Do not open, profile, or cross the holdout (`1782856800000000000`, strict `<`).
- Missing periods are not zero activity.
- Do not concatenate contract-month slices without a certified roll.
- LLM output is never computed evidence and never has status `VALIDATED_RESULT`.
- Do not expose tokens or credentials.

## Track A — custody manifest (first action)

Branch: `audit/edge-discovery-factory-foundation-20260919`

Published evidence:
- `e7c1646`: real Kaggle listing; NQ 09-26 absent.
- `2888805`: deterministic rectifier and 15 reconciliation tests.

The generated manifest is **not yet committed**. Do not claim reconciliation complete until this exact sequence passes from a clean checkout:

```bash
git checkout audit/edge-discovery-factory-foundation-20260919
python tools/rectify_kaggle_manifest.py
python -m pytest -q tests/test_kaggle_manifest_reconciliation.py
git diff --check
```

Then commit **only the generated custody outputs** in a separate commit, principally:

```text
artifacts/audit/EDGELAB_KAGGLE_CANONICAL_MANIFEST.json
```

Required postconditions:
- `migration_status = MIGRATION_CANONICAL_RAW_COMPLETE_EXCEPT_NQ_09_26`
- 55 remote-listed/verified contracts pending download-proof semantics
- 1,009,464,519 rows
- 16,918,433,631 source bytes
- `NQ_09-26 = BLOCKED_BY_CUSTODY`
- no unsupported `downloaded_sha256`
- `viewer_bundle_snapshot.status = AUTHORIZED_PENDING_BUILD_AND_UPLOAD`
- `artifact_role = AUXILIARY_VERSIONED_VIEWER_SNAPSHOT`
- `canonical_source = false`

Important distinction: the remote inventory proves presence and byte size, not content. Only a real download plus recomputed SHA-256 may establish download provenance.

## Track D

Do not upload the 25t snapshot until the corrected manifest is committed and green. Authorization permits only 147 canonical `.json.zst`, 147 corresponding manifests, `manifest.json`, `README.md`, and custody hashes. No `.js`, no `*_CONT`, no 183 general-inventory JSON files.

## Coordination

Do not rewrite `e7c1646` or `2888805`. Synchronize with the brain/PR branch only after the generated manifest is published and verified.
