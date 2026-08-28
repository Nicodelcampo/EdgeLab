# AUDITOR START HERE — EdgeLab

> **Punto de entrada único actualizado: 2026-08-28.**  
> **Base de integración vigente:** `foundation/f0b-compatibility-probe@8ebda7840bc3f0a7e39f3561db75a2c9090fd55f`  
> **Estado vivo:** `docs/CURRENT.md`  
> **Inventario remoto:** `docs/BRANCH_REGISTRY_2026-08-28.md`

## Lectura obligatoria

1. [`docs/CURRENT.md`](docs/CURRENT.md)
2. [`docs/PROJECT_STATE_2026-08-28.md`](docs/PROJECT_STATE_2026-08-28.md)
3. [`docs/BRANCH_REGISTRY_2026-08-28.md`](docs/BRANCH_REGISTRY_2026-08-28.md)
4. [`docs/TRACEABILITY.md`](docs/TRACEABILITY.md)
5. [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md)
6. [`docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md`](docs/incidents/INCIDENTE_OUTCOMES_UNTRACKED_2026-08-24.md)
7. [`PENDIENTE.md`](PENDIENTE.md)

No empezar por el árbol completo de `docs/research/`: mezcla documentos vigentes, borradores, resultados y material histórico.

## Estado en 90 segundos

- El remoto expone **44 ramas**, todas sin protección al corte; no borrar ni mergear por inferencia.
- `main` sigue siendo un baseline antiguo. La base de integración es `foundation/f0b-compatibility-probe`.
- La cadena BT2A activa está distribuida entre PR #15, #16, #18 y #20; no asumir que una rama descendiente ya integra formalmente sus ancestros.
- PR #17 materializa coordenadas target-free de indicadores.
- PR #19 prepara el protocolo aVolClusterPOI → dirección BigTrap en dos etapas.
- La rama `research/avolcluster-nq-microticks-v1-20260828` publicó un sweep target-free de NQ. `tick_120_W5_M20_C4_P950` quedó primera por fitness estructural; no es un resultado de Gate 1 ni evidencia de edge.
- PR #20 sigue en draft y no está lista para freeze: el check contractual pasó, dos checks `pytest` fallaron y Camino B todavía no liga lógicamente las filas del Parquet con los 234 checkpoints.
- Holdout temporal `2026-07-01 → 2026-12-31`: no usar para diseño, selección ni rescate post-hoc.

## Primeros comandos

```powershell
git remote -v
git fetch --all --prune
git rev-parse --show-toplevel
git rev-parse HEAD
git worktree list
git status --short --untracked-files=all
.venv\Scripts\python tools\estado.py
```

Detectar el nombre real del remoto; no asumir `origin`.

## Reglas no negociables

- Repo Git > Notion > memoria del chat.
- Un spec/manifest congelado manda sobre un resumen para el objeto que gobierna.
- No mover paths ya citados por estética.
- No borrar, cerrar o mergear ramas sin decisión explícita y verificación mecánica de ancestry/patch-equivalence.
- Una validación target-free no autoriza outcomes.
- Antes de medir outcomes: STOP, manifest, familia efectiva, riesgos, datos y autorización explícita.
- Todo resultado actualiza MEDIDO/NO MEDIDO en el mismo commit.
- Todo checkpoint termina con `Aporte al referente: …`.

## Aporte al referente

El arranque ya refleja las ramas y campañas abiertas al 28-ago, separa resultados target-free de outcomes y evita que un auditor tome `main`, una PR descendiente o un informe declarativo como integración científica consolidada.
