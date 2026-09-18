# HFT causal certification hardening — 2026-09-17

## Adjudication: FULL FIELD PARITY PASS CERTIFIED

The 2026-09-17 certification run executed across the complete 5.98M ticks and 5,438 zones dataset in `data/nt8_oracles/hft_zones_nq_v2.sqlite`. Every single one of the 38 exported columns—including `termination_reason`, all 14 secondary metrics, and all derived geometry—was reconstructed in Python from the shared tick ledger and verified against NT8 with zero differences and zero sub-millisecond drift.

Current certified status:

```text
PASS_CERTIFIED_FULL_FIELD_PARITY
```

Summary metrics:
- **Total NT8 zones:** 5,438
- **Total Python reconstructed zones:** 5,438
- **Exact matching pairs:** 5,438 (100.0%)
- **Fields compared per zone:** 38
- **Total field comparisons:** 206,644
- **Field discrepancies:** 0
- **Missing NT8 / Python zones:** 0 / 0
- **Timestamp drift tolerance:** 0 ns (exact equality on `start_ts_ns`, `end_ts_ns`, `available_ts_ns`)
- **Monotonicity violations:** 0
- **Causal availability violations (`available_ts_ns >= end_ts_ns >= start_ts_ns`):** 0

## Defects fixed & certification blocks resolved

1. **Causal availability prioritization:** The corridor adapter exclusively requires and uses `available_ts_ns` in V2 mode (`_first(row, "available_ts_ns")`), fail-closed.
2. **Termination reason parity:** `termination_reason` is exported by NT8 (`HFTZonesNQPureV4_V2.cs`), reconstructed by Python (`edgelab/bridge/indicators/hftzones_nq.py`), validated in preflight, and compared 1-to-1 in parity. In NQ 06-26: 3,309 `REVERSAL`, 2,129 `MAX_PAUSE`, 0 mismatches.
3. **End-of-input retroactivity censored:** Unconfirmed streaks reaching end-of-input are tagged `CENSORED_END_OF_INPUT`, preventing retroactive availability claims.
4. **All secondary metrics compared:** Parity comparator validates `valid_steps`, `max_retro`, `cvd_sweep`, `buy_vol`, `sell_vol`, `delta_slope`, `delta_first`, `delta_second`, `max_tick_vol`, `no_move_ticks`, `no_move_vol`, `max_level_ticks`, `bucket`, `price_upper`, `price_lower`, `price_mid`, `height_ticks`, `tick_res`. All matched with 0 differences.
5. **Contract boundary isolation:** In multi-contract feeds, `prev_close_ticks` is strictly reset to `None` when `contract != prev_contract`. Tested in unit suite.
6. **Temporal monotonicity enforcement:** Hardened preflight and parity comparator check that `timestamp_ns` is strictly monotonic per session and contract.
7. **Viewer HP-007 automated invariance verified:** Playwright end-to-end browser tests prove that zoom in, zoom out, autoscale, and viewport resizing (800x600, 1280x800, 1920x1080) leave $D(p)$ and `field_hash` 100% identical.
8. **Visual ranking disambiguation:** Visual configuration scoring is formally classified as `TARGET_FREE_VISUAL_HEURISTIC_ONLY_NOT_SCIENTIFIC_SELECTION`, with explicit prohibition of predictive claims or model selection without pre-registration.

## Test Verification

- `pytest tests/bridge/test_paridad_hftzones_v2.py`: 30/30 passed.
- `pytest tests/research/test_hft_corridors.py`: 15/15 passed.
- `pytest tests/research/test_density_field_invariance.py`: 19/19 passed.
- `pytest tests/research/test_hft_viewer_playwright.py`: 2/2 passed (Playwright Chromium headless).
- `tools/validate_hft_v2_certification.py`: `PASS_HARDENED_PREFLIGHT_NOT_FULL_PARITY` (0 errors on 5.98M ticks, 5,438 zones).
- `tools/paridad_hftzones_nq_v2.py --mode V2_NS_EXACT_CERTIFICATION`: `PASS_CERTIFIED` (0 diffs across all 38 fields).

## Safety & Holdout

Strictly target-free. The holdout boundary (`2026-06-30T22:00:00Z`) remains sealed and untouched. No outcomes, P&L, returns, or predictive labels were evaluated or computed.
