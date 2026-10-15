# Adenda D al manifiesto de la Pasada 3 — fase de desarrollo: filtros para multiplicar el efecto bruto de `HA`/`HB`

Estado: **BORRADOR PARA OK DE NICO. NO EJECUTAR.** Es una búsqueda sobre retornos: aplica el STOP de `CLAUDE.md`.
Fecha: 2026-10-15 · Depende de `MANIFIESTO_PASADA3_CONFIRMATORIA_CORREDOR_20261015.md` (respuestas 1–3 de Nico: **sí**: confirmación en NQ/YM con ES histórico como desarrollo y regresión; `HA` como primaria sin cambios; `HB` exploratoria).
Referente rector: `docs/NORTH_STAR.md` (sha256 del cuerpo declarado `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`; el auditor de gobernanza debe recomputarlo).

## 0. Idea en seis líneas
1. Nico quiere aplicar **todas las herramientas posibles** para filtrar y afinar la precisión de `HA` (y `HB`), bajo la hipótesis de que hay un efecto bruto que se puede multiplicar.
2. Se puede, **sin romper la confirmación**, porque ES (299 sesiones) ya está quemado para confirmar: pasa a ser el **conjunto de desarrollo**. NQ y YM quedan **sellados**; no se tocan hasta congelar el filtro.
3. "Todas las herramientas" es válido sólo si el **pipeline completo** se juzga contra su propio nulo: se baraja la etiqueta por bloques de sesión y se repite todo el proceso de selección; la mejora real debe superar lo que el pipeline "encuentra" en datos sin señal.
4. El criterio es **neto de fricción**, no sólo acierto. Filtrar reduce N: se exige retención mínima para no perder potencia.
5. La simplicidad es un a priori: se prefieren reglas de ≤ 3 variables y se reporta cuánta mejora aporta la primera.
6. Resultado válido incluido: **"ningún filtro mejora"**. Entonces `HA` se confirma tal cual en NQ/YM o se descarta.

## 1. Justificación económica
Si el regreso al borde exterior tiene un efecto bruto pequeño y heterogéneo, el contexto (cuánto volumen hay entre el precio y `orig_px`, cómo regresó el precio, a qué hora, con qué volatilidad) puede separar los casos donde "el vacío de liquidez" existe de los casos donde el borde defiende. Un filtro que aísla ese subconjunto sube la tasa de acierto en la proporción en que la heterogeneidad es real; si es ruido, no sube fuera de muestra.

## 2. Cómo podría refutarse
- R1. La mejora de `E` (expectativa neta por operación) en validación anidada por sesión no es distinta de cero con IC clusterizado.
- R2. La mejora no supera el nulo del pipeline (permutación por bloques de sesión; p ≥ 0,05).
- R3. La mejora desaparece en la mitad cronológica final o en ≥ 2 de los 6 contratos.
- R4. El filtro retiene < 30 % de los eventos (queda sin potencia para confirmar).
Si ocurre R1 o R2, **no se construye filtro** y se mantiene `HA` sin cambios.

## 3. Datos y aislamiento
- **Desarrollo:** ES, 299 sesiones `SELECTED`, `trade_date < 2026-10-01`, resolución 100T (`HA`) y 500T (`HB`). Ya fue usado para seleccionar: sirve para desarrollar, no para confirmar.
- **Sellados:** NQ, YM (confirmación), ES `≥ 2026-10-01` (holdout). **Prohibido** abrirlos en esta fase, ni para ver conteos de retornos.
- Cualquier decisión (variable, umbral, modelo) se toma sólo con ES y se registra en un ledger con sello temporal antes de la validación final.
- Limitación P-28: ninguna variable depende del orden de ticks con igual timestamp.

## 4. Población y etiqueta
Los de `HA` y `HB` de la Pasada 3 (§4–§6 del manifiesto): entradas ≥ `cls_b + 1`, RTH, `no_overlap`, sin cruce de sesión, empates a la parada, fills límite con trade-through. La etiqueta binaria es la carrera de barreras y se guardan además exceso favorable/adverso y tiempo hasta resolución (para el canal no direccional).
Población de desarrollo alternativa **declarada y no usada**: todos los regresos (no sólo `STEEP_SLOPE`); sirve para ver si la pendiente empinada ya es un filtro de este mismo conjunto y se reporta como contraste, no como búsqueda adicional.

