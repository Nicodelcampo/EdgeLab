# REPORTE INVESTIGACIÓN — 2026-08-04l

## TICKBAR-001: decisiones ejecutadas y handoff operativo

Nico autorizó D1, D2 y D6 del consolidado local.

### Ejecutado en repo

1. Se preservó el clasificador gastado y se creó `tools/tickbar_diag_v2.py`.
2. H2 ahora usa igualdad OHLC directa; `n_events` quedó correctamente en H3.
3. Se agregaron regresiones que vuelven alcanzable `ATTRIBUTION_MISMATCH`.
4. Se registró la enmienda post-oráculo sin hacerla pasar por preregistro original.
5. Se preregistró PRED-004, con Python y el detector económico congelados.
6. Se dejó patch mecánico de rotación del EventLog: sufijo por resolución, índice por corrida, sin append ni overwrite.

### Handoff a la máquina NT8 / Claude

Aplicar `patches/TICKBAR-001_bigtrap2_eventlog_rotation.patch` sobre el tip exacto,
compilar y verificar primero que cada corrida produzca un archivo separado.

El arreglo de atribución no se improvisó en remoto: requiere integrar el matcher
OHLCV único de PRED-004 dentro de `BigTrap2.cs` y probarlo en NT8. Orden obligatorio:

1. tests sintéticos y suite;
2. compilación NT8;
3. `time:1` bit-idéntico;
4. K=25;
5. K=10.

Fail-closed: si un snapshot no tiene exactamente un candidato OHLCV, no se crea
zona y no se elige un offset por conveniencia. Registrar hashes, archivos,
tasas y cualquier abstención. No consultar outcomes.
