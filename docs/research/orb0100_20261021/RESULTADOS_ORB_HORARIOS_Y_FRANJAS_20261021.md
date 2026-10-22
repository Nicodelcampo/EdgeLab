# Resultados — ORB-HORARIOS (704 celdas) y ORB0100 NQ + franjas OG/VI

Estado: VIGENTE

## ORB-HORARIOS (manifiesto `MANIFIESTO_ORB_HORARIOS_20261021.md`; `tools/orb0100/orb_horarios.py`; `RESULTADOS_ORB_HORARIOS.json`)
Veredicto: **NINGUNA CELDA PASA EL CRIBADO** (umbral BH 10 % = 0; 0 cribadas, 0 confirmadas).
- 704 celdas (44 ventanas x 2 reglas x 8 activos): 129 con R > 0, 62 positivas en 2025 y 2026, **8 con p < 0,05 cuando se
  esperarian ~35 por azar** -> el conjunto es compatible con ausencia de efecto (o algo peor: la media general es negativa).
- Media de R por activo: NQ -0,01, GC -0,02, MBT -0,07, ES -0,08, MYM -0,10, 6E -0,20, 6J -0,21, 6B -0,30.
- Mejores ventanas (promedio de 16 celdas): 10:00 y 09:30 ET (~0), 10:30 -0,03; peores 15:30, 18:30, 11:30, 06:00 (~-0,2).
- Descriptivo (no promovido): **GC en la noche (22:30-02:30 ET)** aparece varias veces arriba (01:00 R0 +0,14 R, p 0,006;
  23:00 R1 +0,28; 02:30 R1 +0,28; 22:30 R1 +0,24), con ventanas vecinas positivas, pero no pasa la correccion por 704 pruebas.

## ORB0100 NQ + franjas OG/VI (manifiesto `MANIFIESTO_ORB0100_FRANJAS_OGVI_20261021.md`; `orb_franjas.py`)
Veredicto: **NINGUNA DISPOSICION SUMA NI RESTA DE FORMA DEMOSTRABLE**.
| hipotesis | descubrimiento (n 107): dif. R [IC] | abr-sep (n 92) | Holm | MDE80 |
|---|---|---|---|---|
| H1 zonas en el camino al TP (>=1 vs 0) | -0,04 [-0,51, +0,43] (51 vs 56) | -0,34 [-0,86, +0,18] | 1,0 | 0,66 R |
| H2 zonas de respaldo (entrada-SL) | degenerado: 104 de 107 tienen respaldo | 92 de 92 | 1,0 | — |
| H3 desbalance respaldo-camino (>0 vs <0) | +0,88 [-0,30, +1,38] (95 vs 7) | +0,43 (82 vs 8) | 0,31 | 1,19 R |
- Casi siempre hay zonas detras de la entrada (la ruptura sale de un rango lleno de desequilibrios): el respaldo no discrimina.
- "Camino libre" va algo mejor en los dos tramos (+0,21 vs +0,14 R; +0,29 vs -0,06 R), mismo signo, pero sin significancia y
  con MDE de 0,66 R: con ~200 operaciones solo se veria un efecto enorme. Pista anotada, no filtro.

Aporte al referente: 704 horarios x activos y la disposicion de zonas se midieron sin hallar un filtro ni una ventana que
sobreviva; la idea de ORB queda reducida a NQ 01:00 (pendiente de holdout) y una pista descriptiva en GC nocturno.
