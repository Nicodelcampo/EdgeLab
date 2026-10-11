# AVZVOL: indicadores, forma de salida y prioridad de entradas

## Resultado para decidir
La primera prioridad es investigar **continuación después de una salida rápida, cuando el rango previo es grande respecto del ancho de la banda**. Es la combinación con mayor reducción media de error Brier entre las 26 pruebas de esta exploración. **No demuestra rentabilidad ni una ventaja propia de las zonas:** el patrón también aparece en pseudo-controles legacy, que todavía no están certificados como zone-free.

AUC media de la combinación: 0.6030, frente a 0.5561 de la base por celda. AUC NO es tasa de aciertos ni de operaciones ganadoras. Mejora media Brier: 0.0017210; positiva en los tres bloques, pero modesta en magnitud absoluta.

**Después del retest:** ninguna de las 26 pruebas mejora en promedio el error Brier para O3b en reales. No implica que toda estrategia de retest sea imposible: estas variables son viejas, tomadas en t0, y no describen la estructura del regreso.

## Qué significa salida rápida y rango amplio
- Demora: `te-t0`, número de barras de 25 trades hasta la salida observada. No segundos.
- Rango previo: `amp`, máximo high menos mínimo low de las 200 barras terminadas en t0. No desplazamiento de la salida.
- Rango/ancho: `amp/h`, con `h=H-L+1`. Es contexto de escala y facilidad del objetivo geométrico; NO demuestra impulso direccional propio de la zona.
- La esquina ilustrativa rápida/amplia usa el tercil inferior de demora y superior de rango/ancho. La esquina lenta/estrecha, lo opuesto. Cortes aprendidos sólo del pasado, distintos por bloque y cohorte. Se ilustran tras inspeccionar; no son reglas operativas congeladas.
- Covariables antiguas en t0; dirección `dir` sólo observable tras la salida, nunca como señal en t0.
- El primer tercil de demora de reales resulta menor que 5 barras en los tres entrenamientos. El corte superior de rango/ancho cambia; no adoptar un número optimizado.

## Continuación por contexto y soporte
O2 significa llegar una altura h más allá del borde de salida antes del primer cierre dentro, excluyendo la barra de salida, hasta 2.000 barras posteriores de la misma sesión. No hay entrada, stop, fill ni costos medidos. Las tasas usan las ponderaciones del bloque original restringidas al grupo, no una nueva reponderación igualando sólo las sesiones del subgrupo.

| Bloque | Grupo | O2 real | Filas / anclas / sesiones | O2 control |
|---|---|---:|---|---:|
| 1 | Rápida/amplia | 21.37% | 2083 / 835 / 52 | 25.93% |
| 1 | Lenta/estrecha | 9.23% | 1004 / 492 / 48 | 9.58% |
| 2 | Rápida/amplia | 28.32% | 2214 / 877 / 52 | 27.29% |
| 2 | Lenta/estrecha | 7.61% | 1650 / 746 / 45 | 9.12% |
| 3 | Rápida/amplia | 21.87% | 3432 / 1353 / 52 | 25.77% |
| 3 | Lenta/estrecha | 9.18% | 3445 / 1497 / 50 | 8.63% |

Las filas son evento×celda, no observaciones independientes. Las anclas pueden aparecer en varias celdas; las sesiones no son replicaciones independientes entre contratos del mismo mercado. CSV completo conserva los nueve grupos, cortes, masas y soporte.

## Distancia ya disponible, no señal de entrada
`mx_h` registra la máxima excursión observada del lado de salida desde el borde, dividida por h, hasta el primer cierre dentro o el final de la ventana/sesión. Excluye la barra de salida e incluye high/low de la barra que vuelve a cerrar dentro. Si la ventana termina antes de la vuelta, la distancia sigue siendo un máximo observado acotado, no la excursión completa futura. No usarla para filtrar una entrada antes de observarla.

| Bloque | Grupo real | Mediana máxima observada (h) | P90 (h) | Mediana (ticks) |
|---|---|---:|---:|---:|
| 1 | Rápida/amplia | 0.316 | 2.067 | 9.00 |
| 1 | Lenta/estrecha | 0.150 | 0.978 | 6.00 |
| 2 | Rápida/amplia | 0.474 | 2.056 | 12.00 |
| 2 | Lenta/estrecha | 0.125 | 0.714 | 5.00 |
| 3 | Rápida/amplia | 0.389 | 2.066 | 10.00 |
| 3 | Lenta/estrecha | 0.143 | 0.860 | 6.00 |

`(te-t0)/h` mide demora previa normalizada por ancho declarado, no velas por distancia efectivamente recorrida. Faltan índice/tiempo del máximo, precio al salir y trayectoria de regreso: no hay medición válida de velocidad de vuelta ni de picos en estos exports.

La mediana del máximo observado en el grupo rápido/amplio queda por debajo de 0,5h en los tres bloques. Es mejor que el otro contexto, pero la mayoría no alcanza 1h antes de volver a cerrar dentro. Esto impide presentar el filtro como una continuación fuerte asegurada. La distancia desde el borde no equivale a recorrido rentable desde un precio de entrada.

