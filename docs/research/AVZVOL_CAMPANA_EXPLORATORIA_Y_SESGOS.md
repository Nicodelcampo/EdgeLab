# AVZVOL: autorización exploratoria y controles de sesgo

## Decisión
La fuente queda habilitada para investigación exploratoria por contrato bajo la autorización explícita del usuario. No queda certificada; no se modifica ninguna certificación anterior ni se habilita promoción económica. La procedencia original NT8 no está disponible.

## Corrección de alcance: selección del catálogo frente a archivo completo

La revisión de 560 sesiones-contrato era QA de archivos completos, NO el universo de eventos seleccionado por el catálogo. El cruce posterior verifica las 261 identidades fecha+contrato seleccionadas y sus conteos, sin discrepancias. Las 153 sesiones con menos de 2500 registros están fuera de esa selección; ninguna sesión seleccionada tiene esa baja actividad. Hay 261 fechas seleccionadas distintas: el solapamiento entre contratos del archivo completo no describe la selección operativa.

El salto de 1419 ticks de MNQ09-26 no es de una sesión seleccionada para eventos, pero su fecha está dentro de la ventana nominal de warmup. No se lo borra ni se prueba que sea un error; se separa su posible influencia en calibración del análisis de outcomes. El porcentaje de barras de duración cero comunicado anteriormente es del archivo completo: no se estimó su porcentaje específico dentro de las sesiones seleccionadas.

La campaña exploratoria utilizará la lista versionada de 261 sesiones seleccionadas para sus eventos; el warmup se registra aparte y los intervalos/buckets suficientes se comprueban antes de cada formación. No se hereda automáticamente la selección retrospectiva del resolver como regla de una estrategia causal. Ver [conciliación y alcance](AVZVOL_SELECCION_WARMUP_Y_CORRECCION.md).

## Revisión ejecutada
- 485,596,960 registros de seis archivos físicamente repinados. La auditoría estructural anterior y el censo de fórmula de agresor se reutilizan, sin confundirlos con certificación de feed.
- Nuevo escaneo completo: 560 sesiones-contrato bajo una convención Chicago17h declarada, 325 etiquetas de sesión distintas; 222 aparecen en varios contratos. No son 560 días independientes.
- 153/560 sesiones tienen menos de2500 registros (27.32%). Es diagnóstico retrospectivo, NO filtro de selección en vivo.
- 597,259/19,423,615 barras completas de25 registros duran cero tiempo medido (3.07%). No calcular velocidad infinita ni rellenarla con cero.
- El salto máximo de1419ticks en MNQ09-26 está separado por 2537.44segundos (42.29minutos). Ambos precios están dentro de sus quotes publicados: no prueba un precio falso ni un impulso rápido. Se conserva y se trata como exposición a discontinuidad.
- Revisadas las columnas: un tick es un registro exportado de Last; volumen mayor que1 no lo convierte en varios registros. El reloj duplicado ts_local=UTC no se reconvierte como si fuera Chicago.
- No se eliminaron ni reescribieron ticks. La pausa16–17CT, fines de semana y sesiones escasas se etiquetan; no se declara calendario completo.

| Contrato | Sesiones observadas | Mediana de registros/sesión | Sesiones <2500 | Barras25 con duración0 |
|---|---:|---:|---:|---:|
| MNQ_03-26 | 118 | 781,216.5 | 30 | 2.841% |
| MNQ_06-26 | 123 | 346,092.0 | 39 | 3.407% |
| MNQ_09-25 | 43 | 980,861.0 | 7 | 3.117% |
| MNQ_09-26 | 117 | 242,315.0 | 39 | 3.150% |
| MNQ_12-25 | 82 | 1,213,207.0 | 10 | 2.841% |
| MNQ_12-26 | 77 | 2,894.0 | 28 | 3.033% |

Las ventanas de los contratos son distintas; no atribuir la comparación anterior a deterioro del mercado. MNQ12-26 incluye historia muy escasa antes de ganar actividad; seleccionar por volumen de toda la sesión usaría futuro.

