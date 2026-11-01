## RANGO0100-NQ — edgelab.research.rango_asia0100 · señal NQ · ejecución NQ
- Justificación: Ruptura del rango 01:00–01:15 ET en NQ con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626418 pruebas de ['ASIA_BOS_GAPS_NQ']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 174 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 132 (m del FDR 132 de 648 celdas), FDR 0, RW umbral 3.1042003631591797 (diagnóstico), linaje 5626418 como informacion, pistas sin nominación 19, candidatas 0
- PISTAS a réplica (ATJ-25): 1 congeladas de 19 (k 20), ventana [20260401, 20260930], un paso de LORD++ por lote; celdas [[0, 1, 2, 0, 0, 4]]
