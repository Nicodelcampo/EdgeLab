# Datos aprobados para análisis (generado)

Reglas fijas en `tools/data_curate.py` (iguales para todos). **Usar solo lo que figura acá como aprobado.** Fuente: `curated.json`.

## Resumen

| Instrumento | Veredicto | Sesiones elegibles | Aprobadas | Última sesión aprobada | Rangos aprobados (primero..último, sesiones) |
|---|---|---:|---:|---|---|
| 6B | **APROBADO** | 285 | 285 (100%) | 2026-09-25 | 2025-08-04..2025-12-23 (99); 2025-12-29..2026-09-25 (186) |
| 6E | **CON_SALVEDADES** | 288 | 288 (100%) | 2026-09-25 | 2025-07-28..2025-11-26 (87); 2025-12-01..2025-12-23 (16); 2025-12-29..2026-09-25 (185) |
| 6J | **APROBADO** | 267 | 267 (100%) | 2026-09-25 | 2025-08-04..2025-09-11 (29); 2025-09-16..2025-11-07 (39); 2025-12-12..2026-09-25 (199) |
| ES | **CON_SALVEDADES** | 247 | 242 (98%) | 2026-09-25 | 2025-07-18..2025-10-03 (54); 2025-12-15..2026-08-19 (168); 2026-08-24..2026-09-25 (20) |
| GC | **CON_SALVEDADES** | 225 | 225 (100%) | 2026-06-30 | 2025-08-04..2025-11-26 (81); 2025-12-01..2026-06-30 (144) |
| MBT | **CON_SALVEDADES** | 109 | 83 (76%) | 2026-05-29 | 2025-08-22..2025-09-05 (11); 2025-09-26..2025-09-26 (1); 2025-10-02..2025-10-24 (17); 2025-11-24..2025-11-24 (1); 2025-12-01..2025-12-19 (15); 2026-03-31..2026-03-31 (1) … |
| MES | **APROBADO** | 274 | 274 (100%) | 2026-09-25 | 2025-08-04..2025-11-26 (81); 2025-12-01..2025-12-23 (17); 2025-12-29..2026-09-25 (176) |
| MGC | **CON_SALVEDADES** | 213 | 213 (100%) | 2026-09-30 | 2025-10-07..2025-11-26 (36); 2025-12-01..2026-01-09 (28); 2026-01-28..2026-03-31 (43); 2026-04-06..2026-06-30 (55); 2026-07-06..2026-07-15 (6); 2026-07-20..2026-09-09 (32) … |
| MNQ | **CON_SALVEDADES** | 270 | 268 (100%) | 2026-09-30 | 2025-08-04..2025-09-12 (29); 2025-09-17..2025-11-26 (51); 2025-12-01..2025-12-22 (15); 2025-12-29..2026-03-31 (59); 2026-04-06..2026-08-12 (83); 2026-08-17..2026-09-30 (31) |
| MYM | **CON_SALVEDADES** | 184 | 130 (71%) | 2026-09-25 | 2025-09-30..2025-10-03 (4); 2025-12-15..2026-01-09 (18); 2026-03-16..2026-08-19 (87); 2026-08-24..2026-09-25 (21) |
| NQ | **CON_SALVEDADES** | 278 | 278 (100%) | 2026-09-25 | 2025-08-04..2025-09-12 (29); 2025-09-17..2025-11-26 (51); 2025-12-01..2025-12-23 (16); 2025-12-29..2026-09-25 (182) |
| RTY | **CON_SALVEDADES** | 182 | 143 (79%) | 2026-09-25 | 2025-10-03..2025-10-03 (1); 2025-12-15..2025-12-26 (9); 2026-03-16..2026-09-25 (133) |
| YM | **APROBADO** | 260 | 260 (100%) | 2026-09-25 | 2025-08-15..2025-11-26 (72); 2025-12-01..2025-12-22 (15); 2026-01-02..2026-08-19 (156); 2026-08-24..2026-09-04 (8); 2026-09-10..2026-09-25 (9) |
| ZB | **APROBADO** | 211 | 210 (100%) | 2026-06-30 | 2025-08-18..2025-08-22 (5); 2025-08-27..2025-11-26 (63); 2025-12-01..2026-06-30 (142) |

