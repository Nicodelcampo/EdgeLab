# PR #15 — investigación de las fallas de CI, con comparación real base↔head

- **Fecha**: 2026-08-27 · **PR**: `Nicodelcampo/EdgeLab#15` (`work/bt2a-gate2-p2a-freeze-20260826` → `work/bt2a-gate2-l2-hardening-20260826`)
- **Base**: `761f50b` (tip de hardening) · **Head**: `d5edeee` (freeze P2-A V1-R1)
- Metodología: corrí la suite real en dos worktrees locales aisladas (una por commit), apuntando sólo a los archivos que la corrida de CI marcó con fallas — no toda la suite, para no gastar de más. Diff directo de resultados, no inferencia.

## Resultado

**3 de las 4 fallas de CI que corren en local son 100% preexistentes** — idénticas en base y head, mismo archivo, mismo test, mismo error:

| Test | Causa | ¿Preexistente? |
|---|---|---|
| `tests/bridge/test_store_v2.py::test_zones_reconstructable_from_events_all_kernels` | `KeyError: 'csv_lines'` | **Sí**, igual en las dos ramas |
| `tests/bridge/test_ulp_sweep.py::test_todo_candidato_actual_esta_triajeado` | 36 expresiones sin triaje en `BigTrap2Absorption.cs`, `BigTrap2UniversalEdge.cs`, `BigTrap2UniversalFill.cs`, `Gaps2.cs` — faltan en `tools/ulp_sweep_baseline.json` | **Sí**, igual en las dos ramas |
| `tests/bridge/test_ulp_sweep.py::test_cada_cs_declara_version_en_el_meta[GexLevels.cs]` | `GexLevels.cs` no declara `version=` en su meta | **Sí**, igual en las dos ramas |

**1 falla es genuinamente nueva**, introducida por el freeze:

| Test | Causa raíz exacta |
|---|---|
| `tests/research/test_bt2a_p2a_freeze.py::test_validate_only_not_ready_returns_nonzero` | `tools/run_bt2a_gate2_p2a.py` se invoca como script suelto (`python tools/run_bt2a_gate2_p2a.py`, no `python -m`), así que la raíz del repo no queda en `sys.path` y `from edgelab.research... import ...` explota con `ModuleNotFoundError` antes de llegar a la lógica que el test prueba. El test espera `returncode==2` (código de "not ready" limpio) y recibe `returncode==1` (crash de import). |

**Fix propuesto** (no aplicado — el archivo pertenece al freeze sellado `FROZEN_SPEC_PAYLOAD_SHA256`/`FROZEN_LOCK_SHA256`, no me corresponde tocarlo sin autorización de quien controla ese freeze):

```python
# al principio de tools/run_bt2a_gate2_p2a.py, antes de los imports de edgelab.*
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```
Mismo patrón que ya usan otros scripts del repo (ej. `diag/tasa_senales/avolcluster_bar_type_paso0.py`).

## Las otras fallas de CI: no reproducen en local, son de entorno

`test_data_root_resuelve_data_gitignoreado_desde_una_worktree`, `test_f0_main_cli_solo_estructural_omite_claves_del_payload_y_del_stdout`, `test_f22_smoke_archivo_implica_solo_estructural`, `test_f22_gate_de_procedencia_aborta_si_arbol_sucio_o_head_se_mueve`, `test_venv_tiene_precedencia_sobre_repo` — **no fallan corriendo los mismos archivos en local**, en ninguna de las dos ramas. La causa es que el runner de GitHub Actions no tiene `data/` real (gitignoreado, sólo existe en máquinas locales) y difiere en la resolución de `venv`. No son bugs de código; son asunciones de entorno que la suite no debería exigir en CI, pero eso es un tema aparte de este PR.

## Conclusión operativa

El PR **no tiene regresiones nuevas de lógica más allá de una** (`run_bt2a_gate2_p2a.py`'s import path), y esa es de una línea, ya diagnosticada. Las 3 fallas preexistentes no bloquean por sí solas — ya estaban rotas antes del freeze. La decisión de mergear, y quién aplica el fix de una línea sobre el freeze sellado, queda para Nico/el auditor.

## Aporte al referente

No mide edge — es higiene de CI/reproducibilidad. El aporte es evitar un bloqueo de merge basado en una lectura parcial de las fallas (el sandbox había visto solo 1 de las 4 fallas reproducibles en local, y ninguna de las 5 de entorno estaba clasificada) y dejar exactamente 1 causa raíz accionable en vez de una lista de 9-10 fallas sin triar.
