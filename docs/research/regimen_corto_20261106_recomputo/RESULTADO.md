# Recomputo contra ticks de la canasta estática (07/11/2026)

Estado: VIGENTE. Etapa ANALIZAR_REGLA con los cortes congelados de las campañas en R (`PREAPERTURA-ES-R`, `PREAPERTURA-NQ-R`,
`DRC-YM-R`), DESC + réplica (ago-2025 → sep-2026), contra `series_diarias_regimen_20261106.json` (rama foundation). Holdout no tocado.

| Regla | Recomputo | Serie publicada | Días con el mismo n de operaciones |
|---|---|---|---|
| PREAPERTURA-ES | 149 ops, 67,3 R | 149 ops, 67,3 R | **149/149, R idéntico** |
| PREAPERTURA-NQ | 144 ops, 53,5 R | 144 ops, 53,5 R | **144/144, R idéntico** |
| DRC-YM-4 | 110 ops, 42,5 R | 102 ops, 44,5 R | 77/84 (mismos 84 días) |

- **PREAPERTURA-ES y PREAPERTURA-NQ: el R publicado sale de estos ticks.** Se cierra el hueco de la auditoría del 07/11 (cortes por
  cuantiles no archivados): son los de `relanzamiento_R_20261102/embudo/*/estado.json`.
- **DRC-YM-4: casi.** 8 operaciones de más en 7 días, con −2,0 R de diferencia. Lo más probable es la versión del módulo con la que se
  generó la serie (DOBLE-RETROCESO tuvo dos correcciones el 04/11). Antes de abrir su holdout hay que fijar la versión.
- La apertura del holdout sigue el protocolo (`edgelab/autopilot/holdout_apertura.py`): una por familia, con acta registrada antes de
  lanzar. **No se abrió.**
