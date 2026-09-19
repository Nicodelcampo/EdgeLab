# EdgeLab — alcance real y custodia Kaggle de bundles 25t

**Fecha:** 2026-09-19  
**Estado:** `AUTHORITATIVE_SCOPE_CLARIFICATION`  
**Holdout canónico:** `1782856800000000000` (`2026-06-30T22:00:00Z`)  
**Subida de bundles:** `PAUSED_NOT_UPLOADED`

## Advertencia principal

Los **147 bundles 25t canónicos no constituyen activos continuos completos**, no contienen todos los contratos históricos de cada instrumento y no garantizan cobertura temporal sin huecos.

Son **cortes explícitos por instrumento, contrato y mes** producidos a partir de los contratos disponibles y procesados. Deben interpretarse como una colección parcial de `contract-month slices`, nunca como una serie continua completa.

Los archivos locales con nombres como `ES_CONT.json`, `NQ_CONT.json` o `<ASSET>_CONT.json` pertenecen al inventario del visor/legado. Su presencia **no certifica** que exista un histórico 25t continuo, completo, roll-adjusted o compuesto por todos los contratos. Tampoco deben utilizarse para inferir cobertura canónica del dataset remoto.

## Alcance certificado

- 11 instrumentos representados: `GC`, `ZB`, `ES`, `MES`, `6E`, `6J`, `MNQ`, `NQ`, `YM`, `MBT`, `6B`.
- 147 bundles canónicos.
- 40,380,402 velas 25t.
- 3,328,710 zonas HFT.
- Granularidad efectiva: instrumento × contrato × mes, aunque algunos artefactos históricos tengan nombres menos explícitos.
- La ausencia de un archivo o mes **no significa** ausencia de mercado, ticks, zonas o eventos; significa que ese período no forma parte de la cobertura publicada.
- No se certifica continuidad entre contratos ni metodología de roll.
- No se certifica que todos los contratos disponibles localmente estén incluidos.

## Metadatos obligatorios del futuro dataset Kaggle

El README y el manifiesto raíz deben contener, como mínimo:

```yaml
coverage_mode: PARTIAL_CONTRACT_MONTH_SLICES
is_complete_continuous_series: false
includes_all_contracts: false
has_certified_roll_methodology: false
eligible_for_continuous_backtest: false
missing_periods_mean_no_data: false
holdout_boundary_ns: 1782856800000000000
holdout_boundary_utc: 2026-06-30T22:00:00Z
```

Cada entrada del manifiesto debe declarar:

```text
instrument
contract
calendar_month
min_timestamp_ns
max_timestamp_ns
candles_count
zones_count
source_json_sha256
compressed_sha256
decompressed_sha256
compression_codec
schema_version
coverage_status
```

`coverage_status` debe ser uno de:

```text
CERTIFIED_CONTRACT_MONTH_SLICE
PARTIAL_MONTH
LEGACY_UNCERTIFIED
BLOCKED_BY_CUSTODY
```

Los artefactos continuos o heredados no pueden recibir `CERTIFIED_CONTRACT_MONTH_SLICE` sin una auditoría independiente de composición, roll, duplicados, gaps y causalidad.

## Nombre recomendado en Kaggle

Para evitar que `bundles` se interprete como cobertura completa, se recomienda:

```text
nicolasbuttaro/edgelab-25t-hft-contract-month-slices-zstd-preholdout
```

Si se conserva el identificador propuesto originalmente, el título visible y la primera línea del README deben decir:

> PARTIAL CONTRACT-MONTH SLICES — NOT A COMPLETE CONTINUOUS SERIES

## Formato de custodia recomendado, pendiente de autorización operativa

La auditoría recomienda un archivo `.json.zst` ZSTD-19 por bundle y manifiestos separados:

- no subir los `.js`, porque los 147 pares auditados son regenerables desde JSON;
- conservar un archivo independiente por contrato/mes;
- verificar `sha256(decompress(bundle.json.zst)) == source_json_sha256`;
- publicar hashes de fuente, comprimido y descomprimido;
- conservar los archivos locales sin modificación;
- no iniciar la compresión/subida hasta autorización explícita de Nicolas.

Volumen proyectado respaldado por el JSON de auditoría: aproximadamente **353.7 MB / 0.35 GB** más manifiestos. La frase `1.1–1.2 GB` presente en una sección del informe Markdown original es internamente inconsistente con el JSON de auditoría y queda supersedida por `353.7 MB` hasta una nueva medición.

## Estado de MNQ

El dataset privado `nicolasbuttaro/edgelab-ticks-mnq-preholdout` fue reportado como verificado:

- 5 contratos;
- 334,506,728 ticks;
- aproximadamente 5.64 GB;
- SHA-256 post-descarga coincidente para los cinco archivos;
- cero timestamps en o después del holdout.

Esta verificación de ticks MNQ **no transforma** los bundles 25t en una serie continua ni amplía automáticamente su cobertura.

## Reglas para cualquier análisis

1. Seleccionar explícitamente los contratos y meses incluidos.
2. No unir meses o contratos como serie continua sin preregistrar y auditar el método de roll.
3. No interpretar meses ausentes como observaciones cero.
4. No comparar instrumentos sin controlar diferencias de cobertura.
5. No promover resultados a “multiactivo general” si la evidencia proviene de una cobertura parcial.
6. Mantener cerrado el holdout.
7. Registrar el manifiesto exacto y sus hashes en cada experimento.

## Evidencia fuente

- Commit de auditoría: `79592c1ebfb675edb2c9aea332c0f843eed6ad8c`.
- `artifacts/migration/BUNDLE_COMPRESSION_AUDIT.json`.
- `docs/research/BUNDLE_COMPRESSION_AUDIT.md`.

Este documento define la semántica de cobertura que debe prevalecer ante cualquier descripción ambigua de los bundles 25t.
