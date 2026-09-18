# HFT V2 headless export correction

Status: `PATCH_READY_REQUIRES_NT8_COMPILE_AND_REPLAY`.

Apply and validate:

```powershell
python tools/apply_hft_v2_headless_patch.py
python tools/validate_hft_v2_export_readiness.py
git diff --check
```

Compile with `ModoExportacionPuro=true`. Preserve the existing partial SQLite by renaming it and use a new empty DB for the complete replay. Set Playback with the date picker rather than ambiguous typed locale strings: 2026-06-02 00:00:00 through 2026-06-12 23:59:59, and verify From < To.

The replacement partial census filters NT8 zones to the tick prefix actually present. It no longer labels all 955 June-5 zones as verified when only 366 were covered. It explicitly records that `available_ts_ns` was not compared. Partial prefixes can never emit global `PASS_CERTIFIED`.

Aporte al referente: removes WPF drawing from oracle export and prevents interrupted prefixes from being presented as full-session parity.
