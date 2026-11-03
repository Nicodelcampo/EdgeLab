## COMEX-CIERRE-GC-R — edgelab.research.comex_cierre_oro · señal GC · ejecución GC
- Justificación: El precio de liquidación diaria (Daily Settlement) de futuros y opciones de oro en COMEX se fija a las 13:30 ET. Entre las 12:30 y las 13:30 ET, productores, bullion banks y operadores de opciones ejecutan coberturas de delta y margen. Al c (DISENO_COMEX_CIERRE_ORO.md).
- Refutación: Ausencia de celdas nominadas en R o fallo en réplica OOS; si las velas con desplazamiento fuerte en el pit (desp_rango >= 0,60) rinden igual o peor que las de desplazamiento débil.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260930]
- Linaje: hereda 0 pruebas de []; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
