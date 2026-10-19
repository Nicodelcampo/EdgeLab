# Absorción y exhaustion: atlas empírico MNQ

**DESIGN_ONLY_NOT_PREREGISTERED.** Investigación nueva propuesta, sin ejecución, outcomes leídos ni escritura al EdgeBrain canónico. Se mantiene la V3 activa sin cambios. Este documento complementa, no sustituye, el diseño de confluencias ni reabre las campañas cerradas.

## Decisión

Conviene investigar ambos fenómenos como estados observables y sus transiciones, no asumir que BigTrap2Absorption identifica el mecanismo ni que exhaustion implica reversión. Primero medirlos fuera de las zonas; luego preguntar si aVolZonePOI2/racimos/BigTrap agregan información condicional. Aumentar la densidad de zonas amplía cobertura, pero no aumenta automáticamente el número de episodios independientes.

El objetivo es enriquecer al cerebro con definiciones, incidencias, efectos relativos, incertidumbre, contraejemplos y límites de observación. No buscar una configuración ganadora ni producir P&L. Que un resultado sea negativo o inconcluso también es conocimiento, con su alcance y potencia.

## 1. Fuentes efectivamente consultadas

Biblioteca canónica de PR67 fijada en `5c10da451b164c54133bdb9a4674de43d6fa2d22`: índice completo y pasajes seleccionados de seis textos normalizados, no lectura integral de los 401 papers. `ABSORPTION_EXHAUSTION_SOURCE_REVIEW.json` conserva paths, hashes, rangos y límites. No se ejecutó el bootstrap ni se creó otro corpus/ledger. No se obtuvo evidencia pertinente de la búsqueda en Notion.

| Paper del corpus | Lectura útil | Implicación, no resultado MNQ |
|---|---|---|
| Xu, Gould, Howison, MLOFI, SSRN3479741 | Abstract, definición del flujo de órdenes y evaluación | OFI/MLOFI incluyen cambios de tamaño del libro y cancelaciones; delta de trades no es OFI. Su ajuste es contemporáneo, incluso cuando los coeficientes se evalúan fuera de muestra; no demuestra predicción futura. |
| Biais y Weill, Liquidity Shocks, SSRN1193442 | Abstract y dinámica de respuesta al shock | Modelo teórico con recuperación, evolución del spread y volumen no monótono. Sugiere medir secuencias y recuperación, no afirmar que un stall observado prueba absorción. |
| Bhatti, Momentum Exhaustion, SSRN6454659 | Abstract y condiciones de señal | El propio texto declara **sin resultados empíricos**. ADX decreciente, extremos previos y desvío VWAP son una hipótesis de contexto, no validación. VWAP no es valor justo demostrado. |
| Palguna y Pollak, SSRN2021182 | Abstract, soporte por estados y experimento | Estados muy específicos tienen poco soporte; agrupar usando sólo entrenamiento. Supone estacionariedad local y usa tamaños del libro que aquí no tenemos. |
| Duong, Fang y Kalev, SSRN1716874 | Abstract e introducción | Separar frecuencia de trades, tamaño medio, volumen y desequilibrio; no atribuir toda desaceleración a menor presión. Resultados reportados en otros futuros. |
| Osterrieder, SSRN2984315 | Abstract e introducción | Profundidad y provisión de liquidez son partes del modelo. Un flujo de trades sin profundidad no identifica quién absorbió. Modelo teórico, no receta de indicador. |

Memoria: recall científico existente `MNQ_DENSE_CONFLUENCE_BRAIN_RECALL.json` y sus fuentes/anclas; HIPOCAMPO externo leído en `4e879033e43d91bcf0639205ad175ce6ac37c2d1`. Las lecciones operacionales propuestas no son efectos de mercado verificados.

