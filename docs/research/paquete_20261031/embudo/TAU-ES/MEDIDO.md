## TAU-ES — edgelab.research.tau_tendencia · señal ES · ejecución ES
- Justificación: Regla de tendencia de Tori Trades en ES M1: la línea por los dos últimos pivotes es momentum adaptativo y salir sólo en su ruptura (τ) deja correr las ganancias (SPEC_TAU_TENDENCIA.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si FIJO_2R iguala o supera a TAU en la misma población, la ventaja de la salida τ queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5994141 pruebas de ['TORI_TREND_TOQUE3_ES']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 712 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 372 (m del FDR 372 de 648 celdas), FDR 0, RW umbral 3.297156810760498 (diagnóstico), linaje 5994141 como informacion, pistas sin nominación 26, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 0.48263526982662186, 'min': -18.762421914385182, 'q001': -17.91679604228436, 'q010': -14.55683766885387, 'q500': -2.458261346800622, 'q990': 0.41457047920491014, 'q999': 0.48263526982662186, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 155}); pistas a réplica: ninguna pista relevante con media > 0