## Fuente primaria por contrato (la que aporta más sesiones aprobadas)


### 6B

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| 6B_09-25 | `edgelab-nt8-historical-missing-20261001` | `6B_09-25_ticks_nt8.parquet` | 29 | 2025-08-04..2025-09-11 | - |
| 6B_12-25 | `edgelab-nt8-historical-missing-20261001` | `6B_12-25_ticks_nt8.parquet` | 63 | 2025-09-15..2025-12-11 | - |
| 6B_03-26 | `edgelab-nt8-historical-missing-20261001` | `6B_03-26_ticks_nt8.parquet` | 59 | 2025-12-15..2026-03-12 | - |
| 6B_06-26 | `edgelab-nt8-historical-missing-20261001` | `6B_06-26_ticks_nt8.parquet` | 62 | 2026-03-16..2026-06-11 | - |
| 6B_09-26 | `edgelab-nt8-historical-missing-20261001` | `6B_09-26_ticks_nt8.parquet` | 62 | 2026-06-15..2026-09-10 | - |
| 6B_12-26 | `edgelab-nt8-historical-missing-20261001` | `6B_12-26_ticks_nt8.parquet` | 10 | 2026-09-14..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### 6E

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| 6E_09-25 | `edgelab-nt8-historical-missing-20261001` | `6E_09-25_ticks_nt8.parquet` | 34 | 2025-07-28..2025-09-11 | `edgelab-ticks-6e-preholdout:6E_09-25_ticks.parquet` |
| 6E_12-25 | `edgelab-nt8-historical-missing-20261001` | `6E_12-25_ticks_nt8.parquet` | 62 | 2025-09-15..2025-12-11 | - |
| 6E_03-26 | `edgelab-nt8-historical-missing-20261001` | `6E_03-26_ticks_nt8.parquet` | 59 | 2025-12-15..2026-03-12 | - |
| 6E_06-26 | `edgelab-nt8-historical-missing-20261001` | `6E_06-26_ticks_nt8.parquet` | 62 | 2026-03-16..2026-06-11 | - |
| 6E_09-26 | `edgelab-nt8-historical-missing-20261001` | `6E_09-26_ticks_nt8.parquet` | 61 | 2026-06-15..2026-09-10 | - |
| 6E_12-26 | `edgelab-nt8-historical-missing-20261001` | `6E_12-26_ticks_nt8.parquet` | 10 | 2026-09-14..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 61.

### 6J

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| 6J_09-25 | `edgelab-nt8-historical-missing-20261001` | `6J_09-25_ticks_nt8.parquet` | 29 | 2025-08-04..2025-09-11 | - |
| 6J_12-25 | `edgelab-nt8-historical-missing-20261001` | `6J_12-25_ticks_nt8.parquet` | 39 | 2025-09-16..2025-11-07 | - |
| 6J_03-26 | `edgelab-nt8-historical-missing-20261001` | `6J_03-26_ticks_nt8.parquet` | 63 | 2025-12-12..2026-03-12 | - |
| 6J_06-26 | `edgelab-nt8-historical-missing-20261001` | `6J_06-26_ticks_nt8.parquet` | 62 | 2026-03-16..2026-06-11 | - |
| 6J_09-26 | `edgelab-nt8-historical-missing-20261001` | `6J_09-26_ticks_nt8.parquet` | 64 | 2026-06-15..2026-09-10 | - |
| 6J_12-26 | `edgelab-nt8-historical-missing-20261001` | `6J_12-26_ticks_nt8.parquet` | 10 | 2026-09-14..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### ES

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| ES_09-25 | `edgelab-nt8-historical-missing-20261001` | `ES_09-25_ticks_ext.parquet` | 40 | 2025-07-18..2025-09-12 | - |
| ES_12-25 | `edgelab-nt8-historical-missing-20261001` | `ES_12-25_ticks_ext.parquet` | 14 | 2025-09-16..2025-10-03 | - |
| ES_03-26 | `edgelab-nt8-historical-missing-20261001` | `ES_03-26_ticks_ext.parquet` | 62 | 2025-12-15..2026-03-16 | - |
| ES_06-26 | `edgelab-nt8-historical-missing-20261001` | `ES_06-26_ticks_ext.parquet` | 62 | 2026-03-17..2026-06-12 | - |
| ES_09-26 | `edgelab-ticks-es-nq-2026q3-ext` | `ES_parquet/ES_09-26_ticks_ext.parquet` | 57 | 2026-06-16..2026-09-14 | `edgelab-nt8-historical-missing-20261001:ES_09-26_ticks_ext.parquet` |
| ES_12-26 | `edgelab-ticks-es-nq-2026q3-ext` | `ES_parquet/ES_12-26_ticks_ext.parquet` | 7 | 2026-09-15..2026-09-25 | - |

