# aVolClusterPOI — Gate P2 (2026-08-13)

Estado: `CSV_ORACLE_OK` / `P2_REPLAY_BLOCKED` (sandbox sin pyarrow).
Formal: runner listo; falta OHLC M1 del mismo chart.

Archivo: `avolcluster_v05_20260813.csv` (504 filas). Meta v0.5 OK.

## Oracle

133 OFF_PRICE (74 SHORT / 59 LONG). 112 AT_PRICE. 130 FIRST_TOUCH. 129 CloseThrough.
Cero eventos prohibidos. Cero dobles en la misma barra.

Densidad OFF / 48 sesiones con nivel: **2.771**.
OFF / 56 sesiones del export: **2.375**.

## Forma extra (CSV)

- Lag a primer toque: min 1, p50 **4**, p90 73, max 7331. 41/130 en la misma o siguiente barra.
- Sin FIRST_TOUCH: zone_id 6, 82, 198.
- Sin invalidar: 82, 193, 194, 198.
- Abril 28 / mayo 35 / junio 70 OFF_PRICE. El roll de 09-26 sigue inflando junio.

## Formal

`diag/tasa_senales/avolcluster_formal.py`
Solo OFF_PRICE. Primer pasaje vs espejo del mismo ancho, misma distancia al close.
Ceros adentro no cuentan. Toque doble en la misma barra = empate/censor.
No P&L. No AT_PRICE.

Para correrlo acá: exportar del **mismo** chart NT8 6E 09-26 1m (2026-04-10 → 2026-06-30) un CSV con Time, High, Low, Close.
