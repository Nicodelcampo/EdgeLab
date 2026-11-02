## TAU-ES-R — edgelab.research.tau_tendencia · señal ES · ejecución ES
- Justificación: Regla de tendencia de Tori Trades en ES M1: la línea por los dos últimos pivotes es momentum adaptativo y salir sólo en su ruptura (τ) deja correr las ganancias (SPEC_TAU_TENDENCIA.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si FIJO_2R iguala o supera a TAU en la misma población, la ventaja de la salida τ queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 6250617 pruebas de ['TORI_TREND_TOQUE3_ES']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 712 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 372 (m del FDR 372 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.2204689979553223 (diagnóstico), linaje 6250617 como informacion, pistas sin nominación 7, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': -0.3903336415752419, 'min': -40.6237013484547, 'q001': -35.8531687072974, 'q010': -20.099587160461777, 'q500': -4.318152350828877, 'q990': -0.5418876371438472, 'q999': -0.3903336415752419, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 238}); pistas a réplica: ninguna pista relevante con media > 0
