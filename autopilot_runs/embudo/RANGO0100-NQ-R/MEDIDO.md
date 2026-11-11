## RANGO0100-NQ-R — edgelab.research.rango_asia0100 · señal NQ · ejecución NQ
- Justificación: Ruptura del rango 01:00–01:15 ET en NQ con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626428 pruebas de ['ASIA_BOS_GAPS_NQ']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 174 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 132 (m del FDR 132 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.0941901206970215 (diagnóstico), linaje 5626428 como informacion, pistas sin nominación 16, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.101557845852359, 'min': -3.125659269991178, 'q001': -3.0954778280885984, 'q010': -2.8494786573714856, 'q500': -0.6258848296418049, 'q990': 0.9781697850432903, 'q999': 1.0922236358072117, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 0}); pistas a réplica: ninguna pista relevante con media > 0
