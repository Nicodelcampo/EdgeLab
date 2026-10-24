# Estado del resolver frente a Kaggle

Estado: VIGENTE (2026-10-22)

Desde el 2026-10-22 el resolver (`RESOLVER.json`, esquema `EDGELAB_RESOLVER_V2_RELEASE`) sale del índice de sesiones del release
canónico `nicolasbuttaro/edgelab-liquid-ticks-20261014` (manifiesto `db9c42cd…`, aprobado para research el 2026-10-14), con
`tools/resolver_desde_release.py`. Todas las sesiones apuntan a un solo dataset (`data/<ACTIVO>_ticks.parquet`).
El resolver anterior apuntaba a 10 datasets marcados REEMPLAZADO/CUARENTENA en Kaggle; los archivos `scan__*` de este catálogo
describen esos datasets viejos y quedan como historia.

Verificado de punta a punta con 6B (archivo real del release, SHA igual al manifiesto): `edgelab_data.load_ticks` lee 291 sesiones y
8.999.265 filas, igual que el release, y la fecha de sesión coincide con `trade_date` en todas las filas.
