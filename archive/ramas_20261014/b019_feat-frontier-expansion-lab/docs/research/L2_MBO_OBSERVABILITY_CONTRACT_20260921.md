# L2/MBO Observability Contract v1

**Contract:** `L2_MBO_OBSERVABILITY_V1`  
**Status:** `SYNTHETIC / TARGET-FREE / PRE-HOLDOUT`  
**Implementation:** `edgelab/execution_lab/feed_contract.py`

## Research basis

This contract was derived after rereading EdgeLab's existing NT8 depth intake,
its `source_row` ordering fix and the June L2 join failure, then contrasting them
with venue and independent documentation.

- CME MBO disseminates individual orders at every price level. Queue ordering is determined within the same side and price using order priority.
- CME incremental UDP packets have channel-scoped packet sequence numbers; packet loss is detected from gaps and recovery can use redundant A/B feeds, TCP replay and market recovery snapshots.
- CME trade summaries can span packets and include participating order IDs.
- Databento's normalized CME MBO preserves per-instrument message order and FIFO priority, while distinguishing exchange and receive timestamps.
- Queue-valuation research treats position, executions and cancellations as separate processes; it does not justify converting anonymous MBP cancellations into exact FIFO improvement without a calibrated assumption.

Sources:

1. CME MDP 3.0 Market by Order book management: <https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457605721>
2. CME UDP recovery services: <https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457325847/MDP+3.0+-+Recovery+Services+for+UDP>
3. CME Trade Summary: <https://cmegroupclientsite.atlassian.net/wiki/display/EPICSANDBOX/MDP+3.0+-+Trade+Summary>
4. Databento CME MDP 3.0 normalization: <https://databento.com/docs/venues-and-datasets/glbx-mdp3>
5. Moallemi & Yuan, queue position valuation: <https://moallemi.com/ciamac/papers/queue-value-2016.pdf>

## Finding from the repository reread

The existing `edgelab/data/l2.py` input is **aggregated MBP exported by NT8**, not order-level MBO. It preserves line order with `source_row`, but does not expose exchange packet sequence, channel identity and A/B recovery state, CME order ID, order priority, exact lifecycle, or a proved exchange-time/receive-time clock pair.

Therefore it may support target-free book-state checks and carefully scoped OFI, but it cannot certify exact queue position or observed passive fills. The August ES capture is also in the sealed holdout and remains target-free quarantine.

## Required normalized fields

Each event records dataset and channel identity, instrument, packet sequence, event index inside the packet, instrument sequence, exchange and optional receive timestamps, action, side, tick price, quantity, order identity, priority and recovery flag. Provenance separately records raw and decoder SHA-256 identities.

Packet observations are a separate channel-level input. This separation is mandatory: after filtering to one instrument, skipped packet numbers may simply belong to other instruments and cannot prove packet loss or completeness.

## Promotion states

### `CERTIFIED_EXACT_QUEUE`

Allowed only for MBO with raw and decoder hashes, one dataset and channel, strict packet/event order, channel-level contiguous packet evidence, no timestamp inversion, order IDs on lifecycle mutations and priority on add/modify events. This is eligibility for queue reconstruction, **not** proof of a profitable fill model.

### `CERTIFIED_AGGREGATED_ONLY`

MBP segment with valid provenance and continuity. It may support aggregate depth or OFI, but never exact FIFO queue evidence.

### `ABSTAIN`

Any missing hashes, packet evidence, continuity, order identity, priority or ordering integrity. Missing evidence is not converted to zero activity.

## Falsification criteria

The contract fails if it certifies exact queue from aggregated depth, permits an instrument-filtered stream to stand in for channel packet continuity, ignores a sequence gap/reset, or accepts order lifecycle rows without stable identity.

## Measured / not measured

**Measured in this increment:** synthetic contract behavior and deterministic certification state.

**Not measured:** availability of a production MBO source, correctness of any vendor decoder, queue-model calibration, cancellation-position distribution, fill probability, adverse selection, P&L or any holdout outcome.

## Aporte al referente

EdgeLab now has a machine-enforced boundary between aggregated depth and evidence that can actually support exact FIFO execution. Existing NT8 MBP is no longer at risk of being silently promoted into MBO-quality fill evidence.
