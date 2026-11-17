# SOM en la apertura de otros mercados (pre-registro, 2026-11-17)

Estado: PRE-REGISTRO — commiteado antes de correr. Origen: recomendación del 2026-11-16 («el mecanismo de SOM en la apertura propia de otros
mercados», punto 3) y pedido de Nico «seguí con lo que te corresponda». North Star sha256 `16a108dfce2671b7a7c502d7db3eccdb71aabdca1cd1bd6bb7ea0f847d66e345`.
Etapa EF3. Corrida: `tools/som_transfer.py`.

## Regla (congelada: SOM `sin_finde`, la del holdout de NQ, sin tocar nada salvo la hora y el instrumento)
A los 5 min de la apertura propia del mercado, cierre de la vela M5 vs EMA12 → compra/venta; stop 8 × ATR14 M5; trailing a la EMA120 M5 desde
+0,5 R; una posición a la vez; cierra el viernes 15:55 NY. Motor `quantlab_mt5.correr_session_open_momentum` (llenado con gap corregido).

| Prueba | Datos (M1 Dukascopy, zona declarada) | Apertura propia (NY) | Costo canónico |
|---|---|---|---|
| RTY | USSC2000IDXUSD (UTC), 2019-03 → 2026-09 | 09:30 (cash de EE. UU.) | RTY 0,4436 pts |
| GC | XAUUSD_M1_dukas (servidor), 2012 → 2026-09 | 08:20 (pit del COMEX) | GC 0,605 |
| 6E | EURUSD_M1_dukas (servidor), 2012 → 2026-09 | 03:00 (Londres) | 6E 0,0002 |
DAX, FTSE, Nikkei, petróleo y bonos quedan fuera: no tienen costo medido en `edgelab/costos.py`.

## Decisión
A = 2012-01 → 2019-12, B = 2020-01 → 2026-09-29 (RTY: A = 2019-03 → 2019-12, casi vacío: decide B). Pasa si R neto > 0 en A (si A tiene ≥ 30
operaciones) y en B, p de B (bootstrap por sesión) sobrevive BH q 0,10 sobre 3 y fricción mediana ≤ 0,08 R. Se informan años positivos,
ventana reciente (ago-25 → sep-26) y correlación diaria con SOM NQ. Lo que pase va a holdout/forward con su propia acta.

## Justificación económica / cómo podría refutarse
La apertura propia de cada mercado concentra el flujo de órdenes del día (el mecanismo que SOM captura en NQ); oro, euro y Russell responden a
otros flujos que el Nasdaq, así que diversifican. Se refuta con R ≤ 0 en B o sin nominadas por BH con MDE ≤ 0,10 R.

## Contador y linaje
`som_transfer_20261117/SOM_TRANSFER`: 3. Linaje SOM_TRANSFER ← SOM.
