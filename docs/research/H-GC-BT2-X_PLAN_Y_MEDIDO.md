# H-GC-BT2-X — plan y lo ya medido

Campaña **exploratoria**. No confirma. No corona edge.
Handoff: `docs/research/HANDOFF_2026-08-21_SANDBOX_AUDITOR.md`.

## Objeto (lo que Nico quiere medir)

Un **trade**, no una carrera ±B.

- Señal: TRAP / burbuja al **cierre** de la barra (`BARRA_PROCESADA`).
- Entrada: **primer tick posterior**. Camino = ticks crudos.
- `trapped_sellers` → largo; `trapped_buyers` → corto.
- Gestión: SL / TP / BE (SL a entrada tras +X ticks de MFE).
- 1 tick GC = 10 USD. Fricción **medida** cuando haya L1/L2; hasta entonces
  supuesto 1,5 t ida y vuelta, etiquetado.

`SizeScaling` / `TopPercentFilter` **fuera** de la población.

## Capas

| capa | estado |
|---|---|
| 0 identidad / relojes | DEC26: +3 h, match 100 %. L2 GC: semántica pendiente |
| D overfitting holdout 17–21 ago | HECHA. MFE≈MAE. Sin feature PRE. No elige |
| vela siguiente | HECHA. 47,4 % a favor. No es continuación |
| barrido 8 frames × SL/TP/BE | HECHO en 5 días jun. Probe, no capa 4. No es edge |
| 1 plantilla fija más discovery | FALTA N (piso ≥200 burbujas, ≥10 sesiones) |
| 2 familia gestión | no coronar el top del probe |
| 3 params indicador | kernel del repo u oráculos nuevos |
| 4 tickframes de verdad | mismo piso de N |
| 5 un filtro de contexto | después; L2 solo si P-59 cierra |

## Artefactos

- `docs/research/h_gc_bt2x_path_overfit.json`
- `docs/research/h_gc_bt2x_next_bar.json`
- `docs/research/h_gc_bt2x_sweep_frames.json`
- `docs/research/h_gc_bt2x_oracle_inspect.json`
- `docs/research/h_gc_bt2x_ticks_inspect.json`
- `diag/tasa_senales/h_gc_bt2x_*.py`
