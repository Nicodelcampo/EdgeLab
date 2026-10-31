# PRERANGE-ZONAS

Estado: PRE-REGISTRO (2026-10-31). Sin P&L. Módulo: `edgelab/research/prerange_zonas.py`. Campañas inactivas.

Rango 08:12-09:12 NY y barrido 09:12-16:00, los disparos de PRERANGE-HFT. Perillas: conjunto (indicador o par), gatillo, distancia máxima en ATR
por posición (2 niveles, q50 y q90 E0) y cantidad mínima encima, debajo y dentro (cualquiera, q50, q90 de los conteos positivos).
En un par la cantidad es min(nA, nB). Zonas: creadas antes de la vela del disparo, vida 500 velas, `t_fin_ns` respetado.
AVZP2 entra en `t_decidida_ns`. YM usa AVZG definición 17 como aVolZone y no tiene aVolCluster. HFTNQ sólo NQ.
BASE chica: 4 ejecuciones (dirección × objetivo, entrada CIERRE, stop S_SWEEP), 2.592 celdas por conjunto, hasta 11 conjuntos.
Poda sin P&L: conjuntos con >= 20 combinaciones únicas, los 11 mejores por únicas. Cortes en `prerange_zonas_cortes.py`, de `E0_PRERANGE_ZONAS.json`.
Refutación: la de las campañas. Con unos 240 disparos por gatillo, muchas celdas quedan bajo 30.
