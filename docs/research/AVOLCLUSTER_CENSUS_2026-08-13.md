# aVolClusterPOI census 2026-08-13

Source: `avolcluster_census_20260813.csv` (7620 events).
Contract: `6E 09-26`. Chart 1m. 2026-04-10 → 2026-06-30.
Meta: p=98, min_samples=20, filter=0, session buckets, CloseThrough, **max_age=500**.
Outcomes / QualityScore not used.

## Confirmed

- 255 `ZONE_CREATED`.
- Width 2 / 4 / 9 / 21 ticks.
- Samples at create: min 21, p50 58, max 60. Gate works.
- 46 buckets used (ids 0–45).

## Corrections

- 4.11 / min 1 / max 14 is **per calendar day** (62 days), not per CME session.
  `session_index` with ≥1 create: **55** (7–63, gaps 17 and 39). Per session: mean 4.64, max 12.
- CME session ≈ 23h = **46** half-hours, not 48. Coverage is the whole session, not 96% of 48.
- First create at `session_index=7`. `min_samples=20` is not “20 sessions”. Several blocks/bucket/session fill the gate in ~7 sessions.

## Form problems (what to change)

1. **45.5% NEUTRAL** (116/255). Close inside the cluster. That is occupation, not a level. Do not mix with off-price clusters.
2. **6910 TOUCHED** vs 255 created. Every bar inside the band is a touch. Export first-touch only.
3. **137 expire by max_age, 117 close-through.** Age 500 bars (~8h) is an arbitrary middle. Session-end or close-through only.
4. **8 bars minted 18 zones; 38 overlap pairs** in the same session. Optional: keep best cluster per block.
5. **April 49 / May 84 / June 122.** `6E 09-26` from April is not always the front. Density rise is partly roll, not “more signal”.
6. Density p50 = 1.0 (solid). Width p50 = 4. Complementary to a single cell. Keep.

## Next detector (still no formal)

- Split at-price vs off-price.
- First-touch event only.
- MaxAge=0 or session-end.
- Keep p98 / min 20 / filter OFF.
- Next NT8 run: same dates only if we accept 09-26; else front month or 06-26+09-26 noted separately.
