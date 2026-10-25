# ORB0100 — registro MEDIDO / NO MEDIDO
## MEDIDO
- 2026-10-21 Grilla 48 celdas NQ IS/OOS + ES: regla original sin edge (IS -1,35, ES -0,44 pts/op); sobrevive al limite 1,5R/rango/mercado/VWAP (IS +5,5, OOS +15,4, ES +0,24). `RESULTADOS_ORB0100_20261021.md`.
- 2026-10-21 V2: 24 variantes x 8 activos: ninguna transporta (combinado 7 activos -0,13 a -0,23 R, todas con IC < 0); solo NQ y GC positivos en la celda de partida. `RESULTADOS_ORB0100_V2_MULTIACTIVO_20261021.md`.
- 2026-10-21 REPLICACION NQ abr-sep (1,5R/rango/mercado/VWAP): +6,85 pts/op [IC -6,7, +20,7], 5/6 meses > 0 -> NO_CONCLUYENTE. `REPLICACION_NQ_ABR_SEP_PREREGISTRO_20261021.md`.
- 2026-10-21 ORB-HORARIOS 704 celdas: 0 pasan BH (8 con p<0,05 vs ~35 por azar); pista descriptiva GC nocturno. NQ+franjas OG/VI: ninguna disposicion significativa (camino libre algo mejor en ambos tramos, MDE 0,66 R). `RESULTADOS_ORB_HORARIOS_Y_FRANJAS_20261021.md`.
- 2026-10-21 GC nocturno en abr-jun 2026 (no mirado): racimo -0,028 R/op [IC -0,11, +0,06] -> REFUTA; las 4 destacadas negativas. `PREREGISTRO_GC_NOCTURNO_20261021.md`.
- 2026-10-22 ESCALERA DEL EMBUDO con costos CANONICOS (NQ 1,545 pts/viaje; la campana habia usado la comision de MNQ, 1,12 pts con slippage): descubrimiento +8,6 pts/op, replica +6,3 pts/op IC90 [-4,9, +17,3], p = 0,17 frente a nivel LORD++ 0,011; 782 pruebas en ORB0100 + ORB_HORARIOS -> efecto esperado tras seleccion ~0 -> **SIN_POTENCIA** (~1.050 op.; no abrir holdout). Economico de la replica: sin las 5 mejores operaciones el neto es <= 0 (falla G1 concentracion). `docs/research/auditoria_embudo_20261022/ESCALERA_CANDIDATOS_REALES.json`.
- 2026-10-25 HACIA ATRÁS (celda congelada, USATECH 2023-01 → 2025-08, nunca vista por ORB0100, fricción canónica NQ): n 447, **−1,01 pts/op** [IC90 −3,25; +1,22], MDE 3,36, R bruto +0,11; LORD++ t=1 no rechaza -> **EN CONTRA**. Sin candidato: no se abre el holdout. `PREREGISTRO_ORB0100_ATRAS_20261025.md`.
## NO MEDIDO
- Holdout NQ (>= 2026-10-01) de la celda congelada (descartado: sin candidato tras HACIA ATRÁS).
- La celda con riesgo escalado por volatilidad (R fijo en vez de puntos): el R bruto positivo de 2023-2025 sugiere mirarlo, con pre-registro propio.
- Otros rangos horarios, salidas parciales, sizing por volatilidad; holdout.
- Paridad del indicador NT8 contra el simulador Python (NT8 usa 5 min para resolver; Python usa M1).
