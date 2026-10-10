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

El lock CPU incluye core, bridge, funnel, validation y dev, **no CUDA**. `requirements/core-py312.lock` es el subconjunto fijado a esas mismas versiones para importar el núcleo sin Arrow, DuckDB, SciPy ni CUDA. Las requirements históricas del funnel siguen disponibles para entornos Kaggle específicos; no son el lock de esta base. `pip install '.[gpu]'` sólo cuando la imagen CUDA coincida y haya un plan de validación separado. Ningún smoke CPU acredita paridad GPU.

## Paquete y wheel

El wheel incluye subpaquetes `edgelab.*`, soporte `validation.*` (el funnel lo importa) y perfiles JSON del indicador y esquemas JSON de Brain. No incluye datasets, CSV de resultados, campañas `docs/`, builders, strategies ni herramientas del repo. Los scripts legacy dentro de validation no se ejecutan por instalar el paquete: no representan la API estable ni están todos acreditados por un smoke.

```bash
.venv/bin/python -m build --wheel --no-isolation
```

CI instala el wheel en un segundo venv y ejecuta un smoke copiado fuera del checkout, sin `PYTHONPATH`. No presentar importación exitosa como validación científica.

## Configuración reconciliada con foundation

Se porta su API `EdgeLabPaths`, `resolve_settings` y `ensure_dir`, sin reinstaurar rutas personales ni escritura al importar. Precedencia: **config/local.toml > EDGELAB_* > config/default.toml > workspace (cwd)**. Para una operación de datos fijar `EDGELAB_ROOT`; los TOML por defecto se buscan en ese workspace, nunca automáticamente en site-packages.

`config/local.toml` está gitignored; usar `config/local.toml.example`. No guardar credenciales. Claves TOML desconocidas y aliases ambientales contradictorios fallan explícitamente.

Aliases compatibles: DATA_ROOT / DATA_DIR, RUNS_ROOT / RUNS_DIR y NQ_RAW_ROOT / NQ_RAW_DIR (todos con prefijo EDGELAB_). También se recuperan ARTIFACTS_ROOT, CACHE_ROOT, MANIFESTS_ROOT, PARITY_ROOT, FEATURE_ZONE_STORE_ROOT, NT8_EXPORT_ROOT, CEREBRO_ROOT y VECTORBT_ROOT. Overrides directos de archivos del lote anterior se conservan.

**Fuentes externas sin configurar son None**, no rutas de máquina ni un archivo implícito. Es un cambio explícito respecto del default provisional del lote 2: los builders legacy deben exigir una fuente antes de usarse. Productos internos siguen siendo root-relativos. No se migran datos ni se adjudica su validez. Una ruta y un parseo correctos no acreditan completitud, liquidez ni permiso.

`prepare_workspace()` crea data/runs únicamente cuando el llamador lo pide; `ensure_dir()` permite otros directorios explícitos. El contrato y ventanas de `poison_mask` se preservan.

## Validación y regeneración

Suite `tests/` de esta base: navegación, imports, señales/funnel sintéticos, entorno y motor sintético. No incluye la suite mucho mayor de foundation ni resuelve por sí sola issue 37. `testpaths=["tests"]` evita descubrir scripts legacy de research como tests.

Regenerar el lock con uv dentro de un venv de tooling, Python 3.12 y revisión del diff:

```bash
uv pip compile pyproject.toml --python .venv/bin/python --extra bridge --extra funnel --extra validation --extra dev --generate-hashes -o requirements/cpu-dev-py312.lock
```

Regenerar core como subconjunto consistente: `uv pip compile pyproject.toml --python .venv/bin/python --constraint requirements/cpu-dev-py312.lock --generate-hashes -o requirements/core-py312.lock`.

No actualizar pins automáticamente como respuesta a resultados económicos.
