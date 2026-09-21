# NQ BT2A density target-free representation protocol

Episode `EPISODE-NQ-BT2A-DENSITY-REPRESENTATION-008` is the first episode admitted by the new hard-novelty gate after the YM lineage reached `SATURATED_STOP` at 26,856 tested policies and zero survivor.

This episode introduces a new dataset (canonical NQ v6) and a new observable (explicit aggressor classification). It is strictly target-free: no future return, target, stop, trade entry, economic label, validation or holdout outcome may be computed.

The unit of analysis is a contract-month slice with indicator and density state reset at each UTC month boundary. This avoids fabricating a continuous roll and bounds memory. Included data are NQ 09-25, NQ 12-25 and only the pre-2026 portion of NQ 03-26. Formation remains `tick_count:25`.

Measurements are frozen to zone geometry, formation strength/volume/fraction, causal same-direction density and confluence at sigma 1/4, explicit aggressor distribution, and disagreement between explicit aggressor and quote-inferred aggressor. Outputs are aggregate and per contract-month quantiles with source hashes.

Three utility tests pass. Download verification is 5/5 SHA-256. `outcomes_accessed=false`, `validation_accessed=false`, `holdout_accessed=false`.

**Aporte al referente:** moves the Brain from exhausted YM threshold search to target-free cross-instrument representation learning under an executable novelty gate.