## Todas las pruebas: conservar también los fracasos
ΔBrier se muestra ×1.000. Positivo = menor error que la base histórica por celda. Promedio de tres bloques, NO significancia estadística ni beneficio esperado. El control de ruido cuenta entre las 26 pruebas.

| Indicador / mecanismo | ΔBrier O2 ×1.000 | AUC O2 | Bloques mejora O2 | ΔBrier O3b ×1.000 |
|---|---:|---:|---:|---:|
| `delay_x_range_band` | +1.7210 | 0.6030 | 3/3 | -0.5954 |
| `range_over_band` | +1.5889 | 0.6015 | 3/3 | -0.5457 |
| `range_band_x_momentum` | +1.3007 | 0.5957 | 3/3 | -1.0001 |
| `occupancy_x_range_band` | +1.0935 | 0.5920 | 3/3 | -0.9880 |
| `delay_x_duration100` | +0.8985 | 0.5867 | 3/3 | -0.6477 |
| `exit_delay_bars` | +0.7093 | 0.5774 | 3/3 | -0.3401 |
| `delay_x_momentum` | +0.7033 | 0.5773 | 3/3 | -0.6141 |
| `amplitude` | +0.6893 | 0.5772 | 3/3 | -0.6103 |
| `occupancy` | +0.3827 | 0.5705 | 2/3 | -0.2010 |
| `band_height` | +0.3328 | 0.5797 | 2/3 | -0.1485 |
| `delay_per_declared_band_tick` | +0.2881 | 0.5658 | 3/3 | -0.3867 |
| `intensity_x_momentum` | +0.2451 | 0.5679 | 3/3 | -0.5583 |
| `log_intensity100` | +0.2365 | 0.5667 | 3/3 | -0.0552 |
| `duration100` | +0.2263 | 0.5655 | 3/3 | -0.0616 |
| `duration_occ` | +0.2199 | 0.5645 | 2/3 | -0.1853 |
| `momentum_per_range` | +0.2031 | 0.5674 | 3/3 | -0.1256 |
| `momentum_dir` | +0.1953 | 0.5618 | 3/3 | -0.1600 |
| `clock` | +0.0761 | 0.5693 | 2/3 | -1.9140 |
| `trend_sign_dir` | -0.0063 | 0.5525 | 2/3 | -0.0689 |
| `volume100` | -0.0221 | 0.5485 | 1/3 | -0.1667 |
| `log_intensity_change` | -0.0628 | 0.5504 | 1/3 | -0.2073 |
| `noise_control` | -0.1237 | 0.5501 | 0/3 | -0.1523 |
| `trend_per_range` | -0.1326 | 0.5479 | 1/3 | -0.1146 |
| `volume_occ` | -0.1691 | 0.5455 | 0/3 | -0.2329 |
| `trend_x_momentum` | -0.2268 | 0.5469 | 1/3 | -0.3863 |
| `trend_dir` | -0.4073 | 0.5413 | 0/3 | -0.2080 |

## Transferencia por contrato
Los dos contratos más antiguos sólo aparecen en entrenamiento con este corte global; no se presentan como seis confirmaciones. En prueba hay cuatro contratos. Rango/ancho por sí solo se invierte en MNQ_12-26; la combinación mejora allí muy poco y tiene sólo diez sesiones.

| Contrato | Sesiones / bloques | ΔBrier combinación ×1.000 | ΔBrier rango/ancho ×1.000 |
|---|---|---:|---:|
| MNQ_03-26 | 44 / 1 | +0.9024 | +0.9387 |
| MNQ_06-26 | 57 / 2 | +3.1960 | +3.0563 |
| MNQ_09-26 | 46 / 2 | +2.5390 | +2.7138 |
| MNQ_12-26 | 10 / 1 | +0.1738 | -0.6959 |

## Qué lógica de entrada conviene investigar
1. **Continuación temprana:** salida observada, demora corta y rango previo amplio relativo al objetivo; medir entrada ejecutable posterior a la señal, stop, costos, recorrido adverso/favorable y vencimiento. No entrar retrospectivamente al borde ni asumir fill en la barra ya terminada.
2. **Retest con estructura nueva:** no reutilizar estos filtros como dirección del rebote. Actualizar contexto al retest; estudiar rechazo fuera, recuperación dentro y pivotes confirmados como mecanismos separados.
3. **Evitar como filtro central por ahora:** tendencia larga alineada y volumen aislado; fueron peores que la base en O2, y no rescataron O3b. No significa que toda variante de ellos sea inútil.
4. **No optimizar para conseguir un ganador:** las familias y combinaciones se ampliaron después de mirar resultados, a pedido del usuario. Congelar pocos candidatos y confirmar en datos realmente no vistos antes de promover una estrategia.