- `CX-RH-YM-BT2A`: línea saturada en YM, seis campañas/26.856 políticas adjudicadas sin sobrevivientes según memoria. **No repetirla cambiando el nombre.** Novedad propuesta: población MNQ, medición continua independiente del detector, controles nuevos y transiciones; el null de YM no prueba ausencia en MNQ.
- `CX-RH-BIGTRAP2-MAGNET/SR`: controlar la misma geometría y contexto sin zona; no rescatar soporte/resistencia aislado.
- `LESSON-RH-TOUCH-ONLY-POPULATION`: censo fuera de zonas además de aproximación, nacimiento, toque y revisita; no definir población usando rebotes posteriores.
- `CX-RH-HFTZONES-ES`: bajo soporte/MDE grande es inconcluso, no ausencia probada. Filas y configuraciones no reemplazan sesiones.
- `CX-RH-L2-SPOOF-DETECTOR`: no inferir intención a partir de una firma débil. No llamar iceberg/spoofing al proxy.
- AVZ negative tape: UNKNOWN no es detector negativo; calibración incompleta no significa ausencia de fenómeno/zona.
- HIPOCAMPO, L10: comparación con nulos igualmente procesados; rechazar estacionariedad de una transformación no prueba predictibilidad ni edge.

## 2. Qué permite observar la fuente actual

Reusar la fuente aprobada MNQ09-26 y su selección histórica; no repetir QA ni descargar mercado fuera de Kaggle. Columnas: tiempo, secuencia, precio, volumen, bid y ask. No están disponibles tamaños del libro, órdenes individuales ni cancelaciones en esta fuente. Bid/ask registrados en filas de trades no constituyen una cinta completa de todos los cambios de cotización.

Podemos medir **presión agresora estimada / poco avance observado** y **decaimiento de presión tras un impulso**. No demostrar reposición pasiva, iceberg, finalización de una metaorden o agotamiento de todos los participantes. El nombre de los resultados será ABSORPTION_PROXY y EXHAUSTION_PROXY.

El BT2A actual calcula flujo estimado relativo a desplazamiento en cubetas, con fallback BUY para ciertos ticks sin cambio. Se conserva intacto para compararlo como detector; no se hereda ese fallback como verdad física. El estimador científico tendrá signo +1/-1 sólo cuando la regla de cotización sea inequívoca con las cotizaciones registradas; interiores/empates/cotización inválida son UNKNOWN. Su volumen se conserva, no se elimina. La fracción sin signo se reporta y entra como covariable/estrato de calidad; ventana sin cobertura suficiente = estado UNKNOWN, no no-absorción. Sensibilidad con tick-rule causal será otro proxy declarado, no etiqueta real.

Midquote de las cotizaciones registradas es la medida primaria propuesta para limitar bid-ask bounce; precios de trades y bid/ask por separado son sensibilidad. Se usa entero en medios ticks, sin redondear midpoint a tick entero. No forward-fill de cotizaciones o actividad a través de gaps/sesiones.

## 3. Definiciones causales propuestas

Censo común, independiente de indicadores: primer trade observado en cada celda de reloj de **5 segundos**; celdas vacías se cuentan por separado, sin fabricar anchor/precio. `(timestamp_ns, sequence)` determina el corte: ningún tick posterior, aunque comparta nanosegundo, entra como feature. Dirección `s` = signo del flujo estimado en la ventana previa de igual duración; empate/sin soporte = UNKNOWN_DIRECTION. No orientar después por el retorno futuro.

Ventanas candidatas de medición **5, 20 y 60 segundos**, con principal **20 segundos**, todas retrospectivas completas dentro de sesión. Mantener segundos: una cubeta de N ticks no permite medir caída de frecuencia sin considerar su duración. Historia de contexto adicional de 60 segundos y umbrales/calibración sólo con sesiones pasadas. Todo esto es propuesta, no protocolo ejecutado.

Para cada W registrar por separado:
- Volumen total, número de trades, tamaño medio, tiempo entre trades y volumen sin signo.
- Volumen estimado a favor/en contra de `s`, flujo neto, persistencia de signo y cambio respecto de la ventana anterior de igual duración.
- Desplazamiento dirigido del midpoint, rango, recorrido, eficiencia y spread. Mantener las unidades, no confundir rapidez en barras con velocidad por segundo.
- Desplazamiento esperado por presión/contexto bajo modelo ajustado sólo en entrenamiento pasado y residual contemporáneo; descriptivo, no predictor futuro certificado.

