# Datos: responsabilidades y acceso

## Papel dentro de EdgeLab

`data` define contratos e identidad; `bridge` transforma/produce indicadores; `builders` crea derivados; Kaggle resuelve catálogo y ejecución. Ninguno sustituye a los otros ni adjudica permisos por su cuenta.

| API | Entrada → salida | Qué acredita / qué NO |
|---|---|---|
| `edgelab.config.resolve_settings` | TOML/env → `EdgeLabPaths` | Resuelve rutas; no lee precios ni aprueba fuentes |
| `nt8_contract.Nt8TickContract` | instrumento + timezone declarada → contrato | Declaración explícita; no demuestra el reloj real de la fuente |
| `nt8_reader.audit` | iterable de líneas + contrato → registros/reporte | Formato, precios, secuencia y diagnóstico; NO filtra automáticamente holdout ni valida liquidez |
| `nt8_timezone.verify_offset` | timestamps + offset declarado → diagnóstico | Chequeo temporal; no autorización para corregir silenciosamente el reloj |
| `event_identity.EventIdentityV2` / `audit_capture` | eventos tipados → IDs/reporte | Identidad/secuencias locales; no acredita continuidad upstream sin contrato de feed |
| `research_data_gate.require_research_eligibility` | evidencia + tres hashes externos → decisión técnica | Sólo metadatos; NO autentica aprobación ni adjudica saneamiento |
| `research_session.read_research_session` | shard de sesión + evidencia fijada → tabla + reporte | Gate antes de abrir fuente; stats homogéneas y SHA antes de deserializar; opt-in |
| `research_window.read_research_window` | shards por sesión + ventana + exclusiones declaradas → tabla + reporte | Gate de toda la ventana antes de abrir un archivo; cobertura exacta o exclusión con motivo; opt-in |
| `contract_regime` / `continuous_contract` | sesiones/contratos → régimen/derivado | `build_continuous_series` exige `acknowledge_unaudited_legacy=True`; no interpretar tests sintéticos como dataset saneado |

## Ejemplo mínimo, sólo fixture inventado

```python
from edgelab.data.nt8_contract import Nt8TickContract, SIX_E
from edgelab.data.nt8_reader import audit

contract = Nt8TickContract(
    declared_tz="America/Argentina/Buenos_Aires", instrument=SIX_E
)
records, report = audit([
    "20250725 200000 0280000;1.1783;1.1783;1.17835;1",
], contract)
assert report.n == 1
```

Este ejemplo no adjunta datasets ni certifica precio/mercado. Para una fuente real: primero manifiesto, sesiones aprobadas, particiones y preflight. El parser no es el firewall del holdout.

## Gate y lectura nueva: contrato acotado

Consultar [matriz de consumidores](DATA_CONSUMER_MATRIX.md) antes de elegir una entrada.

```bash
python tools/check_research_data_gate.py --help
python tools/check_research_data_gate.py --bundle /ruta/aprobada/request.json
```

El bundle es `{ "schema_version": "research_gate_request_v1", "request": { ... } }`.
`request` contiene `certificate`, `regime_manifest`, `root`, `trade_date`, `liquidity_limits`,
`expected_certificate_sha256`, `expected_regime_sha256` y `expected_liquidity_limits_sha256`.
Los hashes y límites deben provenir del manifiesto aprobado externo: calcularlos de cualquier JSON actual **no equivale a aprobación**. `PASS_METADATA_ONLY` abre cero fuentes y no es un permiso.

Para el lector nuevo, pasar esos mismos argumentos a `read_research_session` más `path`.
La sesión destino del certificado necesita `complete_session=true`, `status=PASS` y
`shard={basename, size_bytes, rows, sha256}`. Retorna `(pyarrow.Table, evidence)`.
Sólo admite shards de **una sesión y contrato** con columnas canónicas `root` y
`contract` string, `trade_date` integer y estadísticas min/max/null completas para
cada grupo. Rechaza archivos mixtos, desconocidos o hashes distintos; no busca una
fuente alternativa, no filtra después de leer y no publica archivos.

Orden: evidencia/pins/D-1/liquidez → abrir descriptor → footer y stats de todas las
identidades → SHA del shard → deserializar → identidad real redundante. Los metadatos
Parquet también se leen: «antes de payload» significa antes de **deserializar filas**, no «cero bytes». Arrow puede hacer lecturas bufferizadas que incluyan bytes fuera del footer. Este lector no promete aislamiento de I/O por página ni un firewall de bytes reservado.
Requiere fuente inmutable y metadatos auditados veraces; no es un sandbox contra
footers falsificados, writers concurrentes o fuentes hostiles. D2/splits, aprobación
independiente y features aguas arriba siguen gobernados externamente. El API no conoce
el split D2: sus fechas deben estar excluidas de `allowed_trade_dates` por la campaña.
No usar un resultado técnico para emitir certificados o ampliar el holdout.

`contract_regime` ahora rechaza volúmenes infinitos/NaN/booleanos; volumen seleccionado
cero deja la siguiente sesión ineligible (`NO_POSITIVE_SELECTED_VOLUME`). No se inventa
un umbral absoluto ni se rellena ausencia con cero.

## Dependencias y límites

Core: NumPy/Pandas/Pydantic. Proyecciones/Parquet: extra bridge/funnel. Config externa ausente es `None`: detenerse con la fuente requerida, no buscar archivos alternativos. No renombrar MNQ a NQ ni deduplicar callbacks sólo por timestamp coincidente.

[Entorno/configuración](ENVIRONMENT.md) · [Mapa](COMPONENTS.md) · [Plan de wiring pendiente](INTEGRATION_PLAN.md).

Gate: stdlib + contract_regime; no Arrow al importar. Lector de shards: extra PyArrow. Pruebas: [fixtures inventados](../tests/data/test_research_data_gate.py); no auditoría de filas reales.
