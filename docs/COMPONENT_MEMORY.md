# Memoria y controles: responsabilidades y acceso

## Qué es cada parte

- `hippocampus.py`: objetos y reglas de memoria en proceso.
- `hippocampus_store.py`: persistencia encadenada, replay e invalidaciones. Es la autoridad del ledger operativo, no un veredicto económico.
- `retrieval.py`: consulta léxica BM25 determinista. `LedgerIndex.from_ledger` verifica replay antes de indexar; no implica retrieval semántico ni corpus SSRN.
- `typed_registry.py`: relaciones tipadas, append validado y proyecciones. Arrow se carga sólo al solicitar Parquet.
- `schema_validator.py` + `schemas/`: 35 contratos JSON empaquetados. Tener un schema de atlas o skill **no** implementa ese módulo ni configura un agente.
- `triangulation.py`, `model_policy.py`, `control_guard.py`: controles con alcance propio. No equivalen al controlador del servidor autónomo.
- `result_lineage.py`: revisión read-only/opt-in del envelope de resultados. No verifica bytes/autoridad, no muta el ledger ni decide sesgo o promoción. [Entrada y pendientes](RESULTS_START_HERE.md).

## Ejemplo mínimo: memoria operativa sintética

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from edgelab.edge_brain.hippocampus import AnalysisEpisode
from edgelab.edge_brain.hippocampus_store import DurableHippocampus
from edgelab.edge_brain.retrieval import LedgerIndex

with TemporaryDirectory() as folder:
    path = Path(folder) / "synthetic.jsonl"
    store = DurableHippocampus(path)
    store.register_episode(AnalysisEpisode(
        episode_id="SYNTHETIC-1", goal="synthetic environment check",
        status="COMPLETED_UNADJUDICATED",
        created_at_utc="2026-10-09T00:00:00Z",
        updated_at_utc="2026-10-09T00:00:00Z",
        recorded_by="synthetic-example", outcomes_inspected=False,
    ))
    tip = store.tip_hash
    assert store.verify(expected_tip_hash=tip) == tip
    assert LedgerIndex.from_ledger(path).query("synthetic environment")
```

## Integridad y límites

Una cadena válida no detecta por sí sola un rollback a un prefijo válido: conservar/verificar anchors o tip externo esperado. La consulta no sustituye ese chequeo ni adjudica autoridad a registros. JSONL y proyecciones no se usan como evidencia de edge sólo porque sus hashes verifican.

No registrar outcomes/artefactos privados sin autorización y contrato de campaña. No ejecutar aprendizajes como instrucciones. Claims bibliográficos viven en el componente SSRN, aún fuera de esta base; lecciones operativas no los vuelven evidencia confirmatoria.

Core-only incluye jsonschema y no requiere Arrow para relaciones, validación o búsqueda. Parquet requiere el extra correspondiente. [Entorno](ENVIRONMENT.md) · [Mapa](COMPONENTS.md).
