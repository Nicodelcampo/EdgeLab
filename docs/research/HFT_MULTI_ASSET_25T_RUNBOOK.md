# HFT V2 multi-asset · 25 ticks · runbook local

Builds viewer bundles from canonical F2 tick parquet. The certified NQ kernel is not modified. Its mechanics are exposed through `hftzones_universal`; parity and NQ volume calibration are never transported implicitly.

Canonical holdout: `1782856800000000000` (`2026-06-30T22:00:00Z`).

## Plan contract

The local operator must derive session windows and hashes from the sanitized custody/roll manifests. The builder does not guess either one.

```json
{"holdout_boundary_ns":1782856800000000000,"entries":[{"asset_id":"GC_0626_25T_HFT","instrument":"GC","contract":"GC 06-26","parquet":"E:/EdgeLab/data/nt8/GC_parquet/GC_06-26_ticks.parquet","expected_sha256":"<64 hex from custody manifest>","profile":"NQ_LITERAL_TRANSFER","parity_status":"PARITY_ABSTAIN","sessions":[{"trade_date":20260601,"start_utc_ns":0,"end_utc_ns":0,"prev_session_close_ticks":null}]}]}
```

`prev_session_close_ticks` is mandatory and explicit. `null` is allowed, but the manifest records `ABSTAIN_MISSING_PREV_SESSION_CLOSE`; the first tick then cannot reproduce NT8's cross-session comparison.

## Commands

```powershell
python tools/build_multiasset_25t_hft_bundles.py --plan artifacts/hft_multiasset/local_plan.json --out viewer/nt8_bridge/bundles --dry-run
python tools/build_multiasset_25t_hft_bundles.py --plan artifacts/hft_multiasset/local_plan.json --out viewer/nt8_bridge/bundles
```

## Gates

Source SHA-256 must match; F2 schema must load; windows are explicit/non-overlapping/preholdout; 25t and HFT reset per session; zones require `origin <= end <= available`; candles are monotonic; non-abstain parity requires an evidence SHA-256.

Outputs per contract: `<asset_id>.json`, `<asset_id>.manifest.json`, and `multiasset_hft25_catalog.json`. Merge the catalog into the existing viewer manifest without deleting legacy assets.

Outside exact certified evidence the status remains `ENGINE_PORTABLE / PARAMETERS_UNCALIBRATED / PARITY_ABSTAIN`. Continuous assets must merge already-computed per-contract zones; HFT state must never cross a roll.
