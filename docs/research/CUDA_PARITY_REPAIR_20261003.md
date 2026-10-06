# CUDA parity failure and minimal repair — 2026-10-03

Attempt 1 ran privately on Kaggle Tesla T4 with no attached datasets and internet disabled. Source bytes matched commit b74a05a951517d9f073488c8e84cdd4d124b626a. The log reports CuPy 14.0.1 / CUDA runtime 12090 and CompileException: identifier NAN is undefined. The harness marked FAIL; no case was completed and gpu_tested remained false. CPU reached and passed the first oracle assertion before GPU compilation, but that is not a completed CPU suite.

Observation is preserved in artifacts/funnel/parity_20261003/attempt_01_observed_failure.json as a session-log extract, NOT a claimed downloaded/hash-verified output file. The original notebook version and failure are retained.

## Minimal repair

Replace only `out[z]=NAN;return;` with `out[z]=__int_as_float(0x7fc00000);return;`. This is the IEEE-754 quiet NaN sentinel using a CUDA device intrinsic without an undeclared macro. CPU logic, signals, fee, seed, SL/TP and horizons remain unchanged. Corrected screen.py SHA-256: e35155b5033231bdd161b4480785a7c6661e48025be521d4ad324d4647a92289.

## Structured operational lesson (candidate, not trading evidence)

- failure_code: CUDA_UNDEFINED_NAN
- scope: CuPy RawKernel compilation on the observed Kaggle CUDA image
- detection: force real GPU compilation and last-bar NaN oracle check before large workloads
- repair: explicit quiet NaN device intrinsic
- regression: identical synthetic harness; both numeric results and NaN masks must agree
- status: REPAIR_PENDING_GPU_VERIFICATION at this commit
- reuse_policy: never treat Python compileall or CPU fallback as CUDA validation

No market conclusion, no hypothesis retuning, no D2 opening, no MGC promotion. This document is a proposed operational learning packet; it is not claimed to be ingested into the canonical append-only Edge Brain ledger or the missing original atlas schemas.
