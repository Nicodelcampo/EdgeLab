# EdgeLab

> Este documento sirve al referente rector: ver [`docs/NORTH_STAR.md`](docs/NORTH_STAR.md).

Infraestructura de investigación cuantitativa. Dos líneas de trabajo:

1. **Legacy ES/NQ/EURUSD** (`strategies/`, `validation/`, `databuild/`) —
   motor tick + gauntlet estadístico. **EURUSD/ARB pausado** (candidato no
   validado, sin experimento en el ledger científico central). Ver
   `EDGES_DISCOVERED.md`, `PLAN.md`.
2. **NT8 Indicator Bridge** (`edgelab/bridge/`, activo) — traduce indicadores
   NT8 a Python, verifica paridad numérica contra NT8 real, y guarda las
   coordenadas de zonas en un store reutilizable para vectorbt/fuerza bruta.

Para retomar el trabajo (humano o sesión de Claude nueva), leer en este orden:

1. **`docs/foundation/SCOPE.md`** — charter: qué está pausado, qué es
   prioridad, roadmap de fases (F0–F9+) y gates (P0/P1/P2).
2. **`CONTRATO_LLM.md`** — reglas para proponer/tocar estrategias legacy.
3. **`ENVIRONMENT.md`** — cómo reconstruir el entorno (abajo, resumido).
4. **`docs/nt8_bridge.md`** — cómo usar el bridge (CLI, visor, zone store).
5. **`docs/nt8_indicator_parity_contract.md`** — protocolo de paridad real
   contra NT8, con el primer oráculo pre-registrado (Gaps2, 6E 06-26).
6. **`docs/foundation/F0B_COMPATIBILITY_REPORT.md`** — por qué el stack de
   dependencias es el que es.

## Estado (branch `foundation/f0b-compatibility-probe`)

```
cde6d93 baseline (tag baseline-pre-foundation) — snapshot original preservado
49289a1 entorno reproducible (.venv vía lockfiles, sin tocar Python global)
b702515 configuración portable (config/default.toml + local.toml + EDGELAB_*)
ceece76 charter de scope
1af710e contrato de datos NT8 .Last.txt (F1)
5a4da89 conversor NT8 → parquet canónico con auditor P0 (F2)
04e24bb bridge: reader F2 + barras tiempo/tick + footprint (gate P1A)
b030e4a bridge: kernel Gaps2 + oráculo NT8 + matcher de paridad (gate P2)
da28b8b bridge: CLI + zone store + visor offline multi-run
```

`main` sigue apuntando al baseline original (`cde6d93`); todo el trabajo de
foundation vive en `foundation/f0b-compatibility-probe`, sin mergear.

## Bootstrap en una máquina nueva

```powershell
# 1. entorno (NO se versiona .venv/; se reconstruye desde el lock)
python -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes --no-deps -r requirements\core-bridge-dev.lock

# 2. config local (rutas de ESTA máquina; gitignored)
copy config\local.toml.example config\local.toml
# editar config\local.toml si vas a usar CerebroSSRN / VectorBTecosistema

# 3. verificar
.\.venv\Scripts\python -m pytest tests -m "not vectorbt" -q
```

Si `config/local.toml` viajó pegado desde otra máquina, sus rutas
(`vectorbt_ecosystem_root`, `cerebro_root`, etc.) casi seguro NO son válidas
acá — son opcionales (`None` si no se configuran) y solo hacen falta para el
research legacy ES/NQ, no para el bridge NT8.

## Datos incluidos en este paquete

- `TickData/` — exports crudos NT8 `.Last.txt` de 6E (fuente irremplazable
  salvo reexport desde el broker).
- `data/nt8/6E/` — parquets canónicos ya convertidos (F2). Regenerables desde
  `TickData/` con `python -m databuild.build_nt8_ticks` (~1 min) si hiciera
  falta.
- `data/eurusd_ticks.parquet`, `data/nq_m1_clean.parquet` — ticks del research
  legacy EURUSD/ES (pausado, preservado).
- `runs/nt8_bridge/` — corridas de ejemplo del bridge (demo sintética + una
  muestra real de 6E 09-25 con grid de parámetros).

## Bridge NT8 — uso rápido

```powershell
.\.venv\Scripts\python tools\run_nt8_bridge.py --synthetic --indicator Gaps2 --out runs\nt8_bridge\demo
# abrir runs\nt8_bridge\demo\viewer\index.html (servido por HTTP, no file://)
```

Detalle completo en `docs/nt8_bridge.md`.
