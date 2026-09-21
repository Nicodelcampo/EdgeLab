# Visores y herramientas retirados — 2026-09-21

**Decisión de Nico, 2026-09-21:** una única versión del visor (`viewer/nt8_bridge/index.html`).

| Retirado | Motivo |
| :-- | :-- |
| `hz2a/`, `visor_server.py` | visor v2 de agosto con backend propio; no figuraba como no canónico y competía con el canónico |
| `hft_corridor_preview.html` (+ `tests/test_hft_viewer_playwright.py`) | tercera implementación de corredores, sin certificar; el botón que navegaba a ella se quitó de `index.html` |
| `parches_apply/` | herramientas que aplicaban parches a `index.html`; los parches **ya están en el archivo** y sus aserciones sobre el resultado se migraron a `tests/research/test_unified_viewer_invariants.py` sin debilitarlas |

**No se archivó** `tools/build_hft_corridor_bundle.py` ni `viewer/nt8_bridge/hft_nq_bundle.js`: los usan
`tests/research/test_hft_corridor_bundle_guard.py` (guard de holdout) y `tools/rank_hft_corridor_configs.py`.

`diag/tasa_senales/visor_*_export.py` exportaban a `viewer/hz2a/`; quedan como historia y ya no tienen destino.

Recuperar: `git mv archive/viewer_retirado_20260921/<ruta> <ruta_original>`.
