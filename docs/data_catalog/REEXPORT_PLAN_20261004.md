# Plan de re-exportación con el AddOn EdgeLab Tick History (2026-10-04)

Responde a `REEXPORT.md`. Revisión de lo que hay en la PC antes de pedir nada a NT8.

## Causa raíz de las "sesiones faltantes"
Todas las sesiones sueltas faltantes caen en **jueves** (07-02, 07-09, 07-16, 07-30, 08-06, 08-13, 08-20, 08-27,
09-03, 09-10, 03-26, 04-02, 05-21). El AddOn pide un día local [d, d+1) y la sesión CME del jueves necesita los
archivos locales del miércoles y del jueves. En `manifest.jsonl` esos pares figuran como `NO_DATA` devuelto al
instante por la conexión (p. ej. `ES 09-26` 20260826/20260827, `MGC 12-26` 20260701/20260702). La base local de NT8
(`db\tick`) **hoy sí tiene esas horas** (22 archivos horarios por día). No es un problema de liquidez ni del
curado: es la exportación. Re-correr el AddOn las completa (los días `NO_DATA` no dejan archivo y se vuelven a pedir).

## Lo que ya está en la PC
- **MBT jun-2026:** `E:\EdgeLab\data\nt8\MBT_parquet\MBT_06-26..09-26_ticks.parquet` cubren hasta 2026-06-26 / 07-31 /
  08-28. Faltan sólo en el dataset, no en la PC.
- **ZB jul-sep 2026:** `E:\DatosNT8\tick_history_completar_20261001\ZB_09-26, ZB_12-26` (hasta 09-21 / 09-27) — sin
  canonizar ni subir. Faltan los mismos pares miércoles/jueves.
- **MGC 08-26 / 12-26:** `E:\DatosNT8\tick_history_MGC_20261002` — con los mismos huecos de jueves.
- **MNQ_12-26:** el parquet canónico local y el de `nt8-canonical` son el mismo (13.457.190 filas); el conflicto es
  contra `mnq-parquet`, que por prioridad queda como respaldo. Se re-exporta igual para la comparación a tres.
- **No están en la PC:** los `.Last.utc.txt` de MES, MNQ, YM, RTY y MYM ext (se armaron en otra máquina), y
  ningún dato de GC 10-25, GC 10-26, MGC 10-25, MGC 10-26 (tampoco en `db\tick`).

## Corrida (carpeta raíz única `E:\DatosNT8\tick_history_reexport_20261004`, una conexión activa)
| # | Contratos | Desde | Hasta |
|---|---|---|---|
| 1 | GC 08-25; GC 10-25; MGC 10-25; MYM 09-25; RTY 09-25; RTY 12-25; NQ 09-25 | 2025-06-29 | 2025-10-31 |
| 2 | GC 08-26; GC 10-26; GC 12-26; MGC 08-26; MGC 10-26; MGC 12-26; ZB 09-26; ZB 12-26; MBT 08-26; MBT 09-26; MBT 10-26 | 2026-06-28 | 2026-09-30 |
| 3 | ES 09-26; 6E 09-26; MES 09-26; MYM 09-26; YM 09-26; YM 12-26; MNQ 09-26; MNQ 12-26 | 2026-06-28 | 2026-09-30 |
| 4 | MNQ 06-26; NQ 06-26; MBT 06-26; MBT 07-26 | 2026-03-10 | 2026-06-30 |

Los ticks después de la apertura de la sesión del 2026-10-01 (2026-09-30 17:00 CT) se cortan al canonizar, como en
`build_es_ext_2026q3.py`. Candado del AddOn corregido al holdout vigente (`HoldoutStart` 2027-01-01 → 2026-10-01;
copia en `nt8/addons/EdgeLabTickHistory.cs`).

## Después
Canonizar (mismo esquema `canonical_tick_v1`), comparar contra las dos fuentes en los contratos en conflicto, volver a
correr `tools/data_curate.py` y subir **versión nueva** de `edgelab-ticks-nt8-canonical` (sin borrar versiones).
Dukascopy: el dataset unificado ya subido trae 2022-07 → 2026-09 en un archivo; sólo falta re-correr el inventario
(2022 se completa con las corridas HDA/HDB/HDC en curso).