**A (absorción proxy):** presión a favor de `s` alta respecto del pasado comparable y progreso dirigido pequeño. Medir presión y progreso como ejes, no depender únicamente de un cociente inestable. Ratio con denominador cero se etiqueta como caso propio; ninguna división silenciosa.

**E (exhaustion proxy):** había presión e impulso previo en dirección `s`, y la presión/frecuencia actuales caen respecto de su ventana anterior. No exigir que el precio ya haya revertido, ni usar el futuro para decidir que terminó el impulso. Separar caída de volumen, de frecuencia y de tamaño medio.

Principal propuesto: presión previa por encima del percentil80 causal; para A, presión actual por encima de ese umbral y progreso dirigido por debajo del percentil20 causal comparable. Para E, presión/actividad actual ≤50% de la previa con impulso previo positivo. Cuantiles y mínimos de cobertura se congelarán desde entrenamiento/ingeniería sin mirar outcomes. Sensibilidades limitadas y registradas: presión70/90, progreso10/30, caída25/75%; variar un eje a la vez, no producto cartesiano para elegir ganador.

A y E pueden coexistir: presión actual aún alta respecto del baseline, pero menor que la previa. Clasificar **A sólo, E sólo, ambos, ninguno y UNKNOWN** sobre el mismo censo. Son firmas observadas, no mecanismos mutuamente exclusivos ni diagnósticos definitivos. Registrar duración y transiciones A→E/E→A con una máquina de estados causal; los resúmenes retrospectivos del episodio no entran en predicción de su comienzo.

## 4. Preguntas y mediciones

1. **Separabilidad:** ¿A/E tienen firmas y transiciones diferentes de alta actividad con avance, pausa de baja actividad y simple bounce? Mostrar cobertura, soporte, ambigüedad y ejemplos contrarios seleccionados por regla, no por éxito.
2. **Respuesta futura:** ¿cambian continuación, reversión o falta de desplazamiento frente a contexto comparable? Puede aparecer continuación tras A; no imponer reversión como definición.
3. **Valor incremental:** ¿una representación A/E mejora modelos restringidos fuera de su entrenamiento frente a los mismos componentes básicos? Los estados son transformaciones deterministas de esos componentes: **no crean información nueva** respecto de un modelo que ya observa todo el tape. Una mejora prueba utilidad de representación en el modelo evaluado, no identificación causal ni nueva fuente de información.
4. **Secuencia:** ¿persistencia, revisita y transición A→E agregan algo al estado instantáneo, o sólo recodifican actividad/contexto?
5. **Interacción espacial:** ¿estar en una AVZ/racimo/BT2/BT2A disponible entonces agrega a A/E, o desaparece al igualar geometría, exposición, edad y ocupación? ¿Importa orden de formación/llegada?
6. **Transportabilidad:** ¿hay signo/soporte estable por reloj, volatilidad, contrato natural y época? MNQ y NQ no son réplicas independientes. Otra población explorada tampoco convierte lo histórico en confirmación independiente.

Respuesta primaria candidata: primera pasada del midpoint observado a una barrera simétrica dirigida, durante **60 segundos**, desde un anchor posterior a la ventana de features. Distancia individual fijada en el anchor: `max(4 ticks, ceil(0.5 * rango_midpoint_previo_60s_en_ticks))`; reportar distancia y soporte, sin optimizarla por outcomes. Tres clases: continuación primero, reversión primero, ninguna pasada con horizonte observable completo. Las sensibilidades15/180s son secundarias, no endpoints alternativos para elegir un ganador.

EOF/sesión/gap/información de cotización insuficiente = censurado/UNKNOWN, nunca “ninguna pasada”. Congelar una política explícita de cobertura/gaps antes del piloto científico; reportar denominadores total/observable/censurado y censura por estado. No interpolar una pasada entre observaciones ni simular fills. Barrera/horizonte/censura todavía sujetos a revisión y congelación.

