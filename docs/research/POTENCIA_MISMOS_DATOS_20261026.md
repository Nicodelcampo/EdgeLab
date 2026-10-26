# Más potencia con los mismos datos — métodos y orden

Estado: VIGENTE
Fecha: 2026-10-26. Pedido de Nico: «con los mismos datos que tenemos, agregarle potencia a los experimentos que les falte».

| # | método | qué gana | cuándo vale | estado |
|---|---|---|---|---|
| 1 | **OOS hacia atrás**: la regla congelada sobre los años de Dukascopy que la familia no usó | n ×3–5 | familias con DESC corto (U1-ORO-GRILLA, U1-ZONAS) y señal en CFD | **U1-ORO-ATRAS: n 197 (vs 41 del DESC), −0,04 USD/oz, IC90 [−0,60; +0,47] → EN CONTRA** con potencia |
| 2 | **P&L normalizado por volatilidad** (en ATR del día o en R) como estadístico | baja la varianza (los días de mucha volatilidad dominan el desvío) | reglas con objetivo/stop en puntos fijos y días muy distintos (GAP-RTH: MDE 82–93 pts) | propuesto; es un cambio del estadístico → pre-registro por campaña |
| 3 | **Juntar instrumentos** (meta-análisis por inverso de la varianza) con la misma regla congelada | n × instrumentos | familias que nominan en varios (U1 en ES, YM, NQ, oro) | propuesto para el holdout de U1 |
| 4 | **Variable de control** (placebo emparejado, CUPED) | resta la parte del P&L que explica el mercado del momento | cuando el placebo correlaciona con la regla | propuesto |
| 5 | Elegir candidatas frecuentes (`min_ops_oos`) | evita OOS sin operaciones | todas | **hecho** 2026-10-25 |

Ninguno relaja un gate: 1 y 3 agregan datos no usados; 2 y 4 son estadísticos más eficientes con el mismo nivel de error, y se
declaran en el pre-registro antes de mirar.
