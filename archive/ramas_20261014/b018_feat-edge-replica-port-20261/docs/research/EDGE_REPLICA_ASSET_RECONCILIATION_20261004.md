# Custodia y reproducción del port

## Acceso recuperado

El notebook privado edgelab-mnq-custody-metadata-bridge-20261004 descargó metadatos y el Parquet MNQ 03-26 v1 por enlaces autorizados. Esto supersede el bloqueo de montaje/manual-attach del informe previo: el montaje original sigue fallando, pero existe una vía de lectura real. No publicar los enlaces firmados.

## Discrepancia real y resolución acotada

Se recibieron 910224741 bytes, SHA256 1b3f6f17fbc1c189d627292bf8b1922ce58b7097a42ab498b546d36ad3b37afa. Coincide con files.sha256 y AUDIT_MANIFEST.json descargados. El manifiesto individual conserva 9a0225520591dd599857d3bcfad3ab8e0af30e053a9fb53f67e66131fe90c71c: discrepancia postcompresión/migración pendiente de reconciliar. El catálogo declara original 1995466586 bytes, comprimido 910224741, 103921542 filas. NO afirmar equivalencia semántica por tamaño/conteo ni corrupción por usar exclusivamente el hash legacy.

La primera auditoría se detuvo ANTES de interpretar filas al encontrar la discrepancia. Se conserva ese intento (notebook v2), y el contraste de las dos autoridades de identidad actuales (v3). El hash actual es identidad de la versión recibida, no certificado de saneamiento/UTC/calendario/liquidez. La QC posterior requiere declarar ese catálogo como fuente de identidad y mantener el conflicto legacy visible. No sobrescribir el historial.

## Cambio ejecutable

stream_safe_preholdout requiere ahora expected_file_sha256 explícito: verifica custodia antes de pyarrow/filas. El archivo debe ser inmutable durante la lectura. Seguir exigiendo límite de campaña, fechas permitidas, cobertura completa, semántica LAST/volume y selección causal de contrato. Esto no migra automáticamente los builders viejos.

## Pruebas

31 pruebas sintéticas locales PASS; 27 de lógica/activos y 4 de custodia. Fuente C# original comprimida sin pérdida en tests/fixtures/edge_replica/EdgeReplica.cs.gz.b64; SHA original se valida contra rules_v1.json. No ejecuta ni instala NinjaTrader.

Ejecutar desde el repo: python3 -m unittest discover -s tests -p test_edge_replica_port.py -q

El lector de mercado y el motor de fills/HOLD compartido siguen pendientes de validación: no presentar el shadow como PnL o paridad NT8 demostrada. Mantener PR como draft; holdout cerrado.
