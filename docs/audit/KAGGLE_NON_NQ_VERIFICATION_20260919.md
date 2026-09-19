# Kaggle non-NQ verification — 2026-09-19

## Result

The ten non-NQ canonical tick datasets currently expose all 51 expected contract-month Parquet files. Their published `files.sha256` entries match the 51 `source_sha256` declarations in the reconciled manifest with zero missing files, extras, or digest mismatches.

This is **remote listing plus published-digest evidence**, not download proof. It does not promote any file to `REMOTE_VERIFIED`; full downloads and independently recomputed SHA-256 remain required.

## Verified scope

- Instruments: 6B, 6E, 6J, ES, GC, MBT, MES, MNQ, YM, ZB.
- Contract files: 51.
- Rows declared by the manifest for this scope: 896,546,782.
- Source bytes declared by the manifest for this scope: 14,725,073,511.
- Every dataset displays the required partial-coverage, non-continuous, no-certified-roll, fail-closed metadata and `STRICT_LESS_THAN (0 holdout rows)`.

Machine-readable evidence is in `artifacts/audit/EDGELAB_KAGGLE_NON_NQ_VERIFICATION_20260919.json`.

## NQ exclusion and regression

NQ is deliberately excluded. Kaggle version 5 currently contains only:

- `NQ_09-26_ticks.parquet`
- `README.md`
- `files.sha256`

Its version history reports `+1 new, -4 removed`, so the upload replaced NQ 03-26, 06-26, 09-25, and 12-25 instead of adding 09-26. NQ remains reconciliation-required until one current version contains all five Parquet files and each file passes independent download and SHA-256 verification.
