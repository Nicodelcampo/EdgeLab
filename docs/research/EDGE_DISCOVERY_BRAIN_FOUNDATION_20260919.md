# Edge Discovery Brain — foundation v0.1

**Status:** `TARGET_FREE_FOUNDATION_ONLY`  
**Base audit commit:** `49eadf059a004fd91c6759f65d03307962263e01`  
**Outcomes:** closed  
**Holdout:** closed

## Purpose

This foundation makes methodological memory machine-readable before autonomous research is enabled. It does not run experiments, open outcomes, promote hypotheses, or treat LLM output as evidence.

## Source-of-truth hierarchy

1. Immutable source artifacts and their hashes.
2. Append-only hash-chained JSONL event ledger.
3. Validated canonical records.
4. Parquet projections and DuckDB views rebuilt from the ledger.
5. Derived dependency graph.
6. Embeddings used only for retrieval.

The graph and embeddings are never authoritative stores.

## Implemented record contracts

- `measurement_contract`: freezes intended vs actual measurement, temporal maturity, wait rules, scope, implementation and regression tests.
- `methodological_learning`: records errors, affected claims, prevention rules, invariants and required tests.
- `claim`: separates literature, statistical, causal, executability and methodological claims and their epistemic states.
- `dependency_edge`: represents explicit, sourced dependencies.
- `model_run`: records external/local model provenance without storing credentials.

## Invalidation policy

Edges are directed as `source depends on target`.

- `DEPENDS_ON`, `MEASURED_BY`, `IMPLEMENTED_BY`: hard dependencies. A measurement error makes dependents `STALE_BY_DEPENDENCY`.
- `TESTED_BY`, `SUPPORTED_BY`, `REPLICATED_BY`: evidentiary dependencies. Affected records become `REQUIRES_REAUDIT`.
- `CONTRADICTED_BY`, `SUPERSEDES`: descriptive transitions; they do not silently invalidate unrelated records.

Every transition must be persisted as a new ledger event. Existing bytes are never rewritten.

## SSRN and CerebroJLP intake

CerebroJLP contributes the rebuild, provenance, contamination review and adjudication architecture. CerebroSSRN contributes literature passages and the historical experimental ledger.

SSRN imports default to non-authoritative states:

- `LITERATURE_CLAIM_UNVERIFIED`
- `LLM_EXTRACTED_CONCEPT`
- `AUTHOR_REPORTED_RESULT`
- `HISTORICAL_EXPERIMENT_PENDING_REAUDIT`

Duplicate paper versions must be connected by `VERSION_OF`, `SUPERSEDES` or `SAME_WORK_DIFFERENT_VERSION` before they may count as independent evidence.

## Model-routing rule

Model output is proposal material, never computed evidence. Every run records provider, exact model ID, execution location, prompt hash, input/output artifact IDs, parameters and review status.

Recommended routing:

- deterministic SQL/Python first;
- local models for bulk private-data processing;
- free hosted models only for sanitized or approved inputs;
- at least one independent adversarial review before a generated claim can enter preregistration;
- no model may promote its own hypothesis.

## Next gated steps

1. Add source/artifact/experiment/result schemas.
2. Add deterministic ledger-to-Parquet projections.
3. Add DuckDB views for unresolved semantic gaps and stale descendants.
4. Import a small adjudicated sample from SSRN and CerebroJLP.
5. Benchmark model routing on a frozen task set.
6. Enable hypothesis generation only after contamination and invalidation tests pass.

## Aporte al referente

La base vuelve explícitas la semántica de medición, la memoria de errores, la procedencia de ejecuciones LLM y la invalidación en cascada antes de permitir investigación autónoma.