Métricas: Brier multiclase emparejado en los mismos anchors y splits; secundarios log-loss/calibración, tasas por clase, tiempo hasta pasada, cambios posteriores de flujo, duración/recurrencia. Una tasa entre completos es condicional a cobertura; no convertirla en tasa de todo el censo. Nada de SL/TP optimizados o P&L.

Modelos propuestos, misma complejidad y presupuesto de ajuste:
- M0: reloj/volatilidad/spread/actividad/extensión previa y calidad del proxy.
- M1: M0 + componentes continuos de presión/progreso/decaimiento; ésta es la referencia fuerte, no sólo M0.
- M2: M1 + representaciones A/E, duración causal y transiciones disponibles.
- M3: M2 + efectos principales de las zonas/racimos/BT2/BT2A.
- M4: M3 + pocas interacciones preregistradas estado×geometría/orden de formación.

M2−M1 = utilidad de representación; M4−M3 = interacción, no llamar sinergia a M4−M0. Reportar ablation A/E y componentes, incluso sin mejora. Si se hace selección de regularización, usar sólo folds internos de entrenamiento con presupuesto congelado.

## 5. Controles, inferencia y falsificaciones

- Mismo censo completo para estados y controles; no sólo los toques o los anchors fáciles de aparear. Cada control reconstruye sus features/eligibilidad en su propio anchor.
- Controles naturales: presión alta con progreso; actividad baja con poco progreso; decaimiento tras actividad no direccional; misma extensión sin decaimiento. Son grupos de contraste, no pruebas causales por sí solos.
- Al estudiar zonas: control de geometría sin zona, ancho/edad/distancia/ocupación similares. Ausencia sólo con detector negativo observado y calibrado, nunca UNKNOWN. Respetar guardia temporal vigente para controles de la misma sesión, sin copiar el camino de llegada del tratado.
- Bounces: repetir con midpoint y cotizaciones versus last trade. Si la firma desaparece al corregir bounce, registrar evidencia contra la interpretación.
- Prefix/truncación, espejado bid/ask y signos, empates, gaps y sesión: tests sintéticos de nueva medición; no otra auditoría NT8 ni QA de datasets.
- Nulos con estructura temporal y procesamiento comparable. Proponer shifts por bloques/sesiones elegibles con reloj/actividad preservados; validar intercambiabilidad primero. No barajar ticks IID destruyendo el mercado y llamar eso evidencia.
- Walk-forward cronológico dentro del research ya autorizado, ventanas de outcome purgadas y embargo≥horizonte máximo. Escalado, cuantiles, bins, matching y agrupación se ajustan sólo en entrenamiento. Registrar el historial de selección ya inspeccionado: “OOS de desarrollo” no es holdout virgen.
- Anchors solapados pertenecen a episodios/sesiones dependientes. Inferencia por bloques de sesiones y pérdidas emparejadas; balancear peso por sesión y declarar estimando, no dominar con la sesión más activa. Registrar reutilización de controles/efectivo soporte.
- Tres contrastes primarios propuestos: representación A, representación E e interacción A×E; familia conjunta con corrección Holm y CI simultáneos revisados. Interacciones de zonas y ventanas/umbrales secundarios forman una familia exploratoria separada, con todos los intentos y sin ocultar censurados/no evaluables. No aplicar DSR/PBO de P&L a Brier por renombrar columnas.
- Fijar margen práctico antes de outcomes; estimar potencia/MDE con unidades independientes y soporte real. Equivalencia sólo si CI cae dentro del margen preregistrado; “no significativo” no prueba ausencia. El piloto de ingeniería no estima edge ni potencia concluyente.

## 6. Ejecución eficiente por fases, propuesta

**P0: ingeniería target-free, un shard de 1–3 sesiones existentes.** Censo y primitives/estados, conteos de soporte/UNKNOWN, costo por etapa y límites. Sin outcomes para escoger umbrales/configs. Reusar manifests y warm-up real; no volver a comprobar todo el dataset. Fijar fechas por selección existente, no elegir las más favorables.

