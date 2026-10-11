# AVZVOL: recuperación y reauditoría de fuente de ticks

## Resultado real, sin desbloqueo ficticio
**Acceso físico recuperado y auditoría estructural completa PASS en485596960ticks. La campaña de hipótesis de mercado todavía NO se ejecutó y los gates de fuente NO se cambiaron.** La autorización explícita actual permite preparar/auditar la campaña; no demuestra por sí misma que el reloj o la procedencia upstream sean correctos.

Se descargaron los6archivos fijados, no latest: canonicalv1para09-25/12-25/03-26 yreexportv2para06-26/09-26/12-26. Todos los hashes, bytes y footers concordaron; barrera global de6archivos antes de payload. Todos estrictamente anteriores a la reserva. No se abrió holdout ni se reescribieron originales.

## Auditoría de archivos completos
| Contrato | Filas auditadas | Errores estructurales |
|---|---:|---:|
| MNQ03-26 | 103921542 | 0 |
| MNQ06-26 | 116002246 | 0 |
| MNQ09-25 | 34508845 | 0 |
| MNQ09-26 | 110632331 | 0 |
| MNQ12-25 | 99091418 | 0 |
| MNQ12-26 | 21440578 | 0 |

Controles: nulos, tipos/identidad, orden temporal y secuencia local, precio/volumen/quotes válidos, book no cruzado, agresor de enum permitido, identidad de origen no duplicada. La repetición independiente reproduce exactamente los errores y advertencias de la auditoría anterior sobre los mismos bytes.

Advertencias conservadas:298243543timestamps repetidos,562books locked y659agresores no clasificados. Un timestamp repetido no es un trade duplicado: se conserva secuencia, no se borran prints. La secuencia local no acredita continuidad ni secuencia del exchange.

El profiler genérico intentó leer los6Parquets y devolvióParserErrorpor falta de soporte del formato. No se interpretó como corrupción: lecturaArrow, hashes/footers y auditoría nativa completa fueron válidos. Los manifiestos anidados se revisaron por claves/grano, no se trataron como filas de trades.

## Dos puntos aclarados por la auditoría de procedencia
### Reloj
Se recuperó código candidato del exportadorEdgeLabTickHistoryy del parser: conversión desde la zona configurada enNT8aUTC, texto.Last.utc.txty parseo a nanosegundos. El productor copia eseUTCtambién a ts_local_ns; la igualdad es intencional, no prueba automática de un reloj erróneo.

El reexport declara días localesUTC−3y lee manifest.jsonl. Los manifiestos Parquet/Kaggle disponibles no incluyen las líneas originales del AddOnconnt_timezone,output_timezone,build,connectionsyhashdiario. Recuperar código correcto no demuestra québuild/zona se usó en cada export real. Por eso no se inventa certificación del reloj.

Código recuperado:exportador/parser candidatos enf397a318be8b0acf68789070fe8064d83e172f7d; productor de reexport identificado en6716ddbf. El contenido del manifiesto06-26v2nombra tools/nt8_reexport_merge.py, pero no contiene attestación del código consumido ni la procedencia NT8original por día.

### Agresor
Se revisaron TODOS los485596960ticks comparando el agresor con la fórmula recuperada:buy si precio≥ask;sell si precio≤bid;si no,no clasificado. Hubo211diferencias de texto, todas equivalentes unknown/unclassified; al distinguir el alias hay0inconsistencias semánticas. No se cambió el archivo ni se asignó dirección a desconocidos.

Esto permite definir con precisión un **proxy de imbalance basado en quotes**, no afirmar agresor verdadero del exchange ni sincronización perfecta de bid/ask. Los books locked también requieren recordar la prioridadbuy de esta fórmula, no tratarlos como verdad direccional independiente.

## Estado de desbloqueo
- Acceso/hash/estructura: PASS, archivos locales recuperados.
- Método de agresor de quotes: consistencia numérica comprobada; verdad upstream no certificada.
- Convención horaria del código: recuperada; uso real por cada día todavía no atestado.
- Calendario/continuidad/completitud/selección causal: no se certifican mediante una auditoría de bytes. Un estudio por contrato separado no implica que un roll continuo sea elegible.
- Reserva y prohibición de promoción/P&L: conservadas.
- Nuevos outcomes/trials de hipótesis:0. No confundir pruebas sintéticas anteriores o QA de precios con resultados de estrategia.

**Para cerrar el replay estricto falta el manifest.jsonloriginal del AddOnde las fuentes, conbuild/zona/outputtimezone/feed/hash, y su enlace a las entradas del productor.** Si el usuario elige una campaña explícitamente exploratoria con relojUTCdeclarado, quotes inferidos y sesiones observadas no certificadas, se necesita registrar ese cambio de estándar como tal: no llamarlo fuente independiente certificada ni cambiar silenciosamente los gates anteriores. Ese alcance no ha sido aprobado específicamente todavía.

## Todas las combinaciones enumeradas, NO ejecutadas
Se materializaron2matrices:1536configuraciones detector/racimo y1260reglas de retroceso parcial. Su producto contiene1935360definicionesconfiguración×regla; NOson1935360observaciones independientes ni pruebas ya realizadas.

La matriz cubre los5parámetros (mínimo, ventana del racimo, altura,percentil,window_bars),10distancias (5ticks fijos y5relativas ah),7porcentajes de vuelta,3endpoints (toque/entrada/cruce) y6horizontes (3en barras/3en segundos). La implementación completa optimizada de toda esta campaña todavía está pendiente; existe el evaluador puro de referencia y su validación sintética, no un motor de millones de pruebas aprobado.

Otros cruces solicitados que se conservan como hipótesis: velocidad/barras por distancia,delta de quotes,estructura de vuelta y picos confirmados asof,memoria espacial del corredor,coincidencia multiescala y comparación con mercado reciente sin racimo. Sus indicadores/cortes deben construirse causalmente y fijarse en entrenamiento, no añadir millones de cortes elegidos por outcome.

Priorizar frecuencia/soporte antes de consultar outcomes; conservar configuraciones y señales sin trigger/censuradas. Compartir agregación porwindow_bars,cintas de zonas porpercentil/windowyestados de barreras para evitar escanear los485millones de trades por cada definición. No se afirma aceleración de ese motor todavía. Corrección de multiplicidad/dependencia por día y validación temporal obligatorias antes de presentar un resultado como ventaja; rentabilidad no se desprende sólo de primeras llegadas simétricas.

## Evidencia
preflight.json fija versiones/hashes/filas y frontera. structural-evidence.json contiene las6auditorías y cotejo previo. quote-method-audit.json separa diferencias de texto de discrepancias semánticas. readiness.json distingue autorización, acceso, certificación y campañas sin ejecutar. CSV conservan el grid completo; no hay resultados inventados ni certificados sellados a mano.

Reproducción de QA: auditor existente tools/audit_kaggle_raw_ticks.py con pins del preflight yclockdiagnostics; primero hash/footer de TODOS los6archivos. Los scripts usados para QA se conservan, pero usan rutas de esta sesión de cómputo; no son el adaptador de mercado ni una API de desbloqueo.
