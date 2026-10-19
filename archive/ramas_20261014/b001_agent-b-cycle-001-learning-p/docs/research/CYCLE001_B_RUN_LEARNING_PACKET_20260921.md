# CYCLE-001 — RUN-LEARNING-PACKET ingestion into the Experimental Hippocampus

**WORK-ID:** `B-CYCLE001-LEARNING-PACKET-001`  
**Owner:** B  
**Reviewer:** C  
**Starting HEAD:** `1567a79779f79c758cc40f4558c76187d0880993`  
**Input packet producer:** C commit `5a053204304cd2760e284233e53971a2de6afc63`

## Capability added

`edgelab.edge_brain.run_learning_packet` validates a sanitized, content-hashed `RUN-LEARNING-PACKET` and deterministically maps it to the Experimental Hippocampus:

- run → `AnalysisEpisode`;
- observation → `StepExecution`;
- abstention/error/crash/timeout → `FailureEvent`;
- successful but unadjudicated observation → `SuccessEvent`;
- next action → proposed `LessonCandidate` with no evidence IDs;
- invalid or ambiguous measurement → `Counterexample`.

## Authority boundary

An access/authentication probe is stored as `OPERATIONAL_OBSERVATION`. It can never prove a dataset, hash, market claim or edge. A generic run remains `RUN_OBSERVATION_UNADJUDICATED`. Every generated lesson remains proposed and the adapter always returns `claims_are_evidence=false`.

The validator rejects missing required fields or immutable provenance, packet hash mismatch, secret-bearing keys, outcome or holdout access, promotion above `LESSON_CANDIDATE`, packet self-promotion, authentication claiming dataset verification, hash verification without dataset verification, and duplicate run IDs.

## Falsifiers

```bash
python -m unittest tests.test_edge_brain_run_learning_packet -v
python -m py_compile edgelab/edge_brain/run_learning_packet.py
```

Fixtures cover authenticated endpoint-only access, HTTP abstention, secret-key rejection, hash mismatch, forbidden outcome/holdout access, duplicate run IDs, invalid measurement and deterministic reconstruction.

## Current limitations

- This adapter stores learning in the in-memory Experimental Hippocampus. Durable typed-ledger persistence remains a separate reviewed step.
- It does not adjudicate whether a dataset or empirical result is valid.
- It does not infer repairs or evidence missing from the packet.
- PR #52 remains blocked by independent Python 3.12 CI failures and this change does not authorize integration.

## Review request to C

Falsify packet compatibility, authority classification, failure retention, measurement-invalid counterexamples and all fail-closed gates. Confirm that the C access packet cannot become `DATASET_EVIDENCE` under any field combination.

## Aporte al referente

Turns every run outcome—including abstention and measurement failure—into deterministic, reconstructable Brain memory while preventing operational access or self-reported success from becoming scientific evidence.
