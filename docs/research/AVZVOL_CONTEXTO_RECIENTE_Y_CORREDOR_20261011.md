# AVZVOL: dirección reciente dentro del contexto de recorrido

## Resultado y alcance real de esta prueba
La combinación rápida+amplia con tendencia larga a favor de la salida y momentum corto en contra presenta mayor alcance medio, pero se INVIERTE en los dos contratos más recientes. Es una hipótesis dependiente de régimen, no un filtro listo para operar.
Esto prueba una interacción de signos en exports, **NO memoria espacial del corredor**. Los signos son anteriores y fueron muestreados en t0: tendencia500 barras y momentum100 barras. No fueron actualizados al salir. La dirección de salida sólo puede usarse después de completar la salida, nunca como feature del ancla inicial.
El contexto rápido/amplio está reutilizado del estudio anterior. Luego de observar que MIXED agrupado daba más alcance, se separaron sus dos mecanismos antes de consultar sus etiquetas específicas; esta ampliación es post-exposición, no preregistrada ni ciega.

## Dentro de rápida + rango amplio: los conflictos no son equivalentes
Medias iguales de3 tasas de bloques ya inspeccionados, pesos globales restringidos al grupo; tasas de alcance, NO trades ni beneficios.
| Contexto original | Real: alcanza20 ticks | Pseudo: alcanza20 ticks | Cobertura de TODAS las salidas reales elegibles |
|---|---:|---:|---:|
| Sin filtro direccional extra | 29.47% | 28.96% | 16.97% |
| Ambos a favor | 27.17% | 28.42% | 6.43% |
| Ambos en contra | 28.86% | 29.95% | 3.20% |
| Corto a favor / largo en contra | 26.17% | 27.80% | 3.27% |
| Corto en contra / largo a favor | 35.63% | 30.20% | 3.75% |
| Alguno neutro | 30.88% | 28.13% | 0.32% |

La cobertura de la pista es pequeña: no es frecuencia de fills. Alguno-neutro no se presenta como ganador: sólo11/20/27 anclas y9/16/19 sesiones por bloque dentro de este contexto. MIXED parent y sus hijos no son grupos aditivos entre sí.

## Variación temporal: no ocultar el bloque débil
| Bloque | Sin filtro extra | Corto en contra / largo a favor | Corto a favor / largo en contra |
|---|---:|---:|---:|
| 1 | 25.18% | 30.93% | 23.12% |
| 2 | 37.06% | 48.73% | 24.60% |
| 3 | 26.17% | 27.22% | 30.81% |

La pista supera el conjunto favorable a20 ticks en los3bloques, pero no en todas las combinaciones de distancia/bloque. A10ticks en el bloque3 es prácticamente igual: brecha−0,03pp. La mejora global no implica transferencia a cada contrato.

## Contratos: inversión importante
| Contrato | Sin filtro extra | Corto en contra / largo a favor | Corto a favor / largo en contra | Sesiones / anclas de la pista |
|---|---:|---:|---:|---|
| MNQ_03-26 | 23.82% | 29.25% | 24.09% | 38 / 136 |
| MNQ_06-26 | 34.01% | 44.39% | 21.43% | 53 / 198 |
| MNQ_09-26 | 29.26% | 27.04% | 35.05% | 46 / 269 |
| MNQ_12-26 | 24.21% | 16.54% | 44.71% | 9 / 51 |

MNQ_09-26 contradice el candidato con46sesiones/269anclas; no reducir toda la contradicción a la muestra pequeña del último contrato. MNQ_12-26 tiene9sesiones/51anclas del candidato. El conflicto inverso resulta más alto en los dos contratos recientes; no cambiar retrospectivamente de regla por contrato.

## Distancias: conservar todos los objetivos fijados
| Objetivo desde borde | Sin filtro extra | Corto en contra / largo a favor | Corto a favor / largo en contra |
|---|---:|---:|---:|
| 5 ticks | 74.69% | 77.63% | 74.85% |
| 10 ticks | 51.31% | 55.04% | 47.05% |
| 20 ticks | 29.47% | 35.63% | 26.17% |
| 40 ticks | 16.24% | 22.80% | 12.15% |
| 0.1h | 88.04% | 89.64% | 89.86% |
| 0.25h | 63.45% | 66.86% | 62.46% |
| 0.5h | 41.92% | 47.98% | 39.23% |
| 0.75h | 30.38% | 36.81% | 27.35% |
| 1h | 23.85% | 30.79% | 22.35% |
| 1.5h | 15.77% | 19.32% | 15.18% |
| 2h | 10.56% | 11.20% | 11.05% |

