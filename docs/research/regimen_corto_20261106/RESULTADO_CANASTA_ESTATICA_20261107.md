# Canasta estática — libro publicado, sin recomputo de ticks

Estado: PROVISIONAL
Fecha: 2026-11-07
Familia / módulo: `CANASTA_REGIMEN` / régimen corto (`regimen_corto_20261106`)
North Star: sha256 del archivo `docs/NORTH_STAR.md` = `f8e6660fc102c1a6af95916eeddeddc1b0df6b5429cc8e3e2732888ba9cc3930`
Procedencia: `series_diarias_regimen_20261106.json`, agregada por `tools/canasta_estatica_ledger.py`. Salida: `ledger_canasta_estatica.json`.

## Qué es

La canasta que el control de H-REG-1 repetía desde abril de 2026: `PREAPERTURA-ES`, `PREAPERTURA-NQ`, `DRC-YM-4`. Estos números salen de la serie diaria ya publicada. No son un recomputo contra ticks.

| Regla | Muestra completa | Abr–sep 2026 |
| --- | --- | --- |
| PREAPERTURA-ES | 67,31 R / 149 ops / 0,452 R/op | 23,61 R / 59 / 0,400 |
| PREAPERTURA-NQ | 53,49 R / 144 / 0,371 | 22,93 R / 56 / 0,409 |
| DRC-YM-4 | 44,50 R / 102 / 0,436 | 14,59 R / 32 / 0,456 |
| Las tres juntas | 165,30 R / 395 / 0,418 | 61,12 R / 147 / 0,416 |

Ningún día de esas series es `>= 20261001`.

## Por qué no se recomputó la celda

- `PREAPERTURA-ES` y `PREAPERTURA-NQ` usan `ancho_rango` por cuantiles del E0 (`rango_ruptura.VARIABLES`). Esos cortes no están en la serie ni en el módulo. Sin ellos, la coordenada no selecciona los mismos disparos.
- `DRC-YM-4` es familia `DOBLE_RETROCESO`. Ese módulo no está en el checkout.
- `ABSORCION-NQ-3R`, que no es de esta canasta, tiene el mismo hueco: `extension_previa` es por cuantiles y el corte no quedó archivado.

## Holdout

No se abrió. Una apertura de esta canasta pide que el recomputo contra ticks coincida con la serie, y ese recomputo no existe. No hay fila nueva en `docs/holdout_access_log.md`.
