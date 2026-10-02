# EdgeLab CPU/GPU funnel

E1 cheap-screen uses one independent work item per signal/configuration. `backend=auto` selects CuPy only when CUDA exists and the batch is large enough; otherwise Numba CPU is the reference. Candidate batches are bounded by a 512 MiB outcome matrix, so registries can contain millions of candidates without materializing the full matrix.

```bash
python tools/run_funnel_arrays.py \
  --arrays /kaggle/input/edgelab-arrays/mgc-bars \
  --registry docs/research/mgc_ema_20261002/candidate_registry.json \
  --out /kaggle/working/mgc-funnel --backend auto
```

Outputs are a ZSTD survivor Parquet, summary JSON and hash-chained Edge Brain ledger. D2 is never read by this entrypoint. GPU results are screening artifacts only; confirmation always returns to the shared CPU tick-exact engine.
