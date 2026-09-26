# Brain capability parity matrix — CerebroSSRN + CerebroJLP vs edge_brain

**Updated:** 2026-09-23  
**Source A (old):** `$ACerebroSSRN.rar` (66 MB; Kaggle dataset `edgebrain-cerebro-ejemplos-auditores`; archive-backed baseline, see 2026-09-22 evidence below).  
**Source B (old):** `CerebroJLP_Fusionado_Diagramas.zip` (120,411,976 bytes; archive inspected locally on 2026-09-23).  
**Source C (current):** `edgelab/edge_brain`, PR #52 base plus durable hippocampus branch at `b10a0b8f9899c7989d9855e7c6fac1780bfd0914`.  
**Scope:** capability and artifact audit only. No outcomes, no holdout, no authority transfer. Legacy content remains historical/narrative unless independently revalidated.

## What each brain actually has

### CerebroSSRN (old)

| Capability | Evidence in archive |
| --- | --- |
| PDF→text pipeline with manifest | `pipeline/extract_pdfs.py`, `Normalizado/manifest.*` (401 documents, 5.25M words per the original audit) |
| Passage retrieval | `pipeline/chunk_docs.py`, `embed_chunks.py`, 24,340 passages and multilingual-e5-small embeddings; cross-lingual ES→EN benchmarked in v2 |
| LLM extraction with verbatim-citation discipline | `extraccion/PROMPT_EXTRACCION.md`, 401 extracted JSONs, validation artifact |
| Concept consolidation + adjudication trail | `pipeline/consolidate_concepts.py`, `grafo/decisiones_jueces.json`; fuzzy candidates required judge repair |
| Graph + communities | `pipeline/build_graph.py`, Louvain and narrative summaries |
| Ecosystem bridge + narrative experiment ledger | `cerebro/PUENTE_ECOSISTEMA.md`, `cerebro/LEDGER_EXPERIMENTOS.md` (30+ EXPs including refutations) |

### CerebroJLP (old)

Evidence from archive inspection (not merely `PLAN.md` claims):

| Capability | Evidence found | Qualification |
| --- | --- | --- |
| Passage corpus and indexes | `Normalizado/chunks.sqlite`: 4,795 `chunks`, 37,286 `passages`; populated FTS5 virtual table; 169 distinct `doc_id` values represented in chunks | DB is a packaged snapshot; does not by itself establish source completeness or rebuildability |
| Passage embeddings | `Normalizado/embeddings.npy` shape `(37286,384)` float32 and aligned `embeddings_ids.npy`; `grafo/nodos_emb.npy` shape `(1268,384)` with 1,268 node IDs | Embeddings are present, but model weights/tokenizer are not in this ZIP; semantic queries require local model files or a network download |
| Hybrid retrieval | `mejoras/consultar_v2.py`, `build_fts.py`, `memoria_diagramatica.py`: semantic + FTS5 lexical search fused with RRF; semantic node lookup; multi-query (`||`); neighboring passage option; JSON output includes passage/document IDs | Code is present; full semantic runtime was not executable offline from the ZIP because `modelo/multilingual-e5-small` is absent. FTS5 table is populated and lexical path is inspectable |
| Graph/canonical concepts | `grafo/grafo_v3.json` lists 1,268 nodes; `grafo/grafo_v3_stats.txt` reports 1,268 nodes / 3,383 edges / 126 isolated / 136 weak components | The JSON's `meta.total_nodos` says 1,301, inconsistent with its 1,268-node list. Older `grafo_final` reports 1,296 nodes / 3,215 edges; artifacts are from different snapshots |
| Topical map | `grafo/comunidades.json`, `comunidades_resumen.md`, Louvain pipeline | Summary reports 170 communities and 135 isolates, which does not match the v3 stats snapshot (136 components, 126 isolates); treat it as version-skewed, not current verified output |
| Diagram/topology memory | `grafo/diagramas/manifest.json`, 11 covered images, 10 families; `AUDITORIA.json` reports 0 failed checks; `topologia_*.json`, `pipeline/inject_diagram_edges.py`, `inject_11_pasos.py` | Strong domain-specific representation, but not a market/empirical validation system |
| Contextual adjudication of merges | `PLAN.md`, `grafo/notas_dominio_para_fase3.md`, `pipeline/apply_fable_review.py`, review outputs | Explicitly recognizes transcription errors vs synonyms vs distinct concepts and retains human decisions; supports contextual/citation-based adjudication rather than string similarity alone |
| Cases/uncertainty handling | `casos_aplicados_confirmados.json`, `_dudosos.json`, `_neutros.json`, conservative contamination scan and reviewed false positives | The plan reports 335 cases not classified; uncertainty is preserved rather than silently forced into yes/no |
| Narrative/guardrails | `cerebro/CEREBRO_JLP.md`, `COMO_USAR.md`, `README_INSTALACION.md` | It explicitly disclaims representing JLP or replacing a professional/teacher and warns of ASR errors; its conceptual content is not evidence for EdgeLab claims |

