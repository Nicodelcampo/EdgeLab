## TAU-GC — edgelab.research.tau_tendencia · señal GC · ejecución GC
- Justificación: Regla de tendencia de Tori Trades en GC M1: la línea por los dos últimos pivotes es momentum adaptativo y salir sólo en su ruptura (τ) deja correr las ganancias (SPEC_TAU_TENDENCIA.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si FIJO_2R iguala o supera a TAU en la misma población, la ventaja de la salida τ queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 4654311 pruebas de ['TORI_TREND_TOQUE3_GC']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 652 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 368 (m del FDR 368 de 648 celdas), FDR 0, RW umbral 3.22554874420166 (diagnóstico), linaje 4654311 como informacion, pistas sin nominación 36, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.1625298775965596, 'min': -13.582840509550987, 'q001': -12.842976157633435, 'q010': -7.877114669030429, 'q500': -1.8224192668568036, 'q990': 0.9901576580913335, 'q999': 1.1625298775965596, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 70}); pistas a réplica: ninguna pista relevante con media > 0
