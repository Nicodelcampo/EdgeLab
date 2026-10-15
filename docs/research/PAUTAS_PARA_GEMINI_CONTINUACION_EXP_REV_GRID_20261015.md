# Pautas para Gemini: continuación de EXP-REV-GRID tras la guía de técnicas avanzadas

Estado: VIGENTE (instrucciones de trabajo; Claude tiene pocos créditos y delega la continuación)
Fecha: 2026-10-15
Familia / módulo: EXP-REV-GRID (`edgelab/research/reversal_grid`) y pista L2 de ES
Referente rector: `docs/NORTH_STAR.md` (cuerpo sha256 `05df5c7c3ec4cf3a1f14f62bb8e2ade4b61dd29203b610a308964ac46995f421`)
Revisa: `GUIA_TECNICAS_Y_HERRAMIENTAS_AVANZADAS_EXP_REV_GRID_20261015.md` (Gemini).

## 1. Veredicto sobre la guía
**Buenas ideas, pero llegan antes de tener una base medida.** Es un catálogo de ~10 componentes (alineación canónica, CoordConv, pooling axial, FiLM, SE, Hawkes, absorción, vacío en ruta, supervisión multi-barrera, pesos de unicidad, IPCW, ACI, selector de ejecución) sin ninguna línea base entrenada todavía. Con ~1.200 (pista L2) a ~15.000 (ticks) episodios independientes, cada pieza extra aumenta el riesgo de sobreajuste y el número efectivo de hipótesis. **Se acepta como lista de candidatos ordenada por niveles (sección 3), no como arquitectura a integrar.**

## 2. Lo que está bien y lo que hay que corregir
**Correcto y útil:** el diagnóstico del `AdaptiveAvgPool2d((2,4))` (promedia justo los nodos finos de precio; coincide con mi reserva 5); pesos de unicidad de muestra (López de Prado); supervisión auxiliar del retorno al vencimiento (`μ_TO`) para completar la fórmula `EV = P(R)·X − P(C)·Y + P(0)·E[ret_timeout] − F`; Hawkes/absorción/vacío como variables de contexto que sólo usan `ts, price, volume`.

**Hay que corregir antes de usar:**
1. **"La alineación canónica duplica el soporte efectivo" es incorrecto.** Orientar el eje por la dirección de la expansión impone equivariancia y reduce parámetros, pero **no crea observaciones**. Además **presupone una regla causal y preregistrada de "expansión" y de dirección**, que todavía no existe (el piloto de soporte usó decisiones sin dirección). Primero hay que definir y congelar esa regla (enumerando las alternativas de población: creación, aproximación, toque, estado continuo) y recién entonces orientar.
2. **"Sin gastar presupuesto de hipótesis" es incorrecto.** Una cabeza auxiliar (16/32/48 y `μ_TO`), pesos de pérdida (0,25 / 0,10), FiLM, SE, CoordConv y pooling axial son variantes de modelo: cada una se cuenta en el número efectivo de hipótesis y se evalúa como **ablación re-entrenada**, no como mejora asumida.
3. **IPCW/Kaplan-Meier por sesión no es la solución correcta a la censura.** La censura aquí es administrativa (fin de sesión) y depende de la hora de decisión, no es independiente de las covariables. Dos salidas válidas: (a) **evitarla por diseño**: no tomar decisiones cuyo horizonte exceda el cierre (el piloto da 0,1–1 % censurado a 1800 s: es casi ignorable), o (b) estimar `G(t)` condicionado a la hora de decisión. Priorizar (a); implementar IPCW sólo si (a) no alcanza.
4. **`session_auction` / `INFORME_MAESTRO_BARRIDO_MULTIDIMENSIONAL_SUBASTA_20261014`:** ese informe sale de una búsqueda de 1.512 configuraciones sobre datos que EdgeLab ya inspeccionó. Sus hallazgos son **hipótesis**, no evidencia ni justificación de que la variable "separa" bien: declarar su historia de exposición y su multiplicidad antes de incluir `in_value_balance_prior_day` y similares.
5. **El selector de ejecución y el ahorro de "~1,5–2,0 ticks" (equilibrio 52,4 %) no tienen sustento.** No hay modelo de llenado: una orden límite sufre no-ejecución y selección adversa. La fricción medida (3,546 ticks, R2) es de entrada a mercado. No usar 52,4 % en ninguna decisión; tratar la ejecución pasiva como línea de investigación aparte, con simulador y trade-through validados.
6. **ACI conformal con calibración de ~12 sesiones** es frágil y el feedback es demorado (el horizonte es de 30 min): no es apto como compuerta de la primera evaluación. Dejarlo para una etapa posterior.
7. **Pesos de unicidad normalizados por sesión** cambian el estimando a "promedio por sesión": declararlo y evaluar con los mismos pesos (o con diferencias pareadas por sesión), no sólo entrenar con ellos.
8. **"Código listo para integrar":** hasta que pase pruebas en Kaggle (equivariancia direccional, ausencia de información futura, formas, gradientes, igualdad con la implementación de referencia) no está listo. **No integrar nada a `edgelab/research/reversal_grid` ni al repo sin OK de Nico.**

