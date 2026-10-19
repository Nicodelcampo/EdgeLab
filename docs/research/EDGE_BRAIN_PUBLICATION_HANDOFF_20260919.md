# Edge Brain — publication and pilot handoff (2026-09-19)

## Purpose

Persist the complete state and design decisions for the recursive EdgeLab brain so no architectural knowledge depends on a chat transcript.

## Authoritative implementation artifact

- Final local commit: `6081c6faedb6af01b90d658cca45ad67b9bd52dd`
- Required remote base: `ab44e2ba68fb2d2b80fbdedbbd6761aa6fcf1122`
- Bundle: `edge-brain-hippocampus-atlas-20260919.bundle`
- SHA-256: `21655a829ba79f397953cd5555712635c61ee26523d3b9cc8f948470e00aeeee`
- Commit chain:
  - `6c0d90cab7e9956d9a9ffc3832d9c02d336058bc` — registry, recursion and adjudication
  - `eb69e301f25a9c3d66d0677a0d85e975cf16f9db` — memory, provider-neutral interface, projection and custody gates
  - `6081c6faedb6af01b90d658cca45ad67b9bd52dd` — hippocampus and measurement atlas

The bundle was verified locally and contains the complete implementation. The branch must not be described as fully published until these files are visible remotely.

## Architecture

```text
Bibliographic Cortex
↔ Experimental Hippocampus
↔ Measurement & Composition Atlas
↔ Procedural Memory
↔ Working Memory / Context Pack
```

### Permanent semantics

- The LLM generates hypotheses but its output is `LLM_PROPOSAL_NOT_EVIDENCE`.
- Deterministic computation tests hypotheses at scale.
- A model never approves its own hypothesis.
- Triangulation is mandatory when a claim depends on another claim.
- Promotion is explicit, auditable and fail-closed.
- Negative results and counterexamples are retained.
- Methodological learning is represented as typed nodes, not reflection prose.
- Papers and external sources are separated from the experimental hippocampus, but linked with typed bidirectional edges.
- The measurement atlas stores how to measure and compose indicators, including roles, units, normalization, timing, ablations and failure modes.
- Reuse/popularity is not credibility; co-occurrence is not causality.

## Main implementation files

New core modules:

- `edgelab/edge_brain/hippocampus.py`
- `edgelab/edge_brain/measurement_atlas.py`
- `edgelab/edge_brain/context_memory.py`

Updated core:

- `edgelab/edge_brain/typed_registry.py`
- `edgelab/edge_brain/invalidation.py`
- `edgelab/edge_brain/__init__.py`
- `tools/edge_brain_cli.py`

Configuration, docs and tests:

- `config/edge_brain/measurement_atlas_seed.json`
- `docs/research/EDGE_BRAIN_HIPPOCAMPUS_MEASUREMENT_ATLAS_20260919.md`
- `tests/test_edge_brain_hippocampus_atlas.py`

## Typed hippocampal records

The final implementation includes JSON schemas for:

- `analysis_episode`
- `step_execution`
- `expectation`
- `failure_event`
- `causal_hypothesis`
- `repair_action`
- `success_event`
- `lesson_candidate`
- `learning_rule`
- `skill`
- `reuse_event`
- `reuse_outcome`
- `counterexample`
- `synthesis`
- `context_pack`
- `open_question`
- `indicator_definition`
- `composition_contract`
- `measurement_atlas_catalog`

Total Edge Brain schemas after the final commit: 35.

## Typed relations

The registry includes relations such as `DERIVED_FROM`, `EXPLAINS`, `CAUSED_BY`, `MITIGATED_BY`, `APPLIES_TO`, `FAILS_UNDER`, `REQUIRES`, `SPECIALIZES`, `GENERALIZES`, `TRANSFERS_TO`, `CO_OCCURRED_WITH`, `USED_IN`, `HELPED`, `HARMED`, `REQUIRES_REAUDIT`, `OPERATIONALIZED_AS`, `NORMALIZES`, `GATES`, `CONDITIONS`, `CONFIRMS`, `DIVERGES_FROM`, `REDUNDANT_WITH`, and `COMPLEMENTS`.

## Seed measurement atlas

IDs:

- Catalog: `ATLAS-FOUNDATION`
- Partition: `METHODOLOGICAL_CORTEX`
- Indicators: `IND-EMA`, `IND-RSI`
- Composition: `COMP-EMA-RSI-REGIME-TRIGGER`
- Measurement concept: `TREND_STRENGTH`

All seed entries remain `DRAFT`/`PROPOSED`; they do not assert edge.

## Validation completed locally

```text
80 passed in 0.97s
Atlas validation: PASS
compileall: PASS
git diff --check: PASS
```

## Controlled Kaggle pilot decision

It is not too early for a pipeline pilot. It is too early to claim edge or promote a general rule.

A valid pilot must:

1. Use a public timestamped OHLCV dataset unrelated to blocked NQ custody.
2. Record URL, version, licence, SHA-256, size, columns, time range and coverage.
3. Enforce `timestamp < 2026-06-30T22:00:00Z` (`holdout_boundary_ns = 1782856800000000000`).
4. Pre-register a methodological question such as: “What marginal information does an EMA regime gate add to a momentum trigger?”
5. Materialize `AnalysisEpisode`, `StepExecution`, `Expectation`, context pack, indicator definitions and composition contract.
6. Run ablations: no EMA, no trigger, shuffled gate, parameter neighbourhood and alternate normalization.
7. Record failures, successes, counterexamples and reuse outcomes.
8. Produce only a `LessonCandidate`; never activate a general `LearningRule` from one pilot.
9. Save manifest, reproducible script/notebook, ledger JSONL, contracts, tables and report under `artifacts/edge_brain/pilots/` and `docs/research/`.

## Custody and holdout invariants

- `NOT_OBSERVED != ZERO_ACTIVITY`
- `REMOTE_LISTED_PENDING_DOWNLOAD_PROOF != REMOTE_VERIFIED`
- NQ 09-26 remains `BLOCKED_BY_CUSTODY` until real download and SHA-256 proof exist.
- Do not open, profile or learn from holdout outcomes.
- The ledger is append-only and canonical; projections never replace it.
- Historical brains remain quarantined until schema validation, deduplication, versioning, contamination tracking and adjudication are complete.

## Next operational steps

1. Publish the complete bundle content on the feature branch and verify the three implementation commits or an equivalent content commit remotely.
2. Verify the key modules and all 35 schemas via GitHub.
3. Re-run the 80-test suite and atlas validation in CI.
4. Execute the controlled Kaggle pilot above.
5. Commit every pilot artifact and update PR #43 with evidence only.
