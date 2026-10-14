# Inventario de la línea `main` (2026-10-14)

Estado: PROVISIONAL (unificación de líneas pendiente de decisión de Nico)  
Fecha: 2026-10-14

**Hallazgo.** `main` ya no es "baseline original": tiene **78 commits (PR #63–#106, todos de `Nicodelcampo`, 2026-10-02 a 2026-10-11)** que `foundation/f0b-compatibility-probe` no tiene, y `foundation` tiene 1.742 commits que `main` no tiene. Son **dos líneas vivas del mismo proyecto**. `CLAUDE.md` seguía diciendo "main = baseline, no mergear".
Medido con `git rev-list --left-right --count` y `git merge-tree` sobre `origin/*` el 2026-10-14. Un merge directo da **29 conflictos** (add/add en `edgelab/bridge`, `edgelab/edge_brain`, `config`, `AGENTS.md`, `README.md`, `pyproject.toml` y pruebas): ambas líneas crearon los mismos archivos de forma independiente.

## Qué aporta `main` (y `foundation` no tiene)
| Área | Contenido | Archivos nuevos |
|---|---|---|
| Línea de investigación AVZVOL | MNQ 25t: O5/O2/retest/vencimientos, controles outcome-blind, QA de etiquetas; PR #77–#106. **Sin P&L** (sus propias actas lo declaran) | ≈118 docs en `docs/research`, 14 en `config/research` |
| `edgelab/funnel` | Funnel exploratorio CPU con separación de etapas D0/D1; paridad GPU pendiente | 12 |
| `edgelab/data/research_data_gate.py`, `edgelab/kaggle/research_access.py`, `docs/DATA_CONSUMER_MATRIX.md` | Compuerta opt-in fail-closed para lectores de datos de research; lectores legacy aún sin cablear | 9 + 16 |
| `config/component_registry.json`, `tools/edgelab_catalog.py` | Catálogo de 17 componentes y chequeo de navegación | 2 |
| `integrations/notion-workers` | Workers de Notion (auditor, operaciones) | 6 |
| `tools/` | Utilidades de auditoría y spec Kaggle v2 | 44 |
| `edgelab/edge_brain`, `edgelab/bridge` | Versiones **paralelas** de módulos que `foundation` también tiene (origen de los conflictos) | 51 y 39 |

## Qué NO se hace en este documento
No se mergea, no se resuelve ningún conflicto y no se toca semántica de validación. Cada archivo en conflicto exige decidir cuál versión rige (CLAUDE.md: los cambios de semántica de validación se consultan con Nico).

## Opciones de unificación (para decisión de Nico)
1. **Traer de `main` a `foundation` sólo lo que no existe** (funnel, `research_data_gate`, `research_access`, `DATA_CONSUMER_MATRIX`, `edgelab_catalog`, workers, actas AVZVOL) por checkout de rutas, como se hizo con la release líquida. Los 29 archivos duplicados se dejan en `foundation` y se deja constancia de las diferencias. **Recomendada**: bajo riesgo, sin tocar semántica.
2. **Merge completo** resolviendo los 29 conflictos a mano: alto costo y alto riesgo de regresión silenciosa.
3. **Congelar `main`** como archivo de la línea AVZVOL y declarar sólo `foundation` viva. Pierde la compuerta de datos y el funnel hasta reescribirlos.

Hasta que se decida, `config/modules.json` registra estos módulos con `status: other-branch` para que el mapa del producto sea verdadero.
