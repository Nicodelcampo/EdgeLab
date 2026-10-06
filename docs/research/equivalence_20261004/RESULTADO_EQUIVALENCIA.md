# Resultado: equivalencia spot XAU/USD (Dukascopy) con MGC para la EMA 200/500/2000 de 25 ticks

Pre-registro: `PREREGISTRO_EQUIVALENCIA.md` (commit `a5f16769`, umbrales fijados antes de correr). Datos: MGC previo al holdout (2025-10-07 a 2026-03-31, 1.643 señales originales) y 48.748.969 ticks spot del mismo período. Salida cruda: `equivalence_spot_vs_mgc.json`. No se abrió el holdout.

## Veredicto: **SOLO_PRECIO**
El spot reproduce la trayectoria de precio, pero **no** sirve para extender la muestra de esta estrategia de barras de ticks.

| Criterio | Umbral | Resultado | Pasa |
|---|---|---|---|
| A: F1 de señales con precio spot sincronizado (tol. 900 s) | ≥ 0,80 | **0,905** (1.487 de 1.643 coinciden, 6 en dirección opuesta) | sí |
| B1: F1 con barras equivalentes de spot (tol. 3.600 s) | ≥ 0,50 | **0,565** (precisión 0,448, exhaustividad 0,765) | sí |
| B2: correlación diaria de resultados a 1.800 s y a 3.600 s | ≥ 0,50 en ambos | **0,201** y 0,528 | **no** (falla 1.800 s) |

Regla: pasa A y falla B2 → SOLO_PRECIO.

## Detalle
- **A (precio):** con el mismo calendario de barras de futuros, el precio spot da casi las mismas señales (F1 0,894 a 300 s, 0,905 a 900 s, 0,900 a 3.600 s). La diferencia de precio entre spot y MGC (base y ruido) casi no altera la señal.
- **B (formación de barras):** el tamaño de barra elegido por KS fue **N = 13 ticks de spot** (mediana de duración 1,97 s frente a 2,58 s en MGC; KS = 0,19, un ajuste mediocre). Las barras de spot generan **2.805 señales frente a 1.643** de MGC: el spot dispara más señales, con precisión de 0,40 a 0,45. Las señales que coinciden en momento y dirección son 1.119 a 1.257 según la tolerancia, y entre 84 y 516 coinciden en tiempo pero con dirección opuesta.
- **Resultados a horizonte fijo (media por señal, en dólares del spot, correlación diaria en 141 días):**

| Horizonte | Media MGC | Media spot | Correlación diaria |
|---|---:|---:|---:|
| 900 s | 0,453 | 0,150 | 0,091 |
| 1.800 s | 0,516 | 0,349 | 0,201 |
| 3.600 s | 0,305 | 0,198 | 0,528 |
| 7.200 s | 0,330 | −0,182 | 0,737 |

A horizontes cortos la correlación diaria es casi nula; a horizontes de horas sube, porque ambos siguen el mismo movimiento del oro. A 7.200 s el resultado medio por señal cambia de signo.

## Cómo leerlo
- **Coincide con la expectativa registrada** («A pasa y B falla»), con una salvedad: B1 pasó por poco (0,565) y lo que hizo fallar a B fue B2.
- El spot es **utilizable para estrategias que dependen del precio en horas fijas** (como la celda horaria del oro), no para esta EMA de barras de 25 ticks.
- **No** se debe usar el spot para decir que la EMA de MGC «funciona o no» en datos nuevos: el momento de las señales difiere y la media por señal no se reproduce.

## Límites
- Un solo par instrumento-estrategia y un solo período. La elección de N por KS cayó en el borde de la rejilla de candidatos, y la mediana de duración del spot con N = 13 (1,97 s) queda por debajo de la de MGC (2,58 s). Un N mayor igualaría la mediana, pero no se probó para no ajustar después de ver el resultado; el veredicto no cambia el criterio A, y B2 ya falla a 1.800 s con una correlación de 0,20.
- El resultado a horizonte fijo es una medida simple (dirección × cambio de precio), no el reproceso con stop y objetivo de la estrategia.
- Los costos y la ejecución siguen modelándose con el instrumento real, no con el spread de Dukascopy.