## 3. Orden de incorporación (con compuertas)
**Nivel 0 — base (antes de cualquier componente de la guía):**
- Congelar **población y reloj de decisión** y la **regla causal de expansión/dirección**; repetir el conteo de soporte sobre esa población (el piloto actual es incondicional). Calcular el **MDE de cada partición** (calibración ≈ 12 sesiones y tuning ≈ 11 en el calendario propuesto son demasiado chicos para sintonizar y calibrar: proponer un calendario alternativo y justificarlo).
- Etiqueta candidata (decisión de Nico): **32/32 ticks a 1800 s** (primaria), 24/24 a 900 s y 48/32 a 1800 s (secundarias); **no** 300 s (resuelve 18,5 %). Detalle: `RESULTADOS_PILOTO_SOPORTE_EXP_REV_GRID_20261015.md`.
- Escalera de baselines ya acordada: hazard constante → GLM → LightGBM → MLP → CNN pequeña, con semillas **≥ 5** (justificar si se usan 3) y presupuesto declarado.

**Nivel 1 — barato y de bajo riesgo (primero como variables en los baselines tabulares, después en los tiles):** `HawkesRatio`, absorción por celda, `ReversalPathVacuum` (con dirección ya congelada), pesos de unicidad.

**Nivel 2 — sólo si la CNN base muestra información incremental sobre el baseline continuo, y siempre como ablación:** pooling axial dual (cabeza de más resolución), CoordConv, alineación canónica, cabeza auxiliar multi-barrera/`μ_TO`.

**Nivel 3 — sólo con señal calibrada y simulador de fills validado:** FiLM, SE, ACI, selector de ejecución, y la capa de política/RL.

## 4. Reglas operativas (obligatorias)
- **No entrenar con retornos de mercado ni abrir particiones sin manifiesto congelado + OK explícito de Nico (STOP).** No abrir NQ/YM ni el holdout (≥ 2026-10-01). La réplica de ES (abril–septiembre) **ya está expuesta** por la línea del corredor.
- **Datos:** la pista sin L2 puede entrenar con todo el historial de ticks (decisión de Nico), pero usar abril–septiembre o más instrumentos consume la réplica de esta familia: pedir la enmienda explícita antes. La pista L2 usa sólo las ~85 sesiones disponibles (28-jun a 14-oct-2026; desarrollo L2 hasta 31-oct) y entra como **contexto de 5–30 min sobre el modelo de ticks**, no como modelo autónomo.
- **Panel decidido por Nico:** DeepLOB-style, Transformer chico, modelo fundacional (extractor congelado) y RL al final, con las mismas reglas y presupuesto que el resto.
- **Evidencia que no se arrastra:** el corredor (`EmaCorridorTrend`) no dio efecto neto en ES (`HA` bruto +1,5, neto −2,0 ticks; p del pipeline 0,239): es una capa a **probar por ablación**, no una premisa. Ver `CORREDOR_EMA_MEDIDO_Y_NO_MEDIDO.md`.
- **Tareas de verificación técnica pendientes (no usan retornos):** equivalencia de features por prefijos vs streaming; `available_at` de anclas; test de equivariancia direccional de cualquier componente nuevo; prueba de que el centrado nunca usa el fill del tick siguiente.
- Un solo escritor por directorio; registrar cada variante intentada (no sólo las ganadoras); recibos con hashes en Kaggle; sin tokens ni URLs firmadas en los documentos.

## 5. Entregables en orden
1. Propuesta de **población, reloj y regla de expansión** (con alternativas enumeradas y condición de refutación).
2. **Soporte condicional** y **MDE por partición** (calendario alternativo si el actual no alcanza).
3. **Manifiesto borrador** de la pista de ticks (etiqueta, baselines, presupuesto, número efectivo de hipótesis, criterio de éxito sobre ΔE neto y calibración) y otro para la pista L2 como contexto 5–30 min.
4. Pruebas técnicas del nivel 0–1 en Kaggle (con recibos).
5. Sólo después, el nivel 2 como ablaciones.
Entregar en `resultados_claude_local` y como kernel privado en Kaggle, con una nota breve de qué falta y qué decisiones requiere de Nico.

## 6. Cómo reportar
Por cada componente: **qué es, hipótesis que agrega al presupuesto, prueba técnica, ablación prevista, qué la refutaría**. Si hay desacuerdo con estas pautas, responder punto por punto (acuerdo / desacuerdo / no verificable) con evidencia, igual que en la revisión del corredor.

*Aporte al referente:* ordena la mejora del modelo de grilla por niveles con compuertas de evidencia, para que ninguna sofisticación entre sin una base medida que la justifique y sin gastar el presupuesto de hipótesis.
