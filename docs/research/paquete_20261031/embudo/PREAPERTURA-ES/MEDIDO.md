## PREAPERTURA-ES — edgelab.research.rango_preapertura · señal ES · ejecución ES
- Justificación: Ruptura del rango 09:15–09:30 ET en ES con una reentrada tras falso quiebre (@theagent_trades; SPEC_RANGOS.md).
- Refutación: 0 nominadas por FDR q <= 0,10 en DESC sin pistas que repliquen, falla en INTEGRIDAD, media <= 0 en OOS/HOLDOUT; si el intento 2 no supera al 1, la reentrada queda refutada.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 5626417 pruebas de ['OTR_930_SWEEP_ES']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 168 de 1296 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 120 (m del FDR 120 de 648 celdas), FDR 0, RW umbral 2.949888229370117 (diagnóstico), linaje 5626417 como informacion, pistas sin nominación 18, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.5441737909206874, 'min': -3.4719746648308005, 'q001': -3.4632894146090547, 'q010': -3.3916254955768097, 'q500': -0.3281071029090671, 'q990': 1.527364779958563, 'q999': 1.5441737909206874, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 4}); pistas a réplica: ninguna pista relevante con media > 0
