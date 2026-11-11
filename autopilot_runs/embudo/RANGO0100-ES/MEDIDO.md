## RANGO0100-ES — edgelab.research.rango_asia0100 · señal ES · ejecución ES
- Justificación: Ruptura del rango 01:00–01:15 ET en ES con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626417 pruebas de ['ASIA_BOS_GAPS_ES']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 150 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 108 (m del FDR 108 de 648 celdas), FDR 0, RW umbral 2.9283196926116943 (diagnóstico), linaje 5626417 como informacion, pistas sin nominación 10, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 0.6195982601216259, 'min': -3.6137655712288415, 'q001': -3.6057752815986666, 'q010': -3.534292197260839, 'q500': -1.077616551083225, 'q990': 0.5560882545281132, 'q999': 0.6133321288930915, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 8}); pistas a réplica: ninguna pista relevante con media > 0
