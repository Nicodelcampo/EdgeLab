# Lo rescatable de k34 / k36 / K37 (2026-10-17)

Estado: sintesis. No contiene mediciones nuevas ni toca retornos. Todo lo de abajo sale de documentos ya publicados (`k36_audit_20261017/`, `k37_results_20261017/`, resultados k34 del 2026-10-16).

## 1. Herramientas y metodo reutilizables (valor alto, costo ya pagado)
1. **Prueba de prefijo HFT v2 (no vacia)**: `tools/k36_audit/prefix_test_nontrivial.patch`. Verifico 234 zonas (descubrimiento) y 1.145 (replicacion), diferencias 0.0. Cualquier estudio que use zonas HFT puede heredarla; la v1 de k36 pasaba como `0 == 0`.
2. **Plantilla de replicacion de una sola variante** (`tools/k36_audit/k37_main_tail.py`): guardas fail-closed (aborta sin medir si hay < 80 sesiones o aparece una sesion >= 2026-10-01 o falla la prueba causal), ejecucion pasiva realista como metrica primaria, SE clusterizado por sesion, nulo de exclusion aleatoria, veredicto automatico segun criterios escritos antes. Sirve para cualquier hipotesis de "filtro sobre una poblacion".
3. **Tabla WF vs submuestra final** (`tools/k36_audit/wf_vs_oos_table.py`): detecta el sesgo del ganador comparando una ventana corta contra el walk-forward completo.
4. **Puente Drive-Kaggle endurecido**: ahora sin `--allow-push`. Una corrida sobre retornos exige manifiesto y OK.

## 2. Hechos medidos que conviene no volver a gastar
- La etiqueta "zona HFT tocada en la 1.a mitad" no agrega probabilidad de volver a la zona (-0.64 pp contra el control geometrico, k34); el +17.5 pp contra pseudo-zonas era geometria.
- Con retornos, la reversion simetrica 2 etapas tras esos impulsos no cubre el costo: descubrimiento +0.68 bruto (k35), replicacion -0.11 bruto / -1.99 neto pasivo (K37).
- El brazo "solo escalera" (n = 217) dio bruto +0.77 con se 1.4: no es un hallazgo, es ruido; no se explota.

## 3. Descriptivo de k34 que SI orienta (no es edge)
- Proximidad y frescura predicen **llegada**: zona a <= 20 ticks, virgen y joven llega 75.8 %, lejos y gastada 32.9 % (AUC 0.77 con regresion logistica simple). Eso describe donde el precio vuelve, no que volver rinda despues de costos.
- Recorrido medio inverso (MFE_inv - MAE_inv) por estrato de k34 (ticks, sin stop, horizonte 300 barras, **sin SE publicado**): 0-0 = -0.1; 1 zona en W1 = +2.7; 2 zonas = +4.8; >= 3 zonas = -3.0; W2 ocupada = +2.3. Con n chico por estrato y sin incertidumbre, es una pista para una Fase 0, no un resultado.

## 4. El obstaculo real es la friccion, no la deteccion
`docs/CURRENT.md` ya registra: el recorrido a 15-60 min supera con holgura la friccion en indices y metales (acierto direccional minimo 52-61 %), y la direccion a 15-60 min no mostro efecto (R3: 0 sobrevivientes). Es decir: hay movimiento, no hay predictor de direccion. En k36/K37 el costo (1.546 ticks) es mayor que cualquier bruto observado.

## 5. Siguientes hipotesis candidatas (SIN ejecutar; cada una exige manifiesto y OK de Nico)
1. **Fase 0 target-free de ejecucion pasiva**: tasa de fill pasivo y costo de seleccion adversa por tipo de impulso (esta es la parte donde k36 mas diferia entre limite inmediato y maquina de estados: -0.6 a -1.3 ticks). Aporta al costo, que es el cuello de botella.
2. **Horizonte largo no direccional**: dado que el recorrido a 15-60 min supera la friccion, caracterizar cuando el movimiento absoluto es grande (volatilidad condicional) como insumo de dimensionamiento y de filtro de regimen, sin apostar direccion.
3. **Distribucion completa de excursiones** (canal no direccional) con SE clusterizado para los estratos de la seccion 3, antes de cualquier estrategia: decide si vale una Fase 1.
Ninguna se corre sin manifiesto: poblacion enumerada, efecto minimo detectable, multiplicidad, criterios de exito/fracaso y datos de replicacion identificados (la ventana abr-sep ya esta usada para esta familia).

## 6. Que NO se rescata
Variantes de stop "punto dulce", rankings con p_win ad hoc, ensambles sobre las mismas 178 sesiones: sin evidencia y con multiplicidad creciente.
