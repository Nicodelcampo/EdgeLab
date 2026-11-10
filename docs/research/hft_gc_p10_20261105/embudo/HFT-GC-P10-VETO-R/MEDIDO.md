## HFT-GC-P10-VETO-R — edgelab.research.hft_gc_p10_veto · señal GC · ejecución GC
- Justificación: Las entradas HFT de Oro COMEX (en particular continuacion tras alejamiento de 20 ticks y retest de borde gris) chocan contra absorcion institucional vecina cuando abren posicion de cara a una zona HFT vigente cercana: vetar entradas sin camino libre frontal (1R/2R/4R) segun tipo de barrera, antiguedad activa (5m..sesion) y estado de mitigacion aisla recorridos a cielo abierto.
- Refutación: 0 celdas nominadas por FDR q <= 0,10 en DESC [20250805, 20260331] (sin rescate por PISTAS porque 202604..202609 ya fue usado por la madre HFT_GC_P10); fallo en INTEGRIDAD o TOPES; refutacion en OOS; o no confirmacion en HOLDOUT sellado a N=150.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en None
- Linaje: hereda 11672 pruebas de ['HFT_GC_P10']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 7730 de 9600 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 4166 (m del FDR 4166 de 4800 celdas), FDR 0 (informativo), maxT 0, RW umbral 3.6044604778289795 (diagnóstico), linaje 11672 como informacion, pistas sin nominación 33, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 1.9851264241632454, 'min': -18.62463294216038, 'q001': -18.578489064805993, 'q010': -17.29763432062062, 'q500': -3.9354526168237722, 'q990': 0.6157745589327153, 'q999': 1.176953495668069, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 1998}); pistas a réplica: apagada por la campaña
