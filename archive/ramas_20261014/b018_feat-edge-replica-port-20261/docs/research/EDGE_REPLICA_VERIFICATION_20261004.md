# Verificación adicional del snapshot remoto

Complementa EDGE_REPLICA_PORT_20261004.md: después de la primera publicación se reconstruyeron los bytes exactos del port y del helper de activos publicados en 0f48c1ff6a8171f1c3b84c0205f959848ebf75fc. Se compararon sus identidades Git blob con las devueltas por GitHub; ambos coincidieron. Se ejecutaron nuevamente las 27 pruebas sintéticas y py_compile contra estos bytes: PASS.

Esto resuelve la advertencia del primer informe sobre ejecutar pruebas de la lógica del sandbox pero no de los comentarios condensados de la publicación. No equivale a CI de todo el repo, NinjaScript compilado ni prueba de dataset/NT8 real.

La CS original, las 60 reglas, fixture/tests y variantes port/helper fueron entregados en EdgeReplica_EdgeLab_port.zip; las diferencias de comentarios se trazan por el reporte de verificación. No se usaron ni cargaron DLLs/licencias externas.

Persisten los bloqueos reales: acceso a las filas del canónico, custodia/hash, cobertura y liquidez por sesión, controles de procedencia/tick_type y timezone, exposición de las reglas, paridad de órdenes/fills NT8 y mercados time-exit en motor compartido. No se ha reparado físicamente el dataset ni certificado una lista de contratos líquidos. Las barreras nuevas rechazan condiciones inseguras, no transforman un dato desconocido en válido. Los builders históricos siguen pendientes de migración, sin reescribir negativos.

Para el acceso, adjuntar la versión 1 de nicolasbuttaro/edgelab-ticks-nt8-canonical al notebook edgelab-canonical-metadata-audit-20261004. Las fuentes privadas sí son listables; el fallo observado es el montaje en las sesiones no interactivas, no la inexistencia del dataset. No solicitar otra credencial ni adivinar slugs como remedio.
