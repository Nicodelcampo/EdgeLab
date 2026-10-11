# AVZVOL: recorrido disponible y precio de entrada

## Resultado para decidir
**Mantener como prioridad una continuación temprana y selectiva, sin perseguir el precio.** El contexto rápido/rango-amplio mejora también el alcance en ticks fijos: no es sólo un objetivo más fácil en alturas de banda. Pero no está validada una entrada rentable y el precio al que se logra entrar puede consumir la ventaja.

## Recorrido desde el borde, no desde una operación
Misma población que la exploración anterior: ancla dentro, salida observada, O2 resuelto; tres bloques temporales internos ya inspeccionados. Rápida/amplia es el grupo 0:2 de los terciles aprendidos exclusivamente del pasado, reutilizados sin volver a ajustar. No es una nueva confirmación ni un filtro promovido.
La distancia es el máximo high/low observado desde el borde después de la barra de salida, hasta el primer cierre dentro o el fin acotado de ventana/sesión. Incluye el high/low de la barra que cierra dentro. No mide orden intrabar, fills, stops ni beneficio.

| Distancia fija | Todos los reales | Contexto favorable real | Contexto favorable control |
|---|---:|---:|---:|
| 5 ticks | 67.11% | 74.69% | 74.99% |
| 10 ticks | 41.55% | 51.31% | 50.54% |
| 20 ticks | 22.61% | 29.47% | 28.96% |
| 40 ticks | 12.27% | 16.24% | 15.27% |

La mejora es positiva en los tres bloques para cada distancia fija. El contexto favorable de los controles da resultados muy parecidos: no atribuir el efecto a una propiedad especial de las zonas. Los controles legacy todavía no están certificados como zone-free.

Cobertura ponderada del contexto favorable: 15.60%–17.93% de la población elegible por bloque. No es porcentaje de trades que se podrían llenar.

## Distancias relativas a la banda
h = H-L+1 ticks. El contexto favorable no asegura un recorrido de una banda.

| Máximo observado al menos | Todos los reales | Contexto favorable |
|---|---:|---:|
| 0.1h | 76.88% | 88.04% |
| 0.25h | 46.83% | 63.45% |
| 0.5h | 27.51% | 41.92% |
| 0.75h | 19.43% | 30.38% |
| 1h | 15.15% | 23.85% |
| 1.5h | 10.08% | 15.77% |
| 2h | 7.41% | 10.56% |

No elegir el objetivo de mayor porcentaje como “ganador”: reducir distancia naturalmente eleva alcance, pero no resuelve recorrido adverso ni costos. Por ejemplo, alcanzar 0,25h no equivale a ganar una entrada con target 0,25h.

## Sensibilidad al precio supuesto de entrada
**Ejemplo hipotético, no objetivo recomendado:** pedir 0,25h adicional después de una entrada posterior a la barra de salida. Si el precio de esa entrada estuviera más lejos del borde, el máximo registrado tendría que llegar a offset +0,25h.
Se usa el máximo de toda la ventana, que puede haber ocurrido ANTES de la entrada hipotética: por eso es una **cota optimista de cobertura geométrica**, no probabilidad de fill ni win-rate. El denominador son TODOS los casos del contexto favorable, incluso los que no cubren el avance supuesto hasta la entrada. No condicionar esta cifra como si fueran operaciones efectivamente llenadas. Tampoco se sabe si un stop habría sido tocado antes. La barra de salida queda excluida: no aplicar esta cota a entradas intrabar en esa barra.

| Precio supuesto de entrada más allá del borde | Fracción de todos los casos que cubre offset +0,25h |
|---|---:|
| 0h | 63.45% |
| 0.1h | 52.72% |
| 0.25h | 41.92% |
| 0.5h | 30.38% |
| 0.75h | 23.85% |

El descenso orienta a estudiar el precio ejecutable y el retardo antes de sumar más indicadores. No certifica que una entrada cercana al borde sea posible ni que esperar un retest conserve el recorrido.

## Variación temporal: ventaja de contexto sobre todos los reales
Brecha en puntos porcentuales de alcance, no retorno ni efecto causal.

| Bloque | 5 ticks | 10 ticks | 20 ticks | 40 ticks |
|---|---:|---:|---:|---:|
| 1 | +4.03 | +5.72 | +2.29 | +1.12 |
| 2 | +10.61 | +14.14 | +13.45 | +8.41 |
| 3 | +8.08 | +9.43 | +4.84 | +2.39 |

## Variación entre contratos
Los dos contratos antiguos sólo aparecen en entrenamiento; cuatro tienen prueba. Promedios de los bloques soportados, ponderaciones de sesión dentro de contrato, no réplicas independientes del mercado MNQ. Se conservan todas las filas/celdas, no sólo contratos favorables.

