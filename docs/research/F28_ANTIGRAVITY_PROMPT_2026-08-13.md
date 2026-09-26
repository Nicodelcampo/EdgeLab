# Prompt para Google Antigravity — F2.8

Paso 0 obligatorio: **fetch**. El ABSTAIN de las 03:02 ART fue correcto para un checkout en `1b8e168`, pero incorrecto como diagnóstico del remoto. Los prerrequisitos ya están en `origin/research/bigtrap2-local-displacement-null`.

## Paso 0 — alinear el grafo

```text
git fetch origin research/bigtrap2-local-displacement-null
git checkout research/bigtrap2-local-displacement-null
git merge --ff-only origin/research/bigtrap2-local-displacement-null
git rev-parse HEAD
git cat-file -t 4d522320a3ef3663ecfa9ad92a13f2dbda9175fb
```

HEAD esperado después del ff-only:

```text
4d522320a3ef3663ecfa9ad92a13f2dbda9175fb
```

Cadena sobre `1b8e168`:

```text
1b8e168  F2.7 formal artifact
00eec6d  docs(f28): preregister protocol
49d0e36  feat(f28): residual labels
0ee1ed5  feat(f28): interruption, controls
4d52232  test(f28): interruption/control geometry
```

Si `git cat-file -t 4d52232` falla **después** del fetch, ahí sí ABSTAIN_PROVENANCE. Si falla antes del fetch, el árbol local está atrasado: no reescribir nada.

Archivos que deben existir después del fetch:

```text
specs/bigtrap2_f28_distance_coverage_v0.json
docs/research/BIGTRAP2_F28_DISTANCE_COVERAGE_PROTOCOL_2026-08-13.md
docs/research/F28_ANTIGRAVITY_PROMPT_2026-08-13.md
edgelab/research/f28/__init__.py
edgelab/research/f28/residual_atlas.py
edgelab/research/f28/interruption.py
edgelab/research/f28/controls.py
tests/research/test_f28_residual_atlas.py
tests/research/test_f28_interruption.py
```

Verificación remota independiente:
https://github.com/Nicodelcampo/EdgeLab/commit/4d522320a3ef3663ecfa9ad92a13f2dbda9175fb

---

Sos el implementador local de EdgeLab. No sos un auditor informal y no estás autorizando Z2.

Trabajá **sólo** en `research/bigtrap2-local-displacement-null`. Si el árbol está sucio, parar.

## Qué ya está hecho. No lo reescribas

Los archivos de arriba. También F2.7 formal y runner:

- `diag/tasa_senales/F2.7_formal_93c2e3f3ac44.json`
- `diag/tasa_senales/F2.7_nulo_reflexion_local.py`

F2.7 ya adjudicó:

```text
Δ = +0.04815265363200558
IC95 = [0.0306759691, 0.0656293381]
201 sesiones / 15947 zonas
8280 real primero / 7661 espejo primero
d p50 = 2; frac_le_2 = 0.6267; frac_le_5 = 0.9108
overlap espejo-otra-zona = 15890  (NO es ocupación de rango)
```

Eso es un hecho geométrico. F2.8 localiza el mecanismo y mapea residuales. No es un tribunal para matar BigTrap2.

## Datos canónicos. No uses los Parquet de Z1

```text
6E_12-25_ticks.parquet  ea8b9f211929658494d952677fe302c33db66086ec1a21731f1f5d7ff74f7336
6E_03-26_ticks.parquet  b54120bfd99b97f218d73a1fe132bd111b997eab6095a529699473131f57cf76
6E_06-26_ticks.parquet  124b37507b95a1027aa753a75213b15e74f66b1396ca8df3c4324ea835f96cb1
6E_09-26_ticks.parquet  6ffcdf041f8d77a2d6fb7cfe85d63bd8b176a081caa8ad8cd0aaae57c6f178f4
```

Si el hash no coincide, **ABSTAIN_PROVENANCE**. No sustituyas por `fd2e358…` ni `654e006…`.
Rutas: `data/nt8/6E/<archivo>` vía `data_root()` de F2.7.

## Tarea

Implementá de forma **aditiva** `diag/tasa_senales/F2.8_atlas_residuales.py`.

Reusá, no copies divergente: `construir_reflejo`, `first_passage_race`, `zone_lifecycle`, `agregar_por_sesion`, `hac_bartlett_ic`, `dias_research`, carga canónica y firewall de F2.7.

No toques `bigtrap2.py`, F1.1, holdout, tick:25, P&L, retornos, dirección, Z2 ni Kaggle.

### Orden de corrida

1. Reproducir totales F2.7 (201, 15947, Δ global compatible).
2. Familia A: curva de `Δ(d)` con `d<=2`, `3<=d<=5`, `d>=6`, más `d>3` y `d>5`.
3. Familia C: ocupación activa precio × tiempo. Unión de zonas **vivas** sobre `[low,high]` de cada barra. 200 colocaciones aleatorias/sesión, semilla `20260813`.
4. Familia B: controles de barra creadora.
5. Familia E: tras primer contacto, 5 barras: `through` / `bounce` / `stay`. Sin P&L.
6. Familia D: etiquetar residuales con `decide_labels`.
7. Escribir `diag/tasa_senales/F2.8_formal_<sha12>.json` y un markdown de reporte.

### Gates y etiquetas

201 sesiones; cobertura ≥ 0.95; resolución global ≥ 0.30; empates técnicos ≤ 0.01; estrato ≥30 sesiones y ≥200 pares resueltos o `CONTINUE_AMBIGUOUS`; árbol limpio; `outcomes_accessed=false`.

```text
OPEN_FAR_ZONE_FAMILY
OPEN_BAR_CLASSIFIER
OPEN_HOLE_FAMILY
OPEN_FADE_MIRROR
OPEN_INTERRUPTION_FAMILY
OPEN_DENSITY_FEATURES
CLOSE_ZONE_ATTRACTION
CONTINUE_AMBIGUOUS
```

Cualquier `OPEN_*` produce **una** spec de seguimiento. No autorices Z2.

## Tests y ejecución

```text
./.venv/Scripts/python.exe -m pytest tests/research/test_f28_residual_atlas.py tests/research/test_f28_interruption.py -q
./.venv/Scripts/python.exe diag/tasa_senales/F2.8_atlas_residuales.py --formal
```

Si el venv está en otra ruta gobernada, usala. Si no hay venv, no ejecutes.

## Qué devolver

1. `git rev-parse HEAD` después del fetch.
2. Totales F2.7 reproducidos sí/no.
3. Tabla `Δ(d)`.
4. Ocupación p50/p90 y isolated_rate.
5. Match rate y contraste de controles.
6. through/bounce/stay.
7. Labels.
8. Una sola familia siguiente, si hay `OPEN_*`.
9. Confirmación: no holdout, no P&L, no Z2.
