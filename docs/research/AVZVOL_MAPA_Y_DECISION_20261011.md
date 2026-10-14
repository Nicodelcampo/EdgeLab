# AVZVOL: mapa candidato y decisión de continuidad

## Decisión principal

**Continuar con controles comparables y procedencia causal del censo; no invertir la siguiente etapa en buscar filtros que refuercen O5.** El defecto de la última barra existe, pero su exclusión apenas cambia la diferencia descriptiva: **-6.4807893% → -6.4803799%**, cambio de **0.000409390 puntos porcentuales**. No explica materialmente el patrón dentro de esta reconstrucción candidata.

Esto es información útil para priorizar, **no un efecto causal validado ni una señal operable**. El signo negativo describe menor razón geométrica post/pre en eventos reales frente a pseudo legacy, con las ponderaciones declaradas; no prueba menor volatilidad absoluta futura, ganancia o ventaja de las zonas frente a situaciones equivalentes.

## Qué se midió realmente

- Se reconstruyeron **19.238.855 barras candidatas** a partir exclusivamente de `ts_utc_ns` de seis archivos originales fijados por SHA y versión. No se leyeron precios para crear nuevos endpoints, no se volvió a ejecutar el detector ni el runner histórico.
- Los seis contadores de barras coinciden exactamente con los logs históricos. **544.531 anclas exportadas** coinciden en sesión y franja horaria; cero discrepancias. Es evidencia de alineación estructural, no atestación de lo consumido por la ejecución histórica.
- De **539.759 O5 finitos**, **539.732** tienen las 200 etiquetas posteriores dentro de la sesión candidata; **27** cruzan justo en la última barra: `te+199` dentro, `te+200` fuera. Son filas evento×celda, **no 27 episodios independientes**. Se excluyen 4 reales y 23 pseudo, **0.005002%** de los finitos.
- Los **4.772 O5 faltantes** permanecen acreditados en el universo original; no se imputan ni se convierten a cero.

| Contrato | Barras candidatas | O5 finitos dentro de sesión candidata | Cruces última barra |
|---|---:|---:|---:|
| MNQ_03-26 | 4,132,082 | 93,196 | 5 |
| MNQ_06-26 | 4,595,341 | 102,851 | 6 |
| MNQ_09-25 | 1,340,185 | 55,850 | 2 |
| MNQ_09-26 | 4,392,969 | 147,320 | 9 |
| MNQ_12-25 | 3,923,675 | 106,060 | 4 |
| MNQ_12-26 | 854,603 | 34,455 | 1 |

## Sensibilidad acotada de O5 ya expuesto

La receta conserva las **31 celdas comunes y seis contratos**. Calcula media real menos media pseudo dentro de contrato/sesión/celda; luego igual peso por sesión soportada, celda y contrato. Conserva las repeticiones pseudo existentes. La exclusión se decide por etiquetas temporales, no por magnitud o signo de O5.

| Comparación | Gap log | Gap geométrico relativo |
|---|---:|---:|
| Original | -0.067003308611 | -6.4807893% |
| Sin 27 cruces candidatos | -0.066998931014 | -6.4803799% |
| Original sobre exactamente los grupos soportados restantes | -0.067003308611 | -6.4807893% |

**Cero grupos de sesión/celda soportados perdidos y cero cambios de signo por celda.** Permanecen 30 celdas negativas y una positiva. La excepción `8_1000_30` se mantiene: **+2,8600% → +2,8763%**; no se elimina. La mayor variación absoluta entre celdas es 0,032555157 puntos porcentuales. No se calcularon intervalos, p-valores, potencia ni independencia entre observaciones.

Máscara de ventana contrastada con las 200 etiquetas por cada salida/sesión única. Los tres titulares numéricos se recomputaron por una vía independiente de listas y `math.fsum`: diferencia máxima 0 dentro de la precisión de cálculo. Evidencia por celda, sin recortes al resultado favorable, en el JSON de sensibilidad.

## Qué pasó con los faltantes de etiquetas y el horario de verano

La auditoría anterior encontró **cero ventanas completas anotadas en el export de eventos**. Eso sigue siendo correcto: no era un mapa de todas las barras y no demostraba que todas las ventanas originales estuvieran rotas. El nuevo mapa completo resuelve ese desconocimiento **condicionado a la receta y fuentes candidatas**, no certifica las fuentes.

