## HFT-GC-P10-CAPTP-R — edgelab.research.hft_gc_p10_captp · señal GC · ejecución GC
- Justificación: Cuando una zona HFT vigente aparece delante de la entrada a distancia intermedia (>= 1,0R o >= 1,5R pero antes del TP de 2R/3R/4R), adelantar el TP causalmente 2 ticks delante del borde cercano captura el tramo libre antes del muro de liquidez HFT, vetando solo cuando la barrera esta pegada a la entrada.
- Refutación: 0 celdas nominadas por FDR q <= 0,10 en DESC [20250805, 20260331] (sin rescate por PISTAS porque 202604..202609 ya fue usado por la madre HFT_GC_P10); fallo en INTEGRIDAD o TOPES; refutacion en OOS; o no confirmacion en HOLDOUT sellado a N=150.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en None
- Linaje: hereda 11672 pruebas de ['HFT_GC_P10']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 8217 de 9600 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 4416 (m del FDR 4416 de 4800 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.4874982833862305 (diagnóstico), linaje 11672 como informacion, pistas sin nominación 37, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.7204328250868604, 'min': -18.618609571477496, 'q001': -18.559697858200757, 'q010': -16.101291268840015, 'q500': -3.816289525160016, 'q990': 1.064064103255207, 'q999': 1.5291593769698346, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 2017}); pistas a réplica: apagada por la campaña
