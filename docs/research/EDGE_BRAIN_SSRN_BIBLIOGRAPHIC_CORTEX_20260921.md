# Edge Brain — CerebroSSRN Bibliographic Cortex

## Scope

This component integrates the complete user-supplied CerebroSSRN corpus into the Edge Brain without treating literature or the historical experimental ledger as verified EdgeLab evidence.

The canonical payload is `$ACerebroSSRN.rar`, SHA-256 `970d55ea05798b2013cb1876a34aae573a96ec5418d010e2a595ca2768816475`. It contains 401 usable normalized papers, 401 complete extractions, 3,254 chunks, 24,340 passages, 771 author-reported findings and a 2,488-node/3,476-edge graph. The original manifest has 402 rows; the executable document list has 401 paper IDs.

## Architecture

- **Bibliographic Cortex:** source identity, full-text passage retrieval, graph, claims and version relationships.
- **Bibliographic Hippocampus:** all 24,340 passages remain searchable and produce citable, bounded context packs.
- **Experimental Hippocampus:** EdgeLab episodes, failures, repairs, counterexamples and lessons.
- **Bridge:** literature can motivate or contradict an episode, but cannot promote itself and never becomes computed evidence.

Raw texts, SQLite and embeddings remain an external hash-addressed artifact. Git stores the adapter, frozen counts, tests and deterministic ledger builder. This avoids silently publishing a large private corpus while preserving full reconstruction and auditability.

## Fail-closed authority

Imports default to `LITERATURE_CLAIM_UNVERIFIED`, `LLM_EXTRACTED_CONCEPT`, `AUTHOR_REPORTED_RESULT`, and `HISTORICAL_EXPERIMENT_PENDING_REAUDIT`. The historical ledger is imported only as pending claims. Old positive edges are not promoted. Duplicate versions must be linked before they count as independent support.

## Commands

```bash
export EDGELAB_SSRN_CORPUS_ROOT=/path/to/$ACerebroSSRN
python tools/ssrn_brain_cli.py audit "$EDGELAB_SSRN_CORPUS_ROOT" --archive /path/to/ACerebroSSRN.rar
python tools/ssrn_brain_cli.py search "$EDGELAB_SSRN_CORPUS_ROOT" "order flow imbalance" -k 6
python tools/ssrn_brain_cli.py ingest "$EDGELAB_SSRN_CORPUS_ROOT" artifacts/edge_brain/ssrn_bibliographic_ledger.jsonl --overwrite
python tools/edge_brain_cli.py verify-ledger artifacts/edge_brain/ssrn_bibliographic_ledger.jsonl
```

## Definition of complete

1. Archive hash matches.
2. All 401 paper IDs have normalized text and complete extraction.
3. SQLite and graph counts match the frozen config.
4. A custody manifest hashes every paper and extraction.
5. Generated ledger verifies as append-only/hash-chained.
6. Retrieval returns citable passages with source IDs.
7. No imported claim is `SUPPORTED` or used as outcome evidence.

**Aporte al referente:** gives the Brain its missing bibliographic memory while preserving the boundary between published claims, historical experiments and newly computed EdgeLab evidence.