## 5. Familias de información candidatas (todas calculadas con datos ≤ instante de entrada τ)
1. **Geometría de la zona:** altura (ticks y ATR), duración, pendiente, `StabilityScore` y sus cuatro pilares, barras fuera del borde antes de volver, antigüedad desde el cierre, nº de retests previos.
2. **Perfil de volumen:** volumen del sector (último 25 % + 25 % más allá) y su percentil frente a las 50 zonas previas (la variante `EmaCorridorTrendVol`), POC, borde del área de valor y barra de máximo volumen (`tools/corridor_anchors.py`), distancia del precio a cada ancla, volumen acumulado entre el precio y `orig_px` (vacío de liquidez), distancia al nodo de alto volumen más cercano.
3. **Forma del regreso:** velocidad y aceleración del retroceso, rango y cuerpo de la barra de reingreso, nº de barras de regreso, profundidad de la penetración al cierre, tiempo y volumen consumido en el regreso.
4. **Flujo:** desbalance de agresión **sólo si el dato lo permite y está verificado** (hoy `side` no se asume; si no se verifica, se omite); tasa de ticks y tamaño medio de operación.
5. **Contexto de mercado:** hora (cíclica), RTH/ETH, volatilidad realizada frente a ATR, rango de sesión hasta τ, distancia a máximos/mínimos de sesión y del día previo, alineación con la EMA macro, gap de apertura.
6. **Contexto de calendario:** día de la semana y mes **no** se incluyen (riesgo alto de ajuste espurio); si el auditor los pide, se declaran aparte.
**Fuera de alcance (regla de independencia de familias):** cruces con BigTrap2, aVolCluster, HFTZones, LUX-IMB. Una confluencia se registra como familia nueva y no entra acá.

## 6. Herramientas (de simple a compleja; se corren todas, se elige la más simple que no sea peor)
| # | Herramienta | Qué produce |
|---|---|---|
| T1 | **Filtros univariados** con umbrales por cuantil (terciles) fijados *dentro* de cada pliegue de entrenamiento | La mejor variable simple y su gradiente (monotonía) |
| T2 | **Regresión logística regularizada (elastic net)**, variables estandarizadas con estadísticos del pliegue de entrenamiento | Combinación lineal sobria y coeficientes |
| T3 | **Árbol de decisión de profundidad ≤ 3** | Reglas legibles (por ejemplo "A y B pero no C") |
| T4 | **Gradient boosting (LightGBM)** poco profundo, restricciones de monotonía donde la economía lo justifique, parada temprana por validación interna | Techo de información no lineal |
| T5 | **Abstención calibrada**: probabilidad calibrada (isotónica/Platt en un tramo de calibración por sesión) y umbral de acción sólo si `P·D − (1−P)·D − F_ES > 0` con cobertura conformal | Regla de operar/abstenerse con garantía de cobertura |
| T6 | **Modelo de mapa de calor** de la ventana multiescala (red pequeña) | **No en esta adenda**: se activa sólo si T4 muestra señal y el N lo permite (queda para la etapa 2 de la propuesta del modelo de reversión) |
Regla de elección: gana la herramienta **más simple** cuyo rendimiento OOS esté a ≤ 1 error estándar de la mejor (regla 1-SE); si T1 con una variable alcanza, se queda en T1.

## 7. Protocolo de validación
- **Validación anidada por sesión:** externa = walk-forward expansivo en bloques cronológicos de sesiones (≥ 5 pliegues) con **purga y embargo** de al menos un horizonte máximo y una sesión; interna = validación por sesión para umbrales e hiperparámetros.
- Sólo se evalúa en cada pliegue externo una vez; nada se ajusta con datos de ese pliegue.
- **Métricas:** `ΔE` = diferencia de expectativa neta por operación y por sesión contra `HA` sin filtro (mismos pliegues), tasa de acierto, retención de eventos, calibración (Brier/curva), no direccional (distribución de excesos y tiempos).
- **Nulo del pipeline (reality check):** ≥ 1.000 repeticiones barajando la etiqueta por bloques de sesión (preserva autocorrelación intradía), corriendo **todo** el pipeline (T1–T5, selección incluida) y registrando la mejor `ΔE` obtenida; el `p` del pipeline es la fracción de nulos con `ΔE` ≥ la observada. Esto internaliza el número de variables y herramientas probadas.
- **Estabilidad:** `ΔE > 0` en ≥ 4 de 5 pliegues, en la segunda mitad cronológica y en ≥ 4 de 6 contratos; espejo largo/corto; sensibilidad a −1 tick y a fricción alta/baja de R2.
- **Retención mínima:** ≥ 30 % de los eventos (R4). Con menos, el filtro se descarta por falta de potencia para NQ/YM.

## 8. Presupuesto de hipótesis (cerrado antes de correr)
- Etiquetas: 2 (`HA`, `HB`; `HB` con N=73 probablemente sin datos suficientes: se reporta, no se optimiza más allá de T1).
- Herramientas: 5 (T1–T5). Variables candidatas: ≈ 40 (listadas en §5; la lista se congela con el commit de esta adenda; no se agregan después).
- Cota superior de "pipelines": 2 × 5 = 10. La multiplicidad de variables y umbrales la absorbe el nulo del pipeline (§7), no una corrección por celda.
- Inferencia confirmatoria de esta fase: **una** (mejora del mejor pipeline para `HA` contra su nulo, α = 0,05). Todo lo demás es exploratorio.

