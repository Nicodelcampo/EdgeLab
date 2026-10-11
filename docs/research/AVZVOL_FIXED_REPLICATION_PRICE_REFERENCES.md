# AVZVOL: réplica fija y referencias de precio sin racimos

## Resultado

**La combinación focal no replicó su mejora en el segundo contrato.** Se mantuvieron P80/window5/racimo8/1000/20, mínimoD40, vuelta50%, tocar borde, primera salidaD-calificada, ocupación del corredor<25% y un primer disparador por bin6250 registros. Sin reajuste tras inspeccionar labels nuevos.

MNQ12-26: 255/467 = 54.6039%, reproducción exacta del hallazgo de PR113. MNQ09-25 canónico v1: 383/782 = 48.9770% en29 sesiones, con 26 censuradas. Banda exploratoria bootstrap por día del segundo contrato: 45.50–52.49%. La tasa entre resueltas es un primer pasaje observado de ticks, no un fill, probabilidad universal ni rentabilidad.

El criterio fijado antes de inspeccionar labels del contrato nuevo falló: tenía muestra suficiente y al menos20 fechas activas, pero no superó50%, su banda no quedó sobre50% y no mostró incrementos positivos consistentes contra las tres referencias de precio. No se rescata seleccionando otra vecina ni se invierte automáticamente su dirección.

## Alcance ejecutado

Dos contratos: diez sesiones MNQ12-26 ya estudiadas y29 MNQ09-25 de la selección documental.90 grupos de reglas: nueve D/q por cinco orígenes por contrato. D20/40/80 y q25/50/75; endpoint toque y modoD-calificado fijados. 469692 filas de evaluación y 294796 señales brutas no son muestras independientes ni operaciones.360 resúmenes adelgazados,288 contrastes entre real y referencias; sensitividades bin25000, con/sin filtro, conservadas sin elegir una mejor.

Datos originales intactos; cero fugas de fechas autorizadas; ninguna reserva abierta; sin certificación de feed, sin P&L ni promoción. Cuatro contratos adicionales y la campaña completa siguen pendientes. La reejecución de MNQ12-26 reproduce la misma muestra y NO añade datos independientes.

## Referencias que no exigen detectar un racimo

Se añadieron niveles artificiales desde el precio de cierre de la barra256 y cada250 barras completas posteriores de cada sesión seleccionada. Anchos fijos1/10/20 ticks, centrados por convención entera sobre el precio entonces conocido. Generar estos anchors no consulta si existe un racimo ni exige un evento de volumen. Pueden coincidir casualmente con racimos; no se los excluye usando información futura.

Se aplica la MISMA regla de alejamiento/vuelta, barrera contraria simétrica desde el trigger, censura gap10s, espera2000 barras y horizonte post-trigger2000 barras. Running peak disponible al instante, resultado desde el trade siguiente. Se conserva también el control trasladado250 barras del PR113 para continuidad.

**Límite:** widths/posición relativa de los niveles artificiales no son una distribución geométrica exactamente emparejada con nacimientos reales. Frecuencias y contexto pueden diferir; sus contrastes no son intervenciones aleatorizadas ni prueba causal del volumen. Sirven como referencias explícitas de comportamiento de precio sin disparador actual de racimo.

### Comparación primaria

Tasas entre resueltas tras muestreo temporal y filtro; diez y29 fechas respectivamente:

| Origen | MNQ12-26: resueltos | MNQ12-26: toque primero | MNQ09-25: resueltos | MNQ09-25: toque primero |
|---|---:|---:|---:|---:|
| Racimo real | 467 | 54.6% | 782 | 49.0% |
| Trasladado250 barras | 492 | 50.8% | 781 | 46.9% |
| Referencia precio1 tick | 109 | 47.7% | 127 | 49.6% |
| Referencia precio10 ticks | 536 | 48.9% | 771 | 51.0% |
| Referencia precio20 ticks | 617 | 48.9% | 874 | 50.0% |


En el contrato inicial, real supera las referencias ancho10/20 en5.72/5.66 puntos; sus bandas por día no incluyen cero, pero no hay ajuste de multiplicidad y la geometría/contexto difieren. La referencia punto1tick tiene109 resultados resueltos y mucha incertidumbre. El control trasladado inicial tampoco confirma aporte incremental.

En el contrato de réplica, real queda−2.00 puntos frente a ancho10 y−1.02 frente a ancho20. Sus bandas emparejadas incluyen cero (aproximadamente−5.35 a+1.34 y−3.94 a+1.81 puntos). No se afirma una desventaja universal; sí ausencia de confirmación de la mejora focal.

## Contexto y vecinos: conservar el resultado desfavorable

