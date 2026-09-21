# Wall-contact order-flow Stage 1 result

Decision: `STOP_NO_SURVIVOR`.

The first transition-based corridor campaign evaluated 3,456 preregistered contexts over 8,056,713 discovery ticks and 2,645 BT2A zones. There were 2,091 zones with an executable first retest, and 455 policies reached 100 non-overlapping trades.

No policy reached even the pre-cluster survival gate. The best observed context required a four-tick Gaussian wall, two-zone confluence, four-tick departure, 50% retest depth, 250-tick expiry, 25-tick observation, two-tick rejection and five wall prints. It produced 113 trades and +1.805 gross ticks: −0.195/−2.195/−4.195 after 2/4/6 ticks of cost. It was negative in every discovery contract and Holm p=1.

Therefore observed bounce confirmation using trade-at-bid/ask imbalance and repeated wall prints is insufficient. This is a stronger rejection than the geometric campaigns because entry occurred only after an actual post-contact transition was observed.

Validation and H2-2026 remained unopened. A distinct continuation hypothesis—aggressive breach through a dense wall—may be tested as a separate preregistered mechanism; the bounce grid must not be widened.

**Aporte al referente:** adds an explicit negative lesson that wall geometry plus observed rejection still does not cover execution costs on YM.
