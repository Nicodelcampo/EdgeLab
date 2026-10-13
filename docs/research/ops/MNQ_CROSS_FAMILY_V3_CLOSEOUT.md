# Cierre real de AVOLZONEPOI2 × BigTrap — V3

Corrida privada CPU138540378/v1 COMPLETE; identidad/fuente/versión y SHA del resultado verificados. Finalizaron los18pares/146representaciones, sin truncar eventos ni reducir configuraciones. Conciliación de población y baseline previa PASS.35,86min host;35,65min runner; RSS pico de runner1,66GiB. Este éxito verifica la corrección para esta campaña, no todo futuro grid.

## Resultados nuevos

Dos sesiones de entrenamiento y10de12fechas originales disponibles,70.544anclas compartidas;las fechas vacías2026-06-18 y2026-07-02 no se reemplazan. Fechas previamente observadas: sólo desarrollo. Media principal: igual peso por sesión, no por número de anclas. Brier de tres clases: menor es mejor.

Modelo continuo:0,601464829391. Ninguna de las144representaciones con zonas mejoró su Brier medio. Modelo completo por par: delta entre+0,001973299 y+0,006857959. Esto limita la representación/modelo/calendario medidos; no demuestra que toda zona carezca de información.

| Contraste fijo | Pares con mejora media /18 |
| --- | --- |
| Densidad−continuo |0|
| Geometría−control de igual capacidad |2|
| Llegada−control de igual capacidad |17|
| Interacciones−control de igual capacidad |4|
| Completo−control espejo |7|

La llegada mejora17/18medias contra su control de capacidad, pero no el resultado neto contra el modelo continuo; su dirección por sesión sigue heterogénea. Las mejoras pequeñas de interacción incluyen A3×X2 en8/10sesiones (ΔBrier×1000≈−0,145794), mientras el modelo completo de ese par empeora el baseline≈+6,628082. El espejo no es un creador independiente zone-free: no atribuir ventaja causal a zonas por vencerlo.

## La hipótesis de aumentar coincidencias

A1×B1 (AVZ25denso×BT2denso) está dentro de ambas exposiciones en28.211/70.544anclas (39,9906%); A2×B2 (ambas referencias) en12anclas (0,0170%). Los perfiles densos sí dan muchísimo más soporte a coincidencias; esa abundancia no produjo mejora media predictiva. Se trata de exposiciones primarias hasta600s con removals nativos BigTrap, no liveness nativa AVZ.

Todos los pares, controles y conteos están en PAIR_SUMMARY/SESSION_DELTAS/DESCRIPTIVE_CUTS. El análisis conserva430cortes descriptivos y deltas completo−baseline. Algunas excepciones favorables ocurren sin uno de los componentes, por lo que no respaldan superposición. El estado proxy BOTH absorción/exhaustion tiene apenas16anclas en8sesiones; el corte A3×B2con ambas edades≤20s tiene58anclas en8sesiones. No convertir estos hallazgos inspeccionados/solapados en edge.

## Aprendizajes operativos y siguiente optimización

V1/V2 tenían un contador acumulado global entre9configuraciones, no400001eventos del perfil que estaba activo al fallar. V3procesó hasta426.387mutaciones en una sesión con máximo pendiente de2.141por lote. Son unidades distintas: no presentar su razón como aceleración o ahorro de RSS. El transportepin volvió a pasar, no se repitió QA de datasets.

BT2A consumió986,010s (46,09%del runner); todos los tiempos nativos/clasificación/primitivos suman1.520,614s. Fit sólo4,973s. Prioridad: preprocesamiento de buckets compartido para Tape25/Tape50, conservar historial/estado independiente por config, comparar eventos/variables/fits exactamente antes de otra ejecución. El remanente no tiene separación completa read/context/scoring: perfilarlo antes de atribuirlo. No anunciar factor de speedup frente a versiones abortadas.

Siguiente pregunta útil: en qué contexto llegada/aproximación aporta información residual reproducible, y qué escenarios tienen soporte suficiente. Antes de otro grid enorme, congelar criterios de soporte y contraste, no seleccionar sólo cortes que salieron positivos. Confirmación fuera de estas fechas requiere protocolo separado; holdout≥2026-10-01 sigue cerrado. No lanzar automáticamente otra corrida.

## Evidencia conservada

MODEL_RECEIPT_PACKED es gzip-base64 de JSON agregado público, no ticks/modelos/logs. Conserva exactamente4.045.861bytes y SHA8ce5e384c4b8c2bb4d4eb797a6d52e88c0eb03a55f89c9dc634e63019187a53b. Para reconstruir: leerJSON, base64decode campo data, gzip.decompress y verificar decompressed_sha256 antes de ejecutar review_crossfamily_models contra PLAN_V3/ROSTER/baseline.

Propuesta de conocimiento registrada, outcomes_inspected=true, NO escritura científica canónica ni despliegue autónomo. Journals deV3 terminalesCOMPLETE; los anteriores permanecenERROR/diagnósticoCOMPLETE. No reset/rerun. Gráfico:preflightPASS,9capturas examinadas;3variantes visuales no verificadas por timeout, sin reintento.

Reproducción de análisis público: después de verificar y descomprimir el archivo, ejecutar `python docs/research/ops/scripts/analyze_crossfamily_v3.py --receipt /ruta/crossfamily-receipt.json --roster docs/research/ops/MNQ_CROSS_FAMILY_PARAMETER_ROSTER.json --out /ruta/agregados`. Este script no tiene red ni lee ticks; usar después de review_crossfamily_models. CHART_SPEC conserva todas las series derivadas y sus controles.
