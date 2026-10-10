# Entradas de datos y cobertura del gate

Esta matriz describe wiring de código, no certificación de datos ni permisos de ejecución.

| Entrada | Gate antes de fuente | Alcance activo / límites |
|---|---|---|
| `tools/check_research_data_gate.py` | Sí; ninguna fuente de mercado se abre | CLI de metadatos, PASS_METADATA_ONLY; no adjudica permisos |
| `research_session.read_research_session` | Sí | Nueva ruta opt-in: shard homogéneo, D-1/liquidez/pins, footer y hash antes de payload |
| `nt8_reader.audit` | No | Parser de iterable; el caller controla fuente, fechas y permisos |
| `continuous_contract.build_continuous_series` | No | Ruta legacy: lee contratos enteros antes del filtro; NO usar como firewall de reservas |
| `tools/run_funnel_arrays.py` | No | Split validado antes de precios, sólo kernels CPU D0/D1 aislados; no gate de custodia/liquidez upstream |
| `databuild` / scripts MGC | No | Builders históricos; no aprobar por presencia o por tests del lector nuevo |
| `tools/kaggle_spec_v2.py` | No gate de research | Infra técnica local; agregados/conservación no certifican calidad ni liquidez |
| `kaggle.aggregate_audit` | Pins/footer antes de filas | QA sobre archivos preholdout aprobados; no saneamiento de ticks ni outcomes |
| `kaggle.research_access` | Sí, opt-in | Política causal + evidencia/liq externa + cobertura diaria de toda la ventana; v15 bloqueado; todas las sesiones del archivo autorizadas antes de precios |
| `kaggle.coverage_inventory` | QA, no research | Toda fecha solicitada y ausencia de observación declaradas; sólo payload identidad/timestamp; calendario no certificado |
| `kaggle.raw_tick_audit` | QA, no research | Ticks canonical v1 con hash/footer y bitmap exacto de identidad; continuidad upstream/calendario/liquidez NO certificados |

## Responsabilidades

- Auditor independiente: verifica fuente, bytes, calendario, completitud y liquidez; emite evidencia revisada.
- Autoridad de campaña: fija hashes/umbrales, fechas y particiones, incluido D2; concede aprobación por separado.
- Gate: comprueba consistencia de esas declaraciones; un hash autoconsistente no autentica a nadie.
- Lector nuevo: limita la lectura a un shard de sesión con identidad auditable; no construye features ni hace research.
- Agente: elige la ruta declarada; ausencia de evidencia es STOP, no un motivo para usar la ruta legacy.

## Compatibilidad e historia

No se reescriben ledgers/certificados históricos ni se conecta silenciosamente el gate a todas las entradas.
Los errores de fecha/sesión/calidad deben conservarse como exclusiones, no normalizarse para pasar.
[Auditoría original PR 65](research/CANONICAL_DATA_AUDIT_20261004.md) y
[estado congelado](../artifacts/data_audit/canonical_20261004_status.json) conservan
su dictamen NOT_CERTIFIED_FOR_NEW_STRATEGY. Este port no declara PR 65 totalmente resuelto.

[Contrato/API de datos](COMPONENT_DATA.md) · [Plan](INTEGRATION_PLAN.md) · [Mapa](COMPONENTS.md).