No escoger el objetivo con mayor porcentaje como optimización: objetivos más cercanos producen más alcance por construcción. La excursión mx_h excluye barra de salida, termina al primer cierre dentro o límite de ventana/sesión y puede incluir precios posteriores al primer toque de retest. No es recorrido desde un fill.

## Conservar el contexto general, no sólo el rincón favorable
| Población real | Sin filtro extra:20ticks | Corto en contra / largo a favor | Corto a favor / largo en contra |
|---|---:|---:|---:|
| all | 22.61% | 25.91% | 22.36% |
| wide | 26.30% | 30.68% | 28.16% |
| fast_wide | 29.47% | 35.63% | 26.17% |

El conflicto inverso también cambia su asociación entre wide y fast_wide: no se describe un mecanismo universal. CSVs preservan controles,7contextos (incluye padre),3políticas, todas las distancias, bloques y contratos.

## Después del retest: otro desenlace
| Contexto en rápida+amplia | Real: lado de salida primero / retests resueltos | Pseudo |
|---|---:|---:|
| Sin filtro direccional extra | 48.95% | 49.53% |
| Ambos a favor | 45.53% | 49.42% |
| Ambos en contra | 53.47% | 49.59% |
| Corto a favor / largo en contra | 49.02% | 49.81% |
| Corto en contra / largo a favor | 49.26% | 49.38% |
| Alguno neutro | 59.68% | 49.01% |

La pista de mayor alcance previo no muestra un salto equivalente en dirección posterior al retest. No comparar estas tasas con alcance20ticks como si fueran la misma población o dos trades. CSV retiene bounds con todos los retests ambiguos/no resueltos; cotas de identificación, no CI. El neutro es de soporte escaso, también aquí.

## Qué investigación concreta sigue
Dos hipótesis rivales, NO patrones ya confirmados por trayectoria:
1. **Continuación tras corrección:** salida en dirección del signo largo, momentum corto previo contrario. Para comprobarlo falta ver si hubo un retroceso real, cómo fue el último recorrido a favor y qué obstáculos quedan delante.
2. **Cambio local de dirección:** momentum corto a favor, signo largo contrario. Para comprobarlo falta ver rechazo previo, recuperación/aceptación de niveles y pivotes disponibles al momento de decidir.
3. **Memoria del corredor:** definir desde la referencia disponible al decidir (no desde máximo futuro) el corredor y medir en datos ANTERIORES: eficiencia de último tránsito, tiempo/visitas por precio, cruces, rechazo/penetración y distancia al siguiente pivote confirmado. Poca o mucha permanencia no garantiza por sí sola continuación o reversión.
4. **Comparación incremental:** mismas situaciones, misma referencia y mismos desenlaces; base contexto frente a base+memoria. Separar decisiones salida/retest, actualizar covariables al trigger y conservar oportunidades omitidas. No añadir una regla económica ahora.
5. Reloj/trayectoria y geometría as-of siguen faltando. Este test no mide esas features, no aprueba el censo de fuentes/controles ni abre P&L/reserva ciega.

## Verificación y reproducción
Seis Parquets exactos,544.531 filas evento×celda; mismos3bloques previos. Hashes y footers preholdout verificados antes de etiquetas.16columnas sin nulls, reconstrucción entera de excursión validada; pesos groupby contrastados con Counter y numeradores con math.fsum. Las tasas originales ALL y rápida/amplia se reproducen a1e-12.
Se conservan duplicados compartiendo peso dentro del ancla. Los4estados originales suman el total; los2hijos suman MIXED. Los padres e hijos son análisis anidados, no réplicas independientes. Historia expuesta y selección exploratoria: no inferencia formal ni una estrategia confirmada.

```bash
python docs/research/avzvol_recent_interaction_20261011/analyze.py --repo . --input-dir /ruta/privada/exports --out /ruta/salida
```

[Evidencia](avzvol_recent_interaction_20261011/evidence.json) · [Resumen completo](avzvol_recent_interaction_20261011/reach-summary.csv) · [Bloques](avzvol_recent_interaction_20261011/reach-by-fold.csv) · [Contratos](avzvol_recent_interaction_20261011/reach-by-contract.csv) · [Soporte](avzvol_recent_interaction_20261011/context-support.csv) · [Retest](avzvol_recent_interaction_20261011/retest-by-fold.csv)
