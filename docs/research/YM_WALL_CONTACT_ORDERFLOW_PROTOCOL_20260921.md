# Causal wall-contact order-flow protocol

Campaign `CAMP-YM-WALL-CONTACT-FLOW-006` tests the first genuinely new mechanism after three geometric density families failed: observed order-flow transition at wall contact.

A BT2A wall must be known causally, have same-direction density/confluence, experience a directional departure, and receive its first later retest. That retest remains only a trigger. The system then watches 5 or 25 ticks for all three preregistered confirmation dimensions: movement away from the wall, aligned aggressor-volume imbalance inferred from contemporaneous bid/ask, and repeated prints at the wall as a replenishment/absorption proxy. Entry is the first tick strictly after confirmation in the same session.

The frozen family contains 3,456 policies. Stage-1 management is TP 12, SL 6, maximum hold 1,000 ticks and no break-even. Costs are 2/4/6 all-in ticks. Trades are non-overlapping per policy and contract. Survival requires at least 100 trades, positive six-tick expectancy, Holm p<0.05 at four ticks, positive net-four expectancy in at least two contracts, and a positive 95% session-cluster bootstrap lower bound.

The target-free quote audit found valid contemporaneous bid/ask on 100% of the five canonical YM files. Five unit tests pass. A grid cardinality assertion corrected 6,912 to 3,456 before preregistration and before any outcome was computed.

No validation or H2-2026 outcome may be accessed before a candidate lock is serialized and hashed.

**Aporte al referente:** upgrades density from a static visual condition to a falsifiable transition mechanism based on price rejection, aggressive flow and wall interaction observed before entry.
