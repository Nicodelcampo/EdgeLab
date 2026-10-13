# Próxima hipótesis por mecanismo — diseño, todavía no corrida científica

**DESIGN_ONLY_NOT_FROZEN_NOT_LAUNCHED.** El corte GC dentro de ambas zonas con ambos retornos no sostuvo su aporte incremental. Ese resultado se conserva; esta propuesta no cambia sus fechas, controles ni clasificación. No se abre holdout ni se retoca la grilla para elegir un corte favorable.

## Pregunta nueva
¿La **transición causal de presión alta con poco avance a decaimiento de presión/actividad** agrega utilidad predictiva frente a observar solamente el estado instantáneo y una historia continua equivalente? Medir A→E y E→A por separado; no asumir que absorción o exhaustion implican reversión. Registrar continuación y ausencia de pasada con censura observable, además de reversión.

Es una pregunta de trayectoria temporal, no otra búsqueda de zonas encima de zonas. Si aporta utilidad de representación se podrá preguntar después por AVOLZONEPOI2×BigTrap, siempre con densidad como comparador; no atribuir a una zona algo ya explicado por actividad o extensión.

## Contexto efectivamente revisado
Revisados el diseño `ABSORPTION_EXHAUSTION_EMPIRICAL_DESIGN.md`, registro de fuentes `ABSORPTION_EXHAUSTION_SOURCE_REVIEW.json`, recall `MNQ_DENSE_CONFLUENCE_BRAIN_RECALL.json` y cierre `GC_FOCUSED_CLOSEOUT.md`. Esta etapa reutiliza los pasajes de papers ya registrados: **no afirma nueva lectura integral** del corpus.

MLOFI: trades con bid/ask no reconstruyen cambios de profundidad ni cancelaciones; no llamar OFI real al flujo estimado. Liquidity Shocks sugiere secuencias de recuperación, no prueba absorción con un stall. Momentum Exhaustion declara no tener resultados empíricos; el nombre no certifica el mecanismo. Separar frecuencia, tamaño medio y volumen según la revisión de Duong/Fang/Kalev. Estado específico sin soporte es inconcluso. Memoria YM-BT2A saturada y geometría genérica obligan a novedad real, no renombrar búsquedas agotadas.

## Diseño candidato mínimo
- Censo independiente de zonas: primera observación real en cada celda5s. UNKNOWN/censurados conservan su propio denominador. No población definida por rebote o toque futuro.
- Mismos proxies A/E observables de ventanas20s, contexto60s, cobertura de volumen firmado≥80%, hueco máximo10s declarado para GC. No iceberg, intención, reposición pasiva ni agotamiento físico certificado.
- Máquina de estados causal a partir de `(timestamp_ns,sequence)`; tiempo desde el inicio observado del estado y transición **ya ocurrida**. Caducidad120s propuesta; gaps/UNKNOWN/sesión cortan continuidad. Ninguna duración final retrospectiva como feature.
- Respuesta primaria candidata: primera pasada simétrica de midquote observado en60s, barrera fijada desde contexto previo. Sin retorno futuro en orientación, features, bins o umbrales.
- Base fuerte: componentes continuos actuales **y su historia retardada en los mismos relojes**. Comparador de igual capacidad con bases continuas fijas. Sin esa historia, ganar con transición sólo demostraría que agregamos información pasada, no representación superior.
- Ablaciones separadas de estado, duración y transición; dos contrastes primarios propuestos: A→E y E→A. No producto cartesiano de umbrales ni elección de regularización sobre evaluación.
- GC como primer activo por soporte, después transporte a otro activo con protocolo propio. No agrupar GC/ES/6E como réplicas idénticas ni reutilizar excepción del oro como confirmación.
- Próximo bloque candidato17–30 de septiembre, calendario completo con vacíos sin sustituciones; todavía NO congelado porque faltan implementación causal y definición exacta de controles. Ya hubo inspección de resultados anteriores; será desarrollo, no holdout virgen. Fuente y sesgo de selección declarados.
- Medias de pérdida por sesión; sensibilidad60s antes de filtro; episodios identificados causalmente sólo si se implementan y prueban. Margen práctico/MDE fijados antes de outcomes usando unidades de sesión, no miles de anclas aparentes.

## Antes de lanzar
Implementar y probar truncación/prefijo, same-ns, transición trasUNKNOWN, gaps, sesión, purga60s, embargo y calendario. Congelar los dos contrastes, formas funcionales, límites, soporte mínimo y criterio inconcluso en plan propio. Medir soporte dentro de esa misma corrida; no repetir QA de dataset ni crear cadena de probes de validación. Registrar todos los negativos. No canonicalBrainwriter ni ganador automático.
