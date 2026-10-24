# Resultados M9 — distancia/tiempo de la vuelta + zonas tomadas/restantes (LUX-IMB, NQ -> ES)

Estado: MEDIDO. Veredicto: **NO REPLICA**. Un contraste sobrevive Holm en NQ y **no se confirma en ES**.
Manifiesto `MANIFIESTO_M9_DISTANCIA_TIEMPO_ZONAS_TOMADAS_20261020.md` (OK + codigo `ec98a2bb`, antes de correr). Fixes sin
cambio de reglas: concatenacion de estratos, celdas vacias, celda degenerada (1 vs 1) que daba p = 0 por NaN -> p = 1.
Eventos `RESULTADOS_M9_eventos.csv` (toques: NQ 2.730, ES 3.713), salida `RESULTADOS_M9.json`.

## Hallazgo estructural (no inferencial)
Casi todas las vueltas tocan d **en <= 15 min** (antes de superar X): NQ d=0,25 rapido 1.781 / lento 3; d=0,50 931 / 15;
ES 2.399 / 0 y 1.292 / 22. Las celdas "lentas" quedaron vacias: si la vuelta no ocurre rapido, el precio casi siempre
supera X primero. El eje tiempo de la grilla no discrimina en esta poblacion.

## NQ (desarrollo), P(llegar a A antes que a X)
| celda | n | P(A) | H_k (k alto - bajo) | H_m (otro lado vacio - cargado) | Holm H_m |
|---|---|---|---|---|---|
| d 25 %, rapido | 1.781 | 0,244 | +1,2 pp [-4,4, +6,8] | **+6,6 pp [+1,9, +11,5]** (715 vs 618) | **0,045** |
| d 50 %, rapido | 931 | 0,464 | +2,3 pp [-5,1, +9,6] | +6,8 pp [0,0, +13,9] | 0,36 |
| celdas lentas | 3 / 15 | — | sin estimacion | sin estimacion | 1,0 |
Lo que tomo la vuelta (k) no importa en ninguna celda. Lo que hay del otro lado (m) muestra signo consistente en NQ
(otro lado vacio -> mas llegada a A), con P&L de la entrada en d: +0,84 pts (vacio) vs -1,45 (cargado) en d 25 %.

## Confirmacion unica en ES (cortes y signo de NQ congelados)
d 25 %, rapido, H_m: **-0,7 pp [-5,1, +4,5]** (1.310 vs 445), P&L -0,08 vs -0,20 -> **no confirma**.

## Alcance
Muere: "otro lado vacio -> vuelve al origen" (H_m) como efecto transportable NQ->ES; "zonas tomadas" (H_k) en NQ.
El +6,6 pp de NQ queda registrado como resultado de desarrollo no replicado (no se promueve, no se re-prueba en NQ).
Replicaciones abr-sep y holdout intactos.

Aporte al referente: la unica senal de la familia que paso Holm en desarrollo fallo en el instrumento externo, y se
corta antes de gastar replicacion u holdout.
