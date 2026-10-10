# Kaggle: infraestructura, QA y acceso de research

## Papel dentro de EdgeLab

Resolver/spec → kernels técnicos offline → merge de evidencia → almacén agregado → QA.
Esto NO ejecuta hipótesis económicas, certifica fuentes ni configura al agente autónomo.
El componente está local; el estado del dataset publicado sigue **BLOCKED para research causal**.

| Entrada / API | Responsabilidad y alcance |
|---|---|
| `tools/kaggle_spec_v2.py` | Generar/ejecutar preflight y agregados target-free, shards por contrato, manifest/attestation/zip, unión fija y consumidor técnico |
| `tools/audit_kaggle_aggregates.py` | QA estructural por batches con manifest/resolver fijados externamente; no emite certificado |
| `tools/audit_kaggle_coverage.py` / `coverage_inventory.audit_coverage` | Inventario de todas las fechas solicitadas + intervalos sin observación; summary separado de detalle privado; NO calendario ni actividad cero |
| `tools/audit_kaggle_raw_ticks.py` / `raw_tick_audit.audit_canonical_tick_file` | QA canonical_tick_v1 por batches; timestamp, cotizaciones, volumen e identidad exacta; no sanea ni certifica continuidad upstream |
| `aggregate_audit.audit_aggregate_store` | Retorna reporte sin precios + totales privados para reconciliación; no reescribe fuente |
| `research_access.require_research_store` | Gate metadata-only; política causal, evidencia y límites externos obligatorios; v15 NO pasa |
| `research_access.load_research_bars` | Consumidor opt-in de research: aprobar TODAS las sesiones del archivo antes de precios, no sólo ventana; funciona desde wheel |
| `tools/kaggle_hippocampus_ingest.py` | Anexar evidencia técnica al store durable existente bajo lock; sin trials/promoción; escribir requiere autorización separada |

## Entrada de datasets para agentes

[Empezar aquí](KAGGLE_START_HERE.md): `python -m edgelab.kaggle.discovery`,
snapshot portable de seis datasets/31 archivos con versiones y hashes, sin secretos.
La verificación de bytes no certifica research. [Anomalía de roll ES](infra/KAGGLE_ROLL_SELECTION_20261010.md)
es un bloqueo adicional del catálogo v15 y sus agregados.

## Acceso mínimo

```bash
python tools/edgelab_catalog.py show kaggle-execution
python tools/kaggle_spec_v2.py --help
python tools/audit_kaggle_aggregates.py --help
python tools/audit_kaggle_coverage.py --help
python tools/audit_kaggle_raw_ticks.py --help
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

## Cobertura diaria obligatoria del consumidor protegido

Además de los checks por sesión, `load_research_bars` exige `coverage_review`
dentro del certificado ya fijado externamente. Su esquema es
`edgelab_reviewed_daily_coverage_v1`, con `calendar_sha256`,
`interval_evidence_sha256` y lista `dates`. Cada fecha de la ventana solicitada,
incluidos fines de semana/feriados, debe tener `instrument`, `date`,
`evidence_sha256` y estado revisado:

- `VERIFIED_OPEN_COMPLETE`: sesión materializada, `interval_review: "PASS"`,
  `unresolved_intervals: 0` entero. La revisión externa debe resolver las ausencias
  como cierre programado/actividad cero demostrada o defecto reparado con nueva
  evidencia; no basta que haya una barra en ese minuto.
- `VERIFIED_SCHEDULED_CLOSED`: cierre sustentado en calendario revisado, sin
  sesión materializada que lo contradiga.

Ausencia, descarte por liquidez, UNKNOWN o contradicción bloquean **antes de hash o
lectura de precios**. La ventana no se acorta silenciosamente. Para trabajar una
subventana legítima se declara expresamente y se obtiene autorización específica,
no se transforma un hueco en cero ni se borra su existencia del inventario.
Los SHA referenciados son declaraciones de la revisión externa, NO firmas ni
verificación automática del calendario. Esta API no autentica al aprobador.

El diagnóstico `edgelab_coverage_diagnostic_v1` NO es el certificado anterior.
Los bins 17:00→17:00 Chicago sólo representan la convención de trade-date:
incluyen posibles mantenimiento/feriados; jamás son minutos esperados de trading.
`UNOBSERVED_ACTIVITY_UNKNOWN` no demuestra pérdida de ticks. La banda horaria
16:00→17:00 CT es un diagnóstico de reloj, NO una clasificación de cierre.
El detalle diario, identidades y totales de la QA cruda quedan privados.
Ambos CLIs preservan outputs anteriores y no reescriben ni interpolan fuentes.

[Auditoría de cobertura y lote crudo](infra/KAGGLE_COVERAGE_RAW_20261010.md).

## QA cruda completa y cuarentena de fuente

[Auditoría de los 18 primarios](infra/KAGGLE_FULL_RAW_AUDIT_20261010.md): estructura
PASS no habilita research. NQ preholdout v6 / NQ_09-26_ticks.parquet sigue con
horario/contenido discrepante; `KNOWN_UNRESOLVED_SOURCES` lo bloquea aun frente
a un certificado PASS. No se cambia la fuente ni se recorta la hora automáticamente.
`--include-clock-diagnostics` habilita conteos de reloj, no un calendario certificado.
