# Exploración EdgeReplica MNQ + celda MGC 04:15 desde la publicación — 2026-10-06

Exploración por decisión de Nico, sin custodia de holdout. Las sesiones desde el 1-oct quedan vistas para estas dos
familias. Ticks NT8 de MNQ 12-26 y MGC 12-26 desde el 11-sep (MGC desde el 13) hasta el 6-oct.
Script: `tools/explo_edgereplica_mgc_20261006.py` (espejo de `EdgeReplica.cs` y `EdgeGold0415.cs`).
Costos: 1 tick de slippage por lado + USD 1,90 por ida y vuelta. IC95 por bootstrap de sesiones.

**Control de paridad con NT8:** la sesión del 5-oct da **+USD 145,70**, igual al Strategy Analyzer de NT8
(con comisión y slippage 1, captura de Nico).

## EdgeReplica MNQ (1 contrato)
| tramo | ops | ses | USD | USD/op | IC95 USD/op | % ganadoras |
|---|---|---|---|---|---|---|
| 11-sep → 30-sep | 128 | 14 | −1.830 | −14,3 | [−33,6; +7,6] | 39,8 |
| 1-oct → 6-oct | 35 | 4 | +798 | +22,8 | [+2,1; +48,1] | 57,1 |
| total | 163 | 18 | −1.032 | −6,3 | [−25,1; +12,7] | 43,6 |

- 14-sep (−818) y 24-sep (−1.103) explican más que toda la pérdida.
- Octubre es positivo, pero son 4 sesiones y +622 vienen de un solo día (1-oct).
- Largos −4,8 USD/op, cortos −8,5 USD/op.
- Antes de la publicación (diagnóstico previo, 1-jul → 10-sep): +3,77 pts/op ≈ +5,6 USD/op.

## MGC 04:15 — corto tras subida, 15 min (1 contrato)
| tramo | ops | USD | USD/op | IC95 |
|---|---|---|---|---|
| 13-sep → 30-sep | 9 | +209 | +23,2 | [+0,1; +49,3] |
| 1-oct → 6-oct | 3 | −17 | −5,6 | — |
| total | 12 | +192 | +16,0 | [−2,1; +37,4] |

Descriptivo, corto sin condición: 16 ops, +22,5 USD/op [+1,4; +48,4].
Igual que en la etapa B: **el corto sin condición rinde lo mismo o más que con la condición**, así que el filtro de los
15 minutos previos no está aportando. Sea lo que sea, es un efecto de hora, no de la condición.

## Lectura
- **EdgeReplica:** desde la publicación es negativa en total, con un IC ancho que no permite separar entre "decayó" y
  "mala racha". El buen arranque de octubre no cambia ese diagnóstico.
- **MGC 04:15:** 12 operaciones positivas, pero n es mínimo. Es consistente con la etapa B, aunque está lejos de
  confirmarse.
- Ninguna de las dos se promueve.
