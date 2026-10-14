# Exports que faltan (generado por `tools/missing_exports_report.py`)

P0 = excluye o bloquea sesiones de la release. P1 = mejora la garantía de procedencia (hoy sólo hay parquet derivado).
Cada fila es un rango de fechas de trading CME por contrato. Se exportan con el AddOn `EdgeLabTickHistory` (un archivo por día NT-local, UTC).

## P0 — 158 tramos, 309 sesiones

| activo | contrato | desde | hasta | sesiones | motivo |
|---|---|---|---|---:|---|
| 6B | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| 6B | (todos) | 20260928 | 20260930 | 3 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| 6B | 6B 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 03-26 | 20251204 | 20251204 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| 6B | 6B 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 06-26 | 20260305 | 20260305 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 09-26 | 20260521 | 20260521 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 09-26 | 20260528 | 20260528 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 09-26 | 20260604 | 20260604 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6B | 6B 12-26 | 20260928 | 20260928 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| 6E | (todos) | 20260928 | 20260930 | 3 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| 6E | 6E 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 03-26 | 20251204 | 20251204 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 06-26 | 20260305 | 20260305 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 12-26 | 20260806 | 20260806 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 12-26 | 20260812 | 20260813 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 12-26 | 20260827 | 20260827 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 12-26 | 20260903 | 20260903 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6E | 6E 12-26 | 20260928 | 20260928 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| 6J | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| 6J | (todos) | 20260928 | 20260930 | 3 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| 6J | 6J 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 03-26 | 20251204 | 20251204 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| 6J | 6J 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 06-26 | 20260226 | 20260226 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 06-26 | 20260305 | 20260305 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 09-26 | 20260521 | 20260521 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 09-26 | 20260528 | 20260528 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 09-26 | 20260604 | 20260604 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| 6J | 6J 12-26 | 20260928 | 20260928 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| ES | (todos) | 20260928 | 20260928 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| ES | ES 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ES | ES 09-26 | 20260821 | 20260821 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ES | ES 12-26 | 20260820 | 20260820 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ES | ES 12-26 | 20260917 | 20260917 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ES | ES 12-26 | 20260928 | 20260928 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| GC | (todos) | 20260916 | 20260916 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| GC | (todos) | 20260924 | 20260924 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| GC | GC 12-26 | 20260916 | 20260916 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| GC | GC 12-26 | 20260916 | 20260916 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| GC | GC 12-26 | 20260924 | 20260924 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| GC | GC 12-26 | 20260924 | 20260924 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 02-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 02-26 | 20260101 | 20260101 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 03-26 | 20260101 | 20260101 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 04-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 04-26 | 20260101 | 20260101 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 05-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 05-26 | 20260101 | 20260101 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MBT | MBT 12-25 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MBT | MBT 12-25 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MES | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| MES | MES 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MES | MES 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MES | MES 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MES | MES 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MES | MES 12-26 | 20260917 | 20260917 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | (todos) | 20250801 | 20251006 | 46 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| MGC | MGC 06-26 | 20260205 | 20260205 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260212 | 20260212 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260219 | 20260219 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260226 | 20260226 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260305 | 20260305 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260312 | 20260312 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260319 | 20260319 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260326 | 20260326 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 06-26 | 20260402 | 20260402 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MGC | MGC 06-26 | 20260402 | 20260402 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260402 | 20260402 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260416 | 20260416 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260423 | 20260423 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260430 | 20260430 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260507 | 20260507 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260514 | 20260514 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260521 | 20260521 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260609 | 20260609 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MGC | MGC 08-26 | 20260609 | 20260610 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260619 | 20260619 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MGC | MGC 08-26 | 20260619 | 20260619 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260624 | 20260624 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MGC | MGC 08-26 | 20260624 | 20260624 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MGC | MGC 08-26 | 20260716 | 20260716 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MGC | MGC 08-26 | 20260716 | 20260717 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| MNQ | MNQ 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MNQ | MNQ 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260318 | 20260318 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260611 | 20260611 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260618 | 20260618 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MNQ | MNQ 09-26 | 20260618 | 20260618 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260702 | 20260702 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MNQ | MNQ 09-26 | 20260702 | 20260703 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260716 | 20260716 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MNQ | MNQ 09-26 | 20260716 | 20260717 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MNQ | MNQ 09-26 | 20260814 | 20260814 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MNQ | MNQ 09-26 | 20260814 | 20260814 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | (todos) | 20250801 | 20250929 | 41 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| MYM | (todos) | 20260820 | 20260820 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| MYM | MYM 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 06-26 | 20260522 | 20260522 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MYM | MYM 06-26 | 20260522 | 20260522 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 06-26 | 20260605 | 20260605 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MYM | MYM 06-26 | 20260605 | 20260605 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 09-26 | 20260820 | 20260820 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| MYM | MYM 09-26 | 20260820 | 20260821 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260806 | 20260806 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260813 | 20260813 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260820 | 20260820 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260827 | 20260827 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260903 | 20260903 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| MYM | MYM 12-26 | 20260910 | 20260910 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| NQ | (todos) | 20260928 | 20260928 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| NQ | NQ 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| NQ | NQ 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| NQ | NQ 06-26 | 20260305 | 20260305 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| NQ | NQ 12-26 | 20260915 | 20260916 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| NQ | NQ 12-26 | 20260928 | 20260928 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| RTY | (todos) | 20250801 | 20251001 | 43 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| RTY | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| RTY | RTY 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| RTY | RTY 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| RTY | RTY 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | (todos) | 20250801 | 20250814 | 10 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| YM | (todos) | 20251225 | 20251225 | 1 | Los demás activos operaron y éste no tiene datos de ningún contrato: falta el export, no es un cero |
| YM | YM 03-26 | 20251127 | 20251127 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 03-26 | 20251225 | 20251225 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| YM | YM 03-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260115 | 20260115 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260122 | 20260122 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260128 | 20260129 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260205 | 20260205 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260212 | 20260212 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260219 | 20260219 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 06-26 | 20260226 | 20260226 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260402 | 20260402 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260409 | 20260409 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260416 | 20260416 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260423 | 20260423 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260430 | 20260430 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260820 | 20260820 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| YM | YM 09-26 | 20260820 | 20260821 | 2 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| YM | YM 09-26 | 20260908 | 20260908 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 03-26 | 20251117 | 20251117 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 06-26 | 20251225 | 20251225 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 06-26 | 20260219 | 20260219 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 09-26 | 20260521 | 20260521 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 09-26 | 20260814 | 20260814 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |
| ZB | ZB 09-26 | 20260826 | 20260826 | 1 | El contrato elegido por D-1 no tiene datos en la sesión (la sesión se excluyó; no se rescató con otro contrato) |
| ZB | ZB 09-26 | 20260826 | 20260826 | 1 | Competidor sin dato en D-1 con volumen reciente no despreciable: la decisión de la sesión siguiente quedó indeterminada |

