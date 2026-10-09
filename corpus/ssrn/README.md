# CerebroSSRN — hipocampo bibliográfico del Edge Brain

401 papers de SSRN (microestructura, order book, trading algorítmico, arbitraje estadístico, pairs trading, HFT, VWAP, finanzas cuantitativas) con extracciones, grafo de conceptos (2.488 nodos / 3.476 aristas), 771 hallazgos reportados por autores y el ledger histórico de experimentos.

## Uso

```bash
pip install -r requirements-edge-brain.txt
python tools/ssrn_corpus_bootstrap.py            # rearma archivos partidos + reconstruye chunks.sqlite + verifica
export EDGELAB_SSRN_CORPUS_ROOT=corpus/ssrn
python tools/ssrn_brain_cli.py search corpus/ssrn "intraday momentum"
```

Desde Python: `SSRNBibliographicCortex("corpus/ssrn").context_pack("consulta")`.

## Reglas

- Todo lo que sale de acá es `LITERATURE_CLAIM_UNVERIFIED` / `AUTHOR_REPORTED_RESULT`: **no es evidencia** de EdgeLab hasta reproducirlo.
- Los textos se versionan byte a byte (`-text` en `.gitattributes`); los hashes por paper están en `config/edge_brain/ssrn_corpus_repo_v1.json`.
- Derivados no versionados: `chunks.sqlite` (se reconstruye idéntico), `embeddings.npy` (índice semántico e5 opcional, `pipeline/embed_chunks.py`).
- Archivo fuente: `$ACerebroSSRN.rar`, sha256 `970d55ea05798b2013cb1876a34aae573a96ec5418d010e2a595ca2768816475`.
