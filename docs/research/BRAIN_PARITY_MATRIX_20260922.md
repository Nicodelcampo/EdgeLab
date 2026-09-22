# Brain capability parity matrix — CerebroSSRN (v1 + v2) vs edge_brain

**Date:** 2026-09-22  
**Source A (old):** `$ACerebroSSRN.rar` (66 MB, Kaggle `edgebrain-cerebro-ejemplos-auditores`), pipeline F0–F6 over ~401 SSRN papers, state 2026-07-13/25  
**Source B (current):** `edgelab/edge_brain` at PR #52 head + durable store branch  
**Scope:** capability audit only. No outcomes, no holdout.

## What each brain actually has

### CerebroSSRN (old)

| Capability | Evidence in archive |
| --- | --- |
| PDF→text pipeline with manifest | `pipeline/extract_pdfs.py`, `Normalizado/manifest.*` (401 docs, 5.25M words) |
| Semantic retrieval (RAG) over raw passages | `pipeline/chunk_docs.py`, `embed_chunks.py`, `Normalizado/embeddings.npy` (24,340 passages, multilingual-e5-small, cross-lingual ES→EN) |
| LLM extraction with verbatim-citation discipline | `extraccion/PROMPT_EXTRACCION.md`, `extraccion/completo/` (401 JSON), `validacion.json` |
| Fuzzy concept consolidation + human/LLM judge decisions | `pipeline/consolidate_concepts.py`, `grafo/decisiones_jueces.json` |
| Idempotent graph build | `pipeline/build_graph.py` (v1: 1,223 nodes / 1,864 edges) |
| Community detection + narrative summaries | `pipeline/detect_communities.py` (254 communities), `grafo/comunidades_resumen.md` |
| Graph v2: node embeddings, dangling-node welding, retrieval benchmark | `mejoras_ssrn_v2.zip`: `nodos_emb.npy`, `soldar_colgantes.py`, `benchmark_corteza.py`, `benchmark_seed.json` |
| Ecosystem bridge (graph ↔ real backtesting state) | `cerebro/PUENTE_ECOSISTEMA.md`, `pipeline/prepare_anchor_context.py` |
| Narrative experiment ledger (proposal→test→result→learning) | `cerebro/LEDGER_EXPERIMENTOS.md` (30+ EXPs incl. refutations: EXP-004b, 041, 042, 044) |
| Skeptical runtime protocol | `cerebro/CEREBRO_SSRN.md` (robustness declarations, no-peer-review stance) |

### edge_brain (current, post 2026-09-22)

| Capability | Evidence |
| --- | --- |
| Typed experimental records (episode/step/failure/success/lesson/counterexample) | `hippocampus.py` |
| Durable append-only hash-chained ledger with deterministic replay | `hippocampus_store.py` (8/8 tests, tamper-evident) |
| Typed registry + schema validation | `typed_registry.py`, `schema_validator.py` |
| Measurement atlas / coverage / eligibility | `measurement_atlas.py`, `coverage.py`, `eligibility.py` |
| Triangulation and invalidation machinery | `triangulation.py`, `invalidation.py` |
| Bibliographic graph (evolved from CerebroSSRN) | PR #52: 3,819 nodes / 5,082 edges, zero missing destinations, anti-fuzzy-merge policy |
| Factory→Brain causal contract | `factory_adapter.py` (PR #49) |
| RUN-LEARNING-PACKET ingestion | `run_learning_packet.py` (B branch) |
| Genesis real memory (CYCLE-001 lessons) | `artifacts/hippocampus/cycle001_genesis_ledger.jsonl` |

## Parity matrix (capability → old / current / gap)

| Capability | CerebroSSRN | edge_brain | Gap |
| --- | --- | --- | --- |
| Semantic retrieval over raw passages | ✅ embeddings e5-small, cross-lingual, benchmarked (v2) | ❌ none | **EDGE-001: edge_brain cannot retrieve passages; only structured records** |
| Corpus extraction pipeline (PDF→claims with citations) | ✅ full F0–F2.5 with verbatim-citation validation | ❌ none (graph arrived pre-built) | **EDGE-002: no reproducible extraction pipeline in repo** |
| Concept consolidation with judge audit trail | ✅ fuzzy + `decisiones_jueces.json` | ⚠️ policy only (anti-fuzzy-merge in #52) | **EDGE-003: current policy refuses merges but has no adjudicated-merge mechanism** |
| Community detection / thematic map | ✅ Louvain + summaries | ❌ none | **EDGE-004: no topical structure over the 3,819-node graph** |
| Ecosystem bridge (theory ↔ own backtests) | ✅ `PUENTE_ECOSISTEMA.md` with 5 concrete uses | ❌ none | **EDGE-005: bibliographic graph is not linked to EdgeLab episodes** |
| Experiment ledger | ✅ narrative, 30+ EXPs with refutations | ✅ typed, durable, tamper-evident | different strengths: old = readable narrative habit; new = machine-checkable |
| Typed records / replay / integrity | ❌ prose only | ✅ hash-chained, deterministic | old ledger cannot be machine-verified |
| Fail-closed gates (outcomes/holdout/promotion) | ❌ none (relied on operator discipline) | ✅ structural | — |
| Invalidation + stale-artifact blocking | ❌ none | ✅ persisted invalidations | — |
| Skepticism / robustness declarations | ✅ explicit per finding | ⚠️ authority_status exists but no robustness field on lessons | **EDGE-006: LessonCandidate lacks robustness/conditions fields** |
| Retrieval-quality benchmark | ✅ `benchmark_corteza.py` + seed set | ❌ none | **EDGE-007: no measurable retrieval regression gate** |

## What the old brain proves is worth porting

1. **Passage-level RAG with a benchmark** — the single biggest capability gap. Without it, edge_brain answers from structure alone.
2. **Verbatim-citation discipline in extraction prompts** — cheap to port, prevents paraphrase drift.
3. **Ecosystem bridge pattern** — the PUENTE document is exactly the "biblioteca ↔ episodios" link proposed in the roadmap (A.4); the old brain already proved its value.
4. **Narrative ledger as projection** — generate a `LEDGER.md` rendering from the durable ledger on each write: humans read prose, machines read JSONL. Best of both.

## What the old brain must NOT bring back

- No outcomes/holdout gating: EXP entries reference live backtests; any ingestion maps them to `RUN_OBSERVATION_UNADJUDICATED`, never evidence.
- Fuzzy auto-merge of concepts (the old one needed judge repair; #52's `EXACT_OR_DISTINCT_TARGET_ONLY_NO_FUZZY_MERGE` is the learned correction).

## Recommended next actions

1. Port `benchmark_corteza`-style retrieval gate when embeddings land (EDGE-007 first — it defines "better").
2. Add embeddings retrieval over ledger + SSRN passages (EDGE-001) using the old `nodos_emb.npy`/passages as the starting corpus.
3. Ingest `LEDGER_EXPERIMENTOS.md` as typed records with `authority_status=HISTORICAL_NARRATIVE` (EDGE-005).
4. Add `robustness` and `conditions` fields to LessonCandidate (EDGE-006) — schema migration v1→v2 of the durable ledger, designed before growth.
5. When CerebroJLP arrives: same matrix, expecting to confirm the 5 shared design principles and diff domain-specific machinery.
