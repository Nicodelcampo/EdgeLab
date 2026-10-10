# Kaggle: infraestructura, QA y acceso de research

## Papel dentro de EdgeLab

Resolver/spec → kernels técnicos offline → merge de evidencia → almacén agregado → QA.
Esto NO ejecuta hipótesis económicas, certifica fuentes ni configura al agente autónomo.
El componente está local; el estado del dataset publicado sigue **BLOCKED para research causal**.

| Entrada / API | Responsabilidad y alcance |
|---|---|
| `tools/kaggle_spec_v2.py` | Generar/ejecutar preflight y agregados target-free, shards por contrato, manifest/attestation/zip, unión fija y consumidor técnico |
| `tools/audit_kaggle_aggregates.py` | QA estructural por batches con manifest/resolver fijados externamente; no emite certificado |
| `aggregate_audit.audit_aggregate_store` | Retorna reporte sin precios + totales privados para reconciliación; no reescribe fuente |
| `research_access.require_research_store` | Gate metadata-only; política causal, evidencia y límites externos obligatorios; v15 NO pasa |
| `research_access.load_research_bars` | Consumidor opt-in de research: aprobar TODAS las sesiones del archivo antes de precios, no sólo ventana; funciona desde wheel |
| `tools/kaggle_hippocampus_ingest.py` | Anexar evidencia técnica al store durable existente bajo lock; sin trials/promoción; escribir requiere autorización separada |

## Acceso mínimo

```bash
python tools/edgelab_catalog.py show kaggle-execution
python tools/kaggle_spec_v2.py --help
python tools/audit_kaggle_aggregates.py --help
```

QA real necesita `--store`, `--resolver`, los dos `--expected-*-sha256` del manifiesto
aprobado y `--out` nuevo. No calcular pins del input actual para simular autoridad.
`PASS_AGGREGATE_STRUCTURE_ONLY` no habilita el consumidor de research.

`load_research_bars(start=..., end=..., seconds=..., **evidence)` recibe `store`,
`resolver`, `instrument`, `expected_manifest_sha256`, `expected_resolver_sha256`,
`certificate`, `regime_manifest`, `liquidity_limits` y los tres pins definidos en el
[gate de datos](COMPONENT_DATA.md). El certificado externo debe vincular el manifest
agregado y su estructura revisada; la política causal estructurada del resolver es
`previous_complete_session_causal_eligibility_v1`. Las salvedades necesitan resolución
reviewed/pinned explícita por sesión. No se fabrica un bundle de aprobación.

## Identidades y compatibilidad

El port se adapta a main tras #71 y usa imports reales de memoria, sin fake sys.modules.
El hash del runner identifica los bytes nuevos; `BASE_COMMIT` es la base de integración,
no una afirmación de árbol git limpio. Spec/artifacts/ledger anteriores siguen históricos
con su runner original y no se regeneran ni se certifican por el port.
La ruta v2 técnica mantiene HOLDOUT-A3 (2026-10-01); el contrato original de cada
campaña, incluido D2, puede ser más restrictivo. Los módulos v1 de otras ramas con
sello de julio NO se portan ni se mezclan con esta autoridad.

## Bloqueos operativos y de calidad

- [QA vigente del dataset](infra/KAGGLE_DATA_QUALITY_20261010.md): ticks/calendario,
  causalidad de máscara, conflictos y límites de liquidez pendientes.
- La generación declara inputs versionados, pero guardar un notebook vía custom MCP
  no demuestra mounts. La interfaz funcionó históricamente; no hay scheduler remoto
  ni attach MCP fiable nuevo en este lote. Mantener ejecuciones privadas/offline.
- Raw-file SHA256/certificados de ticks no se computaron en el agregado original.
- El loader técnico legacy sigue sin gate de research: usarlo sólo para QA, nunca
  como bypass. [Matriz completa](DATA_CONSUMER_MATRIX.md).
- Hashes/certificados son declaraciones externas, no autenticación de aprobadores.
  Fuente inmutable y metadatos auditados; nada de fallback silencioso ni lectura
  whole-file de particiones no autorizadas.

[Historia PR 68](infra/KAGGLE_SPEC_V2_20261009.md) · [Mapa](COMPONENTS.md) · [Plan](INTEGRATION_PLAN.md).
