# AVZVOL: salida y retest requieren contextos diferentes

## Resultado para continuar
**No trasladar automáticamente el filtro de continuación al retest.** Agregar rapidez al rango amplio aumentó alcance tras la salida en el estudio previo, pero REDUCE la fracción de barrera del lado de salida primero tras el retest en cada uno de los tres bloques. No son retornos económicos.
Demora larga+rango amplio merece una hipótesis separada por fase; no es un filtro promovido: el contrato más reciente contradice el patrón.

## Qué se observa realmente
O3a=1 significa que una mecha toca/atraviesa el borde de salida en una ventana acotada de hasta2.000 barras de la sesión. No exige rechazo, cierre favorable, ausencia de penetración ni fill. O3b empieza DESPUÉS de esa barra y compara barreras a+/-1h respecto del borde original. No describe beneficio desde una entrada.
Covariables rango/amplitud son antiguas de t0. Demora es te-t0 en barras de25 operaciones. **Salida demorada NO significa vuelta lenta:** no hay timestamp ni forma de vuelta disponible.
La población aquí conserva TODO pos=0 con salida observada, incluido O2 sin resolver. Las cifras no son exactamente la población anterior restringida a O2 resuelto. Mismos tres bloques y los terciles O2 aprendidos del pasado, aplicados sin refit al desenlace O3. Pesos originales del conjunto de salidas restringidos a cada condición; no reponderar sólo los retests resueltos.

## Retorno frecuente no significa oportunidad de rebote
Medias iguales de3 tasas por bloque; cada columna tiene su propio denominador.
| Condición | Cobertura de salidas | Retest observado / salidas | Lado de salida primero / retests resueltos |
|---|---:|---:|---:|
| Todos | 100.00% | 98.58% | 49.86% |
| Sólo salida rápida | 33.73% | 98.66% | 49.62% |
| Sólo rango amplio | 40.82% | 98.42% | 50.57% |
| Rápida + amplio | 16.96% | 98.73% | 48.95% |
| Demora media + amplio | 16.54% | 97.99% | 51.13% |
| Demora larga + amplio | 7.32% | 98.58% | 53.48% |

El retest observado es común en esta geometría y ventana; no confirma por sí solo una propiedad especial de las zonas. Tasas próximas a50% NO constituyen prueba de azar: no se ha definido ni contrastado un modelo nulo, y la geometría excluye barras y tiene censura.

## Se invierte el aporte de rapidez después del retest
| Bloque | Rango amplio | Rápida + amplio | Diferencia de rapidez | Demora larga + amplio |
|---|---:|---:|---:|---:|
| 1 | 50.88% | 50.33% | -0.55 pp | 55.33% |
| 2 | 50.40% | 46.53% | -3.87 pp | 53.53% |
| 3 | 50.44% | 50.00% | -0.43 pp | 51.57% |

Diferencia rápida+amplio versus amplio negativa en cada bloque, descriptiva y no causal. No se compara P&L entre las fases: alcance previo O2/mx_h y barrera posterior O3b son desenlaces distintos.

## Hipótesis de demora larga: conservar también la contradicción
| Contrato | Todos: lado primero | Demora larga + amplio | Sesiones / anclas en demora larga |
|---|---:|---:|---|
| MNQ_03-26 | 48.93% | 55.07% | 42 / 267 |
| MNQ_06-26 | 51.64% | 54.90% | 55 / 445 |
| MNQ_09-26 | 49.83% | 54.53% | 46 / 692 |
| MNQ_12-26 | 48.62% | 38.38% | 10 / 116 |

El último contrato tiene sólo10 sesiones de prueba y116 anclas del subgrupo; no son116 réplicas independientes ni suficiente confirmación. Su inversión impide describir el patrón como universal o presentar sólo los tres contratos favorables.

## Controles y desenlaces inciertos
| Condición | Real: lado primero / resueltos | Pseudo: lado primero / resueltos | Real: intervalo sobre TODOS los retests | Inciertos / retests reales |
|---|---:|---:|---|---:|
| Todos | 49.86% | 49.94% | 49.77%–49.95% | 0.182% |
| Sólo salida rápida | 49.62% | 49.71% | 49.50%–49.73% | 0.229% |
| Sólo rango amplio | 50.57% | 49.81% | 50.55%–50.59% | 0.045% |
| Rápida + amplio | 48.95% | 49.53% | 48.95%–48.95% | 0.000% |
| Demora media + amplio | 51.13% | 50.01% | 51.13%–51.13% | 0.000% |
| Demora larga + amplio | 53.48% | 49.99% | 53.33%–53.60% | 0.270% |

El intervalo asigna todos los -2 (ambas barreras en una barra posterior) y -1 (sin resolver) primero contra y luego a favor del lado de salida. Es una cota de identificación de etiqueta, NO intervalo de confianza ni resultado de stops. No-observado-retest se mantiene separado y NO se convierte en pérdida. Los controles legacy no están certificados zone-free ni emparejados causalmente.

## Qué cambia en la lógica de entradas
1. **Separar decisiones por fase:** rango+rapidez es candidato de contexto al salir, no dirección válida por defecto al retest.
2. **Retest con información nueva:** medir rechazo/penetración, recuperación dentro, compresión, distancia por vela y picos confirmados al momento de decisión. No usar covariables viejas como si describieran la vuelta.
3. **Contrastar demora larga+rango amplio sin promoverlo:** conservar controles, contrato adverso y soporte; no cambiar cortes tras ver estos resultados.
4. **No usar mx_h ni O2 como filtro causal pre-retest sin reconstrucción:** mx_h/O2 terminan al primer cierre dentro; O3a corresponde al primer TOUCH del borde. No son el mismo instante, y el máximo exportado puede incorporar recorrido posterior al primer touch.
5. Para decidir rentabilidad falta medir precios ejecutables, stop/target desde fill, orden intrabar, costos y comparación neta. No se han generado nuevos desenlaces de precios ni despejado autorizaciones/gates.

## Método y reproducción
Seis hashes/footers preholdout exactos antes de abrir etiquetas;544.531 filas fuente evento×celda. Identidades duplicadas conservadas compartiendo peso dentro del ancla. Perfil completo nativo anterior reutilizado con pins sin cambios; las12 columnas seleccionadas no tienen nulls y los códigos O3 están validados.
Dos caminos de pesos: groupby y Counter. Masas de cada uno de5 estados se contrastan dot versus math.fsum, y suman la población completa. Controles, todos los bloques y cuatro contratos test-soportados retenidos. Los dos contratos anteriores sólo soportan entrenamiento. No hay refit ni estadística inferencial; historia ya inspeccionada, no confirmación ciega.

```bash
python docs/research/avzvol_retest_phase_20261011/analyze.py --repo . --input-dir /ruta/privada/exports --out /ruta/salida
```

[Evidencia](avzvol_retest_phase_20261011/evidence.json) · [Todas las tasas](avzvol_retest_phase_20261011/phase-summary.csv) · [Bloques](avzvol_retest_phase_20261011/phase-by-fold.csv) · [Contratos](avzvol_retest_phase_20261011/phase-by-contract.csv) · [Diferencias](avzvol_retest_phase_20261011/phase-gaps.csv)
La capacidad nativa de adjuntar gráficos sigue bloqueada tras fallos no-reintentables; se entregan tablas y se conserva el plan de comparación, sin afirmar visualización publicada.
