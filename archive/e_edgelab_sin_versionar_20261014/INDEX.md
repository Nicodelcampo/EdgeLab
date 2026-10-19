# Archivo de lo que sólo existía sin versionar en `E:\EdgeLab` (2026-10-14)

Estado: VIGENTE
Fecha: 2026-10-14

`E:\EdgeLab` (rama `claude/focused-fermat-qjt805`, 376 commits detrás de `foundation`) tenía trabajo sin commitear que no estaba en ninguna rama. Para que no dependa de ese directorio:

- `cambios_sin_commitear_vs_HEAD_7d474714.patch` — diff de `.claude/launch.json`, `viewer/nt8_bridge/bundles/manifest.js` e `index.html` (capa ESPEJO-IND del visor y calibración de zonas espejo) contra el HEAD de esa rama. **Es un parche contra una base vieja**: para aplicarlo hay que rebasarlo sobre `foundation` y revisar conflictos con el visor actual.
- `archivos/` — 31 archivos sin versionar (≤ 2 MB): scripts (`tools/apply_viewer_*`, `audit_post_espejo_excursion`, `build_mbt_mym_espejo_bundles`, `upload_nt8_canonical_kaggle`, `run_h2_and_suspend.ps1`), `kaggle_nq_rehash/`, `EdgeReplica.cs`, catálogos de sesiones de regímenes de contrato (MES/MNQ/MYM/RTY/YM), la nota `IDEA_IPC_ENTRADA_CREACION_Y_VSHAPE_20260929.md` y los JSON de análisis de `data/nt8_oracles/` (censo de zonas NQ, decaimiento/estabilidad/rechazo de clusters, paridad, auditorías EMA).
- `OMITIDOS.txt` — archivos > 2 MB (oráculos CSV, un sqlite de 1 GB y `hft_nq_bundle_certified.js`). Son **datos locales por política** (no van a git): respaldo en `D:\_BACKUP_ORACULOS_20261014` (72 archivos, 4,07 GB) con SHA-256 en `ORACULOS_BACKUP_SHA256.csv` y tamaños verificados contra el origen (0 diferencias). Igual que el L2, es una segunda copia en la misma PC.

Esto es archivo, no vigente: el visor y los scripts vigentes viven en `viewer/` y `tools/` de `foundation`.
