# NQ BT2A target-free representation result

Episode `EPISODE-NQ-BT2A-DENSITY-REPRESENTATION-008` completed on seven deterministic contract-month samples totaling 7,000,000 canonical NQ ticks and 4,476 BT2A zones. No outcomes, validation or holdout data were accessed.

## Measurements

- Explicit aggressor: 3,493,804 buy, 3,506,153 sell, 43 unclassified.
- Quote-inferred aggressor disagreed on only 20 classified ticks: 0.0002857%.
- Zone width: median 2 ticks, p90 3, maximum 5.
- Formation strength ratio: median 1.542, p90 3.231.
- Same-direction confluence: median 1/p90 3 at sigma 1; median 2/p90 4 at sigma 4.
- Density including the current zone: median 0.957 at sigma 1 and 0.992 at sigma 4.

## Brain lesson

The canonical explicit aggressor field validates quote-side inference for these NQ files. More importantly, the existing density representation is saturated because it includes the newly formed zone itself. Its theoretical floor is already high, so thresholds such as 0.7 and 0.9 admit a large fraction of events and provide less conditioning than their labels suggest.

This is not leakage and does not invalidate prior negative campaigns; it explains why density thresholds had little discriminatory power. Before any new outcome episode, the representation must split:

1. pre-existing density from zones available before the current zone;
2. incremental density contributed by the current zone;
3. prior confluence excluding the current zone.

Evidence hash: `2d00d496896704764171120e6e8a0d4fdaeacc1538671252b2f3c322dc2db2a9`.

**Aporte al referente:** converts a cross-instrument target-free measurement into a concrete representation correction rather than another economic threshold search.
