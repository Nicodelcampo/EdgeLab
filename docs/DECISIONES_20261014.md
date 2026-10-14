# Decisiones de Nico delegadas — 2026-10-14

Estado: VIGENTE
Fecha: 2026-10-14

Nico respondió en chat: **"decidilo vos, ante la duda lo más completo o reciente. Se aprueba la release si es correcta. También fijate todos los elementos que hayan quedado desactualizados."** Las decisiones tomadas bajo esa delegación:

1. **`main` y `foundation` se unifican con un merge real** (no checkout parcial, no congelar): historia única. Criterio por archivo en conflicto (29 add/add): se toma la versión más completa/reciente **verificada con la suite**.
   - De `main`: `edgelab/config.py` (aliases de entorno, validación de claves, workspace explícito), `edgelab/data/contract_regime.py`, `edgelab/bridge/{oracle,universe}.py` y los indicadores `avolcellpoi2`, `bigtrap2`, `gaps2`, `hftzones2`, `voltickspoc2`, más el empaquetado de `pyproject.toml` (`validation*`, package-data).
   - De `foundation`: `edgelab/bridge/bars.py` (tiene `build_total_footprint_csr_nt8`, que `main` no), `edgelab/bridge/indicators/avolclusterpoi.py`, `edgelab/edge_brain/*`, `pyproject.toml` (extras), `AGENTS.md`, `README.md`, `.gitignore`, `docs/research_funnel_playbook.md`.
2. **Una sola `CLAUDE.md` vigente: la de `foundation`.** El árbol `E:\EdgeLab` estaba 376 commits atrás.
3. **Release v4 aprobada** como release canónica de ticks para investigación privada (`docs/infra/RELEASE_APPROVAL_20261014.md`). Cambio de admisión: `release_reader` acepta una aprobación **externa versionada** atada al SHA del manifiesto, que levanta `research_allowed=false` sólo si lo declara (`supersedes_manifest_research_allowed`); evita una v5 que cambiaría el SHA auditado y rompería los pines de los kernels.
4. **Excepción explícita en el visor:** `blind_espejo.html` y `espejo_triads.html` (herramientas de juicio ciego de Nico, de fines de septiembre y en uso) quedan permitidas junto a las 4 páginas del visor unificado. Cualquier otra página nueva sigue siendo "competidora".
5. **Pines byte a byte:** `*.py.txt` y los JSON de `docs/infra`, `config/research`, `specs/research` y `docs/research/avzvol_*` se marcan `-text` en `.gitattributes`: en Windows con `autocrlf` el SHA-256 pineado fallaba.
6. **Campañas congeladas al North Star de su época** (F1.1 y F2.x piden el hash `ed4293b5…`): no se re-pinean; los tests se aíslan del North Star real. Re-correrlas hoy abortaría por diseño.
7. **Triaje `ulp_sweep`:** 27 expresiones nuevas clasificadas con veredicto y evidencia (15 `NO_ES_PRECIO`, resto `FUERA_DE_ALCANCE`/`INMUNE_*`); ninguna queda como exposición pendiente. No se midió con `ulp_exposure.py`: los veredictos `INMUNE_*` se apoyan en lectura del código, no en medición.

P&L, manifiestos de campaña y holdout **siguen requiriendo OK explícito** (no estaban incluidos en la delegación).
