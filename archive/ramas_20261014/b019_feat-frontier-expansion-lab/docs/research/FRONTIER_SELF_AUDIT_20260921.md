# Frontier self-audit and corrections

**Status:** `CORRECTIVE / PRE-HOLDOUT / NO OUTCOMES`  
**North Star:** `d85364e21951980c0e9273ed1883ce14413db157052162ed38ac9ab2403375a1`

## Findings and corrections

1. **Critical — markout future anchor.** V1 selected the first quote at or after the fill. V1 is retired. V2 selects the last quote at or before the fill, bounds anchor/horizon staleness and requires lineage.
2. **High — unrelated activation depth.** Queue activation must match order side and price; fills require positive quantity.
3. **High — incomplete packet proof.** Exact-queue certification must reject event packets absent from channel evidence, receive-time inversion and non-increasing instrument sequence.
4. **Medium — coupled component warmups.** EMA/SMA/VWAP now become ready independently; combined waits for all.
5. **Medium — placebo warmup movement.** `NOT_READY` stays fixed; only ready states shuffle within session.
6. **Medium — non-finite trend inputs.** NaN/inf now fail closed.
7. **Operational.** Pre-correction Python 3.12 CI was red; focused tests are not a global-green claim. The official CPython 3.12 Linux rpds hash was verified and not changed without job logs.

## Justificación económica

These corrections block optimistic execution, false completeness and malformed contexts from producing false-positive edge.

## Cómo podría refutarse

Failure means a future quote can anchor a fill, unrelated depth seeds queue, events pass without packet evidence, placebo moves warmup states, component warmups stay coupled, or non-finite values enter a digest.

## Aporte al referente

Concrete look-ahead and observability defects were removed before economic campaigns rely on Frontier.
