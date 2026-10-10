# Entorno de la base de producto

## Alcance

Runtime soportado por este lote: **CPython 3.12**. El catálogo stdlib de navegación también puede usarse en Python 3.10+, pero no implica soporte del motor en ese rango. Los locks de foundation pertenecen a otra base y no se sustituyen silenciosamente.

## Instalación aislada

```bash
python3.12 -m venv .venv
# Linux/macOS:
.venv/bin/python -m pip install --require-hashes -r requirements/cpu-dev-py312.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation .
.venv/bin/python -m pytest -q
```

Windows: usar `.venv\Scripts\python.exe` en lugar de `.venv/bin/python`. No se acreditó todavía una ejecución Windows; CI de este lote es Ubuntu/Python 3.12. No modificar Python global.

El lock incluye core, bridge, funnel, validation y dev, **no CUDA**. Las requirements históricas del funnel siguen disponibles para entornos Kaggle específicos; no son el lock de esta base. `pip install '.[gpu]'` sólo cuando la imagen CUDA coincida y haya un plan de validación separado. Ningún smoke CPU acredita paridad GPU.

## Paquete y wheel

El wheel incluye subpaquetes `edgelab.*`, soporte `validation.*` (el funnel lo importa) y perfiles JSON del indicador. No incluye datasets, CSV de resultados, campañas `docs/`, builders, strategies ni herramientas del repo. Los scripts legacy dentro de validation no se ejecutan por instalar el paquete: no representan la API estable ni están todos acreditados por un smoke.

```bash
.venv/bin/python -m build --wheel --no-isolation
```

CI instala el wheel en un segundo venv y ejecuta un smoke copiado fuera del checkout, sin `PYTHONPATH`. No presentar importación exitosa como validación científica.

## Rutas de datos — cambio de compatibilidad explícito

`edgelab.config` ya no usa rutas personales C:/D: ni crea directorios al importarse. `EDGELAB_ROOT` fija workspace; sin esa variable se usa **cwd**. Recomendación para operaciones de datos: fijarla siempre y no usar site-packages como workspace.

Variables: `EDGELAB_DATA_DIR`, `EDGELAB_RUNS_DIR`, `EDGELAB_ES_TICKS`, `EDGELAB_ES_M1`, `EDGELAB_NQ_RAW_DIR`, `EDGELAB_NQ_TICKS_CLEAN`, `EDGELAB_NQ_M1_CLEAN`, `EDGELAB_EURUSD_TICKS_RAW`, `EDGELAB_EURUSD_TICKS`.

Si una fuente externa vivía fuera del repo, **configurar su ruta explícitamente**. No se migran/copian datos ni se usa fallback al filesystem personal. El llamador puede usar `prepare_workspace()` para crear sólo los directorios de trabajo; nunca se hace como efecto de import. Una ruta no demuestra aprobación, completitud ni sanidad: se mantiene el preregistro y preflight por campaña.

## Validación y regeneración

Suite `tests/` de esta base: navegación, imports, señales/funnel sintéticos, entorno y motor sintético. No incluye la suite mucho mayor de foundation ni resuelve por sí sola issue 37. `testpaths=["tests"]` evita descubrir scripts legacy de research como tests.

Regenerar el lock con uv dentro de un venv de tooling, Python 3.12 y revisión del diff:

```bash
uv pip compile pyproject.toml --python .venv/bin/python --extra bridge --extra funnel --extra validation --extra dev --generate-hashes -o requirements/cpu-dev-py312.lock
```

No actualizar pins automáticamente como respuesta a resultados económicos.
