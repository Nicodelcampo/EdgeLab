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

## Re-verificación y port a `main` (2026-10-09)

Port acotado desde `feat/ssrn-bibliographic-cortex-20260921` (PR #52) sobre `main`, sin arrastrar las 1.071 commits divergentes de la rama. `registry.py` es idéntico en ambas ramas; `hippocampus.py` de `main` se conserva.

Re-verificado contra `$ACerebroSSRN.rar` (Linux, Python 3.13):

- archive SHA-256 `970d55ea…816475`: **match**; 876 archivos.
- audit: `VERIFIED_COMPLETE` — 401 papers / 401 extracciones / 3.254 chunks / 24.340 pasajes / 771 hallazgos / 2.488 nodos / 3.476 aristas / 1.331 relaciones sin destino.
- custodia: `papers_aggregate_sha256 = 8abf0ede853f898f17ed3f17d758d1c2c4766ea52484987031a9de0486d7a45f` — **idéntico** al registrado.
- ingesta (`--created-at-utc 2026-09-21T13:15:00Z`): 1.971 registros, 402 fuentes, 798 claims, 771 aristas, 27 experimentos históricos; hash-chain PASS; determinista entre corridas.
- **Discrepancia abierta:** `ledger_sha256 = c6e2190a…de9a1` / `head_hash = 8b91423b…7d10`, distintos de los registrados el 2026-09-21 (`284458bd…`, `8471fff2…`), aun corriendo el commit original `a4f1fb9`. Conteos y custodia de papers coinciden, por lo que la diferencia es de serialización/entorno (probablemente Windows vs Linux), no de contenido. Pendiente de explicar antes de tratar el ledger como canónico.
- tests focales: 5/5 PASS.

El payload sigue externo (`EDGELAB_SSRN_CORPUS_ROOT`); Git no versiona los textos.
