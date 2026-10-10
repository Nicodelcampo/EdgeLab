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
| `contract_regime` / `continuous_contract` | sesiones/contratos → régimen/derivado | Exige revisión de fuente y wiring; no interpretar tests sintéticos como dataset saneado |

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

## Dependencias y límites

Core: NumPy/Pandas/Pydantic. Proyecciones/Parquet: extra bridge/funnel. Config externa ausente es `None`: detenerse con la fuente requerida, no buscar archivos alternativos. No renombrar MNQ a NQ ni deduplicar callbacks sólo por timestamp coincidente.

[Entorno/configuración](ENVIRONMENT.md) · [Mapa](COMPONENTS.md) · [Plan de wiring pendiente](INTEGRATION_PLAN.md).