## 9. Salida de la fase y puente con la confirmación
1. Si el pipeline supera su nulo y R3–R4 no se cumplen: se congela **un** filtro (especificación, umbrales, modelo, semilla, hash de código) y se agrega al manifiesto de la Pasada 3 como `HA′ = HA + filtro`. **Sigue siendo una sola hipótesis primaria.**
2. Se recalcula el MDE de NQ/YM con la retención real; si el MDE sube por encima del efecto esperado, el estado esperado es `SIN_POTENCIA` y se declara antes de abrir NQ/YM.
3. Si no supera el nulo: `HA` va a confirmación sin filtro (o se descarta si Nico lo decide); no se reintenta con otro conjunto de herramientas sobre los mismos datos.
4. Registro MEDIDO/NO MEDIDO actualizado en el mismo commit que los resultados; procedencia dirty-aware; semillas publicadas; landscape completo (todas las herramientas y pliegues), no sólo el mejor.

## 10. Riesgos
| Riesgo | Mitigación |
|---|---|
| Sobreajuste por buscar con muchas herramientas sobre pocos eventos | Nulo del pipeline + 1-SE + retención mínima |
| El filtro óptimo en ES no transporta a NQ/YM | Es el objetivo de la confirmación; se declara y se aceptan refutación o falta de potencia |
| Ajuste a la hora/contexto de ES | Variables de contexto explícitas en el modelo y en el nulo; contraste con la población alternativa |
| Fuga de información (cajas finales, entradas pre-cierre) | Auditor A1: reproducir cada variable en modo streaming hasta τ |
| Variables que dependen del orden de ticks (P-28) | Excluidas; `side` sólo si se verifica |
| Tentación de reabrir la búsqueda | Regla: un solo pipeline congelado por etiqueta; nueva búsqueda = nuevo manifiesto con conjunto de datos nuevo |
| Cómputo | Tabla de eventos pequeña (miles de filas): CPU local; extracción de ticks vía puente Kaggle; sin GPU |

## 11. Plan de auditoría
Reutiliza los roles A1–A7 del manifiesto de la Pasada 3. Atención especial: A1 (causalidad de cada variable), A2 (nulo del pipeline, purga/embargo, retención), A5 (código y hash), A7 (¿el efecto bruto ya está explicado por hora/volatilidad?).

## 12. Preguntas para Nico
1. ¿OK a que ES histórico sea desarrollo y NQ/YM queden sellados hasta congelar el filtro?
2. ¿Se mantiene el límite de ≥ 30 % de retención?
3. ¿Aceptás que **el resultado "ningún filtro mejora" sea válido** y se confirme `HA` sin filtro?
4. ¿Autorizás la extracción de la tabla de eventos+variables de ES vía Kaggle (target-free en las variables; incluye la etiqueta de la carrera de barreras, que es el retorno)?

*Aporte al referente:* permite buscar con amplitud la mejora del efecto bruto sin gastar la confirmación: el desarrollo ocurre sobre datos ya quemados, el juez es un nulo que incluye toda la búsqueda y el filtro sale congelado, simple y con su potencia declarada.

## 13. Enmiendas por auditoría externa (2026-10-15)
Aplican las enmiendas 1–9 de `MANIFIESTO_PASADA3_CONFIRMATORIA_CORREDOR_20261015.md` §13. Efectos específicos en esta fase:
- **Respuestas de Nico a las 4 preguntas de §12: sí a las 4.** ES (299 sesiones) es desarrollo; consecuencia declarada por HOLDOUT-A3: esta familia no tiene replicación de ES.
- **Dos detectores.** La extracción corre `DET_PY` (regresión: debe reproducir las cifras de Pasada 2) y `DET_NT8` (`SMA(Range)`, el del indicador). Todo filtro se desarrolla y se congela sobre `DET_NT8`.
- **Objetivo y economía.** Se guardan por evento los desenlaces R/C/0 y el **retorno al vencimiento** de los no resueltos; la métrica `ΔE` usa P&L realizado en ticks (con timeouts) y la fricción de R2. La decisión de selección usa `ΔE` y calibración, no sólo el acierto.
- **Controles.** Baseline continuo fuerte (hora + volatilidad + trayectoria + intensidad) como comparación obligatoria de T2–T4. Ablaciones que se reentrenan: sin volumen / sin indicador-contexto / sólo trayectoria.
- **Fuera de esta fase:** CNN/mapa de calor/riesgos competitivos (quedan para la propuesta del modelo de reversión).

> Corrección (2026-10-15): el hash de `NORTH_STAR.md` citado originalmente en este documento (`ed4293b5…`) era el de una versión anterior (stale). El valor vigente, verificado con `tests/test_north_star_hash.py`, es `05df5c7c…`. Los scripts de Pasada 2 conservan la constante vieja; no afecta resultados.