Excluidas: liquidez_baja: 5. Sesiones con salvedad por fuentes en conflicto: 57.

### GC

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| GC_12-25 | `edgelab-ticks-gc-preholdout` | `GC_12-25_ticks.parquet` | 80 | 2025-08-04..2025-11-24 | - |
| GC_02-26 | `edgelab-ticks-gc-preholdout` | `GC_02-26_ticks.parquet` | 41 | 2025-11-26..2026-01-27 | - |
| GC_04-26 | `edgelab-ticks-gc-preholdout` | `GC_04-26_ticks.parquet` | 40 | 2026-01-29..2026-03-26 | - |
| GC_06-26 | `edgelab-ticks-gc-preholdout` | `GC_06-26_ticks.parquet` | 40 | 2026-03-30..2026-05-26 | - |
| GC_08-26 | `edgelab-ticks-gc-preholdout` | `GC_08-26_ticks.parquet` | 24 | 2026-05-28..2026-06-30 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### MBT

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| MBT_09-25 | `edgelab-ticks-mbt-preholdout` | `MBT_09-25_ticks.parquet` | 11 | 2025-08-22..2025-09-05 | - |
| MBT_11-25 | `edgelab-ticks-mbt-preholdout` | `MBT_11-25_ticks.parquet` | 18 | 2025-09-26..2025-10-24 | - |
| MBT_01-26 | `edgelab-ticks-mbt-preholdout` | `MBT_01-26_ticks.parquet` | 16 | 2025-11-24..2025-12-19 | - |
| MBT_05-26 | `edgelab-ticks-mbt-preholdout` | `MBT_05-26_ticks.parquet` | 38 | 2026-03-31..2026-05-29 | - |

Excluidas: sesion_truncada: 4, liquidez_baja: 22. Sesiones con salvedad por fuentes en conflicto: 0.

