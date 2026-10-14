# AVZVOL: comparabilidad real de los controles existentes

## Resultado para decidir el siguiente paso

**Los controles legacy permiten una comparación descriptiva, pero aún no una prueba limpia de información incremental de las zonas.** Ahora hay evidencia observada, no sólo un riesgo de código:

1. **412 filas pseudo** también aparecen como anclas de racimos reales exportados, con el mismo contrato, sesión, celda y `t0`. Los grupos positivos y pseudo no son exclusivos. Es un mínimo de coincidencias positivas observadas, **no una medición completa de contaminación ni una clasificación negativa/as-of del detector**.
2. Exigir contexto exacto deja soporte para **81.1514% de las filas reales** y **41.7939% de las pseudo**. La población cambia sustancialmente; no extrapolar al universo original ni presentar el contraste restringido como mejorado causalmente.
3. Aun después de igualar el peso de contrato/sesión/celda/horario/signo de tendencia, queda diferencia en actividad previa de corto plazo: **SMD +0,1203** en log volumen de 100 barras. En MNQ_06-26 es +0,2026 y MNQ_12-26 +0,2162. No se afirma que eso explique el gap direccional ni se declara una aceptación/rechazo numérico sin umbral aprobado.

**Decisión:** no recalcular aquí un efecto supuestamente corregido. Priorizar censo as-of zone-free y controles propios de consolidación; documentar soporte, procedencia y balance antes de abrir nuevos desenlaces. No elegir calipers mirando lo que agranda el resultado.

## Qué se hizo sin leer outcomes

Se verificaron SHA/schema/filas/footers de los seis exports y SHA de los seis mapas candidatos antes del payload. Sólo se leyeron identificadores, `t0` y nueve covariables previas. **No se leyeron `te`, `dir`, O2, O3, O4, O5 o excursión máxima**, ni precios crudos. Los resultados posteriores ya habían sido expuestos en trabajos anteriores: esta revisión no es confirmación ciega, aunque su receta no los usa para elegir filas o pesos.

Todos los exports tienen las nueve covariables finitas: **cero filas imputadas o excluidas por falta de covariable**. Eso no prueba que sus ventanas/calibración/fuentes fueran correctas.

## Soporte: qué población se puede comparar

Estrato exacto: **contrato × sesión × celda × franja horaria × signo de tendencia**. No matching por vecino/caliper ni reconstrucción de parejas originales.

| Grupo | Filas originales | Filas en estratos compartidos, todas las celdas | Cobertura | Filas del panel común de 30 celdas |
|---|---:|---:|---:|---:|
| Reales | 96,755 | 78,518 | 81.1514% | 78,476 |
| Pseudo | 447,776 | 187,143 | 41.7939% | 187,094 |

191.057 estratos observados: **44.434 compartidos**, 15.353 sólo reales y 131.270 sólo pseudo. Se conservan en contabilidad **18.237 filas reales y 260.633 pseudo sin soporte exacto**. El panel de balance usa 30 celdas comunes en los seis contratos, 78.476 reales y 187.094 pseudo: **265.570 filas**, no eventos independientes ni parejas 1:1. Las 36 definiciones originales se conservan; las seis fuera del panel no se eliminan por signo de efecto, que no se leyó.

Peso de cada tipo: igual peso a seis contratos, celdas comunes, sesiones soportadas de contrato/celda, estratos horario/tendencia soportados de la sesión, y finalmente filas del tipo en ese estrato. Suma de pesos=1 para real y pseudo. Duplicados/reutilización pseudo conservados, no se convierten en observaciones independientes.

## Balance: el promedio no sustituye comparabilidad completa

SMD = diferencia de medias real−pseudo / raíz de la media de sus varianzas poblacionales, calculadas con los mismos pesos. La columna sin reponderación usa **exactamente las mismas filas del panel**, no el universo completo. Valores en unidades estandarizadas, no probabilidades o porcentajes. Si ambas varianzas son cero y las medias distintas, el SMD queda desconocido, no infinito ni cero artificial.

| Covariable | SMD mismas filas sin reponderar | SMD reponderado |
|---|---:|---:|
| `occ` — Ocupación de banda | +0.0498 | +0.0473 |
| `h` — Altura de banda | -0.0848 | -0.0114 |
| `amp` — Rango previo de 200 barras | -0.0413 | -0.0578 |
| `trend_h` — Tendencia previa / altura | +0.0408 | +0.0188 |
| `mom100_h` — Momentum de 100 barras / altura | +0.0124 | -0.0022 |
| `vol_occ` — Log volumen previo, 500 barras | +0.2064 | +0.0643 |
| `vol_100` — Log volumen previo, 100 barras | +0.2480 | +0.1203 |
| `dur_occ` — Log duración previa, 500 barras | +0.2223 | +0.0037 |
| `dur_100` — Log duración previa, 100 barras | +0.1876 | +0.0011 |

