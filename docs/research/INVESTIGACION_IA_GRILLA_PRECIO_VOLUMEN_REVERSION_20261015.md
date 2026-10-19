# Investigación: qué IA usar sobre una grilla precio × volumen para predecir reversión (dónde y cuándo)

Estado: PROPUESTA (investigación bibliográfica y de diseño; nada entrenado ni medido)
Fecha: 2026-10-15
Familia / módulo: research · modelos (relacionado con `EmaCorridorTrendVol`, anclas de volumen y `edgelab/external`)
Procedencia: búsquedas web del 2026-10-15 (fuentes abajo) + documentos previos del repo (`docs/research/external/DEEP_RESEARCH_L2_A_20260923.md`, `..._B_...`, `PLAN_L2_POST_DEEP_RESEARCH_20260923.md`). Se leyeron los extractos de las fuentes; **no se leyeron completos los resultados de una búsqueda sobre CNN en imágenes de velas/volumen (resultado demasiado grande), así que esa rama queda sin evidencia propia**.

## Pregunta
Dada una grilla (franjas de tiempo × franjas de precio) con el volumen operado en cada celda alrededor de una zona, ¿qué IA permite predecir **si** el precio revierte, **dónde** y **cuándo**, con ventaja estadística neta?

## Lo que dice la literatura
- **DeepLOB** (Zhang, Zohren, Roberts 2019): CNN + Inception + LSTM sobre el libro de órdenes (100 × 40). Es el estándar de referencia; los números de rentabilidad que publica son **brutos de costos** (mid-price), en acciones.
- **LOBCAST / Prata et al. 2024** (15 modelos): el desempeño **cae fuera de muestra** y los modelos complejos no son consistentemente mejores.
- **TLOB** (Berti & Kasneci 2025): un **MLP simple** supera el estado del arte; su transformer con doble atención mejora en horizontes largos y mercados volátiles; la **predictibilidad bajó con el tiempo (−6,68 de F1)**; al definir la tendencia con el spread (el costo principal) **el desempeño se deteriora**: traducir clasificación a P&L es el problema.
- **Briola et al. 2025 (LOBFrame, «microstructural guide»)**: la probabilidad de ejecutar una transacción correcta es baja aun con buen F1; el rendimiento práctico depende de la estructura del libro (tick grande/chico) y de la latencia.
- **Kronos** (AAAI 2026, modelo fundacional de velas OHLCV; 12.000 M de velas de 45 mercados): mejora el RankIC frente a otros modelos de series de tiempo, pero **las mejoras son relativas**, medidas en cross-section de acciones, y los modelos fundacionales generales (Chronos, TimesFM, Moirai) dan RankIC ≈ 0 en finanzas. No predice reversiones sobre una grilla de volumen.
- **Calibración y abstención:** la predicción conformal y la clasificación selectiva dan garantías de cobertura y permiten **abstenerse** cuando el modelo no sabe (fuentes: Selective Conformal Risk Control 2025; Kaya & Nguyen 2025).
- **Conclusión previa del repo (2026-09-23, dos informes independientes):** *no entrenar DeepLOB ni transformers con 30 días de un instrumento*; Kaggle da ~30 h/semana de GPU (sesiones de hasta 9 h), suficiente para modelos chicos.

## Qué implica para EdgeLab
1. **El cuello de botella no es la arquitectura, es N y la definición de la etiqueta.** Con decenas o cientos de zonas por activo, un CNN grande se sobreajusta; con millones de ventanas sin zona, sí hay datos para aprender representaciones, pero no para validar la reversión en zonas.
2. **TPU no hace falta.** Los modelos razonables son chicos; GPU/CPU de Kaggle alcanza.
3. **«Predecir» y «ganar» son cosas distintas:** hay que medir contra el costo (3,4–3,6 ticks en ES) y contra un nulo sin filtro.

