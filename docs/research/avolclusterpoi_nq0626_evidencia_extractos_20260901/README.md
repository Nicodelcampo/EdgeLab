# Evidencia reproducible — aVolClusterPOI NQ 06-26, tareas 1-3 (2026-09-01)

Extractos mínimos pedidos por el auditor para que `AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md`
sea auditable sin depender de archivos locales fuera del repo. Todos los
archivos `00_raw_*` son exactamente los outputs descargados de los kernels
Kaggle confirmados `COMPLETE` (hashes en `04_kaggle_output_sha256.txt`); los
`01`-`03` son extractos derivados, con la fórmula/fuente documentada en cada
uno.

- `00_raw_zones.json` / `00_raw_creation_blocks.json` — output crudo de
  `avolclusterpoi-tracedump-nq0626` (pin `8bf9fd02861666ec3dc58928b2043223466d5ffe`),
  `run(..., debug_trace=True)` sobre el parquet real completo de NQ JUN26.
- `00_raw_tracedump_kaggle_log.json` / `00_raw_setcmp_kaggle_log.json` — logs
  crudos de ambos kernels (stdout/stderr con timestamps, tal como los
  devuelve la Kaggle API; renombrados de `.log` a `_log.json` sólo para no
  caer en la regla `*.log` de `.gitignore` — mismo contenido byte a byte,
  confirmado por hash).
- `01_tickbar_setcmp_summary.json` — resumen de la tarea 1 (comparación por
  multiset ledger vs parquet), re-parseado del log crudo, no de memoria.
- `02_missing_in_nt8_57.json` — tabla completa de los 57 `MISSING_IN_NT8`:
  `py_id`, score/threshold/ratio del bloque, bucket, `n_history_scores`,
  `n_cells`. Fuente: cruce entre
  `docs/research/avolclusterpoi_nq0626_reports_20260901/paridad_avolclusterpoi_nq0626.json`
  (`sha256=e654ace2...`, ya commiteado) y `00_raw_creation_blocks.json`.
- `03_py_id_372_block_cells.json` — las 66 celdas reales del bloque que creó
  la zona `py_id=372` (el outlier de 8 ticks), más su geometría y la fila del
  oráculo NT8 (`nt8_id=413`) con la que se comparó.
- `04_kaggle_output_sha256.txt` — sha256 de los 4 archivos `00_raw_*` fuente.

Esto no agrega ningún hallazgo nuevo respecto de
`AVOLCLUSTERPOI_PARITY_NQ0626_TASKS123_FINDINGS_2026-09-01.md` — es la
evidencia mínima que ese documento cita, ahora versionada en vez de vivir
sólo en descargas locales de Kaggle.