### JLP packaging and reproducibility caveats

- The database contains 169 source-document IDs, but the archive has only 100 files under `Todos.txt`; `extraccion/completo/` and `extraccion/auditado/` are absent. This does not prove which source texts are missing, but it means the archive is not a self-contained copy of the inputs used by `rebuild_graph.py`.
- `pipeline/rebuild_graph.py` is a useful declarative-rebuild design, but hard-codes `C:\Users\nicoc\CerebroJLP` and reads the absent `extraccion/{auditado,completo}` plus `grafo/grafo_v2.json`; a clean rebuild from this delivered ZIP is therefore not demonstrated.
- `mejoras/README_MEJORAS.md` reports cosine similarity 1.0 for the NumPy e5 implementation, but this could not be independently reproduced because the model/tokenizer files are absent. Treat as author-reported, not verified here.
- The archive includes no retrieval seed benchmark or independently reproducible retrieval-quality score that could substantiate the claimed quality of the query system.
- Edge-label composition is still a material caveat: v3 has 1,530 `PARTE_DE` edges out of 3,383 (~45.2%). The rebuild maps generic `ASOCIADO_A` to `PARTE_DE`; this is documented as a low-confidence fallback, so the apparent part-whole semantics must not be taken literally without adjudication.

## edge_brain (current at reviewed branch head)

| Capability | Evidence | Status / limits |
| --- | --- | --- |
| Typed experimental records | `hippocampus.py` | Typed episodes, steps, failures, successes, lessons, counterexamples |
| Durable tamper-evident memory | `hippocampus_store.py`, genesis and research-history JSONL | Hash-chained append-only ledger; deterministic replay; proposal/low-confidence ceiling |
| Search over memory | `retrieval.py` on PR #56 | Deterministic BM25 over structured ledger records; **partial** parity only, not semantic passage retrieval |
| Typed registry, measurement coverage, triangulation and invalidation | `typed_registry.py`, `schema_validator.py`, `measurement_atlas.py`, `coverage.py`, `eligibility.py`, `triangulation.py`, `invalidation.py` | Stronger explicit machine-enforced authority and fail-closed controls than either legacy brain |
| Bibliographic graph | PR #52 | SSRN-derived graph; unresolved relations are preserved and fuzzy auto-merge is rejected |
| Narrative projection | `render_markdown()` on PR #56 | Human-readable projection while JSONL remains canonical |
| Robustness/conditions | `LessonCandidate` on PR #56 | Fields added with v1-compatible defaults, but formal versioned migration is not yet defined |

**PR #56 currentness check (2026-09-23):** head still equals `b10a0b8f9899c7989d9855e7c6fac1780bfd0914`; base still equals #52 head `3cb3fd21d44e8a8fa1f931e01f09eea83e71d6b9`. GitHub reports `mergeable_state=unstable`; two current Python 3.12 pytest check runs are **failed**. Thus the branch is current against #52 but is **not merge-ready**. Do not merge until the failing run logs/root cause are recovered and CI passes. The previous local focal tests do not override these remote failures.

## Combined parity matrix (capability → legacy brains / edge_brain / gap)

