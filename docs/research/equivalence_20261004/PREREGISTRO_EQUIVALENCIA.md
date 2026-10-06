# Pre-registro: equivalencia entre XAU/USD spot (Dukascopy) y MGC para la EMA 200/500/2000 de barras de 25 ticks

Escrito **antes de correr** la medición sobre datos reales. Herramienta: `tools/equivalence_check.py` (commit anterior a este documento); prueba de cañería con sustituto sintético ya hecha (techo F1 ≈ 0,98).

## Datos
- Futuros: artefactos de MGC previos al holdout (`/data/analysis/mgc/artifacts`, 2025-10-07 a 2026-03-31; 1.643 señales de la regla original, reproducidas exactamente por `ema_cross_signals`). No se abre nada desde 2026-04-01.
- Sustituto: `nicolasbuttaro/edgelab-dukascopy-xauusd-ticks-m1`, `XAUUSD_ticks.parquet` (bid/ask, UTC), recortado al mismo solape.

## Qué se mide
- **A (precio):** el precio spot en el cierre de cada barra de 25 ticks de MGC reemplaza al cierre de MGC; se calcula la misma señal y se compara con las señales originales. Mide la diferencia de precio (base y ruido) sin tocar la formación de barras.
- **B (formación de barras):** barras de N eventos de spot, con N elegido por la distancia de Kolmogorov-Smirnov entre duraciones de barra (solo en el solape); señal EMA 200/500/2000 sobre esas barras. Mide si el spot reproduce el ritmo y el momento de las señales.
- Coincidencia de señales: misma dirección, uno a uno, dentro de una tolerancia de tiempo. Resultado de las señales a horizonte fijo (15, 30, 60 y 120 min), agregado por día; correlación diaria entre MGC y spot.

## Umbrales (fijados ahora)
| Criterio | Umbral para «pasa» |
|---|---|
| A | F1 de señales ≥ **0,80** con tolerancia de 900 s |
| B1 | F1 de señales ≥ **0,50** con tolerancia de 3.600 s |
| B2 | correlación diaria de resultados ≥ **0,50** en los horizontes de 1.800 s y de 3.600 s |

## Veredicto (regla)
- **SUSTITUTO_UTILIZABLE:** pasan A, B1 y B2. El spot puede extender la muestra de la EMA, declarando que es spot.
- **SOLO_PRECIO:** pasa A y falla B1 o B2. El spot sirve para estrategias que dependen del precio en horas fijas, **no** para esta estrategia de barras de ticks.
- **NO_UTILIZABLE:** no pasa A.
Las dos primeras filas del veredicto no cambian si algún valor queda apenas por debajo: no se ajustan umbrales después de ver el resultado.

## Expectativa registrada
Con barras de ≈ 2,6 s (25 operaciones en MGC) y ticks de cotización en el spot, espero que **A pase** (misma trayectoria de precio) y que **B falle**: el momento de las señales depende de operaciones ejecutadas, que el spot no tiene.

## Límites
Un solo par instrumento-estrategia; la equivalencia medida vale para esta señal y este período. No toca el holdout formal (desde 2026-10-01). Costos y ejecución se modelan con MGC, nunca con el spread de Dukascopy.
