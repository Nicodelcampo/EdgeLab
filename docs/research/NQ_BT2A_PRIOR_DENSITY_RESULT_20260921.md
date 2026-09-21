# NQ prior-density target-free result

Episode `EPISODE-NQ-BT2A-PRIOR-DENSITY-009` completed on the identical seven contract-month samples: 7,000,000 NQ ticks and 4,476 BT2A zones. No outcome, validation or holdout field was accessed.

## Core finding

Splitting prior structure from the newly formed zone materially changes the representation:

| Measurement | p10 | p50 | p75 | p90 |
|---|---:|---:|---:|---:|
| Total density, sigma 1 | 0.812 | 0.957 | 0.992 | 0.999 |
| Prior density, sigma 1 | 0.000 | 0.029 | 0.889 | 0.986 |
| Current-zone delta, sigma 1 | 0.012 | 0.751 | 0.906 | 0.957 |
| Prior density, sigma 4 | 0.000 | 0.904 | 0.996 | 1.000 |

At sigma 1, half of newly formed zones had zero prior same-direction confluence; p75 was one prior zone and p90 two. This is a usable, interpretable state variable. At sigma 4, even prior density is already highly saturated and should not be the primary discriminator.

## Brain decision

Adopt representation v2:

- `prior_support_density_sigma1`: pre-existing structure only;
- `prior_same_direction_confluence_sigma1`;
- `current_zone_density_increment_sigma1`;
- keep sigma 4 as context, not as the principal wall gate;
- never call total density including the current zone “pre-existing wall strength.”

Previous campaigns remain valid negative tests of their declared representation, but their density thresholds were less selective than intended. They must not be rerun post hoc with v2 on the same YM outcomes. V2 is available for future target-free work or a genuinely independent dataset episode.

Evidence hash: `7e295ef3dec04f416b26618aa183c904d0b6b3498e17baa591eb622b7eff6bbf`.

**Aporte al referente:** demonstrates recursive self-improvement of the Brain's measurement vocabulary using target-free cross-instrument evidence rather than outcome tuning.
