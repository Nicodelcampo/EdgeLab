# HFTZonesNQ → causal corridor integration

Status: `HARDENED_AWAITING_V2_REEXPORT_AND_LOCAL_DATA_RERUN`.

The original implementation is superseded by `HFT_CAUSAL_CERTIFICATION_HARDENING_2026-09-17.md` on the hardening branch.

## Corrected invariants

- V2 availability uses `available_ts_ns`, never `end_ts_ns`.
- V2 identity, provenance and termination fields are mandatory.
- V1 and V2 inputs cannot be mixed.
- Legacy bundles are diagnostic and cannot inherit V2 parity status.
- The canonical holdout boundary is `2026-06-30T22:00:00Z` (`1782856800000000000` ns), not midnight UTC.
- Every parquet row group must prove `max(timestamp) < holdout` before any row is decoded.
- Visual ranking remains a target-free display heuristic and is prohibited as scientific model selection.

## Required execution

```powershell
python -m pytest tests/research/test_hft_corridors.py tests/research/test_hft_corridor_bundle_guard.py -v
python tools/validate_hft_v2_certification.py --db data/nt8_oracles/hft_zones_nq_v2.sqlite --instrument "NQ JUN26" --out artifacts/hft_v2_hardened_preflight.json
python tools/build_hft_corridor_bundle.py --zone-mode V2 --zones data/nt8_oracles/hft_zones_v2_export.csv --ticks E:/EdgeLab/data/nt8/NQ_parquet/NQ_06-26_ticks.parquet
```

The existing V2 export does not include `termination_reason`, so it must fail closed until NT8 re-exports that field. The historical 5,438/5,438 result remains preserved but is labelled `PASS_EXACT_ON_COMPARED_FIELDS_SINGLE_SHARED_REPLAY_NOT_FULLY_CERTIFIED`.

No outcomes, P&L or holdout access are authorized.