| Capability | CerebroSSRN | CerebroJLP | edge_brain at #56 | Gap / decision |
| --- | --- | --- | --- | --- |
| Search/retrieval | Semantic retrieval over 24,340 passages; benchmark artifacts reported | Hybrid semantic + FTS5 over 37,286 passages, graph node vectors, RRF, context-neighbor and citeable JSON | BM25 over typed ledger records | **EDGE-001 partial:** preserve BM25 baseline; add cited passage retrieval only behind source/hash provenance and a benchmark. Do not claim semantic parity yet |
| Corpus extraction | PDF→text, paper extraction, citation checks | Transcript normalization/chunking/extraction code; packaged source inputs incomplete | No general extraction pipeline | **EDGE-002:** define an input manifest + source checksums + portable, rerunnable stages; legacy JLP ZIP alone cannot be a complete rebuild fixture |
| Entity/concept consolidation | Fuzzy clusters plus judge audit; historical repairs | Contextual manual adjudication, transcription-aware corrections, contamination review | Anti-fuzzy-merge safety policy; no adjudicated merge workflow | **EDGE-003:** add explicit proposed→reviewed merge records with evidence/context and reversible lineage; never restore fuzzy auto-merge |
| Thematic structure | Louvain + narrative summaries | Louvain + summaries and diagram topology | None identified | **EDGE-004:** useful for corpus navigation, but defer until benchmark and provenance; preserve stale/version-skew flags |
| Diagram/structured spatial memory | Not a primary capability | Explicit 11-step/4-coordinate/4-role/Peirce topology with audited diagram files | No diagram-specific subsystem | Candidate representation pattern only; not evidence or an edge claim |
| Bridge from concepts to operational cases | Ecosystem bridge document | Domain reasoning over transcript/case examples | Factory→Brain causal contract exists, but no legacy-to-EdgeLab semantic bridge | **EDGE-005:** any bridge must be explicit, citeable, and `HISTORICAL_NARRATIVE`; no inherited outcomes/evidence |
| Human-readable learning narrative | 30+ EXP narrative ledger | Rule-guided assistant and retrieval/context format | Deterministic Markdown projection of typed ledger | Keep machine ledger canonical; regenerate narrative projection; import legacy prose only with status/provenance |
| Authority / outcomes / holdout | Operator discipline | Disclaimers and source uncertainty; no EdgeLab gates | Structural validation, no self-promotion, durable counterexamples, holdout controls | Preserve edge_brain controls. Never import legacy outcomes as EdgeLab evidence or open holdout |
| Robustness and uncertainty | Robustness declarations on findings | Explicit doubtful/neutral cases; ASR/source caveats | `robustness=UNRATED`, `conditions=[]` introduced | **EDGE-006 partial:** add adjudicated, scoped robustness/conditions schema only with an explicit v2 migration and replay fixtures |
| Retrieval-quality validation | Seed benchmark reported in SSRN v2 | No verifiable seed benchmark found in ZIP | No retrieval benchmark on this branch | **EDGE-007 open:** establish fixed query/gold set, source-citation correctness, recall/nDCG and regression gate before adding embeddings |
| Reproducibility | Documented stages; archive audited in #52 | Some deterministic rebuild intent, but hard-coded path and missing inputs prevent ZIP-to-output reproduction | Hash-chain replay is deterministic | Require clean-room rebuild from manifest-pinned inputs; do not confuse replay determinism with source-pipeline reproducibility |

## Lessons worth porting (with constraints)

1. **Hybrid retrieval architecture:** combine lexical exact-match (rare terminology/names) with semantic retrieval (paraphrase) and deterministic rank fusion; add citation identifiers and neighbor context. First port the interface/evaluation contract, not unvalidated vector machinery.
2. **Evidence-context adjudication:** judge merge candidates using source quotation and provenance, distinguishing ASR error, true synonym, and distinct concepts. Store decision, reviewer, source span, and superseded IDs; do not use fuzzy similarity as the decision.
3. **Represent uncertainty explicitly:** preserve confirmed/doubtful/neutral or unreviewed states; do not turn ambiguous extraction into binary truth.
4. **Represent diagrams/topology as sourced structured data:** can help explain a domain model, but every edge needs source and confidence; keep this as representation, not empirical proof.
5. **Two views, one authority:** narrative ledger is generated from append-only typed JSONL; it must never become a competing source of truth.

## Do not port

- No legacy claim, transcript interpretation, case outcome, or trading result becomes EdgeLab evidence. Ingestion status must be `HISTORICAL_NARRATIVE`, with source hash and scope.
- No automatic fuzzy merge; retain distinct concepts until a contextual adjudication is recorded.
- No promotion of lessons based on author-reported benchmark/model scores or graph centrality.
- No treating v3/final/community files as a single synchronized snapshot until their count discrepancies are resolved.

## Recommended order

1. **Resolve PR #56 CI failures** before merge; remote pytest is red even though branch/base SHAs are current.
2. **Freeze a JLP custody manifest:** archive hash; exact input/output files; reconcile node counts (`meta` 1,301 vs list/stats 1,268), final vs v3 graph, and community version skew; document the 100 packaged raw texts vs 169 chunk doc IDs.
3. **Build EDGE-007 retrieval benchmark first** from approved, non-sensitive, citation-grounded questions. Score source/quote correctness as well as ranking. No retrieval model promotion without beating the lexical baseline.
4. **Port a thin source adapter** that emits source IDs, exact passage IDs, verbatim spans, archive hash, and `HISTORICAL_NARRATIVE`; keep content physically/logically separate from EdgeLab trading evidence.
5. **Add contextual merge adjudication and versioned lesson schema** with tests for replay/migration and no-self-approval; never fuzzy auto-merge.
6. Only after the above, evaluate thematic/diagram projections and semantic retrieval. Any claims remain provisional until independent review.

## Evidence scope / limitations

The JLP findings above are direct file/database inspections of the user-provided ZIP. The SSRN and EdgeLab descriptions refer to the previously audited archive and GitHub PR artifacts; those old external archives were not re-extracted in this resumed sandbox. This update therefore validates the **JLP ZIP** and **current PR metadata/check state**, not every historical source artifact. See the attached source page in Notion for the two old-brain archives and the current PR for code/tests.