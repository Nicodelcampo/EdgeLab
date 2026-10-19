# Llegadas, respuestas y preguntas científicas: fase siguiente

Estado: propuesta exploratoria e implementación técnica parcial. **No es preregistro final ni autorización de confirmación.** No se aplica a kernel 138386707/v1 ya lanzado. Su código/roster/plan permanecen congelados.

## Qué falta después del piloto geométrico

El piloto actual mide generación de zonas y episodios en 32 triadas, no resultados futuros ni las 24 familias completas. Sus conteos pueden subir sólo por más ocupación del espacio-precio. No seleccionar parámetros ganadores por ese aumento ni inferir ventaja.

1. Construir censo propio de oportunidades de cada tratamiento/control antes de elegir anchors. No definir controles únicamente después de un toque real: cambia el denominador y hereda selección del tratamiento.
2. Separar confluencia geométrica ya reconocida de llegada física. AT_CREATION y AT_GEOMETRY_REVISION no son FIRST_OBSERVED_TOUCH. Revisitas no son observaciones independientes por conservar episodio/origen. GAP_THROUGH_NO_INSIDE_PRINT no inventa un touch.
3. Definir población común de anchors para ablations M0/M1/M2/M3, no comparar modelos sobre subconjuntos incompatibles ni convertir detector/feature UNKNOWN en negativo.
4. Fijar respuesta/escenarios, soporte/MDE, temporal folds, dependencia y multiplicidad antes de outcomes del estudio nuevo. Los datasets ya están resueltos; este punto es definición de experimento, no otra auditoría de fuentes.

## Motor de llegada optimizado, sin cambiar features

`arrival.py` ya mantiene índice de bandas, deque causal y distinción de birth/revision/touch. Ahora calcula las features sólo cuando debe emitir al menos un anchor; todos los anchors del mismo clock comparten el mismo objeto inmutable. No calcula 256 elementos por cada tick sin anchor. No se sustituye suma flotante por otro orden de reducción: net/path/efficiency/elapsed/rate/volume/flow conservan exactamente el algoritmo anterior.

Una copia test-only del motor eager anterior se conserva con SHA256 `345a5fb451bcd4bea872d6c186a859c5263b7150ea677369f408d8d02fb4f890`. Comparación independiente en 10 tapes inventados con 500 ticks y geometría/lifecycle mutable cada uno, incluso volumen fraccional, ns compartidos y flujo desconocido. Tests verifican cero cálculos de features sin anchors y uno al emitir ocho anchors simultáneos. Esto no es medición de speedup real ni cambio del job activo.

## Etiquetado futuro: engine genérico, parámetros científicos pendientes

`first_passage.py` recibe únicamente puntos realmente observados y registra anchors después de observar su tick real. Cada label se ancla a ese precio, usa distancia positiva en ticks y horizonte en cantidad de registros observados, con barreras simétricas. No reconstruye OHLC, no interpola intrabar, no usa fills o P&L.

Resultados:
- UP_FIRST o DOWN_FIRST si el primer print posterior observado alcanza esa barrera.
- HORIZON_NO_PASSAGE sólo si se completa el horizonte observado sin pasaje. Un pasaje en el último tick elegible gana sobre esa categoría.
- GAP_CENSORED, SESSION_CENSORED o EOF_CENSORED mantienen respuesta desconocida, nunca negativa.

El caller debe fijar distance_ticks/horizon_ticks/max_gap_ns; **no se escogieron valores por outcomes, ni se lanzó etiquetado de mercado**. La política de gap interpreta desconocimiento/inactividad, no una certificación de outage. Censor después de pasaje no elimina un pasaje ya observado; censurar el gap anterior evita interpretar un print posterior como primer pasaje conocido.

Upper/lower/deadline heaps comparten una travesía del tape entre anchors en lugar de escanear ticks×anchors. Stale heap entries se compactan con reglas técnicas; IDs/pending tienen límites explícitos sin truncado silencioso. Diez tapes inventados comparados contra un oráculo ingenuo punto a punto, más negativos de horizonte, orden, censura, capacidad y holdout.

## Preguntas que deben responderse, no sólo contar más zonas

| Pregunta | Comparación necesaria |
|---|---|
| ¿El triple aporta algo no aditivo? | M3 contexto+efectos individuales+llegada+interacciones frente a M2 sin interacciones, sobre los mismos anchors; Brier OOS emparejado propuesto. |
| ¿Es sólo mayor densidad/ocupación? | Censos propios y controles de geometría/ocupación/exposición comparables, no “más coincidencias = edge”. |
| ¿Importa el orden de formación? | A→B→C frente a simultaneidad/otros órdenes, clocks de reconocimiento originales, sin birth retroactivo. |
| ¿Importa cómo llega el precio? | Dirección, net/path/efficiency/rate y velocidad observables al anchor; bins y transformaciones train-only. |
| ¿Volumen/flow/revisitas agregan información? | Ablaciones incrementales individuales y conjuntas; proxy de flujo desconocido sigue UNKNOWN; dependencia por episodio/sesión. |
| ¿Los racimos agregan algo respecto de AVZ? | Comparación condicional: racimos derivados de AVZ no son un segundo voto independiente. |
| ¿Se mantiene entre tiempo/contratos/geometrías? | Validación temporal/natural-contract, fuera de la geometría primaria por separado; no certificación con una sesión. |
| ¿Las zonas heredadas se comportan distinto? | Brazo carry separado, no mezcla silenciosa con exposición nacida en la sesión. |

Un Brier multiclase upper/down/neither es compatible con el engine propuesto, pero no sustituye silenciosamente el estimando aún propuesto en el diseño. Resolver manejo de censura y población común antes de fijar métrica: filtrar casos según respuesta conocida puede cambiar el estimando. Pointwise intervals no son significancia global. Jerarquía de familias y procedimiento dependiente maxT/stepdown siguen pendientes, sin inferir N efectivo de Jaccard o número de filas.

Holdout/cualquier reserva de confirmación permanecen cerrados, EXPLORAR ≠ CONFIRMAR. El EdgeBrain canónico y su ledger no se modifican ni aprueban candidatos por estos engines.

## Racimos: selección equivalente sin el paso cuadrático

La regla literal `_racimo` de foundation conserva su SHA256 `846aab2ee62074f91de17a64bf8b7ade3efbb5a842cf8ba36a9677ede6a33efe`. El adaptador nuevo sustituye sólo la búsqueda de la banda con más miembros: sweep por low + Fenwick sobre high, O(n log n) en vez de contar todos los candidatos para cada banda. Al elegir el máximo recorre el **orden original reversed-history + new-zone**, por lo que preserva desempates y el orden de asignación/elección de racimo anterior. No ordena el historial detector ni poda sus miembros.

La ventana temporal nativa ya cortaba al llegar a un bar fuera de ventana; no se atribuye un speedup a eliminar un scan histórico que no existía. Clusters, membresías, carry, snapshots y clocks de reconocimiento siguen iguales. Modo `optimized_candidates=False` ejecuta la función literal para referencia. Ocho tapes inventados de 240 batches, caso denso de 400 geometrías repetidas y casos límite comparan outputs y estados. Las snapshots completas aún cuestan O(miembros); no afirmar speedup global, menos memoria total o mejora real de Kaggle sin medirlos.

Cambio reservado para la siguiente versión: **no se modificó el kernel 138386707/v1 activo** ni se recalculó su provenance con source nueva.
