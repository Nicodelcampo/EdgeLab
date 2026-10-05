# Paridad aVolClusterPOI v0.5 — MNQ 12-26, 50 tick (2026-10-05) — **PASS 934/934**

Oráculo NT8 `data/nt8_oracles/avolcluster_v05_MNQ1226_50t_20260715_20260925.csv` (sobrescrito en la 2.ª carga:
chart 2026-07-15 → 2026-09-24, Merge policy **Do not merge**, tz ART, percentil 95, invalidación None, MaxAge 500)
+ `BARPROFILE` y `DIAG` del mismo chart. `.cs` = versión instalada (`nt8/aVolClusterPOI.cs`). Ticks: re-export NT8
`MNQ_12-26_ticks_ext.parquet`. Informe: `paridad_avolcluster_MNQ1226_50t_20261005.json`.

Reproducir:
```
python tools/paridad_oraculo.py --indicador avolclusterpoi --oraculo <oráculo> --parquet <MNQ_12-26_ticks_ext.parquet> \
  --desde-ns <2026-07-14 19:00 ART> --hasta-ns <último cierre del oráculo + 1 ms> --excluir-pausa-cme \
  --footprint-nt8-subserie --chart-tz America/Argentina/Buenos_Aires --barras tick:50 \
  --param max_age_bars=500 --param detection_percentile=95.0 --out <json>
```
Resultado: barras 254.318 (NT8 254.317 + barra parcial final), zonas 934 = 934, **MATCHED 934** (creación al ms,
geometría 0 ticks, estado y fin por MaxAge idénticos).

## Causas raíz encontradas (en orden) — todas del lado de la reproducción, ninguna del indicador
1. **Ventana**: el driver tomaba el fin del parquet (30-sep) y no el del oráculo; y el chart "desde el 15-jul" carga la
   sesión CME del 15-jul, que abre el **14-jul 19:00 ART**. → `--desde-ns/--hasta-ns`.
2. **Merge policy**: con "Merge back adjusted" NT8 usa MNQ 09-26 ajustado antes del roll; la paridad exige "Do not merge".
3. **Footprint desde la subserie de 1 tick** (la mayor): NT8 procesa los ticks con timestamp IGUAL al cierre de una
   barra primaria DESPUÉS de esa barra → caen en la barra siguiente; y descarta los que quedan fuera de [low, high].
   Con esa regla el perfil por barra coincide en 99,35 % (vs 19,7 % con la asignación real). → `build_footprints(...,
   nt8_subseries=True)` / `--footprint-nt8-subserie`. Pasó de 727 a 869 exactas.
4. **Pausa CME**: un tick a las 16:00:00.040 CT (2026-09-23) que la plantilla ETH no incluye; en Python abría la sesión
   siguiente y corría los bloques de 10 barras de todo el 24-sep (4.498 bloques). → `--excluir-pausa-cme`. 934/934.
5. **Ciclo de vida**: el kernel no implementaba MaxAge; agregado idéntico al `.cs` (`max_age_bars`, 0 = sin cambio).

Alcance: valida creación OFF_PRICE + expiración MaxAge en MNQ 12-26 50t con estos parámetros. No valida AT_PRICE,
FIRST_TOUCH ni invalidación CloseThrough/FirstTouch (no ejercitadas con invalidación None). Holdout no tocado.
