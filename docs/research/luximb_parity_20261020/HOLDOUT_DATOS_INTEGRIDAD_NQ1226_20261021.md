# Datos del holdout NQ 12-26 (2026-10-01 .. 2026-10-20) — chequeo de integridad (sin mirar precios ni desenlaces)

Fuente: EdgeLab Tick History `EDGE_TICKHIST_V3_HOLDOUT_SELLADO` (NT 8.1.8.4), conexion "Simulation (Provider31)", zona de NT8
Argentina Standard Time, salida en UTC. Carpeta sellada `E:\DatosNT8\tick_history_HOLDOUT_SELLADO\NQ_12-26\` (+ `SELLADO.txt`).
Descarga 2026-10-21 03:47 UTC. Archivos por dia calendario de NT8 (03:00 UTC a 02:59 UTC), no por sesion CME.

## Resultado (target-free)
- 15 dias OK, 6.857.659 ticks: **sha256 15/15 coincide con el manifiesto**, lineas = ticks del manifiesto, 0 lineas
  malformadas, 0 desordenadas.
- **Hueco: sin datos desde 2026-10-06 23:54:43 UTC hasta 2026-10-09 03:00:00 UTC** (~51 h: sesiones CME completas del
  7 y del 8 de octubre y el final de la del 6). El servidor devolvio NO_DATA para 20261007 y 20261008; el 20261006
  termina 3 h antes de lo normal.
- Resto del calendario normal: viernes cierran 20:59 UTC; domingos abren 22:00 UTC.

## Que implica
- El hueco no es look-ahead ni seleccion por resultado (falta en el servidor), pero reduce la muestra (~2 de 15 sesiones)
  y corta la continuidad de umbrales causales. Antes de la apertura: **reintentar 7-8 oct** (otra conexion o Replay
  Downloader) y, si no aparece, documentarlo como faltante en el registro de apertura.
- Pendiente: conversor de `.Last.utc.txt` al formato de entrada del script congelado (ts_utc_ns, price_ticks, volume,
  contract, trade_date de sesion CME), sin tocar la regla. Nadie mira desenlaces hasta la apertura.
