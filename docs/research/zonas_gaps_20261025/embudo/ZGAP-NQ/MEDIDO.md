## ZGAP-NQ — edgelab.research.zonas_gaps · señal NQ · ejecución NQ
- Justificación: Un salto de precio entre barras de 50 ticks (50T) o 1 minuto (M1) que deja un vacío sin rellenar al cierre, o un cluster compacto de >= 3 gaps activos con espacio libre interno acotado, marca un barrido agresivo del libro de órdenes; al alejarse >= AwayDistanceTicks y regresar (o al girar tras una excursión extrema >= 4x estilo U1), mide si órdenes límite pendientes defienden la zona (FAVOR) o si el vacío facilita el cruce (CONTRA).
- Refutación: Ninguna celda nominada por FDR q <= 0,10 (con linaje D6 de celdas evaluables) ni Romano-Wolf en DESC, fallo de integridad/OOS en abr-sep 2026, o media neta <= 0 en el holdout a N=150 fijo.
- PREFLIGHT: ok
- Linaje (informacion; bruto; sin matriz de P&L: se cobra el número bruto (Li-Ji no aplicable)); pistas a réplica k 20 en [20260401, 20260925]
- Linaje: hereda 4626798 pruebas de ['LUXIMB_GRILLA', 'AREAS_EXP_1_CRUZADO']; régimen actual desde sin declarar (el OOS cuenta como régimen actual)
