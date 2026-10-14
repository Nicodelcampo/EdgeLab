# NQ BT2A density target-free representation protocol

Episode `EPISODE-NQ-BT2A-DENSITY-REPRESENTATION-008` is the first episode admitted by the hard-novelty gate after the YM lineage reached `SATURATED_STOP` at 26,856 tested policies and zero survivor.

This episode introduces canonical NQ v6 and explicit aggressor classification. It is strictly target-free: no future return, target, stop, trade entry, economic label, validation or holdout outcome may be computed.

## Frozen sampled contract

The unit is a contract-month slice with state reset at each UTC month boundary. Each slice uses its first 1,000,000 canonical ticks before 2026. Included contracts are NQ 09-25, NQ 12-25 and the pre-2026 portion of NQ 03-26. Formation remains `tick_count:25`.

The first operational attempt used complete monthly slices. It completed five slices but the ephemeral sandbox disappeared before the aggregate artifact was written. No partial aggregate was accepted and no outcomes existed. Before rerun, the deterministic one-million-tick cap was frozen to bound runtime and make reconstruction reliable; this is an operational amendment, not an outcome-driven change.

Measurements remain zone geometry, formation strength/volume/fraction, causal same-direction density and confluence at sigma 1/4, explicit aggressor distribution, and disagreement between explicit aggressor and quote-inferred aggressor. Outputs include source hashes and per-slice/aggregate quantiles.

Three utility tests pass. Download verification is 5/5 SHA-256. `outcomes_accessed=false`, `validation_accessed=false`, `holdout_accessed=false`.

**Aporte al referente:** moves the Brain from exhausted YM threshold search to reproducible target-free cross-instrument representation learning under an executable novelty gate.
