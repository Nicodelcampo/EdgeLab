# Indicator Coordinate Store v1 — protocolo target-free

- **Fecha:** 2026-08-27
- **Estado:** código y tests sintéticos; falta piloto local con Parquet F2 real.
- **Holdout sellado:** 2026-07-01 → 2026-12-31.

## Objetivo

Ejecutar una sola vez cada combinación autorizada de dataset, kernel, barras y
configuración; conservar el Event Store auditable y una proyección Parquet
mínima de coordenadas para joins multiindicador.

## Regla de selección

La configuración canónica es la configuración sobre la que existe evidencia de
paridad. No significa «ganadora». Variantes adicionales requieren un protocolo
congelado basado en estabilidad, cobertura, densidad, redundancia y coste. Está
prohibido usar P&L, retorno, MFE/MAE, TP/SL, holdout o performance de
combinaciones para seleccionar configuraciones del store canónico.

## Artefactos

- `specs/indicator_parity_catalog_v1.json`
- `specs/indicator_config_catalog_v1.json`
- `specs/indicator_coordinate_store_v1.json`
- `tools/build_indicator_coordinate_store.py`
- `edgelab/bridge/coordinate_store.py`
- `tests/bridge/test_indicator_coordinate_store.py`

## Point-in-time

`coordinates.parquet` contiene únicamente identidad, disponibilidad, secuencia
y geometría conocidas al crear la zona. No incluye estado final, toques,
terminación ni outcomes. Los empates de timestamp se resuelven mediante
`available_event_seq` y, cuando existe, `created_source_row`.

`events.parquet` sigue siendo la fuente de verdad. La proyección de coordenadas
no sustituye el lifecycle ni puede usarse para inferirlo.

## Campaña local

Ejemplo de `campaign.json`:

```json
{
  "schema_version": "indicator_coordinate_campaign_v1",
  "target_free": true,
  "holdout_start": "2026-07-01",
  "datasets": [
    {
      "path": "E:/EdgeLab/data/nt8_research_v2/GC/GC_06-26_ticks.parquet",
      "source_sha256": "REEMPLAZAR_POR_SHA256_REAL",
      "instrument": "GC",
      "contract": "GC 06-26",
      "start_utc": "2026-01-01T00:00:00Z",
      "end_utc": "2026-07-01T00:00:00Z",
      "chart_tz": "America/Argentina/Buenos_Aires"
    }
  ]
}
```

Preflight sin leer Parquet:

```bash
python tools/build_indicator_coordinate_store.py \
  --campaign campaign.json \
  --out E:/EdgeLab/runs/indicator_coordinate_store_v1 \
  --validate-only
```

Ejecución:

```bash
python tools/build_indicator_coordinate_store.py \
  --campaign campaign.json \
  --out E:/EdgeLab/runs/indicator_coordinate_store_v1
```

La ejecución exige worktree sin cambios trackeados, verifica el SHA-256 si se
proporciona, falla ante cualquier timestamp del holdout y es idempotente por
`run_id`. Una reejecución divergente no sobrescribe la partición.

## Indicadores bloqueados

- `aVolCellPOI2`: paridad fallida.
- `aVolClusterPOI`: paridad parcial sin causa cerrada y fuera del registro común.
- `Gaps2` y `AACloseOpenDiffs`: quedan pendientes hasta promoción formal de su
  evidencia de paridad.

## Piloto pendiente

Antigravity debe ejecutar un contrato GC pre-holdout, repetirlo dos veces y
entregar:

1. `campaign_manifest.json`;
2. hashes de `coordinates.parquet`;
3. tiempos, RAM y tamaño;
4. conteos por indicador/configuración/sesión;
5. confirmación `HOLDOUT_TOUCHED=false`.

## Aporte al referente

El store separa por construcción coordenadas disponibles en tiempo real de
estado final y outcomes, evitando que el ahorro computacional introduzca
look-ahead o convierta una configuración paritaria en un ganador post-hoc.
