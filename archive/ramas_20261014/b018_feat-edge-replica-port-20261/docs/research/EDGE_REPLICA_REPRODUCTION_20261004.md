# Reproducción y límites finales

Desde el checkout: python3 -m unittest discover -s tests -p 'test_edge_replica*.py' -q.

32 pruebas sintéticas locales PASS: port/activos/custodia y forma explícita de nombre NT8. Los ocho fragmentos XZ y su decoder se verificaron contra blobs GitHub y reconstruyen la CS exacta (SHA en rules_v1.json). El snapshot previo 95b149e19d6ba662b702c0388ea04ce738ee98e2 pasó las 31 pruebas contra bytes remotos comprobados; esta revisión añade el caso de alias sin cambiar reglas.

El port conserva 60 reglas, Chicago/DST, referencia por reloj y latencia señal/submission/fill supuesto. No incluye stops/targets inexistentes ni PnL. Aceptar MNQ 03-25 y MNQ_03-25 como nombres explícitos del mismo vencimiento no permite NQ ni otro mes.

Custodia de MNQ 03-26 v1 y QC de 103921542 filas probadas en Kaggle; solo ese contrato. Ni el PASS estructural ni el volumen observado autorizan una sesión/roll: faltan calendario-completitud, procedencia UTC/eventos y comparación D-1 entre competidores. El manifiesto individual de Kaggle sigue legacy; se conservó la reconciliación con los catálogos actuales. No se modificó el dataset.

Antes de evaluación económica hacen falta exports NT8 de barras/órdenes/ejecuciones con contratos, timezone y trading-hours, y declarar los períodos ya usados para construir las reglas. Sin ese contraste no hay paridad broker, independencia de evaluación ni permiso de holdout. Código/fixtures/informes en PR draft, no merge ni promoción.
