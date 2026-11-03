## TAU-GC-R — edgelab.research.tau_tendencia · señal GC · ejecución GC
- Justificación: Regla de tendencia de Tori Trades en GC M1: la línea por los dos últimos pivotes es momentum adaptativo y salir sólo en su ruptura (τ) deja correr las ganancias (SPEC_TAU_TENDENCIA.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si FIJO_2R iguala o supera a TAU en la misma población, la ventaja de la salida τ queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 4654321 pruebas de ['TORI_TREND_TOQUE3_GC']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 652 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 368 (m del FDR 368 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.248638153076172 (diagnóstico), linaje 4654321 como informacion, pistas sin nominación 19, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.203946199322236, 'min': -11.314555325185433, 'q001': -11.196354373175048, 'q010': -10.202916424707619, 'q500': -2.3983132369716476, 'q990': 0.8377310926618802, 'q999': 1.203946199322236, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 128}); pistas a réplica: ninguna pista relevante con media > 0
