# AVZVOL: aporte de rapidez y cambio de denominador

## Conclusión para continuar
El rango previo amplio aporta selección de recorrido; la salida rápida añade alcance dentro de ese contexto, con bastante menos cobertura. Conviene comparar rango-solo frente a rango+rapidez con el MISMO trigger y gestión cuando se pueda evaluar ejecución. No hay entrada rentable validada.
**Corrección de interpretación:** el descenso de cobertura geométrica al exigir un nivel más lejano NO prueba que una entrada tardía ejecutada tenga peor expectativa. La prioridad anterior de entrada temprana queda como hipótesis para contrastar, no conclusión de esa curva.

## Ablación: qué aporta cada condición
Misma historia expuesta, mismos tres bloques, mismos terciles del pasado, sin nuevos ajustes. Rango = high-low previo de200 barras / altura de banda. Rapidez = barras de25 operaciones entre ancla y salida, NO velocidad distancia/vela ni velocidad de vuelta. Se reúnen los nueve grupos con sus pesos, no con medias simples de tasas.

| Condición | Cobertura de casos elegibles | Alcanza20 ticks desde borde | Captura de todos los casos que alcanzan20 ticks |
|---|---:|---:|---:|
| Todos | 100.00% | 22.61% | 100.00% |
| Sólo rápida | 33.72% | 25.39% | 37.89% |
| Sólo rango amplio | 40.84% | 26.30% | 47.41% |
| Rápida + amplio | 16.97% | 29.47% | 22.13% |

Cobertura no significa fills. Captura es la fracción ponderada de trayectorias que alcanzan20 ticks que queda dentro del filtro. Todos los porcentajes son medias iguales de3 tasas por bloque. El grupo combinado aumenta concentración de recorrido pero deja fuera más trayectorias con recorrido; no suma automáticamente valor económico.

## Distancias fijas: no escoger sólo el objetivo favorable
| Condición | 5 ticks | 10 ticks | 20 ticks | 40 ticks |
|---|---:|---:|---:|---:|
| Todos | 67.11% | 41.55% | 22.61% | 12.27% |
| Sólo rápida | 70.39% | 45.30% | 25.39% | 14.01% |
| Sólo rango amplio | 71.78% | 47.27% | 26.30% | 14.41% |
| Rápida + amplio | 74.69% | 51.31% | 29.47% | 16.24% |
| Media + amplio | 70.93% | 45.87% | 24.07% | 13.37% |
| Lenta + amplio | 66.33% | 41.10% | 23.77% | 12.55% |

## Incremento de rapidez dentro del rango amplio
Brecha rápida+amplio menos rango-amplio sin filtro de rapidez, puntos porcentuales de alcance; no efecto causal.
| Bloque | 5 ticks | 10 ticks | 20 ticks | 40 ticks |
|---|---:|---:|---:|---:|
| 1 | +0.28 | +1.76 | +0.40 | +0.24 |
| 2 | +4.95 | +5.34 | +7.51 | +4.42 |
| 3 | +3.48 | +5.04 | +1.61 | +0.83 |

El incremento es positivo en cada bloque para todos los niveles declarados, incluidos los objetivos en h. La magnitud no es estable: a20 ticks va desde el pequeño incremento del bloque1 al mayor del bloque2. No es una nueva validación independiente ni significancia estadística.

## La comparación de entrada necesita otro denominador
Ejemplo fijo: 0,25h adicional, no objetivo recomendado. A la izquierda se cuentan TODOS los casos del contexto rápida+amplio; a la derecha sólo las trayectorias cuyo máximo observado llega al nivel supuesto. Son eventos anidados de máximos, no trades.
| Nivel desde el borde | Todos los casos cubriendo nivel +0,25h | Entre trayectorias que llegan al nivel, alcanzan otras0,25h |
|---|---:|---:|
| 0h | 63.45% | 63.45% |
| 0.25h | 41.92% | 65.88% |
| 0.5h | 30.38% | 72.31% |
| 0.75h | 23.85% | 78.59% |

