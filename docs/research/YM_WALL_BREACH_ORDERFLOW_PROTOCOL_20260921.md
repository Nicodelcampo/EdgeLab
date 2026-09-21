# Aggressive dense-wall breach protocol

Campaign `CAMP-YM-WALL-BREACH-FLOW-007` tests a mechanism distinct from every rejected bounce family: continuation after a dense wall fails.

A causal BT2A wall must have preregistered same-direction density/confluence, experience departure and receive its first later retest. The system then waits 5 or 25 ticks for price to penetrate 1/2/4 ticks beyond the wall's far edge with aggressor-volume imbalance aligned to the breach. The trade direction is opposite the wall direction. A maximum number of prints inside the wall represents limited absorption before failure. Entry is the first strictly later tick in the same session.

The frozen family contains 2,304 policies. Stage-1 management is TP 12, SL 6, maximum hold 1,000 ticks and no break-even, under 2/4/6 all-in costs. Survival requires at least 100 non-overlapping trades, positive six-tick expectancy, Holm p<0.05 at four ticks, positive net-four expectancy in at least two contracts, and a positive session-cluster bootstrap lower bound.

Eight unit tests pass before outcomes. This campaign does not reinterpret failed bounce results as continuation evidence; it treats breach as a new preregistered transition with its own multiplicity burden.

No validation or H2-2026 outcomes may be opened before a candidate lock exists.

**Aporte al referente:** tests whether dense walls are economically useful as failure/continuation structures rather than support/resistance bounce structures.
