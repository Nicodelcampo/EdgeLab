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

## Conexión con el Edge Brain (`edgelab/edge_brain/literature_bridge.py`)

```python
from edgelab.edge_brain.hippocampus_store import DurableHippocampus
from edgelab.edge_brain.bibliographic_cortex import SSRNBibliographicCortex
from edgelab.edge_brain.literature_bridge import EdgeBrainMemory

brain = EdgeBrainMemory(DurableHippocampus("artifacts/brain/hippocampus.jsonl"),
                        SSRNBibliographicCortex("corpus/ssrn"))
rec = brain.recall("order flow imbalance desbalance")        # solo lectura: propio + hallazgos + pasajes
cons = brain.consult(consultation_id="CONS-...", episode_id="EP-...", query="...",
                     purpose="antes de proponer H-...", recorded_by="agente", created_at_utc="...")
brain.cite("HYP-...", cons.consultation_id)                  # la hipótesis declara en qué se apoyó
pack = cons.context_pack("CP-...", "EP-...", token_budget=4000, created_at_utc="...")
```

- `recall` junta en una consulta la memoria propia (lecciones, fallas, éxitos, contraejemplos, consultas previas), los 771 hallazgos y los pasajes; cada resultado trae su `authority_status`.
- `consult` deja en el ledger del brain un registro `literature_consulted` (qué fuentes, hash de cada texto visto, episodio y propósito) y una dependencia `SUPPORTED_BY` por paper.
- `invalidate_source("SRC-SSRN-xxxx")` propaga `REQUIRES_REAUDIT` a las consultas e hipótesis que lo citaron; `reuse_artifact` las bloquea.
- El replay rechaza cualquier consulta con autoridad elevada (`claims_are_evidence` distinto de `False`).
- CLI: `python tools/ssrn_brain_cli.py recall corpus/ssrn "consulta" [--ledger brain.jsonl]`.
- Búsqueda léxica y determinista: los hallazgos están en castellano y los pasajes en inglés, así que conviene usar términos en ambos idiomas.
