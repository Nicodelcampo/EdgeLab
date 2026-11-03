## OVERNIGHT-INV-NQ-R — edgelab.research.overnight_inventario · señal NQ · ejecución NQ
- Justificación: La sesión overnight de Globex (18:00–09:29 ET) opera con una fracción de la liquidez del horario regular. Cuando el flujo overnight desplaza el precio de forma persistente hacia un extremo del rango nocturno (alto desequilibrio neto y alta  (DISENO_OVERNIGHT_INVENTARIO.md).
- Refutación: Si ni la liquidación (regla 0) ni la continuación (regla 1) nominan celdas en DESC y confirman en réplica OOS, o si los días con inventario extremo (imb_on >= 0,55) no difieren del resto.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 0 pruebas de []; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
- Evaluables: 48 de 216 celdas registradas heredan multiplicidad (el resto no llegó a 30 operaciones)
- DESC [20250805, 20260331]: evaluables 40 (m del FDR 40 de 108 celdas), FDR 0 (informativo), maxT 0, RW umbral 2.7716119289398193 (diagnóstico), linaje 0 como informacion, pistas sin nominación 12, candidatas 0
- PISTAS a réplica (ATJ-25): 2 congeladas de 12 (k 20), ventana [20260401, 20260930], un paso de LORD++ por lote; celdas [[1, 0, 1, 2, 0], [0, 1, 0, 2, 1]]
