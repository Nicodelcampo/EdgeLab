## OVERNIGHT-INV-YM-R — edgelab.research.overnight_inventario · señal YM · ejecución YM
- Justificación: La sesión overnight de Globex (18:00–09:29 ET) opera con una fracción de la liquidez del horario regular. Cuando el flujo overnight desplaza el precio de forma persistente hacia un extremo del rango nocturno (alto desequilibrio neto y alta  (DISENO_OVERNIGHT_INVENTARIO.md).
- Refutación: Si ni la liquidación (regla 0) ni la continuación (regla 1) nominan celdas en DESC y confirman en réplica OOS, o si los días con inventario extremo (imb_on >= 0,55) no difieren del resto.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 0 pruebas de []; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 36 de 216 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 28 (m del FDR 28 de 108 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.684394598007202 (diagnóstico), linaje 0 como informacion, pistas sin nominación 3, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 0.5556456350902408, 'min': -2.441229164098396, 'q001': -2.434456255433705, 'q010': -2.373500077451482, 'q500': -0.9068035810445438, 'q990': 0.48715597661274035, 'q999': 0.5487966692424905, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 0}); pistas a réplica: ninguna pista relevante con media > 0
