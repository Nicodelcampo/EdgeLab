# ENVIRONMENT — EdgeLab (F0B: entorno reproducible)

## Máquina / intérprete
- SO: Windows 11 (10.0.26200), 64-bit.
- Python: **3.12.10** 64-bit (`...\Programs\Python\Python312\python.exe`).
- CPU: Intel i5-1135G7 (4 cores / 8 threads).
- **Política dura: el Python global NO se toca.** Todo corre en venvs aislados creados con `python -m venv`. Prohibido `--system-site-packages`, y prohibido instalar/actualizar/degradar paquetes globales.

## Toolchain pinneada (para regenerar locks)
- pip **25.0.1**, setuptools **83.0.0**, pip-tools **7.6.0** (venv de tooling; ver comandos).

## Grupos de dependencias (`pyproject.toml`)
- **core** (siempre): numpy, pandas, numba, pyarrow, pydantic.
- **bridge**: duckdb, polars.  · **cli**: typer.  · **dev**: pytest, hypothesis.
- **validation**: scipy, arch.  · **research-vectorbt**: vectorbt (pesado, ~42 deps; opcional).

## Lockfiles (pip-tools, `--generate-hashes`)
| Lock | Contenido | Paquetes | SHA-256 |
|---|---|---|---|
| `requirements/core-bridge-dev.lock` | core+bridge+cli+dev | 30 | `0cb96d720376a3d37cbfaaa94a3dda4d078d4d27206b47077a4cc0b276efaf1f` |
| `requirements/full-research.lock` | todo (core→research-vectorbt) | 81 | `6e1759888487622260e15a5a78b424374d72349b33209bb3b7b892f93e1a3ef2` |

El lock full se generó usando el base como constraints; `tests/foundation/test_environment_contract.py::test_lock_consistency_base_subset_of_full` verifica **cero divergencia** en paquetes compartidos y que base ⊂ full.

Núcleo pinneado (idéntico en ambos locks): numpy 2.4.6 · pandas 3.0.3 · numba 0.66.0 · llvmlite 0.48.0 · pyarrow 25.0.0 · pydantic 2.13.4 · duckdb 1.5.4 · polars 1.43.0.

## Entorno de trabajo diario (`.venv`, desde el lock base)
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes --no-deps -r requirements\core-bridge-dev.lock
.\.venv\Scripts\python -m pytest tests\foundation -m "not vectorbt" -q
```

## Entorno research (vectorbt) — NO persistente
No existe un `.venv-vectorbt` fijo: la evidencia de que funciona es `verify_full`. Se materializa desde el lock full cuando se reanude la investigación vectorbt (una línea):
```powershell
python -m venv .venv-research
.\.venv-research\Scripts\python -m pip install --require-hashes --no-deps -r requirements\full-research.lock
```

## Regenerar locks (toolchain pinneada)
```powershell
python -m venv _tooling
.\_tooling\Scripts\python -m pip install "pip-tools==7.6.0"
.\_tooling\Scripts\python -m piptools compile --generate-hashes --extra bridge --extra cli --extra dev -o requirements\core-bridge-dev.lock pyproject.toml
.\_tooling\Scripts\python -m piptools compile --generate-hashes --all-extras -o requirements\full-research.lock pyproject.toml
```

## Layout / package discovery
Auto-discovery de setuptools tomaría `edgelab, validation, strategies, databuild`. `pyproject.toml` limita a `packages = ["edgelab"]`. **El paquete NO se instala en editable** en F0B: el layout plano no permite un editable limpio sin empaquetar los siblings prohibidos. Las dependencias se gestionan por lockfiles; el código se ejecuta con la raíz del repo en `sys.path` (p.ej. `python -m ...` desde la raíz). Migración a layout instalable = tarea futura separada (F0C+).
