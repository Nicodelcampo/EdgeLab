# Paridad aVolClusterPOI v0.5 — MNQ 12-26, 200 tick (2026-10-06) — **PASS 338/338**

- Oráculo NT8: `data/nt8_oracles/avolcluster_v05_MNQ1226_200t_20260715_20260930.csv`, más `_BARPROFILE` y `_DIAG`.
- Chart: 2026-07-15 → 2026-09-30, Do not merge, tz ART, percentil 95, invalidación None, MaxAge 500.
- Ticks: **re-export NT8 20261005** (`edgelab-ticks-nt8-reexport-20261005/MNQ/MNQ_12-26_ticks_ext.parquet`).
- Informe: `paridad_avolcluster_MNQ1226_200t_20261006.json`. Mismo comando que la paridad de 50t, con `--barras tick:200`.

Resultado: zonas 338 = 338, **MATCHED 338** (creación al ms, geometría 0 ticks, estado y fin).

## Causa raíz del primer FAIL (161/244), del lado de los datos y no del indicador
La primera corrida usó `edgelab-ticks-nt8-canonical/MNQ/MNQ_12-26_ticks_ext.parquet`, que está **incompleto**:
13,4 M ticks en la ventana contra 21,4 M del re-export. **No tiene la sesión del 17-09** y **corta el 28-09** (193 k
ticks contra 2,3 M). NT8 sí tiene esas sesiones, así que las zonas divergían desde el 17-09.
- La paridad de 50t (PASS 934/934) no lo detectó porque su chart terminaba el 24-09.
- AVCL VOL-1/2/3, SR-DIR y DIST **no están afectados**: el RESOLVER prioriza el re-export para MNQ 12-26
  (`edgelab-ticks-nt8-reexport-20261005`), y el log de VOL-1 lo confirma.
- **Riesgo abierto:** cualquier análisis que lea el canónico `MNQ_12-26_ticks_ext` directamente, sin pasar por el
  RESOLVER, ve un contrato incompleto.

Nota: el chart de 200t sólo tiene unas pocas barras por sesión antes del 11-09, porque 12-26 era el contrato trasero.
Las zonas aparecen desde el 14-09, cuando 12-26 pasa a ser el líder.
