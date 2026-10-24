# Resultados M4 — penetracion de vuelta dentro del impulso (LUX-IMB, NQ, descubrimiento)

Estado: MEDIDO. Veredicto: **SIN EFECTO A FAVOR DEL REBALANCEO** en ninguna altura (Holm = 1,0 en las 10).
Preregistro `PREREGISTRO_M4_PENETRACION_LUXIMB_NQ_20261020.md` (commit `35e547c1`, antes de mirar). Codigo
`tools/luximb_parity/luximb_m4_penetracion.py`. Eventos: `RESULTADOS_M4_PENETRACION_NQ_eventos.csv`.

| penetracion | n T / C | P(llega a A antes que a X) T | C | T - C (IC 95 %, por dia) | MDE80 | P&L neto T (IC 95 %) | P&L C |
|---|---|---|---|---|---|---|---|
| 25 % | 310 / 1.880 | 0,206 | 0,247 | -4,1 pp [-9,2, +1,2] | 7,4 pp | -4,24 [-7,9, -0,6] | -0,21 |
| 38,2 % | 293 / 1.753 | 0,324 | 0,366 | -4,1 pp [-9,9, +1,5] | 8,2 pp | -5,08 [-9,6, -0,9] | -0,68 |
| 50 % | 271 / 1.644 | 0,417 | 0,479 | -6,2 pp [-12,8, +0,2] | 9,1 pp | -6,22 [-11,0, -1,6] | -0,85 |
| 61,8 % | 251 / 1.525 | 0,546 | 0,592 | -4,6 pp [-10,9, +1,7] | 9,0 pp | -5,69 [-10,2, -0,9] | -1,45 |
| 75 % | 236 / 1.419 | 0,682 | 0,732 | -5,0 pp [-11,6, +1,3] | 9,2 pp | -3,81 [-7,9, +0,6] | -0,67 |

Lectura:
1. En ninguna altura los impulsos con zonas rebalancean mas que el control; los IC excluyen efectos a favor de >= +2 pp.
2. El signo es **opuesto** y consistente (-4 a -6 pp en las 5 alturas): una vez dentro del impulso, el precio vuelve al
   extremo X algo MAS seguido en T. No es significativo, las alturas se solapan (no son 5 evidencias) y la prueba
   preregistrada era unilateral a favor del rebalanceo. Si se quiere estudiar "continuacion tras penetracion", requiere
   preregistro propio; no se promueve desde aca.
3. El fade a A desde cualquier altura pierde dinero neto en T (IC por debajo de 0 en 4 de 5 alturas). En C, ~0 a -1,5 pts.

Alcance: muere el rebalanceo hasta A tras penetrar 25-75 % del impulso v5 en NQ (descubrimiento), con entrada limite en
la altura y stop en X. No muere: otras salidas (objetivo intermedio), vida 200, otros instrumentos.

Aporte al referente: cierra la variante "esperar a que el precio se meta en el impulso" de la hipotesis de rebalanceo;
no hay altura de entrada que la rescate en NQ.
