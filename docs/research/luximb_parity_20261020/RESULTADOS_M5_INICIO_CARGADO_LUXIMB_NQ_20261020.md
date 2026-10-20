# Resultados M5 — vuelta al inicio cargado (LUX-IMB, NQ, descubrimiento)

Estado: MEDIDO. Veredicto: **SIN EFECTO DETECTADO** (Holm: H2 0,91; resto 1,0). Preregistro
`PREREGISTRO_M5_INICIO_CARGADO_LUXIMB_NQ_20261020.md` (commit `51639b6b`, antes de mirar). Codigo `luximb_m5.py`,
eventos `RESULTADOS_M5_NQ_eventos.csv`, impulsos `desc_m5/`.

| grupo | n | dias | P(vuelve al borde del 25 % inicial antes de +25 %) | P(+25 %) | P&L fade neto 0/1/2 ticks | P&L continuacion 1 tick |
|---|---|---|---|---|---|---|
| T inicio cargado | 233 | 115 | 0,356 | 0,635 | +3,78 / +3,37 / +2,96 | -4,58 |
| C misma amplitud | 2.315 | 164 | 0,334 | 0,649 | +0,65 / +0,24 / -0,18 | -1,44 |

| hipotesis | estimacion | IC 95 % (por dia) | Holm |
|---|---|---|---|
| H1 P(Tg) T - C | +2,2 pp | [-3,9, +8,3] | 1,0 |
| H2 P&L fade T (1 tick) | +3,37 pts | [-3,1, +9,5] | 0,91 |
| H3 P&L continuacion T | -4,57 pts | [-10,8, +1,7] | 1,0 |
| H4 sube / baja | +2,4 / +2,0 pp | ambos cruzan 0 | 1,0 |
| H5 cash / resto | +4,0 / +1,4 pp | ambos cruzan 0 | 1,0 |
| H6 resto vacio / no vacio | +6,2 / +1,2 pp | [-6,9, +19,5] / [-5,9, +8,6] | 1,0 |

MDE80 de H1 = 8,6 pp. Por contrato (P&L fade T): 09-25 -3,8 (n 20), 12-25 -0,3 (99), 03-26 +6,1 (100), 06-26 +20,3 (14):
el signo positivo viene de 03-26 y de 14 eventos de 06-26; no es estable entre contratos.
Canal no direccional (60 min, R): MFE fade p50 0,68 T vs 0,72 C; MAE 0,65 vs 0,69. Sin diferencia.

Lectura: el signo va a favor de la hipotesis (a diferencia de M1-M4), pero es chico, inestable por contrato y con N de
233 en 115 dias no se distingue de 0. Un efecto de +8,6 pp o mas queda descartado; uno de 2-5 pp no se puede ver con
este N. Mas datos de descubrimiento no hay (el resto de 2026 es replicacion comprometida u holdout).

Alcance: muere a nivel de deteccion esta definicion (inicio cargado, piso 60, salida al borde del 25 % / +25 %) en NQ
descubrimiento. No muere: otros instrumentos (ES, YM: mas eventos), otras salidas, otras vidas.

Aporte al referente: primera variante de la familia con el signo a favor, pero sin evidencia; evita promoverla y deja
como unico camino para potencia sumar instrumentos en descubrimiento.