El mayor residual absoluto agregado es `vol_100`, +0,1203. Por contrato se conservan los nueve resultados: además de los extremos positivos de actividad citados, MNQ_03-26 tiene `amp` −0,1176 y MNQ_09-26 `mom100_h` −0,0821. La diferencia agregada pequeña de duración/momentum puede ocultar diferencias por contrato. [Tabla completa de todas las covariables y contratos](avzvol_control_comparability_20261011/balance_all_features.csv).

Esto sólo contrasta medias y varianzas. No demuestra distribución/tails equivalentes, superposición geométrica local, fuentes causales, ausencia de racimos en pseudo, tolerancias de aceptación o intercambiabilidad. La altura de la banda pseudo proviene del real en el método legacy; balance de `h` no acredita un censo independiente de consolidaciones.

## Coincidencias positivas observadas: no equivalen a negativo certificado

- 412/447.776 pseudo filas (**0.092010%**) coinciden con ancla real en la misma celda; corresponden a **409 claves distintas contrato/sesión/celda/t0**, no episodios independientes. Se verificó el conteo por sets y por MultiIndex de forma independiente.
- 1.407 pseudo filas coinciden con un ancla real en alguna celda; esta cifra incluye las 412 y **no se suma** a ellas.
- No se quitaron esas filas para recalcular un efecto. Su frecuencia baja no explica automáticamente el patrón, y tampoco acredita que el resto esté libre de zonas/racimos. Los exports positivos no contienen todas las decisiones negativas, calibración, warmup o disponibilidad por bloque.
- Tampoco se atribuye a estos anclajes un estado causal conocido al ancla: los eventos provienen del export legacy y sigue pendiente revisar snapshots/as-of y formación entre sesiones.

## Ventanas previas: revisión estructural, no filtro aplicado

Con el mapa timestamp-only candidato ya fijado, se comprobó si el índice histórico de cada feature cae dentro de la misma etiqueta de sesión que el ancla; las etiquetas son monótonas. No se modificó ninguna covariable:

| Historia candidata | Filas reales que cruzan sesión | Filas pseudo que cruzan sesión |
|---|---:|---:|
| 501 barras inclusivas para tendencia de 500 diferencias | 403 | 1345 |
| 101 barras inclusivas para momentum de 100 diferencias | 83 | 265 |

Cero índices insuficientes para esa historia máxima. También se conservan contadores de ventanas inclusivas de 500 y 100 barras para ocupación/actividad. **Cruzar sesión no demuestra por sí mismo un error:** el protocolo debe decidir si permite arrastre de historia. Tampoco estar dentro de la etiqueta candidata acredita calendario CME, reloj, continuidad, liquidez ni la preventana O5, cuyo inicio no está en el export. No se filtra por horizonte futuro.

## Qué habilitaría la siguiente medición

1. **P1:** procedencia y calidad independiente, calibración/warmup y consumo histórico; política de ventana previa y formación entre sesiones revisada.
2. **P2:** cinta completa de decisiones as-of, distinguiendo positivo/negativo/desconocido; censo propio de consolidaciones de controles. Acreditar ausencia de zona o de racimo según una definición revisada: no son sinónimos. Reemplazar el supuesto negativo por una etiqueta demostrable; UNKNOWN no es negativo.
3. Fijar reglas de soporte, covariables, escalas/calipers, reutilización y balance **sin elegirlos para mejorar los outcomes**; registrar los no soportados y el universo al que se refiere el contraste.
4. Sólo tras esa preparación y exposición/permisos revisados, calcular efectos no económicos congelados, dirección y continuación por separado, y benchmark del censo propio de controles. P3 reloj/censura/familia sigue pendiente. P4 económicos y holdout prohibidos.

Los `null` y flags de aprobación científica existentes se conservan: esta pieza no crea certificados ni desbloquea una campaña. Pasar pruebas de software no concede validación causal.

## Evidencia y reproducción

[Plan](avzvol_control_comparability_20261011/analysis-plan.json), [evidencia completa](avzvol_control_comparability_20261011/evidence.json), [receta opt-in](../../tools/review_avzvol_control_comparability.py), [dirección/continuación anterior](AVZVOL_DIRECCION_Y_CONTINUACION_20261011.md).

CLI: `--inventory`, `--map-evidence`, su `--map-evidence-sha256`, `--map-dir`, `--out-dir` nuevo y `--allow-exposed-covariate-review`. Mapa SHA `2f8ccd6fba94e510d48a686caacfc725c8f5c124cc5a3fa63b53da9c2db281bc`; auditoría export SHA `1611277b3dc6f6393e0c6f280201359f488b8352e80a23bf9c77149e8152192e`. Contadores de soporte, medias/varianzas y overlap recomprobados independientemente. Medias por vector y por listas/`math.fsum`; no imports del runner histórico.

El plan de datos se fijó antes del payload. La revisión por contrato amplía el diagnóstico de balance tras ver el agregado, sin abrir outcomes ni elegir umbrales. La evidencia pública añade tasas de cobertura aritméticas y hash de receta al objeto de resultados, sin cambiar los contadores/medias originales. No se publican mapas privados ni filas de mercado. El adjunto de gráficos al chat sigue sin devolver un archivo válido; se mantiene la tabla/CSV en lugar de inventar URI.