## Salida, vuelta y picos: pruebas de mecanismo pendientes
Estas son hipótesis, NO resultados medidos en la vuelta:
- Salida: desplazamiento del cierre desde el borde, excursión antes del retest, barras y tiempo por distancia real, eficiencia de trayectoria (desplazamiento / suma de cambios absolutos), cuerpo/mechas, cierres fuera y solapamiento.
- Vuelta: fracción devuelta de la excursión observada hasta ese momento; velocidad de vuelta relativa a la salida; compresión de rango, solapamiento, profundidad y número de cruces. Un regreso lento/comprimido y uno rápido/agresivo deben contrastarse, no suponerse equivalentes.
- Picos: picos aislados frente a cadenas de dos o más; máximos decrecientes/mínimos crecientes; tolerancia al nivel, separación en barras/segundos, pullback intermedio y ruptura del último pico.
- Confirmación: comparar cierre de la propia barra de retest cuando ya es observable, confirmación posterior y recuperación del interior. Nunca inferir orden de high/low intrabar sin datos suficientes.
- Distancia y stops: buscar si la estructura reduce excursión adversa y deja recorrido favorable suficiente tras el precio ejecutable; la probabilidad geométrica O2 sola no responde esa pregunta.

Fuentes del repo:
- [liqpool.find_pivots](../../edgelab/bridge/indicators/liqpool.py): pivote en i disponible sólo al cierre de i+R; no anticiparlo en i ni sustituir toda la trayectoria por el cluster final.
- [peaks_rule histórico](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/tools/peaks_rule.py): `chains` confirma q=j-w; `series` devuelve segmentos finales y pertenencia retrospectiva. `backfill` extiende un segmento visual hacia atrás: esa fecha no es el nacimiento conocido de la señal.
- [Diseño de etiquetado de picos](https://github.com/Nicodelcampo/EdgeLab/blob/f397a318be8b0acf68789070fe8064d83e172f7d/docs/research/ETIQUETADO_PICOS_Y_ML_20260926.md): reconocer un patrón humano no prueba entradas rentables.
- `liqheat` detecta picos de densidad sobre el eje de precio, no los swings temporales de la vuelta. No intercambiarlos.

## Método y reproducción
Seis Parquets pinned, 544.531 filas totales; todas las celdas. Comparación real/pseudo separada, sin suponer controles certificados. Igual peso global por sesión, contrato dentro de sesión, ancla t0 dentro de contrato/sesión y filas dentro de ancla; duplicados retenidos compartiendo peso.
Entrenamiento sólo en fechas globales anteriores; una sesión de embargo; primer 40% para iniciar entrenamiento y tres bloques con el restante 60%. Sesiones de prueba disjuntas. Cada desenlace se evalúa sólo donde su etiqueta está resuelta; ausencias y dobles hits quedan en el ledger. Todos los contratos del mismo mercado comparten fechas: no tratarlos como réplicas independientes.
Historia ya inspeccionada: validación temporal INTERNA, no OOS ciego. Modelos univariados por quintiles o pares por terciles, sin búsqueda de hiperparámetros, reglas económicas ni optimización de cutoff. Actividad exportada ya está log-transformada; las transformaciones monotónicas adicionales de los univariados sólo ordenan grupos. Intensidad usa diferencia de logs originales de volumen/tiempo.
Los checks independientes de Brier (math.fsum) y AUC (pares en muestra acotada) se ejecutan dentro del cálculo. Hashes exactos y footers preholdout verificados antes de abrir el payload. El profiler genérico no soportó estos Parquets: validación nativa más proyecciones CSV verificadas, no una declaración de corrupción.
No se certifica calidad de fuente, censo causal ni snapshots as-of; no se despejan gates. No se mide P&L, fills, spread/slippage ni órdenes.

```bash
python tools/review_avzvol_indicator_screen.py --input-dir /ruta/privada/a/los/seis/exports --out /ruta/de/salida
```

Dependencias de investigación: numpy, pandas, pyarrow. El script sólo abre los seis nombres/hashes de export fijados en el plan; no carga ticks ni la reserva ciega.

[Plan y pins](avzvol_indicator_screen_20261011/analysis-plan.json) · [Evidencia](avzvol_indicator_screen_20261011/evidence.json) · [Resumen completo](avzvol_indicator_screen_20261011/summary-metrics.csv) · [Bloques](avzvol_indicator_screen_20261011/fold-metrics.csv) · [Contratos](avzvol_indicator_screen_20261011/contract-fold-metrics.csv) · [Todos los grupos y distancias](avzvol_indicator_screen_20261011/test-bucket-metrics.csv)

## Comprobaciones y limitaciones de entrega
5 tests de helpers y suite sintética existente: 818 tests +25 subtests. No son evidencia de rentabilidad. La publicación usa directamente los Parquets pinned: la reproducción conserva base/demora/rango/combinación a precisión inferior a 1e-12 en Brier. El roundtrip preliminar CSV alteró algunos empates de cocientes derivados (máxima diferencia Brier 0,0000200734); esos resultados preliminares no son los canónicos publicados.

El gráfico generado pasó preflight y la auditoría automática en 320/1200 px, claro/oscuro. El visor de imágenes falló: no se pudo completar la inspección visual y no se presenta el gráfico como revisado. Se conservan las tablas y el spec para reproducción.
