# ZAMR-1 — Z1 local engineering pilot (2026-08-13)

## Dictamen

```text
Z1_ENGINEERING_LOCAL = PASS_PROVISIONAL
Z1_FORMAL_BUILDER = NOT_EXECUTED
BYTE_DETERMINISM = NOT_ADJUDICATED
ORACLE_PARITY = NOT_ESTABLISHED
Z2 = NOT_AUTHORIZED
```

Este documento registra evidencia de ingeniería target-free obtenida en una VM local sobre los dos Parquet congelados. No convierte la corrida en Z1 formal: la VM no tenía `pyarrow`, `fastparquet`, DuckDB ni red para instalar dependencias. Se usó un lector Parquet mínimo offline y un runner de equivalencia reconstruido desde la semántica del builder v2.

## Inputs

| Archivo | SHA-256 | Resultado |
|---|---|---|
| `6E_06-26_ticks.parquet` | `fd2e358d2b9b5ffa7a48057b6b90e94211c56db252ca884b161b9606e7fab83d` | MATCH |
| `6E_09-26_ticks.parquet` | `654e006e483f62727dd2d52680e41b0c4c03531a3763471a1ba3532497883a06` | MATCH |

Plan: 22 sesiones, 2026-06-01 a 2026-06-30. Roll: 06-26 hasta 2026-06-11 inclusive; 09-26 desde 2026-06-12. Frames: `5, 10, 25, 50, 100, 200`.

## Resultado

- 22/22 sesiones observadas.
- 12/12 unidades contrato × frame ejecutadas.
- 48.314 eventos.
- 8.718 zonas.
- 0 claves de evento duplicadas.
- 0 claves de zona duplicadas.
- 0 discrepancias de contabilidad footprint/barra.
- clasificación por quote: 100%.
- 0 columnas prohibidas.
- timestamp máximo exportado: `1782851668968000000`, menor que el corte exclusivo `1782856800000000000`.
- `outcomes_accessed=false`.
- `pnl_accessed=false`.
- `holdout_included=false`.

### Zonas

| Contrato | tick:5 | tick:10 | tick:25 | tick:50 | tick:100 | tick:200 |
|---|---:|---:|---:|---:|---:|---:|
| 06-26 | 61 | 269 | 1.037 | 971 | 740 | 540 |
| 09-26 | 67 | 317 | 1.380 | 1.371 | 1.102 | 863 |

### Eventos

| Contrato | tick:5 | tick:10 | tick:25 | tick:50 | tick:100 | tick:200 |
|---|---:|---:|---:|---:|---:|---:|
| 06-26 | 644 | 2.164 | 6.368 | 5.096 | 3.510 | 2.365 |
| 09-26 | 722 | 2.608 | 8.088 | 7.335 | 5.388 | 4.026 |

## Recursos

- carga Parquet: ~10,8 s;
- cómputo de 12 unidades: ~125,7 s;
- pico RSS: 601.768 KiB (~588 MiB);
- exports CSV temporales: ~23,7 MB.

El benchmark sugiere holgura de ingeniería amplia, pero el gate formal de margen ≥2× se adjudica sólo con el builder exacto, el bundle Parquet y la política de sharding prevista.

## Huellas del primer run

```text
faa6dbe152b94f18640a1103a4ded470c93eeaed991dff42382d48be737d1263  events_long.csv
3641d39144841a7c87751080da48416edc681726a85016799a37a35af34b6049  zones_long.csv
0c8e42911b435bb90718c1d783d12b28a83a2785e5e775793ebec20ae132ed03  engineering_report.json
```

Los CSV temporales no se versionan: no son los Parquet formales y el sandbox se reinició. Las huellas se preservan para trazabilidad, no como artefactos reproducibles canónicos.

Una segunda ejecución reprodujo exactamente conteos de las dos primeras unidades (`06-26/tick:5` y `06-26/tick:10`) antes del reinicio del sandbox. Esto es evidencia parcial, no adjudicación byte a byte.

## Gates

| Gate | Estado |
|---|---|
| Input hashes | PASS |
| Session count | PASS |
| Roll | PASS_PROVISIONAL |
| Holdout firewall | PASS |
| Target-free | PASS |
| P1A footprint | PASS_12_OF_12 |
| P-01 agregado | PASS |
| Recursos | PASS_PROVISIONAL |
| Determinismo byte a byte | NOT_ADJUDICATED |
| Bundle Parquet autocontenido | NOT_PRODUCED |
| Paridad NT8 | NOT_ESTABLISHED |

## Licencia

`NO_UPLOAD` continúa vigente. Los ticks no se suben a Kaggle ni a otro tercero. El gate agregado en `8a586f5` bloquea Notebook 01 antes de descubrir o leer Parquet cuando la decisión no es `RAW_ALLOWED`.

## Próximo cierre obligatorio

1. endurecer el builder para validar contrato observado contra plan;
2. registrar hash del plan;
3. separar identidad determinística de métricas variables de runtime;
4. producir bundle autocontenido, incluido `hashes.sha256`;
5. ejecutar dos veces el builder exacto y comparar hashes de datos;
6. mantener Z2 bloqueado y paridad `NOT_ESTABLISHED`.
