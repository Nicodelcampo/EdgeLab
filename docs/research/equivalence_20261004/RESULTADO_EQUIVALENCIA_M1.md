# Resultado: equivalencia de M1 spot (Dukascopy) con GC para horas fijas

Pre-registro: `PREREGISTRO_EQUIVALENCIA_M1.md` (commit anterior a la medición). Herramienta: `tools/equivalence_m1_gc.py`. Salida cruda: `equivalence_m1_spot_vs_gc.json`. Solape: 309.413 minutos en común entre las sesiones elegibles de GC (2025-08-03 a 2026-06-30) y el M1 de spot. No se leyó nada desde 2026-10-01.

## Veredicto: **M1_UTILIZABLE** (pasan los cuatro criterios)
| Criterio | Umbral | Resultado | Pasa |
|---|---|---|---|
| M1-a: correlación de retornos de 1 min | ≥ 0,90 | **0,975** (309.004 retornos) | sí |
| M1-b: concordancia de signo de `mom_15` | ≥ 0,90 | **0,970** (18.976 observaciones) | sí |
| M1-c: correlación del retorno de la operación de 15 min | ≥ 0,90 | **0,997** (18.916 operaciones) | sí |
| M1-d: diferencia absoluta media / desvío de GC | ≤ 0,25 | **0,047** (desvío de GC: 8,38 USD) | sí |

## Lectura
- Para análisis de **horas fijas y barras de tiempo**, el M1 de spot reproduce el precio de GC: los retornos de la operación de 15 minutos de la celda del oro casi coinciden (correlación 0,997, error medio ≈ 5 % del desvío).
- A un minuto el signo coincide en el 94,4 % de los retornos no nulos: el ruido de cotización pesa en horizontes cortos y deja de pesar a 15 minutos (97 %).
- Contrasta con la EMA de barras de 25 ticks (`RESULTADO_EQUIVALENCIA.md`, SOLO_PRECIO): ahí lo que falla es la formación de barras por operaciones, no el precio.

## Límites
- Mide equivalencia de **precio**. Costos, spreads y ejecución se modelan con GC (el spot no tiene operaciones ni volumen real).
- Los resultados valen para el oro en este período (2025-08 a 2026-06) y para estrategias que usan solo el precio en horas fijas. No dicen nada sobre variables de volumen, agresor o libro.
- Una estrategia usada con spot debe declararlo: la evidencia es más débil que con el futuro.
