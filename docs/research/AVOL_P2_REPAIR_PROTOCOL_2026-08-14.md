# aVolClusterPOI — Protocolo de reparación P2 v0.1

**Estado:** `ABSTAIN_P2` — parche de grilla de sesión 0 listo, P2 no recorido.  
**Run previo:** `e7602fe6` — 50/53, sello `feaa9cc9…`  
**Parche:** `d89b3a7e` runner + `eaaa55c5` tests.

Autopsia local (parquet `6ffcdf04…`): los 3 clusters NT8 existen en las celdas.  
Dos caen por warmup Python (18 y 19 muestras). Uno por umbral (1107 vs 1550).  
Causa: el parquet arranca 22:03 CT y NT8 a las 22:00; el first-10-seen desfasaba toda la sesión 0.

## Parche

Si la primera sesión no abre en un múltiplo de 10 minutos desde las 17:00 CT, se descartan barras hasta el próximo borde (22:10). Las sesiones completas que abren 17:00 no cambian. El gate sigue siendo 100% uno-a-uno. Formal bloqueada.

## Recorrer P2

```bash
git pull
python diag/tasa_senales/avolcluster_p2_replay_v01.py \
  --parquet "D:\EdgeLab\data\nt8\6E\6E_09-26_ticks.parquet" \
  --oracle data/nt8_oracles/avolcluster_v05_junio2026.csv \
  --out diag/tasa_senales/AVOL_P2_replay_v01.json
```

Mandar `label`, matched, unmatched y `first_session_clock_trim`. No formal hasta `P2_PASS`.
