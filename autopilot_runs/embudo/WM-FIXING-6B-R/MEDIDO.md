## WM-FIXING-6B-R — edgelab.research.wm_fixing · señal 6B · ejecución 6B
- Justificación: Los fondos pasivos y gestores globales de renta fija/variable ejecutan sus coberturas cambiarias al tipo de referencia WMR de las 16:00 de Londres (hora de Londres, con su horario de verano). El flujo acumulado entre las 15:30 y las 16:00 de Londres produce presión de inventario que o bie (DISENO_WM_FIXING.md).
- Refutación: Si ni la rama de reversión (regla 0) ni la de continuación (regla 1) superan el tamiz FDR q <= 0,10 en DESC o no replican en OOS, o si la ventaja no crece con el impulso y volumen relativo del Fix.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 0 pruebas de []; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 120 de 216 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 88 (m del FDR 88 de 108 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.6288180351257324 (diagnóstico), linaje 0 como informacion, pistas sin nominación 9, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 0.7241720183775903, 'min': -4.5934398679931645, 'q001': -4.5748365956628705, 'q010': -4.407407144690227, 'q500': -1.8214238829063967, 'q990': 0.6687393043993661, 'q999': 0.7186287469797676, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 21}); pistas a réplica: ninguna pista relevante con media > 0