**P1: atlas de fenómenos fuera de zonas.** Una lectura por sesión para las tres ventanas, presión/progreso/contexto y anchors. Persistir private feature store en Kaggle. La clasificación se hace sobre arrays/estadísticos compartidos; no ejecutar un kernel por definición. Empezar sin detectar miles de zonas elimina costo y confusión innecesarios.

**P2: respuesta + inferencia en research.** Congelar spec/particiones, calcular etiquetas una vez por anchor/barrera/horizonte/política y reutilizar entre estados/modelos. Sólo aumentar sesiones si falta soporte; no compensarlo fabricando más variantes sobre los mismos episodios.

**P3: interacciones.** Reusar capturas privadas de la campaña de confluencia sólo si completas, compatibles y con identidad exacta; un prefijo V2/V3 no es censo completo. El roster actual96 configs/32 triadas no es el catálogo amplio completo. No mezclar configuraciones distintas como votos independientes. Mapear todos los estados del ciclo de vida; ampliar catálogo por cobertura target-free/diversidad, no por outcomes.

Optimización propuesta: prefix sums/rings para volumen/trades/presión, deques de extremos, búsqueda por tiempo/secuencia, arrays tipados, partición por sesión y spill privado. Dedupe sólo exacto con historial de aliases; filtros por rangos compartidos después de construir primitives. Motores por intervalos/heaps para respuestas y geometría, con presupuesto explícito de intersecciones. No fastmath, retroproyección o truncación silenciosa. Perfil completo: lectura, classifier, ventanas, estados, joins, labels, matching, ajuste y remuestreo, más almacenamiento y pico de memoria medido.

**Límites de código hoy:** `arrival.py` usa ventana en ticks, no ventanas de segundos; `first_passage.py` usa horizonte en ticks, barrera global y precios enteros, no midpoint en medios ticks/barreras por anchor. Requieren extensión nueva con oráculo sintético, no se describen como implementados. `session_resampling.py` optimiza conteos enteros, no pérdidas Brier flotantes: nueva reducción debe preservar orden/método dentro de tolerancia numérica declarada. La mejora sintética de almacenamiento fue pequeña y no se adopta como aceleración demostrada de mercado.

Presupuesto inicial propuesto por shard P0: wall≤900s, RSS medido≤4GiB, 1–3 sesiones y anchors≤250.000; abortar con recibo agregado de etapa y capacidad, sin eliminar casos silenciosamente. No es estimación de duración ni permiso de ejecución. Congelar capacidad basada en el censo target-free; grandes sesiones pueden requerir partición/spill, no selección retrospectiva. Las cotas del atlas completo y costo por sesión se determinarán por medición, no prometer una corrida rápida antes del perfil. No tocar la V3 activa ni lanzar otra carga grande para competir por recursos.

## 7. Qué devolver al cerebro

Preparar episodios tipados con pregunta/versiones/input/selección/build, fuente/pasajes, todos los intentos, definición y unidad, universo/UNKNOWN/censura, soporte por sesión, efectos y CI/MDE, controles, fallos y decisión. Separar AUTHOR_REPORTED/THEORETICAL_HYPOTHESIS de EMPIRICAL_EXPLORATION; una lectura no es réplica. Registrar negativo/inconcluso con alcance, nunca “absorción funciona/no funciona” universal.

No se crea una memoria alternativa. Esta documentación es propuesta de campaña; entrega al ledger canónico mediante el writer/revisión autorizados cuando estén vinculados, sin autoappend ni autopromoción. No se declara autonomía24/7.

## 8. Pendientes antes de ejecución científica

Fijar fechas/splits contra la selección existente; mínimo de cobertura del proxy e historia; política de gaps/censura; formación/dedupe de episodios; margen práctico y soporte mínimo; clase/modelo/regularización; familia inferencial completa; presupuesto medido y builds nuevos. Emitir preregistro específico y revisión científica, sin repetir validaciones históricas ni exigir paridad NT8 perfecta. Todos los trade dates desde2026-10-01 siguen fuera, sin P&L y sin confirmación automática.
