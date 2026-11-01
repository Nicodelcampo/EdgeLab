## RANGO0100-GC — edgelab.research.rango_asia0100 · señal GC · ejecución GC
- Justificación: Ruptura del rango 01:00–01:15 ET en GC con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 4654311 pruebas de ['ASIA_BOS_GAPS_GC']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 108 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 96 (m del FDR 96 de 648 celdas), FDR 49, RW umbral 2.9711320400238037 (diagnóstico), linaje 4654311 como informacion, pistas sin nominación 0, candidatas 3
- Potencia prevista (informativa): [0, 0, 2, 0, 0, 5]: OOS n 36.0 potencia 0.20, holdout n 150 potencia 0.51; [2, 0, 2, 0, 0, 3]: OOS n 111.0 potencia 0.31, holdout n 150 potencia 0.37; [1, 0, 2, 0, 1, 5]: OOS n 55.5 potencia 0.21, holdout n 150 potencia 0.40
- INDAGA: marginales de 3 candidatas guardadas
