# HFTZonesNQ → causal corridor integration

Status: `IMPLEMENTED_AWAITING_LOCAL_DATA_RUN_AND_V2_SHARED_INPUT_EXPORT`.

Implemented: strict V1/V2 HFT adapter; availability at detector completion; six target-free visual configurations; neutral ranking by coverage/dynamic range/fragmentation; holdout-blocking bundle builder; dedicated preview that never draws candles after tRef and keeps the field invariant under display zoom.

```powershell
python -m pytest tests/research/test_hft_corridors.py -v
python tools/build_hft_corridor_bundle.py --zones data/nt8_oracles/hft_zones_nq_20260603_20260611.csv --ticks E:/EdgeLab/data/nt8/NQ_parquet/NQ_06-26_ticks.parquet
python viewer/nt8_bridge/server.py
```

Open `http://localhost:8088/hft_corridor_preview.html`.

Neutral first view: `HFT_RAW_GAUSS_2`. It is not an edge winner. The local target-free ranking may propose a different first view; Nicolas decides visually.

Formal holds: `REVISIT_HYPOTHESIS_MEASUREMENT=ON_HOLD_BY_OWNER`; `OUTCOME_BASED_SELECTION=PROHIBITED`; `HOLDOUT_READS_FOR_SELECTION=0`; `HFT_PARITY=PROVISIONAL_NEAR_EXACT_BLOCKED_BY_SHARED_INPUT_V2_EXPORT`.

Aporte al referente: integra HFTZonesNQ al campo causal sin trasladar paridad a BT2A ni utilizar outcomes para elegir la representación visual.