### MES

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| MES_09-25 | `edgelab-ticks-nt8-canonical` | `MES/MES_09-25_ticks_ext.parquet` | 29 | 2025-08-04..2025-09-12 | - |
| MES_12-25 | `edgelab-ticks-nt8-canonical` | `MES/MES_12-25_ticks_ext.parquet` | 63 | 2025-09-16..2025-12-15 | - |
| MES_03-26 | `edgelab-ticks-nt8-canonical` | `MES/MES_03-26_ticks_ext.parquet` | 58 | 2025-12-16..2026-03-16 | - |
| MES_06-26 | `edgelab-ticks-nt8-canonical` | `MES/MES_06-26_ticks_ext.parquet` | 62 | 2026-03-17..2026-06-12 | - |
| MES_09-26 | `edgelab-ticks-nt8-canonical` | `MES/MES_09-26_ticks_ext.parquet` | 55 | 2026-06-16..2026-09-11 | - |
| MES_12-26 | `edgelab-ticks-nt8-canonical` | `MES/MES_12-26_ticks_ext.parquet` | 7 | 2026-09-15..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### MGC

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| MGC_12-25 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_12-25.parquet` | 35 | 2025-10-07..2025-11-24 | - |
| MGC_02-26 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_02-26.parquet` | 29 | 2025-11-26..2026-01-09 | - |
| MGC_04-26 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_04-26.parquet` | 41 | 2026-01-28..2026-03-26 | - |
| MGC_06-26 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_06-26.parquet` | 38 | 2026-03-30..2026-05-26 | - |
| MGC_08-26 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_08-26.parquet` | 30 | 2026-05-28..2026-07-28 | - |
| MGC_12-26 | `edgelab-mgc-nt8-raw-parquet-20261002` | `MGC_12-26.parquet` | 40 | 2026-07-31..2026-09-30 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### MNQ

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| MNQ_09-25 | `edgelab-ticks-nt8-canonical` | `MNQ/MNQ_09-25_ticks_ext.parquet` | 29 | 2025-08-04..2025-09-12 | - |
| MNQ_12-25 | `edgelab-ticks-nt8-canonical` | `MNQ/MNQ_12-25_ticks_ext.parquet` | 62 | 2025-09-17..2025-12-15 | - |
| MNQ_03-26 | `edgelab-ticks-nt8-canonical` | `MNQ/MNQ_03-26_ticks_ext.parquet` | 57 | 2025-12-17..2026-03-16 | - |
| MNQ_06-26 | `edgelab-ticks-nt8-canonical` | `MNQ/MNQ_06-26_ticks_ext.parquet` | 53 | 2026-03-20..2026-06-12 | - |
| MNQ_09-26 | `edgelab-ticks-nt8-canonical` | `MNQ/MNQ_09-26_ticks_ext.parquet` | 56 | 2026-06-16..2026-09-14 | `mnq-parquet:MNQ 09-26.Lasttt.parquet` |
| MNQ_12-26 | `mnq-parquet` | `MNQ 12-26.Lasttick.parquet` | 11 | 2026-09-16..2026-09-30 | `edgelab-ticks-nt8-canonical:MNQ/MNQ_12-26_ticks_ext.parquet` |

Excluidas: holdout: 2. Sesiones con salvedad por fuentes en conflicto: 67.

### MYM

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| MYM_12-25 | `edgelab-ticks-nt8-canonical` | `MYM/MYM_12-25_ticks_ext.parquet` | 4 | 2025-09-30..2025-10-03 | - |
| MYM_03-26 | `edgelab-ticks-nt8-canonical` | `MYM/MYM_03-26_ticks_ext.parquet` | 18 | 2025-12-15..2026-01-09 | - |
| MYM_06-26 | `edgelab-ticks-nt8-canonical` | `MYM/MYM_06-26_ticks_ext.parquet` | 52 | 2026-03-16..2026-06-15 | - |
| MYM_09-26 | `edgelab-ticks-nt8-canonical` | `MYM/MYM_09-26_ticks_ext.parquet` | 47 | 2026-06-16..2026-09-11 | - |
| MYM_12-26 | `edgelab-ticks-nt8-canonical` | `MYM/MYM_12-26_ticks_ext.parquet` | 9 | 2026-09-15..2026-09-25 | - |

Excluidas: liquidez_baja: 53, sesion_truncada: 1. Sesiones con salvedad por fuentes en conflicto: 0.

### NQ

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| NQ_09-25 | `edgelab-ticks-nq-preholdout` | `NQ_09-25_ticks.parquet` | 29 | 2025-08-04..2025-09-12 | `edgelab-nt8-historical-missing-20261001:NQ_09-25_ticks_ext.parquet` |
| NQ_12-25 | `edgelab-nt8-historical-missing-20261001` | `NQ_12-25_ticks_ext.parquet` | 61 | 2025-09-17..2025-12-12 | `edgelab-ticks-nq-preholdout:NQ_12-25_ticks.parquet` |
| NQ_03-26 | `edgelab-nt8-historical-missing-20261001` | `NQ_03-26_ticks_ext.parquet` | 58 | 2025-12-16..2026-03-13 | - |
| NQ_06-26 | `edgelab-nt8-historical-missing-20261001` | `NQ_06-26_ticks_ext.parquet` | 62 | 2026-03-17..2026-06-12 | `edgelab-ticks-nq-preholdout:NQ_06-26_ticks.parquet` |
| NQ_09-26 | `edgelab-ticks-es-nq-2026q3-ext` | `NQ_parquet/NQ_09-26_ticks_ext.parquet` | 62 | 2026-06-16..2026-09-14 | `edgelab-nt8-historical-missing-20261001:NQ_09-26_ticks_ext.parquet`<br>`edgelab-ticks-nq-preholdout:NQ_09-26_ticks.parquet` |
| NQ_12-26 | `edgelab-ticks-es-nq-2026q3-ext` | `NQ_parquet/NQ_12-26_ticks_ext.parquet` | 6 | 2026-09-18..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 91.

### RTY

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| RTY_12-25 | `edgelab-ticks-nt8-canonical` | `RTY/RTY_12-25_ticks_ext.parquet` | 1 | 2025-10-03..2025-10-03 | - |
| RTY_03-26 | `edgelab-ticks-nt8-canonical` | `RTY/RTY_03-26_ticks_ext.parquet` | 9 | 2025-12-15..2025-12-26 | - |
| RTY_06-26 | `edgelab-ticks-nt8-canonical` | `RTY/RTY_06-26_ticks_ext.parquet` | 63 | 2026-03-16..2026-06-12 | - |
| RTY_09-26 | `edgelab-ticks-nt8-canonical` | `RTY/RTY_09-26_ticks_ext.parquet` | 61 | 2026-06-16..2026-09-11 | - |
| RTY_12-26 | `edgelab-ticks-nt8-canonical` | `RTY/RTY_12-26_ticks_ext.parquet` | 9 | 2026-09-15..2026-09-25 | - |

Excluidas: liquidez_baja: 39. Sesiones con salvedad por fuentes en conflicto: 0.

### YM

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| YM_09-25 | `edgelab-ticks-nt8-canonical` | `YM/YM_09-25_ticks_ext.parquet` | 20 | 2025-08-15..2025-09-12 | - |
| YM_12-25 | `edgelab-ticks-nt8-canonical` | `YM/YM_12-25_ticks_ext.parquet` | 62 | 2025-09-16..2025-12-12 | - |
| YM_03-26 | `edgelab-ticks-nt8-canonical` | `YM/YM_03-26_ticks_ext.parquet` | 54 | 2025-12-16..2026-03-13 | - |
| YM_06-26 | `edgelab-ticks-nt8-canonical` | `YM/YM_06-26_ticks_ext.parquet` | 62 | 2026-03-17..2026-06-12 | - |
| YM_09-26 | `edgelab-ticks-nt8-canonical` | `YM/YM_09-26_ticks_ext.parquet` | 55 | 2026-06-15..2026-09-11 | - |
| YM_12-26 | `edgelab-ticks-nt8-canonical` | `YM/YM_12-26_ticks_ext.parquet` | 7 | 2026-09-15..2026-09-25 | - |

Excluidas: ninguna. Sesiones con salvedad por fuentes en conflicto: 0.

### ZB

| Contrato | Dataset | Archivo | Sesiones aprobadas | Rango | Otras fuentes |
|---|---|---|---:|---|---|
| ZB_09-25 | `edgelab-nt8-historical-missing-20261001` | `ZB_09-25_ticks_nt8.parquet` | 5 | 2025-08-18..2025-08-22 | - |
| ZB_12-25 | `edgelab-nt8-historical-missing-20261001` | `ZB_12-25_ticks_nt8.parquet` | 61 | 2025-08-27..2025-11-21 | - |
| ZB_03-26 | `edgelab-ticks-zb-preholdout` | `ZB_03-26_ticks.parquet` | 59 | 2025-11-25..2026-02-24 | - |
| ZB_06-26 | `edgelab-ticks-zb-preholdout` | `ZB_06-26_ticks.parquet` | 62 | 2026-02-26..2026-05-26 | - |
| ZB_09-26 | `edgelab-ticks-zb-preholdout` | `ZB_09-26_ticks.parquet` | 23 | 2026-05-28..2026-06-30 | - |

Excluidas: sesion_truncada: 1. Sesiones con salvedad por fuentes en conflicto: 0.

## Rol de cada dataset de Kaggle

| Dataset | Rol | Sesiones aprobadas que aporta | Instrumentos | Privado | MB | Nota |
|---|---|---:|---|---|---:|---|
| `edgelab-ticks-nt8-canonical` | PRIMARIO (aporta sesiones aprobadas) | 1045 | MES, MNQ, MYM, RTY, YM | sí | 5,264 |  |
| `edgelab-code-20260928` | CÓDIGO del proyecto | 0 | - | sí | 1 |  |
| `edgelab-ticks-zb-preholdout` | PRIMARIO (aporta sesiones aprobadas) | 144 | ZB | sí | 111 |  |
| `edgelab-mgc-nt8-raw-parquet-20261002` | PRIMARIO (aporta sesiones aprobadas) | 213 | MGC | sí | 605 |  |
| `edgelab-ticks-nq-preholdout` | PRIMARIO (aporta sesiones aprobadas) | 38 | NQ | sí | 1,097 |  |
| `edgelab-ticks-es-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 1,331 |  |
| `edgelab-ticks-ym-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 220 |  |
| `edgelab-l2-gc-bookmap-audit-20260921` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 37 |  |
| `edgelab-ticks-6j-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 102 |  |
| `edgelab-nq-nt8-2026q3-l2ctx` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 323 |  |
| `edgelab-ticks-gc-preholdout` | PRIMARIO (aporta sesiones aprobadas) | 225 | GC | sí | 378 |  |
| `edgelab-avolcluster-nq-oracle` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 11 |  |
| `edgelab-nq-informal-all5-coordinates` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 8 |  |
| `edgelab-tickbar-diag-nq0626` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 0 |  |
| `edgelab-bt2-v2-nq-artifacts` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 8 |  |
| `edgelab-bt2a-nq-event-store` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 8 |  |
| `edgelab-nq-selection-checkpoints` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 72 |  |
| `edgelab-ticks-mnq-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 2,577 |  |
| `edgelab-ticks-mbt-preholdout` | PRIMARIO (aporta sesiones aprobadas) | 83 | MBT | sí | 52 |  |
| `edgelab-edge-factory-audit-evidence-20260919` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 0 |  |
| `edgelab-edge-factory-target-free-audited` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | sí | 95 |  |
| `edgelab-ticks-mes-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 1,187 |  |
| `edgelab-ticks-6e-preholdout` | PRIMARIO (aporta sesiones aprobadas) | 5 | 6E | sí | 139 |  |
| `edgelab-ticks-6b-preholdout` | REDUNDANTE o sin sesiones aprobadas (no usar como fuente; conservar como respaldo) | 0 | - | sí | 64 |  |
| `edgelab-ticks-es-nq-2026q3-ext` | PRIMARIO (aporta sesiones aprobadas) | 112 | ES, NQ | sí | 647 |  |
| `edgelab-nt8-historical-missing-20261001` | PRIMARIO (aporta sesiones aprobadas) | 1271 | 6B, 6E, 6J, ES, NQ, ZB | sí | 1,226 |  |
| `mnq-tick-data` | ARTEFACTOS / EVIDENCIA (no son datos de mercado) | 0 | - | **NO** | 15 | PÚBLICO: pasarlo a privado |
| `mnq-parquet` | PRIMARIO (aporta sesiones aprobadas) | 30 | MNQ | **NO** | 500 | PÚBLICO: pasarlo a privado |
| `edgelab-discovery-cache` | DERIVADO (caché / inventario) | 0 | - | sí | 58 |  |
| `edgelab-dukascopy-xauusd-ticks-m1` | SPOT (no es futuro): ver la sección de Dukascopy | 0 | - | sí | 2,611 |  |
| `edgelab-data-catalog` | DERIVADO (caché / inventario) | 0 | - | sí | 1 |  |