## P1 — 16 tramos, 275 sesiones

| activo | contrato | desde | hasta | sesiones | motivo |
|---|---|---|---|---:|---|
| ES | ES 09-26 | 20260701 | 20260701 | 1 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MES | MES 12-26 | 20260915 | 20260916 | 2 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MES | MES 12-26 | 20260921 | 20260928 | 6 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MNQ | MNQ 09-26 | 20260616 | 20260617 | 2 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MNQ | MNQ 09-26 | 20260622 | 20260624 | 3 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MYM | MYM 06-26 | 20260320 | 20260515 | 18 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MYM | MYM 06-26 | 20260528 | 20260528 | 1 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MYM | MYM 06-26 | 20260611 | 20260615 | 2 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| MYM | MYM 12-26 | 20260915 | 20260928 | 10 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| NQ | NQ 09-26 | 20260701 | 20260701 | 1 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 03-26 | 20251216 | 20251224 | 7 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 03-26 | 20251229 | 20260316 | 55 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 06-26 | 20260317 | 20260615 | 64 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 09-26 | 20260616 | 20260914 | 63 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 12-25 | 20251103 | 20251215 | 30 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
| RTY | RTY 12-26 | 20260915 | 20260928 | 10 | Incluida desde parquet derivado: falta el export original de texto (.Last.utc.txt por día) para verificar procedencia |
