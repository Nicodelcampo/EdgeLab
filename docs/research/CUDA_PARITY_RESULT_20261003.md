# CPU/GPU parity result — 2026-10-03

## Executed, not simulated validation

Kaggle notebook https://www.kaggle.com/code/nicolasbuttaro/edgelab-synthetic-cpu-gpu-parity-20261003 version 2 completed on a Tesla T4. Source commit: a420123afd7b56dae5737375abde54ce6a4960fc. Runtime: Python 3.13.15, NumPy 2.1.3, Numba 0.61.2, CuPy 14.0.1, CUDA runtime 12090. Harness subprocess reported 12.370433674999987 seconds and return code 0 (not a total billed-duration measurement).

Result: CPU_GPU_PARITY_PASS. Eight CPU/oracle cases passed; seven nonempty cases also passed GPU/oracle with identical NaN masks and float32-aware numeric tolerance. Empty signals were tested on CPU only; no GPU empty-launch claim is made.

Cases: known paths, stop-first tie, target touch without fill, seeded random paths with horizons 0/1/17/200, empty signals. Signals include final-bar missing entry, both directions and reversed configuration multipliers. No market datasets attached, no internet enabled, no D2/holdout outcomes read.

## Custody

- artifacts/funnel/parity_20261003/attempt_01_observed_failure.json retains the initial undefined-NAN failure.
- attempt_02_parity_cpu_gpu.json contains the exact report bytes reconstructed from the authenticated MCP session log using the original serializer.
- Locally computed SHA-256 equals the SHA-256 emitted by Kaggle: cff8c8848ff12d1d91a8402aea4279a19e302a36708729a824b1a4cf5d049b12.
- attempt_02_provenance.json records this retrieval path honestly: log reconstruction and hash equality, NOT a direct file download. No signed download URLs or credentials are committed.
- Device and harness sources were unchanged; only the GPU missing-entry NaN expression changed. Source hashes are included in the report and verified at notebook startup.
- The source capsule uses empty package initializers to isolate the tested modules; it is not a full-repository integration test.

## Operational learning

CUDA_UNDEFINED_NAN is reproduced on attempt 1 and repaired on attempt 2 with __int_as_float(0x7fc00000). The regression includes the last-bar NaN sentinel and mask comparison. Preserve failure, repair, source identity and test evidence together. Python compilation or successful CPU fallback must never satisfy a real CUDA gate.

This is validated operational evidence for these specific cases/image, not a general proof of all CUDA versions, hardware, large-memory batching or numerical domains. The learning packet has not been represented as ingestion into the canonical Edge Brain ledger.

## Gates still closed

- PR stays draft: original CPU suite, real Parquet/runner integration, consumer compatibility and independent review remain pending.
- No market rerun, candidate retuning, MGC promotion or change to TP400 tick-exact.
- D2/holdout remain closed. Historic cheap-screen requires isolated D0/D1 revalidation with original frozen split, not enlarged history.
- No claim of validated parameter plateau, full-universe multiplicity, SPA/DSR/BH repair or recovery of the 126 missing trials.
