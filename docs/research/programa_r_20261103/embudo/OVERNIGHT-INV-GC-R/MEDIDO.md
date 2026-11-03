## OVERNIGHT-INV-GC-R — edgelab.research.overnight_inventario · señal GC · ejecución GC
- Justificación: La sesión overnight de Globex (18:00–09:29 ET) opera con una fracción de la liquidez del horario regular. Cuando el flujo overnight desplaza el precio de forma persistente hacia un extremo del rango nocturno (alto desequilibrio neto y alta  (DISENO_OVERNIGHT_INVENTARIO.md).
- Refutación: Si ni la liquidación (regla 0) ni la continuación (regla 1) nominan celdas en DESC y confirman en réplica OOS, o si los días con inventario extremo (imb_on >= 0,55) no difieren del resto.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 0 pruebas de []; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 52 de 216 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 44 (m del FDR 44 de 108 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.7869677543640137 (diagnóstico), linaje 0 como informacion, pistas sin nominación 7, candidatas 0
- **SIN_CANDIDATAS** — ninguna pista nominada por FDR q 0.1 cumple la selección; nulo publicado ({'max': 0.8743256841694041, 'min': -2.17987091497864, 'q001': -2.1582340248982335, 'q010': -1.963502014174575, 'q500': -0.3280632585652057, 'q990': 0.7531049232568309, 'q999': 0.862203608078147, 'sobre_z_tamiz': 0, 'bajo_menos_z_tamiz': 0}); pistas a réplica: ninguna pista relevante con media > 0
