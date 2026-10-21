# Manifiesto ORB0100 — rango 01:00-01:15 NY, ruptura por cuerpo en 5 min (estrategia de Instagram), variantes de friccion/DD

Estado: PRE-REGISTRADO antes de correr. Pedido de Nico 2026-10-21: "Mandalo a edgelab, y probalo no solo asi, sino con otras
variantes, enfocadas en reducir fricciones, drawdown y maximizar el beneficio". Familia NUEVA (ORB0100), independiente de LUX-IMB.
Referente sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`. Indicador NT8: `nt8/user_indicators/ORB0100Filtros.cs`.

## Datos (HOLDOUT-A3)
NQ release v4 (precio de NQ = MNQ), velas M1 de los bundles de descubrimiento (09-25, 12-25, 03-26, 06-26 hasta 31-mar),
agregadas a 5 min. **IS** = 2025-08-05 .. 2025-12-31; **OOS** = 2026-01-01 .. 2026-03-31; **externo** = ES mismo periodo.
Replicacion NQ abr-sep: intacta, reservada para UNA corrida de la variante elegida (con OK). Holdout: no se toca.
Nota: NQ ya se miro para LUX-IMB, pero ORB0100 es otra familia y nunca uso estos datos.

## Regla base (= indicador)
Rango = velas de 5 min que cierran en (01:00, 01:15] ET. Primera vela de 5 min posterior cuyo cierre queda fuera -> entrada
al cierre; SL otro lado del rango; TP 0,5 R; una operacion por dia; cierre forzado 16:00 ET. Resolucion intravela con M1
(misma vela M1 toca SL y TP -> SL).

## Grilla (48 celdas, todas publicadas)
- TP: 0,5 / 0,75 / 1,0 / 1,5 R.
- SL: otro lado del rango (base) / mitad del rango.
- Entrada: al cierre de la ruptura (mercado, slippage) / **limite en el borde del rango** tras la ruptura (sin slippage de
  entrada; solo si el precio vuelve al borde antes de las 16:00 ET; si no, no hay operacion).
- Filtro: ninguno / EMA 50 (5 min) a favor / VWAP de sesion a favor.
## Costos (dos modelos, ambos reportados)
MNQ: $1,24 RT + 1 tick ($0,50) por lado a mercado -> en puntos: com 0,62 pts. NQ: $4,50 RT + 1 tick -> 0,225 pts. (Reducir
friccion = ademas comparar MNQ vs NQ: misma regla, distinto costo por punto.)

## Seleccion y lectura (fijadas ahora)
- Metricas por celda: n, acierto, neto pts/op y USD/op (MNQ), factor de beneficio, max drawdown (USD, 1 contrato, orden temporal),
  IC 95 % por dia de la media.
- Eleccion SOLO en IS: maximo neto/op con n >= 40 y factor de beneficio >= 1,1; se reportan las 3 mejores.
- Sobrevive si: OOS media > 0 **y** ES media > 0 (con costo NQ/ES). Se publica correlacion IS-OOS entre celdas (si ~0, el
  ranking es ruido, ver `no-confundir-ranking-con-edge`: tambien se reporta el agregado de TODAS las celdas por periodo).
- Una sobreviviente pasa a pedir OK para la replicacion NQ abr-sep (una vez).
## Justificacion economica
El overnight (01:00 NY = apertura de Europa) concentra flujo nuevo; si la ruptura del primer rango europeo tiene continuacion
de corto plazo, un TP chico se cumple mas veces de lo que el SL se pierde.
## Como podria refutarse
Ninguna celda con OOS > 0 y ES > 0; o neto <= 0 tras costos en todas.
