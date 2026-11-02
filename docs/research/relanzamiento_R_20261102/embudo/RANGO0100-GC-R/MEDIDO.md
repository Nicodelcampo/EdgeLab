## RANGO0100-GC-R — edgelab.research.rango_asia0100 · señal GC · ejecución GC
- Justificación: Ruptura del rango 01:00–01:15 ET en GC con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 4654321 pruebas de ['ASIA_BOS_GAPS_GC']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 108 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 96 (m del FDR 96 de 648 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.9330413341522217 (diagnóstico), linaje 4654321 como informacion, pistas sin nominación 16, candidatas 0
- PISTAS a réplica (ATJ-25): 1 congeladas de 16 (k 20), ventana [20260401, 20260930], un paso de LORD++ por lote; celdas [[2, 0, 1, 0, 0, 3]]
