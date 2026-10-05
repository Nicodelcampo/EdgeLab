# Pre-registro: equivalencia de barras M1 de XAU/USD spot (Dukascopy) con GC para análisis de horas fijas

Escrito **antes de medir**. Cubre estrategias que dependen del precio en horas fijas y de barras de tiempo (como la celda horaria del oro). **No** cubre estrategias de barras de ticks (ver `RESULTADO_EQUIVALENCIA.md`: SOLO_PRECIO).

## Datos
- Futuros: GC, serie líder elegible (`/data/cache/discovery/GC`, barras de 1 minuto con etiqueta de cierre, corte 2026-06-30; 225 sesiones).
- Sustituto: `XAUUSD_m1.parquet` (M1 bid/ask de Dukascopy, UTC, inicio de vela). Precio = promedio bid/ask del cierre; etiqueta de cierre = inicio + 1 minuto, igual que las barras de GC.
- Solape: sesiones de GC elegibles dentro del rango de M1. No se lee nada desde 2026-10-01.

## Medidas
1. Correlación de los retornos de 1 minuto (cierre a cierre, solo minutos consecutivos presentes en ambos).
2. Concordancia de signo del retorno de 15 minutos (momentum `mom_15`) en los 96 horarios de cada sesión.
3. Retorno de la operación de 15 minutos de la celda: entrada en el cierre de la barra de franja + 2 min, salida 15 min después; correlación entre GC y spot sobre todas las sesiones y franjas, y diferencia media en valor absoluto relativa al desvío de GC.

## Umbrales (fijados ahora)
| Criterio | Umbral para «pasa» |
|---|---|
| M1-a: correlación de retornos de 1 min | ≥ **0,90** |
| M1-b: concordancia de signo de `mom_15` | ≥ **0,90** |
| M1-c: correlación del retorno de la operación de 15 min | ≥ **0,90** |
| M1-d: diferencia absoluta media de ese retorno / desvío de GC | ≤ **0,25** |

## Veredicto
- **M1_UTILIZABLE:** pasan los cuatro. El M1 de spot sirve para análisis de horas fijas dependientes del precio (declarando que es spot).
- **M1_PARCIAL:** pasa alguno y falla alguno; se informa cuál.
- **M1_NO_UTILIZABLE:** no pasa ninguno.
No se ajustan umbrales después de ver el resultado.

## Expectativa registrada
Pasa todo: el M1 de tiempo es un sustituto razonable del precio del oro, con diferencias de base y de ruido de cotización.

## Límites
Mide equivalencia de precio, no de costos ni de ejecución (se modelan con GC). El spot no tiene operaciones ni volumen real.