## Arquitectura recomendada (por etapas, de menor a mayor riesgo)
| Etapa | Qué | Por qué | Datos que exige |
|---|---|---|---|
| 0 | **Etiqueta causal** y definición de «reversión»: evento definido sólo con información posterior a la decisión, con celda de destino (precio relativo × tiempo) | sin esto, todo lo demás es ruido o filtración | zonas confirmadas, ticks |
| 1 | **Baselines baratos en CPU:** regresión logística/elastic net y **gradient boosting (LightGBM)** sobre resúmenes de la grilla (POC, borde del área de valor, desequilibrio de flujo, asimetría, distancia a anclas, velocidad previa, rango relativo) | TLOB muestra que un MLP/lineal ya iguala a lo complejo; define el piso a vencer | cientos de zonas bastan para ver si hay algo |
| 2 | **Cabeza de «mapa de calor»:** MLP o CNN 2D pequeña (3–4 capas) que recibe la grilla normalizada y devuelve una **distribución sobre celdas** (dónde, cuándo) + clase «no revierte», con una softmax 2D. Es la forma natural de contestar tu pregunta | produce el mapa que querés; permite medir con log-loss y CRPS | mismo N; **aumento por espejo** (invertir precio y cambiar compra/venta duplica datos e impone simetría, igual que `mirror_check`); pooling multi-activo con ticks normalizados |
| 3 | **Dónde/cuándo como supervivencia:** riesgo discreto h(t \| x) sobre una grilla de precio relativo, o regresión por cuantiles / mezcla de densidades para el exceso máximo y el tiempo hasta el giro | trata «cuándo» como duración, no como clase | igual |
| 4 | **Preentrenamiento autosupervisado** sobre **todas** las ventanas de la release (1.394 M de filas): enmascarar celdas de la grilla y reconstruirlas, o predecir la grilla siguiente; luego ajustar una cabeza pequeña con las zonas | es el único uso de GPU que se justifica: el N para el pretexto es enorme | GPU (Kaggle), sólo si 1–3 muestran señal |
| 5 | **Calibración + abstención:** predicción conformal / clasificación selectiva; sólo se actúa cuando P(giro en la celda) × recorrido > fricción | evita operar sin evidencia y da probabilidades interpretables | conjunto de calibración separado por sesión |

**No recomendado ahora:** DeepLOB/TLOB/transformers sobre el libro (L2 de ≤ 60 sesiones por producto); fine-tuning de modelos fundacionales (Kronos, Chronos, TimesFM) como predictores directos; aprendizaje por refuerzo. Kronos podría servir sólo como **generador de características** dentro del módulo `edgelab/external` (con su contrato causal), con prior bajo.

## Reglas de evaluación (obligatorias)
- Validación **por sesión** con purga y embargo (walk-forward); nunca mezclar ventanas de una misma sesión entre entrenamiento y prueba.
- Comparar contra: (a) línea base sin filtro, (b) baselines de la etapa 1, (c) placebo/espejo, (d) volatilidad sola. Reportar MDE y N efectivo (sesiones).
- Métricas: log-loss/Brier y CRPS para la distribución, más expectativa **neta de fricción** por celda. Multiplicidad con Holm; holdout sellado (`trade_date ≥ 2026-10-01`) sin tocar.
- Preregistro: etiqueta, grilla (tamaño de celda, ventana), normalización, partición y criterios de éxito, **antes** de entrenar. Una búsqueda sobre retornos necesita OK de Nico.

## Riesgos
- **Filtración por la etiqueta:** la zona del indicador se conoce tarde y su origen se reubica; una «reversión» definida mirando el futuro da un modelo perfecto e inútil.
- **N chico de zonas marcadas** (~10 % por construcción del percentil 90).
- **Cambio de régimen:** la predictibilidad cae con el tiempo (TLOB).
- **Hipótesis previa de EdgeLab:** las zonas como soporte/resistencia están refutadas (~96 % de ruptura) y las zonas como imán están cerradas; un modelo deberá mostrar valor **por encima** de eso.

## Fuentes
- Zhang, Zohren, Roberts (2019). *DeepLOB*. IEEE TSP 67(11). arXiv:1808.03668.
- Prata et al. (2024). *LOB-Based Deep Learning Models for Stock Price Trend Prediction: A Benchmark Study* (LOBCAST). Artif. Intell. Rev.; https://github.com/matteoprata/LOBCAST
- Berti & Kasneci (2025). *TLOB*. arXiv:2502.15757; https://github.com/LeonardoBerti00/TLOB
- Briola et al. (2025). *Deep limit order book forecasting: a microstructural guide* (LOBFrame). Quantitative Finance. https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/
- *Kronos: A Foundation Model for the Language of Financial Markets* (AAAI 2026). arXiv:2508.02739.
- *Selective Conformal Risk Control* (2025), arXiv:2512.12844; Kaya & Nguyen (2025), *Conformal Prediction for Reliable Stock Selections*, PMLR 266.
- Repo: `DEEP_RESEARCH_L2_A_20260923.md`, `DEEP_RESEARCH_L2_B_20260923.md`, `PLAN_L2_POST_DEEP_RESEARCH_20260923.md`.
