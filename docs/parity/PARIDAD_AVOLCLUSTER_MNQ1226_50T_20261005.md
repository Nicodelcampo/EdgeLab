# Paridad aVolClusterPOI v0.5 — MNQ 12-26, 50 tick (2026-10-05) — **FAIL (sin causa raíz todavía)**

Oráculo NT8 `data/nt8_oracles/avolcluster_v05_MNQ1226_50t_20260715_20260925.csv` (chart 2026-07-15 → 2026-09-25,
Merge policy **Do not merge**, tz ART; percentil 95, invalidación None, MaxAge 500). `.cs` = versión instalada,
commiteada en `nt8/aVolClusterPOI.cs`. Ticks: re-export NT8 recortado a la ventana exacta del chart
(`MNQ_12-26_ticks_ventana_chart_20260715_20260925.parquet`, 14.711.260 ticks). Informe completo: `paridad_avolcluster_MNQ1226_50t_20261005.json`.

| | Python | NT8 |
|---|---:|---:|
| barras 50t | 294.246 | 294.247 |
| zonas OFF_PRICE | 1.036 | 1.040 |
| pares exactos (tiempo 0 ms, geometría 0) | 804 | |
| geometría distinta (1-7 ticks en un borde) | 127 | |
| tiempo distinto (8-60 s) | 21 | |
| sólo en un lado | 232 | 236 |

STATE_ORDER_DIFF (804) es esperable: el kernel modela creación, no expiración por MaxAge.

Corrida 1 descartada por error de ventana del driver (tomaba el fin del parquet, 30-sep, no el del oráculo, 25-sep,
y arrancaba la calibración el 12-jun): 1.407 vs 1.040. Corregido recortando el parquet a la ventana del chart.

Lectura: las diferencias están repartidas en todos los días (no hay un punto de divergencia que se arrastre) y las de
geometría son de pocos ticks en un borde del cluster → hipótesis principal: **el perfil de volumen por precio de
cada barra (footprint) difiere entre la reconstrucción de NT8 (subserie de 1 tick) y la de Python**, lo que mueve
bordes de cluster y, a veces, cuál cluster es el de máxima masa. Próximo paso: exportar `Bar Profile Log Path` y
`Diag Block Export` de un día (p. ej. 2026-09-24) y correr `paridad_oraculo.py --barprofile/--diag-blocks` para
aislar barra por barra. No se promueve nada hasta tener la causa raíz.
