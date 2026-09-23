# CerebroSSRN — semantic relation debt resolution

## Decision

All 1,331 relation destinations previously listed in `grafo/relaciones_sin_destino.json` are now materialized. The resolved projection has zero missing endpoints.

The resolver deliberately does **not** fuzzy-merge a missing destination into a similar existing concept. Similar strings may be opposites or different objects (`market inefficiency` vs `market efficiency`, `normal distribution` vs `lognormal distribution`, `feasible` vs `infeasible`). A wrong merge is harder to detect and undo than an explicit target-only node.

## Policy

`EXACT_OR_DISTINCT_TARGET_ONLY_NO_FUZZY_MERGE`

Each missing destination already had evidence: one or more extracted relations with paper `doc_id`. It therefore becomes an evidence-backed target-only node with:

- the exact normalized destination as stable ID;
- every observed spelling;
- source document IDs;
- relation types and mention count;
- `semantic_status=RESOLVED_AS_DISTINCT_TARGET_NODE`;
- `type_status=TARGET_ONLY_UNCLASSIFIED`;
- `authority_status=LLM_EXTRACTED_CONCEPT`.

This resolves graph topology without pretending that a node's ontology has been human-adjudicated.

## Relation types

The twelve canonical relation types remain canonical. Previously adjudicated overrides from `decisiones_jueces.json` are applied. Twenty-six other extracted relation types are retained verbatim with `relation_status=EXTRACTED_TYPE_UNADJUDICATED`; they are not deleted and are not promoted to evidence.

## Verified result

| Metric | Before | After |
| --- | ---: | ---: |
| Nodes | 2,488 | 3,819 |
| Edges | 3,476 | 5,082 |
| Missing destination objects | 1,331 | 0 |
| Missing graph endpoints | — | 0 |
| Raw relation mentions recovered | — | 1,658 |
| Resolved edges added | — | 1,606 |

Resolved graph SHA-256: `6a17df594362f2b9306531dc0b56243b01bcba61665571044bd41f7523cf14bb`.

Resolution decisions SHA-256: `48f9bc709cf28d84c7169e1638497ccea744c29d18efb008d56873c41d8b8499`.

Focused tests: 9/9 PASS. The build checks that all edge origins and destinations exist, the unresolved projection is empty, and hashes are deterministic.

## Rebuild

```bash
python tools/resolve_ssrn_semantic_debt.py "$EDGELAB_SSRN_CORPUS_ROOT" /output/ssrn-semantic-resolved
```

Outputs:

- `grafo_resuelto.json`;
- `resolucion_deuda_semantica.json`;
- `relaciones_sin_destino.json` containing `[]`;
- `resumen_resolucion.json`.

**Aporte al referente:** converts all missing relation destinations into explicit, source-backed graph objects while refusing unsafe synonym/antonym guesses and preserving the distinction between extracted semantics and verified evidence.
