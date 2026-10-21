# ORB0100 — registro MEDIDO / NO MEDIDO
## MEDIDO
- 2026-10-21 Grilla 48 celdas NQ IS/OOS + ES: regla original sin edge (IS -1,35, ES -0,44 pts/op); sobrevive al limite 1,5R/rango/mercado/VWAP (IS +5,5, OOS +15,4, ES +0,24). `RESULTADOS_ORB0100_20261021.md`.
- 2026-10-21 V2: 24 variantes x 8 activos: ninguna transporta (combinado 7 activos -0,13 a -0,23 R, todas con IC < 0); solo NQ y GC positivos en la celda de partida. `RESULTADOS_ORB0100_V2_MULTIACTIVO_20261021.md`.
- 2026-10-21 REPLICACION NQ abr-sep (1,5R/rango/mercado/VWAP): +6,85 pts/op [IC -6,7, +20,7], 5/6 meses > 0 -> NO_CONCLUYENTE. `REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md`.
- 2026-10-21 ORB-HORARIOS 704 celdas: 0 pasan BH (8 con p<0,05 vs ~35 por azar); pista descriptiva GC nocturno. NQ+franjas OG/VI: ninguna disposicion significativa (camino libre algo mejor en ambos tramos, MDE 0,66 R). `RESULTADOS_ORB_HORARIOS_Y_FRANJAS_20261021.md`.
## NO MEDIDO
- GC nocturno 22:30-02:30 (pista; requeriria preregistro propio y datos no mirados).
- Holdout NQ (>= 2026-10-01) de la celda congelada.
- Otros rangos horarios, salidas parciales, sizing por volatilidad; holdout.
- Paridad del indicador NT8 contra el simulador Python (NT8 usa 5 min para resolver; Python usa M1).