El corredor se mide con rangos de **hasta256 barras cerradas de25 registros Last dentro de la misma sesión**. Es ocupación de precio, no liquidez resting ni volumen exacto por nivel. No se incluye una barra en formación ni se usan precios posteriores al trigger para features.

A D40/q50, el contrato inicial dio51.23% sin filtro y54.60% con filtro; el contrato nuevo48.40% sin filtro y48.98% con filtro. Comparar subconjunto con total no estima causalmente el efecto de filtrar. El lift descriptivo no conserva su magnitud y la combinación filtrada no supera50% en la réplica.

Con q50 y el mismo filtro, D20/D40/D80 en el nuevo contrato:46.89%/48.98%/49.49%, con1495/782/887 resultados resueltos. No se elige D80 porque sea el mejor de tres. Las vueltas vecinas y bin más amplio están publicadas íntegramente.

Cobertura histórica: una señal del foco inicial tenía menos de256 barras cerradas disponibles; ninguna del foco de réplica. Exigir256 completas deja54.72% inicial (466 resueltas) y48.98% réplica (782). No cambia la conclusión. La prueba primaria conserva la definición original de hasta256; esta es una sensibilidad explícita, no un cambio oculto de regla.

## Datos, pins y límite de lectura

Fuente original MNQ09-25: dataset Kaggle canónico versión1, ruta real MNQ/MNQ_09-25_ticks_ext.parquet,296821013 bytes,34508845 registros y SHA256 c78ff5cebeca2130876409b27e00dbb9cab8c0007ab451e4ddb4319088a2be85. Coincide con pin autorizado. MNQ12-26 sigue reexport v2, no se lo sustituyó por canónico v1.

Catalog/resolver v15 fija las fechas. Por sesión, las29 cuentas de fuente completa de MNQ09-25 coinciden exactamente con catálogo. Máscara previa al detector: warmup observado antes de primera fecha seleccionada dentro de la ventana declarada, fechas seleccionadas solamente después; hora16 de mantenimiento fuera del buffer derivado. Fuente cruda no modificada.

Un primer intento se detuvo en una aserción antes de calcular detector/labels de MNQ09-25: comparaba la cuenta de sesión cruda completa con la cuenta dentro de la ventana exclusiva que termina a16h. Había tres observaciones de mantenimiento fuera del cutoff final, todas hora16. Se corrigió la comprobación: comparar cuentas crudas completas con catálogo y exigir que cualquier observación seleccionada fuera de ventana sea mantenimiento ya excluido. Buffer de eventos y política no cambiaron; no fue corrupción del dataset. Snapshot del primer intento y revisión de límites conservados.

El lector genérico de tablas no admite este Parquet binario y reportó error de parseo; no se interpretó como un defecto de fuente. Verificación específica: pin exacto, footer filas/instrumento/contrato/tiempo, orden de secuencia y timestamps en todo el streaming, volumen positivo y reconciliación de selección; QA estructural previa pinneada del PR110/111. No se transforma esto en certificación de reloj, calendario, quotes o feed.

## Verificación y riesgo estadístico

90 estratos origen/D/q en los dos contratos contrastados exactamente con referencia Python separada sobre los mismos ticks ordenados;90 resúmenes de labels recontados desde CSV. Diez celdas primarias verificadas por un camino independiente sort/groupby. Resultado255/467 inicial idéntico al PR113. Memmaps privados redujeron RAM y permiten procesar un contrato por vez sin conservar buffers de los anteriores.

Las señales pueden solaparse incluso tras bins; se remuestrean20000 conjuntos de fechas enteras, por contrato, no filas. Fechas de descubrimiento ya inspeccionadas y criterio nuevo fijo antes de labels de réplica; tampoco se llama test virgen a esta prueba: existe investigación previa basada en barras en el universo. Ninguna apertura del holdout. Bandas exploratorias sin corrección familywise; geometría y contextos de controles no idénticos. No se juntan ambos contratos en una tasa pooled para esconder la caída.

## Interpretación y próximos pasos

Baja la prioridad de D40/q50/corredor<25% como regla universal. El hallazgo inicial puede ser específico de régimen o una fluctuación seleccionada entre numerosas pruebas; estos datos no permiten decidir cuál. Antes de profundizar con más parámetros conviene completar réplicas fijas pre-reserva y diseñar comparación de contexto/régimen con criterios causales disponibles al disparador, separando efecto de precio de aporte incremental del racimo. No se promete que otro contrato rescatará la regla.

Artefactos publicados: código, manifest, criterio, evidencia, cuentas diarias y todas las variantes; no ticks, precios ni secuencias event-level. PR apilado sobre PR113, sin merge. No hay proceso de mercado activo al cierre.