En MNQ_03-26, el inicio mínimo cae después del cambio de horario de otoño: restar un día de duración fija a medianoche deja la grilla a las 01:00 y el cierre legacy a las 17:00 en lugar de las 16:00 CT. Se preservó esta peculiaridad, sin corregirla para mejorar el resultado. Se contrastaron las etiquetas de **todas las barras candidatas** contra una referencia ordinaria de días hábiles con cierre a las 16:00 CT: **cero etiquetas de fecha distintas en los seis contratos**. La pausa histórica 16–17 CT evita que ese desfase cambie aquí la fecha asignada. La prueba inventada de un timestamp durante la pausa sí muestra la diferencia; no es un evento observado. La referencia no incorpora feriados CME ni certifica reloj, calendario, ventanas de precios o paridad del detector.

## En qué conviene invertir ahora: las cuatro propuestas

1. **P1 — procedencia y calidad:** mantener abiertos reloj, calendario, continuidad, liquidez, selección D-1 y prueba del montaje/consumo histórico. Para la siguiente medición, acreditar también el inicio exacto de la preventana. El export `h` es altura, no el índice de inicio; no reconstruir ese inicio ajustándolo al valor observado de O5.
2. **P2 — prioridad analítica:** construir y revisar el censo as-of, con controles realmente sin zona y comparables dentro del mismo contrato/sesión, además del benchmark del censo propio de los controles. Fijar covariables previas, reglas, escalas, calipers, soporte y balance **antes** de nuevos resultados. Hoy no se ha demostrado que los pseudo legacy cumplan esto. Esta es la prueba que puede separar información incremental de selección/composición del censo.
3. **P3 — después de esa preparación:** contrastar el horizonte en barras con tiempo de reloj, declarar censura de salidas y horizontes, dependencia por episodio/sesión, familia e inferencia. Dos cientos barras no son una duración fija. No usar la completitud futura como filtro causal conocido al ancla.
4. **P4 — económicos:** permanece prohibida hasta nueva autorización explícita. No P&L, estrategias ni holdout en esta etapa.

**Criterio de continuidad:** si el gap persiste con controles balanceados y reglas congeladas, habrá razón para estudiar las zonas como información incremental. Si desaparece o se explica por el censo propio del control, priorizar consolidación/contexto y dejar de atribuirlo a la zona. No se puede decidir cuál ocurrió con este contraste legacy. La replicación independiente sigue siendo prerrequisito; contratos MNQ/NQ del mismo subyacente no son mercados independientes.

## Qué no queda autorizado ni certificado

No nuevos outcomes de precios, ni económicos, ni acceso al holdout. No validación causal, preventana verificada, calendarización de mercado certificada, cierre de gates o edición de outputs originales. No búsqueda de filtros por signo/tamaño del efecto. Alinear barras y comprobar estabilidad ante un defecto puntual no resuelve todos los otros sesgos.

## Evidencia y reproducción

- [Mapa candidato agregado](../../config/research/avzvol_candidate_bar_map_qa_20261011.json); SHA `2f8ccd6fba94e510d48a686caacfc725c8f5c124cc5a3fa63b53da9c2db281bc`. Se publica byte a byte la evidencia suplementada, no los mapas NPZ privados ni timestamps por evento.
- [Sensibilidad completa por celda](../../config/research/avzvol_candidate_boundary_sensitivity_20261011.json). Todos los pins de mapas y exports se verifican antes de leer magnitudes de O5.
- [Receta timestamp-only](../../tools/reconstruct_avzvol_candidate_bar_map.py), opt-in `--allow-timestamp-structural-qa`: requiere inventarios privados, resolver y fuentes históricas fijadas, logs e output nuevo. Fuentes históricas fijadas en commit `4e1e26930f9778f974a4dd4946977ac48b1725d8`; sus SHA figuran en la evidencia.
- La corrida inicial precedió al chequeo suplementario. Éste lee los NPZ verificados, calcula `reference_weekday_close_labels(end_ns)` contra `session` y verifica para cada export finito `te>t0`, `te<len(session)` y `session[te]==session_export`; no vuelve a leer precios. Sus contadores se guardan en `files` y el hash de la receta está en `candidate_recipe_sha256`. La CLI timestamp-only incluye ahora la comparación de referencia; las salidas finitas se revalidan obligatoriamente en la receta de sensibilidad.
- [Receta de sensibilidad](../../tools/review_avzvol_candidate_boundary_effect.py): `--map-evidence`, su SHA exacto, `--map-dir`, `--export-inventory`, `--out-dir` nuevo y opt-in `--allow-exposed-o5-review`. Falla sin alineación/pins; jamás reemplaza resultados originales.
- [Robustez anterior](AVZVOL_O5_ROBUSTNESS_20261010.md), [auditoría sparse anterior](AVZVOL_FILTROS_Y_VENTANAS_20261011.md): conclusiones históricas conservadas, sin reinterpretarlas como censo causal.