## Controles obligatorios de la campaña
| Riesgo | Mitigación operativa | Incertidumbre residual |
|---|---|---|
| Procedencia, reloj y sincronización no verificables | UTC tal cual, por contrato/versiones; sensibilidad basada en conteo de ticks/barras vs segundos y buckets; publicar hashes | No se certifica reloj, exchange sequence o feed |
| Huecos y saltos | Episodio activo censurado al primer hueco >10s; mantenerlo en denominador. Sensibilidades1s/60s/sin censura; no borrar días por una alarma | Puede ser inactividad real; primeros cruces no observados siguen desconocidos |
| Timestamp empatado/orden local | No deduplicar. Precio usa secuencia almacenada, marcada local. Sensibilidad por grupos de timestamp: cruces opuestos en un grupo ambiguos, no victoria; tiempos0 son faltantes | Orden dentro del grupo no independientemente atestado |
| Imbalance quote-derived | Benchmark de precio sin flow; agregar proxy solo después y medir incremento. Unknown/unclassified faltantes; cobertura por volumen. Sensibilidades sin books locked o spreads amplios | No representa agresor verdadero confirmado ni quotes sincronizadas |
| Contratos simultáneos/roll/liquidez | Nunca concatenar como continuo certificado. Informar por contrato y agrupar incertidumbre por fecha/episodio compartido; no inflar N con configuraciones | Elección de contrato negociable no certificada |
| Filtro de actividad retrospectivo | Solo ventanas cerradas anteriores al trigger; niveles elegidos en entrenamiento. Totales de sesión solo diagnóstico. Mostrar cobertura de todas las señales | Sesiones escasas reducen potencia y cobertura |
| Formación y extremo final | bounds low0/high0 al nacimiento, secuencia de cierre conocida. Peak running; disparo observado. No dar victoria si el target ya fue tocado antes de observar el disparo | No simula fills, latencia o spread de ejecución |
| Barras/detector | Cierre de barras conocido antes de usarlo; reset por sesión explícito y paridad con barras continuas legacy por separado. Window5/10/20/40 recompone footprints e historia; no refiltrar exports | Adapter/footprints no implementados ni benchmark completo todavía |
| Racimos entre sesiones e historia de percentiles | Detectorlegacy conserva historia de racimos entre sesiones: mantener varianteparidad y separarla de reset por sesión. Min20 muestras por bucket conocidas;20 sesiones observadas≠20días calendario. Registrar warmup común vs propio as-of | Diferencias de cobertura no son efecto predictivo |
| Picos que miran a derecha | Inventario incremental causal con available_bar=pivot_bar+right, solo barras cerradas. No usar las zonas finales fusionadas ni estados posteriores de liqpool | Lifecycle de liquidez necesita adapter as-of separado |
| Geometría y censura | Targettouch/enter/cross con opuesta a igual distancia desde triggerobservado; horizontes iguales. Publicar target/opuesta/censura/sintrigger, tasas sobre resueltos Y cotas sobre todos | Mayor50% no prueba ventaja frente al contexto |
| Búsqueda masiva/exposición anterior | Registrar todas las pruebas; tuning solo dentro entrenamiento temporal, purga hasta fin del episodio y embargo máximo horizonte, bootstrap por fechas/episodios, multiplicidad maxT por familias | Los bloques ya vistos no son confirmación ciega |
| Potencia/frecuencia | Ranking inicial por formaciones/episodios/fechas y coberturano por winrate. Señalar <1000eventos o <30fechas como soporte limitado, no ocultarlos ni declarar potencia suficiente solo porN | Millones de definiciones no son millones de muestras |

## Picos: comprobación concreta del repositorio
`edgelab/bridge/indicators/liqpool.py` explica el retardo right, pero sus objetos offline guardan created_bar como barra del último pivote y el tracking empieza desde created_bar+1. Importarlos tal cual como datos conocidos en esa barra adelantaría confirmación y puede usar fusiones posteriores. No se modifica el indicador general: la campaña utiliza un inventario incremental explícito, separado del lifecycle offline.
`causal_pivots.py` pasó3 tests: demora2 barras en caso conocido,8000 comparaciones de prefijos contra find_pivots y conservación de eventos ya conocidos al extender el futuro. Son pruebas de software, no resultados de mercado.

## Ejecución y prioridad
1. Validar adapter optimizado contra referencia, ticks→barras/footprints y límites de cierre; smoke test mercado sin seleccionar resultados.
2. Censo de frecuencia para1536 configuraciones, incluidas18/2000/20 y percentiles80/90/95/97.5 con window5/10/20/40. Compartir16 tapes de zonas,96 variantes racimo cada una; no volver a leer ticks por combinación.
3. Prioridad máxima:45 reglas de retroceso parcial en las5 configuraciones de altafrecuencia declaradas; distancias10/20/40ticks y retrocesos25/50/75%, targettouch a2000barras.
4. Extensión1260 reglas/config y1,935,360 pares nominales: distancias fijas/altura,7retrocesos,3endpoints,6horizontes. Los pivotes, flow, velocidad, recorrido reciente/corridor y coformaciones se prueban como incremento sobre contexto/precio, no solo cortes aislados. ATR, máximofijado y excursionesrepetidas siguen variantes adicionales, no se cuentan falsamente como ya implementadas.
5. Guardar tablas de intentos, señales, censuras y soporte efectivo antes de cualquier ranking de ventaja. No tocar reserva desde2026-10-01niP4/P&L.

## Estado honesto
Autorización exploratoria registrada; revisión de riesgos completada; original ausente declarado. Ninguna combinación nueva produjo todavía resultados de mercado. El adapter optimizado y la campaña masiva siguen pendientes; no se confunde la materialización de matrices con su ejecución.

## Reproducción
`bias_review.py` y `triage_jump.py` requieren PYTHONPATH=/data/analysis/research-runtime y las rutas privadas de sesión anotadas. Son scripts de revisión, no un runner portable. `test_causal_pivots.py` requiere repo en /data/edgelab-parameter-grid. Cruces independientes:6 reconciliaciones de filas+volumen contra censo previo,6 medianas con listas ordenadas, sumas de histogramas,4 fixtures DST. Gate previo permanece byteidéntico. CSV de sesiones y JSON de evidencias adjuntos en esta rama.