**La primera columna de tasas cae y la tasa condicionada aumenta.** Por tanto, la curva anterior no permite afirmar por sí sola “entrar más tarde es peor”. Tampoco la columna condicionada permite afirmar lo contrario: no existen precios/timestamps de fill, orden de stop/target, barras de señal ni costos. No son win-rates y los denominadores cambian entre filas; no seleccionar retrospectivamente trades por máximos futuros. El máximo excluye la barra de salida y puede estar censurado por ventana/sesión; no aplicar a entradas intrabar en la salida.

## Controles: qué NO atribuir a las zonas
| Condición | Real: alcance20 ticks | Control pseudo: alcance20 ticks |
|---|---:|---:|
| Todos | 22.61% | 23.70% |
| Sólo rápida | 25.39% | 26.38% |
| Sólo rango amplio | 26.30% | 27.07% |
| Rápida + amplio | 29.47% | 28.96% |

Los controles reproducen un patrón similar. Fuente/as-of y controles verdaderamente zone-free siguen pendientes; no atribuir una causa propia de la zona. CSVs retienen ambos cohorts, todos los bloques y todas las distancias.

## Prueba operativa que vale la pena preparar
1. Mismo trigger causal de salida y gestión: comparar todos, rango-solo, rapidez-sola y ambos. Mantener los umbrales definidos del pasado, no elegir nuevos cortes con estas cifras.
2. Separar entrada temprana, confirmación de avance y retest confirmado; comparar desde precios realmente ejecutables, no desde el borde. Ninguna de las tres es ganadora todavía.
3. Medir cobertura de señales, fills y oportunidades omitidas, además de retorno neto y drawdown. Una tasa de alcance mayor con menos casos no resuelve la selección óptima.
4. Para el retest: medir excursión previa, distancia por vela, eficiencia, compresión, número de oscilaciones y picos disponibles AL CONFIRMARSE. Trayectoria y timestamps siguen faltando en estos exports, por lo que estos aspectos no se han medido.
5. Nuevos desenlaces/precios, P&L y reserva ciega permanecen fuera de este estudio; no se modifican autorizaciones ni gates.

## Reproducción y límites
Seis Parquets exactos,544.531 filas evento×celda; sólo las etiquetas exportadas ya inspeccionadas. Uniones por fold/cohort/bucket verificadas uno-a-uno; ninguna media simple de buckets. Todos los numeradores y pesos se contrastan directamente con Parquet usando Counter y math.fsum, sin importar el helper anterior. Duplicados conservados compartiendo peso dentro del ancla.
El perfilador interpretó 0:2 como fecha y sugirió sumas diarias de denominadores: ambos indicios son falsos a esta granularidad. Bucket es categoría; rows y sessions se repiten por métrica y NO se suman como observaciones independientes. No hay p-valores, ajuste nuevo ni certificación de estrategia.
El alcance es máximo acotado desde borde después de la salida hasta primer cierre dentro o límite de ventana/sesión. No es beneficio ni trayectoria posterior al fill. Media de tasas/ratios por bloque, no tasa pooled ni cociente de medias.

```bash
python docs/research/avzvol_filter_ablation_20261011/analyze.py --repo . --input-dir /ruta/privada/avzvol --out /ruta/salida
```

[Evidencia](avzvol_filter_ablation_20261011/evidence.json) · [Comparación completa](avzvol_filter_ablation_20261011/policy-summary.csv) · [Por bloque](avzvol_filter_ablation_20261011/policy-by-fold.csv) · [Denominador condicionado](avzvol_filter_ablation_20261011/conditional-path-reach.csv)
El gráfico pasó el preflight canónico; el adjuntador nativo falló sin reintento. Se conservan tablas y spec, sin declarar un gráfico inline publicado.
