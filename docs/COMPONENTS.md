# Mapa de componentes

Fuente de esta tabla: [registro JSON](../config/component_registry.json). Para consultas por agente use `python tools/edgelab_catalog.py show <id> --json`.

**Ubicación local no significa instalado, ejecutable sin datos ni certificado.** `other_branch` exige integración/revisión; `not_pushed` es información del usuario, no implementación observada. Categorías separan infraestructura, investigación, historia y planificación.

| ID | Propósito | Categoría | Ubicación | Rutas / referencias |
|---|---|---|---|---|
| `engine` | Simular fills, costos y salidas en una implementación compartida. | core | local | [edgelab/engine.py](../edgelab/engine.py), [CONTRATO_LLM.md](../CONTRATO_LLM.md) |
| `data` | Definir contratos, régimen y procedencia de datos antes de consumirlos. | core | local | [edgelab/data](../edgelab/data), [edgelab/bridge/session_preflight.py](../edgelab/bridge/session_preflight.py), [nt8_reader](../edgelab/data/nt8_reader.py), [nt8_timezone](../edgelab/data/nt8_timezone.py), [event_identity](../edgelab/data/event_identity.py), [config](../edgelab/config.py), [gate](../edgelab/data/research_data_gate.py), [lector de sesión](../edgelab/data/research_session.py), [matriz](DATA_CONSUMER_MATRIX.md) · [PR 65](https://github.com/Nicodelcampo/EdgeLab/pull/65) |
| `bridge` | Producir barras/indicadores y verificar paridad contra oráculos. | core | local | [edgelab/bridge](../edgelab/bridge) · [PR 17](https://github.com/Nicodelcampo/EdgeLab/pull/17), [PR 22](https://github.com/Nicodelcampo/EdgeLab/pull/22), [PR 34](https://github.com/Nicodelcampo/EdgeLab/pull/34) |
| `validation` | Auditar causalidad, simetría, ejecución y contrastes registrados. | core | local | [validation/harness.py](../validation/harness.py), [validation/verify.py](../validation/verify.py), [validation/mcpt.py](../validation/mcpt.py), [validation/pbo.py](../validation/pbo.py), [validation/spa.py](../validation/spa.py) |
| `funnel` | Screening CPU exploratorio con kernels de outcomes separados por D0/D1. | experimental | local | [edgelab/funnel](../edgelab/funnel), [contrato](COMPONENT_FUNNEL.md), [tools/run_funnel_arrays.py](../tools/run_funnel_arrays.py), [requirements-funnel.txt](../requirements-funnel.txt), [requirements-funnel-gpu.txt](../requirements-funnel-gpu.txt) · [PR 63](https://github.com/Nicodelcampo/EdgeLab/pull/63), [PR 64](https://github.com/Nicodelcampo/EdgeLab/pull/64) |
| `memory` | Persistir episodios, evidencia, lecciones e invalidaciones. | core | local | [edgelab/edge_brain/hippocampus.py](../edgelab/edge_brain/hippocampus.py), [edgelab/edge_brain/hippocampus_store.py](../edgelab/edge_brain/hippocampus_store.py), [retrieval](../edgelab/edge_brain/retrieval.py) · [PR 56](https://github.com/Nicodelcampo/EdgeLab/pull/56), [PR 58](https://github.com/Nicodelcampo/EdgeLab/pull/58) |
| `brain-controls` | Aplicar elegibilidad, políticas y trazabilidad a episodios. | experimental | local | [edgelab/edge_brain](../edgelab/edge_brain), [typed registry](../edgelab/edge_brain/typed_registry.py), [schemas](../edgelab/edge_brain/schemas) · [PR 43](https://github.com/Nicodelcampo/EdgeLab/pull/43), [PR 46](https://github.com/Nicodelcampo/EdgeLab/pull/46), [PR 58](https://github.com/Nicodelcampo/EdgeLab/pull/58) |
| `campaigns` | Conservar hipótesis, preregistros, negativos y artefactos por familia. | campaign | local | [docs/research](../docs/research), [strategies](../strategies), [edgelab/research](../edgelab/research) |
| `builders` | Construir productos de datos con trazabilidad contractual. | experimental | local | [databuild](../databuild) · [PR 65](https://github.com/Nicodelcampo/EdgeLab/pull/65) |
| `kaggle-execution` | Agregados técnicos offline, QA y acceso de research bloqueado sin evidencia causal/liquidez. | experimental | local | [contrato](COMPONENT_KAGGLE.md), [runner](../tools/kaggle_spec_v2.py), [QA](../tools/audit_kaggle_aggregates.py), [guard](../edgelab/kaggle/research_access.py) · [PR 68](https://github.com/Nicodelcampo/EdgeLab/pull/68) |
| `bibliography` | Buscar papers y claims bibliográficos con custodia. | integration_pending | other_branch | `corpus/ssrn`, `tools/ssrn_brain_cli.py`, `tools/ssrn_corpus_bootstrap.py` · [PR 67](https://github.com/Nicodelcampo/EdgeLab/pull/67), [PR 52](https://github.com/Nicodelcampo/EdgeLab/pull/52) · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `factory` | Separar generación de candidatos de evaluación y adjudicación. | experimental | other_branch | `edgelab/edge_factory` · [PR 43](https://github.com/Nicodelcampo/EdgeLab/pull/43), [PR 46](https://github.com/Nicodelcampo/EdgeLab/pull/46), [PR 54](https://github.com/Nicodelcampo/EdgeLab/pull/54), [PR 58](https://github.com/Nicodelcampo/EdgeLab/pull/58) · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `viewer` | Mostrar bundles y evidencia sin ocultar estado exploratorio. | integration_pending | other_branch | `viewer/nt8_bridge/index.html` · [PR 48](https://github.com/Nicodelcampo/EdgeLab/pull/48), [PR 41](https://github.com/Nicodelcampo/EdgeLab/pull/41) · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `propfirm` | Modelar condiciones de evaluación y EV del participante. | experimental | other_branch | `edgelab/propfirm` · [PR 48](https://github.com/Nicodelcampo/EdgeLab/pull/48) · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `context` | Representar información contextual y propuestas de regímenes. | experimental | other_branch | `edgelab/context`, `edgelab/gex`, `edgelab/regimes` · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `history` | Preservar procedencia y versiones retiradas sin activarlas. | historical | other_branch | `archive` · [foundation](https://github.com/Nicodelcampo/EdgeLab/tree/foundation/f0b-compatibility-probe) |
| `agent-coordination` | Reservar el límite de integración para agentes interactivos y futuros procesos autónomos. | planned | not_pushed | Pendiente de push; fuera de alcance actual |

## Interfaces disponibles

- [Datos: contrato, parser e identidad](COMPONENT_DATA.md).
- [Memoria: persistencia, consulta y controles](COMPONENT_MEMORY.md).
- [Resultados: trazabilidad, revisión histórica y límites de reutilización](RESULTS_START_HERE.md).

- [Funnel: aislamiento CPU, split y autoridad](COMPONENT_FUNNEL.md).
- [Kaggle: agregado técnico, QA y restricciones](COMPONENT_KAGGLE.md).

## Fronteras que no deben mezclarse

- Motor ≠ estrategias: las estrategias emiten señales; el motor calcula ejecución.
- Datos/custodia ≠ builders: una transformación no adjudica completitud ni permisos.
- Bibliografía ≠ hipocampo operativo: afirmaciones de papers no son resultados propios.
- Brain/Factory ≠ controlador autónomo: proponer/registrar no autoriza corridas ilimitadas.
- Visor ≠ oráculo: representar evidencia no la certifica.
- Regímenes descriptivos ≠ estrategia rentable: necesitan sus propios criterios de validación.
- Campaña ≠ módulo reutilizable: separar implementación genérica de parámetros/artefactos particulares.
- Histórico ≠ ruta activa: mantener accesible y rotulado, no borrar.

## Añadir o cambiar un componente

Actualizar el registro con propósito, ubicación, categoría, rutas, entradas, salidas, dependencias, límites y PR; regenerar esta tabla y pasar el chequeo de catálogo. Si se cambia una ubicación a local, todas las rutas declaradas deben existir. No autoejecutar un entrypoint ni tratar certificación como un booleano global.
