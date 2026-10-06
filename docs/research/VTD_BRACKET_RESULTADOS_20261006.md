# VTD-BRACKET — resultados (descubrimiento MNQ + ES) — 2026-10-06

Manifiesto: `VTD_BRACKET_MANIFIESTO_20261006.md` (OK de Nico). Kernels `edgelab-brk-{mnq,es,ym,rty,mgc}` +
`edgelab-vtd-bracket-20261006`. JSON: `vtd_bracket_20261006/VTD_BRACKET_RESULTADOS.json`. 8 pruebas.

## Descubrimiento: **ninguna celda pasa** (p_maxT = 1,0 en las 8)
| inst | k | R | trades | USD/trade marcas (IC95) | USD/trade pool | marcas − pool | win |
|---|---|---|---|---|---|---|---|
| MNQ | 0,5 | 2 | 4.020 | −3,09 [−3,42; −2,76] | −2,92 | −0,17 | 30 % |
| MNQ | 0,5 | 3 | 4.020 | −3,19 | −3,01 | −0,18 | 22 % |
| MNQ | 1,0 | 2 | 3.987 | −3,11 | −2,94 | −0,17 | 30 % |
| MNQ | 1,0 | 3 | 3.987 | −3,12 | −3,01 | −0,11 | 22 % |
| ES | 0,5 | 2 | 2.705 | −38,3 [−40,0; −36,6] | −34,4 | **−3,9** (z −3,8) | 11 % |
| ES | 0,5 | 3 | 2.705 | −39,5 | −35,5 | −3,9 | 8 % |
| ES | 1,0 | 2 | 2.701 | −37,6 | −34,4 | −3,2 | 12 % |
| ES | 1,0 | 3 | 2.701 | −38,7 | −35,6 | −3,1 | 8 % |

- **Pierde en todas las celdas, y las marcas VTD rinden IGUAL o PEOR que barras al azar** (en ES, significativamente
  peor).
- Neto total en descubrimiento: MNQ ≈ −12,4 k USD por celda; ES ≈ −100 k USD por celda (1 contrato).
- No depende de un mes ni de 5 días: es pérdida sistemática.
- Confirmación (YM/RTY/MGC): **no se corre**, porque nada pasó, según el manifiesto.

## Por qué pierde (diagnóstico)
- El resultado por trade en ticks, **incluyendo** 1 tick de slippage por lado, es de unos −2,4 (MNQ) y −2,7 (ES). Antes
  de la fricción, el bracket es ≈ 0 a levemente negativo: un bracket bilateral paga la ruptura falsa, porque entra en la
  dirección del primer movimiento y sale en el stop cuando revierte.
- Con un SL de 1 ATR de barras de 150t (pocos ticks en ES), 2 ticks de slippage más la comisión son una fracción enorme
  del riesgo. ES: win 8–12 %, es decir, los stops chicos se disparan casi siempre.
- **Las marcas no ayudan:** el "movimiento más grande" que anticipa VTD (VTD-VOL-1) no se convierte en un bracket ganador.
  El movimiento extra viene con más ida y vuelta, que el bracket paga en stops.

## Estado
`VTD-BRACKET DESCARTADO (descubrimiento)`. VolTicksDef queda como **sello informativo de amplitud**, sin estrategia
bilateral rentable con estos parámetros.
