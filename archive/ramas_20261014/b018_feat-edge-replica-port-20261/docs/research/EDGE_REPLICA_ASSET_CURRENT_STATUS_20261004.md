# Estado real después de la auditoría física

La descarga autorizada funciona: ya no es necesario pedir montaje manual. MNQ 03-26 canónico v1 se recibió completo (910224741 bytes) y coincide con dos catálogos descargados. El hash del manifiesto individual quedó pendiente de reconciliación de migración/recompresión; no se cambiaron archivos en Kaggle.

Notebook privado v4: 103921542 filas, 208 grupos completos, todos antes de 1774994400000000000 (apertura CME del trade-date 2026-04-01). No se ejecutó estrategia ni se abrió holdout. QC de las columnas requeridas: cero nulos, timestamps no positivos, secuencias negativas, precios/quotes no positivos, volumen negativo, quotes cruzadas, e identidades (ts,sequence) repetidas/no ascendentes. Tick_type observado: trade en todas las filas. No extender estas conclusiones a columnas no inspeccionadas ni al resto de contratos.

Esto NO es SANITIZED_VERIFIED integral: sequence es índice generado; no prueba dedup del evento original. La procedencia UTC/DST, cobertura/calendario por sesión y comparación causal de volúmenes entre vencimientos no están certificadas. Se detectaron candidatos de anomalía de calendario (un tick en fechas de fin de semana, cuatro en 2025-12-25); investigar timestamps y reglas de sesión, no desplazar ni borrar automáticamente.

La variación de cantidad por fecha confirma que tener un contrato en el dataset no basta para usarlo en todo el histórico. Ejemplos en el resumen JSON son observaciones, nunca permisos de liquidez. No certificar completitud por conteo ni seleccionar vencimiento según PnL.

Port: 60 reglas intactas, shadow lógico, sin PnL ni fills observados. Pruebas reproducibles de 31 casos. La fuente original se conserva ahora mediante ocho fragmentos XZ/base64 y source_snapshot.py, con longitud y SHA256 exactos; reemplaza la primera transcripción larga gzip inválida, eliminada. El fallo de publicación no modifica ni invalida la CS adjunta o el ZIP original. Reproducir con python3 -m unittest discover -s tests -p test_edge_replica_port.py -q.

No listo para backtest validado: completar calendario y liquidez causal entre contratos, lector certificado por segmento, ejecución HOLD/netting/rechazos/partials contrastada con NT8 y registro de exposición/splits/multiplicidad. No trasladar MNQ a NQ u otros activos como equivalentes.
