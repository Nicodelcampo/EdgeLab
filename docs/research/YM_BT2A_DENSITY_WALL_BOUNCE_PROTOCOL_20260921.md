# YM/BT2A dense-wall first-retest protocol

Campaign `CAMP-YM-BT2A-DENSITY-BOUNCE-004` tests a mechanism distinct from generic corridor traversal: a causally formed BT2A density wall, departure away from that wall, and the first later retest as a rejection opportunity.

The frozen family contains 1,296 entry contexts over Gaussian scale, formation-time same-direction density, confluence count, departure distance, retest depth, expiry and formation strength. Stage-1 management is fixed at SL 6, TP 12, 1,000-tick maximum hold and no break-even. Costs are 2/4/6 all-in ticks.

The retest touch is a trigger only. Fill is the first strictly later observed tick in the same session. Final touches, state and invalidation fields are forbidden. Trades are non-overlapping per contract. Survival requires at least 100 trades, positive six-tick expectancy, Holm-adjusted p<0.05 at four ticks and positive four-tick expectancy in at least two discovery contracts.

No validation or H2-2026 data may be used before a candidate lock is serialized and hashed.

**Aporte al referente:** separates wall rejection from corridor ignition so failure of one mechanism does not silently kill or rescue the other.
