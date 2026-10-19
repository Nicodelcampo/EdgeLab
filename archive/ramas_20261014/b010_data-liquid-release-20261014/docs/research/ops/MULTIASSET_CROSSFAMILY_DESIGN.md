# Campaña exploratoria multiactivo: llegada y confluencia

## Alcance congelado

ES09-26 (índice S&P), GC12-26 (oro),6E09-26 (euro),ZB09-26 (bonos), todos del dataset reexportversion2. MNQ V3 queda como referencia previa, no se repite. Se reutilizan hashes/filas/tick sizes de manifiestos y mediciones existentes: no nueva auditoría de datasets. Ticks/labels/modelos/logs privados permanecen en Kaggle.

72pares principales:18por activo (3AVOLZONEPOI2×3BigTrap2 +3AVOLZONEPOI2×3BigTrap2Absorption),9configuraciones/146representaciones por activo. Los parámetros nativos/historial/edad600s se preservan; no se añaden RACIMO ni grafos de cuatro familias. La aceptación de paridad aproximada del usuario permite explorar; no declara100%medido ni NT8certificado.

## Cronología y comparación

Fuente leída continuamente desde29junio hasta cierre26agosto2026, sin holdout. Calibración propia sin outcomes el31julio;6sesiones de fit3,4,5,6,7,10agosto;12fechas originales de evaluación11,12,13,14,17,18,19,20,21,24,25,26agosto. No reemplazar vacías ni soporte insuficiente. Requiere entrenamiento completo y≥6sesiones evaluables; anclas mínimas100/sesión. Historial mínimo de AVZ20sesiones y BT2A200buckets permanece intacto. Reportar densidad nativa realmente obtenida; parámetros densos no garantizan zonas en cada mercado.

Tick size real por activo:ES0,25;GC0,1;6E0,00005;ZB0,03125. No reutilizar precios/thresholds MNQ. Calibración de proxies con las mismas reglas/quantiles, exclusivamente en la sesión anterior propia; fit/estandarización propios y λ0,01. Sesión CME17CT y comparación RTH son un marco de reloj: RTH corresponde a ventana común cashUS, NO certificado de RTH específico de cada producto. No mezclar anclas, calibraciones, modelos ni resultados entre activos. Diferentes activos no son réplicas causales independientes; calendarios/populaciones distintas impiden afirmar paridad de población con MNQ.

## Preguntas y criterios previos

1. ¿La llegada añade información al control de igual capacidad y al baseline continuo en cada activo?
2. ¿Los parámetros densos aumentan soporte de coincidencias útiles, o sólo abundancia de zonas?
3. ¿Ese aporte cambia por fase común de reloj/dirección, proxiesA/E, edad y relación geométrica?
4.17cortes predefinidos: por cada familia, toque postnacimiento observado, primer toque observado reciente20s, leave-return observado, gapthrough sin print dentro, origenarriba/abajo/dentro; además insideboth con ambosretornos, ambosyaexistentes y ambosprimerostoquesobservadosrecientes. No son primer toque físico ni mecanismos latentes certificados.

La pérdida principal es Brier de3clases con igual peso por sesión; mismo conjunto de anclas por par/modelo/control. Cortes adicionales son pooled por anclas y se explicita soporte de sesiones. Pantalla de soporte antes de outcomes:≥2000anclas pooled y≥6sesiones; pasarla NO es edge ni selección/aprobación automática. Todos18pares/cortes negativos conservados. No ajustar parámetros/regularización al ver ganadores ni excluir fechas por outcomes. Confirmación/P&L/holdout/Brainwriter siguen fuera.

## Optimización y límites

Caché acotado de footprint BT2A por contenido de price/vol/bid/ask del bucket; reproduce exactamente el loop nativo y devuelve mapas inmutables. Historial/percentiles/rowaggregation/activezones permanecen separados por config.2048entradas/200000celdas; evicción recomputa, nunca elimina eventos. La equivalencia sintética conserva conteos, captures,diagnósticos,18matrices actual/espejo y146coeficientes, también con tick sizes de los4mercados. Prueba inventada repetitiva mostró~1,04×en subpaso nativo: no generalizarlo a datos reales ni prometer aceleración total. La medición real de hit/miss/evictions y tiempoBT2A se exporta por activo.

Hasta2intentos pendientes simultáneos,4máximo para esta campaña,1envío por activo,24consultas de estado totales (host≤6por activo). Journals nuevos enlazan V3terminalCOMPLETE, nunca reset/retry ambiguo. No attestation de cuota/custodia global. Por activo:3600srunner/CPU,4500sparent,5400snotebook,4GiBRSS/6GiBAS,100Mticks totales/8Mpor sesión,400000mutaciones pendientes,JSONagregado≤4MiB. No inferir speedup contra campañas fallidas ni contra otro calendario/activo.

## Entrega y continuidad

Paquetes propios CPUprivados, Docker/source/version exactos; boot SHA sella recibo agregado. Public reviewer comprueba cada activo/calibración/censo/aritmética/soporte. Registrar fallos como operativos, no negativos científicos. Archivo de progreso RUNNING no es resultado. Todo será propuesto/revisado en repo; writercientífico canónico y despliegue autónomo siguen desconectados. Consultar MULTIASSET_CROSSFAMILY_LAUNCH/CONTINUATION y journals antes de cualquier siguiente operación; ausencia de un ACK no autoriza reenviar.
