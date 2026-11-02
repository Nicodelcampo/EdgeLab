## TAU-NQ-R — edgelab.research.tau_tendencia · señal NQ · ejecución NQ
- Justificación: Regla de tendencia de Tori Trades en NQ M1: la línea por los dos últimos pivotes es momentum adaptativo y salir sólo en su ruptura (τ) deja correr las ganancias (SPEC_TAU_TENDENCIA.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si FIJO_2R iguala o supera a TAU en la misma población, la ventaja de la salida τ queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626427 pruebas de ['TORI_TREND_TOQUE3_NQ']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 712 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 372 (m del FDR 372 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.199310541152954 (diagnóstico), linaje 5626427 como informacion, pistas sin nominación 33, candidatas 0
- PISTAS a réplica (ATJ-25): 2 congeladas de 33 (k 20), ventana [20260401, 20260930], un paso de LORD++ por lote; celdas [[2, 1, 2, 1, 1, 3], [2, 1, 1, 0, 1, 3]]
