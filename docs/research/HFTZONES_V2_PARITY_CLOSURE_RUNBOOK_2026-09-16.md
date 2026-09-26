# HFTZonesNQ V2 — closure runbook

`PASS_CERTIFIED` is forbidden until input identity and output identity both pass.

Export from one replay/run: `hft_ticks_v2` keyed by `(instrument,contract,session_id,tick_seq)` with nanosecond timestamp, integer price ticks and volume; and `hft_zones_v2` keyed by `(instrument,contract,session_id,zone_seq)` with start/end tick sequence, ns timestamps, integer boundaries, metrics, parameter hash and source hash. No `INSERT OR IGNORE`; any insert failure aborts.

Certification: compile V2 in NT8; replay only pre-holdout sessions; export both tables atomically; hash DB and ordered extracts; reconstruct Python from `hft_ticks_v2` rather than a separately captured parquet; compare one-to-one by session and sequence with exact integer/ns equality; prove monotonic sequences, resets, no gaps and no duplicates; only then promote.

Mandatory abstention: different input ledgers; missing tick table; ms-only V2 comparison; comparator still reading V1 table; missing hashes; any unmatched or reused zone.

Aporte al referente: separates feed identity from detector identity so final parity is attributable to the engine.