| Contrato | Sesiones favorables / anclas | Brecha a20 ticks |
|---|---|---:|
| MNQ_03-26 | 43 / 640 | +1.87 pp |
| MNQ_06-26 | 57 / 930 | +8.64 pp |
| MNQ_09-26 | 46 / 1280 | +4.37 pp |
| MNQ_12-26 | 10 / 215 | +4.02 pp |

MNQ_12-26 tiene sólo10 sesiones de prueba total en el estudio anterior: soporte pequeño, no una confirmación independiente. CSV completo retiene denominadores y todos los cortes.

## Lógicas concretas a contrastar, todavía hipótesis
1. **Ruptura con entrada posterior ejecutable y distancia limitada al borde:** contexto rápido/amplio conocido al finalizar la salida; medir el primer precio realmente ejecutable, no asumir compra/venta retrospectiva en el borde.
2. **Retest que evita perseguir:** distinguir retest superficial con compresión y rechazo fuera, retest agresivo, y recuperación del interior. No asumir que el mismo filtro anticipa el lado del rebote: las26 pruebas anteriores no mejoraron en promedio O3b.
3. **Vuelta y picos causales:** cadenas confirmadas, máximos decrecientes/mínimos crecientes, velocidad real de vuelta/salida y precio de confirmación; no usar un pico en su índice original antes de i+R ni un segmento final backfilled como señal al nacer.
4. **Comparación decisiva pendiente:** mismo trigger y regla de gestión, con/sin contexto, desde fills posibles y neto de costos, después de las autorizaciones y requisitos de fuente/método correspondientes. Este estudio no realiza esa comparación económica.
5. **Prioridad:** primero precio y retardo de entrada, luego estructura del retest; no añadir nuevos indicadores por acumularlos.

## Método, límites y reproducción
Seis exports con hash exacto, 544.531 filas evento×celda; no lecturas de ticks, reserva ciega ni nuevos desenlaces de precios. Sólo se agregan etiquetas de excursión existentes. Duplicados retenidos compartiendo peso por ancla.
Se reproducen todas las tasas O2 y tamaños de los nueve grupos publicados anteriormente; 1h reconstruido en ticks reproduce exactamente O2. Pesos contrastados con un contador independiente y numeradores con math.fsum. La reconstrucción mx_h ×h es entera a tolerancia numérica.
Media igual de tres tasas de bloque, no tasa pooled de filas. Los contratos usan pesos propios por sesión, no se suman como eventos independientes. Cada alcance usa el peso original restringido al grupo; no se reigualan sólo sus sesiones sobrevivientes.
O2 no resuelto excluido sólo para reproducir la población anterior y contado aparte. mx_h puede terminar por límite de ventana/sesión sin una vuelta completa; representa máximo OBSERVADO acotado, no trayectoria futura completa. No hay p-valores, significancia ni selección del mejor objetivo.
La fuente y geometría as-of siguen sin certificar, y no se despejan gates. Ausencia de timestamps/precio de entrada/trayectoria impide medir velocidad real de vuelta, picos y excursión adversa después del fill.
Profilado genérico de los Parquets no soportó su formato (ParserError): hashes/footers/perfil nativo y proyecciones CSV confirmados. La única advertencia CSV, contrato constante por archivo, es esperada. El cálculo canónico usa directamente Parquet, no las proyecciones.

```bash
python tools/review_avzvol_entry_distance.py --repo . --input-dir /ruta/privada/exports --out /ruta/salida --plan docs/research/avzvol_entry_distance_20261011/analysis-plan.json
```

[Plan](avzvol_entry_distance_20261011/analysis-plan.json) · [Evidencia](avzvol_entry_distance_20261011/evidence.json) · [Alcance completo](avzvol_entry_distance_20261011/reach-summary.csv) · [Por bloque](avzvol_entry_distance_20261011/reach-by-fold.csv) · [Por contrato](avzvol_entry_distance_20261011/reach-by-contract.csv) · [Todos los escenarios](avzvol_entry_distance_20261011/entry-offset-scenarios.csv) · [Estudio anterior](AVZVOL_INDICADORES_SALIDA_Y_ENTRADAS_20261011.md)

## Comprobaciones
4 pruebas aritméticas y suite sintética822 tests +25 subtests. Las brechas de alcance del contexto sobre todos los reales son positivas también en cada combinación contrato/bloque soportada, en todas las distancias declaradas (h y ticks); ello sigue siendo descripción de historia expuesta, no significancia ni rentabilidad.

El gráfico canónico pasó preflight estático, pero la herramienta nativa de adjuntos falló sin posibilidad de reintento. Se entregan tablas y se conserva el spec; no se declara una visualización inline publicada.
