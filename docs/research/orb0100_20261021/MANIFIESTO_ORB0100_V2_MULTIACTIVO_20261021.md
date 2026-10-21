# Manifiesto ORB0100 V2 — variantes alrededor de "1,5R / rango / mercado / VWAP", en 8 activos (descubrimiento)

Estado: PRE-REGISTRADO antes de correr. Pedido de Nico 2026-10-21: "crea nuevas variantes, apoyandote sobre la que funciona
y probalo en otros activos tambien". Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`.

## Por que la prueba es multiactivo
NQ (IS y OOS) ya se uso para elegir la celda de partida: cualquier variante nueva medida en NQ esta contaminada. La evidencia
nueva viene de **activos que la familia nunca miro**: ES (solo se vio la celda base, como externo), MYM, GC, 6E, 6B, 6J, MBT.
NQ se reporta, pero no cuenta. Solo descubrimiento (hasta 2026-03-31). Replicaciones abr-sep y holdout intactos.

## Grilla V2 (24 celdas + la de partida)
- TP: 1,5 / 2,0 / 2,5 R. SL: otro lado del rango. Entrada: a mercado al cierre de la ruptura (+1 tick).
- Rango: 01:00-01:15 ET (base) / 01:00-01:30 ET (mas ancho).
- Filtro: VWAP de sesion a favor / VWAP + EMA 50 (5 min) a favor.
- Cierre forzado: 16:00 ET / 11:00 ET (menos exposicion).
Celda de partida = TP 1,5 / 01:00-01:15 / VWAP / 16:00.

## Costos por activo (no se transportan)
1 tick de slippage por lado a mercado (TP limite sin slippage). Comision RT: $4,50 (ES, GC, 6E, 6B, 6J) y $1,24 (MYM, MBT,
y MNQ para NQ), convertida a puntos con el multiplicador de `edgelab/instruments.py`. Ticks de `release_manifest.json`.

## Medida e inferencia
- Resultado por operacion en **R** (P&L neto / riesgo), comparable entre activos; tambien USD por contrato.
- Por celda: media en R por activo; **combinado de los 7 activos nuevos** (inverso de la varianza, bootstrap por dia), Holm
  sobre las 25 celdas, y cuantos activos con media > 0.
- Una celda "transporta" si: combinado > 0 con Holm < 0,05 **y** >= 5 de 7 activos positivos.
- Diagnostico: correlacion entre activos del ranking de celdas; efecto de periodo (mitad 2025 vs 2026) por activo.
## Justificacion economica
Si el primer rango de la apertura europea (01:00 NY) marca direccion para el resto del dia, la ruptura a favor del VWAP
deberia continuar lo suficiente para pagar un TP grande en mercados distintos.
## Como podria refutarse
Ninguna celda transporta; o positivos solo en indices de EE.UU. (seria propio de ese mercado, no general).
